import unittest

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from lemma_text import casefold_preprocessor, normalize_stopwords
from website.data import (
    RHETORIC_MARKER_WORDS,
    TFIDF_TOKEN_PATTERN,
    _fit_greta_sentence_variant,
)
from website.generators import _legacy_variant_href, _variant_href


class RhetoricMarkerStopwordTests(unittest.TestCase):
    def test_rhetoric_marker_stopwords_cover_accent_variants(self):
        stopwords = normalize_stopwords(RHETORIC_MARKER_WORDS)
        vectorizer = TfidfVectorizer(
            token_pattern=TFIDF_TOKEN_PATTERN,
            preprocessor=casefold_preprocessor,
            stop_words=stopwords,
        )

        vectorizer.fit(
            [
                "λέγουσιν φασιν φασὶν φησιν φησὶν ἔπη",
                "πόλεμον χρήματα",
            ]
        )

        features = set(vectorizer.get_feature_names_out())
        self.assertIn("ἔπη", features)
        self.assertNotIn("λέγουσιν", features)
        self.assertNotIn("φασιν", features)
        self.assertNotIn("φασὶν", features)
        self.assertNotIn("φησιν", features)
        self.assertNotIn("φησὶν", features)

    def test_lemma_variant_removes_reporting_and_framing_markers(self):
        rows = []
        for index in range(12):
            rows.append(
                {
                    "book": "1",
                    "sentence": "λέγουσιν λόγος ἔπος θυγάτηρ θεός ἱερόν",
                    "myth_history_bucket": "mythic",
                }
            )
            rows.append(
                {
                    "book": "1",
                    "sentence": "πόλις νόμος στρατός νικάω χρῆμα",
                    "myth_history_bucket": "historical",
                }
            )

        lemma_lookup = {
            "λέγουσιν": "λέγω",
            "λόγος": "λόγος",
            "ἔπος": "ἔπος",
            "θυγάτηρ": "θυγάτηρ",
            "θεός": "θεός",
            "ἱερόν": "ἱερόν",
            "πόλις": "πόλις",
            "νόμος": "νόμος",
            "στρατός": "στρατός",
            "νικάω": "νικάω",
            "χρῆμα": "χρῆμα",
        }

        with_markers = _fit_greta_sentence_variant(
            pd.DataFrame(rows),
            label="with",
            token_source="lemma",
            include_books_4_8=False,
            remove_rhetoric_markers=False,
            proper_stopwords=[],
            lemma_lookup=lemma_lookup,
            max_features=30,
            top_features=30,
            min_df=1,
        )
        without_markers = _fit_greta_sentence_variant(
            pd.DataFrame(rows),
            label="without",
            token_source="lemma",
            include_books_4_8=False,
            remove_rhetoric_markers=True,
            proper_stopwords=[],
            lemma_lookup=lemma_lookup,
            max_features=30,
            top_features=30,
            min_df=1,
        )

        with_terms = set(with_markers["all_predictors"]["phrase"])
        without_terms = set(without_markers["all_predictors"]["phrase"])
        normalized_markers = set(normalize_stopwords(["λέγω", "λόγος", "ἔπος"]))

        self.assertTrue(normalized_markers <= with_terms)
        self.assertTrue(normalized_markers.isdisjoint(without_terms))
        self.assertIn("θυγάτηρ", without_terms)

    def test_tri_marked_variant_urls_have_legacy_redirect_targets(self):
        variant = {"id": "tri-marked-sentence-lemma-excluding-4-8-with-rhetoric"}

        self.assertEqual(
            _variant_href(variant),
            "tri-marked-sentence-lemma-excluding-4-8-with-rhetoric.html",
        )
        self.assertEqual(
            _legacy_variant_href(variant),
            "greta-sentence-lemma-excluding-4-8-with-rhetoric.html",
        )


if __name__ == "__main__":
    unittest.main()
