#!/usr/bin/env python3
"""Exchange the graphic-book corpus and completed pages through one S3 SQLite object."""

from __future__ import annotations

import argparse
import configparser
import hashlib
import os
import random
import re
import sqlite3
import tempfile
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

from graphic_book_asset_store import DEFAULT_S3_URI, sha256_file
from graphic_book_corpus import DEFAULT_SNAPSHOT
from pausanias_db import add_database_argument, connect

ROOT = Path(__file__).resolve().parent
SNAPSHOT_KEY = "workflow/corpus.sqlite"
PASSAGE_RE = re.compile(r"^[1-9][0-9]*\.[1-9][0-9]*\.[1-9][0-9]*$")


class BusyError(RuntimeError):
    """Another worker owns the shared snapshot."""


class ConflictError(RuntimeError):
    """A conditional upload failed; the caller must not publish its old copy."""


def utc_now() -> str:
    """Use explicit UTC timestamps in both databases."""
    return datetime.now(UTC).isoformat()


def source_hash(greek: str, english: str) -> str:
    """Hash exact text with length framing, including whitespace and newlines."""
    digest = hashlib.sha256()
    for text in (greek, english):
        encoded = text.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


@contextmanager
def snapshot_connection(path: Path):
    """Close SQLite handles before uploading the single-file DELETE-journal DB."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def create_snapshot(path: Path) -> None:
    """Initialize a new exchange database; never reuse the legacy SQLite file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with snapshot_connection(path) as conn:
        conn.executescript((ROOT / "database/graphic_book_snapshot.sql").read_text())
        conn.execute("INSERT INTO metadata VALUES (1, 1, 0, '', ?)", (utc_now(),))


class S3Store:
    """Use signed SDK calls so every shared-database write has a precondition."""

    def __init__(self, uri: str, client=None):
        match = re.fullmatch(r"s3://([^/]+)(?:/(.*))?", uri.rstrip("/"))
        if not match:
            raise ValueError(f"Invalid S3 URI: {uri}")
        self.bucket = match[1]
        self.prefix = (match[2] or "").strip("/")
        self.client = client or boto3.client(
            "s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-2")
        )

    def key(self, key: str) -> str:
        """Apply an optional isolated store prefix, including during smoke tests."""
        return f"{self.prefix}/{key}" if self.prefix else key

    def get(self, key: str) -> tuple[bytes, str]:
        """Read bytes and their ETag from the same response."""
        response = self.client.get_object(Bucket=self.bucket, Key=self.key(key))
        try:
            return response["Body"].read(), response["ETag"]
        finally:
            response["Body"].close()

    def put_snapshot(self, path: Path, etag: str | None) -> str:
        """Compare-and-swap the database; a missing object is created once."""
        condition = {"IfMatch": etag} if etag else {"IfNoneMatch": "*"}
        try:
            with path.open("rb") as handle:
                response = self.client.put_object(
                    Bucket=self.bucket,
                    Key=self.key(SNAPSHOT_KEY),
                    Body=handle,
                    ContentType="application/vnd.sqlite3",
                    **condition,
                )
        except ClientError as exc:
            if exc.response["Error"]["Code"] in {
                "PreconditionFailed",
                "ConditionalRequestConflict",
                "412",
                "409",
            }:
                raise ConflictError(
                    "S3 snapshot changed; stop and discard this stale session"
                ) from exc
            raise
        return response["ETag"]

    def put_file(self, path: Path, key: str, *, immutable: bool = True) -> None:
        """Upload an artifact, verifying an existing immutable key on retries."""
        digest = sha256_file(path)
        try:
            with path.open("rb") as handle:
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=self.key(key),
                    Body=handle,
                    Metadata={"sha256": digest},
                    **({"IfNoneMatch": "*"} if immutable else {}),
                )
        except ClientError as exc:
            if not immutable or exc.response["Error"]["Code"] not in {
                "PreconditionFailed",
                "412",
            }:
                raise
            existing, _ = self.get(key)
            if hashlib.sha256(existing).hexdigest() != digest:
                raise ConflictError(f"Existing artifact differs: {key}") from exc

    def mirror_file(self, path: Path, key: str) -> None:
        """Keep compatibility mirrors current without retransferring matching files."""
        try:
            head = self.client.head_object(Bucket=self.bucket, Key=self.key(key))
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in {"NoSuchKey", "404", "NotFound"}:
                raise
        else:
            if head.get("Metadata", {}).get("sha256") == sha256_file(path):
                return
        self.put_file(path, key, immutable=False)

    def download_verified(
        self, key: str, destination: Path, digest: str, size: int
    ) -> None:
        """Stage and verify an object before replacing any accepted local file."""
        if (
            destination.is_file()
            and destination.stat().st_size == size
            and sha256_file(destination) == digest
        ):
            return
        content, _ = self.get(key)
        if len(content) != size or hashlib.sha256(content).hexdigest() != digest:
            raise RuntimeError(f"S3 artifact checksum mismatch: {key}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        try:
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)


class Exchange:
    """One local checkout and its conditional-write ownership token."""

    def __init__(self, store: S3Store, path: Path, clock=time.time):
        self.store = store
        self.path = path.resolve()
        self.session_path = self.path.with_suffix(".session")
        self.clock = clock
        self.etag = None
        self.token = ""
        self.lease_seconds = 21600
        if self.session_path.exists():
            config = configparser.ConfigParser()
            config.read(self.session_path)
            session = config["session"]
            if session["bucket"] != store.bucket or session["prefix"] != store.prefix:
                raise RuntimeError("Local session belongs to a different S3 store")
            self.etag = session["etag"]
            self.token = session["token"]
            self.lease_seconds = int(session["lease_seconds"])

    def save_session(self) -> None:
        """Keep returned ETags outside the file whose content they identify."""
        config = configparser.ConfigParser()
        config["session"] = {
            "etag": self.etag,
            "token": self.token,
            "lease_seconds": str(self.lease_seconds),
            "bucket": self.store.bucket,
            "prefix": self.store.prefix,
        }
        with self.session_path.open("w") as handle:
            config.write(handle)

    def fetch(self, *, create: bool = False) -> None:
        """Fetch an intact database and validate the protocol before using it."""
        try:
            content, self.etag = self.store.get(SNAPSHOT_KEY)
        except ClientError as exc:
            if not create or exc.response["Error"]["Code"] not in {"NoSuchKey", "404"}:
                raise
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.unlink(missing_ok=True)
            create_snapshot(self.path)
            self.etag = None
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        try:
            with snapshot_connection(temporary) as conn:
                if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RuntimeError("Corrupt S3 SQLite snapshot")
                row = conn.execute(
                    "SELECT schema_version FROM metadata WHERE singleton=1"
                ).fetchone()
                if not row or row[0] != 1:
                    raise RuntimeError("Unsupported graphic-book snapshot schema")
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def claim(self, owner: str, role: str, *, lease_seconds: int = 21600) -> str:
        """Claim before doing work, including before PostgreSQL or image changes."""
        if lease_seconds <= 0:
            raise ValueError("Lease duration must be positive")
        self.fetch(create=role == "raksasa")
        self.token = uuid4().hex
        self.lease_seconds = lease_seconds
        now = int(self.clock())
        with snapshot_connection(self.path) as conn:
            worker = conn.execute("SELECT * FROM active_worker").fetchone()
            if worker and worker["expires_at"] > now:
                raise BusyError(
                    f"{worker['owner']} is active until {worker['expires_at']}; no work done"
                )
            if worker and worker["run_id"]:
                conn.execute(
                    "UPDATE runs SET status='expired', completed_at=? WHERE run_id=?",
                    (utc_now(), worker["run_id"]),
                )
            conn.execute("DELETE FROM active_worker")
            if role == "cloud":
                if not conn.execute(
                    "SELECT exported_at FROM metadata WHERE singleton=1"
                ).fetchone()[0]:
                    raise RuntimeError("Raksasa has not exported the corpus yet")
                conn.execute(
                    "INSERT INTO runs (run_id,owner,started_at,status) VALUES (?,?,?,'active')",
                    (self.token, owner, utc_now()),
                )
            conn.execute(
                "INSERT INTO active_worker VALUES (1,?,?,?,?,?,?)",
                (
                    self.token,
                    owner,
                    role,
                    now,
                    now + lease_seconds,
                    self.token if role == "cloud" else None,
                ),
            )
            conn.execute(
                "UPDATE metadata SET generation=generation+1,updated_at=?", (utc_now(),)
            )
        self.etag = self.store.put_snapshot(self.path, self.etag)
        self.save_session()
        return self.token

    def owned_worker(self, conn) -> sqlite3.Row:
        """Fail closed on expired leases or sessions without a successful claim."""
        worker = conn.execute("SELECT * FROM active_worker").fetchone()
        if (
            not self.token
            or not self.session_path.exists()
            or not worker
            or worker["token"] != self.token
        ):
            raise ConflictError("No owned session; begin a new run")
        if worker["expires_at"] <= int(self.clock()):
            raise ConflictError("Lease expired; this worker must not publish")
        return worker

    def publish(
        self, *, release: bool = False, status: str = "completed", notes: str = ""
    ) -> None:
        """Renew/checkpoint or release ownership with a conditional upload."""
        with snapshot_connection(self.path) as conn:
            worker = self.owned_worker(conn)
            if release:
                if worker["run_id"]:
                    conn.execute(
                        "UPDATE runs SET status=?,completed_at=?,notes=? WHERE run_id=?",
                        (status, utc_now(), notes, worker["run_id"]),
                    )
                conn.execute("DELETE FROM active_worker")
            else:
                conn.execute(
                    "UPDATE active_worker SET expires_at=?",
                    (int(self.clock()) + self.lease_seconds,),
                )
            conn.execute(
                "UPDATE metadata SET generation=generation+1,updated_at=?", (utc_now(),)
            )
        self.etag = self.store.put_snapshot(self.path, self.etag)
        if release:
            self.session_path.unlink(missing_ok=True)
        else:
            self.save_session()

    def abort(self, notes: str = "") -> None:
        """Release only our live server claim, discarding unpublished local edits."""
        self.fetch()
        self.publish(release=True, status="aborted", notes=notes)

    def next_passage(self) -> str | None:
        """Select numerically from the complete exported corpus and page catalog."""
        with snapshot_connection(self.path) as conn:
            row = conn.execute("""
                SELECT p.id FROM passages p JOIN translations t ON t.passage_id=p.id
                LEFT JOIN illustrations i ON i.passage_id=p.id
                WHERE i.passage_id IS NULL AND length(t.english_translation)>0
                ORDER BY p.book,p.chapter,p.section LIMIT 1
            """).fetchone()
        return row[0] if row else None

    def hydrate(self, image_dir: Path) -> int:
        """Retrieve accepted pages for references, replacements, and the PDF check."""
        with snapshot_connection(self.path) as conn:
            rows = conn.execute("SELECT * FROM illustrations").fetchall()
        for row in rows:
            path = image_dir.joinpath(*row["passage_id"].split(".")).with_suffix(".png")
            self.store.download_verified(
                row["image_s3_key"], path, row["image_sha256"], row["byte_count"]
            )
        with snapshot_connection(self.path) as conn:
            files = conn.execute("""SELECT f.* FROM result_files f
                JOIN results r ON r.result_id=f.result_id
                WHERE r.import_status!='rejected' ORDER BY r.created_at,f.path""").fetchall()
        for file in files:
            relative = PurePosixPath(file["path"])
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or not file["path"].startswith("graphic_book/assets/generated/")
            ):
                if relative.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    raise ValueError("Unsafe component image path")
                continue
            if relative.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                self.store.download_verified(
                    file["s3_key"], ROOT / relative, file["sha256"], file["byte_count"]
                )
        return len(rows)

    def record_result(
        self,
        passage_id: str,
        image: Path,
        kind: str,
        source_commit: str,
        files: list[Path],
        original_sha256: str | None = None,
    ) -> str:
        """Publish verified run-specific objects before adding their database record."""
        if not PASSAGE_RE.fullmatch(passage_id) or not re.fullmatch(
            r"[0-9a-f]{40}", source_commit
        ):
            raise ValueError(
                "A numeric passage ID and full source Git commit are required"
            )
        from PIL import Image

        with Image.open(image) as page:
            if page.format != "PNG":
                raise ValueError("Finished pages must be PNG files")
            page.verify()
        with snapshot_connection(self.path) as conn:
            worker = self.owned_worker(conn)
            if worker["role"] != "cloud":
                raise RuntimeError("Only a cloud-generation session can record results")
            translation = conn.execute(
                "SELECT source_sha256 FROM translations WHERE passage_id=?",
                (passage_id,),
            ).fetchone()
            old = conn.execute(
                "SELECT image_sha256 FROM illustrations WHERE passage_id=?",
                (passage_id,),
            ).fetchone()
            if not translation:
                raise ValueError("Passage has no exported translation")
            if kind == "new" and (old or passage_id != self.next_passage()):
                raise ValueError(
                    "New page must be the next unillustrated translated passage"
                )
            if kind == "replacement" and (not old or old[0] != original_sha256):
                raise ValueError(
                    "Replacement's original checksum does not match the catalog"
                )
            if conn.execute(
                "SELECT 1 FROM results WHERE run_id=? AND kind=?", (self.token, kind)
            ).fetchone():
                raise ValueError(f"Run already contains a {kind} result")
        result_id = uuid4().hex
        key = f"workflow/results/{result_id}/page.png"
        digest, size = sha256_file(image), image.stat().st_size
        self.store.put_file(image, key)
        file_rows = []
        if kind == "replacement":
            with snapshot_connection(self.path) as conn:
                previous = conn.execute(
                    "SELECT * FROM illustrations WHERE passage_id=?", (passage_id,)
                ).fetchone()
            archive_key = f"workflow/results/{result_id}/previous-page.png"
            archive_path = f"graphic_book/assets/generated/{passage_id.replace('.', '_')}/revisions/{result_id}/previous-page.png"
            with tempfile.TemporaryDirectory() as temporary:
                archive = Path(temporary) / "previous-page.png"
                self.store.download_verified(
                    previous["image_s3_key"],
                    archive,
                    previous["image_sha256"],
                    previous["byte_count"],
                )
                self.store.put_file(archive, archive_key)
            file_rows.append(
                (
                    result_id,
                    archive_path,
                    archive_key,
                    previous["image_sha256"],
                    previous["byte_count"],
                )
            )
        for path in sorted({path.resolve() for path in files}):
            relative = path.relative_to(ROOT).as_posix()
            if not relative.startswith("graphic_book/") or not path.is_file():
                raise ValueError(f"Result file must be inside graphic_book/: {path}")
            file_key = f"workflow/results/{result_id}/files/{relative}"
            self.store.put_file(path, file_key)
            file_rows.append(
                (result_id, relative, file_key, sha256_file(path), path.stat().st_size)
            )
        # Reading objects back verifies the transfer before this result becomes visible.
        with tempfile.TemporaryDirectory() as temporary:
            self.store.download_verified(
                key, Path(temporary) / "page.png", digest, size
            )
            for index, (_, _, file_key, file_digest, file_size) in enumerate(file_rows):
                self.store.download_verified(
                    file_key, Path(temporary) / str(index), file_digest, file_size
                )
        with snapshot_connection(self.path) as conn:
            self.owned_worker(conn)
            conn.execute(
                """INSERT INTO results
                (result_id,run_id,passage_id,kind,source_sha256,image_s3_key,image_sha256,
                 byte_count,original_sha256,source_commit,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    result_id,
                    self.token,
                    passage_id,
                    kind,
                    translation[0],
                    key,
                    digest,
                    size,
                    original_sha256,
                    source_commit,
                    utc_now(),
                ),
            )
            conn.executemany("INSERT INTO result_files VALUES (?,?,?,?,?)", file_rows)
            conn.execute(
                "INSERT OR REPLACE INTO illustrations VALUES (?,?,?,?,?,?)",
                (passage_id, key, digest, size, translation[0], result_id),
            )
        self.publish()
        return result_id

    def replacement_decision(
        self, passage_id: str | None, outcome: str | None
    ) -> float:
        """Persist one draw and target so retries cannot redraw or switch targets."""
        with snapshot_connection(self.path) as conn:
            worker = self.owned_worker(conn)
            row = conn.execute(
                "SELECT * FROM runs WHERE run_id=?", (worker["run_id"],)
            ).fetchone()
            if not row:
                raise ValueError("Replacement decisions require a generation run")
            draw = row["replacement_draw"]
            if draw is None:
                draw = random.SystemRandom().random()
            if passage_id and row["replacement_passage_id"] not in {None, passage_id}:
                raise ValueError("A replacement target has already been selected")
            conn.execute(
                "UPDATE runs SET replacement_draw=?,replacement_passage_id=COALESCE(?,replacement_passage_id),replacement_outcome=COALESCE(?,replacement_outcome) WHERE run_id=?",
                (draw, passage_id, outcome, self.token),
            )
        self.publish()
        return draw


def import_results(exchange: Exchange, pg) -> tuple[int, int]:
    """Import each immutable result once; never import corpus edits from SQLite."""
    accepted = rejected = 0
    with snapshot_connection(exchange.path) as snapshot:
        rows = snapshot.execute(
            "SELECT * FROM results WHERE import_status='pending' ORDER BY created_at,result_id"
        ).fetchall()
        for row in rows:
            old_result = pg.execute(
                "SELECT status,reason FROM graphic_book_results WHERE result_id=%s",
                (row["result_id"],),
            ).fetchone()
            if old_result:
                status, reason = old_result
            else:
                translation = pg.execute(
                    "SELECT p.passage,t.english_translation FROM passages p JOIN translations t ON t.passage_id=p.id WHERE p.id=%s FOR SHARE OF p,t",
                    (row["passage_id"],),
                ).fetchone()
                current = pg.execute(
                    "SELECT image_sha256 FROM graphic_book_pages WHERE passage_id=%s",
                    (row["passage_id"],),
                ).fetchone()
                reason = ""
                if not translation or source_hash(*translation) != row["source_sha256"]:
                    reason = "PostgreSQL source text changed after export"
                elif row["kind"] == "new" and current:
                    reason = "Passage already has an accepted image"
                elif row["kind"] == "replacement" and (
                    not current or current[0] != row["original_sha256"]
                ):
                    reason = "Original page changed after replacement was selected"
                file_rows = snapshot.execute(
                    "SELECT * FROM result_files WHERE result_id=?", (row["result_id"],)
                ).fetchall()
                if not reason:
                    with tempfile.TemporaryDirectory() as temporary:
                        image_path = Path(temporary) / "page.png"
                        exchange.store.download_verified(
                            row["image_s3_key"],
                            image_path,
                            row["image_sha256"],
                            row["byte_count"],
                        )
                        from PIL import Image

                        with Image.open(image_path) as page:
                            if page.format != "PNG":
                                raise ValueError("Result is not a PNG")
                            page.verify()
                        for index, file in enumerate(file_rows):
                            path = PurePosixPath(file["path"])
                            if (
                                path.is_absolute()
                                or ".." in path.parts
                                or not file["path"].startswith("graphic_book/")
                            ):
                                raise ValueError("Unsafe result-file path")
                            exchange.store.download_verified(
                                file["s3_key"],
                                Path(temporary) / str(index),
                                file["sha256"],
                                file["byte_count"],
                            )
                status = "rejected" if reason else "accepted"
                pg.execute(
                    """INSERT INTO graphic_book_results
                    (result_id,run_id,passage_id,kind,source_sha256,image_s3_key,image_sha256,
                     byte_count,original_sha256,source_commit,created_at,status,reason)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    tuple(
                        row[name]
                        for name in (
                            "result_id",
                            "run_id",
                            "passage_id",
                            "kind",
                            "source_sha256",
                            "image_s3_key",
                            "image_sha256",
                            "byte_count",
                            "original_sha256",
                            "source_commit",
                            "created_at",
                        )
                    )
                    + (status, reason),
                )
                for file in file_rows:
                    pg.execute(
                        "INSERT INTO graphic_book_result_files VALUES (%s,%s,%s,%s,%s)",
                        tuple(file),
                    )
                if status == "accepted":
                    pg.execute(
                        """INSERT INTO graphic_book_pages
                        (passage_id,image_s3_key,image_sha256,byte_count,source_sha256,result_id)
                        VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(passage_id) DO UPDATE SET
                        image_s3_key=EXCLUDED.image_s3_key,image_sha256=EXCLUDED.image_sha256,
                        byte_count=EXCLUDED.byte_count,source_sha256=EXCLUDED.source_sha256,
                        result_id=EXCLUDED.result_id,updated_at=CURRENT_TIMESTAMP""",
                        tuple(
                            row[name]
                            for name in (
                                "passage_id",
                                "image_s3_key",
                                "image_sha256",
                                "byte_count",
                                "source_sha256",
                                "result_id",
                            )
                        ),
                    )
            snapshot.execute(
                "UPDATE results SET import_status=?,import_reason=? WHERE result_id=?",
                (status, reason, row["result_id"]),
            )
            if status == "accepted":
                accepted += 1
            else:
                rejected += 1
                print(f"Rejected {row['passage_id']} ({row['result_id']}): {reason}")
    return accepted, rejected


def seed_existing_pages(exchange: Exchange, pg, image_dir: Path) -> int:
    """Register the existing image corpus once, preserving unknown text provenance."""
    from build_graphic_book import discover_images

    existing = {
        row[0] for row in pg.execute("SELECT passage_id FROM graphic_book_pages")
    }
    count = 0
    for passage_id, path in discover_images(image_dir).items():
        if passage_id in existing:
            continue
        if not pg.execute(
            "SELECT 1 FROM passages WHERE id=%s", (passage_id,)
        ).fetchone():
            raise ValueError(f"Image has no PostgreSQL passage: {passage_id}")
        key = f"images/{'/'.join(passage_id.split('.'))}.png"
        exchange.store.put_file(path, key)
        pg.execute(
            "INSERT INTO graphic_book_pages (passage_id,image_s3_key,image_sha256,byte_count) VALUES (%s,%s,%s,%s)",
            (passage_id, key, sha256_file(path), path.stat().st_size),
        )
        count += 1
        if count % 25 == 0:
            print(f"Registered {count} existing pages", flush=True)
    return count


def export_corpus(exchange: Exchange, pg) -> tuple[int, int]:
    """Refresh all corpus rows from PostgreSQL while retaining run/result history."""
    with snapshot_connection(exchange.path) as snapshot:
        passages = pg.execute("SELECT id,passage FROM passages").fetchall()
        for passage_id, greek in passages:
            if not PASSAGE_RE.fullmatch(passage_id):
                raise ValueError(f"Invalid PostgreSQL passage ID: {passage_id}")
            book, chapter, section = map(int, passage_id.split("."))
            snapshot.execute(
                "INSERT INTO passages VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET greek_text=excluded.greek_text",
                (passage_id, book, chapter, section, greek),
            )
        snapshot.execute("DELETE FROM translations")
        translations = pg.execute(
            "SELECT t.passage_id,p.passage,t.english_translation,t.timestamp,t.model FROM translations t JOIN passages p ON p.id=t.passage_id"
        ).fetchall()
        snapshot.executemany(
            "INSERT INTO translations VALUES (?,?,?,?,?,?)",
            [(*row, source_hash(row[1], row[2])) for row in translations],
        )
        snapshot.execute("DELETE FROM illustrations")
        pages = pg.execute(
            "SELECT passage_id,image_s3_key,image_sha256,byte_count,source_sha256,result_id FROM graphic_book_pages"
        ).fetchall()
        snapshot.executemany("INSERT INTO illustrations VALUES (?,?,?,?,?,?)", pages)
        snapshot.execute("UPDATE metadata SET exported_at=?", (utc_now(),))
    return len(passages), len(translations)


def sync_raksasa(exchange: Exchange, database_url: str | None, image_dir: Path) -> None:
    """Import, materialize pages, then export under the same shared ownership."""
    exchange.claim("raksasa", "raksasa", lease_seconds=3600)
    try:
        with connect(database_url) as pg:
            pg.execute((ROOT / "database/graphic_book_exchange.sql").read_text())
            pg.commit()
            with pg.transaction():
                pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                seeded = seed_existing_pages(exchange, pg, image_dir)
                accepted, rejected = import_results(exchange, pg)
                passages, translations = export_corpus(exchange, pg)
        # PostgreSQL commits first. A failed download can be retried from its
        # accepted page catalog even if the result was already imported.
        count = exchange.hydrate(image_dir)
        with snapshot_connection(exchange.path) as snapshot:
            for row in snapshot.execute(
                "SELECT * FROM illustrations WHERE result_id IS NOT NULL"
            ):
                canonical_key = f"images/{'/'.join(row['passage_id'].split('.'))}.png"
                page_path = image_dir.joinpath(
                    *row["passage_id"].split(".")
                ).with_suffix(".png")
                # Maintain the existing finished-page S3 backup contract.
                exchange.store.mirror_file(page_path, canonical_key)
        exchange.publish(release=True)
        print(
            f"Graphic book: imported {accepted}, rejected {rejected}, registered {seeded}; exported {passages} passages/{translations} translations; {count} pages ready",
            flush=True,
        )
    except Exception:
        try:
            exchange.abort(
                "Raksasa sync failed; PostgreSQL results may already be committed and are safe to retry"
            )
        except Exception as release_error:  # noqa: BLE001 - preserve the original failure
            print(f"Could not release failed sync claim: {release_error}")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--s3-uri",
        default=os.environ.get("PAUSANIAS_GRAPHIC_BOOK_S3_URI", DEFAULT_S3_URI),
    )
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    commands = parser.add_subparsers(dest="command", required=True)
    begin = commands.add_parser(
        "begin", help="Claim the shared snapshot before generating art"
    )
    begin.add_argument("--owner", default="daily-graphic-image")
    begin.add_argument("--lease-hours", type=float, default=6)
    commands.add_parser("renew", help="Renew/checkpoint a live session")
    commands.add_parser(
        "next", help="Print the next translated passage without an image"
    )
    hydrate = commands.add_parser(
        "hydrate", help="Download and verify accepted page images"
    )
    hydrate.add_argument("--image-dir", type=Path, default=ROOT / "graphic_book/images")
    record = commands.add_parser(
        "record-result", help="Upload a reviewed page and checkpoint its result"
    )
    record.add_argument("--passage", required=True)
    record.add_argument("--image", type=Path, required=True)
    record.add_argument("--kind", choices=["new", "replacement"], default="new")
    record.add_argument("--source-commit", required=True)
    record.add_argument("--original-sha256")
    record.add_argument("--file", type=Path, action="append", default=[])
    decision = commands.add_parser(
        "replacement-decision", help="Persist/reuse the optional replacement draw"
    )
    decision.add_argument("--passage")
    decision.add_argument("--outcome")
    finish = commands.add_parser(
        "finish", help="Publish completed results and clear this worker"
    )
    finish.add_argument("--notes", default="")
    abort = commands.add_parser(
        "abort", help="Clear our server claim while preserving checkpointed results"
    )
    abort.add_argument("--notes", default="")
    sync = commands.add_parser(
        "sync",
        help="Raksasa: import completed results, materialize pages, export corpus",
    )
    add_database_argument(sync)
    sync.add_argument(
        "--image-dir", type=Path, default=Path.home() / "pausanias-graphic-book/images"
    )
    commands.add_parser(
        "status", help="Inspect the S3 snapshot without taking ownership"
    )
    args = parser.parse_args()
    exchange = Exchange(S3Store(args.s3_uri), args.snapshot)
    try:
        if args.command == "begin":
            print(
                "Run:",
                exchange.claim(
                    args.owner, "cloud", lease_seconds=int(args.lease_hours * 3600)
                ),
            )
            print("Next passage:", exchange.next_passage())
        elif args.command == "renew":
            exchange.publish()
            print("Lease renewed")
        elif args.command == "next":
            print(exchange.next_passage() or "No translated passages remain")
        elif args.command == "hydrate":
            print("Verified pages:", exchange.hydrate(args.image_dir))
        elif args.command == "record-result":
            print(
                "Recorded result:",
                exchange.record_result(
                    args.passage,
                    args.image,
                    args.kind,
                    args.source_commit,
                    args.file,
                    args.original_sha256,
                ),
            )
        elif args.command == "replacement-decision":
            print(
                "Replacement draw:",
                exchange.replacement_decision(args.passage, args.outcome),
            )
        elif args.command == "finish":
            exchange.publish(release=True, notes=args.notes)
            print("Run completed and claim released")
        elif args.command == "abort":
            exchange.abort(args.notes)
            print("Claim released; checkpointed results retained")
        elif args.command == "sync":
            sync_raksasa(exchange, args.database_url, args.image_dir)
        elif args.command == "status":
            # Status cannot overwrite a working session's local checkout.
            with tempfile.TemporaryDirectory() as temporary:
                observer = Exchange(exchange.store, Path(temporary) / "corpus.sqlite")
                observer.fetch()
                with snapshot_connection(observer.path) as conn:
                    print(
                        "Metadata:",
                        dict(conn.execute("SELECT * FROM metadata").fetchone()),
                    )
                    print(
                        "Active:",
                        [
                            dict(row)
                            for row in conn.execute("SELECT * FROM active_worker")
                        ],
                    )
                    for table in (
                        "passages",
                        "translations",
                        "illustrations",
                        "results",
                    ):
                        print(
                            table,
                            conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0],
                        )
                print("Next passage:", observer.next_passage())
    except BusyError as exc:
        print(f"Skipped: {exc}")
        return 0 if args.command == "sync" else 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
