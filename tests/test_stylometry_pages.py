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
                        "greek_sentence": "Μεσσήνιοι πολεμοῦσιν.",
                        "tokens": [
                            _token(1, "Μεσσήνιοι", "Μεσσήνιος", "PROPN", "nsubj", "2", "Case=Nom|Number=Plur"),
                            _token(2, "πολεμοῦσιν", "πολεμέω", "VERB", "root", "0", "Mood=Ind|Tense=Pres"),
                        ],
                    }
                ],
            },
            {
                "passage_id": "5.1.1",
                "book": 5,
                "chapter": 1,
                "section": 1,
                "sentences": [
                    {
                        "passage_id": "5.1.1",
                        "sentence_number": 1,
                        "greek_sentence": "Ἠλεῖοι θύουσιν.",
                        "tokens": [
                            _token(1, "Ἠλεῖοι", "Ἠλεῖος", "PROPN", "nsubj", "2", "Case=Nom|Number=Plur"),
                            _token(2, "θύουσιν", "θύω", "VERB", "root", "0", "Mood=Ind|Tense=Pres"),
                        ],
                    }
                ],
            },
        ],
    }


def test_get_stylometry_page_data_builds_feature_families_and_comparisons():
    data = get_stylometry_page_data(grammar_data=_grammar_data())

    assert data["available"] is True
    assert data["model"] == "gpt-5.4-mini"
    assert data["metrics"]["passage_count"] == 2
    assert data["metrics"]["messenian_wars_count"] == 1

    feature_set_ids = {feature_set["id"] for feature_set in data["feature_sets"]}
    assert {"morphosyntax", "word_mfw", "char4gram"} <= feature_set_ids

    morphosyntax = next(
        feature_set for feature_set in data["feature_sets"] if feature_set["id"] == "morphosyntax"
    )
    assert any(feature.startswith("upos:") for feature in morphosyntax["features"])
    messenian = next(
        comparison
        for comparison in morphosyntax["comparisons"]
        if comparison["id"] == "messenian_wars"
    )
    assert messenian["available"] is True
    assert len(morphosyntax["points"]) == 2


def test_generate_stylometry_pages_writes_interactive_and_statistics_pages():
    data = get_stylometry_page_data(grammar_data=_grammar_data())

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "site"
        (output_dir / "css").mkdir(parents=True)

        generate_stylometry_pages(data, output_dir, "Pausanias")

        index_html = (output_dir / "analysis" / "stylometry.html").read_text(encoding="utf-8")
        umap_html = (output_dir / "analysis" / "stylometry-umap.html").read_text(encoding="utf-8")
        stats_html = (output_dir / "analysis" / "stylometry-statistics.html").read_text(encoding="utf-8")

        assert "Morphosyntactic stylometry" in index_html
        assert "Traditional Word MFW" in index_html
        assert "d3.v7.min.js" in umap_html
        assert "stylometry-data" in umap_html
        assert "Messenian Wars vs. Other Parsed Passages" in stats_html
        assert "../translation/4/4/1.html" in stats_html
