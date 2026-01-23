#!/usr/bin/env python
"""
Link proper nouns to Wikidata entities.

For each unique proper noun (by reference_form + entity_type), queries Wikidata
for matching entities, uses GPT to disambiguate when multiple candidates exist,
and stores the Q-code. For places, also fetches coordinates and Pleiades IDs.

Usage:
    python link_wikidata.py                     # Link all unlinked nouns
    python link_wikidata.py --stop-after 10     # Process only 10 entries
    python link_wikidata.py --relink            # Re-process already linked entries
    python link_wikidata.py --dry-run           # Show what would be done
"""
import argparse
import json
import os
import sqlite3
import time
from datetime import datetime

import requests
from openai import OpenAI
from tqdm import tqdm

# Wikidata SPARQL endpoint
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# OpenAI model for disambiguation
DISAMBIGUATION_MODEL = "gpt-5-mini"

# User-Agent for Wikidata requests
USER_AGENT = "PausaniasProject/1.0 (ancient geography research)"

# Wikidata types to EXCLUDE when searching for places
PLACE_EXCLUDE_TYPES = [
    "Q5",          # human
    "Q11424",      # film
    "Q7725634",    # literary work
    "Q16521",      # taxon
    "Q4167410",    # disambiguation page
    "Q13442814",   # scholarly article
    "Q571",        # book
    "Q215380",     # musical group
    "Q482994",     # album
    "Q134556",     # single (music)
    "Q5398426",    # television series
    "Q7889",       # video game
    "Q4830453",    # business
    "Q431289",     # brand
    "Q35127",      # website
]

# Ancient world bounding box
ANCIENT_WORLD_BOUNDS = {
    "min_lon": -15.0,
    "max_lon": 80.0,
    "min_lat": 10.0,
    "max_lat": 55.0,
}


def parse_arguments():
    parser = argparse.ArgumentParser(description="Link proper nouns to Wikidata entities")
    parser.add_argument("--database", default="pausanias.sqlite",
                        help="SQLite database file (default: pausanias.sqlite)")
    parser.add_argument("--openai-api-key-file", default="~/.openai.key",
                        help="File containing OpenAI API key (default: ~/.openai.key)")
    parser.add_argument("--stop-after", type=int, default=None,
                        help="Maximum number of entries to process")
    parser.add_argument("--relink", action="store_true",
                        help="Re-process already linked entries")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay between Wikidata API calls (default: 1.0)")
    parser.add_argument("--progress-bar", action="store_true", default=False,
                        help="Show progress bar")
    return parser.parse_args()


def load_openai_api_key(key_file):
    key_path = os.path.expanduser(key_file)
    with open(key_path, 'r') as f:
        return f.read().strip()


def create_tables(conn):
    """Create tables for Wikidata links and place coordinates."""
    conn.execute('''
    CREATE TABLE IF NOT EXISTS wikidata_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference_form TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        english_transcription TEXT NOT NULL,
        wikidata_qid TEXT,
        confidence TEXT NOT NULL,
        linked_at TEXT NOT NULL,
        UNIQUE(reference_form, entity_type)
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS place_coordinates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wikidata_qid TEXT NOT NULL UNIQUE,
        reference_form TEXT NOT NULL,
        english_transcription TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        pleiades_id TEXT,
        fetched_at TEXT NOT NULL,
        FOREIGN KEY (wikidata_qid) REFERENCES wikidata_links(wikidata_qid)
    )
    ''')

    conn.commit()


def get_unlinked_nouns(conn, limit=None, relink=False):
    """Get unique proper nouns that need Wikidata linking."""
    cursor = conn.cursor()

    if relink:
        query = """
            SELECT reference_form, entity_type, MIN(english_transcription)
            FROM proper_nouns
            GROUP BY reference_form, entity_type
            ORDER BY CASE entity_type WHEN 'place' THEN 0 WHEN 'person' THEN 1 WHEN 'deity' THEN 2 ELSE 3 END, reference_form
        """
    else:
        query = """
            SELECT p.reference_form, p.entity_type, MIN(p.english_transcription)
            FROM proper_nouns p
            LEFT JOIN wikidata_links w
                ON p.reference_form = w.reference_form
                AND p.entity_type = w.entity_type
            WHERE w.id IS NULL
            GROUP BY p.reference_form, p.entity_type
            ORDER BY CASE p.entity_type WHEN 'place' THEN 0 WHEN 'person' THEN 1 WHEN 'deity' THEN 2 ELSE 3 END, p.reference_form
        """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    return cursor.fetchall()


def get_passage_context(conn, reference_form):
    """Get a sample passage containing this proper noun for disambiguation context."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pa.passage
        FROM proper_nouns pn
        JOIN passages pa ON pn.passage_id = pa.id
        WHERE pn.reference_form = ?
        LIMIT 1
    """, (reference_form,))
    row = cursor.fetchone()
    return row[0][:300] if row else ""


def normalize_name(name):
    """Generate search variants for a name."""
    variants = [name]

    # Greek to Latin ending conversions
    if name.endswith('os'):
        variants.append(name[:-2] + 'us')
    elif name.endswith('us'):
        variants.append(name[:-2] + 'os')

    if name.endswith('on'):
        variants.append(name[:-2] + 'um')
    elif name.endswith('um'):
        variants.append(name[:-2] + 'on')

    return list(dict.fromkeys(variants))


def is_within_ancient_world(lat, lon):
    """Check if coordinates fall within the ancient world."""
    if lat is None or lon is None:
        return True
    bounds = ANCIENT_WORLD_BOUNDS
    return (bounds["min_lon"] <= lon <= bounds["max_lon"] and
            bounds["min_lat"] <= lat <= bounds["max_lat"])


def query_wikidata_person(name_english, name_greek=None):
    """Query Wikidata for person entities (humans, ancient period)."""
    search_terms = normalize_name(name_english)
    if name_greek:
        search_terms.append(name_greek)
    search_terms = list(dict.fromkeys(search_terms))

    candidates = []

    for term in search_terms[:4]:
        try:
            search_response = requests.get(
                "https://www.wikidata.org/w/api.php",
                params={
                    "action": "wbsearchentities",
                    "search": term,
                    "language": "en",
                    "limit": 10,
                    "format": "json"
                },
                headers={"User-Agent": USER_AGENT},
                timeout=30
            )
            search_response.raise_for_status()
            search_data = search_response.json()

            qids = [r["id"] for r in search_data.get("search", [])]
            if not qids:
                continue

            qid_values = " ".join(f"wd:{qid}" for qid in qids)
            query = f"""
            SELECT DISTINCT ?item ?itemLabel ?itemDescription ?birthYear ?deathYear
                   (GROUP_CONCAT(DISTINCT ?occupationLabel; separator=", ") AS ?occupations)
            WHERE {{
                VALUES ?item {{ {qid_values} }}
                ?item wdt:P31 wd:Q5 .
                OPTIONAL {{
                    ?item wdt:P569 ?birth .
                    BIND(YEAR(?birth) AS ?birthYear)
                }}
                OPTIONAL {{
                    ?item wdt:P570 ?death .
                    BIND(YEAR(?death) AS ?deathYear)
                }}
                OPTIONAL {{
                    ?item wdt:P106 ?occupation .
                    ?occupation rdfs:label ?occupationLabel .
                    FILTER(LANG(?occupationLabel) = "en")
                }}
                FILTER(!BOUND(?deathYear) || ?deathYear < 600)
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,grc,la". }}
            }}
            GROUP BY ?item ?itemLabel ?itemDescription ?birthYear ?deathYear
            LIMIT 20
            """

            response = requests.get(
                WIKIDATA_ENDPOINT,
                params={"query": query, "format": "json"},
                headers={"User-Agent": USER_AGENT},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            for result in data.get("results", {}).get("bindings", []):
                qid = result["item"]["value"].split("/")[-1]
                if any(c["qid"] == qid for c in candidates):
                    continue
                candidates.append({
                    "qid": qid,
                    "label": result.get("itemLabel", {}).get("value", ""),
                    "description": result.get("itemDescription", {}).get("value", ""),
                    "birth_year": result.get("birthYear", {}).get("value"),
                    "death_year": result.get("deathYear", {}).get("value"),
                    "occupations": result.get("occupations", {}).get("value", ""),
                })

        except Exception as e:
            print(f"  Warning: Wikidata query failed for '{term}': {e}")

        time.sleep(0.3)

    return candidates


def query_wikidata_place(name_english, name_greek=None):
    """Query Wikidata for place entities with coordinates."""
    search_terms = normalize_name(name_english)
    if name_greek:
        search_terms.append(name_greek)
    # Add "ancient" variants
    for term in list(search_terms):
        search_terms.append(f"ancient {term}")
    search_terms = list(dict.fromkeys(search_terms))[:6]

    candidates = []
    seen_qids = set()

    for term in search_terms:
        try:
            search_response = requests.get(
                "https://www.wikidata.org/w/api.php",
                params={
                    "action": "wbsearchentities",
                    "search": term,
                    "language": "en",
                    "limit": 10,
                    "format": "json"
                },
                headers={"User-Agent": USER_AGENT},
                timeout=30
            )
            search_response.raise_for_status()
            search_data = search_response.json()

            qids = [r["id"] for r in search_data.get("search", []) if r["id"] not in seen_qids]
            seen_qids.update(qids)
            if not qids:
                continue

            qid_values = " ".join(f"wd:{qid}" for qid in qids)
            query = f"""
            SELECT DISTINCT ?item ?itemLabel ?itemDescription ?coord ?placeType ?placeTypeLabel
                   ?pleiadesId ?countryLabel
            WHERE {{
                VALUES ?item {{ {qid_values} }}
                OPTIONAL {{ ?item wdt:P625 ?coord . }}
                OPTIONAL {{ ?item wdt:P31 ?placeType . }}
                OPTIONAL {{ ?item wdt:P6766 ?pleiadesId . }}
                OPTIONAL {{ ?item wdt:P17 ?country . }}
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,grc,la". }}
            }}
            """

            response = requests.get(
                WIKIDATA_ENDPOINT,
                params={"query": query, "format": "json"},
                headers={"User-Agent": USER_AGENT},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # Group results by QID
            qid_data = {}
            for result in data.get("results", {}).get("bindings", []):
                qid = result["item"]["value"].split("/")[-1]

                if qid not in qid_data:
                    lat, lon = None, None
                    coord = result.get("coord", {}).get("value", "")
                    if coord and coord.startswith("Point("):
                        coords = coord.replace("Point(", "").replace(")", "").split()
                        if len(coords) == 2:
                            lon, lat = float(coords[0]), float(coords[1])

                    qid_data[qid] = {
                        "qid": qid,
                        "label": result.get("itemLabel", {}).get("value", ""),
                        "description": result.get("itemDescription", {}).get("value", ""),
                        "lat": lat,
                        "lon": lon,
                        "pleiades_id": result.get("pleiadesId", {}).get("value"),
                        "country": result.get("countryLabel", {}).get("value", ""),
                        "types": set(),
                        "type_labels": set(),
                    }

                place_type = result.get("placeType", {}).get("value", "").split("/")[-1]
                type_label = result.get("placeTypeLabel", {}).get("value", "")
                if place_type:
                    qid_data[qid]["types"].add(place_type)
                if type_label:
                    qid_data[qid]["type_labels"].add(type_label)

            for qid, d in qid_data.items():
                if any(c["qid"] == qid for c in candidates):
                    continue

                # Skip excluded types
                if any(t in PLACE_EXCLUDE_TYPES for t in d["types"]):
                    continue

                # Skip coordinates outside ancient world
                if not is_within_ancient_world(d["lat"], d["lon"]):
                    continue

                # Score how "ancient" the place seems
                ancient_keywords = ['ancient', 'archaeological', 'historical', 'greek',
                                    'roman', 'polis', 'classical', 'hellenistic']
                desc_lower = (d["description"] or "").lower()
                type_str = " ".join(d["type_labels"]).lower()
                has_ancient_keyword = any(kw in desc_lower or kw in type_str
                                          for kw in ancient_keywords)

                d["is_ancient_place"] = (d["pleiades_id"] is not None or has_ancient_keyword)
                d["types"] = list(d["types"])
                d["type_labels"] = list(d["type_labels"])
                candidates.append(d)

        except Exception as e:
            print(f"  Warning: Wikidata query failed for '{term}': {e}")

        time.sleep(0.3)

    # Sort: ancient places first, then by coordinates available
    candidates.sort(key=lambda x: (
        not x.get("is_ancient_place", False),
        x.get("lat") is None,
        x.get("pleiades_id") is None,
    ))

    return candidates


def query_wikidata_deity(name_english, name_greek=None):
    """Query Wikidata for deity entities."""
    search_terms = normalize_name(name_english)
    if name_greek:
        search_terms.append(name_greek)
    search_terms = list(dict.fromkeys(search_terms))

    candidates = []

    for term in search_terms[:4]:
        try:
            search_response = requests.get(
                "https://www.wikidata.org/w/api.php",
                params={
                    "action": "wbsearchentities",
                    "search": term,
                    "language": "en",
                    "limit": 10,
                    "format": "json"
                },
                headers={"User-Agent": USER_AGENT},
                timeout=30
            )
            search_response.raise_for_status()
            search_data = search_response.json()

            qids = [r["id"] for r in search_data.get("search", [])]
            if not qids:
                continue

            qid_values = " ".join(f"wd:{qid}" for qid in qids)
            query = f"""
            SELECT DISTINCT ?item ?itemLabel ?itemDescription
            WHERE {{
                VALUES ?item {{ {qid_values} }}
                ?item wdt:P31/wdt:P279* ?type .
                FILTER(?type IN (wd:Q178885, wd:Q11688446, wd:Q24827227, wd:Q205985))
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,grc,la". }}
            }}
            LIMIT 10
            """
            # Q178885 = deity, Q11688446 = mythological character,
            # Q24827227 = ancient Greek deity, Q205985 = goddess

            response = requests.get(
                WIKIDATA_ENDPOINT,
                params={"query": query, "format": "json"},
                headers={"User-Agent": USER_AGENT},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            for result in data.get("results", {}).get("bindings", []):
                qid = result["item"]["value"].split("/")[-1]
                if any(c["qid"] == qid for c in candidates):
                    continue
                candidates.append({
                    "qid": qid,
                    "label": result.get("itemLabel", {}).get("value", ""),
                    "description": result.get("itemDescription", {}).get("value", ""),
                })

        except Exception as e:
            print(f"  Warning: Wikidata query failed for '{term}': {e}")

        time.sleep(0.3)

    return candidates


def query_wikidata_general(name_english, name_greek=None):
    """Query Wikidata with no type filter (for 'other' entities)."""
    search_terms = normalize_name(name_english)
    if name_greek:
        search_terms.append(name_greek)
    search_terms = list(dict.fromkeys(search_terms))

    candidates = []

    for term in search_terms[:3]:
        try:
            search_response = requests.get(
                "https://www.wikidata.org/w/api.php",
                params={
                    "action": "wbsearchentities",
                    "search": term,
                    "language": "en",
                    "limit": 5,
                    "format": "json"
                },
                headers={"User-Agent": USER_AGENT},
                timeout=30
            )
            search_response.raise_for_status()
            search_data = search_response.json()

            for r in search_data.get("search", []):
                if any(c["qid"] == r["id"] for c in candidates):
                    continue
                candidates.append({
                    "qid": r["id"],
                    "label": r.get("label", ""),
                    "description": r.get("description", ""),
                })

        except Exception as e:
            print(f"  Warning: Wikidata query failed for '{term}': {e}")

        time.sleep(0.3)

    return candidates


def disambiguate_with_gpt(client, name_english, name_greek, entity_type,
                           passage_context, candidates):
    """Use GPT to disambiguate between multiple Wikidata candidates."""
    if not candidates:
        return None, "not_found"

    if len(candidates) == 1:
        return candidates[0]["qid"], "high"

    # Format candidates
    candidate_lines = []
    for i, c in enumerate(candidates[:8]):
        line = f"{i+1}. {c['label']} ({c['qid']}): {c.get('description', 'No description')}"
        if c.get('birth_year') or c.get('death_year'):
            line += f" | Lived: {c.get('birth_year', '?')} - {c.get('death_year', '?')}"
        if c.get('occupations'):
            line += f" | Occupations: {c['occupations']}"
        if c.get('country'):
            line += f" | Country: {c['country']}"
        candidate_lines.append(line)

    candidate_text = "\n".join(candidate_lines)

    type_context = {
        "person": "This is a person mentioned in Pausanias's Description of Greece (2nd century CE travel writing about Greek places, myths, and history).",
        "place": "This is a place mentioned in Pausanias's Description of Greece (2nd century CE). It should be an ancient Greek location.",
        "deity": "This is a deity or divine figure mentioned in Pausanias's Description of Greece (2nd century CE).",
        "other": "This is an entity mentioned in Pausanias's Description of Greece (2nd century CE).",
    }

    prompt = f"""{type_context.get(entity_type, type_context['other'])}

Name (English): {name_english}
Name (Greek): {name_greek}
Entity type: {entity_type}

Passage context (Greek): {passage_context[:300]}

Wikidata candidates:
{candidate_text}

Which Wikidata entity is the correct match? Respond with ONLY a JSON object:
{{"qid": "Q123456", "confidence": "high|medium|low", "reasoning": "brief explanation"}}

If none match, respond: {{"qid": null, "confidence": "not_found", "reasoning": "explanation"}}
"""

    try:
        response = client.chat.completions.create(
            model=DISAMBIGUATION_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert in ancient Greek history, geography, and mythology."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        qid = result.get("qid")
        confidence = result.get("confidence", "low")
        reasoning = result.get("reasoning", "")

        if reasoning and not args_global.progress_bar:
            print(f"    GPT: {reasoning[:80]}")

        return qid, confidence

    except Exception as e:
        print(f"  Warning: GPT disambiguation failed: {e}")
        return None, "low"


def save_wikidata_link(conn, reference_form, entity_type, english_transcription,
                       qid, confidence):
    """Save a Wikidata link to the database."""
    conn.execute("""
        INSERT OR REPLACE INTO wikidata_links
        (reference_form, entity_type, english_transcription, wikidata_qid, confidence, linked_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (reference_form, entity_type, english_transcription, qid, confidence,
          datetime.now().isoformat()))
    conn.commit()


def save_place_coordinates(conn, qid, reference_form, english_transcription,
                           lat, lon, pleiades_id):
    """Save place coordinates to the database."""
    conn.execute("""
        INSERT OR REPLACE INTO place_coordinates
        (wikidata_qid, reference_form, english_transcription, latitude, longitude,
         pleiades_id, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (qid, reference_form, english_transcription, lat, lon, pleiades_id,
          datetime.now().isoformat()))
    conn.commit()


# Global args reference for use in disambiguate_with_gpt
args_global = None


def main():
    global args_global
    args = parse_arguments()
    args_global = args

    # Load OpenAI API key
    api_key = load_openai_api_key(args.openai_api_key_file)
    client = OpenAI(api_key=api_key)

    # Connect to database
    conn = sqlite3.connect(args.database)

    try:
        create_tables(conn)

        # Get nouns to process
        nouns = get_unlinked_nouns(conn, args.stop_after, args.relink)
        print(f"Found {len(nouns)} proper nouns to process")

        if not nouns:
            return

        linked = 0
        geocoded = 0
        not_found = 0

        iterator = tqdm(nouns) if args.progress_bar else nouns

        for reference_form, entity_type, english_transcription in iterator:
            if not args.progress_bar:
                print(f"\nProcessing: {english_transcription} ({reference_form}) [{entity_type}]")

            # Query Wikidata based on entity type
            if entity_type == "person":
                candidates = query_wikidata_person(english_transcription, reference_form)
            elif entity_type == "place":
                candidates = query_wikidata_place(english_transcription, reference_form)
            elif entity_type == "deity":
                candidates = query_wikidata_deity(english_transcription, reference_form)
            else:
                candidates = query_wikidata_general(english_transcription, reference_form)

            if not args.progress_bar:
                print(f"  Found {len(candidates)} candidates")

            if args.dry_run:
                for c in candidates[:3]:
                    desc = c.get('description', '')[:60]
                    geo = ""
                    if c.get('lat'):
                        geo = f" ({c['lat']:.2f}, {c['lon']:.2f})"
                    print(f"    - {c['label']} ({c['qid']}): {desc}{geo}")
                continue

            # Disambiguate
            passage_context = get_passage_context(conn, reference_form)
            qid, confidence = disambiguate_with_gpt(
                client, english_transcription, reference_form,
                entity_type, passage_context, candidates
            )

            # Save link
            save_wikidata_link(conn, reference_form, entity_type,
                              english_transcription, qid, confidence)

            if qid:
                if not args.progress_bar:
                    print(f"  Linked to {qid} (confidence: {confidence})")
                linked += 1

                # For places, also save coordinates
                if entity_type == "place":
                    selected = next((c for c in candidates if c["qid"] == qid), None)
                    if selected and selected.get("lat") is not None:
                        save_place_coordinates(
                            conn, qid, reference_form, english_transcription,
                            selected["lat"], selected["lon"],
                            selected.get("pleiades_id")
                        )
                        geocoded += 1
                        if not args.progress_bar:
                            print(f"  Coordinates: ({selected['lat']:.4f}, {selected['lon']:.4f})")
            else:
                if not args.progress_bar:
                    print(f"  No match ({confidence})")
                not_found += 1

            time.sleep(args.delay)

        print(f"\n{'='*50}")
        print(f"Wikidata linking complete:")
        print(f"  Linked: {linked}")
        print(f"  Geocoded: {geocoded}")
        print(f"  Not found: {not_found}")
        print(f"  Total processed: {linked + not_found}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
