#!/usr/bin/env python

import argparse
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from openai import OpenAI
from tqdm import tqdm

from pausanias_db import add_database_argument, column_exists, connect


LEGACY_PROMPT_VERSION = "legacy-mythic-scepticism-v1"
GRETA_PROMPT_VERSION = "greta-myth-history-other-v1"
DEFAULT_MODEL = "gpt-5"
DEFAULT_COMPARISON_MODEL = "gpt-5.4-mini"
DEFAULT_JUDGE_MODEL = "gpt-5.4"
BUCKETS = ("mythic", "historical", "other")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Analyze Pausanias sentences using the OpenAI API"
    )
    add_database_argument(parser)
    parser.add_argument(
        "--openai-api-key-file",
        default="~/.openai.key",
        help="File containing OpenAI API key (default: ~/.openai.key)",
    )
    parser.add_argument(
        "--mode",
        choices=("legacy", "compare-mini", "greta"),
        default="legacy",
        help=(
            "legacy updates the old boolean columns; compare-mini re-runs a "
            "sample against another model; greta stores the new three-bucket tags."
        ),
    )
    parser.add_argument(
        "--stop-after",
        type=int,
        default=None,
        help="Maximum number of sentences to process (default: all)",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=None,
        help="Maximum input+output tokens for greta mode (default: no token cap)",
    )
    parser.add_argument(
        "--compare-sample-size",
        type=int,
        default=50,
        help="Number of already-tagged sentences to compare in compare-mini mode",
    )
    parser.add_argument(
        "--exclude-books",
        default="",
        help="Comma-separated book numbers to skip, for example '4,8'",
    )
    parser.add_argument(
        "--progress-bar",
        action="store_true",
        default=False,
        help="Show progress bar",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--comparison-model",
        default=DEFAULT_COMPARISON_MODEL,
        help=(
            "OpenAI model used to re-run legacy labels in compare-mini mode "
            f"(default: {DEFAULT_COMPARISON_MODEL})"
        ),
    )
    parser.add_argument(
        "--judge-model",
        default=DEFAULT_JUDGE_MODEL,
        help=f"OpenAI model used to judge disagreements (default: {DEFAULT_JUDGE_MODEL})",
    )
    parser.add_argument(
        "--prompt-version",
        default=None,
        help="Override the prompt/schema version recorded in database rows",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent API calls for greta mode (default: 1)",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.5,
        help="Delay after each legacy/compare API call (default: 0.5)",
    )
    return parser.parse_args()


def parse_excluded_books(value):
    if not value.strip():
        return set()
    return {part.strip() for part in value.split(",") if part.strip()}


def load_openai_api_key(key_file):
    key_path = os.path.expanduser(key_file)
    try:
        with open(key_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"OpenAI API key file not found: {key_file}")


def ensure_sentence_columns(conn):
    """Ensure legacy analysis columns exist on the greek_sentences table."""
    cursor = conn.cursor()
    if not column_exists(conn, "greek_sentences", "references_mythic_era"):
        cursor.execute(
            "ALTER TABLE greek_sentences ADD COLUMN references_mythic_era BOOLEAN"
        )
    if not column_exists(conn, "greek_sentences", "expresses_scepticism"):
        cursor.execute(
            "ALTER TABLE greek_sentences ADD COLUMN expresses_scepticism BOOLEAN"
        )
    conn.commit()


def ensure_sentence_tagging_tables(conn):
    """Create tables for model comparisons and Greta's new three-bucket tags."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sentence_tagging_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            mode TEXT NOT NULL,
            model TEXT NOT NULL,
            comparison_model TEXT,
            judge_model TEXT,
            prompt_version TEXT NOT NULL,
            status TEXT NOT NULL,
            token_budget INTEGER,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            processed_count INTEGER NOT NULL DEFAULT 0,
            discrepancy_count INTEGER NOT NULL DEFAULT 0,
            notes TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sentence_tagging_model_comparisons (
            id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES sentence_tagging_runs(run_id)
                ON DELETE CASCADE,
            passage_id TEXT NOT NULL,
            sentence_number INTEGER NOT NULL,
            greek_sentence TEXT NOT NULL,
            english_sentence TEXT NOT NULL,
            baseline_model TEXT NOT NULL,
            baseline_references_mythic_era BOOLEAN NOT NULL,
            baseline_expresses_scepticism BOOLEAN NOT NULL,
            comparison_model TEXT NOT NULL,
            comparison_references_mythic_era BOOLEAN,
            comparison_expresses_scepticism BOOLEAN,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            disagrees BOOLEAN NOT NULL DEFAULT FALSE,
            judge_model TEXT,
            judge_winner TEXT,
            judge_reason TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(run_id, passage_id, sentence_number)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sentence_greta_tags (
            passage_id TEXT NOT NULL,
            sentence_number INTEGER NOT NULL,
            prompt_version TEXT NOT NULL,
            model TEXT NOT NULL,
            myth_history_bucket TEXT NOT NULL CHECK (
                myth_history_bucket IN ('mythic', 'historical', 'other')
            ),
            expresses_scepticism BOOLEAN NOT NULL,
            confidence TEXT NOT NULL,
            rationale TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            run_id TEXT NOT NULL REFERENCES sentence_tagging_runs(run_id)
                ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            PRIMARY KEY (passage_id, sentence_number, prompt_version)
        )
        """
    )
    conn.commit()


def create_run(
    conn,
    *,
    mode,
    model,
    prompt_version,
    comparison_model=None,
    judge_model=None,
    token_budget=None,
    notes=None,
):
    run_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO sentence_tagging_runs (
            run_id, started_at, mode, model, comparison_model, judge_model,
            prompt_version, status, token_budget, notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'running', %s, %s)
        """,
        (
            run_id,
            now_iso(),
            mode,
            model,
            comparison_model,
            judge_model,
            prompt_version,
            token_budget,
            notes,
        ),
    )
    conn.commit()
    return run_id


def finish_run(
    conn,
    run_id,
    *,
    status,
    input_tokens,
    output_tokens,
    processed_count,
    discrepancy_count=0,
    notes=None,
):
    conn.execute(
        """
        UPDATE sentence_tagging_runs
        SET completed_at = %s,
            status = %s,
            input_tokens = %s,
            output_tokens = %s,
            processed_count = %s,
            discrepancy_count = %s,
            notes = COALESCE(%s, notes)
        WHERE run_id = %s
        """,
        (
            now_iso(),
            status,
            input_tokens,
            output_tokens,
            processed_count,
            discrepancy_count,
            notes,
            run_id,
        ),
    )
    conn.commit()


def get_unprocessed_sentences(conn, limit=None):
    """Retrieve sentences that have not been analysed in the legacy columns."""
    query = (
        "SELECT passage_id, sentence_number, sentence, english_sentence "
        "FROM greek_sentences "
        "WHERE references_mythic_era IS NULL "
        "ORDER BY passage_id, sentence_number"
    )
    if limit:
        query += f" LIMIT {int(limit)}"
    with conn.cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()


def get_legacy_comparison_sample(conn, limit):
    """Retrieve a deterministic sample of already-tagged legacy sentences."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT passage_id, sentence_number, sentence, english_sentence,
                   references_mythic_era, expresses_scepticism
            FROM greek_sentences
            WHERE references_mythic_era IS NOT NULL
              AND expresses_scepticism IS NOT NULL
            ORDER BY md5(passage_id || ':' || sentence_number::text)
            LIMIT %s
            """,
            (limit,),
        )
        return cursor.fetchall()


def get_greta_unprocessed_sentences(conn, prompt_version, excluded_books, limit=None):
    params = [prompt_version]
    book_filter = ""
    if excluded_books:
        book_filter = "AND split_part(s.passage_id, '.', 1) <> ALL(%s)"
        params.append(list(excluded_books))
    limit_clause = ""
    if limit:
        limit_clause = f"LIMIT {int(limit)}"
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT s.passage_id, s.sentence_number, s.sentence, s.english_sentence
            FROM greek_sentences s
            WHERE NOT EXISTS (
                SELECT 1
                FROM sentence_greta_tags t
                WHERE t.passage_id = s.passage_id
                  AND t.sentence_number = s.sentence_number
                  AND t.prompt_version = %s
            )
            {book_filter}
            ORDER BY s.passage_id, s.sentence_number
            {limit_clause}
            """,
            params,
        )
        return cursor.fetchall()


def save_legacy_analysis_results(
    conn, passage_id, sentence_number, references_mythic_era, expresses_scepticism
):
    """Persist legacy boolean analysis results for a sentence."""
    conn.execute(
        """
        UPDATE greek_sentences
        SET references_mythic_era = %s, expresses_scepticism = %s
        WHERE passage_id = %s AND sentence_number = %s
        """,
        (references_mythic_era, expresses_scepticism, passage_id, sentence_number),
    )
    conn.commit()


def legacy_tool():
    return [
        {
            "type": "function",
            "function": {
                "name": "save_annotations",
                "description": (
                    "Save whether the sentence references the mythic era and "
                    "whether Pausanias expresses skepticism."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "references_mythic_era": {
                            "type": "boolean",
                            "description": (
                                "Whether the sentence references the mythic era "
                                "(true) or the historical era (false)."
                            ),
                        },
                        "expresses_scepticism": {
                            "type": "boolean",
                            "description": (
                                "Whether Pausanias expresses skepticism about the "
                                "subject matter."
                            ),
                        },
                    },
                    "required": ["references_mythic_era", "expresses_scepticism"],
                },
            },
        }
    ]


def greta_tool():
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
                            "enum": list(BUCKETS),
                            "description": (
                                "mythic, historical, or other/geographical/descriptive."
                            ),
                        },
                        "expresses_scepticism": {
                            "type": "boolean",
                            "description": (
                                "Whether Pausanias distances himself from, doubts, "
                                "questions, or corrects the reported material."
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
                    "required": [
                        "myth_history_bucket",
                        "expresses_scepticism",
                        "confidence",
                        "rationale",
                    ],
                },
            },
        }
    ]


def analyse_sentence_legacy(
    client, model, passage_id, sentence_number, sentence_text, english_text
):
    """Analyse a sentence using the legacy two-boolean schema."""
    system_prompt = (
        "Act as a Pausanias scholar and report whether this sentence of Pausanias is "
        "a reference to the mythic era or historical era. Then report whether "
        "Pausanias shows scepticism about the subject matter he is writing about."
    )
    user_content = (
        f"Passage {passage_id}, sentence {sentence_number}:\n\n"
        f"Greek:\n{sentence_text}\n\nEnglish:\n{english_text}\n\n"
        "Analyse this sentence and provide your results using the save_annotations function."
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            tools=legacy_tool(),
            tool_choice={"type": "function", "function": {"name": "save_annotations"}},
        )

        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        tool_calls = response.choices[0].message.tool_calls
        if tool_calls:
            function_args = json.loads(tool_calls[0].function.arguments)
            return {
                "references_mythic_era": function_args.get("references_mythic_era"),
                "expresses_scepticism": function_args.get("expresses_scepticism"),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "error": None,
            }
        return {
            "references_mythic_era": None,
            "expresses_scepticism": None,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "error": "No tool call returned",
        }
    except Exception as exc:
        return {
            "references_mythic_era": None,
            "expresses_scepticism": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "error": str(exc),
        }


def analyse_sentence_greta(
    client, model, passage_id, sentence_number, sentence_text, english_text
):
    """Analyse a sentence using Greta's mythic/historical/other tagging plan."""
    system_prompt = (
        "Act as a Pausanias scholar. Classify each sentence into exactly one "
        "bucket. Use 'mythic' for mythic events or the impact of mythic events "
        "on the landscape. Use 'historical' for events after roughly 500 BC or "
        "the impact of those historical events on the landscape. Use 'other' "
        "for geographical, route, descriptive, antiquarian, or otherwise "
        "non-mythic/non-historical material that should not be forced into the "
        "historical bucket. Also mark whether Pausanias expresses scepticism, "
        "distance, doubt, correction, or explicit uncertainty."
    )
    user_content = (
        f"Passage {passage_id}, sentence {sentence_number}:\n\n"
        f"Greek:\n{sentence_text}\n\nEnglish:\n{english_text}\n\n"
        "Classify this sentence using the save_greta_sentence_tag function."
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            tools=greta_tool(),
            tool_choice={
                "type": "function",
                "function": {"name": "save_greta_sentence_tag"},
            },
        )
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            return None, input_tokens, output_tokens, "No tool call returned"

        function_args = json.loads(tool_calls[0].function.arguments)
        bucket = function_args.get("myth_history_bucket")
        if bucket not in BUCKETS:
            return None, input_tokens, output_tokens, f"Invalid bucket: {bucket}"
        return function_args, input_tokens, output_tokens, None
    except Exception as exc:
        return None, 0, 0, str(exc)


def judge_legacy_discrepancy(
    client,
    model,
    passage_id,
    sentence_number,
    sentence_text,
    english_text,
    baseline,
    comparison,
):
    """Ask a judge model which legacy two-boolean label is better."""
    tool = [
        {
            "type": "function",
            "function": {
                "name": "save_judgment",
                "description": "Save which of two sentence annotations is better.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "winner": {
                            "type": "string",
                            "enum": ["baseline", "comparison", "tie"],
                        },
                        "reason": {
                            "type": "string",
                            "description": "One concise explanation of the judgment.",
                        },
                    },
                    "required": ["winner", "reason"],
                },
            },
        }
    ]
    system_prompt = (
        "You are judging two Pausanias sentence annotations. Choose the better "
        "annotation, or tie if both are defensible. The label "
        "references_mythic_era means the sentence references the mythic era, "
        "not merely that it is non-historical. expresses_scepticism means "
        "Pausanias distances, doubts, corrects, or questions the material."
    )
    user_content = (
        f"Passage {passage_id}, sentence {sentence_number}:\n\n"
        f"Greek:\n{sentence_text}\n\nEnglish:\n{english_text}\n\n"
        f"Baseline annotation: {json.dumps(baseline, ensure_ascii=False)}\n"
        f"Comparison annotation: {json.dumps(comparison, ensure_ascii=False)}"
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            tools=tool,
            tool_choice={"type": "function", "function": {"name": "save_judgment"}},
        )
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        tool_calls = response.choices[0].message.tool_calls
        if tool_calls:
            args = json.loads(tool_calls[0].function.arguments)
            return args.get("winner"), args.get("reason"), input_tokens, output_tokens
        return "tie", "No judge tool call returned.", input_tokens, output_tokens
    except Exception as exc:
        return None, f"Judge failed: {exc}", 0, 0


def save_comparison(
    conn,
    *,
    run_id,
    row,
    baseline_model,
    comparison_model,
    comparison,
    disagrees,
    judge_model=None,
    judge_winner=None,
    judge_reason=None,
):
    (
        passage_id,
        sentence_number,
        sentence_text,
        english_text,
        baseline_mythic,
        baseline_scepticism,
    ) = row
    conn.execute(
        """
        INSERT INTO sentence_tagging_model_comparisons (
            run_id, passage_id, sentence_number, greek_sentence, english_sentence,
            baseline_model, baseline_references_mythic_era,
            baseline_expresses_scepticism, comparison_model,
            comparison_references_mythic_era, comparison_expresses_scepticism,
            input_tokens, output_tokens, disagrees, judge_model, judge_winner,
            judge_reason, created_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (run_id, passage_id, sentence_number) DO UPDATE
        SET comparison_references_mythic_era = EXCLUDED.comparison_references_mythic_era,
            comparison_expresses_scepticism = EXCLUDED.comparison_expresses_scepticism,
            input_tokens = EXCLUDED.input_tokens,
            output_tokens = EXCLUDED.output_tokens,
            disagrees = EXCLUDED.disagrees,
            judge_model = EXCLUDED.judge_model,
            judge_winner = EXCLUDED.judge_winner,
            judge_reason = EXCLUDED.judge_reason
        """,
        (
            run_id,
            passage_id,
            sentence_number,
            sentence_text,
            english_text,
            baseline_model,
            baseline_mythic,
            baseline_scepticism,
            comparison_model,
            comparison.get("references_mythic_era"),
            comparison.get("expresses_scepticism"),
            comparison.get("input_tokens", 0),
            comparison.get("output_tokens", 0),
            disagrees,
            judge_model,
            judge_winner,
            judge_reason,
            now_iso(),
        ),
    )
    conn.commit()


def save_greta_tag(
    conn,
    *,
    run_id,
    prompt_version,
    model,
    passage_id,
    sentence_number,
    tag,
    input_tokens,
    output_tokens,
):
    conn.execute(
        """
        INSERT INTO sentence_greta_tags (
            passage_id, sentence_number, prompt_version, model,
            myth_history_bucket, expresses_scepticism, confidence, rationale,
            input_tokens, output_tokens, run_id, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (passage_id, sentence_number, prompt_version) DO UPDATE
        SET model = EXCLUDED.model,
            myth_history_bucket = EXCLUDED.myth_history_bucket,
            expresses_scepticism = EXCLUDED.expresses_scepticism,
            confidence = EXCLUDED.confidence,
            rationale = EXCLUDED.rationale,
            input_tokens = EXCLUDED.input_tokens,
            output_tokens = EXCLUDED.output_tokens,
            run_id = EXCLUDED.run_id,
            created_at = EXCLUDED.created_at
        """,
        (
            passage_id,
            sentence_number,
            prompt_version,
            model,
            tag["myth_history_bucket"],
            tag["expresses_scepticism"],
            tag["confidence"],
            tag["rationale"],
            input_tokens,
            output_tokens,
            run_id,
            now_iso(),
        ),
    )
    conn.commit()


def run_legacy_mode(args, conn, client):
    ensure_sentence_columns(conn)
    sentences = get_unprocessed_sentences(conn, args.stop_after)
    if not sentences:
        print("No unprocessed sentences found in the database.")
        return
    print(f"Found {len(sentences)} unprocessed sentences.")
    iterator = tqdm(sentences) if args.progress_bar else sentences
    total_input_tokens = 0
    total_output_tokens = 0
    for passage_id, sentence_number, sentence_text, english_text in iterator:
        result = analyse_sentence_legacy(
            client, args.model, passage_id, sentence_number, sentence_text, english_text
        )
        total_input_tokens += result["input_tokens"]
        total_output_tokens += result["output_tokens"]
        if (
            result["references_mythic_era"] is not None
            and result["expresses_scepticism"] is not None
        ):
            save_legacy_analysis_results(
                conn,
                passage_id,
                sentence_number,
                result["references_mythic_era"],
                result["expresses_scepticism"],
            )
            if not args.progress_bar:
                print(
                    f"Processed {passage_id} #{sentence_number}: "
                    f"mythic_era={result['references_mythic_era']}, "
                    f"scepticism={result['expresses_scepticism']}, "
                    f"tokens={result['input_tokens']}/{result['output_tokens']}"
                )
        else:
            print(
                f"Failed to analyse {passage_id} #{sentence_number}: {result['error']}"
            )
        time.sleep(args.sleep_seconds)
    print(
        "Processing complete. Total tokens used: "
        f"{total_input_tokens} input, {total_output_tokens} output"
    )


def run_compare_mode(args, conn, client):
    ensure_sentence_tagging_tables(conn)
    run_id = create_run(
        conn,
        mode="compare-mini",
        model=args.model,
        comparison_model=args.comparison_model,
        judge_model=args.judge_model,
        prompt_version=args.prompt_version or LEGACY_PROMPT_VERSION,
        notes=f"Deterministic sample size {args.compare_sample_size}",
    )
    rows = get_legacy_comparison_sample(conn, args.compare_sample_size)
    print(
        f"Run {run_id}: comparing {len(rows)} existing {args.model} labels "
        f"against {args.comparison_model}."
    )
    total_input_tokens = 0
    total_output_tokens = 0
    discrepancy_count = 0
    judge_counts = {"baseline": 0, "comparison": 0, "tie": 0, "failed": 0}

    try:
        for row in rows:
            (
                passage_id,
                sentence_number,
                sentence_text,
                english_text,
                baseline_mythic,
                baseline_scepticism,
            ) = row
            comparison = analyse_sentence_legacy(
                client,
                args.comparison_model,
                passage_id,
                sentence_number,
                sentence_text,
                english_text,
            )
            total_input_tokens += comparison["input_tokens"]
            total_output_tokens += comparison["output_tokens"]
            disagrees = (
                comparison["references_mythic_era"] != baseline_mythic
                or comparison["expresses_scepticism"] != baseline_scepticism
            )

            judge_winner = None
            judge_reason = None
            if disagrees and comparison["error"] is None:
                discrepancy_count += 1
                baseline = {
                    "references_mythic_era": baseline_mythic,
                    "expresses_scepticism": baseline_scepticism,
                }
                comparison_labels = {
                    "references_mythic_era": comparison["references_mythic_era"],
                    "expresses_scepticism": comparison["expresses_scepticism"],
                }
                (
                    judge_winner,
                    judge_reason,
                    judge_input_tokens,
                    judge_output_tokens,
                ) = judge_legacy_discrepancy(
                    client,
                    args.judge_model,
                    passage_id,
                    sentence_number,
                    sentence_text,
                    english_text,
                    baseline,
                    comparison_labels,
                )
                total_input_tokens += judge_input_tokens
                total_output_tokens += judge_output_tokens
                judge_counts[judge_winner or "failed"] = (
                    judge_counts.get(judge_winner or "failed", 0) + 1
                )
            elif disagrees:
                discrepancy_count += 1
                judge_counts["failed"] += 1
                judge_reason = comparison["error"]

            save_comparison(
                conn,
                run_id=run_id,
                row=row,
                baseline_model=args.model,
                comparison_model=args.comparison_model,
                comparison=comparison,
                disagrees=disagrees,
                judge_model=args.judge_model if disagrees else None,
                judge_winner=judge_winner,
                judge_reason=judge_reason,
            )
            status = "DIFF" if disagrees else "same"
            print(f"{status} {passage_id} #{sentence_number}")
            time.sleep(args.sleep_seconds)

        notes = (
            f"judge_counts={judge_counts}; total_tokens="
            f"{total_input_tokens + total_output_tokens}"
        )
        finish_run(
            conn,
            run_id,
            status="completed",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            processed_count=len(rows),
            discrepancy_count=discrepancy_count,
            notes=notes,
        )
        print(
            f"Comparison complete: {discrepancy_count}/{len(rows)} discrepancies. "
            f"Judge counts: {judge_counts}. Run id: {run_id}"
        )
    except Exception as exc:
        finish_run(
            conn,
            run_id,
            status="failed",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            processed_count=0,
            discrepancy_count=discrepancy_count,
            notes=str(exc),
        )
        raise


def run_greta_mode(args, conn, client):
    ensure_sentence_tagging_tables(conn)
    prompt_version = args.prompt_version or GRETA_PROMPT_VERSION
    excluded_books = parse_excluded_books(args.exclude_books)
    run_id = create_run(
        conn,
        mode="greta",
        model=args.model,
        prompt_version=prompt_version,
        token_budget=args.token_budget,
        notes=f"exclude_books={','.join(sorted(excluded_books))}",
    )
    rows = get_greta_unprocessed_sentences(
        conn, prompt_version, excluded_books, args.stop_after
    )
    if not rows:
        finish_run(
            conn,
            run_id,
            status="completed",
            input_tokens=0,
            output_tokens=0,
            processed_count=0,
        )
        print("No unprocessed Greta-plan sentences found.")
        return

    print(
        f"Run {run_id}: tagging up to {len(rows)} sentences with {args.model}; "
        f"token budget={args.token_budget or 'none'}; "
        f"exclude_books={','.join(sorted(excluded_books)) or 'none'}."
    )

    total_input_tokens = 0
    total_output_tokens = 0
    processed_count = 0
    failures = []
    row_iter = iter(rows)
    pending = set()
    max_workers = max(1, args.concurrency)
    stop_submitting = False

    def submit_next(executor):
        try:
            row = next(row_iter)
        except StopIteration:
            return False
        passage_id, sentence_number, sentence_text, english_text = row
        future = executor.submit(
            analyse_sentence_greta,
            client,
            args.model,
            passage_id,
            sentence_number,
            sentence_text,
            english_text,
        )
        future.row = row
        pending.add(future)
        return True

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for _ in range(max_workers):
                if not submit_next(executor):
                    break

            while pending:
                for future in as_completed(pending):
                    pending.remove(future)
                    passage_id, sentence_number, _, _ = future.row
                    tag, input_tokens, output_tokens, error = future.result()
                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens
                    if tag is None:
                        failures.append((passage_id, sentence_number, error))
                        print(f"FAILED {passage_id} #{sentence_number}: {error}")
                    else:
                        save_greta_tag(
                            conn,
                            run_id=run_id,
                            prompt_version=prompt_version,
                            model=args.model,
                            passage_id=passage_id,
                            sentence_number=sentence_number,
                            tag=tag,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                        )
                        processed_count += 1
                        print(
                            f"Tagged {passage_id} #{sentence_number}: "
                            f"{tag['myth_history_bucket']} "
                            f"scepticism={tag['expresses_scepticism']} "
                            f"tokens={input_tokens + output_tokens}"
                        )

                    total_tokens = total_input_tokens + total_output_tokens
                    if args.token_budget and total_tokens >= args.token_budget:
                        stop_submitting = True
                    if not stop_submitting:
                        submit_next(executor)

        status = "completed" if not failures else "completed_with_failures"
        notes = None
        if failures:
            notes = f"{len(failures)} failures; first={failures[0]}"
        finish_run(
            conn,
            run_id,
            status=status,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            processed_count=processed_count,
            notes=notes,
        )
        print(
            f"Greta tagging run complete: {processed_count} saved, "
            f"{len(failures)} failed, tokens={total_input_tokens + total_output_tokens}. "
            f"Run id: {run_id}"
        )
    except Exception as exc:
        finish_run(
            conn,
            run_id,
            status="failed",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            processed_count=processed_count,
            notes=str(exc),
        )
        raise


def main():
    args = parse_arguments()
    api_key = load_openai_api_key(args.openai_api_key_file)
    client = OpenAI(api_key=api_key)
    conn = connect(args.database_url)
    try:
        if args.mode == "legacy":
            run_legacy_mode(args, conn, client)
        elif args.mode == "compare-mini":
            run_compare_mode(args, conn, client)
        elif args.mode == "greta":
            run_greta_mode(args, conn, client)
        else:
            raise ValueError(f"Unknown mode: {args.mode}")
    except Exception as exc:
        print(f"Error: {str(exc)}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
