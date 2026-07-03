import argparse
import json
import unittest

from passage_place_state_batch import (
    completion_body,
    parse_custom_id,
    parse_output_text,
)


def args():
    return argparse.Namespace(model="gpt-5.4-mini")


def batch_record(custom_id, arguments, prompt_tokens=100, completion_tokens=50):
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
    }


class PassagePlaceStateBatchTests(unittest.TestCase):
    def test_completion_body_uses_passage_context_and_candidates(self):
        body = completion_body(
            args(),
            {
                "passage_id": "1.38.9",
                "candidate_summary": "[3] regex_english/ruin: ruins",
                "numbered_sentences": "[3] Greek: x\nEnglish: ruins of houses",
            },
        )

        content = "\n".join(message["content"] for message in body["messages"])
        self.assertIn("whole passage context", content)
        self.assertIn("Candidate hints", content)
        self.assertIn("sentence_number", json.dumps(body["tools"]))
        self.assertEqual(body["temperature"], 0)

    def test_parse_custom_id(self):
        self.assertEqual(parse_custom_id("passageplacestate:run-1:4"), ("run-1", 4))

    def test_parse_output_text_recovers_passage_claims(self):
        run = {
            "run_id": "run-1",
            "prompt_version": "passage-place-state-v1",
            "model": "gpt-5.4-mini",
            "completed_at": "2026-07-03T00:00:00+00:00",
        }
        item_lookup = {1: {"request_number": 1, "passage_id": "1.38.9"}}
        record = batch_record(
            "passageplacestate:run-1:1",
            {
                "has_place_state_claim": True,
                "summary": "Eleutherae has surviving remains.",
                "claims": [
                    {
                        "sentence_number": 3,
                        "exact_place_text": "Eleutherae",
                        "canonical_place_name": "Eleutherae",
                        "place_status": "ruined_or_remains",
                        "temporal_scope": "pausanias_present",
                        "evidence_quote": "ruins of houses",
                        "confidence": "high",
                        "rationale": "The passage says houses are ruins.",
                    }
                ],
            },
        )

        parsed = parse_output_text(json.dumps(record), run=run, item_lookup=item_lookup)

        self.assertEqual(len(parsed.failures), 0)
        self.assertEqual(len(parsed.reviews), 1)
        self.assertEqual(len(parsed.mentions), 1)
        self.assertEqual(parsed.mentions[0]["sentence_number"], 3)
        self.assertEqual(parsed.mentions[0]["target_label"], "does_not_survive")


if __name__ == "__main__":
    unittest.main()
