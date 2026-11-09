#!/usr/bin/env python
"""Stage a pinned MANTO release without changing the active production version.

Creates only a new isolated schema using existing table shapes and constraints.
There is no public-table promotion, model run, website build, or credential change.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
from types import SimpleNamespace
import zipfile

from psycopg import sql

from manto_importer import (
    ENTITY_DETAILS_PATH, TIE_DETAILS_PATH, acquire_import_lock,
    csv_header_likely, csv_record_from_row, fallback_csv_headers, import_release, release_import_lock,
)
from manto_release import checksum_matches, release_from_zenodo_record
from manto_release_check import upsert_release
from pausanias_db import connect

TABLES = (
    'manto_releases', 'manto_raw_records', 'manto_entities',
    'manto_entity_details', 'manto_tie_details', 'manto_edges',
    'manto_place_status_labels',
)


def validate_schema_name(name):
    if not re.fullmatch(r'manto_stage_[a-z0-9_]{1,45}', name):
        raise ValueError('Stage schema must be manto_stage_ followed by safe lowercase letters/digits/underscores')
    return name


def inspect_archive(path, release):
    if not release.file_checksum or not checksum_matches(path, release.file_checksum):
        raise ValueError('Pinned archive checksum missing or mismatched')
    if path.stat().st_size != release.file_size:
        raise ValueError('Pinned archive byte-size mismatch')
    detail_counts = {}
    csv_counts = {}
    duplicate_headers = {}
    differing_name_rows = {}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names):
            raise ValueError('Duplicate ZIP entry names')
        for name in names:
            if name.startswith('/') or '..' in Path(name).parts:
                raise ValueError('Unsafe archive member path')
        if not {ENTITY_DETAILS_PATH, TIE_DETAILS_PATH}.issubset(names):
            raise ValueError('Required entity/tie CSV detail paths changed')
        bad = archive.testzip()
        if bad:
            raise ValueError(f'ZIP CRC failure: {bad}')
        for name in (n for n in names if n.lower().endswith('.csv')):
            with archive.open(name) as raw:
                rows = csv.reader(io.TextIOWrapper(raw, encoding='utf-8-sig'))
                first = next(rows, None)
                if first is None:
                    csv_counts[name] = 0
                    continue
                has_header = csv_header_likely(first)
                headers = first if has_header else fallback_csv_headers(name, len(first))
                duplicated = {header: [i for i, value in enumerate(headers) if value == header]
                              for header in set(headers) if headers.count(header) > 1}
                if duplicated:
                    duplicate_headers[name] = sorted(duplicated)
                if name in (ENTITY_DETAILS_PATH, TIE_DETAILS_PATH) and not {'nodegoat ID', 'Object ID', 'Name'}.issubset(headers):
                    raise ValueError(f'Required columns missing: {name}')
                count = 0 if has_header else 1
                for row in rows:
                    if len(row) != len(headers):
                        raise ValueError(f'CSV row-width mismatch: {name}, row {count + 2}')
                    for header, indices in duplicated.items():
                        if len({row[index] for index in indices}) != 1:
                            if header != 'Name':
                                raise ValueError(f'Conflicting non-Name duplicate values: {name}, {header}, row {count + 2}')
                            differing_name_rows[name] = differing_name_rows.get(name, 0) + 1
                    if duplicated and list(csv_record_from_row(headers, row).values()) != row:
                        raise ValueError(f'Duplicate-column preservation failed: {name}, row {count + 2}')
                    count += 1
                csv_counts[name] = count
                if name in (ENTITY_DETAILS_PATH, TIE_DETAILS_PATH):
                    detail_counts[name] = count
        return {'zip_entries': len(names), 'uncompressed_bytes': sum(i.file_size for i in archive.infolist()),
                'detail_csv_rows': detail_counts, 'csv_record_counts': csv_counts, 'archive_size': path.stat().st_size,
                'preserved_duplicate_headers': duplicate_headers,
                'differing_display_raw_name_rows': differing_name_rows,
                'archive_checksum': release.file_checksum}


def snapshot_counts(conn, schema='public'):
    result = {}
    for table in TABLES:
        key = 'record_id' if table == 'manto_releases' else 'release_record_id'
        query = sql.SQL('SELECT {key}, count(*) FROM {schema}.{table} GROUP BY {key} ORDER BY {key}').format(
            key=sql.Identifier(key), schema=sql.Identifier(schema), table=sql.Identifier(table))
        result[table] = {str(k): v for k, v in conn.execute(query).fetchall()}
    return result


def create_stage(conn, schema):
    validate_schema_name(schema)
    if conn.execute('SELECT to_regnamespace(%s)', (schema,)).fetchone()[0] is not None:
        raise ValueError('Stage schema already exists; inspect it instead of replacing data')
    conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    for table in TABLES:
        conn.execute(sql.SQL('CREATE TABLE {}.{} (LIKE public.{} INCLUDING ALL)').format(
            sql.Identifier(schema), sql.Identifier(table), sql.Identifier(table)))
        if table != 'manto_releases':
            conn.execute(sql.SQL('ALTER TABLE {}.{} ADD FOREIGN KEY (release_record_id) REFERENCES {}.manto_releases(record_id) ON DELETE CASCADE').format(
                sql.Identifier(schema), sql.Identifier(table), sql.Identifier(schema)))
    conn.execute(sql.SQL('ALTER TABLE {}.manto_place_status_labels ADD FOREIGN KEY (release_record_id,object_id) REFERENCES {}.manto_entity_details(release_record_id,object_id) ON DELETE CASCADE').format(
        sql.Identifier(schema), sql.Identifier(schema)))
    # Session-level SET survives the existing importer's per-batch commits.
    conn.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
    conn.commit()
    actual = conn.execute('SHOW search_path').fetchone()[0]
    if actual != schema:
        raise RuntimeError('Stage search_path guard failed')
    conn.commit()


def validate_endpoint(info):
    if (info.server_version // 10000, info.dbname, info.port, info.host, info.user) != (
        18, 'pausanias', 5433, '/var/run/postgresql', 'gregb'
    ):
        raise RuntimeError('This manual stage import requires Pausanias PG18/5433 on the local Unix socket as gregb')


def stage_release(database_url, metadata_path, zip_path, schema, audit_path, backup_path,
                  expected_record_id, backup_sha256):
    validate_schema_name(schema)
    record = json.loads(metadata_path.read_text())
    release = release_from_zenodo_record(record)
    if release.concept_record_id != 19446254 or release.record_id != expected_record_id:
        raise ValueError('Unexpected MANTO release identity')
    if release.license_id != 'cc-by-nc-4.0':
        raise ValueError('Unexpected licence; review before import')
    if not backup_path.is_file() or backup_path.stat().st_size == 0:
        raise ValueError('A completed pre-import backup is required')
    audit = {'record_id': release.record_id, 'concept_record_id': release.concept_record_id,
             'doi': release.doi, 'license_id': release.license_id, 'stage_schema': schema,
             'stage_only': True, 'code': 'manto_stage_import.py',
             'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'backup_path': str(backup_path.resolve()),
             'backup_sha256': ''}
    with backup_path.open('rb') as backup_file:
        audit['backup_sha256'] = hashlib.file_digest(backup_file, 'sha256').hexdigest()
    if not re.fullmatch(r'[0-9a-f]{64}', backup_sha256) or audit['backup_sha256'] != backup_sha256:
        raise ValueError('Completed backup checksum mismatch')
    audit.update(inspect_archive(zip_path, release))
    audit_path.write_text(json.dumps(audit, indent=2)+'\n')
    print(json.dumps({'phase':'archive_verified', 'release':release.record_id, 'zip_entries':audit['zip_entries'],
                      'csv_rows':sum(audit['csv_record_counts'].values()), 'detail_rows':audit['detail_csv_rows']}), flush=True)
    with connect(database_url) as conn:
        validate_endpoint(conn.info)
        conn.execute('SET client_encoding TO UTF8')
        conn.execute("SET lock_timeout TO '10s'")
        if not acquire_import_lock(conn):
            raise RuntimeError('Another MANTO import is active')
        try:
            if conn.execute('SELECT 1 FROM public.manto_releases WHERE record_id=%s', (release.record_id,)).fetchone():
                raise ValueError('Release already present in public; reconcile existing outcome before importing')
            audit['public_counts_before'] = snapshot_counts(conn)
            audit_path.write_text(json.dumps(audit, indent=2)+'\n')
            conn.commit()
            create_stage(conn, schema)
            upsert_release(conn, release, local_zip_path=zip_path.resolve(), status='importing')
            print(json.dumps({'phase':'stage_import_started','schema':schema,'release':release.record_id}), flush=True)
            counts = import_release(conn, release=release, zip_path=zip_path,
                args=SimpleNamespace(append=True, stop_after_records=None, batch_size=2000, pausanias_cutoff_year=180))
            audit['importer_upsert_counters'] = counts
            audit['stage_counts'] = snapshot_counts(conn, schema)
            audit['stage_raw_counts_by_file'] = conn.execute(
                'SELECT file_path,file_format,count(*) FROM manto_raw_records GROUP BY 1,2 ORDER BY 1'
            ).fetchall()
            staged_csv_counts = {path: count for path, fmt, count in audit['stage_raw_counts_by_file'] if fmt == 'csv'}
            if staged_csv_counts != {path: count for path, count in audit['csv_record_counts'].items() if count}:
                raise RuntimeError('Per-file CSV raw record counts differ from independently counted archive rows')
            for table, file_path in [('manto_entity_details',ENTITY_DETAILS_PATH),('manto_tie_details',TIE_DETAILS_PATH)]:
                if audit['stage_counts'][table].get(str(release.record_id)) != audit['detail_csv_rows'][file_path]:
                    raise RuntimeError(f'Canonical detail row count mismatch: {table}')
            for table, releases in audit['stage_counts'].items():
                if set(releases) != {str(release.record_id)} or not releases[str(release.record_id)]:
                    raise RuntimeError(f'Unexpected empty table or mixed release IDs: {table}')
            audit['public_counts_after'] = snapshot_counts(conn)
            if audit['public_counts_before'] != audit['public_counts_after']:
                raise RuntimeError('Public MANTO counts changed during stage import; reconcile before activation')
            audit['stage_edge_filters'] = conn.execute('SELECT is_pre_pausanias, excluded_reason, count(*) FROM manto_edges GROUP BY 1,2 ORDER BY 1,2').fetchall()
            audit['stage_status_labels'] = conn.execute('SELECT target_label,count(*) FROM manto_place_status_labels GROUP BY 1 ORDER BY 1').fetchall()
            audit['validated'] = True
            audit['public_row_counts_unchanged'] = True
            audit['public_data_write_performed'] = False
            conn.commit()
        finally:
            conn.rollback()  # Clear a failed transaction before releasing the session lock.
            release_import_lock(conn)
            conn.commit()
    audit_path.write_text(json.dumps(audit, indent=2)+'\n')
    print(json.dumps({'phase':'validated_stage_complete','schema':schema,'release':release.record_id,'counts':audit['stage_counts'],'public_row_counts_unchanged':True}), flush=True)
    return audit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database-url',required=True)
    parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--zip-path',type=Path,required=True)
    parser.add_argument('--stage-schema',required=True)
    parser.add_argument('--audit-path',type=Path,required=True)
    parser.add_argument('--backup-path',type=Path,required=True)
    parser.add_argument('--expected-record-id',type=int,required=True)
    parser.add_argument('--backup-sha256',required=True)
    args=parser.parse_args()
    stage_release(args.database_url,args.metadata,args.zip_path,args.stage_schema,args.audit_path,args.backup_path,
                  args.expected_record_id,args.backup_sha256)


if __name__=='__main__':
    main()
