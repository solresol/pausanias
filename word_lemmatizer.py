#!/usr/bin/env python

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shlex
import subprocess
import sys
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI


DEFAULT_DATABASE_URL = "dbname=pausanias user=gregb"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_PROMPT_VERSION = "greek-word-lemmas-v1"

GREEK_TOKEN_RE = re.compile(
    r"[\u0370-\u03ff\u1f00-\u1fff]+(?:[ʼ'’\u02bc](?=[\u0370-\u03ff\u1f00-\u1fff])"
    r"[\u0370-\u03ff\u1f00-\u1fff]+|[ʼ'’\u02bc])?"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def postgres_text(value) -> str:
    return str(value).replace("\x00", "")


def sql_string(value: str) -> str:
    return "'" + postgres_text(value).replace("'", "''") + "'"


def sql_nullable_text(value) -> str:
    if value is None:
        return "NULL"
    return sql_string(postgres_text(value))


def sql_integer(value) -> str:
    return str(int(value or 0))


def sql_bool(value) -> str:
    return "TRUE" if bool(value) else "FALSE"


def sql_text_array(values) -> str:
    if not values:
        return "ARRAY[]::text[]"
    return "ARRAY[" + ", ".join(sql_string(value) for value in values) + "]::text[]"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lemmatize distinct Greek surface forms with the OpenAI API."
    )
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--ssh-host", default=None)
    parser.add_argument("--psql-bin", default="psql")
    parser.add_argument("--openai-api-key-file", default="~/.openai.key")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION)
    parser.add_argument(
        "--source",
        choices=("sentences", "passages"),
        default="sentences",
        help="Source table to tokenize (default: sentences).",
    )
    parser.add_argument("--exclude-books", default="")
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--sample-seed", default="word-lemma-sample-v1")
    parser.add_argument("--stop-after", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--schema-only", action="store_true")
    parser.add_argument(
        "--use-batch-api",
        action="store_true",
        help="Submit the work through the OpenAI Batch API and exit.",
    )
    parser.add_argument(
        "--check-batches",
        action="store_true",
        help="Check unretrieved OpenAI Batch API runs recorded in the database.",
    )
    parser.add_argument(
        "--fetch-batches",
        action="store_true",
        help="Fetch completed OpenAI Batch API runs and store their lemmas.",
    )
    parser.add_argument(
        "--batch-run-id",
        default=None,
        help="Restrict --check-batches or --fetch-batches to this local run ID.",
    )
    parser.add_argument(
        "--batch-file",
        default=None,
        help="Path for the JSONL request file when using --use-batch-api.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and validate a batch request file without uploading it.",
    )
    return parser.parse_args()


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def parse_excluded_books(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def load_openai_api_key(key_file: str) -> str:
    with open(os.path.expanduser(key_file), "r", encoding="utf-8") as handle:
        return handle.read().strip()


class PsqlRunner:
    def __init__(self, database_url: str, *, psql_bin: str = "psql", ssh_host: str | None = None):
        self.database_url = database_url
        self.psql_bin = psql_bin
        self.ssh_host = ssh_host

    def command(self) -> list[str]:
        if not self.ssh_host:
            return [self.psql_bin, self.database_url, "-v", "ON_ERROR_STOP=1", "-P", "pager=off"]
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


def schema_sql() -> str:
    return Path(__file__).resolve().parent.joinpath("database", "schema.sql").read_text(
        encoding="utf-8"
    )


def tokenize(text: str) -> list[str]:
    return [match.group(0) for match in GREEK_TOKEN_RE.finditer(text or "")]


def source_rows_sql(source: str, excluded_books: list[str]) -> str:
    book_filter = ""
    if excluded_books:
        books = ", ".join(sql_string(book) for book in excluded_books)
        id_expr = "passage_id" if source == "sentences" else "id"
        book_filter = f"WHERE split_part({id_expr}, '.', 1) <> ALL(ARRAY[{books}])"
    if source == "sentences":
        return f"""
COPY (
    SELECT sentence AS greek_text
    FROM greek_sentences
    {book_filter}
) TO STDOUT WITH CSV HEADER;
"""
    return f"""
COPY (
    SELECT passage AS greek_text
    FROM passages
    {book_filter}
) TO STDOUT WITH CSV HEADER;
"""


def collect_surface_forms(
    psql: PsqlRunner,
    *,
    source: str,
    excluded_books: list[str],
    prompt_version: str,
    sample_size: int | None,
    sample_seed: str,
    stop_after: int | None,
) -> tuple[list[dict], int]:
    raw = psql.run(source_rows_sql(source, excluded_books))
    counts: Counter[str] = Counter()
    examples: dict[str, str] = {}
    for row in csv.DictReader(io.StringIO(raw)):
        for token in tokenize(row["greek_text"]):
            key = token.lower()
            counts[key] += 1
            examples.setdefault(key, token)

    existing_raw = psql.run(
        f"""
COPY (
    SELECT surface_form
    FROM greek_word_lemmas
    WHERE prompt_version = {sql_string(prompt_version)}
) TO STDOUT WITH CSV HEADER;
"""
    )
    existing = {row["surface_form"] for row in csv.DictReader(io.StringIO(existing_raw))}
    items = [
        {
            "surface_form": surface,
            "example_form": examples[surface],
            "occurrence_count": count,
        }
        for surface, count in counts.items()
        if surface not in existing
    ]
    if sample_size is not None:
        import hashlib

        items.sort(
            key=lambda item: hashlib.md5(
                f"{item['surface_form']}:{sample_seed}".encode("utf-8")
            ).hexdigest()
        )
        items = items[:sample_size]
    else:
        items.sort(key=lambda item: (-item["occurrence_count"], item["surface_form"]))
        if stop_after is not None:
            items = items[:stop_after]
    return items, sum(counts.values())


def batches(items: list[dict], batch_size: int) -> list[list[dict]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def word_tool() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "save_word_lemmas",
                "description": "Save lemma choices for context-free Greek word forms.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "word_index": {"type": "integer"},
                                    "lemma": {"type": "string"},
                                    "confidence": {
                                        "type": "string",
                                        "enum": ["high", "medium", "low"],
                                    },
                                    "is_ambiguous": {"type": "boolean"},
                                    "alternatives": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                                "required": [
                                    "word_index",
                                    "lemma",
                                    "confidence",
                                    "is_ambiguous",
                                    "alternatives",
                                ],
                            },
                        }
                    },
                    "required": ["items"],
                },
            },
        }
    ]


SYSTEM_PROMPT = (
    "You lemmatize isolated ancient Greek word forms from Pausanias. For each "
    "numbered surface form, return the most likely Greek dictionary lemma. "
    "If the form is genuinely ambiguous without context, still choose the "
    "most likely lemma, set is_ambiguous=true, and list plausible alternative "
    "lemmas. Use Greek lemmas, not English glosses. Do not explain."
)


def completion_body(*, model: str, batch: list[dict]) -> dict:
    numbered = "\n".join(
        f"{idx}. {item['surface_form']}" for idx, item in enumerate(batch, start=1)
    )
    user_content = f"Surface forms:\n{numbered}\n\nReturn aligned lemma choices."
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "tools": word_tool(),
        "tool_choice": {"type": "function", "function": {"name": "save_word_lemmas"}},
    }


def rows_from_arguments(arguments: dict, batch: list[dict]) -> list[dict]:
    returned = arguments.get("items", [])
    if len(returned) != len(batch):
        raise ValueError(f"Expected {len(batch)} items, got {len(returned)}")
    by_index = {int(item["word_index"]): item for item in returned}
    rows = []
    for idx, source in enumerate(batch, start=1):
        item = by_index.get(idx)
        if not item:
            raise ValueError(f"Missing word_index {idx}")
        rows.append(
            {
                **source,
                "lemma": item["lemma"],
                "confidence": item["confidence"],
                "is_ambiguous": bool(item["is_ambiguous"]),
                "alternatives": item.get("alternatives") or [],
            }
        )
    return rows


def lemmatize_batch(client: OpenAI, *, model: str, batch: list[dict]) -> dict:
    response = client.chat.completions.create(**completion_body(model=model, batch=batch))
    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise ValueError("No tool call returned")
    args = json.loads(tool_calls[0].function.arguments)
    rows = rows_from_arguments(args, batch)
    return {
        "items": rows,
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens,
    }


def write_payload(psql: PsqlRunner, payload: dict) -> None:
    run = payload["run"]
    batches = payload.get("batches") or []
    items = payload.get("items") or []
    run_values = ", ".join(
        [
            sql_string(run["run_id"]),
            sql_string(run["started_at"]),
            sql_string(run.get("completed_at") or ""),
            sql_string(run["model"]),
            sql_string(run["prompt_version"]),
            sql_string(run["status"]),
            sql_string(run["source_scope"]),
            sql_integer(run.get("batch_size")),
            sql_integer(run.get("surface_form_count")),
            sql_integer(run.get("occurrence_count")),
            sql_integer(run.get("input_tokens")),
            sql_integer(run.get("output_tokens")),
            sql_integer(run.get("failure_count")),
            sql_string(run.get("api_mode") or "direct"),
            sql_integer(run.get("request_count")),
            sql_nullable_text(run.get("openai_batch_id")),
            sql_nullable_text(run.get("openai_input_file_id")),
            sql_nullable_text(run.get("openai_output_file_id")),
            sql_nullable_text(run.get("openai_error_file_id")),
            sql_nullable_text(run.get("submitted_at")),
            sql_nullable_text(run.get("retrieved_at")),
            sql_nullable_text(run.get("notes")),
        ]
    )
    sql = f"""
INSERT INTO word_lemmatization_runs (
    run_id, started_at, completed_at, model, prompt_version, status, source_scope,
    batch_size, surface_form_count, occurrence_count, input_tokens, output_tokens,
    failure_count, api_mode, request_count, openai_batch_id, openai_input_file_id,
    openai_output_file_id, openai_error_file_id, submitted_at, retrieved_at, notes
)
VALUES ({run_values})
ON CONFLICT (run_id) DO UPDATE
SET completed_at = EXCLUDED.completed_at,
    status = EXCLUDED.status,
    surface_form_count = EXCLUDED.surface_form_count,
    occurrence_count = EXCLUDED.occurrence_count,
    input_tokens = EXCLUDED.input_tokens,
    output_tokens = EXCLUDED.output_tokens,
    failure_count = EXCLUDED.failure_count,
    api_mode = EXCLUDED.api_mode,
    request_count = EXCLUDED.request_count,
    openai_batch_id = COALESCE(EXCLUDED.openai_batch_id, word_lemmatization_runs.openai_batch_id),
    openai_input_file_id = COALESCE(EXCLUDED.openai_input_file_id, word_lemmatization_runs.openai_input_file_id),
    openai_output_file_id = COALESCE(EXCLUDED.openai_output_file_id, word_lemmatization_runs.openai_output_file_id),
    openai_error_file_id = COALESCE(EXCLUDED.openai_error_file_id, word_lemmatization_runs.openai_error_file_id),
    submitted_at = COALESCE(EXCLUDED.submitted_at, word_lemmatization_runs.submitted_at),
    retrieved_at = COALESCE(EXCLUDED.retrieved_at, word_lemmatization_runs.retrieved_at),
    notes = EXCLUDED.notes;
"""
    if batches:
        batch_values = []
        for batch in batches:
            batch_values.append(
                "("
                + ", ".join(
                    [
                        sql_string(run["run_id"]),
                        sql_integer(batch["batch_number"]),
                        sql_integer(batch.get("item_count")),
                        sql_integer(batch.get("input_tokens")),
                        sql_integer(batch.get("output_tokens")),
                        sql_string(run.get("completed_at") or ""),
                    ]
                )
                + ")"
            )
        batch_sql_values = ",\n    ".join(batch_values)
        sql += f"""
INSERT INTO word_lemmatization_batches (
    run_id, batch_number, item_count, input_tokens, output_tokens, created_at
)
VALUES
    {batch_sql_values}
ON CONFLICT (run_id, batch_number) DO UPDATE
SET item_count = EXCLUDED.item_count,
    input_tokens = EXCLUDED.input_tokens,
    output_tokens = EXCLUDED.output_tokens,
    created_at = EXCLUDED.created_at;
"""
    if items:
        item_values = []
        for item in items:
            item_values.append(
                "("
                + ", ".join(
                    [
                        sql_string(item["surface_form"]),
                        sql_string(run["prompt_version"]),
                        sql_string(run["model"]),
                        sql_string(run["run_id"]),
                        sql_string(item["example_form"]),
                        sql_integer(item.get("occurrence_count")),
                        sql_string(item["lemma"]),
                        sql_string(item["confidence"]),
                        sql_bool(item.get("is_ambiguous")),
                        sql_text_array(item.get("alternatives") or []),
                        sql_string(run.get("completed_at") or ""),
                    ]
                )
                + ")"
            )
        item_sql_values = ",\n    ".join(item_values)
        sql += f"""
INSERT INTO greek_word_lemmas (
    surface_form, prompt_version, model, run_id, example_form, occurrence_count,
    lemma, confidence, is_ambiguous, alternatives, created_at
)
VALUES
    {item_sql_values}
ON CONFLICT (surface_form, prompt_version) DO UPDATE
SET model = EXCLUDED.model,
    run_id = EXCLUDED.run_id,
    example_form = EXCLUDED.example_form,
    occurrence_count = EXCLUDED.occurrence_count,
    lemma = EXCLUDED.lemma,
    confidence = EXCLUDED.confidence,
    is_ambiguous = EXCLUDED.is_ambiguous,
    alternatives = EXCLUDED.alternatives,
    created_at = EXCLUDED.created_at;
"""
    psql.run(sql)


def batch_custom_id(run_id: str, batch_number: int) -> str:
    return f"wordlemma:{run_id}:{batch_number}"


def parse_batch_custom_id(custom_id: str) -> tuple[str, int]:
    parts = str(custom_id).split(":")
    if len(parts) != 3 or parts[0] != "wordlemma":
        raise ValueError(f"Unexpected custom_id {custom_id!r}")
    return parts[1], int(parts[2])


def validate_batch_requests(batch_file_path: Path) -> None:
    problems = []
    with batch_file_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                problems.append(f"line {line_number}: invalid JSON ({exc})")
                continue
            if payload.get("method") != "POST":
                problems.append(f"line {line_number}: expected method POST")
            if payload.get("url") != "/v1/chat/completions":
                problems.append(
                    f"line {line_number}: expected /v1/chat/completions, got "
                    f"{payload.get('url')!r}"
                )
            if not str(payload.get("custom_id", "")).startswith("wordlemma:"):
                problems.append(f"line {line_number}: unexpected custom_id")
    if problems:
        raise ValueError("Invalid batch request file:\n" + "\n".join(problems))


def write_batch_submission(psql: PsqlRunner, payload: dict) -> None:
    run = payload["run"]
    batches = payload.get("batches") or []
    batch_items = payload.get("batch_items") or []
    run_values = ", ".join(
        [
            sql_string(run["run_id"]),
            sql_string(run["started_at"]),
            sql_nullable_text(run.get("completed_at")),
            sql_string(run["model"]),
            sql_string(run["prompt_version"]),
            sql_string(run["status"]),
            sql_string(run["source_scope"]),
            sql_integer(run.get("batch_size")),
            sql_integer(run.get("surface_form_count")),
            sql_integer(run.get("occurrence_count")),
            "0",
            "0",
            "0",
            "'batch'",
            sql_integer(run.get("request_count")),
            sql_nullable_text(run.get("notes")),
        ]
    )
    sql = f"""
INSERT INTO word_lemmatization_runs (
    run_id, started_at, completed_at, model, prompt_version, status, source_scope,
    batch_size, surface_form_count, occurrence_count, input_tokens, output_tokens,
    failure_count, api_mode, request_count, notes
)
VALUES ({run_values})
ON CONFLICT (run_id) DO UPDATE
SET status = EXCLUDED.status,
    source_scope = EXCLUDED.source_scope,
    surface_form_count = EXCLUDED.surface_form_count,
    occurrence_count = EXCLUDED.occurrence_count,
    api_mode = 'batch',
    request_count = EXCLUDED.request_count,
    notes = EXCLUDED.notes;
"""
    if batches:
        batch_values = []
        for batch in batches:
            batch_values.append(
                "("
                + ", ".join(
                    [
                        sql_string(run["run_id"]),
                        sql_integer(batch["batch_number"]),
                        sql_integer(batch.get("item_count")),
                        "0",
                        "0",
                        sql_string(run["started_at"]),
                    ]
                )
                + ")"
            )
        batch_sql_values = ",\n    ".join(batch_values)
        sql += f"""
INSERT INTO word_lemmatization_batches (
    run_id, batch_number, item_count, input_tokens, output_tokens, created_at
)
VALUES
    {batch_sql_values}
ON CONFLICT (run_id, batch_number) DO UPDATE
SET item_count = EXCLUDED.item_count,
    created_at = EXCLUDED.created_at;
"""
    if batch_items:
        item_values = []
        for item in batch_items:
            item_values.append(
                "("
                + ", ".join(
                    [
                        sql_string(run["run_id"]),
                        sql_integer(item["batch_number"]),
                        sql_integer(item["word_index"]),
                        sql_string(item["surface_form"]),
                        sql_string(item["example_form"]),
                        sql_integer(item.get("occurrence_count")),
                    ]
                )
                + ")"
            )
        item_sql_values = ",\n    ".join(item_values)
        sql += f"""
INSERT INTO word_lemmatization_batch_items (
    run_id, batch_number, word_index, surface_form, example_form, occurrence_count
)
VALUES
    {item_sql_values}
ON CONFLICT (run_id, batch_number, word_index) DO UPDATE
SET surface_form = EXCLUDED.surface_form,
    example_form = EXCLUDED.example_form,
    occurrence_count = EXCLUDED.occurrence_count;
"""
    psql.run(sql)


def update_batch_run_ids(
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
) -> None:
    assignments = []
    if openai_batch_id is not None:
        assignments.append(f"openai_batch_id = {sql_string(openai_batch_id)}")
    if openai_input_file_id is not None:
        assignments.append(f"openai_input_file_id = {sql_string(openai_input_file_id)}")
    if openai_output_file_id is not None:
        assignments.append(f"openai_output_file_id = {sql_string(openai_output_file_id)}")
    if openai_error_file_id is not None:
        assignments.append(f"openai_error_file_id = {sql_string(openai_error_file_id)}")
    if status is not None:
        assignments.append(f"status = {sql_string(status)}")
    if submitted_at is not None:
        assignments.append(f"submitted_at = {sql_string(submitted_at)}")
    if retrieved_at is not None:
        assignments.append(f"retrieved_at = {sql_string(retrieved_at)}")
    if not assignments:
        return
    sql = f"""
UPDATE word_lemmatization_runs
SET {", ".join(assignments)}
WHERE run_id = {sql_string(run_id)};
"""
    psql.run(sql)


def batch_run_query(batch_run_id: str | None) -> str:
    run_filter = ""
    if batch_run_id:
        run_filter = f"AND run_id = {sql_string(batch_run_id)}"
    return f"""
COPY (
    SELECT run_id, openai_batch_id
    FROM word_lemmatization_runs
    WHERE api_mode = 'batch'
      AND openai_batch_id IS NOT NULL
      AND retrieved_at IS NULL
      {run_filter}
    ORDER BY started_at
) TO STDOUT WITH CSV HEADER;
"""


def load_batch_runs(psql: PsqlRunner, batch_run_id: str | None) -> list[dict]:
    raw = psql.run(batch_run_query(batch_run_id))
    return list(csv.DictReader(io.StringIO(raw)))


def load_batch_items(psql: PsqlRunner, run_id: str) -> dict[int, list[dict]]:
    raw = psql.run(
        f"""
COPY (
    SELECT batch_number, word_index, surface_form, example_form, occurrence_count
    FROM word_lemmatization_batch_items
    WHERE run_id = {sql_string(run_id)}
    ORDER BY batch_number, word_index
) TO STDOUT WITH CSV HEADER;
"""
    )
    grouped: dict[int, list[dict]] = {}
    for row in csv.DictReader(io.StringIO(raw)):
        batch_number = int(row["batch_number"])
        grouped.setdefault(batch_number, []).append(
            {
                "surface_form": row["surface_form"],
                "example_form": row["example_form"],
                "occurrence_count": int(row["occurrence_count"]),
            }
        )
    return grouped


def extract_batch_tool_arguments(record: dict) -> tuple[dict, dict]:
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


def submit_batch_api_run(
    *,
    client: OpenAI,
    psql: PsqlRunner,
    args: argparse.Namespace,
    items: list[dict],
    total_occurrences: int,
    excluded_books: list[str],
) -> None:
    run_id = str(uuid.uuid4())
    started_at = now_iso()
    batch_items = batches(items, args.batch_size)
    batch_file = (
        Path(args.batch_file)
        if args.batch_file
        else Path("tmp") / f"word-lemmatization-batch-{run_id}.jsonl"
    )
    batch_file.parent.mkdir(parents=True, exist_ok=True)

    flattened_items = []
    with batch_file.open("w", encoding="utf-8") as handle:
        for batch_number, batch in enumerate(batch_items, start=1):
            for word_index, item in enumerate(batch, start=1):
                flattened_items.append(
                    {
                        "batch_number": batch_number,
                        "word_index": word_index,
                        **item,
                    }
                )
            request = {
                "custom_id": batch_custom_id(run_id, batch_number),
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": completion_body(model=args.model, batch=batch),
            }
            handle.write(json.dumps(request, ensure_ascii=False) + "\n")

    validate_batch_requests(batch_file)
    submission_payload = {
        "run": {
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": "",
            "model": args.model,
            "prompt_version": args.prompt_version,
            "status": "batch_prepared" if args.dry_run else "batch_submitting",
            "source_scope": f"{args.source};exclude_books={','.join(excluded_books)}",
            "batch_size": args.batch_size,
            "surface_form_count": len(items),
            "occurrence_count": sum(item["occurrence_count"] for item in items),
            "request_count": len(batch_items),
            "notes": (
                f"sample_size={args.sample_size}; stop_after={args.stop_after}; "
                f"sample_seed={args.sample_seed}; total_source_occurrences={total_occurrences}; "
                f"batch_file={batch_file}"
            ),
        },
        "batches": [
            {"batch_number": idx, "item_count": len(batch)}
            for idx, batch in enumerate(batch_items, start=1)
        ],
        "batch_items": flattened_items,
    }

    if args.dry_run:
        print(
            f"Dry run {run_id}: wrote {len(batch_items)} requests for {len(items)} "
            f"surface forms to {batch_file}."
        )
        return

    write_batch_submission(psql, submission_payload)
    with batch_file.open("rb") as handle:
        batch_input_file = client.files.create(file=handle, purpose="batch")
    result = client.batches.create(
        input_file_id=batch_input_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": f"pausanias word lemmatization {run_id}",
            "local_run_id": run_id,
            "prompt_version": args.prompt_version,
        },
    )
    submitted_at = now_iso()
    update_batch_run_ids(
        psql,
        run_id=run_id,
        openai_batch_id=result.id,
        openai_input_file_id=batch_input_file.id,
        status="batch_submitted",
        submitted_at=submitted_at,
    )
    print(
        f"Submitted run {run_id}: {len(items)} forms in {len(batch_items)} "
        f"Batch API requests."
    )
    print(f"OpenAI batch id: {result.id}")
    print(f"Batch request file: {batch_file}")


def check_batch_api_runs(*, client: OpenAI, psql: PsqlRunner, batch_run_id: str | None) -> None:
    runs = load_batch_runs(psql, batch_run_id)
    if not runs:
        print("No unretrieved Batch API word-lemmatization runs found.")
        return
    for run in runs:
        result = client.batches.retrieve(run["openai_batch_id"])
        status = f"batch_{result.status}"
        update_batch_run_ids(
            psql,
            run_id=run["run_id"],
            status=status,
            openai_output_file_id=result.output_file_id,
            openai_error_file_id=result.error_file_id,
        )
        counts = result.request_counts
        if counts:
            progress = f"{counts.completed}/{counts.total} complete, {counts.failed} failed"
        else:
            progress = "no request counts yet"
        print(f"{run['run_id']} {run['openai_batch_id']}: {result.status} ({progress})")


def fetch_batch_api_runs(
    *,
    client: OpenAI,
    psql: PsqlRunner,
    batch_run_id: str | None,
    output_json: str | None,
) -> None:
    runs = load_batch_runs(psql, batch_run_id)
    if not runs:
        print("No unretrieved Batch API word-lemmatization runs found.")
        return

    for run in runs:
        run_id = run["run_id"]
        openai_batch_id = run["openai_batch_id"]
        result = client.batches.retrieve(openai_batch_id)
        update_batch_run_ids(
            psql,
            run_id=run_id,
            status=f"batch_{result.status}",
            openai_output_file_id=result.output_file_id,
            openai_error_file_id=result.error_file_id,
        )
        if result.status != "completed":
            print(f"{run_id}: remote status is {result.status}; not fetching yet.")
            continue
        if result.output_file_id is None:
            print(f"{run_id}: completed but has no output file.")
            continue

        batch_lookup = load_batch_items(psql, run_id)
        file_response = client.files.content(result.output_file_id)
        results = []
        batch_results = []
        failures = []
        seen_batches = set()

        for line in file_response.text.splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            try:
                record_run_id, batch_number = parse_batch_custom_id(record.get("custom_id", ""))
                if record_run_id != run_id:
                    raise ValueError(
                        f"Output custom_id belongs to {record_run_id}, expected {run_id}"
                    )
                source_batch = batch_lookup.get(batch_number)
                if not source_batch:
                    raise ValueError(f"No stored input rows for batch {batch_number}")
                arguments, usage = extract_batch_tool_arguments(record)
                rows = rows_from_arguments(arguments, source_batch)
                prompt_tokens = int(usage.get("prompt_tokens", 0))
                completion_tokens = int(usage.get("completion_tokens", 0))
                results.extend(rows)
                batch_results.append(
                    {
                        "batch_number": batch_number,
                        "item_count": len(rows),
                        "input_tokens": prompt_tokens,
                        "output_tokens": completion_tokens,
                    }
                )
                seen_batches.add(batch_number)
            except Exception as exc:
                failures.append(
                    {
                        "custom_id": record.get("custom_id"),
                        "error": str(exc),
                    }
                )

        for batch_number in sorted(set(batch_lookup) - seen_batches):
            failures.append(
                {
                    "custom_id": batch_custom_id(run_id, batch_number),
                    "error": "No output record returned for batch",
                }
            )

        completed_at = now_iso()
        input_tokens = sum(row["input_tokens"] for row in batch_results)
        output_tokens = sum(row["output_tokens"] for row in batch_results)
        run_meta_raw = psql.run(
            f"""
COPY (
    SELECT started_at, model, prompt_version, source_scope, batch_size, notes,
           openai_input_file_id, submitted_at
    FROM word_lemmatization_runs
    WHERE run_id = {sql_string(run_id)}
) TO STDOUT WITH CSV HEADER;
"""
        )
        run_meta_rows = list(csv.DictReader(io.StringIO(run_meta_raw)))
        if not run_meta_rows:
            raise RuntimeError(f"No local run metadata for {run_id}")
        run_meta = run_meta_rows[0]
        payload = {
            "run": {
                "run_id": run_id,
                "started_at": run_meta["started_at"],
                "completed_at": completed_at,
                "model": run_meta["model"],
                "prompt_version": run_meta["prompt_version"],
                "status": "completed" if not failures else "completed_with_failures",
                "source_scope": run_meta["source_scope"],
                "batch_size": int(run_meta["batch_size"]),
                "surface_form_count": len(results),
                "occurrence_count": sum(item["occurrence_count"] for item in results),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "failure_count": len(failures),
                "api_mode": "batch",
                "request_count": len(batch_lookup),
                "openai_batch_id": openai_batch_id,
                "openai_input_file_id": run_meta["openai_input_file_id"],
                "openai_output_file_id": result.output_file_id,
                "openai_error_file_id": result.error_file_id,
                "submitted_at": run_meta["submitted_at"],
                "retrieved_at": completed_at,
                "notes": run_meta["notes"],
            },
            "batches": sorted(batch_results, key=lambda row: row["batch_number"]),
            "failures": failures,
            "items": sorted(results, key=lambda row: row["surface_form"]),
        }
        if output_json:
            output_path = Path(output_json)
        else:
            output_path = Path("tmp") / f"word-lemmatization-{run_id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        write_payload(psql, payload)
        update_batch_run_ids(
            psql,
            run_id=run_id,
            status=payload["run"]["status"],
            openai_output_file_id=result.output_file_id,
            openai_error_file_id=result.error_file_id,
            retrieved_at=completed_at,
        )
        print(
            f"Fetched run {run_id}: {len(results)} forms, "
            f"{input_tokens + output_tokens} API tokens "
            f"({input_tokens} input, {output_tokens} output), "
            f"{len(failures)} failures."
        )
        print(f"Saved JSON payload to {output_path}.")


def main() -> None:
    args = parse_arguments()
    psql = PsqlRunner(args.database_url, psql_bin=args.psql_bin, ssh_host=args.ssh_host)
    psql.run(schema_sql())
    if args.schema_only:
        print("Schema ensured.")
        return

    client = OpenAI(api_key=load_openai_api_key(args.openai_api_key_file))
    if args.check_batches:
        check_batch_api_runs(client=client, psql=psql, batch_run_id=args.batch_run_id)
        return
    if args.fetch_batches:
        fetch_batch_api_runs(
            client=client,
            psql=psql,
            batch_run_id=args.batch_run_id,
            output_json=args.output_json,
        )
        return

    excluded_books = parse_excluded_books(args.exclude_books)
    items, total_occurrences = collect_surface_forms(
        psql,
        source=args.source,
        excluded_books=excluded_books,
        prompt_version=args.prompt_version,
        sample_size=args.sample_size,
        sample_seed=args.sample_seed,
        stop_after=args.stop_after,
    )
    if not items:
        print("No unprocessed surface forms found.")
        return

    if args.use_batch_api:
        submit_batch_api_run(
            client=client,
            psql=psql,
            args=args,
            items=items,
            total_occurrences=total_occurrences,
            excluded_books=excluded_books,
        )
        return

    run_id = str(uuid.uuid4())
    started_at = now_iso()
    batch_items = batches(items, args.batch_size)
    print(
        f"Run {run_id}: lemmatizing {len(items)} surface forms in "
        f"{len(batch_items)} batches of up to {args.batch_size}."
    )

    results = []
    batch_results = []
    failures = []

    def process(batch_number: int, batch: list[dict]) -> dict:
        result = lemmatize_batch(client, model=args.model, batch=batch)
        return {"batch_number": batch_number, **result}

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = [
            executor.submit(process, batch_number, batch)
            for batch_number, batch in enumerate(batch_items, start=1)
        ]
        for future in as_completed(futures):
            try:
                result = future.result()
                batch_results.append(
                    {
                        "batch_number": result["batch_number"],
                        "item_count": len(result["items"]),
                        "input_tokens": result["input_tokens"],
                        "output_tokens": result["output_tokens"],
                    }
                )
                results.extend(result["items"])
                print(
                    f"Batch {result['batch_number']}: {len(result['items'])} forms, "
                    f"{result['input_tokens'] + result['output_tokens']} API tokens"
                )
            except Exception as exc:
                failures.append(str(exc))
                print(f"FAILED batch: {exc}")

    completed_at = now_iso()
    input_tokens = sum(row["input_tokens"] for row in batch_results)
    output_tokens = sum(row["output_tokens"] for row in batch_results)
    payload = {
        "run": {
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "model": args.model,
            "prompt_version": args.prompt_version,
            "status": "completed" if not failures else "completed_with_failures",
            "source_scope": f"{args.source};exclude_books={','.join(excluded_books)}",
            "batch_size": args.batch_size,
            "surface_form_count": len(results),
            "occurrence_count": sum(item["occurrence_count"] for item in results),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "failure_count": len(failures),
            "notes": (
                f"sample_size={args.sample_size}; stop_after={args.stop_after}; "
                f"sample_seed={args.sample_seed}; total_source_occurrences={total_occurrences}"
            ),
        },
        "batches": sorted(batch_results, key=lambda row: row["batch_number"]),
        "failures": failures,
        "items": sorted(results, key=lambda row: row["surface_form"]),
    }

    output_path = (
        Path(args.output_json)
        if args.output_json
        else Path("tmp") / f"word-lemmatization-{run_id}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_payload(psql, payload)
    print(f"Saved run {run_id} to database.")
    print(f"Saved JSON payload to {output_path}.")
    print(
        "Totals: "
        f"{len(results)} forms, {sum(item['occurrence_count'] for item in results)} occurrences, "
        f"{input_tokens + output_tokens} API tokens "
        f"({input_tokens} input, {output_tokens} output)."
    )


if __name__ == "__main__":
    main()
