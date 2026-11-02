"""Keep private full step logs while forwarding actionable cron output unchanged."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading


ACTIONABLE = re.compile(r"warning|error|fail(?:ed|ure)?|exception|traceback|reject|missing|cannot|could not|unable|not found|not configured|no .*api.*key", re.I)
COMPLETED_QUEUE = re.compile(
    r"^No (?:unsubmitted (?:sentence tagging|section people|passage place-state) rows found\.|"
    r"unretrieved (?:sentence tagging|section people|passage place-state) Batch API runs found\.|"
    r"pending (?:passages|sentences|translations|summaries|proper nouns)(?: found\.| to process\.))$",
    re.I,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--stage", default="pipeline")
    parser.add_argument("--website-stats", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("A command is required")
    args.log.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = threading.Lock()
    with args.log.open("ab") as log:
        os.fchmod(log.fileno(), 0o600)
        log.write(f"\n[{datetime.now(timezone.utc).isoformat()}] stage={args.stage}\n".encode())
        log.flush()
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 start_new_session=True)

        def forward(signum, _frame):
            try:
                os.killpg(child.pid, signum)
            except ProcessLookupError:
                pass

        previous = {sig: signal.signal(sig, forward) for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP]}

        def drain(stream, is_stderr):
            diagnostic_block = False
            for raw in iter(stream.readline, b""):
                line = raw.decode("utf-8", errors="replace").strip()
                diagnostic = bool(ACTIONABLE.search(line))
                if diagnostic:
                    diagnostic_block = True
                elif not line:
                    diagnostic_block = False
                show = is_stderr or diagnostic or diagnostic_block or (
                    not args.website_stats and not COMPLETED_QUEUE.fullmatch(line)
                )
                with lock:
                    log.write(raw)
                    log.flush()
                    if show:
                        target = sys.stderr.buffer if is_stderr else sys.stdout.buffer
                        target.write(raw)
                        target.flush()
            stream.close()

        threads = [threading.Thread(target=drain, args=(child.stdout, False)),
                   threading.Thread(target=drain, args=(child.stderr, True))]
        try:
            for thread in threads:thread.start()
            status = child.wait()
            for thread in threads:thread.join()
        finally:
            for sig, handler in previous.items():signal.signal(sig, handler)
        code = status if status >= 0 else 128 - status
        log.write(f"[{datetime.now(timezone.utc).isoformat()}] stage={args.stage} exit={code}\n".encode())
        if code:
            print(f"Pausanias {args.stage} exited {code}; full log: {args.log}", file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
