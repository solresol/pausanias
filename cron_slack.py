"""Send small daily-pipeline reports through a channel-specific Slack webhook."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def build_message(args: argparse.Namespace) -> dict:
    """Keep a stable job/run identity for a later daily completion monitor."""
    finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
    elapsed = max(0, int(time.time()) - args.started_at)
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
        check=False,
    ).stdout.strip() or "unknown"
    lines = [
        f"Pausanias daily pipeline — {args.status.upper()}",
        "job: pausanias-daily",
        f"run: {args.run_id}",
        f"host: {socket.gethostname()} | commit: {commit}",
        f"reported_at: {finished} | elapsed: {elapsed}s",
        f"stage: {args.stage} | exit_code: {args.exit_code}",
    ]
    if args.status == "succeeded":
        lines.append("Website published: https://pausanias.symmachus.org/")
    return {"text": "\n".join(lines), "mrkdwn": False}


def send_report(webhook_file: Path, payload: dict) -> None:
    """Send once with a bounded timeout; never print the webhook credential."""
    webhook = webhook_file.read_text().strip()
    parsed = urlsplit(webhook)
    if (parsed.scheme != "https" or parsed.netloc != "hooks.slack.com"
            or not parsed.path.startswith("/services/")):
        raise ValueError("Expected a Slack incoming webhook URL")
    request = Request(
        webhook, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urlopen(request, timeout=5) as response:
        if response.read(100).strip() != b"ok":
            raise ValueError("Slack did not acknowledge the report")


def main() -> int:
    """Allow a dry run without credentials or any pipeline/API work."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", choices=("started", "succeeded", "failed"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--started-at", type=int, required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument("--webhook-file", type=Path, default=Path(
        os.environ.get("PAUSANIAS_SLACK_WEBHOOK_FILE", "~/.config/pausanias/slack-webhook")
    ).expanduser())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    payload = build_message(args)
    if args.dry_run:
        print(payload["text"])
        return 0
    if not args.webhook_file.exists():
        # Optional until a webhook has been provisioned on the cron host.
        return 0
    try:
        send_report(args.webhook_file, payload)
    except HTTPError as exc:
        print(f"Slack report failed: HTTP {exc.code}", file=sys.stderr)
        return 1
    except (OSError, ValueError, URLError):
        print("Slack report failed: check webhook configuration or connectivity", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
