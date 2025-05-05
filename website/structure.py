"""Website structure and CSS creation."""

import os

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