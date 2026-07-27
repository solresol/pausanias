from tempfile import TemporaryDirectory
from pathlib import Path

from website.generators import (
    generate_manto_network_pages,
    generate_manto_place_survival_model_page,
    generate_places_index,
    generate_texts_index,
)
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


def test_texts_index_links_greek_markup_downloads():
    with TemporaryDirectory() as tmpdir:
        generate_texts_index(tmpdir, "Pausanias Analysis")
        html = (Path(tmpdir) / "texts" / "index.html").read_text(encoding="utf-8")

    assert "pausanias-greek-markup.pdf" in html
    assert "pausanias-greek-markup.docx" in html


def test_places_index_links_manto_network_page():
    with TemporaryDirectory() as tmpdir:
        generate_places_index(tmpdir, "Pausanias Analysis")
        html = (Path(tmpdir) / "places" / "index.html").read_text(encoding="utf-8")

    assert "MANTO Place Network" in html
    assert 'href="manto-network.html"' in html
    assert "MANTO Place Survival Model" in html
    assert 'href="manto-survival-model.html"' in html


def test_place_survival_page_publishes_only_corrected_model_story():
    base_metrics = {
        "accuracy": 0.712,
        "majority_accuracy": 0.824,
        "precision_survives": 0.80,
        "recall_survives": 0.84,
        "f1_survives": 0.82,
        "precision_does_not_survive": 0.13,
        "recall_does_not_survive": 0.12,
        "f1_does_not_survive": 0.12,
        "true_survives_pred_survives": 307,
        "true_survives_pred_does_not_survive": 59,
        "true_does_not_survive_pred_survives": 69,
        "true_does_not_survive_pred_does_not_survive": 9,
    }
    attestation = {
        **base_metrics,
        "run_id": "attestation-run",
        "completed_at": "2026-07-27T03:55:08+00:00",
        "feature_family": "attestation",
        "label": "Pre-Pausanias attestation",
        "feature_set_version": "manto-pre-pausanias-attestation-v1",
        "balanced_accuracy": 0.480,
    }
    best = {
        **base_metrics,
        "run_id": "connectedness-run",
        "completed_at": "2026-07-27T03:55:17+00:00",
        "feature_family": "connectedness",
        "label": "Connectedness",
        "feature_set_version": "strict-model",
        "accuracy": 0.678,
        "balanced_accuracy": 0.564,
        "recall_survives": 0.755,
        "recall_does_not_survive": 0.373,
        "true_survives_pred_survives": 154,
        "true_survives_pred_does_not_survive": 50,
        "true_does_not_survive_pred_survives": 32,
        "true_does_not_survive_pred_does_not_survive": 19,
    }
    data = {
        "available": True,
        "release": {
            "record_id": 19446255,
            "doi": "10.5281/zenodo.19446255",
            "version": "v.1",
            "title": "MANTO data release",
        },
        "model_type": "logistic_regression_strict_pre_pausanias_v2",
        "evaluation": "5-fold-cv",
        "label_set": "llm",
        "sample_count": 255,
        "survives_count": 204,
        "does_not_survive_count": 51,
        "comparison": [attestation, best],
        "best_model": best,
        "feature_scores": [
            {
                "feature_name": "exclusive_figure_count",
                "label": "exclusive figure count",
                "family": "Connectedness",
                "coefficient": 1.005,
                "abs_coefficient": 1.005,
                "direction": "survives",
            }
        ],
        "coverage": {
            "passage_count": 3170,
            "reviewed_passage_count": 3170,
            "passages_with_claims": 1098,
        },
        "training_stats": {
            "training_rows_before_place_collapse": 444,
            "training_rows_after_place_collapse": 255,
            "duplicate_training_rows_collapsed": 189,
        },
    }

    with TemporaryDirectory() as tmpdir:
        generate_manto_place_survival_model_page(
            data,
            tmpdir,
            "Pausanias Analysis",
        )
        html = (
            Path(tmpdir) / "places" / "manto-survival-model.html"
        ).read_text(encoding="utf-8")

    assert "Leakage correction" in html
    assert "Pre-Pausanias attestation" in html
    assert "Connectedness" in html
    assert "0.564" in html
    assert "weak predictive result" in html
    assert "189" in html
    assert "exclusive figure count" in html
    assert "Pausanias mention and passage counts" in html
    assert "stratified five-fold cross-validation" in html
    assert 'class="place-survival-table-wrap"' in html
    assert "pausanias_mention_count" not in html
    assert "manto-network.html" in html


def test_manto_network_page_embeds_source_hover_data():
    data = {
        "available": True,
        "release_record_id": 19446255,
        "node_count": 2,
        "edge_count": 1,
        "community_count": 1,
        "modularity": 0.0,
        "athens": {
            "degree": 1,
            "community_size": 2,
            "clustering": 0.0,
            "neighbor_density": 0.0,
            "triangles": 0,
        },
        "athens_network": {
            "nodes": [
                {
                    "id": "8188815",
                    "label": "Athens (Attica)",
                    "community": 1,
                    "degree": 1,
                    "strength": 1,
                    "pagerank": 0.5,
                    "focus": True,
                },
                {
                    "id": "8253960",
                    "label": "Thebes (Boiotia)",
                    "community": 1,
                    "degree": 1,
                    "strength": 1,
                    "pagerank": 0.5,
                },
            ],
            "links": [
                {
                    "source": "8188815",
                    "target": "8253960",
                    "weight": 1,
                    "relations": [{"relation": "place_of_birth_of", "count": 1}],
                    "sources": [{"label": "Test source", "latest_year": -400, "count": 1}],
                }
            ],
        },
        "community_network": {
            "nodes": [
                {
                    "id": "community-1",
                    "community": 1,
                    "label": "Community 1",
                    "size": 2,
                    "top_places": [{"label": "Athens (Attica)"}],
                    "top_localities": [{"label": "Attica", "count": 1}],
                    "contains_athens_attica": True,
                }
            ],
            "links": [],
        },
        "communities": [
            {
                "community": 1,
                "contains_athens_attica": True,
                "size": 2,
                "edge_count": 1,
                "top_localities": [{"label": "Attica", "count": 1}],
                "top_places": [{"label": "Athens (Attica)"}, {"label": "Thebes (Boiotia)"}],
            }
        ],
    }

    with TemporaryDirectory() as tmpdir:
        generate_manto_network_pages(data, tmpdir, "Pausanias Analysis")
        html = (Path(tmpdir) / "places" / "manto-network.html").read_text(encoding="utf-8")

    assert "manto-athens-network" in html
    assert "Test source" in html
    assert "place_of_birth_of" in html
    assert "Athens is not treated as a complete clique" in html
