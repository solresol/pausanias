"""Export a local research preview without modifying the source database."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

from manto_place_connectedness_features import canonical_action
from manto_place_geography_features import haversine_km
from pausanias_db import connect

IDENTITY_ACTIONS = {
    "foundation", "eponym_or_etymology", "rule", "cult_site",
    "cult_establishment", "burial_at", "games", "games_establishment",
    "divine_patronage", "post_mortem_presence",
}
LATEST_PUBLIC = {
    "record_id": 23079055,
    "date": "2026-10-01",
    "url": "https://zenodo.org/records/23079055",
    "verified_on": "2026-11-09",
}


def clean_label(label):
    return re.sub(r"^[^\w]+", "", label or "", flags=re.UNICODE).strip()


def weighted_jaccard(left, right, rarity):
    """Return None when either repertoire is unobserved, never false uniqueness."""
    left, right = set(left), set(right)
    if not left or not right:
        return None
    return sum(rarity.get(x, 1.0) for x in left & right) / sum(
        rarity.get(x, 1.0) for x in left | right
    )


def containment(left, right, rarity):
    left, right = set(left), set(right)
    if not left or not right:
        return None
    return sum(rarity.get(x, 1.0) for x in left & right) / sum(
        rarity.get(x, 1.0) for x in left
    )


def figure_profiles(rows, places):
    profiles = defaultdict(set)
    figures = {}
    actions = defaultdict(lambda: defaultdict(set))
    for row in rows:
        action = canonical_action(row["relation_type"])
        if action not in IDENTITY_ACTIONS:
            continue
        source, target = str(row["source_manto_id"]), str(row["target_manto_id"])
        if source in places and (row["target_name"] or "").startswith("👤"):
            place, figure, name = source, target, row["target_name"]
        elif target in places and (row["source_name"] or "").startswith("👤"):
            place, figure, name = target, source, row["source_name"]
        else:
            continue
        profiles[place].add(figure)
        figures[figure] = clean_label(name)
        actions[place][action].add(figure)
    return profiles, figures, actions


def build_comparisons(places, profiles):
    frequencies = defaultdict(int)
    for profile in profiles.values():
        for figure in profile:
            frequencies[figure] += 1
    rarity = {f: 1 + math.log((len(profiles) + 1) / (n + 1)) for f, n in frequencies.items()}
    mapped = [p for p in places.values() if p["lat"] is not None and p["lon"] is not None]
    pairs = []
    for index, left in enumerate(mapped):
        for right in mapped[index + 1:]:
            if abs(left["lat"] - right["lat"]) > 1:
                continue
            distance = haversine_km(left["lat"], left["lon"], right["lat"], right["lon"])
            if distance > 100:
                continue
            a, b = profiles.get(left["id"], set()), profiles.get(right["id"], set())
            similarity = weighted_jaccard(a, b, rarity)
            pairs.append({
                "a": left["id"], "b": right["id"], "km": round(distance, 3),
                "similarity": None if similarity is None else round(similarity, 6),
                "a_in_b": containment(a, b, rarity), "b_in_a": containment(b, a, rarity),
                "shared": sorted(a & b),
            })
    return pairs, rarity


def prepare_payload(release, places_rows, edge_rows, claims_rows, links_rows, metrics):
    places = {}
    for row in places_rows:
        place_id = str(row["object_id"])
        places[place_id] = {
            "id": place_id, "name": clean_label(row["name"]),
            "parent": clean_label(row.get("parent_label")),
            "lat": float(row["lat"]) if row["lat"] is not None else None,
            "lon": float(row["lon"]) if row["lon"] is not None else None,
            "pleiades_id": row.get("pleiades_id") or None,
        }
    profiles, figures, actions = figure_profiles(edge_rows, places)
    pairs, rarity = build_comparisons(places, profiles)
    for key, place in places.items():
        place["figures"] = sorted(profiles.get(key, set()))
        place["actions"] = {a: sorted(ids) for a, ids in actions.get(key, {}).items()}
    links = defaultdict(set)
    for row in links_rows:
        for name in (row["english_transcription"], row["reference_form"]):
            if name:
                links[name.casefold()].add(str(row["manto_id"]))
    claims = []
    for row in claims_rows:
        claim = dict(row)
        claim["id"] = str(claim["id"])
        claim["candidate_manto_ids"] = sorted(links.get(claim["canonical_place_name"].casefold(), set()))
        claim["review_status"] = "automated_unreviewed"
        # No person-directed or operational identifiers are exported.
        claims.append(claim)
    return {
        "schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "release": release, "latest_public": LATEST_PUBLIC,
        "provenance": {
            "mode": "local research preview; not an adjudicated settlement dataset",
            "source_read_only": True,
            "edge_filter": "existing importer is_pre_pausanias=true; date provenance not independently audited",
            "temporal_cutoff_ce": 180,
            "neighbours": "great-circle distances from representative Pleiades coordinates; all geographic entity types",
            "feature_scope": "binary figure associations for selected identity-related relation types; not independent witness counts",
            "claim_scope": "all existing passage-level candidate claims, including monuments and non-contemporary statements",
            "endpoint_warning": "automated evidence claims, not verified survival outcomes; do not infer abandonment from absence",
            "no_prediction": "No new model or GNN has been trained for this preview.",
        },
        "places": list(places.values()), "figures": figures, "rarity": rarity,
        "pairs": pairs, "claims": claims, "historical_metrics": metrics,
    }


def read_rows(conn, query, params=None):
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        columns = [column.name for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def export_database(database_url, release_id=None):
    with connect(database_url) as conn:
        conn.read_only = True
        conn.execute("SET LOCAL statement_timeout = '30s'")
        if not conn.execute("SHOW transaction_read_only").fetchone()[0] == "on":
            raise RuntimeError("Refusing export without read-only transaction")
        if release_id is None:
            release_id = conn.execute("SELECT record_id FROM manto_releases WHERE import_status='imported' ORDER BY record_id DESC LIMIT 1").fetchone()[0]
        release_rows = read_rows(conn, "SELECT record_id, doi, version, file_key, file_checksum, license_id, imported_at FROM manto_releases WHERE record_id=%s AND import_status='imported'", (release_id,))
        if not release_rows:
            raise ValueError("Requested release is not fully imported")
        places = read_rows(conn, """SELECT d.object_id,d.name,d.pleiades_id,
            d.somewhere_in_or_near_label AS parent_label,
            p.representative_latitude AS lat,p.representative_longitude AS lon
            FROM manto_entity_details d LEFT JOIN pleiades_places p ON p.pleiades_id=d.pleiades_id
            WHERE d.release_record_id=%s AND d.name LIKE '🌍%%'""", (release_id,))
        edges = read_rows(conn, """SELECT e.source_manto_id,e.target_manto_id,e.relation_type,
            s.name AS source_name,t.name AS target_name
            FROM manto_edges e
            JOIN manto_entity_details s ON s.release_record_id=e.release_record_id AND s.object_id=e.source_manto_id
            JOIN manto_entity_details t ON t.release_record_id=e.release_record_id AND t.object_id=e.target_manto_id
            WHERE e.release_record_id=%s AND e.is_pre_pausanias
            AND ((s.name LIKE '🌍%%' AND t.name LIKE '👤%%') OR (s.name LIKE '👤%%' AND t.name LIKE '🌍%%'))""", (release_id,))
        claims = read_rows(conn, """SELECT m.id,m.passage_id,m.canonical_place_name,m.exact_place_text,
            m.place_status,m.temporal_scope,m.evidence_quote,m.confidence,m.rationale,
            p.passage AS greek_text,t.english_translation
            FROM passage_place_state_mentions m JOIN passages p ON p.id=m.passage_id
            LEFT JOIN translations t ON t.passage_id=m.passage_id
            ORDER BY string_to_array(m.passage_id,'.')::int[],m.id""")
        links = read_rows(conn, "SELECT reference_form,english_transcription,manto_id FROM manto_place_links WHERE release_record_id=%s", (release_id,))
        metrics = read_rows(conn, """SELECT release_record_id,feature_set_version,sample_count,positive_count,
            negative_count,balanced_accuracy,completed_at,notes FROM place_survival_model_runs
            WHERE sample_count=255 AND completed_at LIKE '2026-07-27%%'
            ORDER BY completed_at""")
        return prepare_payload(release_rows[0], places, edges, claims, links, metrics)


def write_site(payload, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    assets = Path(__file__).with_name("static")
    for name in ("index.html", "style.css", "app.js"):
        shutil.copyfile(assets / name, output / name)
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    (output / "data.json").write_text(data, encoding="utf-8")
    # External JS permits a local file preview and a strict no-inline-script CSP.
    safe = data.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    (output / "data.js").write_text("window.MANTO_DATA=" + safe + ";\n", encoding="utf-8")
    manifest = {"schema_version": 1, "release_record_id": payload["release"]["record_id"], "files": {}}
    for name in ("index.html", "style.css", "app.js", "data.json", "data.js"):
        manifest["files"][name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True, help="Explicit authorized source DSN; all queries are read-only")
    parser.add_argument("--release-record-id", type=int)
    parser.add_argument("--output-dir", default="tmp/manto-atlas-preview")
    args = parser.parse_args()
    payload = export_database(args.database_url, args.release_record_id)
    write_site(payload, args.output_dir)
    print(json.dumps({"output": args.output_dir, "release": payload["release"]["record_id"], "places": len(payload["places"]), "claims": len(payload["claims"]), "pairs": len(payload["pairs"])}))


if __name__ == "__main__":
    main()
