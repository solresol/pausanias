#!/usr/bin/env python

import argparse
import json
import os
import sqlite3
import sys
import time

from openai import OpenAI
from tqdm import tqdm


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Split Greek passages into sentences using the OpenAI API"
    )
    parser.add_argument(
        "--database",
        default="pausanias.sqlite",
        help="SQLite database file (default: pausanias.sqlite)",
    )
    parser.add_argument(
        "--openai-api-key-file",
        default="~/.openai.key",
        help="File containing OpenAI API key (default: ~/.openai.key)",
    )
    parser.add_argument(
        "--stop-after",
        "--stop",
        dest="stop_after",
        type=int,
        default=None,
        help="Maximum number of passages to process (default: all)",
    )
    parser.add_argument(
        "--progress-bar",
        action="store_true",
        default=False,
        help="Show progress bar",
    )
    parser.add_argument(
        "--model",
        default="gpt-5",
        help="OpenAI model to use (default: gpt-5)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Print the full API response for debugging",
    )
    return parser.parse_args()


def load_openai_api_key(key_file):
    key_path = os.path.expanduser(key_file)
    try:
        with open(key_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"OpenAI API key file not found: {key_file}")


def create_sentences_table(conn):
    """Create the table for storing Greek and English sentences if it doesn't exist."""
    conn.execute(
        """
    CREATE TABLE IF NOT EXISTS greek_sentences (
        passage_id TEXT NOT NULL,
        sentence_number INTEGER NOT NULL,
        sentence TEXT NOT NULL,
        english_sentence TEXT NOT NULL,
        PRIMARY KEY (passage_id, sentence_number),
        FOREIGN KEY (passage_id) REFERENCES passages(id)
    )
        """
    )
    conn.commit()


def get_unsplit_passages(conn, limit=None):
    """Retrieve passages with translations that haven't been split yet."""
    cursor = conn.cursor()
    query = """
    SELECT p.id, p.passage, t.english_translation
    FROM passages p
    JOIN translations t ON p.id = t.passage_id
    LEFT JOIN greek_sentences s ON p.id = s.passage_id
    WHERE s.passage_id IS NULL
    ORDER BY p.id
    """
    if limit:
        query += f" LIMIT {limit}"
    cursor.execute(query)
    return cursor.fetchall()


def split_passage(client, model, passage_id, passage_text, translation, debug=False):
    """Use the OpenAI API to split a passage and its translation into sentences."""
    system_prompt = (
        "You are an expert in Ancient Greek punctuation and a skilled English editor. "
        "Split both the original Greek passage and its English translation into corresponding sentences."
    )
    tools = [
        {
            "type": "function",
            "function": {
                "name": "record_sentences",
                "description": "Store Greek and English sentences",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "greek_sentences": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "english_sentences": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["greek_sentences", "english_sentences"],
                },
            },
        }
    ]
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Passage {passage_id}:\n\nGreek:\n{passage_text}\n\n"
                        f"English translation:\n{translation}\n\n"
                        "Split both the Greek passage and its English translation into sentences."
                    ),
                },
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "record_sentences"}},
        )
        if debug:
            print("\n=== DEBUG: FULL API RESPONSE ===")
            print(f"Response object: {response}")
            print("=== END DEBUG ===\n")
        tool_calls = response.choices[0].message.tool_calls
        if tool_calls:
            function_args = json.loads(tool_calls[0].function.arguments)
            greek_sentences = [s.strip() for s in function_args.get("greek_sentences", []) if s.strip()]
            english_sentences = [s.strip() for s in function_args.get("english_sentences", []) if s.strip()]
            return greek_sentences, english_sentences
        else:
            print(f"No tool call returned for passage {passage_id}")
            return [], []
    except Exception as e:
        print(f"Error splitting passage {passage_id}: {e}")
        return [], []


def save_sentences(conn, passage_id, greek_sentences, english_sentences):
    """Save the list of Greek and English sentences for a passage."""
    cursor = conn.cursor()
    for idx, (gr, en) in enumerate(zip(greek_sentences, english_sentences), start=1):
        cursor.execute(
            """
        INSERT OR REPLACE INTO greek_sentences (passage_id, sentence_number, sentence, english_sentence)
        VALUES (?, ?, ?, ?)
            """,
            (passage_id, idx, gr, en),
        )
    conn.commit()


def main():
    args = parse_arguments()
    api_key = load_openai_api_key(args.openai_api_key_file)
    client = OpenAI(api_key=api_key)
    conn = sqlite3.connect(args.database)
    try:
        create_sentences_table(conn)
        passages = get_unsplit_passages(conn, args.stop_after)
        if not passages:
            print("No unsplit passages found in the database.")
            return
        print(f"Found {len(passages)} unsplit passages.")
        iterator = tqdm(passages) if args.progress_bar else passages
        for passage_id, passage_text, translation in iterator:
            greek_sentences, english_sentences = split_passage(
                client, args.model, passage_id, passage_text, translation, args.debug
            )
            if greek_sentences:
                save_sentences(conn, passage_id, greek_sentences, english_sentences)
                if not args.progress_bar:
                    print(
                        f"Processed passage {passage_id}, extracted {len(greek_sentences)} sentences."
                    )
            else:
                print(f"Failed to split passage {passage_id}")
            time.sleep(0.5)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
