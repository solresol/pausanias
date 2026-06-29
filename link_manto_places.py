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


def name_variants(value: str | None) -> set[str]:
    if not value:
        return set()
    text = re.sub(r"^[^\w]+", "", value).strip()
    without_parenthetical = re.sub(r"\s*\([^)]*\)", "", text).strip()
    variants = {normalize_name(text), normalize_name(without_parenthetical)}
    variants.discard("")
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
        entities.append(
            {
                "manto_id": object_id,
                "label": label or "",
                "entity_kind": "place",
                "pleiades_id": pleiades_id or "",
                "norm_label": normalize_name(label),
                "norm_variants": name_variants(label),
            }
        )
    return entities


def candidate_links(place: dict, entities: list[dict]) -> list[dict]:
    candidates = []
    place_names = {
        normalize_name(place.get("reference_form")),
        normalize_name(place.get("english_transcription")),
    }
    place_names.discard("")
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
    # Prefer high-confidence matches but keep multiple rows if names are ambiguous.
    candidates.sort(key=lambda item: (item["confidence"] != "high", item["match_method"], item["manto_id"]))
    return candidates


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
        for place in places:
            for candidate in candidate_links(place, entities):
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
        if args.dry_run:
            print(f"Would upsert {len(rows):,} MANTO place links for release {release_id}.")
            return
        save_links(conn, release_id, rows)
    print(f"Upserted {len(rows):,} MANTO place links for release {release_id}.")


if __name__ == "__main__":
    main()
