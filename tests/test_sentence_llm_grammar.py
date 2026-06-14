import pytest

from sentence_llm_grammar import (
    tokens_to_conllu,
    tokenize_for_llm,
    validate_and_normalize_tokens,
)


def test_tokenize_for_llm_splits_greek_words_and_punctuation():
    tokens = tokenize_for_llm("μετὰ δὲ αὐτοὺς ἀνήρ ἐστι καθήμενος·")

    assert tokens == ["μετὰ", "δὲ", "αὐτοὺς", "ἀνήρ", "ἐστι", "καθήμενος", "·"]


def test_validate_and_normalize_tokens_preserves_parser_fields():
    raw_tokens = [
        {
            "token_index": 1,
            "form": "ἐπίγραμμα",
            "lemma": "ἐπίγραμμα",
            "upos": "NOUN",
            "xpos": "n-s---na-",
            "feats": {"Case": "Acc", "Gender": "Neut", "Number": "Sing"},
            "head": 2,
            "deprel": "nsubj",
            "confidence": "high",
            "note": "",
        },
        {
            "token_index": 2,
            "form": "λέγει",
            "lemma": "λέγω",
            "upos": "VERB",
            "xpos": "v3spia---",
            "feats": {"Mood": "Ind", "Number": "Sing", "Person": "3"},
            "head": 0,
            "deprel": "root",
            "confidence": "high",
            "note": "",
        },
    ]

    tokens = validate_and_normalize_tokens(raw_tokens, ["ἐπίγραμμα", "λέγει"])

    assert tokens[0]["token_order"] == 1
    assert tokens[0]["upos"] == "NOUN"
    assert tokens[0]["feats_raw"] == "Case=Acc|Gender=Neut|Number=Sing"
    assert tokens[0]["head_token_id"] == "2"
    assert tokens[1]["lemma"] == "λέγω"
    assert tokens[1]["deprel"] == "root"


def test_validate_and_normalize_tokens_rejects_form_mismatch():
    raw_tokens = [
        {
            "token_index": 1,
            "form": "λέγει",
            "lemma": "λέγω",
            "upos": "VERB",
            "xpos": "v3spia---",
            "feats": {},
            "head": 0,
            "deprel": "root",
            "confidence": "high",
            "note": "",
        }
    ]

    with pytest.raises(ValueError, match="Expected form"):
        validate_and_normalize_tokens(raw_tokens, ["ἐπίγραμμα"])


def test_validate_and_normalize_tokens_rejects_self_head():
    raw_tokens = [
        {
            "token_index": 1,
            "form": "λέγει",
            "lemma": "λέγω",
            "upos": "VERB",
            "xpos": "v3spia---",
            "feats": {},
            "head": 1,
            "deprel": "root",
            "confidence": "high",
            "note": "",
        }
    ]

    with pytest.raises(ValueError, match="own head"):
        validate_and_normalize_tokens(raw_tokens, ["λέγει"])


def test_tokens_to_conllu_renders_expected_columns():
    tokens = validate_and_normalize_tokens(
        [
            {
                "token_index": 1,
                "form": "λέγει",
                "lemma": "λέγω",
                "upos": "VERB",
                "xpos": "v3spia---",
                "feats": {"Mood": "Ind"},
                "head": 0,
                "deprel": "root",
                "confidence": "high",
                "note": "",
            }
        ],
        ["λέγει"],
    )

    assert tokens_to_conllu(tokens) == "1\tλέγει\tλέγω\tVERB\tv3spia---\tMood=Ind\t0\troot\t_\t_\n"
