"""HTML page generator functions."""

import json
import os
import html
import math
import re
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from .highlighting import highlight_passage

GRAPHIC_PASSAGE_IMAGE_RE = re.compile(
    r"^(?P<section>\d+)\.(?:png|jpg|jpeg|webp)$", re.IGNORECASE
)

SITE_NAV_LINKS = [
    ("index.html", "Home", "home"),
    ("texts/index.html", "Texts", "texts"),
    ("grammar/index.html", "Grammar", "grammar"),
    ("annotations/index.html", "Annotations", "annotations"),
    ("lemmas/index.html", "Lemmas", "lemmas"),
    ("analysis/index.html", "Analysis", "analysis"),
    ("places/index.html", "Places", "places"),
    ("progress/index.html", "Progress", "progress"),
]

LEGACY_NAV_ACTIVE_MAP = {
    "translation": "texts",
    "graphic_book": "texts",
    "nouns": "texts",
    "grammar": "grammar",
    "mythic": "annotations",
    "skepticism": "annotations",
    "sentences": "annotations",
    "translation_length": "analysis",
    "network": "places",
    "map": "places",
    "place_pairs": "places",
    "progress": "progress",
}


def _site_nav(prefix="", active=None):
    """Generate the compact site-wide nav with links relative to the root."""
    active_key = LEGACY_NAV_ACTIVE_MAP.get(active, active)
    parts = []
    for href, label, key in SITE_NAV_LINKS:
        cls = ' class="active"' if key == active_key else ""
        parts.append(f'<a href="{prefix}{href}"{cls}>{label}</a>')
    return '<nav class="site-nav">\n            ' + "\n            ".join(parts) + "\n        </nav>"


def _graphic_book_image_dir(image_dir=None):
    if image_dir:
        return Path(image_dir).expanduser()
    env_image_dir = os.environ.get("GRAPHIC_BOOK_IMAGE_DIR")
    if env_image_dir:
        return Path(env_image_dir).expanduser()
    return Path(__file__).resolve().parent.parent / "graphic_book" / "images"


def discover_graphic_book_passage_ids(image_dir=None):
    """Return passage IDs that have a generated graphic-book image."""
    root = _graphic_book_image_dir(image_dir)
    passage_ids = set()
    if not root.exists():
        return passage_ids

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        match = GRAPHIC_PASSAGE_IMAGE_RE.match(path.name)
        if not match:
            continue
        try:
            chapter = path.parent.name
            book = path.parent.parent.name
            int(book)
            int(chapter)
        except (ValueError, IndexError):
            continue
        passage_ids.add(f"{book}.{chapter}.{match.group('section')}")
    return passage_ids

PREDICTOR_TABLE_SORT_SCRIPT = """
    <script>
    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-predictor-sort-controls]").forEach(function (controls) {
            const table = document.getElementById(controls.dataset.tableId);
            if (!table || !table.tBodies.length) {
                return;
            }

            const tbody = table.tBodies[0];
            const coefficientDirection = controls.dataset.coefficientDirection || "desc";

            function compareNumbers(a, b, direction) {
                return direction === "asc" ? a - b : b - a;
            }

            function sortTable(mode) {
                const rows = Array.from(tbody.rows);
                rows.sort(function (rowA, rowB) {
                    const coeffA = parseFloat(rowA.querySelector('[data-sort-key="coefficient"]').dataset.sortValue);
                    const coeffB = parseFloat(rowB.querySelector('[data-sort-key="coefficient"]').dataset.sortValue);
                    const qA = parseFloat(rowA.querySelector('[data-sort-key="q_value"]').dataset.sortValue);
                    const qB = parseFloat(rowB.querySelector('[data-sort-key="q_value"]').dataset.sortValue);

                    if (mode === "q_value") {
                        const qComparison = compareNumbers(qA, qB, "asc");
                        if (qComparison !== 0) {
                            return qComparison;
                        }
                    }

                    return compareNumbers(coeffA, coeffB, coefficientDirection);
                });

                rows.forEach(function (row) {
                    tbody.appendChild(row);
                });

                controls.querySelectorAll("[data-sort-mode]").forEach(function (button) {
                    button.classList.toggle("is-active", button.dataset.sortMode === mode);
                });
            }

            controls.querySelectorAll("[data-sort-mode]").forEach(function (button) {
                button.addEventListener("click", function () {
                    sortTable(button.dataset.sortMode);
                });
            });

            sortTable(controls.dataset.defaultMode || "coefficient");
        });
    });
    </script>
"""


def write_redirect_page(output_dir, filename, target, title):
    """Write a lightweight compatibility redirect for older flat URLs."""
    redirect_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url={html.escape(target)}">
    <title>{html.escape(title)}</title>
</head>
<body>
    <p><a href="{html.escape(target)}">{html.escape(title)}</a></p>
</body>
</html>
"""
    with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
        f.write(redirect_html)


def format_classification_metrics(metrics, class_0_label, class_1_label):
    """Format classification metrics into an HTML table.

    Args:
        metrics: Dictionary containing classification metrics
        class_0_label: Label for class 0 (e.g., 'Historical', 'Non-skeptical')
        class_1_label: Label for class 1 (e.g., 'Mythic', 'Skeptical')

    Returns:
        HTML string containing the formatted metrics table
    """
    if metrics is None:
        return "<p>No classification metrics available.</p>"

    html_content = f"""
    <div class="metrics-section">
        <h3>Model Performance Metrics</h3>
        <p>The following metrics are from the logistic regression classifier's performance on the test set:</p>

        <table class="metrics-table">
            <thead>
                <tr>
                    <th>Class</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>F1-Score</th>
                    <th>Support</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{class_0_label}</td>
                    <td>{metrics['precision_0']:.3f}</td>
                    <td>{metrics['recall_0']:.3f}</td>
                    <td>{metrics['f1_0']:.3f}</td>
                    <td>{metrics['support_0']}</td>
                </tr>
                <tr>
                    <td>{class_1_label}</td>
                    <td>{metrics['precision_1']:.3f}</td>
                    <td>{metrics['recall_1']:.3f}</td>
                    <td>{metrics['f1_1']:.3f}</td>
                    <td>{metrics['support_1']}</td>
                </tr>
                <tr class="metrics-summary">
                    <td><strong>Overall Accuracy</strong></td>
                    <td colspan="3"><strong>{metrics['accuracy']:.3f}</strong></td>
                    <td><strong>{metrics['support_0'] + metrics['support_1']}</strong></td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    return html_content


def render_predictor_table(
    table_id,
    rows,
    word_class,
    positive_count_label,
    negative_count_label,
    positive_count_column,
    negative_count_column,
    coefficient_direction="desc",
):
    """Render a sortable predictor table."""
    table_html = f"""
            <div class="predictor-sort-controls" data-predictor-sort-controls data-table-id="{table_id}" data-default-mode="coefficient" data-coefficient-direction="{coefficient_direction}">
                <span>Sort by:</span>
                <button type="button" class="predictor-sort-button" data-sort-mode="coefficient">Coefficient</button>
                <button type="button" class="predictor-sort-button" data-sort-mode="q_value">q-value</button>
            </div>

            <table class="predictor-table" id="{table_id}">
                <thead>
                    <tr>
                        <th>Word/Phrase</th>
                        <th>English</th>
                        <th>Coefficient</th>
                        <th>{positive_count_label}</th>
                        <th>{negative_count_label}</th>
                        <th>p-value</th>
                        <th>q-value</th>
                    </tr>
                </thead>
                <tbody>
    """

    for _, row in rows.iterrows():
        english = row.get("english_translation", "")
        table_html += f"""
                    <tr>
                        <td class="{word_class}">{html.escape(row['phrase'])}</td>
                        <td>{html.escape(english)}</td>
                        <td data-sort-key="coefficient" data-sort-value="{row['coefficient']:.16g}">{row['coefficient']:.4f}</td>
                        <td>{row[positive_count_column]}</td>
                        <td>{row[negative_count_column]}</td>
                        <td>{row['p_value']:.3g}</td>
                        <td data-sort-key="q_value" data-sort-value="{row['q_value']:.16g}">{row['q_value']:.3g}</td>
                    </tr>
        """

    table_html += """
                </tbody>
            </table>
    """
    return table_html


def render_confusion_matrix_card(title, metrics, class_0_label, class_1_label, prefix=""):
    """Render a 2x2 confusion matrix card when exact counts are available."""
    keys = [
        f"{prefix}actual_0_pred_0",
        f"{prefix}actual_0_pred_1",
        f"{prefix}actual_1_pred_0",
        f"{prefix}actual_1_pred_1",
    ]
    if metrics is None or any(key not in metrics for key in keys):
        return ""

    return f"""
            <section class="confusion-card">
                <h3>{html.escape(title)}</h3>
                <table class="confusion-table">
                    <thead>
                        <tr>
                            <th class="confusion-corner" colspan="2" rowspan="2"></th>
                            <th class="confusion-axis confusion-axis-predicted" colspan="2">Predicted</th>
                        </tr>
                        <tr>
                            <th>{html.escape(class_0_label)}</th>
                            <th>{html.escape(class_1_label)}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <th class="confusion-axis confusion-axis-actual" rowspan="2">Actual</th>
                            <th class="confusion-row-label">{html.escape(class_0_label)}</th>
                            <td>{int(metrics[f"{prefix}actual_0_pred_0"])}</td>
                            <td>{int(metrics[f"{prefix}actual_0_pred_1"])}</td>
                        </tr>
                        <tr>
                            <th class="confusion-row-label">{html.escape(class_1_label)}</th>
                            <td>{int(metrics[f"{prefix}actual_1_pred_0"])}</td>
                            <td>{int(metrics[f"{prefix}actual_1_pred_1"])}</td>
                        </tr>
                    </tbody>
                </table>
            </section>
    """


def render_confusion_matrix_section(full_metrics, simplified_metrics, class_0_label, class_1_label, baseline_label):
    """Render confusion matrices for the full, simplified, and baseline models."""
    cards = [
        render_confusion_matrix_card("Full Logistic Model", full_metrics, class_0_label, class_1_label),
        render_confusion_matrix_card("Simplified Checklist", simplified_metrics, class_0_label, class_1_label),
        render_confusion_matrix_card(
            f"Always Guess {baseline_label}",
            simplified_metrics,
            class_0_label,
            class_1_label,
            prefix="baseline_",
        ),
    ]
    cards = [card for card in cards if card]
    if not cards:
        return ""

    return f"""
            <div class="confusion-section">
                <p class="confusion-intro">These confusion matrices show which texts each approach gets right and where it makes false alarms or misses.</p>
                <div class="confusion-grid">
{''.join(cards)}
                </div>
            </div>
    """


def render_simplified_model_section(simplified_predictors, simplified_metrics, full_metrics, class_0_label, class_1_label):
    """Render a plain-language summary of the reduced points-based model."""
    if simplified_metrics is None or simplified_predictors is None or len(simplified_predictors) == 0:
        return f"""
        <section class="simplified-model">
            <h2>Simplified Checklist Version</h2>
            <p>This page can also show a simpler points-based model, but it is not available in the current database yet. Re-run the predictor scripts to generate it.</p>
        </section>
        """

    predictors = simplified_predictors.copy()
    predictors["abs_point_value"] = predictors["point_value"].abs()
    predictors = predictors.sort_values(["abs_point_value", "q_value"], ascending=[False, True])

    baseline_label = class_1_label if int(simplified_metrics["baseline_label"]) == 1 else class_0_label
    full_accuracy = full_metrics["accuracy"] if full_metrics is not None else None
    simplified_accuracy = simplified_metrics["accuracy"]
    baseline_accuracy = simplified_metrics["baseline_accuracy"]
    intercept = simplified_metrics["intercept"]
    threshold = simplified_metrics["threshold"]
    feature_count = int(simplified_metrics["selected_feature_count"])
    confusion_html = render_confusion_matrix_section(
        full_metrics,
        simplified_metrics,
        class_0_label,
        class_1_label,
        baseline_label,
    )

    comparison_parts = [
        f"<strong>Simplified checklist:</strong> {simplified_accuracy:.1%}",
        f"<strong>Always guess {html.escape(baseline_label)}:</strong> {baseline_accuracy:.1%}",
    ]
    if full_accuracy is not None:
        comparison_parts.insert(0, f"<strong>Full logistic model:</strong> {full_accuracy:.1%}")

    table_rows = ""
    for _, row in predictors.iterrows():
        english = row.get("english_translation", "")
        direction = class_1_label if row["point_value"] > 0 else class_0_label
        table_rows += f"""
                    <tr>
                        <td>{html.escape(row['phrase'])}</td>
                        <td>{html.escape(english)}</td>
                        <td class="points-value">{row['point_value']:+.2f}</td>
                        <td>{html.escape(direction)}</td>
                        <td>{row['q_value']:.3g}</td>
                    </tr>
        """

    return f"""
        <section class="simplified-model">
            <h2>Simplified Checklist Version</h2>
            <p>This reduced model keeps only the words or phrases with q-value below 0.1, then turns them into a simple checklist.</p>
            <p class="simplified-rule">Start at <strong>{intercept:+.2f}</strong> points. If one of the items below appears at least once, add its points once. If the final score ends above <strong>0</strong>, classify the text as <strong>{html.escape(class_1_label)}</strong>. That is the same as saying the listed word-points must add up past <strong>{threshold:+.2f}</strong>.</p>
            <p class="simplified-comparison">{' | '.join(comparison_parts)}</p>
            <p>This shorter model uses <strong>{feature_count}</strong> statistically strong vocabulary items.</p>
{confusion_html}

            <table class="predictor-table simplified-points-table">
                <thead>
                    <tr>
                        <th>Word/Phrase</th>
                        <th>English</th>
                        <th>Points If Seen</th>
                        <th>Pushes Toward</th>
                        <th>q-value</th>
                    </tr>
                </thead>
                <tbody>
{table_rows}
                </tbody>
            </table>
        </section>
    """

def generate_home_page(output_dir, title, timestamp):
    """Generate the home page with build timestamp and links to other pages."""
    html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <link rel="stylesheet" href="css/style.css">
    </head>
    <body>
        <header>
            <h1>{title}</h1>
            <p>Analysis of Pausanias' Description of Greece</p>
        </header>
        
        {_site_nav("", "home")}

        <div class="container">
            <h2>Welcome to the Pausanias Analysis Project</h2>
            
            <p>This site collects the Pausanias translation, annotation data, lemma views, and analysis outputs.</p>
            
            <div class="home-card">
                <h2>Texts</h2>
                <p>Browse the HTML translation, the illustrated graphic-book version, and the typeset PDFs.</p>
                <a href="texts/index.html">Open Texts</a>
            </div>

            <div class="home-card">
                <h2>Grammar</h2>
                <p>Inspect parser-style LLM grammar outputs passage by passage, including token tables and dependency-tree views.</p>
                <a href="grammar/index.html">Open Grammar</a>
            </div>

            <div class="home-card">
                <h2>Annotations</h2>
                <p>Review current sentence-level mythic, historical, and other tags, with legacy classifiers kept separately.</p>
                <a href="annotations/index.html">Open Annotations</a>
            </div>
            
            <div class="home-card">
                <h2>Lemmas</h2>
                <p>See the lemma stream extracted for each Greek sentence and track missing word-level lemmatizations.</p>
                <a href="lemmas/index.html">Open Lemmas</a>
            </div>
            
            <div class="home-card">
                <h2>Analyses</h2>
                <p>Compare lemma-based and surface-form models, translation-length residuals, and deprecated predictor pages.</p>
                <a href="analysis/index.html">Open Analyses</a>
            </div>

            <div class="home-card">
                <h2>Places</h2>
                <p>Use the map, place-pair distances, noun index, and noun network views.</p>
                <a href="places/index.html">Open Places</a>
            </div>

            <div class="home-card">
                <h2>Pipeline Progress</h2>
                <p>Track the status of data processing tasks: completion percentages,
                   estimated finish dates, and token usage.</p>
                <a href="progress/index.html">View Progress</a>
            </div>

            <footer>
                Site generated on {timestamp} from the PostgreSQL database
            </footer>
        </div>
    </body>
    </html>
    """
    
    # Write the file
    with open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)


def _sentence_passage_link(passage_id, prefix="../"):
    parts = str(passage_id).split(".")
    if len(parts) != 3:
        return html.escape(str(passage_id))
    href = f"{prefix}translation/{parts[0]}/{parts[1]}/{parts[2]}.html"
    return f'<a href="{href}">{html.escape(str(passage_id))}</a>'


def _text_or_empty(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _normalized_text_with_spans(text):
    normalized = []
    spans = []
    in_space = False
    for index, character in enumerate(text):
        if character.isspace():
            if in_space and spans:
                start, _ = spans[-1]
                spans[-1] = (start, index + 1)
            else:
                normalized.append(" ")
                spans.append((index, index + 1))
                in_space = True
        else:
            normalized.append(character)
            spans.append((index, index + 1))
            in_space = False
    return "".join(normalized), spans


def _find_context_span(context, target):
    if not context or not target:
        return None

    start = context.find(target)
    if start >= 0:
        return start, start + len(target)

    normalized_context, spans = _normalized_text_with_spans(context)
    normalized_target = re.sub(r"\s+", " ", target.strip())
    if not normalized_context or not normalized_target:
        return None

    normalized_start = normalized_context.find(normalized_target)
    if normalized_start < 0:
        return None

    normalized_end = normalized_start + len(normalized_target) - 1
    if normalized_start >= len(spans) or normalized_end >= len(spans):
        return None
    return spans[normalized_start][0], spans[normalized_end][1]


def _highlight_sentence_context(context, target, css_class="sentence-review-highlight"):
    context = _text_or_empty(context)
    target = _text_or_empty(target)
    if not context:
        context = target
    if not target:
        return html.escape(context), False

    span = _find_context_span(context, target)
    if not span:
        fallback = (
            f'{html.escape(context)}'
            f'<span class="sentence-review-fallback">'
            f'<mark class="{css_class}">{html.escape(target)}</mark>'
            f'</span>'
        )
        return fallback, False

    start, end = span
    return (
        f'{html.escape(context[:start])}'
        f'<mark class="{css_class}">{html.escape(context[start:end])}</mark>'
        f'{html.escape(context[end:])}',
        True,
    )


def _generated_footer():
    return f"Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')} from the PostgreSQL database"


def _manto_network_json_payload(network_data):
    return json.dumps(network_data or {}, ensure_ascii=False).replace("</", "<\\/")


def generate_texts_index(output_dir, title):
    """Generate a hub page for text and graphic-book formats."""
    texts_dir = os.path.join(output_dir, "texts")
    os.makedirs(texts_dir, exist_ok=True)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Texts</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Translation and graphic-book formats</p>
    </header>
    {_site_nav("../", "texts")}
    <div class="container">
        <h2>Texts</h2>
        <div class="hub-grid">
            <section class="hub-card">
                <h3>Text HTML</h3>
                <p>Greek and English passage pages with proper nouns, maps, and passage navigation.</p>
                <a href="../translation/index.html">Open HTML Translation</a>
            </section>
            <section class="hub-card">
                <h3>Text PDF</h3>
                <p>Typeset PDF version of the English translation.</p>
                <a href="../pausanias.pdf">Open Text PDF</a>
            </section>
            <section class="hub-card">
                <h3>Greek Text PDF</h3>
                <p>Continuous Greek text with book maps, table of contents, passage index, and name indices.</p>
                <a href="../pausanias-greek.pdf">Open Greek Text PDF</a>
            </section>
            <section class="hub-card">
                <h3>Greek Markup PDF</h3>
                <p>Simple #book.chapter.section# Greek passage copy for print colour annotation.</p>
                <a href="../pausanias-greek-markup.pdf">Open Markup PDF</a>
            </section>
            <section class="hub-card">
                <h3>Greek Markup Word</h3>
                <p>Editable Word version of the same #book.chapter.section# Greek passage copy.</p>
                <a href="../pausanias-greek-markup.docx">Open Markup Word</a>
            </section>
            <section class="hub-card">
                <h3>Greek Checklist PDF</h3>
                <p>Greek sentence review sheet with passage IDs, annotation boxes, and April tags.</p>
                <a href="../pausanias-greek-checklist.pdf">Open Greek Checklist PDF</a>
            </section>
            <section class="hub-card">
                <h3>Greek-English Parallel PDF</h3>
                <p>Aligned Greek and English sentence table for the full text.</p>
                <a href="../pausanias-greek-english-parallel.pdf">Open Parallel PDF</a>
            </section>
            <section class="hub-card">
                <h3>Graphic Book HTML</h3>
                <p>Illustrated passage-by-passage graphic-book reader.</p>
                <a href="../graphic-book/index.html">Open Graphic Book</a>
            </section>
            <section class="hub-card">
                <h3>Graphic Book PDF</h3>
                <p>PDF export of the illustrated graphic-book pages.</p>
                <a href="../graphic-book/pausanias-graphic-book.pdf">Open Graphic PDF</a>
            </section>
            <section class="hub-card">
                <h3>Grammar Parses</h3>
                <p>Passage-level parser-style outputs from the current LLM grammar pipeline.</p>
                <a href="../grammar/index.html">Open Grammar Parses</a>
            </section>
            <section class="hub-card">
                <h3>Proper Noun Index</h3>
                <p>People, places, deities, and other named entities from the translation pages.</p>
                <a href="../translation/nouns/index.html">Open Noun Index</a>
            </section>
        </div>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(texts_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)


def generate_annotations_index(greta_sentences_df, output_dir, title):
    """Generate a hub page for active and deprecated annotation views."""
    annotations_dir = os.path.join(output_dir, "annotations")
    os.makedirs(annotations_dir, exist_ok=True)

    if greta_sentences_df is None or len(greta_sentences_df) == 0:
        active_summary = "No active three-bucket sentence tags are available yet."
        bucket_rows = ""
    else:
        counts = greta_sentences_df["myth_history_bucket"].value_counts().sort_index()
        active_summary = f"{len(greta_sentences_df):,} sentences tagged with the active three-bucket scheme."
        bucket_rows = "".join(
            f"<li><span class=\"status-pill bucket-{html.escape(str(bucket))}\">{html.escape(str(bucket))}</span> {int(count):,}</li>"
            for bucket, count in counts.items()
        )

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Annotations</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Sentence and passage annotation views</p>
    </header>
    {_site_nav("../", "annotations")}
    <div class="container">
        <h2>Current Annotation Scheme</h2>
        <section class="hub-card">
            <h3>Sentence Level: Mythic, Historical, Other</h3>
            <p>{active_summary}</p>
            <ul class="compact-list">{bucket_rows}</ul>
            <a href="sentences/index.html">Open Current Sentence Tags</a>
        </section>

        <section class="hub-card">
            <h3>Classifier Comparison: Original vs. Greta-inspired</h3>
            <p>Compare the simple three-way tagger against the calibrated two-flag
            tagger across the whole corpus &mdash; base rates per book and every
            sentence where they disagree.</p>
            <a href="comparison/index.html">Open Classifier Comparison</a>
        </section>

        <h2>Deprecated Annotation Schemes</h2>
        <div class="hub-grid">
            <section class="hub-card deprecated">
                <h3>Passage Level: Mythic vs. Non-mythic</h3>
                <p>Legacy passage classifier retained for comparison only.</p>
                <a href="../mythic/index.html">Open Deprecated Passage Tags</a>
            </section>
            <section class="hub-card deprecated">
                <h3>Passage Level: Skeptical vs. Non-skeptical</h3>
                <p>Legacy skepticism classifier retained for comparison only.</p>
                <a href="../skepticism/index.html">Open Deprecated Skepticism Tags</a>
            </section>
            <section class="hub-card deprecated">
                <h3>Sentence Level: Legacy Booleans</h3>
                <p>Sentence splits with the older mythic and skepticism boolean labels.</p>
                <a href="../sentences/index.html">Open Deprecated Sentence Tags</a>
            </section>
        </div>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(annotations_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)


def generate_greta_sentence_annotation_pages(greta_sentences_df, output_dir, title):
    """Generate chapter pages for active Greta three-bucket sentence tags."""
    sentences_dir = os.path.join(output_dir, "annotations", "sentences")
    os.makedirs(sentences_dir, exist_ok=True)

    if greta_sentences_df is None or len(greta_sentences_df) == 0:
        chapters = []
    else:
        chapters = sorted(
            greta_sentences_df["chapter"].unique(),
            key=lambda c: [int(p) for p in str(c).split(".")],
        )

    for chapter in chapters:
        chapter_df = greta_sentences_df[greta_sentences_df["chapter"] == chapter]
        rows = []
        for _, row in chapter_df.iterrows():
            bucket = str(row["myth_history_bucket"])
            rows.append(f"""
                <tr>
                    <td>{_sentence_passage_link(row["passage_id"], "../../")}</td>
                    <td class="num">{int(row["sentence_number"])}</td>
                    <td><span class="status-pill bucket-{html.escape(bucket)}">{html.escape(bucket)}</span></td>
                    <td>{html.escape(str(row.get("confidence", "")))}</td>
                    <td class="greek-cell">{html.escape(str(row["sentence"]))}</td>
                    <td>{html.escape(str(row["english_sentence"]))}</td>
                    <td>{html.escape(str(row.get("rationale", "")))}</td>
                </tr>
            """)

        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Current Sentence Tags {chapter}</title>
    <link rel="stylesheet" href="../../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Current sentence-level mythic, historical, and other tags</p>
    </header>
    {_site_nav("../../", "annotations")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="../index.html">Annotations</a> &rsaquo; <a href="index.html">Current Sentence Tags</a> &rsaquo; Chapter {html.escape(str(chapter))}</div>
        <h2>Chapter {html.escape(str(chapter))}</h2>
        <table class="predictor-table sentence-detail-table">
            <thead>
                <tr><th>Passage</th><th>Sentence</th><th>Bucket</th><th>Confidence</th><th>Greek</th><th>English</th><th>Rationale</th></tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
        with open(os.path.join(sentences_dir, f"{chapter.replace('.', '_')}.html"), "w", encoding="utf-8") as f:
            f.write(page)

    chapter_links = ""
    for chapter in chapters:
        count = len(greta_sentences_df[greta_sentences_df["chapter"] == chapter])
        chapter_links += f'<li><a href="{chapter.replace(".", "_")}.html">Chapter {html.escape(str(chapter))}</a> ({count:,} sentences)</li>\n'
    if not chapter_links:
        chapter_links = "<li>No active sentence tags are available yet.</li>"

    index_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Current Sentence Tags</title>
    <link rel="stylesheet" href="../../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Current sentence-level mythic, historical, and other tags</p>
    </header>
    {_site_nav("../../", "annotations")}
    <div class="container">
        <div class="breadcrumb"><a href="../index.html">Annotations</a> &rsaquo; Current Sentence Tags</div>
        <h2>Chapters</h2>
        <ul>{chapter_links}</ul>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(sentences_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page)


def generate_sentence_review_sample_page(review_sample_df, output_dir, title):
    """Generate an unlinked deterministic sentence-classification review sample."""
    annotations_dir = os.path.join(output_dir, "annotations")
    os.makedirs(annotations_dir, exist_ok=True)

    if review_sample_df is None or len(review_sample_df) == 0:
        summary = "No active sentence tags are available for review."
        prompt_version = ""
        sample_rows = """
            <section class="sentence-review-card">
                <p>No sentence review sample could be generated.</p>
            </section>
        """
    else:
        prompt_version = str(review_sample_df.iloc[0].get("prompt_version", ""))
        summary = (
            f"{len(review_sample_df):,} deterministic-random sentence"
            f"{'' if len(review_sample_df) == 1 else 's'} selected from the active tag set."
        )
        rendered_rows = []
        for _, row in review_sample_df.iterrows():
            rank = int(row.get("sample_rank", len(rendered_rows) + 1))
            bucket_value = _text_or_empty(row.get("myth_history_bucket", ""))
            bucket = html.escape(bucket_value)
            bucket_class = re.sub(r"[^a-z0-9_-]+", "-", bucket_value.lower()).strip("-")
            bucket_class = bucket_class or "unknown"
            confidence = html.escape(_text_or_empty(row.get("confidence", "")))
            rationale = html.escape(_text_or_empty(row.get("rationale", "")))
            model = html.escape(_text_or_empty(row.get("model", "")))
            greek_context, greek_matched = _highlight_sentence_context(
                row.get("passage", ""),
                row.get("sentence", ""),
            )
            english_context, english_matched = _highlight_sentence_context(
                row.get("english_translation", ""),
                row.get("english_sentence", ""),
            )
            match_note = ""
            if not greek_matched or not english_matched:
                missing = []
                if not greek_matched:
                    missing.append("Greek")
                if not english_matched:
                    missing.append("English")
                match_note = (
                    f'<p class="note">Exact context match not found for '
                    f'{html.escape(" and ".join(missing))}; the tagged sentence is shown separately.</p>'
                )

            scepticism_value = row.get("expresses_scepticism", False)
            scepticism = (
                "no"
                if pd.isna(scepticism_value)
                else ("yes" if bool(scepticism_value) else "no")
            )
            rendered_rows.append(f"""
            <section class="sentence-review-card" id="sample-{rank}">
                <div class="sentence-review-meta">
                    <span class="sample-rank">#{rank}</span>
                    <span>{_sentence_passage_link(row.get("passage_id", ""), "../")} sentence {int(row.get("sentence_number", 0))}</span>
                    <span class="status-pill bucket-{bucket_class}">{bucket}</span>
                    <span>confidence: {confidence}</span>
                    <span>scepticism: {scepticism}</span>
                </div>
                <div class="sentence-review-contexts">
                    <div>
                        <h3>Greek Context</h3>
                        <p class="greek-passage sentence-review-context">{greek_context}</p>
                    </div>
                    <div>
                        <h3>English Context</h3>
                        <p class="sentence-review-context">{english_context}</p>
                    </div>
                </div>
                {match_note}
                <details>
                    <summary>Classification Rationale</summary>
                    <p>{rationale}</p>
                    <p class="note">Model: {model}</p>
                </details>
            </section>
            """)
        sample_rows = "\n".join(rendered_rows)

    prompt_note = (
        f"<p class=\"note\">Prompt version: <code>{html.escape(prompt_version)}</code></p>"
        if prompt_version
        else ""
    )
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Sentence Review Sample</title>
    <link rel="stylesheet" href="../css/style.css">
    <style>
        .sentence-review-card {{
            border: 1px solid #d8d1c4;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            background: #fffdf8;
        }}
        .sentence-review-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem 0.75rem;
            align-items: center;
            margin-bottom: 0.75rem;
            color: #4b4032;
        }}
        .sentence-review-meta .sample-rank {{
            font-weight: 700;
            color: #2f261e;
        }}
        .sentence-review-contexts {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1rem;
        }}
        .sentence-review-context {{
            line-height: 1.65;
        }}
        .sentence-review-highlight {{
            background: #fff1a8;
            box-decoration-break: clone;
            -webkit-box-decoration-break: clone;
            padding: 0.08em 0.16em;
        }}
        .sentence-review-fallback {{
            display: block;
            margin-top: 0.75rem;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>Sentence classification review sample</p>
    </header>
    {_site_nav("../", "annotations")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Annotations</a> &rsaquo; Sentence Review Sample</div>
        <h2>Sentence Review Sample</h2>
        <p>{summary}</p>
        {prompt_note}
        {sample_rows}
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(annotations_dir, "sentence-review-sample.html"), "w", encoding="utf-8") as f:
        f.write(html_content)


def _bucket_pill(bucket):
    bucket = str(bucket)
    return f'<span class="status-pill bucket-{html.escape(bucket)}">{html.escape(bucket)}</span>'


def generate_classifier_comparison_pages(comparison, output_dir, title):
    """Generate the 'original vs greta-inspired' classifier comparison pages."""
    comparison_dir = os.path.join(output_dir, "annotations", "comparison")
    os.makedirs(comparison_dir, exist_ok=True)

    if not comparison:
        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Classifier Comparison</title>
    <link rel="stylesheet" href="../../css/style.css">
</head>
<body>
    <header><h1>{title}</h1><p>Sentence classifier comparison</p></header>
    {_site_nav("../../", "annotations")}
    <div class="container">
        <div class="breadcrumb"><a href="../index.html">Annotations</a> &rsaquo; Classifier Comparison</div>
        <p>Both classifiers have not yet been tagged across the corpus.</p>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
        with open(os.path.join(comparison_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(page)
        return

    corpus = comparison["corpus"]
    original_buckets = comparison["original_buckets"]
    greta_buckets = comparison["greta_buckets"]
    confusion = comparison["confusion"]
    disagreements = comparison["disagreements"]

    # --- corpus base-rate table (bucket distribution per classifier) ---
    all_buckets = ["mythic", "historical", "both", "other"]
    rate_rows = ""
    for b in all_buckets:
        orig = corpus["original_rates"].get(b)
        grt = corpus["greta_rates"].get(b)
        orig_cell = "&mdash;" if orig is None else f"{orig:.1f}%"
        grt_cell = "&mdash;" if grt is None else f"{grt:.1f}%"
        rate_rows += (
            f"<tr><td>{_bucket_pill(b)}</td>"
            f"<td class=\"num\">{orig_cell}</td>"
            f"<td class=\"num\">{grt_cell}</td></tr>\n"
        )

    # --- confusion matrix (rows = original, cols = greta-inspired) ---
    conf_header = "".join(f"<th>{_bucket_pill(g)}</th>" for g in greta_buckets)
    conf_rows = ""
    for orig in original_buckets:
        cells = ""
        for grb in greta_buckets:
            count = confusion.get((orig, grb), 0)
            agree = orig == grb
            cls = ' class="num agree-cell"' if agree else ' class="num"'
            cells += f"<td{cls}>{count:,}</td>"
        conf_rows += f"<tr><th>{_bucket_pill(orig)}</th>{cells}</tr>\n"

    # --- per-book table ---
    book_rows = ""
    for entry in comparison["per_book"]:
        orates = entry["original_rates"]
        grates = entry["greta_rates"]
        book_rows += (
            f"<tr>"
            f"<td><a href=\"book_{entry['book']}.html\">Book {html.escape(entry['book'])}</a></td>"
            f"<td class=\"num\">{entry['n']:,}</td>"
            f"<td class=\"num\">{entry['agree_pct']:.1f}%</td>"
            f"<td class=\"num\">{orates['mythic']:.0f}%</td>"
            f"<td class=\"num\">{orates['historical']:.0f}%</td>"
            f"<td class=\"num\">{orates['other']:.0f}%</td>"
            f"<td class=\"num\">{grates['mythic']:.0f}%</td>"
            f"<td class=\"num\">{grates['historical']:.0f}%</td>"
            f"<td class=\"num\">{grates['both']:.0f}%</td>"
            f"<td class=\"num\">{grates['other']:.0f}%</td>"
            f"</tr>\n"
        )

    index_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Classifier Comparison</title>
    <link rel="stylesheet" href="../../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Two sentence classifiers, compared across the whole corpus</p>
    </header>
    {_site_nav("../../", "annotations")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="../index.html">Annotations</a> &rsaquo; Classifier Comparison</div>
        <h2>Original vs. Greta-inspired</h2>
        <p>Each Greek sentence is tagged by two independent classifiers
        (both <code>gpt-5.4-mini</code>, temperature&nbsp;0):</p>
        <ul>
            <li><strong>Original</strong> (<code>original-myth-history-other</code>) &mdash;
            the simple prompt that forces every sentence into exactly one of
            <em>mythic</em>, <em>historical</em>, or <em>other</em>.</li>
            <li><strong>Greta-inspired</strong> (<code>greta-inspired-myth-history-other</code>) &mdash;
            two independent flags judged on each sentence's own content, calibrated to the
            Greta/Rosie Book&nbsp;3 base rates; a sentence may be <em>both</em> or <em>neither</em>.</li>
        </ul>
        <p>The two agree on the bucket for
        <strong>{corpus['agree_pct']:.1f}%</strong> of {corpus['n']:,} sentences.</p>

        <h3>Corpus-wide bucket rates</h3>
        <table class="predictor-table">
            <thead><tr><th>Bucket</th><th>Original</th><th>Greta-inspired</th></tr></thead>
            <tbody>{rate_rows}</tbody>
        </table>

        <h3>Where they disagree (bucket confusion)</h3>
        <p>Rows = Original, columns = Greta-inspired; the shaded diagonal is agreement.</p>
        <table class="predictor-table">
            <thead><tr><th>Original \\ Greta-inspired</th>{conf_header}</tr></thead>
            <tbody>{conf_rows}</tbody>
        </table>

        <h3>By book</h3>
        <table class="predictor-table sentence-detail-table">
            <thead>
                <tr>
                    <th rowspan="2">Book</th><th rowspan="2">Sentences</th><th rowspan="2">Agree</th>
                    <th colspan="3">Original</th><th colspan="4">Greta-inspired</th>
                </tr>
                <tr>
                    <th>myth</th><th>hist</th><th>other</th>
                    <th>myth</th><th>hist</th><th>both</th><th>other</th>
                </tr>
            </thead>
            <tbody>{book_rows}</tbody>
        </table>
        <p>Click a book to see every sentence where the two classifiers disagree.</p>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(comparison_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page)

    # --- per-book disagreement detail pages ---
    for entry in comparison["per_book"]:
        book = entry["book"]
        book_df = disagreements[disagreements["book"] == book]
        rows = ""
        for _, row in book_df.iterrows():
            rows += (
                "<tr>"
                f"<td>{_sentence_passage_link(row['passage_id'], '../../')}</td>"
                f"<td class=\"num\">{int(row['sentence_number'])}</td>"
                f"<td>{_bucket_pill(row['original_bucket'])}</td>"
                f"<td>{_bucket_pill(row['greta_bucket'])}</td>"
                f"<td class=\"greek-cell\">{html.escape(str(row['sentence']))}</td>"
                f"<td>{html.escape(str(row['english_sentence']))}</td>"
                f"<td>{html.escape(str(row.get('rationale', '') or ''))}</td>"
                "</tr>\n"
            )
        if not rows:
            rows = '<tr><td colspan="7">The two classifiers agree on every sentence in this book.</td></tr>'

        book_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Classifier Disagreements Book {html.escape(book)}</title>
    <link rel="stylesheet" href="../../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Sentences where the two classifiers disagree</p>
    </header>
    {_site_nav("../../", "annotations")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="../index.html">Annotations</a> &rsaquo; <a href="index.html">Classifier Comparison</a> &rsaquo; Book {html.escape(book)}</div>
        <h2>Book {html.escape(book)} &mdash; {len(book_df):,} of {entry['n']:,} sentences disagree</h2>
        <table class="predictor-table sentence-detail-table">
            <thead>
                <tr><th>Passage</th><th>Sentence</th><th>Original</th><th>Greta-inspired</th><th>Greek</th><th>English</th><th>Greta-inspired rationale</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
        with open(os.path.join(comparison_dir, f"book_{book}.html"), "w", encoding="utf-8") as f:
            f.write(book_page)


def generate_lemma_pages(sentence_lemmas_df, output_dir, title):
    """Generate sentence-level lemma view pages."""
    lemmas_dir = os.path.join(output_dir, "lemmas")
    os.makedirs(lemmas_dir, exist_ok=True)

    if sentence_lemmas_df is None or len(sentence_lemmas_df) == 0:
        chapters = []
        total_tokens = 0
        missing_tokens = 0
    else:
        chapters = sorted(
            sentence_lemmas_df["chapter"].unique(),
            key=lambda c: [int(p) for p in str(c).split(".")],
        )
        total_tokens = int(sentence_lemmas_df["token_count"].sum())
        missing_tokens = int(sentence_lemmas_df["missing_lemma_count"].sum())

    for chapter in chapters:
        chapter_df = sentence_lemmas_df[sentence_lemmas_df["chapter"] == chapter]
        rows = []
        for _, row in chapter_df.iterrows():
            rows.append(f"""
                <tr>
                    <td>{_sentence_passage_link(row["passage_id"], "../")}</td>
                    <td class="num">{int(row["sentence_number"])}</td>
                    <td class="greek-cell">{html.escape(str(row["sentence"]))}</td>
                    <td>{html.escape(str(row["english_sentence"]))}</td>
                    <td class="greek-cell lemma-cell">{html.escape(str(row["lemma_text"]))}</td>
                    <td class="num">{int(row["missing_lemma_count"])}</td>
                </tr>
            """)

        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Lemmas {chapter}</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Word-level lemma forms extracted for each sentence</p>
    </header>
    {_site_nav("../", "lemmas")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Lemmas</a> &rsaquo; Chapter {html.escape(str(chapter))}</div>
        <h2>Chapter {html.escape(str(chapter))}</h2>
        <table class="predictor-table sentence-detail-table">
            <thead>
                <tr><th>Passage</th><th>Sentence</th><th>Greek</th><th>English</th><th>Lemma Forms</th><th>Missing</th></tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
        with open(os.path.join(lemmas_dir, f"{chapter.replace('.', '_')}.html"), "w", encoding="utf-8") as f:
            f.write(page)

    chapter_links = ""
    for chapter in chapters:
        count = len(sentence_lemmas_df[sentence_lemmas_df["chapter"] == chapter])
        chapter_links += f'<li><a href="{chapter.replace(".", "_")}.html">Chapter {html.escape(str(chapter))}</a> ({count:,} sentences)</li>\n'
    if not chapter_links:
        chapter_links = "<li>No word-level lemma cache is available yet.</li>"

    index_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Lemmas</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Word-level lemma forms extracted for each sentence</p>
    </header>
    {_site_nav("../", "lemmas")}
    <div class="container">
        <h2>Lemma View</h2>
        <div class="metric-strip">
            <div><strong>{0 if sentence_lemmas_df is None else len(sentence_lemmas_df):,}</strong><span>sentences</span></div>
            <div><strong>{total_tokens:,}</strong><span>Greek tokens</span></div>
            <div><strong>{missing_tokens:,}</strong><span>raw fallbacks</span></div>
        </div>
        <ul>{chapter_links}</ul>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(lemmas_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page)


def _variant_display_name(variant):
    source = "Lemma" if variant["token_source"] == "lemma" else "Surface"
    books = "including books 4 and 8" if variant["include_books_4_8"] else "excluding books 4 and 8"
    rhetoric = "without rhetoric markers" if variant["remove_rhetoric_markers"] else "with rhetoric markers"
    return f"{source}, {books}, {rhetoric}"


def _variant_href(variant):
    return f"{variant['id']}.html"


def _legacy_variant_href(variant):
    variant_id = variant.get("id", "")
    if variant_id.startswith("tri-marked-sentence-"):
        return f"{variant_id.replace('tri-marked-sentence-', 'greta-sentence-', 1)}.html"
    return None


def _write_redirect_page(analysis_dir, filename, target_href, title, label):
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url={html.escape(target_href)}">
    <link rel="canonical" href="{html.escape(target_href)}">
    <title>{html.escape(title)} - {html.escape(label)}</title>
</head>
<body>
    <p>This analysis page has moved to <a href="{html.escape(target_href)}">{html.escape(target_href)}</a>.</p>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, filename), "w", encoding="utf-8") as f:
        f.write(page)


def _format_optional_float(value, digits=3, signed=False):
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    sign = "+" if signed else ""
    return f"{number:{sign}.{digits}f}"


def _format_label(value):
    return str(value).replace("_", " ").title()


def _format_error_contributions(contributions):
    if not contributions:
        return ""
    parts = []
    for item in contributions:
        contribution = item.get("contribution")
        contribution_text = _format_optional_float(contribution, digits=3, signed=True)
        parts.append(
            f"{html.escape(str(item.get('term', '')))} "
            f"<span class=\"note\">({contribution_text})</span>"
        )
    return "<br>".join(parts)


def _render_error_rows(rows):
    if not rows:
        return '<tr><td colspan="7">No errors of this type in the sampled test split.</td></tr>'
    rendered = []
    for row in rows:
        sentence = html.escape(str(row.get("sentence", "")))
        english_sentence = html.escape(str(row.get("english_sentence") or ""))
        rationale = html.escape(str(row.get("rationale") or ""))
        details = f"<p class=\"greek-text\">{sentence}</p>"
        if english_sentence:
            details += f"<p>{english_sentence}</p>"
        if rationale:
            details += f"<details><summary>Tagging rationale</summary><p>{rationale}</p></details>"
        rendered.append(f"""
            <tr>
                <td>{html.escape(str(row.get("passage_id", "")))}.{int(row.get("sentence_number", 0))}</td>
                <td>{html.escape(_format_label(row.get("actual_label", "")))}</td>
                <td>{html.escape(_format_label(row.get("predicted_label", "")))}</td>
                <td class="num">{_format_optional_float(row.get("probability_mythic"), 3)}</td>
                <td class="num">{_format_optional_float(row.get("predicted_confidence"), 3)}</td>
                <td>{_format_error_contributions(row.get("contributions", []))}</td>
                <td>{details}</td>
            </tr>
        """)
    return "".join(rendered)


def _write_analysis_html_page(analysis_dir, filename, title, header_subtitle, body, site_title):
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(site_title)} - {html.escape(title)}</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{html.escape(site_title)}</h1>
        <p>{html.escape(header_subtitle)}</p>
    </header>
    {_site_nav("../", "analysis")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Analyses</a> &rsaquo; {html.escape(title)}</div>
        <h2>{html.escape(title)}</h2>
        {body}
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, filename), "w", encoding="utf-8") as f:
        f.write(page)


def _write_complementary_analysis_pages(complementary, analysis_dir, title):
    semantic = complementary.get("semantic_field_ablation", {}) if complementary else {}
    if semantic.get("available"):
        baseline = semantic.get("baseline", {})
        baseline_metrics = baseline.get("metrics", {})
        rows = []
        for row in semantic.get("fields", []):
            metrics = row.get("metrics", {})
            row_status = (
                f"{metrics.get('accuracy', 0.0):.3f}"
                if row.get("available") and metrics
                else html.escape(row.get("message", "Unavailable"))
            )
            terms = ", ".join(row.get("terms", []))
            rows.append(f"""
                <tr>
                    <td><strong>{html.escape(row.get("label", ""))}</strong><br><span class="note">{html.escape(row.get("description", ""))}</span></td>
                    <td>{html.escape(terms)}</td>
                    <td class="num">{row_status}</td>
                    <td class="num">{_format_optional_float(row.get("accuracy_delta"), 3, signed=True)}</td>
                    <td class="num">{_format_optional_float(metrics.get("f1_0"), 3)}</td>
                    <td class="num">{_format_optional_float(metrics.get("f1_1"), 3)}</td>
                    <td class="num">{int(row.get("feature_count", 0)):,}</td>
                </tr>
            """)
        body = f"""
            <p class="note">Baseline is the main paper-facing model: lemma vocabulary, books 4 and 8 excluded, proper nouns removed, rhetoric markers retained.</p>
            <div class="metric-strip">
                <div><strong>{baseline_metrics.get("accuracy", 0):.3f}</strong><span>baseline accuracy</span></div>
                <div><strong>{int(baseline.get("sample_count", 0)):,}</strong><span>sentences</span></div>
                <div><strong>{int(baseline.get("feature_count", 0)):,}</strong><span>baseline features</span></div>
            </div>
            <table class="predictor-table">
                <thead>
                    <tr><th>Removed Field</th><th>Terms Removed</th><th>Accuracy</th><th>Delta</th><th>Historical F1</th><th>Mythic F1</th><th>Features</th></tr>
                </thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        """
    else:
        body = f"<p>{html.escape(semantic.get('message', 'Semantic-field ablation is unavailable.'))}</p>"
    _write_analysis_html_page(
        analysis_dir,
        "semantic_field_ablation.html",
        "Semantic-Field Ablation",
        "What happens when interpretable lexical fields are removed",
        body,
        title,
    )

    holdout = complementary.get("book_held_out", {}) if complementary else {}
    if holdout.get("available"):
        summary = holdout.get("summary", {})
        rows = []
        for row in holdout.get("books", []):
            metrics = row.get("metrics", {})
            if row.get("available"):
                status_cells = f"""
                    <td class="num">{metrics.get("accuracy", 0):.3f}</td>
                    <td class="num">{metrics.get("baseline_accuracy", 0):.3f}</td>
                    <td class="num">{_format_optional_float(metrics.get("accuracy_delta_vs_baseline"), 3, signed=True)}</td>
                    <td class="num">{_format_optional_float(metrics.get("f1_0"), 3)}</td>
                    <td class="num">{_format_optional_float(metrics.get("f1_1"), 3)}</td>
                    <td class="num">{metrics.get("actual_0_pred_0", 0)}/{metrics.get("actual_0_pred_1", 0)}/{metrics.get("actual_1_pred_0", 0)}/{metrics.get("actual_1_pred_1", 0)}</td>
                """
            else:
                status_cells = f'<td colspan="6">{html.escape(row.get("message", "Unavailable"))}</td>'
            rows.append(f"""
                <tr>
                    <td class="num">{html.escape(str(row.get("book", "")))}</td>
                    <td class="num">{int(row.get("test_count", 0)):,}</td>
                    <td class="num">{int(row.get("test_historical", 0)):,}</td>
                    <td class="num">{int(row.get("test_mythic", 0)):,}</td>
                    <td class="num">{int(row.get("train_historical", 0)):,}</td>
                    <td class="num">{int(row.get("train_mythic", 0)):,}</td>
                    {status_cells}
                </tr>
            """)
        body = f"""
            <p class="note">Each row trains the same lemma/proper-noun-removed model on all other books and tests on the held-out book. Books 4 and 8 are included here deliberately as stress tests.</p>
            <div class="metric-strip">
                <div><strong>{_format_optional_float(summary.get("weighted_accuracy"), 3)}</strong><span>weighted accuracy</span></div>
                <div><strong>{_format_optional_float(summary.get("macro_accuracy"), 3)}</strong><span>mean book accuracy</span></div>
                <div><strong>{int(summary.get("total_test", 0)):,}</strong><span>held-out sentences</span></div>
            </div>
            <table class="predictor-table">
                <thead>
                    <tr><th>Book</th><th>Test</th><th>Hist Test</th><th>Myth Test</th><th>Hist Train</th><th>Myth Train</th><th>Accuracy</th><th>Baseline</th><th>Delta</th><th>Hist F1</th><th>Myth F1</th><th>HH/HM/MH/MM</th></tr>
                </thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        """
    else:
        body = f"<p>{html.escape(holdout.get('message', 'Book-held-out analysis is unavailable.'))}</p>"
    _write_analysis_html_page(
        analysis_dir,
        "book_held_out.html",
        "Book-Held-Out Robustness",
        "Does the vocabulary model generalise across books?",
        body,
        title,
    )

    errors = complementary.get("error_analysis", {}) if complementary else {}
    if errors.get("available"):
        summary = errors.get("summary", {})
        metrics = summary.get("metrics", {})
        examples = errors.get("examples", {})
        body = f"""
            <p class="note">These are deterministic test-split errors from the main lemma model, sorted by the model's confidence in the wrong prediction. They are meant for close reading, not as a new classifier.</p>
            <div class="metric-strip">
                <div><strong>{metrics.get("accuracy", 0):.3f}</strong><span>test accuracy</span></div>
                <div><strong>{int(summary.get("error_count", 0)):,}</strong><span>test errors</span></div>
                <div><strong>{int(summary.get("false_mythic_count", 0)):,}</strong><span>false mythic</span></div>
                <div><strong>{int(summary.get("false_historical_count", 0)):,}</strong><span>false historical</span></div>
            </div>
            <h3>Historical Sentences Predicted as Mythic</h3>
            <table class="predictor-table">
                <thead>
                    <tr><th>Sentence</th><th>Actual</th><th>Predicted</th><th>P(mythic)</th><th>Confidence</th><th>Top Contributions</th><th>Text</th></tr>
                </thead>
                <tbody>{_render_error_rows(examples.get("false_mythic", []))}</tbody>
            </table>

            <h3>Mythic Sentences Predicted as Historical</h3>
            <table class="predictor-table">
                <thead>
                    <tr><th>Sentence</th><th>Actual</th><th>Predicted</th><th>P(mythic)</th><th>Confidence</th><th>Top Contributions</th><th>Text</th></tr>
                </thead>
                <tbody>{_render_error_rows(examples.get("false_historical", []))}</tbody>
            </table>
        """
    else:
        body = f"<p>{html.escape(errors.get('message', 'Error analysis is unavailable.'))}</p>"
    _write_analysis_html_page(
        analysis_dir,
        "error_analysis.html",
        "Model Error Analysis",
        "Confident misclassifications for close reading",
        body,
        title,
    )


def _sensitivity_count(records, row_key, row_value, column_key=None, column_value=None):
    for record in records or []:
        if record.get(row_key) != row_value:
            continue
        if column_key is not None and record.get(column_key) != column_value:
            continue
        return int(record.get("count", 0))
    return 0


def _render_label_confusion_matrix(sensitivity):
    manual_rows = [
        ("historical", "Historical"),
        ("mythic", "Mythic"),
        ("other", "Other / not highlighted"),
        ("mixed_mythic_historical", "Mixed mythic+historical"),
    ]
    greta_columns = [
        ("historical", "GPT Historical"),
        ("mythic", "GPT Mythic"),
        ("other", "GPT Other"),
    ]
    confusion = sensitivity.get("confusion", [])
    body_rows = []
    column_totals = {key: 0 for key, _ in greta_columns}
    grand_total = 0
    for manual_key, manual_label in manual_rows:
        cells = []
        row_total = 0
        for greta_key, _greta_label in greta_columns:
            count = _sensitivity_count(
                confusion,
                "manual_bucket",
                manual_key,
                "greta_bucket",
                greta_key,
            )
            row_total += count
            column_totals[greta_key] += count
            cells.append(f'<td class="num">{count:,}</td>')
        grand_total += row_total
        body_rows.append(f"""
            <tr>
                <th>{html.escape(manual_label)}</th>
                {''.join(cells)}
                <td class="num"><strong>{row_total:,}</strong></td>
            </tr>
        """)
    footer_cells = "".join(
        f'<td class="num"><strong>{column_totals[key]:,}</strong></td>'
        for key, _label in greta_columns
    )
    return f"""
        <table class="confusion-table sensitivity-confusion">
            <thead>
                <tr>
                    <th>Manual Label</th>
                    {''.join(f'<th>{html.escape(label)}</th>' for _key, label in greta_columns)}
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                {''.join(body_rows)}
                <tr>
                    <th>Total</th>
                    {footer_cells}
                    <td class="num"><strong>{grand_total:,}</strong></td>
                </tr>
            </tbody>
        </table>
    """


def _render_sensitivity_scenario_table(scenarios):
    rows = []
    for scenario in scenarios or []:
        metrics = scenario.get("metrics") or {}
        bucket_counts = scenario.get("bucket_counts") or {}
        if scenario.get("available"):
            status = "Available"
            accuracy = _format_optional_float(metrics.get("accuracy"), 3)
            hist_f1 = _format_optional_float(metrics.get("f1_0"), 3)
            myth_f1 = _format_optional_float(metrics.get("f1_1"), 3)
        else:
            status = html.escape(scenario.get("message", "Unavailable"))
            accuracy = hist_f1 = myth_f1 = ""
        downweighted = scenario.get("downweighted_count")
        rows.append(f"""
            <tr>
                <td><strong>{html.escape(scenario.get("label", ""))}</strong><br><span class="note">{html.escape(scenario.get("description", ""))}</span></td>
                <td class="num">{int(scenario.get("sample_count", 0)):,}</td>
                <td class="num">{int(bucket_counts.get("historical", 0)):,}</td>
                <td class="num">{int(bucket_counts.get("mythic", 0)):,}</td>
                <td class="num">{int(scenario.get("feature_count", 0)):,}</td>
                <td class="num">{accuracy}</td>
                <td class="num">{hist_f1}</td>
                <td class="num">{myth_f1}</td>
                <td class="num">{'' if downweighted is None else f'{int(downweighted):,}'}</td>
                <td>{status}</td>
            </tr>
        """)
    return f"""
        <table class="predictor-table">
            <thead>
                <tr><th>Scenario</th><th>Sample</th><th>Historical</th><th>Mythic</th><th>Features</th><th>Accuracy</th><th>Hist F1</th><th>Myth F1</th><th>Downweighted</th><th>Status</th></tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_sensitivity_stability_table(stability, scenarios, limit=30):
    scenario_labels = {scenario.get("id"): scenario.get("label", scenario.get("id", "")) for scenario in scenarios or []}
    scenario_ids = [
        "gpt_book3",
        "manual_strict",
        "agreement_only",
        "gpt_downweighted_disagreements",
    ]
    scenario_ids = [scenario_id for scenario_id in scenario_ids if scenario_id in scenario_labels]
    header_cells = "".join(
        f"<th>{html.escape(scenario_labels[scenario_id])}</th>"
        for scenario_id in scenario_ids
    )
    rows = []
    for row in (stability or [])[:limit]:
        coefficients = row.get("coefficients", {})
        coefficient_cells = "".join(
            f'<td class="num">{_format_optional_float(coefficients.get(scenario_id), 3, signed=True)}</td>'
            for scenario_id in scenario_ids
        )
        rows.append(f"""
            <tr>
                <td>{html.escape(str(row.get("phrase", "")))}</td>
                <td>{html.escape(str(row.get("baseline_direction", "")))}</td>
                {coefficient_cells}
                <td class="num">{int(row.get("present_scenario_count", 0))}</td>
                <td>{'yes' if row.get("sign_stable") else 'no'}</td>
            </tr>
        """)
    return f"""
        <table class="predictor-table">
            <thead>
                <tr><th>Feature</th><th>Baseline Direction</th>{header_cells}<th>Present</th><th>Sign Stable</th></tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_monte_carlo_table(monte_carlo, limit=25):
    if not monte_carlo or not monte_carlo.get("available"):
        return f"<p>{html.escape((monte_carlo or {}).get('message', 'Monte Carlo label-noise analysis is unavailable.'))}</p>"
    metrics = monte_carlo.get("metrics", {})
    rows = []
    for row in (monte_carlo.get("terms") or [])[:limit]:
        rows.append(f"""
            <tr>
                <td>{html.escape(str(row.get("phrase", "")))}</td>
                <td class="num">{int(row.get("present_count", 0)):,}</td>
                <td class="num">{int(row.get("positive_count", 0)):,}</td>
                <td class="num">{int(row.get("negative_count", 0)):,}</td>
                <td class="num">{_format_optional_float(row.get("mean_coefficient"), 3, signed=True)}</td>
                <td class="num">{_format_optional_float(row.get("coefficient_min"), 3, signed=True)}</td>
                <td class="num">{_format_optional_float(row.get("coefficient_max"), 3, signed=True)}</td>
                <td class="num">{_format_optional_float(row.get("sign_stability"), 2)}</td>
            </tr>
        """)
    return f"""
        <div class="metric-strip">
            <div><strong>{int(metrics.get("completed_iterations", 0)):,}</strong><span>noise runs</span></div>
            <div><strong>{_format_optional_float(metrics.get("mean_accuracy"), 3)}</strong><span>mean accuracy</span></div>
            <div><strong>{_format_optional_float(metrics.get("min_accuracy"), 3)}-{_format_optional_float(metrics.get("max_accuracy"), 3)}</strong><span>accuracy range</span></div>
            <div><strong>{_format_optional_float(metrics.get("mean_sample_count"), 1)}</strong><span>mean fitted rows</span></div>
        </div>
        <table class="predictor-table">
            <thead>
                <tr><th>Feature</th><th>Present</th><th>Positive</th><th>Negative</th><th>Mean Coef</th><th>Min</th><th>Max</th><th>Sign Stability</th></tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _write_label_sensitivity_page(sensitivity, analysis_dir, title):
    if sensitivity and sensitivity.get("available"):
        rate = sensitivity.get("exact_agreement_rate")
        scenarios = sensitivity.get("scenarios", [])
        body = f"""
            <p class="note">Manual labels come from {html.escape(str(sensitivity.get("source_document", "")))} ({html.escape(str(sensitivity.get("annotators", "")))}). GPT labels are the active three-way <code>{html.escape(str(sensitivity.get("prompt_version", "")))}</code> run using <code>{html.escape(str(sensitivity.get("model", "")))}</code>.</p>
            <div class="metric-strip">
                <div><strong>{int(sensitivity.get("sentence_count", 0)):,}</strong><span>joined sentences</span></div>
                <div><strong>{int(sensitivity.get("exact_agreement_count", 0)):,}</strong><span>exact agreements</span></div>
                <div><strong>{_format_optional_float(rate, 3)}</strong><span>agreement rate</span></div>
                <div><strong>{int(sensitivity.get("exact_comparable_count", 0)):,}</strong><span>exact-comparable rows</span></div>
            </div>
            <h3>Manual vs GPT Confusion Matrix</h3>
            {_render_label_confusion_matrix(sensitivity)}
            <h3>Refit Scenarios</h3>
            <p>The scenario models all use the same lemma TF-IDF logistic-regression setup as the current sentence analysis. Rows tagged <code>other</code> are not used in mythic-vs-historical fitting unless a scenario turns them into a mythic or historical sample.</p>
            {_render_sensitivity_scenario_table(scenarios)}
            <h3>Top Baseline Feature Stability</h3>
            <p>This table starts from the strongest GPT-labelled Book 3 coefficients and shows whether their direction survives manual-label and agreement-only refits.</p>
            {_render_sensitivity_stability_table(sensitivity.get("stability", []), scenarios)}
            <h3>Monte Carlo Label-Noise Stress Test</h3>
            <p>This stress test resamples labels from the observed manual-vs-GPT confusion rates and refits the lemma model repeatedly. It is a sensitivity diagnostic, not a claim that either label set is ground truth.</p>
            {_render_monte_carlo_table(sensitivity.get("monte_carlo"))}
        """
    else:
        body = f"<p>{html.escape((sensitivity or {}).get('message', 'Manual label sensitivity analysis is unavailable.'))}</p>"
    _write_analysis_html_page(
        analysis_dir,
        "label_sensitivity.html",
        "Manual Label Sensitivity",
        "How sentence-model conclusions move under unreliable labels",
        body,
        title,
    )


def _fmt_stylometry_number(value, digits=3):
    if value is None:
        return "n/a"
    try:
        if math.isnan(value):
            return "n/a"
    except TypeError:
        pass
    if isinstance(value, int):
        return f"{value:,}"
    return f"{float(value):.{digits}f}"


def _stylometry_feature_label(feature):
    feature = str(feature or "")
    prefixes = {
        "word:": "word ",
        "char4:": "char 4-gram ",
        "upos:": "UPOS ",
        "deprel:": "DepRel ",
        "deprel_upos:": "DepRel/UPOS ",
        "feat:": "Feature ",
        "head_child_upos:": "Head>child ",
        "head_direction:": "Head direction ",
        "root_upos:": "Root UPOS ",
        "sentence_len_bin:": "Sentence length ",
        "func:": "Function word ",
        "func_upos:": "Function UPOS ",
        "func_form_upos:": "Function form/UPOS ",
        "func_deprel:": "Function DepRel ",
    }
    for prefix, label in prefixes.items():
        if feature.startswith(prefix):
            return label + feature[len(prefix) :]
    return feature


def _render_stylometry_metric_strip(metrics):
    return f"""
        <div class="metric-strip">
            <div><strong>{int(metrics.get('passage_count') or 0):,}</strong><span>parsed passage units</span></div>
            <div><strong>{int(metrics.get('sentence_count') or 0):,}</strong><span>sentences</span></div>
            <div><strong>{int(metrics.get('token_count') or 0):,}</strong><span>word tokens</span></div>
            <div><strong>{int(metrics.get('book_count') or 0):,}</strong><span>books represented</span></div>
            <div><strong>{int(metrics.get('messenian_wars_count') or 0):,}</strong><span>Messenian Wars units</span></div>
            <div><strong>{int(metrics.get('book8_count') or 0):,}</strong><span>Book 8 units</span></div>
        </div>
    """


def _render_stylometry_notes(notes):
    if not notes:
        return ""
    items = "".join(f"<li>{html.escape(str(note))}</li>" for note in notes)
    return f'<ul class="compact-list stylometry-notes">{items}</ul>'


def _render_stylometry_feature_cards(feature_sets):
    if not feature_sets:
        return "<p>No stylometry feature sets are available yet.</p>"
    cards = []
    for feature_set in feature_sets:
        features = feature_set.get("features") or []
        feature_list = "".join(
            f"<span>{html.escape(_stylometry_feature_label(feature))}</span>"
            for feature in features[:12]
        )
        cards.append(
            f"""
            <section class="hub-card stylometry-feature-card">
                <h3>{html.escape(feature_set.get('label') or '')}</h3>
                <p>{html.escape(feature_set.get('description') or '')}</p>
                <p><strong>{int(feature_set.get('feature_count') or 0):,}</strong> selected features; projection method: <strong>{html.escape(feature_set.get('projection_method') or 'n/a')}</strong>.</p>
                <div class="stylometry-feature-tags">{feature_list}</div>
            </section>
            """
        )
    return f'<div class="hub-grid">{"".join(cards)}</div>'


def _stylometry_json_payload(stylometry_data):
    return json.dumps(stylometry_data or {}, ensure_ascii=False).replace("</", "<\\/")


def _render_stylometry_comparison_table(feature_set):
    rows = []
    for comparison in feature_set.get("comparisons") or []:
        status = "ready" if comparison.get("available") else comparison.get("message", "unavailable")
        rows.append(
            f"""
            <tr>
                <td>{html.escape(comparison.get('label') or '')}</td>
                <td class="num">{int(comparison.get('positive_count') or 0):,}</td>
                <td class="num">{int(comparison.get('negative_count') or 0):,}</td>
                <td class="num">{_fmt_stylometry_number(comparison.get('within_positive'))}</td>
                <td class="num">{_fmt_stylometry_number(comparison.get('within_negative'))}</td>
                <td class="num">{_fmt_stylometry_number(comparison.get('between'))}</td>
                <td class="num">{_fmt_stylometry_number(comparison.get('separation'))}</td>
                <td>{html.escape(status)}</td>
            </tr>
            """
        )
    return f"""
        <table class="predictor-table stylometry-comparison-table">
            <thead>
                <tr>
                    <th>Question</th>
                    <th>Target n</th>
                    <th>Other n</th>
                    <th>Within target</th>
                    <th>Within other</th>
                    <th>Between</th>
                    <th>Separation</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_stylometry_outlier_table(feature_set):
    rows = []
    for row in feature_set.get("outliers") or []:
        pid = row.get("passage_id")
        rows.append(
            f"""
            <tr>
                <td>{_translation_passage_link(pid)}</td>
                <td class="num">{_fmt_stylometry_number(row.get('score'))}</td>
                <td class="num">{_fmt_stylometry_number(row.get('nearest_distance'))}</td>
            </tr>
            """
        )
    if not rows:
        return "<p>No outlier table is available yet.</p>"
    return f"""
        <table class="predictor-table">
            <thead><tr><th>Passage</th><th>Mean distance to nearest neighbors</th><th>Nearest distance</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_stylometry_neighbor_table(feature_set):
    rows = []
    for row in (feature_set.get("nearest_neighbors") or [])[:16]:
        neighbors = ", ".join(
            f"{html.escape(neighbor.get('passage_id') or '')} ({_fmt_stylometry_number(neighbor.get('distance'))})"
            for neighbor in row.get("neighbors", [])[:4]
        )
        rows.append(
            f"""
            <tr>
                <td>{_translation_passage_link(row.get('passage_id'))}</td>
                <td>{neighbors}</td>
            </tr>
            """
        )
    if not rows:
        return "<p>No nearest-neighbor table is available yet.</p>"
    return f"""
        <table class="predictor-table">
            <thead><tr><th>Passage</th><th>Nearest neighbors by cosine distance</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_stylometry_delta_list(rows, empty_message):
    if not rows:
        return f"<p>{html.escape(empty_message)}</p>"
    items = "".join(
        f"<li><code>{html.escape(_stylometry_feature_label(row.get('feature')))}</code> "
        f"<span>{_fmt_stylometry_number(row.get('delta'), 4)}</span></li>"
        for row in rows[:10]
    )
    return f'<ol class="stylometry-delta-list">{items}</ol>'


def _render_stylometry_feature_deltas(feature_set):
    sections = []
    for comparison in feature_set.get("comparisons") or []:
        if not comparison.get("available"):
            continue
        sections.append(
            f"""
            <section class="stylometry-delta-card">
                <h4>{html.escape(comparison.get('label') or '')}</h4>
                <div class="stylometry-delta-grid">
                    <div>
                        <h5>Higher in {html.escape(comparison.get('positive_label') or 'target')}</h5>
                        {_render_stylometry_delta_list(comparison.get('top_positive_features'), 'No positive feature deltas.')}
                    </div>
                    <div>
                        <h5>Higher in {html.escape(comparison.get('negative_label') or 'other')}</h5>
                        {_render_stylometry_delta_list(comparison.get('top_negative_features'), 'No negative feature deltas.')}
                    </div>
                </div>
            </section>
            """
        )
    return "".join(sections) or "<p>No target-vs-rest feature deltas are available with the current parsed coverage.</p>"


def generate_stylometry_pages(stylometry_data, output_dir, title):
    """Generate morphosyntactic stylometry and traditional baseline pages."""
    analysis_dir = os.path.join(output_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)

    data = stylometry_data or {}
    metrics = data.get("metrics") or {}
    feature_sets = data.get("feature_sets") or []
    timestamp = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
    model = data.get("model") or "gpt-5.4-mini"
    method_notes = _render_stylometry_notes(data.get("method_notes"))
    coverage_notes = _render_stylometry_notes(data.get("coverage_notes"))
    feature_cards = _render_stylometry_feature_cards(feature_sets)

    index_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Stylometry</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>Morphosyntactic stylometry and traditional baselines</p>
    </header>
    {_site_nav("../", "analysis")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Analyses</a> &rsaquo; Stylometry</div>
        <h2>Stylometry</h2>
        <p>This section compares passage-level units using the current <code>{html.escape(model)}</code> LLM grammar parses. It publishes the morphosyntactic feature model alongside traditional word-frequency and character n-gram baselines.</p>
        {_render_stylometry_metric_strip(metrics)}
        {coverage_notes}

        <div class="hub-grid">
            <section class="hub-card">
                <h3>Interactive Projection</h3>
                <p>Mouse over passages in each feature family to inspect labels, token counts, and nearest-neighbor context.</p>
                <a href="stylometry-umap.html">Open Projection</a>
            </section>
            <section class="hub-card">
                <h3>Statistical Outputs</h3>
                <p>Distance summaries, outlier lists, nearest-neighbor tables, and target-vs-rest feature deltas.</p>
                <a href="stylometry-statistics.html">Open Statistics</a>
            </section>
        </div>

        <h2>Feature Families</h2>
        {feature_cards}

        <h2>Current Repo State</h2>
        {method_notes}
        <footer>Generated on {timestamp} from the PostgreSQL database</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "stylometry.html"), "w", encoding="utf-8") as f:
        f.write(index_page)

    payload = _stylometry_json_payload(data)
    umap_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Stylometry Projection</title>
    <link rel="stylesheet" href="../css/style.css">
    <script src="https://d3js.org/d3.v7.min.js"></script>
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>Interactive stylometry projection</p>
    </header>
    {_site_nav("../", "analysis")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Analyses</a> &rsaquo; <a href="stylometry.html">Stylometry</a> &rsaquo; Projection</div>
        <h2>Stylometry Projection</h2>
        <div class="stylometry-controls">
            <label for="stylometry-feature-select">Feature family</label>
            <select id="stylometry-feature-select"></select>
            <span id="stylometry-method" class="stylometry-method"></span>
        </div>
        <div id="stylometry-note" class="note"></div>
        <div class="stylometry-chart-wrap">
            <svg id="stylometry-chart" class="stylometry-chart" viewBox="0 0 980 620" role="img" aria-label="Interactive passage projection"></svg>
            <div id="stylometry-tooltip" class="stylometry-tooltip" hidden></div>
        </div>
        <p class="stylometry-legend"><span class="legend-dot mess"></span>Messenian Wars <span class="legend-dot book4"></span>Book 4 <span class="legend-dot book8"></span>Book 8 <span class="legend-dot other"></span>Other parsed passages</p>
        <footer>Generated on {timestamp} from the PostgreSQL database</footer>
    </div>
    <script id="stylometry-data" type="application/json">{payload}</script>
    <script>
    (function () {{
        const payload = JSON.parse(document.getElementById("stylometry-data").textContent || "{{}}");
        const featureSets = payload.feature_sets || [];
        const select = document.getElementById("stylometry-feature-select");
        const method = document.getElementById("stylometry-method");
        const note = document.getElementById("stylometry-note");
        const tooltip = document.getElementById("stylometry-tooltip");
        const svg = d3.select("#stylometry-chart");
        const width = 980;
        const height = 620;
        const margin = {{ top: 36, right: 36, bottom: 54, left: 58 }};

        featureSets.forEach(function (featureSet) {{
            const option = document.createElement("option");
            option.value = featureSet.id;
            option.textContent = featureSet.label;
            select.appendChild(option);
        }});

        function color(point) {{
            if (point.is_messenian_wars) return "#b94a38";
            if (point.is_book8) return "#397d7a";
            if (point.is_book4) return "#9a762d";
            return "#5f6673";
        }}

        function extent(values) {{
            const e = d3.extent(values);
            if (e[0] === undefined || e[1] === undefined) return [-1, 1];
            if (e[0] === e[1]) return [e[0] - 1, e[1] + 1];
            const pad = (e[1] - e[0]) * 0.08;
            return [e[0] - pad, e[1] + pad];
        }}

        function render(featureSetId) {{
            const featureSet = featureSets.find(function (item) {{ return item.id === featureSetId; }}) || featureSets[0];
            svg.selectAll("*").remove();
            if (!featureSet) {{
                note.textContent = "No stylometry projection is available yet.";
                method.textContent = "";
                return;
            }}
            const points = featureSet.points || [];
            method.textContent = "Projection: " + (featureSet.projection_method || "n/a") + " | features: " + (featureSet.feature_count || 0);
            note.textContent = featureSet.projection_note || featureSet.description || "";
            const xScale = d3.scaleLinear().domain(extent(points.map(function (d) {{ return d.x; }}))).range([margin.left, width - margin.right]);
            const yScale = d3.scaleLinear().domain(extent(points.map(function (d) {{ return d.y; }}))).range([height - margin.bottom, margin.top]);

            svg.append("line").attr("x1", margin.left).attr("x2", width - margin.right).attr("y1", height - margin.bottom).attr("y2", height - margin.bottom).attr("class", "stylometry-axis");
            svg.append("line").attr("x1", margin.left).attr("x2", margin.left).attr("y1", margin.top).attr("y2", height - margin.bottom).attr("class", "stylometry-axis");
            svg.append("text").attr("x", width / 2).attr("y", height - 15).attr("text-anchor", "middle").attr("class", "stylometry-axis-label").text("Dimension 1");
            svg.append("text").attr("x", 18).attr("y", height / 2).attr("text-anchor", "middle").attr("transform", "rotate(-90 18 " + (height / 2) + ")").attr("class", "stylometry-axis-label").text("Dimension 2");

            const neighborsByPassage = new Map((featureSet.nearest_neighbors || []).map(function (row) {{ return [row.passage_id, row.neighbors || []]; }}));
            svg.append("g").selectAll("circle")
                .data(points)
                .join("circle")
                .attr("cx", function (d) {{ return xScale(d.x); }})
                .attr("cy", function (d) {{ return yScale(d.y); }})
                .attr("r", 7)
                .attr("fill", color)
                .attr("class", "stylometry-point")
                .on("mousemove", function (event, d) {{
                    const labels = (d.labels || []).length ? d.labels.join(", ") : "other parsed passage";
                    const neighbors = (neighborsByPassage.get(d.passage_id) || []).slice(0, 3).map(function (n) {{
                        return n.passage_id + " (" + Number(n.distance).toFixed(3) + ")";
                    }}).join("<br>");
                    tooltip.hidden = false;
                    tooltip.style.left = (event.offsetX + 18) + "px";
                    tooltip.style.top = (event.offsetY + 18) + "px";
                    tooltip.innerHTML = "<strong>" + d.passage_id + "</strong><br>" + labels + "<br>" + d.sentence_count + " sentences; " + d.token_count + " tokens" + (neighbors ? "<hr><strong>Nearest</strong><br>" + neighbors : "");
                }})
                .on("mouseleave", function () {{
                    tooltip.hidden = true;
                }});

            svg.append("g").selectAll("text")
                .data(points)
                .join("text")
                .attr("x", function (d) {{ return xScale(d.x) + 9; }})
                .attr("y", function (d) {{ return yScale(d.y) - 9; }})
                .attr("class", "stylometry-point-label")
                .text(function (d) {{ return d.passage_id; }});
        }}

        select.addEventListener("change", function () {{ render(select.value); }});
        if (featureSets.length) {{
            select.value = featureSets[0].id;
            render(featureSets[0].id);
        }} else {{
            render(null);
        }}
    }}());
    </script>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "stylometry-umap.html"), "w", encoding="utf-8") as f:
        f.write(umap_page)

    feature_sections = []
    for feature_set in feature_sets:
        feature_sections.append(
            f"""
            <section class="stylometry-stat-section">
                <h2>{html.escape(feature_set.get('label') or '')}</h2>
                <p>{html.escape(feature_set.get('description') or '')}</p>
                {_render_stylometry_comparison_table(feature_set)}
                <h3>Feature Deltas</h3>
                {_render_stylometry_feature_deltas(feature_set)}
                <h3>Outlier Passages</h3>
                {_render_stylometry_outlier_table(feature_set)}
                <h3>Nearest Neighbors</h3>
                {_render_stylometry_neighbor_table(feature_set)}
            </section>
            """
        )
    stats_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Stylometry Statistics</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>Stylometry statistical outputs</p>
    </header>
    {_site_nav("../", "analysis")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Analyses</a> &rsaquo; <a href="stylometry.html">Stylometry</a> &rsaquo; Statistics</div>
        <h2>Stylometry Statistics</h2>
        <p>Distances are cosine distances over normalized feature counts. Positive separation means target passages are farther from the comparison group than their available within-group baseline.</p>
        {''.join(feature_sections) if feature_sections else '<p>No stylometry statistics are available yet.</p>'}
        <footer>Generated on {timestamp} from the PostgreSQL database</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "stylometry-statistics.html"), "w", encoding="utf-8") as f:
        f.write(stats_page)

    print(
        f"Stylometry pages generated: {int(metrics.get('passage_count') or 0)} passage units, "
        f"{len(feature_sets)} feature families."
    )


PEOPLE_CLASS_LABELS = {
    "anonymous_female": "Anonymous female",
    "named_female": "Named female",
    "anonymous_male": "Anonymous male",
    "named_male": "Named male",
}

PEOPLE_CLASS_COLORS = {
    "anonymous_female": "#d56f7f",
    "named_female": "#a23e73",
    "anonymous_male": "#4f96a2",
    "named_male": "#315f9f",
}

PEOPLE_BUCKET_LABELS = {
    "mythic": "Mythic",
    "historical": "Historical",
    "other": "Other",
}


def _people_class_css(people_class):
    return people_class.replace("_", "-")


def _people_percent(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    if not math.isfinite(numeric):
        numeric = 0.0
    return f"{numeric:.1f}%"


def _people_p_value(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(numeric):
        return "n/a"
    if numeric < 0.001:
        return f"{numeric:.2e}"
    return f"{numeric:.4f}"


def _render_people_legend(classes):
    items = []
    for people_class in classes:
        items.append(
            f"""
            <span class="people-legend-item">
                <span class="people-legend-swatch people-class-{_people_class_css(people_class)}"></span>
                {html.escape(PEOPLE_CLASS_LABELS.get(people_class, people_class))}
            </span>
            """
        )
    return f"<div class=\"people-legend\">{''.join(items)}</div>"


def _people_matrix_value(matrix, bucket, people_class, default=0):
    return (matrix or {}).get(bucket, {}).get(people_class, default)


def _render_people_percentage_table(analysis):
    buckets = analysis.get("buckets", [])
    classes = analysis.get("classes", [])
    percentages = analysis.get("percentages", {})
    counts = analysis.get("counts", {})
    rows = []
    for bucket in buckets:
        row_total = sum(int(_people_matrix_value(counts, bucket, people_class, 0)) for people_class in classes)
        cells = "".join(
            f'<td class="num">{_people_percent(_people_matrix_value(percentages, bucket, people_class, 0.0))}</td>'
            for people_class in classes
        )
        rows.append(
            f"""
            <tr>
                <th>{html.escape(PEOPLE_BUCKET_LABELS.get(bucket, bucket.title()))}</th>
                {cells}
                <td class="num">{row_total:,}</td>
            </tr>
            """
        )
    header_cells = "".join(
        f"<th>{html.escape(PEOPLE_CLASS_LABELS.get(people_class, people_class))}</th>"
        for people_class in classes
    )
    return f"""
        <table class="predictor-table people-table people-headline-table">
            <thead>
                <tr><th>Sentence bucket</th>{header_cells}<th>Gendered mention rows</th></tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_people_count_table(analysis, key, final_column_label):
    buckets = analysis.get("buckets", [])
    classes = analysis.get("classes", [])
    matrix = analysis.get(key, {})
    rows = []
    for bucket in buckets:
        row_total = sum(int(_people_matrix_value(matrix, bucket, people_class, 0)) for people_class in classes)
        cells = "".join(
            f'<td class="num">{int(_people_matrix_value(matrix, bucket, people_class, 0)):,}</td>'
            for people_class in classes
        )
        rows.append(
            f"""
            <tr>
                <th>{html.escape(PEOPLE_BUCKET_LABELS.get(bucket, bucket.title()))}</th>
                {cells}
                <td class="num">{row_total:,}</td>
            </tr>
            """
        )
    header_cells = "".join(
        f"<th>{html.escape(PEOPLE_CLASS_LABELS.get(people_class, people_class))}</th>"
        for people_class in classes
    )
    return f"""
        <table class="predictor-table people-table">
            <thead>
                <tr><th>Sentence bucket</th>{header_cells}<th>{html.escape(final_column_label)}</th></tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_people_stacked_bars(analysis):
    buckets = analysis.get("buckets", [])
    classes = analysis.get("classes", [])
    percentages = analysis.get("percentages", {})
    counts = analysis.get("counts", {})
    width = 760
    height = 230
    label_x = 24
    chart_x = 130
    chart_width = 500
    total_x = chart_x + chart_width + 18
    legend_y = 24
    rows = []
    legend_items = []
    for index, people_class in enumerate(classes):
        x = 24 + index * 175
        label = PEOPLE_CLASS_LABELS.get(people_class, people_class)
        color = PEOPLE_CLASS_COLORS.get(people_class, "#777")
        legend_items.append(
            f"""
            <rect x="{x}" y="{legend_y}" width="12" height="12" rx="2" fill="{color}"></rect>
            <text x="{x + 18}" y="{legend_y + 11}" font-size="13" fill="#333">{html.escape(label)}</text>
            """
        )
    for bucket in buckets:
        total = sum(int(_people_matrix_value(counts, bucket, people_class, 0)) for people_class in classes)
        row_index = len(rows)
        y = 72 + row_index * 42
        x_cursor = chart_x
        segments = [
            f'<text x="{label_x}" y="{y + 21}" font-size="15" font-weight="700" fill="#4b4338">{html.escape(PEOPLE_BUCKET_LABELS.get(bucket, bucket.title()))}</text>',
            f'<rect x="{chart_x}" y="{y}" width="{chart_width}" height="28" rx="4" fill="#ece6dd"></rect>',
        ]
        for people_class in classes:
            value = float(_people_matrix_value(percentages, bucket, people_class, 0.0) or 0.0)
            count = int(_people_matrix_value(counts, bucket, people_class, 0))
            if value <= 0:
                continue
            segment_width = chart_width * value / 100.0
            label = PEOPLE_CLASS_LABELS.get(people_class, people_class)
            color = PEOPLE_CLASS_COLORS.get(people_class, "#777")
            segments.append(
                f"""
                <rect x="{x_cursor:.2f}" y="{y}" width="{segment_width:.2f}" height="28" fill="{color}">
                    <title>{html.escape(label)}: {_people_percent(value)} ({count:,})</title>
                </rect>
                """
            )
            if segment_width >= 45:
                segments.append(
                    f'<text x="{x_cursor + segment_width / 2:.2f}" y="{y + 19}" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">{_people_percent(value)}</text>'
                )
            x_cursor += segment_width
        rows.append(
            f"""
            {''.join(segments)}
            <text x="{total_x}" y="{y + 20}" font-size="14" font-weight="700" fill="#4b4338">{total:,}</text>
            """
        )
    axis_y = 204
    return f"""
        <section class="people-viz-panel">
            <h3>Class Composition by Sentence Bucket</h3>
            <div class="people-svg-wrap">
                <svg class="people-chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Stacked percentage bars for people classes by sentence bucket">
                    <title>Class composition by sentence bucket</title>
                    {''.join(legend_items)}
                    {''.join(rows)}
                    <line x1="{chart_x}" y1="{axis_y}" x2="{chart_x + chart_width}" y2="{axis_y}" stroke="#c9c0b3"></line>
                    <text x="{chart_x}" y="{axis_y + 18}" text-anchor="middle" font-size="12" fill="#776b5d">0%</text>
                    <text x="{chart_x + chart_width / 2}" y="{axis_y + 18}" text-anchor="middle" font-size="12" fill="#776b5d">50%</text>
                    <text x="{chart_x + chart_width}" y="{axis_y + 18}" text-anchor="middle" font-size="12" fill="#776b5d">100%</text>
                    <text x="{total_x}" y="{axis_y + 18}" font-size="12" fill="#776b5d">rows</text>
                </svg>
            </div>
        </section>
    """


def _render_people_share_bars(analysis):
    shares = analysis.get("shares", {})
    width = 760
    height = 250
    label_x = 24
    chart_x = 130
    chart_width = 500
    rows = []
    for bucket in analysis.get("buckets", []):
        row_index = len(rows)
        bucket_shares = shares.get(bucket, {})
        female = float(bucket_shares.get("female_percent") or 0.0)
        named = float(bucket_shares.get("named_percent") or 0.0)
        y = 54 + row_index * 62
        female_width = chart_width * female / 100.0
        named_width = chart_width * named / 100.0
        rows.append(
            f"""
            <text x="{label_x}" y="{y + 22}" font-size="15" font-weight="700" fill="#4b4338">{html.escape(PEOPLE_BUCKET_LABELS.get(bucket, bucket.title()))}</text>
            <text x="{chart_x - 12}" y="{y + 9}" text-anchor="end" font-size="12" fill="#4b4338">Female</text>
            <rect x="{chart_x}" y="{y}" width="{chart_width}" height="12" rx="6" fill="#ece6dd"></rect>
            <rect x="{chart_x}" y="{y}" width="{female_width:.2f}" height="12" rx="6" fill="#a23e73"></rect>
            <text x="{chart_x + chart_width + 18}" y="{y + 11}" font-size="13" font-weight="700" fill="#4b4338">{_people_percent(female)}</text>
            <text x="{chart_x - 12}" y="{y + 34}" text-anchor="end" font-size="12" fill="#4b4338">Named</text>
            <rect x="{chart_x}" y="{y + 25}" width="{chart_width}" height="12" rx="6" fill="#ece6dd"></rect>
            <rect x="{chart_x}" y="{y + 25}" width="{named_width:.2f}" height="12" rx="6" fill="#315f9f"></rect>
            <text x="{chart_x + chart_width + 18}" y="{y + 36}" font-size="13" font-weight="700" fill="#4b4338">{_people_percent(named)}</text>
            """
        )
    axis_y = 226
    return f"""
        <section class="people-viz-panel">
            <h3>Female and Named Shares</h3>
            <div class="people-svg-wrap">
                <svg class="people-chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Female and named share bars by sentence bucket">
                    <title>Female and named shares by sentence bucket</title>
                    {''.join(rows)}
                    <line x1="{chart_x}" y1="{axis_y}" x2="{chart_x + chart_width}" y2="{axis_y}" stroke="#c9c0b3"></line>
                    <text x="{chart_x}" y="{axis_y + 18}" text-anchor="middle" font-size="12" fill="#776b5d">0%</text>
                    <text x="{chart_x + chart_width / 2}" y="{axis_y + 18}" text-anchor="middle" font-size="12" fill="#776b5d">50%</text>
                    <text x="{chart_x + chart_width}" y="{axis_y + 18}" text-anchor="middle" font-size="12" fill="#776b5d">100%</text>
                </svg>
            </div>
        </section>
    """


def _residual_cell_style(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    if not math.isfinite(numeric) or numeric == 0:
        return ""
    intensity = min(abs(numeric) / 2.5, 1.0)
    alpha = 0.12 + 0.32 * intensity
    if numeric > 0:
        return f' style="background-color: rgba(176, 64, 91, {alpha:.3f});"'
    return f' style="background-color: rgba(49, 95, 159, {alpha:.3f});"'


def _render_people_residual_heatmap(analysis):
    chi_square = analysis.get("chi_square")
    if not chi_square:
        return '<p class="note">Not enough bucketed people rows are available for a chi-squared residual heatmap.</p>'
    classes = analysis.get("classes", [])
    rows = []
    residuals = analysis.get("residuals", {})
    for bucket in analysis.get("buckets", []):
        cells = []
        for people_class in classes:
            value = float(_people_matrix_value(residuals, bucket, people_class, 0.0) or 0.0)
            cells.append(
                f'<td class="num"{_residual_cell_style(value)}>{value:+.2f}</td>'
            )
        rows.append(
            f"""
            <tr>
                <th>{html.escape(PEOPLE_BUCKET_LABELS.get(bucket, bucket.title()))}</th>
                {''.join(cells)}
            </tr>
            """
        )
    header_cells = "".join(
        f"<th>{html.escape(PEOPLE_CLASS_LABELS.get(people_class, people_class))}</th>"
        for people_class in classes
    )
    return f"""
        <section class="people-viz-panel">
            <h3>Standardized Residual Heatmap</h3>
            <p>Positive cells are more frequent than expected under independence; negative cells are less frequent.</p>
            <table class="predictor-table people-table people-residual-table">
                <thead><tr><th>Sentence bucket</th>{header_cells}</tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </section>
    """


def _render_people_pairwise_tests(analysis):
    rows = []
    for test in analysis.get("pairwise_tests", []):
        rows.append(
            f"""
            <tr>
                <td>{html.escape(test.get("comparison", ""))}</td>
                <td class="num">{_format_optional_number(test.get("chi2"), 3)}</td>
                <td class="num">{int(test.get("dof") or 0)}</td>
                <td class="num">{_people_p_value(test.get("p_value"))}</td>
                <td class="num">{_people_p_value(test.get("p_holm"))}</td>
                <td class="num">{_format_optional_number(test.get("cramers_v"), 3)}</td>
            </tr>
            """
        )
    if not rows:
        return ""
    return f"""
        <h3>Pairwise Bucket Tests</h3>
        <table class="predictor-table people-table">
            <thead>
                <tr><th>Comparison</th><th>Chi2</th><th>dof</th><th>p</th><th>Holm p</th><th>Cramer's V</th></tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_people_bucket_sample_table(analysis):
    sample = analysis.get("bucket_sample", {})
    rows = []
    for bucket in analysis.get("buckets", []):
        bucket_sample = sample.get(bucket, {})
        rows.append(
            f"""
            <tr>
                <th>{html.escape(PEOPLE_BUCKET_LABELS.get(bucket, bucket.title()))}</th>
                <td class="num">{int(bucket_sample.get("sentences") or 0):,}</td>
                <td class="num">{int(bucket_sample.get("sections") or 0):,}</td>
            </tr>
            """
        )
    return f"""
        <table class="predictor-table people-table people-sample-table">
            <thead><tr><th>Sentence bucket</th><th>Sentences in processed sections</th><th>Sections containing bucket</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _write_section_people_page(section_people_analysis, analysis_dir, title):
    analysis = section_people_analysis or {}
    summary = analysis.get("summary", {})
    if analysis.get("available"):
        chi_square = analysis.get("chi_square") or {}
        chi_square_metrics = ""
        if chi_square:
            chi_square_metrics = f"""
                <div><strong>{_people_p_value(chi_square.get("p_value"))}</strong><span>overall chi-squared p</span></div>
                <div><strong>{_format_optional_number(chi_square.get("cramers_v"), 3)}</strong><span>Cramer's V</span></div>
            """
        body = f"""
            <div class="metric-strip">
                <div><strong>{int(summary.get("processed_sections") or 0):,}</strong><span>sections processed</span></div>
                <div><strong>{int(summary.get("processed_sentences") or 0):,}</strong><span>sentences in those sections</span></div>
                <div><strong>{int(summary.get("sentences_with_mentions") or 0):,}</strong><span>sentences with mentions</span></div>
                <div><strong>{int(summary.get("mention_rows") or 0):,}</strong><span>mention rows, including unknown gender</span></div>
                <div><strong>{int(summary.get("total_tokens") or 0):,}</strong><span>Batch API tokens used</span></div>
                <div><strong>{_people_percent(summary.get("coverage_percent") or 0.0)}</strong><span>section coverage</span></div>
                {chi_square_metrics}
            </div>

            <h2>Headline Percentages</h2>
            <p>Percentages are by gendered mention row inside each sentence bucket.</p>
            {_render_people_percentage_table(analysis)}

            <div class="people-visual-grid">
                {_render_people_stacked_bars(analysis)}
                {_render_people_share_bars(analysis)}
            </div>

            <h2>Counts</h2>
            <h3>Mention-Row Counts</h3>
            {_render_people_count_table(analysis, "counts", "Total")}
            <h3>Exact Person Totals</h3>
            <p>Exact totals expand countable groups and count uncounted groups as zero.</p>
            {_render_people_count_table(analysis, "exact_counts", "Exact total")}

            <h2>Sample Shape</h2>
            {_render_people_bucket_sample_table(analysis)}

            <h2>Difference Tests</h2>
            {_render_people_residual_heatmap(analysis)}
            {_render_people_pairwise_tests(analysis)}
        """
    else:
        message = analysis.get("message") or "No people extraction data is available yet."
        body = f"""
            <p class="note">{html.escape(message)}</p>
            <p>The daily pipeline will publish this report once section people batches have completed and been fetched.</p>
        """

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - People and Gender Mentions</title>
    <link rel="stylesheet" href="../css/style.css?v=section-people-3">
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>Named and anonymous people by sentence bucket</p>
    </header>
    {_site_nav("../", "analysis")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Analyses</a> &rsaquo; People and Gender</div>
        <h2>People and Gender Mentions</h2>
        <p>This page reports section-by-section Batch API extraction using prompt <code>{html.escape(str(analysis.get("prompt_version") or ""))}</code>, joined to sentence buckets from <code>{html.escape(str(analysis.get("bucket_prompt_version") or ""))}</code>.</p>
        {body}
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "people-gender.html"), "w", encoding="utf-8") as f:
        f.write(page)


def _dict_summary(values):
    if not values:
        return ""
    return ", ".join(
        f"{html.escape(str(key))}: {int(value):,}"
        for key, value in values.items()
    )


def _model_metric(metrics, key, digits=3):
    if not metrics or metrics.get(key) is None:
        return "n/a"
    return _fmt_stylometry_number(metrics.get(key), digits)


def _flatten_stylometric_classifier_rows(model_data):
    rows = []
    for result in model_data.get("classifiers") or []:
        metrics = result.get("metrics") or {}
        rows.append(
            {
                "source_id": result.get("source_id"),
                "source_label": result.get("source_label"),
                "task_id": result.get("task_id"),
                "task_label": result.get("task_label"),
                "feature_set_id": result.get("feature_set_id"),
                "feature_set_label": result.get("feature_set_label"),
                "available": bool(result.get("available")),
                "message": result.get("message", ""),
                "sample_count": result.get("sample_count", 0),
                "label_counts": _dict_summary(result.get("label_counts")),
                "feature_count": result.get("feature_count", 0),
                "cv_folds": metrics.get("cv_folds"),
                "accuracy": metrics.get("accuracy"),
                "baseline_accuracy": metrics.get("baseline_accuracy"),
                "accuracy_delta_vs_baseline": metrics.get("accuracy_delta_vs_baseline"),
                "macro_f1": metrics.get("macro_f1"),
                "weighted_f1": metrics.get("weighted_f1"),
            }
        )
    return rows


def _flatten_stylometric_classifier_feature_rows(model_data):
    rows = []
    for result in model_data.get("classifiers") or []:
        for feature in result.get("top_features") or []:
            rows.append(
                {
                    "source_id": result.get("source_id"),
                    "source_label": result.get("source_label"),
                    "task_id": result.get("task_id"),
                    "task_label": result.get("task_label"),
                    "feature_set_id": result.get("feature_set_id"),
                    "feature_set_label": result.get("feature_set_label"),
                    "class_label": feature.get("class_label"),
                    "direction": feature.get("direction"),
                    "feature": feature.get("feature"),
                    "feature_label": _stylometry_feature_label(feature.get("feature")),
                    "coefficient": feature.get("coefficient"),
                }
            )
    return rows


def _flatten_stylometric_regression_rows(model_data):
    rows = []
    for result in model_data.get("regressions") or []:
        metrics = result.get("metrics") or {}
        rows.append(
            {
                "variant_id": result.get("variant_id"),
                "variant_label": result.get("variant_label"),
                "include_books_4_8": bool(result.get("include_books_4_8")),
                "feature_set_id": result.get("feature_set_id"),
                "feature_set_label": result.get("feature_set_label"),
                "available": bool(result.get("available")),
                "message": result.get("message", ""),
                "sample_count": result.get("sample_count", 0),
                "book_count": result.get("book_count", 0),
                "book_counts": _dict_summary(result.get("book_counts")),
                "feature_count": result.get("feature_count", 0),
                "cv_folds": metrics.get("cv_folds"),
                "selected_alpha": metrics.get("selected_alpha"),
                "r2": metrics.get("r2"),
                "mae": metrics.get("mae"),
                "baseline_mae": metrics.get("baseline_mae"),
                "mae_improvement_vs_baseline": metrics.get("mae_improvement_vs_baseline"),
                "rmse": metrics.get("rmse"),
                "baseline_rmse": metrics.get("baseline_rmse"),
                "rmse_improvement_vs_baseline": metrics.get("rmse_improvement_vs_baseline"),
            }
        )
    return rows


def _flatten_stylometric_regression_feature_rows(model_data):
    rows = []
    for result in model_data.get("regressions") or []:
        for feature in result.get("top_features") or []:
            rows.append(
                {
                    "variant_id": result.get("variant_id"),
                    "variant_label": result.get("variant_label"),
                    "include_books_4_8": bool(result.get("include_books_4_8")),
                    "feature_set_id": result.get("feature_set_id"),
                    "feature_set_label": result.get("feature_set_label"),
                    "direction": feature.get("direction"),
                    "feature": feature.get("feature"),
                    "feature_label": _stylometry_feature_label(feature.get("feature")),
                    "coefficient": feature.get("coefficient"),
                }
            )
    return rows


def _write_stylometric_model_csvs(model_data, analysis_dir):
    data_dir = os.path.join(analysis_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    outputs = {
        "stylometric_sentence_classifier_metrics.csv": _flatten_stylometric_classifier_rows(model_data),
        "stylometric_sentence_classifier_features.csv": _flatten_stylometric_classifier_feature_rows(model_data),
        "stylometric_book_regression_metrics.csv": _flatten_stylometric_regression_rows(model_data),
        "stylometric_book_regression_features.csv": _flatten_stylometric_regression_feature_rows(model_data),
    }
    for filename, rows in outputs.items():
        pd.DataFrame(rows).to_csv(os.path.join(data_dir, filename), index=False)


def _render_stylometric_source_notes(model_data):
    rows = []
    for source in model_data.get("label_sources") or []:
        rows.append(
            f"""
            <tr>
                <td>{html.escape(source.get('label') or '')}</td>
                <td>{html.escape(source.get('prompt_version') or '')}</td>
                <td>{html.escape(source.get('model') or '')}</td>
                <td>{int(source.get('label_count') or 0):,}</td>
                <td>{_dict_summary(source.get('bucket_counts'))}</td>
                <td>{html.escape(source.get('note') or '')}</td>
            </tr>
            """
        )
    if not rows:
        return "<p>No label sources are available.</p>"
    return f"""
        <table class="predictor-table">
            <thead><tr><th>Source</th><th>Version/source ID</th><th>Model</th><th>Labels</th><th>Buckets</th><th>Handling</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_stylometric_classifier_table(model_data):
    rows = []
    for result in model_data.get("classifiers") or []:
        metrics = result.get("metrics") or {}
        status = "ready" if result.get("available") else result.get("message", "unavailable")
        rows.append(
            f"""
            <tr>
                <td>{html.escape(result.get('source_label') or '')}</td>
                <td>{html.escape(result.get('task_label') or '')}</td>
                <td>{html.escape(result.get('feature_set_label') or '')}</td>
                <td class="num">{int(result.get('sample_count') or 0):,}</td>
                <td>{_dict_summary(result.get('label_counts'))}</td>
                <td class="num">{int(result.get('feature_count') or 0):,}</td>
                <td class="num">{_model_metric(metrics, 'accuracy')}</td>
                <td class="num">{_model_metric(metrics, 'baseline_accuracy')}</td>
                <td class="num">{_model_metric(metrics, 'accuracy_delta_vs_baseline')}</td>
                <td class="num">{_model_metric(metrics, 'macro_f1')}</td>
                <td>{html.escape(status)}</td>
            </tr>
            """
        )
    return f"""
        <table class="predictor-table stylometry-comparison-table">
            <thead>
                <tr>
                    <th>Label source</th><th>Task</th><th>Features</th><th>n</th><th>Label counts</th><th>Features</th>
                    <th>Accuracy</th><th>Chance baseline</th><th>Delta</th><th>Macro F1</th><th>Status</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_compact_feature_list(features):
    if not features:
        return "n/a"
    items = []
    for feature in features[:8]:
        items.append(
            f"{html.escape(str(feature.get('class_label') or feature.get('direction') or ''))}: "
            f"<code>{html.escape(_stylometry_feature_label(feature.get('feature')))}</code> "
            f"({_fmt_stylometry_number(feature.get('coefficient'), 3)})"
        )
    return "<br>".join(items)


def _render_stylometric_classifier_feature_table(model_data):
    rows = []
    for result in model_data.get("classifiers") or []:
        if not result.get("available"):
            continue
        rows.append(
            f"""
            <tr>
                <td>{html.escape(result.get('source_label') or '')}</td>
                <td>{html.escape(result.get('task_label') or '')}</td>
                <td>{html.escape(result.get('feature_set_label') or '')}</td>
                <td>{_render_compact_feature_list(result.get('top_features'))}</td>
            </tr>
            """
        )
    if not rows:
        return "<p>No classifier feature coefficients are available.</p>"
    return f"""
        <table class="predictor-table">
            <thead><tr><th>Label source</th><th>Task</th><th>Feature family</th><th>Top coefficients</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_stylometric_regression_table(model_data):
    rows = []
    for result in model_data.get("regressions") or []:
        metrics = result.get("metrics") or {}
        status = "ready" if result.get("available") else result.get("message", "unavailable")
        rows.append(
            f"""
            <tr>
                <td>{html.escape(result.get('variant_label') or '')}</td>
                <td>{html.escape(result.get('feature_set_label') or '')}</td>
                <td class="num">{int(result.get('sample_count') or 0):,}</td>
                <td>{_dict_summary(result.get('book_counts'))}</td>
                <td class="num">{int(result.get('feature_count') or 0):,}</td>
                <td class="num">{_model_metric(metrics, 'selected_alpha')}</td>
                <td class="num">{_model_metric(metrics, 'r2')}</td>
                <td class="num">{_model_metric(metrics, 'mae')}</td>
                <td class="num">{_model_metric(metrics, 'baseline_mae')}</td>
                <td class="num">{_model_metric(metrics, 'mae_improvement_vs_baseline')}</td>
                <td class="num">{_model_metric(metrics, 'rmse')}</td>
                <td>{html.escape(status)}</td>
            </tr>
            """
        )
    return f"""
        <table class="predictor-table stylometry-comparison-table">
            <thead>
                <tr>
                    <th>Variant</th><th>Features</th><th>n</th><th>Book counts</th><th>Features</th>
                    <th>Alpha</th><th>R2</th><th>MAE</th><th>Chance MAE</th><th>MAE improvement</th><th>RMSE</th><th>Status</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_stylometric_regression_feature_table(model_data):
    rows = []
    for result in model_data.get("regressions") or []:
        if not result.get("available"):
            continue
        rows.append(
            f"""
            <tr>
                <td>{html.escape(result.get('variant_label') or '')}</td>
                <td>{html.escape(result.get('feature_set_label') or '')}</td>
                <td>{_render_compact_feature_list(result.get('top_features'))}</td>
            </tr>
            """
        )
    if not rows:
        return "<p>No regression feature coefficients are available.</p>"
    return f"""
        <table class="predictor-table">
            <thead><tr><th>Variant</th><th>Feature family</th><th>Largest standardized coefficients</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_stylometric_feature_family_notes(model_data):
    cards = []
    for feature_set in model_data.get("feature_sets") or []:
        cards.append(
            f"""
            <section class="hub-card stylometry-feature-card">
                <h3>{html.escape(feature_set.get('label') or '')}</h3>
                <p>{html.escape(feature_set.get('description') or '')}</p>
                <p>Maximum selected features: <strong>{int(feature_set.get('max_features') or 0):,}</strong>.</p>
            </section>
            """
        )
    return f'<div class="hub-grid">{"".join(cards)}</div>' if cards else ""


def generate_stylometric_sentence_model_pages(model_data, output_dir, title):
    """Generate sentence-level stylometric classifier and book-regression pages."""
    analysis_dir = os.path.join(output_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)
    _write_stylometric_model_csvs(model_data or {}, analysis_dir)

    data = model_data or {}
    metrics = data.get("metrics") or {}
    timestamp = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
    notes = _render_stylometry_notes(data.get("coverage_notes"))
    feature_notes = _render_stylometric_feature_family_notes(data)
    source_notes = _render_stylometric_source_notes(data)

    classifier_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Sentence Stylometric Classifiers</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>Sentence-level stylometric classifiers</p>
    </header>
    {_site_nav("../", "analysis")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Analyses</a> &rsaquo; <a href="stylometry.html">Stylometry</a> &rsaquo; Sentence Classifiers</div>
        <h2>Mythic, Historical, and Other from Stylometric Features</h2>
        <p>These models predict sentence labels using style-oriented feature families derived from the current <code>{html.escape(data.get('model') or 'gpt-5.4-mini')}</code> grammar parses. The evaluation is cross-validated on the parsed subset and compared with a majority-label chance baseline inside each fold.</p>
        <div class="metric-strip">
            <div><strong>{int(metrics.get('parsed_sentence_count') or 0):,}</strong><span>parsed sentences</span></div>
            <div><strong>{int(metrics.get('token_count') or 0):,}</strong><span>word tokens</span></div>
            <div><strong>{int(metrics.get('book_count') or 0):,}</strong><span>books represented</span></div>
        </div>
        {notes}
        <p><a href="data/stylometric_sentence_classifier_metrics.csv">Download classifier metrics CSV</a> | <a href="data/stylometric_sentence_classifier_features.csv">Download classifier features CSV</a></p>

        <h2>Label Sources</h2>
        {source_notes}

        <h2>Feature Families</h2>
        {feature_notes}

        <h2>Classifier Metrics</h2>
        {_render_stylometric_classifier_table(data)}

        <h2>Predictive Stylometric Features</h2>
        {_render_stylometric_classifier_feature_table(data)}
        <footer>Generated on {timestamp} from the PostgreSQL database</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "stylometric-sentence-classifiers.html"), "w", encoding="utf-8") as f:
        f.write(classifier_page)

    regression_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Stylometric Book Regression</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>Book-number regression from stylometric features</p>
    </header>
    {_site_nav("../", "analysis")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Analyses</a> &rsaquo; <a href="stylometry.html">Stylometry</a> &rsaquo; Book Regression</div>
        <h2>Can Stylometric Features Predict Book Number?</h2>
        <p>This page uses Ridge regression, not classification, to predict the numeric book number of each grammar-parsed sentence. Chance is the per-fold training-set mean book number.</p>
        {notes}
        <p><a href="stylometric-book-feature-trends.html">Open feature trend diagnostics</a> | <a href="data/stylometric_book_regression_metrics.csv">Download regression metrics CSV</a> | <a href="data/stylometric_book_regression_features.csv">Download regression features CSV</a></p>

        <h2>Regression Metrics</h2>
        {_render_stylometric_regression_table(data)}

        <h2>Predictive Stylometric Features</h2>
        {_render_stylometric_regression_feature_table(data)}
        <footer>Generated on {timestamp} from the PostgreSQL database</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "stylometric-book-regression.html"), "w", encoding="utf-8") as f:
        f.write(regression_page)

    print(
        f"Stylometric sentence model pages generated: "
        f"{int(metrics.get('parsed_sentence_count') or 0):,} parsed sentences."
    )


def _flatten_book_feature_proportions(trend_data):
    rows = []
    for feature in trend_data.get("feature_trends") or []:
        for point in feature.get("points") or []:
            rows.append(
                {
                    "feature": feature.get("feature"),
                    "feature_label": feature.get("feature_label"),
                    "coefficient": feature.get("coefficient"),
                    "direction": feature.get("direction"),
                    "book": point.get("book"),
                    "sentence_count": point.get("sentence_count"),
                    "hit_count": point.get("hit_count"),
                    "proportion": point.get("proportion"),
                    "is_book4": point.get("is_book4"),
                    "is_book8": point.get("is_book8"),
                }
            )
    return rows


def _flatten_book_feature_regressions(trend_data):
    rows = []
    for feature in trend_data.get("feature_trends") or []:
        for variant_id, regression in (feature.get("regressions") or {}).items():
            rows.append(
                {
                    "feature": feature.get("feature"),
                    "feature_label": feature.get("feature_label"),
                    "coefficient": feature.get("coefficient"),
                    "direction": feature.get("direction"),
                    "variant_id": variant_id,
                    "available": regression.get("available"),
                    "n_books": regression.get("n"),
                    "slope": regression.get("slope"),
                    "intercept": regression.get("intercept"),
                    "r_squared": regression.get("r_squared"),
                    "p_value": regression.get("p_value"),
                    "stderr": regression.get("stderr"),
                }
            )
    return rows


def _flatten_sentence_length_books(trend_data):
    rows = []
    for book in (trend_data.get("length_distribution") or {}).get("books") or []:
        rows.append(
            {
                "book": book.get("book"),
                "count": book.get("count"),
                "mean": book.get("mean"),
                "median": book.get("median"),
                "q1": book.get("q1"),
                "q3": book.get("q3"),
                "std": book.get("std"),
                "min": book.get("min"),
                "max": book.get("max"),
                "is_book4": book.get("is_book4"),
                "is_book8": book.get("is_book8"),
            }
        )
    return rows


def _flatten_sentence_length_tests(trend_data):
    length_data = trend_data.get("length_distribution") or {}
    rows = []
    for test in length_data.get("tests") or []:
        rows.append(
            {
                "type": "global_test",
                "name": test.get("test"),
                "variant_id": "",
                "statistic": test.get("statistic"),
                "p_value": test.get("p_value"),
                "r_squared": "",
                "slope": "",
                "intercept": "",
                "n": "",
                "interpretation": test.get("interpretation"),
            }
        )
    for variant_id, regression in (length_data.get("regressions") or {}).items():
        rows.append(
            {
                "type": "length_regression",
                "name": "Sentence length vs. book",
                "variant_id": variant_id,
                "statistic": "",
                "p_value": regression.get("p_value"),
                "r_squared": regression.get("r_squared"),
                "slope": regression.get("slope"),
                "intercept": regression.get("intercept"),
                "n": regression.get("n"),
                "interpretation": "OLS over individual parsed sentences.",
            }
        )
    return rows


def _write_book_feature_trend_csvs(trend_data, analysis_dir):
    data_dir = os.path.join(analysis_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    outputs = {
        "stylometric_book_feature_proportions.csv": _flatten_book_feature_proportions(trend_data),
        "stylometric_book_feature_regressions.csv": _flatten_book_feature_regressions(trend_data),
        "stylometric_sentence_length_by_book.csv": _flatten_sentence_length_books(trend_data),
        "stylometric_sentence_length_tests.csv": _flatten_sentence_length_tests(trend_data),
    }
    for filename, rows in outputs.items():
        pd.DataFrame(rows).to_csv(os.path.join(data_dir, filename), index=False)


def _trend_book_color(book):
    if int(book) == 4:
        return "#9a762d"
    if int(book) == 8:
        return "#397d7a"
    return "#5f6673"


def _svg_scale(value, domain_min, domain_max, range_min, range_max):
    if domain_max == domain_min:
        return (range_min + range_max) / 2.0
    return range_min + ((float(value) - domain_min) / (domain_max - domain_min)) * (range_max - range_min)


def _trend_line_points(regression, x_values, y_domain, width, height, margin):
    if not regression or not regression.get("available") or len(x_values) < 2:
        return ""
    x_start = min(x_values)
    x_end = max(x_values)
    y_start = regression["intercept"] + regression["slope"] * x_start
    y_end = regression["intercept"] + regression["slope"] * x_end
    return (
        f'{_svg_scale(x_start, 1, 10, margin, width - margin):.1f},'
        f'{_svg_scale(y_start, y_domain[0], y_domain[1], height - margin, margin):.1f} '
        f'{_svg_scale(x_end, 1, 10, margin, width - margin):.1f},'
        f'{_svg_scale(y_end, y_domain[0], y_domain[1], height - margin, margin):.1f}'
    )


def _render_feature_trend_svg(feature):
    points = feature.get("points") or []
    width = 560
    height = 260
    margin = 38
    y_values = [point.get("proportion") or 0.0 for point in points]
    regressions = feature.get("regressions") or {}
    for regression in regressions.values():
        if regression.get("available"):
            for x in [1, 10]:
                y_values.append(regression["intercept"] + regression["slope"] * x)
    y_max = max(0.05, min(1.0, max(y_values or [0.0]) * 1.18))
    y_domain = (0.0, y_max)
    axis_lines = f"""
        <line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#c9c0b3" />
        <line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#c9c0b3" />
    """
    x_ticks = []
    for book in range(1, 11):
        x = _svg_scale(book, 1, 10, margin, width - margin)
        x_ticks.append(
            f'<text x="{x:.1f}" y="{height - 14}" text-anchor="middle" font-size="11" fill="#5c5142">{book}</text>'
        )
    y_ticks = []
    for tick in [0.0, y_max / 2.0, y_max]:
        y = _svg_scale(tick, y_domain[0], y_domain[1], height - margin, margin)
        y_ticks.append(
            f'<text x="{margin - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="#5c5142">{tick * 100:.0f}%</text>'
        )
    all_line = _trend_line_points(
        regressions.get("all_books"),
        [point["book"] for point in points],
        y_domain,
        width,
        height,
        margin,
    )
    excluding_line = _trend_line_points(
        regressions.get("excluding_4_8"),
        [point["book"] for point in points if point["book"] not in {4, 8}],
        y_domain,
        width,
        height,
        margin,
    )
    line_svg = ""
    if all_line:
        line_svg += f'<polyline points="{all_line}" fill="none" stroke="#b94a38" stroke-width="2.4" />'
    if excluding_line:
        line_svg += f'<polyline points="{excluding_line}" fill="none" stroke="#315c59" stroke-width="2.4" stroke-dasharray="6 4" />'

    point_svg = []
    for point in points:
        x = _svg_scale(point["book"], 1, 10, margin, width - margin)
        y = _svg_scale(point["proportion"], y_domain[0], y_domain[1], height - margin, margin)
        point_svg.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{_trend_book_color(point["book"])}">'
            f'<title>Book {point["book"]}: {point["hit_count"]}/{point["sentence_count"]} ({point["proportion"] * 100:.1f}%)</title>'
            '</circle>'
        )
    return f"""
        <svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(feature.get('feature_label') or '')} by book">
            {axis_lines}
            {''.join(x_ticks)}
            {''.join(y_ticks)}
            {line_svg}
            {''.join(point_svg)}
            <text x="{width / 2:.1f}" y="{height - 2}" text-anchor="middle" font-size="12" fill="#5c5142">Book</text>
            <text x="14" y="{height / 2:.1f}" text-anchor="middle" transform="rotate(-90 14 {height / 2:.1f})" font-size="12" fill="#5c5142">Sentence proportion</text>
        </svg>
    """


def _render_feature_regression_table(feature):
    rows = []
    for variant_id, label in (("all_books", "All books"), ("excluding_4_8", "Excluding Books 4 and 8")):
        regression = (feature.get("regressions") or {}).get(variant_id) or {}
        rows.append(
            f"""
            <tr>
                <td>{label}</td>
                <td class="num">{_fmt_stylometry_number(regression.get('slope'), 4)}</td>
                <td class="num">{_fmt_stylometry_number(regression.get('r_squared'), 3)}</td>
                <td class="num">{_people_p_value(regression.get('p_value'))}</td>
                <td class="num">{int(regression.get('n') or 0)}</td>
            </tr>
            """
        )
    return f"""
        <table class="predictor-table compact-table">
            <thead><tr><th>Fit</th><th class="num">Slope per book</th><th class="num">R2</th><th class="num">p</th><th class="num">n books</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_feature_trend_cards(trend_data):
    cards = []
    for feature in trend_data.get("feature_trends") or []:
        cards.append(
            f"""
            <section class="stylometry-delta-card">
                <h3>{html.escape(feature.get('feature_label') or '')}</h3>
                <p>Ridge coefficient: <strong>{_fmt_stylometry_number(feature.get('coefficient'), 3)}</strong>; direction in the model: <strong>{html.escape(str(feature.get('direction') or ''))}</strong>.</p>
                {_render_feature_trend_svg(feature)}
                <p class="stylometry-legend"><span class="legend-dot other"></span>Other books <span class="legend-dot book4"></span>Book 4 <span class="legend-dot book8"></span>Book 8 <span style="color:#b94a38;font-weight:bold;">solid</span> all-books regression <span style="color:#315c59;font-weight:bold;">dashed</span> excluding Books 4 and 8</p>
                {_render_feature_regression_table(feature)}
            </section>
            """
        )
    return "".join(cards) or "<p>No morphosyntax feature trends are available.</p>"


def _book_palette(book):
    palette = {
        1: "#4e79a7",
        2: "#59a14f",
        3: "#e15759",
        4: "#9a762d",
        5: "#76b7b2",
        6: "#f28e2b",
        7: "#af7aa1",
        8: "#397d7a",
        9: "#edc948",
        10: "#8cd17d",
    }
    return palette.get(int(book), "#5f6673")


def _render_kde_svg(length_data):
    books = length_data.get("books") or []
    if not books:
        return "<p>No sentence-length density data is available.</p>"
    width = 820
    height = 360
    margin = 44
    x_values = [point["x"] for book in books for point in book.get("kde", [])]
    y_values = [point["density"] for book in books for point in book.get("kde", [])]
    x_min = min(x_values or [0.0])
    x_max = max(x_values or [1.0])
    y_max = max(y_values or [0.001]) * 1.12
    paths = []
    for book in books:
        coords = []
        for point in book.get("kde", []):
            x = _svg_scale(point["x"], x_min, x_max, margin, width - margin)
            y = _svg_scale(point["density"], 0, y_max, height - margin, margin)
            coords.append(f"{x:.1f},{y:.1f}")
        if coords:
            paths.append(
                f'<polyline points="{" ".join(coords)}" fill="none" stroke="{_book_palette(book["book"])}" stroke-width="2"><title>Book {book["book"]}</title></polyline>'
            )
    x_ticks = []
    for tick in np.linspace(x_min, x_max, 6):
        x = _svg_scale(tick, x_min, x_max, margin, width - margin)
        x_ticks.append(f'<text x="{x:.1f}" y="{height - 14}" text-anchor="middle" font-size="11" fill="#5c5142">{tick:.0f}</text>')
    legend = []
    for book in books:
        legend.append(
            f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:10px;"><span class="legend-dot" style="background:{_book_palette(book["book"])}"></span>Book {book["book"]}</span>'
        )
    return f"""
        <svg viewBox="0 0 {width} {height}" role="img" aria-label="Sentence length KDE by book">
            <line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#c9c0b3" />
            <line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#c9c0b3" />
            {''.join(paths)}
            {''.join(x_ticks)}
            <text x="{width / 2:.1f}" y="{height - 2}" text-anchor="middle" font-size="12" fill="#5c5142">Sentence length, non-punctuation tokens</text>
            <text x="15" y="{height / 2:.1f}" text-anchor="middle" transform="rotate(-90 15 {height / 2:.1f})" font-size="12" fill="#5c5142">Density</text>
        </svg>
        <p class="stylometry-legend">{''.join(legend)}</p>
    """


def _render_violin_svg(length_data):
    books = length_data.get("books") or []
    if not books:
        return "<p>No sentence-length violin data is available.</p>"
    width = 820
    height = 420
    margin = 46
    all_lengths = [length for book in books for length in book.get("lengths", [])]
    y_min = max(0, min(all_lengths or [0]) - 2)
    y_max = max(all_lengths or [1]) + 2
    step = (width - 2 * margin) / max(1, len(books) - 1)
    violins = []
    for index, book in enumerate(books):
        center = margin + index * step
        densities = [point["density"] for point in book.get("kde", [])]
        max_density = max(densities or [0.0]) or 1.0
        right = []
        left = []
        for point in book.get("kde", []):
            y = _svg_scale(point["x"], y_min, y_max, height - margin, margin)
            half_width = 30.0 * (point["density"] / max_density)
            right.append(f"{center + half_width:.1f},{y:.1f}")
            left.append(f"{center - half_width:.1f},{y:.1f}")
        polygon = " ".join(right + list(reversed(left)))
        q1_y = _svg_scale(book["q1"], y_min, y_max, height - margin, margin)
        q3_y = _svg_scale(book["q3"], y_min, y_max, height - margin, margin)
        median_y = _svg_scale(book["median"], y_min, y_max, height - margin, margin)
        violins.append(
            f"""
            <polygon points="{polygon}" fill="{_book_palette(book['book'])}" fill-opacity="0.34" stroke="{_book_palette(book['book'])}" stroke-width="1.3" />
            <line x1="{center:.1f}" x2="{center:.1f}" y1="{q1_y:.1f}" y2="{q3_y:.1f}" stroke="#333" stroke-width="3" />
            <line x1="{center - 18:.1f}" x2="{center + 18:.1f}" y1="{median_y:.1f}" y2="{median_y:.1f}" stroke="#333" stroke-width="2" />
            <text x="{center:.1f}" y="{height - 16}" text-anchor="middle" font-size="12" fill="#5c5142">{book['book']}</text>
            """
        )
    y_ticks = []
    for tick in np.linspace(y_min, y_max, 6):
        y = _svg_scale(tick, y_min, y_max, height - margin, margin)
        y_ticks.append(f'<text x="{margin - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="#5c5142">{tick:.0f}</text>')
    return f"""
        <svg viewBox="0 0 {width} {height}" role="img" aria-label="Sentence length violin plots by book">
            <line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#c9c0b3" />
            <line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#c9c0b3" />
            {''.join(y_ticks)}
            {''.join(violins)}
            <text x="{width / 2:.1f}" y="{height - 2}" text-anchor="middle" font-size="12" fill="#5c5142">Book</text>
            <text x="15" y="{height / 2:.1f}" text-anchor="middle" transform="rotate(-90 15 {height / 2:.1f})" font-size="12" fill="#5c5142">Sentence length</text>
        </svg>
    """


def _render_length_stats_table(length_data):
    rows = []
    for book in length_data.get("books") or []:
        rows.append(
            f"""
            <tr>
                <td>Book {book.get('book')}</td>
                <td class="num">{int(book.get('count') or 0):,}</td>
                <td class="num">{_fmt_stylometry_number(book.get('mean'), 2)}</td>
                <td class="num">{_fmt_stylometry_number(book.get('median'), 2)}</td>
                <td class="num">{_fmt_stylometry_number(book.get('q1'), 2)}</td>
                <td class="num">{_fmt_stylometry_number(book.get('q3'), 2)}</td>
                <td class="num">{_fmt_stylometry_number(book.get('std'), 2)}</td>
            </tr>
            """
        )
    return f"""
        <table class="predictor-table">
            <thead><tr><th>Book</th><th class="num">n</th><th class="num">Mean</th><th class="num">Median</th><th class="num">Q1</th><th class="num">Q3</th><th class="num">SD</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_length_tests_table(length_data):
    rows = []
    for test in length_data.get("tests") or []:
        rows.append(
            f"""
            <tr>
                <td>{html.escape(test.get('test') or '')}</td>
                <td class="num">{_fmt_stylometry_number(test.get('statistic'), 3)}</td>
                <td class="num">{_people_p_value(test.get('p_value'))}</td>
                <td>{html.escape(test.get('interpretation') or '')}</td>
            </tr>
            """
        )
    for variant_id, label in (("all_books", "Length ~ book, all books"), ("excluding_4_8", "Length ~ book, excluding Books 4 and 8")):
        regression = (length_data.get("regressions") or {}).get(variant_id) or {}
        rows.append(
            f"""
            <tr>
                <td>{label}</td>
                <td class="num">{_fmt_stylometry_number(regression.get('slope'), 3)}</td>
                <td class="num">{_people_p_value(regression.get('p_value'))}</td>
                <td>OLS slope in tokens per book; R2 {_fmt_stylometry_number(regression.get('r_squared'), 3)}, n {int(regression.get('n') or 0):,} sentences.</td>
            </tr>
            """
        )
    return f"""
        <table class="predictor-table">
            <thead><tr><th>Test</th><th class="num">Statistic / slope</th><th class="num">p</th><th>Interpretation</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def generate_stylometric_book_feature_trend_page(trend_data, output_dir, title):
    """Generate book-by-book morphosyntax feature trend diagnostics."""
    analysis_dir = os.path.join(output_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)
    _write_book_feature_trend_csvs(trend_data or {}, analysis_dir)

    data = trend_data or {}
    metrics = data.get("metrics") or {}
    length_data = data.get("length_distribution") or {}
    timestamp = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
    notes = _render_stylometry_notes(data.get("notes"))
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Book Feature Trends</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>Book-level morphosyntax trends and sentence-length diagnostics</p>
    </header>
    {_site_nav("../", "analysis")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Analyses</a> &rsaquo; <a href="stylometric-book-regression.html">Book Regression</a> &rsaquo; Feature Trends</div>
        <h2>Morphosyntax Feature Trends by Book</h2>
        <p>This page expands the top <code>excluding Books 4 and 8</code> morphosyntax regression coefficients into direct book-by-book prevalence checks. Each point is a book-level proportion of grammar-parsed sentences containing the feature at least once.</p>
        <div class="metric-strip">
            <div><strong>{int(metrics.get('parsed_sentence_count') or 0):,}</strong><span>parsed sentences</span></div>
            <div><strong>{int(metrics.get('book_count') or 0):,}</strong><span>books represented</span></div>
            <div><strong>{int(metrics.get('feature_count') or 0):,}</strong><span>features plotted</span></div>
        </div>
        {notes}
        <p><a href="data/stylometric_book_feature_proportions.csv">Download feature proportions CSV</a> | <a href="data/stylometric_book_feature_regressions.csv">Download feature regressions CSV</a> | <a href="data/stylometric_sentence_length_by_book.csv">Download length summary CSV</a> | <a href="data/stylometric_sentence_length_tests.csv">Download length tests CSV</a></p>

        <h2>Feature Proportions</h2>
        {_render_feature_trend_cards(data)}

        <h2>Sentence Length Distributions</h2>
        <h3>KDE Overlay</h3>
        {_render_kde_svg(length_data)}
        <h3>Violin Plots</h3>
        {_render_violin_svg(length_data)}
        <h3>Book Summaries</h3>
        {_render_length_stats_table(length_data)}
        <h3>Length Tests</h3>
        {_render_length_tests_table(length_data)}
        <footer>Generated on {timestamp} from the PostgreSQL database</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "stylometric-book-feature-trends.html"), "w", encoding="utf-8") as f:
        f.write(page)

    print(
        f"Stylometric book feature trend page generated: "
        f"{int(metrics.get('feature_count') or 0):,} features."
    )


DISCOURSE_MODE_COLORS = {
    "route_locative_description": "#4e79a7",
    "monument_catalogue": "#9a762d",
    "historical_narrative": "#e15759",
    "mythological_narrative": "#7f63b8",
    "ritual_ethnographic_description": "#59a14f",
    "sources_traditions_discussion": "#b66d3f",
}


def _flatten_discourse_unit_rows(analysis):
    rows = []
    for row in analysis.get("unit_rows") or []:
        rows.append(
            {
                "passage_id": row.get("passage_id"),
                "sentence_number": row.get("sentence_number"),
                "book": row.get("book"),
                "chapter": row.get("chapter"),
                "section": row.get("section"),
                "discourse_mode": row.get("discourse_mode"),
                "discourse_mode_label": row.get("discourse_mode_label"),
                "confidence": row.get("confidence"),
                "has_aorist": row.get("has_aorist"),
                "token_count": row.get("token_count"),
                "excerpt": row.get("excerpt"),
            }
        )
    return rows


def _flatten_discourse_mode_aorist_rows(analysis):
    rows = []
    for trend in analysis.get("mode_trends") or []:
        for point in trend.get("points") or []:
            rows.append(
                {
                    "discourse_mode": trend.get("discourse_mode"),
                    "discourse_mode_label": trend.get("discourse_mode_label"),
                    "book": point.get("book"),
                    "sentence_count": point.get("sentence_count"),
                    "aorist_count": point.get("aorist_count"),
                    "aorist_rate": point.get("aorist_rate"),
                    "is_book4": point.get("is_book4"),
                    "is_book8": point.get("is_book8"),
                }
            )
    return rows


def _flatten_discourse_regression_rows(analysis):
    rows = []
    for regression_id, regression in (analysis.get("adjusted_regressions") or {}).items():
        rows.append(
            {
                "scope": regression_id,
                "discourse_mode": "",
                "discourse_mode_label": "",
                "fit": "mode_adjusted" if "mode_adjusted" in regression_id else "book_only",
                "available": regression.get("available"),
                "n": regression.get("n"),
                "book_count": regression.get("book_count"),
                "mode_count": regression.get("mode_count"),
                "slope": regression.get("slope"),
                "intercept": regression.get("intercept"),
                "r_squared": regression.get("r_squared"),
                "p_value": regression.get("p_value"),
                "stderr": regression.get("stderr"),
            }
        )
    for trend in analysis.get("mode_trends") or []:
        for fit_id, regression in (trend.get("regressions") or {}).items():
            rows.append(
                {
                    "scope": fit_id,
                    "discourse_mode": trend.get("discourse_mode"),
                    "discourse_mode_label": trend.get("discourse_mode_label"),
                    "fit": "within_mode",
                    "available": regression.get("available"),
                    "n": regression.get("n"),
                    "book_count": regression.get("n"),
                    "mode_count": 1,
                    "slope": regression.get("slope"),
                    "intercept": regression.get("intercept"),
                    "r_squared": regression.get("r_squared"),
                    "p_value": regression.get("p_value"),
                    "stderr": regression.get("stderr"),
                }
            )
    return rows


def _write_discourse_mode_aorist_csvs(analysis, analysis_dir):
    data_dir = os.path.join(analysis_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    outputs = {
        "discourse_mode_aorist_sentences.csv": _flatten_discourse_unit_rows(analysis),
        "discourse_mode_composition_by_book.csv": analysis.get("mode_composition") or [],
        "discourse_mode_aorist_by_book.csv": _flatten_discourse_mode_aorist_rows(analysis),
        "discourse_mode_aorist_regressions.csv": _flatten_discourse_regression_rows(analysis),
        "discourse_mode_summary.csv": analysis.get("mode_summary") or [],
        "discourse_mode_book_aorist.csv": analysis.get("book_aorist") or [],
    }
    for filename, rows in outputs.items():
        pd.DataFrame(rows).to_csv(os.path.join(data_dir, filename), index=False)


def _render_discourse_mode_summary_table(analysis):
    rows = []
    for row in analysis.get("mode_summary") or []:
        rows.append(
            f"""
            <tr>
                <td>{html.escape(row.get('discourse_mode_label') or '')}</td>
                <td class="num">{int(row.get('sentence_count') or 0):,}</td>
                <td class="num">{int(row.get('book_count') or 0):,}</td>
                <td class="num">{int(row.get('aorist_count') or 0):,}</td>
                <td class="num">{_fmt_stylometry_number((row.get('aorist_rate') or 0.0) * 100, 1)}%</td>
            </tr>
            """
        )
    return f"""
        <table class="predictor-table compact-table">
            <thead><tr><th>Discourse mode</th><th class="num">Sentences</th><th class="num">Books</th><th class="num">Aorist sentences</th><th class="num">Aorist rate</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_discourse_adjusted_regression_table(analysis):
    labels = {
        "book_only_all_books": "Book only, all books",
        "mode_adjusted_all_books": "Mode-adjusted, all books",
        "book_only_excluding_4_8": "Book only, excluding Books 4 and 8",
        "mode_adjusted_excluding_4_8": "Mode-adjusted, excluding Books 4 and 8",
    }
    rows = []
    for key, label in labels.items():
        regression = (analysis.get("adjusted_regressions") or {}).get(key) or {}
        rows.append(
            f"""
            <tr>
                <td>{html.escape(label)}</td>
                <td class="num">{int(regression.get('n') or 0):,}</td>
                <td class="num">{int(regression.get('book_count') or 0):,}</td>
                <td class="num">{int(regression.get('mode_count') or 0):,}</td>
                <td class="num">{_fmt_stylometry_number(regression.get('slope'), 4)}</td>
                <td class="num">{_fmt_stylometry_number(regression.get('r_squared'), 3)}</td>
                <td class="num">{_people_p_value(regression.get('p_value'))}</td>
            </tr>
            """
        )
    return f"""
        <table class="predictor-table compact-table">
            <thead><tr><th>Fit</th><th class="num">n</th><th class="num">Books</th><th class="num">Modes</th><th class="num">Aorist slope / book</th><th class="num">R2</th><th class="num">p</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_discourse_mode_composition_svg(analysis):
    composition = analysis.get("mode_composition") or []
    modes = analysis.get("discourse_modes") or []
    books = sorted({int(row["book"]) for row in composition if row.get("book") is not None})
    if not composition or not books:
        return "<p>No discourse-mode composition data is available.</p>"
    width = 860
    height = 360
    margin_left = 44
    chart_width = width - margin_left - 24
    chart_height = 250
    bar_gap = 8
    bar_width = max(18, (chart_width - bar_gap * (len(books) - 1)) / max(1, len(books)))
    parts = []
    for book_index, book in enumerate(books):
        x = margin_left + book_index * (bar_width + bar_gap)
        y_cursor = 28 + chart_height
        for mode in modes:
            mode_id = mode.get("id")
            row = next(
                (
                    item for item in composition
                    if int(item.get("book") or 0) == book
                    and item.get("discourse_mode") == mode_id
                ),
                None,
            )
            proportion = float((row or {}).get("proportion") or 0.0)
            segment_height = chart_height * proportion
            y_cursor -= segment_height
            if segment_height <= 0:
                continue
            label = mode.get("label") or mode_id
            count = int((row or {}).get("sentence_count") or 0)
            color = DISCOURSE_MODE_COLORS.get(mode_id, "#777")
            parts.append(
                f"""
                <rect x="{x:.1f}" y="{y_cursor:.1f}" width="{bar_width:.1f}" height="{segment_height:.1f}" fill="{color}">
                    <title>Book {book}: {html.escape(label)} {proportion * 100:.1f}% ({count:,})</title>
                </rect>
                """
            )
        parts.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{height - 16}" text-anchor="middle" font-size="12" fill="#5c5142">{book}</text>'
        )
    legend = []
    legend_x = margin_left
    legend_y = 332
    for mode_index, mode in enumerate(modes):
        x = legend_x + (mode_index % 3) * 260
        y = legend_y + (mode_index // 3) * 18
        mode_id = mode.get("id")
        label = mode.get("label") or mode_id
        legend.append(
            f'<rect x="{x}" y="{y}" width="11" height="11" fill="{DISCOURSE_MODE_COLORS.get(mode_id, "#777")}"></rect>'
            f'<text x="{x + 16}" y="{y + 10}" font-size="12" fill="#4b4338">{html.escape(label)}</text>'
        )
    return f"""
        <svg viewBox="0 0 {width} {height}" role="img" aria-label="Discourse-mode composition by book">
            <line x1="{margin_left}" y1="{28 + chart_height}" x2="{width - 20}" y2="{28 + chart_height}" stroke="#c9c0b3"></line>
            {''.join(parts)}
            <text x="{width / 2:.1f}" y="{height - 2}" text-anchor="middle" font-size="12" fill="#5c5142">Book</text>
            <text x="14" y="{28 + chart_height / 2:.1f}" text-anchor="middle" transform="rotate(-90 14 {28 + chart_height / 2:.1f})" font-size="12" fill="#5c5142">Mode share</text>
            {''.join(legend)}
        </svg>
    """


def _render_discourse_aorist_svg(trend):
    points = trend.get("points") or []
    if not points:
        return "<p>No book-level aorist points are available for this mode.</p>"
    feature = {
        "feature_label": trend.get("discourse_mode_label"),
        "points": [
            {
                "book": point.get("book"),
                "sentence_count": point.get("sentence_count"),
                "hit_count": point.get("aorist_count"),
                "proportion": point.get("aorist_rate"),
            }
            for point in points
        ],
        "regressions": trend.get("regressions") or {},
    }
    return _render_feature_trend_svg(feature)


def _render_discourse_within_mode_cards(analysis):
    cards = []
    for trend in analysis.get("mode_trends") or []:
        all_fit = (trend.get("regressions") or {}).get("all_books") or {}
        excluding_fit = (trend.get("regressions") or {}).get("excluding_4_8") or {}
        cards.append(
            f"""
            <section class="stylometry-delta-card">
                <h3>{html.escape(trend.get('discourse_mode_label') or '')}</h3>
                <p><strong>{int(trend.get('sentence_count') or 0):,}</strong> tagged parsed sentences; <strong>{int(trend.get('aorist_count') or 0):,}</strong> contain at least one aorist-tagged token.</p>
                {_render_discourse_aorist_svg(trend)}
                <table class="predictor-table compact-table">
                    <thead><tr><th>Fit</th><th class="num">Slope / book</th><th class="num">R2</th><th class="num">p</th><th class="num">n books</th></tr></thead>
                    <tbody>
                        <tr><td>All books</td><td class="num">{_fmt_stylometry_number(all_fit.get('slope'), 4)}</td><td class="num">{_fmt_stylometry_number(all_fit.get('r_squared'), 3)}</td><td class="num">{_people_p_value(all_fit.get('p_value'))}</td><td class="num">{int(all_fit.get('n') or 0)}</td></tr>
                        <tr><td>Excluding Books 4 and 8</td><td class="num">{_fmt_stylometry_number(excluding_fit.get('slope'), 4)}</td><td class="num">{_fmt_stylometry_number(excluding_fit.get('r_squared'), 3)}</td><td class="num">{_people_p_value(excluding_fit.get('p_value'))}</td><td class="num">{int(excluding_fit.get('n') or 0)}</td></tr>
                    </tbody>
                </table>
            </section>
            """
        )
    return "".join(cards)


def generate_discourse_mode_aorist_page(analysis, output_dir, title):
    """Generate the discourse-mode control page for the aorist book trend."""
    analysis_dir = os.path.join(output_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)
    _write_discourse_mode_aorist_csvs(analysis or {}, analysis_dir)

    data = analysis or {}
    metrics = data.get("metrics") or {}
    timestamp = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
    notes = _render_stylometry_notes(data.get("notes"))
    if data.get("available"):
        body = f"""
        <p>This pilot controls the aorist trend by classifying parsed sentences into discourse modes, then asking whether <code>Feature Tense=Aor</code> still declines over book number within comparable modes.</p>
        <div class="metric-strip">
            <div><strong>{int(metrics.get('tagged_sentence_count') or 0):,}</strong><span>tagged parsed sentences</span></div>
            <div><strong>{int(metrics.get('parsed_sentence_count') or 0):,}</strong><span>parsed sentences available</span></div>
            <div><strong>{int(metrics.get('book_count') or 0):,}</strong><span>books represented</span></div>
            <div><strong>{int(metrics.get('mode_count') or 0):,}</strong><span>modes represented</span></div>
            <div><strong>{_fmt_stylometry_number((metrics.get('aorist_rate') or 0.0) * 100, 1)}%</strong><span>sentences with aorist</span></div>
        </div>
        {notes}
        <p><a href="data/discourse_mode_aorist_regressions.csv">Download regression CSV</a> | <a href="data/discourse_mode_aorist_by_book.csv">Download by-mode aorist CSV</a> | <a href="data/discourse_mode_composition_by_book.csv">Download mode composition CSV</a> | <a href="data/discourse_mode_aorist_sentences.csv">Download sentence rows CSV</a></p>

        <h2>Mode-Adjusted Aorist Slope</h2>
        <p>The slope is the change in probability that a tagged parsed sentence contains at least one <code>Tense=Aor</code> token per book number.</p>
        {_render_discourse_adjusted_regression_table(data)}

        <h2>Discourse Mix by Book</h2>
        {_render_discourse_mode_composition_svg(data)}

        <h2>Aorist Rate by Mode</h2>
        {_render_discourse_mode_summary_table(data)}

        <h2>Within-Mode Aorist Trends</h2>
        {_render_discourse_within_mode_cards(data)}
        """
    else:
        body = f"""
        <p class="note">No discourse-mode tags are available yet for prompt <code>{html.escape(str(data.get('prompt_version') or ''))}</code>.</p>
        <p>The daily sentence-tagging pipeline will populate this page from grammar-parsed sentences under the 100k-token pilot budget.</p>
        """

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Discourse Mode Aorist Control</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>Aorist trend by discourse mode</p>
    </header>
    {_site_nav("../", "analysis")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Analyses</a> &rsaquo; <a href="stylometric-book-feature-trends.html">Feature Trends</a> &rsaquo; Discourse Mode Control</div>
        <h2>Is the Aorist Trend Stylistic or Content-Driven?</h2>
        {body}
        <footer>Generated on {timestamp} from the PostgreSQL database</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "discourse-mode-aorist.html"), "w", encoding="utf-8") as f:
        f.write(page)

    print(
        f"Discourse-mode aorist page generated: "
        f"{int(metrics.get('tagged_sentence_count') or 0):,} tagged parsed sentences."
    )


def generate_analysis_pages(greta_analysis, section_people_analysis, discourse_aorist_analysis, output_dir, title):
    """Generate the analysis hub and current Greta logistic-regression variants."""
    analysis_dir = os.path.join(output_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)

    variants = greta_analysis.get("variants", []) if greta_analysis else []
    complementary = greta_analysis.get("complementary", {}) if greta_analysis else {}
    label_sensitivity = greta_analysis.get("label_sensitivity", {}) if greta_analysis else {}
    _write_section_people_page(section_people_analysis, analysis_dir, title)
    _write_complementary_analysis_pages(complementary, analysis_dir, title)
    _write_label_sensitivity_page(label_sensitivity, analysis_dir, title)
    for variant in variants:
        predictors = variant.get("predictors")
        metrics = variant.get("metrics")
        if predictors is None or len(predictors) == 0:
            body = f"<p>{html.escape(variant.get('message') or 'No predictor table is available for this variant.')}</p>"
        else:
            mythic_words = predictors[predictors["is_mythic"] == 1].sort_values("coefficient", ascending=False)
            historical_words = predictors[predictors["is_mythic"] == 0].sort_values("coefficient", ascending=True)
            body = f"""
                {format_classification_metrics(metrics, "Historical", "Mythic")}
                {render_confusion_matrix_card("Confusion Matrix", metrics, "Historical", "Mythic")}
                <h2>Counts</h2>
                <div class="metric-strip">
                    <div><strong>{variant["sample_count"]:,}</strong><span>mythic/historical sentences</span></div>
                    <div><strong>{variant["bucket_counts"].get("mythic", 0):,}</strong><span>mythic</span></div>
                    <div><strong>{variant["bucket_counts"].get("historical", 0):,}</strong><span>historical</span></div>
                    <div><strong>{variant["feature_count"]:,}</strong><span>features</span></div>
                </div>

                <h2>Predictors of Mythic Sentences</h2>
                {render_predictor_table(
                    f"{variant['id']}-mythic",
                    mythic_words,
                    "mythic-word",
                    "Mythic Count",
                    "Historical Count",
                    "mythic_count",
                    "historical_count",
                    coefficient_direction="desc",
                )}

                <h2>Predictors of Historical Sentences</h2>
                {render_predictor_table(
                    f"{variant['id']}-historical",
                    historical_words,
                    "historical-word",
                    "Mythic Count",
                    "Historical Count",
                    "mythic_count",
                    "historical_count",
                    coefficient_direction="asc",
                )}
            """

        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {_variant_display_name(variant)}</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Tri-marked sentence-level mythic vs. historical analysis</p>
    </header>
    {_site_nav("../", "analysis")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Analyses</a> &rsaquo; {_variant_display_name(variant)}</div>
        <h2>{_variant_display_name(variant)}</h2>
        <p>This model drops sentences tagged <code>other</code> and fits a balanced TF-IDF logistic regression to the remaining mythic and historical tags.</p>
        {body}
        <footer>{_generated_footer()}</footer>
    </div>
{PREDICTOR_TABLE_SORT_SCRIPT}
</body>
</html>
"""
        with open(os.path.join(analysis_dir, _variant_href(variant)), "w", encoding="utf-8") as f:
            f.write(page)
        legacy_href = _legacy_variant_href(variant)
        if legacy_href:
            _write_redirect_page(
                analysis_dir,
                legacy_href,
                _variant_href(variant),
                title,
                _variant_display_name(variant),
            )

    if greta_analysis and greta_analysis.get("available"):
        bucket_counts = greta_analysis.get("bucket_counts", {})
        book_counts = greta_analysis.get("book_counts", {})
        book_scope_note = ""
        if not any(str(book) in book_counts for book in ("4", "8")):
            book_scope_note = (
                "<p class=\"note\">The active tag batch currently has no book 4 or book 8 sentences, "
                "so the all-books and excluding-books-4-and-8 variants use the same sample for now.</p>"
            )
        bucket_html = "".join(
            f"<li><span class=\"status-pill bucket-{html.escape(str(bucket))}\">{html.escape(str(bucket))}</span> {int(count):,}</li>"
            for bucket, count in sorted(bucket_counts.items())
        )
        variant_rows = []
        for variant in variants:
            accuracy = ""
            if variant.get("metrics"):
                accuracy = f"{variant['metrics']['accuracy']:.3f}"
            status = (
                f'<a href="{_variant_href(variant)}">Open</a>'
                if variant.get("available")
                else html.escape(variant.get("message", "Unavailable"))
            )
            variant_rows.append(f"""
                <tr>
                    <td>{html.escape("Lemma" if variant["token_source"] == "lemma" else "Surface")}</td>
                    <td>{'All books' if variant["include_books_4_8"] else 'Excluding 4 and 8'}</td>
                    <td>{'Removed' if variant["remove_rhetoric_markers"] else 'Included'}</td>
                    <td class="num">{variant["sample_count"]:,}</td>
                    <td class="num">{variant["feature_count"]:,}</td>
                    <td class="num">{accuracy}</td>
                    <td>{status}</td>
                </tr>
            """)
        greta_section = f"""
            <h2>Current Tri-Marked Sentence-Level Analyses</h2>
            <p>The current paper-facing analysis uses the active three-bucket tags, then restricts the model to mythic vs. historical sentences.</p>
            {book_scope_note}
            <ul class="compact-list">{bucket_html}</ul>
            <table class="predictor-table">
                <thead>
                    <tr><th>Vocabulary</th><th>Book Scope</th><th>Rhetoric Markers</th><th>Sample</th><th>Features</th><th>Accuracy</th><th>Page</th></tr>
                </thead>
                <tbody>{''.join(variant_rows)}</tbody>
            </table>
        """
    else:
        greta_section = f"""
            <h2>Current Tri-Marked Sentence-Level Analyses</h2>
            <p>{html.escape(greta_analysis.get("message", "No Greta analysis data is available.") if greta_analysis else "No Greta analysis data is available.")}</p>
        """

    people_summary = (section_people_analysis or {}).get("summary", {})
    if section_people_analysis and section_people_analysis.get("available"):
        people_blurb = (
            f"{int(people_summary.get('processed_sections') or 0):,} sections and "
            f"{int(people_summary.get('processed_sentences') or 0):,} numbered sentences processed; "
            f"{int(people_summary.get('mention_rows') or 0):,} mention rows extracted."
        )
    else:
        people_blurb = (
            section_people_analysis.get("message")
            if section_people_analysis
            else "People extraction data is not available yet."
        )
    people_section = f"""
        <h2>People Mentions</h2>
        <div class="hub-grid">
            <section class="hub-card">
                <h3>People and Gender Mentions</h3>
                <p>{html.escape(people_blurb)}</p>
                <a href="people-gender.html">Open People Report</a>
            </section>
        </div>
    """

    discourse_metrics = (discourse_aorist_analysis or {}).get("metrics", {})
    if discourse_aorist_analysis and discourse_aorist_analysis.get("available"):
        discourse_blurb = (
            f"{int(discourse_metrics.get('tagged_sentence_count') or 0):,} tagged parsed sentences "
            f"across {int(discourse_metrics.get('mode_count') or 0):,} discourse modes."
        )
    else:
        discourse_blurb = "Awaiting discourse-mode tags from the 100k-token parsed-sentence pilot."

    index_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Analyses</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Analysis outputs and model variants</p>
    </header>
        {_site_nav("../", "analysis")}
    <div class="container wide-container">
        {greta_section}

        {people_section}

        <h2>Morphosyntactic Stylometry</h2>
        <div class="hub-grid">
            <section class="hub-card">
                <h3>LLM Grammar Stylometry</h3>
                <p>Passage-level morphosyntactic features from the gpt-5.4-mini grammar parser, with word-frequency and character n-gram baselines.</p>
                <a href="stylometry.html">Open Stylometry</a>
            </section>
            <section class="hub-card">
                <h3>Interactive Projection</h3>
                <p>Feature-family projection display for comparing current parsed passages and mouseover neighbor context.</p>
                <a href="stylometry-umap.html">Open Projection</a>
            </section>
            <section class="hub-card">
                <h3>Sentence Classifiers</h3>
                <p>Cross-validated mythic, historical, and other sentence classifiers using grammar-derived stylometric features.</p>
                <a href="stylometric-sentence-classifiers.html">Open Classifiers</a>
            </section>
            <section class="hub-card">
                <h3>Book Regression</h3>
                <p>Ridge regressors that test whether stylometric features can predict sentence book number better than a mean-book baseline.</p>
                <a href="stylometric-book-regression.html">Open Regression</a>
            </section>
            <section class="hub-card">
                <h3>Feature Trends</h3>
                <p>Book-by-book proportions for the strongest morphosyntax regression features, plus sentence-length KDE and violin diagnostics.</p>
                <a href="stylometric-book-feature-trends.html">Open Trends</a>
            </section>
            <section class="hub-card">
                <h3>Discourse Mode Control</h3>
                <p>{html.escape(discourse_blurb)}</p>
                <a href="discourse-mode-aorist.html">Open Mode Control</a>
            </section>
        </div>

        <h2>Complementary Robustness Checks</h2>
        <div class="hub-grid">
            <section class="hub-card">
                <h3>Semantic-Field Ablation</h3>
                <p>Reruns the main lemma model after removing kinship, reporting, memorial, and military-political vocabularies.</p>
                <a href="semantic_field_ablation.html">Open Ablation Analysis</a>
            </section>
            <section class="hub-card">
                <h3>Book-Held-Out Robustness</h3>
                <p>Trains on all but one book, then tests whether the model generalises to the held-out book.</p>
                <a href="book_held_out.html">Open Held-Out Analysis</a>
            </section>
            <section class="hub-card">
                <h3>Model Error Analysis</h3>
                <p>Confident false mythic and false historical predictions for close-reading follow-up.</p>
                <a href="error_analysis.html">Open Error Analysis</a>
            </section>
            <section class="hub-card">
                <h3>Manual Label Sensitivity</h3>
                <p>Confusion matrix, label-scenario refits, and noise stress tests using the Greta/Rosie Book 3 manual labels.</p>
                <a href="label_sensitivity.html">Open Sensitivity Analysis</a>
            </section>
        </div>

        <h2>Translation Length</h2>
        <div class="hub-grid">
            <section class="hub-card">
                <h3>Unexpectedly Long or Short Translations</h3>
                <p>Greek predictors of length residuals, plus the dual view of English terms found in longer or shorter-than-expected passages.</p>
                <a href="../translation_length/index.html">Open Translation Length Analysis</a>
            </section>
            <section class="hub-card">
                <h3>Residual Length vs. Mythic/Historical Strength</h3>
                <p>Exploratory comparison of length-residual terms against the main mythic/historical classifier coefficients.</p>
                <a href="../translation_length/mythic_historical_strength.html">Open Diagnostic Page</a>
            </section>
        </div>

        <h2>Place and Network Analyses</h2>
        <div class="hub-grid">
            <section class="hub-card">
                <h3>Maps and Proper-Noun Networks</h3>
                <p>Geographic map, place-pair distances, and proper-noun co-occurrence network pages.</p>
                <a href="../places/index.html">Open Place and Network Pages</a>
            </section>
            <section class="hub-card">
                <h3>Paper Network Analyses</h3>
                <p>Mythic/historical subgraphs, bridge nouns, book-level drift, and place-person/deity networks.</p>
                <a href="../network_analysis/index.html">Open Network Analyses</a>
            </section>
        </div>

        <h2>Deprecated Predictor Pages</h2>
        <div class="hub-grid">
            <section class="hub-card deprecated">
                <h3>Passage Mythic Predictors</h3>
                <a href="../mythic_words.html">Open Page</a>
            </section>
            <section class="hub-card deprecated">
                <h3>Passage Skepticism Predictors</h3>
                <a href="../skeptic_words.html">Open Page</a>
            </section>
            <section class="hub-card deprecated">
                <h3>Sentence Mythic Predictors</h3>
                <a href="../sentence_mythic_words.html">Open Page</a>
            </section>
            <section class="hub-card deprecated">
                <h3>Sentence Skepticism Predictors</h3>
                <a href="../sentence_skeptic_words.html">Open Page</a>
            </section>
        </div>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page)


def _render_manto_community_rows(communities):
    rows = []
    for community in communities:
        localities = ", ".join(
            f"{item.get('label')} ({int(item.get('count') or 0)})"
            for item in community.get("top_localities", [])
        )
        places = ", ".join(
            item.get("label", "")
            for item in community.get("top_places", [])[:8]
        )
        marker = "Yes" if community.get("contains_athens_attica") else ""
        rows.append(f"""
            <tr>
                <td class="num">{int(community.get("community") or 0)}</td>
                <td>{marker}</td>
                <td class="num">{int(community.get("size") or 0):,}</td>
                <td class="num">{int(community.get("edge_count") or 0):,}</td>
                <td>{html.escape(localities)}</td>
                <td>{html.escape(places)}</td>
            </tr>
        """)
    if not rows:
        return '<tr><td colspan="6">No MANTO communities are available.</td></tr>'
    return "".join(rows)


def _manto_network_script(network_data):
    data_json = _manto_network_json_payload(network_data)
    return """
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
    const mantoData = __MANTO_DATA__;

    function formatNumber(value, digits) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) {
            return "n/a";
        }
        return Number(value).toFixed(digits);
    }

    function relationSummary(link) {
        const relations = link.relations || [];
        if (!relations.length) {
            return "No relation label recorded";
        }
        return relations.map(function (row) {
            return row.relation + " (" + row.count + ")";
        }).join(", ");
    }

    function sourceSummary(link) {
        const sources = link.sources || [];
        if (!sources.length) {
            return "No source label recorded";
        }
        return sources.map(function (row) {
            const year = row.latest_year === null || row.latest_year === undefined ? "" : ", latest year " + row.latest_year;
            return row.label + year + " (" + row.count + ")";
        }).join("<br>");
    }

    function nodeHtml(node) {
        const topPlaces = node.top_places || [];
        const places = topPlaces.map(function (row) { return row.label; }).join(", ");
        const localityRows = node.top_localities || [];
        const localities = localityRows.map(function (row) {
            return row.label + " (" + row.count + ")";
        }).join(", ");
        return "<strong>" + node.label + "</strong>"
            + "<br>Community: " + (node.community || "n/a")
            + "<br>Degree: " + (node.degree || 0)
            + "<br>Weighted links: " + (node.strength || 0)
            + "<br>PageRank: " + formatNumber(node.pagerank, 4)
            + (node.parent_label ? "<br>Locality: " + node.parent_label : "")
            + (places ? "<br>Leading places: " + places : "")
            + (localities ? "<br>Leading localities: " + localities : "");
    }

    function linkHtml(link) {
        const source = typeof link.source === "object" ? link.source.label : link.source;
        const target = typeof link.target === "object" ? link.target.label : link.target;
        return "<strong>" + source + " ↔ " + target + "</strong>"
            + "<br>Weight: " + (link.weight || 1)
            + "<br>Relations: " + relationSummary(link)
            + "<br>Sources:<br>" + sourceSummary(link);
    }

    function setDetails(html) {
        const detail = document.getElementById("manto-network-detail");
        if (detail) {
            detail.innerHTML = html;
        }
    }

    function renderNetwork(containerId, graph, options) {
        const container = document.getElementById(containerId);
        if (!container || !graph || !graph.nodes || !graph.nodes.length) {
            return;
        }
        const width = container.clientWidth || 900;
        const height = options.height || 620;
        const color = d3.scaleOrdinal()
            .domain(d3.range(1, 30))
            .range([
                "#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2",
                "#b279a2", "#ff9da6", "#9d755d", "#bab0ab", "#8cd17d",
                "#b6992d", "#499894", "#86bcb6", "#d37295", "#a0cbe8"
            ]);
        const tooltip = d3.select("#manto-network-tooltip");
        const svg = d3.select(container).append("svg")
            .attr("viewBox", [0, 0, width, height])
            .attr("role", "img")
            .attr("aria-label", options.label || "MANTO network visualization");
        const g = svg.append("g");
        svg.call(d3.zoom().scaleExtent([0.35, 4]).on("zoom", function (event) {
            g.attr("transform", event.transform);
        }));
        const links = (graph.links || []).map(function (link) { return Object.assign({}, link); });
        const nodes = (graph.nodes || []).map(function (node) { return Object.assign({}, node); });
        const linkForceDistance = options.linkDistance || 95;
        const simulation = d3.forceSimulation(nodes)
            .force("link", d3.forceLink(links).id(function (d) { return d.id; }).distance(linkForceDistance).strength(0.55))
            .force("charge", d3.forceManyBody().strength(options.charge || -260))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(function (d) {
                return (d.focus ? 28 : 13) + Math.sqrt(d.size || d.strength || d.degree || 1);
            }));

        const link = g.append("g")
            .attr("class", "manto-links")
            .selectAll("line")
            .data(links)
            .join("line")
            .attr("stroke-width", function (d) { return Math.max(1, Math.sqrt(d.weight || 1)); })
            .on("mousemove", function (event, d) {
                tooltip.style("display", "block")
                    .style("left", (event.pageX + 12) + "px")
                    .style("top", (event.pageY + 12) + "px")
                    .html(linkHtml(d));
            })
            .on("mouseout", function () {
                tooltip.style("display", "none");
            })
            .on("click", function (event, d) {
                setDetails(linkHtml(d));
            });
        link.append("title").text(function (d) { return relationSummary(d); });

        const node = g.append("g")
            .attr("class", "manto-nodes")
            .selectAll("circle")
            .data(nodes)
            .join("circle")
            .attr("r", function (d) {
                if (d.focus || d.contains_athens_attica) {
                    return 14;
                }
                return Math.max(5, Math.min(18, 4 + Math.sqrt(d.size || d.strength || d.degree || 1)));
            })
            .attr("fill", function (d) { return d.focus ? "#7f2d1f" : color(d.community || 0); })
            .attr("stroke", function (d) { return d.focus || d.contains_athens_attica ? "#2f241c" : "#fff"; })
            .attr("stroke-width", function (d) { return d.focus || d.contains_athens_attica ? 2.5 : 1.2; })
            .on("mousemove", function (event, d) {
                tooltip.style("display", "block")
                    .style("left", (event.pageX + 12) + "px")
                    .style("top", (event.pageY + 12) + "px")
                    .html(nodeHtml(d));
            })
            .on("mouseout", function () {
                tooltip.style("display", "none");
            })
            .on("click", function (event, d) {
                setDetails(nodeHtml(d));
            })
            .call(d3.drag()
                .on("start", function (event, d) {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on("drag", function (event, d) {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on("end", function (event, d) {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                }));
        node.append("title").text(function (d) { return d.label; });

        const labels = g.append("g")
            .attr("class", "manto-labels")
            .selectAll("text")
            .data(nodes.filter(function (d) {
                return d.focus || d.contains_athens_attica || (d.size && d.size >= 25) || (d.strength && d.strength >= 15);
            }))
            .join("text")
            .text(function (d) { return d.label; })
            .attr("font-size", "11px")
            .attr("dx", 10)
            .attr("dy", 4);

        simulation.on("tick", function () {
            link
                .attr("x1", function (d) { return d.source.x; })
                .attr("y1", function (d) { return d.source.y; })
                .attr("x2", function (d) { return d.target.x; })
                .attr("y2", function (d) { return d.target.y; });
            node
                .attr("cx", function (d) { return d.x; })
                .attr("cy", function (d) { return d.y; });
            labels
                .attr("x", function (d) { return d.x; })
                .attr("y", function (d) { return d.y; });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!mantoData.available) {
            return;
        }
        renderNetwork("manto-athens-network", mantoData.athens_network, {
            label: "Athens MANTO neighborhood",
            height: 660,
            charge: -320,
            linkDistance: 105
        });
        renderNetwork("manto-community-network", mantoData.community_network, {
            label: "MANTO place-community graph",
            height: 520,
            charge: -420,
            linkDistance: 150
        });
    });
    </script>
    """.replace("__MANTO_DATA__", data_json)


def generate_manto_network_pages(network_data, output_dir, title):
    """Generate MANTO place-network visualisation pages."""
    places_dir = os.path.join(output_dir, "places")
    os.makedirs(places_dir, exist_ok=True)

    if not network_data or not network_data.get("available"):
        message = html.escape(
            network_data.get("message", "No MANTO network data is available.")
            if network_data
            else "No MANTO network data is available."
        )
        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - MANTO Place Network</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>MANTO place network</p>
    </header>
    {_site_nav("../", "places")}
    <div class="container">
        <div class="breadcrumb"><a href="index.html">Places</a> &rsaquo; MANTO Place Network</div>
        <h2>MANTO Place Network</h2>
        <p>{message}</p>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
        with open(os.path.join(places_dir, "manto-network.html"), "w", encoding="utf-8") as f:
            f.write(page)
        return

    athens = network_data.get("athens", {})
    communities = network_data.get("communities", [])
    script = _manto_network_script(network_data)
    athens_summary = f"""
        <div class="metric-strip">
            <div><strong>{int(network_data.get("node_count", 0)):,}</strong><span>MANTO places</span></div>
            <div><strong>{int(network_data.get("edge_count", 0)):,}</strong><span>place links</span></div>
            <div><strong>{int(network_data.get("community_count", 0)):,}</strong><span>detected communities</span></div>
            <div><strong>{_format_network_float(network_data.get("modularity", 0), 3)}</strong><span>modularity</span></div>
        </div>
        <div class="metric-strip">
            <div><strong>{int(athens.get("degree", 0)):,}</strong><span>Athens neighbors</span></div>
            <div><strong>{int(athens.get("community_size", 0)):,}</strong><span>Athens community size</span></div>
            <div><strong>{_format_network_float(athens.get("clustering", 0), 3)}</strong><span>Athens clustering</span></div>
            <div><strong>{_format_network_float(athens.get("neighbor_density", 0), 3)}</strong><span>neighbor density</span></div>
        </div>
    """
    structure_note = (
        "Athens is not treated as a complete clique here. The local-clustering "
        f"coefficient is {_format_network_float(athens.get('clustering', 0), 3)} "
        f"with {int(athens.get('triangles', 0)):,} closed neighbor triangles; "
        f"its neighbors have density {_format_network_float(athens.get('neighbor_density', 0), 3)}. "
        "That is a hub embedded in a dense community, not an all-to-all clique."
    )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - MANTO Place Network</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>MANTO place-place structure and source-backed links</p>
    </header>
    {_site_nav("../", "places")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Places</a> &rsaquo; MANTO Place Network</div>
        <h2>MANTO Place Network</h2>
        <p class="note">This page uses the latest imported MANTO release ({int(network_data.get("release_record_id", 0))}) and strict pre-Pausanias place-place edges, plus MANTO <code>somewhere_in_or_near</code> locality edges from place details. Hover or click a link to see relation labels and source labels recorded for that edge.</p>
        {athens_summary}

        <section class="manto-network-layout">
            <div>
                <h2>Athens Neighborhood</h2>
                <p class="note">{html.escape(structure_note)}</p>
                <div id="manto-athens-network" class="manto-network-panel"></div>
            </div>
            <aside id="manto-network-detail" class="manto-network-detail">
                <strong>Network details</strong><br>
                Hover or click a node or link to see MANTO relation/source evidence.
            </aside>
        </section>

        <h2>Community Graph</h2>
        <p class="note">Nodes are detected MANTO place communities; links are aggregated cross-community place links among the displayed communities.</p>
        <div id="manto-community-network" class="manto-network-panel manto-community-panel"></div>

        <h2>Detected Place Communities</h2>
        <table class="predictor-table">
            <thead>
                <tr><th>#</th><th>Athens?</th><th>Places</th><th>Internal Edges</th><th>Leading Localities</th><th>Leading Places</th></tr>
            </thead>
            <tbody>{_render_manto_community_rows(communities)}</tbody>
        </table>

        <footer>{_generated_footer()}</footer>
    </div>
    <div id="manto-network-tooltip" class="manto-network-tooltip"></div>
    {script}
</body>
</html>
"""
    with open(os.path.join(places_dir, "manto-network.html"), "w", encoding="utf-8") as f:
        f.write(page)


def _render_manto_link_rows(links):
    if not links:
        return '<tr><td colspan="7">No MANTO place links are available.</td></tr>'
    rows = []
    for link in links:
        survival = link.get("survival_label") or ""
        survival_cell = {
            "survives": '<span class="badge badge-good">survives</span>',
            "does_not_survive": '<span class="badge badge-bad">does not survive</span>',
            "conflicting": '<span class="badge">conflicting</span>',
        }.get(survival, "")
        rows.append(
            "<tr>"
            f"<td>{html.escape(link['reference_form'])}</td>"
            f"<td>{html.escape(link['english_transcription'])}</td>"
            f"<td>{html.escape(link['manto_label'])}</td>"
            f"<td><code>{html.escape(link['manto_id'])}</code></td>"
            f"<td>{html.escape(link['match_method'])}</td>"
            f"<td>{html.escape(link['confidence'])}{' ✓' if link.get('reviewed') else ''}</td>"
            f"<td>{survival_cell}</td>"
            "</tr>"
        )
    return "".join(rows)


def _render_manto_unlinked_rows(unlinked):
    if not unlinked:
        return '<tr><td colspan="4">Every labelled place currently links to MANTO.</td></tr>'
    rows = []
    for item in unlinked:
        rows.append(
            "<tr>"
            f"<td>{html.escape(item['place_name'])}</td>"
            f"<td>{html.escape(item['survival_label'])}</td>"
            f"<td>{int(item['mention_count'])}</td>"
            f"<td>{html.escape(item.get('llm_decision') or '')}</td>"
            "</tr>"
        )
    return "".join(rows)


def generate_manto_links_page(links_data, output_dir, title):
    """Generate the MANTO-Pausanias place-link listing and curation queue."""
    places_dir = os.path.join(output_dir, "places")
    os.makedirs(places_dir, exist_ok=True)

    if not links_data or not links_data.get("available"):
        message = html.escape(
            links_data.get("message", "No MANTO link data is available.")
            if links_data
            else "No MANTO link data is available."
        )
        body = f"<p>{message}</p>"
        summary = ""
        method_note = ""
    else:
        method_counts = links_data.get("method_counts", {})
        method_note = ", ".join(
            f"{html.escape(method)}: {count:,}"
            for method, count in sorted(method_counts.items(), key=lambda item: -item[1])
        )
        summary = f"""
        <div class="metric-strip">
            <div><strong>{int(links_data.get("linked_count", 0)):,}</strong><span>Pausanias&ndash;MANTO links</span></div>
            <div><strong>{int(links_data.get("labelled_place_count", 0)):,}</strong><span>places with survival labels</span></div>
            <div><strong>{int(links_data.get("unlinked_count", 0)):,}</strong><span>labelled but unlinked</span></div>
        </div>
        """
        body = f"""
        <h2>Linked Places</h2>
        <p class="note">Match methods: {method_note}. Links marked ✓ have been manually reviewed. Curated rows come from <code>curated_place_links</code> (manual entries or LLM suggestions via <code>llm_link_manto_places.py</code>).</p>
        <table class="predictor-table">
            <thead>
                <tr><th>Pausanias Form</th><th>Transcription</th><th>MANTO Label</th><th>MANTO ID</th><th>Method</th><th>Confidence</th><th>Survival Label</th></tr>
            </thead>
            <tbody>{_render_manto_link_rows(links_data.get("links", []))}</tbody>
        </table>

        <h2>Curation Queue: Labelled but Unlinked</h2>
        <p class="note">These places carry survival labels from the place-state sweeps but match no MANTO entity yet. Add rows to <code>curated_place_links</code> (source='manual') or run <code>llm_link_manto_places.py</code>, then re-run <code>link_manto_places.py</code>.</p>
        <table class="predictor-table">
            <thead>
                <tr><th>Labelled Place Name</th><th>Survival Label</th><th>Mentions</th><th>LLM Decision</th></tr>
            </thead>
            <tbody>{_render_manto_unlinked_rows(links_data.get("unlinked", []))}</tbody>
        </table>
        """

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - MANTO Place Links</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Pausanias&ndash;MANTO place identifications</p>
    </header>
    {_site_nav("../", "places")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Places</a> &rsaquo; MANTO Place Links</div>
        <h2>MANTO &harr; Pausanias Connections</h2>
        <p class="note">How places named by Pausanias map onto MANTO mythology entities. These links join the survival labels to the MANTO network features in the place-survival model.</p>
        {summary}
        {body}
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(places_dir, "manto-links.html"), "w", encoding="utf-8") as f:
        f.write(page)


def generate_places_index(output_dir, title):
    """Generate a hub page for geographic and noun-network views."""
    places_dir = os.path.join(output_dir, "places")
    os.makedirs(places_dir, exist_ok=True)

    network_dir = Path(output_dir) / "network_viz"
    component_pages = []
    if network_dir.exists():
        component_pages = sorted(
            network_dir.glob("component_*.html"),
            key=lambda path: int(path.stem.split("_")[1])
            if path.stem.split("_")[1].isdigit()
            else path.stem,
        )
    component_links = ""
    if component_pages:
        component_links = "<ul class=\"compact-list\">" + "".join(
            f'<li><a href="../network_viz/{path.name}">Component {html.escape(path.stem.split("_")[1])}</a></li>'
            for path in component_pages
        ) + "</ul>"
    component_map_link = ""
    if (network_dir / "component_map.png").exists():
        component_map_link = '<a href="../network_viz/component_map.png">Open Component Map</a>'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Places</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Places, proper nouns, and networks</p>
    </header>
    {_site_nav("../", "places")}
    <div class="container wide-container">
        <h2>Maps</h2>
        <div class="hub-grid">
            <section class="hub-card">
                <h3>Global Place Map</h3>
                <p>Interactive map of geolocated places mentioned by Pausanias.</p>
                <a href="../map/index.html">Open Map</a>
            </section>
            <section class="hub-card">
                <h3>Geographic Surprise / Place Pairs</h3>
                <p>Distances between geolocated places mentioned in the same passage, sorted by largest separation.</p>
                <a href="../place_pairs/index.html">Open Place Pairs</a>
            </section>
            <section class="hub-card">
                <h3>Passage Mini-maps</h3>
                <p>Individual translation pages include mini-maps when a passage has geolocated places.</p>
                <a href="../translation/index.html">Open Translation</a>
            </section>
        </div>

        <h2>Network Analysis</h2>
        <div class="hub-grid">
            <section class="hub-card">
                <h3>MANTO Place Network</h3>
                <p>Strict pre-Pausanias MANTO place-place links, locality edges, Athens neighborhood structure, and detected place communities.</p>
                <a href="manto-network.html">Open MANTO Network</a>
            </section>
            <section class="hub-card">
                <h3>MANTO Place Links</h3>
                <p>How Pausanias' place names map onto MANTO entities: link methods, confidence, survival labels, and the labelled-but-unlinked curation queue.</p>
                <a href="manto-links.html">Open MANTO Links</a>
            </section>
            <section class="hub-card">
                <h3>Interactive Network</h3>
                <p>Full proper-noun co-occurrence network with component, centrality, link, and node filters.</p>
                <a href="../network_viz/index.html">Open Full Network</a>
            </section>
            <section class="hub-card">
                <h3>Paper Network Analyses</h3>
                <p>Mythic/historical subgraphs, bridge nouns, book-level drift, and place-person/deity networks.</p>
                <a href="../network_analysis/index.html">Open Network Analyses</a>
            </section>
            <section class="hub-card">
                <h3>Network Components</h3>
                <p>Separate pages for the largest connected components in the proper-noun network.</p>
                {component_links or '<p>No component pages are present in this build yet.</p>'}
            </section>
            <section class="hub-card">
                <h3>Static Network Exports</h3>
                <p>Generated network images, including the component map when available.</p>
                {component_map_link or '<p>No static component map is present in this build yet.</p>'}
            </section>
        </div>

        <h2>Proper Noun Indices</h2>
        <div class="hub-grid">
            <section class="hub-card">
                <h3>All Proper Nouns</h3>
                <p>Index of people, places, deities, and other named entities.</p>
                <a href="../translation/nouns/index.html">Open Noun Index</a>
            </section>
            <section class="hub-card">
                <h3>Places</h3>
                <p>Named places extracted from the text.</p>
                <a href="../translation/nouns/places.html">Open Places Index</a>
            </section>
            <section class="hub-card">
                <h3>People</h3>
                <p>Named people and groups extracted from the text.</p>
                <a href="../translation/nouns/people.html">Open People Index</a>
            </section>
            <section class="hub-card">
                <h3>Deities</h3>
                <p>Named deities extracted from the text.</p>
                <a href="../translation/nouns/deities.html">Open Deities Index</a>
            </section>
            <section class="hub-card">
                <h3>Other Entities</h3>
                <p>Named entities that are not currently grouped as people, places, or deities.</p>
                <a href="../translation/nouns/other.html">Open Other Index</a>
            </section>
        </div>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(places_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)


def _format_network_float(value, places=3):
    if value is None:
        return ""
    return f"{float(value):.{places}f}"


def _entity_count_text(counts):
    if not counts:
        return ""
    order = ["place", "person", "deity", "other"]
    parts = []
    for key in order:
        if counts.get(key):
            parts.append(f"{html.escape(key)} {int(counts[key]):,}")
    for key, value in sorted(counts.items()):
        if key not in order and value:
            parts.append(f"{html.escape(str(key))} {int(value):,}")
    return ", ".join(parts)


def _network_metric_strip(metrics):
    return f"""
        <div class="metric-strip">
            <div><strong>{metrics.get("node_count", 0):,}</strong><span>nodes</span></div>
            <div><strong>{metrics.get("edge_count", 0):,}</strong><span>edges</span></div>
            <div><strong>{metrics.get("component_count", 0):,}</strong><span>components</span></div>
            <div><strong>{metrics.get("largest_component_size", 0):,}</strong><span>largest component</span></div>
            <div><strong>{_format_network_float(metrics.get("density", 0), 4)}</strong><span>density</span></div>
        </div>
    """


def _render_network_node_rows(rows, include_bridge=False):
    if not rows:
        return "<tr><td colspan=\"9\">No rows available yet.</td></tr>"

    output = []
    for row in rows:
        if include_bridge:
            output.append(f"""
                <tr>
                    <td>{html.escape(str(row["label"]))}</td>
                    <td>{html.escape(str(row["entity_type"]))}</td>
                    <td class="num">{int(row["mythic_count"]):,}</td>
                    <td class="num">{int(row["historical_count"]):,}</td>
                    <td class="num">{int(row["other_count"]):,}</td>
                    <td class="num">{int(row["neighbor_count"]):,}</td>
                    <td class="num">{int(row["strength"]):,}</td>
                    <td class="num">{_format_network_float(row["betweenness_centrality"], 4)}</td>
                    <td class="num">{_format_network_float(row["bridge_score"], 4)}</td>
                </tr>
            """)
        else:
            output.append(f"""
                <tr>
                    <td>{html.escape(str(row["label"]))}</td>
                    <td>{html.escape(str(row["entity_type"]))}</td>
                    <td class="num">{int(row.get("context_count", 0)):,}</td>
                    <td class="num">{int(row["neighbor_count"]):,}</td>
                    <td class="num">{int(row["strength"]):,}</td>
                    <td class="num">{_format_network_float(row["degree_centrality"], 4)}</td>
                    <td class="num">{_format_network_float(row["betweenness_centrality"], 4)}</td>
                </tr>
            """)
    return "".join(output)


def _render_network_strength_rows(rows):
    if not rows:
        return "<tr><td colspan=\"5\">No rows available yet.</td></tr>"

    output = []
    for row in rows:
        output.append(f"""
            <tr>
                <td>{html.escape(str(row["label"]))}</td>
                <td>{html.escape(str(row["entity_type"]))}</td>
                <td class="num">{int(row.get("context_count", 0)):,}</td>
                <td class="num">{int(row["neighbor_count"]):,}</td>
                <td class="num">{int(row["strength"]):,}</td>
            </tr>
        """)
    return "".join(output)


def _render_community_rows(rows):
    if not rows:
        return "<tr><td colspan=\"5\">No community rows available yet.</td></tr>"

    output = []
    for row in rows:
        output.append(f"""
            <tr>
                <td class="num">{int(row["community"])}</td>
                <td class="num">{int(row["size"]):,}</td>
                <td class="num">{int(row["edge_count"]):,}</td>
                <td>{html.escape(_entity_count_text(row.get("entity_counts", {})))}</td>
                <td>{html.escape(", ".join(row.get("top_nodes", [])))}</td>
            </tr>
        """)
    return "".join(output)


def _render_louvain_community_rows(rows):
    if not rows:
        return "<tr><td colspan=\"8\">No Louvain community rows available yet.</td></tr>"

    output = []
    for row in rows:
        output.append(f"""
            <tr>
                <td class="num">{int(row["community"])}</td>
                <td>{html.escape(str(row["dominant_context"]))}</td>
                <td class="num">{int(row["size"]):,}</td>
                <td class="num">{int(row.get("node_mythic", 0)):,}</td>
                <td class="num">{int(row.get("node_historical", 0)):,}</td>
                <td class="num">{int(row.get("context_mythic", 0)):,}</td>
                <td class="num">{int(row.get("context_historical", 0)):,}</td>
                <td>{html.escape(", ".join(row.get("top_nodes", [])))}</td>
            </tr>
        """)
    return "".join(output)


def _render_louvain_cross_edge_rows(rows):
    if not rows:
        return "<tr><td colspan=\"3\">No cross-community edges available.</td></tr>"

    output = []
    for row in rows:
        output.append(f"""
            <tr>
                <td class="num">{int(row["source"])}</td>
                <td class="num">{int(row["target"])}</td>
                <td class="num">{int(row["weight"]):,}</td>
            </tr>
        """)
    return "".join(output)


def generate_network_analysis_pages(network_analysis, output_dir, title):
    """Generate paper-facing network analysis pages."""
    analysis_dir = os.path.join(output_dir, "network_analysis")
    os.makedirs(analysis_dir, exist_ok=True)

    if not network_analysis or not network_analysis.get("available"):
        message = html.escape(
            network_analysis.get("message", "No network analysis data is available.")
            if network_analysis
            else "No network analysis data is available."
        )
        index_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Network Analyses</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Paper-facing proper-noun network analyses</p>
    </header>
    {_site_nav("../", "places")}
    <div class="container">
        <h2>Network Analyses</h2>
        <p>{message}</p>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
        with open(os.path.join(analysis_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(index_page)
        return

    sentence_stats = network_analysis.get("sentence_matching", {})
    class_subgraphs = network_analysis.get("class_subgraphs", {})

    class_sections = []
    for bucket, label in [("mythic", "Mythic"), ("historical", "Historical")]:
        subgraph = class_subgraphs.get(bucket)
        if not subgraph:
            class_sections.append(f"<h2>{label}</h2><p>No {bucket} noun network is available yet.</p>")
            continue
        class_sections.append(f"""
            <h2>{label} Sentence Subgraph</h2>
            {_network_metric_strip(subgraph["metrics"])}
            <h3>Central Nouns</h3>
            <table class="predictor-table">
                <thead>
                    <tr><th>Noun</th><th>Type</th><th>Sentences</th><th>Neighbors</th><th>Weighted Links</th><th>Degree</th><th>Betweenness</th></tr>
                </thead>
                <tbody>{_render_network_node_rows(subgraph.get("top_nodes", []))}</tbody>
            </table>

            <h3>Communities</h3>
            <table class="predictor-table">
                <thead>
                    <tr><th>#</th><th>Nodes</th><th>Edges</th><th>Types</th><th>Leading Nouns</th></tr>
                </thead>
                <tbody>{_render_community_rows(subgraph.get("communities", []))}</tbody>
            </table>
        """)

    class_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Mythic and Historical Subgraphs</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Proper-noun networks inside current Greta sentence classes</p>
    </header>
    {_site_nav("../", "places")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Network Analyses</a> &rsaquo; Mythic and Historical Subgraphs</div>
        <p class="note">These subgraphs use proper nouns whose extracted exact form appears inside an active Greta-tagged sentence. Betweenness is sampled on larger graphs, so it is for ranking rather than exact reporting.</p>
        {''.join(class_sections)}
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "class_subgraphs.html"), "w", encoding="utf-8") as f:
        f.write(class_page)

    bridge_rows = _render_network_node_rows(
        network_analysis.get("bridge_nouns", []),
        include_bridge=True,
    )
    bridge_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Bridge Nouns</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Names and places connecting mythic and historical sentence networks</p>
    </header>
    {_site_nav("../", "places")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Network Analyses</a> &rsaquo; Bridge Nouns</div>
        <h2>Bridge Nouns</h2>
        <p class="note">Bridge score combines approximate betweenness with how evenly a noun appears in mythic and historical tagged sentences.</p>
        <table class="predictor-table">
            <thead>
                <tr><th>Noun</th><th>Type</th><th>Mythic</th><th>Historical</th><th>Other</th><th>Neighbors</th><th>Weighted Links</th><th>Betweenness</th><th>Bridge Score</th></tr>
            </thead>
            <tbody>{bridge_rows}</tbody>
        </table>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "bridge_nouns.html"), "w", encoding="utf-8") as f:
        f.write(bridge_page)

    louvain = network_analysis.get("louvain_core", {})
    if louvain.get("available"):
        louvain_body = f"""
        <p class="note">This shared-core analysis builds one sentence-level proper-noun graph from mythic and historical sentences, excludes books 4 and 8, keeps names in at least <strong>{int(louvain.get("min_contexts", 0))}</strong> tagged sentences with weighted degree at least <strong>{int(louvain.get("min_strength", 0))}</strong>, and then runs Louvain community detection.</p>
        <div class="metric-strip">
            <div><strong>{int(louvain.get("core_node_count", 0)):,}</strong><span>core names</span></div>
            <div><strong>{int(louvain.get("core_edge_count", 0)):,}</strong><span>core links</span></div>
            <div><strong>{int(louvain.get("community_count", 0)):,}</strong><span>communities</span></div>
            <div><strong>{_format_network_float(louvain.get("modularity", 0), 3)}</strong><span>modularity</span></div>
        </div>

        <h2>Louvain Communities</h2>
        <table class="predictor-table">
            <thead>
                <tr><th>#</th><th>Dominant</th><th>Names</th><th>Mythic-Dominant Names</th><th>Historical-Dominant Names</th><th>Mythic Contexts</th><th>Historical Contexts</th><th>Leading Names</th></tr>
            </thead>
            <tbody>{_render_louvain_community_rows(louvain.get("communities", []))}</tbody>
        </table>

        <h2>Strongest Cross-Community Links</h2>
        <table class="predictor-table">
            <thead>
                <tr><th>Community A</th><th>Community B</th><th>Weighted Links</th></tr>
            </thead>
            <tbody>{_render_louvain_cross_edge_rows(louvain.get("cross_community_edges", []))}</tbody>
        </table>
        """
    else:
        louvain_body = f"<p>{html.escape(louvain.get('message', 'No Louvain core analysis is available.'))}</p>"
    louvain_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Louvain Core Communities</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Community detection on the shared mythic/historical proper-noun core</p>
    </header>
    {_site_nav("../", "places")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Network Analyses</a> &rsaquo; Louvain Core Communities</div>
        <h2>Louvain Core Communities</h2>
        {louvain_body}
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "louvain_core.html"), "w", encoding="utf-8") as f:
        f.write(louvain_page)

    book_rows = []
    for book in network_analysis["book_drift"].get("books", []):
        metrics = book["metrics"]
        top = ", ".join(row["label"] for row in book.get("top_nodes", [])[:5])
        node_jaccard = book.get("node_jaccard_previous")
        edge_jaccard = book.get("edge_jaccard_previous")
        book_rows.append(f"""
            <tr>
                <td class="num">{html.escape(str(book["book"]))}</td>
                <td class="num">{metrics.get("node_count", 0):,}</td>
                <td class="num">{metrics.get("edge_count", 0):,}</td>
                <td class="num">{metrics.get("component_count", 0):,}</td>
                <td class="num">{metrics.get("largest_component_size", 0):,}</td>
                <td class="num">{_format_network_float(metrics.get("density", 0), 4)}</td>
                <td class="num">{_format_network_float(node_jaccard, 3)}</td>
                <td class="num">{_format_network_float(edge_jaccard, 3)}</td>
                <td>{html.escape(top)}</td>
            </tr>
        """)

    scope_sections = []
    for scope in network_analysis["book_drift"].get("scopes", []):
        scope_sections.append(f"""
            <h3>{html.escape(scope["label"])}</h3>
            {_network_metric_strip(scope["metrics"])}
            <table class="predictor-table">
                <thead>
                    <tr><th>Noun</th><th>Type</th><th>Passages</th><th>Neighbors</th><th>Weighted Links</th></tr>
                </thead>
                <tbody>{_render_network_strength_rows(scope.get("top_nodes", []))}</tbody>
            </table>
        """)

    book_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Book-Level Network Drift</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Book-level proper-noun network drift</p>
    </header>
    {_site_nav("../", "places")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Network Analyses</a> &rsaquo; Book-Level Drift</div>
        <h2>Per-Book Networks</h2>
        <table class="predictor-table">
            <thead>
                <tr><th>Book</th><th>Nodes</th><th>Edges</th><th>Components</th><th>Largest Component</th><th>Density</th><th>Node Jaccard vs Previous</th><th>Edge Jaccard vs Previous</th><th>Leading Nouns</th></tr>
            </thead>
            <tbody>{''.join(book_rows)}</tbody>
        </table>

        <h2>Book 4 and 8 Sensitivity</h2>
        {''.join(scope_sections)}
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "book_drift.html"), "w", encoding="utf-8") as f:
        f.write(book_page)

    bipartite = network_analysis.get("bipartite", {})
    pair_rows = []
    for row in bipartite.get("top_pairs", []):
        pair_rows.append(f"""
            <tr>
                <td>{html.escape(str(row["place"]))}</td>
                <td>{html.escape(str(row["counterpart"]))}</td>
                <td>{html.escape(str(row["counterpart_type"]))}</td>
                <td class="num">{int(row["weight"]):,}</td>
                <td class="num">{int(row["passage_count"]):,}</td>
            </tr>
        """)

    top_place_rows = _render_network_strength_rows(
        [
            {
                "label": row["label"],
                "entity_type": "place",
                "context_count": 0,
                "neighbor_count": row["neighbor_count"],
                "strength": row["strength"],
                "degree_centrality": 0.0,
                "betweenness_centrality": 0.0,
            }
            for row in bipartite.get("top_places", [])
        ],
    )
    top_actor_rows = _render_network_strength_rows(
        [
            {
                "label": row["label"],
                "entity_type": row["entity_type"],
                "context_count": 0,
                "neighbor_count": row["neighbor_count"],
                "strength": row["strength"],
                "degree_centrality": 0.0,
                "betweenness_centrality": 0.0,
            }
            for row in bipartite.get("top_people_deities", [])
        ],
    )
    bipartite_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Place-Person and Place-Deity Networks</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Place-to-person and place-to-deity co-mention networks</p>
    </header>
    {_site_nav("../", "places")}
    <div class="container wide-container">
        <div class="breadcrumb"><a href="index.html">Network Analyses</a> &rsaquo; Bipartite Networks</div>
        <div class="metric-strip">
            <div><strong>{bipartite.get("pair_count", 0):,}</strong><span>place-counterpart pairs</span></div>
            <div><strong>{bipartite.get("passage_count", 0):,}</strong><span>passages</span></div>
        </div>

        <h2>Top Place-Person/Deity Pairs</h2>
        <table class="predictor-table">
            <thead>
                <tr><th>Place</th><th>Person/Deity</th><th>Type</th><th>Weighted Links</th><th>Passages</th></tr>
            </thead>
            <tbody>{''.join(pair_rows) if pair_rows else '<tr><td colspan="5">No bipartite pairs available yet.</td></tr>'}</tbody>
        </table>

        <h2>Top Places</h2>
        <table class="predictor-table">
            <thead>
                <tr><th>Place</th><th>Type</th><th>Passages</th><th>Counterparts</th><th>Weighted Links</th></tr>
            </thead>
            <tbody>{top_place_rows}</tbody>
        </table>

        <h2>Top People and Deities</h2>
        <table class="predictor-table">
            <thead>
                <tr><th>Name</th><th>Type</th><th>Passages</th><th>Places</th><th>Weighted Links</th></tr>
            </thead>
            <tbody>{top_actor_rows}</tbody>
        </table>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "bipartite.html"), "w", encoding="utf-8") as f:
        f.write(bipartite_page)

    index_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Network Analyses</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Paper-facing proper-noun network analyses</p>
    </header>
    {_site_nav("../", "places")}
    <div class="container wide-container">
        <h2>Network Analyses</h2>
        <p class="note">The Greta-class pages are preliminary until sentence splitting and tagging finish. Current exact-form matching found nouns in <strong>{sentence_stats.get("sentences_with_matched_nouns", 0):,}</strong> of <strong>{sentence_stats.get("tagged_sentence_count", 0):,}</strong> active tagged sentences.</p>
        <div class="hub-grid">
            <section class="hub-card">
                <h3>Mythic vs Historical Subgraphs</h3>
                <p>Central nouns and communities inside the current Greta mythic and historical sentence classes.</p>
                <a href="class_subgraphs.html">Open Subgraphs</a>
            </section>
            <section class="hub-card">
                <h3>Bridge Nouns</h3>
                <p>Names and places with high bridge scores between mythic and historical sentence networks.</p>
                <a href="bridge_nouns.html">Open Bridge Nouns</a>
            </section>
            <section class="hub-card">
                <h3>Louvain Core Communities</h3>
                <p>Community detection on the shared mythic/historical proper-noun core, excluding books 4 and 8.</p>
                <a href="louvain_core.html">Open Louvain Core</a>
            </section>
            <section class="hub-card">
                <h3>Book-Level Drift</h3>
                <p>Per-book proper-noun network shape, adjacent-book overlap, and Book 4/8 sensitivity.</p>
                <a href="book_drift.html">Open Book Drift</a>
            </section>
            <section class="hub-card">
                <h3>Place-Person/Deity Networks</h3>
                <p>Bipartite co-mention views that suppress same-type proper-noun noise.</p>
                <a href="bipartite.html">Open Bipartite Networks</a>
            </section>
            <section class="hub-card">
                <h3>Geographic Surprise</h3>
                <p>Co-mentioned places sorted by geographic distance. This is the existing place-pair separation view.</p>
                <a href="../place_pairs/index.html">Open Place Pairs</a>
            </section>
        </div>
        <footer>{_generated_footer()}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(analysis_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page)


def generate_mythic_page(passages_df, mythic_color_map, mythic_class_map, proper_nouns_dict, output_dir, title):
    """Generate pages showing mythic aspects of passages grouped by chapter."""

    passages_df = passages_df.copy()
    passages_df['chapter'] = passages_df['id'].apply(lambda pid: '.'.join(pid.split('.')[:2]))
    chapters = sorted(passages_df['chapter'].unique(), key=lambda c: [int(p) for p in c.split('.')])

    mythic_dir = os.path.join(output_dir, 'mythic')
    os.makedirs(mythic_dir, exist_ok=True)

    # Create chapter pages
    for chapter in chapters:
        chapter_passages = passages_df[passages_df['chapter'] == chapter]
        html_content = f"""<!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>{title} - Mythic Analysis {chapter}</title>
        <link rel=\"stylesheet\" href=\"../css/style.css\">
    </head>
    <body>
        <header>
            <h1>{title}</h1>
            <p>Analysis of Mythic vs. Historical Elements in Pausanias</p>
        </header>

        {_site_nav("../", "annotations")}

        <div class=\"container\">
            <div class=\"legend\">
                <h3>Legend:</h3>
                <div class=\"legend-item\">
                    <span class=\"color-sample mythic-sample\"></span> Mythic content (warmer colors, <span class=\"mythic\">italics</span>)
                </div>
                <div class=\"legend-item\">
                    <span class=\"color-sample historical-sample\"></span> Historical content (cooler colors)
                </div>
                <p>Color intensity indicates the strength of the predictive word or phrase.</p>
            </div>

            <h2>Chapter {chapter}</h2>
    """

        for _, row in chapter_passages.iterrows():
            passage_id = row['id']
            passage_text = row['passage']
            is_mythic = row['references_mythic_era']
            translation = row.get('english_translation', None)
            proper_nouns = proper_nouns_dict.get(passage_id, [])

            highlighted_passage = highlight_passage(
                passage_text,
                mythic_color_map,
                mythic_color_map,
                mythic_class_map,
                is_mythic_page=True
            )

            html_content += f"""
            <div class=\"passage\">
                <div class=\"passage-header\">
                    <span class=\"passage-id\">Passage {passage_id}</span>
                    <span class=\"passage-class\">Class: {'Mythic' if is_mythic else 'Historical'}</span>
                </div>
                <div class=\"passage-container\">
                     <div class=\"greek-text\">
                         {highlighted_passage}
        """

            if proper_nouns:
                html_content += f"""
                        <div class=\"proper-nouns\">
                            <div class=\"proper-noun-header\">Proper Nouns:</div>
            """

                for noun in sorted(proper_nouns):
                    html_content += f"""
                            <span class=\"proper-noun-tag\">{html.escape(noun)}</span>
                """

                html_content += """
                        </div>
                """

            html_content += """
                     </div>
        """

            if translation and not pd.isna(translation):
                html_content += f"""
                    <div class=\"english-translation\">
                        {translation}
                    </div>
            """

            html_content += """
                </div>
            </div>
        """

        html_content += f"""
            <footer>
                Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")} from the PostgreSQL database
            </footer>
        </div>
    </body>
    </html>
    """

        filename = f"{chapter.replace('.', '_')}.html"
        with open(os.path.join(mythic_dir, filename), 'w', encoding='utf-8') as f:
            f.write(html_content)

    # Create index page linking to chapters
    index_content = f"""<!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>{title} - Mythic Analysis</title>
        <link rel=\"stylesheet\" href=\"../css/style.css\">
    </head>
    <body>
        <header>
            <h1>{title}</h1>
            <p>Analysis of Mythic vs. Historical Elements in Pausanias</p>
        </header>

        {_site_nav("../", "annotations")}

        <div class=\"container\">
            <h2>Chapters</h2>
            <ul>
    """

    for chapter in chapters:
        filename = f"{chapter.replace('.', '_')}.html"
        index_content += f"<li><a href=\"{filename}\">Chapter {chapter}</a></li>\n"

    index_content += """
            </ul>
            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """ from the PostgreSQL database
            </footer>
        </div>
    </body>
    </html>
    """

    with open(os.path.join(mythic_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_content)

    write_redirect_page(output_dir, "mythic.html", "mythic/index.html", "Mythic Analysis")

def generate_skepticism_page(passages_df, skeptic_color_map, skeptic_class_map, proper_nouns_dict, output_dir, title):
    """Generate pages showing skeptical aspects of passages grouped by chapter."""

    passages_df = passages_df.copy()
    passages_df['chapter'] = passages_df['id'].apply(lambda pid: '.'.join(pid.split('.')[:2]))
    chapters = sorted(passages_df['chapter'].unique(), key=lambda c: [int(p) for p in c.split('.')])

    skeptic_dir = os.path.join(output_dir, 'skepticism')
    os.makedirs(skeptic_dir, exist_ok=True)

    for chapter in chapters:
        chapter_passages = passages_df[passages_df['chapter'] == chapter]
        html_content = f"""<!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>{title} - Skepticism Analysis {chapter}</title>
        <link rel=\"stylesheet\" href=\"../css/style.css\">
    </head>
    <body>
        <header>
            <h1>{title}</h1>
            <p>Analysis of Skepticism in Pausanias</p>
        </header>

        {_site_nav("../", "annotations")}

        <div class=\"container\">
            <div class=\"legend\">
                <h3>Legend:</h3>
                <div class=\"legend-item\">
                    <span class=\"color-sample skeptical-sample\"></span> Skeptical content (green)
                </div>
                <div class=\"legend-item\">
                    <span class=\"color-sample non-skeptical-sample\"></span> Non-skeptical content (orange, <strong>bold</strong>)
                </div>
                <p>Color intensity indicates the strength of the predictive word or phrase.</p>
            </div>

            <h2>Chapter {chapter}</h2>
    """

        for _, row in chapter_passages.iterrows():
            passage_id = row['id']
            passage_text = row['passage']
            is_skeptical = row['expresses_scepticism']
            translation = row.get('english_translation', None)
            proper_nouns = proper_nouns_dict.get(passage_id, [])

            highlighted_passage = highlight_passage(
                passage_text,
                skeptic_color_map,
                skeptic_color_map,
                skeptic_class_map,
                is_mythic_page=False
            )

            html_content += f"""
            <div class=\"passage\">
                <div class=\"passage-header\">
                    <span class=\"passage-id\">Passage {passage_id}</span>
                    <span class=\"passage-class\">Class: {'Skeptical' if is_skeptical else 'Non-skeptical'}</span>
                </div>
                <div class=\"passage-container\">
                   <div class=\"greek-text\">
                    {highlighted_passage}
        """

            if proper_nouns:
                html_content += f"""
                        <div class=\"proper-nouns\">
                            <div class=\"proper-noun-header\">Proper Nouns:</div>
            """

                for noun in sorted(proper_nouns):
                    html_content += f"""
                            <span class=\"proper-noun-tag\">{html.escape(noun)}</span>
                """

                html_content += """
                        </div>
                """

            html_content += """
                   </div>
        """

            if translation and not pd.isna(translation):
                html_content += f"""
                    <div class=\"english-translation\">
                        {translation}
                    </div>
            """

            html_content += """
            </div>
        </div>
        """

        html_content += f"""
            <footer>
                Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")} from the PostgreSQL database
            </footer>
        </div>
    </body>
    </html>
    """

        filename = f"{chapter.replace('.', '_')}.html"
        with open(os.path.join(skeptic_dir, filename), 'w', encoding='utf-8') as f:
            f.write(html_content)

    # Create index page linking to chapters
    index_content = f"""<!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>{title} - Skepticism Analysis</title>
        <link rel=\"stylesheet\" href=\"../css/style.css\">
    </head>
    <body>
        <header>
            <h1>{title}</h1>
            <p>Analysis of Skepticism in Pausanias</p>
        </header>

        {_site_nav("../", "annotations")}

        <div class=\"container\">
            <h2>Chapters</h2>
            <ul>
    """

    for chapter in chapters:
        filename = f"{chapter.replace('.', '_')}.html"
        index_content += f"<li><a href=\"{filename}\">Chapter {chapter}</a></li>\n"

    index_content += """
            </ul>
            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """ from the PostgreSQL database
            </footer>
        </div>
    </body>
    </html>
    """

    with open(os.path.join(skeptic_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_content)

    write_redirect_page(output_dir, "skepticism.html", "skepticism/index.html", "Skepticism Analysis")

def generate_mythic_words_page(mythic_predictors, output_dir, title, metrics=None, simplified_predictors=None, simplified_metrics=None):
    """Generate a page showing words and phrases that predict mythic/historical content."""

    # Split into mythic and historical predictors
    mythic_words = mythic_predictors[mythic_predictors['is_mythic'] == 1].sort_values('coefficient', ascending=False)
    historical_words = mythic_predictors[mythic_predictors['is_mythic'] == 0].sort_values('coefficient', ascending=True)

    html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Mythic Predictors</title>
        <link rel="stylesheet" href="css/style.css">
    </head>
    <body>
        <header>
            <h1>{title}</h1>
            <p>Words and Phrases that Predict Mythic vs. Historical Content</p>
        </header>

        {_site_nav("", "analysis")}

        <div class="container">
            {format_classification_metrics(metrics, 'Historical', 'Mythic')}

            <h2>Predictors of Mythic Content</h2>
            <p>These words and phrases are most strongly associated with mythic content in Pausanias.</p>
    """

    html_content += render_predictor_table(
        "mythic-positive-table",
        mythic_words,
        "mythic-word",
        "Mythic Count",
        "Non-mythic Count",
        "mythic_count",
        "non_mythic_count",
        coefficient_direction="desc",
    )

    html_content += """
            <h2>Predictors of Historical Content</h2>
            <p>These words and phrases are most strongly associated with historical content in Pausanias.</p>
    """
    html_content += render_predictor_table(
        "mythic-negative-table",
        historical_words,
        "historical-word",
        "Mythic Count",
        "Non-mythic Count",
        "mythic_count",
        "non_mythic_count",
        coefficient_direction="asc",
    )
    html_content += render_simplified_model_section(
        simplified_predictors,
        simplified_metrics,
        metrics,
        "Historical",
        "Mythic",
    )

    html_content += """
            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """ from the PostgreSQL database
            </footer>
        </div>
""" + PREDICTOR_TABLE_SORT_SCRIPT + """
    </body>
    </html>
    """
    
    # Write the file
    with open(os.path.join(output_dir, 'mythic_words.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

def generate_skeptic_words_page(skeptic_predictors, output_dir, title, metrics=None, simplified_predictors=None, simplified_metrics=None):
    """Generate a page showing words and phrases that predict skeptical/non-skeptical content."""

    # Split into skeptical and non-skeptical predictors
    skeptical_words = skeptic_predictors[skeptic_predictors['is_skeptical'] == 1].sort_values('coefficient', ascending=False)
    non_skeptical_words = skeptic_predictors[skeptic_predictors['is_skeptical'] == 0].sort_values('coefficient', ascending=True)

    html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Skepticism Predictors</title>
        <link rel="stylesheet" href="css/style.css">
    </head>
    <body>
        <header>
            <h1>{title}</h1>
            <p>Words and Phrases that Predict Skeptical vs. Non-skeptical Content</p>
        </header>

        {_site_nav("", "analysis")}

        <div class="container">
            {format_classification_metrics(metrics, 'Non-skeptical', 'Skeptical')}

            <h2>Predictors of Skeptical Content</h2>
            <p>These words and phrases are most strongly associated with skeptical content in Pausanias.</p>
    """
    html_content += render_predictor_table(
        "skeptic-positive-table",
        skeptical_words,
        "skeptical-word",
        "Skeptical Count",
        "Non-skeptical Count",
        "skeptical_count",
        "non_skeptical_count",
        coefficient_direction="desc",
    )

    html_content += """
            <h2>Predictors of Non-skeptical Content</h2>
            <p>These words and phrases are most strongly associated with non-skeptical content in Pausanias.</p>
    """
    html_content += render_predictor_table(
        "skeptic-negative-table",
        non_skeptical_words,
        "non-skeptical-word",
        "Skeptical Count",
        "Non-skeptical Count",
        "skeptical_count",
        "non_skeptical_count",
        coefficient_direction="asc",
    )
    html_content += render_simplified_model_section(
        simplified_predictors,
        simplified_metrics,
        metrics,
        "Non-skeptical",
        "Skeptical",
    )

    html_content += """
            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """ from the PostgreSQL database
            </footer>
        </div>
""" + PREDICTOR_TABLE_SORT_SCRIPT + """
    </body>
    </html>
    """
    
    # Write the file
    with open(os.path.join(output_dir, 'skeptic_words.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)


def generate_sentence_mythic_words_page(mythic_predictors, output_dir, title, metrics=None, simplified_predictors=None, simplified_metrics=None):
    """Generate a page showing sentence-level predictors of mythic/historical content."""

    mythic_words = mythic_predictors[mythic_predictors['is_mythic'] == 1].sort_values('coefficient', ascending=False)
    historical_words = mythic_predictors[mythic_predictors['is_mythic'] == 0].sort_values('coefficient', ascending=True)

    html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Sentence Mythic Predictors</title>
        <link rel="stylesheet" href="css/style.css">
    </head>
    <body>
        <header>
            <h1>{title}</h1>
            <p>Sentence-level words and phrases that predict mythic vs. historical content</p>
        </header>

        {_site_nav("", "analysis")}

        <div class="container">
            {format_classification_metrics(metrics, 'Historical', 'Mythic')}

            <h2>Sentence Predictors of Mythic Content</h2>
    """
    html_content += render_predictor_table(
        "sentence-mythic-positive-table",
        mythic_words,
        "mythic-word",
        "Mythic Count",
        "Non-mythic Count",
        "mythic_count",
        "non_mythic_count",
        coefficient_direction="desc",
    )

    html_content += """
            <h2>Sentence Predictors of Historical Content</h2>
    """
    html_content += render_predictor_table(
        "sentence-mythic-negative-table",
        historical_words,
        "historical-word",
        "Mythic Count",
        "Non-mythic Count",
        "mythic_count",
        "non_mythic_count",
        coefficient_direction="asc",
    )
    html_content += render_simplified_model_section(
        simplified_predictors,
        simplified_metrics,
        metrics,
        "Historical",
        "Mythic",
    )

    html_content += """
            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """ from the PostgreSQL database
            </footer>
        </div>
""" + PREDICTOR_TABLE_SORT_SCRIPT + """
    </body>
    </html>
    """

    with open(os.path.join(output_dir, 'sentence_mythic_words.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)


def generate_sentence_skeptic_words_page(skeptic_predictors, output_dir, title, metrics=None, simplified_predictors=None, simplified_metrics=None):
    """Generate a page showing sentence-level predictors of skepticism."""

    skeptical_words = skeptic_predictors[skeptic_predictors['is_skeptical'] == 1].sort_values('coefficient', ascending=False)
    non_skeptical_words = skeptic_predictors[skeptic_predictors['is_skeptical'] == 0].sort_values('coefficient', ascending=True)

    html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Sentence Skeptic Predictors</title>
        <link rel="stylesheet" href="css/style.css">
    </head>
    <body>
        <header>
            <h1>{title}</h1>
            <p>Sentence-level words and phrases that predict skepticism vs. non-skepticism</p>
        </header>

        {_site_nav("", "analysis")}

        <div class="container">
            {format_classification_metrics(metrics, 'Non-skeptical', 'Skeptical')}

            <h2>Sentence Predictors of Skeptical Content</h2>
    """
    html_content += render_predictor_table(
        "sentence-skeptic-positive-table",
        skeptical_words,
        "skeptical-word",
        "Skeptical Count",
        "Non-skeptical Count",
        "skeptical_count",
        "non_skeptical_count",
        coefficient_direction="desc",
    )

    html_content += """
            <h2>Sentence Predictors of Non-skeptical Content</h2>
    """
    html_content += render_predictor_table(
        "sentence-skeptic-negative-table",
        non_skeptical_words,
        "non-skeptical-word",
        "Skeptical Count",
        "Non-skeptical Count",
        "skeptical_count",
        "non_skeptical_count",
        coefficient_direction="asc",
    )
    html_content += render_simplified_model_section(
        simplified_predictors,
        simplified_metrics,
        metrics,
        "Non-skeptical",
        "Skeptical",
    )

    html_content += """
            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """ from the PostgreSQL database
            </footer>
        </div>
""" + PREDICTOR_TABLE_SORT_SCRIPT + """
    </body>
    </html>
    """

    with open(os.path.join(output_dir, 'sentence_skeptic_words.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)


def generate_sentences_page(sentences_df, output_dir, title):
    """Generate pages listing Greek passages split into sentences, grouped by chapter."""

    sentences_df = sentences_df.copy()
    sentences_df["chapter"] = sentences_df["passage_id"].apply(lambda pid: ".".join(pid.split(".")[:2]))
    chapters = sorted(
        sentences_df["chapter"].unique(),
        key=lambda c: [int(p) for p in c.split(".")],
    )

    sentences_dir = os.path.join(output_dir, "sentences")
    os.makedirs(sentences_dir, exist_ok=True)

    # Create chapter pages
    for chapter in chapters:
        chapter_df = sentences_df[sentences_df["chapter"] == chapter]
        html_content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>{title} - Sentences {chapter}</title>
    <link rel=\"stylesheet\" href=\"../css/style.css\">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Greek passages split into sentences with English translation</p>
    </header>

    {_site_nav("../", "annotations")}

    <div class=\"container\">
        <h2>Chapter {chapter}</h2>
        <table class=\"sentences-table\">
            <thead>
                <tr>
                    <th>Passage</th>
                    <th>Sentence</th>
                    <th>Greek</th>
                    <th>English</th>
                    <th>Era</th>
                    <th>Skepticism</th>
                </tr>
            </thead>
            <tbody>
"""

        for _, row in chapter_df.iterrows():
            if pd.isna(row["references_mythic_era"]):
                era = "?"
            else:
                era = "Mythic" if row["references_mythic_era"] else "Historical"

            if pd.isna(row["expresses_scepticism"]):
                sceptic = "?"
            else:
                sceptic = (
                    "Skeptical" if row["expresses_scepticism"] else "Not Skeptical"
                )

            html_content += f"""
                <tr>
                    <td>{html.escape(row['passage_id'])}</td>
                    <td>{row['sentence_number']}</td>
                    <td>{html.escape(row['sentence'])}</td>
                    <td>{html.escape(row['english_sentence'])}</td>
                    <td>{era}</td>
                    <td>{sceptic}</td>
                </tr>
"""

        html_content += f"""
            </tbody>
        </table>

        <footer>
            Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")} from the PostgreSQL database
        </footer>
    </div>
</body>
</html>
"""

        filename = f"{chapter.replace('.', '_')}.html"
        with open(os.path.join(sentences_dir, filename), "w", encoding="utf-8") as f:
            f.write(html_content)

    # Create index page linking to chapters
    index_content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>{title} - Sentences</title>
    <link rel=\"stylesheet\" href=\"../css/style.css\">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Greek passages split into sentences with English translation</p>
    </header>

    {_site_nav("../", "annotations")}

    <div class=\"container\">
        <h2>Chapters</h2>
        <ul>
"""

    for chapter in chapters:
        filename = f"{chapter.replace('.', '_')}.html"
        index_content += f"            <li><a href=\"{filename}\">Chapter {chapter}</a></li>\n"

    index_content += f"""
        </ul>
        <footer>
            Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")} from the PostgreSQL database
        </footer>
    </div>
</body>
</html>
"""

    with open(os.path.join(sentences_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_content)

    write_redirect_page(output_dir, "sentences.html", "sentences/index.html", "Sentences")


def generate_map_page(map_data, output_dir, title):
    """Generate an interactive Leaflet.js map showing places mentioned in Pausanias."""

    map_dir = os.path.join(output_dir, 'map')
    os.makedirs(map_dir, exist_ok=True)

    # Write map data as JSON
    with open(os.path.join(map_dir, 'map_data.json'), 'w', encoding='utf-8') as f:
        json.dump(map_data, f, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Place Map</title>
    <link rel="stylesheet" href="../css/style.css">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        #map {{
            width: 100%;
            height: 600px;
            border-radius: 5px;
            border: 2px solid #5c5142;
            margin: 20px 0;
        }}
        .map-popup .popup-title {{
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 4px;
        }}
        .map-popup .popup-greek {{
            font-style: italic;
            color: #555;
            margin-bottom: 6px;
        }}
        .map-popup .popup-passages {{
            margin-top: 6px;
            font-size: 0.9em;
        }}
        .map-popup .popup-passages a {{
            margin-right: 6px;
            color: #5c5142;
        }}
        .map-popup .popup-wikidata {{
            margin-top: 4px;
            font-size: 0.8em;
        }}
        .map-stats {{
            background-color: #eee9e3;
            padding: 10px 15px;
            border-radius: 5px;
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Places mentioned in Pausanias' Description of Greece</p>
    </header>

    {_site_nav("../", "places")}

    <div class="container" style="max-width: 1000px;">
        <h2>Place Map</h2>
        <div class="map-stats" id="map-stats"></div>
        <div id="map"></div>

        <footer>
            Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")} from the PostgreSQL database
        </footer>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        // Initialize map centered on Greece
        const map = L.map('map').setView([38.0, 23.5], 6);

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 18
        }}).addTo(map);

        // Load and display place data
        fetch('map_data.json')
            .then(response => response.json())
            .then(data => {{
                document.getElementById('map-stats').innerHTML =
                    `Showing <strong>${{data.length}}</strong> places with known coordinates.`;

                data.forEach(place => {{
                    // Build passage links
                    const passageLinks = place.passages.map(pid => {{
                        const parts = pid.split('.');
                        return `<a href="../translation/${{parts[0]}}/${{parts[1]}}/${{parts[2]}}.html">${{pid}}</a>`;
                    }}).join(' ');

                    // Build popup content
                    let popup = `<div class="map-popup">`;
                    popup += `<div class="popup-title">${{place.english}}</div>`;
                    popup += `<div class="popup-greek">${{place.reference_form}}</div>`;
                    if (place.passages.length > 0) {{
                        popup += `<div class="popup-passages">Passages: ${{passageLinks}}</div>`;
                    }}
                    if (place.qid) {{
                        popup += `<div class="popup-wikidata"><a href="https://www.wikidata.org/wiki/${{place.qid}}" target="_blank">${{place.qid}}</a></div>`;
                    }}
                    popup += `</div>`;

                    L.marker([place.lat, place.lon])
                        .addTo(map)
                        .bindPopup(popup);
                }});

                // Fit map to markers if we have data
                if (data.length > 0) {{
                    const bounds = L.latLngBounds(data.map(p => [p.lat, p.lon]));
                    map.fitBounds(bounds, {{ padding: [30, 30] }});
                }}
            }})
            .catch(err => {{
                document.getElementById('map-stats').innerHTML =
                    'No place coordinate data available yet. Run <code>python link_wikidata.py</code> to populate.';
            }});
    </script>
</body>
</html>
"""

    with open(os.path.join(map_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Map page generated with {len(map_data)} places.")


def _format_place_label(place):
    """Format a place label using English if available, with Greek reference in parentheses."""
    english = place.get("english") or ""
    ref_form = place.get("reference_form") or ""
    if english and ref_form and english != ref_form:
        return f"{html.escape(english)} ({html.escape(ref_form)})"
    return html.escape(english or ref_form or "Unknown")


def generate_place_pairs_page(place_pairs, output_dir, title):
    """Generate a page listing place pairs mentioned in the same passage with distances."""
    place_pairs_dir = os.path.join(output_dir, "place_pairs")
    os.makedirs(place_pairs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
    total_pairs = len(place_pairs)
    total_passages = len({p["passage_id"] for p in place_pairs}) if place_pairs else 0

    if not place_pairs:
        rows_html = "<p>No place pairs with coordinates found yet. Run <code>python link_wikidata.py</code> to populate coordinates.</p>"
    else:
        rows = []
        for pair in place_pairs:
            passage_id = pair["passage_id"]
            parts = passage_id.split(".")
            passage_href = None
            if len(parts) == 3:
                passage_href = f"../translation/{parts[0]}/{parts[1]}/{parts[2]}.html"

            distance = f"{pair['distance_km']:.1f} km"
            place_a = _format_place_label(pair["place_a"])
            place_b = _format_place_label(pair["place_b"])
            passage_link = (
                f'<a href="{passage_href}">{passage_id}</a>' if passage_href else html.escape(passage_id)
            )
            rows.append(f"""
                <tr>
                    <td>{distance}</td>
                    <td>{place_a}</td>
                    <td>{place_b}</td>
                    <td>{passage_link}</td>
                </tr>
            """)

        rows_html = f"""
        <p>Found <strong>{total_pairs:,}</strong> place pairs across <strong>{total_passages:,}</strong> passages.</p>
        <table class="predictor-table">
            <thead>
                <tr>
                    <th>Distance</th>
                    <th>Place A</th>
                    <th>Place B</th>
                    <th>Passage</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Geographic Surprise</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Geographic surprise: distant places mentioned together in the same passage</p>
    </header>

    {_site_nav("../", "places")}

    <div class="container" style="max-width: 1000px;">
        <h2>Geographic Surprise / Place Pairs</h2>
        {rows_html}

        <footer>
            Generated on {timestamp} from the PostgreSQL database
        </footer>
    </div>
</body>
</html>
"""

    with open(os.path.join(place_pairs_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Place pairs page generated with {total_pairs} pairs.")


def _translation_nav(prefix, active=None):
    """Generate compact nav HTML for pages that historically used translation nav."""
    return _site_nav(prefix, active)


def _format_residual(value):
    return f"{float(value):+.1f}"


def _format_optional_number(value, digits=3, signed=False):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(numeric):
        return "n/a"
    sign = "+" if signed else ""
    return f"{numeric:{sign}.{digits}f}"


def _format_p_value(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(numeric):
        return "n/a"
    if numeric < 0.001:
        return "< 0.001"
    return f"{numeric:.3f}"


def _translation_passage_link(passage_id):
    parts = str(passage_id).split(".")
    if len(parts) != 3:
        return html.escape(str(passage_id))
    href = f"../translation/{parts[0]}/{parts[1]}/{parts[2]}.html"
    return f'<a href="{href}">{html.escape(str(passage_id))}</a>'


def _short_text(text, limit=180):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _render_translation_length_predictor_table(
    rows,
    empty_message,
    phrase_label="Greek Word/Phrase",
    translation_label="English",
    show_translation=True,
):
    if rows is None or len(rows) == 0:
        return f"<p>{html.escape(empty_message)}</p>"

    body = []
    for _, row in rows.iterrows():
        english = row.get("english_translation", "")
        translation_cell = (
            f"<td>{html.escape(str(english or ''))}</td>" if show_translation else ""
        )
        body.append(f"""
            <tr>
                <td>{html.escape(str(row["phrase"]))}</td>
                {translation_cell}
                <td class="num">{float(row["coefficient"]):+.3f}</td>
                <td class="num">{int(row["passage_count"])}</td>
                <td class="num">{_format_residual(row["mean_residual_with_term"])}</td>
                <td class="num">{_format_residual(row["mean_residual_without_term"])}</td>
            </tr>
        """)

    return f"""
        <table class="predictor-table translation-length-table">
            <thead>
                <tr>
                    <th>{html.escape(phrase_label)}</th>
                    {f"<th>{html.escape(translation_label)}</th>" if show_translation else ""}
                    <th>Coefficient</th>
                    <th>Passages</th>
                    <th>Mean Residual With Term</th>
                    <th>Mean Residual Without Term</th>
                </tr>
            </thead>
            <tbody>
                {''.join(body)}
            </tbody>
        </table>
    """


def _render_translation_length_passage_table(rows):
    if rows is None or len(rows) == 0:
        return "<p>No passage residuals available.</p>"

    body = []
    for _, row in rows.iterrows():
        body.append(f"""
            <tr>
                <td>{_translation_passage_link(row["id"])}</td>
                <td class="num">{int(row["greek_word_count"])}</td>
                <td class="num">{int(row["english_word_count"])}</td>
                <td class="num">{float(row["expected_english_word_count"]):.1f}</td>
                <td class="num">{_format_residual(row["length_residual"])}</td>
                <td>{html.escape(_short_text(row["english_translation"]))}</td>
            </tr>
        """)

    return f"""
        <table class="predictor-table translation-length-table">
            <thead>
                <tr>
                    <th>Passage</th>
                    <th>Greek Words</th>
                    <th>English Words</th>
                    <th>Expected English</th>
                    <th>Residual</th>
                    <th>English Snippet</th>
                </tr>
            </thead>
            <tbody>
                {''.join(body)}
            </tbody>
        </table>
    """


def _nice_chart_ticks(min_value, max_value, count=6):
    if not math.isfinite(min_value) or not math.isfinite(max_value):
        return []
    if max_value <= min_value:
        return [min_value]

    raw_step = (max_value - min_value) / max(1, count - 1)
    magnitude = 10 ** math.floor(math.log10(raw_step))
    step = 10 * magnitude
    for candidate in (1, 2, 5, 10):
        nice_step = candidate * magnitude
        if raw_step <= nice_step:
            step = nice_step
            break

    start = math.ceil(min_value / step) * step
    ticks = []
    current = start
    while current <= max_value + (step * 0.5):
        ticks.append(current)
        current += step
    return ticks


def _tick_label(value):
    if abs(value - round(value)) < 0.001:
        return f"{int(round(value))}"
    return f"{value:.1f}"


def _render_translation_length_relationship_graph(points, metrics):
    if points is None or len(points) == 0:
        return "<p>No length relationship data points are available.</p>"

    plot_points = points.copy()
    plot_points = plot_points.dropna(subset=["greek_word_count", "english_word_count"])
    if len(plot_points) == 0:
        return "<p>No length relationship data points are available.</p>"

    plot_points["greek_word_count"] = plot_points["greek_word_count"].astype(float)
    plot_points["english_word_count"] = plot_points["english_word_count"].astype(float)
    grouped = (
        plot_points.groupby(["greek_word_count", "english_word_count"], as_index=False)
        .agg(passage_count=("id", "count"))
        .sort_values(["greek_word_count", "english_word_count"])
    )

    width = 920
    height = 500
    left = 72
    right = 30
    top = 36
    bottom = 64
    plot_width = width - left - right
    plot_height = height - top - bottom

    slope = float(metrics.get("length_slope", 0.0))
    intercept = float(metrics.get("length_intercept", 0.0))
    x_values = plot_points["greek_word_count"].tolist()
    y_values = plot_points["english_word_count"].tolist()
    x_min = min(0.0, min(x_values))
    x_max = max(x_values)
    if x_max <= x_min:
        x_min = max(0.0, x_min - 1.0)
        x_max = x_max + 1.0

    line_y_min = intercept + slope * x_min
    line_y_max = intercept + slope * x_max
    y_min = min(0.0, min(y_values), line_y_min, line_y_max)
    y_max = max(y_values + [line_y_min, line_y_max])
    if y_max <= y_min:
        y_min = max(0.0, y_min - 1.0)
        y_max = y_max + 1.0
    y_padding = (y_max - y_min) * 0.08
    y_min = max(0.0, y_min - y_padding)
    y_max = y_max + y_padding

    def x_coord(value):
        return left + ((value - x_min) / (x_max - x_min)) * plot_width

    def y_coord(value):
        return top + ((y_max - value) / (y_max - y_min)) * plot_height

    x_ticks = _nice_chart_ticks(x_min, x_max)
    y_ticks = _nice_chart_ticks(y_min, y_max)
    grid_lines = []
    for tick in x_ticks:
        x = x_coord(tick)
        grid_lines.append(f'<line class="chart-grid" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height - bottom}" />')
        grid_lines.append(f'<text class="chart-tick" x="{x:.1f}" y="{height - bottom + 22}" text-anchor="middle">{html.escape(_tick_label(tick))}</text>')
    for tick in y_ticks:
        y = y_coord(tick)
        grid_lines.append(f'<line class="chart-grid" x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" />')
        grid_lines.append(f'<text class="chart-tick" x="{left - 12}" y="{y + 4:.1f}" text-anchor="end">{html.escape(_tick_label(tick))}</text>')

    max_count = max(grouped["passage_count"])
    circles = []
    for _, row in grouped.iterrows():
        count = int(row["passage_count"])
        radius = 3.0 + (5.0 * math.sqrt(count) / math.sqrt(max_count))
        x = x_coord(float(row["greek_word_count"]))
        y = y_coord(float(row["english_word_count"]))
        title = (
            f"{count} passage{'s' if count != 1 else ''}: "
            f"{int(row['greek_word_count'])} Greek words, "
            f"{int(row['english_word_count'])} English words"
        )
        circles.append(f"""
            <circle class="length-point" cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}">
                <title>{html.escape(title)}</title>
            </circle>
        """)

    line_x1 = x_coord(x_min)
    line_x2 = x_coord(x_max)
    line_y1 = y_coord(line_y_min)
    line_y2 = y_coord(line_y_max)
    equation = f"English = {intercept:.2f} + {slope:.2f} * Greek"
    r2 = _format_optional_number(metrics.get("length_r2"), 3)
    slope_p = _format_p_value(metrics.get("length_slope_p_value"))

    coefficient_table = f"""
        <table class="predictor-table translation-length-coefficients">
            <thead>
                <tr>
                    <th>Term</th>
                    <th>Coefficient</th>
                    <th>Std. Error</th>
                    <th>p-value</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Intercept</td>
                    <td class="num">{_format_optional_number(metrics.get("length_intercept"), 3, signed=True)}</td>
                    <td class="num">{_format_optional_number(metrics.get("length_intercept_std_error"), 3)}</td>
                    <td class="num">{html.escape(_format_p_value(metrics.get("length_intercept_p_value")))}</td>
                </tr>
                <tr>
                    <td>Greek word count</td>
                    <td class="num">{_format_optional_number(metrics.get("length_slope"), 3, signed=True)}</td>
                    <td class="num">{_format_optional_number(metrics.get("length_slope_std_error"), 3)}</td>
                    <td class="num">{html.escape(_format_p_value(metrics.get("length_slope_p_value")))}</td>
                </tr>
            </tbody>
        </table>
    """

    return f"""
        <section class="translation-length-relationship">
            <h2>English Length vs. Greek Length</h2>
            <p>Each point is a translated passage, grouped when multiple passages have the same Greek and English word counts. The fitted line is the baseline model used before calculating residuals.</p>
            <div class="translation-length-chart" role="img" aria-label="Scatter plot of English translation length by Greek source length">
                <svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
                    <rect class="chart-background" x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" />
                    {''.join(grid_lines)}
                    <line class="chart-axis" x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" />
                    <line class="chart-axis" x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" />
                    <line class="regression-line" x1="{line_x1:.1f}" y1="{line_y1:.1f}" x2="{line_x2:.1f}" y2="{line_y2:.1f}" />
                    {''.join(circles)}
                    <text class="chart-axis-label" x="{left + plot_width / 2:.1f}" y="{height - 18}" text-anchor="middle">Greek source words</text>
                    <text class="chart-axis-label" transform="translate(20 {top + plot_height / 2:.1f}) rotate(-90)" text-anchor="middle">English translation words</text>
                    <g class="chart-stat-panel">
                        <rect x="{width - 315}" y="{top + 12}" width="275" height="76" rx="4" />
                        <text x="{width - 298}" y="{top + 38}">{html.escape(equation)}</text>
                        <text x="{width - 298}" y="{top + 60}">R^2 = {html.escape(r2)}</text>
                        <text x="{width - 298}" y="{top + 82}">slope p = {html.escape(slope_p)}</text>
                    </g>
                </svg>
            </div>
            {coefficient_table}
        </section>
    """


def _format_correlation_stat(stat):
    if not stat:
        return "n/a", "n/a"
    return (
        _format_optional_number(stat.get("coefficient"), 3, signed=True),
        _format_p_value(stat.get("p_value")),
    )


def _plotly_safe_number(value, digits=6):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return round(numeric, digits)


def _render_translation_coefficient_scatter(points, *, y_column, y_label, title, chart_id, absolute_view=False):
    if points is None or len(points) == 0:
        return "<p>No matched coefficient points are available.</p>"

    plot_points = points.copy()
    plot_points = plot_points.dropna(subset=["translation_residual_coefficient", y_column])
    if len(plot_points) == 0:
        return "<p>No matched coefficient points are available.</p>"

    plot_points["translation_residual_coefficient"] = plot_points[
        "translation_residual_coefficient"
    ].astype(float)
    plot_points[y_column] = plot_points[y_column].astype(float)

    traces = []
    color_by_direction = {
        "mythic": "#9a3f31",
        "historical": "#316a84",
    }
    for direction, direction_points in plot_points.groupby("classification_direction"):
        custom_data = []
        for _, row in direction_points.iterrows():
            custom_data.append(
                [
                    str(row.get("phrase", "")),
                    str(row.get("english_translation", "") or ""),
                    str(row.get("translation_direction", "")).title(),
                    _plotly_safe_number(row.get("translation_residual_coefficient"), 3),
                    _plotly_safe_number(row.get("mythic_log_odds_coefficient"), 3),
                    int(row.get("translation_passage_count", 0) or 0),
                    int(row.get("mythic_count", 0) or 0),
                    int(row.get("historical_count", 0) or 0),
                    _plotly_safe_number(row.get("mythic_q_value"), 6),
                ]
            )
        traces.append(
            {
                "type": "scattergl",
                "mode": "markers",
                "name": str(direction).title(),
                "x": [
                    _plotly_safe_number(value)
                    for value in direction_points["translation_residual_coefficient"]
                ],
                "y": [
                    _plotly_safe_number(value)
                    for value in direction_points[y_column]
                ],
                "customdata": custom_data,
                "marker": {
                    "color": color_by_direction.get(str(direction), "#75685a"),
                    "size": 8,
                    "opacity": 0.72,
                    "line": {"color": "rgba(40, 35, 30, 0.55)", "width": 0.7},
                },
                "hovertemplate": (
                    "<b>%{customdata[0]}</b><br>"
                    "%{customdata[1]}<br>"
                    "Translation direction: %{customdata[2]}<br>"
                    "Residual coefficient: %{customdata[3]:+.3f}<br>"
                    "Myth/history coefficient: %{customdata[4]:+.3f}<br>"
                    "Translated passages: %{customdata[5]}<br>"
                    "Mythic / historical counts: %{customdata[6]} / %{customdata[7]}<br>"
                    "q-value: %{customdata[8]}<extra></extra>"
                ),
            }
        )

    layout = {
        "title": {"text": title, "font": {"size": 16}},
        "height": 520,
        "margin": {"l": 76, "r": 26, "t": 52, "b": 70},
        "plot_bgcolor": "#fbfaf7",
        "paper_bgcolor": "#fffdf8",
        "legend": {"orientation": "h", "x": 0, "y": 1.08},
        "xaxis": {
            "title": "Translation-length residual coefficient",
            "zeroline": True,
            "zerolinecolor": "#75685a",
            "gridcolor": "#ded7cc",
        },
        "yaxis": {
            "title": y_label,
            "zeroline": not absolute_view,
            "zerolinecolor": "#75685a",
            "gridcolor": "#ded7cc",
            **({"rangemode": "tozero"} if absolute_view else {}),
        },
        "hovermode": "closest",
    }
    config = {
        "responsive": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    }
    script = f"""
        <script>
        Plotly.newPlot(
            {json.dumps(chart_id)},
            {json.dumps(traces, ensure_ascii=False)},
            {json.dumps(layout, ensure_ascii=False)},
            {json.dumps(config)}
        );
        </script>
    """

    return f"""
        <div class="translation-coefficient-chart" role="img" aria-label="{html.escape(title)}">
            <div id="{html.escape(chart_id)}" class="plotly-chart"></div>
            {script}
        </div>
    """


def _render_translation_mythic_relationship_table(points):
    if points is None or len(points) == 0:
        return "<p>No matched terms are available.</p>"

    rows = []
    for _, row in points.iterrows():
        english = row.get("english_translation", "")
        translation_cell = f"<td>{html.escape(str(english or ''))}</td>"
        rows.append(f"""
            <tr>
                <td>{html.escape(str(row["phrase"]))}</td>
                {translation_cell}
                <td>{html.escape(str(row["translation_direction"]).title())}</td>
                <td class="num">{float(row["translation_residual_coefficient"]):+.3f}</td>
                <td class="num">{float(row["mythic_log_odds_coefficient"]):+.3f}</td>
                <td>{html.escape(str(row["classification_direction"]).title())}</td>
                <td class="num">{int(row["mythic_count"])}</td>
                <td class="num">{int(row["historical_count"])}</td>
                <td class="num">{html.escape(_format_p_value(row.get("mythic_q_value")))}</td>
            </tr>
        """)

    return f"""
        <table class="predictor-table translation-length-table">
            <thead>
                <tr>
                    <th>Greek Word/Phrase</th>
                    <th>Translation</th>
                    <th>Length Direction</th>
                    <th>Residual Coefficient</th>
                    <th>Myth/History Coefficient</th>
                    <th>Class Direction</th>
                    <th>Mythic Count</th>
                    <th>Historical Count</th>
                    <th>q-value</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_translation_mythic_coefficient_relationship(relationship):
    if not relationship or not relationship.get("available"):
        message = (
            relationship.get("message", "No translation/coefficient relationship is available.")
            if relationship
            else "No translation/coefficient relationship is available."
        )
        return f"""
            <section class="translation-coefficient-relationship">
                <h2>Residual Terms vs. Mythic/Historical Coefficients</h2>
                <p>{html.escape(message)}</p>
            </section>
        """

    points = relationship.get("points")
    metrics = relationship.get("metrics", {})
    linear_pearson, linear_pearson_p = _format_correlation_stat(metrics.get("linear_pearson"))
    linear_spearman, linear_spearman_p = _format_correlation_stat(metrics.get("linear_spearman"))
    extremity_pearson, extremity_pearson_p = _format_correlation_stat(metrics.get("extremity_pearson"))
    extremity_spearman, extremity_spearman_p = _format_correlation_stat(metrics.get("extremity_spearman"))
    quadratic_abs_r2 = _format_optional_number(metrics.get("quadratic_abs_r2"), 3)

    signed_chart = _render_translation_coefficient_scatter(
        points,
        y_column="mythic_log_odds_coefficient",
        y_label="Mythic/historical log-odds coefficient",
        title="Signed Mythic vs. Historical Direction",
        chart_id="translation-mythic-signed-scatter",
    )
    extremity_chart = _render_translation_coefficient_scatter(
        points,
        y_column="abs_mythic_log_odds_coefficient",
        y_label="Classification strength |log-odds|",
        title="Coefficient Extremity",
        chart_id="translation-mythic-extremity-scatter",
        absolute_view=True,
    )
    terms_table = _render_translation_mythic_relationship_table(points)

    return f"""
        <section class="translation-coefficient-relationship">
            <h2>Residual Terms vs. Mythic/Historical Coefficients</h2>
            <p>This matches every Greek residual term from the translation-length model against the main lemma model's mythic/historical coefficients. Positive myth/history coefficients point toward mythic narration; negative coefficients point toward historical narration.</p>
            <div class="translation-length-metrics">
                <div><strong>{metrics.get("matched_term_count", 0):,}</strong><span>matched residual terms</span></div>
                <div><strong>{metrics.get("residual_term_count", 0):,}</strong><span>residual terms checked</span></div>
                <div><strong>{linear_pearson}</strong><span>linear Pearson r, p = {linear_pearson_p}</span></div>
                <div><strong>{linear_spearman}</strong><span>linear Spearman rho, p = {linear_spearman_p}</span></div>
                <div><strong>{extremity_pearson}</strong><span>|residual| vs |coefficient| Pearson r, p = {extremity_pearson_p}</span></div>
                <div><strong>{extremity_spearman}</strong><span>|residual| vs |coefficient| Spearman rho, p = {extremity_spearman_p}</span></div>
                <div><strong>{quadratic_abs_r2}</strong><span>quadratic R2 for coefficient extremity</span></div>
            </div>
            <div class="coefficient-chart-grid">
                {signed_chart}
                {extremity_chart}
            </div>
            <h3>Matched Terms</h3>
            {terms_table}
        </section>
    """


def _write_translation_mythic_strength_page(analysis, translation_length_dir, title, timestamp):
    relationship = analysis.get("mythic_coefficient_relationship") if analysis else None
    body = _render_translation_mythic_coefficient_relationship(relationship)
    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Residual Length vs. Mythic/Historical Strength</title>
    <link rel="stylesheet" href="../css/style.css">
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        .translation-length-metrics {{
            display: grid;
            gap: 12px;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            margin: 22px 0 30px;
        }}
        .translation-length-metrics div {{
            background: #eee9e3;
            border-radius: 5px;
            padding: 12px;
        }}
        .translation-length-metrics strong {{
            display: block;
            color: #5c5142;
            font-size: 1.4em;
        }}
        .translation-length-metrics span {{
            display: block;
            font-size: 0.9em;
        }}
        .translation-length-table .num {{
            text-align: right;
            white-space: nowrap;
        }}
        .translation-coefficient-relationship {{
            margin: 34px 0;
        }}
        .coefficient-chart-grid {{
            display: grid;
            gap: 18px;
            grid-template-columns: 1fr;
            margin: 20px 0 28px;
        }}
        .translation-coefficient-chart {{
            border: 1px solid #d8d0c5;
            border-radius: 6px;
            padding: 12px;
            overflow-x: auto;
        }}
        .plotly-chart {{
            min-height: 520px;
            min-width: 560px;
            width: 100%;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Translation residuals compared with mythic/historical classifier strength</p>
    </header>
    {_translation_nav("../", "translation_length")}
    <div class="container" style="max-width: 1100px;">
        <p><a href="index.html">Back to Translation Length Analysis</a></p>
        <section class="hub-card">
            <h2>Exploratory Diagnostic</h2>
            <p>This page keeps the residual-length comparison separate from the stronger translation-length results. The linear relationship is weak, but the scatterplots remain useful as a check on whether unexpectedly long or short translated terms align with mythic or historical classifier strength.</p>
        </section>
        {body}
        <footer>
            Generated on {timestamp} from the PostgreSQL database
        </footer>
    </div>
</body>
</html>
"""

    with open(
        os.path.join(translation_length_dir, "mythic_historical_strength.html"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(page_html)

    print("Translation mythic/historical strength page generated.")


def _render_sentence_bucket_summary_table(summary):
    if summary is None or len(summary) == 0:
        return "<p>No sentence bucket summary is available.</p>"

    rows = []
    for _, row in summary.iterrows():
        rows.append(f"""
            <tr>
                <td>{html.escape(str(row.get("label", row.get("bucket", ""))))}</td>
                <td class="num">{int(row.get("sentence_count", 0)):,}</td>
                <td class="num">{_format_optional_number(row.get("mean_greek_word_count"), 1)}</td>
                <td class="num">{_format_optional_number(row.get("mean_english_word_count"), 1)}</td>
                <td class="num">{_format_optional_number(row.get("english_per_greek_word"), 2)}</td>
                <td class="num">{_format_optional_number(row.get("mean_global_residual"), 2, signed=True)}</td>
                <td class="num">{_format_optional_number(row.get("median_global_residual"), 2, signed=True)}</td>
                <td class="num">{_format_optional_number(row.get("global_residual_std"), 2)}</td>
                <td class="num">{_format_optional_number(row.get("bucket_length_slope"), 2)}</td>
                <td class="num">{_format_optional_number(row.get("bucket_length_r2"), 3)}</td>
            </tr>
        """)

    return f"""
        <table class="predictor-table translation-length-table sentence-bucket-table">
            <thead>
                <tr>
                    <th>Bucket</th>
                    <th>Sentences</th>
                    <th>Mean Greek Words</th>
                    <th>Mean English Words</th>
                    <th>English / Greek</th>
                    <th>Mean Residual</th>
                    <th>Median Residual</th>
                    <th>Residual SD</th>
                    <th>Bucket Slope</th>
                    <th>Bucket R2</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_sentence_bucket_predictors(bucket_analyses):
    if not bucket_analyses:
        return ""

    bucket_labels = {
        "mythic": "Mythic",
        "historical": "Historical",
        "other": "Other",
    }
    sections = []
    for bucket, label in bucket_labels.items():
        bucket_result = bucket_analyses.get(bucket)
        if not bucket_result:
            continue
        if not bucket_result.get("available"):
            message = bucket_result.get("message", "No model is available for this bucket.")
            sections.append(f"""
                <section class="sentence-bucket-predictor-block">
                    <h3>{html.escape(label)} Sentence Predictors</h3>
                    <p>{html.escape(message)}</p>
                </section>
            """)
            continue

        metrics = bucket_result.get("metrics", {})
        longer_table = _render_translation_length_predictor_table(
            bucket_result.get("longer_predictors"),
            "No Greek terms had positive residual coefficients in this bucket.",
            phrase_label="Greek Word/Phrase",
        )
        shorter_table = _render_translation_length_predictor_table(
            bucket_result.get("shorter_predictors"),
            "No Greek terms had negative residual coefficients in this bucket.",
            phrase_label="Greek Word/Phrase",
        )
        sections.append(f"""
            <section class="sentence-bucket-predictor-block">
                <h3>{html.escape(label)} Sentence Predictors</h3>
                <p>Within-bucket residual model over {metrics.get("passage_count", 0):,} sentences; length R2 = {_format_optional_number(metrics.get("length_r2"), 3)}, residual SD = {_format_optional_number(metrics.get("residual_std"), 2)}.</p>
                <h4>Longer English</h4>
                {longer_table}
                <h4>Shorter English</h4>
                {shorter_table}
            </section>
        """)

    return "".join(sections)


def _render_sentence_translation_bucket_analysis(bucket_analysis):
    if not bucket_analysis:
        return ""
    if not bucket_analysis.get("available"):
        return f"""
            <section class="sentence-translation-buckets">
                <h2>Sentence Translation Length by Bucket</h2>
                <p>{html.escape(bucket_analysis.get("message", "No sentence bucket analysis is available."))}</p>
            </section>
        """

    metrics = bucket_analysis.get("metrics", {})
    summary_table = _render_sentence_bucket_summary_table(bucket_analysis.get("bucket_summary"))
    predictor_sections = _render_sentence_bucket_predictors(bucket_analysis.get("bucket_analyses"))

    return f"""
        <section class="sentence-translation-buckets">
            <h2>Sentence Translation Length by Bucket</h2>
            <p>This uses the aligned Greek and English sentence table plus the active Greta mythic/historical/other tags. The residual means use one shared sentence-level baseline, so positive values mean that a bucket's English sentences run longer than expected for their Greek sentence lengths.</p>
            <div class="translation-length-metrics">
                <div><strong>{metrics.get("sentence_count", 0):,}</strong><span>tagged sentence translations</span></div>
                <div><strong>{metrics.get("bucket_count", 0):,}</strong><span>buckets compared</span></div>
                <div><strong>{_format_optional_number(metrics.get("length_slope"), 2)}</strong><span>shared English words per Greek word</span></div>
                <div><strong>{_format_optional_number(metrics.get("length_r2"), 3)}</strong><span>shared length model R2</span></div>
                <div><strong>{_format_optional_number(metrics.get("residual_std"), 2)}</strong><span>shared residual SD</span></div>
                <div><strong>{html.escape(str(metrics.get("greek_vocabulary_source") or "surface"))}</strong><span>Greek vocabulary source</span></div>
            </div>
            {summary_table}
            {predictor_sections}
        </section>
    """


def generate_translation_length_page(analysis, output_dir, title):
    """Generate a page for translation length residual predictors."""
    translation_length_dir = os.path.join(output_dir, "translation_length")
    os.makedirs(translation_length_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")

    if not analysis or not analysis.get("available"):
        message = analysis.get("message", "Translation length analysis is not available.") if analysis else "Translation length analysis is not available."
        body = f"""
            <h2>Translation Length Residuals</h2>
            <p>{html.escape(message)}</p>
        """
    else:
        metrics = analysis["metrics"]
        longer_table = _render_translation_length_predictor_table(
            analysis["longer_predictors"],
            "No vocabulary terms had positive residual coefficients.",
            phrase_label="Greek Word/Phrase",
        )
        shorter_table = _render_translation_length_predictor_table(
            analysis["shorter_predictors"],
            "No vocabulary terms had negative residual coefficients.",
            phrase_label="Greek Word/Phrase",
        )
        english_longer_table = _render_translation_length_predictor_table(
            analysis.get("english_longer_predictors"),
            "No English terms had positive residual coefficients.",
            phrase_label="English Word/Phrase",
            show_translation=False,
        )
        english_shorter_table = _render_translation_length_predictor_table(
            analysis.get("english_shorter_predictors"),
            "No English terms had negative residual coefficients.",
            phrase_label="English Word/Phrase",
            show_translation=False,
        )
        longest_table = _render_translation_length_passage_table(analysis["longest_passages"])
        shortest_table = _render_translation_length_passage_table(analysis["shortest_passages"])
        relationship_graph = _render_translation_length_relationship_graph(
            analysis.get("length_points"),
            metrics,
        )
        sentence_bucket_analysis = _render_sentence_translation_bucket_analysis(
            analysis.get("sentence_bucket_analysis")
        )

        body = f"""
            <h2>Translation Length Residuals</h2>
            <p>English word count is first predicted from Greek word count. The residual is actual English length minus expected English length; positive values mark translations that are longer than expected for the Greek passage length.</p>

            <div class="translation-length-metrics">
                <div><strong>{metrics["passage_count"]:,}</strong><span>translated passages</span></div>
                <div><strong>{metrics["feature_count"]:,}</strong><span>Greek terms modeled</span></div>
                <div><strong>{metrics.get("english_feature_count", 0):,}</strong><span>English terms modeled</span></div>
                <div><strong>{metrics["length_slope"]:.2f}</strong><span>English words per Greek word</span></div>
                <div><strong>{metrics["length_r2"]:.3f}</strong><span>length model R2</span></div>
                <div><strong>{metrics["residual_std"]:.1f}</strong><span>residual std. dev.</span></div>
                <div><strong>{metrics["vocabulary_residual_r2"]:.3f}</strong><span>vocabulary residual R2</span></div>
                <div><strong>{metrics.get("english_vocabulary_residual_r2", 0.0):.3f}</strong><span>English residual R2</span></div>
            </div>

            {relationship_graph}

            {sentence_bucket_analysis}

            <h2>Greek Predictors of Longer English</h2>
            <p>These Greek words and phrases are associated with translations that run longer than expected after the length adjustment.</p>
            {longer_table}

            <h2>Greek Predictors of Shorter English</h2>
            <p>These Greek words and phrases are associated with translations that run shorter than expected after the length adjustment.</p>
            {shorter_table}

            <h2>English Terms in Longer Passages</h2>
            <p>These English words and phrases are disproportionately found in passages whose translations are longer than expected.</p>
            {english_longer_table}

            <h2>English Terms in Shorter Passages</h2>
            <p>These English words and phrases are disproportionately found in passages whose translations are shorter than expected.</p>
            {english_shorter_table}

            <h2>Longest Positive Residuals</h2>
            {longest_table}

            <h2>Largest Negative Residuals</h2>
            {shortest_table}
        """

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Translation Length</title>
    <link rel="stylesheet" href="../css/style.css">
    <style>
        .translation-length-metrics {{
            display: grid;
            gap: 12px;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            margin: 22px 0 30px;
        }}
        .translation-length-metrics div {{
            background: #eee9e3;
            border-radius: 5px;
            padding: 12px;
        }}
        .translation-length-metrics strong {{
            display: block;
            color: #5c5142;
            font-size: 1.4em;
        }}
        .translation-length-metrics span {{
            display: block;
            font-size: 0.9em;
        }}
        .translation-length-table .num {{
            text-align: right;
            white-space: nowrap;
        }}
        .translation-length-relationship {{
            margin: 30px 0 34px;
        }}
        .translation-length-chart {{
            border: 1px solid #d8d0c5;
            border-radius: 6px;
            margin: 16px 0;
            overflow-x: auto;
            padding: 10px;
        }}
        .translation-length-chart svg {{
            display: block;
            min-width: 720px;
            width: 100%;
        }}
        .chart-background {{
            fill: #fbfaf7;
        }}
        .chart-grid {{
            stroke: #ded7cc;
            stroke-width: 1;
        }}
        .chart-axis {{
            stroke: #5c5142;
            stroke-width: 1.5;
        }}
        .chart-axis-label,
        .chart-tick {{
            fill: #5c5142;
            font-size: 13px;
        }}
        .regression-line {{
            stroke: #9a3f31;
            stroke-width: 3;
        }}
        .length-point {{
            fill: #316a84;
            fill-opacity: 0.62;
            stroke: #17475a;
            stroke-opacity: 0.75;
            stroke-width: 1;
        }}
        .chart-stat-panel rect {{
            fill: rgba(255, 255, 255, 0.92);
            stroke: #d8d0c5;
        }}
        .chart-stat-panel text {{
            fill: #463d33;
            font-size: 13px;
            font-weight: bold;
        }}
        .translation-length-coefficients {{
            max-width: 680px;
        }}
        .sentence-translation-buckets {{
            margin: 34px 0;
        }}
        .sentence-bucket-table th,
        .sentence-bucket-table td {{
            vertical-align: top;
        }}
        .sentence-bucket-predictor-block {{
            margin: 26px 0 34px;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Greek vocabulary and unexpectedly long or short English translations</p>
    </header>
    {_translation_nav("../", "translation_length")}
    <div class="container" style="max-width: 1100px;">
        {body}
        <footer>
            Generated on {timestamp} from the PostgreSQL database
        </footer>
    </div>
</body>
</html>
"""

    with open(os.path.join(translation_length_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(page_html)

    _write_translation_mythic_strength_page(analysis, translation_length_dir, title, timestamp)

    print("Translation length page generated.")


def _grammar_passage_href(passage_id, prefix=""):
    parts = str(passage_id).split(".")
    if len(parts) != 3:
        return "#"
    return f"{prefix}grammar/{parts[0]}/{parts[1]}/{parts[2]}.html"


def _translation_href_for_passage(passage_id, prefix=""):
    parts = str(passage_id).split(".")
    if len(parts) != 3:
        return "#"
    return f"{prefix}translation/{parts[0]}/{parts[1]}/{parts[2]}.html"


def _grammar_token_index(token):
    raw = token.get("token_id") or token.get("token_order")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _grammar_head_label(tokens_by_index, token):
    raw = token.get("head_token_id")
    try:
        head = int(raw)
    except (TypeError, ValueError):
        return str(raw or "")
    if head == 0:
        return "0 ROOT"
    head_token = tokens_by_index.get(head)
    if not head_token:
        return str(head)
    return f"{head} {head_token.get('form') or ''}"


def _render_grammar_tree_svg(tokens):
    if not tokens:
        return '<div class="grammar-empty-tree">No tokens stored.</div>'

    spacing = 88
    margin = 46
    width = max(760, margin * 2 + spacing * max(1, len(tokens) - 1))
    indexed_tokens = [(_grammar_token_index(token), token) for token in tokens]
    positions = {
        index: margin + position * spacing
        for position, (index, _token) in enumerate(indexed_tokens)
        if index is not None
    }
    max_span = 1
    arcs = []
    root_tokens = []
    for index, token in indexed_tokens:
        if index is None:
            continue
        try:
            head = int(token.get("head_token_id") or 0)
        except (TypeError, ValueError):
            continue
        if head == 0:
            root_tokens.append(token)
            continue
        if head not in positions:
            continue
        span = abs(head - index)
        max_span = max(max_span, span)
        arcs.append((token, head, index, span))

    baseline = 58 + min(260, 24 + max_span * 15)
    height = baseline + 112
    svg_parts = [
        f'<svg class="grammar-parse-tree" viewBox="0 0 {width} {height}" '
        'role="img" aria-label="Dependency parse tree">'
    ]
    svg_parts.append(f'<line class="grammar-axis" x1="24" y1="{baseline}" x2="{width - 24}" y2="{baseline}" />')

    for token, head, child, span in sorted(arcs, key=lambda item: item[3], reverse=True):
        x1 = positions[head]
        x2 = positions[child]
        top = baseline - min(260, 34 + span * 15)
        control_y = top - 12
        label_x = (x1 + x2) / 2
        label_y = top - 5
        deprel = html.escape(str(token.get("deprel") or "dep"))
        svg_parts.append(
            f'<path class="grammar-arc" d="M{x1},{baseline} C{x1},{control_y} {x2},{control_y} {x2},{baseline}" />'
        )
        svg_parts.append(
            f'<text class="grammar-arc-label" x="{label_x}" y="{label_y}" text-anchor="middle">{deprel}</text>'
        )

    for token in root_tokens:
        index = _grammar_token_index(token)
        if index is None or index not in positions:
            continue
        x = positions[index]
        top = baseline - min(250, 48 + max_span * 15)
        svg_parts.append(f'<line class="grammar-root-line" x1="{x}" y1="{top}" x2="{x}" y2="{baseline}" />')
        svg_parts.append(f'<text class="grammar-root-label" x="{x}" y="{top - 7}" text-anchor="middle">root</text>')

    for index, token in indexed_tokens:
        if index is None or index not in positions:
            continue
        x = positions[index]
        form = html.escape(str(token.get("form") or ""))
        lemma = html.escape(str(token.get("lemma") or ""))
        upos = html.escape(str(token.get("upos") or ""))
        svg_parts.append(f'<circle class="grammar-token-dot" cx="{x}" cy="{baseline}" r="4" />')
        svg_parts.append(
            f'<text class="grammar-token-index" x="{x}" y="{baseline + 22}" text-anchor="middle">{index}</text>'
        )
        svg_parts.append(
            f'<text class="grammar-token-form" x="{x}" y="{baseline + 44}" text-anchor="middle">{form}</text>'
        )
        svg_parts.append(
            f'<text class="grammar-token-meta" x="{x}" y="{baseline + 64}" text-anchor="middle">{lemma} / {upos}</text>'
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def _render_grammar_token_table(tokens):
    tokens_by_index = {
        index: token
        for token in tokens
        if (index := _grammar_token_index(token)) is not None
    }
    rows = []
    for token in tokens:
        feats = token.get("feats_raw") or "_"
        note = token.get("note") or ""
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(token.get('token_id') or token.get('token_order') or ''))}</td>"
            f"<td class=\"greek-cell\">{html.escape(str(token.get('form') or ''))}</td>"
            f"<td class=\"greek-cell\">{html.escape(str(token.get('lemma') or ''))}</td>"
            f"<td><span class=\"upos\">{html.escape(str(token.get('upos') or ''))}</span></td>"
            f"<td>{html.escape(str(token.get('xpos') or '_'))}</td>"
            f"<td>{html.escape(str(feats))}</td>"
            f"<td>{html.escape(_grammar_head_label(tokens_by_index, token))}</td>"
            f"<td>{html.escape(str(token.get('deprel') or ''))}</td>"
            f"<td>{html.escape(str(token.get('confidence') or ''))}</td>"
            f"<td>{html.escape(str(note))}</td>"
            "</tr>"
        )
    return (
        '<div class="grammar-table-wrap">'
        '<table class="predictor-table grammar-token-table">'
        "<thead><tr>"
        "<th>#</th><th>Form</th><th>Lemma</th><th>UPOS</th><th>XPOS</th>"
        "<th>Features</th><th>Head</th><th>DepRel</th><th>Conf.</th><th>Note</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
    )


def _render_grammar_sentence_card(sentence):
    tokens = sentence.get("tokens") or []
    total_tokens = int(sentence.get("input_tokens") or 0) + int(sentence.get("output_tokens") or 0)
    sentence_note = sentence.get("sentence_note") or ""
    return f"""
        <section class="grammar-sentence-card" id="sentence-{int(sentence['sentence_number'])}">
            <header class="grammar-sentence-header">
                <div>
                    <div class="ordinal">Sentence {int(sentence['sentence_number'])}</div>
                    <h3>{html.escape(str(sentence.get('passage_id', '')))} sentence {int(sentence['sentence_number'])}</h3>
                </div>
                <dl class="grammar-metrics">
                    <div><dt>Tokens</dt><dd>{len(tokens)}</dd></div>
                    <div><dt>Input</dt><dd>{int(sentence.get('input_tokens') or 0):,}</dd></div>
                    <div><dt>Output</dt><dd>{int(sentence.get('output_tokens') or 0):,}</dd></div>
                    <div><dt>Total</dt><dd>{total_tokens:,}</dd></div>
                </dl>
            </header>
            <p class="greek-cell grammar-sentence-text">{html.escape(str(sentence.get('greek_sentence') or ''))}</p>
            {f'<p class="grammar-sentence-note">{html.escape(sentence_note)}</p>' if sentence_note else ''}
            <div class="grammar-tree-wrap">{_render_grammar_tree_svg(tokens)}</div>
            {_render_grammar_token_table(tokens)}
        </section>
    """


def generate_llm_grammar_pages(grammar_data, output_dir, title):
    """Generate passage-level pages for stored gpt-5.4-mini grammar parses."""
    grammar_dir = os.path.join(output_dir, "grammar")
    os.makedirs(grammar_dir, exist_ok=True)

    data = grammar_data or {}
    passages = data.get("passages") or []
    model = data.get("model") or "gpt-5.4-mini"
    timestamp = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
    prompt_versions = ", ".join(data.get("prompt_versions") or [])
    created_summary = ""
    if data.get("created_at_min") and data.get("created_at_max"):
        created_summary = f"{data['created_at_min']} to {data['created_at_max']}"

    books = sorted({passage["book"] for passage in passages})
    book_chapters = {
        book: sorted({passage["chapter"] for passage in passages if passage["book"] == book})
        for book in books
    }
    passage_order = sorted(
        passages,
        key=lambda passage: (passage["book"], passage["chapter"], passage["section"]),
    )
    passage_index = {
        passage["passage_id"]: index for index, passage in enumerate(passage_order)
    }

    if not passages:
        body = """
        <p>No stored grammar parses are available yet for this model.</p>
        """
    else:
        body = f"""
        <div class="metric-strip">
            <div><strong>{len(passages):,}</strong><span>passages with parses</span></div>
            <div><strong>{int(data.get('sentence_count') or 0):,}</strong><span>sentences</span></div>
            <div><strong>{int(data.get('token_count') or 0):,}</strong><span>Greek tokens</span></div>
            <div><strong>{int(data.get('input_tokens') or 0):,}</strong><span>input tokens</span></div>
            <div><strong>{int(data.get('output_tokens') or 0):,}</strong><span>output tokens</span></div>
        </div>
        <p class="note">Model: <code>{html.escape(model)}</code>{f'; prompt version(s): <code>{html.escape(prompt_versions)}</code>' if prompt_versions else ''}{f'; created: {html.escape(created_summary)}' if created_summary else ''}.</p>
        <h2>Books</h2>
        <ul>
        """
        for book in books:
            book_passages = [passage for passage in passages if passage["book"] == book]
            sentence_count = sum(len(passage["sentences"]) for passage in book_passages)
            body += (
                f'<li><a href="{book}/index.html">Book {book}</a> '
                f'({len(book_passages):,} passages, {sentence_count:,} sentences)</li>\n'
            )
        body += "</ul>"

    index_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Grammar Parses</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>LLM grammar parses by passage</p>
    </header>
    {_site_nav("../", "grammar")}
    <div class="container wide-container">
        <h2>Grammar Parses</h2>
        {body}
        <footer>Generated on {timestamp} from the PostgreSQL database</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(grammar_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page)

    for book in books:
        book_dir = os.path.join(grammar_dir, str(book))
        os.makedirs(book_dir, exist_ok=True)
        chapter_links = []
        for chapter in book_chapters[book]:
            chapter_passages = [
                passage
                for passage in passages
                if passage["book"] == book and passage["chapter"] == chapter
            ]
            sentence_count = sum(len(passage["sentences"]) for passage in chapter_passages)
            chapter_links.append(
                f'<li><a href="{chapter}/index.html">Chapter {book}.{chapter}</a> '
                f'({len(chapter_passages):,} passages, {sentence_count:,} sentences)</li>'
            )
        book_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Grammar Book {book}</title>
    <link rel="stylesheet" href="../../css/style.css">
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>Grammar parses, Book {book}</p>
    </header>
    {_site_nav("../../", "grammar")}
    <div class="container">
        <div class="breadcrumb"><a href="../index.html">Grammar</a> &rsaquo; Book {book}</div>
        <h2>Book {book}</h2>
        <ul>{''.join(chapter_links)}</ul>
        <footer>Generated on {timestamp}</footer>
    </div>
</body>
</html>
"""
        with open(os.path.join(book_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(book_page)

    for book in books:
        for chapter in book_chapters[book]:
            chapter_dir = os.path.join(grammar_dir, str(book), str(chapter))
            os.makedirs(chapter_dir, exist_ok=True)
            chapter_passages = [
                passage
                for passage in passages
                if passage["book"] == book and passage["chapter"] == chapter
            ]
            passage_links = []
            for passage in chapter_passages:
                pid = passage["passage_id"]
                sentence_count = len(passage["sentences"])
                token_count = sum(len(sentence.get("tokens") or []) for sentence in passage["sentences"])
                passage_links.append(
                    f'<li><a href="{passage["section"]}.html">{html.escape(pid)}</a> '
                    f'({sentence_count:,} sentences, {token_count:,} tokens) '
                    f'<span class="preview"><a href="../../../translation/{book}/{chapter}/{passage["section"]}.html">translation</a></span></li>'
                )
            chapter_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Grammar Chapter {book}.{chapter}</title>
    <link rel="stylesheet" href="../../../css/style.css">
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>Grammar parses, Chapter {book}.{chapter}</p>
    </header>
    {_site_nav("../../../", "grammar")}
    <div class="container">
        <div class="breadcrumb"><a href="../../index.html">Grammar</a> &rsaquo; <a href="../index.html">Book {book}</a> &rsaquo; Chapter {book}.{chapter}</div>
        <h2>Chapter {book}.{chapter}</h2>
        <ul class="passage-list">{''.join(passage_links)}</ul>
        <footer>Generated on {timestamp}</footer>
    </div>
</body>
</html>
"""
            with open(os.path.join(chapter_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write(chapter_page)

    for passage in passage_order:
        book = passage["book"]
        chapter = passage["chapter"]
        section = passage["section"]
        pid = passage["passage_id"]
        chapter_dir = os.path.join(grammar_dir, str(book), str(chapter))
        prefix = "../../../"
        index = passage_index[pid]
        prev_link = ""
        if index > 0:
            previous = passage_order[index - 1]
            prev_link = (
                f'<a href="{prefix}grammar/{previous["book"]}/{previous["chapter"]}/{previous["section"]}.html" '
                f'class="nav-prev">&larr; {html.escape(previous["passage_id"])}</a>'
            )
        next_link = ""
        if index < len(passage_order) - 1:
            following = passage_order[index + 1]
            next_link = (
                f'<a href="{prefix}grammar/{following["book"]}/{following["chapter"]}/{following["section"]}.html" '
                f'class="nav-next">{html.escape(following["passage_id"])} &rarr;</a>'
            )
        sentence_cards = "\n".join(
            _render_grammar_sentence_card(sentence) for sentence in passage["sentences"]
        )
        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Grammar {html.escape(pid)}</title>
    <link rel="stylesheet" href="{prefix}css/style.css">
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>Grammar parses for passage {html.escape(pid)}</p>
    </header>
    {_site_nav(prefix, "grammar")}
    <div class="container wide-container">
        <div class="breadcrumb">
            <a href="{prefix}grammar/index.html">Grammar</a> &rsaquo;
            <a href="../index.html">Book {book}</a> &rsaquo;
            <a href="index.html">Chapter {book}.{chapter}</a> &rsaquo;
            {html.escape(pid)}
        </div>
        <div class="passage-nav-top">{prev_link}{next_link}</div>
        <h2>Passage {html.escape(pid)}</h2>
        <p><a href="{_translation_href_for_passage(pid, prefix)}">Open translation for this passage</a></p>
        <div class="metric-strip">
            <div><strong>{len(passage["sentences"]):,}</strong><span>sentences parsed</span></div>
            <div><strong>{sum(len(sentence.get("tokens") or []) for sentence in passage["sentences"]):,}</strong><span>Greek tokens</span></div>
            <div><strong>{int(passage.get("input_tokens") or 0):,}</strong><span>input tokens</span></div>
            <div><strong>{int(passage.get("output_tokens") or 0):,}</strong><span>output tokens</span></div>
        </div>
        {sentence_cards}
        <div class="passage-nav-bottom">{prev_link}{next_link}</div>
        <footer>Generated on {timestamp} from the PostgreSQL database</footer>
    </div>
</body>
</html>
"""
        with open(os.path.join(chapter_dir, f"{section}.html"), "w", encoding="utf-8") as f:
            f.write(page)

    print(
        f"Grammar pages generated: {len(passages)} passages, "
        f"{int(data.get('sentence_count') or 0)} sentences for {model}."
    )


def generate_translation_pages(
    passages,
    nouns_by_passage,
    noun_passages,
    output_dir,
    title,
    summaries=None,
    graphic_book_image_dir=None,
    grammar_passage_ids=None,
):
    """Generate hierarchical translation pages: book > chapter > passage."""

    from .data import passage_id_sort_key

    translation_dir = os.path.join(output_dir, 'translation')
    os.makedirs(translation_dir, exist_ok=True)
    graphic_book_passage_ids = discover_graphic_book_passage_ids(graphic_book_image_dir)
    grammar_passage_ids = set(grammar_passage_ids or [])

    # Parse all passage IDs into (book, chapter, section) tuples
    parsed = []
    for p in passages:
        parts = p["id"].split(".")
        book, chapter, section = int(parts[0]), int(parts[1]), int(parts[2])
        parsed.append((book, chapter, section, p))

    # Group by book and chapter
    books = sorted(set(b for b, c, s, p in parsed))
    book_chapters = {}
    for book in books:
        chapters = sorted(set(c for b, c, s, p in parsed if b == book))
        book_chapters[book] = chapters

    # Build passage index for prev/next navigation
    passage_order = [(b, c, s, p) for b, c, s, p in parsed]

    timestamp = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")

    # --- Top-level index: list books ---
    books_index = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Translation</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Pausanias' Description of Greece &mdash; Greek text with English translation</p>
    </header>
    {_translation_nav("../", "translation")}
    <div class="container">
        <h2>Books</h2>
        <ul>
"""
    for book in books:
        n_chapters = len(book_chapters[book])
        books_index += f'            <li><a href="{book}/index.html">Book {book}</a> ({n_chapters} chapters)</li>\n'

    books_index += f"""        </ul>
        <h2>Indices</h2>
        <ul>
            <li><a href="nouns/index.html">Proper Noun Index</a> &mdash; People, places, deities, and other entities</li>
        </ul>
        <footer>Generated on {timestamp}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(translation_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(books_index)

    # --- Book-level pages: list chapters ---
    for book in books:
        book_dir = os.path.join(translation_dir, str(book))
        os.makedirs(book_dir, exist_ok=True)

        chapter_index = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Book {book}</title>
    <link rel="stylesheet" href="../../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Book {book}</p>
    </header>
    {_translation_nav("../../", "translation")}
    <div class="container">
        <h2>Book {book} &mdash; Chapters</h2>
        <ul>
"""
        for chapter in book_chapters[book]:
            # Count passages in this chapter
            n_passages = sum(1 for b, c, s, p in parsed if b == book and c == chapter)
            chapter_index += f'            <li><a href="{chapter}/index.html">Chapter {book}.{chapter}</a> ({n_passages} passages)</li>\n'

        chapter_index += f"""        </ul>
        <footer>Generated on {timestamp}</footer>
    </div>
</body>
</html>
"""
        with open(os.path.join(book_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(chapter_index)

    # --- Chapter-level pages: list passages with previews ---
    for book in books:
        for chapter in book_chapters[book]:
            chapter_dir = os.path.join(translation_dir, str(book), str(chapter))
            os.makedirs(chapter_dir, exist_ok=True)

            chapter_passages = [(s, p) for b, c, s, p in parsed if b == book and c == chapter]

            passage_list = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Chapter {book}.{chapter}</title>
    <link rel="stylesheet" href="../../../css/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Chapter {book}.{chapter}</p>
    </header>
    {_translation_nav("../../../", "translation")}
    <div class="container">
        <div class="breadcrumb">
            <a href="../index.html">Book {book}</a> &rsaquo; Chapter {book}.{chapter}
        </div>
        <h2>Chapter {book}.{chapter}</h2>
        <ul class="passage-list">
"""
            for section, p in chapter_passages:
                summary = summaries.get(p["id"]) if summaries else None
                if summary:
                    passage_list += f'            <li><a href="{section}.html">{p["id"]}: {html.escape(summary)}</a></li>\n'
                else:
                    preview = p["greek"][:80].rstrip() + ("..." if len(p["greek"]) > 80 else "")
                    passage_list += f'            <li><a href="{section}.html">{p["id"]}</a> <span class="preview">{html.escape(preview)}</span></li>\n'

            passage_list += f"""        </ul>
        <footer>Generated on {timestamp}</footer>
    </div>
</body>
</html>
"""
            with open(os.path.join(chapter_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(passage_list)

    # --- Individual passage pages ---
    linked_graphic_passages = 0
    for idx, (book, chapter, section, passage) in enumerate(passage_order):
        chapter_dir = os.path.join(translation_dir, str(book), str(chapter))
        pid = passage["id"]
        prefix = "../../../"

        # Prev/Next
        prev_link = ""
        if idx > 0:
            pb, pc, ps, pp = passage_order[idx - 1]
            prev_link = f'<a href="{prefix}translation/{pb}/{pc}/{ps}.html" class="nav-prev">&larr; {pp["id"]}</a>'
        next_link = ""
        if idx < len(passage_order) - 1:
            nb, nc, ns, np_ = passage_order[idx + 1]
            next_link = f'<a href="{prefix}translation/{nb}/{nc}/{ns}.html" class="nav-next">{np_["id"]} &rarr;</a>'

        # Proper nouns
        nouns = nouns_by_passage.get(pid, [])
        nouns_html = ""
        geo_places = []

        if nouns:
            nouns_html = '<div class="translation-nouns"><h3>Proper Nouns</h3>\n'
            for noun in nouns:
                entity_class = f"entity-{noun['entity_type']}"
                nouns_html += f'<div class="noun-entry {entity_class}">\n'
                nouns_html += f'  <span class="noun-name">{html.escape(noun["english"])}</span> '
                nouns_html += f'<span class="noun-greek">({html.escape(noun["reference_form"])})</span> '
                nouns_html += f'<span class="noun-type">{noun["entity_type"]}</span>'

                # Wikidata link
                if noun.get("qid"):
                    nouns_html += f' <a href="https://www.wikidata.org/wiki/{noun["qid"]}" target="_blank" class="noun-link">{noun["qid"]}</a>'

                # Pleiades link
                if noun.get("pleiades_id"):
                    nouns_html += f' <a href="https://pleiades.stoa.org/places/{noun["pleiades_id"]}" target="_blank" class="noun-link">Pleiades</a>'

                # Collect geolocated places for mini-map
                if noun.get("lat") is not None and noun.get("lon") is not None:
                    geo_places.append(noun)

                # Cross-references
                key = (noun["reference_form"], noun["entity_type"])
                xrefs = noun_passages.get(key, [])
                other_refs = [r for r in xrefs if r != pid]
                if other_refs:
                    xref_links = []
                    for ref in other_refs[:10]:  # Limit to 10
                        rparts = ref.split(".")
                        xref_links.append(
                            f'<a href="{prefix}translation/{rparts[0]}/{rparts[1]}/{rparts[2]}.html">{ref}</a>'
                        )
                    if len(other_refs) > 10:
                        xref_links.append(f"... +{len(other_refs) - 10} more")
                    nouns_html += f'\n  <div class="noun-xrefs">Also in: {" ".join(xref_links)}</div>'

                nouns_html += '\n</div>\n'
            nouns_html += '</div>\n'

        # Mini-map
        map_html = ""
        leaflet_head = ""
        if geo_places:
            leaflet_head = """<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>"""

            markers_js = ""
            for gp in geo_places:
                markers_js += f"        L.marker([{gp['lat']}, {gp['lon']}]).addTo(miniMap).bindPopup('{html.escape(gp['english'])}');\n"

            # Center on first place, or average
            center_lat = sum(gp["lat"] for gp in geo_places) / len(geo_places)
            center_lon = sum(gp["lon"] for gp in geo_places) / len(geo_places)
            zoom = 7 if len(geo_places) == 1 else 5

            map_html = f"""
        <div class="passage-map">
            <div id="mini-map" style="height: 250px; border-radius: 5px; border: 1px solid #5c5142; margin: 15px 0;"></div>
            <script>
                const miniMap = L.map('mini-map').setView([{center_lat}, {center_lon}], {zoom});
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; OSM',
                    maxZoom: 18
                }}).addTo(miniMap);
{markers_js}            </script>
        </div>
"""

        # Sentence analysis link
        sentence_link = f'<a href="{prefix}sentences/{book}_{chapter}.html">View sentence analysis for this chapter</a>'
        graphic_book_link_html = ""
        if pid in graphic_book_passage_ids:
            linked_graphic_passages += 1
            graphic_href = f"{prefix}graphic-book/{book}/{chapter}/{section}.html"
            graphic_book_link_html = (
                f'\n            <p><a class="graphic-book-link" href="{graphic_href}">'
                "Open graphic version of this passage</a></p>"
            )
        grammar_link_html = ""
        if pid in grammar_passage_ids:
            grammar_href = f"{prefix}grammar/{book}/{chapter}/{section}.html"
            grammar_link_html = (
                f'\n            <p><a class="grammar-passage-link" href="{grammar_href}">'
                "Open grammar parses for this passage</a></p>"
            )

        # English translation
        english_html = ""
        if passage.get("english"):
            english_html = f"""
        <div class="translation-english">
            <h3>English Translation</h3>
            <p>{html.escape(passage["english"])}</p>
        </div>
"""

        # Build full page
        page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {pid}</title>
    <link rel="stylesheet" href="{prefix}css/style.css">
    <link rel="stylesheet" href="{prefix}css/translation.css">
    {leaflet_head}
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Passage {pid}</p>
    </header>
    {_translation_nav(prefix, "translation")}
    <div class="container">
        <div class="breadcrumb">
            <a href="../../../translation/index.html">Translation</a> &rsaquo;
            <a href="../index.html">Book {book}</a> &rsaquo;
            <a href="index.html">Chapter {book}.{chapter}</a> &rsaquo;
            {pid}
        </div>

        <div class="passage-nav-top">
            {prev_link}
            {next_link}
        </div>

        <h2>Passage {pid}{f": {html.escape(summaries[pid])}" if summaries and pid in summaries else ""}</h2>

        <div class="translation-greek">
            <h3>Greek Text</h3>
            <p class="greek-passage">{html.escape(passage["greek"])}</p>
        </div>
{english_html}{nouns_html}{map_html}
        <div class="passage-links">
            <p>{sentence_link}</p>
            {graphic_book_link_html}
            {grammar_link_html}
        </div>

        <div class="passage-nav-bottom">
            {prev_link}
            {next_link}
        </div>

        <footer>Generated on {timestamp}</footer>
    </div>
</body>
</html>
"""
        filepath = os.path.join(chapter_dir, f"{section}.html")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(page_html)

    # Write translation-specific CSS
    css_path = os.path.join(output_dir, 'css', 'translation.css')
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write("""
.breadcrumb {
    font-size: 0.9em;
    margin-bottom: 15px;
    color: #776b5d;
}
.breadcrumb a {
    color: #5c5142;
}
.passage-nav-top, .passage-nav-bottom {
    display: flex;
    justify-content: space-between;
    margin: 10px 0;
}
.nav-prev, .nav-next {
    color: #5c5142;
    text-decoration: none;
    font-weight: bold;
    padding: 5px 10px;
    border: 1px solid #5c5142;
    border-radius: 4px;
}
.nav-prev:hover, .nav-next:hover {
    background-color: #eee9e3;
}
.translation-greek, .translation-english {
    margin-bottom: 20px;
}
.greek-passage {
    font-size: 1.1em;
    line-height: 1.8;
}
.translation-english p {
    line-height: 1.7;
    background-color: #f5f5f5;
    padding: 15px;
    border-radius: 5px;
    border-left: 3px solid #5c5142;
}
.translation-nouns {
    margin: 20px 0;
    padding: 15px;
    background-color: #faf9f7;
    border-radius: 5px;
    border: 1px solid #eee9e3;
}
.noun-entry {
    padding: 6px 0;
    border-bottom: 1px solid #eee9e3;
}
.noun-entry:last-child {
    border-bottom: none;
}
.noun-name {
    font-weight: bold;
}
.noun-greek {
    color: #555;
    font-style: italic;
}
.noun-type {
    display: inline-block;
    font-size: 0.75em;
    padding: 1px 6px;
    border-radius: 8px;
    background-color: #eee9e3;
    color: #5c5142;
    margin-left: 4px;
}
.noun-link {
    font-size: 0.8em;
    margin-left: 6px;
    color: #5c5142;
}
.noun-xrefs {
    font-size: 0.8em;
    color: #776b5d;
    margin-top: 3px;
    margin-left: 10px;
}
.noun-xrefs a {
    margin-right: 4px;
    color: #5c5142;
}
.passage-links {
    margin: 20px 0;
    font-size: 0.9em;
}
.passage-links a {
    color: #5c5142;
}
.passage-links a.graphic-book-link {
    background-color: #2c5f78;
    border-radius: 4px;
    color: white;
    display: inline-block;
    font-weight: bold;
    padding: 7px 11px;
    text-decoration: none;
}
.passage-links a.graphic-book-link:hover {
    background-color: #39758f;
}
.passage-list li {
    margin-bottom: 6px;
}
.preview {
    color: #776b5d;
    font-size: 0.85em;
    margin-left: 8px;
}
.passage-summary {
    color: #555;
    font-style: italic;
    margin-top: -0.5em;
    margin-bottom: 1em;
}
.noun-index-list li {
    margin-bottom: 6px;
    font-size: 1.1em;
}
.noun-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9em;
}
.noun-table th, .noun-table td {
    border: 1px solid #ddd;
    padding: 6px 8px;
    text-align: left;
    vertical-align: top;
}
.noun-table th {
    background: #f5f0eb;
}
.noun-table .greek {
    font-family: serif;
}
.noun-table .noun-refs {
    font-size: 0.85em;
}
.noun-table .noun-refs a {
    margin-right: 4px;
}
""")

    # --- Proper noun index pages ---
    nouns_dir = os.path.join(translation_dir, 'nouns')
    os.makedirs(nouns_dir, exist_ok=True)

    # Build noun registry, merging inflected forms by English name
    type_normalize = {"people": "person", "people (person)": "person", "people group": "person", "epithet": "deity"}
    type_labels = {"person": "People", "place": "Places", "deity": "Deities", "other": "Other"}
    type_files = {"person": "people", "place": "places", "deity": "deities", "other": "other"}

    # Step 1: For each (reference_form, entity_type), find the most common English name
    form_english = {}  # (reference_form, entity_type) -> most common english
    form_english_counts = {}
    for pid, nouns in nouns_by_passage.items():
        for noun in nouns:
            key = (noun["reference_form"], noun["entity_type"])
            english = noun["english"] if noun["english"] else noun["reference_form"]
            if key not in form_english_counts:
                form_english_counts[key] = {}
            form_english_counts[key][english] = form_english_counts[key].get(english, 0) + 1
    for key, counts in form_english_counts.items():
        form_english[key] = max(counts, key=counts.get)

    # Step 2: Merge by (canonical_english, normalized_type)
    merged_nouns = {}
    for pid, nouns in nouns_by_passage.items():
        for noun in nouns:
            etype = type_normalize.get(noun["entity_type"], noun["entity_type"])
            if etype not in type_labels:
                etype = "other"
            # Use the canonical English name for this reference_form
            canonical = form_english.get((noun["reference_form"], noun["entity_type"]),
                                         noun["english"] or noun["reference_form"])
            merge_key = (canonical, etype)

            if merge_key not in merged_nouns:
                merged_nouns[merge_key] = {
                    "english": canonical,
                    "entity_type": etype,
                    "greek_forms": set(),
                    "passages": set(),
                    "qid": None,
                    "pleiades_id": None,
                }

            entry = merged_nouns[merge_key]
            entry["greek_forms"].add(noun["reference_form"])
            entry["passages"].add(pid)
            if noun.get("qid") and not entry["qid"]:
                entry["qid"] = noun["qid"]
            if noun.get("pleiades_id") and not entry["pleiades_id"]:
                entry["pleiades_id"] = noun["pleiades_id"]

    # Group by entity type
    nouns_by_type = {}
    for (english, etype), entry in merged_nouns.items():
        if etype not in nouns_by_type:
            nouns_by_type[etype] = []
        entry["passages"] = sorted(entry["passages"], key=passage_id_sort_key)
        entry["greek_forms"] = sorted(entry["greek_forms"])
        nouns_by_type[etype].append(entry)

    # Sort each type alphabetically by English name
    for etype in nouns_by_type:
        nouns_by_type[etype].sort(key=lambda x: x["english"].lower())

    # Noun index page
    noun_index = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Proper Nouns</title>
    <link rel="stylesheet" href="../../css/style.css">
    <link rel="stylesheet" href="../../css/translation.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Proper Noun Index</p>
    </header>
    {_translation_nav("../../", "translation")}
    <div class="container">
        <div class="breadcrumb">
            <a href="../index.html">Translation</a> &rsaquo; Proper Nouns
        </div>
        <h2>Proper Noun Index</h2>
        <ul class="noun-index-list">
"""
    for etype in ["person", "place", "deity", "other"]:
        if etype in nouns_by_type:
            count = len(nouns_by_type[etype])
            noun_index += f'            <li><a href="{type_files[etype]}.html">{type_labels[etype]}</a> ({count})</li>\n'

    noun_index += f"""        </ul>
        <footer>Generated on {timestamp}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(nouns_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(noun_index)

    # Per-type pages
    for etype in ["person", "place", "deity", "other"]:
        if etype not in nouns_by_type:
            continue

        type_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {type_labels[etype]}</title>
    <link rel="stylesheet" href="../../css/style.css">
    <link rel="stylesheet" href="../../css/translation.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>{type_labels[etype]}</p>
    </header>
    {_translation_nav("../../", "translation")}
    <div class="container">
        <div class="breadcrumb">
            <a href="../index.html">Translation</a> &rsaquo;
            <a href="index.html">Proper Nouns</a> &rsaquo;
            {type_labels[etype]}
        </div>
        <h2>{type_labels[etype]}</h2>
        <table class="noun-table">
            <thead><tr><th>Name</th><th>Greek</th><th>Passages</th><th>Links</th></tr></thead>
            <tbody>
"""
        for entry in nouns_by_type[etype]:
            english = html.escape(entry["english"])
            greek = ", ".join(html.escape(g) for g in entry["greek_forms"])
            # Passage links
            passage_links = []
            for ref in entry["passages"][:15]:
                rparts = ref.split(".")
                passage_links.append(f'<a href="../../translation/{rparts[0]}/{rparts[1]}/{rparts[2]}.html">{ref}</a>')
            if len(entry["passages"]) > 15:
                passage_links.append(f"... +{len(entry['passages']) - 15} more")
            passages_html = " ".join(passage_links)
            # External links
            ext_links = []
            if entry.get("qid"):
                ext_links.append(f'<a href="https://www.wikidata.org/wiki/{entry["qid"]}" target="_blank">{entry["qid"]}</a>')
            if entry.get("pleiades_id"):
                ext_links.append(f'<a href="https://pleiades.stoa.org/places/{entry["pleiades_id"]}" target="_blank">Pleiades</a>')
            ext_html = " ".join(ext_links)

            type_page += f'            <tr><td>{english}</td><td class="greek">{greek}</td><td class="noun-refs">{passages_html}</td><td>{ext_html}</td></tr>\n'

        type_page += f"""            </tbody>
        </table>
        <footer>Generated on {timestamp}</footer>
    </div>
</body>
</html>
"""
        with open(os.path.join(nouns_dir, f'{type_files[etype]}.html'), 'w', encoding='utf-8') as f:
            f.write(type_page)

    total_nouns = sum(len(v) for v in nouns_by_type.values())
    total_passages = len(passage_order)
    print(f"Translation pages generated: {total_passages} passages across {len(books)} books.")
    if linked_graphic_passages:
        print(f"Graphic-book links added for {linked_graphic_passages} translated passages.")
    print(f"Proper noun index generated: {total_nouns} nouns across {len(nouns_by_type)} types.")


def generate_progress_page(progress_data, output_dir, title):
    """Generate a progress tracking page showing pipeline status."""
    from datetime import datetime

    progress_dir = os.path.join(output_dir, 'progress')
    os.makedirs(progress_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")

    def fmt_count(value):
        if value is None:
            return "n/a"
        return f"{int(value):,}"

    def fmt_text(value):
        return html.escape(str(value or ""))

    def progress_cell(percent):
        if percent is None:
            return '<span class="progress-na">n/a</span>'
        if percent >= 100:
            bar_class = "bar-complete"
        elif percent >= 50:
            bar_class = "bar-progress"
        else:
            bar_class = "bar-early"
        return (
            f'<div class="bar-container"><div class="{bar_class}" '
            f'style="width:{min(percent,100):.0f}%"></div><span>{percent:.1f}%</span></div>'
        )

    # Build task rows
    task_rows = ""
    for task in progress_data["tasks"]:
        pct = task.get("percent")
        if pct is not None and pct >= 100:
            row_class = ' class="complete"'
        else:
            row_class = ""

        task_rows += f"""            <tr{row_class}>
                <td>{fmt_text(task.get("area", ""))}</td>
                <td>{fmt_text(task["name"])}</td>
                <td><code>{fmt_text(task["script"])}</code></td>
                <td>{fmt_text(task.get("cadence", task.get("batch_size", "")))}</td>
                <td class="num">{fmt_count(task.get("done"))}</td>
                <td class="num">{fmt_count(task.get("total"))}</td>
                <td class="num">{progress_cell(pct)}</td>
                <td>{fmt_text(task.get("status", ""))}</td>
                <td>{fmt_text(task.get("est_completion", ""))}</td>
                <td>{fmt_text(task.get("details", ""))}</td>
            </tr>
"""

    # Build token usage rows
    token_rows = ""
    total_input = 0
    total_output = 0
    for src in progress_data["token_usage"]:
        total_input += src["input_tokens"]
        total_output += src["output_tokens"]
        token_rows += f"""            <tr>
                <td>{src["name"]}</td>
                <td class="num">{src["input_tokens"]:,}</td>
                <td class="num">{src["output_tokens"]:,}</td>
                <td class="num">{src["total_tokens"]:,}</td>
            </tr>
"""
    token_rows += f"""            <tr class="total-row">
                <td><strong>Total</strong></td>
                <td class="num"><strong>{total_input:,}</strong></td>
                <td class="num"><strong>{total_output:,}</strong></td>
                <td class="num"><strong>{total_input + total_output:,}</strong></td>
            </tr>
"""

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Progress</title>
    <link rel="stylesheet" href="../css/style.css">
    <style>
        .progress-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
            margin-bottom: 2em;
        }}
        .progress-table-wrap {{
            max-width: 100%;
            overflow-x: auto;
        }}
        .progress-table th, .progress-table td {{
            border: 1px solid #ddd;
            padding: 6px 10px;
            text-align: left;
            vertical-align: top;
        }}
        .progress-table th {{
            background: #f5f0eb;
        }}
        .progress-table .num {{
            text-align: right;
        }}
        .progress-table tr.complete td {{
            background: #f0f9f0;
        }}
        .progress-table tr.total-row td {{
            background: #f5f0eb;
        }}
        .progress-table code {{
            font-size: 0.85em;
            background: #f0ebe5;
            padding: 1px 4px;
            border-radius: 3px;
            white-space: nowrap;
        }}
        .bar-container {{
            position: relative;
            background: #eee;
            border-radius: 3px;
            height: 20px;
            min-width: 80px;
        }}
        .bar-container span {{
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            font-size: 0.8em;
            font-weight: bold;
            color: #333;
        }}
        .bar-complete {{
            background: #8bc78b;
            height: 100%;
            border-radius: 3px;
        }}
        .bar-progress {{
            background: #c7c28b;
            height: 100%;
            border-radius: 3px;
        }}
        .bar-early {{
            background: #c7a08b;
            height: 100%;
            border-radius: 3px;
        }}
        .progress-na {{
            color: #666;
            display: inline-block;
            min-width: 80px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Pipeline Progress</p>
    </header>
    {_translation_nav("../", "progress")}
    <div class="container wide-container">
        <h2>Task Progress</h2>
        <div class="progress-table-wrap">
        <table class="progress-table">
            <thead>
                <tr><th>Area</th><th>Task</th><th>Script</th><th>Cadence</th><th>Done</th><th>Total</th><th>Progress</th><th>Status</th><th>Est. completion</th><th>Details</th></tr>
            </thead>
            <tbody>
{task_rows}            </tbody>
        </table>
        </div>

        <h2>Token Usage</h2>
        <div class="progress-table-wrap">
        <table class="progress-table">
            <thead>
                <tr><th>Source</th><th>Input tokens</th><th>Output tokens</th><th>Total</th></tr>
            </thead>
            <tbody>
{token_rows}            </tbody>
        </table>
        </div>

        <footer>Generated on {timestamp}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(progress_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page_html)

    print("Progress page generated.")
