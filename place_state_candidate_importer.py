#!/usr/bin/env python
"""Populate deterministic place-state candidate sentences."""

from __future__ import annotations

import argparse
import hashlib
import re
from datetime import datetime, timezone
from typing import Iterable

from pausanias_db import add_database_argument, connect, initialize_schema


DEFAULT_SOURCE_VERSION = "place-state-candidates-v1"

ENGLISH_PATTERNS = [
    (
        "ruin",
        r"\b(ruin|ruins|ruined|fallen into ruin)\b",
        "does_not_survive",
    ),
    (
        "deserted_uninhabited",
        r"\b(deserted|uninhabited|without inhabitants|not inhabited|no inhabitants)\b",
        "does_not_survive",
    ),
    (
        "no_longer_extant",
        r"\b(no longer (?:exists?|in existence|inhabited)|not [^.]{0,60}survive|has vanished|disappeared)\b",
        "does_not_survive",
    ),
    (
        "settlement_remains",
        r"\b(remains? of (?:the )?(?:city|town|village|settlement|marketplace|wall|walls|houses|acropolis)|city wall still remains|walls? [^.]{0,60}remain|houses? [^.]{0,60}remain)\b",
        "needs_review",
    ),
    (
        "destroyed_place_context",
        r"\b(?:city|town|village|settlement|place|walls?|houses?) [^.;,]{0,80}(?:destroyed|razed|laid waste|burned|burnt)|(?:destroyed|razed|laid waste|burned|burnt) [^.;,]{0,80}(?:city|town|village|settlement|place|walls?|houses?)\b",
        "does_not_survive",
    ),
]

GREEK_PATTERNS = [
    (
        "greek_place_state_marker",
        r"(ἐρείπ|ἐρήμ|ἔρημ|οὐκέτι|λείπ|κατεσκα|ἀφαν|ἠφαν|ἄοικ|ἀοίκ|ἐξῳκ)",
        "needs_review",
    )
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def candidate_key(
    *,
    source_version: str,
    source_type: str,
    passage_id: str,
    sentence_number: int,
    category: str,
    matched_text: str,
) -> str:
    raw = "\t".join(
        [
            source_version,
            source_type,
            passage_id,
            str(sentence_number),
            category,
            matched_text,
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def regex_candidates_for_sentence(
    *,
    source_version: str,
    passage_id: str,
    sentence_number: int,
    greek_sentence: str,
    english_sentence: str,
    created_at: str,
) -> list[dict]:
    rows = []
    for category, pattern, hint in ENGLISH_PATTERNS:
        match = re.search(pattern, english_sentence, re.I)
        if match:
            matched_text = match.group(0)
            rows.append(
                {
                    "candidate_key": candidate_key(
                        source_version=source_version,
                        source_type="regex_english",
                        passage_id=passage_id,
                        sentence_number=sentence_number,
                        category=category,
                        matched_text=matched_text,
                    ),
                    "source_version": source_version,
                    "source_type": "regex_english",
                    "passage_id": passage_id,
                    "sentence_number": sentence_number,
                    "category": category,
                    "matched_text": matched_text,
                    "target_label_hint": hint,
                    "created_at": created_at,
                }
            )
    for category, pattern, hint in GREEK_PATTERNS:
        match = re.search(pattern, greek_sentence)
        if match:
            matched_text = match.group(0)
            rows.append(
                {
                    "candidate_key": candidate_key(
                        source_version=source_version,
                        source_type="regex_greek",
                        passage_id=passage_id,
                        sentence_number=sentence_number,
                        category=category,
                        matched_text=matched_text,
                    ),
                    "source_version": source_version,
                    "source_type": "regex_greek",
                    "passage_id": passage_id,
                    "sentence_number": sentence_number,
                    "category": category,
                    "matched_text": matched_text,
                    "target_label_hint": hint,
                    "created_at": created_at,
                }
            )
    return rows


def recovered_llm_candidate_rows(
    rows: Iterable[dict],
    *,
    source_version: str,
    created_at: str,
) -> list[dict]:
    candidates = []
    for row in rows:
        matched_text = row["evidence_quote"] or row["canonical_place_name"]
        category = row["place_status"]
        candidates.append(
            {
                "candidate_key": candidate_key(
                    source_version=source_version,
                    source_type="recovered_sentence_llm",
                    passage_id=row["passage_id"],
                    sentence_number=int(row["sentence_number"]),
                    category=category,
                    matched_text=matched_text,
                ),
                "source_version": source_version,
                "source_type": "recovered_sentence_llm",
                "passage_id": row["passage_id"],
                "sentence_number": int(row["sentence_number"]),
                "category": category,
                "matched_text": matched_text,
                "target_label_hint": row["target_label"] or "needs_review",
                "created_at": created_at,
            }
        )
    return candidates


def load_sentence_rows(conn) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT passage_id, sentence_number, sentence, english_sentence
            FROM greek_sentences
            ORDER BY string_to_array(passage_id, '.')::int[], sentence_number
            """
        )
        columns = [column.name for column in cursor.description or []]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def load_recovered_place_state_rows(conn) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT m.passage_id,
                   m.sentence_number,
                   m.place_status,
                   m.evidence_quote,
                   m.canonical_place_name,
                   m.target_label
            FROM place_state_mentions m
            JOIN greek_sentences s
              ON s.passage_id = m.passage_id
             AND s.sentence_number = m.sentence_number
            ORDER BY string_to_array(m.passage_id, '.')::int[],
                     m.sentence_number,
                     m.claim_index
            """
        )
        columns = [column.name for column in cursor.description or []]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def insert_candidates(conn, rows: list[dict], *, source_version: str, dry_run: bool) -> None:
    if dry_run:
        return
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM place_state_candidate_sentences WHERE source_version = %s",
            (source_version,),
        )
        if rows:
            cursor.executemany(
                """
                INSERT INTO place_state_candidate_sentences (
                    candidate_key, source_version, source_type, passage_id,
                    sentence_number, category, matched_text, target_label_hint, created_at
                )
                VALUES (
                    %(candidate_key)s, %(source_version)s, %(source_type)s,
                    %(passage_id)s, %(sentence_number)s, %(category)s,
                    %(matched_text)s, %(target_label_hint)s, %(created_at)s
                )
                ON CONFLICT (candidate_key) DO UPDATE
                SET category = EXCLUDED.category,
                    matched_text = EXCLUDED.matched_text,
                    target_label_hint = EXCLUDED.target_label_hint,
                    created_at = EXCLUDED.created_at
                """,
                rows,
            )
    conn.commit()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate regex and recovered-LLM place-state candidate sentences."
    )
    add_database_argument(parser)
    parser.add_argument("--source-version", default=DEFAULT_SOURCE_VERSION)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    created_at = now_iso()
    with connect(args.database_url) as conn:
        initialize_schema(conn)
        candidates = []
        for row in load_sentence_rows(conn):
            candidates.extend(
                regex_candidates_for_sentence(
                    source_version=args.source_version,
                    passage_id=row["passage_id"],
                    sentence_number=int(row["sentence_number"]),
                    greek_sentence=row["sentence"],
                    english_sentence=row["english_sentence"],
                    created_at=created_at,
                )
            )
        candidates.extend(
            recovered_llm_candidate_rows(
                load_recovered_place_state_rows(conn),
                source_version=args.source_version,
                created_at=created_at,
            )
        )
        insert_candidates(
            conn,
            candidates,
            source_version=args.source_version,
            dry_run=args.dry_run,
        )
    source_counts = {}
    for row in candidates:
        source_counts[row["source_type"]] = source_counts.get(row["source_type"], 0) + 1
    print(
        f"{'Would save' if args.dry_run else 'Saved'} {len(candidates)} "
        f"place-state candidate rows for {args.source_version}: "
        + ", ".join(f"{key}={value}" for key, value in sorted(source_counts.items()))
    )


if __name__ == "__main__":
    main()
