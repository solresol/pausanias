#!/usr/bin/env python

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shlex
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve

from pausanias_db import schema_path


DEFAULT_DATABASE_URL = "dbname=pausanias user=gregb"
DEFAULT_MODEL_NAME = "ancient_greek-perseus-ud-2.5-191206"
DEFAULT_MODEL_FILENAME = f"{DEFAULT_MODEL_NAME}.udpipe"
DEFAULT_MODEL_DIR = Path("models") / "udpipe"
DEFAULT_MODEL_URL = (
    "https://raw.githubusercontent.com/jwijffels/udpipe.models.ud.2.5/master/"
    "inst/udpipe-ud-2.5-191206/ancient_greek-perseus-ud-2.5-191206.udpipe"
)
GREEK_WORD_RE = (
    r"[\u0370-\u03ff\u1f00-\u1fff]+(?:[ʼ'’\u02bc](?=[\u0370-\u03ff\u1f00-\u1fff])"
    r"[\u0370-\u03ff\u1f00-\u1fff]+|[ʼ'’\u02bc])?"
)
UDPIPE_TOKEN_RE = re.compile(rf"{GREEK_WORD_RE}|\d+(?:[.,]\d+)?|[^\s]")


@dataclass(frozen=True)
class LoadedUdpipePipeline:
    model: Any
    pipeline: Any


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


def parse_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Annotate Pausanias Greek sentences with UDPipe grammar data."
    )
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--ssh-host", default=None)
    parser.add_argument("--psql-bin", default="psql")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR))
    parser.add_argument("--model-url", default=DEFAULT_MODEL_URL)
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Fail if --model-path/default model is missing instead of downloading it.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Download the model even if the target path already exists.",
    )
    parser.add_argument(
        "--input-format",
        default="horizontal",
        choices=("tokenize", "horizontal", "vertical", "conllu"),
        help=(
            "UDPipe input format. The bundled Ancient Greek model expects "
            "pre-tokenized 'horizontal' input."
        ),
    )
    parser.add_argument("--stop-after", type=int, default=None)
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--sample-seed", default="sentence-udpipe-sample-v1")
    parser.add_argument("--exclude-books", default="")
    parser.add_argument("--passage-id", default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--write-batch-size", type=int, default=100)
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
    return schema_path().read_text(encoding="utf-8")


def model_path_for(args: argparse.Namespace) -> Path:
    if args.model_path:
        return Path(args.model_path).expanduser()
    filename = Path(args.model_url).name or DEFAULT_MODEL_FILENAME
    return Path(args.model_dir).expanduser() / filename


def ensure_model(args: argparse.Namespace) -> Path:
    path = model_path_for(args)
    if path.exists() and not args.force_download:
        return path
    if args.no_download:
        raise FileNotFoundError(f"UDPipe model not found: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = path.with_suffix(path.suffix + ".part")
    print(f"Downloading UDPipe model from {args.model_url}")
    print("Model license: CC BY-NC-SA 4.0; keep the downloaded model out of git.")
    urlretrieve(args.model_url, partial_path)
    partial_path.replace(path)
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_pipeline(model_path: Path, input_format: str) -> LoadedUdpipePipeline:
    from ufal.udpipe import Model, Pipeline

    model = Model.load(str(model_path))
    if not model:
        raise RuntimeError(f"Could not load UDPipe model: {model_path}")
    pipeline = Pipeline(model, input_format, Pipeline.DEFAULT, Pipeline.DEFAULT, "conllu")
    return LoadedUdpipePipeline(model=model, pipeline=pipeline)


def parse_conllu_mapping(raw: str) -> dict[str, str]:
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


def parse_conllu_deps(raw: str) -> list[dict[str, str]]:
    if not raw or raw == "_":
        return []
    deps: list[dict[str, str]] = []
    for part in raw.split("|"):
        if not part:
            continue
        if ":" in part:
            head, deprel = part.split(":", 1)
        else:
            head, deprel = part, ""
        deps.append({"head": head, "deprel": deprel})
    return deps


def tokenize_for_udpipe(sentence: str) -> list[str]:
    return [match.group(0) for match in UDPIPE_TOKEN_RE.finditer(sentence or "")]


def format_udpipe_input(sentence: str, input_format: str) -> str:
    if input_format == "horizontal":
        return " ".join(tokenize_for_udpipe(sentence)) + "\n"
    if input_format == "vertical":
        return "\n".join(tokenize_for_udpipe(sentence)) + "\n\n"
    return sentence


def none_if_blank(raw: str) -> str | None:
    return None if raw == "_" else raw


def parse_conllu_tokens(conllu: str) -> list[dict]:
    tokens: list[dict] = []
    token_order = 0
    for line in conllu.splitlines():
        if not line or line.startswith("#"):
            continue
        columns = line.split("\t")
        if len(columns) != 10:
            raise ValueError(f"Expected 10 CoNLL-U columns, got {len(columns)}: {line}")
        (
            token_id,
            form,
            lemma,
            upos,
            xpos,
            feats_raw,
            head,
            deprel,
            deps_raw,
            misc_raw,
        ) = columns
        token_order += 1
        tokens.append(
            {
                "token_order": token_order,
                "token_id": token_id,
                "form": form,
                "lemma": none_if_blank(lemma),
                "upos": none_if_blank(upos),
                "xpos": none_if_blank(xpos),
                "feats_raw": feats_raw,
                "feats": parse_conllu_mapping(feats_raw),
                "head_token_id": none_if_blank(head),
                "deprel": none_if_blank(deprel),
                "deps_raw": deps_raw,
                "deps": parse_conllu_deps(deps_raw),
                "misc_raw": misc_raw,
                "misc": parse_conllu_mapping(misc_raw),
                "is_multiword_token": "-" in token_id,
                "is_empty_node": "." in token_id,
            }
        )
    return tokens


def syntactic_token_count(tokens: list[dict]) -> int:
    return sum(
        1
        for token in tokens
        if not token["is_multiword_token"] and not token["is_empty_node"]
    )


def analyse_sentence(
    pipeline: LoadedUdpipePipeline,
    sentence: str,
    *,
    input_format: str = "horizontal",
) -> tuple[str, list[dict]]:
    from ufal.udpipe import ProcessingError

    error = ProcessingError()
    conllu = pipeline.pipeline.process(format_udpipe_input(sentence, input_format), error)
    if error.occurred():
        raise RuntimeError(error.message)
    tokens = parse_conllu_tokens(conllu)
    if not tokens:
        raise ValueError("UDPipe returned no tokens")
    return conllu, tokens


def get_sentences(
    psql: PsqlRunner,
    *,
    model_name: str,
    overwrite: bool,
    excluded_books: list[str],
    passage_id: str | None,
    limit: int | None,
    sample_size: int | None,
    sample_seed: str,
) -> list[dict]:
    clauses = ["TRUE"]
    if not overwrite:
        clauses.append(
            f"""
            NOT EXISTS (
                SELECT 1
                FROM sentence_udpipe_analyses a
                WHERE a.passage_id = s.passage_id
                  AND a.sentence_number = s.sentence_number
                  AND a.model_name = {sql_string(model_name)}
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
    WHERE {' AND '.join(clauses)}
    {order_clause}
    {limit_clause}
) TO STDOUT WITH CSV HEADER;
"""
    rows = list(csv.DictReader(io.StringIO(psql.run(sql))))
    for row in rows:
        row["sentence_number"] = int(row["sentence_number"])
    return rows


def write_run(psql: PsqlRunner, run: dict) -> None:
    run_values = ", ".join(
        [
            sql_string(run["run_id"]),
            sql_string(run["started_at"]),
            sql_nullable_text(run.get("completed_at")),
            sql_string(run["model_name"]),
            sql_string(run["model_path"]),
            sql_string(run["model_sha256"]),
            sql_string(run["udpipe_version"]),
            sql_string(run["input_format"]),
            sql_string(run["status"]),
            sql_integer(run.get("processed_count")),
            sql_integer(run.get("token_count")),
            sql_integer(run.get("failure_count")),
            sql_nullable_text(run.get("notes"))
        ]
    )
    sql = f"""
INSERT INTO sentence_udpipe_runs (
    run_id, started_at, completed_at, model_name, model_path, model_sha256,
    udpipe_version, input_format, status, processed_count, token_count,
    failure_count, notes
)
VALUES ({run_values})
ON CONFLICT (run_id) DO UPDATE
SET completed_at = EXCLUDED.completed_at,
    status = EXCLUDED.status,
    processed_count = EXCLUDED.processed_count,
    token_count = EXCLUDED.token_count,
    failure_count = EXCLUDED.failure_count,
    notes = EXCLUDED.notes;
"""
    psql.run(sql)


def write_results(psql: PsqlRunner, run: dict, results: list[dict]) -> None:
    if not results:
        return
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
                    sql_string(run["model_name"]),
                    sql_string(run["run_id"]),
                    sql_string(result["greek_sentence"]),
                    sql_string(result["conllu"]),
                    sql_integer(result.get("token_count")),
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
                    sql_string(run["model_name"]),
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
                        sql_string(run["model_name"]),
                        sql_integer(token["token_order"]),
                        sql_string(token["token_id"]),
                        sql_string(token["form"]),
                        sql_nullable_text(token.get("lemma")),
                        sql_nullable_text(token.get("upos")),
                        sql_nullable_text(token.get("xpos")),
                        sql_string(token.get("feats_raw") or "_"),
                        "'{}'::jsonb",
                        sql_nullable_text(token.get("head_token_id")),
                        sql_nullable_text(token.get("deprel")),
                        sql_string(token.get("deps_raw") or "_"),
                        "'[]'::jsonb",
                        sql_string(token.get("misc_raw") or "_"),
                        "'{}'::jsonb",
                        sql_bool(token.get("is_multiword_token")),
                        sql_bool(token.get("is_empty_node")),
                        sql_string(run.get("completed_at") or ""),
                    ]
                )
                + ")"
            )
    analysis_sql_values = ",\n    ".join(analysis_values)
    key_sql_values = ",\n    ".join(key_values)
    sql = f"""
INSERT INTO sentence_udpipe_analyses (
    passage_id, sentence_number, model_name, run_id, greek_sentence,
    conllu, token_count, created_at
)
VALUES
    {analysis_sql_values}
ON CONFLICT (passage_id, sentence_number, model_name) DO UPDATE
SET run_id = EXCLUDED.run_id,
    greek_sentence = EXCLUDED.greek_sentence,
    conllu = EXCLUDED.conllu,
    token_count = EXCLUDED.token_count,
    created_at = EXCLUDED.created_at;

WITH rows(passage_id, sentence_number, model_name) AS (
    VALUES
    {key_sql_values}
)
DELETE FROM sentence_udpipe_tokens t
USING rows
WHERE t.passage_id = rows.passage_id
  AND t.sentence_number = rows.sentence_number
  AND t.model_name = rows.model_name;
"""
    if token_values:
        token_sql_values = ",\n    ".join(token_values)
        sql += f"""
INSERT INTO sentence_udpipe_tokens (
    passage_id, sentence_number, model_name, token_order, token_id, form,
    lemma, upos, xpos, feats_raw, feats, head_token_id, deprel, deps_raw,
    deps, misc_raw, misc, is_multiword_token, is_empty_node, created_at
)
VALUES
    {token_sql_values};
"""
    psql.run(sql)


def output_payload(path: str | None, run: dict, failures: list[dict], results: list[dict]) -> None:
    if not path:
        return
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"run": run, "failures": failures, "results": results}
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved JSON payload to {output_path}.")


def main() -> None:
    args = parse_arguments()
    psql = PsqlRunner(args.database_url, psql_bin=args.psql_bin, ssh_host=args.ssh_host)
    psql.run(schema_sql())
    if args.schema_only:
        print("Schema ensured.")
        return

    excluded_books = parse_list(args.exclude_books)
    model_path = ensure_model(args)
    model_sha256 = sha256_file(model_path)
    pipeline = load_pipeline(model_path, args.input_format)
    import ufal.udpipe as udpipe

    rows = get_sentences(
        psql,
        model_name=args.model_name,
        overwrite=args.overwrite,
        excluded_books=excluded_books,
        passage_id=args.passage_id,
        limit=args.stop_after,
        sample_size=args.sample_size,
        sample_seed=args.sample_seed,
    )
    if not rows:
        print(f"No unprocessed UDPipe rows found for model {args.model_name}.")
        return

    run = {
        "run_id": str(uuid.uuid4()),
        "started_at": now_iso(),
        "completed_at": "",
        "model_name": args.model_name,
        "model_path": str(model_path),
        "model_sha256": model_sha256,
        "udpipe_version": udpipe.__version__,
        "input_format": args.input_format,
        "status": "dry_run" if args.dry_run else "running",
        "processed_count": 0,
        "token_count": 0,
        "failure_count": 0,
        "notes": (
            f"model_url={args.model_url}; sample_size={args.sample_size}; "
            f"stop_after={args.stop_after}; exclude_books={','.join(excluded_books)}; "
            f"sample_seed={args.sample_seed}; passage_id={args.passage_id}; "
            f"overwrite={args.overwrite}"
        ),
    }
    if not args.dry_run:
        write_run(psql, run)

    print(
        f"Run {run['run_id']}: analysing {len(rows)} sentences with {args.model_name} "
        f"({args.input_format} input)."
    )

    failures: list[dict] = []
    pending_results: list[dict] = []
    all_results: list[dict] = []
    write_batch_size = max(1, args.write_batch_size)

    try:
        for index, row in enumerate(rows, start=1):
            try:
                conllu, tokens = analyse_sentence(
                    pipeline,
                    row["greek_sentence"],
                    input_format=args.input_format,
                )
                token_count = syntactic_token_count(tokens)
                result = {
                    "passage_id": row["passage_id"],
                    "sentence_number": row["sentence_number"],
                    "greek_sentence": row["greek_sentence"],
                    "conllu": conllu,
                    "token_count": token_count,
                    "tokens": tokens,
                }
                run["processed_count"] += 1
                run["token_count"] += token_count
                pending_results.append(result)
                if args.output_json or args.dry_run:
                    all_results.append(result)
            except Exception as exc:
                run["failure_count"] += 1
                failure = {
                    "passage_id": row["passage_id"],
                    "sentence_number": row["sentence_number"],
                    "error": str(exc),
                }
                failures.append(failure)
                print(
                    f"FAILED {row['passage_id']} #{row['sentence_number']}: {exc}",
                    file=sys.stderr,
                )

            if pending_results and (
                len(pending_results) >= write_batch_size or index == len(rows)
            ):
                if not args.dry_run:
                    batch_completed_at = now_iso()
                    run["completed_at"] = batch_completed_at
                    write_results(psql, run, pending_results)
                    print(
                        f"Saved {len(pending_results)} sentence analyses "
                        f"({run['processed_count']}/{len(rows)} complete)."
                    )
                pending_results = []

        run["completed_at"] = now_iso()
        run["status"] = "completed" if not failures else "completed_with_failures"
        if args.dry_run:
            run["status"] = "dry_run"
        else:
            write_run(psql, run)
    except Exception as exc:
        run["completed_at"] = now_iso()
        run["status"] = "failed"
        run["notes"] = f"{run['notes']}; fatal_error={exc}"
        if not args.dry_run:
            write_run(psql, run)
        raise

    output_payload(args.output_json, run, failures, all_results)
    print(
        f"Totals: {run['processed_count']} sentences, {run['token_count']} syntactic tokens, "
        f"{run['failure_count']} failures."
    )


if __name__ == "__main__":
    main()
