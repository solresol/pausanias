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
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from link_manto_places import name_variants
from pausanias_db import add_database_argument, connect, initialize_schema, read_sql_query


FEATURE_SET_VERSION = "manto-pausanias-place-network-v2"
LABEL_SOURCE_VERSION = "manto-entity-info-v1"
LLM_LABEL_SOURCE_VERSION = "llm-place-state-v1"
TRAINING_LABEL_SETS = ("manto", "sentence-llm", "passage-llm", "llm", "combined")
FEATURE_COLUMNS = [
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
]


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


def load_feature_rows(conn, *, release_id: int, feature_set_version: str, pre_pausanias_only: bool):
    return read_sql_query(
        """
        SELECT reference_form, english_transcription, manto_id, manto_label,
               degree, degree_centrality, pagerank, betweenness_centrality,
               clustering_coefficient, component_size, community_size,
               high_centrality_neighbor_count, max_neighbor_pagerank,
               shared_neighbor_high_centrality_score
        FROM manto_place_network_features
        WHERE release_record_id = %s
          AND feature_set_version = %s
          AND pre_pausanias_only = %s
        """,
        conn,
        (release_id, feature_set_version, pre_pausanias_only),
    )


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
    return {
        f"name:{variant}"
        for variant in name_variants(
            value,
            include_parenthetical_content=include_parenthetical_content,
            include_location_container=include_location_container,
            include_generic_head=include_generic_head,
        )
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
                baseline_accuracy, precision_survives, recall_survives, f1_survives,
                precision_does_not_survive, recall_does_not_survive,
                f1_does_not_survive, notes
            )
            VALUES (%s, %s, %s, %s, 'logistic_regression', %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (run_id) DO UPDATE
            SET completed_at = EXCLUDED.completed_at,
                status = EXCLUDED.status,
                sample_count = EXCLUDED.sample_count,
                positive_count = EXCLUDED.positive_count,
                negative_count = EXCLUDED.negative_count,
                accuracy = EXCLUDED.accuracy,
                baseline_accuracy = EXCLUDED.baseline_accuracy,
                precision_survives = EXCLUDED.precision_survives,
                recall_survives = EXCLUDED.recall_survives,
                f1_survives = EXCLUDED.f1_survives,
                precision_does_not_survive = EXCLUDED.precision_does_not_survive,
                recall_does_not_survive = EXCLUDED.recall_does_not_survive,
                f1_does_not_survive = EXCLUDED.f1_does_not_survive,
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
                metrics.get("precision_survives"),
                metrics.get("recall_survives"),
                metrics.get("f1_survives"),
                metrics.get("precision_does_not_survive"),
                metrics.get("recall_does_not_survive"),
                metrics.get("f1_does_not_survive"),
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
        release_id = args.release_record_id or latest_release_id(conn)
        features = load_feature_rows(
            conn,
            release_id=release_id,
            feature_set_version=args.feature_set_version,
            pre_pausanias_only=pre_pausanias_only,
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
                feature_set_version=args.feature_set_version,
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
                    f"label set={args.training_label_set}, "
                    f"label stats={dict(label_stats)}."
                ),
            )
            print(
                f"Insufficient place-survival training data: {len(training)} linked rows "
                f"({positive_count} survives, {negative_count} does_not_survive)."
            )
            return
        x = training[FEATURE_COLUMNS].astype(float).to_numpy()
        x_train, x_test, y_train, y_test = train_test_split(
            x,
            y,
            test_size=args.test_size,
            random_state=42,
            stratify=y,
        )
        pipeline = Pipeline(
            [
                ("scale", StandardScaler()),
                ("logreg", LogisticRegression(max_iter=2000, class_weight="balanced")),
            ]
        )
        pipeline.fit(x_train, y_train)
        y_pred = pipeline.predict(x_test)
        majority_label = Counter(y_train).most_common(1)[0][0]
        baseline_pred = np.full(len(y_test), majority_label)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test,
            y_pred,
            labels=[1, 0],
            zero_division=0,
        )
        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "baseline_accuracy": float(accuracy_score(y_test, baseline_pred)),
            "precision_survives": float(precision[0]),
            "recall_survives": float(recall[0]),
            "f1_survives": float(f1[0]),
            "precision_does_not_survive": float(precision[1]),
            "recall_does_not_survive": float(recall[1]),
            "f1_does_not_survive": float(f1[1]),
        }
        save_run(
            conn,
            run_id=run_id,
            release_id=release_id,
            feature_set_version=args.feature_set_version,
            label_source_version=label_source_version_for_run(args),
            pre_pausanias_only=pre_pausanias_only,
            status="completed",
            sample_count=len(training),
            positive_count=positive_count,
            negative_count=negative_count,
            metrics=metrics,
            notes=(
                f"label set={args.training_label_set}; "
                f"conflict policy={args.label_conflict_policy}; "
                f"label stats={dict(label_stats)}"
            ),
        )
        coefficients = pipeline.named_steps["logreg"].coef_[0]
        save_feature_scores(conn, run_id, FEATURE_COLUMNS, coefficients)
    print(
        f"Trained place-survival model {run_id}: accuracy={metrics['accuracy']:.3f}, "
        f"baseline={metrics['baseline_accuracy']:.3f}, samples={len(training)}, "
        f"labels={args.training_label_set}."
    )


if __name__ == "__main__":
    main()
