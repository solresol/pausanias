import unittest

import pandas as pd

from predict_place_survival import attach_labels, label_key, label_keys, merge_label_records


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


if __name__ == "__main__":
    unittest.main()
