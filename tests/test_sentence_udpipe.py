from sentence_udpipe import (
    format_udpipe_input,
    parse_conllu_deps,
    parse_conllu_mapping,
    parse_conllu_tokens,
    syntactic_token_count,
    tokenize_for_udpipe,
)


def test_parse_conllu_mapping_handles_empty_and_key_values():
    assert parse_conllu_mapping("_") == {}
    assert parse_conllu_mapping("Case=Nom|Gender=Masc|Number=Sing") == {
        "Case": "Nom",
        "Gender": "Masc",
        "Number": "Sing",
    }


def test_parse_conllu_deps_preserves_deprel_subtypes():
    assert parse_conllu_deps("_") == []
    assert parse_conllu_deps("2:nsubj|4:nmod:poss") == [
        {"head": "2", "deprel": "nsubj"},
        {"head": "4", "deprel": "nmod:poss"},
    ]


def test_tokenize_for_udpipe_splits_greek_words_and_punctuation():
    tokens = tokenize_for_udpipe("τῆς ἠπείρου· Ἀθηναῖοι, φασίν.")

    assert tokens == ["τῆς", "ἠπείρου", "·", "Ἀθηναῖοι", ",", "φασίν", "."]
    assert format_udpipe_input("τῆς ἠπείρου.", "horizontal") == "τῆς ἠπείρου .\n"


def test_parse_conllu_tokens_keeps_raw_and_json_fields():
    conllu = """# sent_id = 1
# text = οἱ δὲ Ἀθηναῖοι
1\tοἱ\tὁ\tDET\tl-s---mn-\tCase=Nom|Gender=Masc|Number=Plur\t3\tdet\t_\tSpaceAfter=No
2\tδὲ\tδέ\tADV\td--------\t_\t3\tdiscourse\t_\t_
3\tἈθηναῖοι\tἈθηναῖος\tNOUN\tn-p---mn-\tCase=Nom|Gender=Masc|Number=Plur\t0\troot\t_\t_
"""

    tokens = parse_conllu_tokens(conllu)

    assert len(tokens) == 3
    assert tokens[0]["token_order"] == 1
    assert tokens[0]["lemma"] == "ὁ"
    assert tokens[0]["upos"] == "DET"
    assert tokens[0]["feats"] == {
        "Case": "Nom",
        "Gender": "Masc",
        "Number": "Plur",
    }
    assert tokens[0]["misc"] == {"SpaceAfter": "No"}
    assert tokens[1]["feats"] == {}
    assert tokens[2]["head_token_id"] == "0"
    assert syntactic_token_count(tokens) == 3


def test_parse_conllu_tokens_marks_multiword_and_empty_nodes():
    conllu = """1-2\tτοὐμόν\t_\t_\t_\t_\t_\t_\t_\t_
1\tτὸ\tὁ\tDET\t_\tCase=Acc\t2\tdet\t_\t_
2\tἐμόν\tἐμός\tPRON\t_\tCase=Acc\t0\troot\t_\t_
2.1\tγε\tγε\tPART\t_\t_\t2\tdiscourse\t_\t_
"""

    tokens = parse_conllu_tokens(conllu)

    assert tokens[0]["is_multiword_token"] is True
    assert tokens[0]["lemma"] is None
    assert tokens[3]["is_empty_node"] is True
    assert syntactic_token_count(tokens) == 2
