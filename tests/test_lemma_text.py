from collections import Counter

from lemma_text import (
    build_lemma_texts,
    expand_stopwords_with_lemma_forms,
    lemma_text_for,
)


def test_lemma_text_replaces_cached_surface_forms_and_tracks_fallbacks():
    lookup = {
        "λόγοις": "λόγος",
        "ἄνδρας": "ἀνήρ",
    }
    missing = Counter()

    text = lemma_text_for("λόγοις καὶ ἄνδρας", lookup, missing_counter=missing)

    assert text == "λόγος καὶ ἀνήρ"
    assert missing == Counter({"καὶ": 1})


def test_build_lemma_texts_reports_missing_tokens():
    lookup = {"λόγοις": "λόγος"}

    texts, stats = build_lemma_texts(["λόγοις καὶ", "λόγοις"], lookup)

    assert texts == ["λόγος καὶ", "λόγος"]
    assert stats.text_count == 2
    assert stats.token_count == 3
    assert stats.lemmatized_token_count == 2
    assert stats.missing_token_count == 1
    assert stats.unique_missing_count == 1


def test_stopwords_include_lemma_equivalents_and_non_greek_tokens():
    lookup = {"ἡρακλέους": "Ἡρακλῆς"}

    stopwords = expand_stopwords_with_lemma_forms(["ἡρακλέους", "hom"], lookup)

    assert "ἡρακλέουσ" in stopwords
    assert "ἡρακλῆσ" in stopwords
    assert "hom" in stopwords
