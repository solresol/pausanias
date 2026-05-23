import math
import unittest
from pathlib import Path

import pandas as pd

from website.data import (
    calculate_sentence_translation_bucket_analysis,
    calculate_translation_length_analysis,
    calculate_translation_mythic_coefficient_relationship,
    count_words,
)
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

    def test_matches_translation_residual_terms_to_mythic_coefficients(self):
        translation_analysis = {
            "available": True,
            "all_greek_predictors": pd.DataFrame(
                [
                    {
                        "phrase": "hero",
                        "coefficient": 1.2,
                        "passage_count": 5,
                        "mean_residual_with_term": 3.0,
                        "mean_residual_without_term": -0.5,
                    },
                    {
                        "phrase": "war",
                        "coefficient": -0.9,
                        "passage_count": 4,
                        "mean_residual_with_term": -2.0,
                        "mean_residual_without_term": 0.2,
                    },
                    {
                        "phrase": "name",
                        "coefficient": 0.1,
                        "passage_count": 6,
                        "mean_residual_with_term": 0.3,
                        "mean_residual_without_term": -0.1,
                    },
                ]
            ),
            "longer_predictors": pd.DataFrame(
                [
                    {
                        "phrase": "hero",
                        "coefficient": 1.2,
                        "passage_count": 5,
                        "mean_residual_with_term": 3.0,
                        "mean_residual_without_term": -0.5,
                    }
                ]
            ),
            "shorter_predictors": pd.DataFrame(
                [
                    {
                        "phrase": "war",
                        "coefficient": -0.9,
                        "passage_count": 4,
                        "mean_residual_with_term": -2.0,
                        "mean_residual_without_term": 0.2,
                    }
                ]
            ),
        }
        greta_analysis = {
            "available": True,
            "variants": [
                {
                    "available": True,
                    "token_source": "lemma",
                    "include_books_4_8": False,
                    "remove_rhetoric_markers": False,
                    "feature_count": 2,
                    "all_predictors": pd.DataFrame(
                        [
                            {
                                "phrase": "hero",
                                "coefficient": 2.0,
                                "mythic_count": 10,
                                "historical_count": 1,
                                "p_value": 0.01,
                                "q_value": 0.02,
                            },
                            {
                                "phrase": "war",
                                "coefficient": -1.5,
                                "mythic_count": 2,
                                "historical_count": 8,
                                "p_value": 0.03,
                                "q_value": 0.04,
                            },
                            {
                                "phrase": "name",
                                "coefficient": 0.3,
                                "mythic_count": 4,
                                "historical_count": 3,
                                "p_value": 0.5,
                                "q_value": 0.6,
                            },
                        ]
                    ),
                }
            ],
        }

        relationship = calculate_translation_mythic_coefficient_relationship(
            translation_analysis,
            greta_analysis,
        )

        self.assertTrue(relationship["available"])
        self.assertEqual(relationship["metrics"]["matched_term_count"], 3)
        self.assertEqual(relationship["metrics"]["residual_term_count"], 3)
        self.assertIn("abs_mythic_log_odds_coefficient", relationship["points"].columns)
        directions = set(relationship["points"]["classification_direction"])
        self.assertEqual(directions, {"mythic", "historical"})

    def test_compares_sentence_translation_residuals_by_bucket(self):
        rows = []
        for index, greek_words in enumerate(range(3, 8), start=1):
            rows.append(
                {
                    "passage_id": "1.1.1",
                    "sentence_number": index,
                    "sentence": "μυθος " + " ".join(f"α{i}" for i in range(greek_words - 1)),
                    "english_sentence": " ".join(f"m{i}" for i in range(greek_words + 4)),
                    "myth_history_bucket": "mythic",
                }
            )
            rows.append(
                {
                    "passage_id": "1.1.2",
                    "sentence_number": index,
                    "sentence": "πολεμος " + " ".join(f"β{i}" for i in range(greek_words - 1)),
                    "english_sentence": " ".join(f"h{i}" for i in range(greek_words + 1)),
                    "myth_history_bucket": "historical",
                }
            )
            rows.append(
                {
                    "passage_id": "1.1.3",
                    "sentence_number": index,
                    "sentence": "χωρα " + " ".join(f"γ{i}" for i in range(greek_words - 1)),
                    "english_sentence": " ".join(f"o{i}" for i in range(greek_words + 2)),
                    "myth_history_bucket": "other",
                }
            )

        analysis = calculate_sentence_translation_bucket_analysis(
            pd.DataFrame(rows),
            max_features=50,
            top_features=5,
            min_df=1,
        )

        self.assertTrue(analysis["available"])
        self.assertEqual(analysis["metrics"]["sentence_count"], 15)
        summary = analysis["bucket_summary"].set_index("bucket")
        self.assertGreater(
            summary.loc["mythic", "mean_global_residual"],
            summary.loc["historical", "mean_global_residual"],
        )
        self.assertEqual(set(analysis["bucket_analyses"]), {"mythic", "historical", "other"})
        self.assertTrue(analysis["bucket_analyses"]["mythic"]["available"])

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
            "mythic_coefficient_relationship": {
                "available": True,
                "message": "",
                "metrics": {
                    "matched_term_count": 1,
                    "residual_term_count": 2,
                    "linear_pearson": {"coefficient": 0.1, "p_value": 0.5},
                    "linear_spearman": {"coefficient": 0.2, "p_value": 0.4},
                    "extremity_pearson": {"coefficient": 0.3, "p_value": 0.2},
                    "extremity_spearman": {"coefficient": 0.4, "p_value": 0.1},
                    "quadratic_abs_r2": 0.05,
                },
                "points": pd.DataFrame(
                    [
                        {
                            "phrase": "θυγατηρ",
                            "english_translation": "daughter",
                            "translation_direction": "longer",
                            "translation_residual_coefficient": 1.1,
                            "mythic_log_odds_coefficient": 2.3,
                            "abs_mythic_log_odds_coefficient": 2.3,
                            "classification_direction": "mythic",
                            "translation_passage_count": 4,
                            "mythic_count": 3,
                            "historical_count": 1,
                            "mythic_q_value": 0.01,
                        }
                    ]
                ),
            },
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
            "sentence_bucket_analysis": {
                "available": True,
                "message": "",
                "metrics": {
                    "sentence_count": 12,
                    "bucket_count": 3,
                    "length_slope": 1.25,
                    "length_r2": 0.8,
                    "residual_std": 1.5,
                    "greek_vocabulary_source": "lemma",
                },
                "bucket_summary": pd.DataFrame(
                    [
                        {
                            "bucket": "mythic",
                            "label": "Mythic",
                            "sentence_count": 4,
                            "mean_greek_word_count": 8.0,
                            "mean_english_word_count": 11.0,
                            "english_per_greek_word": 1.38,
                            "mean_global_residual": 1.2,
                            "median_global_residual": 1.1,
                            "global_residual_std": 0.5,
                            "bucket_length_slope": 1.4,
                            "bucket_length_r2": 0.7,
                        },
                        {
                            "bucket": "historical",
                            "label": "Historical",
                            "sentence_count": 4,
                            "mean_greek_word_count": 9.0,
                            "mean_english_word_count": 10.0,
                            "english_per_greek_word": 1.11,
                            "mean_global_residual": -0.6,
                            "median_global_residual": -0.4,
                            "global_residual_std": 0.4,
                            "bucket_length_slope": 1.1,
                            "bucket_length_r2": 0.6,
                        },
                    ]
                ),
                "bucket_analyses": {
                    "mythic": {
                        "available": True,
                        "message": "",
                        "metrics": {
                            "passage_count": 4,
                            "length_r2": 0.7,
                            "residual_std": 0.5,
                        },
                        "longer_predictors": pd.DataFrame(
                            [
                                {
                                    "phrase": "μυθος",
                                    "english_translation": "myth",
                                    "coefficient": 0.8,
                                    "passage_count": 3,
                                    "mean_residual_with_term": 1.0,
                                    "mean_residual_without_term": -0.5,
                                }
                            ]
                        ),
                        "shorter_predictors": pd.DataFrame(),
                    }
                },
            },
        }

        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            generate_translation_length_page(analysis, tmpdir, "Pausanias")
            html = (Path(tmpdir) / "translation_length" / "index.html").read_text(encoding="utf-8")
            diagnostic_html = (
                Path(tmpdir) / "translation_length" / "mythic_historical_strength.html"
            ).read_text(encoding="utf-8")

        self.assertIn("Translation Length Residuals", html)
        self.assertNotIn("plotly-2.35.2.min.js", html)
        self.assertIn("English Length vs. Greek Length", html)
        self.assertNotIn("Residual Terms vs. Mythic/Historical Coefficients", html)
        self.assertIn("Sentence Translation Length by Bucket", html)
        self.assertIn("shared sentence-level baseline", html)
        self.assertIn("Greek word count", html)
        self.assertIn("R^2 = 0.900", html)
        self.assertIn("μακρον", html)
        self.assertIn("English Terms in Longer Passages", html)
        self.assertIn("five", html)
        self.assertIn("../translation/1/1/1.html", html)
        self.assertIn("plotly-2.35.2.min.js", diagnostic_html)
        self.assertIn("Exploratory Diagnostic", diagnostic_html)
        self.assertIn("Residual Terms vs. Mythic/Historical Coefficients", diagnostic_html)
        self.assertIn("translation-mythic-signed-scatter", diagnostic_html)
        self.assertIn("θυγατηρ", diagnostic_html)


if __name__ == "__main__":
    unittest.main()
