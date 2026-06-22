from pathlib import Path
from tempfile import TemporaryDirectory

from website.data import get_stylometry_page_data
from website.data import get_discourse_mode_aorist_analysis
from website.data import get_stylometric_book_feature_trend_data
from website.data import get_stylometric_sentence_model_data
from website.generators import generate_discourse_mode_aorist_page
from website.generators import generate_stylometric_book_feature_trend_page
from website.generators import generate_stylometric_sentence_model_pages
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


def _sentence_model_grammar_data():
    passages = []
    feature_templates = [
        [
            _token(1, "οἱ", "ὁ", "DET", "det", "2", "Case=Nom|Number=Plur"),
            _token(2, "θεοί", "θεός", "NOUN", "nsubj", "3", "Case=Nom|Number=Plur"),
            _token(3, "λέγουσι", "λέγω", "VERB", "root", "0", "Mood=Ind|Tense=Pres"),
        ],
        [
            _token(1, "ἐν", "ἐν", "ADP", "case", "2", "_"),
            _token(2, "πόλει", "πόλις", "NOUN", "obl", "3", "Case=Dat|Number=Sing"),
            _token(3, "ἐμάχοντο", "μάχομαι", "VERB", "root", "0", "Mood=Ind|Tense=Aor"),
        ],
        [
            _token(1, "τὸ", "ὁ", "DET", "det", "2", "Case=Nom|Number=Sing"),
            _token(2, "ἄγαλμα", "ἄγαλμα", "NOUN", "root", "0", "Case=Nom|Number=Sing"),
            _token(3, "καλόν", "καλός", "ADJ", "amod", "2", "Case=Nom|Number=Sing"),
        ],
    ]
    for book in range(1, 9):
        for section in range(1, 5):
            template = feature_templates[(book + section) % len(feature_templates)]
            passages.append(
                {
                    "passage_id": f"{book}.1.{section}",
                    "book": book,
                    "chapter": 1,
                    "section": section,
                    "sentences": [
                        {
                            "passage_id": f"{book}.1.{section}",
                            "sentence_number": 1,
                            "greek_sentence": " ".join(token["form"] for token in template),
                            "tokens": template,
                        }
                    ],
                }
            )
    return {"model": "gpt-5.4-mini", "passages": passages}


def _sentence_model_label_sources(grammar_data):
    labels = ["mythic", "historical", "other"]
    records = {}
    for index, passage in enumerate(grammar_data["passages"]):
        bucket = labels[index % len(labels)]
        records[(passage["passage_id"], 1)] = {
            "bucket": bucket,
            "mythic": bucket == "mythic",
            "historical": bucket == "historical",
        }
    return [
        {
            "id": "test_labels",
            "label": "Test Labels",
            "prompt_version": "test-v1",
            "model": "manual-test",
            "note": "Synthetic test labels.",
            "records": records,
        }
    ]


def _sentence_model_discourse_records(grammar_data):
    modes = [
        "route_locative_description",
        "monument_catalogue",
        "historical_narrative",
        "mythological_narrative",
        "ritual_ethnographic_description",
        "sources_traditions_discussion",
    ]
    records = {}
    for index, passage in enumerate(grammar_data["passages"]):
        records[(passage["passage_id"], 1)] = {
            "mode": modes[index % len(modes)],
            "confidence": "high",
            "rationale": "Synthetic discourse-mode fixture.",
        }
    return records


def test_stylometric_sentence_model_data_and_pages():
    grammar_data = _sentence_model_grammar_data()
    model_data = get_stylometric_sentence_model_data(
        grammar_data=grammar_data,
        label_sources=_sentence_model_label_sources(grammar_data),
    )

    assert model_data["available"] is True
    assert model_data["metrics"]["parsed_sentence_count"] == 32
    assert any(
        result["available"]
        and result["task_id"] == "three_way"
        and result["feature_set_id"] == "morphosyntax"
        for result in model_data["classifiers"]
    )
    assert any(
        result["available"]
        and result["variant_id"] == "all_books"
        and result["feature_set_id"] == "morphosyntax"
        for result in model_data["regressions"]
    )

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "site"
        (output_dir / "css").mkdir(parents=True)
        generate_stylometric_sentence_model_pages(model_data, output_dir, "Pausanias")

        classifier_html = (output_dir / "analysis" / "stylometric-sentence-classifiers.html").read_text(encoding="utf-8")
        regression_html = (output_dir / "analysis" / "stylometric-book-regression.html").read_text(encoding="utf-8")

        assert "Sentence-level stylometric classifiers" in classifier_html
        assert "Download classifier metrics CSV" in classifier_html
        assert "Ridge regression" in regression_html
        assert (output_dir / "analysis" / "data" / "stylometric_sentence_classifier_metrics.csv").exists()
        assert (output_dir / "analysis" / "data" / "stylometric_book_regression_metrics.csv").exists()


def test_stylometric_book_feature_trend_data_and_page():
    grammar_data = _sentence_model_grammar_data()
    model_data = get_stylometric_sentence_model_data(
        grammar_data=grammar_data,
        label_sources=_sentence_model_label_sources(grammar_data),
    )
    trend_data = get_stylometric_book_feature_trend_data(
        grammar_data=grammar_data,
        model_data=model_data,
    )

    assert trend_data["available"] is True
    assert trend_data["metrics"]["parsed_sentence_count"] == 32
    assert trend_data["feature_trends"]
    assert trend_data["length_distribution"]["books"]
    assert "excluding_4_8" in trend_data["length_distribution"]["regressions"]

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "site"
        (output_dir / "css").mkdir(parents=True)
        generate_stylometric_book_feature_trend_page(trend_data, output_dir, "Pausanias")

        trends_html = (output_dir / "analysis" / "stylometric-book-feature-trends.html").read_text(encoding="utf-8")

        assert "Morphosyntax Feature Trends by Book" in trends_html
        assert "KDE Overlay" in trends_html
        assert "Violin Plots" in trends_html
        assert "Download feature proportions CSV" in trends_html
        assert '<th class="num">R2</th>' in trends_html
        assert '<th class="num">Statistic / slope</th>' in trends_html
        assert (output_dir / "analysis" / "data" / "stylometric_book_feature_proportions.csv").exists()
        assert (output_dir / "analysis" / "data" / "stylometric_sentence_length_tests.csv").exists()


def test_discourse_mode_aorist_analysis_and_page():
    grammar_data = _sentence_model_grammar_data()
    analysis = get_discourse_mode_aorist_analysis(
        grammar_data=grammar_data,
        discourse_records=_sentence_model_discourse_records(grammar_data),
    )

    assert analysis["available"] is True
    assert analysis["metrics"]["tagged_sentence_count"] == 32
    assert analysis["metrics"]["aorist_sentence_count"] > 0
    assert analysis["adjusted_regressions"]["mode_adjusted_all_books"]["available"] is True
    assert analysis["mode_trends"]

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "site"
        (output_dir / "css").mkdir(parents=True)
        generate_discourse_mode_aorist_page(analysis, output_dir, "Pausanias")

        html = (output_dir / "analysis" / "discourse-mode-aorist.html").read_text(encoding="utf-8")

        assert "Is the Aorist Trend Stylistic or Content-Driven?" in html
        assert "Mode-Adjusted Aorist Slope" in html
        assert "Within-Mode Aorist Trends" in html
        assert (output_dir / "analysis" / "data" / "discourse_mode_aorist_regressions.csv").exists()
        assert (output_dir / "analysis" / "data" / "discourse_mode_aorist_sentences.csv").exists()
