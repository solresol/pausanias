from sentence_trankit import (
    conllu_blocks,
    parse_conllu_tokens,
    syntactic_token_count,
    tokenize_for_trankit,
)


def test_tokenize_for_trankit_splits_greek_words_and_punctuation():
    tokens = tokenize_for_trankit("μετὰ δὲ αὐτοὺς ἀνήρ ἐστι καθήμενος·")

    assert tokens == ["μετὰ", "δὲ", "αὐτοὺς", "ἀνήρ", "ἐστι", "καθήμενος", "·"]


def test_conllu_blocks_splits_trankit_output():
    text = "1\tμετὰ\t_\tr\tr--------\t_\t2\tAuxP\t_\t_\n\n1\tδὲ\t_\td\td--------\t_\t0\tAuxY\t_\t_\n"

    assert conllu_blocks(text) == [
        "1\tμετὰ\t_\tr\tr--------\t_\t2\tAuxP\t_\t_\n",
        "1\tδὲ\t_\td\td--------\t_\t0\tAuxY\t_\t_\n",
    ]


def test_parse_conllu_tokens_preserves_agdt_morphosyntax():
    conllu = """1\tἐπίγραμμα\t_\tn\tn-s---na-\tCase=a|Gender=n|Number=s\t11\tPNOM\t_\t_
2\tλέγει\t_\tv\tv3spia---\tMood=i|Number=s|Person=3|Tense=p|Voice=a\t0\tPRED\t_\t_
"""

    tokens = parse_conllu_tokens(conllu)

    assert tokens[0]["form"] == "ἐπίγραμμα"
    assert tokens[0]["lemma"] is None
    assert tokens[0]["pos"] == "n"
    assert tokens[0]["xpos"] == "n-s---na-"
    assert tokens[0]["feats"] == {"Case": "a", "Gender": "n", "Number": "s"}
    assert tokens[0]["deprel"] == "PNOM"
    assert tokens[1]["head_token_id"] == "0"
    assert syntactic_token_count(tokens) == 2
