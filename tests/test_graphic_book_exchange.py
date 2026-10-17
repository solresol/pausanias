"""Exercise concurrency and recovery using the same conditional-write API as S3."""

import hashlib
import os
from io import BytesIO

import pytest
from botocore.exceptions import ClientError
from PIL import Image

from graphic_book_corpus import load_translation, snapshot_path
from graphic_book_exchange import (
    ROOT,
    BusyError,
    ConflictError,
    Exchange,
    S3Store,
    snapshot_connection,
    source_hash,
)


class MemoryS3:
    def __init__(self):
        self.objects = {}
        self.metadata = {}

    def get_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        body = self.objects[Key]
        return {"Body": BytesIO(body), "ETag": self.etag(body)}

    @staticmethod
    def etag(body):
        return '"' + hashlib.sha256(body).hexdigest() + '"'

    def put_object(
        self, *, Bucket, Key, Body, IfMatch=None, IfNoneMatch=None, **kwargs
    ):
        old = self.objects.get(Key)
        if (IfNoneMatch == "*" and old is not None) or (
            IfMatch is not None and (old is None or self.etag(old) != IfMatch)
        ):
            raise ClientError({"Error": {"Code": "PreconditionFailed"}}, "PutObject")
        data = Body.read() if hasattr(Body, "read") else Body
        self.objects[Key] = data
        self.metadata[Key] = kwargs.get("Metadata", {})
        return {"ETag": self.etag(data)}

    def head_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return {"Metadata": self.metadata[Key], "ContentLength": len(self.objects[Key])}


@pytest.fixture
def setup_exchange(tmp_path):
    client = MemoryS3()
    store = S3Store("s3://test/prefix", client)
    clock = [1000]
    exporter = Exchange(store, tmp_path / "export.sqlite", clock=lambda: clock[0])
    exporter.claim("raksasa", "raksasa")
    with snapshot_connection(exporter.path) as conn:
        for passage in ("1.2.9", "1.2.10", "1.3.1"):
            book, chapter, section = map(int, passage.split("."))
            greek, english = "Ἀθῆναι\n", f"Translation {passage}\nSecond line.  "
            conn.execute(
                "INSERT INTO passages VALUES (?,?,?,?,?)",
                (passage, book, chapter, section, greek),
            )
            conn.execute(
                "INSERT INTO translations VALUES (?,?,?,?,?,?)",
                (passage, greek, english, "now", "test", source_hash(greek, english)),
            )
        conn.execute("UPDATE metadata SET exported_at='2026-10-17T00:00:00+00:00'")
    exporter.publish(release=True)
    return store, tmp_path, clock


def worker(setup_exchange, name="worker"):
    store, path, clock = setup_exchange
    return Exchange(store, path / f"{name}.sqlite", clock=lambda: clock[0])


def png(path, color="white"):
    Image.new("RGB", (80, 60), color).save(path)
    return path


def test_only_one_of_two_workers_with_same_download_can_claim(setup_exchange):
    first, second = worker(setup_exchange, "first"), worker(setup_exchange, "second")
    second.fetch()
    second.fetch = lambda **kwargs: None
    first.claim("first", "cloud")
    with pytest.raises(ConflictError):
        second.claim("second", "cloud")
    assert not second.session_path.exists()
    observer = worker(setup_exchange, "observer")
    observer.fetch()
    with snapshot_connection(observer.path) as conn:
        assert conn.execute("SELECT owner FROM active_worker").fetchone()[0] == "first"


def test_active_claim_aborts_before_any_work(setup_exchange):
    first = worker(setup_exchange, "first")
    first.claim("first", "cloud")
    before = setup_exchange[0].client.objects.copy()
    with pytest.raises(BusyError):
        worker(setup_exchange, "second").claim("second", "raksasa")
    assert setup_exchange[0].client.objects == before


def test_expired_worker_cannot_overwrite_successor(setup_exchange):
    first = worker(setup_exchange, "first")
    first.claim("first", "cloud", lease_seconds=10)
    setup_exchange[2][0] += 11
    successor = worker(setup_exchange, "successor")
    successor.claim("successor", "cloud")
    # Even a stalled worker with an incorrect clock cannot overwrite a takeover.
    first.clock = lambda: 1001
    with pytest.raises(ConflictError):
        first.publish(release=True)
    observer = worker(setup_exchange, "observer")
    observer.fetch()
    with snapshot_connection(observer.path) as conn:
        assert (
            conn.execute("SELECT owner FROM active_worker").fetchone()[0] == "successor"
        )


def test_expired_lease_fails_without_takeover(setup_exchange):
    current = worker(setup_exchange)
    current.claim("worker", "cloud", lease_seconds=10)
    setup_exchange[2][0] += 11
    with pytest.raises(ConflictError, match="expired"):
        current.publish()


def test_new_page_selection_is_numeric_and_uses_catalog(setup_exchange):
    current = worker(setup_exchange)
    current.claim("worker", "cloud")
    assert current.next_passage() == "1.2.9"
    current.record_result(
        "1.2.9", png(current.path.parent / "page.png"), "new", "a" * 40, []
    )
    assert current.next_passage() == "1.2.10"
    with pytest.raises(ValueError, match="already contains"):
        current.record_result(
            "1.2.10", png(current.path.parent / "second.png"), "new", "a" * 40, []
        )


def test_abort_retains_checkpointed_page_and_releases_owner(setup_exchange):
    current = worker(setup_exchange)
    current.claim("worker", "cloud")
    result_id = current.record_result(
        "1.2.9", png(current.path.parent / "page.png"), "new", "b" * 40, []
    )
    current.abort("optional replacement failed")
    assert not current.session_path.exists()
    observer = worker(setup_exchange, "observer")
    observer.fetch()
    with snapshot_connection(observer.path) as conn:
        assert conn.execute("SELECT count(*) FROM active_worker").fetchone()[0] == 0
        assert conn.execute("SELECT result_id FROM results").fetchone()[0] == result_id
        assert conn.execute("SELECT status FROM runs").fetchone()[0] == "aborted"


def test_replacement_archives_original_and_rejects_wrong_original(setup_exchange):
    current = worker(setup_exchange)
    current.claim("worker", "cloud")
    current.record_result(
        "1.2.9", png(current.path.parent / "page.png"), "new", "b" * 40, []
    )
    with snapshot_connection(current.path) as conn:
        old = conn.execute("SELECT image_sha256 FROM illustrations").fetchone()[0]
    current.publish(release=True)
    current = worker(setup_exchange, "replacement-worker")
    current.claim("replacement-worker", "cloud")
    replacement = png(current.path.parent / "replacement.png", "blue")
    with pytest.raises(ValueError, match="original checksum"):
        current.record_result(
            "1.2.9", replacement, "replacement", "c" * 40, [], "0" * 64
        )
    result_id = current.record_result(
        "1.2.9", replacement, "replacement", "c" * 40, [], old
    )
    with snapshot_connection(current.path) as conn:
        archived = conn.execute(
            "SELECT * FROM result_files WHERE result_id=?", (result_id,)
        ).fetchone()
        assert archived["sha256"] == old
        assert archived["path"].endswith("previous-page.png")


def test_replacement_draw_and_target_are_reused(setup_exchange):
    current = worker(setup_exchange)
    current.claim("worker", "cloud")
    draw = current.replacement_decision("1.2.9", None)
    assert current.replacement_decision(None, "pending") == draw
    with pytest.raises(ValueError, match="already been selected"):
        current.replacement_decision("1.2.10", None)


def test_corpus_reader_preserves_exact_unicode_and_whitespace(
    setup_exchange, monkeypatch
):
    current = worker(setup_exchange)
    current.fetch()
    monkeypatch.setenv("PAUSANIAS_GRAPHIC_BOOK_SNAPSHOT", str(current.path))
    assert load_translation("1.2.9") == "Translation 1.2.9\nSecond line.  "
    assert source_hash("Ἀθῆναι\n", "text") != source_hash("Ἀθῆναι", "text")


def test_corpus_reader_rejects_legacy_database(monkeypatch):
    monkeypatch.setenv(
        "PAUSANIAS_GRAPHIC_BOOK_SNAPSHOT", str(ROOT / "pausanias.sqlite")
    )
    with pytest.raises(RuntimeError, match="legacy"):
        snapshot_path()


def test_missing_snapshot_does_not_create_an_empty_file(tmp_path, monkeypatch):
    path = tmp_path / "missing.sqlite"
    monkeypatch.setenv("PAUSANIAS_GRAPHIC_BOOK_SNAPSHOT", str(path))
    with pytest.raises(RuntimeError, match="Missing corpus"):
        snapshot_path()
    assert not path.exists()


def test_artifact_corruption_never_replaces_accepted_file(setup_exchange):
    store, path, _ = setup_exchange
    accepted = path / "accepted.png"
    accepted.write_bytes(b"previous accepted image")
    store.client.objects[store.key("bad.png")] = b"corrupt"
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        store.download_verified("bad.png", accepted, "0" * 64, 7)
    assert accepted.read_bytes() == b"previous accepted image"


def test_generation_changes_even_when_claim_is_cleared(setup_exchange):
    first = worker(setup_exchange, "first")
    first.fetch()
    old_etag = first.etag
    first.claim("first", "cloud")
    first.publish(release=True)
    first.fetch()
    assert first.etag != old_etag


def test_live_renderers_cannot_open_legacy_database():
    for path in (ROOT / "graphic_book").glob("render_passage_*.py"):
        assert "pausanias.sqlite" not in path.read_text(), path


@pytest.fixture
def pg():
    """Use only session-local temporary tables on an explicitly selected server."""
    database_url = os.environ.get("PAUSANIAS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Set PAUSANIAS_TEST_DATABASE_URL to run PostgreSQL integration checks"
        )
    from pausanias_db import connect

    with connect(database_url) as connection:
        connection.execute(
            "CREATE TEMP TABLE passages (id TEXT PRIMARY KEY,passage TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TEMP TABLE translations (passage_id TEXT PRIMARY KEY REFERENCES passages(id),english_translation TEXT NOT NULL,timestamp TEXT NOT NULL,model TEXT NOT NULL)"
        )
        connection.execute(
            (ROOT / "database/graphic_book_exchange.sql")
            .read_text()
            .replace("CREATE TABLE IF NOT EXISTS", "CREATE TEMP TABLE")
        )
        for passage in ("1.2.9", "1.2.10", "1.3.1"):
            connection.execute(
                "INSERT INTO passages VALUES (%s,%s)", (passage, "Ἀθῆναι\n")
            )
            connection.execute(
                "INSERT INTO translations VALUES (%s,%s,'now','test')",
                (passage, f"Translation {passage}\nSecond line.  "),
            )
        yield connection


def test_postgres_import_is_idempotent_and_exports_entire_corpus(setup_exchange, pg):
    from graphic_book_exchange import export_corpus, import_results

    current = worker(setup_exchange)
    current.claim("worker", "cloud")
    current.record_result(
        "1.2.9", png(current.path.parent / "page.png"), "new", "a" * 40, []
    )
    current.publish(release=True)
    importer = worker(setup_exchange, "importer")
    importer.claim("raksasa", "raksasa")
    assert import_results(importer, pg) == (1, 0)
    assert import_results(importer, pg) == (0, 0)
    assert pg.execute("SELECT count(*) FROM graphic_book_results").fetchone()[0] == 1
    assert pg.execute("SELECT count(*) FROM graphic_book_pages").fetchone()[0] == 1
    assert export_corpus(importer, pg) == (3, 3)
    assert importer.next_passage() == "1.2.10"


def test_postgres_rejects_changed_translation_and_keeps_previous_page(
    setup_exchange, pg
):
    from graphic_book_exchange import import_results

    current = worker(setup_exchange)
    current.claim("worker", "cloud")
    current.record_result(
        "1.2.9", png(current.path.parent / "page.png"), "new", "a" * 40, []
    )
    current.publish(release=True)
    pg.execute(
        "UPDATE translations SET english_translation='New corrected translation' WHERE passage_id='1.2.9'"
    )
    importer = worker(setup_exchange, "importer")
    importer.claim("raksasa", "raksasa")
    assert import_results(importer, pg) == (0, 1)
    assert pg.execute("SELECT count(*) FROM graphic_book_pages").fetchone()[0] == 0
    assert (
        pg.execute(
            "SELECT english_translation FROM translations WHERE passage_id='1.2.9'"
        ).fetchone()[0]
        == "New corrected translation"
    )
    assert import_results(importer, pg) == (0, 0)


def test_postgres_checks_artifacts_before_accepting_results(setup_exchange, pg):
    from graphic_book_exchange import import_results

    current = worker(setup_exchange)
    current.claim("worker", "cloud")
    current.record_result(
        "1.2.9", png(current.path.parent / "page.png"), "new", "a" * 40, []
    )
    current.publish(release=True)
    with snapshot_connection(current.path) as conn:
        key = conn.execute("SELECT image_s3_key FROM results").fetchone()[0]
    current.store.client.objects[current.store.key(key)] = b"corrupt page"
    importer = worker(setup_exchange, "importer")
    importer.claim("raksasa", "raksasa")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        import_results(importer, pg)
    assert pg.execute("SELECT count(*) FROM graphic_book_results").fetchone()[0] == 0


def test_postgres_recovers_when_prior_commit_preceded_snapshot_upload(
    setup_exchange, pg
):
    from graphic_book_exchange import import_results

    current = worker(setup_exchange)
    current.claim("worker", "cloud")
    current.record_result(
        "1.2.9", png(current.path.parent / "page.png"), "new", "a" * 40, []
    )
    current.publish(release=True)
    importer = worker(setup_exchange, "importer")
    importer.claim("raksasa", "raksasa")
    assert import_results(importer, pg) == (1, 0)
    # Simulate the next worker downloading the still-unacknowledged S3 copy.
    with snapshot_connection(importer.path) as conn:
        conn.execute("UPDATE results SET import_status='pending'")
    assert import_results(importer, pg) == (1, 0)
    assert pg.execute("SELECT count(*) FROM graphic_book_results").fetchone()[0] == 1
