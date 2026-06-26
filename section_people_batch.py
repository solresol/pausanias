#!/usr/bin/env python

from __future__ import annotations

import argparse
import csv
import io
import itertools
import json
import math
import os
import shlex
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from openai import OpenAI
from scipy.stats import chi2_contingency

from pausanias_db import schema_path


DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_PROMPT_VERSION = "section-people-v1"
DEFAULT_BUCKET_PROMPT_VERSION = "original-myth-history-other"
DEFAULT_TOKENS_PER_SECTION = 2500
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
    return "'" + postgres_text(value).replace("'", "''") + "'"


def postgres_text(value: Any) -> str:
    return str(value).replace("\x00", "")


def sql_nullable_text(value: Any) -> str:
    if value is None:
        return "NULL"
    return sql_string(postgres_text(value))


def sql_integer(value: Any) -> str:
    return str(int(value or 0))


def sql_bool(value: Any) -> str:
    return "TRUE" if bool(value) else "FALSE"


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
        description=(
            "Submit and fetch Batch API runs that extract named and anonymous "
            "people from numbered Pausanias sections."
        )
    )
    parser.add_argument("--database-url", default="dbname=pausanias user=gregb")
    parser.add_argument("--ssh-host", default=None)
    parser.add_argument("--psql-bin", default="psql")
    parser.add_argument("--openai-api-key-file", default="~/.openai.key")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION)
    parser.add_argument("--token-budget", type=int, default=100_000)
    parser.add_argument("--tokens-per-section", type=int, default=DEFAULT_TOKENS_PER_SECTION)
    parser.add_argument("--stop-after", type=int, default=None)
    parser.add_argument("--random-seed", default=DEFAULT_PROMPT_VERSION)
    parser.add_argument("--batch-file", default=None)
    parser.add_argument("--batch-run-id", default=None)
    parser.add_argument("--use-batch-api", action="store_true")
    parser.add_argument("--check-batches", action="store_true")
    parser.add_argument("--fetch-batches", action="store_true")
    parser.add_argument("--report-stats", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-if-submitted-hours",
        type=float,
        default=0.0,
        help="Skip submission if this prompt version was submitted recently.",
    )
    parser.add_argument(
        "--bucket-prompt-version",
        default=DEFAULT_BUCKET_PROMPT_VERSION,
        help="sentence_greta_tags prompt version to use for mythic/historical/other stats.",
    )
    return parser.parse_args()


def people_tool() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "save_section_people_mentions",
                "description": (
                    "Save all named and anonymous people mentioned in a numbered "
                    "Pausanias section."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "people": {
                            "type": "array",
                            "description": (
                                "One row per distinct person reference in a numbered sentence."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "sentence_number": {
                                        "type": "integer",
                                        "description": "The numbered sentence containing the reference.",
                                    },
                                    "mention_text": {
                                        "type": "string",
                                        "description": (
                                            "The name or short phrase identifying the person."
                                        ),
                                    },
                                    "canonical_name": {
                                        "type": "string",
                                        "description": (
                                            "A canonical name for named people; empty string for anonymous people."
                                        ),
                                    },
                                    "is_named": {
                                        "type": "boolean",
                                        "description": "True if the person is named by a proper name or individual epithet.",
                                    },
                                    "gender": {
                                        "type": "string",
                                        "enum": ["male", "female", "unknown"],
                                    },
                                    "person_category": {
                                        "type": "string",
                                        "enum": [
                                            "human",
                                            "hero",
                                            "deity",
                                            "mythic_person",
                                            "collective",
                                            "uncertain",
                                        ],
                                    },
                                    "count_kind": {
                                        "type": "string",
                                        "enum": [
                                            "individual",
                                            "group_exact",
                                            "group_uncounted",
                                        ],
                                        "description": (
                                            "Use individual for one person, group_exact when an exact number is recoverable, "
                                            "and group_uncounted when the group size is not recoverable."
                                        ),
                                    },
                                    "person_count": {
                                        "type": "integer",
                                        "description": (
                                            "1 for individual rows, exact group count for group_exact, 0 for group_uncounted."
                                        ),
                                    },
                                    "confidence": {
                                        "type": "string",
                                        "enum": ["high", "medium", "low"],
                                    },
                                    "rationale": {
                                        "type": "string",
                                        "description": "Short reason for inclusion and gender decision.",
                                    },
                                },
                                "required": [
                                    "sentence_number",
                                    "mention_text",
                                    "canonical_name",
                                    "is_named",
                                    "gender",
                                    "person_category",
                                    "count_kind",
                                    "person_count",
                                    "confidence",
                                    "rationale",
                                ],
                            },
                        }
                    },
                    "required": ["people"],
                },
            },
        }
    ]


def completion_body(args: argparse.Namespace, row: dict[str, str]) -> dict[str, Any]:
    system_prompt = (
        "You are a Classical Greek prosopography assistant working passage by passage "
        "through Pausanias. You will receive one Pausanias section with all of its "
        "sentences numbered. Use the Greek and the English translation together.\n\n"
        "Task: list all individual people mentioned in the section, named or anonymous, "
        "and identify the sentence number where each reference occurs.\n\n"
        "Include named humans, heroes, mythic persons, and deities when they are referred "
        "to as individual persons. Include anonymous countable people or gendered groups "
        "such as a wife, mother, daughter, maiden, king, priestess, two brothers, or women "
        "when gender is identifiable. If an anonymous group's exact size is not recoverable, "
        "use count_kind=group_uncounted and person_count=0.\n\n"
        "Do not count places, ethnic or political collectives, peoples, armies, institutions, "
        "festivals, offices, artifacts, animals, or generic mankind. Do not treat a grammatically "
        "masculine people-name such as Athenians, Messenians, Lacedaemonians, Greeks, Rhodians, "
        "or Egyptians as male people. Do not count pronouns by themselves. If the same person is "
        "named or described repeatedly inside one sentence, return one row for that sentence.\n\n"
        "Gender should be male/female only when the name, kinship term, role, morphology, or "
        "secure classical identity supports it; otherwise use unknown. Keep rationales short."
    )
    user_content = (
        f"Passage {row['passage_id']}\n\n"
        f"{row['numbered_sentences']}\n\n"
        "Extract people using the save_section_people_mentions function."
    )
    return {
        "model": args.model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "tools": people_tool(),
        "tool_choice": {
            "type": "function",
            "function": {"name": "save_section_people_mentions"},
        },
    }


def custom_id(run_id: str, request_number: int) -> str:
    return f"sectpeople:{run_id}:{request_number}"


def parse_custom_id(value: str) -> tuple[str, int]:
    parts = str(value).split(":")
    if len(parts) != 3 or parts[0] != "sectpeople":
        raise ValueError(f"Unexpected custom_id {value!r}")
    return parts[1], int(parts[2])


def request_limit(args: argparse.Namespace) -> int | None:
    limits = []
    if args.stop_after is not None:
        limits.append(args.stop_after)
    if args.token_budget is not None:
        limits.append(max(1, args.token_budget // args.tokens_per_section))
    if not limits:
        return None
    return min(limits)


def pending_status_sql() -> str:
    return ", ".join(sql_string(status) for status in TERMINAL_RUN_STATUSES)


def unprocessed_sections_sql(args: argparse.Namespace) -> str:
    limit = request_limit(args)
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    terminal_statuses = pending_status_sql()
    return f"""
COPY (
    WITH section_rows AS (
        SELECT
            s.passage_id,
            string_agg(
                '[' || s.sentence_number || '] Greek: ' || s.sentence ||
                E'\nEnglish: ' || s.english_sentence,
                E'\n\n'
                ORDER BY s.sentence_number
            ) AS numbered_sentences
        FROM greek_sentences s
        GROUP BY s.passage_id
    )
    SELECT passage_id, numbered_sentences
    FROM section_rows sr
    WHERE NOT EXISTS (
        SELECT 1
        FROM section_people_batch_items bi
        JOIN section_people_runs r ON r.run_id = bi.run_id
        WHERE bi.passage_id = sr.passage_id
          AND r.prompt_version = {sql_string(args.prompt_version)}
          AND bi.status = 'completed'
          AND r.status IN ('completed', 'completed_with_failures')
    )
      AND NOT EXISTS (
        SELECT 1
        FROM section_people_batch_items bi
        JOIN section_people_runs r ON r.run_id = bi.run_id
        WHERE bi.passage_id = sr.passage_id
          AND r.prompt_version = {sql_string(args.prompt_version)}
          AND r.status NOT IN ({terminal_statuses})
    )
    ORDER BY md5(sr.passage_id || ':' || {sql_string(args.random_seed)})
    {limit_clause}
) TO STDOUT WITH CSV HEADER;
"""


def load_unprocessed_sections(psql: PsqlRunner, args: argparse.Namespace) -> list[dict[str, str]]:
    raw = psql.run(unprocessed_sections_sql(args))
    return list(csv.DictReader(io.StringIO(raw)))


def recent_submission(psql: PsqlRunner, args: argparse.Namespace) -> dict[str, str] | None:
    if args.skip_if_submitted_hours <= 0:
        return None
    raw = psql.run(
        f"""
COPY (
    SELECT run_id, submitted_at, status, request_count
    FROM section_people_runs
    WHERE prompt_version = {sql_string(args.prompt_version)}
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
            if not str(payload.get("custom_id", "")).startswith("sectpeople:"):
                problems.append(f"line {line_number}: unexpected custom_id")
    if problems:
        raise ValueError("Invalid people batch request file:\n" + "\n".join(problems))


def write_submission(psql: PsqlRunner, payload: dict[str, Any]) -> None:
    run = payload["run"]
    items = payload.get("items") or []
    run_values = ", ".join(
        [
            sql_string(run["run_id"]),
            sql_string(run["started_at"]),
            sql_nullable_text(run.get("completed_at")),
            sql_string(run["model"]),
            sql_string(run["prompt_version"]),
            sql_string(run["status"]),
            sql_integer(run.get("token_budget")),
            sql_integer(run.get("tokens_per_section_estimate")),
            "0",
            "0",
            "0",
            "'batch'",
            sql_integer(run.get("request_count")),
            sql_nullable_text(run.get("random_seed")),
            sql_nullable_text(run.get("notes")),
        ]
    )
    sql = f"""
INSERT INTO section_people_runs (
    run_id, started_at, completed_at, model, prompt_version, status,
    token_budget, tokens_per_section_estimate, input_tokens, output_tokens,
    processed_count, api_mode, request_count, random_seed, notes
)
VALUES ({run_values})
ON CONFLICT (run_id) DO UPDATE
SET status = EXCLUDED.status,
    token_budget = EXCLUDED.token_budget,
    tokens_per_section_estimate = EXCLUDED.tokens_per_section_estimate,
    api_mode = 'batch',
    request_count = EXCLUDED.request_count,
    random_seed = EXCLUDED.random_seed,
    notes = EXCLUDED.notes;
"""
    if items:
        item_values = []
        for item in items:
            item_values.append(
                "("
                + ", ".join(
                    [
                        sql_string(run["run_id"]),
                        sql_integer(item["request_number"]),
                        sql_string(item["passage_id"]),
                        sql_integer(item["estimated_tokens"]),
                        "0",
                        "0",
                        "'submitted'",
                        "NULL",
                        sql_string(run["started_at"]),
                    ]
                )
                + ")"
            )
        item_sql_values = ",\n    ".join(item_values)
        sql += f"""

INSERT INTO section_people_batch_items (
    run_id, request_number, passage_id, estimated_tokens, input_tokens,
    output_tokens, status, error, created_at
)
VALUES
    {item_sql_values}
ON CONFLICT (run_id, request_number) DO UPDATE
SET passage_id = EXCLUDED.passage_id,
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
UPDATE section_people_runs
SET {", ".join(assignments)}
WHERE run_id = {sql_string(run_id)};
"""
    )


def submit_batch(psql: PsqlRunner, client: OpenAI, args: argparse.Namespace) -> None:
    recent = recent_submission(psql, args)
    if recent:
        print(
            f"Skipping people submission: recent run {recent['run_id']} "
            f"submitted at {recent['submitted_at']} with {recent['request_count']} requests."
        )
        return

    rows = load_unprocessed_sections(psql, args)
    if not rows:
        print("No unsubmitted section people rows found.")
        return

    run_id = str(uuid.uuid4())
    started_at = now_iso()
    batch_file = (
        Path(args.batch_file)
        if args.batch_file
        else Path("tmp") / f"section-people-batch-{run_id}.jsonl"
    )
    batch_file.parent.mkdir(parents=True, exist_ok=True)

    items = []
    with batch_file.open("w", encoding="utf-8") as handle:
        for request_number, row in enumerate(rows, start=1):
            items.append(
                {
                    "request_number": request_number,
                    "passage_id": row["passage_id"],
                    "estimated_tokens": args.tokens_per_section,
                }
            )
            request = {
                "custom_id": custom_id(run_id, request_number),
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
            "model": args.model,
            "prompt_version": args.prompt_version,
            "status": "batch_prepared" if args.dry_run else "batch_submitting",
            "token_budget": args.token_budget,
            "tokens_per_section_estimate": args.tokens_per_section,
            "request_count": len(items),
            "random_seed": args.random_seed,
            "notes": f"batch_file={batch_file}",
        },
        "items": items,
    }
    if args.dry_run:
        print(
            f"Dry run {run_id}: wrote {len(items)} section people requests to {batch_file}; "
            f"estimated {len(items) * args.tokens_per_section} tokens."
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
            "description": f"pausanias section people {run_id}",
            "local_run_id": run_id,
            "prompt_version": args.prompt_version,
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
        f"Submitted section people run {run_id}: {len(items)} requests, "
        f"estimated {len(items) * args.tokens_per_section} tokens."
    )
    print(f"OpenAI batch id: {result.id}")
    print(f"Batch request file: {batch_file}")


def load_batch_runs(psql: PsqlRunner, batch_run_id: str | None) -> list[dict[str, str]]:
    run_filter = ""
    if batch_run_id:
        run_filter = f"AND run_id = {sql_string(batch_run_id)}"
    raw = psql.run(
        f"""
COPY (
    SELECT run_id, prompt_version, model, openai_batch_id
    FROM section_people_runs
    WHERE api_mode = 'batch'
      AND openai_batch_id IS NOT NULL
      AND retrieved_at IS NULL
      {run_filter}
    ORDER BY started_at
) TO STDOUT WITH CSV HEADER;
"""
    )
    return list(csv.DictReader(io.StringIO(raw)))


def load_batch_items(psql: PsqlRunner, run_id: str) -> dict[int, dict[str, Any]]:
    raw = psql.run(
        f"""
COPY (
    SELECT request_number, passage_id
    FROM section_people_batch_items
    WHERE run_id = {sql_string(run_id)}
    ORDER BY request_number
) TO STDOUT WITH CSV HEADER;
"""
    )
    rows = {}
    for row in csv.DictReader(io.StringIO(raw)):
        row["request_number"] = int(row["request_number"])
        rows[row["request_number"]] = row
    return rows


def extract_tool_arguments(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
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
        print("No unretrieved section people Batch API runs found.")
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


def normalize_person(row: dict[str, Any], *, mention_order: int, source: dict[str, Any]) -> dict[str, Any]:
    gender = row.get("gender") if row.get("gender") in {"male", "female", "unknown"} else "unknown"
    person_category = row.get("person_category")
    if person_category not in {
        "human",
        "hero",
        "deity",
        "mythic_person",
        "collective",
        "uncertain",
    }:
        person_category = "uncertain"
    count_kind = row.get("count_kind")
    if count_kind not in {"individual", "group_exact", "group_uncounted"}:
        count_kind = "individual"
    try:
        person_count = int(row.get("person_count", 1))
    except (TypeError, ValueError):
        person_count = 0 if count_kind == "group_uncounted" else 1
    if count_kind == "group_uncounted":
        person_count = 0
    if count_kind == "individual" and person_count < 1:
        person_count = 1
    confidence = row.get("confidence")
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"
    sentence_number = int(row.get("sentence_number"))
    return {
        "passage_id": source["passage_id"],
        "sentence_number": sentence_number,
        "mention_order": mention_order,
        "mention_text": str(row.get("mention_text") or "").strip()[:500],
        "canonical_name": str(row.get("canonical_name") or "").strip()[:500],
        "is_named": bool(row.get("is_named")),
        "gender": gender,
        "person_category": person_category,
        "count_kind": count_kind,
        "person_count": max(0, person_count),
        "confidence": confidence,
        "rationale": str(row.get("rationale") or "").strip()[:1000],
    }


def write_results(psql: PsqlRunner, payload: dict[str, Any]) -> None:
    run = payload["run"]
    items = payload.get("items") or []
    mentions = payload.get("mentions") or []
    sql = ""
    if items:
        item_values = []
        for item in items:
            item_values.append(
                "("
                + ", ".join(
                    [
                        sql_integer(item["request_number"]),
                        sql_integer(item.get("input_tokens")),
                        sql_integer(item.get("output_tokens")),
                        sql_string(item.get("status") or ""),
                        sql_nullable_text(item.get("error")),
                    ]
                )
                + ")"
            )
        item_sql_values = ",\n    ".join(item_values)
        sql += f"""
WITH item_rows(request_number, input_tokens, output_tokens, status, error) AS (
    VALUES
    {item_sql_values}
)
UPDATE section_people_batch_items bi
SET input_tokens = item_rows.input_tokens,
    output_tokens = item_rows.output_tokens,
    status = item_rows.status,
    error = item_rows.error
FROM item_rows
WHERE bi.run_id = {sql_string(run["run_id"])}
  AND bi.request_number = item_rows.request_number;
"""
    if mentions:
        mention_values = []
        for mention in mentions:
            mention_values.append(
                "("
                + ", ".join(
                    [
                        sql_string(mention["passage_id"]),
                        sql_integer(mention["sentence_number"]),
                        sql_string(run["prompt_version"]),
                        sql_string(run["model"]),
                        sql_string(run["run_id"]),
                        sql_integer(mention["mention_order"]),
                        sql_string(mention["mention_text"]),
                        sql_string(mention.get("canonical_name") or ""),
                        sql_bool(mention.get("is_named")),
                        sql_nullable_text(mention.get("gender")),
                        sql_nullable_text(mention.get("person_category")),
                        sql_nullable_text(mention.get("count_kind")),
                        sql_integer(mention.get("person_count")),
                        sql_nullable_text(mention.get("confidence")),
                        sql_string(mention.get("rationale") or ""),
                        sql_string(run["completed_at"]),
                    ]
                )
                + ")"
            )
        mention_sql_values = ",\n    ".join(mention_values)
        sql += f"""

INSERT INTO section_people_mentions (
    passage_id, sentence_number, prompt_version, model, run_id, mention_order,
    mention_text, canonical_name, is_named, gender, person_category, count_kind,
    person_count, confidence, rationale, created_at
)
VALUES
    {mention_sql_values}
ON CONFLICT (passage_id, sentence_number, prompt_version, mention_order) DO UPDATE
SET model = EXCLUDED.model,
    run_id = EXCLUDED.run_id,
    mention_text = EXCLUDED.mention_text,
    canonical_name = EXCLUDED.canonical_name,
    is_named = EXCLUDED.is_named,
    gender = EXCLUDED.gender,
    person_category = EXCLUDED.person_category,
    count_kind = EXCLUDED.count_kind,
    person_count = EXCLUDED.person_count,
    confidence = EXCLUDED.confidence,
    rationale = EXCLUDED.rationale,
    created_at = EXCLUDED.created_at;
"""
    sql += f"""

UPDATE section_people_runs
SET completed_at = {sql_string(run["completed_at"])},
    status = {sql_string(run["status"])},
    input_tokens = {sql_integer(run.get("input_tokens"))},
    output_tokens = {sql_integer(run.get("output_tokens"))},
    processed_count = {sql_integer(run.get("processed_count"))},
    api_mode = 'batch',
    request_count = {sql_integer(run.get("request_count"))},
    openai_output_file_id = {sql_nullable_text(run.get("openai_output_file_id"))},
    openai_error_file_id = {sql_nullable_text(run.get("openai_error_file_id"))},
    retrieved_at = {sql_nullable_text(run.get("retrieved_at"))},
    notes = {sql_nullable_text(run.get("notes"))}
WHERE section_people_runs.run_id = {sql_string(run["run_id"])};
"""
    psql.run(sql)


def fetch_batches(psql: PsqlRunner, client: OpenAI, *, batch_run_id: str | None) -> None:
    runs = load_batch_runs(psql, batch_run_id)
    if not runs:
        print("No unretrieved section people Batch API runs found.")
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
        mentions = []
        failures = []
        seen_requests = set()

        for line in output.text.splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            request_number = None
            try:
                output_run_id, request_number = parse_custom_id(record.get("custom_id", ""))
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
                section_people = args.get("people") or []
                if not isinstance(section_people, list):
                    raise ValueError("Tool arguments people field is not a list")
                for mention_order, person in enumerate(section_people, start=1):
                    if not isinstance(person, dict):
                        raise ValueError(f"Person row {mention_order} is not an object")
                    mentions.append(
                        normalize_person(
                            person,
                            mention_order=mention_order,
                            source=source,
                        )
                    )
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
                failures.append({"custom_id": record.get("custom_id"), "error": str(exc)})

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
                    "custom_id": custom_id(run_id, request_number),
                    "error": "No output record returned for request",
                }
            )

        completed_at = now_iso()
        input_tokens = sum(item["input_tokens"] for item in item_updates)
        output_tokens = sum(item["output_tokens"] for item in item_updates)
        processed_count = sum(1 for item in item_updates if item["status"] == "completed")
        status = "completed" if not failures else "completed_with_failures"
        notes = (
            f"failures={len(failures)}; mentions={len(mentions)}; "
            f"fetched_from_batch={run['openai_batch_id']}"
        )
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
            "mentions": mentions,
        }
        write_results(psql, payload)
        print(
            f"Fetched section people run {run_id}: {processed_count}/{len(item_lookup)} "
            f"sections saved, {len(mentions)} mentions, "
            f"{input_tokens + output_tokens} tokens, {len(failures)} failures."
        )


def stats_sql(args: argparse.Namespace) -> str:
    return f"""
COPY (
    WITH bucket_tags AS (
        SELECT passage_id, sentence_number, myth_history_bucket
        FROM sentence_greta_tags
        WHERE prompt_version = {sql_string(args.bucket_prompt_version)}
    )
    SELECT
        b.myth_history_bucket,
        CASE WHEN m.is_named THEN 'named' ELSE 'anonymous' END AS name_status,
        m.gender,
        count(*) AS mention_rows,
        sum(CASE WHEN m.person_count > 0 THEN m.person_count ELSE 0 END) AS exact_people,
        count(DISTINCT m.passage_id) AS sections,
        count(DISTINCT m.passage_id || ':' || m.sentence_number) AS sentences
    FROM section_people_mentions m
    JOIN bucket_tags b
      ON b.passage_id = m.passage_id
     AND b.sentence_number = m.sentence_number
    WHERE m.prompt_version = {sql_string(args.prompt_version)}
      AND m.gender IN ('male', 'female')
    GROUP BY b.myth_history_bucket, name_status, m.gender
    ORDER BY b.myth_history_bucket, name_status, m.gender
) TO STDOUT WITH CSV HEADER;
"""


def holm_adjust(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [math.nan] * len(p_values)
    running = 0.0
    total = len(p_values)
    for rank, index in enumerate(order):
        value = min(1.0, p_values[index] * (total - rank))
        running = max(running, value)
        adjusted[index] = running
    return adjusted


def report_stats(psql: PsqlRunner, args: argparse.Namespace) -> None:
    raw = psql.run(stats_sql(args))
    rows = list(csv.DictReader(io.StringIO(raw)))
    if not rows:
        print(f"No section people mentions found for prompt_version={args.prompt_version}.")
        return

    frame = pd.DataFrame(rows)
    frame["mention_rows"] = frame["mention_rows"].astype(int)
    frame["exact_people"] = frame["exact_people"].astype(int)
    frame["class"] = frame["name_status"] + "_" + frame["gender"]
    wanted_classes = ["anonymous_female", "named_female", "anonymous_male", "named_male"]
    wanted_buckets = ["mythic", "historical", "other"]
    table = (
        frame.pivot_table(
            index="myth_history_bucket",
            columns="class",
            values="mention_rows",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(index=wanted_buckets, columns=wanted_classes, fill_value=0)
        .astype(int)
    )
    exact_table = (
        frame.pivot_table(
            index="myth_history_bucket",
            columns="class",
            values="exact_people",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(index=wanted_buckets, columns=wanted_classes, fill_value=0)
        .astype(int)
    )
    proportions = table.div(table.sum(axis=1).replace(0, pd.NA), axis=0).fillna(0)
    percentages = proportions * 100
    print("Within-bucket percentages by people class (mention rows)")
    print(percentages.map(lambda value: f"{value:.1f}%").to_string())
    print("\nMention-row counts by sentence bucket and class")
    print(table.to_string())
    print("\nExact-count people totals (group_uncounted contributes 0)")
    print(exact_table.to_string())

    if table.to_numpy().sum() == 0 or (table.sum(axis=1) == 0).any():
        print("\nNot enough data for chi-squared test across all buckets.")
        return

    chi2, p_value, dof, expected = chi2_contingency(table.to_numpy(), correction=False)
    n = table.to_numpy().sum()
    cramers_v = math.sqrt(chi2 / (n * min(table.shape[0] - 1, table.shape[1] - 1)))
    print("\nChi-squared test of bucket x people-class independence")
    print(f"chi2={chi2:.4f}, dof={dof}, p={p_value:.6g}, Cramer's V={cramers_v:.4f}")
    expected_frame = pd.DataFrame(expected, index=table.index, columns=table.columns)
    residuals = (table - expected_frame) / expected_frame.pow(0.5)
    print("\nStandardized residuals")
    print(residuals.map(lambda value: f"{value:.2f}").to_string())

    pair_rows = []
    p_values = []
    for bucket_a, bucket_b in itertools.combinations(wanted_buckets, 2):
        sub = table.loc[[bucket_a, bucket_b]]
        if sub.to_numpy().sum() == 0 or (sub.sum(axis=1) == 0).any():
            continue
        chi2_pair, p_pair, dof_pair, _ = chi2_contingency(
            sub.to_numpy(), correction=False
        )
        n_pair = sub.to_numpy().sum()
        v_pair = math.sqrt(
            chi2_pair / (n_pair * min(sub.shape[0] - 1, sub.shape[1] - 1))
        )
        pair_rows.append(
            {
                "comparison": f"{bucket_a} vs {bucket_b}",
                "chi2": chi2_pair,
                "dof": dof_pair,
                "p": p_pair,
                "cramers_v": v_pair,
            }
        )
        p_values.append(p_pair)
    if pair_rows:
        adjusted = holm_adjust(p_values)
        print("\nPairwise bucket tests (Holm-adjusted p)")
        for row, p_adjusted in zip(pair_rows, adjusted):
            print(
                f"{row['comparison']}: chi2={row['chi2']:.4f}, dof={row['dof']}, "
                f"p={row['p']:.6g}, p_holm={p_adjusted:.6g}, "
                f"Cramer's V={row['cramers_v']:.4f}"
            )


def main() -> None:
    args = parse_arguments()
    psql = PsqlRunner(args.database_url, psql_bin=args.psql_bin, ssh_host=args.ssh_host)
    psql.run(schema_path().read_text(encoding="utf-8"))
    if args.report_stats:
        report_stats(psql, args)
        return

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
    raise SystemExit(
        "Specify --use-batch-api, --check-batches, --fetch-batches, or --report-stats."
    )


if __name__ == "__main__":
    main()
