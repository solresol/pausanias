#!/usr/bin/env python
"""Import Pleiades representative coordinates from the public CSV dump."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
from datetime import datetime, timezone
from pathlib import Path

import requests

from pausanias_db import add_database_argument, connect, initialize_schema


DUMP_URL = "https://atlantides.org/downloads/pleiades/dumps/pleiades-places-latest.csv.gz"
CACHE_DIR = Path("tmp/pleiades")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_database_argument(parser)
    parser.add_argument("--dump-url", default=DUMP_URL)
    parser.add_argument(
        "--cache-path",
        default=str(CACHE_DIR / "pleiades-places-latest.csv.gz"),
        help="Local cached copy of the dump; downloaded if missing.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-download the dump even if a cached copy exists.",
    )
    parser.add_argument(
        "--stop",
        type=int,
        default=None,
        help="Import at most this many rows (for cheap partial runs).",
    )
    return parser.parse_args()


def download_dump(url: str, cache_path: Path, *, refresh: bool) -> Path:
    if cache_path.exists() and not refresh:
        print(f"Using cached dump at {cache_path}", flush=True)
        return cache_path
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} ...", flush=True)
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    cache_path.write_bytes(response.content)
    print(f"Saved {len(response.content):,} bytes to {cache_path}", flush=True)
    return cache_path


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_place_rows(dump_path: Path, *, stop: int | None = None) -> list[tuple]:
    timestamp = now_iso()
    rows: list[tuple] = []
    with gzip.open(dump_path, "rb") as handle:
        reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8"))
        missing = {"id", "reprLat", "reprLong"} - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(
                f"Pleiades dump is missing expected columns: {sorted(missing)}; "
                f"found {reader.fieldnames}"
            )
        for record in reader:
            pleiades_id = (record.get("id") or "").strip()
            if not pleiades_id:
                continue
            rows.append(
                (
                    pleiades_id,
                    (record.get("title") or "").strip(),
                    parse_float(record.get("reprLat")),
                    parse_float(record.get("reprLong")),
                    (record.get("locationPrecision") or "").strip(),
                    (record.get("timePeriodsKeys") or "").strip(),
                    timestamp,
                )
            )
            if stop is not None and len(rows) >= stop:
                break
    return rows


def save_rows(conn, rows: list[tuple]) -> None:
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO pleiades_places (
                pleiades_id, title, representative_latitude,
                representative_longitude, location_precision, time_periods,
                imported_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (pleiades_id) DO UPDATE
            SET title = EXCLUDED.title,
                representative_latitude = EXCLUDED.representative_latitude,
                representative_longitude = EXCLUDED.representative_longitude,
                location_precision = EXCLUDED.location_precision,
                time_periods = EXCLUDED.time_periods,
                imported_at = EXCLUDED.imported_at
            """,
            rows,
        )
    conn.commit()


def main() -> None:
    args = parse_arguments()
    dump_path = download_dump(args.dump_url, Path(args.cache_path), refresh=args.refresh)
    rows = read_place_rows(dump_path, stop=args.stop)
    with_coordinates = sum(1 for row in rows if row[2] is not None and row[3] is not None)
    with connect(args.database_url) as conn:
        initialize_schema(conn)
        save_rows(conn, rows)
    print(
        f"Imported {len(rows):,} Pleiades places "
        f"({with_coordinates:,} with representative coordinates)."
    )


if __name__ == "__main__":
    main()
