"""HTML page generator functions."""

import json
import os
import html
import pandas as pd
from datetime import datetime
from .highlighting import highlight_passage


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
        
        <nav>
            <a href="index.html" class="active">Home</a>
            <a href="translation/index.html">Translation</a>
            <a href="mythic/index.html">Mythic Analysis</a>
            <a href="skepticism/index.html">Skepticism Analysis</a>
            <a href="mythic_words.html">Mythic Words</a>
            <a href="skeptic_words.html">Skeptic Words</a>
            <a href="sentences/index.html">Sentences</a>
            <a href="sentence_mythic_words.html">Sentence Mythic Words</a>
            <a href="sentence_skeptic_words.html">Sentence Skeptic Words</a>
            <a href="network_viz/index.html">Network Analysis</a>
            <a href="map/index.html">Place Map</a>
        </nav>

        <div class="container">
            <h2>Welcome to the Pausanias Analysis Project</h2>
            
            <p>This site presents an analysis of Pausanias' "Description of Greece", focusing on two key aspects:</p>
            
            <div class="home-card">
                <h2>Translation</h2>
                <p>Browse Pausanias' text with Greek and English side by side,
                   proper nouns linked to Wikidata, and places shown on maps.</p>
                <a href="translation/index.html">View Translation</a>
            </div>

            <div class="home-card">
                <h2>Mythic vs. Historical Content</h2>
                <p>Explore passages with mythical content highlighted in warm colors and italics, 
                   while historical content appears in cool colors.</p>
                <a href="mythic/index.html">View Mythic Analysis</a>
            </div>
            
            <div class="home-card">
                <h2>Expression of Skepticism</h2>
                <p>Discover how Pausanias expresses skepticism (or credulity) through his writing. 
                   Skeptical content is highlighted in green, while non-skeptical appears in orange and bold.</p>
                <a href="skepticism/index.html">View Skepticism Analysis</a>
            </div>
            
            <div class="home-card">
                <h2>Predictive Words and Phrases</h2>
                <p>Examine the specific words and phrases that are most strongly associated with mythic content and skepticism.</p>
                <a href="mythic_words.html">Mythic Predictors</a>
                <a href="skeptic_words.html">Skepticism Predictors</a>
                <a href="sentence_mythic_words.html">Sentence Mythic Predictors</a>
                <a href="sentence_skeptic_words.html">Sentence Skepticism Predictors</a>
            </div>

            <div class="home-card">
                <h2>Place Map</h2>
                <p>View places mentioned by Pausanias on an interactive map. Click markers to see
                   which passages reference each location.</p>
                <a href="map/index.html">View Place Map</a>
            </div>

            <footer>
                Site generated on {timestamp} from <a href="pausanias.sqlite">pausanias.sqlite</a>
            </footer>
        </div>
    </body>
    </html>
    """
    
    # Write the file
    with open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

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

        <nav>
            <a href=\"../index.html\">Home</a>
            <a href=\"index.html\" class=\"active\">Mythic Analysis</a>
            <a href=\"../skepticism/index.html\">Skepticism Analysis</a>
            <a href=\"../mythic_words.html\">Mythic Words</a>
            <a href=\"../skeptic_words.html\">Skeptic Words</a>
            <a href=\"../sentences/index.html\">Sentences</a>
            <a href=\"../sentence_mythic_words.html\">Sentence Mythic Words</a>
            <a href=\"../sentence_skeptic_words.html\">Sentence Skeptic Words</a>
            <a href=\"../network_viz/index.html\">Network Analysis</a>
            <a href=\"../map/index.html\">Place Map</a>
        </nav>

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
                Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")} from <a href=\"../pausanias.sqlite\">pausanias.sqlite</a>
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

        <nav>
            <a href=\"../index.html\">Home</a>
            <a href=\"index.html\" class=\"active\">Mythic Analysis</a>
            <a href=\"../skepticism/index.html\">Skepticism Analysis</a>
            <a href=\"../mythic_words.html\">Mythic Words</a>
            <a href=\"../skeptic_words.html\">Skeptic Words</a>
            <a href=\"../sentences/index.html\">Sentences</a>
            <a href=\"../sentence_mythic_words.html\">Sentence Mythic Words</a>
            <a href=\"../sentence_skeptic_words.html\">Sentence Skeptic Words</a>
            <a href=\"../network_viz/index.html\">Network Analysis</a>
            <a href=\"../map/index.html\">Place Map</a>
        </nav>

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
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """ from <a href=\"../pausanias.sqlite\">pausanias.sqlite</a>
            </footer>
        </div>
    </body>
    </html>
    """

    with open(os.path.join(mythic_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_content)

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

        <nav>
            <a href=\"../index.html\">Home</a>
            <a href=\"../translation/index.html\">Translation</a>
            <a href=\"../mythic/index.html\">Mythic Analysis</a>
            <a href=\"index.html\" class=\"active\">Skepticism Analysis</a>
            <a href=\"../mythic_words.html\">Mythic Words</a>
            <a href=\"../skeptic_words.html\">Skeptic Words</a>
            <a href=\"../sentences/index.html\">Sentences</a>
            <a href=\"../sentence_mythic_words.html\">Sentence Mythic Words</a>
            <a href=\"../sentence_skeptic_words.html\">Sentence Skeptic Words</a>
            <a href=\"../network_viz/index.html\">Network Analysis</a>
            <a href=\"../map/index.html\">Place Map</a>
        </nav>

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
                Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")} from <a href=\"../pausanias.sqlite\">pausanias.sqlite</a>
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

        <nav>
            <a href=\"../index.html\">Home</a>
            <a href=\"../translation/index.html\">Translation</a>
            <a href=\"../mythic/index.html\">Mythic Analysis</a>
            <a href=\"index.html\" class=\"active\">Skepticism Analysis</a>
            <a href=\"../mythic_words.html\">Mythic Words</a>
            <a href=\"../skeptic_words.html\">Skeptic Words</a>
            <a href=\"../sentences/index.html\">Sentences</a>
            <a href=\"../sentence_mythic_words.html\">Sentence Mythic Words</a>
            <a href=\"../sentence_skeptic_words.html\">Sentence Skeptic Words</a>
            <a href=\"../network_viz/index.html\">Network Analysis</a>
            <a href=\"../map/index.html\">Place Map</a>
        </nav>

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
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """ from <a href=\"../pausanias.sqlite\">pausanias.sqlite</a>
            </footer>
        </div>
    </body>
    </html>
    """

    with open(os.path.join(skeptic_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_content)

def generate_mythic_words_page(mythic_predictors, output_dir, title, metrics=None):
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

        <nav>
            <a href="index.html">Home</a>
            <a href="translation/index.html">Translation</a>
            <a href="mythic/index.html">Mythic Analysis</a>
            <a href="skepticism/index.html">Skepticism Analysis</a>
            <a href="mythic_words.html" class="active">Mythic Words</a>
            <a href="skeptic_words.html">Skeptic Words</a>
            <a href="sentences/index.html">Sentences</a>
            <a href="sentence_mythic_words.html">Sentence Mythic Words</a>
            <a href="sentence_skeptic_words.html">Sentence Skeptic Words</a>
            <a href="network_viz/index.html">Network Analysis</a>
            <a href="map/index.html">Place Map</a>
        </nav>

        <div class="container">
            {format_classification_metrics(metrics, 'Historical', 'Mythic')}

            <h2>Predictors of Mythic Content</h2>
            <p>These words and phrases are most strongly associated with mythic content in Pausanias.</p>
            
            <table class="predictor-table">
                <thead>
                    <tr>
                        <th>Word/Phrase</th>
                        <th>English</th>
                        <th>Coefficient</th>
                        <th>Mythic Count</th>
                        <th>Non-mythic Count</th>
                        <th>p-value</th>
                        <th>q-value</th>
                    </tr>
                </thead>
                <tbody>
    """

    # Add mythic predictors
    for _, row in mythic_words.iterrows():
        english = row.get('english_translation', '')
        html_content += f"""
                    <tr>
                        <td class="mythic-word">{html.escape(row['phrase'])}</td>
                        <td>{html.escape(english)}</td>
                        <td>{row['coefficient']:.4f}</td>
                        <td>{row['mythic_count']}</td>
                        <td>{row['non_mythic_count']}</td>
                        <td>{row['p_value']:.3g}</td>
                        <td>{row['q_value']:.3g}</td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
            
            <h2>Predictors of Historical Content</h2>
            <p>These words and phrases are most strongly associated with historical content in Pausanias.</p>
            
            <table class="predictor-table">
                <thead>
                    <tr>
                        <th>Word/Phrase</th>
                        <th>English</th>
                        <th>Coefficient</th>
                        <th>Mythic Count</th>
                        <th>Non-mythic Count</th>
                        <th>p-value</th>
                        <th>q-value</th>
                    </tr>
                </thead>
                <tbody>
    """

    # Add historical predictors
    for _, row in historical_words.iterrows():
        english = row.get('english_translation', '')
        html_content += f"""
                    <tr>
                        <td class="historical-word">{html.escape(row['phrase'])}</td>
                        <td>{html.escape(english)}</td>
                        <td>{row['coefficient']:.4f}</td>
                        <td>{row['mythic_count']}</td>
                        <td>{row['non_mythic_count']}</td>
                        <td>{row['p_value']:.3g}</td>
                        <td>{row['q_value']:.3g}</td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>

            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """ from <a href=\"pausanias.sqlite\">pausanias.sqlite</a>
            </footer>
        </div>
    </body>
    </html>
    """
    
    # Write the file
    with open(os.path.join(output_dir, 'mythic_words.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

def generate_skeptic_words_page(skeptic_predictors, output_dir, title, metrics=None):
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

        <nav>
            <a href="index.html">Home</a>
            <a href="translation/index.html">Translation</a>
            <a href="mythic/index.html">Mythic Analysis</a>
            <a href="skepticism/index.html">Skepticism Analysis</a>
            <a href="mythic_words.html">Mythic Words</a>
            <a href="skeptic_words.html" class="active">Skeptic Words</a>
            <a href="sentences/index.html">Sentences</a>
            <a href="sentence_mythic_words.html">Sentence Mythic Words</a>
            <a href="sentence_skeptic_words.html">Sentence Skeptic Words</a>
            <a href="network_viz/index.html">Network Analysis</a>
            <a href="map/index.html">Place Map</a>
        </nav>

        <div class="container">
            {format_classification_metrics(metrics, 'Non-skeptical', 'Skeptical')}

            <h2>Predictors of Skeptical Content</h2>
            <p>These words and phrases are most strongly associated with skeptical content in Pausanias.</p>
            
            <table class="predictor-table">
                <thead>
                    <tr>
                        <th>Word/Phrase</th>
                        <th>English</th>
                        <th>Coefficient</th>
                        <th>Skeptical Count</th>
                        <th>Non-skeptical Count</th>
                        <th>p-value</th>
                        <th>q-value</th>
                    </tr>
                </thead>
                <tbody>
    """

    # Add skeptical predictors
    for _, row in skeptical_words.iterrows():
        english = row.get('english_translation', '')
        html_content += f"""
                    <tr>
                        <td class="skeptical-word">{html.escape(row['phrase'])}</td>
                        <td>{html.escape(english)}</td>
                        <td>{row['coefficient']:.4f}</td>
                        <td>{row['skeptical_count']}</td>
                        <td>{row['non_skeptical_count']}</td>
                        <td>{row['p_value']:.3g}</td>
                        <td>{row['q_value']:.3g}</td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
            
            <h2>Predictors of Non-skeptical Content</h2>
            <p>These words and phrases are most strongly associated with non-skeptical content in Pausanias.</p>
            
            <table class="predictor-table">
                <thead>
                    <tr>
                        <th>Word/Phrase</th>
                        <th>English</th>
                        <th>Coefficient</th>
                        <th>Skeptical Count</th>
                        <th>Non-skeptical Count</th>
                        <th>p-value</th>
                        <th>q-value</th>
                    </tr>
                </thead>
                <tbody>
    """

    # Add non-skeptical predictors
    for _, row in non_skeptical_words.iterrows():
        english = row.get('english_translation', '')
        html_content += f"""
                    <tr>
                        <td class="non-skeptical-word">{html.escape(row['phrase'])}</td>
                        <td>{html.escape(english)}</td>
                        <td>{row['coefficient']:.4f}</td>
                        <td>{row['skeptical_count']}</td>
                        <td>{row['non_skeptical_count']}</td>
                        <td>{row['p_value']:.3g}</td>
                        <td>{row['q_value']:.3g}</td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
            
            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """ from <a href=\"pausanias.sqlite\">pausanias.sqlite</a>
            </footer>
        </div>
    </body>
    </html>
    """
    
    # Write the file
    with open(os.path.join(output_dir, 'skeptic_words.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)


def generate_sentence_mythic_words_page(mythic_predictors, output_dir, title, metrics=None):
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

        <nav>
            <a href="index.html">Home</a>
            <a href="translation/index.html">Translation</a>
            <a href="mythic/index.html">Mythic Analysis</a>
            <a href="skepticism/index.html">Skepticism Analysis</a>
            <a href="mythic_words.html">Mythic Words</a>
            <a href="skeptic_words.html">Skeptic Words</a>
            <a href="sentences/index.html">Sentences</a>
            <a href="sentence_mythic_words.html" class="active">Sentence Mythic Words</a>
            <a href="sentence_skeptic_words.html">Sentence Skeptic Words</a>
            <a href="network_viz/index.html">Network Analysis</a>
            <a href="map/index.html">Place Map</a>
        </nav>

        <div class="container">
            {format_classification_metrics(metrics, 'Historical', 'Mythic')}

            <h2>Sentence Predictors of Mythic Content</h2>
            <table class="predictor-table">
                <thead>
                    <tr>
                        <th>Word/Phrase</th>
                        <th>English</th>
                        <th>Coefficient</th>
                        <th>Mythic Count</th>
                        <th>Non-mythic Count</th>
                        <th>p-value</th>
                        <th>q-value</th>
                    </tr>
                </thead>
                <tbody>
    """

    for _, row in mythic_words.iterrows():
        english = row.get('english_translation', '')
        html_content += f"""
                    <tr>
                        <td class="mythic-word">{html.escape(row['phrase'])}</td>
                        <td>{html.escape(english)}</td>
                        <td>{row['coefficient']:.4f}</td>
                        <td>{row['mythic_count']}</td>
                        <td>{row['non_mythic_count']}</td>
                        <td>{row['p_value']:.3g}</td>
                        <td>{row['q_value']:.3g}</td>
                    </tr>
        """

    html_content += """
                </tbody>
            </table>

            <h2>Sentence Predictors of Historical Content</h2>
            <table class="predictor-table">
                <thead>
                    <tr>
                        <th>Word/Phrase</th>
                        <th>English</th>
                        <th>Coefficient</th>
                        <th>Mythic Count</th>
                        <th>Non-mythic Count</th>
                        <th>p-value</th>
                        <th>q-value</th>
                    </tr>
                </thead>
                <tbody>
    """

    for _, row in historical_words.iterrows():
        english = row.get('english_translation', '')
        html_content += f"""
                    <tr>
                        <td class="historical-word">{html.escape(row['phrase'])}</td>
                        <td>{html.escape(english)}</td>
                        <td>{row['coefficient']:.4f}</td>
                        <td>{row['mythic_count']}</td>
                        <td>{row['non_mythic_count']}</td>
                        <td>{row['p_value']:.3g}</td>
                        <td>{row['q_value']:.3g}</td>
                    </tr>
        """

    html_content += """
                </tbody>
            </table>

            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """ from <a href=\"pausanias.sqlite\">pausanias.sqlite</a>
            </footer>
        </div>
    </body>
    </html>
    """

    with open(os.path.join(output_dir, 'sentence_mythic_words.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)


def generate_sentence_skeptic_words_page(skeptic_predictors, output_dir, title, metrics=None):
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

        <nav>
            <a href="index.html">Home</a>
            <a href="translation/index.html">Translation</a>
            <a href="mythic/index.html">Mythic Analysis</a>
            <a href="skepticism/index.html">Skepticism Analysis</a>
            <a href="mythic_words.html">Mythic Words</a>
            <a href="skeptic_words.html">Skeptic Words</a>
            <a href="sentences/index.html">Sentences</a>
            <a href="sentence_mythic_words.html">Sentence Mythic Words</a>
            <a href="sentence_skeptic_words.html" class="active">Sentence Skeptic Words</a>
            <a href="network_viz/index.html">Network Analysis</a>
            <a href="map/index.html">Place Map</a>
        </nav>

        <div class="container">
            {format_classification_metrics(metrics, 'Non-skeptical', 'Skeptical')}

            <h2>Sentence Predictors of Skeptical Content</h2>
            <table class="predictor-table">
                <thead>
                    <tr>
                        <th>Word/Phrase</th>
                        <th>English</th>
                        <th>Coefficient</th>
                        <th>Skeptical Count</th>
                        <th>Non-skeptical Count</th>
                        <th>p-value</th>
                        <th>q-value</th>
                    </tr>
                </thead>
                <tbody>
    """

    for _, row in skeptical_words.iterrows():
        english = row.get('english_translation', '')
        html_content += f"""
                    <tr>
                        <td class="skeptical-word">{html.escape(row['phrase'])}</td>
                        <td>{html.escape(english)}</td>
                        <td>{row['coefficient']:.4f}</td>
                        <td>{row['skeptical_count']}</td>
                        <td>{row['non_skeptical_count']}</td>
                        <td>{row['p_value']:.3g}</td>
                        <td>{row['q_value']:.3g}</td>
                    </tr>
        """

    html_content += """
                </tbody>
            </table>

            <h2>Sentence Predictors of Non-skeptical Content</h2>
            <table class="predictor-table">
                <thead>
                    <tr>
                        <th>Word/Phrase</th>
                        <th>English</th>
                        <th>Coefficient</th>
                        <th>Skeptical Count</th>
                        <th>Non-skeptical Count</th>
                        <th>p-value</th>
                        <th>q-value</th>
                    </tr>
                </thead>
                <tbody>
    """

    for _, row in non_skeptical_words.iterrows():
        english = row.get('english_translation', '')
        html_content += f"""
                    <tr>
                        <td class="non-skeptical-word">{html.escape(row['phrase'])}</td>
                        <td>{html.escape(english)}</td>
                        <td>{row['coefficient']:.4f}</td>
                        <td>{row['skeptical_count']}</td>
                        <td>{row['non_skeptical_count']}</td>
                        <td>{row['p_value']:.3g}</td>
                        <td>{row['q_value']:.3g}</td>
                    </tr>
        """

    html_content += """
                </tbody>
            </table>

            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """ from <a href=\"pausanias.sqlite\">pausanias.sqlite</a>
            </footer>
        </div>
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

    <nav>
        <a href=\"../index.html\">Home</a>
        <a href=\"../mythic/index.html\">Mythic Analysis</a>
        <a href=\"../skepticism/index.html\">Skepticism Analysis</a>
        <a href=\"../mythic_words.html\">Mythic Words</a>
        <a href=\"../skeptic_words.html\">Skeptic Words</a>
        <a href=\"index.html\" class=\"active\">Sentences</a>
        <a href=\"../sentence_mythic_words.html\">Sentence Mythic Words</a>
        <a href=\"../sentence_skeptic_words.html\">Sentence Skeptic Words</a>
        <a href=\"../network_viz/index.html\">Network Analysis</a>
    </nav>

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
            Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")} from <a href=\"../pausanias.sqlite\">pausanias.sqlite</a>
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

    <nav>
        <a href=\"../index.html\">Home</a>
        <a href=\"../mythic/index.html\">Mythic Analysis</a>
        <a href=\"../skepticism/index.html\">Skepticism Analysis</a>
        <a href=\"../mythic_words.html\">Mythic Words</a>
        <a href=\"../skeptic_words.html\">Skeptic Words</a>
        <a href=\"index.html\" class=\"active\">Sentences</a>
        <a href=\"../sentence_mythic_words.html\">Sentence Mythic Words</a>
        <a href=\"../sentence_skeptic_words.html\">Sentence Skeptic Words</a>
        <a href=\"../network_viz/index.html\">Network Analysis</a>
    </nav>

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
            Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")} from <a href=\"../pausanias.sqlite\">pausanias.sqlite</a>
        </footer>
    </div>
</body>
</html>
"""

    with open(os.path.join(sentences_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_content)


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

    <nav>
        <a href="../index.html">Home</a>
        <a href="../translation/index.html">Translation</a>
        <a href="../mythic/index.html">Mythic Analysis</a>
        <a href="../skepticism/index.html">Skepticism Analysis</a>
        <a href="../mythic_words.html">Mythic Words</a>
        <a href="../skeptic_words.html">Skeptic Words</a>
        <a href="../sentences/index.html">Sentences</a>
        <a href="../sentence_mythic_words.html">Sentence Mythic Words</a>
        <a href="../sentence_skeptic_words.html">Sentence Skeptic Words</a>
        <a href="../network_viz/index.html">Network Analysis</a>
        <a href="index.html" class="active">Place Map</a>
    </nav>

    <div class="container" style="max-width: 1000px;">
        <h2>Place Map</h2>
        <div class="map-stats" id="map-stats"></div>
        <div id="map"></div>

        <footer>
            Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")} from <a href="../pausanias.sqlite">pausanias.sqlite</a>
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


def _translation_nav(prefix, active=None):
    """Generate nav HTML for translation pages with correct relative paths."""
    links = [
        ("index.html", "Home", "home"),
        ("translation/index.html", "Translation", "translation"),
        ("mythic/index.html", "Mythic Analysis", "mythic"),
        ("skepticism/index.html", "Skepticism Analysis", "skepticism"),
        ("sentences/index.html", "Sentences", "sentences"),
        ("translation/nouns/index.html", "Noun Index", "nouns"),
        ("network_viz/index.html", "Network Analysis", "network"),
        ("map/index.html", "Place Map", "map"),
        ("progress/index.html", "Progress", "progress"),
    ]
    parts = []
    for href, label, key in links:
        cls = ' class="active"' if key == active else ""
        parts.append(f'<a href="{prefix}{href}"{cls}>{label}</a>')
    return "<nav>\n            " + "\n            ".join(parts) + "\n        </nav>"


def generate_translation_pages(passages, nouns_by_passage, noun_passages, output_dir, title, summaries=None):
    """Generate hierarchical translation pages: book > chapter > passage."""

    from .data import passage_id_sort_key

    translation_dir = os.path.join(output_dir, 'translation')
    os.makedirs(translation_dir, exist_ok=True)

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
