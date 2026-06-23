from generate_latex_book import (
    april_tag_id_pair,
    april_tag_relative_path,
    generate_book_content,
    generate_greek_book_content,
    generate_greek_main_document,
    generate_greek_checklist_document,
    generate_makefile,
    generate_parallel_document,
)


def test_greek_checklist_brackets_checkbox_group_with_apriltag_images():
    sentences = [
        {
            "passage_id": "1.1.1",
            "sentence_number": 1,
            "greek": "Ἀρχὴ πρώτη.",
            "english": "First beginning.",
        },
        {
            "passage_id": "1.1.1",
            "sentence_number": 2,
            "greek": "Δευτέρα πρότασις.",
            "english": "Second sentence.",
        },
    ]

    tex = generate_greek_checklist_document(sentences)

    assert r"\texttt{1.1.1 s1}" in tex
    assert r"\texttt{1.1.1 s2}" in tex
    assert "Ἀρχὴ πρώτη." in tex
    assert r"\apriltagimage{apriltags/tagstandard52h13/tag-00000.png}" in tex
    assert r"\apriltagimage{apriltags/tagstandard52h13/tag-00001.png}" in tex
    assert r"\apriltagimage{apriltags/tagstandard52h13/tag-00002.png}" in tex
    assert r"\apriltagimage{apriltags/tagstandard52h13/tag-00003.png}" in tex
    assert r"\setlength{\reviewboxsize}{4mm}" in tex
    assert r"\fbox{\rule{0pt}{\reviewboxsize}\rule{\reviewboxsize}{0pt}}" in tex
    assert tex.count(r"\reviewbox & \reviewbox & \reviewbox") == 2
    assert april_tag_id_pair(1) == (0, 1)
    assert april_tag_id_pair(2) == (2, 3)
    assert april_tag_relative_path(3) == "apriltags/tagstandard52h13/tag-00003.png"


def test_parallel_document_keeps_aligned_greek_and_english_sentences():
    sentences = [
        {
            "passage_id": "1.1.1",
            "sentence_number": 1,
            "greek": "Ἀρχὴ πρώτη.",
            "english": "First beginning.",
        }
    ]

    tex = generate_parallel_document(sentences)

    assert r"\texttt{1.1.1 s1}" in tex
    assert "Ἀρχὴ πρώτη." in tex
    assert "First beginning." in tex


def test_greek_book_content_has_passage_index_and_name_indices():
    passages = [
        {
            "id": "1.1.1",
            "greek": "Ἀρχὴ πρώτη.",
            "english": "First beginning.",
        }
    ]
    nouns_by_passage = {
        "1.1.1": [
            {
                "reference_form": "Ἀθῆναι",
                "english": "Athens",
                "entity_type": "place",
            },
            {
                "reference_form": "Ζεύς",
                "english": "Zeus",
                "entity_type": "deity",
            },
        ]
    }

    tex = generate_greek_book_content(1, passages, nouns_by_passage, map_file="map1.pdf")

    assert r"\part{Book 1: Attica}" in tex
    assert r"\chapter{Chapter 1}" in tex
    assert r"\passageheading{1.1.1}" in tex
    assert r"\index[gpassages]{001.001.001@1.1.1}" in tex
    assert r"\index[gplaces]{Athens@Athens (Ἀθῆναι)}" in tex
    assert r"\index[gdeities]{Zeus@Zeus (Ζεύς)}" in tex
    assert "Ἀρχὴ πρώτη." in tex
    assert r"\includegraphics[width=0.82\textwidth]{map1.pdf}" in tex


def test_greek_main_document_prints_all_indices():
    tex = generate_greek_main_document([1])

    assert r"\input{greek-preamble}" in tex
    assert r"\input{greek-titlepage}" in tex
    assert r"\input{greek-book1}" in tex
    assert r"\tableofcontents" in tex
    assert r"\printindex[gpassages]" in tex
    assert r"\printindex[gpeople]" in tex
    assert r"\printindex[gplaces]" in tex
    assert r"\printindex[gdeities]" in tex


def test_english_book_content_omits_passage_classifier_icons():
    passages = [
        {
            "id": "1.1.1",
            "english": "A translated passage.",
            "is_mythic": True,
            "is_skeptical": True,
        }
    ]

    tex = generate_book_content(1, passages, nouns_by_passage={})

    assert r"\passage{1.1.1}" in tex
    assert r"\mythic" not in tex
    assert r"\skeptic" not in tex


def test_makefile_uses_lualatex_for_large_apriltag_checklist():
    makefile = generate_makefile()

    assert "all: pausanias.pdf pausanias-greek.pdf pausanias-greek-english-parallel.pdf" in makefile
    assert "pausanias-greek.pdf: pausanias-greek.tex greek-preamble.tex" in makefile
    assert "$(MAKEINDEX) gpassages.idx" in makefile
    assert "$(MAKEINDEX) gpeople.idx" in makefile
    assert "$(MAKEINDEX) gplaces.idx" in makefile
    assert "$(MAKEINDEX) gdeities.idx" in makefile
    assert "LUALATEX = lualatex" in makefile
    assert "pausanias-greek-checklist.pdf:\n\t$(LUALATEX)" in makefile
    assert "pausanias-greek-checklist.pdf: pausanias-greek-checklist.tex" not in makefile
    assert "$(LUALATEX) -interaction=nonstopmode -halt-on-error pausanias-greek-checklist.tex" in makefile
    clean_block = makefile.split("clean:", 1)[1].split("clean-checklist:", 1)[0]
    assert "pausanias-greek-checklist.pdf" not in clean_block
    assert "clean-checklist:" in makefile
