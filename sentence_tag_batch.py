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


# Two production classifiers, both no-context, temperature=0:
#   greta      -> "original-myth-history-other"      (simple forced single label)
#   greta-both -> "greta-inspired-myth-history-other" (two-flag, calibrated to Greta/Rosie)
GRETA_BATCH_PROMPT_VERSION = "original-myth-history-other"
GRETA_BOTH_BATCH_PROMPT_VERSION = "greta-inspired-myth-history-other"
DEFAULT_GRETA_MODEL = "gpt-5.4-mini"
DEFAULT_LEGACY_MODEL = "gpt-5"
DEFAULT_DISCOURSE_MODEL = "gpt-5.4-mini"
DEFAULT_PLACE_STATE_MODEL = "gpt-5.4-mini"
DEFAULT_GRETA_TOKENS_PER_SENTENCE = 545
DEFAULT_GRETA_BOTH_TOKENS_PER_SENTENCE = 680
DEFAULT_LEGACY_TOKENS_PER_SENTENCE = 540
DEFAULT_DISCOURSE_TOKENS_PER_SENTENCE = 1000
DEFAULT_PLACE_STATE_TOKENS_PER_SENTENCE = 1300
DISCOURSE_MODE_PROMPT_VERSION = "discourse-mode-v1"
PLACE_STATE_PROMPT_VERSION = "place-state-v1"
DEFAULT_GRAMMAR_MODEL = "gpt-5.4-mini"
DEFAULT_GRAMMAR_PROMPT_VERSION = "greek-sentence-grammar-v1"
GRETA_MODES = {"greta", "greta-both"}
DISCOURSE_MODES = [
    "route_locative_description",
    "monument_catalogue",
    "historical_narrative",
    "mythological_narrative",
    "ritual_ethnographic_description",
    "sources_traditions_discussion",
]
PLACE_STATE_STATUSES = [
    "inhabited_still_exists",
    "extant_uninhabited",
    "ruined_or_remains",
    "abandoned_or_deserted",
    "destroyed_no_trace",
    "renamed_refounded_or_transferred",
    "unclear",
]
PLACE_STATE_TEMPORAL_SCOPES = [
    "pausanias_present",
    "past_before_pausanias",
    "mythic_past",
    "later_commentary",
    "unclear",
]
PLACE_STATE_TARGET_LABELS = {
    "inhabited_still_exists": "survives",
    "extant_uninhabited": "survives",
    "ruined_or_remains": "does_not_survive",
    "abandoned_or_deserted": "does_not_survive",
    "destroyed_no_trace": "does_not_survive",
    "renamed_refounded_or_transferred": "exclude",
    "unclear": "exclude",
}
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


def postgres_text(value) -> str:
    return str(value).replace("\x00", "")


def sql_nullable_text(value) -> str:
    if value is None:
        return "NULL"
    return sql_string(postgres_text(value))


def sql_integer(value) -> str:
    return str(int(value or 0))


def sql_bool(value) -> str:
    return "TRUE" if bool(value) else "FALSE"


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
    parser.add_argument(
        "--mode",
        choices=("greta", "greta-both", "legacy", "discourse", "place-state"),
        default="greta",
    )
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
        "--priority-books-first",
        default="",
        help="Comma-separated book numbers to process before the natural order.",
    )
    parser.add_argument(
        "--priority-books-last",
        default="4,8",
        help="Comma-separated book numbers to leave until other books are submitted.",
    )
    parser.add_argument(
        "--random-order",
        action="store_true",
        help="Process untagged sentences in seeded pseudo-random order.",
    )
    parser.add_argument("--sample-seed", default=DISCOURSE_MODE_PROMPT_VERSION)
    parser.add_argument("--grammar-model", default=DEFAULT_GRAMMAR_MODEL)
    parser.add_argument("--grammar-prompt-version", default=DEFAULT_GRAMMAR_PROMPT_VERSION)
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
    if args.mode == "place-state":
        return DEFAULT_PLACE_STATE_MODEL
    if args.mode == "discourse":
        return DEFAULT_DISCOURSE_MODEL
    return DEFAULT_GRETA_MODEL if args.mode in GRETA_MODES else DEFAULT_LEGACY_MODEL


def mode_prompt_version(args: argparse.Namespace) -> str:
    if args.prompt_version:
        return args.prompt_version
    if args.mode == "greta":
        return GRETA_BATCH_PROMPT_VERSION
    if args.mode == "greta-both":
        return GRETA_BOTH_BATCH_PROMPT_VERSION
    if args.mode == "discourse":
        return DISCOURSE_MODE_PROMPT_VERSION
    if args.mode == "place-state":
        return PLACE_STATE_PROMPT_VERSION
    return LEGACY_PROMPT_VERSION


def mode_tokens_per_sentence(args: argparse.Namespace) -> int:
    if args.tokens_per_sentence:
        return args.tokens_per_sentence
    if args.mode == "greta":
        return DEFAULT_GRETA_TOKENS_PER_SENTENCE
    if args.mode == "greta-both":
        return DEFAULT_GRETA_BOTH_TOKENS_PER_SENTENCE
    if args.mode == "discourse":
        return DEFAULT_DISCOURSE_TOKENS_PER_SENTENCE
    if args.mode == "place-state":
        return DEFAULT_PLACE_STATE_TOKENS_PER_SENTENCE
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


def discourse_tool() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "save_discourse_mode_tag",
                "description": "Save the main discourse mode for one Pausanias sentence.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "discourse_mode": {
                            "type": "string",
                            "enum": DISCOURSE_MODES,
                            "description": "The sentence's primary discourse mode.",
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "rationale": {
                            "type": "string",
                            "description": "One short reason for the mode choice.",
                        },
                    },
                    "required": ["discourse_mode", "confidence", "rationale"],
                },
            },
        }
    ]


def place_state_tool() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "save_place_state_review",
                "description": (
                    "Save explicit Pausanias claims about whether places still "
                    "exist, remain only as ruins, or are deserted/destroyed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "has_place_state_claim": {
                            "type": "boolean",
                            "description": (
                                "True only if this sentence explicitly makes a "
                                "survival, habitation, ruin, abandonment, destruction, "
                                "renaming, refoundation, or transfer claim about a place."
                            ),
                        },
                        "summary": {
                            "type": "string",
                            "description": (
                                "Short summary of the sentence-level decision. Use an empty "
                                "string when there is nothing to summarize."
                            ),
                        },
                        "claims": {
                            "type": "array",
                            "description": (
                                "One item per explicit place-state claim. Leave empty when "
                                "has_place_state_claim is false."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "exact_place_text": {
                                        "type": "string",
                                        "description": "The place wording in the sentence.",
                                    },
                                    "canonical_place_name": {
                                        "type": "string",
                                        "description": (
                                            "A normalized English/Greek-compatible place name."
                                        ),
                                    },
                                    "place_status": {
                                        "type": "string",
                                        "enum": PLACE_STATE_STATUSES,
                                    },
                                    "temporal_scope": {
                                        "type": "string",
                                        "enum": PLACE_STATE_TEMPORAL_SCOPES,
                                        "description": (
                                            "Use pausanias_present only for claims about the "
                                            "state of the place in Pausanias' own time."
                                        ),
                                    },
                                    "evidence_quote": {
                                        "type": "string",
                                        "description": (
                                            "The shortest exact Greek or English phrase that "
                                            "supports the status."
                                        ),
                                    },
                                    "confidence": {
                                        "type": "string",
                                        "enum": ["high", "medium", "low"],
                                    },
                                    "rationale": {
                                        "type": "string",
                                        "description": "One short reason for this claim.",
                                    },
                                },
                                "required": [
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
        "temperature": 0,
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
        "You are tagging single sentences of Pausanias to match the human annotators "
        "Greta and Rosie, who highlighted Book 3 sentence by sentence. Mark two "
        "independent flags for THIS sentence only: references_mythic and "
        "references_historical. Judge the sentence by what it itself asserts, not by "
        "the episode around it. The annotators are conservative: a little under half "
        "of all sentences get neither flag. Do NOT inherit a label from neighbouring "
        "sentences.\n\n"
        "Set references_mythic = true only when the sentence itself narrates or "
        "asserts mythic content: a deed of a god or hero, divine or heroic genealogy, "
        "a foundation or naming legend, a cult etiology (why a rite/name/object exists, "
        "told as story), an oracle's pronouncement within myth, or an explicit claim "
        "that a mythic figure did/made/suffered something.\n\n"
        "Set references_historical = true only when the sentence itself narrates or "
        "asserts post-~500 BC historical content: a datable event, war, treaty, "
        "political act, institution's workings, victory record, dedication with a "
        "historical agent, or biography of a historical person.\n\n"
        "Set BOTH flags false (other) when the sentence is, in its own right: a route "
        "or topographic note (what comes next, distances, what is 'on the right'); a "
        "bare notice that a sanctuary, temple, statue, tomb, spring, or shrine exists "
        "or is located somewhere; a physical description of an object or place; a "
        "procedural or ritual instruction without narration; an authorial transition, "
        "cross-reference, or comment. Such sentences are 'other' EVEN when they sit "
        "inside a mythic or historical episode and EVEN when they name a god, hero, "
        "king, or famous place. Naming or locating a mythic/historic entity is not "
        "enough; the sentence must do the mythic or historical asserting.\n\n"
        "Use both flags true only when the single sentence genuinely asserts mythic and "
        "historical content together. When in doubt between a content flag and other, "
        "prefer other. Do not classify scepticism."
    )
    user_content = (
        f"Passage {passage_id}, sentence {sentence_number}:\n\n"
        f"Greek:\n{sentence}\n\nEnglish:\n{english_sentence}\n\n"
        "Classify this sentence using the save_greta_both_sentence_tag function."
    )
    return {
        "model": model,
        "temperature": 0,
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


def discourse_completion_body(
    *, model: str, passage_id: str, sentence_number: int, sentence: str, english_sentence: str
) -> dict:
    system_prompt = (
        "You are classifying single sentences of Pausanias by discourse mode. "
        "Choose exactly one primary mode for THIS sentence only, using the Greek "
        "and English together. Do not inherit a mode from neighboring sentences.\n\n"
        "Available modes:\n"
        "- route_locative_description: route sequence, distance, direction, topography, "
        "location, or physical/geographical description whose main work is orienting the reader.\n"
        "- monument_catalogue: bare notice, catalogue, attribution, dedication, inscription, "
        "artist note, or physical description of temples, statues, tombs, altars, images, "
        "buildings, offerings, or other monuments.\n"
        "- historical_narrative: narration or assertion of post-roughly-500-BCE human, "
        "political, military, institutional, biographical, or dedicatory events.\n"
        "- mythological_narrative: narration or assertion involving gods, heroes, mythic "
        "genealogy, foundation legend, heroic deed, divine action, or mythic etiology.\n"
        "- ritual_ethnographic_description: ritual procedure, cult practice, festival, "
        "sacrifice, local custom, ethnographic description, or social practice, without "
        "primarily narrating an event.\n"
        "- sources_traditions_discussion: explicit discussion of sources, variants, local "
        "traditions, reports, sayings, Pausanias' judgment, disagreement, or source reliability.\n\n"
        "If a sentence mentions a monument while mainly narrating why it exists, choose "
        "the narrative or sources mode. If it simply says what is there or who made/dedicated "
        "it, choose monument_catalogue. If it mainly tells how to move through or locate "
        "places, choose route_locative_description. When genuinely unsure, choose the mode "
        "that best describes the sentence's main rhetorical job and use medium or low confidence."
    )
    user_content = (
        f"Passage {passage_id}, sentence {sentence_number}:\n\n"
        f"Greek:\n{sentence}\n\nEnglish:\n{english_sentence}\n\n"
        "Classify this sentence using the save_discourse_mode_tag function."
    )
    return {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "tools": discourse_tool(),
        "tool_choice": {
            "type": "function",
            "function": {"name": "save_discourse_mode_tag"},
        },
    }


def place_state_completion_body(
    *, model: str, passage_id: str, sentence_number: int, sentence: str, english_sentence: str
) -> dict:
    system_prompt = (
        "You are extracting explicit place-state claims from single sentences of "
        "Pausanias. Identify only claims where Pausanias says or directly implies "
        "that a named or clearly delimited place still exists, is inhabited, remains "
        "only as ruins/remains, is abandoned/deserted, has been destroyed with no trace, "
        "or has been renamed/refounded/transferred. Do not infer a survival status merely "
        "because a place is named, appears on a route, has a monument, or is the setting "
        "for a myth or historical episode.\n\n"
        "Use temporal_scope='pausanias_present' only for the place's status in Pausanias' "
        "own time. Claims about mythic time, earlier history, or later commentary must not "
        "be treated as Pausanias-present evidence.\n\n"
        "Status guide:\n"
        "- inhabited_still_exists: Pausanias presents the place as a continuing inhabited "
        "settlement/city/village in his time.\n"
        "- extant_uninhabited: the place, site, sanctuary, or settlement remains materially "
        "present, but habitation is absent or not asserted.\n"
        "- ruined_or_remains: Pausanias says only ruins/remains/traces are present.\n"
        "- abandoned_or_deserted: Pausanias says it is deserted, uninhabited, empty, or "
        "abandoned.\n"
        "- destroyed_no_trace: Pausanias says the place has been destroyed, vanished, or has "
        "no surviving trace.\n"
        "- renamed_refounded_or_transferred: the state claim is mainly that the place changed "
        "name, was refounded, or its population/site moved.\n"
        "- unclear: there is a real state claim, but the status is uncertain.\n\n"
        "Return every explicit place-state claim in the sentence. If there is no such claim, "
        "set has_place_state_claim=false and claims=[]."
    )
    user_content = (
        f"Passage {passage_id}, sentence {sentence_number}:\n\n"
        f"Greek:\n{sentence}\n\nEnglish:\n{english_sentence}\n\n"
        "Extract place-state claims using the save_place_state_review function."
    )
    return {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "tools": place_state_tool(),
        "tool_choice": {
            "type": "function",
            "function": {"name": "save_place_state_review"},
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
    if args.mode == "discourse":
        return discourse_completion_body(**kwargs)
    if args.mode == "place-state":
        return place_state_completion_body(**kwargs)
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


def priority_order_sql(priority_books_first: list[str], priority_books_last: list[str]) -> str:
    natural_order = (
        "split_part(s.passage_id, '.', 1)::integer, "
        "split_part(s.passage_id, '.', 2)::integer, "
        "split_part(s.passage_id, '.', 3)::integer, "
        "s.sentence_number"
    )
    if not priority_books_first and not priority_books_last:
        return natural_order
    book_expr = "split_part(s.passage_id, '.', 1)"
    order_parts = []
    if priority_books_first:
        first_books = ", ".join(sql_string(book) for book in priority_books_first)
        order_parts.append(
            f"CASE WHEN {book_expr} = ANY(ARRAY[{first_books}]) THEN 0 ELSE 1 END"
        )
    if priority_books_last:
        last_books = ", ".join(sql_string(book) for book in priority_books_last)
        order_parts.append(
            f"CASE WHEN {book_expr} = ANY(ARRAY[{last_books}]) THEN 1 ELSE 0 END"
        )
    order_parts.append(natural_order)
    return ", ".join(order_parts)


def pending_status_sql() -> str:
    statuses = ", ".join(sql_string(status) for status in TERMINAL_RUN_STATUSES)
    return statuses


def unprocessed_sql(args: argparse.Namespace) -> str:
    mode = run_mode(args)
    prompt_version = mode_prompt_version(args)
    limit = request_limit(args)
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    if args.random_order:
        order_by = (
            "md5(s.passage_id || ':' || s.sentence_number::text || ':' || "
            f"{sql_string(args.sample_seed)})"
        )
    else:
        order_by = priority_order_sql(
            parse_list(args.priority_books_first),
            parse_list(args.priority_books_last),
        )
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
    join_clause = ""
    select_context = ""

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
    elif args.mode == "discourse":
        work_clause = f"""
      AND EXISTS (
          SELECT 1
          FROM sentence_llm_grammar_analyses g
          WHERE g.passage_id = s.passage_id
            AND g.sentence_number = s.sentence_number
            AND g.model = {sql_string(args.grammar_model)}
            AND g.prompt_version = {sql_string(args.grammar_prompt_version)}
      )
      AND NOT EXISTS (
          SELECT 1
          FROM sentence_discourse_mode_tags t
          WHERE t.passage_id = s.passage_id
            AND t.sentence_number = s.sentence_number
            AND t.prompt_version = {sql_string(prompt_version)}
      )
"""
    elif args.mode == "place-state":
        work_clause = f"""
      AND NOT EXISTS (
          SELECT 1
          FROM sentence_place_state_reviews t
          WHERE t.passage_id = s.passage_id
            AND t.sentence_number = s.sentence_number
            AND t.prompt_version = {sql_string(prompt_version)}
      )
"""
    else:
        work_clause = "      AND s.references_mythic_era IS NULL\n"
    return f"""
COPY (
    SELECT s.passage_id, s.sentence_number, s.sentence, s.english_sentence{select_context}
    FROM greek_sentences s
{join_clause}
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
    run = payload["run"]
    items = payload.get("items") or []
    run_values = ", ".join(
        [
            sql_string(run["run_id"]),
            sql_string(run["started_at"]),
            sql_nullable_text(run.get("completed_at")),
            sql_string(run["mode"]),
            sql_string(run["model"]),
            sql_string(run["prompt_version"]),
            sql_string(run["status"]),
            sql_integer(run.get("token_budget")),
            "0",
            "0",
            "0",
            "0",
            "'batch'",
            sql_integer(run.get("request_count")),
            sql_nullable_text(run.get("notes")),
        ]
    )
    sql = f"""
INSERT INTO sentence_tagging_runs (
    run_id, started_at, completed_at, mode, model, prompt_version, status,
    token_budget, input_tokens, output_tokens, processed_count, discrepancy_count,
    api_mode, request_count, notes
)
VALUES ({run_values})
ON CONFLICT (run_id) DO UPDATE
SET status = EXCLUDED.status,
    token_budget = EXCLUDED.token_budget,
    api_mode = 'batch',
    request_count = EXCLUDED.request_count,
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
                        sql_string(run["mode"]),
                        sql_string(run["prompt_version"]),
                        sql_string(item["passage_id"]),
                        sql_integer(item["sentence_number"]),
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

INSERT INTO sentence_tagging_batch_items (
    run_id, request_number, mode, prompt_version, passage_id, sentence_number,
    estimated_tokens, input_tokens, output_tokens, status, error, created_at
)
VALUES
    {item_sql_values}
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
      AND mode IN (
          'greta-batch',
          'greta-both-batch',
          'legacy-batch',
          'discourse-batch',
          'place-state-batch'
      )
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


def place_state_target_label(place_status: str, temporal_scope: str) -> str:
    if temporal_scope != "pausanias_present":
        return "exclude"
    return PLACE_STATE_TARGET_LABELS.get(place_status, "exclude")


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
    run = payload["run"]
    sql = ""
    items = payload.get("items") or []
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
UPDATE sentence_tagging_batch_items bi
SET input_tokens = item_rows.input_tokens,
    output_tokens = item_rows.output_tokens,
    status = item_rows.status,
    error = item_rows.error
FROM item_rows
WHERE bi.run_id = {sql_string(run["run_id"])}
  AND bi.request_number = item_rows.request_number;
"""

    def append_insert(rows: list[dict], *, table: str, columns: list[str], values_for_row, conflict: str) -> None:
        nonlocal sql
        if not rows:
            return
        row_values = []
        for row in rows:
            row_values.append("(" + ", ".join(values_for_row(row)) + ")")
        sql_values = ",\n    ".join(row_values)
        column_list = ", ".join(columns)
        sql += f"""
INSERT INTO {table} ({column_list})
VALUES
    {sql_values}
{conflict}
"""

    append_insert(
        payload.get("greta_tags") or [],
        table="sentence_greta_tags",
        columns=[
            "passage_id",
            "sentence_number",
            "prompt_version",
            "model",
            "myth_history_bucket",
            "expresses_scepticism",
            "confidence",
            "rationale",
            "input_tokens",
            "output_tokens",
            "run_id",
            "created_at",
        ],
        values_for_row=lambda row: [
            sql_string(row["passage_id"]),
            sql_integer(row["sentence_number"]),
            sql_string(run["prompt_version"]),
            sql_string(run["model"]),
            sql_string(row["myth_history_bucket"]),
            "FALSE",
            sql_string(row["confidence"]),
            sql_string(row["rationale"]),
            sql_integer(row["input_tokens"]),
            sql_integer(row["output_tokens"]),
            sql_string(run["run_id"]),
            sql_string(run["completed_at"]),
        ],
        conflict="""ON CONFLICT (passage_id, sentence_number, prompt_version) DO UPDATE
SET model = EXCLUDED.model,
    myth_history_bucket = EXCLUDED.myth_history_bucket,
    expresses_scepticism = EXCLUDED.expresses_scepticism,
    confidence = EXCLUDED.confidence,
    rationale = EXCLUDED.rationale,
    input_tokens = EXCLUDED.input_tokens,
    output_tokens = EXCLUDED.output_tokens,
    run_id = EXCLUDED.run_id,
    created_at = EXCLUDED.created_at;
""",
    )
    append_insert(
        payload.get("greta_both_tags") or [],
        table="sentence_greta_both_tags",
        columns=[
            "passage_id",
            "sentence_number",
            "prompt_version",
            "model",
            "references_mythic",
            "references_historical",
            "myth_history_bucket",
            "confidence",
            "rationale",
            "input_tokens",
            "output_tokens",
            "run_id",
            "created_at",
        ],
        values_for_row=lambda row: [
            sql_string(row["passage_id"]),
            sql_integer(row["sentence_number"]),
            sql_string(run["prompt_version"]),
            sql_string(run["model"]),
            sql_bool(row["references_mythic"]),
            sql_bool(row["references_historical"]),
            sql_string(row["myth_history_bucket"]),
            sql_string(row["confidence"]),
            sql_string(row["rationale"]),
            sql_integer(row["input_tokens"]),
            sql_integer(row["output_tokens"]),
            sql_string(run["run_id"]),
            sql_string(run["completed_at"]),
        ],
        conflict="""ON CONFLICT (passage_id, sentence_number, prompt_version) DO UPDATE
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
""",
    )
    append_insert(
        payload.get("discourse_tags") or [],
        table="sentence_discourse_mode_tags",
        columns=[
            "passage_id",
            "sentence_number",
            "prompt_version",
            "model",
            "discourse_mode",
            "confidence",
            "rationale",
            "input_tokens",
            "output_tokens",
            "run_id",
            "created_at",
        ],
        values_for_row=lambda row: [
            sql_string(row["passage_id"]),
            sql_integer(row["sentence_number"]),
            sql_string(run["prompt_version"]),
            sql_string(run["model"]),
            sql_string(row["discourse_mode"]),
            sql_string(row["confidence"]),
            sql_string(row["rationale"]),
            sql_integer(row["input_tokens"]),
            sql_integer(row["output_tokens"]),
            sql_string(run["run_id"]),
            sql_string(run["completed_at"]),
        ],
        conflict="""ON CONFLICT (passage_id, sentence_number, prompt_version) DO UPDATE
SET model = EXCLUDED.model,
    discourse_mode = EXCLUDED.discourse_mode,
    confidence = EXCLUDED.confidence,
    rationale = EXCLUDED.rationale,
    input_tokens = EXCLUDED.input_tokens,
    output_tokens = EXCLUDED.output_tokens,
    run_id = EXCLUDED.run_id,
    created_at = EXCLUDED.created_at;
""",
    )
    place_state_reviews = payload.get("place_state_reviews") or []
    append_insert(
        place_state_reviews,
        table="sentence_place_state_reviews",
        columns=[
            "passage_id",
            "sentence_number",
            "prompt_version",
            "model",
            "has_place_state_claim",
            "summary",
            "input_tokens",
            "output_tokens",
            "run_id",
            "created_at",
        ],
        values_for_row=lambda row: [
            sql_string(row["passage_id"]),
            sql_integer(row["sentence_number"]),
            sql_string(run["prompt_version"]),
            sql_string(run["model"]),
            sql_bool(row["has_place_state_claim"]),
            sql_string(row["summary"]),
            sql_integer(row["input_tokens"]),
            sql_integer(row["output_tokens"]),
            sql_string(run["run_id"]),
            sql_string(run["completed_at"]),
        ],
        conflict="""ON CONFLICT (passage_id, sentence_number, prompt_version) DO UPDATE
SET model = EXCLUDED.model,
    has_place_state_claim = EXCLUDED.has_place_state_claim,
    summary = EXCLUDED.summary,
    input_tokens = EXCLUDED.input_tokens,
    output_tokens = EXCLUDED.output_tokens,
    run_id = EXCLUDED.run_id,
    created_at = EXCLUDED.created_at;
""",
    )
    if place_state_reviews:
        review_values = ",\n    ".join(
            "("
            + ", ".join([sql_string(row["passage_id"]), sql_integer(row["sentence_number"])])
            + ")"
            for row in place_state_reviews
        )
        sql += f"""
WITH review_rows(passage_id, sentence_number) AS (
    VALUES
    {review_values}
)
DELETE FROM place_state_mentions m
USING review_rows
WHERE m.passage_id = review_rows.passage_id
  AND m.sentence_number = review_rows.sentence_number
  AND m.prompt_version = {sql_string(run["prompt_version"])};
"""
    append_insert(
        payload.get("place_state_mentions") or [],
        table="place_state_mentions",
        columns=[
            "passage_id",
            "sentence_number",
            "prompt_version",
            "model",
            "claim_index",
            "exact_place_text",
            "canonical_place_name",
            "place_status",
            "temporal_scope",
            "evidence_quote",
            "confidence",
            "rationale",
            "target_label",
            "input_tokens",
            "output_tokens",
            "run_id",
            "created_at",
        ],
        values_for_row=lambda row: [
            sql_string(row["passage_id"]),
            sql_integer(row["sentence_number"]),
            sql_string(run["prompt_version"]),
            sql_string(run["model"]),
            sql_integer(row["claim_index"]),
            sql_string(row["exact_place_text"]),
            sql_string(row["canonical_place_name"]),
            sql_string(row["place_status"]),
            sql_string(row["temporal_scope"]),
            sql_string(row["evidence_quote"]),
            sql_string(row["confidence"]),
            sql_string(row["rationale"]),
            sql_string(row["target_label"]),
            sql_integer(row["input_tokens"]),
            sql_integer(row["output_tokens"]),
            sql_string(run["run_id"]),
            sql_string(run["completed_at"]),
        ],
        conflict="""ON CONFLICT (passage_id, sentence_number, prompt_version, claim_index) DO UPDATE
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
    created_at = EXCLUDED.created_at;
""",
    )
    legacy_tags = payload.get("legacy_tags") or []
    if legacy_tags:
        legacy_values = ",\n    ".join(
            "("
            + ", ".join(
                [
                    sql_string(row["passage_id"]),
                    sql_integer(row["sentence_number"]),
                    sql_bool(row["references_mythic_era"]),
                    sql_bool(row["expresses_scepticism"]),
                ]
            )
            + ")"
            for row in legacy_tags
        )
        sql += f"""
WITH legacy_rows(
    passage_id, sentence_number, references_mythic_era, expresses_scepticism
) AS (
    VALUES
    {legacy_values}
)
UPDATE greek_sentences s
SET references_mythic_era = legacy_rows.references_mythic_era,
    expresses_scepticism = legacy_rows.expresses_scepticism
FROM legacy_rows
WHERE s.passage_id = legacy_rows.passage_id
  AND s.sentence_number = legacy_rows.sentence_number;
"""
    sql += f"""
UPDATE sentence_tagging_runs
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
WHERE sentence_tagging_runs.run_id = {sql_string(run["run_id"])};
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
        discourse_tags = []
        place_state_reviews = []
        place_state_mentions = []
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
                elif output_mode == "discourse":
                    discourse_mode = args.get("discourse_mode")
                    if discourse_mode not in set(DISCOURSE_MODES):
                        raise ValueError(f"Invalid discourse mode: {discourse_mode}")
                    confidence = args.get("confidence")
                    if confidence not in {"high", "medium", "low"}:
                        confidence = "low"
                    discourse_tags.append(
                        {
                            "passage_id": source["passage_id"],
                            "sentence_number": source["sentence_number"],
                            "discourse_mode": discourse_mode,
                            "confidence": confidence,
                            "rationale": args.get("rationale") or "",
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        }
                    )
                elif output_mode == "place-state":
                    claims = args.get("claims") or []
                    if not isinstance(claims, list):
                        raise ValueError("place-state claims must be a list")
                    has_place_state_claim = bool(args.get("has_place_state_claim"))
                    if has_place_state_claim and not claims:
                        raise ValueError("has_place_state_claim is true but claims is empty")
                    if claims and not has_place_state_claim:
                        raise ValueError("claims are present but has_place_state_claim is false")
                    place_state_reviews.append(
                        {
                            "passage_id": source["passage_id"],
                            "sentence_number": source["sentence_number"],
                            "has_place_state_claim": has_place_state_claim,
                            "summary": args.get("summary") or "",
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        }
                    )
                    for claim_index, claim in enumerate(claims, start=1):
                        place_status = claim.get("place_status")
                        if place_status not in set(PLACE_STATE_STATUSES):
                            raise ValueError(f"Invalid place status: {place_status}")
                        temporal_scope = claim.get("temporal_scope")
                        if temporal_scope not in set(PLACE_STATE_TEMPORAL_SCOPES):
                            raise ValueError(f"Invalid temporal scope: {temporal_scope}")
                        confidence = claim.get("confidence")
                        if confidence not in {"high", "medium", "low"}:
                            confidence = "low"
                        place_state_mentions.append(
                            {
                                "passage_id": source["passage_id"],
                                "sentence_number": source["sentence_number"],
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
        processed_count = (
            len(greta_tags)
            + len(greta_both_tags)
            + len(discourse_tags)
            + len(place_state_reviews)
            + len(legacy_tags)
        )
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
            "discourse_tags": discourse_tags,
            "place_state_reviews": place_state_reviews,
            "place_state_mentions": place_state_mentions,
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
