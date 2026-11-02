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


COMPLETED_QUEUE = tuple(re.compile(pattern, re.I) for pattern in (
    r"No unsubmitted (?:sentence tagging|section people|passage place-state|greta-both-batch|greta-batch|discourse-batch) rows found\.",
    r"No unretrieved (?:sentence tagging|section people|passage place-state) Batch API runs found\.",
    r"No pending (?:passages|sentences|translations|summaries|proper nouns)(?: found\.| to process\.)",
    r"Found 0 proper nouns to process\.?",
    r"No untranslated passages found in the database\.",
    r"No unsplit passages found in the database\.",
    r"Found 0 passages to summarise\.?",
    r"No unprocessed LLM grammar rows found for [A-Za-z0-9_.:-]+/[A-Za-z0-9_.:-]+\.",
    r"0 failures\.?",
    r"rejected 0\.?",
))
WEBSITE_STATS = tuple(re.compile(pattern) for pattern in (
    re.escape("LLM translation enabled for missing phrase translations"),
    r"Found \d+ (?:analyzed passages|mythicness predictors|skepticism predictors|sentence-level mythicness predictors|sentence-level skepticism predictors)\.",
    re.escape("Adding phrase translations..."),
    r"Website generated successfully(?: in '[^'\r\n]+')?\.?",
    r"Open '[^'\r\n]+' in a web browser to view it\.",
    r"Website: \d+ passages, \d+ pages",
    r"Graphic book built in [A-Za-z0-9_./@:+-]+ with \d+ illustrated passages\.",
    r"(?:pausanias\.pdf|pausanias-greek\.pdf|pausanias-greek-markup\.pdf|pausanias-greek-markup\.docx|pausanias-greek-checklist\.pdf|pausanias-greek-english-parallel\.pdf) copied to website\.",
))


def forward_stdout(line, website_stats):
    """Quiet only complete known routine messages; unknown output stays visible.

    Classify the normal phrase-translation preamble before treating its word
    'missing' as a failure. There is no diagnostic latch: zero counters cannot
    turn subsequent website statistics into email, and positive failures,
    rejections, missing output and traceback lines are never in the allowlist.
    """
    if not line or any(pattern.fullmatch(line) for pattern in COMPLETED_QUEUE):
        return False
    if website_stats and any(pattern.fullmatch(line) for pattern in WEBSITE_STATS):
        return False
    return True


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
            for raw in iter(stream.readline, b""):
                line = raw.decode("utf-8", errors="replace").strip()
                show = is_stderr or forward_stdout(line, args.website_stats)
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
