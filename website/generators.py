"""HTML page generator functions."""

import json
import os
import html
import re
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


def _generated_footer():
    return f"Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')} from the PostgreSQL database"


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


def generate_analysis_pages(greta_analysis, output_dir, title):
    """Generate the analysis hub and current Greta logistic-regression variants."""
    analysis_dir = os.path.join(output_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)

    variants = greta_analysis.get("variants", []) if greta_analysis else []
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
        <p>Greta sentence-level mythic vs. historical analysis</p>
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
            <h2>Current Sentence-Level Analyses</h2>
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
            <h2>Current Sentence-Level Analyses</h2>
            <p>{html.escape(greta_analysis.get("message", "No Greta analysis data is available.") if greta_analysis else "No Greta analysis data is available.")}</p>
        """

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

        <h2>Translation Length</h2>
        <section class="hub-card">
            <h3>Unexpectedly Long or Short Translations</h3>
            <p>Greek predictors of length residuals, plus the dual view of English terms found in longer or shorter-than-expected passages.</p>
            <a href="../translation_length/index.html">Open Translation Length Analysis</a>
        </section>

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

    print("Translation length page generated.")


def generate_translation_pages(
    passages,
    nouns_by_passage,
    noun_passages,
    output_dir,
    title,
    summaries=None,
    graphic_book_image_dir=None,
):
    """Generate hierarchical translation pages: book > chapter > passage."""

    from .data import passage_id_sort_key

    translation_dir = os.path.join(output_dir, 'translation')
    os.makedirs(translation_dir, exist_ok=True)
    graphic_book_passage_ids = discover_graphic_book_passage_ids(graphic_book_image_dir)

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

        # Classification badges
        badges = []
        if passage["is_mythic"] is not None:
            label = "Mythic" if passage["is_mythic"] else "Historical"
            css_class = "badge-mythic" if passage["is_mythic"] else "badge-historical"
            badges.append(f'<span class="badge {css_class}">{label}</span>')
        if passage["is_skeptical"] is not None:
            label = "Skeptical" if passage["is_skeptical"] else "Non-skeptical"
            css_class = "badge-skeptical" if passage["is_skeptical"] else "badge-non-skeptical"
            badges.append(f'<span class="badge {css_class}">{label}</span>')
        badges_html = " ".join(badges)

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
        <div class="classification-badges">{badges_html}</div>

        <div class="translation-greek">
            <h3>Greek Text</h3>
            <p class="greek-passage">{html.escape(passage["greek"])}</p>
        </div>
{english_html}{nouns_html}{map_html}
        <div class="passage-links">
            <p>{sentence_link}</p>
            {graphic_book_link_html}
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
.classification-badges {
    margin-bottom: 15px;
}
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.85em;
    margin-right: 8px;
}
.badge-mythic { background-color: #fde8e4; color: #cc3300; }
.badge-historical { background-color: #e4eefb; color: #0066cc; }
.badge-skeptical { background-color: #e4f5e9; color: #009933; }
.badge-non-skeptical { background-color: #fef3e4; color: #cc6600; }
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

    # Build task rows
    task_rows = ""
    for task in progress_data["tasks"]:
        pct = task["percent"]
        if pct >= 100:
            row_class = ' class="complete"'
            bar_class = "bar-complete"
        elif pct >= 50:
            row_class = ""
            bar_class = "bar-progress"
        else:
            row_class = ""
            bar_class = "bar-early"

        task_rows += f"""            <tr{row_class}>
                <td>{task["name"]}</td>
                <td><code>{task["script"]}</code></td>
                <td class="num">{task["batch_size"]}</td>
                <td class="num">{task["done"]:,}</td>
                <td class="num">{task["total"]:,}</td>
                <td class="num"><div class="bar-container"><div class="{bar_class}" style="width:{min(pct,100):.0f}%"></div><span>{pct:.1f}%</span></div></td>
                <td>{task["est_completion"]}</td>
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
        .progress-table th, .progress-table td {{
            border: 1px solid #ddd;
            padding: 6px 10px;
            text-align: left;
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
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Pipeline Progress</p>
    </header>
    {_translation_nav("../", "progress")}
    <div class="container">
        <h2>Task Progress</h2>
        <table class="progress-table">
            <thead>
                <tr><th>Task</th><th>Script</th><th>Batch/day</th><th>Done</th><th>Total</th><th>Progress</th><th>Est. completion</th></tr>
            </thead>
            <tbody>
{task_rows}            </tbody>
        </table>

        <h2>Token Usage</h2>
        <table class="progress-table">
            <thead>
                <tr><th>Source</th><th>Input tokens</th><th>Output tokens</th><th>Total</th></tr>
            </thead>
            <tbody>
{token_rows}            </tbody>
        </table>

        <footer>Generated on {timestamp}</footer>
    </div>
</body>
</html>
"""
    with open(os.path.join(progress_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page_html)

    print("Progress page generated.")
