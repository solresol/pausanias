from pathlib import Path
from tempfile import TemporaryDirectory

from website.generators import generate_progress_page


def test_generate_progress_page_renders_pipeline_status_details():
    progress_data = {
        "tasks": [
            {
                "name": "LLM grammar analysis",
                "area": "Grammar",
                "script": "sentence_llm_grammar_daily.sh",
                "cadence": "1M tokens/day, ~438/day",
                "done": 878,
                "total": 11302,
                "percent": 7.8,
                "status": "In progress",
                "est_completion": "2026-07-11",
                "details": "completed budget exhausted: 2",
            },
            {
                "name": "People/name analysis",
                "area": "Names and gender",
                "script": "section_people_daily.sh",
                "cadence": "Batch API, ~40 sections/day",
                "done": 40,
                "total": 3170,
                "percent": 1.3,
                "status": "In progress",
                "est_completion": "2026-09-04",
                "details": "completed: 1; 265 mention rows",
            },
            {
                "name": "Word-form lemmatization",
                "area": "Lemmas",
                "script": "word_lemmatizer.py",
                "cadence": "Batch API/ad hoc",
                "done": 28580,
                "total": None,
                "percent": None,
                "status": "Tracking",
                "est_completion": "n/a",
                "details": "batch in progress: 1",
            },
        ],
        "token_usage": [
            {
                "name": "LLM grammar",
                "input_tokens": 123,
                "output_tokens": 45,
                "total_tokens": 168,
            }
        ],
    }

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "site"
        generate_progress_page(progress_data, output_dir, "Pausanias")
        html = (output_dir / "progress" / "index.html").read_text(encoding="utf-8")

    assert "LLM grammar analysis" in html
    assert "People/name analysis" in html
    assert "Names and gender" in html
    assert "completed: 1; 265 mention rows" in html
    assert '<span class="progress-na">n/a</span>' in html
    assert "Batch API/ad hoc" in html
