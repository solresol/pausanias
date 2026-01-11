#!/usr/bin/env python

"""Module for translating Greek phrases to English using LLM caching."""

import os
import sqlite3
import time
from datetime import datetime
from typing import Optional, Dict

from openai import OpenAI


def create_phrase_translations_table(conn):
    """Create the phrase_translations table if it doesn't exist."""
    conn.execute('''
    CREATE TABLE IF NOT EXISTS phrase_translations (
        phrase TEXT PRIMARY KEY,
        english_translation TEXT NOT NULL,
        is_proper_noun BOOLEAN DEFAULT 0,
        timestamp TEXT NOT NULL,
        model TEXT NOT NULL,
        input_tokens INTEGER NOT NULL,
        output_tokens INTEGER NOT NULL
    )
    ''')
    conn.commit()


def get_phrase_translation(conn, phrase: str) -> Optional[tuple[str, bool]]:
    """Get the English translation for a Greek phrase from the cache.

    Args:
        conn: Database connection
        phrase: Greek phrase to look up

    Returns:
        Tuple of (english_translation, is_proper_noun) if found, None otherwise
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT english_translation, is_proper_noun FROM phrase_translations WHERE phrase = ?",
        (phrase,)
    )
    result = cursor.fetchone()
    return (result[0], bool(result[1])) if result else None


def save_phrase_translation(conn, phrase: str, translation: str, is_proper_noun: bool,
                           model: str, input_tokens: int, output_tokens: int):
    """Save a phrase translation to the database.

    Args:
        conn: Database connection
        phrase: Greek phrase
        translation: English translation
        is_proper_noun: Whether the phrase is a proper noun
        model: Model name used for translation
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
    """
    timestamp = datetime.now().isoformat()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO phrase_translations
        (phrase, english_translation, is_proper_noun, timestamp, model, input_tokens, output_tokens)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (phrase, translation, is_proper_noun, timestamp, model, input_tokens, output_tokens)
    )
    conn.commit()


def translate_phrase(client: OpenAI, model: str, phrase: str) -> tuple[str, bool, int, int]:
    """Translate a Greek phrase to English using the OpenAI API.

    Args:
        client: OpenAI client
        model: Model name to use
        phrase: Greek phrase to translate

    Returns:
        Tuple of (translation, is_proper_noun, input_tokens, output_tokens)
    """
    system_prompt = """You are an expert in Ancient Greek who specializes in translating classical Greek texts.
Translate the provided Greek word or phrase into clear, accurate English.
Also determine if this is a proper noun (a name of a person, place, deity, or specific thing).

Respond in exactly this format:
Translation: [your translation here]
Proper Noun: [yes or no]"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Translate this Ancient Greek word or phrase to English:\n\n{phrase}"}
            ]
        )

        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        content = response.choices[0].message.content.strip()

        # Parse the response
        translation = ""
        is_proper_noun = False

        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('Translation:'):
                translation = line.replace('Translation:', '').strip()
            elif line.startswith('Proper Noun:'):
                proper_noun_str = line.replace('Proper Noun:', '').strip().lower()
                is_proper_noun = proper_noun_str in ['yes', 'true', '1']

        return translation, is_proper_noun, input_tokens, output_tokens

    except Exception as e:
        print(f"Error translating phrase '{phrase}': {str(e)}")
        return "", False, 0, 0


def get_or_fetch_translation(conn, client: OpenAI, model: str, phrase: str,
                             delay: float = 0.5) -> tuple[str, bool]:
    """Get translation from cache or fetch from LLM if not available.

    Args:
        conn: Database connection
        client: OpenAI client
        model: Model name to use for new translations
        phrase: Greek phrase to translate
        delay: Delay in seconds after API call to avoid rate limits

    Returns:
        Tuple of (english_translation, is_proper_noun)
    """
    # Check cache first
    cached = get_phrase_translation(conn, phrase)
    if cached:
        return cached

    # Fetch from LLM
    translation, is_proper_noun, input_tokens, output_tokens = translate_phrase(client, model, phrase)

    if translation:
        # Save to cache
        save_phrase_translation(conn, phrase, translation, is_proper_noun, model, input_tokens, output_tokens)
        # Small delay to avoid rate limits
        time.sleep(delay)

    return translation, is_proper_noun


def get_translations_for_phrases(conn, client: Optional[OpenAI], model: str,
                                 phrases: list[str], delay: float = 0.5) -> Dict[str, tuple[str, bool]]:
    """Get translations for a list of phrases, fetching from LLM only when needed.

    Args:
        conn: Database connection
        client: OpenAI client (None to only use cache)
        model: Model name to use for new translations
        phrases: List of Greek phrases to translate
        delay: Delay in seconds after each API call

    Returns:
        Dictionary mapping phrases to tuples of (english_translation, is_proper_noun)
    """
    translations = {}
    phrases_to_fetch = []

    # First, get all cached translations
    for phrase in phrases:
        cached = get_phrase_translation(conn, phrase)
        if cached:
            translations[phrase] = cached
        elif client is not None:
            phrases_to_fetch.append(phrase)
        else:
            # No client provided, leave empty
            translations[phrase] = ("", False)

    # Fetch missing translations if client is available
    if client and phrases_to_fetch:
        print(f"Fetching {len(phrases_to_fetch)} new phrase translations from LLM...")
        for phrase in phrases_to_fetch:
            translation_tuple = get_or_fetch_translation(conn, client, model, phrase, delay)
            translations[phrase] = translation_tuple

    return translations


def load_openai_api_key(key_file: str = "~/.openai.key") -> str:
    """Load OpenAI API key from file.

    Args:
        key_file: Path to file containing API key

    Returns:
        API key string

    Raises:
        FileNotFoundError: If key file doesn't exist
    """
    key_path = os.path.expanduser(key_file)
    try:
        with open(key_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"OpenAI API key file not found: {key_file}")
