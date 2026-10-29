"""Exercise delivery failures and cron exit handling without running the pipeline."""

import importlib.util
import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cron_slack", ROOT / "cron_slack.py")
cron_slack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cron_slack)


def test_webhook_errors_do_not_expose_secret(tmp_path, monkeypatch, capsys):
    webhook = tmp_path / "webhook"
    webhook.write_text("https://hooks.slack.com/services/secret-value")

    def fail(*args, **kwargs):
        raise OSError("https://hooks.slack.com/services/secret-value")

    monkeypatch.setattr(cron_slack, "urlopen", fail)
    monkeypatch.setattr("sys.argv", [
        "cron_slack.py", "--status", "started", "--run-id", "test",
        "--started-at", "0", "--stage", "test", "--webhook-file", str(webhook),
    ])
    assert cron_slack.main() == 1
    output = capsys.readouterr()
    assert "secret-value" not in output.err + output.out


@pytest.mark.parametrize("failure,notify_failure,expected_stage", [
    ("", False, "publish"),
    ("find_predictors.py", False, "analysis"),
    ("rsync", False, "publish"),
    ("", True, "publish"),
    ("rsync", True, "publish"),
])
def test_cron_exit_status(tmp_path, failure, notify_failure, expected_stage):
    """Run the real shell control flow with every external pipeline command stubbed."""
    events = tmp_path / "events"
    stub = tmp_path / "stub"
    stub.write_text("""#!/bin/sh
printf '%s\\n' "$*" >> "$CRON_TEST_EVENTS"
if [ "$1" = cron_slack.py ]; then
  if [ "$CRON_TEST_NOTIFY_FAILURE" = yes ]; then exit 9; fi
elif [ "$1" = "$CRON_TEST_FAILURE" ]; then
  exit 42
fi
""")
    stub.chmod(0o755)
    script = (ROOT / "cronscript.sh").read_text()
    # Stub command boundaries only; preserve shell traps, stage changes and ordering.
    script = script.replace("uv run ", f"'{stub}' ")
    script = script.replace("git pull -q", f"'{stub}' checkout")
    script = script.replace("./sentence_tagging_daily.sh", f"'{stub}' tagging")
    script = script.replace("./sentence_llm_grammar_daily.sh", f"'{stub}' grammar")
    script = script.replace("./section_people_daily.sh", f"'{stub}' people")
    script = script.replace("./passage_place_state_daily.sh", f"'{stub}' places")
    script = script.replace("rsync -az", f"'{stub}' rsync -az")
    run_file = tmp_path / "cron.sh"
    run_file.write_text(script)
    result = subprocess.run(["sh", str(run_file)], capture_output=True, text=True, env={
        **os.environ, "CRON_TEST_EVENTS": str(events),
        "CRON_TEST_FAILURE": failure,
        "CRON_TEST_NOTIFY_FAILURE": "yes" if notify_failure else "no",
    })
    assert result.returncode == (42 if failure else 0)
    reports = [line for line in events.read_text().splitlines() if line.startswith("cron_slack.py")]
    assert len(reports) == 2
    assert "--status started" in reports[0]
    assert f"--status {'failed' if failure else 'succeeded'}" in reports[1]
    assert f"--stage {expected_stage}" in reports[1]
    if failure == "find_predictors.py":
        assert "rsync -az" not in events.read_text()
