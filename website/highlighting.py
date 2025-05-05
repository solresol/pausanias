"""Text highlighting and predictor mapping functions."""

import numpy as np
import re
import html
from sklearn.preprocessing import MinMaxScaler

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