#!/usr/bin/env python

"""Utility to add proper nouns found in predictors to manual stopwords.

This script checks all predictor tables for phrases that have been identified
as proper nouns by the translation system and adds them to manual_stopwords.
This is a second-phase catch for proper nouns that should have been filtered
earlier in the analysis pipeline.
"""

import argparse
import sqlite3
import sys


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Add proper nouns from predictors to manual stopwords"
    )
    parser.add_argument(
        "--database",
        default="pausanias.sqlite",
        help="SQLite database file (default: pausanias.sqlite)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be added without making changes"
    )
    return parser.parse_args()


def get_proper_nouns_in_predictors(conn):
    """Find all phrases in predictor tables that are marked as proper nouns.

    Args:
        conn: Database connection

    Returns:
        Set of (phrase, table_name) tuples
    """
    proper_nouns = set()

    predictor_tables = [
        'mythicness_predictors',
        'skepticism_predictors',
        'sentence_mythicness_predictors',
        'sentence_skepticism_predictors'
    ]

    cursor = conn.cursor()

    for table in predictor_tables:
        query = f"""
        SELECT DISTINCT p.phrase
        FROM {table} p
        JOIN phrase_translations pt ON p.phrase = pt.phrase
        WHERE pt.is_proper_noun = 1
        """
        cursor.execute(query)
        results = cursor.fetchall()

        for (phrase,) in results:
            proper_nouns.add((phrase, table))

    return proper_nouns


def get_existing_stopwords(conn):
    """Get all existing manual stopwords.

    Args:
        conn: Database connection

    Returns:
        Set of stopwords
    """
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM manual_stopwords")
    return {row[0] for row in cursor.fetchall()}


def add_to_stopwords(conn, phrases):
    """Add phrases to manual_stopwords table.

    Args:
        conn: Database connection
        phrases: Iterable of phrases to add
    """
    cursor = conn.cursor()
    for phrase in phrases:
        cursor.execute(
            "INSERT OR IGNORE INTO manual_stopwords (word) VALUES (?)",
            (phrase,)
        )
    conn.commit()


def main():
    args = parse_arguments()

    conn = sqlite3.connect(args.database)

    try:
        # Find proper nouns in predictors
        proper_nouns = get_proper_nouns_in_predictors(conn)

        if not proper_nouns:
            print("No proper nouns found in predictor tables.")
            return 0

        # Get existing stopwords
        existing_stopwords = get_existing_stopwords(conn)

        # Determine which need to be added
        to_add = {phrase for phrase, _ in proper_nouns if phrase not in existing_stopwords}

        if not to_add:
            print("All proper nouns from predictors are already in manual_stopwords.")
            return 0

        # Group by table for reporting
        by_table = {}
        for phrase, table in proper_nouns:
            if phrase in to_add:
                if table not in by_table:
                    by_table[table] = []
                by_table[table].append(phrase)

        # Report findings
        print(f"Found {len(to_add)} proper noun(s) in predictor tables:")
        print()
        for table, phrases in sorted(by_table.items()):
            print(f"  {table}:")
            for phrase in sorted(phrases):
                print(f"    - {phrase}")
        print()

        if args.dry_run:
            print("DRY RUN: No changes made to database.")
            print(f"Would add {len(to_add)} phrase(s) to manual_stopwords.")
        else:
            add_to_stopwords(conn, to_add)
            print(f"Added {len(to_add)} phrase(s) to manual_stopwords.")
            print()
            print("NOTE: You should re-run your predictor analysis scripts to regenerate")
            print("      predictor tables without these proper nouns.")

        return 0

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
