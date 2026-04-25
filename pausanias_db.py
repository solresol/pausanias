"""Shared PostgreSQL helpers for the Pausanias pipeline."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import psycopg


DEFAULT_DATABASE_URL = "dbname=pausanias"


def get_database_url(database_url: str | None = None) -> str:
    """Resolve the PostgreSQL connection string for scripts."""
    return (
        database_url
        or os.getenv("PAUSANIAS_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or DEFAULT_DATABASE_URL
    )


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
    return psycopg.connect(get_database_url(database_url))


def schema_path() -> Path:
    return Path(__file__).resolve().parent / "database" / "schema.sql"


def initialize_schema(conn: psycopg.Connection) -> None:
    """Create the canonical schema if it does not already exist."""
    conn.execute(schema_path().read_text(encoding="utf-8"))
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
