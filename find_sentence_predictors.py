#!/usr/bin/env python

import argparse
import sqlite3
import sys
import re
import unicodedata
import numpy as np
import pandas as pd
from collections import Counter
from datetime import datetime

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, precision_recall_fscore_support, accuracy_score, confusion_matrix
import joblib

from stats_utils import compute_p_q_values

TOKEN_PATTERN = re.compile(r"(?u)\b\w\w+\b")


def normalize_stopwords(stopwords):
    """Normalize stopwords to match the vectorizer's preprocessing.

    Uses casefold() for proper Unicode case-insensitive comparison,
    which correctly handles Greek final sigma (ς → σ).

    NFC normalization is applied after casefold to match the
    casefold_preprocessor behavior and ensure stopwords match tokens.
    """

    normalized = []
    for word in stopwords:
        # Must match casefold_preprocessor: casefold + NFC
        normalized_word = unicodedata.normalize('NFC', word.casefold())
        tokens = TOKEN_PATTERN.findall(normalized_word)
        normalized.extend(tokens)

    return list(dict.fromkeys(normalized))


def casefold_preprocessor(text):
    """Custom preprocessor using casefold() for proper Greek handling.

    Python's casefold() correctly converts Greek final sigma (ς) to
    regular sigma (σ), which is the proper Unicode behavior for
    case-insensitive comparison. sklearn's default uses lower() which
    does not handle this correctly.

    NFC normalization is applied after casefold to recompose characters.
    casefold() can decompose precomposed Greek characters (e.g., ῆ → η + ͂),
    and these combining marks break word boundaries in the tokenizer regex.
    """
    return unicodedata.normalize('NFC', text.casefold())

def parse_arguments():
    parser = argparse.ArgumentParser(description="Create TF-IDF and logistic regression models for Pausanias sentences")
    parser.add_argument("--database", default="pausanias.sqlite", 
                        help="SQLite database file (default: pausanias.sqlite)")
    parser.add_argument("--min-samples", type=int, default=20,
                        help="Minimum number of samples required to build models (default: 20)")
    parser.add_argument("--test-size", type=float, default=0.2,
                        help="Proportion of data to use for testing (default: 0.2)")
    parser.add_argument("--max-features", type=int, default=1000,
                        help="Maximum number of features for TF-IDF vectorizer (default: 1000)")
    parser.add_argument("--ngram-range", type=str, default="1,2",
                        help="N-gram range for TF-IDF vectorizer, format: min,max (default: 1,2)")
    parser.add_argument("--top-features", type=int, default=30,
                        help="Number of top predictive features to report (default: 30)")
    parser.add_argument("--save-models", action="store_true", default=False,
                        help="Save trained models to disk")
    
    return parser.parse_args()

def create_predictor_tables(conn):
    """Create tables for storing predictive words/phrases for sentences."""
    # Recreate mythicness predictors table with count columns
    conn.execute("DROP TABLE IF EXISTS sentence_mythicness_predictors")
    conn.execute('''
    CREATE TABLE sentence_mythicness_predictors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phrase TEXT NOT NULL,
        coefficient REAL NOT NULL,
        is_mythic INTEGER NOT NULL,
        mythic_count INTEGER NOT NULL,
        non_mythic_count INTEGER NOT NULL,
        p_value REAL NOT NULL,
        q_value REAL NOT NULL,
        timestamp TEXT NOT NULL
    )
    ''')

    # Recreate skepticism predictors table with count columns
    conn.execute("DROP TABLE IF EXISTS sentence_skepticism_predictors")
    conn.execute('''
    CREATE TABLE sentence_skepticism_predictors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phrase TEXT NOT NULL,
        coefficient REAL NOT NULL,
        is_skeptical INTEGER NOT NULL,
        skeptical_count INTEGER NOT NULL,
        non_skeptical_count INTEGER NOT NULL,
        p_value REAL NOT NULL,
        q_value REAL NOT NULL,
        timestamp TEXT NOT NULL
    )
    ''')

    conn.commit()

def create_classification_metrics_tables(conn):
    """Create tables for storing sentence-level classification metrics."""
    conn.execute("DROP TABLE IF EXISTS sentence_mythicness_metrics")
    conn.execute('''
    CREATE TABLE sentence_mythicness_metrics (
        id INTEGER PRIMARY KEY,
        accuracy REAL NOT NULL,
        precision_0 REAL NOT NULL,
        recall_0 REAL NOT NULL,
        f1_0 REAL NOT NULL,
        support_0 INTEGER NOT NULL,
        precision_1 REAL NOT NULL,
        recall_1 REAL NOT NULL,
        f1_1 REAL NOT NULL,
        support_1 INTEGER NOT NULL,
        timestamp TEXT NOT NULL
    )
    ''')

    conn.execute("DROP TABLE IF EXISTS sentence_skepticism_metrics")
    conn.execute('''
    CREATE TABLE sentence_skepticism_metrics (
        id INTEGER PRIMARY KEY,
        accuracy REAL NOT NULL,
        precision_0 REAL NOT NULL,
        recall_0 REAL NOT NULL,
        f1_0 REAL NOT NULL,
        support_0 INTEGER NOT NULL,
        precision_1 REAL NOT NULL,
        recall_1 REAL NOT NULL,
        f1_1 REAL NOT NULL,
        support_1 INTEGER NOT NULL,
        timestamp TEXT NOT NULL
    )
    ''')
    conn.commit()

def save_classification_metrics(conn, table_name, y_true, y_pred):
    """Save classification metrics to the database."""
    precision, recall, f1, support = precision_recall_fscore_support(y_true, y_pred, average=None, zero_division=0)
    accuracy = accuracy_score(y_true, y_pred)
    timestamp = datetime.now().isoformat()

    cursor = conn.cursor()
    cursor.execute(
        f"""
        INSERT INTO {table_name}
        (accuracy, precision_0, recall_0, f1_0, support_0, precision_1, recall_1, f1_1, support_1, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (float(accuracy),
         float(precision[0]), float(recall[0]), float(f1[0]), int(support[0]),
         float(precision[1]), float(recall[1]), float(f1[1]), int(support[1]),
         timestamp)
    )
    conn.commit()

def clear_predictor_tables(conn):
    """Clear existing sentence-level predictor tables before inserting new values."""
    conn.execute("DELETE FROM sentence_mythicness_predictors")
    conn.execute("DELETE FROM sentence_skepticism_predictors")
    conn.commit()
    print("Cleared existing predictor tables.")

def get_analyzed_sentences(conn):
    """Get sentences that have been analyzed for mythicness and skepticism."""
    query = """
    SELECT sentence, references_mythic_era, expresses_scepticism
    FROM greek_sentences
    WHERE references_mythic_era IS NOT NULL
    AND expresses_scepticism IS NOT NULL
    """

    df = pd.read_sql_query(query, conn)
    return df

def get_proper_nouns(conn):
    """Get all proper nouns to use as stopwords."""
    query = """
    SELECT DISTINCT exact_form
    FROM proper_nouns
    """

    df = pd.read_sql_query(query, conn)
    return df['exact_form'].tolist()

def get_manual_stopwords(conn):
    """Get manually specified stopwords from the database."""
    # Ensure the table exists so users can manually insert words later
    conn.execute('''
    CREATE TABLE IF NOT EXISTS manual_stopwords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT UNIQUE NOT NULL
    )
    ''')
    conn.commit()

    df = pd.read_sql_query("SELECT word FROM manual_stopwords", conn)
    return df['word'].tolist()

def save_predictors(conn, feature_names, coefficients, label, table_name, pos_counts, neg_counts, p_values, q_values):
    """Save predictive features to the database."""
    timestamp = datetime.now().isoformat()
    cursor = conn.cursor()

    pos_col = f"{label}_count"
    neg_col = f"non_{label}_count"

    for feature, coef, pos, neg, p, q in zip(feature_names, coefficients, pos_counts, neg_counts, p_values, q_values):
        is_positive = 1 if coef > 0 else 0

        cursor.execute(
            f"""
            INSERT INTO {table_name} (phrase, coefficient, is_{label}, {pos_col}, {neg_col}, p_value, q_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (feature, float(coef), is_positive, int(pos), int(neg), float(p), float(q), timestamp),
        )

    conn.commit()

def build_and_evaluate_model(X, y, vectorizer_params, model_params, feature_label, conn, table_name, metrics_table_name, top_n=30):
    """Build a TF-IDF + LogReg model, evaluate it, and save top predictors."""
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=args.test_size, random_state=42)

    # Create pipeline
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(**vectorizer_params)),
        ('logreg', LogisticRegression(**model_params))
    ])

    # Train model
    pipeline.fit(X_train, y_train)

    # Evaluate model
    y_pred = pipeline.predict(X_test)
    print(f"\n=== {feature_label.capitalize()} Model Evaluation ===")
    print(classification_report(y_test, y_pred))

    # Save classification metrics to database
    save_classification_metrics(conn, metrics_table_name, y_test, y_pred)
    
    # Get feature names and coefficients
    vectorizer = pipeline.named_steps['tfidf']
    model = pipeline.named_steps['logreg']

    feature_names = vectorizer.get_feature_names_out()
    coefficients = model.coef_[0]

    # Compute sentence-level token counts for each class
    analyzer = vectorizer.build_analyzer()
    vocab_set = set(feature_names)
    pos_counter = Counter()
    neg_counter = Counter()
    total_pos = int(np.sum(y))
    total_neg = len(y) - total_pos
    for text, label_val in zip(X, y):
        tokens = {t for t in analyzer(text) if t in vocab_set}
        if label_val:
            pos_counter.update(tokens)
        else:
            neg_counter.update(tokens)
    pos_counts = np.array([pos_counter.get(f, 0) for f in feature_names])
    neg_counts = np.array([neg_counter.get(f, 0) for f in feature_names])

    # Compute p- and q-values
    p_values, q_values = compute_p_q_values(pos_counts, neg_counts, total_pos, total_neg)
    
    # Get top positive and negative predictors
    sorted_indices = np.argsort(coefficients)
    top_negative_indices = sorted_indices[:top_n]
    top_positive_indices = sorted_indices[-top_n:]
    
    # Print top predictors
    print(f"\nTop predictors for NOT {feature_label}:")
    for i in top_negative_indices:
        feature = feature_names[i]
        coef = coefficients[i]
        print(
            f"  {feature}: {coef:.4f} ({feature_label}={pos_counts[i]}, non_{feature_label}={neg_counts[i]}, p={p_values[i]:.3g}, q={q_values[i]:.3g})"
        )

    print(f"\nTop predictors for {feature_label}:")
    for i in top_positive_indices:
        feature = feature_names[i]
        coef = coefficients[i]
        print(
            f"  {feature}: {coef:.4f} ({feature_label}={pos_counts[i]}, non_{feature_label}={neg_counts[i]}, p={p_values[i]:.3g}, q={q_values[i]:.3g})"
        )

    # Save predictors to database
    selected_indices = np.concatenate([top_negative_indices, top_positive_indices])
    all_feature_names = [feature_names[i] for i in selected_indices]
    all_coefficients = [coefficients[i] for i in selected_indices]
    all_pos_counts = [pos_counts[i] for i in selected_indices]
    all_neg_counts = [neg_counts[i] for i in selected_indices]
    all_p_values = [p_values[i] for i in selected_indices]
    all_q_values = [q_values[i] for i in selected_indices]
    save_predictors(
        conn,
        all_feature_names,
        all_coefficients,
        feature_label,
        table_name,
        all_pos_counts,
        all_neg_counts,
        all_p_values,
        all_q_values,
    )
    
    return pipeline

if __name__ == '__main__':
    args = parse_arguments()
    
    # Parse ngram_range
    ngram_min, ngram_max = map(int, args.ngram_range.split(','))
    
    # Connect to the database
    conn = sqlite3.connect(args.database)
    
    try:
        # Create predictor tables if they don't exist
        create_predictor_tables(conn)

        # Create classification metrics tables
        create_classification_metrics_tables(conn)

        # Clear existing predictor data
        clear_predictor_tables(conn)
        
        # Get analyzed sentences
        sentences_df = get_analyzed_sentences(conn)

        if len(sentences_df) < args.min_samples:
            print(f"Not enough analyzed sentences. Found {len(sentences_df)}, need at least {args.min_samples}.")
            sys.exit(0)

        print(f"Found {len(sentences_df)} analyzed sentences.")
        print(f"References mythic era: {sentences_df['references_mythic_era'].sum()} sentences")
        print(f"Expresses skepticism: {sentences_df['expresses_scepticism'].sum()} sentences")
        
        # Get stopwords: proper nouns plus any manually specified additions
        proper_nouns = get_proper_nouns(conn)
        manual_stopwords = get_manual_stopwords(conn)
        all_stopwords = normalize_stopwords(proper_nouns + manual_stopwords)
        print(
            f"Using {len(proper_nouns)} proper nouns and {len(manual_stopwords)} manual stopwords (normalized to {len(all_stopwords)} unique tokens) as stopwords for mythicness model."
        )

        # Build mythicness model (with stopwords)
        mythic_vectorizer_params = {
            'max_features': args.max_features,
            'ngram_range': (ngram_min, ngram_max),
            'stop_words': all_stopwords,
            'preprocessor': casefold_preprocessor
        }
        
        mythic_model_params = {
            'C': 1.0,
            'max_iter': 1000,
            'class_weight': 'balanced',
            'random_state': 42
        }
        
        print("\nBuilding mythicness prediction model...")
        mythic_model = build_and_evaluate_model(
            sentences_df['sentence'],
            sentences_df['references_mythic_era'],
            mythic_vectorizer_params,
            mythic_model_params,
            'mythic',
            conn,
            'sentence_mythicness_predictors',
            'sentence_mythicness_metrics',
            args.top_features
        )
        
        # Build skepticism model (without proper noun stopwords)
        skeptic_vectorizer_params = {
            'max_features': args.max_features,
            'ngram_range': (ngram_min, ngram_max),
            'stop_words': [],  # No stopwords as requested
            'preprocessor': casefold_preprocessor
        }
        
        skeptic_model_params = {
            'C': 1.0,
            'max_iter': 1000,
            'class_weight': 'balanced',
            'random_state': 42
        }
        
        print("\nBuilding skepticism prediction model...")
        skeptic_model = build_and_evaluate_model(
            sentences_df['sentence'],
            sentences_df['expresses_scepticism'],
            skeptic_vectorizer_params,
            skeptic_model_params,
            'skeptical',
            conn,
            'sentence_skepticism_predictors',
            'sentence_skepticism_metrics',
            args.top_features
        )
        
        # Save models if requested
        if args.save_models:
            joblib.dump(mythic_model, 'sentence_mythicness_model.joblib')
            joblib.dump(skeptic_model, 'sentence_skepticism_model.joblib')
            print("\nModels saved to disk.")
        
        print("\nProcessing complete.")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    
    finally:
        conn.close()
