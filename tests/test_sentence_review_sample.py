import tempfile
import unittest
from pathlib import Path

import pandas as pd

from website.generators import (
    _highlight_sentence_context,
    generate_sentence_review_sample_page,
)


class SentenceReviewSampleTests(unittest.TestCase):
    def test_highlight_sentence_context_marks_exact_sentence(self):
        rendered, matched = _highlight_sentence_context(
            "Alpha sentence. Target sentence. Omega sentence.",
            "Target sentence.",
        )

        self.assertTrue(matched)
        self.assertIn(
            '<mark class="sentence-review-highlight">Target sentence.</mark>',
            rendered,
        )

    def test_highlight_sentence_context_matches_collapsed_whitespace(self):
        rendered, matched = _highlight_sentence_context(
            "Alpha sentence. Target\nsentence. Omega sentence.",
            "Target sentence.",
        )

        self.assertTrue(matched)
        self.assertIn(
            '<mark class="sentence-review-highlight">Target\nsentence.</mark>',
            rendered,
        )

    def test_generate_sentence_review_sample_page_writes_context_page(self):
        sample = pd.DataFrame(
            [
                {
                    "sample_rank": 1,
                    "passage_id": "1.1.1",
                    "sentence_number": 2,
                    "sentence": "Target Greek sentence.",
                    "english_sentence": "Target English sentence.",
                    "passage": "First Greek sentence. Target Greek sentence. Later Greek sentence.",
                    "english_translation": "First English sentence. Target English sentence. Later English sentence.",
                    "prompt_version": "greta-test-v1",
                    "model": "gpt-test",
                    "myth_history_bucket": "mythic",
                    "expresses_scepticism": False,
                    "confidence": "high",
                    "rationale": "It concerns mythic material.",
                }
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_sentence_review_sample_page(sample, tmpdir, "Pausanias Analysis")
            page_path = Path(tmpdir) / "annotations" / "sentence-review-sample.html"
            page = page_path.read_text(encoding="utf-8")

        self.assertIn("Sentence Review Sample", page)
        self.assertIn('href="../translation/1/1/1.html"', page)
        self.assertIn('<span class="status-pill bucket-mythic">mythic</span>', page)
        self.assertIn(
            '<mark class="sentence-review-highlight">Target Greek sentence.</mark>',
            page,
        )
        self.assertIn(
            '<mark class="sentence-review-highlight">Target English sentence.</mark>',
            page,
        )


if __name__ == "__main__":
    unittest.main()
