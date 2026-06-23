#!/usr/bin/env python3
"""Generate a LaTeX book from Pausanias translations."""

import argparse
import os
import re
from collections import defaultdict
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np

from website.data import get_translation_page_data, passage_id_sort_key
from pausanias_db import add_database_argument, connect


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

CHECKLIST_TEX = "pausanias-greek-checklist.tex"
PARALLEL_TEX = "pausanias-greek-english-parallel.tex"
GREEK_TEX = "pausanias-greek.tex"
GREEK_PREAMBLE_TEX = "greek-preamble.tex"
GREEK_TITLEPAGE_TEX = "greek-titlepage.tex"
GREEK_BOOK_PREFIX = "greek-book"
CHECKLIST_PDF = "pausanias-greek-checklist.pdf"
PARALLEL_PDF = "pausanias-greek-english-parallel.pdf"
GREEK_PDF = "pausanias-greek.pdf"
APRILTAG_FAMILY = "tagStandard52h13"
APRILTAG_IMAGE_DIR = "apriltags/tagstandard52h13"
APRILTAG_PNG_SCALE = 10
APRILTAG_WIDTH = "6mm"
CHECKBOX_SIZE = "4mm"
CHECKBOX_FIELDS = [
    ("epichoric", "Has epichoric sources"),
    ("mythic", "Mythic"),
    ("historic", "Historic"),
]
GREEK_INDEX_NAMES = {
    "passages": "gpassages",
    "people": "gpeople",
    "places": "gplaces",
    "deities": "gdeities",
}


def escape_latex(text):
    """Escape special LaTeX characters in text."""
    if not text:
        return ""

    # Handle smart quotes and dashes first (before filtering).
    text = text.replace("\u201c", '"')
    text = text.replace("\u201d", '"')
    text = text.replace("\u2018", "'")
    text = text.replace("\u2019", "'")
    text = text.replace("\u2014", "--")
    text = text.replace("\u2013", "-")

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


def escape_xelatex(text):
    """Escape TeX control characters while preserving Unicode Greek."""
    if not text:
        return ""

    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    escaped = str(text)
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def clean_makeindex_value(text):
    """Escape TeX content and remove MakeIndex control characters."""
    cleaned = escape_xelatex(text)
    for special in ('"', "@", "!", "|"):
        cleaned = cleaned.replace(special, "")
    return " ".join(cleaned.split())


def passage_index_sort_key(passage_id):
    """Return a numeric-sortable MakeIndex key for a passage identifier."""
    parts = [int(part) for part in str(passage_id).split(".")]
    return ".".join(f"{part:03d}" for part in parts)


def make_index_entry(index_name, sort_text, display_text=None):
    """Return a MakeIndex entry with a stable sort key and display text."""
    sort_key = clean_makeindex_value(sort_text) or "Unknown"
    display = clean_makeindex_value(display_text if display_text is not None else sort_text)
    if display and display != sort_key:
        return rf"\index[{index_name}]{{{sort_key}@{display}}}"
    return rf"\index[{index_name}]{{{sort_key}}}"


def noun_index_display(noun):
    """Return display/sort labels for a proper noun index entry."""
    reference_form = str(noun.get("reference_form") or "").strip()
    english_name = str(noun.get("english") or "").strip()
    sort_name = english_name or reference_form or "Unknown"
    if english_name and reference_form and english_name != reference_form:
        return sort_name, f"{english_name} ({reference_form})"
    return sort_name, sort_name


def get_sentence_page_data(conn, limit=None):
    """Return aligned Greek and English sentence rows for PDF outputs."""
    query = """
        SELECT passage_id, sentence_number, sentence, english_sentence
        FROM greek_sentences
        ORDER BY split_part(passage_id, '.', 1)::int,
                 split_part(passage_id, '.', 2)::int,
                 split_part(passage_id, '.', 3)::int,
                 sentence_number
    """
    params = ()
    if limit is not None:
        query += "\n        LIMIT %s"
        params = (limit,)

    cursor = conn.cursor()
    cursor.execute(query, params)
    return [
        {
            "passage_id": passage_id,
            "sentence_number": sentence_number,
            "greek": greek,
            "english": english,
        }
        for passage_id, sentence_number, greek, english in cursor.fetchall()
    ]


def sentence_identifier(sentence):
    """Format a compact, stable sentence identifier for PDF tables."""
    return f"{sentence['passage_id']} s{int(sentence['sentence_number'])}"


def april_tag_id_pair(row_number):
    """Return a distinct left/right AprilTag ID pair for one sentence row."""
    first_id = (int(row_number) - 1) * 2
    return first_id, first_id + 1


def april_tag_relative_path(tag_id):
    """Return the TeX-relative PNG path for an AprilTag ID."""
    return f"{APRILTAG_IMAGE_DIR}/tag-{int(tag_id):05d}.png"


def ensure_apriltag_images(output_dir, sentence_count):
    """Generate the AprilTag PNGs needed by the Greek checklist."""
    if sentence_count <= 0:
        return 0

    try:
        from moms_apriltag import TagGenerator3
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "moms-apriltag is required to generate checklist AprilTag images. "
            "Run `uv sync` to install project dependencies."
        ) from exc

    generator = TagGenerator3(APRILTAG_FAMILY)
    required_tag_count = sentence_count * 2
    if required_tag_count > generator.max_id:
        raise ValueError(
            f"{APRILTAG_FAMILY} provides {generator.max_id:,} tags, but "
            f"{required_tag_count:,} are required for {sentence_count:,} sentences."
        )

    image_dir = os.path.join(output_dir, APRILTAG_IMAGE_DIR)
    os.makedirs(image_dir, exist_ok=True)

    generated = 0
    for tag_id in range(required_tag_count):
        path = os.path.join(output_dir, april_tag_relative_path(tag_id))
        if os.path.exists(path):
            continue
        tag = np.asarray(generator.generate(tag_id, scale=APRILTAG_PNG_SCALE), dtype=np.uint8)
        Image.fromarray(tag).save(path)
        generated += 1
    return generated


def checkbox_heading_row():
    """Return the checklist table header row."""
    headings = " & ".join(escape_xelatex(label) for _field_name, label in CHECKBOX_FIELDS)
    return rf"Sentence & Greek & Left tag & {headings} & Right tag \\"


def generate_xelatex_table_preamble(title, *, landscape=True):
    """Generate a standalone XeLaTeX preamble for Unicode sentence PDFs."""
    page_orientation = ",landscape" if landscape else ""
    safe_title = escape_xelatex(title)
    return rf"""\documentclass[10pt,a4paper{page_orientation}]{{article}}
\usepackage{{fontspec}}
\setmainfont{{FreeSerif.otf}}[
  BoldFont={{FreeSerifBold.otf}},
  ItalicFont={{FreeSerifItalic.otf}},
  BoldItalicFont={{FreeSerifBoldItalic.otf}}
]
\usepackage[margin=10mm]{{geometry}}
\usepackage{{amssymb}}
\usepackage{{array}}
\usepackage{{booktabs}}
\usepackage{{graphicx}}
\usepackage{{longtable}}
\usepackage{{microtype}}
\usepackage{{fancyhdr}}
\usepackage[hidelinks,pdfusetitle]{{hyperref}}

\hypersetup{{
  pdftitle={{{safe_title}}},
  pdfauthor={{Pausanias Analysis Project}},
  pdfsubject={{Pausanias sentence review output}},
}}

\pagestyle{{fancy}}
\fancyhf{{}}
\lhead{{{safe_title}}}
\rhead{{\thepage}}
\renewcommand{{\headrulewidth}}{{0.3pt}}
\setlength{{\headheight}}{{13pt}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\tabcolsep}}{{3pt}}
\renewcommand{{\arraystretch}}{{1.18}}
\newcolumntype{{L}}[1]{{>{{\raggedright\arraybackslash}}p{{#1}}}}
\newcolumntype{{C}}[1]{{>{{\centering\arraybackslash}}p{{#1}}}}
\newcommand{{\apriltagimage}}[1]{{\includegraphics[width={APRILTAG_WIDTH}]{{#1}}}}
\newlength{{\reviewboxsize}}
\setlength{{\reviewboxsize}}{{{CHECKBOX_SIZE}}}
\newcommand{{\reviewbox}}{{%
  \begingroup
  \setlength{{\fboxsep}}{{0pt}}%
  \raisebox{{-0.45mm}}{{\fbox{{\rule{{0pt}}{{\reviewboxsize}}\rule{{\reviewboxsize}}{{0pt}}}}}}%
  \endgroup
}}
\emergencystretch=3em
"""


def generate_greek_checklist_document(sentences, generated_at=None):
    """Generate the Greek-only sentence checklist PDF source."""
    generated_at = generated_at or datetime.now()
    title = "Pausanias Greek Sentence Checklist"
    lines = [
        generate_xelatex_table_preamble(title, landscape=True),
        r"\begin{document}",
        rf"\section*{{{escape_xelatex(title)}}}",
        (
            rf"\small Generated {escape_xelatex(generated_at.strftime('%Y-%m-%d %H:%M'))}. "
            r"Each row is one Greek sentence; the checkbox group is bracketed by sentence-specific AprilTags."
        ),
        r"\footnotesize",
        (
            r"\begin{longtable}{L{0.075\linewidth} L{0.53\linewidth} "
            r"C{0.045\linewidth} C{0.085\linewidth} C{0.055\linewidth} "
            r"C{0.06\linewidth} C{0.045\linewidth}}"
        ),
        r"\toprule",
        checkbox_heading_row(),
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        checkbox_heading_row(),
        r"\midrule",
        r"\endhead",
        r"\midrule",
        r"\multicolumn{7}{r}{Continued on next page} \\",
        r"\midrule",
        r"\endfoot",
        r"\bottomrule",
        r"\endlastfoot",
    ]

    for row_number, sentence in enumerate(sentences, start=1):
        left_tag_id, right_tag_id = april_tag_id_pair(row_number)
        checkbox_cells = [r"\reviewbox" for _field in CHECKBOX_FIELDS]
        lines.append(
            " & ".join(
                [
                    rf"\texttt{{{escape_xelatex(sentence_identifier(sentence))}}}",
                    escape_xelatex(sentence["greek"]),
                    rf"\apriltagimage{{{april_tag_relative_path(left_tag_id)}}}",
                    *checkbox_cells,
                    rf"\apriltagimage{{{april_tag_relative_path(right_tag_id)}}}",
                ]
            )
            + r" \\"
        )

    lines.extend([r"\end{longtable}", r"\end{document}", ""])
    return "\n".join(lines)


def generate_parallel_document(sentences, generated_at=None):
    """Generate the Greek/English parallel sentence PDF source."""
    generated_at = generated_at or datetime.now()
    title = "Pausanias Greek-English Parallel Sentences"
    lines = [
        generate_xelatex_table_preamble(title, landscape=True),
        r"\begin{document}",
        rf"\section*{{{escape_xelatex(title)}}}",
        rf"\small Generated {escape_xelatex(generated_at.strftime('%Y-%m-%d %H:%M'))}.",
        r"\footnotesize",
        r"\begin{longtable}{L{0.075\linewidth} L{0.44\linewidth} L{0.44\linewidth}}",
        r"\toprule",
        r"Sentence & Greek & English \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"Sentence & Greek & English \\",
        r"\midrule",
        r"\endhead",
        r"\midrule",
        r"\multicolumn{3}{r}{Continued on next page} \\",
        r"\midrule",
        r"\endfoot",
        r"\bottomrule",
        r"\endlastfoot",
    ]

    for sentence in sentences:
        lines.append(
            " & ".join(
                [
                    rf"\texttt{{{escape_xelatex(sentence_identifier(sentence))}}}",
                    escape_xelatex(sentence["greek"]),
                    escape_xelatex(sentence["english"]),
                ]
            )
            + r" \\"
        )

    lines.extend([r"\end{longtable}", r"\end{document}", ""])
    return "\n".join(lines)


def generate_greek_book_preamble():
    """Generate a Unicode-capable preamble for the Greek text PDF."""
    return r"""\documentclass[11pt,twoside,openright,a4paper]{memoir}

\usepackage{fontspec}
\setmainfont{FreeSerif.otf}[
  BoldFont={FreeSerifBold.otf},
  ItalicFont={FreeSerifItalic.otf},
  BoldItalicFont={FreeSerifBoldItalic.otf}
]
\setsansfont{FreeSans.otf}[
  BoldFont={FreeSansBold.otf},
  ItalicFont={FreeSansOblique.otf},
  BoldItalicFont={FreeSansBoldOblique.otf}
]
\setmonofont{lmmono10-regular.otf}

\usepackage{microtype}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{needspace}
\usepackage{imakeidx}
\usepackage[hidelinks,pdfusetitle]{hyperref}

\makeindex[name=gpassages,title=Index of Passages,intoc]
\makeindex[name=gpeople,title=Index of People,intoc]
\makeindex[name=gplaces,title=Index of Places,intoc]
\makeindex[name=gdeities,title=Index of Deities,intoc]

\definecolor{pausaniasblue}{HTML}{1F4E5F}
\definecolor{passagegray}{HTML}{666666}

\setlrmarginsandblock{0.75in}{0.85in}{*}
\setulmarginsandblock{1.0in}{1.05in}{*}
\checkandfixthelayout

\chapterstyle{bianchi}
\renewcommand{\partnamefont}{\normalfont\Large\scshape}
\renewcommand{\partnumfont}{\normalfont\Large\scshape}
\renewcommand{\parttitlefont}{\normalfont\Huge\scshape}

\setlength{\parindent}{0pt}
\setlength{\parskip}{0.55\baselineskip}
\emergencystretch=4em
\tolerance=2500
\newcommand{\passageheading}[1]{%
  \par\needspace{3\baselineskip}%
  \phantomsection%
  {\small\color{pausaniasblue}\texttt{#1}}\quad%
}
\newcommand{\greektext}[1]{{\large #1\par}}

\nouppercaseheads
\renewcommand{\chaptermark}[1]{\markright{#1}}
\renewcommand{\partmark}[1]{\markboth{#1}{}}
\makepagestyle{pausaniasgreek}
\makeevenhead{pausaniasgreek}{\thepage}{}{\scshape\leftmark}
\makeoddhead{pausaniasgreek}{\itshape\rightmark}{}{\thepage}
\makeevenfoot{pausaniasgreek}{}{}{}
\makeoddfoot{pausaniasgreek}{}{}{}
\pagestyle{pausaniasgreek}

\hypersetup{
  pdftitle={Pausanias: Description of Greece - Greek Text},
  pdfauthor={Pausanias},
  pdfsubject={Ancient Greek Travel Writing},
}
"""


def generate_greek_titlepage(generated_at=None):
    """Generate title page source for the Greek-only PDF."""
    generated_at = generated_at or datetime.now()
    generated = escape_xelatex(generated_at.strftime("%Y-%m-%d"))
    return rf"""\begin{{titlingpage}}
\begin{{center}}

\vspace*{{1.6in}}

{{\Huge\scshape Pausanias}}

\vspace{{0.35in}}

{{\LARGE Description of Greece}}

\vspace{{0.55in}}

{{\Large Greek Text}}

\vspace{{0.9in}}

\rule{{2.4in}}{{0.4pt}}

\vspace{{0.55in}}

\begin{{minipage}}{{0.72\textwidth}}
\centering
{{\small Continuous Greek text arranged by book, chapter, and passage, with
book maps, a passage index, and proper-noun indices for people, places, and
deities.}}
\end{{minipage}}

\vfill

{{\small Generated {generated} from the Pausanias Analysis Project}}

\end{{center}}
\end{{titlingpage}}
"""


def generate_greek_index_entries(passage_id, nouns_by_passage, indexed_nouns):
    """Return Greek-PDF index entries for one passage."""
    entries = [make_index_entry(GREEK_INDEX_NAMES["passages"], passage_index_sort_key(passage_id), passage_id)]

    for noun in nouns_by_passage.get(passage_id, []):
        entity_type = (noun.get("entity_type") or "").lower()
        if entity_type in ("person", "people", "people group"):
            idx_name = GREEK_INDEX_NAMES["people"]
        elif entity_type == "place":
            idx_name = GREEK_INDEX_NAMES["places"]
        elif entity_type == "deity":
            idx_name = GREEK_INDEX_NAMES["deities"]
        else:
            continue

        sort_name, display_name = noun_index_display(noun)
        noun_key = (idx_name, sort_name, display_name)
        if noun_key in indexed_nouns:
            continue
        indexed_nouns.add(noun_key)
        entries.append(make_index_entry(idx_name, sort_name, display_name))

    return entries


def generate_greek_book_content(book_num, passages, nouns_by_passage, map_file=None):
    """Generate Greek content for one book."""
    title = BOOK_TITLES.get(book_num, f"Book {book_num}")

    book_passages = []
    for passage in passages:
        parts = passage["id"].split(".")
        if int(parts[0]) == book_num:
            book_passages.append(passage)
    book_passages.sort(key=lambda passage: passage_id_sort_key(passage["id"]))

    chapters = defaultdict(list)
    for passage in book_passages:
        chapter_num = int(passage["id"].split(".")[1])
        chapters[chapter_num].append(passage)

    lines = [
        rf"\part{{Book {book_num}: {escape_xelatex(title)}}}",
        r"\setcounter{chapter}{0}",
        "",
    ]

    if map_file:
        lines.extend(
            [
                r"\begin{figure}[h]",
                r"\centering",
                rf"\includegraphics[width=0.82\textwidth]{{{map_file}}}",
                rf"\caption{{Places mentioned in Book {book_num}: {escape_xelatex(title)}}}",
                r"\end{figure}",
                r"\clearpage",
                "",
            ]
        )

    indexed_nouns = set()
    for chapter_num in sorted(chapters):
        lines.extend([rf"\chapter{{Chapter {chapter_num}}}", ""])

        for passage in chapters[chapter_num]:
            passage_id = passage["id"]
            greek = escape_xelatex(passage.get("greek") or "")
            index_entries = generate_greek_index_entries(passage_id, nouns_by_passage, indexed_nouns)
            lines.append(rf"\passageheading{{{escape_xelatex(passage_id)}}}{''.join(index_entries)}")
            lines.append(rf"\greektext{{{greek}}}")
            lines.append("")

    return "\n".join(lines)


def generate_greek_main_document(book_nums):
    """Generate the Greek-only main document."""
    lines = [
        rf"\input{{{GREEK_PREAMBLE_TEX.removesuffix('.tex')}}}",
        r"\begin{document}",
        rf"\input{{{GREEK_TITLEPAGE_TEX.removesuffix('.tex')}}}",
        r"\frontmatter",
        r"\tableofcontents",
        r"\mainmatter",
        "",
    ]
    for book_num in book_nums:
        lines.append(rf"\input{{{GREEK_BOOK_PREFIX}{book_num}}}")
    lines.extend(
        [
            "",
            r"\backmatter",
            r"\printindex[gpassages]",
            r"\printindex[gpeople]",
            r"\printindex[gplaces]",
            r"\printindex[gdeities]",
            r"\end{document}",
            "",
        ]
    )
    return "\n".join(lines)


def get_places_for_book(conn, book_num):
    """Get all places with coordinates mentioned in a specific book."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT pn.reference_form, pn.english_transcription,
               e.latitude, e.longitude
        FROM proper_nouns pn
        JOIN wikidata_links w ON pn.reference_form = w.reference_form
            AND pn.entity_type = w.entity_type
        JOIN wikidata_entities e ON w.wikidata_qid = e.wikidata_qid
        WHERE pn.entity_type = 'place'
        AND pn.passage_id LIKE %s
        AND e.latitude IS NOT NULL
        AND e.longitude IS NOT NULL
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
\nouppercaseheads
\renewcommand{\chaptermark}[1]{\markright{#1}}
\renewcommand{\partmark}[1]{}
\makepagestyle{pausanias}
\makeevenhead{pausanias}{\thepage}{}{\scshape Book \thepart}
\makeoddhead{pausanias}{\itshape\rightmark}{}{\thepage}
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
    lines.append("\\setcounter{chapter}{0}")
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

            lines.append(f"\\passage{{{passage_id}}}")

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
    """Generate Makefile for building the PDF outputs."""

    makefile = """# Makefile for Pausanias LaTeX book

LATEX = pdflatex
XELATEX = xelatex
LUALATEX = lualatex
MAKEINDEX = makeindex

all: pausanias.pdf pausanias-greek.pdf pausanias-greek-english-parallel.pdf pausanias-greek-checklist.pdf

pausanias.pdf: pausanias.tex preamble.tex titlepage.tex book*.tex
\t$(LATEX) -interaction=nonstopmode -halt-on-error pausanias.tex
\t$(MAKEINDEX) people.idx
\t$(MAKEINDEX) places.idx
\t$(MAKEINDEX) deities.idx
\t$(LATEX) -interaction=nonstopmode -halt-on-error pausanias.tex
\t$(LATEX) -interaction=nonstopmode -halt-on-error pausanias.tex

pausanias-greek.pdf: pausanias-greek.tex greek-preamble.tex greek-titlepage.tex greek-book*.tex map*.pdf
\t$(XELATEX) -interaction=nonstopmode -halt-on-error pausanias-greek.tex
\t$(MAKEINDEX) gpassages.idx
\t$(MAKEINDEX) gpeople.idx
\t$(MAKEINDEX) gplaces.idx
\t$(MAKEINDEX) gdeities.idx
\t$(XELATEX) -interaction=nonstopmode -halt-on-error pausanias-greek.tex
\t$(XELATEX) -interaction=nonstopmode -halt-on-error pausanias-greek.tex

# The AprilTag checklist is a stable review artifact. Keep this target
# presence-based so routine source regeneration does not rebuild it.
pausanias-greek-checklist.pdf:
\t$(LUALATEX) -interaction=nonstopmode -halt-on-error pausanias-greek-checklist.tex
\t$(LUALATEX) -interaction=nonstopmode -halt-on-error pausanias-greek-checklist.tex

pausanias-greek-english-parallel.pdf: pausanias-greek-english-parallel.tex
\t$(XELATEX) -interaction=nonstopmode -halt-on-error pausanias-greek-english-parallel.tex
\t$(XELATEX) -interaction=nonstopmode -halt-on-error pausanias-greek-english-parallel.tex

clean:
\trm -f *.aux *.log *.toc *.idx *.ind *.ilg *.out *.xdv *.fls *.fdb_latexmk \\
\t\tpausanias.pdf pausanias-greek.pdf pausanias-greek-english-parallel.pdf

clean-checklist:
\trm -f pausanias-greek-checklist.aux pausanias-greek-checklist.log \\
\t\tpausanias-greek-checklist.out pausanias-greek-checklist.pdf

.PHONY: all clean clean-checklist
"""

    return makefile


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate Pausanias LaTeX sources for PDF build outputs."
    )
    add_database_argument(parser)
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help=f"Directory for generated TeX sources (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--max-sentences",
        type=int,
        default=None,
        help="Limit sentence rows in the Greek and parallel PDFs for quick test builds.",
    )
    return parser.parse_args()


def main():
    """Generate all LaTeX files."""
    args = parse_args()
    output_dir = args.output_dir

    # Connect to database
    conn = connect(args.database_url)

    # Get data
    print("Fetching translation data...")
    passages, nouns_by_passage, noun_passages = get_translation_page_data(conn)

    print(f"Found {len(passages)} passages")

    print("Fetching sentence data...")
    sentences = get_sentence_page_data(conn, limit=args.max_sentences)
    print(f"Found {len(sentences)} sentences")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    print("Generating AprilTag images...")
    generated_tags = ensure_apriltag_images(output_dir, len(sentences))
    print(f"  {generated_tags} AprilTag image(s) generated")

    # Generate preamble
    print("Generating preamble.tex...")
    with open(os.path.join(output_dir, "preamble.tex"), "w", encoding="utf-8") as f:
        f.write(generate_preamble())

    # Generate title page
    print("Generating titlepage.tex...")
    with open(os.path.join(output_dir, "titlepage.tex"), "w", encoding="utf-8") as f:
        f.write(generate_titlepage())

    print(f"Generating {GREEK_PREAMBLE_TEX}...")
    with open(os.path.join(output_dir, GREEK_PREAMBLE_TEX), "w", encoding="utf-8") as f:
        f.write(generate_greek_book_preamble())

    print(f"Generating {GREEK_TITLEPAGE_TEX}...")
    with open(os.path.join(output_dir, GREEK_TITLEPAGE_TEX), "w", encoding="utf-8") as f:
        f.write(generate_greek_titlepage())

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
            map_file = generate_book_map(book_num, places, output_dir)
            book_maps[book_num] = map_file
            print(f"  Book {book_num}: {len(places)} places")
        else:
            print(f"  Book {book_num}: no places with coordinates")

    # Generate each book file
    for book_num in book_nums:
        print(f"Generating book{book_num}.tex...")
        map_file = book_maps.get(book_num)
        content = generate_book_content(book_num, passages, nouns_by_passage, map_file)
        with open(os.path.join(output_dir, f"book{book_num}.tex"), "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Generating {GREEK_BOOK_PREFIX}{book_num}.tex...")
        greek_content = generate_greek_book_content(book_num, passages, nouns_by_passage, map_file)
        with open(
            os.path.join(output_dir, f"{GREEK_BOOK_PREFIX}{book_num}.tex"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(greek_content)

    # Generate main document
    print("Generating pausanias.tex...")
    with open(os.path.join(output_dir, "pausanias.tex"), "w", encoding="utf-8") as f:
        f.write(generate_main_document(book_nums))

    print(f"Generating {GREEK_TEX}...")
    with open(os.path.join(output_dir, GREEK_TEX), "w", encoding="utf-8") as f:
        f.write(generate_greek_main_document(book_nums))

    print(f"Generating {CHECKLIST_TEX}...")
    with open(os.path.join(output_dir, CHECKLIST_TEX), "w", encoding="utf-8") as f:
        f.write(generate_greek_checklist_document(sentences))

    print(f"Generating {PARALLEL_TEX}...")
    with open(os.path.join(output_dir, PARALLEL_TEX), "w", encoding="utf-8") as f:
        f.write(generate_parallel_document(sentences))

    # Generate Makefile
    print("Generating Makefile...")
    with open(os.path.join(output_dir, "Makefile"), "w", encoding="utf-8") as f:
        f.write(generate_makefile())

    conn.close()

    print(f"\nLaTeX files generated in '{output_dir}/'")
    print(f"To build PDFs: cd {output_dir} && make")


if __name__ == "__main__":
    main()
