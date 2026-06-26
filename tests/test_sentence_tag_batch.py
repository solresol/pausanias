import argparse
import unittest

from sentence_tag_batch import (
    DISCOURSE_MODE_PROMPT_VERSION,
    GRETA_BATCH_PROMPT_VERSION,
    GRETA_BOTH_BATCH_PROMPT_VERSION,
    PLACE_STATE_PROMPT_VERSION,
    bucket_from_flags,
    completion_body,
    mode_prompt_version,
    place_state_target_label,
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
        priority_books_first="",
        priority_books_last="4,8",
        random_order=False,
        sample_seed="test-seed",
        grammar_model="gpt-5.4-mini",
        grammar_prompt_version="greek-sentence-grammar-v1",
    )


class SentenceTagBatchTests(unittest.TestCase):
    def test_bucket_from_flags(self):
        self.assertEqual(bucket_from_flags(True, True), "both")
        self.assertEqual(bucket_from_flags(True, False), "mythic")
        self.assertEqual(bucket_from_flags(False, True), "historical")
        self.assertEqual(bucket_from_flags(False, False), "other")

    def test_production_prompt_versions(self):
        self.assertEqual(
            mode_prompt_version(args_for_mode("greta")), GRETA_BATCH_PROMPT_VERSION
        )
        self.assertEqual(
            mode_prompt_version(args_for_mode("greta-both")),
            GRETA_BOTH_BATCH_PROMPT_VERSION,
        )
        self.assertEqual(GRETA_BATCH_PROMPT_VERSION, "original-myth-history-other")
        self.assertEqual(
            GRETA_BOTH_BATCH_PROMPT_VERSION, "greta-inspired-myth-history-other"
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
        # V1 (calibrated) prompt judges each sentence on its own content.
        self.assertIn("two independent flags", body["messages"][0]["content"])
        self.assertEqual(body["temperature"], 0)

    def test_greta_both_completion_is_no_context(self):
        # The greta-both lane must not pull in full-passage context.
        body = completion_body(
            args_for_mode("greta-both"),
            {
                "passage_id": "3.1.1",
                "sentence_number": 1,
                "sentence": "target Greek",
                "english_sentence": "target English",
            },
        )
        content = "\n".join(message["content"] for message in body["messages"])
        self.assertNotIn("full context", content)

    def test_greta_both_unprocessed_sql_uses_new_table(self):
        sql = unprocessed_sql(args_for_mode("greta-both"))
        self.assertIn("sentence_greta_both_tags", sql)
        self.assertNotIn("FROM sentence_greta_tags t", sql)
        self.assertNotIn("sentence_greta_both_context_tags", sql)
        self.assertNotIn("JOIN passages p", sql)
        self.assertIn(GRETA_BOTH_BATCH_PROMPT_VERSION, sql)

    def test_context_mode_is_removed(self):
        with self.assertRaises(SystemExit):
            # argparse would reject the removed choice; mode_prompt_version never
            # sees it, but guard the dispatch too.
            import argparse as _ap

            parser = _ap.ArgumentParser()
            parser.add_argument(
                "--mode",
                choices=("greta", "greta-both", "legacy", "discourse", "place-state"),
            )
            parser.parse_args(["--mode", "greta-both-context"])

    def test_priority_books_first_order_is_before_natural_order(self):
        args = args_for_mode("greta-both")
        args.priority_books_first = "3"
        sql = unprocessed_sql(args)
        self.assertIn("THEN 0 ELSE 1 END", sql)
        self.assertIn("ARRAY['3']", sql)
        self.assertLess(
            sql.index("ARRAY['3']"),
            sql.index("split_part(s.passage_id, '.', 1)::integer"),
        )

    def test_discourse_completion_and_unprocessed_sql_use_grammar_subset(self):
        args = args_for_mode("discourse")
        body = completion_body(
            args,
            {
                "passage_id": "7.1.1",
                "sentence_number": 2,
                "sentence": "Greek",
                "english_sentence": "English",
            },
        )
        tool = body["tools"][0]["function"]
        self.assertEqual(mode_prompt_version(args), DISCOURSE_MODE_PROMPT_VERSION)
        self.assertEqual(tool["name"], "save_discourse_mode_tag")
        self.assertIn("route_locative_description", tool["parameters"]["properties"]["discourse_mode"]["enum"])
        self.assertEqual(body["temperature"], 0)

        sql = unprocessed_sql(args)
        self.assertIn("sentence_llm_grammar_analyses", sql)
        self.assertIn("sentence_discourse_mode_tags", sql)
        self.assertIn("greek-sentence-grammar-v1", sql)

    def test_place_state_completion_and_unprocessed_sql_use_review_table(self):
        args = args_for_mode("place-state")
        body = completion_body(
            args,
            {
                "passage_id": "8.1.1",
                "sentence_number": 1,
                "sentence": "Greek",
                "english_sentence": "English",
            },
        )
        tool = body["tools"][0]["function"]
        self.assertEqual(mode_prompt_version(args), PLACE_STATE_PROMPT_VERSION)
        self.assertEqual(tool["name"], "save_place_state_review")
        self.assertIn("claims", tool["parameters"]["properties"])
        self.assertIn("pausanias_present", str(tool["parameters"]))
        self.assertEqual(body["temperature"], 0)

        sql = unprocessed_sql(args)
        self.assertIn("sentence_place_state_reviews", sql)
        self.assertIn(PLACE_STATE_PROMPT_VERSION, sql)

    def test_place_state_target_label_requires_pausanias_present(self):
        self.assertEqual(
            place_state_target_label("inhabited_still_exists", "pausanias_present"),
            "survives",
        )
        self.assertEqual(
            place_state_target_label("ruined_or_remains", "pausanias_present"),
            "does_not_survive",
        )
        self.assertEqual(
            place_state_target_label("inhabited_still_exists", "mythic_past"),
            "exclude",
        )


if __name__ == "__main__":
    unittest.main()
