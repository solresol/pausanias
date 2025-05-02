#!/usr/bin/env python

import argparse
import sqlite3
import sys
import os
import re
import numpy as np
import pandas as pd
from datetime import datetime
import html
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler

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

def passage_id_sort_key(passage_id):
    """Create a sort key for passage IDs in the format X.Y.Z."""
    parts = passage_id.split('.')
    # Convert each part to integer for proper numerical sorting
    return tuple(int(part) for part in parts)

def get_proper_nouns_by_passage(conn):
    """Get proper nouns (in nominative form) grouped by passage."""
    query = """
    SELECT passage_id, reference_form
    FROM proper_nouns
    ORDER BY passage_id, reference_form
    """
    
    df = pd.read_sql_query(query, conn)
    
    # Group by passage_id
    proper_nouns_dict = {}
    for passage_id, group in df.groupby('passage_id'):
        proper_nouns_dict[passage_id] = group['reference_form'].tolist()
    
    return proper_nouns_dict

def get_translations(conn):
    """Get all available translations."""
    query = """
    SELECT passage_id, english_translation
    FROM translations
    """
    
    df = pd.read_sql_query(query, conn)
    # Convert to dictionary for easy lookup
    translations_dict = dict(zip(df['passage_id'], df['english_translation']))
    return translations_dict

def get_analyzed_passages(conn, limit=None):
    """Get passages that have been analyzed for both mythicness and skepticism."""
    query = """
    SELECT p.id, p.passage, p.references_mythic_era, p.expresses_scepticism,
           t.english_translation
    FROM passages p
    LEFT JOIN translations t ON p.id = t.passage_id
    WHERE p.references_mythic_era IS NOT NULL
    AND p.expresses_scepticism IS NOT NULL
    ORDER BY p.id
    """
    
    df = pd.read_sql_query(query, conn)
    df['sort_key'] = df['id'].apply(passage_id_sort_key)
    df = df.sort_values('sort_key')
    
    # Remove the sort_key column as it's no longer needed
    df = df.drop('sort_key', axis=1)
    if limit:
        df = df.head(limit)

    return df

def get_mythicness_predictors(conn):
    """Get words/phrases that predict mythicness/historicity."""
    query = """
    SELECT phrase, coefficient, is_mythic
    FROM mythicness_predictors
    ORDER BY coefficient DESC
    """
    
    df = pd.read_sql_query(query, conn)
    return df

def get_skepticism_predictors(conn):
    """Get words/phrases that predict skepticism/non-skepticism."""
    query = """
    SELECT phrase, coefficient, is_skeptical
    FROM skepticism_predictors
    ORDER BY coefficient DESC
    """
    
    df = pd.read_sql_query(query, conn)
    return df

def create_website_structure(output_dir):
    """Create the directory structure for the website."""
    # Create main directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create CSS directory
    css_dir = os.path.join(output_dir, 'css')
    if not os.path.exists(css_dir):
        os.makedirs(css_dir)
    
    # Create CSS file
    css_content = """
    body {
        font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif;
        line-height: 1.6;
        margin: 0;
        padding: 0;
        background-color: #f9f8f4;
        color: #333;
    }
    
    .container {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }
    
    header {
        background-color: #5c5142;
        color: white;
        padding: 1em;
        text-align: center;
    }
    
    nav {
        background-color: #776b5d;
        padding: 0.5em;
        text-align: center;
    }
    
    nav a {
        color: white;
        margin: 0 15px;
        text-decoration: none;
        font-weight: bold;
    }
    
    nav a:hover {
        text-decoration: underline;
    }
    
    nav a.active {
        text-decoration: underline;
    }
    
    h1, h2, h3 {
        color: #5c5142;
    }
    
    .passage {
        margin-bottom: 30px;
        border-bottom: 1px solid #ddd;
        padding-bottom: 20px;
    }
    
    .passage-header {
        background-color: #eee9e3;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }

    .passage-container {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        margin-bottom: 20px;
    }
    
    .greek-text {
        flex: 1;
        min-width: 300px;
        padding: 15px;
    }
    
    .english-translation {
        flex: 1;
        min-width: 300px;
        background-color: #f5f5f5;
        padding: 15px;
        border-radius: 5px;
        border-left: 3px solid #5c5142;
    }
    
    .passage-id {
        font-weight: bold;
        color: #5c5142;
    }

    .translation-header {
        font-weight: bold;
        margin-bottom: 10px;
        color: #5c5142;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .passage-container {
            flex-direction: column;
        }
    }


    .proper-nouns {
        margin-top: 15px;
        padding-top: 10px;
        font-size: 0.6em;
        border-radius: 5px;
        border: 2px solid #5c5142;
    }
    
    .proper-noun-tag {
        display: inline-block;
        background-color: #eee9e3;
        padding: 3px 8px;
        margin: 2px;
        border-radius: 12px;
        font-style: italic;
    }
    
    .proper-noun-header {
        background-color: #eee9e3;
        font-weight: bold;
        margin-top: 12px;
        margin-bottom: 5px;
        color: #5c5142;
    }
    
    .mythic {
        font-style: italic;
    }
    
    .non-skeptical {
        font-weight: bold;
    }
    
    .legend {
        margin-top: 20px;
        padding: 15px;
        background-color: #eee9e3;
        border-radius: 5px;
    }
    
    .legend-item {
        display: inline-block;
        margin-right: 20px;
        margin-bottom: 10px;
    }
    
    .color-sample {
        display: inline-block;
        width: 20px;
        height: 20px;
        margin-right: 5px;
        vertical-align: middle;
    }
    
    .historical-sample {
        background-color: #0066cc;
    }
    
    .mythic-sample {
        background-color: #cc3300;
    }
    
    .skeptical-sample {
        background-color: #009933;
    }
    
    .non-skeptical-sample {
        background-color: #cc6600;
    }
    
    .predictor-table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
    }
    
    .predictor-table th, .predictor-table td {
        padding: 8px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }
    
    .predictor-table th {
        background-color: #eee9e3;
    }
    
    .predictor-table tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    
    .predictor-table tr:hover {
        background-color: #ddd;
    }
    
    .mythic-word {
        color: #cc3300;
    }
    
    .historical-word {
        color: #0066cc;
    }
    
    .skeptical-word {
        color: #009933;
    }
    
    .non-skeptical-word {
        color: #cc6600;
    }
    
    .home-card {
        background-color: #eee9e3;
        border-radius: 5px;
        padding: 20px;
        margin: 20px 0;
        text-align: center;
    }
    
    .home-card h2 {
        margin-top: 0;
    }
    
    .home-card a {
        display: inline-block;
        margin-top: 10px;
        background-color: #5c5142;
        color: white;
        padding: 10px 20px;
        text-decoration: none;
        border-radius: 5px;
    }
    
    .home-card a:hover {
        background-color: #776b5d;
    }
    
    footer {
        text-align: center;
        margin-top: 30px;
        padding: 10px;
        background-color: #eee9e3;
        font-size: 0.8em;
    }
    """
    
    with open(os.path.join(css_dir, 'style.css'), 'w') as f:
        f.write(css_content)
    
    return output_dir, css_dir

def create_predictor_maps(mythic_predictors, skeptic_predictors):
    """Create maps from words/phrases to their coefficients and color values."""
    # Normalize coefficients to range [0, 1] for color intensity
    mythic_scaler = MinMaxScaler(feature_range=(0.3, 1.0))
    skeptic_scaler = MinMaxScaler(feature_range=(0.3, 1.0))
    
    # Split predictors by mythic/historical and skeptical/non-skeptical
    mythic_positive = mythic_predictors[mythic_predictors['is_mythic'] == 1]
    mythic_negative = mythic_predictors[mythic_predictors['is_mythic'] == 0]
    
    skeptic_positive = skeptic_predictors[skeptic_predictors['is_skeptical'] == 1]
    skeptic_negative = skeptic_predictors[skeptic_predictors['is_skeptical'] == 0]
    
    # Scale coefficients for color intensity
    if not mythic_positive.empty:
        mythic_positive['intensity'] = mythic_scaler.fit_transform(np.abs(mythic_positive['coefficient']).values.reshape(-1, 1))
    if not mythic_negative.empty:
        mythic_negative['intensity'] = mythic_scaler.fit_transform(np.abs(mythic_negative['coefficient']).values.reshape(-1, 1))
    if not skeptic_positive.empty:
        skeptic_positive['intensity'] = skeptic_scaler.fit_transform(np.abs(skeptic_positive['coefficient']).values.reshape(-1, 1))
    if not skeptic_negative.empty:
        skeptic_negative['intensity'] = skeptic_scaler.fit_transform(np.abs(skeptic_negative['coefficient']).values.reshape(-1, 1))
    
    # Create maps for word to color
    mythic_color_map = {}
    for _, row in mythic_positive.iterrows():
        # Red for mythic (warm color)
        intensity = int(row['intensity'] * 255)
        mythic_color_map[row['phrase']] = f"rgb({intensity}, 0, 0)"
    
    for _, row in mythic_negative.iterrows():
        # Blue for historical (cool color)
        intensity = int(row['intensity'] * 255)
        mythic_color_map[row['phrase']] = f"rgb(0, 0, {intensity})"
    
    skeptic_color_map = {}
    for _, row in skeptic_positive.iterrows():
        # Green for skeptical
        intensity = int(row['intensity'] * 255)
        skeptic_color_map[row['phrase']] = f"rgb(0, {intensity}, 0)"
    
    for _, row in skeptic_negative.iterrows():
        # Orange for non-skeptical
        intensity = int(row['intensity'] * 255)
        skeptic_color_map[row['phrase']] = f"rgb({intensity}, {intensity//2}, 0)"
    
    # Create maps for word to class
    mythic_class_map = {}
    for _, row in mythic_predictors.iterrows():
        mythic_class_map[row['phrase']] = 'mythic' if row['is_mythic'] == 1 else 'historical'
    
    skeptic_class_map = {}
    for _, row in skeptic_predictors.iterrows():
        skeptic_class_map[row['phrase']] = 'skeptical' if row['is_skeptical'] == 1 else 'non-skeptical'
    
    return mythic_color_map, skeptic_color_map, mythic_class_map, skeptic_class_map

def highlight_passage(passage, predictor_map, color_map, class_map, is_mythic_page=True):
    """Highlight words in the passage based on their predictive power."""
    # Escape HTML characters
    highlighted_passage = html.escape(passage)
    
    # Sort predictors by length (longest first) to avoid partial matches
    predictors = sorted(predictor_map.keys(), key=len, reverse=True)
    
    # Replace each predictor with a colored version
    for predictor in predictors:
        if predictor in passage:
            color = color_map.get(predictor, 'black')
            css_class = class_map.get(predictor, '')
            
            # Add appropriate styling based on page type and word classification
            style_class = ''
            if is_mythic_page:
                if css_class == 'mythic':
                    style_class = ' mythic'
            else:  # skepticism page
                if css_class == 'non-skeptical':
                    style_class = ' non-skeptical'
            
            # Create a regex pattern that matches the whole word/phrase
            pattern = r'\b' + re.escape(predictor) + r'\b'
            
            # Highlight the word/phrase
            replacement = f'<span style="color: {color};" class="{css_class}{style_class}">{predictor}</span>'
            highlighted_passage = re.sub(pattern, replacement, highlighted_passage)
    
    return highlighted_passage

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
            <a href="mythic.html">Mythic Analysis</a>
            <a href="skepticism.html">Skepticism Analysis</a>
            <a href="mythic_words.html">Mythic Words</a>
            <a href="skeptic_words.html">Skeptic Words</a>
        </nav>
        
        <div class="container">
            <h2>Welcome to the Pausanias Analysis Project</h2>
            
            <p>This site presents an analysis of Pausanias' "Description of Greece", focusing on two key aspects:</p>
            
            <div class="home-card">
                <h2>Mythic vs. Historical Content</h2>
                <p>Explore passages with mythical content highlighted in warm colors and italics, 
                   while historical content appears in cool colors.</p>
                <a href="mythic.html">View Mythic Analysis</a>
            </div>
            
            <div class="home-card">
                <h2>Expression of Skepticism</h2>
                <p>Discover how Pausanias expresses skepticism (or credulity) through his writing. 
                   Skeptical content is highlighted in green, while non-skeptical appears in orange and bold.</p>
                <a href="skepticism.html">View Skepticism Analysis</a>
            </div>
            
            <div class="home-card">
                <h2>Predictive Words and Phrases</h2>
                <p>Examine the specific words and phrases that are most strongly associated with mythic content and skepticism.</p>
                <a href="mythic_words.html">Mythic Predictors</a>
                <a href="skeptic_words.html">Skepticism Predictors</a>
            </div>
            
            <footer>
                Site last updated on {timestamp}
            </footer>
        </div>
    </body>
    </html>
    """
    
    # Write the file
    with open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

def generate_mythic_page(passages_df, mythic_color_map, mythic_class_map, proper_nouns_dict, output_dir, title):
    """Generate the page showing mythic aspects of passages."""
    html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Mythic Analysis</title>
        <link rel="stylesheet" href="css/style.css">
    </head>
    <body>
        <header>
            <h1>{title}</h1>
            <p>Analysis of Mythic vs. Historical Elements in Pausanias</p>
        </header>
        
        <nav>
            <a href="index.html">Home</a>
            <a href="mythic.html" class="active">Mythic Analysis</a>
            <a href="skepticism.html">Skepticism Analysis</a>
            <a href="mythic_words.html">Mythic Words</a>
            <a href="skeptic_words.html">Skeptic Words</a>
        </nav>
        
        <div class="container">
            <div class="legend">
                <h3>Legend:</h3>
                <div class="legend-item">
                    <span class="color-sample mythic-sample"></span> Mythic content (warmer colors, <span class="mythic">italics</span>)
                </div>
                <div class="legend-item">
                    <span class="color-sample historical-sample"></span> Historical content (cooler colors)
                </div>
                <p>Color intensity indicates the strength of the predictive word or phrase.</p>
            </div>
            
            <h2>Passages</h2>
    """
    
    # Add each passage with highlighting
    for _, row in passages_df.iterrows():
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
            <div class="passage">
                <div class="passage-header">
                    <span class="passage-id">Passage {passage_id}</span>
                    <span class="passage-class">Class: {'Mythic' if is_mythic else 'Historical'}</span>
                </div>
                <div class="passage-container">
                     <div class="greek-text">
                         {highlighted_passage}
        """

        if proper_nouns:
            html_content += f"""
                        <div class="proper-nouns">
                            <div class="proper-noun-header">Proper Nouns:</div>
            """
            
            for noun in sorted(proper_nouns):
                html_content += f"""
                            <span class="proper-noun-tag">{html.escape(noun)}</span>
                """
            
            html_content += """
                        </div>
            """

        html_content += """
                     </div>
        """

        if translation and not pd.isna(translation):
            html_content += f"""
                    <div class="english-translation">
                        <!-- <div class="translation-header">English Translation:</div> -->
                        {translation}
                    </div>
            """

    html_content += """
                </div>
            </div>
        """
    
    # Close the HTML
    html_content += """
            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """
            </footer>
        </div>
    </body>
    </html>
    """
    
    # Write the file
    with open(os.path.join(output_dir, 'mythic.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

def generate_skepticism_page(passages_df, skeptic_color_map, skeptic_class_map, proper_nouns_dict, output_dir, title):
    """Generate the page showing skeptical aspects of passages."""
    html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Skepticism Analysis</title>
        <link rel="stylesheet" href="css/style.css">
    </head>
    <body>
        <header>
            <h1>{title}</h1>
            <p>Analysis of Skepticism in Pausanias</p>
        </header>
        
        <nav>
            <a href="index.html">Home</a>
            <a href="mythic.html">Mythic Analysis</a>
            <a href="skepticism.html" class="active">Skepticism Analysis</a>
            <a href="mythic_words.html">Mythic Words</a>
            <a href="skeptic_words.html">Skeptic Words</a>
        </nav>
        
        <div class="container">
            <div class="legend">
                <h3>Legend:</h3>
                <div class="legend-item">
                    <span class="color-sample skeptical-sample"></span> Skeptical content (green)
                </div>
                <div class="legend-item">
                    <span class="color-sample non-skeptical-sample"></span> Non-skeptical content (orange, <strong>bold</strong>)
                </div>
                <p>Color intensity indicates the strength of the predictive word or phrase.</p>
            </div>
            
            <h2>Passages</h2>
    """
    
    # Add each passage with highlighting
    for _, row in passages_df.iterrows():
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
            <div class="passage">
                <div class="passage-header">
                    <span class="passage-id">Passage {passage_id}</span>
                    <span class="passage-class">Class: {'Skeptical' if is_skeptical else 'Non-skeptical'}</span>
                </div>
                <div class="passage-container">
                   <div class="greek-text">
                    {highlighted_passage}
        """

        if proper_nouns:
            html_content += f"""
                        <div class="proper-nouns">
                            <div class="proper-noun-header">Proper Nouns:</div>
            """
            
            for noun in sorted(proper_nouns):
                html_content += f"""
                            <span class="proper-noun-tag">{html.escape(noun)}</span>
                """
            
            html_content += """
                        </div>
            """
        html_content += """
                   </div>
        """

        if translation and not pd.isna(translation):
            html_content += f"""
                    <div class="english-translation">
                        <!--<div class="translation-header">English Translation:</div>-->
                        {translation}
                    </div>
            """

        html_content += """
            </div>
        </div>
        """
    
    # Close the HTML
    html_content += """
            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """
            </footer>
        </div>
    </body>
    </html>
    """
    
    # Write the file
    with open(os.path.join(output_dir, 'skepticism.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

def generate_mythic_words_page(mythic_predictors, output_dir, title):
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
            <a href="mythic.html">Mythic Analysis</a>
            <a href="skepticism.html">Skepticism Analysis</a>
            <a href="mythic_words.html" class="active">Mythic Words</a>
            <a href="skeptic_words.html">Skeptic Words</a>
        </nav>
        
        <div class="container">
            <h2>Predictors of Mythic Content</h2>
            <p>These words and phrases are most strongly associated with mythic content in Pausanias.</p>
            
            <table class="predictor-table">
                <thead>
                    <tr>
                        <th>Word/Phrase</th>
                        <th>Coefficient</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Add mythic predictors
    for _, row in mythic_words.iterrows():
        html_content += f"""
                    <tr>
                        <td class="mythic-word">{html.escape(row['phrase'])}</td>
                        <td>{row['coefficient']:.4f}</td>
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
                        <th>Coefficient</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Add historical predictors
    for _, row in historical_words.iterrows():
        html_content += f"""
                    <tr>
                        <td class="historical-word">{html.escape(row['phrase'])}</td>
                        <td>{row['coefficient']:.4f}</td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
            
            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """
            </footer>
        </div>
    </body>
    </html>
    """
    
    # Write the file
    with open(os.path.join(output_dir, 'mythic_words.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

def generate_skeptic_words_page(skeptic_predictors, output_dir, title):
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
            <a href="mythic.html">Mythic Analysis</a>
            <a href="skepticism.html">Skepticism Analysis</a>
            <a href="mythic_words.html">Mythic Words</a>
            <a href="skeptic_words.html" class="active">Skeptic Words</a>
        </nav>
        
        <div class="container">
            <h2>Predictors of Skeptical Content</h2>
            <p>These words and phrases are most strongly associated with skeptical content in Pausanias.</p>
            
            <table class="predictor-table">
                <thead>
                    <tr>
                        <th>Word/Phrase</th>
                        <th>Coefficient</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Add skeptical predictors
    for _, row in skeptical_words.iterrows():
        html_content += f"""
                    <tr>
                        <td class="skeptical-word">{html.escape(row['phrase'])}</td>
                        <td>{row['coefficient']:.4f}</td>
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
                        <th>Coefficient</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Add non-skeptical predictors
    for _, row in non_skeptical_words.iterrows():
        html_content += f"""
                    <tr>
                        <td class="non-skeptical-word">{html.escape(row['phrase'])}</td>
                        <td>{row['coefficient']:.4f}</td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
            
            <footer>
                Generated on """ + datetime.now().strftime("%Y-%m-%d at %H:%M:%S") + """
            </footer>
        </div>
    </body>
    </html>
    """
    
    # Write the file
    with open(os.path.join(output_dir, 'skeptic_words.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == '__main__':
    args = parse_arguments()
    
    # Connect to the database
    conn = sqlite3.connect(args.database)
    
    try:
        # Get data from database
        passages_df = get_analyzed_passages(conn, args.max_passages)
        mythic_predictors = get_mythicness_predictors(conn)
        skeptic_predictors = get_skepticism_predictors(conn)
        proper_nouns_dict = get_proper_nouns_by_passage(conn)
        
        if len(passages_df) == 0:
            print("No analyzed passages found in the database.")
            sys.exit(0)
        
        if len(mythic_predictors) == 0 or len(skeptic_predictors) == 0:
            print("No predictor data found in the database. Run the analysis program first.")
            sys.exit(1)
        
        print(f"Found {len(passages_df)} analyzed passages.")
        print(f"Found {len(mythic_predictors)} mythicness predictors.")
        print(f"Found {len(skeptic_predictors)} skepticism predictors.")
        
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
        generate_mythic_words_page(mythic_predictors, output_dir, args.title)
        generate_skeptic_words_page(skeptic_predictors, output_dir, args.title)
        
        print(f"Website generated successfully in '{output_dir}'")
        print(f"Open '{os.path.join(output_dir, 'index.html')}' in a web browser to view it.")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    
    finally:
        conn.close()        
