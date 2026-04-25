#!/usr/bin/env python

"""Migrate the current Pausanias SQLite database into PostgreSQL."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from pausanias_db import connect, initialize_schema


COPY_TABLES: list[tuple[str, list[str], Callable[[sqlite3.Row], tuple[Any, ...]] | None]] = [
    (
        "passages",
        ["id", "passage", "references_mythic_era", "expresses_scepticism"],
        lambda row: (
            row["id"],
            row["passage"],
            bool_or_none(row["references_mythic_era"]),
            bool_or_none(row["expresses_scepticism"]),
        ),
    ),
    ("content_queries", ["id", "passage_id", "timestamp", "model", "input_tokens", "output_tokens"], None),
    (
        "noun_extraction_status",
        ["passage_id", "timestamp", "model", "input_tokens", "output_tokens", "is_processed"],
        lambda row: (
            row["passage_id"],
            row["timestamp"],
            row["model"],
            row["input_tokens"],
            row["output_tokens"],
            bool_or_none(row["is_processed"]),
        ),
    ),
    ("translations", ["passage_id", "greek_text", "english_translation", "timestamp", "model", "input_tokens", "output_tokens"], None),
    ("proper_nouns", ["id", "passage_id", "exact_form", "reference_form", "english_transcription", "entity_type"], None),
    (
        "noun_centrality",
        [
            "id",
            "reference_form",
            "entity_type",
            "english_transcription",
            "component_id",
            "degree_centrality",
            "betweenness_centrality",
            "eigenvector_centrality",
            "pagerank",
            "clustering_coefficient",
            "timestamp",
        ],
        None,
    ),
    ("manual_stopwords", ["id", "word"], None),
    ("manual_skepticism_stopwords", ["id", "word"], None),
    (
        "greek_sentences",
        [
            "passage_id",
            "sentence_number",
            "sentence",
            "english_sentence",
            "references_mythic_era",
            "expresses_scepticism",
        ],
        lambda row: (
            row["passage_id"],
            row["sentence_number"],
            row["sentence"],
            row["english_sentence"],
            bool_or_none(row["references_mythic_era"]),
            bool_or_none(row["expresses_scepticism"]),
        ),
    ),
    (
        "phrase_translations",
        ["phrase", "english_translation", "is_proper_noun", "timestamp", "model", "input_tokens", "output_tokens"],
        lambda row: (
            row["phrase"],
            row["english_translation"],
            bool_or_none(row["is_proper_noun"]),
            row["timestamp"],
            row["model"],
            row["input_tokens"],
            row["output_tokens"],
        ),
    ),
    ("passage_summaries", ["passage_id", "summary", "model", "timestamp", "input_tokens", "output_tokens"], None),
    (
        "mythicness_predictors",
        ["id", "phrase", "coefficient", "is_mythic", "mythic_count", "non_mythic_count", "p_value", "q_value", "timestamp"],
        None,
    ),
    (
        "skepticism_predictors",
        ["id", "phrase", "coefficient", "is_skeptical", "skeptical_count", "non_skeptical_count", "p_value", "q_value", "timestamp"],
        None,
    ),
    (
        "simplified_mythicness_predictors",
        [
            "id",
            "phrase",
            "coefficient",
            "idf",
            "point_value",
            "is_mythic",
            "mythic_count",
            "non_mythic_count",
            "p_value",
            "q_value",
            "timestamp",
        ],
        None,
    ),
    (
        "simplified_skepticism_predictors",
        [
            "id",
            "phrase",
            "coefficient",
            "idf",
            "point_value",
            "is_skeptical",
            "skeptical_count",
            "non_skeptical_count",
            "p_value",
            "q_value",
            "timestamp",
        ],
        None,
    ),
    (
        "passage_mythicness_metrics",
        [
            "id",
            "accuracy",
            "precision_0",
            "recall_0",
            "f1_0",
            "support_0",
            "precision_1",
            "recall_1",
            "f1_1",
            "support_1",
            "actual_0_pred_0",
            "actual_0_pred_1",
            "actual_1_pred_0",
            "actual_1_pred_1",
            "timestamp",
        ],
        None,
    ),
    (
        "passage_skepticism_metrics",
        [
            "id",
            "accuracy",
            "precision_0",
            "recall_0",
            "f1_0",
            "support_0",
            "precision_1",
            "recall_1",
            "f1_1",
            "support_1",
            "actual_0_pred_0",
            "actual_0_pred_1",
            "actual_1_pred_0",
            "actual_1_pred_1",
            "timestamp",
        ],
        None,
    ),
    (
        "simplified_mythicness_metrics",
        [
            "id",
            "accuracy",
            "baseline_accuracy",
            "baseline_label",
            "intercept",
            "threshold",
            "selected_feature_count",
            "precision_0",
            "recall_0",
            "f1_0",
            "support_0",
            "precision_1",
            "recall_1",
            "f1_1",
            "support_1",
            "actual_0_pred_0",
            "actual_0_pred_1",
            "actual_1_pred_0",
            "actual_1_pred_1",
            "baseline_actual_0_pred_0",
            "baseline_actual_0_pred_1",
            "baseline_actual_1_pred_0",
            "baseline_actual_1_pred_1",
            "timestamp",
        ],
        None,
    ),
    (
        "simplified_skepticism_metrics",
        [
            "id",
            "accuracy",
            "baseline_accuracy",
            "baseline_label",
            "intercept",
            "threshold",
            "selected_feature_count",
            "precision_0",
            "recall_0",
            "f1_0",
            "support_0",
            "precision_1",
            "recall_1",
            "f1_1",
            "support_1",
            "actual_0_pred_0",
            "actual_0_pred_1",
            "actual_1_pred_0",
            "actual_1_pred_1",
            "baseline_actual_0_pred_0",
            "baseline_actual_0_pred_1",
            "baseline_actual_1_pred_0",
            "baseline_actual_1_pred_1",
            "timestamp",
        ],
        None,
    ),
    (
        "sentence_mythicness_predictors",
        ["id", "phrase", "coefficient", "is_mythic", "mythic_count", "non_mythic_count", "p_value", "q_value", "timestamp"],
        None,
    ),
    (
        "sentence_skepticism_predictors",
        ["id", "phrase", "coefficient", "is_skeptical", "skeptical_count", "non_skeptical_count", "p_value", "q_value", "timestamp"],
        None,
    ),
    (
        "sentence_simplified_mythicness_predictors",
        [
            "id",
            "phrase",
            "coefficient",
            "idf",
            "point_value",
            "is_mythic",
            "mythic_count",
            "non_mythic_count",
            "p_value",
            "q_value",
            "timestamp",
        ],
        None,
    ),
    (
        "sentence_simplified_skepticism_predictors",
        [
            "id",
            "phrase",
            "coefficient",
            "idf",
            "point_value",
            "is_skeptical",
            "skeptical_count",
            "non_skeptical_count",
            "p_value",
            "q_value",
            "timestamp",
        ],
        None,
    ),
    (
        "sentence_mythicness_metrics",
        [
            "id",
            "accuracy",
            "precision_0",
            "recall_0",
            "f1_0",
            "support_0",
            "precision_1",
            "recall_1",
            "f1_1",
            "support_1",
            "actual_0_pred_0",
            "actual_0_pred_1",
            "actual_1_pred_0",
            "actual_1_pred_1",
            "timestamp",
        ],
        None,
    ),
    (
        "sentence_skepticism_metrics",
        [
            "id",
            "accuracy",
            "precision_0",
            "recall_0",
            "f1_0",
            "support_0",
            "precision_1",
            "recall_1",
            "f1_1",
            "support_1",
            "actual_0_pred_0",
            "actual_0_pred_1",
            "actual_1_pred_0",
            "actual_1_pred_1",
            "timestamp",
        ],
        None,
    ),
    (
        "sentence_simplified_mythicness_metrics",
        [
            "id",
            "accuracy",
            "baseline_accuracy",
            "baseline_label",
            "intercept",
            "threshold",
            "selected_feature_count",
            "precision_0",
            "recall_0",
            "f1_0",
            "support_0",
            "precision_1",
            "recall_1",
            "f1_1",
            "support_1",
            "actual_0_pred_0",
            "actual_0_pred_1",
            "actual_1_pred_0",
            "actual_1_pred_1",
            "baseline_actual_0_pred_0",
            "baseline_actual_0_pred_1",
            "baseline_actual_1_pred_0",
            "baseline_actual_1_pred_1",
            "timestamp",
        ],
        None,
    ),
    (
        "sentence_simplified_skepticism_metrics",
        [
            "id",
            "accuracy",
            "baseline_accuracy",
            "baseline_label",
            "intercept",
            "threshold",
            "selected_feature_count",
            "precision_0",
            "recall_0",
            "f1_0",
            "support_0",
            "precision_1",
            "recall_1",
            "f1_1",
            "support_1",
            "actual_0_pred_0",
            "actual_0_pred_1",
            "actual_1_pred_0",
            "actual_1_pred_1",
            "baseline_actual_0_pred_0",
            "baseline_actual_0_pred_1",
            "baseline_actual_1_pred_0",
            "baseline_actual_1_pred_1",
            "timestamp",
        ],
        None,
    ),
]

IDENTITY_TABLES = [
    "content_queries",
    "proper_nouns",
    "noun_centrality",
    "manual_stopwords",
    "manual_skepticism_stopwords",
    "wikidata_links",
    "mythicness_predictors",
    "skepticism_predictors",
    "simplified_mythicness_predictors",
    "simplified_skepticism_predictors",
    "sentence_mythicness_predictors",
    "sentence_skepticism_predictors",
    "sentence_simplified_mythicness_predictors",
    "sentence_simplified_skepticism_predictors",
]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sqlite_path", type=Path, help="Source SQLite database")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Target PostgreSQL connection string. Defaults like other scripts.",
    )
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="Do not clear existing PostgreSQL data before loading.",
    )
    return parser.parse_args()


def bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def sqlite_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def sqlite_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {row["name"] for row in conn.execute(f'PRAGMA table_info("{table_name}")')}


def row_to_tuple(row: sqlite3.Row, columns: list[str]) -> tuple[Any, ...]:
    return tuple(row[column] for column in columns)


def copy_table(
    source: sqlite3.Connection,
    target,
    table_name: str,
    columns: list[str],
    transform: Callable[[sqlite3.Row], tuple[Any, ...]] | None = None,
) -> int:
    if not sqlite_table_exists(source, table_name):
        return 0

    available_columns = sqlite_columns(source, table_name)
    if not set(columns).issubset(available_columns):
        missing = sorted(set(columns) - available_columns)
        raise RuntimeError(f"{table_name} is missing expected columns: {missing}")

    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = f'INSERT INTO "{table_name}" ({quoted_columns}) VALUES ({placeholders})'
    rows = source.execute(f'SELECT {quoted_columns} FROM "{table_name}"').fetchall()
    values = [transform(row) if transform else row_to_tuple(row, columns) for row in rows]

    with target.cursor() as cursor:
        cursor.executemany(insert_sql, values)
    return len(values)


def migrate_wikidata_entities(source: sqlite3.Connection, target) -> int:
    if not sqlite_table_exists(source, "wikidata_links"):
        return 0

    now = datetime.now().isoformat()
    link_rows = source.execute(
        """
        SELECT wikidata_qid,
               MIN(english_transcription) AS label,
               MIN(entity_type) AS entity_type,
               MIN(linked_at) AS updated_at
        FROM wikidata_links
        WHERE wikidata_qid IS NOT NULL
        GROUP BY wikidata_qid
        """
    ).fetchall()

    with target.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO wikidata_entities
            (wikidata_qid, label, description, entity_type, latitude, longitude, pleiades_id, fetched_at, updated_at)
            VALUES (%s, %s, NULL, %s, NULL, NULL, NULL, NULL, %s)
            ON CONFLICT (wikidata_qid) DO UPDATE SET
                label = COALESCE(wikidata_entities.label, EXCLUDED.label),
                entity_type = COALESCE(wikidata_entities.entity_type, EXCLUDED.entity_type),
                updated_at = EXCLUDED.updated_at
            """,
            [
                (
                    row["wikidata_qid"],
                    row["label"],
                    row["entity_type"],
                    row["updated_at"] or now,
                )
                for row in link_rows
            ],
        )

    if sqlite_table_exists(source, "place_coordinates"):
        place_rows = source.execute(
            """
            SELECT wikidata_qid, english_transcription, latitude, longitude, pleiades_id, fetched_at
            FROM place_coordinates
            """
        ).fetchall()
        with target.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO wikidata_entities
                (wikidata_qid, label, description, entity_type, latitude, longitude, pleiades_id, fetched_at, updated_at)
                VALUES (%s, %s, NULL, 'place', %s, %s, %s, %s, %s)
                ON CONFLICT (wikidata_qid) DO UPDATE SET
                    label = COALESCE(EXCLUDED.label, wikidata_entities.label),
                    entity_type = COALESCE(wikidata_entities.entity_type, 'place'),
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    pleiades_id = EXCLUDED.pleiades_id,
                    fetched_at = EXCLUDED.fetched_at,
                    updated_at = EXCLUDED.updated_at
                """,
                [
                    (
                        row["wikidata_qid"],
                        row["english_transcription"],
                        row["latitude"],
                        row["longitude"],
                        row["pleiades_id"],
                        row["fetched_at"],
                        row["fetched_at"] or now,
                    )
                    for row in place_rows
                ],
            )

    with target.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM wikidata_entities")
        return cursor.fetchone()[0]


def copy_wikidata_links(source: sqlite3.Connection, target) -> int:
    if not sqlite_table_exists(source, "wikidata_links"):
        return 0

    columns = [
        "id",
        "reference_form",
        "entity_type",
        "english_transcription",
        "wikidata_qid",
        "confidence",
        "linked_at",
    ]
    return copy_table(source, target, "wikidata_links", columns)


def truncate_target(target) -> None:
    table_names = [table for table, _, _ in COPY_TABLES] + ["wikidata_entities", "wikidata_links"]
    quoted_tables = ", ".join(f'"{table}"' for table in table_names)
    target.execute(f"TRUNCATE {quoted_tables} RESTART IDENTITY CASCADE")
    target.commit()


def reset_identities(target) -> None:
    with target.cursor() as cursor:
        for table in IDENTITY_TABLES:
            cursor.execute(
                """
                SELECT setval(
                    pg_get_serial_sequence(%s, 'id'),
                    COALESCE((SELECT MAX(id) FROM """ + f'"{table}"' + """), 1),
                    COALESCE((SELECT MAX(id) FROM """ + f'"{table}"' + """), 0) > 0
                )
                """,
                (table,),
            )
    target.commit()


def main() -> None:
    args = parse_arguments()
    if not args.sqlite_path.exists():
        raise FileNotFoundError(args.sqlite_path)

    source = sqlite3.connect(args.sqlite_path)
    source.row_factory = sqlite3.Row
    target = connect(args.database_url)

    try:
        initialize_schema(target)
        if not args.no_truncate:
            truncate_target(target)

        copied: dict[str, int] = {}
        for table_name, columns, transform in COPY_TABLES:
            if table_name == "wikidata_links":
                continue
            copied[table_name] = copy_table(source, target, table_name, columns, transform)

        copied["wikidata_entities"] = migrate_wikidata_entities(source, target)
        copied["wikidata_links"] = copy_wikidata_links(source, target)

        reset_identities(target)
        target.commit()

        for table_name in sorted(copied):
            print(f"{table_name}\t{copied[table_name]}")
    finally:
        source.close()
        target.close()


if __name__ == "__main__":
    main()
