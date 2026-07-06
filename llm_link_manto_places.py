#!/usr/bin/env python
"""Ask an LLM to link labelled Pausanias place names to MANTO entities.

Deterministic linking (link_manto_places.py) misses names that differ beyond
transliteration or that name a sub-place ("acropolis of Gythium"). This script
finds place names that carry survival labels but link to nothing, shortlists
plausible MANTO candidates by name similarity, and asks the model to pick one
or decline. Decisions land in curated_place_links with source='llm' so
link_manto_places.py injects them on its next run and reviewers can audit or
reject them later.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
from datetime import datetime, timezone

from openai import OpenAI

from link_manto_places import (
    latest_release_id,
    name_variants,
    transliteration_keys,
)
from pausanias_db import add_database_argument, connect, initialize_schema


DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_CANDIDATE_LIMIT = 10

LINK_TOOL = {
    "type": "function",
    "function": {
        "name": "record_link",
        "description": "Record whether the Pausanias place name matches a MANTO entity.",
        "parameters": {
            "type": "object",
            "properties": {
                "manto_id": {
                    "type": "string",
                    "description": (
                        "The MANTO id of the matching entity, or an empty string "
                        "when none of the candidates is the same place."
                    ),
                },
                "confident": {
                    "type": "boolean",
                    "description": "Whether the identification is clearly correct.",
                },
                "rationale": {
                    "type": "string",
                    "description": "One sentence explaining the decision.",
                },
            },
            "required": ["manto_id", "confident", "rationale"],
        },
    },
}

SYSTEM_PROMPT = """You link place names from Pausanias' Description of Greece to entries in the MANTO Greek-myth database. You are given one Pausanias place name (as extracted from an English translation) and a shortlist of MANTO place entities with their regions.

Rules:
- Choose a candidate only if it denotes the same place. Spelling differences from Latin vs Greek transliteration (Amyclae/Amyklai, c/k, -ae/-ai, -us/-os) are the same place.
- Qualifiers like "ancient X", "X city", or "the rest of X" still denote X.
- For a named part of a settlement ("acropolis of Gythium", "harbor of X"), link to the settlement only if MANTO has no closer entity, and set confident=false.
- Monuments, buildings, statues, altars, and non-Greek regions with no matching candidate get an empty manto_id.
- When two candidates share a name, prefer the one whose region matches what Pausanias is describing; if you cannot tell, set confident=false."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_database_argument(parser)
    parser.add_argument("--release-record-id", type=int, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--openai-api-key-file", default="~/.openai.key")
    parser.add_argument("--candidate-limit", type=int, default=DEFAULT_CANDIDATE_LIMIT)
    parser.add_argument(
        "--stop",
        type=int,
        default=None,
        help="Process at most this many unlinked names (for cheap partial runs).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the unlinked names and their candidates without calling the API.",
    )
    return parser.parse_args()


def load_openai_api_key(key_file: str) -> str:
    with open(os.path.expanduser(key_file), "r", encoding="utf-8") as handle:
        return handle.read().strip()


def matching_keys(value: str | None) -> set[str]:
    variants = name_variants(
        value,
        include_parenthetical_content=True,
        include_location_container=True,
        include_generic_head=True,
    )
    return variants | transliteration_keys(variants)


def load_labelled_place_names(conn) -> list[str]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT canonical_place_name FROM passage_place_state_mentions
            WHERE target_label IN ('survives', 'does_not_survive')
            UNION
            SELECT canonical_place_name FROM place_state_mentions
            WHERE target_label IN ('survives', 'does_not_survive')
            ORDER BY canonical_place_name
            """
        )
        return [row[0] for row in cursor.fetchall()]


def load_linked_name_keys(conn, release_id: int) -> set[str]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT reference_form, english_transcription, manto_label
            FROM manto_place_links
            WHERE release_record_id = %s
              AND confidence <> 'rejected'
            """,
            (release_id,),
        )
        rows = cursor.fetchall()
    keys: set[str] = set()
    for row in rows:
        for value in row:
            keys.update(matching_keys(value))
    return keys


def load_decided_names(conn) -> set[str]:
    with conn.cursor() as cursor:
        cursor.execute("SELECT place_name FROM curated_place_links")
        return {row[0] for row in cursor.fetchall()}


def load_manto_place_candidates(conn, release_id: int) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT object_id, name, somewhere_in_or_near_label
            FROM manto_entity_details
            WHERE release_record_id = %s
              AND substring(name from 1 for 1) = '🌍'
            """,
            (release_id,),
        )
        rows = cursor.fetchall()
    entities = []
    for object_id, label, parent_label in rows:
        variants = name_variants(
            label,
            include_location_container=False,
            include_generic_head=False,
        )
        entities.append(
            {
                "manto_id": str(object_id),
                "label": label or "",
                "parent_label": parent_label or "",
                "keys": variants | transliteration_keys(variants),
            }
        )
    return entities


def shortlist_candidates(
    place_name: str,
    entities: list[dict],
    *,
    limit: int,
) -> list[dict]:
    place_keys = matching_keys(place_name)
    if not place_keys:
        return []
    scored = []
    for entity in entities:
        if not entity["keys"]:
            continue
        best = max(
            difflib.SequenceMatcher(None, place_key, entity_key).ratio()
            for place_key in place_keys
            for entity_key in entity["keys"]
        )
        contains = any(
            place_key in entity_key or entity_key in place_key
            for place_key in place_keys
            for entity_key in entity["keys"]
            if len(place_key) >= 4 and len(entity_key) >= 4
        )
        score = best + (0.15 if contains else 0.0)
        if score >= 0.6:
            scored.append((score, entity))
    scored.sort(key=lambda item: (-item[0], item[1]["manto_id"]))
    return [entity for _, entity in scored[:limit]]


def ask_model(client: OpenAI, model: str, place_name: str, candidates: list[dict]) -> dict:
    candidate_lines = "\n".join(
        f"- manto_id {entity['manto_id']}: {entity['label']}"
        + (f" (in or near {entity['parent_label']})" if entity["parent_label"] else "")
        for entity in candidates
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Pausanias place name: {place_name}\n\n"
                    f"MANTO candidates:\n{candidate_lines}\n\n"
                    "Record your decision with the record_link function."
                ),
            },
        ],
        tools=[LINK_TOOL],
        tool_choice={"type": "function", "function": {"name": "record_link"}},
    )
    call = response.choices[0].message.tool_calls[0]
    decision = json.loads(call.function.arguments)
    usage = response.usage
    return {
        "manto_id": str(decision.get("manto_id") or "").strip(),
        "confident": bool(decision.get("confident")),
        "rationale": str(decision.get("rationale") or "").strip(),
        "input_tokens": int(usage.prompt_tokens if usage else 0),
        "output_tokens": int(usage.completion_tokens if usage else 0),
    }


def save_decision(
    conn,
    *,
    place_name: str,
    manto_id: str,
    manto_label: str,
    model: str,
    rationale: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    timestamp = now_iso()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO curated_place_links (
                place_name, manto_id, manto_label, source, model, rationale,
                input_tokens, output_tokens, reviewed, rejected,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, 'llm', %s, %s, %s, %s, FALSE, %s, %s, %s)
            ON CONFLICT (place_name, manto_id) DO UPDATE
            SET manto_label = EXCLUDED.manto_label,
                model = EXCLUDED.model,
                rationale = EXCLUDED.rationale,
                input_tokens = EXCLUDED.input_tokens,
                output_tokens = EXCLUDED.output_tokens,
                updated_at = EXCLUDED.updated_at
            """,
            (
                place_name,
                manto_id,
                manto_label,
                model,
                rationale,
                input_tokens,
                output_tokens,
                not manto_id,
                timestamp,
                timestamp,
            ),
        )
    conn.commit()


def main() -> None:
    args = parse_arguments()
    with connect(args.database_url) as conn:
        initialize_schema(conn)
        release_id = args.release_record_id or latest_release_id(conn)
        labelled = load_labelled_place_names(conn)
        linked_keys = load_linked_name_keys(conn, release_id)
        decided = load_decided_names(conn)
        entities = load_manto_place_candidates(conn, release_id)
        entity_labels = {entity["manto_id"]: entity["label"] for entity in entities}

        unlinked = [
            name
            for name in labelled
            if name not in decided and not (matching_keys(name) & linked_keys)
        ]
        if args.stop is not None:
            unlinked = unlinked[: args.stop]
        print(
            f"{len(labelled)} labelled names; {len(unlinked)} unlinked and undecided.",
            flush=True,
        )

        if args.dry_run:
            for name in unlinked:
                candidates = shortlist_candidates(
                    name, entities, limit=args.candidate_limit
                )
                labels = "; ".join(entity["label"] for entity in candidates) or "(none)"
                print(f"{name} -> {labels}")
            return

        client = OpenAI(api_key=load_openai_api_key(args.openai_api_key_file))
        linked_count = 0
        no_match_count = 0
        total_input = 0
        total_output = 0
        for name in unlinked:
            candidates = shortlist_candidates(name, entities, limit=args.candidate_limit)
            if not candidates:
                save_decision(
                    conn,
                    place_name=name,
                    manto_id="",
                    manto_label="",
                    model=args.model,
                    rationale="No MANTO candidate passed the name-similarity shortlist.",
                    input_tokens=0,
                    output_tokens=0,
                )
                no_match_count += 1
                continue
            decision = ask_model(client, args.model, name, candidates)
            manto_id = decision["manto_id"]
            if manto_id and manto_id not in entity_labels:
                print(f"Model invented manto_id {manto_id!r} for {name!r}; recording no match.")
                manto_id = ""
            rationale = decision["rationale"]
            if manto_id and not decision["confident"]:
                rationale = f"(low confidence) {rationale}"
            save_decision(
                conn,
                place_name=name,
                manto_id=manto_id,
                manto_label=entity_labels.get(manto_id, ""),
                model=args.model,
                rationale=rationale,
                input_tokens=decision["input_tokens"],
                output_tokens=decision["output_tokens"],
            )
            total_input += decision["input_tokens"]
            total_output += decision["output_tokens"]
            if manto_id:
                linked_count += 1
                print(f"{name} -> {entity_labels[manto_id]} ({manto_id})")
            else:
                no_match_count += 1
                print(f"{name} -> no match")
    print(
        f"Recorded {linked_count} LLM links and {no_match_count} no-match decisions "
        f"({total_input:,} input / {total_output:,} output tokens). "
        "Run link_manto_places.py to inject them into manto_place_links."
    )


if __name__ == "__main__":
    main()
