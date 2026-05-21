import unittest

import numpy as np
from scipy import sparse

from website.data import _binary_classification_metrics, _top_feature_contributions


class ComplementaryAnalysisHelperTests(unittest.TestCase):
    def test_binary_metrics_keep_historical_and_mythic_order(self):
        metrics = _binary_classification_metrics(
            np.array([0, 0, 1, 1]),
            np.array([0, 1, 0, 1]),
        )

        self.assertEqual(metrics["actual_0_pred_0"], 1)
        self.assertEqual(metrics["actual_0_pred_1"], 1)
        self.assertEqual(metrics["actual_1_pred_0"], 1)
        self.assertEqual(metrics["actual_1_pred_1"], 1)
        self.assertAlmostEqual(metrics["accuracy"], 0.5)

    def test_top_feature_contributions_follow_predicted_direction(self):
        row = sparse.csr_matrix([[0.5, 1.0, 2.0]])
        feature_names = np.array(["daughter", "war", "tomb"])
        coefficients = np.array([2.0, -3.0, 0.25])

        mythic_terms = _top_feature_contributions(
            row,
            feature_names,
            coefficients,
            predicted_label=1,
            limit=2,
        )
        historical_terms = _top_feature_contributions(
            row,
            feature_names,
            coefficients,
            predicted_label=0,
            limit=2,
        )

        self.assertEqual([item["term"] for item in mythic_terms], ["daughter", "tomb"])
        self.assertEqual([item["term"] for item in historical_terms], ["war"])


if __name__ == "__main__":
    unittest.main()
