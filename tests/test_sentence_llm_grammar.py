import pytest

from sentence_llm_grammar import (
    effective_token_budget,
    get_daily_token_usage,
    get_sentences,
    tokens_to_conllu,
    tokenize_for_llm,
    validate_and_normalize_tokens,
    write_payload,
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


def test_write_payload_removes_nul_chars_before_postgres_jsonb():
    psql = FakePsql("")
    payload = {
        "run": {
            "run_id": "11111111-2222-3333-4444-555555555555",
            "started_at": "2026-06-26T00:00:00+00:00",
            "completed_at": "2026-06-26T00:01:00+00:00",
            "model": "gpt-5.4-mini",
            "prompt_version": "greek-sentence-grammar-v1",
            "status": "completed",
            "input_tokens": 1,
            "output_tokens": 1,
            "processed_count": 1,
            "token_count": 1,
            "failure_count": 0,
            "notes": "nul\x00removed",
        },
        "results": [
            {
                "passage_id": "1.1.1",
                "sentence_number": 1,
                "greek_sentence": "λόγος",
                "conllu": "1\tλόγος\tλόγος\tNOUN\t_\x00\t_\t0\troot\t_\t_\n",
                "response_json": {"note": "ok\x00"},
                "sentence_note": None,
                "input_tokens": 1,
                "output_tokens": 1,
                "token_count": 1,
                "tokens": [
                    {
                        "token_order": 1,
                        "token_id": "1",
                        "form": "λόγος",
                        "lemma": "λόγος",
                        "upos": "NOUN",
                        "xpos": "_",
                        "feats_raw": "_",
                        "feats": {},
                        "head_token_id": "0",
                        "deprel": "root",
                        "confidence": "high",
                        "note": "clean\x00me",
                        "is_multiword_token": False,
                        "is_empty_node": False,
                    }
                ],
            }
        ],
        "failures": [],
    }

    write_payload(psql, payload)

    assert "\\u0000" not in psql.sql
    assert "jsonb_to_recordset" not in psql.sql
    assert "WITH payload AS" not in psql.sql
    assert "nulremoved" in psql.sql
    assert "cleanme" in psql.sql
