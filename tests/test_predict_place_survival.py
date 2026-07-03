import unittest

import numpy as np
import pandas as pd

from predict_place_survival import (
    attach_labels,
    label_key,
    label_keys,
    merge_label_records,
    model_metrics,
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


if __name__ == "__main__":
    unittest.main()
