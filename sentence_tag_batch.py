#!/usr/bin/env python

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shlex
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from pausanias_db import schema_path
from sentence_mythic_sceptic_analyser import LEGACY_PROMPT_VERSION, legacy_tool


GRETA_BATCH_PROMPT_VERSION = "greta-myth-history-other-no-scepticism-v1"
GRETA_BOTH_BATCH_PROMPT_VERSION = "greta-myth-history-both-other-no-scepticism-v1"
DEFAULT_GRETA_MODEL = "gpt-5.4-mini"
DEFAULT_LEGACY_MODEL = "gpt-5"
DEFAULT_GRETA_TOKENS_PER_SENTENCE = 545
DEFAULT_GRETA_BOTH_TOKENS_PER_SENTENCE = 680
DEFAULT_LEGACY_TOKENS_PER_SENTENCE = 540
GRETA_MODES = {"greta", "greta-both"}
TERMINAL_RUN_STATUSES = (
    "completed",
    "completed_with_failures",
    "failed",
    "batch_failed",
    "batch_expired",
    "batch_cancelled",
    "batch_canceled",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def parse_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def load_openai_api_key(key_file: str) -> str:
    with open(os.path.expanduser(key_file), "r", encoding="utf-8") as handle:
        return handle.read().strip()


class PsqlRunner:
    def __init__(self, database_url: str, *, psql_bin: str, ssh_host: str | None):
        self.database_url = database_url
        self.psql_bin = psql_bin
        self.ssh_host = ssh_host

    def command(self) -> list[str]:
        if not self.ssh_host:
            return [
                self.psql_bin,
                self.database_url,
                "-v",
                "ON_ERROR_STOP=1",
                "-P",
                "pager=off",
            ]
        remote = (
            f"{shlex.quote(self.psql_bin)} {shlex.quote(self.database_url)} "
            "-v ON_ERROR_STOP=1 -P pager=off"
        )
        return ["ssh", self.ssh_host, remote]

    def run(self, sql: str) -> str:
        proc = subprocess.run(
            self.command(),
            input=sql,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            raise RuntimeError(f"psql failed with exit code {proc.returncode}")
        return proc.stdout


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit and fetch OpenAI Batch API runs for Pausanias sentence tags."
    )
    parser.add_argument("--database-url", default="dbname=pausanias user=gregb")
    parser.add_argument("--ssh-host", default=None)
    parser.add_argument("--psql-bin", default="psql")
    parser.add_argument("--openai-api-key-file", default="~/.openai.key")
    parser.add_argument("--mode", choices=("greta", "greta-both", "legacy"), default="greta")
    parser.add_argument("--model", default=None)
    parser.add_argument("--prompt-version", default=None)
    parser.add_argument("--token-budget", type=int, default=None)
    parser.add_argument("--stop-after", type=int, default=None)
    parser.add_argument(
        "--tokens-per-sentence",
        type=int,
        default=None,
        help="Planning estimate used before Batch API usage is known.",
    )
    parser.add_argument(
        "--priority-books-last",
        default="4,8",
        help="Comma-separated book numbers to leave until other books are submitted.",
    )
    parser.add_argument("--batch-file", default=None)
    parser.add_argument("--batch-run-id", default=None)
    parser.add_argument("--use-batch-api", action="store_true")
    parser.add_argument("--check-batches", action="store_true")
    parser.add_argument("--fetch-batches", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-if-submitted-hours",
        type=float,
        default=0.0,
        help="Do not submit a new run for this mode if one was submitted recently.",
    )
    return parser.parse_args()


def mode_model(args: argparse.Namespace) -> str:
    if args.model:
        return args.model
    return DEFAULT_GRETA_MODEL if args.mode in GRETA_MODES else DEFAULT_LEGACY_MODEL


def mode_prompt_version(args: argparse.Namespace) -> str:
    if args.prompt_version:
        return args.prompt_version
    if args.mode == "greta":
        return GRETA_BATCH_PROMPT_VERSION
    if args.mode == "greta-both":
        return GRETA_BOTH_BATCH_PROMPT_VERSION
    return LEGACY_PROMPT_VERSION


def mode_tokens_per_sentence(args: argparse.Namespace) -> int:
    if args.tokens_per_sentence:
        return args.tokens_per_sentence
    if args.mode == "greta":
        return DEFAULT_GRETA_TOKENS_PER_SENTENCE
    if args.mode == "greta-both":
        return DEFAULT_GRETA_BOTH_TOKENS_PER_SENTENCE
    return DEFAULT_LEGACY_TOKENS_PER_SENTENCE


def run_mode(args: argparse.Namespace) -> str:
    return f"{args.mode}-batch"


def greta_tool() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "save_greta_sentence_tag",
                "description": "Save Greta's three-bucket Pausanias sentence tag.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "myth_history_bucket": {
                            "type": "string",
                            "enum": ["mythic", "historical", "other"],
                            "description": (
                                "mythic, historical, or other/geographical/descriptive."
                            ),
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "rationale": {
                            "type": "string",
                            "description": "One short reason for the bucket choice.",
                        },
                    },
                    "required": ["myth_history_bucket", "confidence", "rationale"],
                },
            },
        }
    ]


def bucket_from_flags(references_mythic: bool, references_historical: bool) -> str:
    if references_mythic and references_historical:
        return "both"
    if references_mythic:
        return "mythic"
    if references_historical:
        return "historical"
    return "other"


def greta_both_tool() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "save_greta_both_sentence_tag",
                "description": (
                    "Save Greta's Pausanias sentence tag with independent mythic "
                    "and historical flags."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "references_mythic": {
                            "type": "boolean",
                            "description": (
                                "Whether the sentence contains mythic, heroic, "
                                "genealogical, or mythic-landscape material."
                            ),
                        },
                        "references_historical": {
                            "type": "boolean",
                            "description": (
                                "Whether the sentence contains post-500 BCE "
                                "historical, institutional, political, military, "
                                "dedicatory, or biographical material."
                            ),
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "rationale": {
                            "type": "string",
                            "description": "One short reason for the two flag choices.",
                        },
                    },
                    "required": [
                        "references_mythic",
                        "references_historical",
                        "confidence",
                        "rationale",
                    ],
                },
            },
        }
    ]


def greta_completion_body(
    *, model: str, passage_id: str, sentence_number: int, sentence: str, english_sentence: str
) -> dict:
    system_prompt = (
        "Act as a Pausanias scholar. Classify each sentence into exactly one "
        "bucket. Use 'mythic' for mythic events or the impact of mythic events "
        "on the landscape. Use 'historical' for events after roughly 500 BC or "
        "the impact of those historical events on the landscape. Use 'other' "
        "for geographical, route, descriptive, antiquarian, or otherwise "
        "non-mythic/non-historical material that should not be forced into the "
        "historical bucket. Do not classify scepticism."
    )
    user_content = (
        f"Passage {passage_id}, sentence {sentence_number}:\n\n"
        f"Greek:\n{sentence}\n\nEnglish:\n{english_sentence}\n\n"
        "Classify this sentence using the save_greta_sentence_tag function."
    )
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "tools": greta_tool(),
        "tool_choice": {
            "type": "function",
            "function": {"name": "save_greta_sentence_tag"},
        },
    }


def greta_both_completion_body(
    *, model: str, passage_id: str, sentence_number: int, sentence: str, english_sentence: str
) -> dict:
    system_prompt = (
        "Act as a Pausanias scholar. Mark two independent labels for each "
        "sentence: references_mythic and references_historical. A sentence may "
        "be mythic only, historical only, both mythic and historical, or neither. "
        "Set references_mythic true for mythic or heroic events, mythic-era "
        "genealogy, founder legend, heroic/Trojan/Heraclid tradition, oracle-linked "
        "heroic relics, or the impact of mythic events and traditions on cult, "
        "monuments, or landscape. Set references_historical true for events after "
        "roughly 500 BC or their impact on landscape, cult, monuments, institutions, "
        "dedications, athletic or artistic records, courts, politics, war, or "
        "biography. Antiquarian detail can be mythic or historical when it carries "
        "one of those functions; it is not automatically other. Do not classify a "
        "bare mention of a deity, hero, sanctuary, statue, tomb, or route landmark "
        "as mythic unless the sentence links it to a mythic tradition, event, "
        "genealogy, or etiology. Do not classify early legendary or pre-500 Spartan, "
        "Dorian, Heraclid, or heroic king-list material as historical merely because "
        "it describes kings, colonies, or warfare. Set both flags false only for "
        "pure route, geography, object description, or narrative transition with no "
        "mythic or historical function. Do not classify scepticism."
    )
    user_content = (
        f"Passage {passage_id}, sentence {sentence_number}:\n\n"
        f"Greek:\n{sentence}\n\nEnglish:\n{english_sentence}\n\n"
        "Classify this sentence using the save_greta_both_sentence_tag function."
    )
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "tools": greta_both_tool(),
        "tool_choice": {
            "type": "function",
            "function": {"name": "save_greta_both_sentence_tag"},
        },
    }


def legacy_completion_body(
    *, model: str, passage_id: str, sentence_number: int, sentence: str, english_sentence: str
) -> dict:
    system_prompt = (
        "Act as a Pausanias scholar and report whether this sentence of Pausanias is "
        "a reference to the mythic era or historical era. Then report whether "
        "Pausanias shows scepticism about the subject matter he is writing about."
    )
    user_content = (
        f"Passage {passage_id}, sentence {sentence_number}:\n\n"
        f"Greek:\n{sentence}\n\nEnglish:\n{english_sentence}\n\n"
        "Analyse this sentence and provide your results using the save_annotations function."
    )
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "tools": legacy_tool(),
        "tool_choice": {"type": "function", "function": {"name": "save_annotations"}},
    }


def completion_body(args: argparse.Namespace, row: dict) -> dict:
    model = mode_model(args)
    kwargs = {
        "model": model,
        "passage_id": row["passage_id"],
        "sentence_number": int(row["sentence_number"]),
        "sentence": row["sentence"],
        "english_sentence": row["english_sentence"],
    }
    if args.mode == "greta":
        return greta_completion_body(**kwargs)
    if args.mode == "greta-both":
        return greta_both_completion_body(**kwargs)
    return legacy_completion_body(**kwargs)


def custom_id(mode: str, run_id: str, request_number: int) -> str:
    return f"senttag:{mode}:{run_id}:{request_number}"


def parse_custom_id(value: str) -> tuple[str, str, int]:
    parts = str(value).split(":")
    if len(parts) != 4 or parts[0] != "senttag":
        raise ValueError(f"Unexpected custom_id {value!r}")
    return parts[1], parts[2], int(parts[3])


def request_limit(args: argparse.Namespace) -> int | None:
    limits = []
    if args.stop_after is not None:
        limits.append(args.stop_after)
    if args.token_budget is not None:
        limits.append(max(1, args.token_budget // mode_tokens_per_sentence(args)))
    if not limits:
        return None
    return min(limits)


def priority_order_sql(priority_books: list[str]) -> str:
    natural_order = (
        "split_part(s.passage_id, '.', 1)::integer, "
        "split_part(s.passage_id, '.', 2)::integer, "
        "split_part(s.passage_id, '.', 3)::integer, "
        "s.sentence_number"
    )
    if not priority_books:
        return natural_order
    books = ", ".join(sql_string(book) for book in priority_books)
    return (
        f"CASE WHEN split_part(s.passage_id, '.', 1) = ANY(ARRAY[{books}]) "
        f"THEN 1 ELSE 0 END, {natural_order}"
    )


def pending_status_sql() -> str:
    statuses = ", ".join(sql_string(status) for status in TERMINAL_RUN_STATUSES)
    return statuses


def unprocessed_sql(args: argparse.Namespace) -> str:
    mode = run_mode(args)
    prompt_version = mode_prompt_version(args)
    limit = request_limit(args)
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    order_by = priority_order_sql(parse_list(args.priority_books_last))
    terminal_statuses = pending_status_sql()
    pending_clause = f"""
      AND NOT EXISTS (
          SELECT 1
          FROM sentence_tagging_batch_items bi
          JOIN sentence_tagging_runs r ON r.run_id = bi.run_id
          WHERE bi.passage_id = s.passage_id
            AND bi.sentence_number = s.sentence_number
            AND bi.mode = {sql_string(mode)}
            AND bi.prompt_version = {sql_string(prompt_version)}
            AND r.status NOT IN ({terminal_statuses})
      )
"""
    if args.mode == "greta":
        work_clause = f"""
      AND NOT EXISTS (
          SELECT 1
          FROM sentence_greta_tags t
          WHERE t.passage_id = s.passage_id
            AND t.sentence_number = s.sentence_number
            AND t.prompt_version = {sql_string(prompt_version)}
      )
"""
    elif args.mode == "greta-both":
        work_clause = f"""
      AND NOT EXISTS (
          SELECT 1
          FROM sentence_greta_both_tags t
          WHERE t.passage_id = s.passage_id
            AND t.sentence_number = s.sentence_number
            AND t.prompt_version = {sql_string(prompt_version)}
      )
"""
    else:
        work_clause = "      AND s.references_mythic_era IS NULL\n"
    return f"""
COPY (
    SELECT s.passage_id, s.sentence_number, s.sentence, s.english_sentence
    FROM greek_sentences s
    WHERE TRUE
{work_clause}
{pending_clause}
    ORDER BY {order_by}
    {limit_clause}
) TO STDOUT WITH CSV HEADER;
"""


def load_unprocessed_rows(psql: PsqlRunner, args: argparse.Namespace) -> list[dict]:
    raw = psql.run(unprocessed_sql(args))
    rows = list(csv.DictReader(io.StringIO(raw)))
    for row in rows:
        row["sentence_number"] = int(row["sentence_number"])
    return rows


def recent_submission(psql: PsqlRunner, args: argparse.Namespace) -> dict | None:
    if args.skip_if_submitted_hours <= 0:
        return None
    raw = psql.run(
        f"""
COPY (
    SELECT run_id, submitted_at, status, request_count
    FROM sentence_tagging_runs
    WHERE mode = {sql_string(run_mode(args))}
      AND prompt_version = {sql_string(mode_prompt_version(args))}
      AND api_mode = 'batch'
      AND submitted_at IS NOT NULL
      AND submitted_at::timestamptz >= (
          now() - ({float(args.skip_if_submitted_hours)} || ' hours')::interval
      )
    ORDER BY submitted_at DESC
    LIMIT 1
) TO STDOUT WITH CSV HEADER;
"""
    )
    rows = list(csv.DictReader(io.StringIO(raw)))
    return rows[0] if rows else None


def validate_batch_file(path: Path) -> None:
    problems = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                problems.append(f"line {line_number}: invalid JSON ({exc})")
                continue
            if payload.get("method") != "POST":
                problems.append(f"line {line_number}: expected method POST")
            if payload.get("url") != "/v1/chat/completions":
                problems.append(f"line {line_number}: unexpected url {payload.get('url')!r}")
            if not str(payload.get("custom_id", "")).startswith("senttag:"):
                problems.append(f"line {line_number}: unexpected custom_id")
    if problems:
        raise ValueError("Invalid sentence batch request file:\n" + "\n".join(problems))


def write_submission(psql: PsqlRunner, payload: dict) -> None:
    tag = f"json_{payload['run']['run_id'].replace('-', '_')}"
    payload_json = json.dumps(payload, ensure_ascii=False)
    sql = f"""
WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS j
), run_row AS (
    SELECT j->'run' AS r FROM payload
)
INSERT INTO sentence_tagging_runs (
    run_id, started_at, completed_at, mode, model, prompt_version, status,
    token_budget, input_tokens, output_tokens, processed_count, discrepancy_count,
    api_mode, request_count, notes
)
SELECT
    r->>'run_id',
    r->>'started_at',
    NULLIF(r->>'completed_at', ''),
    r->>'mode',
    r->>'model',
    r->>'prompt_version',
    r->>'status',
    (r->>'token_budget')::integer,
    0,
    0,
    0,
    0,
    'batch',
    (r->>'request_count')::integer,
    r->>'notes'
FROM run_row
ON CONFLICT (run_id) DO UPDATE
SET status = EXCLUDED.status,
    token_budget = EXCLUDED.token_budget,
    api_mode = 'batch',
    request_count = EXCLUDED.request_count,
    notes = EXCLUDED.notes;

WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS j
)
INSERT INTO sentence_tagging_batch_items (
    run_id, request_number, mode, prompt_version, passage_id, sentence_number,
    estimated_tokens, input_tokens, output_tokens, status, error, created_at
)
SELECT
    j->'run'->>'run_id',
    x.request_number,
    j->'run'->>'mode',
    j->'run'->>'prompt_version',
    x.passage_id,
    x.sentence_number,
    x.estimated_tokens,
    0,
    0,
    'submitted',
    NULL,
    j->'run'->>'started_at'
FROM payload,
     jsonb_to_recordset(j->'items') AS x(
        request_number integer,
        passage_id text,
        sentence_number integer,
        estimated_tokens integer
     )
ON CONFLICT (run_id, request_number) DO UPDATE
SET passage_id = EXCLUDED.passage_id,
    sentence_number = EXCLUDED.sentence_number,
    estimated_tokens = EXCLUDED.estimated_tokens,
    status = EXCLUDED.status,
    error = NULL;
"""
    psql.run(sql)


def update_batch_ids(
    psql: PsqlRunner,
    *,
    run_id: str,
    openai_batch_id: str | None = None,
    openai_input_file_id: str | None = None,
    openai_output_file_id: str | None = None,
    openai_error_file_id: str | None = None,
    status: str | None = None,
    submitted_at: str | None = None,
    retrieved_at: str | None = None,
    completed_at: str | None = None,
) -> None:
    assignments = []
    for column, value in (
        ("openai_batch_id", openai_batch_id),
        ("openai_input_file_id", openai_input_file_id),
        ("openai_output_file_id", openai_output_file_id),
        ("openai_error_file_id", openai_error_file_id),
        ("status", status),
        ("submitted_at", submitted_at),
        ("retrieved_at", retrieved_at),
        ("completed_at", completed_at),
    ):
        if value is not None:
            assignments.append(f"{column} = {sql_string(value)}")
    if not assignments:
        return
    psql.run(
        f"""
UPDATE sentence_tagging_runs
SET {", ".join(assignments)}
WHERE run_id = {sql_string(run_id)};
"""
    )


def submit_batch(psql: PsqlRunner, client: OpenAI, args: argparse.Namespace) -> None:
    recent = recent_submission(psql, args)
    if recent:
        print(
            f"Skipping {run_mode(args)} submission: recent run {recent['run_id']} "
            f"submitted at {recent['submitted_at']} with {recent['request_count']} requests."
        )
        return

    rows = load_unprocessed_rows(psql, args)
    if not rows:
        print(f"No unsubmitted {run_mode(args)} rows found.")
        return

    run_id = str(uuid.uuid4())
    started_at = now_iso()
    model = mode_model(args)
    prompt_version = mode_prompt_version(args)
    batch_file = (
        Path(args.batch_file)
        if args.batch_file
        else Path("tmp") / f"sentence-tag-{args.mode}-batch-{run_id}.jsonl"
    )
    batch_file.parent.mkdir(parents=True, exist_ok=True)
    estimated_tokens = mode_tokens_per_sentence(args)

    items = []
    with batch_file.open("w", encoding="utf-8") as handle:
        for request_number, row in enumerate(rows, start=1):
            items.append(
                {
                    "request_number": request_number,
                    "passage_id": row["passage_id"],
                    "sentence_number": int(row["sentence_number"]),
                    "estimated_tokens": estimated_tokens,
                }
            )
            request = {
                "custom_id": custom_id(args.mode, run_id, request_number),
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": completion_body(args, row),
            }
            handle.write(json.dumps(request, ensure_ascii=False) + "\n")
    validate_batch_file(batch_file)

    payload = {
        "run": {
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": "",
            "mode": run_mode(args),
            "model": model,
            "prompt_version": prompt_version,
            "status": "batch_prepared" if args.dry_run else "batch_submitting",
            "token_budget": args.token_budget,
            "request_count": len(items),
            "notes": (
                f"priority_books_last={args.priority_books_last}; "
                f"tokens_per_sentence_estimate={estimated_tokens}; "
                f"batch_file={batch_file}"
            ),
        },
        "items": items,
    }
    if args.dry_run:
        print(
            f"Dry run {run_id}: wrote {len(items)} {run_mode(args)} requests to {batch_file}."
        )
        return

    write_submission(psql, payload)
    with batch_file.open("rb") as handle:
        batch_input_file = client.files.create(file=handle, purpose="batch")
    result = client.batches.create(
        input_file_id=batch_input_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": f"pausanias sentence {run_mode(args)} {run_id}",
            "local_run_id": run_id,
            "mode": run_mode(args),
            "prompt_version": prompt_version,
        },
    )
    submitted_at = now_iso()
    update_batch_ids(
        psql,
        run_id=run_id,
        openai_batch_id=result.id,
        openai_input_file_id=batch_input_file.id,
        status="batch_submitted",
        submitted_at=submitted_at,
    )
    print(
        f"Submitted {run_mode(args)} run {run_id}: {len(items)} requests, "
        f"estimated {len(items) * estimated_tokens} tokens."
    )
    print(f"OpenAI batch id: {result.id}")
    print(f"Batch request file: {batch_file}")


def load_batch_runs(psql: PsqlRunner, batch_run_id: str | None) -> list[dict]:
    run_filter = ""
    if batch_run_id:
        run_filter = f"AND run_id = {sql_string(batch_run_id)}"
    raw = psql.run(
        f"""
COPY (
    SELECT run_id, mode, prompt_version, model, openai_batch_id
    FROM sentence_tagging_runs
    WHERE api_mode = 'batch'
      AND mode IN ('greta-batch', 'greta-both-batch', 'legacy-batch')
      AND openai_batch_id IS NOT NULL
      AND retrieved_at IS NULL
      {run_filter}
    ORDER BY started_at
) TO STDOUT WITH CSV HEADER;
"""
    )
    return list(csv.DictReader(io.StringIO(raw)))


def load_batch_items(psql: PsqlRunner, run_id: str) -> dict[int, dict]:
    raw = psql.run(
        f"""
COPY (
    SELECT request_number, mode, prompt_version, passage_id, sentence_number
    FROM sentence_tagging_batch_items
    WHERE run_id = {sql_string(run_id)}
    ORDER BY request_number
) TO STDOUT WITH CSV HEADER;
"""
    )
    rows = {}
    for row in csv.DictReader(io.StringIO(raw)):
        row["request_number"] = int(row["request_number"])
        row["sentence_number"] = int(row["sentence_number"])
        rows[row["request_number"]] = row
    return rows


def extract_tool_arguments(record: dict) -> tuple[dict, dict]:
    response = record.get("response") or {}
    if response.get("status_code") != 200:
        body = response.get("body") or {}
        error = body.get("error") if isinstance(body, dict) else None
        message = error.get("message") if isinstance(error, dict) else response
        raise ValueError(f"Batch record status {response.get('status_code')}: {message}")
    body = response.get("body") or {}
    choices = body.get("choices") or []
    if not choices:
        raise ValueError("Batch record has no choices")
    message = choices[0].get("message") or {}
    tool_calls = message.get("tool_calls") or []
    if not tool_calls:
        raise ValueError("Batch record has no tool call")
    arguments_text = tool_calls[0].get("function", {}).get("arguments")
    if not arguments_text:
        raise ValueError("Batch record has no tool arguments")
    return json.loads(arguments_text), body.get("usage") or {}


def request_counts_text(result) -> str:
    counts = getattr(result, "request_counts", None)
    if not counts:
        return "no request counts yet"
    return (
        f"{getattr(counts, 'completed', 0)}/{getattr(counts, 'total', 0)} complete, "
        f"{getattr(counts, 'failed', 0)} failed"
    )


def check_batches(psql: PsqlRunner, client: OpenAI, batch_run_id: str | None) -> None:
    runs = load_batch_runs(psql, batch_run_id)
    if not runs:
        print("No unretrieved sentence-tagging Batch API runs found.")
        return
    for run in runs:
        result = client.batches.retrieve(run["openai_batch_id"])
        status = f"batch_{result.status}"
        update_batch_ids(
            psql,
            run_id=run["run_id"],
            status=status,
            openai_output_file_id=result.output_file_id,
            openai_error_file_id=result.error_file_id,
        )
        print(
            f"{run['run_id']} {run['openai_batch_id']}: "
            f"{result.status} ({request_counts_text(result)})"
        )


def write_results(psql: PsqlRunner, payload: dict) -> None:
    tag = f"json_{payload['run']['run_id'].replace('-', '_')}"
    payload_json = json.dumps(payload, ensure_ascii=False)
    sql = f"""
WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS j
), item_rows AS (
    SELECT x.*
    FROM payload,
         jsonb_to_recordset(j->'items') AS x(
            request_number integer,
            input_tokens integer,
            output_tokens integer,
            status text,
            error text
         )
)
UPDATE sentence_tagging_batch_items bi
SET input_tokens = item_rows.input_tokens,
    output_tokens = item_rows.output_tokens,
    status = item_rows.status,
    error = item_rows.error
FROM item_rows, payload
WHERE bi.run_id = j->'run'->>'run_id'
  AND bi.request_number = item_rows.request_number;

WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS j
)
INSERT INTO sentence_greta_tags (
    passage_id, sentence_number, prompt_version, model, myth_history_bucket,
    expresses_scepticism, confidence, rationale, input_tokens, output_tokens,
    run_id, created_at
)
SELECT
    x.passage_id,
    x.sentence_number,
    j->'run'->>'prompt_version',
    j->'run'->>'model',
    x.myth_history_bucket,
    FALSE,
    x.confidence,
    x.rationale,
    x.input_tokens,
    x.output_tokens,
    j->'run'->>'run_id',
    j->'run'->>'completed_at'
FROM payload,
     jsonb_to_recordset(j->'greta_tags') AS x(
        passage_id text,
        sentence_number integer,
        myth_history_bucket text,
        confidence text,
        rationale text,
        input_tokens integer,
        output_tokens integer
     )
ON CONFLICT (passage_id, sentence_number, prompt_version) DO UPDATE
SET model = EXCLUDED.model,
    myth_history_bucket = EXCLUDED.myth_history_bucket,
    expresses_scepticism = EXCLUDED.expresses_scepticism,
    confidence = EXCLUDED.confidence,
    rationale = EXCLUDED.rationale,
    input_tokens = EXCLUDED.input_tokens,
    output_tokens = EXCLUDED.output_tokens,
    run_id = EXCLUDED.run_id,
    created_at = EXCLUDED.created_at;

WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS j
)
INSERT INTO sentence_greta_both_tags (
    passage_id, sentence_number, prompt_version, model, references_mythic,
    references_historical, myth_history_bucket, confidence, rationale,
    input_tokens, output_tokens, run_id, created_at
)
SELECT
    x.passage_id,
    x.sentence_number,
    j->'run'->>'prompt_version',
    j->'run'->>'model',
    x.references_mythic,
    x.references_historical,
    x.myth_history_bucket,
    x.confidence,
    x.rationale,
    x.input_tokens,
    x.output_tokens,
    j->'run'->>'run_id',
    j->'run'->>'completed_at'
FROM payload,
     jsonb_to_recordset(j->'greta_both_tags') AS x(
        passage_id text,
        sentence_number integer,
        references_mythic boolean,
        references_historical boolean,
        myth_history_bucket text,
        confidence text,
        rationale text,
        input_tokens integer,
        output_tokens integer
     )
ON CONFLICT (passage_id, sentence_number, prompt_version) DO UPDATE
SET model = EXCLUDED.model,
    references_mythic = EXCLUDED.references_mythic,
    references_historical = EXCLUDED.references_historical,
    myth_history_bucket = EXCLUDED.myth_history_bucket,
    confidence = EXCLUDED.confidence,
    rationale = EXCLUDED.rationale,
    input_tokens = EXCLUDED.input_tokens,
    output_tokens = EXCLUDED.output_tokens,
    run_id = EXCLUDED.run_id,
    created_at = EXCLUDED.created_at;

WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS j
), legacy_rows AS (
    SELECT x.*
    FROM payload,
         jsonb_to_recordset(j->'legacy_tags') AS x(
            passage_id text,
            sentence_number integer,
            references_mythic_era boolean,
            expresses_scepticism boolean
         )
)
UPDATE greek_sentences s
SET references_mythic_era = legacy_rows.references_mythic_era,
    expresses_scepticism = legacy_rows.expresses_scepticism
FROM legacy_rows
WHERE s.passage_id = legacy_rows.passage_id
  AND s.sentence_number = legacy_rows.sentence_number;

WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS j
), run_row AS (
    SELECT j->'run' AS r FROM payload
)
UPDATE sentence_tagging_runs
SET completed_at = r->>'completed_at',
    status = r->>'status',
    input_tokens = (r->>'input_tokens')::integer,
    output_tokens = (r->>'output_tokens')::integer,
    processed_count = (r->>'processed_count')::integer,
    api_mode = 'batch',
    request_count = (r->>'request_count')::integer,
    openai_output_file_id = r->>'openai_output_file_id',
    openai_error_file_id = r->>'openai_error_file_id',
    retrieved_at = r->>'retrieved_at',
    notes = r->>'notes'
FROM run_row
WHERE sentence_tagging_runs.run_id = r->>'run_id';
"""
    psql.run(sql)


def fetch_batches(
    psql: PsqlRunner,
    client: OpenAI,
    *,
    batch_run_id: str | None,
) -> None:
    runs = load_batch_runs(psql, batch_run_id)
    if not runs:
        print("No unretrieved sentence-tagging Batch API runs found.")
        return
    for run in runs:
        run_id = run["run_id"]
        result = client.batches.retrieve(run["openai_batch_id"])
        update_batch_ids(
            psql,
            run_id=run_id,
            status=f"batch_{result.status}",
            openai_output_file_id=result.output_file_id,
            openai_error_file_id=result.error_file_id,
        )
        if result.status != "completed":
            print(f"{run_id}: remote status is {result.status}; not fetching yet.")
            continue
        if not result.output_file_id:
            print(f"{run_id}: completed but has no output file.")
            continue

        item_lookup = load_batch_items(psql, run_id)
        output = client.files.content(result.output_file_id)
        item_updates = []
        greta_tags = []
        greta_both_tags = []
        legacy_tags = []
        failures = []
        seen_requests = set()

        for line in output.text.splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            request_number = None
            try:
                output_mode, output_run_id, request_number = parse_custom_id(
                    record.get("custom_id", "")
                )
                if output_run_id != run_id:
                    raise ValueError(
                        f"Output custom_id belongs to {output_run_id}, expected {run_id}"
                    )
                source = item_lookup.get(request_number)
                if not source:
                    raise ValueError(f"No stored input row for request {request_number}")
                args, usage = extract_tool_arguments(record)
                input_tokens = int(usage.get("prompt_tokens", 0))
                output_tokens = int(usage.get("completion_tokens", 0))
                if output_mode == "greta":
                    bucket = args.get("myth_history_bucket")
                    if bucket not in {"mythic", "historical", "other"}:
                        raise ValueError(f"Invalid Greta bucket: {bucket}")
                    greta_tags.append(
                        {
                            "passage_id": source["passage_id"],
                            "sentence_number": source["sentence_number"],
                            "myth_history_bucket": bucket,
                            "confidence": args.get("confidence") or "low",
                            "rationale": args.get("rationale") or "",
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        }
                    )
                elif output_mode == "greta-both":
                    references_mythic = bool(args.get("references_mythic"))
                    references_historical = bool(args.get("references_historical"))
                    greta_both_tags.append(
                        {
                            "passage_id": source["passage_id"],
                            "sentence_number": source["sentence_number"],
                            "references_mythic": references_mythic,
                            "references_historical": references_historical,
                            "myth_history_bucket": bucket_from_flags(
                                references_mythic, references_historical
                            ),
                            "confidence": args.get("confidence") or "low",
                            "rationale": args.get("rationale") or "",
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        }
                    )
                elif output_mode == "legacy":
                    legacy_tags.append(
                        {
                            "passage_id": source["passage_id"],
                            "sentence_number": source["sentence_number"],
                            "references_mythic_era": bool(args["references_mythic_era"]),
                            "expresses_scepticism": bool(args["expresses_scepticism"]),
                        }
                    )
                else:
                    raise ValueError(f"Unexpected mode in custom_id: {output_mode}")
                item_updates.append(
                    {
                        "request_number": request_number,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "status": "completed",
                        "error": None,
                    }
                )
                seen_requests.add(request_number)
            except Exception as exc:
                if request_number is not None:
                    item_updates.append(
                        {
                            "request_number": request_number,
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "status": "failed",
                            "error": str(exc),
                        }
                    )
                failures.append(
                    {
                        "custom_id": record.get("custom_id"),
                        "error": str(exc),
                    }
                )

        for request_number in sorted(set(item_lookup) - seen_requests):
            item_updates.append(
                {
                    "request_number": request_number,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "status": "failed",
                    "error": "No output record returned for request",
                }
            )
            failures.append(
                {
                    "custom_id": custom_id(run["mode"].replace("-batch", ""), run_id, request_number),
                    "error": "No output record returned for request",
                }
            )

        completed_at = now_iso()
        input_tokens = sum(item["input_tokens"] for item in item_updates)
        output_tokens = sum(item["output_tokens"] for item in item_updates)
        processed_count = len(greta_tags) + len(greta_both_tags) + len(legacy_tags)
        status = "completed" if not failures else "completed_with_failures"
        notes = f"failures={len(failures)}; fetched_from_batch={run['openai_batch_id']}"
        payload = {
            "run": {
                "run_id": run_id,
                "completed_at": completed_at,
                "status": status,
                "model": run["model"],
                "prompt_version": run["prompt_version"],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "processed_count": processed_count,
                "request_count": len(item_lookup),
                "openai_output_file_id": result.output_file_id,
                "openai_error_file_id": result.error_file_id,
                "retrieved_at": completed_at,
                "notes": notes,
            },
            "items": item_updates,
            "greta_tags": greta_tags,
            "greta_both_tags": greta_both_tags,
            "legacy_tags": legacy_tags,
        }
        write_results(psql, payload)
        print(
            f"Fetched {run['mode']} run {run_id}: {processed_count}/{len(item_lookup)} "
            f"saved, {input_tokens + output_tokens} tokens, {len(failures)} failures."
        )


def main() -> None:
    args = parse_arguments()
    psql = PsqlRunner(args.database_url, psql_bin=args.psql_bin, ssh_host=args.ssh_host)
    psql.run(schema_path().read_text(encoding="utf-8"))
    client = OpenAI(api_key=load_openai_api_key(args.openai_api_key_file))
    if args.check_batches:
        check_batches(psql, client, args.batch_run_id)
        return
    if args.fetch_batches:
        fetch_batches(psql, client, batch_run_id=args.batch_run_id)
        return
    if args.use_batch_api:
        submit_batch(psql, client, args)
        return
    raise SystemExit("Specify --use-batch-api, --check-batches, or --fetch-batches.")


if __name__ == "__main__":
    main()
