#!/usr/bin/env python
"""Train an explainable classifier for Pausanias place survival claims."""

from __future__ import annotations

import argparse
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Iterable

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from link_manto_places import name_variants, transliteration_keys
from pausanias_db import (
    add_database_argument,
    column_exists,
    connect,
    initialize_schema,
    read_sql_query,
)


FEATURE_SET_VERSION = "manto-pausanias-place-network-v3"
CONNECTEDNESS_FEATURE_SET_VERSION = "manto-place-connectedness-v2"
GEOGRAPHY_FEATURE_SET_VERSION = "manto-place-geography-v1"
FAME_FEATURE_SET_VERSION = "manto-pausanias-fame-v1"
LABEL_SOURCE_VERSION = "manto-entity-info-v1"
LLM_LABEL_SOURCE_VERSION = "llm-place-state-v1"
TRAINING_LABEL_SETS = ("manto", "sentence-llm", "passage-llm", "llm", "combined")
BASE_FEATURE_FAMILIES = ("network", "connectedness", "geography", "fame")
FEATURE_FAMILY_ALIASES = {
    "combined": ["network", "connectedness"],
    "all": ["network", "connectedness", "geography", "fame"],
}
IDENTITY_COLUMNS = [
    "reference_form",
    "entity_type",
    "english_transcription",
    "manto_id",
    "manto_label",
]
NETWORK_FEATURE_COLUMNS = [
    "degree",
    "degree_centrality",
    "pagerank",
    "betweenness_centrality",
    "clustering_coefficient",
    "component_size",
    "community_size",
    "high_centrality_neighbor_count",
    "max_neighbor_pagerank",
    "shared_neighbor_high_centrality_score",
    "k_core",
    "hop_distance_to_large_place",
    "nodes_within_two_hops",
    "nodes_within_three_hops",
    "disjoint_paths_to_large_place",
    "bridge_edge_fraction",
    "within_module_degree_zscore",
    "participation_coefficient",
]
CONNECTEDNESS_FEATURE_COLUMNS = [
    "place_graph_degree",
    "place_graph_pagerank",
    "local_place_neighbor_count",
    "direct_place_neighbor_count",
    "same_parent_place_neighbor_count",
    "large_place_neighbor_count",
    "large_place_max_degree",
    "large_place_max_pagerank",
    "has_large_place_neighbor",
    "strong_place_tie_count",
    "mythic_figure_count",
    "action_pattern_count",
    "shared_mythic_figure_neighbor_count",
    "shared_mythic_figure_count",
    "max_shared_mythic_figures_with_neighbor",
    "shared_mythic_figure_large_place_neighbor_count",
    "shared_action_neighbor_count",
    "shared_action_pattern_count",
    "shared_action_neighbor_pattern_count",
    "max_shared_action_patterns_with_neighbor",
    "shared_action_large_place_neighbor_count",
    "exclusive_figure_count",
    "panhellenic_figure_count",
    "figure_mean_ubiquity",
    "figure_max_ubiquity",
    "kin_linked_place_count",
    "kin_linked_neighbor_count",
    "kin_linked_large_place_count",
    "action_profile_entropy",
    "max_action_cosine_with_neighbor",
    "mean_action_cosine_with_neighbors",
    "max_action_cosine_with_large_place",
    "archaic_story_count",
    "classical_story_count",
    "hellenistic_story_count",
    "early_imperial_story_count",
    "earliest_attestation_year",
    "latest_attestation_year",
    "attestation_span_years",
    "shared_figure_count_zscore",
    "shared_figure_neighbor_zscore",
]
GEOGRAPHY_FEATURE_COLUMNS = [
    "has_coordinates",
    "geo_distance_to_nearest_large_place_km",
    "geo_distance_to_nearest_place_km",
    "places_within_50km_count",
    "narrative_neighbor_count_with_coords",
    "mean_narrative_neighbor_distance_km",
    "min_narrative_neighbor_distance_km",
    "max_narrative_neighbor_distance_km",
    "neighbors_within_25km_count",
    "neighbors_within_50km_count",
    "neighbors_within_100km_count",
    "local_tie_fraction_50km",
]
FAME_FEATURE_COLUMNS = [
    "pausanias_mention_count",
    "pausanias_passage_count",
    "manto_pre_pausanias_edge_count",
]
FEATURE_COLUMNS = NETWORK_FEATURE_COLUMNS
MODEL_RUN_METRIC_COLUMNS = {
    "balanced_accuracy": "DOUBLE PRECISION",
    "true_survives_pred_survives": "INTEGER",
    "true_survives_pred_does_not_survive": "INTEGER",
    "true_does_not_survive_pred_survives": "INTEGER",
    "true_does_not_survive_pred_does_not_survive": "INTEGER",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_database_argument(parser)
    parser.add_argument("--release-record-id", type=int, default=None)
    parser.add_argument("--feature-set-version", default=FEATURE_SET_VERSION)
    parser.add_argument(
        "--connectedness-feature-set-version",
        default=CONNECTEDNESS_FEATURE_SET_VERSION,
    )
    parser.add_argument(
        "--geography-feature-set-version",
        default=GEOGRAPHY_FEATURE_SET_VERSION,
    )
    parser.add_argument(
        "--feature-family",
        default="network",
        help=(
            "Comma-separated combination of network, connectedness, geography, "
            "and fame (e.g. 'connectedness,fame'). 'combined' means "
            "network+connectedness; 'all' means every family. 'fame' alone is "
            "the no-structure attention baseline the structural families must beat."
        ),
    )
    parser.add_argument(
        "--cv-folds",
        type=int,
        default=0,
        help=(
            "When >= 2, report pooled out-of-fold metrics from stratified "
            "k-fold cross-validation instead of a single train/test split."
        ),
    )
    parser.add_argument("--label-source-version", default=LABEL_SOURCE_VERSION)
    parser.add_argument(
        "--training-label-set",
        choices=TRAINING_LABEL_SETS,
        default="manto",
        help=(
            "Which target labels to train from. 'manto' is the default; "
            "'combined' adds sentence and passage LLM labels by normalized place name."
        ),
    )
    parser.add_argument(
        "--label-conflict-policy",
        choices=("drop", "prefer-manto", "prefer-llm"),
        default="drop",
        help="How to handle contradictory labels for the same normalized key.",
    )
    parser.add_argument("--min-samples", type=int, default=10)
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--include-non-pre-pausanias", action="store_true")
    return parser.parse_args()


def latest_release_id(conn) -> int:
    df = read_sql_query(
        """
        SELECT record_id
        FROM manto_releases
        WHERE import_status IN ('imported', 'partial_imported')
        ORDER BY COALESCE(imported_at, updated_at) DESC, record_id DESC
        LIMIT 1
        """,
        conn,
    )
    if df.empty:
        raise RuntimeError("No imported MANTO release found.")
    return int(df.iloc[0]["record_id"])


def resolve_feature_families(feature_family: str) -> list[str]:
    if feature_family in FEATURE_FAMILY_ALIASES:
        return list(FEATURE_FAMILY_ALIASES[feature_family])
    families = [part.strip() for part in feature_family.split(",") if part.strip()]
    unknown = sorted(set(families) - set(BASE_FEATURE_FAMILIES))
    if unknown or not families:
        raise SystemExit(
            f"Unknown feature families {unknown}; choose from "
            f"{BASE_FEATURE_FAMILIES} (comma-separated) or aliases "
            f"{sorted(FEATURE_FAMILY_ALIASES)}."
        )
    seen: list[str] = []
    for family in families:
        if family not in seen:
            seen.append(family)
    return seen


def load_family_table(
    conn,
    *,
    table: str,
    columns: list[str],
    release_id: int,
    feature_set_version: str,
    pre_pausanias_only: bool,
):
    column_sql = ", ".join(IDENTITY_COLUMNS + columns)
    return read_sql_query(
        f"""
        SELECT {column_sql}
        FROM {table}
        WHERE release_record_id = %s
          AND feature_set_version = %s
          AND pre_pausanias_only = %s
        """,
        conn,
        (release_id, feature_set_version, pre_pausanias_only),
    )


def load_fame_counts(conn, *, release_id: int):
    """Attention-only baseline: Pausanias mention volume and raw MANTO degree.

    Mention counts arrive via manto_place_links, so unlinked places count 0;
    the MANTO edge count deliberately includes bookkeeping relations because it
    measures attestation volume, not narrative structure.
    """
    mentions = read_sql_query(
        """
        SELECT l.manto_id,
               count(*) AS pausanias_mention_count,
               count(DISTINCT pn.passage_id) AS pausanias_passage_count
        FROM manto_place_links l
        JOIN proper_nouns pn
          ON pn.reference_form = l.reference_form
         AND pn.entity_type = l.entity_type
        WHERE l.release_record_id = %s
          AND l.confidence <> 'rejected'
        GROUP BY l.manto_id
        """,
        conn,
        (release_id,),
    )
    edge_counts = read_sql_query(
        """
        SELECT manto_id, count(*) AS manto_pre_pausanias_edge_count
        FROM (
            SELECT source_manto_id AS manto_id
            FROM manto_edges
            WHERE release_record_id = %s AND is_pre_pausanias
            UNION ALL
            SELECT target_manto_id
            FROM manto_edges
            WHERE release_record_id = %s AND is_pre_pausanias
        ) endpoints
        GROUP BY manto_id
        """,
        conn,
        (release_id, release_id),
    )
    if mentions.empty:
        merged = edge_counts.copy()
        merged["pausanias_mention_count"] = 0
        merged["pausanias_passage_count"] = 0
    else:
        merged = mentions.merge(edge_counts, on="manto_id", how="outer")
    for column in FAME_FEATURE_COLUMNS:
        if column not in merged.columns:
            merged[column] = 0
    return merged[["manto_id"] + FAME_FEATURE_COLUMNS].fillna(0)


FAMILY_TABLES = {
    "network": ("manto_place_network_features", NETWORK_FEATURE_COLUMNS),
    "connectedness": ("manto_place_connectedness_features", CONNECTEDNESS_FEATURE_COLUMNS),
    "geography": ("manto_place_geography_features", GEOGRAPHY_FEATURE_COLUMNS),
}


def load_feature_rows(
    conn,
    *,
    release_id: int,
    feature_set_version: str,
    connectedness_feature_set_version: str,
    geography_feature_set_version: str,
    pre_pausanias_only: bool,
    feature_family: str,
):
    families = resolve_feature_families(feature_family)
    versions = {
        "network": feature_set_version,
        "connectedness": connectedness_feature_set_version,
        "geography": geography_feature_set_version,
        "fame": FAME_FEATURE_SET_VERSION,
    }
    feature_columns: list[str] = []
    merged = None
    # Fame has no feature table of its own; it joins onto another family's rows,
    # so a fame-only run borrows the network rows as its identity spine.
    table_families = [family for family in families if family != "fame"]
    spine_families = table_families or ["network"]
    for family in spine_families:
        table, columns = FAMILY_TABLES[family]
        frame = load_family_table(
            conn,
            table=table,
            columns=columns,
            release_id=release_id,
            feature_set_version=versions[family],
            pre_pausanias_only=pre_pausanias_only,
        )
        if family in families:
            feature_columns.extend(columns)
        else:
            frame = frame[IDENTITY_COLUMNS]
        if merged is None:
            merged = frame
        elif frame.empty or merged.empty:
            merged = merged.iloc[0:0].copy()
        else:
            merge_columns = [
                column for column in frame.columns
                if column in ("reference_form", "entity_type", "manto_id")
                or column not in merged.columns
            ]
            merged = merged.merge(
                frame[merge_columns],
                on=["reference_form", "entity_type", "manto_id"],
                how="inner",
            )
    if "fame" in families and merged is not None and not merged.empty:
        fame = load_fame_counts(conn, release_id=release_id)
        merged = merged.merge(fame, on="manto_id", how="left")
        merged[FAME_FEATURE_COLUMNS] = merged[FAME_FEATURE_COLUMNS].fillna(0)
        feature_columns.extend(FAME_FEATURE_COLUMNS)
    elif "fame" in families:
        feature_columns.extend(FAME_FEATURE_COLUMNS)
    run_version = "+".join(versions[family] for family in families)
    return merged, feature_columns, run_version


def label_source_version_for_run(args: argparse.Namespace) -> str:
    if args.training_label_set == "manto":
        return args.label_source_version
    if args.training_label_set == "combined":
        return f"{args.label_source_version}+{LLM_LABEL_SOURCE_VERSION}"
    return f"{LLM_LABEL_SOURCE_VERSION}:{args.training_label_set}"


def label_key(kind: str, value: str | None) -> str:
    if kind == "manto":
        return f"manto:{value or ''}"
    return f"name:{normalize_name(value)}"


def label_keys(
    kind: str,
    value: str | None,
    *,
    include_parenthetical_content: bool = False,
    include_location_container: bool = False,
    include_generic_head: bool = False,
) -> set[str]:
    if kind == "manto":
        return {label_key(kind, value)}
    variants = name_variants(
        value,
        include_parenthetical_content=include_parenthetical_content,
        include_location_container=include_location_container,
        include_generic_head=include_generic_head,
    )
    return {f"name:{variant}" for variant in variants} | {
        f"translit:{key}" for key in transliteration_keys(variants)
    }


def load_manto_label_records(
    conn,
    *,
    release_id: int,
    label_source_version: str,
) -> list[dict[str, str]]:
    df = read_sql_query(
        """
        SELECT object_id, place_name, target_label
        FROM manto_place_status_labels
        WHERE release_record_id = %s
          AND label_source_version = %s
          AND target_label IN ('survives', 'does_not_survive')
        """,
        conn,
        (release_id, label_source_version),
    )
    records: list[dict[str, str]] = []
    for _, row in df.iterrows():
        object_id = str(row["object_id"])
        label = row["target_label"]
        records.append(
            {
                "key": label_key("manto", object_id),
                "label": label,
                "source": "manto",
            }
        )
        name_key = normalize_name(row["place_name"])
        if name_key:
            for key in label_keys("name", row["place_name"]):
                records.append(
                    {
                        "key": key,
                        "label": label,
                        "source": "manto",
                    }
                )

    return records


def label_records_from_name_rows(
    df,
    *,
    name_column: str,
    source: str,
    include_parenthetical_content: bool = False,
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for _, row in df.iterrows():
        for key in label_keys(
            "name",
            row[name_column],
            include_parenthetical_content=include_parenthetical_content,
            include_location_container=True,
            include_generic_head=True,
        ):
            records.append(
                {
                    "key": key,
                    "label": row["target_label"],
                    "source": source,
                }
            )
    return records


def load_sentence_llm_label_records(conn) -> list[dict[str, str]]:
    df = read_sql_query(
        """
        SELECT canonical_place_name, target_label
        FROM place_state_mentions
        WHERE target_label IN ('survives', 'does_not_survive')
        """,
        conn,
    )
    return label_records_from_name_rows(
        df,
        name_column="canonical_place_name",
        source="sentence-llm",
        include_parenthetical_content=True,
    )


def load_passage_llm_label_records(conn) -> list[dict[str, str]]:
    df = read_sql_query(
        """
        SELECT canonical_place_name, target_label
        FROM passage_place_state_mentions
        WHERE target_label IN ('survives', 'does_not_survive')
        """,
        conn,
    )
    return label_records_from_name_rows(
        df,
        name_column="canonical_place_name",
        source="passage-llm",
        include_parenthetical_content=True,
    )


def choose_conflicting_label(
    existing: dict[str, str],
    incoming: dict[str, str],
    *,
    conflict_policy: str,
) -> dict[str, str] | None:
    if existing["label"] == incoming["label"]:
        return existing
    if conflict_policy == "prefer-manto":
        if existing["source"] == "manto":
            return existing
        if incoming["source"] == "manto":
            return incoming
    if conflict_policy == "prefer-llm":
        if existing["source"] != "manto":
            return existing
        if incoming["source"] != "manto":
            return incoming
    return None


def merge_label_records(
    records: Iterable[dict[str, str]],
    *,
    conflict_policy: str,
) -> tuple[dict[str, str], Counter]:
    merged: dict[str, dict[str, str] | None] = {}
    stats: Counter = Counter()
    for record in records:
        if not record["key"] or record["key"] in {"manto:", "name:"}:
            continue
        stats["records"] += 1
        stats[f"records_{record['source']}"] += 1
        existing = merged.get(record["key"])
        if existing is None and record["key"] in merged:
            stats["ignored_after_conflict"] += 1
            continue
        if existing is None:
            merged[record["key"]] = record
            continue
        winner = choose_conflicting_label(
            existing,
            record,
            conflict_policy=conflict_policy,
        )
        if winner is None:
            merged[record["key"]] = None
            stats["conflicts_dropped"] += 1
        else:
            merged[record["key"]] = winner
            if winner is not existing:
                stats["conflicts_resolved"] += 1
    labels = {
        key: record["label"]
        for key, record in merged.items()
        if record is not None
    }
    stats["label_keys"] = len(labels)
    return labels, stats


def load_labels(
    conn,
    *,
    release_id: int,
    label_source_version: str,
    training_label_set: str,
    conflict_policy: str,
) -> tuple[dict[str, str], Counter]:
    records: list[dict[str, str]] = []
    if training_label_set in {"manto", "combined"}:
        records.extend(
            load_manto_label_records(
                conn,
                release_id=release_id,
                label_source_version=label_source_version,
            )
        )
    if training_label_set in {"sentence-llm", "llm", "combined"}:
        records.extend(load_sentence_llm_label_records(conn))
    if training_label_set in {"passage-llm", "llm", "combined"}:
        records.extend(load_passage_llm_label_records(conn))
    return merge_label_records(records, conflict_policy=conflict_policy)


def attach_labels(features_df, labels: dict[str, str]):
    rows = []
    for _, row in features_df.iterrows():
        label = labels.get(label_key("manto", str(row.get("manto_id") or "")))
        candidate_names = [
            row.get("reference_form"),
            row.get("english_transcription"),
            row.get("manto_label"),
        ]
        if not label:
            for name in candidate_names:
                for key in label_keys("name", name):
                    label = labels.get(key)
                    if label:
                        break
                if label:
                    break
        if not label:
            continue
        rows.append({**row.to_dict(), "target_label": label})
    if not rows:
        return features_df.iloc[0:0].copy()
    import pandas as pd

    return pd.DataFrame(rows)


def ensure_model_run_metric_columns(conn) -> None:
    with conn.cursor() as cursor:
        for column_name, column_type in MODEL_RUN_METRIC_COLUMNS.items():
            if not column_exists(conn, "place_survival_model_runs", column_name):
                cursor.execute(
                    f"ALTER TABLE place_survival_model_runs ADD COLUMN {column_name} {column_type}"
                )
    conn.commit()


def model_metrics(y_test: np.ndarray, y_pred: np.ndarray, baseline_pred: np.ndarray) -> dict:
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test,
        y_pred,
        labels=[1, 0],
        zero_division=0,
    )
    confusion = confusion_matrix(y_test, y_pred, labels=[1, 0])
    return {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "baseline_accuracy": float(accuracy_score(y_test, baseline_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, y_pred)),
        "precision_survives": float(precision[0]),
        "recall_survives": float(recall[0]),
        "f1_survives": float(f1[0]),
        "precision_does_not_survive": float(precision[1]),
        "recall_does_not_survive": float(recall[1]),
        "f1_does_not_survive": float(f1[1]),
        "true_survives_pred_survives": int(confusion[0][0]),
        "true_survives_pred_does_not_survive": int(confusion[0][1]),
        "true_does_not_survive_pred_survives": int(confusion[1][0]),
        "true_does_not_survive_pred_does_not_survive": int(confusion[1][1]),
    }


def save_run(
    conn,
    *,
    run_id: str,
    release_id: int,
    feature_set_version: str,
    label_source_version: str,
    pre_pausanias_only: bool,
    status: str,
    sample_count: int,
    positive_count: int,
    negative_count: int,
    metrics: dict | None = None,
    notes: str = "",
) -> None:
    metrics = metrics or {}
    timestamp = now_iso()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO place_survival_model_runs (
                run_id, release_record_id, feature_set_version, label_source_version,
                model_type, pre_pausanias_only, started_at, completed_at, status,
                sample_count, positive_count, negative_count, accuracy,
                baseline_accuracy, balanced_accuracy,
                precision_survives, recall_survives, f1_survives,
                precision_does_not_survive, recall_does_not_survive,
                f1_does_not_survive, true_survives_pred_survives,
                true_survives_pred_does_not_survive,
                true_does_not_survive_pred_survives,
                true_does_not_survive_pred_does_not_survive, notes
            )
            VALUES (%s, %s, %s, %s, 'logistic_regression', %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (run_id) DO UPDATE
            SET completed_at = EXCLUDED.completed_at,
                status = EXCLUDED.status,
                sample_count = EXCLUDED.sample_count,
                positive_count = EXCLUDED.positive_count,
                negative_count = EXCLUDED.negative_count,
                accuracy = EXCLUDED.accuracy,
                baseline_accuracy = EXCLUDED.baseline_accuracy,
                balanced_accuracy = EXCLUDED.balanced_accuracy,
                precision_survives = EXCLUDED.precision_survives,
                recall_survives = EXCLUDED.recall_survives,
                f1_survives = EXCLUDED.f1_survives,
                precision_does_not_survive = EXCLUDED.precision_does_not_survive,
                recall_does_not_survive = EXCLUDED.recall_does_not_survive,
                f1_does_not_survive = EXCLUDED.f1_does_not_survive,
                true_survives_pred_survives = EXCLUDED.true_survives_pred_survives,
                true_survives_pred_does_not_survive = EXCLUDED.true_survives_pred_does_not_survive,
                true_does_not_survive_pred_survives = EXCLUDED.true_does_not_survive_pred_survives,
                true_does_not_survive_pred_does_not_survive = EXCLUDED.true_does_not_survive_pred_does_not_survive,
                notes = EXCLUDED.notes
            """,
            (
                run_id,
                release_id,
                feature_set_version,
                label_source_version,
                pre_pausanias_only,
                timestamp,
                timestamp,
                status,
                sample_count,
                positive_count,
                negative_count,
                metrics.get("accuracy"),
                metrics.get("baseline_accuracy"),
                metrics.get("balanced_accuracy"),
                metrics.get("precision_survives"),
                metrics.get("recall_survives"),
                metrics.get("f1_survives"),
                metrics.get("precision_does_not_survive"),
                metrics.get("recall_does_not_survive"),
                metrics.get("f1_does_not_survive"),
                metrics.get("true_survives_pred_survives"),
                metrics.get("true_survives_pred_does_not_survive"),
                metrics.get("true_does_not_survive_pred_survives"),
                metrics.get("true_does_not_survive_pred_does_not_survive"),
                notes,
            ),
        )
    conn.commit()


def save_feature_scores(conn, run_id: str, feature_names: list[str], coefficients: np.ndarray) -> None:
    timestamp = now_iso()
    rows = []
    for feature, coefficient in zip(feature_names, coefficients):
        rows.append(
            (
                run_id,
                feature,
                float(coefficient),
                float(abs(coefficient)),
                "survives" if coefficient > 0 else "does_not_survive",
                timestamp,
            )
        )
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO place_survival_feature_scores (
                run_id, feature_name, coefficient, abs_coefficient, direction, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (run_id, feature_name) DO UPDATE
            SET coefficient = EXCLUDED.coefficient,
                abs_coefficient = EXCLUDED.abs_coefficient,
                direction = EXCLUDED.direction,
                created_at = EXCLUDED.created_at
            """,
            rows,
        )
    conn.commit()


def main() -> None:
    args = parse_arguments()
    pre_pausanias_only = not args.include_non_pre_pausanias
    run_id = str(uuid.uuid4())
    with connect(args.database_url) as conn:
        initialize_schema(conn)
        ensure_model_run_metric_columns(conn)
        release_id = args.release_record_id or latest_release_id(conn)
        features, feature_columns, run_feature_set_version = load_feature_rows(
            conn,
            release_id=release_id,
            feature_set_version=args.feature_set_version,
            connectedness_feature_set_version=args.connectedness_feature_set_version,
            geography_feature_set_version=args.geography_feature_set_version,
            pre_pausanias_only=pre_pausanias_only,
            feature_family=args.feature_family,
        )
        labels, label_stats = load_labels(
            conn,
            release_id=release_id,
            label_source_version=args.label_source_version,
            training_label_set=args.training_label_set,
            conflict_policy=args.label_conflict_policy,
        )
        training = attach_labels(features, labels)
        y = np.array([1 if label == "survives" else 0 for label in training.get("target_label", [])])
        positive_count = int(np.sum(y)) if len(y) else 0
        negative_count = int(len(y) - positive_count)
        if (
            len(training) < args.min_samples
            or len(set(y)) < 2
            or positive_count < 2
            or negative_count < 2
        ):
            save_run(
                conn,
                run_id=run_id,
                release_id=release_id,
                feature_set_version=run_feature_set_version,
                label_source_version=label_source_version_for_run(args),
                pre_pausanias_only=pre_pausanias_only,
                status="blocked_insufficient_training_data",
                sample_count=len(training),
                positive_count=positive_count,
                negative_count=negative_count,
                notes=(
                    f"Need at least {args.min_samples} linked labeled places and at least "
                    f"two examples from both classes; "
                    f"feature rows={len(features)}, label keys={len(labels)}, "
                    f"feature family={args.feature_family}, "
                    f"label set={args.training_label_set}, "
                    f"label stats={dict(label_stats)}."
                ),
            )
            print(
                f"Insufficient place-survival training data: {len(training)} linked rows "
                f"({positive_count} survives, {negative_count} does_not_survive)."
            )
            return
        x = training[feature_columns].astype(float).to_numpy()

        def make_pipeline() -> Pipeline:
            return Pipeline(
                [
                    ("scale", StandardScaler()),
                    ("logreg", LogisticRegression(max_iter=2000, class_weight="balanced")),
                ]
            )

        cv_folds = min(args.cv_folds, positive_count, negative_count) if args.cv_folds >= 2 else 0
        if cv_folds >= 2:
            splitter = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
            oof_pred = np.zeros(len(y), dtype=int)
            for train_index, test_index in splitter.split(x, y):
                fold_pipeline = make_pipeline()
                fold_pipeline.fit(x[train_index], y[train_index])
                oof_pred[test_index] = fold_pipeline.predict(x[test_index])
            majority_label = Counter(y).most_common(1)[0][0]
            baseline_pred = np.full(len(y), majority_label)
            metrics = model_metrics(y, oof_pred, baseline_pred)
            evaluation_mode = f"{cv_folds}-fold-cv"
            pipeline = make_pipeline()
            pipeline.fit(x, y)
        else:
            x_train, x_test, y_train, y_test = train_test_split(
                x,
                y,
                test_size=args.test_size,
                random_state=42,
                stratify=y,
            )
            pipeline = make_pipeline()
            pipeline.fit(x_train, y_train)
            y_pred = pipeline.predict(x_test)
            majority_label = Counter(y_train).most_common(1)[0][0]
            baseline_pred = np.full(len(y_test), majority_label)
            metrics = model_metrics(y_test, y_pred, baseline_pred)
            evaluation_mode = "single-split"
        save_run(
            conn,
            run_id=run_id,
            release_id=release_id,
            feature_set_version=run_feature_set_version,
            label_source_version=label_source_version_for_run(args),
            pre_pausanias_only=pre_pausanias_only,
            status="completed",
            sample_count=len(training),
            positive_count=positive_count,
            negative_count=negative_count,
            metrics=metrics,
            notes=(
                f"feature family={args.feature_family}; "
                f"label set={args.training_label_set}; "
                f"conflict policy={args.label_conflict_policy}; "
                f"evaluation={evaluation_mode}; "
                f"label stats={dict(label_stats)}"
            ),
        )
        coefficients = pipeline.named_steps["logreg"].coef_[0]
        save_feature_scores(conn, run_id, feature_columns, coefficients)
    print(
        f"Trained place-survival model {run_id}: accuracy={metrics['accuracy']:.3f}, "
        f"baseline={metrics['baseline_accuracy']:.3f}, "
        f"balanced_accuracy={metrics['balanced_accuracy']:.3f}, "
        f"samples={len(training)}, "
        f"features={args.feature_family}, "
        f"labels={args.training_label_set}, "
        f"evaluation={evaluation_mode}."
    )


if __name__ == "__main__":
    main()
