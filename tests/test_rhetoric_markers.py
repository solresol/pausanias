import unittest

from sklearn.feature_extraction.text import TfidfVectorizer

from lemma_text import casefold_preprocessor, normalize_stopwords
from website.data import RHETORIC_MARKER_WORDS, TFIDF_TOKEN_PATTERN


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


if __name__ == "__main__":
    unittest.main()
