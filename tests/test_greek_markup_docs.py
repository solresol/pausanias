from generate_greek_markup_docs import parse_passages


def test_parse_passages_collapses_source_line_wrapping():
    source = """#3.1.1#

first line
second---line

#3.1.2#
  third   line
"""

    assert parse_passages(source) == [
        ("3.1.1", "first line second\u2014line"),
        ("3.1.2", "third line"),
    ]
