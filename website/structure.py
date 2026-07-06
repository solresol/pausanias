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
        box-sizing: border-box;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        width: 100%;
    }

    .wide-container {
        max-width: 1200px;
    }
    
    header {
        background-color: #5c5142;
        color: white;
        padding: 1em;
        text-align: center;
    }

    header p {
        margin-left: auto;
        margin-right: auto;
        max-width: 100%;
        overflow-wrap: anywhere;
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

    .site-nav {
        align-items: center;
        display: flex;
        flex-wrap: wrap;
        gap: 6px 22px;
        justify-content: center;
    }

    .site-nav a {
        margin: 0;
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

    .predictor-sort-controls {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 15px;
    }

    .predictor-sort-button {
        border: 1px solid #b9afa4;
        background-color: #f8f5f1;
        border-radius: 999px;
        color: #5c5142;
        cursor: pointer;
        font: inherit;
        padding: 6px 12px;
    }

    .predictor-sort-button.is-active {
        background-color: #5c5142;
        border-color: #5c5142;
        color: white;
    }

    .simplified-model {
        margin-top: 35px;
        padding: 20px;
        background-color: #f6f1ea;
        border-left: 6px solid #5c5142;
        border-radius: 6px;
    }

    .simplified-model h2 {
        margin-top: 0;
    }

    .simplified-rule,
    .simplified-comparison {
        font-size: 1.05em;
    }

    .simplified-points-table {
        margin-bottom: 0;
    }

    .points-value {
        font-weight: bold;
    }

    .confusion-section {
        margin: 18px 0 24px;
    }

    .confusion-intro {
        margin-bottom: 12px;
    }

    .confusion-grid {
        display: grid;
        gap: 16px;
        align-items: start;
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .confusion-card {
        background-color: #fffaf4;
        border: 1px solid #d9cec0;
        border-radius: 6px;
        min-width: 0;
        padding: 14px;
    }

    @media (max-width: 1000px) {
        .confusion-grid {
            grid-template-columns: 1fr;
        }
    }

    .confusion-card h3 {
        margin-top: 0;
        margin-bottom: 10px;
        font-size: 1em;
    }

    .confusion-table {
        table-layout: fixed;
        width: 100%;
        border-collapse: collapse;
    }

    .confusion-table th,
    .confusion-table td {
        border: 1px solid #d9cec0;
        padding: 8px;
        text-align: center;
    }

    .confusion-table thead th,
    .confusion-table tbody th {
        background-color: #eee9e3;
        font-weight: bold;
    }

    .confusion-corner {
        background-color: transparent;
        border-left: none;
        border-top: none;
    }

    .confusion-axis {
        background-color: #eee9e3;
        font-weight: bold;
    }

    .confusion-axis-predicted {
        text-align: right;
        padding-right: 12px;
    }

    .confusion-axis-actual {
        text-align: left;
        vertical-align: middle;
        padding-left: 8px;
    }

    .confusion-row-label {
        text-align: left;
        padding-left: 12px;
    }
    
    .predictor-table th, .predictor-table td {
        padding: 8px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }
    
    .predictor-table th {
        background-color: #eee9e3;
    }

    .predictor-table th.num {
        text-align: right;
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

    .hub-grid {
        display: grid;
        gap: 16px;
        grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
        margin: 20px 0;
    }

    .hub-card {
        background-color: #eee9e3;
        border-radius: 5px;
        padding: 18px;
    }

    .hub-card h3 {
        margin-top: 0;
    }

    .hub-card a {
        display: inline-block;
        margin-top: 8px;
        background-color: #5c5142;
        color: white;
        padding: 8px 14px;
        text-decoration: none;
        border-radius: 5px;
    }

    .hub-card a:hover {
        background-color: #776b5d;
    }

    .deprecated {
        border-left: 5px solid #9d8771;
    }

    .compact-list {
        margin: 10px 0;
        padding-left: 18px;
    }

    .note {
        background-color: #f6f1ea;
        border-left: 5px solid #9d8771;
        padding: 10px 12px;
    }

    .status-pill {
        border-radius: 999px;
        display: inline-block;
        font-size: 0.82em;
        font-weight: bold;
        padding: 2px 9px;
        white-space: nowrap;
    }

    .bucket-mythic {
        background-color: #fde8e4;
        color: #a63a22;
    }

    .bucket-historical {
        background-color: #e4eefb;
        color: #245f9f;
    }

    .bucket-other {
        background-color: #e8ece8;
        color: #4f604f;
    }

    .bucket-both {
        background-color: #f3e8fb;
        color: #6b3a9f;
    }

    .agree-cell {
        background-color: #eef5ee;
        font-weight: bold;
    }

    .metric-strip {
        display: grid;
        gap: 12px;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        margin: 16px 0 24px;
    }

    .metric-strip div {
        background-color: #eee9e3;
        border-radius: 5px;
        padding: 12px;
    }

    .metric-strip strong {
        display: block;
        color: #5c5142;
        font-size: 1.35em;
    }

    .metric-strip span {
        display: block;
        font-size: 0.9em;
    }

    .badge {
        background-color: #eee9e3;
        border-radius: 10px;
        font-size: 0.85em;
        padding: 2px 8px;
        white-space: nowrap;
    }

    .badge-good {
        background-color: #dcebd5;
        color: #2f5d2a;
    }

    .badge-bad {
        background-color: #f0dcd7;
        color: #7a3527;
    }

    .manto-network-layout {
        align-items: start;
        display: grid;
        gap: 18px;
        grid-template-columns: minmax(0, 1fr) minmax(260px, 340px);
        margin: 20px 0 28px;
    }

    .manto-network-panel {
        background-color: #fffaf4;
        border: 1px solid #d9cec0;
        border-radius: 6px;
        min-height: 520px;
        overflow: hidden;
        position: relative;
        width: 100%;
    }

    .manto-community-panel {
        min-height: 440px;
    }

    .manto-network-panel svg {
        display: block;
        height: 100%;
        min-height: inherit;
        width: 100%;
    }

    .manto-links line {
        cursor: pointer;
        stroke: #9c8d7f;
        stroke-opacity: 0.58;
    }

    .manto-links line:hover {
        stroke: #7f2d1f;
        stroke-opacity: 0.95;
    }

    .manto-nodes circle {
        cursor: pointer;
    }

    .manto-labels text {
        fill: #463d33;
        paint-order: stroke;
        pointer-events: none;
        stroke: #fffaf4;
        stroke-width: 3px;
    }

    .manto-network-detail {
        background-color: #f6f1ea;
        border-left: 5px solid #9d8771;
        border-radius: 6px;
        box-sizing: border-box;
        min-height: 180px;
        overflow-wrap: anywhere;
        padding: 14px;
    }

    .manto-network-tooltip {
        background-color: rgba(47, 36, 28, 0.94);
        border-radius: 5px;
        color: white;
        display: none;
        font-size: 0.9em;
        line-height: 1.35;
        max-width: min(420px, calc(100vw - 32px));
        padding: 10px 12px;
        pointer-events: none;
        position: absolute;
        z-index: 30;
    }

    @media (max-width: 960px) {
        .manto-network-layout {
            grid-template-columns: 1fr;
        }
    }

    .people-table {
        font-size: 0.92em;
        margin-bottom: 24px;
        width: 100%;
    }

    .people-headline-table td {
        font-weight: bold;
    }

    .people-visual-grid {
        display: grid;
        gap: 22px;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        margin: 22px 0 30px;
    }

    .people-viz-panel {
        background: #fbfaf7;
        border: 1px solid #d8d1c4;
        border-radius: 6px;
        padding: 16px;
    }

    .people-viz-panel h3 {
        margin-top: 0;
    }

    .people-svg-wrap {
        overflow-x: auto;
    }

    .people-chart-svg {
        display: block;
        height: auto;
        max-width: 100%;
        min-width: 0;
        width: 100%;
    }

    .people-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 14px;
        margin: 10px 0 16px;
    }

    .people-legend-item {
        align-items: center;
        display: inline-flex;
        gap: 6px;
        font-size: 0.9em;
    }

    .people-legend-swatch {
        border-radius: 3px;
        display: inline-block;
        height: 12px;
        width: 12px;
    }

    .people-class-anonymous-female {
        background-color: #d56f7f;
    }

    .people-class-named-female {
        background-color: #a23e73;
    }

    .people-class-anonymous-male {
        background-color: #4f96a2;
    }

    .people-class-named-male {
        background-color: #315f9f;
    }

    .people-stack-chart {
        display: grid;
        gap: 12px;
    }

    .people-stack-row {
        align-items: center;
        display: grid;
        gap: 10px;
        grid-template-columns: 86px minmax(160px, 1fr) 48px;
    }

    .people-stack-label,
    .people-stack-total {
        color: #4b4338;
        font-weight: bold;
    }

    .people-stack-total {
        text-align: right;
    }

    .people-stack-bar {
        background: #ece6dd;
        border-radius: 5px;
        display: flex;
        height: 30px;
        overflow: hidden;
    }

    .people-stack-segment {
        display: block;
        min-width: 1px;
    }

    .people-share-chart {
        display: grid;
        gap: 14px;
    }

    .people-share-row {
        display: grid;
        gap: 8px;
    }

    .people-share-label {
        color: #4b4338;
        font-weight: bold;
    }

    .people-share-meters {
        display: grid;
        gap: 8px;
    }

    .people-share-meter {
        align-items: center;
        display: grid;
        gap: 8px;
        grid-template-columns: 64px minmax(120px, 1fr) 56px;
    }

    .people-share-meter span {
        font-size: 0.9em;
    }

    .people-share-meter strong {
        text-align: right;
    }

    .people-meter {
        background: #ece6dd;
        border-radius: 999px;
        height: 12px;
        overflow: hidden;
    }

    .people-meter-fill {
        display: block;
        height: 100%;
    }

    .people-meter-fill.female {
        background: #a23e73;
    }

    .people-meter-fill.named {
        background: #315f9f;
    }

    .people-residual-table td {
        font-weight: bold;
    }

    .sentence-detail-table {
        font-size: 0.9em;
    }

    .sentence-detail-table .num,
    .predictor-table .num {
        text-align: right;
        white-space: nowrap;
    }

    .greek-cell {
        font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif;
        line-height: 1.55;
    }

    .lemma-cell {
        color: #4b4338;
    }

    .grammar-sentence-card {
        background: #fffdf8;
        border: 1px solid #d8d1c4;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        margin: 22px 0;
        padding: 18px;
    }

    .grammar-sentence-header {
        align-items: flex-start;
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        justify-content: space-between;
    }

    .grammar-sentence-header h3 {
        margin-top: 0;
    }

    .ordinal {
        color: #5c5142;
        font-size: 0.8em;
        font-weight: bold;
        letter-spacing: 0;
        text-transform: uppercase;
    }

    .grammar-metrics {
        display: grid;
        gap: 8px;
        grid-template-columns: repeat(4, minmax(74px, 1fr));
        margin: 0;
    }

    .grammar-metrics div {
        background-color: #f3eee6;
        border: 1px solid #d8d1c4;
        border-radius: 6px;
        padding: 8px 10px;
    }

    .grammar-metrics dt {
        color: #776b5d;
        font-size: 0.75em;
        text-transform: uppercase;
    }

    .grammar-metrics dd {
        font-weight: bold;
        margin: 2px 0 0;
    }

    .grammar-sentence-text {
        font-size: 1.18em;
        margin: 16px 0 10px;
    }

    .grammar-sentence-note {
        background: #fff6df;
        border-left: 5px solid #b88a35;
        color: #6b4a15;
        padding: 8px 10px;
    }

    .grammar-tree-wrap {
        background: #fbfaf7;
        border: 1px solid #d8d1c4;
        border-radius: 6px;
        margin: 14px 0;
        overflow-x: auto;
    }

    .grammar-parse-tree {
        display: block;
        min-width: 100%;
    }

    .grammar-axis {
        stroke: #d8d1c4;
        stroke-width: 1;
    }

    .grammar-arc {
        fill: none;
        opacity: 0.82;
        stroke: #4f7b78;
        stroke-width: 1.3;
    }

    .grammar-arc-label,
    .grammar-root-label {
        fill: #4b625f;
        font-size: 11px;
        paint-order: stroke;
        stroke: #fbfaf7;
        stroke-linejoin: round;
        stroke-width: 4px;
    }

    .grammar-root-line {
        stroke: #8c6f2a;
        stroke-dasharray: 4 4;
        stroke-width: 1.3;
    }

    .grammar-token-dot {
        fill: #4f7b78;
    }

    .grammar-token-index {
        fill: #776b5d;
        font-size: 11px;
        font-weight: bold;
    }

    .grammar-token-form {
        fill: #333;
        font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif;
        font-size: 15px;
    }

    .grammar-token-meta {
        fill: #776b5d;
        font-size: 11px;
    }

    .grammar-table-wrap {
        max-width: 100%;
        overflow-x: auto;
    }

    .grammar-token-table {
        font-size: 0.86em;
        min-width: 0;
        table-layout: fixed;
        width: 100%;
    }

    .grammar-token-table th,
    .grammar-token-table td {
        overflow-wrap: anywhere;
        vertical-align: top;
    }

    .grammar-token-table th:nth-child(1),
    .grammar-token-table td:nth-child(1),
    .grammar-token-table th:nth-child(4),
    .grammar-token-table td:nth-child(4),
    .grammar-token-table th:nth-child(5),
    .grammar-token-table td:nth-child(5),
    .grammar-token-table th:nth-child(9),
    .grammar-token-table td:nth-child(9) {
        width: 7%;
    }

    .grammar-token-table th:nth-child(2),
    .grammar-token-table td:nth-child(2),
    .grammar-token-table th:nth-child(3),
    .grammar-token-table td:nth-child(3),
    .grammar-token-table th:nth-child(7),
    .grammar-token-table td:nth-child(7),
    .grammar-token-table th:nth-child(8),
    .grammar-token-table td:nth-child(8) {
        width: 10%;
    }

    .grammar-token-table th:nth-child(6),
    .grammar-token-table td:nth-child(6) {
        width: 16%;
    }

    .grammar-token-table th:nth-child(10),
    .grammar-token-table td:nth-child(10) {
        width: 16%;
    }

    .upos {
        background-color: #e1eeeb;
        border-radius: 4px;
        color: #315c59;
        display: inline-block;
        font-size: 0.86em;
        font-weight: bold;
        padding: 2px 6px;
    }

    .grammar-empty-tree {
        color: #776b5d;
        padding: 18px;
    }

    .grammar-passage-link {
        font-weight: bold;
    }

    .stylometry-feature-card p {
        margin-bottom: 10px;
    }

    .stylometry-feature-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 12px;
    }

    .stylometry-feature-tags span {
        background-color: #e8f0ed;
        border: 1px solid #bfd2ca;
        border-radius: 4px;
        color: #335f59;
        display: inline-block;
        font-size: 0.82em;
        padding: 3px 7px;
    }

    .stylometry-notes {
        background-color: #fff9eb;
        border-left: 5px solid #b88a35;
        padding: 12px 16px 12px 28px;
    }

    .stylometry-controls {
        align-items: center;
        display: flex;
        flex-wrap: wrap;
        gap: 10px 14px;
        margin: 18px 0;
    }

    .stylometry-controls label {
        font-weight: bold;
    }

    .stylometry-controls select {
        border: 1px solid #b9afa4;
        border-radius: 4px;
        color: #333;
        font: inherit;
        min-width: 260px;
        padding: 7px 9px;
    }

    .stylometry-method {
        color: #5c5142;
        font-weight: bold;
    }

    .stylometry-chart-wrap {
        background: #fffdf8;
        border: 1px solid #d8d1c4;
        border-radius: 6px;
        margin-top: 14px;
        overflow-x: auto;
        position: relative;
    }

    .stylometry-chart {
        display: block;
        min-height: 520px;
        min-width: 860px;
        width: 100%;
    }

    .stylometry-axis {
        stroke: #c9c0b3;
        stroke-width: 1;
    }

    .stylometry-axis-label {
        fill: #776b5d;
        font-size: 13px;
    }

    .stylometry-point {
        cursor: pointer;
        opacity: 0.88;
        stroke: white;
        stroke-width: 1.5px;
    }

    .stylometry-point:hover {
        opacity: 1;
        stroke: #222;
    }

    .stylometry-point-label {
        fill: #333;
        font-size: 11px;
        paint-order: stroke;
        pointer-events: none;
        stroke: #fffdf8;
        stroke-linejoin: round;
        stroke-width: 4px;
    }

    .stylometry-tooltip {
        background: rgba(38, 35, 31, 0.94);
        border-radius: 5px;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);
        color: white;
        font-size: 0.9em;
        line-height: 1.35;
        max-width: 280px;
        padding: 10px 12px;
        pointer-events: none;
        position: absolute;
        z-index: 3;
    }

    .stylometry-tooltip hr {
        border: 0;
        border-top: 1px solid rgba(255, 255, 255, 0.28);
        margin: 7px 0;
    }

    .stylometry-legend {
        align-items: center;
        display: flex;
        flex-wrap: wrap;
        gap: 8px 12px;
    }

    .legend-dot {
        border-radius: 50%;
        display: inline-block;
        height: 11px;
        width: 11px;
    }

    .legend-dot.mess {
        background: #b94a38;
    }

    .legend-dot.book4 {
        background: #9a762d;
    }

    .legend-dot.book8 {
        background: #397d7a;
    }

    .legend-dot.other {
        background: #5f6673;
    }

    .stylometry-stat-section {
        border-top: 1px solid #d8d1c4;
        margin-top: 30px;
        padding-top: 18px;
    }

    .stylometry-comparison-table {
        font-size: 0.9em;
    }

    .stylometry-delta-grid {
        display: grid;
        gap: 18px;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }

    .stylometry-delta-card {
        background: #fbfaf7;
        border: 1px solid #d8d1c4;
        border-radius: 6px;
        margin: 16px 0;
        padding: 14px;
    }

    .stylometry-delta-card h4,
    .stylometry-delta-card h5 {
        margin-top: 0;
    }

    .stylometry-delta-list {
        margin-bottom: 0;
        padding-left: 22px;
    }

    .stylometry-delta-list li {
        margin: 4px 0;
    }

    .stylometry-delta-list span {
        color: #5c5142;
        font-weight: bold;
        margin-left: 5px;
    }

    @media (max-width: 720px) {
        body {
            overflow-x: hidden;
        }

        header,
        nav,
        .container {
            box-sizing: border-box;
            max-width: 100vw;
            width: 100vw;
        }

        header p,
        .container p {
            max-width: 42ch;
            overflow-wrap: anywhere;
        }

        .site-nav {
            max-width: 100%;
            overflow-x: auto;
        }

        .grammar-metrics {
            grid-template-columns: repeat(2, minmax(96px, 1fr));
            width: 100%;
        }

        .grammar-sentence-card {
            padding: 14px;
        }

        .grammar-token-table {
            min-width: 760px;
        }

        .stylometry-controls select {
            min-width: 100%;
        }

        .metric-strip {
            grid-template-columns: 1fr;
        }

        .metric-strip div {
            min-width: 0;
        }

        .people-stack-row {
            grid-template-columns: 1fr;
        }

        .people-stack-total {
            text-align: left;
        }

        .people-table {
            display: block;
            max-width: 100%;
            overflow-x: auto;
            white-space: nowrap;
        }

        .people-visual-grid {
            grid-template-columns: 1fr;
        }

        .people-viz-panel {
            padding: 12px;
        }

        .people-share-meter {
            grid-template-columns: 58px minmax(80px, 1fr) 52px;
        }
    }

    @media (max-width: 480px) {
        header p,
        .container p {
            max-width: 320px;
        }

        .metric-strip div,
        .people-viz-panel {
            max-width: 320px;
        }

        .people-table {
            max-width: 350px;
        }
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
