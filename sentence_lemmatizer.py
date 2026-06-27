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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI


DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_PROMPT_VERSION = "greek-sentence-lemmas-v1"
DEFAULT_DATABASE_URL = "dbname=pausanias user=gregb"

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


def sql_nullable_integer(value) -> str:
    if value is None:
        return "NULL"
    return str(int(value))


def sql_integer(value) -> str:
    return str(int(value or 0))


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lemmatize Greek Pausanias sentences with the OpenAI API."
    )
    parser.add_argument(
        "--database-url",
        default=DEFAULT_DATABASE_URL,
        help=f"psql connection string (default: {DEFAULT_DATABASE_URL})",
    )
    parser.add_argument(
        "--ssh-host",
        default=None,
        help="Run psql through this SSH host, for example raksasa.",
    )
    parser.add_argument(
        "--psql-bin",
        default="psql",
        help="psql binary to use locally or on --ssh-host (default: psql)",
    )
    parser.add_argument(
        "--openai-api-key-file",
        default="~/.openai.key",
        help="File containing OpenAI API key (default: ~/.openai.key)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--prompt-version",
        default=DEFAULT_PROMPT_VERSION,
        help=f"Prompt/schema version (default: {DEFAULT_PROMPT_VERSION})",
    )
    parser.add_argument(
        "--stop-after",
        type=int,
        default=None,
        help="Maximum number of unprocessed sentences to lemmatize.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Deterministic random sample size instead of passage-order rows.",
    )
    parser.add_argument(
        "--sample-seed",
        default="sentence-lemma-sample-v1",
        help="Seed string used with --sample-size.",
    )
    parser.add_argument(
        "--exclude-books",
        default="",
        help="Comma-separated book numbers to skip, for example '4,8'.",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=None,
        help="Stop after total input+output tokens reach this budget.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent API calls (default: 1).",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional path to write the run payload as JSON.",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Create/refresh schema tables and exit.",
    )
    return parser.parse_args()


def load_openai_api_key(key_file: str) -> str:
    key_path = os.path.expanduser(key_file)
    with open(key_path, "r", encoding="utf-8") as handle:
        return handle.read().strip()


def parse_excluded_books(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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


def tokenize_greek(sentence: str) -> list[str]:
    return [match.group(0) for match in GREEK_TOKEN_RE.finditer(sentence or "")]


def schema_sql() -> str:
    return Path(__file__).resolve().parent.joinpath("database", "schema.sql").read_text(
        encoding="utf-8"
    )


def get_sentences(
    psql: PsqlRunner,
    *,
    prompt_version: str,
    excluded_books: list[str],
    limit: int | None,
    sample_size: int | None,
    sample_seed: str,
) -> list[dict[str, str]]:
    params = [sql_string(book) for book in excluded_books]
    book_filter = ""
    if params:
        book_filter = f"AND split_part(s.passage_id, '.', 1) <> ALL(ARRAY[{', '.join(params)}])"
    limit_value = sample_size or limit
    limit_clause = f"LIMIT {int(limit_value)}" if limit_value else ""
    if sample_size:
        order_clause = (
            "ORDER BY md5(s.passage_id || ':' || s.sentence_number::text || ':' "
            f"|| {sql_string(sample_seed)})"
        )
    else:
        order_clause = "ORDER BY string_to_array(s.passage_id, '.')::int[], s.sentence_number"
    sql = f"""
COPY (
    SELECT s.passage_id, s.sentence_number, s.sentence AS greek_sentence
    FROM greek_sentences s
    WHERE NOT EXISTS (
        SELECT 1
        FROM sentence_lemmatizations l
        WHERE l.passage_id = s.passage_id
          AND l.sentence_number = s.sentence_number
          AND l.prompt_version = {sql_string(prompt_version)}
    )
    {book_filter}
    {order_clause}
    {limit_clause}
) TO STDOUT WITH CSV HEADER;
"""
    return list(csv.DictReader(io.StringIO(psql.run(sql))))


def lemmatization_tool() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "save_lemmas",
                "description": "Save Greek lemmas aligned to the numbered tokens.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lemmas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "One Greek dictionary lemma per numbered token, in the same order."
                            ),
                        }
                    },
                    "required": ["lemmas"],
                },
            },
        }
    ]


def lemmatize_sentence(
    client: OpenAI,
    *,
    model: str,
    passage_id: str,
    sentence_number: int,
    sentence: str,
) -> dict:
    tokens = tokenize_greek(sentence)
    if not tokens:
        return {
            "lemmas": [],
            "tokens": [],
            "input_tokens": 0,
            "output_tokens": 0,
            "error": None,
        }

    numbered_tokens = "\n".join(f"{idx}. {token}" for idx, token in enumerate(tokens, 1))
    system_prompt = (
        "You lemmatize ancient Greek. Given a Pausanias sentence and a numbered "
        "list of Greek word tokens, return exactly one dictionary lemma for each "
        "token in the same order. Use Greek lemmas, not English glosses. For "
        "proper names, return the nominative dictionary form. For particles, "
        "articles, pronouns, and elided forms, return the standard dictionary "
        "headword. Do not add explanations."
    )
    user_content = (
        f"Passage {passage_id}, sentence {sentence_number}:\n\n"
        f"Sentence:\n{sentence}\n\n"
        f"Numbered tokens:\n{numbered_tokens}\n\n"
        "Return the aligned lemmas with save_lemmas."
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            tools=lemmatization_tool(),
            tool_choice={"type": "function", "function": {"name": "save_lemmas"}},
        )
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            return {
                "lemmas": [],
                "tokens": tokens,
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "error": "No tool call returned",
            }
        args = json.loads(tool_calls[0].function.arguments)
        lemmas = args.get("lemmas", [])
        if len(lemmas) != len(tokens):
            return {
                "lemmas": lemmas,
                "tokens": tokens,
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "error": f"Expected {len(tokens)} lemmas, got {len(lemmas)}",
            }
        return {
            "lemmas": lemmas,
            "tokens": tokens,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "error": None,
        }
    except Exception as exc:
        return {
            "lemmas": [],
            "tokens": tokens,
            "input_tokens": 0,
            "output_tokens": 0,
            "error": str(exc),
        }


def write_payload_to_database(psql: PsqlRunner, payload: dict) -> None:
    run = payload["run"]
    results = payload.get("results") or []
    run_values = ", ".join(
        [
            sql_string(run["run_id"]),
            sql_string(run["started_at"]),
            sql_string(run.get("completed_at") or ""),
            sql_string(run["model"]),
            sql_string(run["prompt_version"]),
            sql_string(run["status"]),
            sql_nullable_integer(run.get("token_budget")),
            sql_integer(run.get("input_tokens")),
            sql_integer(run.get("output_tokens")),
            sql_integer(run.get("processed_count")),
            sql_integer(run.get("token_count")),
            sql_integer(run.get("failure_count")),
            sql_string(run.get("notes") or ""),
        ]
    )
    sql = f"""
INSERT INTO sentence_lemmatization_runs (
    run_id, started_at, completed_at, model, prompt_version, status, token_budget,
    input_tokens, output_tokens, processed_count, token_count, failure_count, notes
)
VALUES ({run_values})
ON CONFLICT (run_id) DO UPDATE
SET completed_at = EXCLUDED.completed_at,
    status = EXCLUDED.status,
    input_tokens = EXCLUDED.input_tokens,
    output_tokens = EXCLUDED.output_tokens,
    processed_count = EXCLUDED.processed_count,
    token_count = EXCLUDED.token_count,
    failure_count = EXCLUDED.failure_count,
    notes = EXCLUDED.notes;
"""
    if results:
        analysis_values = []
        key_values = []
        token_values = []
        for result in results:
            passage_id = result["passage_id"]
            sentence_number = result["sentence_number"]
            analysis_values.append(
                "("
                + ", ".join(
                    [
                        sql_string(passage_id),
                        sql_integer(sentence_number),
                        sql_string(run["prompt_version"]),
                        sql_string(run["model"]),
                        sql_string(run["run_id"]),
                        sql_string(result["greek_sentence"]),
                        sql_integer(result.get("token_count")),
                        sql_integer(result.get("input_tokens")),
                        sql_integer(result.get("output_tokens")),
                        sql_string(run.get("completed_at") or ""),
                    ]
                )
                + ")"
            )
            key_values.append(
                "("
                + ", ".join(
                    [
                        sql_string(passage_id),
                        sql_integer(sentence_number),
                        sql_string(run["prompt_version"]),
                    ]
                )
                + ")"
            )
            for token in result.get("tokens") or []:
                token_values.append(
                    "("
                    + ", ".join(
                        [
                            sql_string(passage_id),
                            sql_integer(sentence_number),
                            sql_string(run["prompt_version"]),
                            sql_integer(token["token_index"]),
                            sql_string(token["surface_form"]),
                            sql_string(token["lemma"]),
                            sql_string(run.get("completed_at") or ""),
                        ]
                    )
                    + ")"
                )
        analysis_sql_values = ",\n    ".join(analysis_values)
        key_sql_values = ",\n    ".join(key_values)
        sql += f"""
INSERT INTO sentence_lemmatizations (
    passage_id, sentence_number, prompt_version, model, run_id, greek_sentence,
    token_count, input_tokens, output_tokens, created_at
)
VALUES
    {analysis_sql_values}
ON CONFLICT (passage_id, sentence_number, prompt_version) DO UPDATE
SET model = EXCLUDED.model,
    run_id = EXCLUDED.run_id,
    greek_sentence = EXCLUDED.greek_sentence,
    token_count = EXCLUDED.token_count,
    input_tokens = EXCLUDED.input_tokens,
    output_tokens = EXCLUDED.output_tokens,
    created_at = EXCLUDED.created_at;

WITH rows(passage_id, sentence_number, prompt_version) AS (
    VALUES
    {key_sql_values}
)
DELETE FROM sentence_lemma_tokens t
USING rows
WHERE t.passage_id = rows.passage_id
  AND t.sentence_number = rows.sentence_number
  AND t.prompt_version = rows.prompt_version;
"""
        if token_values:
            token_sql_values = ",\n    ".join(token_values)
            sql += f"""
INSERT INTO sentence_lemma_tokens (
    passage_id, sentence_number, prompt_version, token_index,
    surface_form, lemma, created_at
)
VALUES
    {token_sql_values};
"""
    psql.run(sql)


def main() -> None:
    args = parse_arguments()
    psql = PsqlRunner(args.database_url, psql_bin=args.psql_bin, ssh_host=args.ssh_host)
    psql.run(schema_sql())
    if args.schema_only:
        print("Schema ensured.")
        return

    client = OpenAI(api_key=load_openai_api_key(args.openai_api_key_file))
    excluded_books = parse_excluded_books(args.exclude_books)
    rows = get_sentences(
        psql,
        prompt_version=args.prompt_version,
        excluded_books=excluded_books,
        limit=args.stop_after,
        sample_size=args.sample_size,
        sample_seed=args.sample_seed,
    )
    if not rows:
        print("No unprocessed sentences found.")
        return

    run_id = str(uuid.uuid4())
    started_at = now_iso()
    print(
        f"Run {run_id}: lemmatizing {len(rows)} sentences with {args.model}; "
        f"exclude_books={','.join(excluded_books) or 'none'}."
    )

    results = []
    failures = []
    input_tokens = 0
    output_tokens = 0
    token_count = 0
    stop_submitting = False
    row_iter = iter(rows)
    pending = set()

    def submit_next(executor: ThreadPoolExecutor) -> bool:
        try:
            row = next(row_iter)
        except StopIteration:
            return False
        future = executor.submit(
            lemmatize_sentence,
            client,
            model=args.model,
            passage_id=row["passage_id"],
            sentence_number=int(row["sentence_number"]),
            sentence=row["greek_sentence"],
        )
        future.row = row
        pending.add(future)
        return True

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        for _ in range(max(1, args.concurrency)):
            if not submit_next(executor):
                break

        while pending:
            for future in as_completed(pending):
                pending.remove(future)
                row = future.row
                result = future.result()
                input_tokens += result["input_tokens"]
                output_tokens += result["output_tokens"]
                if result["error"]:
                    failures.append(
                        {
                            "passage_id": row["passage_id"],
                            "sentence_number": int(row["sentence_number"]),
                            "error": result["error"],
                        }
                    )
                    print(
                        f"FAILED {row['passage_id']} #{row['sentence_number']}: "
                        f"{result['error']}"
                    )
                else:
                    tokens = [
                        {
                            "token_index": idx,
                            "surface_form": surface,
                            "lemma": lemma,
                        }
                        for idx, (surface, lemma) in enumerate(
                            zip(result["tokens"], result["lemmas"]), start=1
                        )
                    ]
                    token_count += len(tokens)
                    results.append(
                        {
                            "passage_id": row["passage_id"],
                            "sentence_number": int(row["sentence_number"]),
                            "greek_sentence": row["greek_sentence"],
                            "token_count": len(tokens),
                            "input_tokens": result["input_tokens"],
                            "output_tokens": result["output_tokens"],
                            "tokens": tokens,
                        }
                    )
                    print(
                        f"Lemmatized {row['passage_id']} #{row['sentence_number']}: "
                        f"{len(tokens)} tokens, "
                        f"{result['input_tokens'] + result['output_tokens']} API tokens"
                    )

                if args.token_budget and input_tokens + output_tokens >= args.token_budget:
                    stop_submitting = True
                if not stop_submitting:
                    submit_next(executor)

    completed_at = now_iso()
    payload = {
        "run": {
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "model": args.model,
            "prompt_version": args.prompt_version,
            "status": "completed" if not failures else "completed_with_failures",
            "token_budget": args.token_budget,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "processed_count": len(results),
            "token_count": token_count,
            "failure_count": len(failures),
            "notes": (
                f"sample_size={args.sample_size}; stop_after={args.stop_after}; "
                f"exclude_books={','.join(excluded_books)}; sample_seed={args.sample_seed}"
            ),
        },
        "failures": failures,
        "results": results,
    }

    output_path = (
        Path(args.output_json)
        if args.output_json
        else Path("tmp") / f"sentence-lemmatization-{run_id}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_payload_to_database(psql, payload)
    print(f"Saved run {run_id} to database.")
    print(f"Saved JSON payload to {output_path}.")
    print(
        "Totals: "
        f"{len(results)} sentences, {token_count} Greek tokens, "
        f"{input_tokens + output_tokens} API tokens "
        f"({input_tokens} input, {output_tokens} output)."
    )


if __name__ == "__main__":
    main()
