"""Read the PostgreSQL-exported graphic-book corpus; reject the legacy database."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_SNAPSHOT = ROOT / "graphic_book/workflow/corpus.sqlite"


def snapshot_path() -> Path:
    """Locate a validated exchange snapshot without creating an empty database."""
    path = Path(
        os.environ.get("PAUSANIAS_GRAPHIC_BOOK_SNAPSHOT", DEFAULT_SNAPSHOT)
    ).resolve()
    if path == ROOT / "pausanias.sqlite":
        raise RuntimeError(
            "The legacy pausanias.sqlite is not a graphic-book corpus snapshot"
        )
    if not path.is_file():
        raise RuntimeError(
            f"Missing corpus snapshot {path}; run graphic_book_exchange.py begin first"
        )
    try:
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as conn:
            row = conn.execute(
                "SELECT schema_version, exported_at FROM metadata WHERE singleton=1"
            ).fetchone()
            if not row or row[0] != 1 or not row[1]:
                raise RuntimeError(
                    "Corpus snapshot has not been exported from PostgreSQL"
                )
    except sqlite3.DatabaseError as exc:
        raise RuntimeError(f"Invalid corpus snapshot: {path}") from exc
    return path


def load_translation(passage_id: str) -> str:
    """Return the exact exported English translation, including its whitespace."""
    with sqlite3.connect(snapshot_path().as_uri() + "?mode=ro", uri=True) as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id=?",
            (passage_id,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing exported translation for passage {passage_id}")
    return row[0]
