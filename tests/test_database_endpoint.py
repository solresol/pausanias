from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from psycopg.conninfo import conninfo_to_dict
import pausanias_db as db


@pytest.fixture
def profile(tmp_path, monkeypatch):
    for key in ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PAUSANIAS_DATABASE_URL",
                "DATABASE_URL", "PAUSANIAS_DATABASE_EXPECTED_MAJOR"]:
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / "database.conf"
    path.write_text("DB_HOST=/var/run/postgresql\nDB_PORT=5433\nDB_NAME=pausanias\n"
                    "DB_USER=pausanias\nDB_EXPECTED_SERVER_MAJOR=18\n")
    monkeypatch.setenv("PAUSANIAS_DATABASE_CONFIG", str(path))
    return path


def test_profile_applies_to_legacy_name_only_wrapper(profile):
    values = conninfo_to_dict(db.get_database_url("dbname=pausanias"))
    assert values == {"host": "/var/run/postgresql", "port": "5433",
                      "dbname": "pausanias", "user": "pausanias"}


def test_explicit_fields_and_pg_environment_precedence(profile, monkeypatch):
    monkeypatch.setenv("PGPORT", "6543")
    monkeypatch.setenv("PAUSANIAS_DATABASE_URL", "dbname=env_name port=5434")
    assert conninfo_to_dict(db.get_database_url())["port"] == "5434"
    values = conninfo_to_dict(db.get_database_url("dbname=isolated user=gregb port=5433"))
    assert values["dbname"] == "isolated" and values["user"] == "gregb" and values["port"] == "5433"


def test_wrong_actual_server_fails_before_application_sql(profile, monkeypatch):
    conn = Mock()
    conn.info = SimpleNamespace(dbname="pausanias", user="pausanias", host="/var/run/postgresql",
                                port=5433, server_version=160015)
    monkeypatch.setattr(db.psycopg, "connect", lambda *a, **k: conn)
    with pytest.raises(RuntimeError, match="Refusing"):
        db.connect()
    conn.close.assert_called_once()
    conn.execute.assert_not_called()


def test_correct_actual_server_is_returned(profile, monkeypatch):
    conn = Mock()
    conn.info = SimpleNamespace(dbname="pausanias", user="pausanias", host="/var/run/postgresql",
                                port=5433, server_version=180006)
    monkeypatch.setattr(db.psycopg, "connect", lambda *a, **k: conn)
    assert db.connect() is conn


def test_missing_explicit_profile_and_secret_key_fail_closed(profile):
    profile.unlink()
    with pytest.raises(FileNotFoundError):db.get_database_url()
    profile.write_text("DB_PASSWORD=should-not-be-here\n")
    with pytest.raises(ValueError, match="non-secret"):db.get_database_url()
