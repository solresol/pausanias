"""Report resolved non-secret database identity without executing application work."""
import json
from pausanias_db import connect


def main():
    with connect() as conn:
        print(json.dumps({"database": conn.info.dbname, "user": conn.info.user,
                          "host": conn.info.host, "port": conn.info.port,
                          "major": conn.info.server_version // 10000}))


if __name__ == "__main__":
    main()
