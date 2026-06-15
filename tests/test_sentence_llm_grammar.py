import pytest

from sentence_llm_grammar import (
    effective_token_budget,
    get_daily_token_usage,
    get_sentences,
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


def test_effective_token_budget_respects_daily_remaining():
    assert (
        effective_token_budget(
            token_budget=None,
            daily_token_budget=1_000_000,
            daily_tokens_used=250_000,
        )
        == 750_000
    )
    assert (
        effective_token_budget(
            token_budget=100_000,
            daily_token_budget=1_000_000,
            daily_tokens_used=250_000,
        )
        == 100_000
    )
    assert (
        effective_token_budget(
            token_budget=900_000,
            daily_token_budget=1_000_000,
            daily_tokens_used=250_000,
        )
        == 750_000
    )
    assert (
        effective_token_budget(
            token_budget=None,
            daily_token_budget=1_000_000,
            daily_tokens_used=1_250_000,
        )
        == 0
    )


class FakePsql:
    def __init__(self, output):
        self.output = output
        self.sql = ""

    def run(self, sql):
        self.sql = sql
        return self.output


def test_get_daily_token_usage_counts_selected_model_prompt_day():
    psql = FakePsql("token_count\n12345\n")

    assert (
        get_daily_token_usage(
            psql,
            model="gpt-5.4-mini",
            prompt_version="greek-sentence-grammar-v1",
            budget_timezone="Australia/Sydney",
        )
        == 12345
    )
    assert "a.model = 'gpt-5.4-mini'" in psql.sql
    assert "a.prompt_version = 'greek-sentence-grammar-v1'" in psql.sql
    assert "Australia/Sydney" in psql.sql


def test_get_sentences_can_use_seeded_random_order_without_sample_size():
    psql = FakePsql("passage_id,sentence_number,greek_sentence\n")

    rows = get_sentences(
        psql,
        model="gpt-5.4-mini",
        prompt_version="greek-sentence-grammar-v1",
        overwrite=False,
        excluded_books=[],
        passage_id=None,
        limit=10,
        sample_size=None,
        sample_seed="daily-seed",
        random_order=True,
    )

    assert rows == []
    assert "ORDER BY md5" in psql.sql
    assert "'daily-seed'" in psql.sql
    assert "LIMIT 10" in psql.sql
