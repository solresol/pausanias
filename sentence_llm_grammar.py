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
from typing import Any

from openai import OpenAI


DEFAULT_DATABASE_URL = "dbname=pausanias user=gregb"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_PROMPT_VERSION = "greek-sentence-grammar-v1"
DEFAULT_SAMPLE_SEED = "sentence-llm-grammar-sample-v1"
DEFAULT_BUDGET_TIMEZONE = "Australia/Sydney"
UPOS_TAGS = {
    "ADJ",
    "ADP",
    "ADV",
    "AUX",
    "CCONJ",
    "DET",
    "INTJ",
    "NOUN",
    "NUM",
    "PART",
    "PRON",
    "PROPN",
    "PUNCT",
    "SCONJ",
    "SYM",
    "VERB",
    "X",
}
GREEK_WORD_RE = (
    r"[\u0370-\u03ff\u1f00-\u1fff]+(?:[ʼ'’\u02bc](?=[\u0370-\u03ff\u1f00-\u1fff])"
    r"[\u0370-\u03ff\u1f00-\u1fff]+|[ʼ'’\u02bc])?"
)
LLM_TOKEN_RE = re.compile(rf"{GREEK_WORD_RE}|\d+(?:[.,]\d+)?|[^\s]")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def remove_postgres_nul_chars(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [remove_postgres_nul_chars(item) for item in value]
    if isinstance(value, dict):
        return {
            remove_postgres_nul_chars(key): remove_postgres_nul_chars(item)
            for key, item in value.items()
        }
    return value


def parse_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def effective_token_budget(
    *,
    token_budget: int | None,
    daily_token_budget: int | None,
    daily_tokens_used: int,
) -> int | None:
    if daily_token_budget is None:
        return token_budget
    daily_remaining = max(0, daily_token_budget - daily_tokens_used)
    if token_budget is None:
        return daily_remaining
    return min(token_budget, daily_remaining)


def total_api_tokens(run: dict) -> int:
    return int(run["input_tokens"]) + int(run["output_tokens"])


def load_openai_api_key(key_file: str) -> str:
    key_path = os.path.expanduser(key_file)
    with open(key_path, "r", encoding="utf-8") as handle:
        return handle.read().strip()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Annotate Pausanias Greek sentences with LLM-generated grammar "
            "analyses comparable to parser CoNLL-U output."
        )
    )
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--ssh-host", default=None)
    parser.add_argument("--psql-bin", default="psql")
    parser.add_argument("--openai-api-key-file", default="~/.openai.key")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION)
    parser.add_argument("--stop-after", type=int, default=None)
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--sample-seed", default=DEFAULT_SAMPLE_SEED)
    parser.add_argument(
        "--random-order",
        action="store_true",
        help="Process unannotated sentences in seeded pseudo-random order.",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=None,
        help=(
            "Soft maximum API tokens for this run. With concurrency or write "
            "batches above 1, the run can exceed this by the final in-flight batch."
        ),
    )
    parser.add_argument(
        "--daily-token-budget",
        type=int,
        default=None,
        help=(
            "Soft maximum API tokens per day for this model/prompt version, "
            "counted from stored successful analyses."
        ),
    )
    parser.add_argument(
        "--budget-timezone",
        default=DEFAULT_BUDGET_TIMEZONE,
        help=(
            "--daily-token-budget day-boundary timezone "
            f"(default: {DEFAULT_BUDGET_TIMEZONE})."
        ),
    )
    parser.add_argument("--exclude-books", default="")
    parser.add_argument("--passage-id", default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--write-batch-size", type=int, default=20)
    parser.add_argument(
        "--max-failures",
        type=int,
        default=None,
        help="Stop the run after this many failed sentence analyses.",
    )
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--schema-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


class PsqlRunner:
    def __init__(self, database_url: str, *, psql_bin: str = "psql", ssh_host: str | None = None):
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


def schema_sql() -> str:
    return (Path(__file__).resolve().parent / "database" / "schema.sql").read_text(
        encoding="utf-8"
    )


def get_daily_token_usage(
    psql: PsqlRunner,
    *,
    model: str,
    prompt_version: str,
    budget_timezone: str,
) -> int:
    sql = f"""
COPY (
    WITH bounds AS (
        SELECT
            (date_trunc('day', timezone({sql_string(budget_timezone)}, now()))
                AT TIME ZONE {sql_string(budget_timezone)}) AS day_start,
            ((date_trunc('day', timezone({sql_string(budget_timezone)}, now()))
                + interval '1 day') AT TIME ZONE {sql_string(budget_timezone)}) AS day_end
    )
    SELECT COALESCE(SUM(a.input_tokens + a.output_tokens), 0)::bigint AS token_count
    FROM sentence_llm_grammar_analyses a
    CROSS JOIN bounds
    WHERE a.model = {sql_string(model)}
      AND a.prompt_version = {sql_string(prompt_version)}
      AND a.created_at::timestamptz >= bounds.day_start
      AND a.created_at::timestamptz < bounds.day_end
) TO STDOUT WITH CSV HEADER;
"""
    rows = list(csv.DictReader(io.StringIO(psql.run(sql))))
    if not rows:
        return 0
    return int(rows[0]["token_count"] or 0)


def tokenize_for_llm(sentence: str) -> list[str]:
    return [match.group(0) for match in LLM_TOKEN_RE.finditer(sentence or "")]


def parse_conllu_mapping(raw: str | None) -> dict[str, str]:
    if not raw or raw == "_":
        return {}
    values: dict[str, str] = {}
    for part in raw.split("|"):
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
        else:
            key, value = part, ""
        values[key] = value
    return values


def format_feats(feats: Any) -> tuple[str, dict[str, str]]:
    if not feats:
        return "_", {}
    if isinstance(feats, str):
        parsed = parse_conllu_mapping(feats)
    elif isinstance(feats, dict):
        parsed = {
            str(key): str(value)
            for key, value in feats.items()
            if value is not None and str(value) != ""
        }
    else:
        parsed = {}
    if not parsed:
        return "_", {}
    raw = "|".join(f"{key}={parsed[key]}" for key in sorted(parsed))
    return raw, parsed


def none_if_blank(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return None if not text or text == "_" else text


def safe_usage(response) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    if not usage:
        return 0, 0
    return int(getattr(usage, "prompt_tokens", 0) or 0), int(
        getattr(usage, "completion_tokens", 0) or 0
    )


def grammar_tool() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "save_sentence_grammar",
                "description": (
                    "Save token-aligned Ancient Greek grammar in parser-style fields."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tokens": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "token_index": {
                                        "type": "integer",
                                        "description": "1-based token index from the input list.",
                                    },
                                    "form": {
                                        "type": "string",
                                        "description": "Exact token form copied from the input list.",
                                    },
                                    "lemma": {
                                        "type": "string",
                                        "description": (
                                            "Greek dictionary lemma; use nominative for names."
                                        ),
                                    },
                                    "upos": {
                                        "type": "string",
                                        "enum": sorted(UPOS_TAGS),
                                        "description": "Universal Dependencies UPOS tag.",
                                    },
                                    "xpos": {
                                        "type": "string",
                                        "description": (
                                            "Detailed Ancient Greek morphology code, "
                                            "or '_' if not confident."
                                        ),
                                    },
                                    "feats": {
                                        "type": "object",
                                        "additionalProperties": {"type": "string"},
                                        "description": (
                                            "UD-style morphology features, e.g. Case, "
                                            "Gender, Number, Mood, Tense, Voice."
                                        ),
                                    },
                                    "head": {
                                        "type": "integer",
                                        "description": (
                                            "Syntactic head token index, or 0 for the root."
                                        ),
                                    },
                                    "deprel": {
                                        "type": "string",
                                        "description": "UD-style dependency relation label.",
                                    },
                                    "confidence": {
                                        "type": "string",
                                        "enum": ["high", "medium", "low"],
                                    },
                                    "note": {
                                        "type": "string",
                                        "description": "Short note for ambiguity or uncertainty.",
                                    },
                                },
                                "required": [
                                    "token_index",
                                    "form",
                                    "lemma",
                                    "upos",
                                    "xpos",
                                    "feats",
                                    "head",
                                    "deprel",
                                    "confidence",
                                    "note",
                                ],
                            },
                        },
                        "sentence_note": {
                            "type": "string",
                            "description": "One short sentence-level note about difficult syntax.",
                        },
                    },
                    "required": ["tokens", "sentence_note"],
                },
            },
        }
    ]


def completion_messages(*, passage_id: str, sentence_number: int, sentence: str, tokens: list[str]):
    numbered_tokens = "\n".join(f"{index}. {token}" for index, token in enumerate(tokens, 1))
    system_prompt = (
        "You are an expert Ancient Greek morphosyntactic annotator. Annotate "
        "Pausanias sentence tokens with the same kind of information produced by "
        "dependency parsers: lemma, UPOS, detailed morphology, UD-style features, "
        "head token, and dependency relation. Work token-by-token against the "
        "numbered input list. Do not add, remove, split, merge, or reorder tokens. "
        "Use head=0 for the syntactic root. Use Greek lemmas rather than English "
        "glosses. For punctuation, use upos=PUNCT, lemma equal to the mark, and "
        "empty features. Prefer explicit uncertainty in confidence/note over "
        "inventing impossible morphology."
    )
    user_content = (
        f"Passage {passage_id}, sentence {sentence_number}:\n\n"
        f"Greek sentence:\n{sentence}\n\n"
        f"Numbered tokens:\n{numbered_tokens}\n\n"
        "Call save_sentence_grammar with exactly one output token object for each "
        "numbered token."
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def validate_and_normalize_tokens(raw_tokens: list[dict], expected_tokens: list[str]) -> list[dict]:
    if len(raw_tokens) != len(expected_tokens):
        raise ValueError(f"Expected {len(expected_tokens)} tokens, got {len(raw_tokens)}")

    normalized = []
    for index, (raw, expected_form) in enumerate(zip(raw_tokens, expected_tokens), start=1):
        token_index = int(raw.get("token_index", 0))
        form = str(raw.get("form", ""))
        if token_index != index:
            raise ValueError(f"Expected token_index {index}, got {token_index}")
        if form != expected_form:
            raise ValueError(f"Expected form {expected_form!r} at {index}, got {form!r}")

        upos = str(raw.get("upos", "")).upper()
        if upos not in UPOS_TAGS:
            raise ValueError(f"Invalid UPOS {upos!r} at token {index}")

        head = int(raw.get("head", -1))
        if head < 0 or head > len(expected_tokens):
            raise ValueError(f"Invalid head {head} at token {index}")
        if head == index:
            raise ValueError(f"Token {index} cannot be its own head")

        feats_raw, feats = format_feats(raw.get("feats"))
        normalized.append(
            {
                "token_order": index,
                "token_id": str(index),
                "form": form,
                "lemma": none_if_blank(raw.get("lemma")) or form,
                "upos": upos,
                "xpos": none_if_blank(raw.get("xpos")),
                "feats_raw": feats_raw,
                "feats": feats,
                "head_token_id": str(head),
                "deprel": none_if_blank(raw.get("deprel")) or "dep",
                "confidence": none_if_blank(raw.get("confidence")) or "medium",
                "note": none_if_blank(raw.get("note")) or "",
                "is_multiword_token": False,
                "is_empty_node": False,
            }
        )
    return normalized


def tokens_to_conllu(tokens: list[dict]) -> str:
    lines = []
    for token in tokens:
        lines.append(
            "\t".join(
                [
                    token["token_id"],
                    token["form"],
                    token["lemma"] or "_",
                    token["upos"] or "_",
                    token["xpos"] or "_",
                    token["feats_raw"] or "_",
                    token["head_token_id"] or "_",
                    token["deprel"] or "_",
                    "_",
                    "_",
                ]
            )
        )
    return "\n".join(lines) + "\n"


def analyse_sentence(
    client: OpenAI,
    *,
    model: str,
    passage_id: str,
    sentence_number: int,
    sentence: str,
) -> dict:
    expected_tokens = tokenize_for_llm(sentence)
    if not expected_tokens:
        return {
            "tokens": [],
            "conllu": "",
            "response_json": {},
            "sentence_note": "No tokens found.",
            "input_tokens": 0,
            "output_tokens": 0,
            "error": None,
        }

    response = client.chat.completions.create(
        model=model,
        messages=completion_messages(
            passage_id=passage_id,
            sentence_number=sentence_number,
            sentence=sentence,
            tokens=expected_tokens,
        ),
        tools=grammar_tool(),
        tool_choice={"type": "function", "function": {"name": "save_sentence_grammar"}},
    )
    input_tokens, output_tokens = safe_usage(response)
    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise ValueError("No tool call returned")

    response_json = json.loads(tool_calls[0].function.arguments)
    raw_tokens = response_json.get("tokens") or []
    normalized_tokens = validate_and_normalize_tokens(raw_tokens, expected_tokens)
    sentence_note = str(response_json.get("sentence_note") or "").strip()
    return {
        "tokens": normalized_tokens,
        "conllu": tokens_to_conllu(normalized_tokens),
        "response_json": response_json,
        "sentence_note": sentence_note,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "error": None,
    }


def get_sentences(
    psql: PsqlRunner,
    *,
    model: str,
    prompt_version: str,
    overwrite: bool,
    excluded_books: list[str],
    passage_id: str | None,
    limit: int | None,
    sample_size: int | None,
    sample_seed: str,
    random_order: bool,
) -> list[dict]:
    clauses = ["TRUE"]
    if not overwrite:
        clauses.append(
            f"""
            NOT EXISTS (
                SELECT 1
                FROM sentence_llm_grammar_analyses a
                WHERE a.passage_id = s.passage_id
                  AND a.sentence_number = s.sentence_number
                  AND a.model = {sql_string(model)}
                  AND a.prompt_version = {sql_string(prompt_version)}
            )
            """
        )
    if excluded_books:
        books = ", ".join(sql_string(book) for book in excluded_books)
        clauses.append(f"split_part(s.passage_id, '.', 1) <> ALL(ARRAY[{books}])")
    if passage_id:
        clauses.append(f"s.passage_id = {sql_string(passage_id)}")

    limit_value = sample_size or limit
    limit_clause = f"LIMIT {int(limit_value)}" if limit_value else ""
    if sample_size or random_order:
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
    WHERE {' AND '.join(clauses)}
    {order_clause}
    {limit_clause}
) TO STDOUT WITH CSV HEADER;
"""
    rows = list(csv.DictReader(io.StringIO(psql.run(sql))))
    for row in rows:
        row["sentence_number"] = int(row["sentence_number"])
    return rows


def write_payload(psql: PsqlRunner, payload: dict) -> None:
    tag = f"json_{payload['run']['run_id'].replace('-', '_')}"
    payload_json = json.dumps(remove_postgres_nul_chars(payload), ensure_ascii=False)
    sql = f"""
WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS j
), run_row AS (
    SELECT j->'run' AS r FROM payload
)
INSERT INTO sentence_llm_grammar_runs (
    run_id, started_at, completed_at, model, prompt_version, status,
    input_tokens, output_tokens, processed_count, token_count, failure_count, notes
)
SELECT
    r->>'run_id',
    r->>'started_at',
    r->>'completed_at',
    r->>'model',
    r->>'prompt_version',
    r->>'status',
    (r->>'input_tokens')::integer,
    (r->>'output_tokens')::integer,
    (r->>'processed_count')::integer,
    (r->>'token_count')::integer,
    (r->>'failure_count')::integer,
    r->>'notes'
FROM run_row
ON CONFLICT (run_id) DO UPDATE
SET completed_at = EXCLUDED.completed_at,
    status = EXCLUDED.status,
    input_tokens = EXCLUDED.input_tokens,
    output_tokens = EXCLUDED.output_tokens,
    processed_count = EXCLUDED.processed_count,
    token_count = EXCLUDED.token_count,
    failure_count = EXCLUDED.failure_count,
    notes = EXCLUDED.notes;

WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS j
), run_row AS (
    SELECT j->'run' AS r FROM payload
), rows AS (
    SELECT *
    FROM jsonb_to_recordset((SELECT j->'results' FROM payload)) AS x(
        passage_id text,
        sentence_number integer,
        greek_sentence text,
        conllu text,
        response_json jsonb,
        sentence_note text,
        input_tokens integer,
        output_tokens integer,
        token_count integer,
        tokens jsonb
    )
)
INSERT INTO sentence_llm_grammar_analyses (
    passage_id, sentence_number, model, prompt_version, run_id, greek_sentence,
    conllu, response_json, sentence_note, input_tokens, output_tokens, token_count,
    created_at
)
SELECT
    rows.passage_id,
    rows.sentence_number,
    run_row.r->>'model',
    run_row.r->>'prompt_version',
    run_row.r->>'run_id',
    rows.greek_sentence,
    rows.conllu,
    rows.response_json,
    rows.sentence_note,
    rows.input_tokens,
    rows.output_tokens,
    rows.token_count,
    run_row.r->>'completed_at'
FROM rows CROSS JOIN run_row
ON CONFLICT (passage_id, sentence_number, model, prompt_version) DO UPDATE
SET run_id = EXCLUDED.run_id,
    greek_sentence = EXCLUDED.greek_sentence,
    conllu = EXCLUDED.conllu,
    response_json = EXCLUDED.response_json,
    sentence_note = EXCLUDED.sentence_note,
    input_tokens = EXCLUDED.input_tokens,
    output_tokens = EXCLUDED.output_tokens,
    token_count = EXCLUDED.token_count,
    created_at = EXCLUDED.created_at;

WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS j
), run_row AS (
    SELECT j->'run' AS r FROM payload
), rows AS (
    SELECT x.passage_id, x.sentence_number, run_row.r->>'model' AS model,
           run_row.r->>'prompt_version' AS prompt_version
    FROM run_row,
         jsonb_to_recordset((SELECT j->'results' FROM payload)) AS x(
            passage_id text,
            sentence_number integer
         )
)
DELETE FROM sentence_llm_grammar_tokens t
USING rows
WHERE t.passage_id = rows.passage_id
  AND t.sentence_number = rows.sentence_number
  AND t.model = rows.model
  AND t.prompt_version = rows.prompt_version;

WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS j
), run_row AS (
    SELECT j->'run' AS r FROM payload
), rows AS (
    SELECT *
    FROM jsonb_to_recordset((SELECT j->'results' FROM payload)) AS x(
        passage_id text,
        sentence_number integer,
        tokens jsonb
    )
)
INSERT INTO sentence_llm_grammar_tokens (
    passage_id, sentence_number, model, prompt_version, token_order, token_id,
    form, lemma, upos, xpos, feats_raw, feats, head_token_id, deprel, confidence,
    note, is_multiword_token, is_empty_node, created_at
)
SELECT
    rows.passage_id,
    rows.sentence_number,
    run_row.r->>'model',
    run_row.r->>'prompt_version',
    tok.token_order,
    tok.token_id,
    tok.form,
    tok.lemma,
    tok.upos,
    tok.xpos,
    tok.feats_raw,
    tok.feats,
    tok.head_token_id,
    tok.deprel,
    tok.confidence,
    tok.note,
    tok.is_multiword_token,
    tok.is_empty_node,
    run_row.r->>'completed_at'
FROM rows
CROSS JOIN run_row
CROSS JOIN LATERAL jsonb_to_recordset(rows.tokens) AS tok(
    token_order integer,
    token_id text,
    form text,
    lemma text,
    upos text,
    xpos text,
    feats_raw text,
    feats jsonb,
    head_token_id text,
    deprel text,
    confidence text,
    note text,
    is_multiword_token boolean,
    is_empty_node boolean
);
"""
    psql.run(sql)


def output_payload(path: str | None, payload: dict) -> None:
    if not path:
        return
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved JSON payload to {output_path}.")


def analyse_row(client: OpenAI, model: str, row: dict) -> dict:
    try:
        result = analyse_sentence(
            client,
            model=model,
            passage_id=row["passage_id"],
            sentence_number=row["sentence_number"],
            sentence=row["greek_sentence"],
        )
        return {
            "passage_id": row["passage_id"],
            "sentence_number": row["sentence_number"],
            "greek_sentence": row["greek_sentence"],
            "conllu": result["conllu"],
            "response_json": result["response_json"],
            "sentence_note": result["sentence_note"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "token_count": len(result["tokens"]),
            "tokens": result["tokens"],
            "error": None,
        }
    except Exception as exc:
        return {
            "passage_id": row["passage_id"],
            "sentence_number": row["sentence_number"],
            "greek_sentence": row["greek_sentence"],
            "input_tokens": 0,
            "output_tokens": 0,
            "token_count": 0,
            "tokens": [],
            "error": str(exc),
        }


def batched(rows: list[dict], batch_size: int):
    for index in range(0, len(rows), batch_size):
        yield rows[index : index + batch_size]


def main() -> None:
    args = parse_arguments()
    psql = PsqlRunner(args.database_url, psql_bin=args.psql_bin, ssh_host=args.ssh_host)
    psql.run(schema_sql())
    if args.schema_only:
        print("Schema ensured.")
        return

    daily_tokens_used = 0
    run_token_budget = args.token_budget
    if args.daily_token_budget is not None:
        daily_tokens_used = get_daily_token_usage(
            psql,
            model=args.model,
            prompt_version=args.prompt_version,
            budget_timezone=args.budget_timezone,
        )
        run_token_budget = effective_token_budget(
            token_budget=args.token_budget,
            daily_token_budget=args.daily_token_budget,
            daily_tokens_used=daily_tokens_used,
        )
        if run_token_budget <= 0:
            print(
                "Daily LLM grammar token budget exhausted: "
                f"{daily_tokens_used}/{args.daily_token_budget} tokens used today "
                f"for {args.model}/{args.prompt_version} "
                f"({args.budget_timezone})."
            )
            return

    rows = get_sentences(
        psql,
        model=args.model,
        prompt_version=args.prompt_version,
        overwrite=args.overwrite,
        excluded_books=parse_list(args.exclude_books),
        passage_id=args.passage_id,
        limit=args.stop_after,
        sample_size=args.sample_size,
        sample_seed=args.sample_seed,
        random_order=args.random_order,
    )
    if not rows:
        print(f"No unprocessed LLM grammar rows found for {args.model}/{args.prompt_version}.")
        return

    run = {
        "run_id": str(uuid.uuid4()),
        "started_at": now_iso(),
        "completed_at": "",
        "model": args.model,
        "prompt_version": args.prompt_version,
        "status": "dry_run" if args.dry_run else "running",
        "input_tokens": 0,
        "output_tokens": 0,
        "processed_count": 0,
        "token_count": 0,
        "failure_count": 0,
        "notes": (
            f"sample_size={args.sample_size}; stop_after={args.stop_after}; "
            f"sample_seed={args.sample_seed}; exclude_books={args.exclude_books}; "
            f"passage_id={args.passage_id}; overwrite={args.overwrite}; "
            f"concurrency={args.concurrency}; random_order={args.random_order}; "
            f"token_budget={args.token_budget}; daily_token_budget={args.daily_token_budget}; "
            f"daily_tokens_used={daily_tokens_used}; effective_token_budget={run_token_budget}; "
            f"budget_timezone={args.budget_timezone}; max_failures={args.max_failures}"
        ),
    }
    payload = {"run": run, "results": [], "failures": []}
    if not args.dry_run:
        write_payload(psql, payload)

    print(
        f"Run {run['run_id']}: analysing {len(rows)} sentences with "
        f"{args.model}/{args.prompt_version}; "
        f"token budget={run_token_budget if run_token_budget is not None else 'none'}."
    )
    client = OpenAI(api_key=load_openai_api_key(args.openai_api_key_file))
    write_batch_size = max(1, args.write_batch_size)
    pending_results: list[dict] = []
    concurrency = max(1, args.concurrency)
    budget_hit = False
    failure_limit_hit = False

    for batch in batched(rows, write_batch_size):
        if concurrency == 1:
            analysed = [analyse_row(client, args.model, row) for row in batch]
        else:
            analysed = []
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {
                    executor.submit(analyse_row, client, args.model, row): row
                    for row in batch
                }
                for future in as_completed(futures):
                    analysed.append(future.result())
            order = {
                (row["passage_id"], row["sentence_number"]): index
                for index, row in enumerate(batch)
            }
            analysed.sort(key=lambda row: order[(row["passage_id"], row["sentence_number"])])

        for result in analysed:
            run["input_tokens"] += result["input_tokens"]
            run["output_tokens"] += result["output_tokens"]
            if result.get("error"):
                run["failure_count"] += 1
                payload["failures"].append(
                    {
                        "passage_id": result["passage_id"],
                        "sentence_number": result["sentence_number"],
                        "error": result["error"],
                    }
                )
                print(
                    f"FAILED {result['passage_id']} #{result['sentence_number']}: "
                    f"{result['error']}",
                    file=sys.stderr,
                )
                continue
            run["processed_count"] += 1
            run["token_count"] += result["token_count"]
            pending_results.append(result)
            payload["results"].append(result)

        if pending_results and not args.dry_run:
            run["completed_at"] = now_iso()
            write_payload(psql, {"run": run, "results": pending_results, "failures": []})
            print(
                f"Saved {len(pending_results)} sentence analyses "
                f"({run['processed_count']}/{len(rows)} complete)."
            )
            pending_results = []
        if run_token_budget is not None and total_api_tokens(run) >= run_token_budget:
            budget_hit = True
            print(
                f"Reached token budget after {total_api_tokens(run)} API tokens; "
                "stopping before the next batch."
            )
            break
        if args.max_failures is not None and run["failure_count"] >= args.max_failures:
            failure_limit_hit = True
            print(
                f"Reached failure limit after {run['failure_count']} failed analyses; "
                "stopping before the next batch."
            )
            break

    run["completed_at"] = now_iso()
    if args.dry_run:
        run["status"] = "dry_run"
    elif failure_limit_hit:
        run["status"] = "failed_failure_limit"
    elif budget_hit and run["failure_count"]:
        run["status"] = "completed_with_failures_budget_exhausted"
    elif budget_hit:
        run["status"] = "completed_budget_exhausted"
    elif run["failure_count"]:
        run["status"] = "completed_with_failures"
    else:
        run["status"] = "completed"
    if not args.dry_run:
        write_payload(psql, payload)
    output_payload(args.output_json, payload)
    print(
        f"Totals: {run['processed_count']} sentences, {run['token_count']} tokens, "
        f"{run['failure_count']} failures, {run['input_tokens']} input tokens, "
        f"{run['output_tokens']} output tokens."
    )


if __name__ == "__main__":
    main()
