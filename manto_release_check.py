#!/usr/bin/env python
"""Check whether a newer public MANTO Zenodo release is available."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from psycopg.types.json import Jsonb

from manto_release import (
    DEFAULT_CACHE_DIR,
    MANTO_CONCEPT_RECORD_ID,
    download_release,
    fetch_latest_release,
    now_iso,
    release_json,
)
from pausanias_db import add_database_argument, connect, initialize_schema


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_database_argument(parser)
    parser.add_argument("--concept-record-id", type=int, default=MANTO_CONCEPT_RECORD_ID)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument(
        "--record-known",
        action="store_true",
        help="Upsert the discovered release into manto_releases.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the latest release ZIP into the local cache.",
    )
    parser.add_argument(
        "--fail-on-newer",
        action="store_true",
        help="Exit with status 2 when the latest release is not recorded locally.",
    )
    parser.add_argument(
        "--no-database",
        action="store_true",
        help="Only query Zenodo and do not compare against manto_releases.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def known_release(conn, record_id: int) -> dict | None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT record_id, file_checksum, import_status, local_zip_path, imported_at
            FROM manto_releases
            WHERE record_id = %s
            """,
            (record_id,),
        )
        row = cursor.fetchone()
    if not row:
        return None
    return {
        "record_id": row[0],
        "file_checksum": row[1],
        "import_status": row[2],
        "local_zip_path": row[3],
        "imported_at": row[4],
    }


def upsert_release(conn, release, *, local_zip_path: Path | None = None, status: str = "discovered") -> None:
    timestamp = now_iso()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO manto_releases (
                record_id, concept_record_id, doi, concept_doi, version, title,
                zenodo_created_at, zenodo_modified_at, license_id, file_key,
                file_size, file_checksum, file_url, local_zip_path, downloaded_at,
                import_status, metadata, created_at, updated_at
            )
            VALUES (
                %(record_id)s, %(concept_record_id)s, %(doi)s, %(concept_doi)s,
                %(version)s, %(title)s, %(created)s, %(modified)s, %(license_id)s,
                %(file_key)s, %(file_size)s, %(file_checksum)s, %(file_url)s,
                %(local_zip_path)s, %(downloaded_at)s, %(status)s, %(metadata)s,
                %(timestamp)s, %(timestamp)s
            )
            ON CONFLICT (record_id) DO UPDATE
            SET concept_record_id = EXCLUDED.concept_record_id,
                doi = EXCLUDED.doi,
                concept_doi = EXCLUDED.concept_doi,
                version = EXCLUDED.version,
                title = EXCLUDED.title,
                zenodo_created_at = EXCLUDED.zenodo_created_at,
                zenodo_modified_at = EXCLUDED.zenodo_modified_at,
                license_id = EXCLUDED.license_id,
                file_key = EXCLUDED.file_key,
                file_size = EXCLUDED.file_size,
                file_checksum = EXCLUDED.file_checksum,
                file_url = EXCLUDED.file_url,
                local_zip_path = COALESCE(EXCLUDED.local_zip_path, manto_releases.local_zip_path),
                downloaded_at = COALESCE(EXCLUDED.downloaded_at, manto_releases.downloaded_at),
                import_status = CASE
                    WHEN manto_releases.import_status = 'imported' AND EXCLUDED.import_status = 'discovered'
                        THEN manto_releases.import_status
                    ELSE EXCLUDED.import_status
                END,
                metadata = EXCLUDED.metadata,
                updated_at = EXCLUDED.updated_at
            """,
            {
                "record_id": release.record_id,
                "concept_record_id": release.concept_record_id,
                "doi": release.doi,
                "concept_doi": release.concept_doi,
                "version": release.version,
                "title": release.title,
                "created": release.created,
                "modified": release.modified,
                "license_id": release.license_id,
                "file_key": release.file_key,
                "file_size": release.file_size,
                "file_checksum": release.file_checksum,
                "file_url": release.file_url,
                "local_zip_path": str(local_zip_path) if local_zip_path else None,
                "downloaded_at": timestamp if local_zip_path else None,
                "status": status,
                "metadata": Jsonb(release.metadata),
                "timestamp": timestamp,
            },
        )
    conn.commit()


def main() -> None:
    args = parse_arguments()
    release = fetch_latest_release(concept_record_id=args.concept_record_id)
    local_zip_path = None
    known = None
    if args.no_database:
        if args.record_known:
            raise SystemExit("--record-known requires a database.")
        if args.download:
            local_zip_path = download_release(release, cache_dir=args.cache_dir)
    else:
        with connect(args.database_url) as conn:
            initialize_schema(conn)
            known = known_release(conn, release.record_id)
            if args.download:
                local_zip_path = download_release(release, cache_dir=args.cache_dir)
            if args.record_known or args.download:
                upsert_release(
                    conn,
                    release,
                    local_zip_path=local_zip_path,
                    status="downloaded" if local_zip_path else "discovered",
                )
                known = known_release(conn, release.record_id)

    latest_is_known = known is not None and known["file_checksum"] == release.file_checksum
    payload = {
        "latest_is_known": latest_is_known,
        "release": json.loads(release_json(release)),
        "known": known,
        "downloaded_path": str(local_zip_path) if local_zip_path else None,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif latest_is_known:
        status = known["import_status"] if known else "known"
        print(f"MANTO release {release.record_id} is already known ({status}).")
    else:
        print(
            f"New MANTO release available: {release.record_id} {release.version} "
            f"{release.file_key} {release.file_checksum}"
        )
    if args.fail_on_newer and not latest_is_known:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
