#!/usr/bin/env python
"""Recover archived place-state Batch API outputs into typed tables.

This is intentionally a recovery/import tool. It does not submit new LLM work
and does not put the retired place-state sweep back into the daily pipeline.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from openai import OpenAI

from pausanias_db import add_database_argument, connect, initialize_schema


PLACE_STATE_PROMPT_VERSION = "place-state-v1"
PLACE_STATE_STATUSES = {
    "inhabited_still_exists",
    "extant_uninhabited",
    "ruined_or_remains",
    "abandoned_or_deserted",
    "destroyed_no_trace",
    "renamed_refounded_or_transferred",
    "unclear",
}
PLACE_STATE_TEMPORAL_SCOPES = {
    "pausanias_present",
    "past_before_pausanias",
    "mythic_past",
    "later_commentary",
    "unclear",
}
PLACE_STATE_TARGET_LABELS = {
    "inhabited_still_exists": "survives",
    "extant_uninhabited": "survives",
    "ruined_or_remains": "does_not_survive",
    "abandoned_or_deserted": "does_not_survive",
    "destroyed_no_trace": "does_not_survive",
    "renamed_refounded_or_transferred": "exclude",
    "unclear": "exclude",
}


@dataclass
class ParsedRecovery:
    reviews: list[dict[str, Any]] = field(default_factory=list)
    mentions: list[dict[str, Any]] = field(default_factory=list)
    item_updates: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, str | None]] = field(default_factory=list)
    seen_requests: set[int] = field(default_factory=set)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_openai_api_key(key_file: str) -> str:
    with open(os.path.expanduser(key_file), "r", encoding="utf-8") as handle:
        return handle.read().strip()


def parse_custom_id(value: str) -> tuple[str, str, int]:
    parts = value.split(":")
    if len(parts) != 4 or parts[0] != "senttag":
        raise ValueError(f"Unexpected custom_id: {value!r}")
    return parts[1], parts[2], int(parts[3])


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


def place_state_target_label(place_status: str, temporal_scope: str) -> str:
    if temporal_scope != "pausanias_present":
        return "exclude"
    return PLACE_STATE_TARGET_LABELS.get(place_status, "exclude")


def created_at_for_run(run: dict[str, Any]) -> str:
    return run.get("completed_at") or run.get("retrieved_at") or now_iso()


def parse_output_text(
    output_text: str,
    *,
    run: dict[str, Any],
    item_lookup: dict[int, dict[str, Any]],
) -> ParsedRecovery:
    parsed = ParsedRecovery()
    run_id = run["run_id"]
    created_at = created_at_for_run(run)
    for line in output_text.splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        request_number: int | None = None
        try:
            output_mode, output_run_id, request_number = parse_custom_id(
                record.get("custom_id", "")
            )
            if output_mode != "place-state":
                raise ValueError(f"Unexpected mode in custom_id: {output_mode}")
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
            claims = args.get("claims") or []
            if not isinstance(claims, list):
                raise ValueError("place-state claims must be a list")
            has_place_state_claim = bool(args.get("has_place_state_claim"))
            if has_place_state_claim and not claims:
                raise ValueError("has_place_state_claim is true but claims is empty")
            if claims and not has_place_state_claim:
                raise ValueError("claims are present but has_place_state_claim is false")

            base = {
                "passage_id": source["passage_id"],
                "sentence_number": int(source["sentence_number"]),
                "prompt_version": run["prompt_version"],
                "model": run["model"],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "run_id": run_id,
                "created_at": created_at,
            }
            parsed.reviews.append(
                {
                    **base,
                    "has_place_state_claim": has_place_state_claim,
                    "summary": args.get("summary") or "",
                }
            )
            for claim_index, claim in enumerate(claims, start=1):
                place_status = claim.get("place_status")
                if place_status not in PLACE_STATE_STATUSES:
                    raise ValueError(f"Invalid place status: {place_status}")
                temporal_scope = claim.get("temporal_scope")
                if temporal_scope not in PLACE_STATE_TEMPORAL_SCOPES:
                    raise ValueError(f"Invalid temporal scope: {temporal_scope}")
                confidence = claim.get("confidence")
                if confidence not in {"high", "medium", "low"}:
                    confidence = "low"
                parsed.mentions.append(
                    {
                        **base,
                        "claim_index": claim_index,
                        "exact_place_text": claim.get("exact_place_text") or "",
                        "canonical_place_name": claim.get("canonical_place_name") or "",
                        "place_status": place_status,
                        "temporal_scope": temporal_scope,
                        "evidence_quote": claim.get("evidence_quote") or "",
                        "confidence": confidence,
                        "rationale": claim.get("rationale") or "",
                        "target_label": place_state_target_label(
                            place_status, temporal_scope
                        ),
                    }
                )
            parsed.item_updates.append(
                {
                    "request_number": request_number,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "status": "completed",
                    "error": None,
                }
            )
            parsed.seen_requests.add(request_number)
        except Exception as exc:
            if request_number is not None:
                parsed.item_updates.append(
                    {
                        "request_number": request_number,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "status": "failed",
                        "error": str(exc),
                    }
                )
            parsed.failures.append(
                {"custom_id": record.get("custom_id"), "error": str(exc)}
            )

    for request_number in sorted(set(item_lookup) - parsed.seen_requests):
        parsed.item_updates.append(
            {
                "request_number": request_number,
                "input_tokens": 0,
                "output_tokens": 0,
                "status": "failed",
                "error": "No output record returned for request",
            }
        )
        parsed.failures.append(
            {
                "custom_id": f"senttag:place-state:{run_id}:{request_number}",
                "error": "No output record returned for request",
            }
        )
    return parsed


def load_place_state_runs(
    conn: psycopg.Connection,
    *,
    prompt_version: str,
    batch_run_id: str | None,
) -> list[dict[str, Any]]:
    where = ["mode = 'place-state-batch'", "prompt_version = %s"]
    params: list[Any] = [prompt_version]
    if batch_run_id:
        where.append("run_id = %s")
        params.append(batch_run_id)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT run_id, mode, prompt_version, model, completed_at, retrieved_at,
                   openai_batch_id, openai_output_file_id, openai_error_file_id
            FROM sentence_tagging_runs
            WHERE {" AND ".join(where)}
            ORDER BY started_at
            """,
            params,
        )
        columns = [column.name for column in cursor.description or []]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def load_batch_items(conn: psycopg.Connection, run_id: str) -> dict[int, dict[str, Any]]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT request_number, mode, prompt_version, passage_id, sentence_number
            FROM sentence_tagging_batch_items
            WHERE run_id = %s
            ORDER BY request_number
            """,
            (run_id,),
        )
        columns = [column.name for column in cursor.description or []]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {int(row["request_number"]): row for row in rows}


def fetch_output_text(client: OpenAI, output_file_id: str) -> str:
    output = client.files.content(output_file_id)
    return output.text


def insert_parsed_recovery(
    conn: psycopg.Connection,
    parsed: ParsedRecovery,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        return
    with conn.cursor() as cursor:
        if parsed.reviews:
            cursor.executemany(
                """
                INSERT INTO sentence_place_state_reviews (
                    passage_id, sentence_number, prompt_version, model,
                    has_place_state_claim, summary, input_tokens, output_tokens,
                    run_id, created_at
                )
                VALUES (
                    %(passage_id)s, %(sentence_number)s, %(prompt_version)s,
                    %(model)s, %(has_place_state_claim)s, %(summary)s,
                    %(input_tokens)s, %(output_tokens)s, %(run_id)s, %(created_at)s
                )
                ON CONFLICT (passage_id, sentence_number, prompt_version) DO UPDATE
                SET model = EXCLUDED.model,
                    has_place_state_claim = EXCLUDED.has_place_state_claim,
                    summary = EXCLUDED.summary,
                    input_tokens = EXCLUDED.input_tokens,
                    output_tokens = EXCLUDED.output_tokens,
                    run_id = EXCLUDED.run_id,
                    created_at = EXCLUDED.created_at
                """,
                parsed.reviews,
            )
            delete_keys = {
                (row["passage_id"], row["sentence_number"], row["prompt_version"])
                for row in parsed.reviews
            }
            cursor.executemany(
                """
                DELETE FROM place_state_mentions
                WHERE passage_id = %s
                  AND sentence_number = %s
                  AND prompt_version = %s
                """,
                list(delete_keys),
            )
        if parsed.mentions:
            cursor.executemany(
                """
                INSERT INTO place_state_mentions (
                    passage_id, sentence_number, prompt_version, model, claim_index,
                    exact_place_text, canonical_place_name, place_status,
                    temporal_scope, evidence_quote, confidence, rationale,
                    target_label, input_tokens, output_tokens, run_id, created_at
                )
                VALUES (
                    %(passage_id)s, %(sentence_number)s, %(prompt_version)s,
                    %(model)s, %(claim_index)s, %(exact_place_text)s,
                    %(canonical_place_name)s, %(place_status)s, %(temporal_scope)s,
                    %(evidence_quote)s, %(confidence)s, %(rationale)s,
                    %(target_label)s, %(input_tokens)s, %(output_tokens)s,
                    %(run_id)s, %(created_at)s
                )
                ON CONFLICT (
                    passage_id, sentence_number, prompt_version, claim_index
                ) DO UPDATE
                SET model = EXCLUDED.model,
                    exact_place_text = EXCLUDED.exact_place_text,
                    canonical_place_name = EXCLUDED.canonical_place_name,
                    place_status = EXCLUDED.place_status,
                    temporal_scope = EXCLUDED.temporal_scope,
                    evidence_quote = EXCLUDED.evidence_quote,
                    confidence = EXCLUDED.confidence,
                    rationale = EXCLUDED.rationale,
                    target_label = EXCLUDED.target_label,
                    input_tokens = EXCLUDED.input_tokens,
                    output_tokens = EXCLUDED.output_tokens,
                    run_id = EXCLUDED.run_id,
                    created_at = EXCLUDED.created_at
                """,
                parsed.mentions,
            )
        if parsed.item_updates:
            cursor.executemany(
                """
                UPDATE sentence_tagging_batch_items
                SET input_tokens = %(input_tokens)s,
                    output_tokens = %(output_tokens)s,
                    status = %(status)s,
                    error = %(error)s
                WHERE run_id = %(run_id)s
                  AND request_number = %(request_number)s
                """,
                parsed.item_updates,
            )
    conn.commit()


def summarize_mentions(mentions: list[dict[str, Any]]) -> str:
    statuses = Counter(row["place_status"] for row in mentions)
    present_negative = sum(
        1
        for row in mentions
        if row["temporal_scope"] == "pausanias_present"
        and row["target_label"] == "does_not_survive"
    )
    parts = [
        f"claims={len(mentions)}",
        f"pausanias_present_negative={present_negative}",
    ]
    if statuses:
        parts.append(
            "statuses="
            + ",".join(f"{status}:{count}" for status, count in sorted(statuses.items()))
        )
    return "; ".join(parts)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recover retired place-state Batch API outputs into typed tables."
    )
    add_database_argument(parser)
    parser.add_argument("--openai-api-key-file", default="~/.openai.key")
    parser.add_argument("--batch-run-id")
    parser.add_argument("--prompt-version", default=PLACE_STATE_PROMPT_VERSION)
    parser.add_argument(
        "--jsonl-file",
        type=Path,
        help=(
            "Parse this saved OpenAI batch output JSONL instead of refetching the "
            "stored OpenAI output file. Requires --batch-run-id."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-schema-init",
        action="store_true",
        help="Do not apply database/schema.sql before inserting rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    if args.jsonl_file and not args.batch_run_id:
        raise SystemExit("--jsonl-file requires --batch-run-id")

    with connect(args.database_url) as conn:
        if not args.skip_schema_init:
            initialize_schema(conn)
        runs = load_place_state_runs(
            conn,
            prompt_version=args.prompt_version,
            batch_run_id=args.batch_run_id,
        )
        if not runs:
            print("No stored place-state batch runs found.")
            return

        client = None
        if not args.jsonl_file:
            client = OpenAI(api_key=load_openai_api_key(args.openai_api_key_file))

        total_reviews = 0
        total_claims = 0
        total_failures = 0
        for run in runs:
            run_id = run["run_id"]
            if args.jsonl_file:
                output_text = args.jsonl_file.read_text(encoding="utf-8")
            else:
                output_file_id = run.get("openai_output_file_id")
                if not output_file_id:
                    print(f"{run_id}: skipping; no stored OpenAI output file id.")
                    continue
                assert client is not None
                output_text = fetch_output_text(client, output_file_id)
            item_lookup = load_batch_items(conn, run_id)
            parsed = parse_output_text(output_text, run=run, item_lookup=item_lookup)
            for item in parsed.item_updates:
                item["run_id"] = run_id
            insert_parsed_recovery(conn, parsed, dry_run=args.dry_run)
            total_reviews += len(parsed.reviews)
            total_claims += len(parsed.mentions)
            total_failures += len(parsed.failures)
            action = "Would recover" if args.dry_run else "Recovered"
            reviews_with_claims = sum(
                1 for row in parsed.reviews if row["has_place_state_claim"]
            )
            print(
                f"{action} {run_id}: reviews={len(parsed.reviews)}, "
                f"reviews_with_claims={reviews_with_claims}, "
                f"{summarize_mentions(parsed.mentions)}, "
                f"failures={len(parsed.failures)}."
            )
        print(
            f"Total: reviews={total_reviews}, claims={total_claims}, "
            f"failures={total_failures}, dry_run={args.dry_run}."
        )


if __name__ == "__main__":
    main()
