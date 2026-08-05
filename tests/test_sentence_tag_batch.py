import argparse
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sentence_tag_batch import (
    DISCOURSE_MODE_PROMPT_VERSION,
    GRETA_BATCH_PROMPT_VERSION,
    GRETA_BOTH_BATCH_PROMPT_VERSION,
    bucket_from_flags,
    completion_body,
    fetch_batches,
    mode_prompt_version,
    parse_batch_error_records,
    unprocessed_sql,
)
from section_people_batch import fetch_batches as fetch_people_batches


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
                choices=("greta", "greta-both", "legacy", "discourse"),
            )
            parser.parse_args(["--mode", "greta-both-context"])

    def test_place_state_mode_is_removed(self):
        import argparse as _ap

        parser = _ap.ArgumentParser()
        parser.add_argument(
            "--mode",
            choices=("greta", "greta-both", "legacy", "discourse"),
        )
        with self.assertRaises(SystemExit):
            parser.parse_args(["--mode", "place-state"])

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
        self.assertEqual(body["reasoning_effort"], "none")

        sql = unprocessed_sql(args)
        self.assertIn("sentence_llm_grammar_analyses", sql)
        self.assertIn("sentence_discourse_mode_tags", sql)
        self.assertIn("greek-sentence-grammar-v1", sql)

    def test_other_batch_models_leave_reasoning_unspecified(self):
        args = args_for_mode("discourse")
        args.model = "gpt-5.4-mini"
        body = completion_body(
            args,
            {
                "passage_id": "7.1.1",
                "sentence_number": 2,
                "sentence": "Greek",
                "english_sentence": "English",
            },
        )

        self.assertNotIn("reasoning_effort", body)

    def test_parse_batch_error_records_preserves_request_errors(self):
        text = "\n".join(
            [
                '{"custom_id":"senttag:discourse:run-1:1","response":'
                '{"status_code":400,"body":{"error":{"message":"invalid prompt"}}}}',
                '{"custom_id":"senttag:discourse:run-1:2","response":'
                '{"status_code":429,"body":{"error":{"message":"rate limited"}}}}',
            ]
        )

        errors, unassigned = parse_batch_error_records(
            text,
            run_id="run-1",
            item_lookup={1: {}, 2: {}},
        )

        self.assertEqual(errors, {1: "invalid prompt", 2: "rate limited"})
        self.assertEqual(unassigned, [])

    def test_parse_batch_error_records_reports_unmatched_records(self):
        errors, unassigned = parse_batch_error_records(
            '{"custom_id":"senttag:discourse:other-run:1","error":"failed"}',
            run_id="run-1",
            item_lookup={1: {}},
        )

        self.assertEqual(errors, {})
        self.assertEqual(len(unassigned), 1)
        self.assertIn("belongs to other-run", unassigned[0])

    @patch("sentence_tag_batch.update_batch_ids")
    @patch("sentence_tag_batch.load_batch_runs")
    @patch("sentence_tag_batch.now_iso", return_value="2026-07-31T00:00:00+00:00")
    def test_expired_sentence_batch_is_finalized(
        self, _now_iso, load_batch_runs, update_batch_ids
    ):
        load_batch_runs.return_value = [
            {
                "run_id": "run-1",
                "openai_batch_id": "batch-1",
                "mode": "discourse-batch",
                "model": "model",
                "prompt_version": "prompt",
            }
        ]
        client = SimpleNamespace(
            batches=SimpleNamespace(
                retrieve=Mock(
                    return_value=SimpleNamespace(
                        status="expired",
                        output_file_id=None,
                        error_file_id="error-1",
                    )
                )
            )
        )

        fetch_batches(Mock(), client, batch_run_id=None)

        update_batch_ids.assert_called_once_with(
            unittest.mock.ANY,
            run_id="run-1",
            status="batch_expired",
            openai_output_file_id=None,
            openai_error_file_id="error-1",
            retrieved_at="2026-07-31T00:00:00+00:00",
            completed_at="2026-07-31T00:00:00+00:00",
        )

    @patch("section_people_batch.update_batch_ids")
    @patch("section_people_batch.load_batch_runs")
    @patch("section_people_batch.now_iso", return_value="2026-07-31T00:00:00+00:00")
    def test_expired_people_batch_is_finalized(
        self, _now_iso, load_batch_runs, update_batch_ids
    ):
        load_batch_runs.return_value = [
            {
                "run_id": "run-1",
                "openai_batch_id": "batch-1",
                "model": "model",
                "prompt_version": "prompt",
            }
        ]
        client = SimpleNamespace(
            batches=SimpleNamespace(
                retrieve=Mock(
                    return_value=SimpleNamespace(
                        status="expired",
                        output_file_id=None,
                        error_file_id=None,
                    )
                )
            )
        )

        fetch_people_batches(Mock(), client, batch_run_id=None)

        update_batch_ids.assert_called_once_with(
            unittest.mock.ANY,
            run_id="run-1",
            status="batch_expired",
            openai_output_file_id=None,
            openai_error_file_id=None,
            retrieved_at="2026-07-31T00:00:00+00:00",
            completed_at="2026-07-31T00:00:00+00:00",
        )


if __name__ == "__main__":
    unittest.main()
