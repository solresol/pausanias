from pathlib import Path
import subprocess
import sys

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
