from pathlib import Path
from tempfile import TemporaryDirectory

from website.data import get_stylometry_page_data
from website.generators import generate_stylometry_pages


def _token(order, form, lemma, upos, deprel, head="0", feats="_"):
    return {
        "token_order": order,
        "token_id": str(order),
        "form": form,
        "lemma": lemma,
        "upos": upos,
        "xpos": "_",
        "feats_raw": feats,
        "feats": None,
        "head_token_id": head,
        "deprel": deprel,
        "confidence": "high",
        "note": "",
    }


def _grammar_data():
    return {
        "model": "gpt-5.4-mini",
        "passages": [
            {
                "passage_id": "4.4.1",
                "book": 4,
                "chapter": 4,
                "section": 1,
                "sentences": [
                    {
                        "passage_id": "4.4.1",
                        "sentence_number": 1,
                        "greek_sentence": "οἱ Μεσσήνιοι μάχονται.",
                        "tokens": [
                            _token(1, "οἱ", "ὁ", "DET", "det", "2", "Case=Nom|Number=Plur"),
                            _token(2, "Μεσσήνιοι", "Μεσσήνιος", "NOUN", "nsubj", "3", "Case=Nom|Number=Plur"),
                            _token(3, "μάχονται", "μάχομαι", "VERB", "root", "0", "Mood=Ind|Tense=Pres"),
                        ],
                    }
                ],
            },
            {
                "passage_id": "1.1.1",
                "book": 1,
                "chapter": 1,
                "section": 1,
                "sentences": [
                    {
                        "passage_id": "1.1.1",
                        "sentence_number": 1,
                        "greek_sentence": "Ἀθηναῖοι λέγουσι λόγον.",
                        "tokens": [
                            _token(1, "Ἀθηναῖοι", "Ἀθηναῖος", "NOUN", "nsubj", "2", "Case=Nom|Number=Plur"),
                            _token(2, "λέγουσι", "λέγω", "VERB", "root", "0", "Mood=Ind|Tense=Pres"),
                            _token(3, "λόγον", "λόγος", "NOUN", "obj", "2", "Case=Acc|Number=Sing"),
                        ],
                    }
                ],
            },
        ],
    }


def test_stylometry_data_builds_morphosyntax_and_baselines():
    data = get_stylometry_page_data(grammar_data=_grammar_data())

    assert data["available"] is True
    assert data["model"] == "gpt-5.4-mini"
    assert data["metrics"]["passage_count"] == 2
    assert data["metrics"]["messenian_wars_count"] == 1

    feature_sets = {feature_set["id"]: feature_set for feature_set in data["feature_sets"]}
    assert set(feature_sets) == {"morphosyntax", "word_mfw", "char4gram"}
    assert "upos:VERB" in feature_sets["morphosyntax"]["features"]
    assert any(feature.startswith("word:") for feature in feature_sets["word_mfw"]["features"])
    assert any(feature.startswith("char4:") for feature in feature_sets["char4gram"]["features"])

    comparison = next(
        row
        for row in feature_sets["morphosyntax"]["comparisons"]
        if row["id"] == "messenian_wars"
    )
    assert comparison["available"] is True
    assert comparison["positive_count"] == 1
    assert comparison["negative_count"] == 1


def test_generates_stylometry_pages():
    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "site"
        (output_dir / "css").mkdir(parents=True)
        data = get_stylometry_page_data(grammar_data=_grammar_data())

        generate_stylometry_pages(data, output_dir, "Pausanias")

        index_html = (output_dir / "analysis" / "stylometry.html").read_text(encoding="utf-8")
        umap_html = (output_dir / "analysis" / "stylometry-umap.html").read_text(encoding="utf-8")
        stats_html = (output_dir / "analysis" / "stylometry-statistics.html").read_text(encoding="utf-8")

        assert "Morphosyntactic stylometry" in index_html
        assert "Traditional Word MFW" in index_html
        assert "gpt-5.4-mini" in index_html
        assert 'href="stylometry-umap.html"' in index_html
        assert "d3.v7.min.js" in umap_html
        assert "stylometry-data" in umap_html
        assert "Messenian Wars vs. Other Parsed Passages" in stats_html
        assert "../translation/4/4/1.html" in stats_html
