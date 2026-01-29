#!/usr/bin/env python

"""Main entry point for website generation."""

import argparse
import shutil
import sqlite3
import sys
import os
from datetime import datetime

from .data import (
    get_analyzed_passages,
    get_mythicness_predictors,
    get_skepticism_predictors,
    get_proper_nouns_by_passage,
    get_all_sentences,
    get_sentence_mythicness_predictors,
    get_sentence_skepticism_predictors,
    get_passage_mythicness_metrics,
    get_passage_skepticism_metrics,
    get_sentence_mythicness_metrics,
    get_sentence_skepticism_metrics,
    get_map_data,
    get_translation_page_data,
    get_passage_summaries,
    get_progress_data,
    add_phrase_translations,
)
from .structure import create_website_structure
from .highlighting import create_predictor_maps
from .generators import (
    generate_home_page,
    generate_mythic_page,
    generate_skepticism_page,
    generate_mythic_words_page,
    generate_skeptic_words_page,
    generate_sentences_page,
    generate_sentence_mythic_words_page,
    generate_sentence_skeptic_words_page,
    generate_map_page,
    generate_translation_pages,
    generate_progress_page,
)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Create a static website to visualize mythic and skeptical aspects of Pausanias passages")
    parser.add_argument("--database", default="pausanias.sqlite",
                        help="SQLite database file (default: pausanias.sqlite)")
    parser.add_argument("--output-dir", default="pausanias_site",
                        help="Output directory for the static website (default: pausanias_site)")
    parser.add_argument("--max-passages", type=int, default=None,
                        help="Maximum number of passages to include (default: all)")
    parser.add_argument("--title", default="Pausanias Analysis",
                        help="Title for the website (default: 'Pausanias Analysis')")
    parser.add_argument("--translate-phrases", action="store_true",
                        help="Fetch missing phrase translations using LLM (requires OpenAI API key)")
    parser.add_argument("--openai-api-key-file", default="~/.openai.key",
                        help="File containing OpenAI API key (default: ~/.openai.key)")
    parser.add_argument("--model", default="gpt-5",
                        help="OpenAI model to use for translations (default: gpt-5)")

    return parser.parse_args()

def main():
    args = parse_arguments()

    # Connect to the database
    conn = sqlite3.connect(args.database)

    # Initialize OpenAI client if translation is requested
    client = None
    if args.translate_phrases:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from phrase_translator import load_openai_api_key, create_phrase_translations_table
        from openai import OpenAI

        api_key = load_openai_api_key(args.openai_api_key_file)
        client = OpenAI(api_key=api_key)
        create_phrase_translations_table(conn)
        print("LLM translation enabled for missing phrase translations")

    try:
        # Get data from database
        passages_df = get_analyzed_passages(conn, args.max_passages)
        mythic_predictors = get_mythicness_predictors(conn)
        skeptic_predictors = get_skepticism_predictors(conn)
        proper_nouns_dict = get_proper_nouns_by_passage(conn)
        sentences_df = get_all_sentences(conn)
        sentence_mythic_predictors = get_sentence_mythicness_predictors(conn)
        sentence_skeptic_predictors = get_sentence_skepticism_predictors(conn)

        # Get classification metrics
        passage_mythic_metrics = get_passage_mythicness_metrics(conn)
        passage_skeptic_metrics = get_passage_skepticism_metrics(conn)
        sentence_mythic_metrics = get_sentence_mythicness_metrics(conn)
        sentence_skeptic_metrics = get_sentence_skepticism_metrics(conn)
        
        if len(passages_df) == 0:
            print("No analyzed passages found in the database.")
            sys.exit(0)
        
        if len(mythic_predictors) == 0 or len(skeptic_predictors) == 0:
            print("No passage-level predictor data found in the database. Run the analysis program first.")
            sys.exit(1)

        if len(sentence_mythic_predictors) == 0 or len(sentence_skeptic_predictors) == 0:
            print("No sentence-level predictor data found in the database. Run the sentence analysis program.")
            sys.exit(1)

        print(f"Found {len(passages_df)} analyzed passages.")
        print(f"Found {len(mythic_predictors)} mythicness predictors.")
        print(f"Found {len(skeptic_predictors)} skepticism predictors.")
        print(f"Found {len(sentence_mythic_predictors)} sentence-level mythicness predictors.")
        print(f"Found {len(sentence_skeptic_predictors)} sentence-level skepticism predictors.")

        # Add translations to predictors
        print("Adding phrase translations...")
        mythic_predictors = add_phrase_translations(mythic_predictors, conn, client, args.model)
        skeptic_predictors = add_phrase_translations(skeptic_predictors, conn, client, args.model)
        sentence_mythic_predictors = add_phrase_translations(sentence_mythic_predictors, conn, client, args.model)
        sentence_skeptic_predictors = add_phrase_translations(sentence_skeptic_predictors, conn, client, args.model)
        
        # Create website structure
        output_dir, css_dir = create_website_structure(args.output_dir)
        
        # Create color and class maps for highlighting
        mythic_color_map, skeptic_color_map, mythic_class_map, skeptic_class_map = create_predictor_maps(
            mythic_predictors, skeptic_predictors
        )
        
        # Get timestamp for the website
        timestamp = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
        
        # Generate all pages
        generate_home_page(output_dir, args.title, timestamp)
        generate_mythic_page(passages_df, mythic_color_map, mythic_class_map, proper_nouns_dict, output_dir, args.title)
        generate_skepticism_page(passages_df, skeptic_color_map, skeptic_class_map, proper_nouns_dict, output_dir, args.title)
        generate_mythic_words_page(mythic_predictors, output_dir, args.title, passage_mythic_metrics)
        generate_skeptic_words_page(skeptic_predictors, output_dir, args.title, passage_skeptic_metrics)
        generate_sentences_page(sentences_df, output_dir, args.title)
        generate_sentence_mythic_words_page(sentence_mythic_predictors, output_dir, args.title, sentence_mythic_metrics)
        generate_sentence_skeptic_words_page(sentence_skeptic_predictors, output_dir, args.title, sentence_skeptic_metrics)

        # Generate place map
        map_data = get_map_data(conn)
        generate_map_page(map_data, output_dir, args.title)

        # Generate translation pages
        translation_passages, nouns_by_passage, noun_passages = get_translation_page_data(conn)
        passage_summaries = get_passage_summaries(conn)
        generate_translation_pages(translation_passages, nouns_by_passage, noun_passages, output_dir, args.title, passage_summaries)

        # Generate progress page
        progress_data = get_progress_data(conn)
        generate_progress_page(progress_data, output_dir, args.title)

        # Copy PDF book if it exists
        pdf_source = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pausanias_book", "pausanias.pdf")
        if os.path.exists(pdf_source):
            shutil.copy2(pdf_source, os.path.join(output_dir, "pausanias.pdf"))
            print("PDF book copied to website.")

        print(f"Website generated successfully in '{output_dir}'")
        print(f"Open '{os.path.join(output_dir, 'index.html')}' in a web browser to view it.")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    
    finally:
        conn.close()
        
if __name__ == '__main__':
    import os
    main()
