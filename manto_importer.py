#!/usr/bin/env python
"""Import a public MANTO release ZIP into PostgreSQL.

The importer is intentionally conservative. It stores every public CSV/JSON row
as raw JSONB, then builds best-effort entity and edge tables from recognizable
identifier columns. Network features should use only `manto_edges` rows whose
`is_pre_pausanias` flag is true.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from psycopg.types.json import Jsonb

from manto_release import (
    DEFAULT_CACHE_DIR,
    MANTO_CONCEPT_RECORD_ID,
    download_release,
    fetch_latest_release,
    now_iso,
    release_zip_path,
)
from manto_release_check import upsert_release
from pausanias_db import add_database_argument, connect, initialize_schema


DEFAULT_PAUSANIAS_CUTOFF_YEAR = 180
MANTO_ID_RE = re.compile(
    r"(?:object|objects|classification|classifications|source|sources)[/_:-]?(\d+)",
    re.IGNORECASE,
)
PLEIADES_RE = re.compile(r"(?:pleiades\.stoa\.org/places/|pleiades[:=\s]+)(\d+)", re.I)
DATE_OR_SOURCE_RE = re.compile(
    r"\b(?:BCE|BC|CE|AD|Pausanias|Periegesis|start-attributes)\b",
    re.I,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_database_argument(parser)
    parser.add_argument("--concept-record-id", type=int, default=MANTO_CONCEPT_RECORD_ID)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--zip-path", type=Path, default=None)
    parser.add_argument("--download", action="store_true")
    parser.add_argument(
        "--append",
        action="store_true",
        help="Do not delete existing raw/entity/edge rows for this release before importing.",
    )
    parser.add_argument(
        "--stop-after-records",
        type=int,
        default=None,
        help="Import at most this many raw rows; useful for smoke tests.",
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument(
        "--pausanias-cutoff-year",
        type=int,
        default=DEFAULT_PAUSANIAS_CUTOFF_YEAR,
        help="Latest source year allowed in the strict pre-Pausanias graph.",
    )
    return parser.parse_args()


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    return " ".join(str(value).split())


def normalize_manto_id(value: Any) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    match = MANTO_ID_RE.search(text)
    if match:
        return match.group(1)
    if re.fullmatch(r"\d{1,10}", text):
        return text
    if text.startswith("http"):
        tail = re.split(r"[/#]", text.rstrip("/"))[-1]
        if re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", tail):
            return tail
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{2,80}", text):
        return text
    return None


def first_by_normalized_key(record: dict[str, Any], candidates: Iterable[str]) -> str:
    candidate_set = {normalize_key(candidate) for candidate in candidates}
    for key, value in record.items():
        if normalize_key(key) in candidate_set:
            text = normalize_text(value)
            if text:
                return text
    return ""


def first_key_containing(record: dict[str, Any], *needles: str) -> str:
    normalized_needles = [normalize_key(needle) for needle in needles]
    for key, value in record.items():
        normalized = normalize_key(key)
        if all(needle in normalized for needle in normalized_needles):
            text = normalize_text(value)
            if text:
                return text
    return ""


def record_kind_from_path(path: str) -> str:
    normalized = normalize_key(Path(path).stem)
    if "classification" in normalized:
        return "classification"
    if "object" in normalized:
        return "object"
    if "source" in normalized:
        return "source"
    return normalized[:80] or "unknown"


def record_identifier(record: dict[str, Any]) -> str:
    direct = first_by_normalized_key(
        record,
        [
            "id",
            "ID",
            "Object ID",
            "Object_ID",
            "Object Id",
            "Classification ID",
            "Classification_ID",
            "Nodegoat ID",
            "URI",
            "Persistent Identifier",
        ],
    )
    return normalize_manto_id(direct) or direct


def record_label(record: dict[str, Any]) -> str:
    return first_by_normalized_key(
        record,
        [
            "label",
            "name",
            "title",
            "object name",
            "object",
            "classification",
            "preferred label",
            "display title",
        ],
    )


def evidence_source_label(record: dict[str, Any]) -> str:
    exact = first_by_normalized_key(
        record,
        [
            "source",
            "sources",
            "citation",
            "reference",
            "bibliographic source",
            "ancient source",
            "work",
            "author",
        ],
    )
    if exact:
        return exact
    for needle in ("citation", "reference", "bibliographic", "ancientsource"):
        found = first_key_containing(record, needle)
        if found:
            return found
    # Avoid treating source object IDs as evidence source labels.
    for key, value in record.items():
        normalized = normalize_key(key)
        if "source" in normalized and "id" not in normalized:
            text = normalize_text(value)
            if text:
                return text
    return ""


def candidate_date_text(record: dict[str, Any], source_label: str) -> str:
    parts = [source_label]
    for key, value in record.items():
        normalized = normalize_key(key)
        text = normalize_text(value)
        if not text:
            continue
        if (
            any(token in normalized for token in ("date", "year", "century", "chronology"))
            or DATE_OR_SOURCE_RE.search(text)
        ):
            if text:
                parts.append(text)
    return " ".join(parts)


def extract_latest_year(text: str) -> int | None:
    """Extract a conservative latest year from loose date/source text."""
    if not text:
        return None
    years: list[int] = []
    for match in re.finditer(r"(\d{1,4})\s*(BCE|BC|CE|AD)\b", text, re.I):
        year = int(match.group(1))
        era = match.group(2).upper()
        years.append(-year if era in {"BCE", "BC"} else year)
    for match in re.finditer(
        r"(\d{1,2})(?:st|nd|rd|th)?\s*(?:c\.|century)\s*(BCE|BC|CE|AD)\b",
        text,
        re.I,
    ):
        century = int(match.group(1))
        era = match.group(2).upper()
        if era in {"BCE", "BC"}:
            years.append(-((century - 1) * 100 + 1))
        else:
            years.append(century * 100)
    if not years:
        return None
    return max(years)


def source_filter_status(
    source_label: str,
    latest_year: int | None,
    *,
    cutoff_year: int = DEFAULT_PAUSANIAS_CUTOFF_YEAR,
) -> tuple[bool, str | None]:
    text = source_label.lower()
    if "pausanias" in text or "periegesis" in text or "description of greece" in text:
        return False, "pausanias_source"
    if latest_year is None:
        return False, "unknown_source_date"
    if latest_year < cutoff_year:
        return True, None
    return False, "source_not_pre_pausanias"


def json_records(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item
            else:
                yield {"value": item}
    elif isinstance(value, dict):
        if value and all(isinstance(item, dict) for item in value.values()):
            for key, item in value.items():
                yield {"_json_key": key, **item}
        else:
            yield value


def iter_zip_records(zip_path: Path) -> Iterator[tuple[str, str, int, dict[str, Any]]]:
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            suffix = Path(info.filename).suffix.lower()
            if suffix not in {".csv", ".json"}:
                continue
            with archive.open(info) as raw_handle:
                if suffix == ".csv":
                    text_handle = io.TextIOWrapper(raw_handle, encoding="utf-8-sig", newline="")
                    for number, row in enumerate(csv.DictReader(text_handle), start=1):
                        yield info.filename, "csv", number, dict(row)
                else:
                    data = json.load(io.TextIOWrapper(raw_handle, encoding="utf-8-sig"))
                    for number, row in enumerate(json_records(data), start=1):
                        yield info.filename, "json", number, row


def id_value_by_key(record: dict[str, Any], accepted_keys: Iterable[str]) -> str | None:
    accepted = {normalize_key(key) for key in accepted_keys}
    for key, value in record.items():
        normalized = normalize_key(key)
        if normalized in accepted:
            manto_id = normalize_manto_id(value)
            if manto_id:
                return manto_id
    return None


def edge_candidates(record: dict[str, Any], record_id: str) -> list[tuple[str, str, str]]:
    object_id = id_value_by_key(record, ["object id", "object_id", "object"])
    classification_id = id_value_by_key(
        record,
        ["classification id", "classification_id", "classification"],
    )
    subject_id = id_value_by_key(record, ["subject id", "subject_id", "from id", "from_id"])
    target_id = id_value_by_key(
        record,
        ["target id", "target_id", "to id", "to_id", "related object id", "related_object_id"],
    )
    source_id = id_value_by_key(record, ["source object id", "source_object_id"])
    destination_id = id_value_by_key(
        record,
        ["target object id", "target_object_id", "destination object id", "destination_object_id"],
    )
    pairs: list[tuple[str, str, str]] = []
    if object_id and classification_id and object_id != classification_id:
        pairs.append((object_id, classification_id, "object_classification"))
    if subject_id and target_id and subject_id != target_id:
        pairs.append((subject_id, target_id, "subject_target"))
    if source_id and destination_id and source_id != destination_id:
        pairs.append((source_id, destination_id, "object_relation"))
    if record_id and classification_id and record_id != classification_id:
        pairs.append((record_id, classification_id, "record_classification"))
    if object_id:
        for key, value in record.items():
            normalized = normalize_key(key)
            if not normalized.endswith("objectid"):
                continue
            if normalized in {
                "objectid",
                "sourceobjectid",
                "targetobjectid",
                "destinationobjectid",
                "relatedobjectid",
            }:
                continue
            target_id = normalize_manto_id(value)
            if not target_id or target_id == object_id:
                continue
            relation_type = re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", key.lower()))
            relation_type = re.sub(r"_object_id$", "", relation_type).strip("_")
            pairs.append((object_id, target_id, relation_type or "object_definition"))
    deduped = []
    seen = set()
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            deduped.append(pair)
    return deduped


def extract_pleiades_id(data: dict[str, Any]) -> str:
    text = json.dumps(data, ensure_ascii=False)
    match = PLEIADES_RE.search(text)
    return match.group(1) if match else ""


def raw_record_tuple(
    *,
    release_id: int,
    file_path: str,
    file_format: str,
    record_number: int,
    record: dict[str, Any],
    imported_at: str,
) -> tuple:
    source_label = evidence_source_label(record)
    latest_year = extract_latest_year(candidate_date_text(record, source_label))
    return (
        release_id,
        file_path,
        record_number,
        file_format,
        record_identifier(record) or None,
        record_kind_from_path(file_path),
        record_label(record) or None,
        source_label or None,
        latest_year,
        Jsonb(record),
        imported_at,
    )


def entity_tuple(
    *, release_id: int, record: dict[str, Any], file_path: str, imported_at: str
) -> tuple | None:
    manto_id = record_identifier(record)
    if not manto_id:
        return None
    source_label = evidence_source_label(record)
    latest_year = extract_latest_year(candidate_date_text(record, source_label))
    return (
        release_id,
        manto_id,
        record_kind_from_path(file_path),
        record_label(record) or None,
        first_by_normalized_key(record, ["type", "object type", "classification type"]) or None,
        source_label or None,
        latest_year,
        Jsonb(record),
        imported_at,
    )


def edge_tuples(
    *,
    release_id: int,
    record: dict[str, Any],
    file_path: str,
    record_number: int,
    imported_at: str,
    cutoff_year: int,
) -> list[tuple]:
    record_id = record_identifier(record)
    source_label = evidence_source_label(record)
    filter_text = candidate_date_text(record, source_label)
    latest_year = extract_latest_year(filter_text)
    is_pre, reason = source_filter_status(filter_text, latest_year, cutoff_year=cutoff_year)
    base_relation_label = first_by_normalized_key(
        record,
        ["relation", "relationship", "classification type"],
    )
    rows = []
    for source_id, target_id, relation_type in edge_candidates(record, record_id):
        relation_label = base_relation_label or relation_type
        edge_key = f"{file_path}:{record_number}:{source_id}:{target_id}:{relation_type}"
        edge_id = hashlib.sha1(edge_key.encode("utf-8")).hexdigest()
        rows.append(
            (
                release_id,
                edge_id,
                source_id,
                target_id,
                relation_label or relation_type,
                source_label or None,
                latest_year,
                is_pre,
                reason,
                Jsonb(record),
                imported_at,
            )
        )
    return rows


def execute_batch(conn, sql: str, rows: list[tuple]) -> None:
    if not rows:
        return
    with conn.cursor() as cursor:
        cursor.executemany(sql, rows)


RAW_SQL = """
INSERT INTO manto_raw_records (
    release_record_id, file_path, record_number, file_format, record_id,
    record_kind, label, evidence_source_label, evidence_latest_year, data, imported_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (release_record_id, file_path, record_number) DO UPDATE
SET file_format = EXCLUDED.file_format,
    record_id = EXCLUDED.record_id,
    record_kind = EXCLUDED.record_kind,
    label = EXCLUDED.label,
    evidence_source_label = EXCLUDED.evidence_source_label,
    evidence_latest_year = EXCLUDED.evidence_latest_year,
    data = EXCLUDED.data,
    imported_at = EXCLUDED.imported_at
"""

ENTITY_SQL = """
INSERT INTO manto_entities (
    release_record_id, manto_id, entity_kind, label, type_label,
    evidence_source_label, evidence_latest_year, data, imported_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (release_record_id, manto_id) DO UPDATE
SET entity_kind = EXCLUDED.entity_kind,
    label = COALESCE(EXCLUDED.label, manto_entities.label),
    type_label = COALESCE(EXCLUDED.type_label, manto_entities.type_label),
    evidence_source_label = COALESCE(EXCLUDED.evidence_source_label, manto_entities.evidence_source_label),
    evidence_latest_year = COALESCE(EXCLUDED.evidence_latest_year, manto_entities.evidence_latest_year),
    data = EXCLUDED.data,
    imported_at = EXCLUDED.imported_at
"""

EDGE_SQL = """
INSERT INTO manto_edges (
    release_record_id, edge_id, source_manto_id, target_manto_id, relation_type,
    evidence_source_label, evidence_latest_year, is_pre_pausanias, excluded_reason,
    data, imported_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (release_record_id, edge_id) DO UPDATE
SET source_manto_id = EXCLUDED.source_manto_id,
    target_manto_id = EXCLUDED.target_manto_id,
    relation_type = EXCLUDED.relation_type,
    evidence_source_label = EXCLUDED.evidence_source_label,
    evidence_latest_year = EXCLUDED.evidence_latest_year,
    is_pre_pausanias = EXCLUDED.is_pre_pausanias,
    excluded_reason = EXCLUDED.excluded_reason,
    data = EXCLUDED.data,
    imported_at = EXCLUDED.imported_at
"""


def import_release(conn, *, release, zip_path: Path, args: argparse.Namespace) -> dict[str, int]:
    imported_at = now_iso()
    if not args.append:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM manto_raw_records WHERE release_record_id = %s", (release.record_id,))
            cursor.execute("DELETE FROM manto_entities WHERE release_record_id = %s", (release.record_id,))
            cursor.execute("DELETE FROM manto_edges WHERE release_record_id = %s", (release.record_id,))
        conn.commit()

    raw_batch: list[tuple] = []
    entity_batch: list[tuple] = []
    edge_batch: list[tuple] = []
    counts = {"raw_records": 0, "entities": 0, "edges": 0}

    for file_path, file_format, record_number, record in iter_zip_records(zip_path):
        raw_batch.append(
            raw_record_tuple(
                release_id=release.record_id,
                file_path=file_path,
                file_format=file_format,
                record_number=record_number,
                record=record,
                imported_at=imported_at,
            )
        )
        entity = entity_tuple(
            release_id=release.record_id,
            record=record,
            file_path=file_path,
            imported_at=imported_at,
        )
        if entity:
            entity_batch.append(entity)
        edge_batch.extend(
            edge_tuples(
                release_id=release.record_id,
                record=record,
                file_path=file_path,
                record_number=record_number,
                imported_at=imported_at,
                cutoff_year=args.pausanias_cutoff_year,
            )
        )
        counts["raw_records"] += 1
        if args.stop_after_records and counts["raw_records"] >= args.stop_after_records:
            break
        if len(raw_batch) >= args.batch_size:
            execute_batch(conn, RAW_SQL, raw_batch)
            execute_batch(conn, ENTITY_SQL, entity_batch)
            execute_batch(conn, EDGE_SQL, edge_batch)
            counts["entities"] += len(entity_batch)
            counts["edges"] += len(edge_batch)
            raw_batch.clear()
            entity_batch.clear()
            edge_batch.clear()
            conn.commit()

    execute_batch(conn, RAW_SQL, raw_batch)
    execute_batch(conn, ENTITY_SQL, entity_batch)
    execute_batch(conn, EDGE_SQL, edge_batch)
    counts["entities"] += len(entity_batch)
    counts["edges"] += len(edge_batch)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE manto_releases
            SET imported_at = %s,
                import_status = %s,
                local_zip_path = %s,
                updated_at = %s
            WHERE record_id = %s
            """,
            (
                imported_at,
                "partial_imported" if args.stop_after_records else "imported",
                str(zip_path),
                imported_at,
                release.record_id,
            ),
        )
    conn.commit()
    return counts


def main() -> None:
    args = parse_arguments()
    release = fetch_latest_release(concept_record_id=args.concept_record_id)
    if args.zip_path:
        zip_path = args.zip_path
    elif args.download:
        zip_path = download_release(release, cache_dir=args.cache_dir)
    else:
        zip_path = release_zip_path(release, args.cache_dir)
        if not zip_path.exists():
            raise SystemExit(
                f"Release ZIP is not cached at {zip_path}; pass --download or --zip-path."
            )
    if not zip_path.exists():
        raise SystemExit(f"MANTO ZIP does not exist: {zip_path}")

    with connect(args.database_url) as conn:
        initialize_schema(conn)
        upsert_release(
            conn,
            release,
            local_zip_path=zip_path,
            status="importing",
        )
        counts = import_release(conn, release=release, zip_path=zip_path, args=args)
    print(
        f"Imported MANTO release {release.record_id}: "
        f"{counts['raw_records']:,} raw rows, "
        f"{counts['entities']:,} entity upserts, "
        f"{counts['edges']:,} edge upserts."
    )


if __name__ == "__main__":
    main()
