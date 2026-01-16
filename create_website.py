#!/usr/bin/env python

"""
Entry point for website generation.
This script uses the refactored modules from the website package.
"""

import argparse
import sys
import os
from website.main import main as website_main

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
    
    return parser.parse_args()

if __name__ == '__main__':
    # Enable phrase translation by default unless explicitly disabled
    if '--no-translate-phrases' in sys.argv:
        sys.argv.remove('--no-translate-phrases')
    elif '--translate-phrases' not in sys.argv:
        sys.argv.append('--translate-phrases')

    # This script simply delegates to the refactored website module
    website_main()
