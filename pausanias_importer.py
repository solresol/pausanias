#!/usr/bin/env python

import argparse
import sys
import re
import os.path

from pausanias_db import add_database_argument, connect, initialize_schema


def create_db_schema(conn):
    """Create the database schema if it doesn't exist."""
    initialize_schema(conn)

def parse_pausanias_file(file_path):
    """Parse the Pausanias file and extract sections with their IDs."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match section markers and content
        pattern = r'#(\d+\.\d+\.\d+)#\s*(.*?)(?=#\d+\.\d+\.\d+#|$)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        parsed_sections = []
        for section_id, section_text in matches:
            # Clean up the text: remove excessive whitespace and join lines
            cleaned_text = re.sub(r'\s+', ' ', section_text.strip())
            parsed_sections.append((section_id, cleaned_text))
        
        return parsed_sections
    
    except Exception as e:
        raise RuntimeError(f"Failed to parse file {file_path}: {str(e)}")

def import_passages(conn, passages):
    """Import passages into the database."""
    cursor = conn.cursor()
    
    for section_id, passage_text in passages:
        cursor.execute(
            """
            INSERT INTO passages (id, passage)
            VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE SET passage = EXCLUDED.passage
            """,
            (section_id, passage_text)
        )
    
    conn.commit()

def parse_arguments():
    parser = argparse.ArgumentParser(description="Import Pausanias passages into PostgreSQL")
    parser.add_argument("input_file", help="Text file containing marked Pausanias passages")
    add_database_argument(parser)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    input_file = args.input_file
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    
    conn = connect(args.database_url)
    
    try:
        create_db_schema(conn)
        passages = parse_pausanias_file(input_file)
        
        if not passages:
            print("Warning: No passages found in the input file.")
            sys.exit(0)
        
        import_passages(conn, passages)
        print(f"Successfully imported {len(passages)} passages into PostgreSQL")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    finally:
        conn.close()
