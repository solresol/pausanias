import argparse
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from section_people_batch import (
    completion_body,
    fetch_batches,
    parse_batch_error_records,
)


def people_args(model: str) -> argparse.Namespace:
    return argparse.Namespace(model=model)


def people_row() -> dict[str, str]:
    return {
        "passage_id": "1.1.1",
        "numbered_sentences": "[1] Greek: text\nEnglish: text",
    }


def test_gpt_5_6_batch_function_tools_disable_reasoning():
    body = completion_body(people_args("gpt-5.6-luna"), people_row())

    assert body["reasoning_effort"] == "none"


def test_other_batch_models_leave_reasoning_unspecified():
    body = completion_body(people_args("gpt-5.4-mini"), people_row())

    assert "reasoning_effort" not in body


def test_parse_batch_error_records_assigns_messages():
    text = "\n".join(
        [
            json.dumps(
                {
                    "custom_id": "sectpeople:run-1:1",
                    "response": {
                        "status_code": 400,
                        "body": {"error": {"message": "request rejected"}},
                    },
                }
            ),
            json.dumps(
                {
                    "custom_id": "sectpeople:other-run:2",
                    "response": {"status_code": 400},
                }
            ),
        ]
    )

    errors, unassigned = parse_batch_error_records(
        text,
        run_id="run-1",
        item_lookup={1: {"passage_id": "1.1.1"}, 2: {"passage_id": "1.1.2"}},
    )

    assert errors == {1: "request rejected"}
    assert len(unassigned) == 1
    assert "belongs to other-run" in unassigned[0]


@patch("section_people_batch.write_results")
@patch("section_people_batch.load_batch_items")
@patch("section_people_batch.update_batch_ids")
@patch("section_people_batch.load_batch_runs")
@patch("section_people_batch.now_iso", return_value="2026-08-04T00:00:00+00:00")
def test_completed_batch_without_output_finalizes_error_items(
    _now_iso, load_batch_runs, update_batch_ids, load_batch_items, write_results
):
    load_batch_runs.return_value = [
        {
            "run_id": "run-1",
            "openai_batch_id": "batch-1",
            "model": "gpt-5.6-luna",
            "prompt_version": "section-people-v1",
        }
    ]
    load_batch_items.return_value = {
        1: {"passage_id": "1.1.1"},
        2: {"passage_id": "1.1.2"},
    }
    error_text = json.dumps(
        {
            "custom_id": "sectpeople:run-1:1",
            "response": {
                "status_code": 400,
                "body": {"error": {"message": "request rejected"}},
            },
        }
    )
    client = SimpleNamespace(
        batches=SimpleNamespace(
            retrieve=Mock(
                return_value=SimpleNamespace(
                    status="completed",
                    output_file_id=None,
                    error_file_id="error-1",
                )
            )
        ),
        files=SimpleNamespace(
            content=Mock(return_value=SimpleNamespace(text=error_text))
        ),
    )

    fetch_batches(Mock(), client, batch_run_id=None)

    update_batch_ids.assert_called_once()
    payload = write_results.call_args.args[1]
    assert payload["run"]["status"] == "completed_with_failures"
    assert payload["run"]["retrieved_at"] == "2026-08-04T00:00:00+00:00"
    assert payload["items"] == [
        {
            "request_number": 1,
            "input_tokens": 0,
            "output_tokens": 0,
            "status": "failed",
            "error": "request rejected",
        },
        {
            "request_number": 2,
            "input_tokens": 0,
            "output_tokens": 0,
            "status": "failed",
            "error": "Completed batch returned no output record",
        },
    ]
