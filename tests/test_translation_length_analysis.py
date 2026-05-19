import math
import unittest
from pathlib import Path

import pandas as pd

from website.data import calculate_translation_length_analysis, count_words
from website.generators import generate_translation_length_page


class TranslationLengthAnalysisTests(unittest.TestCase):
    def test_counts_word_like_tokens(self):
        self.assertEqual(count_words("alpha beta, gamma."), 3)
        self.assertEqual(count_words("Ἀθηναῖοι καὶ Θηβαῖοι"), 3)

    def test_models_translation_length_residuals(self):
        passages = pd.DataFrame(
            [
                {
                    "id": "1.1.1",
                    "passage": "μακρον αλφα βητα γαμμα",
                    "english_translation": "one two three four five six seven eight",
                },
                {
                    "id": "1.1.2",
                    "passage": "μακρον δελτα εψιλον ζητα",
                    "english_translation": "one two three four five six seven eight",
                },
                {
                    "id": "1.1.3",
                    "passage": "μακρον ητα θητα ιωτα",
                    "english_translation": "one two three four five six seven eight",
                },
                {
                    "id": "1.1.4",
                    "passage": "βραχυ αλφα βητα γαμμα",
                    "english_translation": "one two three four",
                },
                {
                    "id": "1.1.5",
                    "passage": "βραχυ δελτα εψιλον ζητα",
                    "english_translation": "one two three four",
                },
                {
                    "id": "1.1.6",
                    "passage": "βραχυ ητα θητα ιωτα",
                    "english_translation": "one two three four",
                },
            ]
        )

        analysis = calculate_translation_length_analysis(
            passages,
            max_features=20,
            top_features=5,
            min_df=1,
        )

        self.assertTrue(analysis["available"])
        self.assertEqual(analysis["metrics"]["passage_count"], 6)
        self.assertIn("μακρον", set(analysis["longer_predictors"]["phrase"]))
        self.assertIn("βραχυ", set(analysis["shorter_predictors"]["phrase"]))
        self.assertGreater(len(analysis["english_longer_predictors"]), 0)
        self.assertGreater(len(analysis["english_shorter_predictors"]), 0)
        self.assertEqual(len(analysis["length_points"]), 6)
        self.assertIn("length_slope_p_value", analysis["metrics"])
        self.assertGreater(analysis["longest_passages"].iloc[0]["length_residual"], 0)
        self.assertLess(analysis["shortest_passages"].iloc[0]["length_residual"], 0)

    def test_models_source_target_length_relationship(self):
        passages = pd.DataFrame(
            [
                {
                    "id": "1.1.1",
                    "passage": "αλφα βητα",
                    "english_translation": "one two three",
                },
                {
                    "id": "1.1.2",
                    "passage": "αλφα βητα γαμμα δελτα",
                    "english_translation": "one two three four five six seven",
                },
                {
                    "id": "1.1.3",
                    "passage": "αλφα βητα γαμμα δελτα εψιλον ζητα",
                    "english_translation": "one two three four five six seven eight nine",
                },
                {
                    "id": "1.1.4",
                    "passage": "αλφα βητα γαμμα δελτα εψιλον ζητα ητα θητα",
                    "english_translation": "one two three four five six seven eight nine ten eleven twelve thirteen",
                },
                {
                    "id": "1.1.5",
                    "passage": "αλφα βητα γαμμα δελτα εψιλον ζητα ητα θητα ιωτα καππα",
                    "english_translation": "one two three four five six seven eight nine ten eleven twelve thirteen fourteen",
                },
            ]
        )

        analysis = calculate_translation_length_analysis(
            passages,
            max_features=20,
            top_features=5,
            min_df=1,
        )
        metrics = analysis["metrics"]

        self.assertTrue(analysis["available"])
        self.assertGreater(metrics["length_r2"], 0.95)
        self.assertTrue(math.isfinite(metrics["length_slope_p_value"]))
        self.assertLess(metrics["length_slope_p_value"], 0.01)

    def test_generates_translation_length_page(self):
        analysis = {
            "available": True,
            "message": "",
            "metrics": {
                "passage_count": 1,
                "feature_count": 2,
                "length_intercept": 1.0,
                "length_slope": 1.5,
                "length_r2": 0.9,
                "length_intercept_std_error": 0.2,
                "length_intercept_p_value": 0.01,
                "length_slope_std_error": 0.1,
                "length_slope_p_value": 0.001,
                "residual_std": 2.0,
                "vocabulary_residual_r2": 0.4,
                "min_df": 1,
                "max_features": 2,
            },
            "longer_predictors": pd.DataFrame(
                [
                    {
                        "phrase": "μακρον",
                        "english_translation": "long",
                        "coefficient": 1.2,
                        "passage_count": 3,
                        "mean_residual_with_term": 2.1,
                        "mean_residual_without_term": -0.4,
                    }
                ]
            ),
            "shorter_predictors": pd.DataFrame(),
            "english_longer_predictors": pd.DataFrame(
                [
                    {
                        "phrase": "five",
                        "coefficient": 0.7,
                        "passage_count": 1,
                        "mean_residual_with_term": 2.0,
                        "mean_residual_without_term": -0.2,
                    }
                ]
            ),
            "english_shorter_predictors": pd.DataFrame(),
            "length_points": pd.DataFrame(
                [
                    {
                        "id": "1.1.1",
                        "greek_word_count": 4,
                        "english_word_count": 8,
                        "expected_english_word_count": 6.0,
                        "length_residual": 2.0,
                    }
                ]
            ),
            "longest_passages": pd.DataFrame(
                [
                    {
                        "id": "1.1.1",
                        "greek_word_count": 4,
                        "english_word_count": 8,
                        "expected_english_word_count": 6.0,
                        "length_residual": 2.0,
                        "english_translation": "one two three four five six seven eight",
                    }
                ]
            ),
            "shortest_passages": pd.DataFrame(),
        }

        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            generate_translation_length_page(analysis, tmpdir, "Pausanias")
            html = (Path(tmpdir) / "translation_length" / "index.html").read_text(encoding="utf-8")

        self.assertIn("Translation Length Residuals", html)
        self.assertIn("English Length vs. Greek Length", html)
        self.assertIn("Greek word count", html)
        self.assertIn("R^2 = 0.900", html)
        self.assertIn("μακρον", html)
        self.assertIn("English Terms in Longer Passages", html)
        self.assertIn("five", html)
        self.assertIn("../translation/1/1/1.html", html)


if __name__ == "__main__":
    unittest.main()
