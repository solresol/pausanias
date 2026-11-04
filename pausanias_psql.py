"""Profile-aware psql transport for batch tools, with guards before their SQL."""
from __future__ import annotations

import shlex
import subprocess
import sys

from psycopg import sql as sql_tools
from psycopg.conninfo import make_conninfo

from pausanias_db import resolved_database


def endpoint_guard_sql(values: dict[str, str], expected_major: int | None) -> str:
    """Check the actual server in the same psql connection as application SQL.

    The fully resolved DSN selects the socket path; Unix-socket routes also reject
    a TCP connection. An unconfigured development endpoint retains legacy behavior.
    """
    if expected_major is None:
        return ""
    port = int(values["port"])
    if not 1 <= port <= 65535:
        raise ValueError("Guarded Pausanias routing requires a single valid port")
    socket_check = sql_tools.SQL(" OR inet_client_addr() IS NOT NULL") if values["host"].startswith("/") else sql_tools.SQL("")
    return sql_tools.SQL("""DO $pausanias_endpoint_guard$
BEGIN
    IF current_database() IS DISTINCT FROM {database}
       OR current_user IS DISTINCT FROM {role}
       OR current_setting('port')::integer IS DISTINCT FROM {port}
       OR current_setting('server_version_num')::integer / 10000 IS DISTINCT FROM {major}{socket_check}
    THEN
        RAISE EXCEPTION 'Refusing Pausanias SQL: database/role/socket/port/version mismatch';
    END IF;
END
$pausanias_endpoint_guard$;
""").format(database=sql_tools.Literal(values["dbname"]), role=sql_tools.Literal(values["user"]),
             port=sql_tools.Literal(port), major=sql_tools.Literal(expected_major),
             socket_check=socket_check).as_string()


class PsqlRunner:
    """Use the shared DSN precedence for local and explicitly requested SSH routes."""

    def __init__(self, database_url: str | None, *, psql_bin: str = "psql", ssh_host: str | None = None):
        values, expected_major = resolved_database(database_url)
        self.database_url = make_conninfo(**values)
        self.psql_bin = psql_bin
        self.ssh_host = ssh_host
        self.guard_sql = endpoint_guard_sql(values, expected_major)

    def command(self) -> list[str]:
        # Ignore psqlrc and suppress command tags, including the guard's DO tag;
        # COPY CSV stdout and all actionable stderr keep their existing behavior.
        command = [self.psql_bin, "-X", "-q", self.database_url,
                   "-v", "ON_ERROR_STOP=1", "-P", "pager=off"]
        if not self.ssh_host:
            return command
        return ["ssh", self.ssh_host, shlex.join(command)]

    def run(self, sql: str) -> str:
        proc = subprocess.run(self.command(), input=self.guard_sql + sql,
                              text=True, encoding="utf-8", stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            raise RuntimeError(f"psql failed with exit code {proc.returncode}")
        return proc.stdout
