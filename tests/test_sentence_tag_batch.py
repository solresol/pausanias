import argparse
import unittest

from sentence_tag_batch import (
    GRETA_BOTH_BATCH_PROMPT_VERSION,
    bucket_from_flags,
    completion_body,
    mode_prompt_version,
    unprocessed_sql,
)


def args_for_mode(mode):
    return argparse.Namespace(
        mode=mode,
        model=None,
        prompt_version=None,
        tokens_per_sentence=None,
        stop_after=10,
        token_budget=None,
        priority_books_last="4,8",
    )


class SentenceTagBatchTests(unittest.TestCase):
    def test_bucket_from_flags(self):
        self.assertEqual(bucket_from_flags(True, True), "both")
        self.assertEqual(bucket_from_flags(True, False), "mythic")
        self.assertEqual(bucket_from_flags(False, True), "historical")
        self.assertEqual(bucket_from_flags(False, False), "other")

    def test_greta_both_prompt_version_is_separate(self):
        self.assertEqual(
            mode_prompt_version(args_for_mode("greta-both")),
            GRETA_BOTH_BATCH_PROMPT_VERSION,
        )

    def test_greta_both_completion_uses_independent_flags(self):
        body = completion_body(
            args_for_mode("greta-both"),
            {
                "passage_id": "3.1.1",
                "sentence_number": 1,
                "sentence": "test Greek",
                "english_sentence": "test English",
            },
        )
        tool = body["tools"][0]["function"]
        properties = tool["parameters"]["properties"]
        self.assertEqual(tool["name"], "save_greta_both_sentence_tag")
        self.assertIn("references_mythic", properties)
        self.assertIn("references_historical", properties)
        self.assertIn(
            "both mythic and historical",
            body["messages"][0]["content"],
        )

    def test_greta_both_unprocessed_sql_uses_new_table(self):
        sql = unprocessed_sql(args_for_mode("greta-both"))
        self.assertIn("sentence_greta_both_tags", sql)
        self.assertNotIn("FROM sentence_greta_tags t", sql)
        self.assertIn(GRETA_BOTH_BATCH_PROMPT_VERSION, sql)


if __name__ == "__main__":
    unittest.main()
