#!/usr/bin/env python
"""
Generate one-line summaries of Pausanias passages using GPT.

Takes the English translation of each passage and asks gpt-5-mini to produce
a brief one-line summary. Stores results in a passage_summaries table.

Usage:
    python summarise_passages.py                    # Summarise all unsummarised passages
    python summarise_passages.py --stop-after 50    # Process only 50 passages
    python summarise_passages.py --progress-bar     # Show progress bar
"""
import argparse
import json
import os
import sqlite3
import time
from datetime import datetime

from openai import OpenAI
from tqdm import tqdm


def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate one-line summaries of Pausanias passages")
    parser.add_argument("--database", default="pausanias.sqlite",
                        help="SQLite database file (default: pausanias.sqlite)")
    parser.add_argument("--openai-api-key-file", default="~/.openai.key",
                        help="File containing OpenAI API key (default: ~/.openai.key)")
    parser.add_argument("--stop-after", type=int, default=None,
                        help="Maximum number of passages to process")
    parser.add_argument("--progress-bar", action="store_true", default=False,
                        help="Show progress bar")
    parser.add_argument("--model", default="gpt-5-mini",
                        help="OpenAI model to use (default: gpt-5-mini)")
    parser.add_argument("--resummarise", action="store_true",
                        help="Re-process already summarised passages")
    return parser.parse_args()


def load_openai_api_key(key_file):
    key_path = os.path.expanduser(key_file)
    with open(key_path, 'r') as f:
        return f.read().strip()


def create_table(conn):
    """Create the passage_summaries table."""
    conn.execute('''
    CREATE TABLE IF NOT EXISTS passage_summaries (
        passage_id TEXT PRIMARY KEY,
        summary TEXT NOT NULL,
        model TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        input_tokens INTEGER,
        output_tokens INTEGER,
        FOREIGN KEY (passage_id) REFERENCES passages(id)
    )
    ''')
    conn.commit()


def get_unsummarised_passages(conn, limit=None, resummarise=False):
    """Get passages that need summaries."""
    if resummarise:
        query = """
            SELECT p.id, t.english_translation
            FROM passages p
            JOIN translations t ON p.id = t.passage_id
            WHERE t.english_translation IS NOT NULL
            ORDER BY p.id
        """
    else:
        query = """
            SELECT p.id, t.english_translation
            FROM passages p
            JOIN translations t ON p.id = t.passage_id
            LEFT JOIN passage_summaries s ON p.id = s.passage_id
            WHERE t.english_translation IS NOT NULL
              AND s.passage_id IS NULL
            ORDER BY p.id
        """

    if limit:
        query += f" LIMIT {limit}"

    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


def summarise_passage(client, model, passage_id, english_text):
    """Generate a one-line summary of a passage."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You summarise passages from Pausanias' Description of Greece. "
                 "Given an English translation of a passage, produce a single brief sentence (under 100 characters if possible) "
                 "summarising what the passage is about. Focus on the key subject: a place, person, monument, or event. "
                 "Do not start with 'This passage' or 'Pausanias'. Just state the subject directly. "
                 "Examples: 'The temple of Athena at Sounion', 'Theseus defeats the Minotaur', "
                 "'Dedications in the Athenian agora'."},
                {"role": "user", "content": english_text}
            ]
        )

        summary = response.choices[0].message.content.strip()
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        return summary, input_tokens, output_tokens

    except Exception as e:
        print(f"Error summarising passage {passage_id}: {e}")
        return None, 0, 0


def save_summary(conn, passage_id, summary, model, input_tokens, output_tokens):
    """Save a summary to the database."""
    conn.execute("""
        INSERT OR REPLACE INTO passage_summaries
        (passage_id, summary, model, timestamp, input_tokens, output_tokens)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (passage_id, summary, model, datetime.now().isoformat(),
          input_tokens, output_tokens))
    conn.commit()


def main():
    args = parse_arguments()

    api_key = load_openai_api_key(args.openai_api_key_file)
    client = OpenAI(api_key=api_key)

    conn = sqlite3.connect(args.database)

    try:
        create_table(conn)

        passages = get_unsummarised_passages(conn, args.stop_after, args.resummarise)
        print(f"Found {len(passages)} passages to summarise")

        if not passages:
            return

        total_input_tokens = 0
        total_output_tokens = 0
        summarised = 0

        iterator = tqdm(passages) if args.progress_bar else passages

        for passage_id, english_text in iterator:
            summary, input_tokens, output_tokens = summarise_passage(
                client, args.model, passage_id, english_text
            )

            if summary:
                save_summary(conn, passage_id, summary, args.model,
                             input_tokens, output_tokens)
                summarised += 1
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens

                if not args.progress_bar:
                    print(f"  {passage_id}: {summary}")

        print(f"\nSummarisation complete:")
        print(f"  Summarised: {summarised}")
        print(f"  Total tokens: {total_input_tokens} input, {total_output_tokens} output")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
