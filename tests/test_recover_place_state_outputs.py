import json
import unittest

from recover_place_state_outputs import (
    parse_custom_id,
    parse_output_text,
    place_state_target_label,
)


def batch_record(custom_id, arguments, prompt_tokens=10, completion_tokens=5):
    return {
        "custom_id": custom_id,
        "response": {
            "status_code": 200,
            "body": {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "arguments": json.dumps(arguments),
                                    }
                                }
                            ]
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                },
            },
        },
        "error": None,
    }


class RecoverPlaceStateOutputsTests(unittest.TestCase):
    def test_parse_custom_id(self):
        self.assertEqual(
            parse_custom_id("senttag:place-state:run-1:23"),
            ("place-state", "run-1", 23),
        )

    def test_target_label_depends_on_temporal_scope(self):
        self.assertEqual(
            place_state_target_label("ruined_or_remains", "pausanias_present"),
            "does_not_survive",
        )
        self.assertEqual(
            place_state_target_label("ruined_or_remains", "past_before_pausanias"),
            "exclude",
        )
        self.assertEqual(
            place_state_target_label("extant_uninhabited", "pausanias_present"),
            "survives",
        )

    def test_parse_output_text_recovers_reviews_and_mentions(self):
        run = {
            "run_id": "run-1",
            "prompt_version": "place-state-v1",
            "model": "gpt-5.4-mini",
            "completed_at": "2026-06-28T00:00:00+00:00",
            "retrieved_at": None,
        }
        item_lookup = {
            1: {
                "request_number": 1,
                "passage_id": "1.1.1",
                "sentence_number": 3,
            }
        }
        record = batch_record(
            "senttag:place-state:run-1:1",
            {
                "has_place_state_claim": True,
                "summary": "One deserted island.",
                "claims": [
                    {
                        "exact_place_text": "νῆσος ἔρημος",
                        "canonical_place_name": "Patroclus",
                        "place_status": "abandoned_or_deserted",
                        "temporal_scope": "pausanias_present",
                        "evidence_quote": "νῆσος ἔρημος",
                        "confidence": "high",
                        "rationale": "The island is directly called deserted.",
                    }
                ],
            },
            prompt_tokens=905,
            completion_tokens=154,
        )

        parsed = parse_output_text(json.dumps(record), run=run, item_lookup=item_lookup)

        self.assertEqual(len(parsed.failures), 0)
        self.assertEqual(len(parsed.reviews), 1)
        self.assertEqual(len(parsed.mentions), 1)
        self.assertTrue(parsed.reviews[0]["has_place_state_claim"])
        self.assertEqual(parsed.reviews[0]["input_tokens"], 905)
        self.assertEqual(parsed.mentions[0]["target_label"], "does_not_survive")
        self.assertEqual(parsed.mentions[0]["claim_index"], 1)


if __name__ == "__main__":
    unittest.main()
