#!/usr/bin/env python
"""Train an explainable classifier for Pausanias place survival claims."""

from __future__ import annotations

import argparse
import re
import uuid
from collections import Counter
from datetime import datetime, timezone

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from pausanias_db import add_database_argument, connect, initialize_schema, read_sql_query


FEATURE_SET_VERSION = "manto-pausanias-place-network-v2"
LABEL_SOURCE_VERSION = "manto-entity-info-v1"
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


def load_labels(conn, *, release_id: int, label_source_version: str) -> dict[str, str]:
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
    labels: dict[str, str] = {}
    for _, row in df.iterrows():
        object_id = str(row["object_id"])
        labels[object_id] = row["target_label"]
        name_key = normalize_name(row["place_name"])
        if name_key:
            labels.setdefault(name_key, row["target_label"])
    return labels


def attach_labels(features_df, labels: dict[str, str]):
    rows = []
    for _, row in features_df.iterrows():
        label = labels.get(str(row.get("manto_id") or ""))
        candidate_names = [
            row.get("reference_form"),
            row.get("english_transcription"),
            row.get("manto_label"),
        ]
        if not label:
            for name in candidate_names:
                label = labels.get(normalize_name(name))
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
        labels = load_labels(
            conn,
            release_id=release_id,
            label_source_version=args.label_source_version,
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
                label_source_version=args.label_source_version,
                pre_pausanias_only=pre_pausanias_only,
                status="blocked_insufficient_training_data",
                sample_count=len(training),
                positive_count=positive_count,
                negative_count=negative_count,
                notes=(
                    f"Need at least {args.min_samples} linked labeled places and at least "
                    f"two examples from both classes; "
                    f"feature rows={len(features)}, label names={len(labels)}."
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
            label_source_version=args.label_source_version,
            pre_pausanias_only=pre_pausanias_only,
            status="completed",
            sample_count=len(training),
            positive_count=positive_count,
            negative_count=negative_count,
            metrics=metrics,
        )
        coefficients = pipeline.named_steps["logreg"].coef_[0]
        save_feature_scores(conn, run_id, FEATURE_COLUMNS, coefficients)
    print(
        f"Trained place-survival model {run_id}: accuracy={metrics['accuracy']:.3f}, "
        f"baseline={metrics['baseline_accuracy']:.3f}, samples={len(training)}."
    )


if __name__ == "__main__":
    main()
