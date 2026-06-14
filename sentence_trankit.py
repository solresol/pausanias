#!/usr/bin/env python

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shlex
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DATABASE_URL = "dbname=pausanias user=gregb"
DEFAULT_MODEL_NAME = "trankit-oga-celano-2024-agdt-xlm-roberta-base"
DEFAULT_MODEL_PATH = Path("models") / "trankit-oga" / "save_dir40"
DEFAULT_SOURCE_PATH = Path("models") / "trankit-oga" / "trankit-master"
DEFAULT_SOURCE_REPO = (
    "https://git.informatik.uni-leipzig.de/celano/"
    "morphosyntactic_parser_for_oga.git"
)
DEFAULT_SOURCE_COMMIT = "da21a5292db2889e9e8628c391c1ee15498a0975"
GREEK_WORD_RE = (
    r"[\u0370-\u03ff\u1f00-\u1fff]+(?:[ʼ'’\u02bc](?=[\u0370-\u03ff\u1f00-\u1fff])"
    r"[\u0370-\u03ff\u1f00-\u1fff]+|[ʼ'’\u02bc])?"
)
TRANKIT_TOKEN_RE = re.compile(rf"{GREEK_WORD_RE}|\d+(?:[.,]\d+)?|[^\s]")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def parse_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Annotate Pausanias Greek sentences with Celano's Trankit OGA "
            "Ancient Greek morphosyntactic parser."
        )
    )
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--ssh-host", default=None)
    parser.add_argument("--psql-bin", default="psql")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--source-path", default=str(DEFAULT_SOURCE_PATH))
    parser.add_argument("--source-repo", default=DEFAULT_SOURCE_REPO)
    parser.add_argument("--source-commit", default=DEFAULT_SOURCE_COMMIT)
    parser.add_argument("--stop-after", type=int, default=None)
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--sample-seed", default="sentence-trankit-sample-v1")
    parser.add_argument("--exclude-books", default="")
    parser.add_argument("--passage-id", default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--parse-batch-size", type=int, default=16)
    parser.add_argument("--write-batch-size", type=int, default=64)
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


def tokenize_for_trankit(sentence: str) -> list[str]:
    return [match.group(0) for match in TRANKIT_TOKEN_RE.finditer(sentence or "")]


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
            pos,
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
                "pos": none_if_blank(pos),
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


def conllu_blocks(conllu: str) -> list[str]:
    blocks = []
    current = []
    for line in conllu.splitlines():
        if line.strip():
            current.append(line)
        elif current:
            blocks.append("\n".join(current) + "\n")
            current = []
    if current:
        blocks.append("\n".join(current) + "\n")
    return blocks


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_manifest_hash(model_path: Path, source_path: Path) -> str:
    candidates = [
        model_path / "xlm-roberta-base" / "customized" / "customized.tagger.mdl",
        model_path / "xlm-roberta-base" / "customized" / "customized.tokenizer.mdl",
        model_path / "xlm-roberta-base" / "customized" / "customized_lemmatizer.pt",
        model_path / "xlm-roberta-base" / "customized" / "customized.vocabs.json",
        source_path / "trankit" / "pipeline.py",
    ]
    digest = hashlib.sha256()
    for path in candidates:
        if not path.exists():
            raise FileNotFoundError(f"Required Trankit model/source file not found: {path}")
        digest.update(str(path.relative_to(path.parents[0])).encode("utf-8"))
        digest.update(sha256_file(path).encode("ascii"))
    return digest.hexdigest()


def ensure_runtime_paths(model_path: Path, source_path: Path) -> None:
    customized = model_path / "xlm-roberta-base" / "customized"
    if not customized.exists():
        raise FileNotFoundError(
            f"Trankit OGA model cache not found at {customized}. "
            "Populate models/trankit-oga/save_dir40 from Celano's "
            "morphosyntactic_parser_for_oga repository."
        )
    if not (source_path / "trankit" / "__init__.py").exists():
        raise FileNotFoundError(
            f"Trankit OGA source not found at {source_path}. "
            "Populate models/trankit-oga/trankit-master from Celano's repository."
        )


def import_trankit(source_path: Path):
    sys.path.insert(0, str(source_path))
    try:
        import trankit  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised by runtime smoke commands
        raise RuntimeError(
            "Could not import Celano's bundled Trankit source. Run this script with:\n"
            "PYTHONPATH=models/trankit-oga/trankit-master "
            "uv run --no-project --python 3.10 "
            "--with adapters==0.1.1 --with transformers==4.35.2 "
            "--with huggingface-hub==0.20.3 --with langid==1.1.6 "
            "--with sentencepiece --with 'torch>=1.6.0,<=2.0.1' "
            "--with 'numpy<2' --with six python sentence_trankit.py ..."
        ) from exc
    return trankit


def load_pipeline(trankit, model_path: Path):
    trankit.verify_customized_pipeline(
        category="customized",
        save_dir=str(model_path),
        embedding_name="xlm-roberta-base",
    )
    return trankit.Pipeline(lang="customized", cache_dir=str(model_path))


def parse_batch(trankit, pipeline, rows: list[dict]) -> list[dict]:
    token_lists = [tokenize_for_trankit(row["greek_sentence"]) for row in rows]
    tagged_doc = pipeline.posdep(token_lists)
    blocks = conllu_blocks(trankit.trankit2conllu(tagged_doc))
    if len(blocks) != len(rows):
        raise ValueError(f"Expected {len(rows)} CoNLL-U blocks, got {len(blocks)}")

    results = []
    for row, conllu in zip(rows, blocks):
        tokens = parse_conllu_tokens(conllu)
        results.append(
            {
                "passage_id": row["passage_id"],
                "sentence_number": row["sentence_number"],
                "greek_sentence": row["greek_sentence"],
                "conllu": conllu,
                "token_count": syntactic_token_count(tokens),
                "tokens": tokens,
            }
        )
    return results


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
                FROM sentence_trankit_analyses a
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
    tag = f"json_{run['run_id'].replace('-', '_')}"
    payload_json = json.dumps(run, ensure_ascii=False)
    sql = f"""
WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS r
)
INSERT INTO sentence_trankit_runs (
    run_id, started_at, completed_at, model_name, model_path, source_path,
    model_sha256, trankit_version, python_version, annotation_scheme, status,
    processed_count, token_count, failure_count, notes
)
SELECT
    r->>'run_id',
    r->>'started_at',
    NULLIF(r->>'completed_at', ''),
    r->>'model_name',
    r->>'model_path',
    r->>'source_path',
    r->>'model_sha256',
    r->>'trankit_version',
    r->>'python_version',
    r->>'annotation_scheme',
    r->>'status',
    (r->>'processed_count')::integer,
    (r->>'token_count')::integer,
    (r->>'failure_count')::integer,
    r->>'notes'
FROM payload
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
    payload = {"run": run, "results": results}
    tag = f"json_{run['run_id'].replace('-', '_')}"
    payload_json = json.dumps(payload, ensure_ascii=False)
    sql = f"""
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
        token_count integer,
        tokens jsonb
    )
)
INSERT INTO sentence_trankit_analyses (
    passage_id, sentence_number, model_name, run_id, greek_sentence,
    conllu, token_count, created_at
)
SELECT
    rows.passage_id,
    rows.sentence_number,
    run_row.r->>'model_name',
    run_row.r->>'run_id',
    rows.greek_sentence,
    rows.conllu,
    rows.token_count,
    run_row.r->>'completed_at'
FROM rows CROSS JOIN run_row
ON CONFLICT (passage_id, sentence_number, model_name) DO UPDATE
SET run_id = EXCLUDED.run_id,
    greek_sentence = EXCLUDED.greek_sentence,
    conllu = EXCLUDED.conllu,
    token_count = EXCLUDED.token_count,
    created_at = EXCLUDED.created_at;

WITH payload AS (
    SELECT ${tag}${payload_json}${tag}$::jsonb AS j
), run_row AS (
    SELECT j->'run' AS r FROM payload
), rows AS (
    SELECT x.passage_id, x.sentence_number, run_row.r->>'model_name' AS model_name
    FROM run_row,
         jsonb_to_recordset((SELECT j->'results' FROM payload)) AS x(
            passage_id text,
            sentence_number integer
         )
)
DELETE FROM sentence_trankit_tokens t
USING rows
WHERE t.passage_id = rows.passage_id
  AND t.sentence_number = rows.sentence_number
  AND t.model_name = rows.model_name;

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
INSERT INTO sentence_trankit_tokens (
    passage_id, sentence_number, model_name, token_order, token_id, form,
    lemma, pos, xpos, feats_raw, feats, head_token_id, deprel, deps_raw,
    deps, misc_raw, misc, is_multiword_token, is_empty_node, created_at
)
SELECT
    rows.passage_id,
    rows.sentence_number,
    run_row.r->>'model_name',
    tok.token_order,
    tok.token_id,
    tok.form,
    tok.lemma,
    tok.pos,
    tok.xpos,
    tok.feats_raw,
    tok.feats,
    tok.head_token_id,
    tok.deprel,
    tok.deps_raw,
    tok.deps,
    tok.misc_raw,
    tok.misc,
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
    pos text,
    xpos text,
    feats_raw text,
    feats jsonb,
    head_token_id text,
    deprel text,
    deps_raw text,
    deps jsonb,
    misc_raw text,
    misc jsonb,
    is_multiword_token boolean,
    is_empty_node boolean
);
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


def batched(rows: list[dict], batch_size: int):
    for index in range(0, len(rows), batch_size):
        yield rows[index : index + batch_size]


def main() -> None:
    args = parse_arguments()
    model_path = Path(args.model_path).expanduser()
    source_path = Path(args.source_path).expanduser()

    psql = PsqlRunner(args.database_url, psql_bin=args.psql_bin, ssh_host=args.ssh_host)
    psql.run(schema_sql())
    if args.schema_only:
        print("Schema ensured.")
        return

    ensure_runtime_paths(model_path, source_path)
    excluded_books = parse_list(args.exclude_books)
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
        print(f"No unprocessed Trankit rows found for model {args.model_name}.")
        return

    trankit = import_trankit(source_path)
    pipeline = load_pipeline(trankit, model_path)
    run = {
        "run_id": str(uuid.uuid4()),
        "started_at": now_iso(),
        "completed_at": "",
        "model_name": args.model_name,
        "model_path": str(model_path),
        "source_path": str(source_path),
        "model_sha256": model_manifest_hash(model_path, source_path),
        "trankit_version": getattr(trankit, "__version__", "bundled"),
        "python_version": sys.version.split()[0],
        "annotation_scheme": "AGDT",
        "status": "dry_run" if args.dry_run else "running",
        "processed_count": 0,
        "token_count": 0,
        "failure_count": 0,
        "notes": (
            f"source_repo={args.source_repo}; source_commit={args.source_commit}; "
            f"sample_size={args.sample_size}; stop_after={args.stop_after}; "
            f"exclude_books={','.join(excluded_books)}; sample_seed={args.sample_seed}; "
            f"passage_id={args.passage_id}; overwrite={args.overwrite}"
        ),
    }
    if not args.dry_run:
        write_run(psql, run)

    print(f"Run {run['run_id']}: analysing {len(rows)} sentences with {args.model_name}.")

    failures: list[dict] = []
    pending_results: list[dict] = []
    all_results: list[dict] = []
    parse_batch_size = max(1, args.parse_batch_size)
    write_batch_size = max(1, args.write_batch_size)

    try:
        for batch in batched(rows, parse_batch_size):
            try:
                batch_results = parse_batch(trankit, pipeline, batch)
            except Exception as exc:
                run["failure_count"] += len(batch)
                for row in batch:
                    failures.append(
                        {
                            "passage_id": row["passage_id"],
                            "sentence_number": row["sentence_number"],
                            "error": str(exc),
                        }
                    )
                    print(
                        f"FAILED {row['passage_id']} #{row['sentence_number']}: {exc}",
                        file=sys.stderr,
                    )
                continue

            for result in batch_results:
                run["processed_count"] += 1
                run["token_count"] += result["token_count"]
                pending_results.append(result)
                if args.output_json or args.dry_run:
                    all_results.append(result)

            if pending_results and len(pending_results) >= write_batch_size:
                if not args.dry_run:
                    run["completed_at"] = now_iso()
                    write_results(psql, run, pending_results)
                    print(
                        f"Saved {len(pending_results)} sentence analyses "
                        f"({run['processed_count']}/{len(rows)} complete)."
                    )
                pending_results = []

        if pending_results and not args.dry_run:
            run["completed_at"] = now_iso()
            write_results(psql, run, pending_results)
            print(
                f"Saved {len(pending_results)} sentence analyses "
                f"({run['processed_count']}/{len(rows)} complete)."
            )

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
        f"Totals: {run['processed_count']} sentences, {run['token_count']} tokens, "
        f"{run['failure_count']} failures."
    )


if __name__ == "__main__":
    main()
