#!/usr/bin/env python3
"""Generate simple Greek markup documents for manual annotation."""

import argparse
import datetime as dt
import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import textwrap
import zipfile


SOURCE_TEXT = "description_of_greece.txt"
OUTPUT_DIR = "pausanias_book"
STATIC_DIR = "website/static"
DOCX_NAME = "pausanias-greek-markup.docx"
PDF_NAME = "pausanias-greek-markup.pdf"
TEX_NAME = "pausanias-greek-markup.tex"
TITLE = "Pausanias: Description of Greece - Greek Text for Markup"
NOTE = (
    "Section identifiers are retained as #book.chapter.section# markers so "
    "annotators can apply any colour scheme in Word or on a printed PDF."
)


def parse_passages(source_text):
    """Return (passage_id, greek_text) rows from a hashtag-marked source text."""
    passages = []
    current_id = None
    buffer = []
    marker_re = re.compile(r"^#(\d+\.\d+\.\d+)#$")

    def flush():
        if current_id is None:
            return
        text = normalise_passage_text("\n".join(buffer))
        if text:
            passages.append((current_id, text))

    for raw_line in source_text.splitlines():
        line = raw_line.strip()
        match = marker_re.match(line)
        if match:
            flush()
            current_id = match.group(1)
            buffer = []
            continue
        buffer.append(raw_line.rstrip())

    flush()
    return passages


def normalise_passage_text(text):
    """Collapse source line wrapping into one annotatable paragraph."""
    collapsed = " ".join(text.split())
    return collapsed.replace("---", "\u2014")


def xml_text(text):
    """Escape text for OOXML and remove XML-forbidden control characters."""
    cleaned = "".join(
        char
        for char in text
        if char in "\t\n\r" or ord(char) >= 0x20
    )
    return html.escape(cleaned, quote=False)


def docx_paragraph(text, style_id):
    return (
        "<w:p>"
        "<w:pPr>"
        f'<w:pStyle w:val="{style_id}"/>'
        "</w:pPr>"
        "<w:r>"
        f'<w:t xml:space="preserve">{xml_text(text)}</w:t>'
        "</w:r>"
        "</w:p>"
    )


def build_document_xml(passages):
    paragraphs = [
        docx_paragraph(TITLE, "Title"),
        docx_paragraph(NOTE, "Subtitle"),
    ]
    for passage_id, greek in passages:
        paragraphs.append(docx_paragraph(f"#{passage_id}#", "PassageId"))
        paragraphs.append(docx_paragraph(greek, "GreekText"))

    body = "\n".join(paragraphs)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
            xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
            mc:Ignorable="w14">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>
      <w:cols w:space="708"/>
      <w:docGrid w:linePitch="360"/>
    </w:sectPr>
  </w:body>
</w:document>
"""


def styles_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr>
      <w:spacing w:after="160"/>
    </w:pPr>
    <w:rPr>
      <w:b/>
      <w:sz w:val="36"/>
      <w:szCs w:val="36"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle">
    <w:name w:val="Subtitle"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr>
      <w:spacing w:after="360"/>
    </w:pPr>
    <w:rPr>
      <w:i/>
      <w:color w:val="555555"/>
      <w:sz w:val="20"/>
      <w:szCs w:val="20"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="PassageId">
    <w:name w:val="Passage ID"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr>
      <w:keepNext/>
      <w:spacing w:before="220" w:after="80"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/>
      <w:b/>
      <w:color w:val="1F4E5F"/>
      <w:sz w:val="21"/>
      <w:szCs w:val="21"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="GreekText">
    <w:name w:val="Greek Text"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr>
      <w:spacing w:line="300" w:lineRule="auto" w:after="120"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
    </w:rPr>
  </w:style>
</w:styles>
"""


def core_xml(created):
    timestamp = created.strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                   xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:dcterms="http://purl.org/dc/terms/"
                   xmlns:dcmitype="http://purl.org/dc/dcmitype/"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{xml_text(TITLE)}</dc:title>
  <dc:subject>Ancient Greek annotation copy</dc:subject>
  <dc:creator>Pausanias Analysis Project</dc:creator>
  <cp:lastModifiedBy>Pausanias Analysis Project</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>
</cp:coreProperties>
"""


def app_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
            xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Pausanias Analysis Project</Application>
</Properties>
"""


def write_docx(passages, output_path):
    created = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    files = {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
""",
        "word/_rels/document.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
""",
        "word/document.xml": build_document_xml(passages),
        "word/styles.xml": styles_xml(),
        "word/settings.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:zoom w:percent="100"/>
</w:settings>
""",
        "docProps/core.xml": core_xml(created),
        "docProps/app.xml": app_xml(),
    }

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, contents in files.items():
            archive.writestr(name, contents)


def escape_xelatex(text):
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
    escaped = text
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def build_tex(passages):
    lines = [
        r"\documentclass[11pt,a4paper]{article}",
        r"\usepackage{fontspec}",
        r"\setmainfont{FreeSerif.otf}[",
        r"  BoldFont={FreeSerifBold.otf},",
        r"  ItalicFont={FreeSerifItalic.otf},",
        r"  BoldItalicFont={FreeSerifBoldItalic.otf}",
        r"]",
        r"\setmonofont{lmmono10-regular.otf}",
        r"\usepackage[margin=0.8in]{geometry}",
        r"\usepackage{xcolor}",
        r"\usepackage{needspace}",
        r"\usepackage[hidelinks,pdfusetitle]{hyperref}",
        r"\definecolor{pausaniasblue}{HTML}{1F4E5F}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{0.65\baselineskip}",
        r"\emergencystretch=4em",
        r"\tolerance=2500",
        r"\newcommand{\passageid}[1]{\par\needspace{4\baselineskip}{\small\ttfamily\bfseries\color{pausaniasblue}\##1\#\par}}",
        r"\newcommand{\greekpassage}[1]{{\large #1\par}}",
        rf"\hypersetup{{pdftitle={{{escape_xelatex(TITLE)}}}, pdfauthor={{Pausanias}}}}",
        r"\begin{document}",
        rf"{{\LARGE\bfseries {escape_xelatex(TITLE)}\par}}",
        rf"{{\small\itshape {escape_xelatex(NOTE)}\par}}",
        r"\bigskip",
    ]
    for passage_id, greek in passages:
        lines.append(rf"\passageid{{{escape_xelatex(passage_id)}}}")
        wrapped_greek = "\n".join(
            textwrap.wrap(
                escape_xelatex(greek),
                width=100,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
        lines.append("\\greekpassage{%")
        lines.append(wrapped_greek)
        lines.append("}")
    lines.extend([r"\end{document}", ""])
    return "\n".join(lines)


def run_xelatex(tex_path):
    xelatex = shutil.which("xelatex")
    if not xelatex:
        raise RuntimeError("xelatex is required to build the PDF output.")
    for _pass in range(2):
        subprocess.run(
            [xelatex, "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=tex_path.parent,
            check=True,
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate simple Greek DOCX and PDF markup copies."
    )
    parser.add_argument("--source", default=SOURCE_TEXT, help=f"Source text file (default: {SOURCE_TEXT})")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help=f"Output directory (default: {OUTPUT_DIR})")
    parser.add_argument("--static-dir", default=STATIC_DIR, help=f"Directory for fixed website copies (default: {STATIC_DIR})")
    parser.add_argument("--no-static-copy", action="store_true", help="Do not copy final PDF/DOCX into the fixed website asset directory.")
    parser.add_argument("--no-pdf", action="store_true", help="Write the TeX source and DOCX, but skip XeLaTeX PDF build.")
    return parser.parse_args()


def main():
    args = parse_args()
    source_path = Path(args.source)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    passages = parse_passages(source_path.read_text(encoding="utf-8"))
    if not passages:
        raise RuntimeError(f"No #book.chapter.section# passages found in {source_path}")

    docx_path = output_dir / DOCX_NAME
    tex_path = output_dir / TEX_NAME

    write_docx(passages, docx_path)
    tex_path.write_text(build_tex(passages), encoding="utf-8")
    if not args.no_pdf:
        run_xelatex(tex_path)

    pdf_path = output_dir / PDF_NAME
    if not args.no_static_copy:
        static_dir = Path(args.static_dir)
        static_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(docx_path, static_dir / DOCX_NAME)
        if pdf_path.exists():
            shutil.copy2(pdf_path, static_dir / PDF_NAME)

    print(f"Parsed {len(passages)} passages from {source_path}")
    print(f"Wrote {docx_path}")
    print(f"Wrote {tex_path}")
    if pdf_path.exists():
        print(f"Wrote {pdf_path}")
    if not args.no_static_copy:
        print(f"Copied website assets to {Path(args.static_dir)}")


if __name__ == "__main__":
    main()
