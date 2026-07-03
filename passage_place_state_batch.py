#!/usr/bin/env python
"""Submit and fetch passage-level place-state Batch API runs."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from pausanias_db import add_database_argument, connect, initialize_schema
from place_state_candidate_importer import DEFAULT_SOURCE_VERSION
from recover_place_state_outputs import (
    PLACE_STATE_STATUSES,
    PLACE_STATE_TEMPORAL_SCOPES,
    place_state_target_label,
)


DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_PROMPT_VERSION = "passage-place-state-v1"
DEFAULT_TOKENS_PER_PASSAGE = 3500
TERMINAL_RUN_STATUSES = {
    "completed",
    "completed_with_failures",
    "failed",
    "batch_failed",
    "batch_expired",
    "batch_cancelled",
    "batch_canceled",
}


@dataclass
class ParsedBatch:
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


def custom_id(run_id: str, request_number: int) -> str:
    return f"passageplacestate:{run_id}:{request_number}"


def parse_custom_id(value: str) -> tuple[str, int]:
    parts = str(value).split(":")
    if len(parts) != 3 or parts[0] != "passageplacestate":
        raise ValueError(f"Unexpected custom_id {value!r}")
    return parts[1], int(parts[2])


def request_limit(args: argparse.Namespace) -> int | None:
    limits = []
    if args.stop_after is not None:
        limits.append(args.stop_after)
    if args.token_budget is not None:
        limits.append(max(1, args.token_budget // args.tokens_per_passage))
    if not limits:
        return None
    return min(limits)


def place_state_tool() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "save_passage_place_state_review",
                "description": (
                    "Save explicit Pausanias place-state claims from a numbered passage."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "has_place_state_claim": {
                            "type": "boolean",
                            "description": (
                                "True when the passage explicitly makes one or more "
                                "survival, habitation, ruin, abandonment, destruction, "
                                "renaming, refoundation, or transfer claims about places."
                            ),
                        },
                        "summary": {
                            "type": "string",
                            "description": "Short passage-level summary of the decision.",
                        },
                        "claims": {
                            "type": "array",
                            "description": (
                                "One row per explicit place-state claim in the passage."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "sentence_number": {
                                        "type": "integer",
                                        "description": (
                                            "The numbered sentence with the strongest evidence."
                                        ),
                                    },
                                    "exact_place_text": {
                                        "type": "string",
                                        "description": "The place wording in the passage.",
                                    },
                                    "canonical_place_name": {
                                        "type": "string",
                                        "description": "A normalized place name.",
                                    },
                                    "place_status": {
                                        "type": "string",
                                        "enum": sorted(PLACE_STATE_STATUSES),
                                    },
                                    "temporal_scope": {
                                        "type": "string",
                                        "enum": sorted(PLACE_STATE_TEMPORAL_SCOPES),
                                        "description": (
                                            "Use pausanias_present only for status in "
                                            "Pausanias' own time."
                                        ),
                                    },
                                    "evidence_quote": {
                                        "type": "string",
                                        "description": (
                                            "Shortest Greek or English phrase supporting the claim."
                                        ),
                                    },
                                    "confidence": {
                                        "type": "string",
                                        "enum": ["high", "medium", "low"],
                                    },
                                    "rationale": {
                                        "type": "string",
                                        "description": "One short reason for the classification.",
                                    },
                                },
                                "required": [
                                    "sentence_number",
                                    "exact_place_text",
                                    "canonical_place_name",
                                    "place_status",
                                    "temporal_scope",
                                    "evidence_quote",
                                    "confidence",
                                    "rationale",
                                ],
                            },
                        },
                    },
                    "required": ["has_place_state_claim", "summary", "claims"],
                },
            },
        }
    ]


def completion_body(args: argparse.Namespace, row: dict[str, Any]) -> dict[str, Any]:
    system_prompt = (
        "You are extracting explicit place-state claims from Pausanias passage by "
        "passage. You will receive one numbered Pausanias section with Greek and "
        "English sentence pairs. Use the whole passage context to resolve ellipsis, "
        "pronouns, and cases where a place is named in one sentence but its state is "
        "described in another.\n\n"
        "Identify only claims where Pausanias says or directly implies that a named "
        "or clearly delimited place still exists, is inhabited, remains materially "
        "present, remains only as ruins/remains/traces, is abandoned/deserted, has "
        "been destroyed with no trace, or has been renamed/refounded/transferred. "
        "Do not infer survival merely because a place is named, appears on a route, "
        "has a monument, or is the setting for a story.\n\n"
        "Use temporal_scope='pausanias_present' only for the place's state in "
        "Pausanias' own time. If a passage narrates a past destruction or desertion "
        "but does not say that this remained true in Pausanias' time, use "
        "past_before_pausanias. If the passage says both that a place was destroyed "
        "and later refounded, return separate claims if needed.\n\n"
        "Status guide:\n"
        "- inhabited_still_exists: Pausanias presents the place as a continuing "
        "inhabited settlement/city/village in his time.\n"
        "- extant_uninhabited: the place, site, sanctuary, or settlement remains "
        "materially present, but habitation is absent or not asserted.\n"
        "- ruined_or_remains: Pausanias says only ruins/remains/traces are present.\n"
        "- abandoned_or_deserted: Pausanias says it is deserted, uninhabited, empty, "
        "or abandoned.\n"
        "- destroyed_no_trace: Pausanias says the place has been destroyed, vanished, "
        "or has no surviving trace.\n"
        "- renamed_refounded_or_transferred: the claim is mainly that the place changed "
        "name, was refounded, or its population/site moved.\n"
        "- unclear: there is a real state claim, but the status is uncertain.\n\n"
        "Candidate hints, if provided, are only search aids. Correct them if the "
        "passage context shows they are false positives."
    )
    candidate_summary = row.get("candidate_summary") or "No deterministic candidates."
    user_content = (
        f"Passage {row['passage_id']}\n\n"
        f"Candidate hints:\n{candidate_summary}\n\n"
        f"Numbered sentences:\n{row['numbered_sentences']}\n\n"
        "Extract passage-level place-state claims using the "
        "save_passage_place_state_review function."
    )
    return {
        "model": args.model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "tools": place_state_tool(),
        "tool_choice": {
            "type": "function",
            "function": {"name": "save_passage_place_state_review"},
        },
    }


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
                problems.append(f"line {line_number}: unexpected url")
            if not str(payload.get("custom_id", "")).startswith("passageplacestate:"):
                problems.append(f"line {line_number}: unexpected custom_id")
    if problems:
        raise ValueError("Invalid passage place-state batch file:\n" + "\n".join(problems))


def load_unprocessed_passages(conn, args: argparse.Namespace) -> list[dict[str, Any]]:
    limit = request_limit(args)
    candidate_filter = "AND COALESCE(cc.candidate_count, 0) > 0" if args.candidate_only else ""
    order_by = """
        CASE WHEN COALESCE(cc.candidate_count, 0) > 0 THEN 0 ELSE 1 END,
        COALESCE(cc.candidate_count, 0) DESC,
        md5(sr.passage_id || ':' || %s)
    """ if args.candidate_first else "md5(sr.passage_id || ':' || %s)"
    params: list[Any] = [
        args.candidate_source_version,
        args.prompt_version,
        args.prompt_version,
        args.random_seed,
    ]
    limit_clause = ""
    if limit:
        limit_clause = "LIMIT %s"
        params.append(limit)
    terminal_statuses = tuple(TERMINAL_RUN_STATUSES)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
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
            ), candidate_rows AS (
                SELECT
                    passage_id,
                    string_agg(
                        '[' || sentence_number || '] ' || source_type || '/' ||
                        category || ': ' || matched_text,
                        E'\n'
                        ORDER BY sentence_number, source_type, category, matched_text
                    ) AS candidate_summary,
                    count(*) AS candidate_count
                FROM place_state_candidate_sentences
                WHERE source_version = %s
                GROUP BY passage_id
            )
            SELECT
                sr.passage_id,
                sr.numbered_sentences,
                COALESCE(cc.candidate_summary, '') AS candidate_summary,
                COALESCE(cc.candidate_count, 0) AS candidate_count
            FROM section_rows sr
            LEFT JOIN candidate_rows cc ON cc.passage_id = sr.passage_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM passage_place_state_reviews r
                WHERE r.passage_id = sr.passage_id
                  AND r.prompt_version = %s
            )
              AND NOT EXISTS (
                SELECT 1
                FROM passage_place_state_batch_items bi
                JOIN passage_place_state_runs r ON r.run_id = bi.run_id
                WHERE bi.passage_id = sr.passage_id
                  AND r.prompt_version = %s
                  AND r.status <> ALL(%s)
            )
            {candidate_filter}
            ORDER BY {order_by}
            {limit_clause}
            """,
            [
                params[0],
                params[1],
                params[2],
                list(terminal_statuses),
                params[3],
                *params[4:],
            ],
        )
        columns = [column.name for column in cursor.description or []]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def recent_submission(conn, args: argparse.Namespace) -> dict[str, Any] | None:
    if args.skip_if_submitted_hours <= 0:
        return None
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT run_id, submitted_at, status, request_count
            FROM passage_place_state_runs
            WHERE prompt_version = %s
              AND api_mode = 'batch'
              AND submitted_at IS NOT NULL
              AND submitted_at::timestamptz >= (
                  now() - (%s || ' hours')::interval
              )
            ORDER BY submitted_at DESC
            LIMIT 1
            """,
            (args.prompt_version, float(args.skip_if_submitted_hours)),
        )
        row = cursor.fetchone()
        if not row:
            return None
        columns = [column.name for column in cursor.description or []]
        return dict(zip(columns, row))


def write_submission(conn, payload: dict[str, Any]) -> None:
    run = payload["run"]
    items = payload.get("items") or []
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO passage_place_state_runs (
                run_id, started_at, completed_at, model, prompt_version, status,
                token_budget, tokens_per_passage_estimate, input_tokens, output_tokens,
                processed_count, api_mode, request_count, random_seed,
                candidate_source_version, notes
            )
            VALUES (
                %(run_id)s, %(started_at)s, %(completed_at)s, %(model)s,
                %(prompt_version)s, %(status)s, %(token_budget)s,
                %(tokens_per_passage_estimate)s, 0, 0, 0, 'batch',
                %(request_count)s, %(random_seed)s, %(candidate_source_version)s,
                %(notes)s
            )
            ON CONFLICT (run_id) DO UPDATE
            SET status = EXCLUDED.status,
                token_budget = EXCLUDED.token_budget,
                tokens_per_passage_estimate = EXCLUDED.tokens_per_passage_estimate,
                api_mode = 'batch',
                request_count = EXCLUDED.request_count,
                random_seed = EXCLUDED.random_seed,
                candidate_source_version = EXCLUDED.candidate_source_version,
                notes = EXCLUDED.notes
            """,
            run,
        )
        if items:
            cursor.executemany(
                """
                INSERT INTO passage_place_state_batch_items (
                    run_id, request_number, passage_id, estimated_tokens,
                    input_tokens, output_tokens, status, error, created_at
                )
                VALUES (
                    %(run_id)s, %(request_number)s, %(passage_id)s,
                    %(estimated_tokens)s, 0, 0, 'submitted', NULL, %(created_at)s
                )
                ON CONFLICT (run_id, request_number) DO UPDATE
                SET passage_id = EXCLUDED.passage_id,
                    estimated_tokens = EXCLUDED.estimated_tokens,
                    status = EXCLUDED.status,
                    error = NULL
                """,
                items,
            )
    conn.commit()


def update_batch_ids(conn, run_id: str, **values: Any) -> None:
    assignments = []
    params: list[Any] = []
    for column, value in values.items():
        if value is not None:
            assignments.append(f"{column} = %s")
            params.append(value)
    if not assignments:
        return
    params.append(run_id)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE passage_place_state_runs
            SET {", ".join(assignments)}
            WHERE run_id = %s
            """,
            params,
        )
    conn.commit()


def submit_batch(conn, client: OpenAI, args: argparse.Namespace) -> None:
    recent = recent_submission(conn, args)
    if recent:
        print(
            f"Skipping passage place-state submission: recent run {recent['run_id']} "
            f"submitted at {recent['submitted_at']} with {recent['request_count']} requests."
        )
        return
    rows = load_unprocessed_passages(conn, args)
    if not rows:
        print("No unsubmitted passage place-state rows found.")
        return
    run_id = str(uuid.uuid4())
    started_at = now_iso()
    batch_file = (
        Path(args.batch_file)
        if args.batch_file
        else Path("tmp") / f"passage-place-state-batch-{run_id}.jsonl"
    )
    batch_file.parent.mkdir(parents=True, exist_ok=True)
    items = []
    with batch_file.open("w", encoding="utf-8") as handle:
        for request_number, row in enumerate(rows, start=1):
            items.append(
                {
                    "run_id": run_id,
                    "request_number": request_number,
                    "passage_id": row["passage_id"],
                    "estimated_tokens": args.tokens_per_passage,
                    "created_at": started_at,
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
            "completed_at": None,
            "model": args.model,
            "prompt_version": args.prompt_version,
            "status": "batch_prepared" if args.dry_run else "batch_submitting",
            "token_budget": args.token_budget,
            "tokens_per_passage_estimate": args.tokens_per_passage,
            "request_count": len(items),
            "random_seed": args.random_seed,
            "candidate_source_version": args.candidate_source_version,
            "notes": f"batch_file={batch_file}",
        },
        "items": items,
    }
    if args.dry_run:
        print(
            f"Dry run {run_id}: wrote {len(items)} passage place-state requests "
            f"to {batch_file}; estimated {len(items) * args.tokens_per_passage} tokens."
        )
        return
    write_submission(conn, payload)
    with batch_file.open("rb") as handle:
        batch_input_file = client.files.create(file=handle, purpose="batch")
    result = client.batches.create(
        input_file_id=batch_input_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": f"pausanias passage place-state {run_id}",
            "local_run_id": run_id,
            "prompt_version": args.prompt_version,
        },
    )
    submitted_at = now_iso()
    update_batch_ids(
        conn,
        run_id,
        openai_batch_id=result.id,
        openai_input_file_id=batch_input_file.id,
        status="batch_submitted",
        submitted_at=submitted_at,
    )
    print(
        f"Submitted passage place-state run {run_id}: {len(items)} requests, "
        f"estimated {len(items) * args.tokens_per_passage} tokens."
    )
    print(f"OpenAI batch id: {result.id}")
    print(f"Batch request file: {batch_file}")


def load_batch_runs(conn, batch_run_id: str | None) -> list[dict[str, Any]]:
    clauses = [
        "api_mode = 'batch'",
        "openai_batch_id IS NOT NULL",
        "retrieved_at IS NULL",
    ]
    params: list[Any] = []
    if batch_run_id:
        clauses.append("run_id = %s")
        params.append(batch_run_id)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT run_id, prompt_version, model, openai_batch_id
            FROM passage_place_state_runs
            WHERE {" AND ".join(clauses)}
            ORDER BY started_at
            """,
            params,
        )
        columns = [column.name for column in cursor.description or []]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def load_batch_items(conn, run_id: str) -> dict[int, dict[str, Any]]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT request_number, passage_id
            FROM passage_place_state_batch_items
            WHERE run_id = %s
            ORDER BY request_number
            """,
            (run_id,),
        )
        columns = [column.name for column in cursor.description or []]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {int(row["request_number"]): row for row in rows}


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


def normalize_sentence_number(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def parse_output_text(
    output_text: str,
    *,
    run: dict[str, Any],
    item_lookup: dict[int, dict[str, Any]],
) -> ParsedBatch:
    parsed = ParsedBatch()
    completed_at = run.get("completed_at") or now_iso()
    for line in output_text.splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        request_number = None
        try:
            output_run_id, request_number = parse_custom_id(record.get("custom_id", ""))
            if output_run_id != run["run_id"]:
                raise ValueError(
                    f"Output custom_id belongs to {output_run_id}, expected {run['run_id']}"
                )
            source = item_lookup.get(request_number)
            if not source:
                raise ValueError(f"No stored input row for request {request_number}")
            args, usage = extract_tool_arguments(record)
            input_tokens = int(usage.get("prompt_tokens", 0))
            output_tokens = int(usage.get("completion_tokens", 0))
            claims = args.get("claims") or []
            if not isinstance(claims, list):
                raise ValueError("claims must be a list")
            has_place_state_claim = bool(args.get("has_place_state_claim"))
            if has_place_state_claim and not claims:
                raise ValueError("has_place_state_claim is true but claims is empty")
            if claims and not has_place_state_claim:
                raise ValueError("claims are present but has_place_state_claim is false")
            base = {
                "passage_id": source["passage_id"],
                "prompt_version": run["prompt_version"],
                "model": run["model"],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "run_id": run["run_id"],
                "created_at": completed_at,
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
                        "sentence_number": normalize_sentence_number(
                            claim.get("sentence_number")
                        ),
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
            parsed.failures.append({"custom_id": record.get("custom_id"), "error": str(exc)})
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
                "custom_id": custom_id(run["run_id"], request_number),
                "error": "No output record returned for request",
            }
        )
    return parsed


def write_results(conn, payload: dict[str, Any]) -> None:
    run = payload["run"]
    parsed: ParsedBatch = payload["parsed"]
    with conn.cursor() as cursor:
        if parsed.item_updates:
            for row in parsed.item_updates:
                row["run_id"] = run["run_id"]
            cursor.executemany(
                """
                UPDATE passage_place_state_batch_items
                SET input_tokens = %(input_tokens)s,
                    output_tokens = %(output_tokens)s,
                    status = %(status)s,
                    error = %(error)s
                WHERE run_id = %(run_id)s
                  AND request_number = %(request_number)s
                """,
                parsed.item_updates,
            )
        if parsed.reviews:
            cursor.executemany(
                """
                INSERT INTO passage_place_state_reviews (
                    passage_id, prompt_version, model, has_place_state_claim,
                    summary, input_tokens, output_tokens, run_id, created_at
                )
                VALUES (
                    %(passage_id)s, %(prompt_version)s, %(model)s,
                    %(has_place_state_claim)s, %(summary)s, %(input_tokens)s,
                    %(output_tokens)s, %(run_id)s, %(created_at)s
                )
                ON CONFLICT (passage_id, prompt_version) DO UPDATE
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
            cursor.executemany(
                """
                DELETE FROM passage_place_state_mentions
                WHERE passage_id = %s
                  AND prompt_version = %s
                """,
                {(row["passage_id"], row["prompt_version"]) for row in parsed.reviews},
            )
        if parsed.mentions:
            cursor.executemany(
                """
                INSERT INTO passage_place_state_mentions (
                    passage_id, prompt_version, model, claim_index, sentence_number,
                    exact_place_text, canonical_place_name, place_status,
                    temporal_scope, evidence_quote, confidence, rationale,
                    target_label, input_tokens, output_tokens, run_id, created_at
                )
                VALUES (
                    %(passage_id)s, %(prompt_version)s, %(model)s, %(claim_index)s,
                    %(sentence_number)s, %(exact_place_text)s, %(canonical_place_name)s,
                    %(place_status)s, %(temporal_scope)s, %(evidence_quote)s,
                    %(confidence)s, %(rationale)s, %(target_label)s,
                    %(input_tokens)s, %(output_tokens)s, %(run_id)s, %(created_at)s
                )
                ON CONFLICT (passage_id, prompt_version, claim_index) DO UPDATE
                SET model = EXCLUDED.model,
                    sentence_number = EXCLUDED.sentence_number,
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
        cursor.execute(
            """
            UPDATE passage_place_state_runs
            SET completed_at = %(completed_at)s,
                status = %(status)s,
                input_tokens = %(input_tokens)s,
                output_tokens = %(output_tokens)s,
                processed_count = %(processed_count)s,
                api_mode = 'batch',
                request_count = %(request_count)s,
                openai_output_file_id = %(openai_output_file_id)s,
                openai_error_file_id = %(openai_error_file_id)s,
                retrieved_at = %(retrieved_at)s,
                notes = %(notes)s
            WHERE run_id = %(run_id)s
            """,
            run,
        )
    conn.commit()


def request_counts_text(result) -> str:
    counts = getattr(result, "request_counts", None)
    if not counts:
        return "no request counts yet"
    return (
        f"{getattr(counts, 'completed', 0)}/{getattr(counts, 'total', 0)} complete, "
        f"{getattr(counts, 'failed', 0)} failed"
    )


def check_batches(conn, client: OpenAI, batch_run_id: str | None) -> None:
    runs = load_batch_runs(conn, batch_run_id)
    if not runs:
        print("No unretrieved passage place-state Batch API runs found.")
        return
    for run in runs:
        result = client.batches.retrieve(run["openai_batch_id"])
        update_batch_ids(
            conn,
            run["run_id"],
            status=f"batch_{result.status}",
            openai_output_file_id=result.output_file_id,
            openai_error_file_id=result.error_file_id,
        )
        print(
            f"{run['run_id']} {run['openai_batch_id']}: "
            f"{result.status} ({request_counts_text(result)})"
        )


def fetch_batches(conn, client: OpenAI, batch_run_id: str | None) -> None:
    runs = load_batch_runs(conn, batch_run_id)
    if not runs:
        print("No unretrieved passage place-state Batch API runs found.")
        return
    for run in runs:
        result = client.batches.retrieve(run["openai_batch_id"])
        update_batch_ids(
            conn,
            run["run_id"],
            status=f"batch_{result.status}",
            openai_output_file_id=result.output_file_id,
            openai_error_file_id=result.error_file_id,
        )
        if result.status != "completed":
            print(f"{run['run_id']}: remote status is {result.status}; not fetching yet.")
            continue
        if not result.output_file_id:
            print(f"{run['run_id']}: completed but has no output file.")
            continue
        item_lookup = load_batch_items(conn, run["run_id"])
        output = client.files.content(result.output_file_id)
        completed_at = now_iso()
        parsed = parse_output_text(
            output.text,
            run={**run, "completed_at": completed_at},
            item_lookup=item_lookup,
        )
        input_tokens = sum(item["input_tokens"] for item in parsed.item_updates)
        output_tokens = sum(item["output_tokens"] for item in parsed.item_updates)
        processed_count = sum(1 for item in parsed.item_updates if item["status"] == "completed")
        status = "completed" if not parsed.failures else "completed_with_failures"
        notes = (
            f"failures={len(parsed.failures)}; mentions={len(parsed.mentions)}; "
            f"fetched_from_batch={run['openai_batch_id']}"
        )
        write_results(
            conn,
            {
                "run": {
                    "run_id": run["run_id"],
                    "completed_at": completed_at,
                    "status": status,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "processed_count": processed_count,
                    "request_count": len(item_lookup),
                    "openai_output_file_id": result.output_file_id,
                    "openai_error_file_id": result.error_file_id,
                    "retrieved_at": completed_at,
                    "notes": notes,
                },
                "parsed": parsed,
            },
        )
        status_counts = Counter(row["target_label"] for row in parsed.mentions)
        print(
            f"Fetched passage place-state run {run['run_id']}: "
            f"{processed_count}/{len(item_lookup)} passages saved, "
            f"{len(parsed.mentions)} mentions, "
            f"{input_tokens + output_tokens} tokens, {len(parsed.failures)} failures, "
            f"labels={dict(status_counts)}."
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit and fetch passage-level Pausanias place-state batches."
    )
    add_database_argument(parser)
    parser.add_argument("--openai-api-key-file", default="~/.openai.key")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION)
    parser.add_argument("--token-budget", type=int, default=100_000)
    parser.add_argument("--tokens-per-passage", type=int, default=DEFAULT_TOKENS_PER_PASSAGE)
    parser.add_argument("--stop-after", type=int, default=None)
    parser.add_argument("--random-seed", default=DEFAULT_PROMPT_VERSION)
    parser.add_argument("--candidate-source-version", default=DEFAULT_SOURCE_VERSION)
    parser.add_argument("--batch-file", default=None)
    parser.add_argument("--batch-run-id", default=None)
    parser.add_argument("--use-batch-api", action="store_true")
    parser.add_argument("--check-batches", action="store_true")
    parser.add_argument("--fetch-batches", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--candidate-first", action="store_true")
    parser.add_argument("--candidate-only", action="store_true")
    parser.add_argument(
        "--skip-if-submitted-hours",
        type=float,
        default=0.0,
        help="Skip submission if this prompt version was submitted recently.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    if not (args.use_batch_api or args.check_batches or args.fetch_batches):
        raise SystemExit("Specify --use-batch-api, --check-batches, or --fetch-batches.")
    with connect(args.database_url) as conn:
        initialize_schema(conn)
        client = OpenAI(api_key=load_openai_api_key(args.openai_api_key_file))
        if args.check_batches:
            check_batches(conn, client, args.batch_run_id)
            return
        if args.fetch_batches:
            fetch_batches(conn, client, args.batch_run_id)
            return
        submit_batch(conn, client, args)


if __name__ == "__main__":
    main()
