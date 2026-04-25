#!/usr/bin/env python
"""Check and optionally correct proper-noun spelling drift in translations."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from pausanias_db import add_database_argument, connect


DEFAULT_POLICY_SEEDS = [
    {
        "reference_form": "Πειραιεύς",
        "entity_type": "place",
        "preferred_english": "Piraeus",
        "deprecated_variants": ["Peiraeus"],
        "allowed_variants": [],
        "notes": "Conventional English spelling; live proper_nouns and Wikidata use Piraeus.",
    },
]


CANONICAL_POLICY_OVERRIDES = {
    (
        "Ἀφροδίτη Οὐρανία",
        "deity",
    ): (
        "Aphrodite Urania",
        "Keep the compound epithet consistent with standalone Urania.",
    ),
    (
        "Ἀχαϊκοί",
        "person",
    ): (
        "Achaeans",
        "Keep the ethnonym consistent with the dominant Achaeans policy.",
    ),
    (
        "Μαίναλον",
        "place",
    ): (
        "Maenalus",
        "Keep the place and eponymous founder under the same English form.",
    ),
    (
        "Μαίναλος",
        "person",
    ): (
        "Maenalus",
        "Keep the place and eponymous founder under the same English form.",
    ),
    (
        "Κάναχος",
        "person",
    ): (
        "Canachus",
        "Keep the artist's name consistent with Canachus of Sicyon.",
    ),
    (
        "Παιωνία",
        "other",
    ): (
        "Paeonia",
        "Keep the epithet consistent with Athena Paeonia.",
    ),
}


@dataclass(frozen=True)
class Policy:
    reference_form: str
    entity_type: str
    wikidata_qid: str | None
    preferred_english: str
    allowed_variants: tuple[str, ...]
    deprecated_variants: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    passage_id: str
    source_table: str
    source_column: str
    source_key: str
    reference_form: str
    entity_type: str
    wikidata_qid: str | None
    preferred_english: str
    observed_variant: str
    finding_type: str
    snippet: str
    replacement_applied: bool = False
    resolved_after_scan: bool = False


@dataclass(frozen=True)
class TextRow:
    passage_id: str
    source_table: str
    source_column: str
    source_key: str
    text: str
    update_key: tuple[object, ...]


@dataclass(frozen=True)
class PolicyImportDecision:
    reference_form: str
    entity_type: str
    wikidata_qid: str | None
    preferred_english: str
    deprecated_variants: tuple[str, ...]
    source_preferred_english: str
    selection_reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find proper-noun spelling variants in completed Pausanias translations."
    )
    add_database_argument(parser)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Update translation text fields by replacing deprecated variants with preferred spellings.",
    )
    parser.add_argument(
        "--no-seed-defaults",
        action="store_true",
        help="Do not insert the built-in starter policies before scanning.",
    )
    parser.add_argument(
        "--passage",
        action="append",
        default=[],
        help="Restrict the scan to a passage ID. May be repeated.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of finding rows reported.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print findings as JSON instead of a text report.",
    )
    parser.add_argument(
        "--import-review-tsv",
        type=Path,
        default=None,
        help=(
            "Import active spelling policies from a review TSV. The importer chooses "
            "the spelling with the most completed-prose hits as canonical."
        ),
    )
    parser.add_argument(
        "--include-lowercase-policy-candidates",
        action="store_true",
        help="Import review candidates whose spellings are lowercase. Skipped by default.",
    )
    parser.add_argument(
        "--sync-registry",
        action="store_true",
        help=(
            "Update registry/derived name columns in proper_nouns, wikidata_links, "
            "and noun_centrality to each active policy's preferred spelling."
        ),
    )
    parser.add_argument(
        "--sync-derived-name-spellings",
        action="store_true",
        help=(
            "Apply unambiguous deprecated-token replacements globally in prose and "
            "name registries. This catches compound names such as epithets while "
            "skipping variants that are canonical for another active policy."
        ),
    )
    return parser.parse_args()


def ensure_tables(conn) -> None:
    """Create the policy and finding tables used by this checker."""
    schema = Path(__file__).resolve().parent / "database" / "schema.sql"
    conn.execute(schema.read_text(encoding="utf-8"))
    conn.execute(
        """
        ALTER TABLE proper_noun_spelling_findings
        ADD COLUMN IF NOT EXISTS source_table TEXT NOT NULL DEFAULT 'translations'
        """
    )
    conn.execute(
        """
        ALTER TABLE proper_noun_spelling_findings
        ADD COLUMN IF NOT EXISTS source_column TEXT NOT NULL DEFAULT 'english_translation'
        """
    )
    conn.execute(
        """
        ALTER TABLE proper_noun_spelling_findings
        ADD COLUMN IF NOT EXISTS source_key TEXT NOT NULL DEFAULT ''
        """
    )
    conn.commit()


def seed_default_policies(conn) -> None:
    """Insert conservative starter policies when the entity exists in the noun table."""
    timestamp = datetime.now().isoformat()
    with conn.cursor() as cursor:
        for seed in DEFAULT_POLICY_SEEDS:
            cursor.execute(
                """
                SELECT w.wikidata_qid
                FROM proper_nouns pn
                LEFT JOIN wikidata_links w
                  ON pn.reference_form = w.reference_form
                 AND pn.entity_type = w.entity_type
                WHERE pn.reference_form = %s
                  AND pn.entity_type = %s
                LIMIT 1
                """,
                (seed["reference_form"], seed["entity_type"]),
            )
            row = cursor.fetchone()
            if row is None:
                continue

            cursor.execute(
                """
                INSERT INTO proper_noun_spelling_policies (
                    reference_form,
                    entity_type,
                    wikidata_qid,
                    preferred_english,
                    allowed_variants,
                    deprecated_variants,
                    status,
                    notes,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, %s)
                ON CONFLICT (reference_form, entity_type) DO UPDATE SET
                    wikidata_qid = COALESCE(proper_noun_spelling_policies.wikidata_qid, EXCLUDED.wikidata_qid),
                    preferred_english = EXCLUDED.preferred_english,
                    allowed_variants = EXCLUDED.allowed_variants,
                    deprecated_variants = EXCLUDED.deprecated_variants,
                    status = 'active',
                    notes = COALESCE(proper_noun_spelling_policies.notes, EXCLUDED.notes),
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    seed["reference_form"],
                    seed["entity_type"],
                    row[0],
                    seed["preferred_english"],
                    seed["allowed_variants"],
                    seed["deprecated_variants"],
                    seed["notes"],
                    timestamp,
                ),
            )
    conn.commit()


def parse_variant_counts(variants: str) -> dict[str, int]:
    """Parse a review TSV variant cell like 'Foo (2); Bar (3)'."""
    counts: dict[str, int] = {}
    if not variants:
        return counts

    for chunk in variants.split("; "):
        match = re.fullmatch(r"(.+) \((\d+)\)", chunk)
        if match is None:
            raise ValueError(f"Cannot parse variant count: {chunk!r}")
        counts[match.group(1)] = int(match.group(2))
    return counts


def import_decisions_from_review_tsv(
    review_tsv: Path,
    include_lowercase_candidates: bool = False,
) -> list[PolicyImportDecision]:
    """Turn a spelling review TSV into canonical policy decisions."""
    decisions: list[PolicyImportDecision] = []
    with review_tsv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            source_preferred = row["preferred"]
            counts = {source_preferred: int(row["preferred_hits"] or 0)}
            counts.update(parse_variant_counts(row["variants"]))

            if (
                not include_lowercase_candidates
                and not any(term[:1].isupper() for term in counts)
            ):
                continue

            override = CANONICAL_POLICY_OVERRIDES.get(
                (row["reference_form"], row["entity_type"])
            )
            if override:
                preferred_english, override_reason = override
                if preferred_english not in counts:
                    counts[preferred_english] = 0
            else:
                # Ties keep the existing registry spelling, which is the least surprising
                # choice when the completed prose is evenly divided.
                preferred_english = max(
                    counts,
                    key=lambda term: (counts[term], term == source_preferred),
                )
                override_reason = ""
            deprecated_variants = tuple(
                term for term, _ in sorted(counts.items()) if term != preferred_english
            )
            if not deprecated_variants:
                continue

            reason_bits = [
                f"{preferred_english} has {counts[preferred_english]} completed-prose hit(s)"
            ]
            if preferred_english != source_preferred:
                reason_bits.append(f"registry had {source_preferred}")
            if override_reason:
                reason_bits.append(f"override: {override_reason}")

            decisions.append(
                PolicyImportDecision(
                    reference_form=row["reference_form"],
                    entity_type=row["entity_type"],
                    wikidata_qid=row["qid"] or None,
                    preferred_english=preferred_english,
                    deprecated_variants=deprecated_variants,
                    source_preferred_english=source_preferred,
                    selection_reason="; ".join(reason_bits),
                )
            )
    return decisions


def import_policy_decisions(conn, decisions: list[PolicyImportDecision]) -> int:
    """Upsert imported canonical spelling decisions into the policy table."""
    if not decisions:
        return 0

    timestamp = datetime.now().isoformat()
    with conn.cursor() as cursor:
        for decision in decisions:
            cursor.execute(
                """
                SELECT wikidata_qid
                FROM wikidata_links
                WHERE reference_form = %s
                  AND entity_type = %s
                """,
                (decision.reference_form, decision.entity_type),
            )
            row = cursor.fetchone()
            wikidata_qid = decision.wikidata_qid or (row[0] if row else None)
            notes = (
                "Imported from proper-noun spelling review; "
                f"{decision.selection_reason}."
            )
            cursor.execute(
                """
                INSERT INTO proper_noun_spelling_policies (
                    reference_form,
                    entity_type,
                    wikidata_qid,
                    preferred_english,
                    allowed_variants,
                    deprecated_variants,
                    status,
                    notes,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, '{}'::TEXT[], %s, 'active', %s, %s)
                ON CONFLICT (reference_form, entity_type) DO UPDATE SET
                    wikidata_qid = COALESCE(EXCLUDED.wikidata_qid, proper_noun_spelling_policies.wikidata_qid),
                    preferred_english = EXCLUDED.preferred_english,
                    allowed_variants = EXCLUDED.allowed_variants,
                    deprecated_variants = EXCLUDED.deprecated_variants,
                    status = 'active',
                    notes = EXCLUDED.notes,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    decision.reference_form,
                    decision.entity_type,
                    wikidata_qid,
                    decision.preferred_english,
                    list(decision.deprecated_variants),
                    notes,
                    timestamp,
                ),
            )
    conn.commit()
    return len(decisions)


def load_policies(conn) -> list[Policy]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT reference_form,
                   entity_type,
                   wikidata_qid,
                   preferred_english,
                   allowed_variants,
                   deprecated_variants
            FROM proper_noun_spelling_policies
            WHERE status = 'active'
            ORDER BY reference_form, entity_type
            """
        )
        rows = cursor.fetchall()
    return [
        Policy(
            reference_form=row[0],
            entity_type=row[1],
            wikidata_qid=row[2],
            preferred_english=row[3],
            allowed_variants=tuple(row[4] or ()),
            deprecated_variants=tuple(row[5] or ()),
        )
        for row in rows
    ]


def token_pattern(term: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])")


def snippet_for(text: str, start: int, end: int, width: int = 80) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    snippet = text[left:right].replace("\n", " ")
    if left:
        snippet = "..." + snippet
    if right < len(text):
        snippet += "..."
    return snippet


def find_deprecated_variants(
    row: TextRow,
    policy: Policy,
) -> list[Finding]:
    findings: list[Finding] = []
    for variant in policy.deprecated_variants:
        for match in token_pattern(variant).finditer(row.text):
            findings.append(
                Finding(
                    passage_id=row.passage_id,
                    source_table=row.source_table,
                    source_column=row.source_column,
                    source_key=row.source_key,
                    reference_form=policy.reference_form,
                    entity_type=policy.entity_type,
                    wikidata_qid=policy.wikidata_qid,
                    preferred_english=policy.preferred_english,
                    observed_variant=match.group(0),
                    finding_type="deprecated_variant",
                    snippet=snippet_for(row.text, match.start(), match.end()),
                )
            )
    return findings


def replace_deprecated_variants(text: str, policy: Policy) -> tuple[str, int]:
    replacements = 0
    updated = text
    for variant in policy.deprecated_variants:
        updated, count = token_pattern(variant).subn(policy.preferred_english, updated)
        replacements += count
    return updated, replacements


def build_unambiguous_replacements(policies: list[Policy]) -> dict[str, str]:
    """Return deprecated variants that have one target and are never canonical."""
    preferred_terms = {policy.preferred_english for policy in policies}
    targets: dict[str, set[str]] = {}
    for policy in policies:
        for variant in policy.deprecated_variants:
            targets.setdefault(variant, set()).add(policy.preferred_english)

    replacements: dict[str, str] = {}
    for variant, preferred in targets.items():
        if len(preferred) != 1:
            continue
        if variant in preferred_terms:
            continue
        if any(token_pattern(variant).search(term) for term in preferred_terms):
            continue
        if not variant[:1].isupper():
            continue
        target = next(iter(preferred))
        if target != variant:
            replacements[variant] = target
    return replacements


def compile_replacement_pattern(replacements: dict[str, str]) -> re.Pattern[str] | None:
    if not replacements:
        return None

    alternatives = "|".join(
        re.escape(variant)
        for variant in sorted(replacements, key=len, reverse=True)
    )
    return re.compile(rf"(?<![A-Za-z])(?:{alternatives})(?![A-Za-z])")


def replace_unambiguous_variants(
    text: str,
    replacements: dict[str, str],
    pattern: re.Pattern[str] | None = None,
) -> tuple[str, int]:
    """Replace globally safe deprecated variants in a text field."""
    if not replacements:
        return text, 0

    compiled = pattern or compile_replacement_pattern(replacements)
    if compiled is None:
        return text, 0

    replacement_count = 0

    def replace_match(match: re.Match[str]) -> str:
        nonlocal replacement_count
        replacement_count += 1
        return replacements[match.group(0)]

    updated = compiled.sub(replace_match, text)
    return updated, replacement_count


def get_text_rows(
    conn,
    policy: Policy,
    passage_ids: Iterable[str] | None = None,
) -> list[TextRow]:
    passage_ids = list(passage_ids or [])
    rows: list[TextRow] = []
    with conn.cursor() as cursor:
        params: list[object] = [policy.reference_form, policy.entity_type]
        passage_filter = ""
        if passage_ids:
            passage_filter = "AND t.passage_id = ANY(%s)"
            params.append(passage_ids)

        cursor.execute(
            f"""
            SELECT DISTINCT t.passage_id, t.english_translation
            FROM proper_nouns pn
            JOIN translations t ON t.passage_id = pn.passage_id
            WHERE pn.reference_form = %s
              AND pn.entity_type = %s
              {passage_filter}
            ORDER BY t.passage_id
            """,
            params,
        )
        for passage_id, text in cursor.fetchall():
            rows.append(
                TextRow(
                    passage_id=passage_id,
                    source_table="translations",
                    source_column="english_translation",
                    source_key=passage_id,
                    text=text,
                    update_key=(passage_id,),
                )
            )

        params = [policy.reference_form, policy.entity_type]
        sentence_filter = ""
        if passage_ids:
            sentence_filter = "AND s.passage_id = ANY(%s)"
            params.append(passage_ids)

        cursor.execute(
            f"""
            SELECT s.passage_id, s.sentence_number, s.english_sentence
            FROM proper_nouns pn
            JOIN greek_sentences s ON s.passage_id = pn.passage_id
            WHERE pn.reference_form = %s
              AND pn.entity_type = %s
              {sentence_filter}
            GROUP BY s.passage_id, s.sentence_number, s.english_sentence
            ORDER BY s.passage_id, s.sentence_number
            """,
            params,
        )
        for passage_id, sentence_number, text in cursor.fetchall():
            rows.append(
                TextRow(
                    passage_id=passage_id,
                    source_table="greek_sentences",
                    source_column="english_sentence",
                    source_key=f"{passage_id}:{sentence_number}",
                    text=text,
                    update_key=(passage_id, sentence_number),
                )
            )

        params = [policy.reference_form, policy.entity_type]
        summary_filter = ""
        if passage_ids:
            summary_filter = "AND ps.passage_id = ANY(%s)"
            params.append(passage_ids)

        cursor.execute(
            f"""
            SELECT ps.passage_id, ps.summary
            FROM proper_nouns pn
            JOIN passage_summaries ps ON ps.passage_id = pn.passage_id
            WHERE pn.reference_form = %s
              AND pn.entity_type = %s
              {summary_filter}
            GROUP BY ps.passage_id, ps.summary
            ORDER BY ps.passage_id
            """,
            params,
        )
        for passage_id, text in cursor.fetchall():
            rows.append(
                TextRow(
                    passage_id=passage_id,
                    source_table="passage_summaries",
                    source_column="summary",
                    source_key=passage_id,
                    text=text,
                    update_key=(passage_id,),
                )
            )

    return rows


def scan_policy(conn, policy: Policy, passage_ids: Iterable[str] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    for row in get_text_rows(conn, policy, passage_ids):
        findings.extend(find_deprecated_variants(row, policy))
    return findings


def apply_policy(conn, policy: Policy, passage_ids: Iterable[str] | None = None) -> int:
    updates = 0
    with conn.cursor() as cursor:
        for row in get_text_rows(conn, policy, passage_ids):
            updated, replacements = replace_deprecated_variants(row.text, policy)
            if replacements == 0:
                continue

            if row.source_table == "translations":
                cursor.execute(
                    """
                    UPDATE translations
                    SET english_translation = %s
                    WHERE passage_id = %s
                    """,
                    (updated, *row.update_key),
                )
            elif row.source_table == "greek_sentences":
                cursor.execute(
                    """
                    UPDATE greek_sentences
                    SET english_sentence = %s
                    WHERE passage_id = %s
                      AND sentence_number = %s
                    """,
                    (updated, *row.update_key),
                )
            elif row.source_table == "passage_summaries":
                cursor.execute(
                    """
                    UPDATE passage_summaries
                    SET summary = %s
                    WHERE passage_id = %s
                    """,
                    (updated, *row.update_key),
                )
            else:
                raise ValueError(f"Unsupported source table: {row.source_table}")
            updates += 1
    conn.commit()
    return updates


def sync_registry_spellings(conn, policies: list[Policy]) -> dict[str, int]:
    """Sync canonical English names in registry and derived name tables."""
    counts = {
        "proper_nouns": 0,
        "wikidata_links": 0,
        "noun_centrality": 0,
    }
    with conn.cursor() as cursor:
        for policy in policies:
            cursor.execute(
                """
                UPDATE proper_nouns
                SET english_transcription = %s
                WHERE reference_form = %s
                  AND entity_type = %s
                  AND english_transcription <> %s
                """,
                (
                    policy.preferred_english,
                    policy.reference_form,
                    policy.entity_type,
                    policy.preferred_english,
                ),
            )
            counts["proper_nouns"] += cursor.rowcount

            cursor.execute(
                """
                UPDATE wikidata_links
                SET english_transcription = %s
                WHERE reference_form = %s
                  AND entity_type = %s
                  AND english_transcription <> %s
                """,
                (
                    policy.preferred_english,
                    policy.reference_form,
                    policy.entity_type,
                    policy.preferred_english,
                ),
            )
            counts["wikidata_links"] += cursor.rowcount

            cursor.execute(
                """
                UPDATE noun_centrality
                SET english_transcription = %s
                WHERE reference_form = %s
                  AND entity_type = %s
                  AND english_transcription <> %s
                """,
                (
                    policy.preferred_english,
                    policy.reference_form,
                    policy.entity_type,
                    policy.preferred_english,
                ),
            )
            counts["noun_centrality"] += cursor.rowcount
    conn.commit()
    return counts


def sync_derived_name_spellings(conn, policies: list[Policy]) -> dict[str, int]:
    """Apply safe base-name spelling decisions to compound names and prose."""
    replacements = build_unambiguous_replacements(policies)
    counts = {
        "translations": 0,
        "greek_sentences": 0,
        "passage_summaries": 0,
        "proper_nouns": 0,
        "wikidata_links": 0,
        "noun_centrality": 0,
    }
    if not replacements:
        return counts
    replacement_pattern = compile_replacement_pattern(replacements)

    with conn.cursor() as cursor:
        cursor.execute("SELECT passage_id, english_translation FROM translations")
        for passage_id, text in cursor.fetchall():
            updated, replacements_applied = replace_unambiguous_variants(
                text,
                replacements,
                replacement_pattern,
            )
            if replacements_applied:
                cursor.execute(
                    """
                    UPDATE translations
                    SET english_translation = %s
                    WHERE passage_id = %s
                    """,
                    (updated, passage_id),
                )
                counts["translations"] += 1

        cursor.execute(
            """
            SELECT passage_id, sentence_number, english_sentence
            FROM greek_sentences
            """
        )
        for passage_id, sentence_number, text in cursor.fetchall():
            updated, replacements_applied = replace_unambiguous_variants(
                text,
                replacements,
                replacement_pattern,
            )
            if replacements_applied:
                cursor.execute(
                    """
                    UPDATE greek_sentences
                    SET english_sentence = %s
                    WHERE passage_id = %s
                      AND sentence_number = %s
                    """,
                    (updated, passage_id, sentence_number),
                )
                counts["greek_sentences"] += 1

        cursor.execute("SELECT passage_id, summary FROM passage_summaries")
        for passage_id, text in cursor.fetchall():
            updated, replacements_applied = replace_unambiguous_variants(
                text,
                replacements,
                replacement_pattern,
            )
            if replacements_applied:
                cursor.execute(
                    """
                    UPDATE passage_summaries
                    SET summary = %s
                    WHERE passage_id = %s
                    """,
                    (updated, passage_id),
                )
                counts["passage_summaries"] += 1

        cursor.execute("SELECT id, english_transcription FROM proper_nouns")
        for row_id, text in cursor.fetchall():
            updated, replacements_applied = replace_unambiguous_variants(
                text,
                replacements,
                replacement_pattern,
            )
            if replacements_applied:
                cursor.execute(
                    """
                    UPDATE proper_nouns
                    SET english_transcription = %s
                    WHERE id = %s
                    """,
                    (updated, row_id),
                )
                counts["proper_nouns"] += 1

        cursor.execute("SELECT id, english_transcription FROM wikidata_links")
        for row_id, text in cursor.fetchall():
            updated, replacements_applied = replace_unambiguous_variants(
                text,
                replacements,
                replacement_pattern,
            )
            if replacements_applied:
                cursor.execute(
                    """
                    UPDATE wikidata_links
                    SET english_transcription = %s
                    WHERE id = %s
                    """,
                    (updated, row_id),
                )
                counts["wikidata_links"] += 1

        cursor.execute(
            """
            SELECT reference_form, entity_type, component_id, english_transcription
            FROM noun_centrality
            """
        )
        for reference_form, entity_type, component_id, text in cursor.fetchall():
            updated, replacements_applied = replace_unambiguous_variants(
                text,
                replacements,
                replacement_pattern,
            )
            if replacements_applied:
                cursor.execute(
                    """
                    UPDATE noun_centrality
                    SET english_transcription = %s
                    WHERE reference_form = %s
                      AND entity_type = %s
                      AND component_id = %s
                    """,
                    (updated, reference_form, entity_type, component_id),
                )
                counts["noun_centrality"] += 1
    conn.commit()
    return counts


def save_findings(conn, scan_id: str, scan_started_at: str, findings: list[Finding]) -> None:
    if not findings:
        return

    created_at = datetime.now().isoformat()
    with conn.cursor() as cursor:
        for finding in findings:
            cursor.execute(
                """
                INSERT INTO proper_noun_spelling_findings (
                    scan_id,
                    scan_started_at,
                    passage_id,
                    source_table,
                    source_column,
                    source_key,
                    reference_form,
                    entity_type,
                    wikidata_qid,
                    preferred_english,
                    observed_variant,
                    finding_type,
                    snippet,
                    replacement_applied,
                    resolved_after_scan,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    scan_id,
                    scan_started_at,
                    finding.passage_id,
                    finding.source_table,
                    finding.source_column,
                    finding.source_key,
                    finding.reference_form,
                    finding.entity_type,
                    finding.wikidata_qid,
                    finding.preferred_english,
                    finding.observed_variant,
                    finding.finding_type,
                    finding.snippet,
                    finding.replacement_applied,
                    finding.resolved_after_scan,
                    created_at,
                ),
            )
    conn.commit()


def mark_resolution(
    findings: list[Finding],
    remaining: list[Finding],
    replacement_applied: bool,
) -> list[Finding]:
    remaining_keys = {
        (
            finding.passage_id,
            finding.source_table,
            finding.source_column,
            finding.source_key,
            finding.reference_form,
            finding.entity_type,
            finding.observed_variant,
            finding.snippet,
        )
        for finding in remaining
    }

    resolved: list[Finding] = []
    for finding in findings:
        key = (
            finding.passage_id,
            finding.source_table,
            finding.source_column,
            finding.source_key,
            finding.reference_form,
            finding.entity_type,
            finding.observed_variant,
            finding.snippet,
        )
        resolved.append(
            Finding(
                passage_id=finding.passage_id,
                source_table=finding.source_table,
                source_column=finding.source_column,
                source_key=finding.source_key,
                reference_form=finding.reference_form,
                entity_type=finding.entity_type,
                wikidata_qid=finding.wikidata_qid,
                preferred_english=finding.preferred_english,
                observed_variant=finding.observed_variant,
                finding_type=finding.finding_type,
                snippet=finding.snippet,
                replacement_applied=replacement_applied,
                resolved_after_scan=key not in remaining_keys,
            )
        )
    return resolved


def print_text_report(
    findings: list[Finding],
    policies: list[Policy],
    applied_updates: int,
    imported_policies: int,
    registry_updates: dict[str, int],
    derived_name_updates: dict[str, int],
    limit: int | None,
) -> None:
    print(f"Policies scanned: {len(policies)}")
    if imported_policies:
        print(f"Policies imported: {imported_policies}")
    print(f"Findings: {len(findings)}")
    if applied_updates:
        print(f"Text rows updated: {applied_updates}")
    if registry_updates:
        print(
            "Registry rows updated: "
            + ", ".join(f"{table}={count}" for table, count in registry_updates.items())
        )
    if derived_name_updates:
        print(
            "Derived-name rows updated: "
            + ", ".join(f"{table}={count}" for table, count in derived_name_updates.items())
        )

    rows = findings[:limit] if limit is not None else findings
    for finding in rows:
        status = "applied" if finding.replacement_applied else "found"
        resolved = "resolved" if finding.resolved_after_scan else "unresolved"
        print(
            f"{finding.source_table}.{finding.source_column} {finding.source_key}: "
            f"{finding.observed_variant} -> "
            f"{finding.preferred_english} ({finding.reference_form}, "
            f"{finding.entity_type}; {status}, {resolved})"
        )
        print(f"  {finding.snippet}")

    if limit is not None and len(findings) > limit:
        print(f"... {len(findings) - limit} more finding(s) omitted by --limit.")


def findings_as_json(
    findings: list[Finding],
    policies: list[Policy],
    applied_updates: int,
    imported_policies: int,
    registry_updates: dict[str, int],
    derived_name_updates: dict[str, int],
    limit: int | None,
) -> str:
    rows = findings[:limit] if limit is not None else findings
    payload = {
        "policies_scanned": len(policies),
        "policies_imported": imported_policies,
        "findings": len(findings),
        "text_rows_updated": applied_updates,
        "registry_rows_updated": registry_updates,
        "derived_name_rows_updated": derived_name_updates,
        "rows": [finding.__dict__ for finding in rows],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main() -> int:
    args = parse_args()
    scan_id = str(uuid.uuid4())
    scan_started_at = datetime.now().isoformat()

    with connect(args.database_url) as conn:
        ensure_tables(conn)
        if not args.no_seed_defaults:
            seed_default_policies(conn)
        imported_policies = 0
        if args.import_review_tsv:
            decisions = import_decisions_from_review_tsv(
                args.import_review_tsv,
                include_lowercase_candidates=args.include_lowercase_policy_candidates,
            )
            imported_policies = import_policy_decisions(conn, decisions)

        policies = load_policies(conn)
        findings: list[Finding] = []
        for policy in policies:
            findings.extend(scan_policy(conn, policy, args.passage))

        applied_updates = 0
        if args.apply and findings:
            for policy in policies:
                applied_updates += apply_policy(conn, policy, args.passage)

            remaining: list[Finding] = []
            for policy in policies:
                remaining.extend(scan_policy(conn, policy, args.passage))
            findings = mark_resolution(findings, remaining, replacement_applied=True)

        registry_updates: dict[str, int] = {}
        if args.sync_registry:
            registry_updates = sync_registry_spellings(conn, policies)

        derived_name_updates: dict[str, int] = {}
        if args.sync_derived_name_spellings:
            derived_name_updates = sync_derived_name_spellings(conn, policies)

        save_findings(conn, scan_id, scan_started_at, findings)

    if args.json:
        print(
            findings_as_json(
                findings,
                policies,
                applied_updates,
                imported_policies,
                registry_updates,
                derived_name_updates,
                args.limit,
            )
        )
    else:
        print_text_report(
            findings,
            policies,
            applied_updates,
            imported_policies,
            registry_updates,
            derived_name_updates,
            args.limit,
        )

    return 1 if findings and not args.apply else 0


if __name__ == "__main__":
    sys.exit(main())
