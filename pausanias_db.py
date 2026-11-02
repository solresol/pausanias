"""Shared PostgreSQL helpers for the Pausanias pipeline."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo


DEFAULT_DATABASE_URL = "dbname=pausanias"
PROFILE_KEYS = {"DB_HOST": "host", "DB_PORT": "port", "DB_NAME": "dbname", "DB_USER": "user"}


def database_profile() -> tuple[dict[str, str], int | None]:
    """Read only non-secret connection metadata; never source shell commands."""
    configured = os.getenv("PAUSANIAS_DATABASE_CONFIG")
    path = Path(configured) if configured else Path.home() / ".config/pausanias/database.conf"
    if not path.exists():
        if configured:
            raise FileNotFoundError("Explicit Pausanias database profile is missing")
        return {}, None
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key not in {*PROFILE_KEYS, "DB_EXPECTED_SERVER_MAJOR"}:
            raise ValueError("Unknown or malformed non-secret database profile entry")
        if not value.strip():
            raise ValueError("Empty database profile entry")
        values[key] = value.strip()
    major = values.get("DB_EXPECTED_SERVER_MAJOR")
    return {dest: values[key] for key, dest in PROFILE_KEYS.items() if key in values}, int(major) if major else None


def resolved_database(database_url: str | None = None) -> tuple[dict[str, str], int | None]:
    """Explicit DSN fields override PG* environment, then the production profile."""
    profile, major = database_profile()
    values = {"dbname": "pausanias", **profile}
    for key, dest in {"PGHOST": "host", "PGPORT": "port", "PGDATABASE": "dbname", "PGUSER": "user"}.items():
        if os.getenv(key):
            values[dest] = os.environ[key]
    explicit = database_url or os.getenv("PAUSANIAS_DATABASE_URL") or os.getenv("DATABASE_URL")
    if explicit:
        values.update(conninfo_to_dict(explicit))
    if os.getenv("PAUSANIAS_DATABASE_EXPECTED_MAJOR"):
        major = int(os.environ["PAUSANIAS_DATABASE_EXPECTED_MAJOR"])
    if major is not None and not all(values.get(k) for k in ["dbname", "user", "host", "port"]):
        raise ValueError("Guarded Pausanias routing requires an explicit database, role, host and port")
    return values, major


def get_database_url(database_url: str | None = None) -> str:
    """Resolve the PostgreSQL connection string for scripts."""
    values, _ = resolved_database(database_url)
    return make_conninfo(**values)


def add_database_argument(parser: argparse.ArgumentParser) -> None:
    """Add the standard PostgreSQL connection option to a CLI parser."""
    parser.add_argument(
        "--database-url",
        default=None,
        help=(
            "PostgreSQL connection string. Defaults to PAUSANIAS_DATABASE_URL, "
            "DATABASE_URL, or 'dbname=pausanias'."
        ),
    )


def connect(database_url: str | None = None) -> psycopg.Connection:
    """Open a PostgreSQL connection."""
    values, expected_major = resolved_database(database_url)
    conn = psycopg.connect(make_conninfo(**values))
    if expected_major is not None:
        expected = (values["dbname"], values["user"], values["host"], int(values["port"]), expected_major)
        actual = (conn.info.dbname, conn.info.user, conn.info.host, conn.info.port, conn.info.server_version // 10000)
        if actual != expected:
            conn.close()
            raise RuntimeError("Refusing Pausanias SQL: database/role/socket/port/version mismatch")
    return conn


def schema_path() -> Path:
    return Path(__file__).resolve().parent / "database" / "schema.sql"


def initialize_schema(conn: psycopg.Connection) -> None:
    """Create the canonical schema if it does not already exist."""
    conn.execute(schema_path().read_text(encoding="utf-8"))
    conn.execute((schema_path().parent / "graphic_book_exchange.sql").read_text(encoding="utf-8"))
    conn.commit()


def read_sql_query(
    query: str,
    conn: psycopg.Connection,
    params: Iterable[Any] | dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Run a query and return a DataFrame without relying on sqlite-specific pandas paths."""
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = []
        for column in cursor.description or []:
            columns.append(column.name if hasattr(column, "name") else column[0])
    return pd.DataFrame(rows, columns=columns)


def table_exists(conn: psycopg.Connection, table_name: str) -> bool:
    with conn.cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
        return cursor.fetchone()[0] is not None


def column_exists(conn: psycopg.Connection, table_name: str, column_name: str) -> bool:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = %s
            """,
            (table_name, column_name),
        )
        return cursor.fetchone() is not None
