from tempfile import TemporaryDirectory
from pathlib import Path

from website.generators import generate_manto_network_pages, generate_places_index, generate_texts_index
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
