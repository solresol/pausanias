#!/usr/bin/env python

"""Import Greta/Rosie manual sentence highlights into PostgreSQL."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

from pausanias_db import connect


DEFAULT_SOURCE_ID = "greta-rosie-book3-rtf-2026-05-28"
DEFAULT_SOURCE_DOCUMENT = "Pausanias book 3.rtf"
DEFAULT_ANNOTATORS = "Greta/Rosie"


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sentence_manual_tags (
    source_id TEXT NOT NULL,
    annotators TEXT NOT NULL,
    source_document TEXT NOT NULL,
    passage_id TEXT NOT NULL,
    sentence_number INTEGER NOT NULL,
    manual_label TEXT NOT NULL,
    manual_bucket TEXT NOT NULL CHECK (
        manual_bucket IN ('mythic', 'historical', 'other', 'mixed_mythic_historical')
    ),
    yellow_mythic BOOLEAN NOT NULL DEFAULT FALSE,
    blue_historical BOOLEAN NOT NULL DEFAULT FALSE,
    green_both BOOLEAN NOT NULL DEFAULT FALSE,
    manual_highlighted_text TEXT NOT NULL DEFAULT '',
    yellow_mythic_letter_count INTEGER NOT NULL DEFAULT 0,
    blue_historical_letter_count INTEGER NOT NULL DEFAULT 0,
    green_both_letter_count INTEGER NOT NULL DEFAULT 0,
    sentence_letter_count INTEGER NOT NULL DEFAULT 0,
    highlighted_letter_fraction DOUBLE PRECISION NOT NULL DEFAULT 0,
    alignment_coverage DOUBLE PRECISION NOT NULL DEFAULT 0,
    alignment_status TEXT NOT NULL DEFAULT '',
    imported_at TEXT NOT NULL,
    PRIMARY KEY (source_id, passage_id, sentence_number),
    FOREIGN KEY (passage_id, sentence_number)
        REFERENCES greek_sentences(passage_id, sentence_number)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sentence_manual_tags_bucket
    ON sentence_manual_tags (source_id, manual_bucket);
"""


UPSERT_SQL = """
INSERT INTO sentence_manual_tags (
    source_id,
    annotators,
    source_document,
    passage_id,
    sentence_number,
    manual_label,
    manual_bucket,
    yellow_mythic,
    blue_historical,
    green_both,
    manual_highlighted_text,
    yellow_mythic_letter_count,
    blue_historical_letter_count,
    green_both_letter_count,
    sentence_letter_count,
    highlighted_letter_fraction,
    alignment_coverage,
    alignment_status,
    imported_at
) VALUES (
    %(source_id)s,
    %(annotators)s,
    %(source_document)s,
    %(passage_id)s,
    %(sentence_number)s,
    %(manual_label)s,
    %(manual_bucket)s,
    %(yellow_mythic)s,
    %(blue_historical)s,
    %(green_both)s,
    %(manual_highlighted_text)s,
    %(yellow_mythic_letter_count)s,
    %(blue_historical_letter_count)s,
    %(green_both_letter_count)s,
    %(sentence_letter_count)s,
    %(highlighted_letter_fraction)s,
    %(alignment_coverage)s,
    %(alignment_status)s,
    %(imported_at)s
)
ON CONFLICT (source_id, passage_id, sentence_number) DO UPDATE SET
    annotators = EXCLUDED.annotators,
    source_document = EXCLUDED.source_document,
    manual_label = EXCLUDED.manual_label,
    manual_bucket = EXCLUDED.manual_bucket,
    yellow_mythic = EXCLUDED.yellow_mythic,
    blue_historical = EXCLUDED.blue_historical,
    green_both = EXCLUDED.green_both,
    manual_highlighted_text = EXCLUDED.manual_highlighted_text,
    yellow_mythic_letter_count = EXCLUDED.yellow_mythic_letter_count,
    blue_historical_letter_count = EXCLUDED.blue_historical_letter_count,
    green_both_letter_count = EXCLUDED.green_both_letter_count,
    sentence_letter_count = EXCLUDED.sentence_letter_count,
    highlighted_letter_fraction = EXCLUDED.highlighted_letter_fraction,
    alignment_coverage = EXCLUDED.alignment_coverage,
    alignment_status = EXCLUDED.alignment_status,
    imported_at = EXCLUDED.imported_at
"""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import manual Greta/Rosie Book 3 sentence labels from CSV."
    )
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--source-id", default=DEFAULT_SOURCE_ID)
    parser.add_argument("--source-document", default=DEFAULT_SOURCE_DOCUMENT)
    parser.add_argument("--annotators", default=DEFAULT_ANNOTATORS)
    return parser.parse_args()


def bool_from_csv(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def int_from_csv(value: str) -> int:
    value = str(value or "").strip()
    return int(value) if value else 0


def float_from_csv(value: str) -> float:
    value = str(value or "").strip()
    return float(value) if value else 0.0


def manual_bucket(label: str) -> str:
    label = label.strip()
    if label == "not highlighted":
        return "other"
    if label in {"mythic", "historical"}:
        return label
    if label in {
        "mythic and historical",
        "both",
        "both (green, plus additional highlighted text)",
    }:
        return "mixed_mythic_historical"
    raise ValueError(f"Unrecognized manual label: {label!r}")


def row_payload(row: dict[str, str], args: argparse.Namespace, imported_at: str) -> dict[str, object]:
    label = row["greta_rosie_manual_identification"]
    return {
        "source_id": args.source_id,
        "annotators": args.annotators,
        "source_document": args.source_document,
        "passage_id": row["passage_id"],
        "sentence_number": int(row["sentence_number"]),
        "manual_label": label,
        "manual_bucket": manual_bucket(label),
        "yellow_mythic": bool_from_csv(row.get("yellow_mythic", "")),
        "blue_historical": bool_from_csv(row.get("blue_historical", "")),
        "green_both": bool_from_csv(row.get("green_both", "")),
        "manual_highlighted_text": row.get("manual_highlighted_text", ""),
        "yellow_mythic_letter_count": int_from_csv(row.get("yellow_mythic_letter_count", "")),
        "blue_historical_letter_count": int_from_csv(row.get("blue_historical_letter_count", "")),
        "green_both_letter_count": int_from_csv(row.get("green_both_letter_count", "")),
        "sentence_letter_count": int_from_csv(row.get("sentence_letter_count_from_rtf_span", "")),
        "highlighted_letter_fraction": float_from_csv(row.get("highlighted_letter_fraction", "")),
        "alignment_coverage": float_from_csv(row.get("alignment_coverage", "")),
        "alignment_status": row.get("alignment_status", ""),
        "imported_at": imported_at,
    }


def main() -> None:
    args = parse_arguments()
    imported_at = datetime.now(timezone.utc).isoformat()
    with args.csv_path.open(encoding="utf-8", newline="") as handle:
        payloads = [row_payload(row, args, imported_at) for row in csv.DictReader(handle)]

    conn = connect(args.database_url)
    try:
        conn.execute(CREATE_TABLE_SQL)
        with conn.cursor() as cursor:
            cursor.executemany(UPSERT_SQL, payloads)
        conn.commit()
    finally:
        conn.close()

    print(
        f"Imported {len(payloads)} manual sentence tags into source_id={args.source_id}"
    )


if __name__ == "__main__":
    main()
