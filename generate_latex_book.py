#!/usr/bin/env python3
"""Generate a LaTeX book from Pausanias translations."""

import os
import re
import sqlite3
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np

from website.data import get_translation_page_data, passage_id_sort_key


# Book titles (traditional names for each book of Pausanias)
BOOK_TITLES = {
    1: "Attica",
    2: "Corinth",
    3: "Laconia",
    4: "Messenia",
    5: "Elis I",
    6: "Elis II",
    7: "Achaia",
    8: "Arcadia",
    9: "Boeotia",
    10: "Phocis",
}

OUTPUT_DIR = "pausanias_book"


def escape_latex(text):
    """Escape special LaTeX characters in text."""
    if not text:
        return ""

    # Handle smart quotes and em-dashes first (before filtering)
    text = text.replace('"', '"')
    text = text.replace('"', '"')
    text = text.replace(''', "'")
    text = text.replace(''', "'")
    text = text.replace('—', '--')
    text = text.replace('–', '-')

    # Remove any non-Latin-1 characters (e.g., corrupted Unicode)
    # Keep ASCII + Latin-1 supplement (accented Latin letters)
    cleaned = []
    for char in text:
        if ord(char) < 256:  # Latin-1 range
            cleaned.append(char)
        # else: skip the character
    text = ''.join(cleaned)

    # Order matters: backslash first, then others
    replacements = [
        ('\\', r'\textbackslash{}'),
        ('&', r'\&'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('#', r'\#'),
        ('_', r'\_'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\textasciicircum{}'),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    # Convert straight quotes to LaTeX quotes
    # Simple approach: alternate opening/closing
    text = re.sub(r'"([^"]*)"', r"``\1''", text)

    return text


def get_places_for_book(conn, book_num):
    """Get all places with coordinates mentioned in a specific book."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT pc.reference_form, pc.english_transcription,
               pc.latitude, pc.longitude
        FROM proper_nouns pn
        JOIN wikidata_links w ON pn.reference_form = w.reference_form
            AND pn.entity_type = w.entity_type
        JOIN place_coordinates pc ON w.wikidata_qid = pc.wikidata_qid
        WHERE pn.entity_type = 'place'
        AND pn.passage_id LIKE ?
        AND pc.latitude IS NOT NULL
        AND pc.longitude IS NOT NULL
    """, (f"{book_num}.%",))

    places = []
    for ref_form, english, lat, lon in cursor.fetchall():
        places.append({
            "name": english or ref_form,
            "lat": lat,
            "lon": lon
        })

    return places


def generate_book_map(book_num, places, output_dir):
    """Generate a map image for a book showing mentioned places."""

    if not places:
        return None

    # Extract coordinates
    lats = [p["lat"] for p in places]
    lons = [p["lon"] for p in places]
    names = [p["name"] for p in places]

    # Set up the figure with a nice style
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(6, 5), dpi=150)

    # Calculate bounds with padding
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    lat_pad = (lat_max - lat_min) * 0.15 + 0.5
    lon_pad = (lon_max - lon_min) * 0.15 + 0.5

    ax.set_xlim(lon_min - lon_pad, lon_max + lon_pad)
    ax.set_ylim(lat_min - lat_pad, lat_max + lat_pad)

    # Plot places
    ax.scatter(lons, lats, c='#8B0000', s=30, zorder=5, alpha=0.7)

    # Add labels for places (limit to avoid overcrowding)
    if len(places) <= 30:
        for name, lat, lon in zip(names, lats, lons):
            # Truncate long names
            display_name = name[:15] + "..." if len(name) > 15 else name
            ax.annotate(display_name, (lon, lat), fontsize=6,
                       xytext=(3, 3), textcoords='offset points',
                       alpha=0.8)

    # Style the map
    ax.set_xlabel('Longitude', fontsize=8)
    ax.set_ylabel('Latitude', fontsize=8)
    ax.tick_params(labelsize=7)

    title = BOOK_TITLES.get(book_num, f"Book {book_num}")
    ax.set_title(f"Places in Book {book_num}: {title}", fontsize=10, fontweight='bold')

    # Add a simple Greece outline hint with aspect ratio
    ax.set_aspect('equal', adjustable='box')

    # Save
    map_path = os.path.join(output_dir, f"map{book_num}.pdf")
    plt.savefig(map_path, bbox_inches='tight', pad_inches=0.1)
    plt.close()

    return f"map{book_num}.pdf"


def generate_preamble():
    """Generate preamble.tex with packages and custom commands."""

    preamble = r"""\documentclass[11pt,twoside,openright,a4paper]{memoir}

% Encoding and fonts
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{ebgaramond}
\usepackage{microtype}

% Layout
\usepackage{marginnote}
\usepackage{xcolor}
\usepackage{pifont}  % For symbols
\usepackage{graphicx}  % For maps

% Index - multiple indices
\usepackage{imakeidx}
\makeindex[name=people,title=Index of People,intoc]
\makeindex[name=places,title=Index of Places,intoc]
\makeindex[name=deities,title=Index of Deities,intoc]

% Hyperlinks (load last)
\usepackage[hidelinks,pdfusetitle]{hyperref}

% Colors for margin icons
\definecolor{mythicred}{HTML}{8B0000}
\definecolor{skepticgreen}{HTML}{006400}

% Margin icons - appear in outer margin
\newcommand{\mythic}{\marginnote{\textcolor{mythicred}{\ding{72}}}}
\newcommand{\skeptic}{\marginnote{\textcolor{skepticgreen}{\textbf{?}}}}

% Passage command - creates a labeled subsection
\newcommand{\passage}[1]{%
  \subsection*{#1}%
  \phantomsection%
  \label{p:#1}%
}

% Index entry commands (invisible - just add to index)
\newcommand{\person}[1]{\index[people]{#1}}
\newcommand{\place}[1]{\index[places]{#1}}
\newcommand{\deity}[1]{\index[deities]{#1}}

% Page layout - generous margins for notes
\setlrmarginsandblock{1in}{1.5in}{*}
\setulmarginsandblock{1.2in}{1.2in}{*}
\checkandfixthelayout

% Chapter style
\chapterstyle{bianchi}

% Part style - cleaner look
\renewcommand{\partnamefont}{\normalfont\Large\scshape}
\renewcommand{\partnumfont}{\normalfont\Large\scshape}
\renewcommand{\parttitlefont}{\normalfont\Huge\scshape}

% Running headers
\makepagestyle{pausanias}
\makeevenhead{pausanias}{\thepage}{}{\leftmark}
\makeoddhead{pausanias}{\rightmark}{}{\thepage}
\makeevenfoot{pausanias}{}{}{}
\makeoddfoot{pausanias}{}{}{}
\pagestyle{pausanias}

% PDF metadata
\hypersetup{
  pdftitle={Description of Greece},
  pdfauthor={Pausanias},
  pdfsubject={Ancient Greek Travel Writing},
}
"""

    return preamble


def generate_titlepage():
    """Generate titlepage.tex with elegant title page design."""

    titlepage = r"""\begin{titlingpage}
\begin{center}

\vspace*{2in}

{\Huge\scshape Pausanias}

\vspace{0.5in}

{\LARGE Description of Greece}

\vspace{1.5in}

{\large English Translation}

\vspace{0.5in}

\rule{2in}{0.4pt}

\vspace{2in}

{\small Generated from the Pausanias Analysis Project}

\end{center}
\end{titlingpage}
"""

    return titlepage


def generate_book_content(book_num, passages, nouns_by_passage, map_file=None):
    """Generate content for one book (bookN.tex)."""

    title = BOOK_TITLES.get(book_num, f"Book {book_num}")

    # Filter passages for this book
    book_passages = []
    for p in passages:
        parts = p["id"].split(".")
        if int(parts[0]) == book_num:
            book_passages.append(p)

    # Sort by passage ID
    book_passages.sort(key=lambda p: passage_id_sort_key(p["id"]))

    # Group by chapter
    chapters = defaultdict(list)
    for p in book_passages:
        parts = p["id"].split(".")
        chapter_num = int(parts[1])
        chapters[chapter_num].append(p)

    # Generate LaTeX
    lines = []
    lines.append(f"\\part{{Book {book_num}: {title}}}")
    lines.append("")

    # Include map if available
    if map_file:
        lines.append("\\begin{figure}[h]")
        lines.append("\\centering")
        lines.append(f"\\includegraphics[width=0.85\\textwidth]{{{map_file}}}")
        lines.append(f"\\caption{{Places mentioned in Book {book_num}: {title}}}")
        lines.append("\\end{figure}")
        lines.append("\\clearpage")
        lines.append("")

    # Track which nouns we've indexed in this book (to avoid duplicates)
    indexed_nouns = {"people": set(), "places": set(), "deities": set()}

    for chapter_num in sorted(chapters.keys()):
        lines.append(f"\\chapter{{Chapter {chapter_num}}}")
        lines.append("")

        for p in chapters[chapter_num]:
            passage_id = p["id"]

            # Build passage header with margin icons
            icons = []
            if p.get("is_mythic"):
                icons.append("\\mythic")
            if p.get("is_skeptical"):
                icons.append("\\skeptic")

            icon_str = "".join(icons)
            lines.append(f"\\passage{{{passage_id}}}{icon_str}")

            # Translation text
            english = p.get("english") or ""
            english = escape_latex(english)
            lines.append(english)

            # Add index entries for proper nouns
            if passage_id in nouns_by_passage:
                index_entries = []
                for noun in nouns_by_passage[passage_id]:
                    english_name = noun.get("english") or ""
                    if not english_name:
                        continue

                    entity_type = (noun.get("entity_type") or "").lower()

                    # Map entity types to index categories
                    if entity_type in ("person", "people", "people group"):
                        idx_name = "people"
                    elif entity_type == "place":
                        idx_name = "places"
                    elif entity_type == "deity":
                        idx_name = "deities"
                    else:
                        continue  # Skip 'other', 'epithet', etc.

                    # Only index each noun once per book
                    if english_name not in indexed_nouns[idx_name]:
                        indexed_nouns[idx_name].add(english_name)
                        safe_name = escape_latex(english_name)
                        # Remove any @ signs which have special meaning in index
                        safe_name = safe_name.replace("@", "")
                        index_entries.append(f"\\index[{idx_name}]{{{safe_name}}}")

                if index_entries:
                    lines.append("% Index entries")
                    lines.append("".join(index_entries))

            lines.append("")

    return "\n".join(lines)


def generate_main_document(book_nums):
    """Generate pausanias.tex main document."""

    main = r"""\input{preamble}

\begin{document}

\input{titlepage}

\frontmatter
\tableofcontents

\mainmatter

"""

    for book_num in book_nums:
        main += f"\\input{{book{book_num}}}\n"

    main += r"""
\backmatter

% Print indices
\printindex[people]
\printindex[places]
\printindex[deities]

\end{document}
"""

    return main


def generate_makefile():
    """Generate Makefile for building the PDF."""

    makefile = """# Makefile for Pausanias LaTeX book

LATEX = pdflatex
MAKEINDEX = makeindex

all: pausanias.pdf

pausanias.pdf: pausanias.tex preamble.tex titlepage.tex book*.tex
\t$(LATEX) pausanias.tex
\t$(MAKEINDEX) people.idx
\t$(MAKEINDEX) places.idx
\t$(MAKEINDEX) deities.idx
\t$(LATEX) pausanias.tex
\t$(LATEX) pausanias.tex

clean:
\trm -f *.aux *.log *.toc *.idx *.ind *.ilg *.out pausanias.pdf

.PHONY: all clean
"""

    return makefile


def main():
    """Generate all LaTeX files."""

    # Connect to database
    conn = sqlite3.connect("pausanias.sqlite")

    # Get data
    print("Fetching translation data...")
    passages, nouns_by_passage, noun_passages = get_translation_page_data(conn)

    print(f"Found {len(passages)} passages")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate preamble
    print("Generating preamble.tex...")
    with open(os.path.join(OUTPUT_DIR, "preamble.tex"), "w", encoding="utf-8") as f:
        f.write(generate_preamble())

    # Generate title page
    print("Generating titlepage.tex...")
    with open(os.path.join(OUTPUT_DIR, "titlepage.tex"), "w", encoding="utf-8") as f:
        f.write(generate_titlepage())

    # Determine which books exist
    book_nums = set()
    for p in passages:
        parts = p["id"].split(".")
        book_nums.add(int(parts[0]))
    book_nums = sorted(book_nums)

    # Generate maps for each book
    print("Generating maps...")
    book_maps = {}
    for book_num in book_nums:
        places = get_places_for_book(conn, book_num)
        if places:
            map_file = generate_book_map(book_num, places, OUTPUT_DIR)
            book_maps[book_num] = map_file
            print(f"  Book {book_num}: {len(places)} places")
        else:
            print(f"  Book {book_num}: no places with coordinates")

    # Generate each book file
    for book_num in book_nums:
        print(f"Generating book{book_num}.tex...")
        map_file = book_maps.get(book_num)
        content = generate_book_content(book_num, passages, nouns_by_passage, map_file)
        with open(os.path.join(OUTPUT_DIR, f"book{book_num}.tex"), "w", encoding="utf-8") as f:
            f.write(content)

    # Generate main document
    print("Generating pausanias.tex...")
    with open(os.path.join(OUTPUT_DIR, "pausanias.tex"), "w", encoding="utf-8") as f:
        f.write(generate_main_document(book_nums))

    # Generate Makefile
    print("Generating Makefile...")
    with open(os.path.join(OUTPUT_DIR, "Makefile"), "w", encoding="utf-8") as f:
        f.write(generate_makefile())

    conn.close()

    print(f"\nLaTeX files generated in '{OUTPUT_DIR}/'")
    print(f"To build PDF: cd {OUTPUT_DIR} && make")


if __name__ == "__main__":
    main()
