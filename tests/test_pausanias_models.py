import json
from types import SimpleNamespace
from unittest.mock import Mock

import extract_proper_nouns
import mythic_sceptic_analyser
import sentence_mythic_sceptic_analyser
import split_sentences
import translate_pausanias
from pausanias_models import ANNOTATION_MODEL, SPLIT_FALLBACK_MODEL, TEXT_MODEL
from website import main as website_main


def test_model_defaults(monkeypatch):
    monkeypatch.setattr("sys.argv", ["pausanias"])
    for module in (extract_proper_nouns, mythic_sceptic_analyser, sentence_mythic_sceptic_analyser):
        assert module.parse_arguments().model == ANNOTATION_MODEL
    assert translate_pausanias.parse_arguments().model == TEXT_MODEL
    assert website_main.parse_arguments().model == TEXT_MODEL
    assert not website_main.parse_arguments().translate_phrases
    assert split_sentences.parse_arguments().model == "gpt-5.6-luna"
    assert split_sentences.parse_arguments().fallback_model == SPLIT_FALLBACK_MODEL


def test_sentence_split_retries_with_supported_tool_mode(monkeypatch):
    client = Mock()
    def response(greek, english):
        args = json.dumps({"greek_sentences": greek, "english_sentences": english})
        tool = SimpleNamespace(function=SimpleNamespace(arguments=args))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[tool]))])

    client.chat.completions.create.side_effect = [
        response(["Θάλασσα."], ["Sea.", "Sky."]),
        response(["Θάλασσα.", "Οὐρανός."], ["Sea.", "Sky."]),
    ]
    conn = Mock()
    save = Mock()
    monkeypatch.setattr("sys.argv", ["split_sentences.py", "--stop", "1"])
    monkeypatch.setattr(split_sentences, "OpenAI", lambda **kwargs: client)
    monkeypatch.setattr(split_sentences, "load_openai_api_key", lambda path: "fixture")
    monkeypatch.setattr(split_sentences, "connect", lambda url: conn)
    monkeypatch.setattr(split_sentences, "create_sentences_table", Mock())
    monkeypatch.setattr(split_sentences, "get_unsplit_passages", lambda *args: [("1.1.1", "Θάλασσα. Οὐρανός.", "Sea. Sky.")])
    monkeypatch.setattr(split_sentences, "save_sentences", save)
    monkeypatch.setattr(split_sentences.time, "sleep", Mock())

    split_sentences.main()

    primary, fallback = [call.kwargs for call in client.chat.completions.create.call_args_list]
    assert primary["model"] == "gpt-5.6-luna" and "reasoning_effort" not in primary
    assert fallback["model"] == SPLIT_FALLBACK_MODEL and fallback["reasoning_effort"] == "none"
    assert fallback["tool_choice"]["function"]["name"] == "record_sentences"
    save.assert_called_once_with(conn, "1.1.1", ["Θάλασσα.", "Οὐρανός."], ["Sea.", "Sky."])
