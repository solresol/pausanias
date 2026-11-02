from pathlib import Path
import os
import signal
import subprocess
import sys
import time

import pytest

RUNNER = Path(__file__).resolve().parents[1] / "cron_output.py"


def run_step(tmp_path, code, quiet=False):
    log = tmp_path / "full.log"
    command = [sys.executable, str(RUNNER), "--log", str(log), "--stage", "test"]
    if quiet:command += ["--website-stats"]
    result = subprocess.run(command + ["--", sys.executable, "-c", code], capture_output=True, text=True)
    return result, log.read_text()


def test_website_stats_stay_in_full_log(tmp_path):
    result, log = run_step(tmp_path, "print('Website: 3940 passages, 200 pages')", quiet=True)
    assert result.returncode == 0 and not result.stdout and not result.stderr
    assert "3940 passages" in log


def test_stderr_and_zero_exit_failure_are_retained(tmp_path):
    result, log = run_step(tmp_path, "import sys;print('Failures: 2');print('remote warning',file=sys.stderr)", quiet=True)
    assert result.returncode == 0
    assert "Failures: 2" in result.stdout and "remote warning" in result.stderr
    assert "Failures: 2" in log and "remote warning" in log


def test_completed_queue_quiet_but_new_work_and_missing_key_visible(tmp_path):
    result, log = run_step(tmp_path, "print('No unretrieved section people Batch API runs found.');print('Submitted batch: original-id');print('No OpenAI API key found')")
    assert "No unretrieved" not in result.stdout and "No unretrieved" in log
    assert "original-id" in result.stdout and "API key" in result.stdout


def test_real_failure_status_is_preserved(tmp_path):
    result, log = run_step(tmp_path, "import sys;print('routine site counts');print('real error',file=sys.stderr);sys.exit(42)", quiet=True)
    assert result.returncode == 42
    assert "real error" in result.stderr and "exited 42" in result.stderr
    assert "routine site counts" in log


EMPTY_QUEUE_FIXTURES = [
    "Found 0 proper nouns to process",
    "No untranslated passages found in the database.",
    "No unsplit passages found in the database.",
    "Found 0 passages to summarise",
    "No unsubmitted greta-both-batch rows found.",
    "No unsubmitted greta-batch rows found.",
    "No unprocessed LLM grammar rows found for gpt-5.6-luna/greek-sentence-grammar-v1.",
]
WEBSITE_FIXTURES = [
    "LLM translation enabled for missing phrase translations",
    "Found 3170 analyzed passages.",
    "Found 60 mythicness predictors.",
    "Adding phrase translations...",
    "Website generated successfully",
]
ZERO_EXIT_FAILURE_FIXTURES = [
    "Fetched discourse-batch run x: 99/100 saved, 76080 tokens, 1 failures.",
    "Rejected 1.28.3 (x): hash mismatch",
    "x: completed but has no output file.",
    "Reached failure limit after 10 failed analyses; stopping before the next batch.",
]


@pytest.mark.parametrize("line", EMPTY_QUEUE_FIXTURES)
@pytest.mark.parametrize("quiet", [False, True])
def test_real_completed_queues_are_quiet_and_logged(tmp_path, line, quiet):
    result, log = run_step(tmp_path, f"print({line!r})", quiet=quiet)
    assert result.returncode == 0 and result.stdout == result.stderr == ""
    assert line in log
    assert (tmp_path / "full.log").stat().st_mode & 0o777 == 0o600


def test_consecutive_website_preamble_and_statistics_do_not_leak(tmp_path):
    result, log = run_step(tmp_path, f"print({chr(10).join(WEBSITE_FIXTURES)!r})", quiet=True)
    assert result.returncode == 0 and result.stdout == result.stderr == ""
    assert all(line in log for line in WEBSITE_FIXTURES)


@pytest.mark.parametrize("line", ZERO_EXIT_FAILURE_FIXTURES)
@pytest.mark.parametrize("quiet", [False, True])
def test_real_zero_exit_failures_remain_visible(tmp_path, line, quiet):
    result, log = run_step(tmp_path, f"print({line!r})", quiet=quiet)
    assert result.returncode == 0 and result.stdout == line + "\n"
    assert line in log


def test_zero_counters_cannot_latch_later_statistics(tmp_path):
    lines = ["0 failures", WEBSITE_FIXTURES[1], "rejected 0", WEBSITE_FIXTURES[2]]
    result, log = run_step(tmp_path, f"print({chr(10).join(lines)!r})", quiet=True)
    assert result.returncode == 0 and result.stdout == result.stderr == ""
    assert all(line in log for line in lines)


def test_unknown_output_and_unrecognized_missing_messages_fail_visible(tmp_path):
    lines = ["Unexpected worker state: needs attention", "Missing translation payload",
             "No API key found in the database.", "Found 1 unexpected result.",
             "LLM translation failed for missing phrase translations",
             "No untranslated passages found in the database. Warning: source unavailable",
             "Website generated successfully in '/tmp/out' but missing artifact 'index.html'",
             "Graphic book built in /tmp/out, missing input with 10 illustrated passages.",
             "Submitted batch: original-id"]
    result, log = run_step(tmp_path, f"print({chr(10).join(lines)!r})", quiet=True)
    assert result.returncode == 0 and result.stdout == "\n".join(lines) + "\n"
    assert all(line in log for line in lines)


def test_all_stderr_survives_even_when_text_looks_routine(tmp_path):
    text = EMPTY_QUEUE_FIXTURES[0] + "\nworker note\nWarning: retained stderr\n"
    result, log = run_step(tmp_path, f"import sys;sys.stderr.write({text!r})", quiet=True)
    assert result.returncode == 0 and result.stderr == text
    assert text in log


@pytest.mark.parametrize("signum", [signal.SIGHUP, signal.SIGINT, signal.SIGTERM])
def test_child_signal_exit_status_is_preserved(tmp_path, signum):
    code = f"import os,signal;signal.signal({signum},signal.SIG_DFL);os.kill(os.getpid(),{signum})"
    result, log = run_step(tmp_path, code, quiet=True)
    assert result.returncode == 128 + signum
    assert f"exit={128 + signum}" in log


@pytest.mark.parametrize("signum", [signal.SIGHUP, signal.SIGINT, signal.SIGTERM])
def test_wrapper_forwards_signal_to_its_own_child_group(tmp_path, signum):
    marker = tmp_path / "child.pid"
    log = tmp_path / "full.log"
    code = f"import os,time;from pathlib import Path;Path({str(marker)!r}).write_text(str(os.getpid()));time.sleep(30)"
    proc = subprocess.Popen([sys.executable, str(RUNNER), "--log", str(log), "--website-stats",
                             "--", sys.executable, "-c", code], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    child_pid = None
    try:
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert marker.exists(), "Test child did not start"
        child_pid = int(marker.read_text())
        proc.send_signal(signum)
        _, stderr = proc.communicate(timeout=5)
        assert proc.returncode == 128 + signum
        assert f"exited {128 + signum}" in stderr
        assert f"exit={128 + signum}" in log.read_text()
    finally:
        if proc.poll() is None:
            # Only the uniquely identified fake child created by this test is cleaned up.
            if child_pid is not None:
                try:os.killpg(child_pid, signal.SIGKILL)
                except ProcessLookupError:pass
            proc.kill()
            proc.communicate(timeout=5)
