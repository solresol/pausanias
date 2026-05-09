"""Helpers for turning Greek surface text into lemma-token documents."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Iterable


DEFAULT_PROMPT_VERSION = "greek-word-lemmas-v1"
GREEK_TOKEN_RE = re.compile(
    r"[\u0370-\u03ff\u1f00-\u1fff]+(?:[ʼ'’\u02bc](?=[\u0370-\u03ff\u1f00-\u1fff])"
    r"[\u0370-\u03ff\u1f00-\u1fff]+|[ʼ'’\u02bc])?"
)
TOKEN_PATTERN = re.compile(r"(?u)\b\w\w+\b")


@dataclass(frozen=True)
class LemmaTextStats:
    text_count: int
    token_count: int
    lemmatized_token_count: int
    missing_token_count: int
    unique_missing_count: int


def casefold_preprocessor(text: str) -> str:
    """Match the vectorizer's intended Unicode handling for Greek text."""
    return unicodedata.normalize("NFC", str(text).casefold())


def surface_lookup_key(token: str) -> str:
    """Match the key shape stored by word_lemmatizer.py."""
    return token.lower()


def tokenize_greek(text: str) -> list[str]:
    return [match.group(0) for match in GREEK_TOKEN_RE.finditer(str(text or ""))]


def normalize_stopwords(stopwords: Iterable[str]) -> list[str]:
    """Normalize stopwords to match TfidfVectorizer preprocessing."""
    normalized: list[str] = []
    for word in stopwords:
        normalized_word = casefold_preprocessor(str(word))
        normalized.extend(TOKEN_PATTERN.findall(normalized_word))
    return list(dict.fromkeys(normalized))


def load_word_lemma_lookup(
    conn,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> dict[str, str]:
    """Load context-free Greek surface-form lemmas from PostgreSQL."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT surface_form, lemma
            FROM greek_word_lemmas
            WHERE prompt_version = %s
            """,
            (prompt_version,),
        )
        return {surface: lemma for surface, lemma in cursor.fetchall()}


def lemma_text_for(
    text: str,
    lemma_lookup: dict[str, str],
    *,
    missing_counter: Counter[str] | None = None,
) -> str:
    """Return a whitespace-separated lemma stream for a Greek source text."""
    lemmas: list[str] = []
    for token in tokenize_greek(text):
        lemma = lemma_lookup.get(surface_lookup_key(token))
        if lemma is None:
            if missing_counter is not None:
                missing_counter[token] += 1
            lemma = token
        lemmas.append(lemma)
    return " ".join(lemmas)


def build_lemma_texts(
    texts: Iterable[str],
    lemma_lookup: dict[str, str],
) -> tuple[list[str], LemmaTextStats]:
    missing_counter: Counter[str] = Counter()
    lemma_texts: list[str] = []
    token_count = 0
    lemmatized_token_count = 0

    for text in texts:
        tokens = tokenize_greek(text)
        token_count += len(tokens)
        lemmatized_token_count += sum(
            1 for token in tokens if surface_lookup_key(token) in lemma_lookup
        )
        lemma_texts.append(
            lemma_text_for(text, lemma_lookup, missing_counter=missing_counter)
        )

    return lemma_texts, LemmaTextStats(
        text_count=len(lemma_texts),
        token_count=token_count,
        lemmatized_token_count=lemmatized_token_count,
        missing_token_count=sum(missing_counter.values()),
        unique_missing_count=len(missing_counter),
    )


def expand_stopwords_with_lemma_forms(
    stopwords: Iterable[str],
    lemma_lookup: dict[str, str],
) -> list[str]:
    """Include both original stopword tokens and their cached lemma forms."""
    expanded: list[str] = []
    for word in stopwords:
        if word is None:
            continue
        text = str(word)
        expanded.append(text)
        for token in tokenize_greek(text):
            lemma = lemma_lookup.get(surface_lookup_key(token))
            if lemma is not None:
                expanded.append(lemma)
    return normalize_stopwords(expanded)
