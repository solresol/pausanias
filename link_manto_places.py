#!/usr/bin/env python
"""Link Pausanias place proper nouns to imported MANTO entities."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone

from pausanias_db import add_database_argument, connect, initialize_schema


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


# Ordered substitutions mapping Latin-style romanizations onto a canonical
# Greek-style key: Amyclae/Amyklai, Aegae/Aigai, Rhium/Rion all collide.
TRANSLITERATION_SUBSTITUTIONS = (
    ("ae", "ai"),
    ("oe", "oi"),
    ("rh", "r"),
    ("c", "k"),
)
TRANSLITERATION_ENDINGS = (
    ("um", "on"),
    ("us", "os"),
)


def transliteration_key(value: str | None) -> str:
    key = normalize_name(value)
    if not key:
        return ""
    for source, target in TRANSLITERATION_SUBSTITUTIONS:
        key = key.replace(source, target)
    for source, target in TRANSLITERATION_ENDINGS:
        if key.endswith(source):
            key = key[: -len(source)] + target
            break
    return key


def transliteration_keys(variants: set[str]) -> set[str]:
    """Canonical transliteration keys for normalized name variants.

    Includes a looser final -ai/-a merge so Latin plurals like Alipherae meet
    Greek singulars like Aliphera.
    """
    keys: set[str] = set()
    for variant in variants:
        key = transliteration_key(variant)
        if not key:
            continue
        keys.add(key)
        if key.endswith("ai"):
            keys.add(key[:-1])
    return keys


GENERIC_TRAILING_WORDS = {
    "acropolis",
    "agora",
    "altar",
    "bedchamber",
    "cave",
    "citadel",
    "city",
    "desert",
    "gate",
    "gates",
    "grove",
    "harbor",
    "harbour",
    "hill",
    "house",
    "island",
    "marketplace",
    "mount",
    "mountain",
    "plain",
    "river",
    "sanctuary",
    "spring",
    "temple",
    "town",
    "village",
    "wall",
    "walls",
}
GENERIC_NORMALIZED_NAMES = {normalize_name(word) for word in GENERIC_TRAILING_WORDS}

DESCRIPTIVE_PREFIXES = (
    "ancient ",
    "old ",
    "former ",
    "the ancient ",
    "the old ",
    "the former ",
    "the ",
)


def add_normalized_variant(variants: set[str], value: str | None) -> None:
    normalized = normalize_name(value)
    if normalized and normalized not in GENERIC_NORMALIZED_NAMES:
        variants.add(normalized)


def name_variants(
    value: str | None,
    *,
    include_parenthetical_content: bool = False,
    include_location_container: bool = True,
    include_generic_head: bool = True,
) -> set[str]:
    if not value:
        return set()
    text = re.sub(r"^[^\w]+", "", value).strip()
    variants: set[str] = set()
    add_normalized_variant(variants, text)
    without_parenthetical = re.sub(r"\s*\([^)]*\)", "", text).strip()
    add_normalized_variant(variants, without_parenthetical)

    for parenthetical in re.findall(r"\(([^)]*)\)", text):
        raw_parenthetical = parenthetical.strip()
        is_alias = re.match(r"^(?:alt\.?|aka|also called)\s+", raw_parenthetical, flags=re.I)
        if include_parenthetical_content or is_alias:
            cleaned = re.sub(r"^(?:alt\.?|aka|also called)\s+", "", raw_parenthetical, flags=re.I)
            add_normalized_variant(variants, cleaned)

    for base in {text, without_parenthetical}:
        lowered = base.lower()
        for prefix in DESCRIPTIVE_PREFIXES:
            if lowered.startswith(prefix):
                add_normalized_variant(variants, base[len(prefix):])
        if include_location_container and " at " in lowered:
            add_normalized_variant(variants, re.split(r"\s+at\s+", base, maxsplit=1, flags=re.I)[1])
        if include_location_container and " near " in lowered:
            add_normalized_variant(variants, re.split(r"\s+near\s+", base, maxsplit=1, flags=re.I)[1])
        if include_location_container and " of " in lowered:
            before, after = re.split(r"\s+of\s+", base, maxsplit=1, flags=re.I)
            if before.split() and before.split()[-1].lower() in GENERIC_TRAILING_WORDS:
                add_normalized_variant(variants, after)
        words = base.split()
        while include_generic_head and len(words) > 1 and words[-1].lower() in GENERIC_TRAILING_WORDS:
            words = words[:-1]
            add_normalized_variant(variants, " ".join(words))
    return variants


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_database_argument(parser)
    parser.add_argument("--release-record-id", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def latest_release_id(conn) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT record_id
            FROM manto_releases
            WHERE import_status IN ('imported', 'partial_imported')
            ORDER BY COALESCE(imported_at, updated_at) DESC, record_id DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
    if not row:
        raise RuntimeError("No imported MANTO release found.")
    return int(row[0])


def load_places(conn) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT pn.reference_form,
                   pn.entity_type,
                   MIN(pn.english_transcription) AS english_transcription,
                   wl.wikidata_qid,
                   we.pleiades_id
            FROM proper_nouns pn
            LEFT JOIN wikidata_links wl
              ON wl.reference_form = pn.reference_form
             AND wl.entity_type = pn.entity_type
            LEFT JOIN wikidata_entities we
              ON we.wikidata_qid = wl.wikidata_qid
            WHERE pn.entity_type = 'place'
            GROUP BY pn.reference_form, pn.entity_type, wl.wikidata_qid, we.pleiades_id
            ORDER BY pn.reference_form
            """
        )
        rows = cursor.fetchall()
    return [
        {
            "reference_form": row[0],
            "entity_type": row[1],
            "english_transcription": row[2],
            "wikidata_qid": row[3],
            "pleiades_id": row[4],
        }
        for row in rows
    ]


def load_manto_entities(conn, release_id: int) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT object_id, name, pleiades_id
            FROM manto_entity_details
            WHERE release_record_id = %s
              AND name LIKE '🌍%%'
            """,
            (release_id,),
        )
        rows = cursor.fetchall()
    entities = []
    for object_id, label, pleiades_id in rows:
        norm_variants = name_variants(
            label,
            include_location_container=False,
            include_generic_head=False,
        )
        entities.append(
            {
                "manto_id": object_id,
                "label": label or "",
                "entity_kind": "place",
                "pleiades_id": pleiades_id or "",
                "norm_label": normalize_name(label),
                "norm_variants": norm_variants,
                "translit_variants": transliteration_keys(norm_variants),
            }
        )
    return entities


def candidate_links(place: dict, entities: list[dict]) -> list[dict]:
    candidates = []
    place_names = (
        name_variants(place.get("reference_form"), include_parenthetical_content=True)
        | name_variants(place.get("english_transcription"), include_parenthetical_content=True)
    )
    place_translit = transliteration_keys(place_names)
    pleiades_id = place.get("pleiades_id") or ""
    for entity in entities:
        if pleiades_id and entity["pleiades_id"] == pleiades_id:
            candidates.append(
                {
                    **entity,
                    "match_method": "pleiades",
                    "confidence": "high",
                    "rationale": f"Pleiades ID {pleiades_id} matches.",
                }
            )
            continue
        if place_names & entity["norm_variants"]:
            confidence = "high" if entity["norm_label"] in place_names else "medium"
            candidates.append(
                {
                    **entity,
                    "match_method": "exact_normalized_name",
                    "confidence": confidence,
                    "rationale": "Normalized Pausanias place name matches MANTO label.",
                }
            )
            continue
        if place_translit & entity.get("translit_variants", set()):
            candidates.append(
                {
                    **entity,
                    "match_method": "transliteration",
                    "confidence": "medium",
                    "rationale": (
                        "Latin/Greek transliteration key matches MANTO label "
                        "(e.g. -ae/-ai, c/k)."
                    ),
                }
            )
    # Prefer high-confidence matches but keep multiple rows if names are ambiguous.
    candidates.sort(key=lambda item: (item["confidence"] != "high", item["match_method"], item["manto_id"]))
    return candidates


def load_curated_links(conn) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT place_name, manto_id, manto_label, source, rationale,
                   reviewed, rejected
            FROM curated_place_links
            """
        )
        rows = cursor.fetchall()
    return [
        {
            "place_name": row[0],
            "manto_id": row[1],
            "manto_label": row[2] or "",
            "source": row[3],
            "rationale": row[4] or "",
            "reviewed": bool(row[5]),
            "rejected": bool(row[6]),
        }
        for row in rows
    ]


def curated_link_rows(
    curated: list[dict],
    entities: list[dict],
    *,
    release_id: int,
    existing_keys: set[tuple[str, str]],
    timestamp: str,
) -> list[tuple]:
    """Rows for curated links the deterministic pass did not already produce.

    Rejected curated rows are skipped (an empty manto_id records an LLM
    no-match decision so the name is not re-queried).
    """
    entity_labels = {entity["manto_id"]: entity["label"] for entity in entities}
    rows: list[tuple] = []
    for link in curated:
        if link["rejected"] or not link["manto_id"]:
            continue
        key = (link["place_name"], link["manto_id"])
        if key in existing_keys:
            continue
        if link["manto_id"] not in entity_labels:
            print(
                f"Curated link {link['place_name']!r} -> {link['manto_id']} "
                "has no MANTO entity in this release; skipping.",
                flush=True,
            )
            continue
        confidence = "high" if link["source"] == "manual" or link["reviewed"] else "medium"
        rows.append(
            (
                release_id,
                link["place_name"],
                "place",
                link["place_name"],
                None,
                None,
                link["manto_id"],
                entity_labels[link["manto_id"]] or link["manto_label"],
                f"curated-{link['source']}",
                confidence,
                link["rationale"] or "Curated link.",
                timestamp,
                timestamp,
            )
        )
    return rows


def save_links(conn, release_id: int, links: list[tuple]) -> None:
    if not links:
        return
    with conn.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM manto_place_links
            WHERE release_record_id = %s
              AND reviewed = FALSE
            """,
            (release_id,),
        )
        cursor.executemany(
            """
            INSERT INTO manto_place_links (
                release_record_id, reference_form, entity_type, english_transcription,
                wikidata_qid, pleiades_id, manto_id, manto_label, match_method,
                confidence, rationale, reviewed, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s)
            ON CONFLICT (release_record_id, reference_form, entity_type, manto_id) DO UPDATE
            SET english_transcription = EXCLUDED.english_transcription,
                wikidata_qid = EXCLUDED.wikidata_qid,
                pleiades_id = EXCLUDED.pleiades_id,
                manto_label = EXCLUDED.manto_label,
                match_method = EXCLUDED.match_method,
                confidence = EXCLUDED.confidence,
                rationale = EXCLUDED.rationale,
                updated_at = EXCLUDED.updated_at
            """,
            links,
        )
    conn.commit()


def main() -> None:
    args = parse_arguments()
    timestamp = now_iso()
    with connect(args.database_url) as conn:
        initialize_schema(conn)
        release_id = args.release_record_id or latest_release_id(conn)
        places = load_places(conn)
        if args.limit:
            places = places[: args.limit]
        entities = load_manto_entities(conn, release_id)
        rows = []
        existing_keys: set[tuple[str, str]] = set()
        for place in places:
            for candidate in candidate_links(place, entities):
                existing_keys.add((place["reference_form"], candidate["manto_id"]))
                rows.append(
                    (
                        release_id,
                        place["reference_form"],
                        place["entity_type"],
                        place["english_transcription"],
                        place["wikidata_qid"],
                        place["pleiades_id"],
                        candidate["manto_id"],
                        candidate["label"],
                        candidate["match_method"],
                        candidate["confidence"],
                        candidate["rationale"],
                        timestamp,
                        timestamp,
                    )
                )
        curated = load_curated_links(conn)
        curated_rows = curated_link_rows(
            curated,
            entities,
            release_id=release_id,
            existing_keys=existing_keys,
            timestamp=timestamp,
        )
        rows.extend(curated_rows)
        if args.dry_run:
            print(
                f"Would upsert {len(rows):,} MANTO place links for release {release_id} "
                f"({len(curated_rows):,} from curated links)."
            )
            return
        save_links(conn, release_id, rows)
    print(
        f"Upserted {len(rows):,} MANTO place links for release {release_id} "
        f"({len(curated_rows):,} from curated links)."
    )


if __name__ == "__main__":
    main()
