"""Batch subprocesses must resolve and guard the same endpoint as Python clients."""
import shlex
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo

import pausanias_psql as transport
import section_people_batch
import sentence_llm_grammar
import sentence_tag_batch


@pytest.fixture
def profile(tmp_path, monkeypatch):
    for key in ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PAUSANIAS_DATABASE_URL",
                "DATABASE_URL", "PAUSANIAS_DATABASE_EXPECTED_MAJOR"]:
        monkeypatch.delenv(key, raising=False)
    path = tmp_path/"database.conf"
    path.write_text("DB_HOST=/var/run/postgresql\nDB_PORT=5433\nDB_NAME=pausanias\n"
                    "DB_USER=pausanias\nDB_EXPECTED_SERVER_MAJOR=18\n")
    monkeypatch.setenv("PAUSANIAS_DATABASE_CONFIG", str(path))
    return path


@pytest.mark.parametrize("module", [sentence_tag_batch, sentence_llm_grammar, section_people_batch])
def test_every_batch_cli_name_only_dsn_uses_production_profile(module, profile, monkeypatch):
    assert module.PsqlRunner is transport.PsqlRunner
    monkeypatch.setattr("sys.argv", [module.__name__])
    args = module.parse_arguments()
    assert args.database_url is None
    runner = module.PsqlRunner("dbname=pausanias", psql_bin="psql", ssh_host=None)
    assert conninfo_to_dict(runner.database_url) == {
        "dbname": "pausanias", "user": "pausanias", "host": "/var/run/postgresql", "port": "5433"}


def test_guard_precedes_sql_in_same_psql_and_csv_stdout_is_unchanged(profile, monkeypatch):
    run = Mock(return_value=SimpleNamespace(returncode=0, stdout="name,n\na,1\n", stderr=""))
    monkeypatch.setattr(transport.subprocess, "run", run)
    runner = transport.PsqlRunner("dbname=pausanias")
    query = "COPY (SELECT 'a' AS name, 1 AS n) TO STDOUT WITH CSV HEADER;"
    assert runner.run(query) == "name,n\na,1\n"
    args, kwargs = run.call_args
    assert "-X" in args[0] and "-q" in args[0] and "ON_ERROR_STOP=1" in args[0]
    payload = kwargs["input"]
    assert payload.endswith(query) and payload.index("RAISE EXCEPTION") < payload.index("COPY")
    for check in ["current_database()", "current_user", "current_setting('port')",
                  "current_setting('server_version_num')", "inet_client_addr()", "5433", "18"]:
        assert check in payload
    run.assert_called_once()


def test_guard_failure_is_reported_without_retrying_or_new_connection(profile, monkeypatch, capsys):
    run = Mock(return_value=SimpleNamespace(returncode=3, stdout="", stderr="Refusing Pausanias SQL: endpoint mismatch"))
    monkeypatch.setattr(transport.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="exit code 3"):
        transport.PsqlRunner(None).run("SELECT 'application';")
    assert "Refusing" in capsys.readouterr().err
    run.assert_called_once()


def test_explicit_test_endpoint_and_pg_precedence_keep_major_guard(profile, monkeypatch):
    monkeypatch.setenv("PGPORT", "5432")
    inherited = transport.PsqlRunner("dbname=pausanias")
    assert conninfo_to_dict(inherited.database_url)["port"] == "5432"
    assert "FROM 18" in inherited.guard_sql  # A PG16 server cannot satisfy the guard.
    explicit = transport.PsqlRunner("dbname=isolated user=tester port=5433")
    assert conninfo_to_dict(explicit.database_url)["port"] == "5433"
    assert "'isolated'" in explicit.guard_sql and "'tester'" in explicit.guard_sql


def test_ssh_preserves_explicit_route_and_safe_argument_boundaries(profile):
    local = transport.PsqlRunner("dbname='odd name' password='private value'", psql_bin="/usr/bin/psql")
    remote = transport.PsqlRunner("dbname='odd name' password='private value'", psql_bin="/usr/bin/psql", ssh_host="raksasa")
    assert remote.command()[:2] == ["ssh", "raksasa"]
    assert shlex.split(remote.command()[2]) == local.command()
    assert "private value" not in remote.guard_sql
    assert "'odd name'" in remote.guard_sql


def test_malformed_profile_or_port_fails_before_subprocess(profile, monkeypatch):
    run = Mock();monkeypatch.setattr(transport.subprocess, "run", run)
    profile.write_text("DB_PASSWORD=not-allowed\n")
    with pytest.raises(ValueError, match="non-secret"):
        transport.PsqlRunner(None)
    run.assert_not_called()
    profile.write_text("DB_HOST=/var/run/postgresql\nDB_PORT=5433,5432\nDB_NAME=pausanias\n"
                       "DB_USER=pausanias\nDB_EXPECTED_SERVER_MAJOR=18\n")
    with pytest.raises(ValueError):transport.PsqlRunner(None)
    run.assert_not_called()


def test_sql_identity_literals_are_quoted(profile):
    runner = transport.PsqlRunner(make_conninfo(dbname="quoted'name"))
    assert "'quoted''name'" in runner.guard_sql
