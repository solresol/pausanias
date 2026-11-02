"""Exercise actual producer report expressions without calculations, SQL or APIs."""
import ast
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "cron_output.py"
LOG_ENV = "PAUSANIAS_ROUTINE_REPORT_LOG"

CLASSIFICATION = "              precision    recall  f1-score   support\n\n           0       0.82      0.77      0.79       163\n           1       0.88      0.91      0.89       294\n\n    accuracy                           0.86       457"


def signature(node):
    argument = node.args[0]
    if isinstance(argument, ast.Constant):return str(argument.value)
    if isinstance(argument, ast.JoinedStr):
        return "".join(part.value if isinstance(part, ast.Constant) else "{}" for part in argument.values)
    return ast.unparse(argument)


def report_nodes(relative):
    tree = ast.parse((ROOT / relative).read_text())
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name) and node.func.id == "routine_report"]


def predictor_fixture(relative):
    nodes = report_nodes(relative)
    wanted = ["Cleared existing predictor tables.", "\nBuilding mythicness prediction model...",
              "\n=== {} Model Evaluation ===", "classification_report(y_test, y_pred)",
              "\nTop predictors for NOT {}:", "  {}: {} ({}={}, non_{}={}, p={}, q={})"]
    selected = [next(node for node in nodes if signature(node) == text) for text in wanted]
    setup = (f"classification_report=lambda *a:{CLASSIFICATION!r}\ny_test=[]\ny_pred=[]\n"
             "feature_label='mythic'\nfeature='λέγω'\ncoef=-0.7142\ni=0\n"
             "pos_counts=[12]\nneg_counts=[3]\np_values=[0.001]\nq_values=[0.002]\n")
    return setup, selected


def fixture_code(setup, nodes, interactive_baseline=False):
    calls = []
    for node in nodes:
        expression = ast.unparse(node)
        if interactive_baseline:expression = expression.replace("routine_report(", "print(", 1)
        calls.append(expression)
    return f"import sys;sys.path.insert(0,{str(ROOT)!r})\nfrom cron_reporting import routine_report\n" + setup + "\n".join(calls)


def run_wrapped(tmp_path, code, quiet=True):
    log = tmp_path / "full.log"
    command = [sys.executable, str(RUNNER), "--log", str(log)]
    if quiet:command += ["--website-stats"]
    result = subprocess.run(command + ["--", sys.executable, "-c", code], capture_output=True, text=True)
    return result, log.read_text()


@pytest.mark.parametrize("relative", ["find_predictors.py", "find_sentence_predictors.py"])
def test_real_predictor_tables_are_logged_without_cron_email(tmp_path, relative):
    setup, nodes = predictor_fixture(relative)
    result, log = run_wrapped(tmp_path, fixture_code(setup, nodes))
    assert result.returncode == 0 and result.stdout == result.stderr == ""
    for text in ["Cleared existing predictor tables.", "Building mythicness prediction model...",
                 "=== Mythic Model Evaluation ===", CLASSIFICATION, "Top predictors for NOT mythic:",
                 "λέγω: -0.7142 (mythic=12, non_mythic=3, p=0.001, q=0.002)"]:
        assert text in log


@pytest.mark.parametrize("relative", ["find_predictors.py", "find_sentence_predictors.py"])
def test_real_predictor_reports_are_identical_interactively(relative):
    setup, nodes = predictor_fixture(relative)
    environment = os.environ.copy();environment.pop(LOG_ENV, None)
    actual = subprocess.run([sys.executable, "-c", fixture_code(setup, nodes)], capture_output=True, text=True, env=environment)
    baseline = subprocess.run([sys.executable, "-c", fixture_code(setup, nodes, True)], capture_output=True, text=True, env=environment)
    assert actual.returncode == baseline.returncode == 0
    assert actual.stdout == baseline.stdout and actual.stderr == baseline.stderr == ""


def test_actual_grammar_and_map_generation_summaries_are_quiet(tmp_path):
    nodes = report_nodes("website/generators.py")
    selected = [next(n for n in nodes if signature(n).startswith(prefix))
                for prefix in ["Grammar pages generated:", "Map page generated with"]]
    setup = "passages=range(3170)\ndata={'sentence_count':11302}\nmodel='gpt-5.6-luna'\nmap_data=range(1140)\n"
    result, log = run_wrapped(tmp_path, fixture_code(setup, selected))
    assert result.returncode == 0 and result.stdout == result.stderr == ""
    assert "Grammar pages generated: 3170 passages, 11302 sentences for gpt-5.6-luna." in log
    assert "Map page generated with 1140 places." in log


def test_unmarked_table_like_output_and_zero_exit_diagnostics_remain_visible(tmp_path):
    lines = ["Unexpected predictor state: investigate", "precision recall strange NEW FORMAT",
             "Fetched discourse-batch run x: 99/100 saved, 76080 tokens, 1 failures.",
             "Rejected 1.28.3 (x): hash mismatch", "x: completed but has no output file.",
             "Reached failure limit after 10 failed analyses; stopping before the next batch."]
    code = f"import sys;sys.path.insert(0,{str(ROOT)!r})\nfrom cron_reporting import routine_report\nroutine_report('routine private table')\nprint({chr(10).join(lines)!r})\nprint('Warning: retained stderr',file=sys.stderr)"
    result, log = run_wrapped(tmp_path, code)
    assert result.returncode == 0 and result.stdout == "\n".join(lines) + "\n"
    assert result.stderr == "Warning: retained stderr\n"
    assert "routine private table" in log and "routine private table" not in result.stdout
    assert all(line in log for line in lines)


def test_explicit_stderr_is_never_redirected_as_routine(tmp_path):
    code = f"import sys;sys.path.insert(0,{str(ROOT)!r})\nfrom cron_reporting import routine_report\nroutine_report('Warning: explicit stderr',file=sys.stderr)"
    result, log = run_wrapped(tmp_path, code)
    assert result.returncode == 0 and result.stderr == "Warning: explicit stderr\n"
    assert "Warning: explicit stderr" in log


def test_non_opted_in_wrapper_clears_an_inherited_routine_sink(tmp_path):
    code = f"import sys;sys.path.insert(0,{str(ROOT)!r})\nfrom cron_reporting import routine_report\nroutine_report('complete interactive model table')"
    log = tmp_path / "full.log";wrong = tmp_path / "wrong.log"
    result = subprocess.run([sys.executable, str(RUNNER), "--log", str(log), "--", sys.executable, "-c", code],
                            capture_output=True, text=True, env={**os.environ, LOG_ENV: str(wrong)})
    assert result.returncode == 0 and result.stdout == "complete interactive model table\n"
    assert not wrong.exists() and "complete interactive model table" in log.read_text()


def test_unavailable_sink_falls_back_visibly_without_changing_child_exit(tmp_path):
    code = f"import sys;sys.path.insert(0,{str(ROOT)!r})\nfrom cron_reporting import routine_report\nroutine_report('report retained on fallback')\nsys.exit(42)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            env={**os.environ, LOG_ENV: str(tmp_path / "missing" / "log")})
    assert result.returncode == 42 and result.stdout == "report retained on fallback\n"
    assert "Warning: private routine-report logging failed" in result.stderr


@pytest.mark.parametrize("sink_kind", ["public", "symlink", "directory"])
def test_unsafe_sink_cannot_silence_or_receive_reports(tmp_path, sink_kind):
    sink = tmp_path / "sink"
    original = "existing log\n"
    target = tmp_path / "target"
    target.write_text(original)
    target.chmod(0o600)
    if sink_kind == "public":
        sink.write_text(original)
        sink.chmod(0o644)
    elif sink_kind == "symlink":
        sink.symlink_to(target)
    else:
        sink.mkdir()
    code = f"import sys;sys.path.insert(0,{str(ROOT)!r})\nfrom cron_reporting import routine_report\nroutine_report('report must remain visible')"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            env={**os.environ, LOG_ENV: str(sink)})
    assert result.returncode == 0 and result.stdout == "report must remain visible\n"
    assert "Warning: private routine-report logging failed" in result.stderr
    assert target.read_text() == original
    if sink_kind == "public":assert sink.read_text() == original


def test_private_routine_report_does_not_mask_failure_exit(tmp_path):
    code = f"import sys;sys.path.insert(0,{str(ROOT)!r})\nfrom cron_reporting import routine_report\nroutine_report('normal model table')\nprint('Error: model artifact missing')\nsys.exit(42)"
    result, log = run_wrapped(tmp_path, code)
    assert result.returncode == 42 and result.stdout == "Error: model artifact missing\n"
    assert "exited 42" in result.stderr
    assert "normal model table" in log and "exit=42" in log


def test_actual_producer_alert_paths_remain_unmarked():
    expected = {"find_predictors.py": ["Not enough analyzed", "No cached Greek", "Error:"],
                "find_sentence_predictors.py": ["Not enough analyzed", "No cached Greek", "Error:"],
                "analyse_noun_network.py": ["Warning: Eigenvector", "Warning: Power iteration", "No proper nouns found", "No centrality data"],
                "website/main.py": ["No analyzed passages", "No passage-level predictor", "No sentence-level predictor", "Error:"]}
    for relative, prefixes in expected.items():
        calls = [n for n in ast.walk(ast.parse((ROOT / relative).read_text())) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id in ["print", "routine_report"]]
        for prefix in prefixes:
            matching = [node for node in calls if signature(node).strip().startswith(prefix)]
            assert matching and all(node.func.id == "print" for node in matching)
