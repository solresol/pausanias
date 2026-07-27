import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from predict_place_survival import (
    ATTESTATION_FEATURE_COLUMNS,
    attach_labels,
    collapse_training_places,
    label_key,
    label_keys,
    load_pre_pausanias_attestation_counts,
    merge_label_records,
    model_metrics,
    resolve_feature_families,
)


class PredictPlaceSurvivalTests(unittest.TestCase):
    def test_merge_label_records_drops_conflicting_name_labels(self):
        labels, stats = merge_label_records(
            [
                {
                    "key": label_key("name", "Eleutherae"),
                    "label": "survives",
                    "source": "manto",
                },
                {
                    "key": label_key("name", "Eleutherae"),
                    "label": "does_not_survive",
                    "source": "sentence-llm",
                },
                {
                    "key": label_key("name", "Oropus"),
                    "label": "survives",
                    "source": "sentence-llm",
                },
            ],
            conflict_policy="drop",
        )

        self.assertNotIn(label_key("name", "Eleutherae"), labels)
        self.assertEqual(labels[label_key("name", "Oropus")], "survives")
        self.assertEqual(stats["conflicts_dropped"], 1)

    def test_attach_labels_prefers_manto_id_then_normalized_names(self):
        features = pd.DataFrame(
            [
                {
                    "reference_form": "Eleutherae",
                    "english_transcription": "Eleutherae",
                    "manto_id": "123",
                    "manto_label": "Eleutherae",
                },
                {
                    "reference_form": "Μαντίνεια",
                    "english_transcription": "Mantinea",
                    "manto_id": "456",
                    "manto_label": "🌍 Mantinea (Arcadia)",
                },
            ]
        )
        labels = {
            label_key("manto", "123"): "survives",
        }
        for key in label_keys("name", "ancient Mantinea", include_generic_head=True):
            labels[key] = "does_not_survive"

        attached = attach_labels(features, labels)

        self.assertEqual(list(attached["target_label"]), ["survives", "does_not_survive"])

    def test_model_metrics_store_confusion_matrix_when_accuracy_matches_baseline(self):
        y_test = np.array([1] * 12 + [0] * 16)
        y_pred = np.array([1] * 9 + [0] * 3 + [1] * 9 + [0] * 7)
        baseline_pred = np.zeros(len(y_test), dtype=int)

        metrics = model_metrics(y_test, y_pred, baseline_pred)

        self.assertAlmostEqual(metrics["accuracy"], metrics["baseline_accuracy"])
        self.assertAlmostEqual(metrics["balanced_accuracy"], 0.59375)
        self.assertEqual(metrics["true_survives_pred_survives"], 9)
        self.assertEqual(metrics["true_survives_pred_does_not_survive"], 3)
        self.assertEqual(metrics["true_does_not_survive_pred_survives"], 9)
        self.assertEqual(metrics["true_does_not_survive_pred_does_not_survive"], 7)

    def test_resolve_feature_families_handles_aliases_combinations_and_errors(self):
        self.assertEqual(
            resolve_feature_families("combined"), ["network", "connectedness"]
        )
        self.assertEqual(
            resolve_feature_families("all"),
            ["network", "connectedness", "geography", "attestation"],
        )
        self.assertEqual(
            resolve_feature_families("connectedness, fame"),
            ["connectedness", "attestation"],
        )
        self.assertEqual(
            resolve_feature_families("fame,fame"),
            ["attestation"],
        )
        with self.assertRaises(SystemExit):
            resolve_feature_families("mystery")
        with self.assertRaises(SystemExit):
            resolve_feature_families("")

    def test_attestation_baseline_excludes_pausanias_mention_features(self):
        edge_counts = pd.DataFrame(
            [
                {
                    "manto_id": "123",
                    "manto_pre_pausanias_edge_count": 17,
                }
            ]
        )
        with patch(
            "predict_place_survival.read_sql_query",
            return_value=edge_counts,
        ) as query:
            counts = load_pre_pausanias_attestation_counts(
                object(),
                release_id=19446255,
            )

        self.assertEqual(
            list(counts.columns),
            ["manto_id", "manto_pre_pausanias_edge_count"],
        )
        self.assertEqual(
            ATTESTATION_FEATURE_COLUMNS,
            ["manto_pre_pausanias_edge_count"],
        )
        self.assertNotIn("pausanias_mention_count", counts.columns)
        self.assertNotIn("pausanias_passage_count", counts.columns)
        sql = query.call_args.args[0]
        self.assertIn("is_pre_pausanias", sql)
        self.assertNotIn("proper_nouns", sql)

    def test_training_rows_collapse_to_one_row_per_manto_place(self):
        training = pd.DataFrame(
            [
                {
                    "manto_id": "123",
                    "reference_form": "Amyklai",
                    "degree": 4,
                    "target_label": "survives",
                },
                {
                    "manto_id": "123",
                    "reference_form": "Amyclae",
                    "degree": 4,
                    "target_label": "survives",
                },
                {
                    "manto_id": "456",
                    "reference_form": "Aigai",
                    "degree": 2,
                    "target_label": "survives",
                },
                {
                    "manto_id": "456",
                    "reference_form": "Aegae",
                    "degree": 2,
                    "target_label": "does_not_survive",
                },
            ]
        )

        collapsed, stats = collapse_training_places(training, ["degree"])

        self.assertEqual(list(collapsed["manto_id"]), ["123"])
        self.assertEqual(stats["manto_places_before_conflict_drop"], 2)
        self.assertEqual(stats["duplicate_training_rows_collapsed"], 2)
        self.assertEqual(stats["conflicting_manto_places_dropped"], 1)
        self.assertEqual(stats["training_rows_after_place_collapse"], 1)


if __name__ == "__main__":
    unittest.main()
