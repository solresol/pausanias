#!/usr/bin/env python

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime

from openai import OpenAI
from tqdm import tqdm


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Analyze Pausanias sentences using the OpenAI API"
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
        type=int,
        default=None,
        help="Maximum number of sentences to process (default: all)",
    )
    parser.add_argument(
        "--progress-bar",
        action="store_true",
        default=False,
        help="Show progress bar",
    )
    parser.add_argument(
        "--model",
        default="gpt-4.1",
        help="OpenAI model to use (default: gpt-4.1)",
    )
    return parser.parse_args()


def load_openai_api_key(key_file):
    key_path = os.path.expanduser(key_file)
    try:
        with open(key_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"OpenAI API key file not found: {key_file}")


def ensure_sentence_columns(conn):
    """Ensure analysis columns exist on the greek_sentences table."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(greek_sentences)")
    cols = {row[1] for row in cursor.fetchall()}
    if "references_mythic_era" not in cols:
        cursor.execute(
            "ALTER TABLE greek_sentences ADD COLUMN references_mythic_era BOOLEAN"
        )
    if "expresses_scepticism" not in cols:
        cursor.execute(
            "ALTER TABLE greek_sentences ADD COLUMN expresses_scepticism BOOLEAN"
        )
    conn.commit()


def get_unprocessed_sentences(conn, limit=None):
    """Retrieve sentences that haven't been analysed."""
    cursor = conn.cursor()
    query = (
        "SELECT passage_id, sentence_number, sentence, english_sentence "
        "FROM greek_sentences "
        "WHERE references_mythic_era IS NULL "
        "ORDER BY passage_id, sentence_number"
    )
    if limit:
        query += f" LIMIT {limit}"
    cursor.execute(query)
    return cursor.fetchall()


def save_analysis_results(
    conn, passage_id, sentence_number, references_mythic_era, expresses_scepticism
):
    """Persist analysis results for a sentence."""
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE greek_sentences
        SET references_mythic_era = ?, expresses_scepticism = ?
        WHERE passage_id = ? AND sentence_number = ?
        """,
        (references_mythic_era, expresses_scepticism, passage_id, sentence_number),
    )
    conn.commit()


def analyse_sentence(client, model, passage_id, sentence_number, sentence_text, english_text):
    """Analyse a sentence via the OpenAI API."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "save_annotations",
                "description": (
                    "Save the analysis of whether the sentence references the mythic era "
                    "and expresses skepticism"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "references_mythic_era": {
                            "type": "boolean",
                            "description": (
                                "Whether the sentence references the mythic era (true) "
                                "or the historical era (false)"
                            ),
                        },
                        "expresses_scepticism": {
                            "type": "boolean",
                            "description": (
                                "Whether Pausanias expresses skepticism about the "
                                "subject matter"
                            ),
                        },
                    },
                    "required": ["references_mythic_era", "expresses_scepticism"],
                },
            },
        }
    ]

    system_prompt = (
        "Act as a Pausanias scholar and report whether this sentence of Pausanias is "
        "a reference to the mythic era or historical era. Then report whether "
        "Pausanias shows scepticism about the subject matter he is writing about."
    )

    user_content = (
        f"Passage {passage_id}, sentence {sentence_number}:\n\n"
        f"Greek:\n{sentence_text}\n\nEnglish:\n{english_text}\n\n"
        "Analyse this sentence and provide your results using the save_annotations function."
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "save_annotations"}},
        )

        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        tool_calls = response.choices[0].message.tool_calls
        if tool_calls:
            function_call = tool_calls[0]
            function_args = json.loads(function_call.function.arguments)
            return (
                function_args.get("references_mythic_era"),
                function_args.get("expresses_scepticism"),
                input_tokens,
                output_tokens,
            )
        return None, None, input_tokens, output_tokens
    except Exception as e:
        print(
            f"Error analysing sentence {passage_id} #{sentence_number}: {str(e)}"
        )
        return None, None, 0, 0


def main():
    args = parse_arguments()
    api_key = load_openai_api_key(args.openai_api_key_file)
    client = OpenAI(api_key=api_key)

    conn = sqlite3.connect(args.database)
    try:
        ensure_sentence_columns(conn)
        sentences = get_unprocessed_sentences(conn, args.stop_after)
        if not sentences:
            print("No unprocessed sentences found in the database.")
            return
        print(f"Found {len(sentences)} unprocessed sentences.")
        iterator = tqdm(sentences) if args.progress_bar else sentences
        total_input_tokens = 0
        total_output_tokens = 0
        for passage_id, sentence_number, sentence_text, english_text in iterator:
            (
                references_mythic_era,
                expresses_scepticism,
                input_tokens,
                output_tokens,
            ) = analyse_sentence(
                client,
                args.model,
                passage_id,
                sentence_number,
                sentence_text,
                english_text,
            )
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            if (
                references_mythic_era is not None
                and expresses_scepticism is not None
            ):
                save_analysis_results(
                    conn,
                    passage_id,
                    sentence_number,
                    references_mythic_era,
                    expresses_scepticism,
                )
                if not args.progress_bar:
                    print(
                        f"Processed {passage_id} #{sentence_number}: mythic_era={references_mythic_era}, "
                        f"scepticism={expresses_scepticism}, tokens={input_tokens}/{output_tokens}"
                    )
            else:
                print(f"Failed to analyse {passage_id} #{sentence_number}")
            time.sleep(0.5)
        print(
            "Processing complete. Total tokens used: "
            f"{total_input_tokens} input, {total_output_tokens} output"
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
