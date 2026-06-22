from tempfile import TemporaryDirectory
from pathlib import Path

from website.structure import create_website_structure


def test_grammar_token_table_css_stays_within_parent():
    with TemporaryDirectory() as tmpdir:
        create_website_structure(tmpdir)
        css = (Path(tmpdir) / "css" / "style.css").read_text(encoding="utf-8")

    assert ".grammar-table-wrap" in css
    assert "max-width: 100%;" in css
    assert "table-layout: fixed;" in css
    assert "overflow-wrap: anywhere;" in css
    assert "min-width: 760px;" in css
