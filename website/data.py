"""Database operations and data retrieval functions."""

import math
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
import pandas as pd
from typing import Optional
import networkx as nx
from openai import OpenAI
import numpy as np
from scipy import stats
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge, RidgeCV
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_fscore_support,
    r2_score,
)
from sklearn.model_selection import KFold, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from lemma_text import (
    build_lemma_texts,
    casefold_preprocessor,
    expand_stopwords_with_lemma_forms,
    load_word_lemma_lookup,
    normalize_stopwords,
    surface_lookup_key,
    tokenize_greek,
)
from pausanias_db import read_sql_query, table_exists as pg_table_exists
from stats_utils import compute_p_q_values

WORD_PATTERN = re.compile(r"(?u)\b\w+\b")
TFIDF_TOKEN_PATTERN = r"(?u)\b\w\w+\b"
GRETA_SENTENCE_PROMPT_VERSION = "original-myth-history-other"
# The two production sentence classifiers compared on the comparison page.
ORIGINAL_CLASSIFIER_VERSION = "original-myth-history-other"
GRETA_INSPIRED_CLASSIFIER_VERSION = "greta-inspired-myth-history-other"
MANUAL_SENTENCE_SOURCE_ID = "greta-rosie-book3-rtf-2026-05-28"
RHETORIC_MARKER_LEMMAS = [
    "λέγω",
    "φημί",
    "φάσκω",
    "φάσις",
    "λόγος",
    "ἔπος",
    "ἀκούω",
    "καλέω",
    "ὀνομάζω",
    "ὄνομα",
    "νομίζω",
    "δοκέω",
    "μανθάνω",
    "οἶδα",
]
RHETORIC_MARKER_SURFACE_FORMS = [
    "λέγω",
    "λέγεται",
    "λέγουσι",
    "λέγουσιν",
    "λέγει",
    "λέγειν",
    "λεγεται",
    "λεγουσι",
    "λεγουσιν",
    "λεγει",
    "λεγειν",
    "φημί",
    "φησί",
    "φησίν",
    "φησὶ",
    "φησὶν",
    "φησι",
    "φησιν",
    "φασί",
    "φασίν",
    "φασὶ",
    "φασὶν",
    "φασι",
    "φασιν",
    "φάσι",
    "φάσιν",
    "φάσις",
    "φάσκω",
]
RHETORIC_MARKER_WORDS = list(
    dict.fromkeys(RHETORIC_MARKER_LEMMAS + RHETORIC_MARKER_SURFACE_FORMS)
)

DEFAULT_LLM_GRAMMAR_MODEL = "gpt-5.4-mini"
DISCOURSE_MODE_PROMPT_VERSION = "discourse-mode-v1"
DISCOURSE_MODES = [
    "route_locative_description",
    "monument_catalogue",
    "historical_narrative",
    "mythological_narrative",
    "ritual_ethnographic_description",
    "sources_traditions_discussion",
]
DISCOURSE_MODE_LABELS = {
    "route_locative_description": "Route and Locative Description",
    "monument_catalogue": "Monument Catalogue",
    "historical_narrative": "Historical Narrative",
    "mythological_narrative": "Mythological Narrative",
    "ritual_ethnographic_description": "Ritual or Ethnographic Description",
    "sources_traditions_discussion": "Sources or Traditions Discussion",
}
SECTION_PEOPLE_PROMPT_VERSION = "section-people-v1"
SECTION_PEOPLE_CLASSES = [
    "anonymous_female",
    "named_female",
    "anonymous_male",
    "named_male",
]
SECTION_PEOPLE_BUCKETS = ["mythic", "historical", "other"]

SEMANTIC_FIELD_ABLATIONS = [
    {
        "id": "genealogy-kinship",
        "label": "Genealogy and Kinship",
        "description": "Kinship, descent, marriage, and birth terms that drive the genealogical side of mythic narration.",
        "terms": [
            "θυγάτηρ",
            "πατήρ",
            "μήτηρ",
            "υἱός",
            "παῖς",
            "γυνή",
            "ἀνήρ",
            "γάμος",
            "γαμέω",
            "τίκτω",
            "γένος",
            "γεννάω",
            "ἀδελφός",
            "ἀδελφή",
            "ἔκγονος",
            "ἀπόγονος",
        ],
    },
    {
        "id": "speech-reporting",
        "label": "Speech and Reporting",
        "description": "Speech, report, attribution, naming, and knowledge-framing terms.",
        "terms": RHETORIC_MARKER_LEMMAS + ["μῦθος"],
    },
    {
        "id": "memorial-place-ritual",
        "label": "Memorial, Place, and Ritual",
        "description": "Tombs, shrines, names, cult sites, and place-making vocabulary.",
        "terms": [
            "μνῆμα",
            "τάφος",
            "θάπτω",
            "ἡρῷον",
            "ἱερόν",
            "ναός",
            "βωμός",
            "ἄγαλμα",
            "ἄγος",
            "ἀνάθημα",
            "θυσία",
            "θύω",
            "τελετή",
            "ὄνομα",
            "καλέω",
        ],
    },
    {
        "id": "war-politics-competition",
        "label": "War, Politics, and Competition",
        "description": "Military, civic, dynastic, athletic, and victory vocabulary that marks historical narration.",
        "terms": [
            "πόλεμος",
            "πολεμέω",
            "πολέμιος",
            "μάχη",
            "στρατός",
            "στρατεύω",
            "νικάω",
            "νίκη",
            "τύραννος",
            "τυραννέω",
            "βασιλεύς",
            "ἀρχή",
            "ἄρχω",
            "πέμπω",
            "ἀποστέλλω",
            "χρῆμα",
            "ἀριθμός",
            "ἀγών",
            "ἀθλητής",
        ],
    },
]

NETWORK_BETWEENNESS_EXACT_LIMIT = 250
NETWORK_BETWEENNESS_SAMPLE_SIZE = 120


def table_exists(conn, table_name):
    """Return True if a table exists in the PostgreSQL database."""
    return pg_table_exists(conn, table_name)

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
    
    df = read_sql_query(query, conn)
    
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
    
    df = read_sql_query(query, conn)
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
    
    df = read_sql_query(query, conn)
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
    SELECT phrase, coefficient, is_mythic, mythic_count, non_mythic_count,
           p_value, q_value
    FROM mythicness_predictors
    ORDER BY coefficient DESC
    """

    df = read_sql_query(query, conn)
    return df

def get_skepticism_predictors(conn):
    """Get words/phrases that predict skepticism/non-skepticism."""
    query = """
    SELECT phrase, coefficient, is_skeptical, skeptical_count,
           non_skeptical_count, p_value, q_value
    FROM skepticism_predictors
    ORDER BY coefficient DESC
    """

    df = read_sql_query(query, conn)
    return df


def get_sentence_mythicness_predictors(conn):
    """Get sentence-level words/phrases that predict mythicness/historicity."""
    query = """
    SELECT phrase, coefficient, is_mythic, mythic_count, non_mythic_count,
           p_value, q_value
    FROM sentence_mythicness_predictors
    ORDER BY coefficient DESC
    """

    df = read_sql_query(query, conn)
    return df


def get_sentence_skepticism_predictors(conn):
    """Get sentence-level words/phrases that predict skepticism/non-skepticism."""
    query = """
    SELECT phrase, coefficient, is_skeptical, skeptical_count,
           non_skeptical_count, p_value, q_value
    FROM sentence_skepticism_predictors
    ORDER BY coefficient DESC
    """

    df = read_sql_query(query, conn)
    return df


def get_simplified_mythicness_predictors(conn):
    """Get reduced-model predictors for passage-level mythicness."""
    if not table_exists(conn, "simplified_mythicness_predictors"):
        return pd.DataFrame()

    query = """
    SELECT phrase, coefficient, idf, point_value, is_mythic, mythic_count,
           non_mythic_count, p_value, q_value
    FROM simplified_mythicness_predictors
    ORDER BY ABS(point_value) DESC, q_value ASC
    """
    return read_sql_query(query, conn)


def get_simplified_skepticism_predictors(conn):
    """Get reduced-model predictors for passage-level skepticism."""
    if not table_exists(conn, "simplified_skepticism_predictors"):
        return pd.DataFrame()

    query = """
    SELECT phrase, coefficient, idf, point_value, is_skeptical, skeptical_count,
           non_skeptical_count, p_value, q_value
    FROM simplified_skepticism_predictors
    ORDER BY ABS(point_value) DESC, q_value ASC
    """
    return read_sql_query(query, conn)


def get_sentence_simplified_mythicness_predictors(conn):
    """Get reduced-model predictors for sentence-level mythicness."""
    if not table_exists(conn, "sentence_simplified_mythicness_predictors"):
        return pd.DataFrame()

    query = """
    SELECT phrase, coefficient, idf, point_value, is_mythic, mythic_count,
           non_mythic_count, p_value, q_value
    FROM sentence_simplified_mythicness_predictors
    ORDER BY ABS(point_value) DESC, q_value ASC
    """
    return read_sql_query(query, conn)


def get_sentence_simplified_skepticism_predictors(conn):
    """Get reduced-model predictors for sentence-level skepticism."""
    if not table_exists(conn, "sentence_simplified_skepticism_predictors"):
        return pd.DataFrame()

    query = """
    SELECT phrase, coefficient, idf, point_value, is_skeptical, skeptical_count,
           non_skeptical_count, p_value, q_value
    FROM sentence_simplified_skepticism_predictors
    ORDER BY ABS(point_value) DESC, q_value ASC
    """
    return read_sql_query(query, conn)


def get_all_sentences(conn):
    """Retrieve all Greek and English sentences with analysis flags."""
    query = """
    SELECT passage_id, sentence_number, sentence, english_sentence,
           references_mythic_era, expresses_scepticism
    FROM greek_sentences
    ORDER BY passage_id, sentence_number
    """

    df = read_sql_query(query, conn)
    return df


def _add_sentence_sort_columns(df):
    """Add chapter/book sorting columns to a sentence-level dataframe."""
    if len(df) == 0 or "passage_id" not in df.columns:
        return df
    result = df.copy()
    result["book"] = result["passage_id"].apply(lambda pid: str(pid).split(".")[0])
    result["chapter"] = result["passage_id"].apply(
        lambda pid: ".".join(str(pid).split(".")[:2])
    )
    result["sort_key"] = result["passage_id"].apply(passage_id_sort_key)
    result = result.sort_values(["sort_key", "sentence_number"])
    return result.drop(columns=["sort_key"])


def _active_greta_prompt_version(conn, prompt_version=None):
    """Return the active Greta sentence-tag prompt version, if present."""
    if not table_exists(conn, "sentence_greta_tags"):
        return None
    if prompt_version:
        return prompt_version

    versions = read_sql_query(
        """
        SELECT prompt_version, COUNT(*) AS count
        FROM sentence_greta_tags
        GROUP BY prompt_version
        ORDER BY
            CASE WHEN prompt_version = %s THEN 0 ELSE 1 END,
            count DESC,
            prompt_version
        """,
        conn,
        (GRETA_SENTENCE_PROMPT_VERSION,),
    )
    if len(versions) == 0:
        return None
    return versions.iloc[0]["prompt_version"]


def get_greta_sentence_annotations(conn, prompt_version=None):
    """Return active three-bucket Greta sentence annotations."""
    active_prompt = _active_greta_prompt_version(conn, prompt_version)
    if not active_prompt:
        return pd.DataFrame()

    query = """
    SELECT gs.passage_id,
           gs.sentence_number,
           gs.sentence,
           gs.english_sentence,
           t.prompt_version,
           COALESCE(NULLIF(t.model, ''), NULLIF(r.model, ''), t.model) AS model,
           t.myth_history_bucket,
           t.confidence,
           t.rationale,
           t.input_tokens,
           t.output_tokens,
           t.run_id,
           t.created_at
    FROM sentence_greta_tags t
    JOIN greek_sentences gs
      ON gs.passage_id = t.passage_id
     AND gs.sentence_number = t.sentence_number
    LEFT JOIN sentence_tagging_runs r
      ON r.run_id = t.run_id
    WHERE t.prompt_version = %s
    ORDER BY gs.passage_id, gs.sentence_number
    """
    df = read_sql_query(query, conn, (active_prompt,))
    return _add_sentence_sort_columns(df)


def get_sentence_review_sample(conn, prompt_version=None, sample_size=50):
    """Return a deterministic pseudo-random sample of active sentence tags."""
    active_prompt = _active_greta_prompt_version(conn, prompt_version)
    if not active_prompt:
        return pd.DataFrame()

    sample_size = max(0, int(sample_size))
    if sample_size == 0:
        return pd.DataFrame()

    query = """
    SELECT gs.passage_id,
           gs.sentence_number,
           gs.sentence,
           gs.english_sentence,
           p.passage,
           tr.english_translation,
           t.prompt_version,
           COALESCE(NULLIF(t.model, ''), NULLIF(r.model, ''), t.model) AS model,
           t.myth_history_bucket,
           t.expresses_scepticism,
           t.confidence,
           t.rationale,
           t.run_id,
           t.created_at,
           md5(%s || ':' || t.prompt_version || ':' || gs.passage_id || ':' || gs.sentence_number::text) AS sample_key
    FROM sentence_greta_tags t
    JOIN greek_sentences gs
      ON gs.passage_id = t.passage_id
     AND gs.sentence_number = t.sentence_number
    JOIN passages p
      ON p.id = gs.passage_id
    LEFT JOIN translations tr
      ON tr.passage_id = gs.passage_id
    LEFT JOIN sentence_tagging_runs r
      ON r.run_id = t.run_id
    WHERE t.prompt_version = %s
    ORDER BY sample_key, gs.passage_id, gs.sentence_number
    LIMIT %s
    """
    df = read_sql_query(
        query,
        conn,
        ("sentence-review-sample-v1", active_prompt, sample_size),
    )
    if len(df) == 0:
        return df

    df = df.copy()
    df["sample_rank"] = range(1, len(df) + 1)
    df["book"] = df["passage_id"].apply(lambda pid: str(pid).split(".")[0])
    df["chapter"] = df["passage_id"].apply(lambda pid: ".".join(str(pid).split(".")[:2]))
    return df


def get_classifier_comparison(conn):
    """Compare the two production sentence classifiers across the whole corpus.

    Returns a dict with corpus-wide and per-book bucket base rates for the
    'original' three-way tagger and the 'greta-inspired' two-flag tagger, their
    per-sentence agreement, the bucket confusion matrix, and the list of
    sentences where they disagree. Returns None if either lane is missing.
    """
    if not (
        table_exists(conn, "sentence_greta_tags")
        and table_exists(conn, "sentence_greta_both_tags")
    ):
        return None

    original = read_sql_query(
        """
        SELECT passage_id, sentence_number,
               myth_history_bucket AS original_bucket
        FROM sentence_greta_tags
        WHERE prompt_version = %s
        """,
        conn,
        (ORIGINAL_CLASSIFIER_VERSION,),
    )
    greta = read_sql_query(
        """
        SELECT t.passage_id, t.sentence_number,
               t.myth_history_bucket AS greta_bucket,
               t.rationale,
               gs.sentence, gs.english_sentence
        FROM sentence_greta_both_tags t
        JOIN greek_sentences gs
          ON gs.passage_id = t.passage_id
         AND gs.sentence_number = t.sentence_number
        WHERE t.prompt_version = %s
        """,
        conn,
        (GRETA_INSPIRED_CLASSIFIER_VERSION,),
    )
    if len(original) == 0 or len(greta) == 0:
        return None

    df = original.merge(greta, on=["passage_id", "sentence_number"], how="inner")
    if len(df) == 0:
        return None
    df["book"] = df["passage_id"].apply(lambda pid: str(pid).split(".")[0])
    df["agree"] = df["original_bucket"] == df["greta_bucket"]

    original_buckets = ["mythic", "historical", "other"]
    greta_buckets = ["mythic", "historical", "both", "other"]

    def _rates(frame, column, buckets):
        n = len(frame)
        counts = frame[column].value_counts().to_dict()
        return {b: (round(100.0 * counts.get(b, 0) / n, 1) if n else 0.0) for b in buckets}

    corpus = {
        "n": len(df),
        "agree_pct": round(100.0 * df["agree"].mean(), 1),
        "original_rates": _rates(df, "original_bucket", original_buckets),
        "greta_rates": _rates(df, "greta_bucket", greta_buckets),
    }

    per_book = []
    for book in sorted(df["book"].unique(), key=lambda b: int(b)):
        book_df = df[df["book"] == book]
        per_book.append(
            {
                "book": book,
                "n": len(book_df),
                "agree_pct": round(100.0 * book_df["agree"].mean(), 1),
                "original_rates": _rates(book_df, "original_bucket", original_buckets),
                "greta_rates": _rates(book_df, "greta_bucket", greta_buckets),
            }
        )

    confusion = {}
    for orig in original_buckets:
        for grb in greta_buckets:
            confusion[(orig, grb)] = int(
                ((df["original_bucket"] == orig) & (df["greta_bucket"] == grb)).sum()
            )

    disagreements = df[~df["agree"]].copy()
    disagreements["sort_key"] = disagreements["passage_id"].apply(passage_id_sort_key)
    disagreements = disagreements.sort_values(["sort_key", "sentence_number"]).drop(
        columns=["sort_key"]
    )

    return {
        "corpus": corpus,
        "per_book": per_book,
        "confusion": confusion,
        "original_buckets": original_buckets,
        "greta_buckets": greta_buckets,
        "disagreements": disagreements,
    }


def get_sentence_lemma_view(conn):
    """Return each sentence with the word-level lemma stream used by analyses."""
    if not table_exists(conn, "greek_word_lemmas"):
        return pd.DataFrame()
    lemma_lookup = load_word_lemma_lookup(conn)
    if not lemma_lookup:
        return pd.DataFrame()

    sentences = read_sql_query(
        """
        SELECT passage_id, sentence_number, sentence, english_sentence
        FROM greek_sentences
        ORDER BY passage_id, sentence_number
        """,
        conn,
    )
    rows = []
    for _, row in sentences.iterrows():
        tokens = tokenize_greek(row["sentence"])
        lemmas = []
        missing = 0
        for token in tokens:
            lemma = lemma_lookup.get(surface_lookup_key(token))
            if lemma is None:
                lemma = token
                missing += 1
            lemmas.append(lemma)
        rows.append(
            {
                "passage_id": row["passage_id"],
                "sentence_number": row["sentence_number"],
                "sentence": row["sentence"],
                "english_sentence": row["english_sentence"],
                "lemma_text": " ".join(lemmas),
                "token_count": len(tokens),
                "missing_lemma_count": missing,
            }
        )

    return _add_sentence_sort_columns(pd.DataFrame(rows))


def _stopword_rows(conn):
    parts = [
        "SELECT exact_form AS word FROM proper_nouns",
        "SELECT reference_form AS word FROM proper_nouns",
    ]
    if table_exists(conn, "manual_stopwords"):
        parts.append("SELECT word FROM manual_stopwords")
    return read_sql_query("\nUNION\n".join(parts), conn)["word"].dropna().tolist()


def _sentence_texts_and_stopwords(
    variant_df,
    *,
    token_source,
    proper_stopwords,
    lemma_lookup,
    extra_stopwords=None,
):
    extra_stopwords = list(extra_stopwords or [])
    if token_source == "lemma":
        if not lemma_lookup:
            return None, None, None, "No cached word-level lemmas are available."
        texts, lemma_stats = build_lemma_texts(variant_df["sentence"], lemma_lookup)
        stopwords = expand_stopwords_with_lemma_forms(
            proper_stopwords + extra_stopwords,
            lemma_lookup,
        )
        lemma_summary = {
            "token_count": lemma_stats.token_count,
            "lemmatized_token_count": lemma_stats.lemmatized_token_count,
            "missing_token_count": lemma_stats.missing_token_count,
            "unique_missing_count": lemma_stats.unique_missing_count,
        }
    else:
        texts = variant_df["sentence"].tolist()
        stopwords = normalize_stopwords(proper_stopwords + extra_stopwords)
        lemma_summary = None

    return texts, stopwords, lemma_summary, ""


def _binary_classification_metrics(y_true, y_pred):
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=[0, 1],
        zero_division=0,
    )
    actual_0_pred_0, actual_0_pred_1, actual_1_pred_0, actual_1_pred_1 = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1],
    ).ravel()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_0": float(precision[0]),
        "recall_0": float(recall[0]),
        "f1_0": float(f1[0]),
        "support_0": int(support[0]),
        "precision_1": float(precision[1]),
        "recall_1": float(recall[1]),
        "f1_1": float(f1[1]),
        "support_1": int(support[1]),
        "actual_0_pred_0": int(actual_0_pred_0),
        "actual_0_pred_1": int(actual_0_pred_1),
        "actual_1_pred_0": int(actual_1_pred_0),
        "actual_1_pred_1": int(actual_1_pred_1),
    }


def _new_sentence_vectorizer(stopwords, *, max_features=1000, min_df=2):
    return TfidfVectorizer(
        max_features=max_features,
        min_df=min_df,
        ngram_range=(1, 2),
        token_pattern=TFIDF_TOKEN_PATTERN,
        preprocessor=casefold_preprocessor,
        stop_words=stopwords,
    )


def _new_sentence_logistic_model():
    return LogisticRegression(
        C=1.0,
        max_iter=1000,
        class_weight="balanced",
        random_state=42,
    )


def _fit_greta_sentence_variant(
    df,
    *,
    label,
    token_source,
    include_books_4_8,
    remove_rhetoric_markers,
    proper_stopwords,
    lemma_lookup,
    additional_stopwords=None,
    max_features=1000,
    top_features=30,
    min_df=2,
):
    """Fit one Greta mythic-vs-historical sentence analysis variant."""
    variant_df = df[df["myth_history_bucket"].isin(["mythic", "historical"])].copy()
    if not include_books_4_8:
        variant_df = variant_df[~variant_df["book"].isin(["4", "8"])].copy()

    bucket_counts = (
        variant_df["myth_history_bucket"].value_counts().sort_index().to_dict()
        if len(variant_df) > 0
        else {}
    )
    y = (variant_df["myth_history_bucket"] == "mythic").astype(int).to_numpy()
    min_class_count = min(bucket_counts.values()) if bucket_counts else 0

    result = {
        "id": label,
        "token_source": token_source,
        "include_books_4_8": include_books_4_8,
        "remove_rhetoric_markers": remove_rhetoric_markers,
        "sample_count": int(len(variant_df)),
        "bucket_counts": bucket_counts,
        "feature_count": 0,
        "predictors": pd.DataFrame(),
        "all_predictors": pd.DataFrame(),
        "metrics": None,
        "available": False,
        "message": "",
    }

    if len(variant_df) < 20 or min_class_count < 5:
        result["message"] = "Not enough mythic and historical sentences are tagged yet."
        return result

    extra_stopwords = list(additional_stopwords or [])
    if remove_rhetoric_markers:
        extra_stopwords.extend(RHETORIC_MARKER_WORDS)
    texts, stopwords, lemma_stats, message = _sentence_texts_and_stopwords(
        variant_df,
        token_source=token_source,
        proper_stopwords=proper_stopwords,
        lemma_lookup=lemma_lookup,
        extra_stopwords=extra_stopwords,
    )
    if message:
        result["message"] = message
        return result
    if lemma_stats is not None:
        result["lemma_stats"] = {
            **lemma_stats,
        }

    vectorizer = _new_sentence_vectorizer(
        stopwords,
        max_features=max_features,
        min_df=min_df,
    )
    model = _new_sentence_logistic_model()

    test_size = 0.25
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            texts,
            y,
            test_size=test_size,
            random_state=42,
            stratify=y,
        )
        train_matrix = vectorizer.fit_transform(X_train)
        if train_matrix.shape[1] == 0:
            result["message"] = "No repeated vocabulary survived filtering."
            return result
        model.fit(train_matrix, y_train)
        test_matrix = vectorizer.transform(X_test)
        y_pred = model.predict(test_matrix)
    except ValueError as exc:
        result["message"] = f"Could not fit model: {exc}"
        return result

    feature_names = vectorizer.get_feature_names_out()
    coefficients = model.coef_[0]
    analyzer = vectorizer.build_analyzer()
    vocab = set(feature_names)
    mythic_counter = Counter()
    historical_counter = Counter()
    total_mythic = int(np.sum(y))
    total_historical = len(y) - total_mythic

    for text, label_value in zip(texts, y):
        terms = {term for term in analyzer(text) if term in vocab}
        if label_value:
            mythic_counter.update(terms)
        else:
            historical_counter.update(terms)

    mythic_counts = np.array([mythic_counter.get(feature, 0) for feature in feature_names])
    historical_counts = np.array(
        [historical_counter.get(feature, 0) for feature in feature_names]
    )
    p_values, q_values = compute_p_q_values(
        mythic_counts,
        historical_counts,
        total_mythic,
        total_historical,
    )

    predictor_rows = pd.DataFrame(
        {
            "phrase": feature_names,
            "english_translation": "",
            "coefficient": coefficients,
            "is_mythic": (coefficients > 0).astype(int),
            "mythic_count": mythic_counts,
            "historical_count": historical_counts,
            "p_value": p_values,
            "q_value": q_values,
        }
    )
    top_positive = predictor_rows.sort_values("coefficient", ascending=False).head(
        top_features
    )
    top_negative = predictor_rows.sort_values("coefficient", ascending=True).head(
        top_features
    )

    result.update(
        {
            "available": True,
            "feature_count": int(len(feature_names)),
            "predictors": pd.concat([top_negative, top_positive]).reset_index(drop=True),
            "all_predictors": predictor_rows.reset_index(drop=True),
            "metrics": _binary_classification_metrics(y_test, y_pred),
        }
    )
    return result


def _main_scope_sentence_frame(annotations, *, include_books_4_8=False):
    frame = annotations[annotations["myth_history_bucket"].isin(["mythic", "historical"])].copy()
    if not include_books_4_8:
        frame = frame[~frame["book"].isin(["4", "8"])].copy()
    return frame


def _semantic_field_ablation_analysis(annotations, proper_stopwords, lemma_lookup, baseline_variant):
    """Rerun the main lemma model after removing interpretable semantic fields."""
    if not baseline_variant or not baseline_variant.get("available"):
        return {
            "available": False,
            "message": "The baseline lemma model is unavailable.",
            "fields": [],
        }

    baseline_metrics = baseline_variant.get("metrics") or {}
    baseline_accuracy = baseline_metrics.get("accuracy")
    rows = []
    for field in SEMANTIC_FIELD_ABLATIONS:
        variant = _fit_greta_sentence_variant(
            annotations,
            label=f"ablation-{field['id']}",
            token_source="lemma",
            include_books_4_8=False,
            remove_rhetoric_markers=False,
            proper_stopwords=proper_stopwords,
            lemma_lookup=lemma_lookup,
            additional_stopwords=field["terms"],
            top_features=8,
        )
        metrics = variant.get("metrics") or {}
        accuracy = metrics.get("accuracy")
        if accuracy is not None and baseline_accuracy is not None:
            delta = float(accuracy - baseline_accuracy)
        else:
            delta = None
        rows.append(
            {
                "id": field["id"],
                "label": field["label"],
                "description": field["description"],
                "terms": field["terms"],
                "available": bool(variant.get("available")),
                "message": variant.get("message", ""),
                "sample_count": int(variant.get("sample_count", 0)),
                "feature_count": int(variant.get("feature_count", 0)),
                "metrics": metrics,
                "accuracy_delta": delta,
            }
        )

    return {
        "available": True,
        "message": "",
        "baseline": {
            "id": baseline_variant.get("id"),
            "sample_count": int(baseline_variant.get("sample_count", 0)),
            "feature_count": int(baseline_variant.get("feature_count", 0)),
            "metrics": baseline_metrics,
        },
        "fields": rows,
    }


def _book_held_out_analysis(annotations, proper_stopwords, lemma_lookup):
    """Train on all but one book and test on the held-out book."""
    variant_df = _main_scope_sentence_frame(annotations, include_books_4_8=True)
    if len(variant_df) < 20:
        return {
            "available": False,
            "message": "Not enough mythic and historical sentences are tagged yet.",
            "books": [],
        }

    texts, stopwords, _, message = _sentence_texts_and_stopwords(
        variant_df,
        token_source="lemma",
        proper_stopwords=proper_stopwords,
        lemma_lookup=lemma_lookup,
        extra_stopwords=[],
    )
    if message:
        return {"available": False, "message": message, "books": []}

    text_series = pd.Series(texts, index=variant_df.index)
    y_series = (variant_df["myth_history_bucket"] == "mythic").astype(int)
    rows = []
    total_correct = 0
    total_test = 0
    for book in sorted(variant_df["book"].unique(), key=lambda value: int(value)):
        test_mask = variant_df["book"] == book
        train_mask = ~test_mask
        train_df = variant_df[train_mask]
        test_df = variant_df[test_mask]
        train_counts = train_df["myth_history_bucket"].value_counts().to_dict()
        test_counts = test_df["myth_history_bucket"].value_counts().to_dict()
        min_train_class = min(train_counts.values()) if len(train_counts) == 2 else 0
        row = {
            "book": str(book),
            "available": False,
            "message": "",
            "train_count": int(len(train_df)),
            "test_count": int(len(test_df)),
            "train_mythic": int(train_counts.get("mythic", 0)),
            "train_historical": int(train_counts.get("historical", 0)),
            "test_mythic": int(test_counts.get("mythic", 0)),
            "test_historical": int(test_counts.get("historical", 0)),
            "feature_count": 0,
            "metrics": {},
        }
        if len(test_df) == 0 or min_train_class < 5:
            row["message"] = "Not enough train/test data for this held-out book."
            rows.append(row)
            continue

        vectorizer = _new_sentence_vectorizer(stopwords)
        model = _new_sentence_logistic_model()
        try:
            train_matrix = vectorizer.fit_transform(text_series[train_mask].tolist())
            if train_matrix.shape[1] == 0:
                row["message"] = "No repeated vocabulary survived filtering."
                rows.append(row)
                continue
            y_train = y_series[train_mask].to_numpy()
            y_test = y_series[test_mask].to_numpy()
            model.fit(train_matrix, y_train)
            y_pred = model.predict(vectorizer.transform(text_series[test_mask].tolist()))
        except ValueError as exc:
            row["message"] = f"Could not fit model: {exc}"
            rows.append(row)
            continue

        majority_label = 1 if row["train_mythic"] >= row["train_historical"] else 0
        baseline_pred = np.full_like(y_test, majority_label)
        metrics = _binary_classification_metrics(y_test, y_pred)
        metrics["baseline_accuracy"] = float(accuracy_score(y_test, baseline_pred))
        metrics["baseline_label"] = int(majority_label)
        metrics["accuracy_delta_vs_baseline"] = float(
            metrics["accuracy"] - metrics["baseline_accuracy"]
        )
        row.update(
            {
                "available": True,
                "feature_count": int(len(vectorizer.get_feature_names_out())),
                "metrics": metrics,
            }
        )
        total_correct += int(np.sum(y_pred == y_test))
        total_test += int(len(y_test))
        rows.append(row)

    available_rows = [row for row in rows if row["available"]]
    summary = {
        "book_count": int(len(available_rows)),
        "weighted_accuracy": float(total_correct / total_test) if total_test else None,
        "macro_accuracy": float(np.mean([row["metrics"]["accuracy"] for row in available_rows]))
        if available_rows
        else None,
        "total_test": int(total_test),
    }
    return {
        "available": bool(available_rows),
        "message": "" if available_rows else "No held-out book models could be fit.",
        "summary": summary,
        "books": rows,
    }


def _top_feature_contributions(row_vector, feature_names, coefficients, predicted_label, limit=8):
    contributions = []
    coo = row_vector.tocoo()
    for feature_index, value in zip(coo.col, coo.data):
        contribution = float(value * coefficients[feature_index])
        contributions.append((feature_names[feature_index], contribution))
    if predicted_label == 1:
        preferred = [item for item in contributions if item[1] > 0]
        preferred.sort(key=lambda item: item[1], reverse=True)
    else:
        preferred = [item for item in contributions if item[1] < 0]
        preferred.sort(key=lambda item: item[1])
    if not preferred:
        preferred = sorted(contributions, key=lambda item: abs(item[1]), reverse=True)
    return [
        {"term": term, "contribution": float(contribution)}
        for term, contribution in preferred[:limit]
    ]


def _error_analysis(annotations, proper_stopwords, lemma_lookup, limit_per_type=20):
    """Collect deterministic examples where the main model misclassifies held-out sentences."""
    variant_df = _main_scope_sentence_frame(annotations, include_books_4_8=False)
    bucket_counts = variant_df["myth_history_bucket"].value_counts().to_dict()
    if len(variant_df) < 20 or len(bucket_counts) < 2 or min(bucket_counts.values()) < 5:
        return {
            "available": False,
            "message": "Not enough mythic and historical sentences are tagged yet.",
            "examples": {},
        }

    texts, stopwords, _, message = _sentence_texts_and_stopwords(
        variant_df,
        token_source="lemma",
        proper_stopwords=proper_stopwords,
        lemma_lookup=lemma_lookup,
        extra_stopwords=[],
    )
    if message:
        return {"available": False, "message": message, "examples": {}}

    y = (variant_df["myth_history_bucket"] == "mythic").astype(int).to_numpy()
    try:
        X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
            texts,
            y,
            variant_df.index.to_numpy(),
            test_size=0.25,
            random_state=42,
            stratify=y,
        )
        vectorizer = _new_sentence_vectorizer(stopwords)
        train_matrix = vectorizer.fit_transform(X_train)
        if train_matrix.shape[1] == 0:
            return {
                "available": False,
                "message": "No repeated vocabulary survived filtering.",
                "examples": {},
            }
        model = _new_sentence_logistic_model()
        model.fit(train_matrix, y_train)
        test_matrix = vectorizer.transform(X_test)
        y_pred = model.predict(test_matrix)
        mythic_class_index = list(model.classes_).index(1)
        mythic_probabilities = model.predict_proba(test_matrix)[:, mythic_class_index]
    except ValueError as exc:
        return {"available": False, "message": f"Could not fit model: {exc}", "examples": {}}

    feature_names = vectorizer.get_feature_names_out()
    coefficients = model.coef_[0]
    test_rows = variant_df.loc[idx_test]
    error_rows = []
    for row_position, (idx, actual, predicted, mythic_probability) in enumerate(
        zip(idx_test, y_test, y_pred, mythic_probabilities)
    ):
        if int(actual) == int(predicted):
            continue
        source_row = test_rows.loc[idx]
        predicted_confidence = (
            float(mythic_probability)
            if int(predicted) == 1
            else float(1.0 - mythic_probability)
        )
        error_rows.append(
            {
                "passage_id": source_row["passage_id"],
                "sentence_number": int(source_row["sentence_number"]),
                "book": str(source_row["book"]),
                "sentence": source_row["sentence"],
                "english_sentence": source_row.get("english_sentence", ""),
                "rationale": source_row.get("rationale", ""),
                "actual_label": "mythic" if int(actual) == 1 else "historical",
                "predicted_label": "mythic" if int(predicted) == 1 else "historical",
                "probability_mythic": float(mythic_probability),
                "predicted_confidence": predicted_confidence,
                "contributions": _top_feature_contributions(
                    test_matrix[row_position],
                    feature_names,
                    coefficients,
                    int(predicted),
                ),
            }
        )

    false_mythic = [
        row for row in error_rows
        if row["actual_label"] == "historical" and row["predicted_label"] == "mythic"
    ]
    false_historical = [
        row for row in error_rows
        if row["actual_label"] == "mythic" and row["predicted_label"] == "historical"
    ]
    false_mythic.sort(
        key=lambda row: (row["predicted_confidence"], row["passage_id"], row["sentence_number"]),
        reverse=True,
    )
    false_historical.sort(
        key=lambda row: (row["predicted_confidence"], row["passage_id"], row["sentence_number"]),
        reverse=True,
    )
    metrics = _binary_classification_metrics(y_test, y_pred)
    return {
        "available": True,
        "message": "",
        "summary": {
            "sample_count": int(len(variant_df)),
            "test_count": int(len(y_test)),
            "error_count": int(len(error_rows)),
            "false_mythic_count": int(len(false_mythic)),
            "false_historical_count": int(len(false_historical)),
            "feature_count": int(len(feature_names)),
            "metrics": metrics,
        },
        "examples": {
            "false_mythic": false_mythic[:limit_per_type],
            "false_historical": false_historical[:limit_per_type],
        },
    }


def _get_greta_complementary_analyses(annotations, proper_stopwords, lemma_lookup, variants):
    baseline = next(
        (
            variant for variant in variants
            if variant.get("token_source") == "lemma"
            and not variant.get("include_books_4_8")
            and not variant.get("remove_rhetoric_markers")
        ),
        None,
    )
    return {
        "semantic_field_ablation": _semantic_field_ablation_analysis(
            annotations,
            proper_stopwords,
            lemma_lookup,
            baseline,
        ),
        "book_held_out": _book_held_out_analysis(
            annotations,
            proper_stopwords,
            lemma_lookup,
        ),
        "error_analysis": _error_analysis(
            annotations,
            proper_stopwords,
            lemma_lookup,
        ),
    }


def get_greta_sentence_analysis_variants(conn):
    """Build current Greta mythic-vs-historical logistic-regression variants."""
    annotations = get_greta_sentence_annotations(conn)
    if len(annotations) == 0:
        return {
            "available": False,
            "message": "No active Greta sentence tags are available.",
            "prompt_version": None,
            "variants": [],
            "bucket_counts": {},
        }

    lemma_lookup = load_word_lemma_lookup(conn) if table_exists(conn, "greek_word_lemmas") else {}
    proper_stopwords = _stopword_rows(conn)
    bucket_counts = annotations["myth_history_bucket"].value_counts().sort_index().to_dict()
    book_counts = annotations["book"].value_counts().sort_index().to_dict()
    variants = []
    for token_source in ["lemma", "surface"]:
        for include_books in [False, True]:
            for remove_rhetoric in [False, True]:
                label = "-".join(
                    [
                        "tri-marked-sentence",
                        token_source,
                        "all-books" if include_books else "excluding-4-8",
                        "without-rhetoric" if remove_rhetoric else "with-rhetoric",
                    ]
                )
                variants.append(
                    _fit_greta_sentence_variant(
                        annotations,
                        label=label,
                        token_source=token_source,
                        include_books_4_8=include_books,
                        remove_rhetoric_markers=remove_rhetoric,
                        proper_stopwords=proper_stopwords,
                        lemma_lookup=lemma_lookup,
                    )
                )

    return {
        "available": True,
        "message": "",
        "prompt_version": annotations.iloc[0]["prompt_version"],
        "model": annotations.iloc[0].get("model", ""),
        "variants": variants,
        "complementary": _get_greta_complementary_analyses(
            annotations,
            proper_stopwords,
            lemma_lookup,
            variants,
        ),
        "label_sensitivity": get_manual_label_sensitivity_analysis(
            conn,
            source_id=MANUAL_SENTENCE_SOURCE_ID,
            proper_stopwords=proper_stopwords,
            lemma_lookup=lemma_lookup,
        ),
        "bucket_counts": bucket_counts,
        "book_counts": book_counts,
        "tagged_sentence_count": int(len(annotations)),
    }


def _holm_adjust(p_values):
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [math.nan] * len(p_values)
    running = 0.0
    total = len(p_values)
    for rank, index in enumerate(order):
        value = min(1.0, p_values[index] * (total - rank))
        running = max(running, value)
        adjusted[index] = running
    return adjusted


def _section_people_empty_matrix(value=0):
    return {
        bucket: {people_class: value for people_class in SECTION_PEOPLE_CLASSES}
        for bucket in SECTION_PEOPLE_BUCKETS
    }


def _section_people_matrix_from_frame(frame):
    return {
        bucket: {
            people_class: int(frame.loc[bucket, people_class])
            for people_class in SECTION_PEOPLE_CLASSES
        }
        for bucket in SECTION_PEOPLE_BUCKETS
    }


def _section_people_float_matrix_from_frame(frame, digits=None):
    matrix = {}
    for bucket in SECTION_PEOPLE_BUCKETS:
        matrix[bucket] = {}
        for people_class in SECTION_PEOPLE_CLASSES:
            value = float(frame.loc[bucket, people_class])
            matrix[bucket][people_class] = round(value, digits) if digits is not None else value
    return matrix


def get_section_people_analysis(
    conn,
    prompt_version=SECTION_PEOPLE_PROMPT_VERSION,
    bucket_prompt_version=GRETA_SENTENCE_PROMPT_VERSION,
):
    """Build named/anonymous people and gender statistics for the analysis site."""
    required_tables = [
        "section_people_runs",
        "section_people_batch_items",
        "section_people_mentions",
        "greek_sentences",
        "sentence_greta_tags",
    ]
    missing_tables = [table for table in required_tables if not table_exists(conn, table)]
    if missing_tables:
        return {
            "available": False,
            "message": "Missing tables: " + ", ".join(missing_tables),
            "prompt_version": prompt_version,
            "bucket_prompt_version": bucket_prompt_version,
            "classes": SECTION_PEOPLE_CLASSES,
            "buckets": SECTION_PEOPLE_BUCKETS,
        }

    summary_query = """
    WITH completed_sections AS (
        SELECT DISTINCT bi.passage_id
        FROM section_people_batch_items bi
        JOIN section_people_runs r ON r.run_id = bi.run_id
        WHERE r.prompt_version = %s
          AND bi.status = 'completed'
          AND r.status IN ('completed', 'completed_with_failures')
    ), section_sentence_counts AS (
        SELECT passage_id, count(*) AS sentence_count
        FROM greek_sentences
        GROUP BY passage_id
    ), mention_summary AS (
        SELECT
            count(*) AS mention_rows,
            count(*) FILTER (WHERE gender IN ('male', 'female')) AS gendered_mention_rows,
            count(*) FILTER (WHERE gender = 'unknown') AS unknown_mention_rows,
            count(DISTINCT passage_id) AS sections_with_mentions,
            count(DISTINCT passage_id || ':' || sentence_number::text) AS sentences_with_mentions,
            COALESCE(sum(CASE WHEN person_count > 0 THEN person_count ELSE 0 END), 0) AS exact_people
        FROM section_people_mentions
        WHERE prompt_version = %s
    ), run_summary AS (
        SELECT
            count(*) AS runs,
            COALESCE(sum(input_tokens), 0) AS input_tokens,
            COALESCE(sum(output_tokens), 0) AS output_tokens,
            max(submitted_at) AS latest_submitted_at,
            max(retrieved_at) AS latest_retrieved_at
        FROM section_people_runs
        WHERE prompt_version = %s
          AND status IN ('completed', 'completed_with_failures')
    ), corpus_summary AS (
        SELECT
            (SELECT count(*) FROM passages) AS total_sections,
            (SELECT count(*) FROM greek_sentences) AS total_sentences
    )
    SELECT
        (SELECT count(*) FROM completed_sections) AS processed_sections,
        COALESCE((SELECT sum(ssc.sentence_count)
                  FROM completed_sections cs
                  JOIN section_sentence_counts ssc ON ssc.passage_id = cs.passage_id), 0) AS processed_sentences,
        m.mention_rows,
        m.gendered_mention_rows,
        m.unknown_mention_rows,
        m.sections_with_mentions,
        m.sentences_with_mentions,
        m.exact_people,
        r.runs,
        r.input_tokens,
        r.output_tokens,
        r.latest_submitted_at,
        r.latest_retrieved_at,
        c.total_sections,
        c.total_sentences
    FROM mention_summary m
    CROSS JOIN run_summary r
    CROSS JOIN corpus_summary c
    """
    summary_df = read_sql_query(
        summary_query,
        conn,
        (prompt_version, prompt_version, prompt_version),
    )
    summary = summary_df.iloc[0].to_dict() if len(summary_df) else {}
    for key in (
        "processed_sections",
        "processed_sentences",
        "mention_rows",
        "gendered_mention_rows",
        "unknown_mention_rows",
        "sections_with_mentions",
        "sentences_with_mentions",
        "exact_people",
        "runs",
        "input_tokens",
        "output_tokens",
        "total_sections",
        "total_sentences",
    ):
        summary[key] = int(summary.get(key) or 0)
    summary["total_tokens"] = summary["input_tokens"] + summary["output_tokens"]
    summary["coverage_percent"] = (
        100 * summary["processed_sections"] / summary["total_sections"]
        if summary["total_sections"]
        else 0.0
    )

    bucket_sample_query = """
    WITH completed_sections AS (
        SELECT DISTINCT bi.passage_id
        FROM section_people_batch_items bi
        JOIN section_people_runs r ON r.run_id = bi.run_id
        WHERE r.prompt_version = %s
          AND bi.status = 'completed'
          AND r.status IN ('completed', 'completed_with_failures')
    )
    SELECT
        b.myth_history_bucket,
        count(DISTINCT gs.passage_id) AS sections,
        count(*) AS sentences
    FROM greek_sentences gs
    JOIN completed_sections cs ON cs.passage_id = gs.passage_id
    JOIN sentence_greta_tags b
      ON b.passage_id = gs.passage_id
     AND b.sentence_number = gs.sentence_number
     AND b.prompt_version = %s
    GROUP BY b.myth_history_bucket
    """
    sample_df = read_sql_query(bucket_sample_query, conn, (prompt_version, bucket_prompt_version))
    bucket_sample = {
        bucket: {"sections": 0, "sentences": 0}
        for bucket in SECTION_PEOPLE_BUCKETS
    }
    for row in sample_df.to_dict("records"):
        bucket = row.get("myth_history_bucket")
        if bucket in bucket_sample:
            bucket_sample[bucket] = {
                "sections": int(row.get("sections") or 0),
                "sentences": int(row.get("sentences") or 0),
            }

    stats_query = """
    WITH bucket_tags AS (
        SELECT passage_id, sentence_number, myth_history_bucket
        FROM sentence_greta_tags
        WHERE prompt_version = %s
    )
    SELECT
        b.myth_history_bucket,
        CASE WHEN m.is_named THEN 'named' ELSE 'anonymous' END AS name_status,
        m.gender,
        count(*) AS mention_rows,
        COALESCE(sum(CASE WHEN m.person_count > 0 THEN m.person_count ELSE 0 END), 0) AS exact_people,
        count(DISTINCT m.passage_id) AS sections,
        count(DISTINCT m.passage_id || ':' || m.sentence_number::text) AS sentences
    FROM section_people_mentions m
    JOIN bucket_tags b
      ON b.passage_id = m.passage_id
     AND b.sentence_number = m.sentence_number
    WHERE m.prompt_version = %s
      AND m.gender IN ('male', 'female')
    GROUP BY b.myth_history_bucket, name_status, m.gender
    ORDER BY b.myth_history_bucket, name_status, m.gender
    """
    stats_df = read_sql_query(stats_query, conn, (bucket_prompt_version, prompt_version))
    empty_int_matrix = _section_people_empty_matrix(0)
    if len(stats_df) == 0:
        return {
            "available": summary["processed_sections"] > 0,
            "message": "No gendered people mentions are available yet.",
            "prompt_version": prompt_version,
            "bucket_prompt_version": bucket_prompt_version,
            "classes": SECTION_PEOPLE_CLASSES,
            "buckets": SECTION_PEOPLE_BUCKETS,
            "summary": summary,
            "bucket_sample": bucket_sample,
            "counts": empty_int_matrix,
            "percentages": _section_people_empty_matrix(0.0),
            "exact_counts": empty_int_matrix,
            "shares": {},
            "chi_square": None,
            "pairwise_tests": [],
            "residuals": _section_people_empty_matrix(0.0),
        }

    stats_df["mention_rows"] = stats_df["mention_rows"].astype(int)
    stats_df["exact_people"] = stats_df["exact_people"].astype(int)
    stats_df["class"] = stats_df["name_status"] + "_" + stats_df["gender"]
    counts_table = (
        stats_df.pivot_table(
            index="myth_history_bucket",
            columns="class",
            values="mention_rows",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(index=SECTION_PEOPLE_BUCKETS, columns=SECTION_PEOPLE_CLASSES, fill_value=0)
        .astype(int)
    )
    exact_table = (
        stats_df.pivot_table(
            index="myth_history_bucket",
            columns="class",
            values="exact_people",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(index=SECTION_PEOPLE_BUCKETS, columns=SECTION_PEOPLE_CLASSES, fill_value=0)
        .astype(int)
    )
    proportions = counts_table.div(
        counts_table.sum(axis=1).replace(0, pd.NA),
        axis=0,
    ).fillna(0.0)
    percentages = proportions * 100

    shares = {}
    for bucket in SECTION_PEOPLE_BUCKETS:
        row = counts_table.loc[bucket]
        total = int(row.sum())
        named_total = int(row["named_female"] + row["named_male"])
        anonymous_total = int(row["anonymous_female"] + row["anonymous_male"])
        female_total = int(row["anonymous_female"] + row["named_female"])
        shares[bucket] = {
            "total": total,
            "female_percent": 100 * female_total / total if total else 0.0,
            "named_percent": 100 * named_total / total if total else 0.0,
            "anonymous_percent": 100 * anonymous_total / total if total else 0.0,
            "named_female_percent_of_named": (
                100 * int(row["named_female"]) / named_total if named_total else 0.0
            ),
        }

    chi_square = None
    residual_matrix = pd.DataFrame(
        0.0,
        index=SECTION_PEOPLE_BUCKETS,
        columns=SECTION_PEOPLE_CLASSES,
    )
    analysis_table = counts_table.loc[
        counts_table.sum(axis=1) > 0,
        counts_table.sum(axis=0) > 0,
    ]
    if analysis_table.shape[0] >= 2 and analysis_table.shape[1] >= 2:
        chi2, p_value, dof, expected = stats.chi2_contingency(
            analysis_table.to_numpy(),
            correction=False,
        )
        n = int(analysis_table.to_numpy().sum())
        denominator = n * min(analysis_table.shape[0] - 1, analysis_table.shape[1] - 1)
        cramers_v = math.sqrt(chi2 / denominator) if denominator else 0.0
        expected_frame = pd.DataFrame(
            expected,
            index=analysis_table.index,
            columns=analysis_table.columns,
        )
        residuals = (analysis_table - expected_frame) / expected_frame.pow(0.5)
        residual_matrix.loc[residuals.index, residuals.columns] = residuals
        chi_square = {
            "chi2": float(chi2),
            "dof": int(dof),
            "p_value": float(p_value),
            "cramers_v": float(cramers_v),
            "n": n,
        }

    pairwise_tests = []
    p_values = []
    for bucket_a, bucket_b in combinations(SECTION_PEOPLE_BUCKETS, 2):
        sub = counts_table.loc[[bucket_a, bucket_b]]
        sub = sub.loc[sub.sum(axis=1) > 0, sub.sum(axis=0) > 0]
        if sub.shape[0] < 2 or sub.shape[1] < 2:
            continue
        chi2_pair, p_pair, dof_pair, _ = stats.chi2_contingency(
            sub.to_numpy(),
            correction=False,
        )
        n_pair = int(sub.to_numpy().sum())
        denominator = n_pair * min(sub.shape[0] - 1, sub.shape[1] - 1)
        v_pair = math.sqrt(chi2_pair / denominator) if denominator else 0.0
        pairwise_tests.append(
            {
                "comparison": f"{bucket_a} vs {bucket_b}",
                "bucket_a": bucket_a,
                "bucket_b": bucket_b,
                "chi2": float(chi2_pair),
                "dof": int(dof_pair),
                "p_value": float(p_pair),
                "cramers_v": float(v_pair),
            }
        )
        p_values.append(float(p_pair))
    for row, adjusted in zip(pairwise_tests, _holm_adjust(p_values)):
        row["p_holm"] = float(adjusted)

    return {
        "available": True,
        "message": "",
        "prompt_version": prompt_version,
        "bucket_prompt_version": bucket_prompt_version,
        "classes": SECTION_PEOPLE_CLASSES,
        "buckets": SECTION_PEOPLE_BUCKETS,
        "summary": summary,
        "bucket_sample": bucket_sample,
        "counts": _section_people_matrix_from_frame(counts_table),
        "percentages": _section_people_float_matrix_from_frame(percentages, digits=3),
        "exact_counts": _section_people_matrix_from_frame(exact_table),
        "shares": shares,
        "chi_square": chi_square,
        "pairwise_tests": pairwise_tests,
        "residuals": _section_people_float_matrix_from_frame(residual_matrix, digits=4),
    }


def _manual_component_agrees(manual_bucket, greta_bucket):
    if manual_bucket == "mixed_mythic_historical":
        return greta_bucket in {"mythic", "historical"}
    return manual_bucket == greta_bucket


def _comparison_result(manual_bucket, greta_bucket):
    if not greta_bucket:
        return "missing_greta_tag"
    if manual_bucket in {"mythic", "historical", "other"}:
        return "exact_agreement" if manual_bucket == greta_bucket else "disagreement"
    if _manual_component_agrees(manual_bucket, greta_bucket):
        return "partial_agreement_manual_mixed"
    return "disagreement_manual_mixed"


def _counter_records(counter, first_key, second_key=None):
    records = []
    for key, count in sorted(counter.items()):
        if second_key:
            first_value, second_value = key
            records.append(
                {
                    first_key: first_value,
                    second_key: second_value,
                    "count": int(count),
                }
            )
        else:
            records.append({first_key: key, "count": int(count)})
    return records


def _fit_label_sensitivity_scenario(
    df,
    *,
    scenario_id,
    label,
    description,
    token_source,
    proper_stopwords,
    lemma_lookup,
    sample_weight_column=None,
    max_features=1000,
    top_features=25,
    min_df=2,
):
    """Fit one mythic-vs-historical model for a label-sensitivity scenario."""
    variant_df = df[df["analysis_bucket"].isin(["mythic", "historical"])].copy()
    bucket_counts = (
        variant_df["analysis_bucket"].value_counts().sort_index().to_dict()
        if len(variant_df) > 0
        else {}
    )
    y = (variant_df["analysis_bucket"] == "mythic").astype(int).to_numpy()
    min_class_count = min(bucket_counts.values()) if bucket_counts else 0
    result = {
        "id": scenario_id,
        "label": label,
        "description": description,
        "token_source": token_source,
        "sample_count": int(len(variant_df)),
        "bucket_counts": bucket_counts,
        "feature_count": 0,
        "predictors": pd.DataFrame(),
        "all_predictors": pd.DataFrame(),
        "metrics": None,
        "available": False,
        "message": "",
    }
    if sample_weight_column and sample_weight_column in variant_df.columns:
        result["downweighted_count"] = int(
            (variant_df[sample_weight_column].astype(float) < 1.0).sum()
        )

    if len(variant_df) < 20 or min_class_count < 5:
        result["message"] = "Not enough mythic and historical sentences for this label scenario."
        return result

    texts, stopwords, lemma_stats, message = _sentence_texts_and_stopwords(
        variant_df,
        token_source=token_source,
        proper_stopwords=proper_stopwords,
        lemma_lookup=lemma_lookup,
        extra_stopwords=[],
    )
    if message:
        result["message"] = message
        return result
    if lemma_stats is not None:
        result["lemma_stats"] = {**lemma_stats}

    weights = None
    if sample_weight_column and sample_weight_column in variant_df.columns:
        weights = variant_df[sample_weight_column].astype(float).to_numpy()

    vectorizer = _new_sentence_vectorizer(
        stopwords,
        max_features=max_features,
        min_df=min_df,
    )
    model = _new_sentence_logistic_model()
    try:
        if weights is None:
            X_train, X_test, y_train, y_test = train_test_split(
                texts,
                y,
                test_size=0.25,
                random_state=42,
                stratify=y,
            )
            train_weights = None
        else:
            X_train, X_test, y_train, y_test, train_weights, _test_weights = train_test_split(
                texts,
                y,
                weights,
                test_size=0.25,
                random_state=42,
                stratify=y,
            )
        train_matrix = vectorizer.fit_transform(X_train)
        if train_matrix.shape[1] == 0:
            result["message"] = "No repeated vocabulary survived filtering."
            return result
        if train_weights is None:
            model.fit(train_matrix, y_train)
        else:
            model.fit(train_matrix, y_train, sample_weight=train_weights)
        test_matrix = vectorizer.transform(X_test)
        y_pred = model.predict(test_matrix)
    except ValueError as exc:
        result["message"] = f"Could not fit model: {exc}"
        return result

    feature_names = vectorizer.get_feature_names_out()
    coefficients = model.coef_[0]
    analyzer = vectorizer.build_analyzer()
    vocab = set(feature_names)
    mythic_counter = Counter()
    historical_counter = Counter()
    total_mythic = int(np.sum(y))
    total_historical = len(y) - total_mythic

    for text, label_value in zip(texts, y):
        terms = {term for term in analyzer(text) if term in vocab}
        if label_value:
            mythic_counter.update(terms)
        else:
            historical_counter.update(terms)

    mythic_counts = np.array([mythic_counter.get(feature, 0) for feature in feature_names])
    historical_counts = np.array(
        [historical_counter.get(feature, 0) for feature in feature_names]
    )
    p_values, q_values = compute_p_q_values(
        mythic_counts,
        historical_counts,
        total_mythic,
        total_historical,
    )

    predictor_rows = pd.DataFrame(
        {
            "phrase": feature_names,
            "english_translation": "",
            "coefficient": coefficients,
            "is_mythic": (coefficients > 0).astype(int),
            "mythic_count": mythic_counts,
            "historical_count": historical_counts,
            "p_value": p_values,
            "q_value": q_values,
        }
    )
    top_positive = predictor_rows.sort_values("coefficient", ascending=False).head(
        top_features
    )
    top_negative = predictor_rows.sort_values("coefficient", ascending=True).head(
        top_features
    )
    result.update(
        {
            "available": True,
            "feature_count": int(len(feature_names)),
            "predictors": pd.concat([top_negative, top_positive]).reset_index(drop=True),
            "all_predictors": predictor_rows.reset_index(drop=True),
            "metrics": _binary_classification_metrics(y_test, y_pred),
        }
    )
    return result


def _scenario_feature_stability(scenarios, *, top_n=40):
    baseline = next((scenario for scenario in scenarios if scenario.get("id") == "gpt_book3"), None)
    if not baseline or not baseline.get("available"):
        return []
    all_predictors = baseline.get("all_predictors")
    if all_predictors is None or len(all_predictors) == 0:
        return []

    baseline_terms = (
        all_predictors.assign(abs_coefficient=all_predictors["coefficient"].abs())
        .sort_values("abs_coefficient", ascending=False)
        .head(top_n)
    )
    scenario_maps = {}
    for scenario in scenarios:
        predictors = scenario.get("all_predictors")
        if predictors is None or len(predictors) == 0:
            scenario_maps[scenario["id"]] = {}
            continue
        scenario_maps[scenario["id"]] = dict(
            zip(predictors["phrase"], predictors["coefficient"])
        )

    rows = []
    for _, row in baseline_terms.iterrows():
        term = row["phrase"]
        coefficients = {
            scenario["id"]: scenario_maps.get(scenario["id"], {}).get(term)
            for scenario in scenarios
        }
        present_values = [
            float(value) for value in coefficients.values() if value is not None
        ]
        nonzero_signs = {
            1 if value > 0 else -1
            for value in present_values
            if abs(value) > 1e-12
        }
        rows.append(
            {
                "phrase": term,
                "baseline_coefficient": float(row["coefficient"]),
                "baseline_direction": "mythic" if row["coefficient"] > 0 else "historical",
                "coefficients": coefficients,
                "present_scenario_count": int(len(present_values)),
                "sign_stable": len(nonzero_signs) <= 1,
                "coefficient_min": float(min(present_values)) if present_values else None,
                "coefficient_max": float(max(present_values)) if present_values else None,
            }
        )
    return rows


def _manual_conditioned_probabilities(joined):
    probability_map = {}
    for greta_bucket, group in joined.groupby("greta_bucket"):
        counts = Counter(group["manual_bucket"])
        mythic = counts.get("mythic", 0) + 0.5 * counts.get("mixed_mythic_historical", 0)
        historical = counts.get("historical", 0) + 0.5 * counts.get("mixed_mythic_historical", 0)
        other = counts.get("other", 0)
        total = mythic + historical + other
        if total <= 0:
            continue
        probability_map[greta_bucket] = {
            "buckets": np.array(["historical", "mythic", "other"], dtype=object),
            "probabilities": np.array(
                [historical / total, mythic / total, other / total],
                dtype=float,
            ),
        }
    return probability_map


def _monte_carlo_label_noise_analysis(
    joined,
    *,
    proper_stopwords,
    lemma_lookup,
    baseline_terms,
    iterations=30,
):
    probability_map = _manual_conditioned_probabilities(joined)
    if not probability_map or not baseline_terms:
        return {
            "available": False,
            "message": "No manual/GPT confusion probabilities are available.",
            "iterations": 0,
            "terms": [],
            "metrics": {},
        }

    rng = np.random.default_rng(42)
    term_coefficients = defaultdict(list)
    accuracies = []
    sample_counts = []
    completed = 0
    for iteration in range(iterations):
        sampled = joined.copy()
        sampled_buckets = []
        for _, row in sampled.iterrows():
            probs = probability_map.get(row["greta_bucket"])
            if probs is None:
                sampled_buckets.append("other")
                continue
            sampled_buckets.append(
                rng.choice(probs["buckets"], p=probs["probabilities"])
            )
        sampled["analysis_bucket"] = sampled_buckets
        scenario = _fit_label_sensitivity_scenario(
            sampled,
            scenario_id=f"noise_{iteration + 1}",
            label=f"Noise run {iteration + 1}",
            description="Sampled from the observed manual-vs-GPT confusion rates.",
            token_source="lemma",
            proper_stopwords=proper_stopwords,
            lemma_lookup=lemma_lookup,
            max_features=500,
            top_features=10,
        )
        if not scenario.get("available"):
            continue
        completed += 1
        sample_counts.append(int(scenario.get("sample_count", 0)))
        metrics = scenario.get("metrics") or {}
        if metrics.get("accuracy") is not None:
            accuracies.append(float(metrics["accuracy"]))
        predictors = scenario.get("all_predictors")
        if predictors is None or len(predictors) == 0:
            continue
        predictor_map = dict(zip(predictors["phrase"], predictors["coefficient"]))
        for term in baseline_terms:
            if term in predictor_map:
                term_coefficients[term].append(float(predictor_map[term]))

    term_rows = []
    for term in baseline_terms:
        values = term_coefficients.get(term, [])
        if not values:
            term_rows.append(
                {
                    "phrase": term,
                    "present_count": 0,
                    "positive_count": 0,
                    "negative_count": 0,
                    "mean_coefficient": None,
                    "coefficient_min": None,
                    "coefficient_max": None,
                    "sign_stability": None,
                }
            )
            continue
        positive = sum(1 for value in values if value > 0)
        negative = sum(1 for value in values if value < 0)
        term_rows.append(
            {
                "phrase": term,
                "present_count": int(len(values)),
                "positive_count": int(positive),
                "negative_count": int(negative),
                "mean_coefficient": float(np.mean(values)),
                "coefficient_min": float(min(values)),
                "coefficient_max": float(max(values)),
                "sign_stability": float(max(positive, negative) / len(values)),
            }
        )

    metrics = {
        "completed_iterations": int(completed),
        "requested_iterations": int(iterations),
        "mean_accuracy": float(np.mean(accuracies)) if accuracies else None,
        "min_accuracy": float(min(accuracies)) if accuracies else None,
        "max_accuracy": float(max(accuracies)) if accuracies else None,
        "mean_sample_count": float(np.mean(sample_counts)) if sample_counts else None,
    }
    return {
        "available": completed > 0,
        "message": "" if completed else "No Monte Carlo label-noise models could be fit.",
        "iterations": int(completed),
        "terms": term_rows,
        "metrics": metrics,
    }


def get_manual_label_sensitivity_analysis(
    conn,
    *,
    source_id=MANUAL_SENTENCE_SOURCE_ID,
    proper_stopwords=None,
    lemma_lookup=None,
):
    """Compare manual Greta/Rosie labels with GPT Greta tags and refit models."""
    if not table_exists(conn, "sentence_manual_tags") or not table_exists(conn, "sentence_greta_tags"):
        return {
            "available": False,
            "message": "Manual sentence labels or Greta sentence tags are not available.",
            "source_id": source_id,
        }

    joined = read_sql_query(
        """
        SELECT gs.passage_id,
               gs.sentence_number,
               gs.sentence,
               gs.english_sentence,
               m.source_id,
               m.annotators,
               m.source_document,
               m.manual_label,
               m.manual_bucket,
               m.yellow_mythic,
               m.blue_historical,
               m.green_both,
               m.alignment_coverage,
               m.alignment_status,
               t.prompt_version,
               COALESCE(NULLIF(t.model, ''), NULLIF(r.model, ''), t.model) AS model,
               t.myth_history_bucket AS greta_bucket,
               t.confidence AS greta_confidence,
               t.rationale AS greta_rationale
        FROM sentence_manual_tags m
        JOIN greek_sentences gs
          ON gs.passage_id = m.passage_id
         AND gs.sentence_number = m.sentence_number
        JOIN sentence_greta_tags t
          ON t.passage_id = m.passage_id
         AND t.sentence_number = m.sentence_number
         AND t.prompt_version = %s
        LEFT JOIN sentence_tagging_runs r
          ON r.run_id = t.run_id
        WHERE m.source_id = %s
        ORDER BY gs.passage_id, gs.sentence_number
        """,
        conn,
        (GRETA_SENTENCE_PROMPT_VERSION, source_id),
    )
    if len(joined) == 0:
        return {
            "available": False,
            "message": f"No joined manual/GPT sentence labels found for {source_id}.",
            "source_id": source_id,
        }

    joined = _add_sentence_sort_columns(joined)
    joined["comparison_result"] = joined.apply(
        lambda row: _comparison_result(row["manual_bucket"], row["greta_bucket"]),
        axis=1,
    )
    joined["component_agreement"] = joined.apply(
        lambda row: _manual_component_agrees(row["manual_bucket"], row["greta_bucket"]),
        axis=1,
    )

    manual_label_counts = Counter(joined["manual_label"])
    manual_bucket_counts = Counter(joined["manual_bucket"])
    greta_bucket_counts = Counter(joined["greta_bucket"])
    comparison_counts = Counter(joined["comparison_result"])
    confusion = Counter(zip(joined["manual_bucket"], joined["greta_bucket"]))
    manual_label_confusion = Counter(zip(joined["manual_label"], joined["greta_bucket"]))

    proper_stopwords = proper_stopwords if proper_stopwords is not None else _stopword_rows(conn)
    lemma_lookup = lemma_lookup if lemma_lookup is not None else (
        load_word_lemma_lookup(conn) if table_exists(conn, "greek_word_lemmas") else {}
    )

    gpt_scope = joined.copy()
    gpt_scope["analysis_bucket"] = gpt_scope["greta_bucket"]
    manual_scope = joined.copy()
    manual_scope["analysis_bucket"] = manual_scope["manual_bucket"]
    agreement_scope = joined[
        (joined["manual_bucket"].isin(["mythic", "historical"]))
        & (joined["manual_bucket"] == joined["greta_bucket"])
    ].copy()
    agreement_scope["analysis_bucket"] = agreement_scope["manual_bucket"]
    weighted_scope = joined.copy()
    weighted_scope["analysis_bucket"] = weighted_scope["greta_bucket"]
    weighted_scope["scenario_weight"] = np.where(weighted_scope["component_agreement"], 1.0, 0.35)

    scenario_inputs = [
        (
            gpt_scope,
            "gpt_book3",
            "GPT labels on manual Book 3 scope",
            "Uses the active GPT-5.4-mini three-way tags, restricted to sentences that have manual Book 3 labels.",
            None,
        ),
        (
            manual_scope,
            "manual_strict",
            "Manual labels only",
            "Uses Greta/Rosie manual labels; unhighlighted and mixed rows are dropped for mythic-vs-historical fitting.",
            None,
        ),
        (
            agreement_scope,
            "agreement_only",
            "Agreement-only labels",
            "Keeps only sentences where manual and GPT labels exactly agree as mythic or historical.",
            None,
        ),
        (
            weighted_scope,
            "gpt_downweighted_disagreements",
            "GPT labels, disagreements downweighted",
            "Uses GPT labels but gives manual/GPT disagreements 35% of the weight of agreement rows.",
            "scenario_weight",
        ),
    ]
    scenarios = [
        _fit_label_sensitivity_scenario(
            frame,
            scenario_id=scenario_id,
            label=label,
            description=description,
            token_source="lemma",
            proper_stopwords=proper_stopwords,
            lemma_lookup=lemma_lookup,
            sample_weight_column=weight_column,
        )
        for frame, scenario_id, label, description, weight_column in scenario_inputs
    ]

    stability = _scenario_feature_stability(scenarios)
    baseline_terms = [row["phrase"] for row in stability[:25]]
    monte_carlo = _monte_carlo_label_noise_analysis(
        joined,
        proper_stopwords=proper_stopwords,
        lemma_lookup=lemma_lookup,
        baseline_terms=baseline_terms,
    )

    exact_comparable = int(joined["manual_bucket"].isin(["mythic", "historical", "other"]).sum())
    exact_agreement = int((joined["comparison_result"] == "exact_agreement").sum())
    return {
        "available": True,
        "message": "",
        "source_id": source_id,
        "source_document": joined.iloc[0].get("source_document", ""),
        "annotators": joined.iloc[0].get("annotators", ""),
        "prompt_version": joined.iloc[0].get("prompt_version", ""),
        "model": joined.iloc[0].get("model", ""),
        "sentence_count": int(len(joined)),
        "exact_comparable_count": exact_comparable,
        "exact_agreement_count": exact_agreement,
        "exact_agreement_rate": float(exact_agreement / exact_comparable) if exact_comparable else None,
        "manual_label_counts": _counter_records(manual_label_counts, "manual_label"),
        "manual_bucket_counts": _counter_records(manual_bucket_counts, "manual_bucket"),
        "greta_bucket_counts": _counter_records(greta_bucket_counts, "greta_bucket"),
        "comparison_counts": _counter_records(comparison_counts, "comparison_result"),
        "confusion": _counter_records(confusion, "manual_bucket", "greta_bucket"),
        "manual_label_confusion": _counter_records(
            manual_label_confusion,
            "manual_label",
            "greta_bucket",
        ),
        "scenarios": scenarios,
        "stability": stability,
        "monte_carlo": monte_carlo,
    }


def get_passage_mythicness_metrics(conn):
    """Get classification metrics for passage-level mythicness prediction."""
    query = """
    SELECT *
    FROM passage_mythicness_metrics
    ORDER BY id DESC
    LIMIT 1
    """
    df = read_sql_query(query, conn)
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def get_passage_skepticism_metrics(conn):
    """Get classification metrics for passage-level skepticism prediction."""
    query = """
    SELECT *
    FROM passage_skepticism_metrics
    ORDER BY id DESC
    LIMIT 1
    """
    df = read_sql_query(query, conn)
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def get_sentence_mythicness_metrics(conn):
    """Get classification metrics for sentence-level mythicness prediction."""
    query = """
    SELECT *
    FROM sentence_mythicness_metrics
    ORDER BY id DESC
    LIMIT 1
    """
    df = read_sql_query(query, conn)
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def get_sentence_skepticism_metrics(conn):
    """Get classification metrics for sentence-level skepticism prediction."""
    query = """
    SELECT *
    FROM sentence_skepticism_metrics
    ORDER BY id DESC
    LIMIT 1
    """
    df = read_sql_query(query, conn)
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def get_simplified_mythicness_metrics(conn):
    """Get reduced-model metrics for passage-level mythicness."""
    if not table_exists(conn, "simplified_mythicness_metrics"):
        return None

    query = """
    SELECT *
    FROM simplified_mythicness_metrics
    ORDER BY id DESC
    LIMIT 1
    """
    df = read_sql_query(query, conn)
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def get_simplified_skepticism_metrics(conn):
    """Get reduced-model metrics for passage-level skepticism."""
    if not table_exists(conn, "simplified_skepticism_metrics"):
        return None

    query = """
    SELECT *
    FROM simplified_skepticism_metrics
    ORDER BY id DESC
    LIMIT 1
    """
    df = read_sql_query(query, conn)
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def get_sentence_simplified_mythicness_metrics(conn):
    """Get reduced-model metrics for sentence-level mythicness."""
    if not table_exists(conn, "sentence_simplified_mythicness_metrics"):
        return None

    query = """
    SELECT *
    FROM sentence_simplified_mythicness_metrics
    ORDER BY id DESC
    LIMIT 1
    """
    df = read_sql_query(query, conn)
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def get_sentence_simplified_skepticism_metrics(conn):
    """Get reduced-model metrics for sentence-level skepticism."""
    if not table_exists(conn, "sentence_simplified_skepticism_metrics"):
        return None

    query = """
    SELECT *
    FROM sentence_simplified_skepticism_metrics
    ORDER BY id DESC
    LIMIT 1
    """
    df = read_sql_query(query, conn)
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def get_map_data(conn):
    """Get place coordinates with their associated passage IDs for the map."""
    cursor = conn.cursor()

    if not table_exists(conn, "wikidata_entities"):
        return []

    # Get all places with coordinates
    cursor.execute("""
        SELECT DISTINCT e.wikidata_qid, pn.reference_form, pn.english_transcription,
               e.latitude, e.longitude, e.pleiades_id
        FROM proper_nouns pn
        JOIN wikidata_links w
            ON pn.reference_form = w.reference_form
            AND pn.entity_type = w.entity_type
        JOIN wikidata_entities e
            ON w.wikidata_qid = e.wikidata_qid
        WHERE pn.entity_type = 'place'
          AND e.latitude IS NOT NULL
          AND e.longitude IS NOT NULL
        ORDER BY pn.reference_form
    """)
    places = cursor.fetchall()

    if not places:
        return []

    # For each place, find the passages where it appears
    map_data = []
    for qid, reference_form, english, lat, lon, pleiades_id in places:
        cursor.execute("""
            SELECT DISTINCT passage_id
            FROM proper_nouns
            WHERE reference_form = %s AND entity_type = 'place'
            ORDER BY passage_id
        """, (reference_form,))
        passage_ids = [row[0] for row in cursor.fetchall()]

        map_data.append({
            "qid": qid,
            "reference_form": reference_form,
            "english": english,
            "lat": lat,
            "lon": lon,
            "pleiades_id": pleiades_id,
            "passages": passage_ids,
        })

    return map_data


def _haversine_km(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points in kilometers."""
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def get_place_pairs(conn):
    """Get place pairs that appear in the same passage, sorted by distance."""
    cursor = conn.cursor()

    if not table_exists(conn, "wikidata_entities") or not table_exists(conn, "wikidata_links"):
        return []

    cursor.execute("""
        SELECT pn.passage_id, pn.reference_form, pn.english_transcription,
               e.latitude, e.longitude, e.pleiades_id
        FROM proper_nouns pn
        JOIN wikidata_links w
            ON pn.reference_form = w.reference_form
            AND pn.entity_type = w.entity_type
        JOIN wikidata_entities e
            ON w.wikidata_qid = e.wikidata_qid
        WHERE pn.entity_type = 'place'
          AND e.latitude IS NOT NULL
          AND e.longitude IS NOT NULL
        ORDER BY pn.passage_id, pn.reference_form
    """)
    rows = cursor.fetchall()

    if not rows:
        return []

    places_by_passage = {}
    for passage_id, ref_form, english, lat, lon, pleiades_id in rows:
        if passage_id not in places_by_passage:
            places_by_passage[passage_id] = {}
        key = (ref_form, lat, lon)
        if key not in places_by_passage[passage_id]:
            places_by_passage[passage_id][key] = {
                "reference_form": ref_form,
                "english": english,
                "lat": lat,
                "lon": lon,
                "pleiades_id": pleiades_id,
            }

    place_pairs = []
    for passage_id, places_map in places_by_passage.items():
        places = list(places_map.values())
        if len(places) < 2:
            continue
        for i in range(len(places) - 1):
            for j in range(i + 1, len(places)):
                place_a = places[i]
                place_b = places[j]
                distance_km = _haversine_km(
                    place_a["lat"], place_a["lon"],
                    place_b["lat"], place_b["lon"]
                )
                place_pairs.append({
                    "passage_id": passage_id,
                    "place_a": place_a,
                    "place_b": place_b,
                    "distance_km": distance_km,
                })

    place_pairs.sort(key=lambda p: p["distance_km"], reverse=True)
    return place_pairs


def _network_entity_type(entity_type):
    """Normalize the few historical proper-noun type variants in the database."""
    value = str(entity_type or "").strip().lower()
    if value.startswith("place"):
        return "place"
    if value.startswith("deity"):
        return "deity"
    if value.startswith("person") or value in {"people", "people group"}:
        return "person"
    return "other"


def _network_node_key(row):
    return (str(row["reference_form"]), _network_entity_type(row["entity_type"]))


def _network_node_id(node):
    return f"{node[0]}|{node[1]}"


def _network_node_label(attrs, node=None):
    english = attrs.get("english") or attrs.get("english_transcription") or ""
    reference_form = attrs.get("reference_form") or (node[0] if node else "")
    if english and reference_form and english != reference_form:
        return f"{english} ({reference_form})"
    return english or reference_form or "Unknown"


def _graph_from_context_rows(rows_df):
    """Build a co-occurrence graph from rows with a context_id and proper noun columns."""
    graph = nx.Graph()
    if rows_df is None or len(rows_df) == 0:
        return graph, {}

    context_nodes = defaultdict(dict)
    context_counts = defaultdict(int)
    node_attrs = {}

    for _, row in rows_df.iterrows():
        reference_form = str(row["reference_form"])
        entity_type = _network_entity_type(row["entity_type"])
        key = (reference_form, entity_type)
        english = row.get("english_transcription") or reference_form
        context_id = row["context_id"]

        node_attrs.setdefault(
            key,
            {
                "reference_form": reference_form,
                "entity_type": entity_type,
                "english": english,
            },
        )
        context_nodes[context_id][key] = True

    edge_weights = Counter()
    for nodes_map in context_nodes.values():
        nodes = sorted(nodes_map)
        for node in nodes:
            context_counts[node] += 1
        for source, target in combinations(nodes, 2):
            edge_weights[(source, target)] += 1

    for node, attrs in node_attrs.items():
        graph.add_node(node, **attrs)

    for (source, target), weight in edge_weights.items():
        graph.add_edge(source, target, weight=int(weight), distance=1.0 / float(weight))

    return graph, context_counts


def _graph_metrics(graph):
    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    component_sizes = (
        sorted((len(component) for component in nx.connected_components(graph)), reverse=True)
        if node_count
        else []
    )
    entity_counts = Counter(
        attrs.get("entity_type", "other") for _, attrs in graph.nodes(data=True)
    )
    return {
        "node_count": int(node_count),
        "edge_count": int(edge_count),
        "component_count": int(len(component_sizes)),
        "largest_component_size": int(component_sizes[0]) if component_sizes else 0,
        "density": float(nx.density(graph)) if node_count > 1 else 0.0,
        "total_edge_weight": int(
            sum(attrs.get("weight", 1) for _, _, attrs in graph.edges(data=True))
        ),
        "entity_counts": dict(entity_counts),
    }


def _weighted_strengths(graph):
    return {
        node: sum(attrs.get("weight", 1) for _, _, attrs in graph.edges(node, data=True))
        for node in graph.nodes()
    }


def _betweenness_centrality(graph):
    node_count = graph.number_of_nodes()
    if node_count <= 2 or graph.number_of_edges() == 0:
        return {node: 0.0 for node in graph.nodes()}
    if node_count <= NETWORK_BETWEENNESS_EXACT_LIMIT:
        return nx.betweenness_centrality(graph, weight="distance")
    return nx.betweenness_centrality(
        graph,
        k=min(NETWORK_BETWEENNESS_SAMPLE_SIZE, node_count),
        weight="distance",
        seed=42,
    )


def _centrality_rows(graph, context_counts=None, limit=30, include_betweenness=True):
    if graph.number_of_nodes() == 0:
        return []

    context_counts = context_counts or {}
    strengths = _weighted_strengths(graph)
    degree_centrality = nx.degree_centrality(graph) if graph.number_of_nodes() > 1 else {
        node: 0.0 for node in graph.nodes()
    }
    betweenness = _betweenness_centrality(graph) if include_betweenness else {
        node: 0.0 for node in graph.nodes()
    }

    rows = []
    for node, attrs in graph.nodes(data=True):
        rows.append(
            {
                "node_id": _network_node_id(node),
                "reference_form": attrs.get("reference_form", node[0]),
                "english": attrs.get("english", node[0]),
                "label": _network_node_label(attrs, node),
                "entity_type": attrs.get("entity_type", node[1]),
                "context_count": int(context_counts.get(node, 0)),
                "neighbor_count": int(graph.degree(node)),
                "strength": int(strengths.get(node, 0)),
                "degree_centrality": float(degree_centrality.get(node, 0.0)),
                "betweenness_centrality": float(betweenness.get(node, 0.0)),
            }
        )

    rows.sort(
        key=lambda row: (
            row["betweenness_centrality"],
            row["strength"],
            row["neighbor_count"],
            row["label"],
        ),
        reverse=True,
    )
    return rows[:limit]


def _community_rows(graph, limit=10):
    if graph.number_of_nodes() == 0 or graph.number_of_edges() == 0:
        return []

    try:
        if graph.number_of_nodes() <= 800:
            communities = nx.community.greedy_modularity_communities(graph, weight="weight")
        else:
            communities = list(
                nx.community.asyn_lpa_communities(graph, weight="weight", seed=42)
            )
    except (nx.NetworkXException, ZeroDivisionError):
        return []

    strengths = _weighted_strengths(graph)
    rows = []
    for idx, community in enumerate(sorted(communities, key=len, reverse=True)[:limit], start=1):
        subgraph = graph.subgraph(community)
        entity_counts = Counter(
            graph.nodes[node].get("entity_type", "other") for node in community
        )
        top_nodes = sorted(
            community,
            key=lambda node: (strengths.get(node, 0), graph.degree(node), node[0]),
            reverse=True,
        )[:8]
        rows.append(
            {
                "community": idx,
                "size": int(len(community)),
                "edge_count": int(subgraph.number_of_edges()),
                "entity_counts": dict(entity_counts),
                "top_nodes": [
                    _network_node_label(graph.nodes[node], node) for node in top_nodes
                ],
            }
        )
    return rows


def _get_sentence_noun_matches(conn):
    """Return proper nouns matched into active Greta-tagged sentences by exact form."""
    if not table_exists(conn, "sentence_greta_tags"):
        return pd.DataFrame(), {
            "tagged_sentence_count": 0,
            "sentences_with_matched_nouns": 0,
            "noun_mentions": 0,
            "distinct_nodes": 0,
        }

    rows = read_sql_query(
        """
        SELECT gs.passage_id,
               gs.sentence_number,
               gs.sentence,
               t.myth_history_bucket,
               pn.exact_form,
               pn.reference_form,
               pn.entity_type,
               pn.english_transcription
        FROM greek_sentences gs
        JOIN sentence_greta_tags t
          ON t.passage_id = gs.passage_id
         AND t.sentence_number = gs.sentence_number
        JOIN proper_nouns pn
          ON pn.passage_id = gs.passage_id
        WHERE t.prompt_version = %s
        ORDER BY gs.passage_id, gs.sentence_number, pn.reference_form
        """,
        conn,
        (GRETA_SENTENCE_PROMPT_VERSION,),
    )
    if len(rows) == 0:
        return rows, {
            "tagged_sentence_count": 0,
            "sentences_with_matched_nouns": 0,
            "noun_mentions": 0,
            "distinct_nodes": 0,
        }

    tagged_sentence_count = int(
        rows[["passage_id", "sentence_number"]].drop_duplicates().shape[0]
    )
    matches = rows[
        rows.apply(lambda row: str(row["exact_form"]) in str(row["sentence"]), axis=1)
    ].copy()
    if len(matches) > 0:
        matches["book"] = matches["passage_id"].apply(lambda pid: str(pid).split(".")[0])
        matches["context_id"] = matches.apply(
            lambda row: f"{row['passage_id']}:{int(row['sentence_number'])}",
            axis=1,
        )
        distinct_nodes = int(
            matches[["reference_form", "entity_type"]].drop_duplicates().shape[0]
        )
        sentences_with_nouns = int(
            matches[["passage_id", "sentence_number"]].drop_duplicates().shape[0]
        )
    else:
        distinct_nodes = 0
        sentences_with_nouns = 0

    return matches, {
        "tagged_sentence_count": tagged_sentence_count,
        "sentences_with_matched_nouns": sentences_with_nouns,
        "noun_mentions": int(len(matches)),
        "distinct_nodes": distinct_nodes,
    }


def _get_passage_noun_rows(conn):
    rows = read_sql_query(
        """
        SELECT passage_id,
               reference_form,
               entity_type,
               english_transcription
        FROM proper_nouns
        ORDER BY passage_id, reference_form
        """,
        conn,
    )
    if len(rows) == 0:
        return rows
    rows["book"] = rows["passage_id"].apply(lambda pid: str(pid).split(".")[0])
    rows["context_id"] = rows["passage_id"]
    rows["entity_type"] = rows["entity_type"].apply(_network_entity_type)
    return rows


def _class_subgraph_analysis(sentence_nouns):
    subgraphs = {}
    for bucket in ["mythic", "historical"]:
        bucket_rows = sentence_nouns[sentence_nouns["myth_history_bucket"] == bucket]
        graph, context_counts = _graph_from_context_rows(bucket_rows)
        subgraphs[bucket] = {
            "bucket": bucket,
            "metrics": _graph_metrics(graph),
            "top_nodes": _centrality_rows(graph, context_counts, limit=35),
            "communities": _community_rows(graph, limit=10),
        }
    return subgraphs


def _bridge_noun_rows(sentence_nouns, limit=60):
    relevant = sentence_nouns[
        sentence_nouns["myth_history_bucket"].isin(["mythic", "historical"])
    ].copy()
    graph, _ = _graph_from_context_rows(relevant)
    if graph.number_of_nodes() == 0:
        return []

    bucket_contexts = defaultdict(lambda: defaultdict(set))
    for _, row in sentence_nouns.iterrows():
        node = _network_node_key(row)
        bucket_contexts[node][row["myth_history_bucket"]].add(row["context_id"])

    betweenness = _betweenness_centrality(graph)
    strengths = _weighted_strengths(graph)
    rows = []
    for node, attrs in graph.nodes(data=True):
        mythic_count = len(bucket_contexts[node].get("mythic", set()))
        historical_count = len(bucket_contexts[node].get("historical", set()))
        if mythic_count == 0 or historical_count == 0:
            continue
        total = mythic_count + historical_count
        balance = (2.0 * min(mythic_count, historical_count) / total) if total else 0.0
        bridge_score = float(betweenness.get(node, 0.0)) * (1.0 + math.log1p(total)) * balance
        rows.append(
            {
                "label": _network_node_label(attrs, node),
                "reference_form": attrs.get("reference_form", node[0]),
                "english": attrs.get("english", node[0]),
                "entity_type": attrs.get("entity_type", node[1]),
                "mythic_count": int(mythic_count),
                "historical_count": int(historical_count),
                "other_count": int(len(bucket_contexts[node].get("other", set()))),
                "neighbor_count": int(graph.degree(node)),
                "strength": int(strengths.get(node, 0)),
                "betweenness_centrality": float(betweenness.get(node, 0.0)),
                "bridge_score": bridge_score,
            }
        )

    rows.sort(
        key=lambda row: (
            row["bridge_score"],
            row["betweenness_centrality"],
            row["strength"],
            row["label"],
        ),
        reverse=True,
    )
    return rows[:limit]


def _louvain_core_analysis(
    sentence_nouns,
    *,
    min_contexts=10,
    min_strength=20,
    exclude_books=("4", "8"),
    limit_communities=20,
):
    relevant = sentence_nouns[
        sentence_nouns["myth_history_bucket"].isin(["mythic", "historical"])
    ].copy()
    if exclude_books:
        relevant = relevant[~relevant["book"].isin(list(exclude_books))].copy()
    if len(relevant) == 0:
        return {
            "available": False,
            "message": "No mythic or historical sentence-level noun matches are available.",
            "communities": [],
        }

    graph, context_counts = _graph_from_context_rows(relevant)
    if graph.number_of_nodes() == 0 or graph.number_of_edges() == 0:
        return {
            "available": False,
            "message": "The shared noun graph is empty.",
            "communities": [],
        }

    largest_component_nodes = max(nx.connected_components(graph), key=len)
    largest_component = graph.subgraph(largest_component_nodes).copy()
    strengths = _weighted_strengths(largest_component)
    core_nodes = [
        node for node in largest_component.nodes()
        if context_counts.get(node, 0) >= min_contexts
        and strengths.get(node, 0) >= min_strength
    ]
    core_graph = largest_component.subgraph(core_nodes).copy()
    core_graph.remove_nodes_from(list(nx.isolates(core_graph)))
    if core_graph.number_of_nodes() == 0 or core_graph.number_of_edges() == 0:
        return {
            "available": False,
            "message": "No connected core remains after the context and strength thresholds.",
            "communities": [],
        }
    core_graph = core_graph.subgraph(max(nx.connected_components(core_graph), key=len)).copy()
    stable_core_graph = nx.Graph()
    for node in sorted(core_graph.nodes(), key=lambda value: (value[0], value[1])):
        stable_core_graph.add_node(node, **core_graph.nodes[node])
    for source, target, attrs in sorted(
        core_graph.edges(data=True),
        key=lambda edge: (edge[0][0], edge[0][1], edge[1][0], edge[1][1]),
    ):
        stable_core_graph.add_edge(source, target, **attrs)
    core_graph = stable_core_graph
    strengths = _weighted_strengths(core_graph)

    bucket_contexts = defaultdict(lambda: defaultdict(set))
    for _, row in relevant.iterrows():
        node = _network_node_key(row)
        if node in core_graph:
            bucket_contexts[node][row["myth_history_bucket"]].add(row["context_id"])

    node_bucket = {}
    for node in core_graph.nodes():
        mythic_contexts = len(bucket_contexts[node].get("mythic", set()))
        historical_contexts = len(bucket_contexts[node].get("historical", set()))
        if mythic_contexts > historical_contexts:
            dominant_bucket = "mythic"
        elif historical_contexts > mythic_contexts:
            dominant_bucket = "historical"
        else:
            dominant_bucket = "balanced"
        node_bucket[node] = dominant_bucket
        core_graph.nodes[node]["mythic_contexts"] = mythic_contexts
        core_graph.nodes[node]["historical_contexts"] = historical_contexts
        core_graph.nodes[node]["dominant_bucket"] = dominant_bucket

    try:
        communities = nx.community.louvain_communities(
            core_graph,
            weight="weight",
            seed=42,
            resolution=1.0,
        )
    except (AttributeError, nx.NetworkXException, ZeroDivisionError) as exc:
        return {
            "available": False,
            "message": f"Could not run Louvain community detection: {exc}",
            "communities": [],
        }

    communities = sorted(
        communities,
        key=lambda community: (
            -len(community),
            sorted(community, key=lambda node: (node[0], node[1]))[0],
        ),
    )
    modularity = nx.community.modularity(core_graph, communities, weight="weight")
    community_index = {}
    for idx, community in enumerate(communities, start=1):
        for node in community:
            community_index[node] = idx

    community_rows = []
    for idx, community in enumerate(communities[:limit_communities], start=1):
        node_counts = Counter(node_bucket[node] for node in community)
        mythic_contexts = sum(
            core_graph.nodes[node].get("mythic_contexts", 0) for node in community
        )
        historical_contexts = sum(
            core_graph.nodes[node].get("historical_contexts", 0) for node in community
        )
        if mythic_contexts > historical_contexts:
            dominant_context = "mythic"
        elif historical_contexts > mythic_contexts:
            dominant_context = "historical"
        else:
            dominant_context = "balanced"
        top_nodes = sorted(
            community,
            key=lambda node: (
                strengths.get(node, 0),
                core_graph.degree(node),
                node[0],
            ),
            reverse=True,
        )[:10]
        community_rows.append(
            {
                "community": int(idx),
                "size": int(len(community)),
                "node_mythic": int(node_counts.get("mythic", 0)),
                "node_historical": int(node_counts.get("historical", 0)),
                "node_balanced": int(node_counts.get("balanced", 0)),
                "context_mythic": int(mythic_contexts),
                "context_historical": int(historical_contexts),
                "dominant_context": dominant_context,
                "top_nodes": [
                    _network_node_label(core_graph.nodes[node], node)
                    for node in top_nodes
                ],
            }
        )

    cross_edges = Counter()
    for source, target, attrs in core_graph.edges(data=True):
        source_community = community_index[source]
        target_community = community_index[target]
        if source_community == target_community:
            continue
        cross_edges[tuple(sorted((source_community, target_community)))] += attrs.get(
            "weight",
            1,
        )
    cross_community_edges = [
        {
            "source": int(source),
            "target": int(target),
            "weight": int(weight),
        }
        for (source, target), weight in sorted(
            cross_edges.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    return {
        "available": True,
        "message": "",
        "scope": "excluding books 4 and 8",
        "min_contexts": int(min_contexts),
        "min_strength": int(min_strength),
        "source_sentence_count": int(
            relevant[["passage_id", "sentence_number"]].drop_duplicates().shape[0]
        ),
        "source_noun_mentions": int(len(relevant)),
        "source_node_count": int(graph.number_of_nodes()),
        "source_edge_count": int(graph.number_of_edges()),
        "largest_component_size": int(largest_component.number_of_nodes()),
        "core_node_count": int(core_graph.number_of_nodes()),
        "core_edge_count": int(core_graph.number_of_edges()),
        "community_count": int(len(communities)),
        "modularity": float(modularity),
        "dominant_node_counts": dict(Counter(node_bucket.values())),
        "communities": community_rows,
        "cross_community_edges": cross_community_edges[:30],
    }


def _node_set(graph):
    return set(graph.nodes())


def _edge_set(graph):
    return {tuple(sorted(edge)) for edge in graph.edges()}


def _jaccard(left, right):
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def _book_drift_analysis(passage_nouns):
    book_rows = []
    previous_nodes = None
    previous_edges = None
    for book in sorted(passage_nouns["book"].unique(), key=lambda value: int(value)):
        rows = passage_nouns[passage_nouns["book"] == book]
        graph, context_counts = _graph_from_context_rows(rows)
        top_nodes = _centrality_rows(
            graph,
            context_counts,
            limit=8,
            include_betweenness=False,
        )
        nodes = _node_set(graph)
        edges = _edge_set(graph)
        book_rows.append(
            {
                "book": book,
                "metrics": _graph_metrics(graph),
                "top_nodes": top_nodes,
                "node_jaccard_previous": None
                if previous_nodes is None
                else _jaccard(nodes, previous_nodes),
                "edge_jaccard_previous": None
                if previous_edges is None
                else _jaccard(edges, previous_edges),
            }
        )
        previous_nodes = nodes
        previous_edges = edges

    scopes = []
    for label, rows in [
        ("All books", passage_nouns),
        ("Excluding books 4 and 8", passage_nouns[~passage_nouns["book"].isin(["4", "8"])])
    ]:
        graph, context_counts = _graph_from_context_rows(rows)
        scopes.append(
            {
                "label": label,
                "metrics": _graph_metrics(graph),
                "top_nodes": _centrality_rows(
                    graph,
                    context_counts,
                    limit=15,
                    include_betweenness=False,
                ),
            }
        )

    return {"books": book_rows, "scopes": scopes}


def _bipartite_analysis(passage_nouns, limit=60):
    if len(passage_nouns) == 0:
        return {
            "pair_count": 0,
            "passage_count": 0,
            "top_pairs": [],
            "top_places": [],
            "top_people_deities": [],
        }

    context_nodes = defaultdict(dict)
    node_attrs = {}
    for _, row in passage_nouns.iterrows():
        node = _network_node_key(row)
        node_attrs.setdefault(
            node,
            {
                "reference_form": node[0],
                "entity_type": node[1],
                "english": row.get("english_transcription") or node[0],
            },
        )
        context_nodes[row["passage_id"]][node] = True

    pair_weights = Counter()
    pair_passages = defaultdict(set)
    for passage_id, nodes_map in context_nodes.items():
        nodes = set(nodes_map)
        places = sorted(node for node in nodes if node[1] == "place")
        actors = sorted(node for node in nodes if node[1] in {"person", "deity"})
        for place in places:
            for actor in actors:
                pair_weights[(place, actor)] += 1
                pair_passages[(place, actor)].add(passage_id)

    place_strength = Counter()
    actor_strength = Counter()
    for (place, actor), weight in pair_weights.items():
        place_strength[place] += weight
        actor_strength[actor] += weight

    top_pairs = []
    for (place, actor), weight in pair_weights.most_common(limit):
        top_pairs.append(
            {
                "place": _network_node_label(node_attrs[place], place),
                "counterpart": _network_node_label(node_attrs[actor], actor),
                "counterpart_type": actor[1],
                "weight": int(weight),
                "passage_count": int(len(pair_passages[(place, actor)])),
            }
        )

    def strength_rows(counter, row_limit):
        rows = []
        for node, strength in counter.most_common(row_limit):
            rows.append(
                {
                    "label": _network_node_label(node_attrs[node], node),
                    "entity_type": node[1],
                    "strength": int(strength),
                    "neighbor_count": int(
                        sum(1 for pair in pair_weights if node in pair)
                    ),
                }
            )
        return rows

    return {
        "pair_count": int(len(pair_weights)),
        "passage_count": int(
            len(
                {
                    passage_id
                    for passages in pair_passages.values()
                    for passage_id in passages
                }
            )
        ),
        "top_pairs": top_pairs,
        "top_places": strength_rows(place_strength, 30),
        "top_people_deities": strength_rows(actor_strength, 30),
    }


def get_extended_network_analysis(conn):
    """Build paper-facing network summaries beyond the full proper-noun map."""
    if not table_exists(conn, "proper_nouns"):
        return {
            "available": False,
            "message": "No proper-noun table is available.",
        }

    sentence_nouns, sentence_stats = _get_sentence_noun_matches(conn)
    passage_nouns = _get_passage_noun_rows(conn)
    if len(passage_nouns) == 0:
        return {
            "available": False,
            "message": "No proper-noun rows are available.",
            "sentence_matching": sentence_stats,
        }

    if len(sentence_nouns) == 0:
        class_subgraphs = {}
        bridge_nouns = []
        louvain_core = {
            "available": False,
            "message": "No sentence-level noun matches are available.",
            "communities": [],
        }
    else:
        class_subgraphs = _class_subgraph_analysis(sentence_nouns)
        bridge_nouns = _bridge_noun_rows(sentence_nouns)
        louvain_core = _louvain_core_analysis(sentence_nouns)

    return {
        "available": True,
        "message": "",
        "sentence_matching": sentence_stats,
        "class_subgraphs": class_subgraphs,
        "bridge_nouns": bridge_nouns,
        "louvain_core": louvain_core,
        "book_drift": _book_drift_analysis(passage_nouns),
        "bipartite": _bipartite_analysis(passage_nouns),
    }


MANTO_PLACE_PREFIX = "🌍"
MANTO_PLACE_EXCLUDED_RELATIONS = {
    "",
    "collection",
    "period",
    "source_attributes",
    "unesco_status",
}
MANTO_ATHENS_ATTICA_ID = "8188815"


def _manto_clean_label(value):
    text = str(value or "").strip()
    return re.sub(r"^[^\w]+", "", text).strip() or text or "Unknown"


def _manto_latest_release_id(conn):
    rows = read_sql_query(
        """
        SELECT record_id
        FROM manto_releases
        WHERE import_status IN ('imported', 'partial_imported')
        ORDER BY COALESCE(imported_at, updated_at) DESC, record_id DESC
        LIMIT 1
        """,
        conn,
    )
    if len(rows) == 0:
        return None
    return int(rows.iloc[0]["record_id"])


def _manto_edge_key(source_id, target_id):
    return tuple(sorted((str(source_id), str(target_id))))


def _add_manto_place_edge(graph, edge_details, source_id, target_id, relation, source_label, year):
    if not source_id or not target_id or source_id == target_id:
        return
    relation = str(relation or "").strip() or "related"
    if relation in MANTO_PLACE_EXCLUDED_RELATIONS:
        return
    if graph.has_edge(source_id, target_id):
        graph[source_id][target_id]["weight"] += 1
    else:
        graph.add_edge(source_id, target_id, weight=1)
    key = _manto_edge_key(source_id, target_id)
    detail = edge_details[key]
    detail["relations"][relation] += 1
    detail["sources"][(str(source_label or "MANTO edge row without source label"), year)] += 1


def _manto_weighted_strengths(graph):
    return {
        node: sum(attrs.get("weight", 1) for _, _, attrs in graph.edges(node, data=True))
        for node in graph.nodes()
    }


def _manto_community_payload(graph, communities, community_index, strengths, pagerank, places):
    rows = []
    for index, community in enumerate(communities, start=1):
        subgraph = graph.subgraph(community)
        parent_counts = Counter(
            places[node].get("parent_label") or "No locality parent"
            for node in community
        )
        top_nodes = sorted(
            community,
            key=lambda node: (
                strengths.get(node, 0),
                graph.degree(node),
                pagerank.get(node, 0.0),
                places[node]["label"],
            ),
            reverse=True,
        )[:10]
        rows.append(
            {
                "community": int(index),
                "size": int(len(community)),
                "edge_count": int(subgraph.number_of_edges()),
                "weighted_edges": int(
                    sum(attrs.get("weight", 1) for _, _, attrs in subgraph.edges(data=True))
                ),
                "top_localities": [
                    {
                        "label": _manto_clean_label(label),
                        "count": int(count),
                    }
                    for label, count in parent_counts.most_common(5)
                ],
                "top_places": [
                    {
                        "id": str(node),
                        "label": places[node]["label"],
                        "degree": int(graph.degree(node)),
                        "strength": int(strengths.get(node, 0)),
                        "pagerank": float(pagerank.get(node, 0.0)),
                    }
                    for node in top_nodes
                ],
                "contains_athens_attica": MANTO_ATHENS_ATTICA_ID in community,
            }
        )
    return rows


def _manto_edge_payload(graph, edge_details, source_id, target_id):
    attrs = graph.get_edge_data(source_id, target_id, default={})
    detail = edge_details.get(_manto_edge_key(source_id, target_id), {})
    relation_rows = detail.get("relations", Counter()).most_common(6)
    source_rows = detail.get("sources", Counter()).most_common(6)
    return {
        "source": str(source_id),
        "target": str(target_id),
        "weight": int(attrs.get("weight", 1)),
        "relations": [
            {"relation": relation, "count": int(count)}
            for relation, count in relation_rows
        ],
        "sources": [
            {
                "label": label,
                "latest_year": int(year) if year is not None and not pd.isna(year) else None,
                "count": int(count),
            }
            for (label, year), count in source_rows
        ],
    }


def _manto_node_payload(node_id, graph, places, community_index, strengths, pagerank, focus=False):
    return {
        "id": str(node_id),
        "label": places[node_id]["label"],
        "parent_label": _manto_clean_label(places[node_id].get("parent_label")),
        "community": int(community_index.get(node_id, 0)),
        "degree": int(graph.degree(node_id)),
        "strength": int(strengths.get(node_id, 0)),
        "pagerank": float(pagerank.get(node_id, 0.0)),
        "focus": bool(focus),
    }


def get_manto_place_network_analysis(conn, *, neighborhood_limit=75, community_limit=15):
    """Build compact MANTO place-network data for static website visualisations."""
    required_tables = {"manto_releases", "manto_entity_details", "manto_edges"}
    if not all(table_exists(conn, table) for table in required_tables):
        return {
            "available": False,
            "message": "MANTO tables are not available.",
        }

    release_id = _manto_latest_release_id(conn)
    if release_id is None:
        return {
            "available": False,
            "message": "No imported MANTO release is available.",
        }

    place_rows = read_sql_query(
        """
        SELECT object_id, name, somewhere_in_or_near_object_id,
               somewhere_in_or_near_label
        FROM manto_entity_details
        WHERE release_record_id = %s
          AND substring(name from 1 for 1) = %s
        """,
        conn,
        (release_id, MANTO_PLACE_PREFIX),
    )
    if len(place_rows) == 0:
        return {
            "available": False,
            "message": "No MANTO place details are available.",
        }

    places = {}
    for _, row in place_rows.iterrows():
        object_id = str(row["object_id"])
        places[object_id] = {
            "id": object_id,
            "label": _manto_clean_label(row["name"]),
            "raw_label": str(row["name"] or ""),
            "parent_id": str(row["somewhere_in_or_near_object_id"] or ""),
            "parent_label": str(row["somewhere_in_or_near_label"] or ""),
        }

    edge_rows = read_sql_query(
        """
        SELECT e.source_manto_id, e.target_manto_id, e.relation_type,
               e.evidence_source_label, e.evidence_latest_year
        FROM manto_edges e
        JOIN manto_entity_details sd
          ON sd.release_record_id = e.release_record_id
         AND sd.object_id = e.source_manto_id
         AND substring(sd.name from 1 for 1) = %s
        JOIN manto_entity_details td
          ON td.release_record_id = e.release_record_id
         AND td.object_id = e.target_manto_id
         AND substring(td.name from 1 for 1) = %s
        WHERE e.release_record_id = %s
          AND e.is_pre_pausanias
        """,
        conn,
        (MANTO_PLACE_PREFIX, MANTO_PLACE_PREFIX, release_id),
    )

    graph = nx.Graph()
    graph.add_nodes_from(places)
    edge_details = defaultdict(lambda: {"relations": Counter(), "sources": Counter()})

    for _, row in edge_rows.iterrows():
        source_id = str(row["source_manto_id"])
        target_id = str(row["target_manto_id"])
        if source_id not in places or target_id not in places:
            continue
        _add_manto_place_edge(
            graph,
            edge_details,
            source_id,
            target_id,
            str(row["relation_type"] or "").lower(),
            row["evidence_source_label"],
            row["evidence_latest_year"],
        )

    parent_edge_count = 0
    for place_id, place in places.items():
        parent_id = place.get("parent_id")
        if parent_id and parent_id in places and parent_id != place_id:
            _add_manto_place_edge(
                graph,
                edge_details,
                place_id,
                parent_id,
                "somewhere_in_or_near",
                "MANTO place-detail locality field",
                None,
            )
            parent_edge_count += 1

    connected_graph = graph.copy()
    connected_graph.remove_nodes_from(list(nx.isolates(connected_graph)))
    if connected_graph.number_of_edges() == 0:
        return {
            "available": False,
            "message": "The MANTO place graph has no place-place links.",
        }

    strengths = _manto_weighted_strengths(graph)
    pagerank = nx.pagerank(graph, weight="weight") if graph.number_of_edges() else {
        node: 0.0 for node in graph.nodes()
    }
    component_sizes = sorted((len(component) for component in nx.connected_components(graph)), reverse=True)
    try:
        communities = nx.community.louvain_communities(
            connected_graph,
            weight="weight",
            seed=42,
            resolution=1.0,
        )
    except (AttributeError, nx.NetworkXException, ZeroDivisionError):
        communities = list(nx.community.greedy_modularity_communities(connected_graph, weight="weight"))
    communities = sorted(
        communities,
        key=lambda community: (
            -len(community),
            sorted(places[node]["label"] for node in community)[0],
        ),
    )
    community_index = {}
    for index, community in enumerate(communities, start=1):
        for node in community:
            community_index[node] = index
    modularity = (
        nx.community.modularity(connected_graph, communities, weight="weight")
        if communities and connected_graph.number_of_edges()
        else 0.0
    )

    athens_id = MANTO_ATHENS_ATTICA_ID if MANTO_ATHENS_ATTICA_ID in graph else None
    if athens_id is None:
        for node_id, attrs in places.items():
            if attrs["raw_label"] == "🌍 Athens (Attica)" or attrs["label"] == "Athens (Attica)":
                athens_id = node_id
                break

    athens = {}
    athens_network = {"nodes": [], "links": []}
    if athens_id and athens_id in graph:
        athens_neighbors = set(graph.neighbors(athens_id))
        neighbor_subgraph = graph.subgraph(athens_neighbors)
        possible_neighbor_edges = len(athens_neighbors) * (len(athens_neighbors) - 1) / 2
        core_numbers = nx.core_number(connected_graph) if connected_graph.number_of_edges() else {}
        athens_community = community_index.get(athens_id, 0)
        athens_community_nodes = {
            node for node, index in community_index.items() if index == athens_community
        }
        athens = {
            "id": athens_id,
            "label": places[athens_id]["label"],
            "degree": int(graph.degree(athens_id)),
            "strength": int(strengths.get(athens_id, 0)),
            "pagerank": float(pagerank.get(athens_id, 0.0)),
            "community": int(athens_community),
            "community_size": int(len(athens_community_nodes)),
            "clustering": float(nx.clustering(graph, athens_id)) if graph.degree(athens_id) > 1 else 0.0,
            "triangles": int(nx.triangles(graph, athens_id)),
            "neighbor_edge_count": int(neighbor_subgraph.number_of_edges()),
            "neighbor_density": float(
                neighbor_subgraph.number_of_edges() / possible_neighbor_edges
            ) if possible_neighbor_edges else 0.0,
            "core_number": int(core_numbers.get(athens_id, 0)),
        }
        selected_neighbors = sorted(
            athens_neighbors,
            key=lambda node: (
                graph[athens_id][node].get("weight", 1),
                strengths.get(node, 0),
                graph.degree(node),
                pagerank.get(node, 0.0),
            ),
            reverse=True,
        )[:neighborhood_limit]
        selected_nodes = {athens_id, *selected_neighbors}
        athens_network = {
            "nodes": [
                _manto_node_payload(
                    node,
                    graph,
                    places,
                    community_index,
                    strengths,
                    pagerank,
                    focus=(node == athens_id),
                )
                for node in sorted(
                    selected_nodes,
                    key=lambda node: (node != athens_id, -strengths.get(node, 0), places[node]["label"]),
                )
            ],
            "links": [
                _manto_edge_payload(graph, edge_details, source, target)
                for source, target in graph.subgraph(selected_nodes).edges()
            ],
        }

    community_rows = _manto_community_payload(
        graph,
        communities[:community_limit],
        community_index,
        strengths,
        pagerank,
        places,
    )
    top_community_ids = {row["community"] for row in community_rows}
    community_edges = Counter()
    for source, target, attrs in graph.edges(data=True):
        source_community = community_index.get(source)
        target_community = community_index.get(target)
        if not source_community or not target_community or source_community == target_community:
            continue
        if source_community not in top_community_ids or target_community not in top_community_ids:
            continue
        community_edges[tuple(sorted((source_community, target_community)))] += attrs.get("weight", 1)

    community_network = {
        "nodes": [
            {
                "id": f"community-{row['community']}",
                "community": int(row["community"]),
                "label": f"Community {row['community']}",
                "size": int(row["size"]),
                "top_places": row["top_places"][:5],
                "top_localities": row["top_localities"][:3],
                "contains_athens_attica": bool(row["contains_athens_attica"]),
            }
            for row in community_rows
        ],
        "links": [
            {
                "source": f"community-{source}",
                "target": f"community-{target}",
                "weight": int(weight),
            }
            for (source, target), weight in community_edges.most_common(80)
        ],
    }

    return {
        "available": True,
        "message": "",
        "release_record_id": int(release_id),
        "pre_pausanias_only": True,
        "node_count": int(graph.number_of_nodes()),
        "edge_count": int(graph.number_of_edges()),
        "manto_place_edge_rows": int(len(edge_rows)),
        "somewhere_in_or_near_edges": int(parent_edge_count),
        "component_count": int(len(component_sizes)),
        "largest_component_size": int(component_sizes[0]) if component_sizes else 0,
        "community_count": int(len(communities)),
        "modularity": float(modularity),
        "athens": athens,
        "athens_network": athens_network,
        "communities": community_rows,
        "community_network": community_network,
    }


def get_translation_page_data(conn):
    """Get all data needed for translation pages: passages, translations, proper nouns with Wikidata info."""
    cursor = conn.cursor()

    # Get all passages with translations and classification
    cursor.execute("""
        SELECT p.id, p.passage, t.english_translation,
               p.references_mythic_era, p.expresses_scepticism
        FROM passages p
        LEFT JOIN translations t ON p.id = t.passage_id
        ORDER BY p.id
    """)
    passages_raw = cursor.fetchall()

    # Sort by numeric passage ID
    passages_raw.sort(key=lambda r: passage_id_sort_key(r[0]))

    # Build ordered passage list
    passages = []
    for pid, greek, english, is_mythic, is_skeptical in passages_raw:
        passages.append({
            "id": pid,
            "greek": greek,
            "english": english,
            "is_mythic": is_mythic,
            "is_skeptical": is_skeptical,
        })

    # Get proper nouns with Wikidata links and coordinates
    has_wikidata = table_exists(conn, "wikidata_links") and table_exists(conn, "wikidata_entities")

    if has_wikidata:
        cursor.execute("""
            SELECT pn.passage_id, pn.reference_form, pn.english_transcription,
                   pn.entity_type, w.wikidata_qid, e.latitude, e.longitude,
                   e.pleiades_id
            FROM proper_nouns pn
            LEFT JOIN wikidata_links w
                ON pn.reference_form = w.reference_form
                AND pn.entity_type = w.entity_type
            LEFT JOIN wikidata_entities e
                ON w.wikidata_qid = e.wikidata_qid
            ORDER BY pn.passage_id, pn.entity_type, pn.reference_form
        """)
    else:
        cursor.execute("""
            SELECT passage_id, reference_form, english_transcription,
                   entity_type, NULL, NULL, NULL, NULL
            FROM proper_nouns
            ORDER BY passage_id, entity_type, reference_form
        """)

    noun_rows = cursor.fetchall()

    # Group nouns by passage_id
    nouns_by_passage = {}
    # Also build cross-reference index: reference_form -> list of passage_ids
    noun_passages = {}

    for passage_id, ref_form, english, entity_type, qid, lat, lon, pleiades_id in noun_rows:
        if passage_id not in nouns_by_passage:
            nouns_by_passage[passage_id] = []

        noun_entry = {
            "reference_form": ref_form,
            "english": english,
            "entity_type": entity_type,
            "qid": qid,
            "lat": lat,
            "lon": lon,
            "pleiades_id": pleiades_id,
        }

        # Avoid duplicates within a passage
        if not any(n["reference_form"] == ref_form and n["entity_type"] == entity_type
                   for n in nouns_by_passage[passage_id]):
            nouns_by_passage[passage_id].append(noun_entry)

        # Build cross-reference
        key = (ref_form, entity_type)
        if key not in noun_passages:
            noun_passages[key] = set()
        noun_passages[key].add(passage_id)

    # Convert cross-reference sets to sorted lists
    noun_passages = {k: sorted(v, key=passage_id_sort_key)
                     for k, v in noun_passages.items()}

    return passages, nouns_by_passage, noun_passages


def get_llm_grammar_page_data(conn, model=DEFAULT_LLM_GRAMMAR_MODEL):
    """Get latest stored LLM grammar parses, grouped by passage for website pages."""
    required_tables = [
        "sentence_llm_grammar_analyses",
        "sentence_llm_grammar_tokens",
    ]
    if not all(table_exists(conn, table_name) for table_name in required_tables):
        return {
            "model": model,
            "passages": [],
            "passage_ids": set(),
            "sentence_count": 0,
            "token_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "prompt_versions": [],
            "created_at_min": None,
            "created_at_max": None,
        }

    with conn.cursor() as cursor:
        cursor.execute(
            """
            WITH selected AS (
                SELECT DISTINCT ON (passage_id, sentence_number)
                    passage_id,
                    sentence_number,
                    model,
                    prompt_version,
                    run_id,
                    greek_sentence,
                    sentence_note,
                    input_tokens,
                    output_tokens,
                    token_count,
                    created_at
                FROM sentence_llm_grammar_analyses
                WHERE model = %s
                ORDER BY
                    passage_id,
                    sentence_number,
                    created_at::timestamptz DESC NULLS LAST,
                    prompt_version DESC
            )
            SELECT
                s.passage_id,
                s.sentence_number,
                s.model,
                s.prompt_version,
                s.run_id,
                s.greek_sentence,
                s.sentence_note,
                s.input_tokens,
                s.output_tokens,
                s.token_count,
                s.created_at,
                t.token_order,
                t.token_id,
                t.form,
                t.lemma,
                t.upos,
                t.xpos,
                t.feats_raw,
                t.head_token_id,
                t.deprel,
                t.confidence,
                t.note
            FROM selected s
            LEFT JOIN sentence_llm_grammar_tokens t
              ON t.passage_id = s.passage_id
             AND t.sentence_number = s.sentence_number
             AND t.model = s.model
             AND t.prompt_version = s.prompt_version
            ORDER BY
                string_to_array(s.passage_id, '.')::int[],
                s.sentence_number,
                t.token_order
            """,
            (model,),
        )
        rows = cursor.fetchall()
        columns = [column.name if hasattr(column, "name") else column[0] for column in cursor.description]

    sentence_lookup = {}
    passage_lookup = {}
    prompt_versions = set()
    created_at_values = []
    for raw_row in rows:
        row = dict(zip(columns, raw_row))
        passage_id = row["passage_id"]
        sentence_key = (passage_id, int(row["sentence_number"]))
        prompt_versions.add(row["prompt_version"])
        if row["created_at"]:
            created_at_values.append(str(row["created_at"]))

        sentence = sentence_lookup.get(sentence_key)
        if sentence is None:
            sentence = {
                "passage_id": passage_id,
                "sentence_number": int(row["sentence_number"]),
                "model": row["model"],
                "prompt_version": row["prompt_version"],
                "run_id": row["run_id"],
                "greek_sentence": row["greek_sentence"],
                "sentence_note": row["sentence_note"] or "",
                "input_tokens": int(row["input_tokens"] or 0),
                "output_tokens": int(row["output_tokens"] or 0),
                "token_count": int(row["token_count"] or 0),
                "created_at": str(row["created_at"] or ""),
                "tokens": [],
            }
            sentence_lookup[sentence_key] = sentence

            passage = passage_lookup.get(passage_id)
            if passage is None:
                book, chapter, section = passage_id.split(".")
                passage = {
                    "passage_id": passage_id,
                    "book": int(book),
                    "chapter": int(chapter),
                    "section": int(section),
                    "sentences": [],
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "token_count": 0,
                }
                passage_lookup[passage_id] = passage
            passage["sentences"].append(sentence)
            passage["input_tokens"] += sentence["input_tokens"]
            passage["output_tokens"] += sentence["output_tokens"]
            passage["token_count"] += sentence["token_count"]

        if row["token_order"] is not None:
            sentence["tokens"].append(
                {
                    "token_order": int(row["token_order"]),
                    "token_id": row["token_id"],
                    "form": row["form"],
                    "lemma": row["lemma"],
                    "upos": row["upos"],
                    "xpos": row["xpos"],
                    "feats_raw": row["feats_raw"],
                    "feats": None,
                    "head_token_id": row["head_token_id"],
                    "deprel": row["deprel"],
                    "confidence": row["confidence"],
                    "note": row["note"],
                }
            )

    passages = sorted(
        passage_lookup.values(),
        key=lambda passage: (passage["book"], passage["chapter"], passage["section"]),
    )
    sentence_count = len(sentence_lookup)
    return {
        "model": model,
        "passages": passages,
        "passage_ids": set(passage_lookup),
        "sentence_count": sentence_count,
        "token_count": sum(len(sentence["tokens"]) for sentence in sentence_lookup.values()),
        "input_tokens": sum(sentence["input_tokens"] for sentence in sentence_lookup.values()),
        "output_tokens": sum(sentence["output_tokens"] for sentence in sentence_lookup.values()),
        "prompt_versions": sorted(prompt_versions),
        "created_at_min": min(created_at_values) if created_at_values else None,
        "created_at_max": max(created_at_values) if created_at_values else None,
    }


STYLOMETRY_FEATURE_SETS = [
    {
        "id": "morphosyntax",
        "label": "Morphosyntactic Grammar",
        "description": "UPOS tags, dependency labels, morphological features, and head-dependent POS relations from the LLM grammar parser.",
        "max_features": 180,
    },
    {
        "id": "word_mfw",
        "label": "Traditional Word MFW",
        "description": "Most frequent Greek surface forms after casefolding.",
        "max_features": 120,
    },
    {
        "id": "char4gram",
        "label": "Traditional Character 4-Grams",
        "description": "Most frequent normalized Greek character 4-grams, a language-agnostic stylometry baseline.",
        "max_features": 160,
    },
]

STYLOMETRY_COMPARISONS = [
    {
        "id": "messenian_wars",
        "label": "Messenian Wars vs. Other Parsed Passages",
        "flag": "is_messenian_wars",
        "positive_label": "Messenian Wars",
        "negative_label": "Other parsed passages",
        "description": "Passages from 4.4.1 through 4.27.1, the Book 4 Messenian Wars block discussed as a possible special target.",
    },
    {
        "id": "book4",
        "label": "Book 4 vs. Other Parsed Passages",
        "flag": "is_book4",
        "positive_label": "Book 4",
        "negative_label": "Other parsed passages",
        "description": "Whole-book check for whether Book 4 separates before narrowing to the Messenian Wars section.",
    },
    {
        "id": "book8",
        "label": "Book 8 vs. Other Parsed Passages",
        "flag": "is_book8",
        "positive_label": "Book 8",
        "negative_label": "Other parsed passages",
        "description": "Arcadian material in Book 8 against the rest of the parsed corpus.",
    },
]


def _passage_tuple(passage_id):
    try:
        return tuple(int(part) for part in str(passage_id).split("."))
    except (TypeError, ValueError):
        return ()


def _is_messenian_wars_passage(passage_id):
    parts = _passage_tuple(passage_id)
    return len(parts) == 3 and (4, 4, 1) <= parts <= (4, 27, 1)


def _stylometry_normalize_token(text):
    text = unicodedata.normalize("NFC", str(text or "").casefold()).strip()
    return text


def _stylometry_word_forms(tokens):
    forms = []
    for token in tokens:
        upos = str(token.get("upos") or "").upper()
        if upos == "PUNCT":
            continue
        form = _stylometry_normalize_token(token.get("form"))
        if form and WORD_PATTERN.search(form):
            forms.append(form)
    return forms


def _stylometry_char_ngrams(forms, n=4):
    text = " ".join(forms)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < n:
        return []
    return [text[index : index + n] for index in range(len(text) - n + 1)]


def _stylometry_token_index(token):
    raw = token.get("token_id") or token.get("token_order")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _iter_stylometry_feats(token):
    raw = token.get("feats")
    if isinstance(raw, dict):
        for key, value in sorted(raw.items()):
            if value in (None, "", "_"):
                continue
            if isinstance(value, (list, tuple, set)):
                for item in sorted(value):
                    if item not in (None, "", "_"):
                        yield f"{key}={item}"
            else:
                yield f"{key}={value}"
        return

    raw = token.get("feats_raw") or raw
    if raw in (None, "", "_"):
        return
    for piece in str(raw).split("|"):
        piece = piece.strip()
        if piece and piece != "_":
            yield piece


def _build_morphosyntax_counts(sentences):
    counts = Counter()
    for sentence in sentences:
        tokens = sentence.get("tokens") or []
        tokens_by_index = {
            index: token
            for token in tokens
            if (index := _stylometry_token_index(token)) is not None
        }
        non_punct = [
            token
            for token in tokens
            if str(token.get("upos") or "").upper() != "PUNCT"
        ]
        if non_punct:
            length_bin = min(40, (len(non_punct) // 5) * 5)
            counts[f"sentence_len_bin:{length_bin:02d}-{length_bin + 4:02d}"] += 1

        for token in tokens:
            upos = str(token.get("upos") or "").upper()
            deprel = str(token.get("deprel") or "").lower()
            if upos and upos != "PUNCT":
                counts[f"upos:{upos}"] += 1
            if deprel and deprel != "punct":
                counts[f"deprel:{deprel}"] += 1
            if upos and deprel and upos != "PUNCT" and deprel != "punct":
                counts[f"deprel_upos:{deprel}:{upos}"] += 1
            for feat in _iter_stylometry_feats(token):
                counts[f"feat:{feat}"] += 1

            child_index = _stylometry_token_index(token)
            try:
                head_index = int(token.get("head_token_id") or 0)
            except (TypeError, ValueError):
                head_index = 0
            if child_index is None or head_index == 0:
                if upos and upos != "PUNCT":
                    counts[f"root_upos:{upos}"] += 1
                continue
            head = tokens_by_index.get(head_index)
            head_upos = str((head or {}).get("upos") or "").upper()
            if head_upos and upos and upos != "PUNCT" and deprel != "punct":
                direction = "left" if head_index > child_index else "right"
                counts[f"head_child_upos:{head_upos}>{upos}"] += 1
                counts[f"head_direction:{deprel}:{direction}"] += 1
    return counts


def _build_stylometry_unit(passage):
    passage_id = passage.get("passage_id")
    sentences = passage.get("sentences") or []
    tokens = [
        token
        for sentence in sentences
        for token in (sentence.get("tokens") or [])
    ]
    forms = _stylometry_word_forms(tokens)
    greek_text = " ".join(
        str(sentence.get("greek_sentence") or "").strip()
        for sentence in sentences
        if sentence.get("greek_sentence")
    )
    word_counts = Counter(f"word:{form}" for form in forms)
    char_counts = Counter(f"char4:{gram}" for gram in _stylometry_char_ngrams(forms))
    morph_counts = _build_morphosyntax_counts(sentences)

    return {
        "passage_id": passage_id,
        "book": int(passage.get("book") or 0),
        "chapter": int(passage.get("chapter") or 0),
        "section": int(passage.get("section") or 0),
        "sentence_count": len(sentences),
        "token_count": len(forms),
        "raw_token_count": len(tokens),
        "excerpt": greek_text[:180],
        "is_messenian_wars": _is_messenian_wars_passage(passage_id),
        "is_book4": int(passage.get("book") or 0) == 4,
        "is_book8": int(passage.get("book") or 0) == 8,
        "features": {
            "morphosyntax": morph_counts,
            "word_mfw": word_counts,
            "char4gram": char_counts,
        },
    }


def _select_stylometry_features(units, feature_set_id, max_features):
    totals = Counter()
    for unit in units:
        totals.update(unit["features"].get(feature_set_id) or {})
    return [feature for feature, _count in totals.most_common(max_features)]


def _stylometry_feature_vector(unit, feature_set_id, features):
    counts = unit["features"].get(feature_set_id) or Counter()
    denominator = float(sum(counts.values()) or 1)
    return np.asarray([counts.get(feature, 0) / denominator for feature in features], dtype=float)


def _stylometry_distance_matrix(matrix):
    if len(matrix) == 0:
        return np.zeros((0, 0), dtype=float)
    norms = np.linalg.norm(matrix, axis=1)
    safe = matrix.copy()
    nonzero = norms > 0
    safe[nonzero] = safe[nonzero] / norms[nonzero, None]
    similarities = np.clip(safe @ safe.T, -1.0, 1.0)
    distances = 1.0 - similarities
    np.fill_diagonal(distances, 0.0)
    return distances


def _stylometry_svd_projection(matrix, method="SVD fallback", note=""):
    sample_count = len(matrix)
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    try:
        u, singular_values, _vh = np.linalg.svd(centered, full_matrices=False)
        coords = u[:, :2] * singular_values[:2]
        if coords.shape[1] == 0:
            coords = np.column_stack([np.arange(sample_count, dtype=float), np.zeros(sample_count)])
        elif coords.shape[1] == 1:
            coords = np.column_stack([coords[:, 0], np.zeros(sample_count)])
        return coords.tolist(), method, note
    except np.linalg.LinAlgError as exc:
        return (
            [[float(index), 0.0] for index in range(sample_count)],
            "ordinal fallback",
            f"Projection failed, so passages are plotted in text order: {exc}",
        )


def _stylometry_projection(matrix):
    sample_count = len(matrix)
    if sample_count == 0:
        return [], "unavailable", "No parsed passages are available for projection."
    if sample_count == 1:
        return [[0.0, 0.0]], "single-point", "Only one parsed passage is available."
    if sample_count < 4:
        return _stylometry_svd_projection(
            matrix,
            method="SVD fallback",
            note="Fewer than four parsed passages are available, so this build uses the deterministic SVD fallback instead of UMAP.",
        )

    try:
        import umap  # type: ignore

        n_neighbors = max(2, min(15, sample_count - 1))
        reducer = umap.UMAP(
            n_components=2,
            n_neighbors=n_neighbors,
            min_dist=0.1,
            metric="cosine",
            random_state=42,
        )
        coords = reducer.fit_transform(matrix)
        return coords.tolist(), "UMAP", ""
    except Exception as exc:
        return _stylometry_svd_projection(
            matrix,
            method="SVD fallback",
            note=f"UMAP was unavailable for this build: {exc}",
        )


def _stylometry_neighbors(units, distances, limit=5):
    if len(units) <= 1:
        return []
    rows = []
    for index, unit in enumerate(units):
        ordered = [
            (other_index, float(distances[index, other_index]))
            for other_index in range(len(units))
            if other_index != index
        ]
        ordered.sort(key=lambda item: item[1])
        rows.append(
            {
                "passage_id": unit["passage_id"],
                "neighbors": [
                    {
                        "passage_id": units[other_index]["passage_id"],
                        "distance": distance,
                    }
                    for other_index, distance in ordered[:limit]
                ],
            }
        )
    return rows


def _stylometry_outliers(units, distances, limit=12):
    if len(units) <= 1:
        return []
    k = min(5, len(units) - 1)
    rows = []
    for index, unit in enumerate(units):
        nearest = sorted(
            float(distances[index, other_index])
            for other_index in range(len(units))
            if other_index != index
        )[:k]
        rows.append(
            {
                "passage_id": unit["passage_id"],
                "book": unit["book"],
                "chapter": unit["chapter"],
                "section": unit["section"],
                "score": float(np.mean(nearest)) if nearest else 0.0,
                "nearest_distance": float(nearest[0]) if nearest else 0.0,
            }
        )
    rows.sort(key=lambda row: row["score"], reverse=True)
    return rows[:limit]


def _mean_distance(distances, indexes_a, indexes_b=None):
    if indexes_b is None:
        if len(indexes_a) < 2:
            return None
        values = [
            float(distances[left, right])
            for left, right in combinations(indexes_a, 2)
        ]
    else:
        if not indexes_a or not indexes_b:
            return None
        values = [
            float(distances[left, right])
            for left in indexes_a
            for right in indexes_b
            if left != right
        ]
    if not values:
        return None
    return float(np.mean(values))


def _stylometry_group_comparisons(units, distances, matrix, features):
    comparisons = []
    for spec in STYLOMETRY_COMPARISONS:
        positive_indexes = [
            index for index, unit in enumerate(units) if unit.get(spec["flag"])
        ]
        negative_indexes = [
            index for index, unit in enumerate(units) if not unit.get(spec["flag"])
        ]
        result = {
            "id": spec["id"],
            "label": spec["label"],
            "positive_label": spec["positive_label"],
            "negative_label": spec["negative_label"],
            "description": spec["description"],
            "positive_count": len(positive_indexes),
            "negative_count": len(negative_indexes),
            "available": bool(positive_indexes and negative_indexes),
            "message": "",
            "within_positive": None,
            "within_negative": None,
            "between": None,
            "separation": None,
            "top_positive_features": [],
            "top_negative_features": [],
        }
        if not result["available"]:
            result["message"] = "Current parsed coverage does not contain both comparison groups."
            comparisons.append(result)
            continue

        within_positive = _mean_distance(distances, positive_indexes)
        within_negative = _mean_distance(distances, negative_indexes)
        between = _mean_distance(distances, positive_indexes, negative_indexes)
        within_values = [
            value
            for value in (within_positive, within_negative)
            if value is not None
        ]
        result["within_positive"] = within_positive
        result["within_negative"] = within_negative
        result["between"] = between
        if between is not None and within_values:
            result["separation"] = between - float(np.mean(within_values))

        positive_mean = matrix[positive_indexes].mean(axis=0)
        negative_mean = matrix[negative_indexes].mean(axis=0)
        deltas = positive_mean - negative_mean
        feature_deltas = [
            {
                "feature": features[index],
                "delta": float(deltas[index]),
                "positive_mean": float(positive_mean[index]),
                "negative_mean": float(negative_mean[index]),
            }
            for index in range(len(features))
        ]
        result["top_positive_features"] = sorted(
            feature_deltas,
            key=lambda row: row["delta"],
            reverse=True,
        )[:12]
        result["top_negative_features"] = sorted(
            feature_deltas,
            key=lambda row: row["delta"],
        )[:12]
        comparisons.append(result)
    return comparisons


def _stylometry_label(unit):
    labels = []
    if unit["is_messenian_wars"]:
        labels.append("Messenian Wars")
    if unit["is_book4"]:
        labels.append("Book 4")
    if unit["is_book8"]:
        labels.append("Book 8")
    return labels


def get_stylometry_page_data(conn=None, grammar_data=None, model=DEFAULT_LLM_GRAMMAR_MODEL):
    """Build morphosyntactic and traditional stylometry summaries for the website."""
    if grammar_data is None and conn is not None:
        grammar_data = get_llm_grammar_page_data(conn, model)
    grammar_data = grammar_data or {"model": model, "passages": []}

    units = [
        _build_stylometry_unit(passage)
        for passage in grammar_data.get("passages", [])
        if passage.get("sentences")
    ]
    units = [
        unit
        for unit in units
        if any(sum(counter.values()) for counter in unit["features"].values())
    ]
    units.sort(key=lambda unit: (unit["book"], unit["chapter"], unit["section"]))

    book_counts = Counter(unit["book"] for unit in units)
    coverage_notes = []
    if not any(unit["is_messenian_wars"] for unit in units):
        coverage_notes.append("No current parsed passages fall inside the Messenian Wars target range 4.4.1-4.27.1.")
    if not any(unit["is_book8"] for unit in units):
        coverage_notes.append("No current parsed passages fall in Book 8.")
    if len(units) < 2:
        coverage_notes.append("At least two parsed passages are needed for distance and projection outputs.")

    prepared_units = [
        {
            "passage_id": unit["passage_id"],
            "book": unit["book"],
            "chapter": unit["chapter"],
            "section": unit["section"],
            "sentence_count": unit["sentence_count"],
            "token_count": unit["token_count"],
            "raw_token_count": unit["raw_token_count"],
            "excerpt": unit["excerpt"],
            "labels": _stylometry_label(unit),
            "is_messenian_wars": unit["is_messenian_wars"],
            "is_book4": unit["is_book4"],
            "is_book8": unit["is_book8"],
        }
        for unit in units
    ]

    feature_sets = []
    for spec in STYLOMETRY_FEATURE_SETS:
        features = _select_stylometry_features(units, spec["id"], spec["max_features"])
        if features:
            matrix = np.vstack([
                _stylometry_feature_vector(unit, spec["id"], features)
                for unit in units
            ])
        else:
            matrix = np.zeros((len(units), 0), dtype=float)
        distances = _stylometry_distance_matrix(matrix)
        coords, projection_method, projection_note = _stylometry_projection(matrix)
        points = []
        for unit, coord in zip(prepared_units, coords):
            points.append(
                {
                    **unit,
                    "x": float(coord[0]) if coord else 0.0,
                    "y": float(coord[1]) if len(coord) > 1 else 0.0,
                }
            )

        feature_sets.append(
            {
                "id": spec["id"],
                "label": spec["label"],
                "description": spec["description"],
                "feature_count": len(features),
                "features": features[:30],
                "projection_method": projection_method,
                "projection_note": projection_note,
                "points": points,
                "nearest_neighbors": _stylometry_neighbors(prepared_units, distances),
                "outliers": _stylometry_outliers(prepared_units, distances),
                "comparisons": _stylometry_group_comparisons(units, distances, matrix, features),
            }
        )

    return {
        "available": bool(units),
        "model": grammar_data.get("model") or model,
        "unit_type": "passage",
        "units": prepared_units,
        "feature_sets": feature_sets,
        "coverage_notes": coverage_notes,
        "metrics": {
            "passage_count": len(units),
            "sentence_count": sum(unit["sentence_count"] for unit in units),
            "token_count": sum(unit["token_count"] for unit in units),
            "book_count": len(book_counts),
            "messenian_wars_count": sum(1 for unit in units if unit["is_messenian_wars"]),
            "book4_count": sum(1 for unit in units if unit["is_book4"]),
            "book8_count": sum(1 for unit in units if unit["is_book8"]),
        },
        "book_counts": dict(sorted(book_counts.items())),
        "method_notes": [
            "This first website implementation uses each parsed passage as one stylometric unit because the current LLM grammar table is still growing.",
            "The production parser target is gpt-5.4-mini; the older UDPipe-style parsers are retained only as historical scripts.",
            "When grammar coverage is dense enough, the same feature families can be aggregated into larger rolling chunks for stronger authorship-style statistics.",
        ],
    }


SENTENCE_STYLOMETRIC_FEATURE_SETS = [
    {
        "id": "morphosyntax",
        "label": "Morphosyntax",
        "description": "UPOS, dependency labels, morphology, sentence-length bins, and head-dependent relations from the LLM grammar parser.",
        "max_features": 240,
    },
    {
        "id": "function_words",
        "label": "Function Words",
        "description": "Surface forms and UPOS/dependency profiles for grammatical tokens: articles, pronouns, prepositions, conjunctions, particles, and auxiliaries.",
        "max_features": 160,
    },
    {
        "id": "char4gram",
        "label": "Character 4-Grams",
        "description": "Traditional character 4-gram stylometric baseline over normalized Greek sentence text.",
        "max_features": 220,
    },
]

SENTENCE_STYLOMETRIC_CLASSIFIER_TASKS = [
    {
        "id": "three_way",
        "label": "3-way classifier",
        "description": "Predict mythic, historical, or other. Ambiguous both/mixed labels are excluded from strict three-way fitting.",
    },
    {
        "id": "mythic_vs_historical",
        "label": "2-way classifier, other dropped",
        "description": "Predict mythic versus historical after dropping other and mixed/both rows.",
        "positive_label": "mythic",
        "negative_label": "historical",
    },
    {
        "id": "historical_vs_all",
        "label": "Historical vs. everything else",
        "description": "Predict whether a sentence is historical. In the two-flag LLM lane, both counts as historical.",
        "positive_label": "historical",
        "negative_label": "not historical",
    },
    {
        "id": "mythic_vs_all",
        "label": "Mythic vs. everything else",
        "description": "Predict whether a sentence is mythic. In the two-flag LLM lane, both counts as mythic.",
        "positive_label": "mythic",
        "negative_label": "not mythic",
    },
]

FUNCTION_WORD_UPOS = {"ADP", "AUX", "CCONJ", "DET", "PART", "PRON", "SCONJ"}


def _sentence_key(passage_id, sentence_number):
    try:
        sentence_number = int(sentence_number)
    except (TypeError, ValueError):
        sentence_number = 0
    return (str(passage_id), sentence_number)


def _build_function_word_counts(tokens):
    counts = Counter()
    for token in tokens:
        upos = str(token.get("upos") or "").upper()
        if upos not in FUNCTION_WORD_UPOS:
            continue
        form = _stylometry_normalize_token(token.get("form"))
        deprel = str(token.get("deprel") or "").lower()
        counts[f"func_upos:{upos}"] += 1
        if form and WORD_PATTERN.search(form):
            counts[f"func:{form}"] += 1
            counts[f"func_form_upos:{form}:{upos}"] += 1
        if deprel and deprel != "punct":
            counts[f"func_deprel:{deprel}"] += 1
    return counts


def _build_sentence_stylometric_unit(passage, sentence):
    passage_id = passage.get("passage_id")
    sentence_number = int(sentence.get("sentence_number") or 0)
    tokens = sentence.get("tokens") or []
    forms = _stylometry_word_forms(tokens)
    greek_text = str(sentence.get("greek_sentence") or sentence.get("sentence") or "").strip()
    morph_counts = _build_morphosyntax_counts([sentence])
    function_counts = _build_function_word_counts(tokens)
    char_counts = Counter(f"char4:{gram}" for gram in _stylometry_char_ngrams(forms))
    passage_parts = _passage_tuple(passage_id)

    return {
        "key": _sentence_key(passage_id, sentence_number),
        "passage_id": passage_id,
        "sentence_number": sentence_number,
        "book": int(passage.get("book") or (passage_parts[0] if passage_parts else 0)),
        "chapter": int(passage.get("chapter") or 0),
        "section": int(passage.get("section") or 0),
        "token_count": len(forms),
        "raw_token_count": len(tokens),
        "sentence": greek_text,
        "excerpt": greek_text[:180],
        "features": {
            "morphosyntax": morph_counts,
            "function_words": function_counts,
            "char4gram": char_counts,
        },
    }


def _build_sentence_stylometric_units(grammar_data):
    units = []
    for passage in grammar_data.get("passages", []):
        for sentence in passage.get("sentences") or []:
            unit = _build_sentence_stylometric_unit(passage, sentence)
            if any(sum(counter.values()) for counter in unit["features"].values()):
                units.append(unit)
    units.sort(key=lambda unit: (unit["book"], unit["chapter"], unit["section"], unit["sentence_number"]))
    return units


def _load_sentence_stylometric_label_sources(conn):
    sources = []

    if conn is not None and table_exists(conn, "sentence_greta_tags"):
        df = read_sql_query(
            """
            SELECT passage_id, sentence_number, prompt_version, model, myth_history_bucket
            FROM sentence_greta_tags
            WHERE prompt_version = %s
            """,
            conn,
            (ORIGINAL_CLASSIFIER_VERSION,),
        )
        records = {}
        for _, row in df.iterrows():
            bucket = row["myth_history_bucket"]
            records[_sentence_key(row["passage_id"], row["sentence_number"])] = {
                "bucket": bucket,
                "mythic": bucket == "mythic",
                "historical": bucket == "historical",
            }
        sources.append(
            {
                "id": "llm_original",
                "label": "LLM original three-way",
                "prompt_version": ORIGINAL_CLASSIFIER_VERSION,
                "model": str(df.iloc[0]["model"] or "") if len(df) else "",
                "note": "Stored in sentence_greta_tags as mythic/historical/other.",
                "records": records,
            }
        )

    if conn is not None and table_exists(conn, "sentence_greta_both_tags"):
        df = read_sql_query(
            """
            SELECT passage_id, sentence_number, prompt_version, model,
                   references_mythic, references_historical, myth_history_bucket
            FROM sentence_greta_both_tags
            WHERE prompt_version = %s
            """,
            conn,
            (GRETA_INSPIRED_CLASSIFIER_VERSION,),
        )
        records = {}
        for _, row in df.iterrows():
            bucket = row["myth_history_bucket"]
            records[_sentence_key(row["passage_id"], row["sentence_number"])] = {
                "bucket": bucket,
                "mythic": bool(row["references_mythic"]),
                "historical": bool(row["references_historical"]),
            }
        sources.append(
            {
                "id": "llm_greta_inspired",
                "label": "LLM Greta-inspired flags",
                "prompt_version": GRETA_INSPIRED_CLASSIFIER_VERSION,
                "model": str(df.iloc[0]["model"] or "") if len(df) else "",
                "note": "Stored as independent mythic/historical flags; strict three-way rows drop the rare both label.",
                "records": records,
            }
        )

    if conn is not None and table_exists(conn, "sentence_manual_tags"):
        df = read_sql_query(
            """
            SELECT source_id, passage_id, sentence_number, manual_bucket,
                   yellow_mythic, blue_historical, green_both
            FROM sentence_manual_tags
            WHERE source_id = %s
            """,
            conn,
            (MANUAL_SENTENCE_SOURCE_ID,),
        )
        records = {}
        for _, row in df.iterrows():
            bucket = row["manual_bucket"]
            is_mixed = bucket == "mixed_mythic_historical"
            records[_sentence_key(row["passage_id"], row["sentence_number"])] = {
                "bucket": "both" if is_mixed else bucket,
                "mythic": bool(row["yellow_mythic"]) or bool(row["green_both"]) or bucket == "mythic" or is_mixed,
                "historical": bool(row["blue_historical"]) or bool(row["green_both"]) or bucket == "historical" or is_mixed,
            }
        sources.append(
            {
                "id": "manual_book3",
                "label": "Book 3 manual Greta/Rosie",
                "prompt_version": MANUAL_SENTENCE_SOURCE_ID,
                "model": "manual",
                "note": "Book 3 hand labels; strict three-way rows drop mixed mythic/historical labels.",
                "records": records,
            }
        )

    return sources


def _source_metadata(label_sources):
    metadata = []
    for source in label_sources:
        buckets = Counter(record["bucket"] for record in source.get("records", {}).values())
        metadata.append(
            {
                "id": source.get("id"),
                "label": source.get("label"),
                "prompt_version": source.get("prompt_version"),
                "model": source.get("model"),
                "note": source.get("note", ""),
                "label_count": int(sum(buckets.values())),
                "bucket_counts": dict(sorted(buckets.items())),
            }
        )
    return metadata


def _select_sentence_stylometric_features(units, feature_set_id, max_features, min_count=2):
    totals = Counter()
    for unit in units:
        totals.update(unit["features"].get(feature_set_id) or {})
    features = [
        feature
        for feature, count in totals.most_common()
        if count >= min_count
    ][:max_features]
    if not features and totals:
        features = [feature for feature, _count in totals.most_common(max_features)]
    return features


def _sentence_stylometric_matrix(units, feature_set_id, features):
    if not units or not features:
        return np.zeros((len(units), 0), dtype=float)
    rows = []
    for unit in units:
        counts = unit["features"].get(feature_set_id) or Counter()
        denominator = float(sum(counts.values()) or 1)
        rows.append([counts.get(feature, 0) / denominator for feature in features])
    return np.asarray(rows, dtype=float)


def _classifier_labels_for_task(units, source, task):
    rows = []
    task_id = task["id"]
    for unit in units:
        record = source.get("records", {}).get(unit["key"])
        if not record:
            continue
        bucket = record.get("bucket")
        label = None
        if task_id == "three_way":
            if bucket in {"mythic", "historical", "other"}:
                label = bucket
        elif task_id == "mythic_vs_historical":
            if bucket == "mythic":
                label = 1
            elif bucket == "historical":
                label = 0
        elif task_id == "historical_vs_all":
            label = 1 if record.get("historical") else 0
        elif task_id == "mythic_vs_all":
            label = 1 if record.get("mythic") else 0

        if label is None:
            continue
        rows.append((unit, label))
    return rows


def _label_count_dict(labels, task):
    counts = Counter(labels)
    if task["id"] == "three_way":
        order = ["historical", "mythic", "other"]
        return {label: int(counts.get(label, 0)) for label in order if counts.get(label, 0)}
    if task["id"] == "mythic_vs_historical":
        return {
            task["negative_label"]: int(counts.get(0, 0)),
            task["positive_label"]: int(counts.get(1, 0)),
        }
    return {
        task["negative_label"]: int(counts.get(0, 0)),
        task["positive_label"]: int(counts.get(1, 0)),
    }


def _classification_feature_rows(model, feature_names, task, limit=10):
    logreg = model.named_steps["logreg"]
    classes = list(logreg.classes_)
    coefficients = logreg.coef_
    rows = []

    if len(classes) == 2 and task["id"] != "three_way":
        coefs = coefficients[0]
        for index in np.argsort(coefs)[-limit:][::-1]:
            rows.append(
                {
                    "class_label": task["positive_label"],
                    "direction": "positive",
                    "feature": feature_names[index],
                    "coefficient": float(coefs[index]),
                }
            )
        for index in np.argsort(coefs)[:limit]:
            rows.append(
                {
                    "class_label": task["negative_label"],
                    "direction": "negative",
                    "feature": feature_names[index],
                    "coefficient": float(coefs[index]),
                }
            )
        return rows

    for class_index, class_label in enumerate(classes):
        coefs = coefficients[class_index]
        for index in np.argsort(coefs)[-limit:][::-1]:
            rows.append(
                {
                    "class_label": str(class_label),
                    "direction": "positive",
                    "feature": feature_names[index],
                    "coefficient": float(coefs[index]),
                }
            )
    return rows


def _fit_sentence_stylometric_classifier(source, task, feature_spec, units):
    labeled_rows = _classifier_labels_for_task(units, source, task)
    labeled_units = [row[0] for row in labeled_rows]
    labels = [row[1] for row in labeled_rows]
    label_counts = _label_count_dict(labels, task)
    feature_names = _select_sentence_stylometric_features(
        labeled_units,
        feature_spec["id"],
        feature_spec["max_features"],
    )
    result = {
        "id": f"{source['id']}:{task['id']}:{feature_spec['id']}",
        "source_id": source["id"],
        "source_label": source["label"],
        "task_id": task["id"],
        "task_label": task["label"],
        "task_description": task["description"],
        "feature_set_id": feature_spec["id"],
        "feature_set_label": feature_spec["label"],
        "sample_count": int(len(labeled_units)),
        "label_counts": label_counts,
        "feature_count": int(len(feature_names)),
        "available": False,
        "message": "",
        "metrics": {},
        "top_features": [],
    }
    if len(labeled_units) < 10:
        result["message"] = "Not enough grammar-parsed labeled sentences."
        return result
    if len(set(labels)) < 2:
        result["message"] = "Only one label is present in the parsed subset."
        return result
    min_class_count = min(Counter(labels).values())
    if min_class_count < 2:
        result["message"] = "At least two examples per class are needed for cross-validation."
        return result
    if not feature_names:
        result["message"] = "No repeated stylometric features survived feature selection."
        return result

    x = _sentence_stylometric_matrix(labeled_units, feature_spec["id"], feature_names)
    y = np.asarray(labels)
    n_splits = min(5, min_class_count)
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    y_true = []
    y_pred = []
    y_baseline = []
    for train_index, test_index in cv.split(x, y):
        train_y = y[train_index]
        majority = Counter(train_y).most_common(1)[0][0]
        model = Pipeline([
            ("scaler", StandardScaler()),
            ("logreg", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
        ])
        model.fit(x[train_index], train_y)
        fold_pred = model.predict(x[test_index])
        y_true.extend(y[test_index].tolist())
        y_pred.extend(fold_pred.tolist())
        y_baseline.extend([majority] * len(test_index))

    final_model = Pipeline([
        ("scaler", StandardScaler()),
        ("logreg", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
    ])
    final_model.fit(x, y)

    result.update(
        {
            "available": True,
            "metrics": {
                "cv_folds": int(n_splits),
                "accuracy": float(accuracy_score(y_true, y_pred)),
                "baseline_accuracy": float(accuracy_score(y_true, y_baseline)),
                "accuracy_delta_vs_baseline": float(accuracy_score(y_true, y_pred) - accuracy_score(y_true, y_baseline)),
                "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
                "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
            },
            "top_features": _classification_feature_rows(final_model, feature_names, task),
        }
    )
    return result


def _fit_sentence_book_regressor(feature_spec, units, *, include_books_4_8):
    selected_units = [
        unit for unit in units
        if include_books_4_8 or unit["book"] not in {4, 8}
    ]
    feature_names = _select_sentence_stylometric_features(
        selected_units,
        feature_spec["id"],
        feature_spec["max_features"],
    )
    book_counts = Counter(unit["book"] for unit in selected_units)
    variant_label = "Including Books 4 and 8" if include_books_4_8 else "Excluding Books 4 and 8"
    result = {
        "id": f"{'all_books' if include_books_4_8 else 'excluding_4_8'}:{feature_spec['id']}",
        "variant_id": "all_books" if include_books_4_8 else "excluding_4_8",
        "variant_label": variant_label,
        "include_books_4_8": bool(include_books_4_8),
        "feature_set_id": feature_spec["id"],
        "feature_set_label": feature_spec["label"],
        "sample_count": int(len(selected_units)),
        "book_counts": {str(book): int(count) for book, count in sorted(book_counts.items())},
        "book_count": int(len(book_counts)),
        "feature_count": int(len(feature_names)),
        "available": False,
        "message": "",
        "metrics": {},
        "top_features": [],
    }
    if len(selected_units) < 10 or len(book_counts) < 2:
        result["message"] = "Not enough grammar-parsed sentences across books."
        return result
    if not feature_names:
        result["message"] = "No repeated stylometric features survived feature selection."
        return result

    x = _sentence_stylometric_matrix(selected_units, feature_spec["id"], feature_names)
    y = np.asarray([unit["book"] for unit in selected_units], dtype=float)
    n_splits = min(5, len(selected_units))
    cv = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    y_true = []
    y_pred = []
    y_baseline = []
    for train_index, test_index in cv.split(x):
        train_y = y[train_index]
        baseline_value = float(np.mean(train_y))
        model = Pipeline([
            ("scaler", StandardScaler()),
            ("ridge", RidgeCV(alphas=np.logspace(-2, 4, 13))),
        ])
        model.fit(x[train_index], train_y)
        fold_pred = model.predict(x[test_index])
        y_true.extend(y[test_index].tolist())
        y_pred.extend(fold_pred.tolist())
        y_baseline.extend([baseline_value] * len(test_index))

    final_model = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge", RidgeCV(alphas=np.logspace(-2, 4, 13))),
    ])
    final_model.fit(x, y)
    coefs = final_model.named_steps["ridge"].coef_
    feature_rows = []
    for index in np.argsort(np.abs(coefs))[-16:][::-1]:
        feature_rows.append(
            {
                "direction": "later_books" if coefs[index] > 0 else "earlier_books",
                "feature": feature_names[index],
                "coefficient": float(coefs[index]),
            }
        )

    rmse = math.sqrt(mean_squared_error(y_true, y_pred))
    baseline_rmse = math.sqrt(mean_squared_error(y_true, y_baseline))
    mae = mean_absolute_error(y_true, y_pred)
    baseline_mae = mean_absolute_error(y_true, y_baseline)
    result.update(
        {
            "available": True,
            "metrics": {
                "cv_folds": int(n_splits),
                "selected_alpha": float(final_model.named_steps["ridge"].alpha_),
                "r2": float(r2_score(y_true, y_pred)),
                "mae": float(mae),
                "baseline_mae": float(baseline_mae),
                "mae_improvement_vs_baseline": float(baseline_mae - mae),
                "rmse": float(rmse),
                "baseline_rmse": float(baseline_rmse),
                "rmse_improvement_vs_baseline": float(baseline_rmse - rmse),
            },
            "top_features": feature_rows,
        }
    )
    return result


def get_stylometric_sentence_model_data(
    conn=None,
    grammar_data=None,
    label_sources=None,
    model=DEFAULT_LLM_GRAMMAR_MODEL,
):
    """Build sentence-level stylometric classifiers and book-number regressors."""
    if grammar_data is None and conn is not None:
        grammar_data = get_llm_grammar_page_data(conn, model)
    grammar_data = grammar_data or {"model": model, "passages": []}
    units = _build_sentence_stylometric_units(grammar_data)
    label_sources = label_sources if label_sources is not None else _load_sentence_stylometric_label_sources(conn)
    units_by_book = Counter(unit["book"] for unit in units)

    classifiers = []
    for source in label_sources:
        for task in SENTENCE_STYLOMETRIC_CLASSIFIER_TASKS:
            for feature_spec in SENTENCE_STYLOMETRIC_FEATURE_SETS:
                classifiers.append(
                    _fit_sentence_stylometric_classifier(source, task, feature_spec, units)
                )

    regressions = []
    for include_books in [True, False]:
        for feature_spec in SENTENCE_STYLOMETRIC_FEATURE_SETS:
            regressions.append(
                _fit_sentence_book_regressor(
                    feature_spec,
                    units,
                    include_books_4_8=include_books,
                )
            )

    coverage_notes = [
        "These models use only sentences with current LLM grammar-token rows, so the sample is smaller than the full annotation corpus.",
        "Strict three-way and mythic-vs-historical tasks drop rare both/mixed rows; one-vs-rest tasks use the available mythic/historical flags where present.",
        "Character 4-grams are included as a traditional baseline; morphosyntax is the primary non-lexical stylometric family.",
    ]
    if not units:
        coverage_notes.append("No grammar-parsed sentences are available.")

    return {
        "available": bool(units),
        "model": grammar_data.get("model") or model,
        "unit_type": "sentence",
        "feature_sets": [
            {
                "id": spec["id"],
                "label": spec["label"],
                "description": spec["description"],
                "max_features": spec["max_features"],
            }
            for spec in SENTENCE_STYLOMETRIC_FEATURE_SETS
        ],
        "label_sources": _source_metadata(label_sources),
        "classifiers": classifiers,
        "regressions": regressions,
        "coverage_notes": coverage_notes,
        "metrics": {
            "parsed_sentence_count": int(len(units)),
            "token_count": int(sum(unit["token_count"] for unit in units)),
            "book_count": int(len(units_by_book)),
        },
        "book_counts": {str(book): int(count) for book, count in sorted(units_by_book.items())},
    }


BOOK_FEATURE_TREND_LIMIT = 8


def _stylometry_feature_display_label(feature):
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


def _weighted_regression(x_values, y_values, weights):
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    w = np.asarray(weights, dtype=float)
    finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(w) & (w > 0)
    x = x[finite]
    y = y[finite]
    w = w[finite]
    if len(x) < 3 or len(np.unique(x)) < 2:
        return {
            "available": False,
            "n": int(len(x)),
            "slope": None,
            "intercept": None,
            "r_squared": None,
            "p_value": None,
            "stderr": None,
        }

    design = np.column_stack([np.ones(len(x)), x])
    weighted_design = design * w[:, None]
    xtwx = design.T @ weighted_design
    try:
        beta = np.linalg.solve(xtwx, design.T @ (w * y))
    except np.linalg.LinAlgError:
        return {
            "available": False,
            "n": int(len(x)),
            "slope": None,
            "intercept": None,
            "r_squared": None,
            "p_value": None,
            "stderr": None,
        }
    yhat = design @ beta
    residual = y - yhat
    weighted_mean = float(np.average(y, weights=w))
    sse = float(np.sum(w * residual ** 2))
    sst = float(np.sum(w * (y - weighted_mean) ** 2))
    dof = len(x) - 2
    sigma2 = sse / dof if dof > 0 else math.nan
    try:
        covariance = sigma2 * np.linalg.inv(xtwx)
        stderr = float(math.sqrt(covariance[1, 1]))
    except (ValueError, np.linalg.LinAlgError):
        stderr = math.nan
    slope = float(beta[1])
    if stderr and np.isfinite(stderr) and stderr > 0 and dof > 0:
        t_stat = slope / stderr
        p_value = float(2.0 * stats.t.sf(abs(t_stat), dof))
    else:
        p_value = math.nan
    return {
        "available": True,
        "n": int(len(x)),
        "slope": slope,
        "intercept": float(beta[0]),
        "r_squared": float(1.0 - (sse / sst)) if sst > 0 else 0.0,
        "p_value": p_value,
        "stderr": stderr,
    }


def _plain_regression(x_values, y_values):
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    finite = np.isfinite(x) & np.isfinite(y)
    x = x[finite]
    y = y[finite]
    if len(x) < 3 or len(np.unique(x)) < 2:
        return {
            "available": False,
            "n": int(len(x)),
            "slope": None,
            "intercept": None,
            "r_squared": None,
            "p_value": None,
            "stderr": None,
        }
    result = stats.linregress(x, y)
    return {
        "available": True,
        "n": int(len(x)),
        "slope": float(result.slope),
        "intercept": float(result.intercept),
        "r_squared": float(result.rvalue ** 2),
        "p_value": float(result.pvalue),
        "stderr": float(result.stderr) if result.stderr is not None else None,
    }


def _book_feature_trend_rows(units, selected_features):
    by_book = defaultdict(list)
    for unit in units:
        by_book[unit["book"]].append(unit)

    trend_features = []
    for feature in selected_features:
        per_book = []
        for book, book_units in sorted(by_book.items()):
            hit_count = sum(
                1
                for unit in book_units
                if (unit["features"].get("morphosyntax") or {}).get(feature["feature"], 0) > 0
            )
            sentence_count = len(book_units)
            proportion = hit_count / sentence_count if sentence_count else 0.0
            per_book.append(
                {
                    "book": int(book),
                    "sentence_count": int(sentence_count),
                    "hit_count": int(hit_count),
                    "proportion": float(proportion),
                    "is_book4": int(book) == 4,
                    "is_book8": int(book) == 8,
                }
            )

        all_fit = _weighted_regression(
            [row["book"] for row in per_book],
            [row["proportion"] for row in per_book],
            [row["sentence_count"] for row in per_book],
        )
        excluding_rows = [row for row in per_book if row["book"] not in {4, 8}]
        excluding_fit = _weighted_regression(
            [row["book"] for row in excluding_rows],
            [row["proportion"] for row in excluding_rows],
            [row["sentence_count"] for row in excluding_rows],
        )
        trend_features.append(
            {
                **feature,
                "points": per_book,
                "regressions": {
                    "all_books": all_fit,
                    "excluding_4_8": excluding_fit,
                },
            }
        )
    return trend_features


def _kde_points(values, grid):
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or float(np.std(values)) == 0.0:
        return [0.0 for _ in grid]
    try:
        kde = stats.gaussian_kde(values)
        densities = kde(np.asarray(grid, dtype=float))
    except Exception:
        return [0.0 for _ in grid]
    return [float(value) for value in densities]


def _sentence_length_distribution_data(units):
    by_book = defaultdict(list)
    for unit in units:
        by_book[unit["book"]].append(int(unit["token_count"]))

    all_lengths = [length for lengths in by_book.values() for length in lengths]
    if all_lengths:
        grid = np.linspace(max(0, min(all_lengths) - 2), max(all_lengths) + 2, 140)
    else:
        grid = np.linspace(0, 1, 20)

    books = []
    for book, lengths in sorted(by_book.items()):
        values = np.asarray(lengths, dtype=float)
        if len(values):
            q1, median, q3 = np.percentile(values, [25, 50, 75])
            mean = float(np.mean(values))
            std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            minimum = int(np.min(values))
            maximum = int(np.max(values))
        else:
            q1 = median = q3 = mean = std = 0.0
            minimum = maximum = 0
        books.append(
            {
                "book": int(book),
                "lengths": [int(value) for value in lengths],
                "count": int(len(lengths)),
                "mean": mean,
                "median": float(median),
                "q1": float(q1),
                "q3": float(q3),
                "std": std,
                "min": minimum,
                "max": maximum,
                "is_book4": int(book) == 4,
                "is_book8": int(book) == 8,
                "kde": [
                    {"x": float(x), "density": density}
                    for x, density in zip(grid, _kde_points(values, grid))
                ],
            }
        )

    grouped_lengths = [book["lengths"] for book in books if len(book["lengths"]) > 1]
    tests = []
    if len(grouped_lengths) >= 2:
        has_variation = len({length for group in grouped_lengths for length in group}) > 1
        has_within_group_variation = any(float(np.std(group)) > 0.0 for group in grouped_lengths)
        try:
            if has_variation and has_within_group_variation:
                anova = stats.f_oneway(*grouped_lengths)
                tests.append(
                    {
                        "test": "One-way ANOVA",
                        "statistic": float(anova.statistic),
                        "p_value": float(anova.pvalue),
                        "interpretation": "Tests equality of mean sentence length across books.",
                    }
                )
        except Exception:
            pass
        try:
            if has_variation:
                kruskal = stats.kruskal(*grouped_lengths)
                tests.append(
                    {
                        "test": "Kruskal-Wallis",
                        "statistic": float(kruskal.statistic),
                        "p_value": float(kruskal.pvalue),
                        "interpretation": "Non-parametric test for distribution/median differences across books.",
                    }
                )
        except Exception:
            pass
        try:
            if has_variation and has_within_group_variation:
                levene = stats.levene(*grouped_lengths)
                tests.append(
                    {
                        "test": "Levene",
                        "statistic": float(levene.statistic),
                        "p_value": float(levene.pvalue),
                        "interpretation": "Tests equality of sentence-length variance across books.",
                    }
                )
        except Exception:
            pass

    sentence_books = []
    sentence_lengths = []
    for book in books:
        for length in book["lengths"]:
            sentence_books.append(book["book"])
            sentence_lengths.append(length)
    all_regression = _plain_regression(sentence_books, sentence_lengths)
    excluding_pairs = [
        (book, length)
        for book, length in zip(sentence_books, sentence_lengths)
        if book not in {4, 8}
    ]
    excluding_regression = _plain_regression(
        [book for book, _length in excluding_pairs],
        [length for _book, length in excluding_pairs],
    )

    return {
        "books": books,
        "grid": [float(x) for x in grid],
        "tests": tests,
        "regressions": {
            "all_books": all_regression,
            "excluding_4_8": excluding_regression,
        },
    }


def get_stylometric_book_feature_trend_data(
    conn=None,
    grammar_data=None,
    model_data=None,
    model=DEFAULT_LLM_GRAMMAR_MODEL,
):
    """Build book-by-book trend plots for morphosyntax regression features."""
    if grammar_data is None and conn is not None:
        grammar_data = get_llm_grammar_page_data(conn, model)
    grammar_data = grammar_data or {"model": model, "passages": []}
    if model_data is None:
        model_data = get_stylometric_sentence_model_data(
            conn,
            grammar_data=grammar_data,
            model=model,
        )

    units = _build_sentence_stylometric_units(grammar_data)
    target_regression = next(
        (
            regression
            for regression in (model_data or {}).get("regressions", [])
            if regression.get("variant_id") == "excluding_4_8"
            and regression.get("feature_set_id") == "morphosyntax"
            and regression.get("available")
        ),
        None,
    )
    selected_features = []
    if target_regression:
        for row in (target_regression.get("top_features") or [])[:BOOK_FEATURE_TREND_LIMIT]:
            selected_features.append(
                {
                    "feature": row.get("feature"),
                    "feature_label": _stylometry_feature_display_label(row.get("feature")),
                    "coefficient": float(row.get("coefficient") or 0.0),
                    "direction": row.get("direction"),
                }
            )

    by_book = Counter(unit["book"] for unit in units)
    return {
        "available": bool(units),
        "model": grammar_data.get("model") or model,
        "unit_type": "sentence",
        "source_regression": {
            "variant_id": "excluding_4_8",
            "feature_set_id": "morphosyntax",
            "sample_count": target_regression.get("sample_count") if target_regression else 0,
            "metrics": target_regression.get("metrics") if target_regression else {},
        },
        "feature_trends": _book_feature_trend_rows(units, selected_features),
        "length_distribution": _sentence_length_distribution_data(units),
        "book_counts": {str(book): int(count) for book, count in sorted(by_book.items())},
        "metrics": {
            "parsed_sentence_count": int(len(units)),
            "book_count": int(len(by_book)),
            "feature_count": int(len(selected_features)),
        },
        "notes": [
            "Feature proportions are sentence-level rates: a sentence counts once if the selected morphosyntax feature appears at least once.",
            "Regression lines are weighted by parsed sentence count per book; the dashed line refits after excluding Books 4 and 8.",
            "Sentence-length tests use individual parsed sentences and should be read as diagnostics over current grammar coverage.",
        ],
    }


def _load_discourse_mode_records(conn, prompt_version=DISCOURSE_MODE_PROMPT_VERSION):
    if conn is None or not table_exists(conn, "sentence_discourse_mode_tags"):
        return {}
    df = read_sql_query(
        """
        SELECT passage_id, sentence_number, prompt_version, model, discourse_mode,
               confidence, rationale
        FROM sentence_discourse_mode_tags
        WHERE prompt_version = %s
        """,
        conn,
        (prompt_version,),
    )
    records = {}
    for _, row in df.iterrows():
        mode = row["discourse_mode"]
        if mode not in DISCOURSE_MODES:
            continue
        records[_sentence_key(row["passage_id"], row["sentence_number"])] = {
            "mode": mode,
            "confidence": row["confidence"],
            "rationale": row["rationale"],
            "model": row["model"],
            "prompt_version": row["prompt_version"],
        }
    return records


def _linear_probability_book_fit(rows, *, include_modes, exclude_books=()):
    selected = [row for row in rows if row["book"] not in set(exclude_books)]
    if len(selected) < 4 or len({row["book"] for row in selected}) < 2:
        return {
            "available": False,
            "n": int(len(selected)),
            "slope": None,
            "intercept": None,
            "r_squared": None,
            "p_value": None,
            "stderr": None,
            "mode_count": int(len({row["mode"] for row in selected})),
            "book_count": int(len({row["book"] for row in selected})),
        }

    modes = sorted({row["mode"] for row in selected})
    mode_columns = modes[1:] if include_modes else []
    design = []
    y = []
    for row in selected:
        design.append(
            [1.0, float(row["book"])]
            + [1.0 if row["mode"] == mode else 0.0 for mode in mode_columns]
        )
        y.append(1.0 if row["has_aorist"] else 0.0)
    x = np.asarray(design, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.shape[0] <= x.shape[1]:
        return {
            "available": False,
            "n": int(len(selected)),
            "slope": None,
            "intercept": None,
            "r_squared": None,
            "p_value": None,
            "stderr": None,
            "mode_count": int(len(modes)),
            "book_count": int(len({row["book"] for row in selected})),
        }

    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ beta
    residual = y - fitted
    sse = float(np.sum(residual ** 2))
    sst = float(np.sum((y - float(np.mean(y))) ** 2))
    dof = int(x.shape[0] - x.shape[1])
    sigma2 = sse / dof if dof > 0 else math.nan
    try:
        covariance = sigma2 * np.linalg.pinv(x.T @ x)
        stderr = float(math.sqrt(covariance[1, 1]))
    except (ValueError, np.linalg.LinAlgError):
        stderr = math.nan
    slope = float(beta[1])
    if stderr and np.isfinite(stderr) and stderr > 0 and dof > 0:
        p_value = float(2.0 * stats.t.sf(abs(slope / stderr), dof))
    else:
        p_value = math.nan
    return {
        "available": True,
        "n": int(len(selected)),
        "slope": slope,
        "intercept": float(beta[0]),
        "r_squared": float(1.0 - sse / sst) if sst > 0 else 0.0,
        "p_value": p_value,
        "stderr": stderr,
        "mode_count": int(len(modes)),
        "book_count": int(len({row["book"] for row in selected})),
        "mode_columns": mode_columns,
    }


def _aorist_book_rows(rows):
    by_book = defaultdict(list)
    for row in rows:
        by_book[row["book"]].append(row)
    output = []
    for book, book_rows in sorted(by_book.items()):
        hit_count = sum(1 for row in book_rows if row["has_aorist"])
        sentence_count = len(book_rows)
        output.append(
            {
                "book": int(book),
                "sentence_count": int(sentence_count),
                "aorist_count": int(hit_count),
                "aorist_rate": float(hit_count / sentence_count) if sentence_count else 0.0,
                "is_book4": int(book) == 4,
                "is_book8": int(book) == 8,
            }
        )
    return output


def _mode_composition_rows(rows):
    by_book = defaultdict(list)
    for row in rows:
        by_book[row["book"]].append(row)
    output = []
    for book, book_rows in sorted(by_book.items()):
        counts = Counter(row["mode"] for row in book_rows)
        total = len(book_rows)
        for mode in DISCOURSE_MODES:
            count = counts.get(mode, 0)
            output.append(
                {
                    "book": int(book),
                    "discourse_mode": mode,
                    "discourse_mode_label": DISCOURSE_MODE_LABELS.get(mode, mode),
                    "sentence_count": int(count),
                    "book_sentence_count": int(total),
                    "proportion": float(count / total) if total else 0.0,
                    "is_book4": int(book) == 4,
                    "is_book8": int(book) == 8,
                }
            )
    return output


def _mode_aorist_trend_rows(rows):
    by_mode = defaultdict(list)
    for row in rows:
        by_mode[row["mode"]].append(row)

    output = []
    for mode in DISCOURSE_MODES:
        mode_rows = by_mode.get(mode, [])
        by_book = defaultdict(list)
        for row in mode_rows:
            by_book[row["book"]].append(row)
        points = []
        for book, book_rows in sorted(by_book.items()):
            hit_count = sum(1 for row in book_rows if row["has_aorist"])
            sentence_count = len(book_rows)
            points.append(
                {
                    "book": int(book),
                    "sentence_count": int(sentence_count),
                    "aorist_count": int(hit_count),
                    "aorist_rate": float(hit_count / sentence_count) if sentence_count else 0.0,
                    "is_book4": int(book) == 4,
                    "is_book8": int(book) == 8,
                }
            )
        excluding_points = [point for point in points if point["book"] not in {4, 8}]
        output.append(
            {
                "discourse_mode": mode,
                "discourse_mode_label": DISCOURSE_MODE_LABELS.get(mode, mode),
                "sentence_count": int(len(mode_rows)),
                "aorist_count": int(sum(1 for row in mode_rows if row["has_aorist"])),
                "book_count": int(len(by_book)),
                "points": points,
                "regressions": {
                    "all_books": _weighted_regression(
                        [point["book"] for point in points],
                        [point["aorist_rate"] for point in points],
                        [point["sentence_count"] for point in points],
                    ),
                    "excluding_4_8": _weighted_regression(
                        [point["book"] for point in excluding_points],
                        [point["aorist_rate"] for point in excluding_points],
                        [point["sentence_count"] for point in excluding_points],
                    ),
                },
            }
        )
    return output


def get_discourse_mode_aorist_analysis(
    conn=None,
    grammar_data=None,
    discourse_records=None,
    model=DEFAULT_LLM_GRAMMAR_MODEL,
    prompt_version=DISCOURSE_MODE_PROMPT_VERSION,
):
    """Control the aorist book trend by sentence-level discourse mode."""
    if grammar_data is None and conn is not None:
        grammar_data = get_llm_grammar_page_data(conn, model)
    grammar_data = grammar_data or {"model": model, "passages": []}
    units = _build_sentence_stylometric_units(grammar_data)
    if discourse_records is None:
        discourse_records = _load_discourse_mode_records(conn, prompt_version)

    rows = []
    for unit in units:
        record = discourse_records.get(unit["key"])
        if not record:
            continue
        mode = record.get("mode")
        if mode not in DISCOURSE_MODES:
            continue
        features = unit["features"].get("morphosyntax") or {}
        rows.append(
            {
                "passage_id": unit["passage_id"],
                "sentence_number": int(unit["sentence_number"]),
                "book": int(unit["book"]),
                "chapter": int(unit["chapter"]),
                "section": int(unit["section"]),
                "discourse_mode": mode,
                "discourse_mode_label": DISCOURSE_MODE_LABELS.get(mode, mode),
                "mode": mode,
                "confidence": record.get("confidence", ""),
                "has_aorist": bool(features.get("feat:Tense=Aor", 0) > 0),
                "token_count": int(unit["token_count"]),
                "excerpt": unit["excerpt"],
            }
        )

    mode_counts = Counter(row["mode"] for row in rows)
    mode_summary = []
    for mode in DISCOURSE_MODES:
        mode_rows = [row for row in rows if row["mode"] == mode]
        aorist_count = sum(1 for row in mode_rows if row["has_aorist"])
        mode_summary.append(
            {
                "discourse_mode": mode,
                "discourse_mode_label": DISCOURSE_MODE_LABELS.get(mode, mode),
                "sentence_count": int(len(mode_rows)),
                "aorist_count": int(aorist_count),
                "aorist_rate": float(aorist_count / len(mode_rows)) if mode_rows else 0.0,
                "book_count": int(len({row["book"] for row in mode_rows})),
            }
        )

    adjusted_regressions = {
        "book_only_all_books": _linear_probability_book_fit(rows, include_modes=False),
        "mode_adjusted_all_books": _linear_probability_book_fit(rows, include_modes=True),
        "book_only_excluding_4_8": _linear_probability_book_fit(
            rows,
            include_modes=False,
            exclude_books={4, 8},
        ),
        "mode_adjusted_excluding_4_8": _linear_probability_book_fit(
            rows,
            include_modes=True,
            exclude_books={4, 8},
        ),
    }

    return {
        "available": bool(rows),
        "model": grammar_data.get("model") or model,
        "prompt_version": prompt_version,
        "discourse_modes": [
            {"id": mode, "label": DISCOURSE_MODE_LABELS.get(mode, mode)}
            for mode in DISCOURSE_MODES
        ],
        "unit_rows": rows,
        "mode_summary": mode_summary,
        "book_aorist": _aorist_book_rows(rows),
        "mode_composition": _mode_composition_rows(rows),
        "mode_trends": _mode_aorist_trend_rows(rows),
        "adjusted_regressions": adjusted_regressions,
        "metrics": {
            "parsed_sentence_count": int(len(units)),
            "tagged_sentence_count": int(len(rows)),
            "book_count": int(len({row["book"] for row in rows})),
            "mode_count": int(len([mode for mode, count in mode_counts.items() if count > 0])),
            "aorist_sentence_count": int(sum(1 for row in rows if row["has_aorist"])),
            "aorist_rate": (
                float(sum(1 for row in rows if row["has_aorist"]) / len(rows))
                if rows
                else 0.0
            ),
        },
        "notes": [
            "This is a content-control pilot over sentences that have both LLM grammar parses and discourse-mode tags.",
            "The mode-adjusted fits are linear probability diagnostics for a sentence containing at least one Tense=Aor token.",
            "Within-mode trend lines use book-level aorist proportions weighted by the number of tagged parsed sentences in that mode/book cell.",
        ],
    }


def get_passage_summaries(conn):
    """Get one-line summaries for passages (from passage_summaries table)."""
    cursor = conn.cursor()

    if not table_exists(conn, "passage_summaries"):
        return {}

    cursor.execute("SELECT passage_id, summary FROM passage_summaries")
    return dict(cursor.fetchall())


def count_words(text):
    """Count word-like tokens in Greek or English text."""
    if text is None:
        return 0
    return len(WORD_PATTERN.findall(str(text)))


def _coefficient_p_value(coefficient, std_error, dof):
    """Return a two-sided p-value for a regression coefficient."""
    if dof <= 0 or not np.isfinite(std_error):
        return math.nan
    if std_error == 0:
        if coefficient == 0:
            return 1.0
        return 0.0
    t_statistic = coefficient / std_error
    return float(2.0 * stats.t.sf(abs(t_statistic), dof))


def simple_length_model_stats(greek_lengths, english_lengths, expected_lengths, length_model):
    """Calculate coefficient standard errors and p-values for the length model."""
    x = np.asarray(greek_lengths, dtype=float).reshape(-1)
    y = np.asarray(english_lengths, dtype=float).reshape(-1)
    predicted = np.asarray(expected_lengths, dtype=float).reshape(-1)
    sample_count = len(x)
    dof = sample_count - 2
    slope = float(length_model.coef_[0])
    intercept = float(length_model.intercept_)

    x_mean = float(np.mean(x)) if sample_count else math.nan
    sxx = float(np.sum((x - x_mean) ** 2)) if sample_count else 0.0
    if dof <= 0 or sxx == 0:
        return {
            "length_intercept_std_error": math.nan,
            "length_intercept_p_value": math.nan,
            "length_slope_std_error": math.nan,
            "length_slope_p_value": math.nan,
        }

    residuals = y - predicted
    residual_sum_squares = float(np.sum(residuals ** 2))
    residual_variance = residual_sum_squares / dof
    slope_std_error = math.sqrt(residual_variance / sxx)
    intercept_std_error = math.sqrt(residual_variance * ((1.0 / sample_count) + (x_mean ** 2 / sxx)))

    return {
        "length_intercept_std_error": float(intercept_std_error),
        "length_intercept_p_value": _coefficient_p_value(intercept, intercept_std_error, dof),
        "length_slope_std_error": float(slope_std_error),
        "length_slope_p_value": _coefficient_p_value(slope, slope_std_error, dof),
    }


def tfidf_casefold_preprocessor(text):
    """Casefold and normalize text before Greek TF-IDF tokenization."""
    return unicodedata.normalize("NFC", str(text).casefold())


def calculate_residual_predictors(
    texts,
    residuals,
    *,
    max_features,
    top_features,
    min_df,
    stop_words=None,
):
    """Find terms associated with positive or negative length residuals."""
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        min_df=min_df,
        ngram_range=(1, 2),
        token_pattern=TFIDF_TOKEN_PATTERN,
        preprocessor=tfidf_casefold_preprocessor,
        stop_words=stop_words,
    )

    feature_matrix = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()
    if len(feature_names) == 0:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0, 0.0

    residual_model = Ridge(alpha=10.0)
    residual_model.fit(feature_matrix, residuals)
    predicted_residuals = residual_model.predict(feature_matrix)
    coefficients = residual_model.coef_

    analyzer = vectorizer.build_analyzer()
    vocab = set(feature_names)
    present_counts = {feature: 0 for feature in feature_names}
    residual_sums = {feature: 0.0 for feature in feature_names}

    for text, residual in zip(texts, residuals):
        terms = {term for term in analyzer(text) if term in vocab}
        for term in terms:
            present_counts[term] += 1
            residual_sums[term] += float(residual)

    overall_mean_residual = float(np.mean(residuals))
    predictor_rows = []
    sample_count = len(texts)
    total_residual = float(np.sum(residuals))
    for feature, coefficient in zip(feature_names, coefficients):
        count = present_counts[feature]
        if count == 0:
            continue
        absent_count = sample_count - count
        present_mean = residual_sums[feature] / count
        absent_sum = total_residual - residual_sums[feature]
        absent_mean = absent_sum / absent_count if absent_count > 0 else overall_mean_residual
        predictor_rows.append(
            {
                "phrase": feature,
                "coefficient": float(coefficient),
                "passage_count": int(count),
                "mean_residual_with_term": float(present_mean),
                "mean_residual_without_term": float(absent_mean),
            }
        )

    predictors = pd.DataFrame(predictor_rows)
    if len(predictors) == 0:
        longer_predictors = pd.DataFrame()
        shorter_predictors = pd.DataFrame()
    else:
        longer_predictors = predictors[predictors["coefficient"] > 0].sort_values(
            "coefficient", ascending=False
        ).head(top_features)
        shorter_predictors = predictors[predictors["coefficient"] < 0].sort_values(
            "coefficient", ascending=True
        ).head(top_features)

    return (
        longer_predictors.reset_index(drop=True),
        shorter_predictors.reset_index(drop=True),
        predictors.reset_index(drop=True),
        int(len(feature_names)),
        float(r2_score(residuals, predicted_residuals)),
    )


def _safe_correlation(x_values, y_values, *, method):
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    finite = np.isfinite(x) & np.isfinite(y)
    x = x[finite]
    y = y[finite]
    if len(x) < 3 or float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return {"coefficient": None, "p_value": None}
    if method == "spearman":
        coefficient, p_value = stats.spearmanr(x, y)
    else:
        coefficient, p_value = stats.pearsonr(x, y)
    return {
        "coefficient": float(coefficient) if math.isfinite(coefficient) else None,
        "p_value": float(p_value) if math.isfinite(p_value) else None,
    }


def _quadratic_r2(x_values, y_values):
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    finite = np.isfinite(x) & np.isfinite(y)
    x = x[finite]
    y = y[finite]
    if len(x) < 3 or float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return None
    design = np.column_stack([x, x ** 2])
    model = LinearRegression()
    model.fit(design, y)
    predicted = model.predict(design)
    return float(r2_score(y, predicted))


def calculate_translation_mythic_coefficient_relationship(
    translation_length_analysis,
    greta_analysis,
):
    """Relate translation-length residual terms to mythic/historical coefficients."""
    unavailable = {
        "available": False,
        "message": "Translation residual and Greta coefficient data are not both available.",
        "points": pd.DataFrame(),
        "metrics": {},
    }
    if not translation_length_analysis or not translation_length_analysis.get("available"):
        result = unavailable.copy()
        result["message"] = "Translation length residual data is unavailable."
        return result
    if not greta_analysis or not greta_analysis.get("available"):
        result = unavailable.copy()
        result["message"] = "Greta mythic/historical coefficient data is unavailable."
        return result

    baseline = next(
        (
            variant for variant in greta_analysis.get("variants", [])
            if variant.get("token_source") == "lemma"
            and not variant.get("include_books_4_8")
            and not variant.get("remove_rhetoric_markers")
        ),
        None,
    )
    if not baseline or not baseline.get("available"):
        result = unavailable.copy()
        result["message"] = "The paper-facing lemma model is unavailable."
        return result

    residual_terms = translation_length_analysis.get("all_greek_predictors")
    if residual_terms is None or len(residual_terms) == 0:
        fallback_frames = []
        for direction, key in (("longer", "longer_predictors"), ("shorter", "shorter_predictors")):
            frame = translation_length_analysis.get(key)
            if frame is not None and len(frame) > 0:
                fallback_frame = frame.copy()
                fallback_frame["translation_direction"] = direction
                fallback_frames.append(fallback_frame)
        residual_terms = (
            pd.concat(fallback_frames, ignore_index=True)
            if fallback_frames
            else pd.DataFrame()
        )
    if residual_terms is None or len(residual_terms) == 0:
        result = unavailable.copy()
        result["message"] = "No Greek residual terms are available."
        return result

    residual_terms = residual_terms.copy()
    if "translation_direction" not in residual_terms.columns:
        residual_terms["translation_direction"] = np.where(
            residual_terms["coefficient"].astype(float) >= 0,
            "longer",
            "shorter",
        )
    residual_terms = residual_terms.rename(
        columns={
            "coefficient": "translation_residual_coefficient",
            "passage_count": "translation_passage_count",
            "mean_residual_with_term": "mean_translation_residual_with_term",
            "mean_residual_without_term": "mean_translation_residual_without_term",
        }
    )
    residual_terms["abs_translation_residual_coefficient"] = residual_terms[
        "translation_residual_coefficient"
    ].abs()
    residual_terms = (
        residual_terms.sort_values("abs_translation_residual_coefficient", ascending=False)
        .drop_duplicates(subset=["phrase"])
        .reset_index(drop=True)
    )

    classifier_predictors = baseline.get("all_predictors")
    if classifier_predictors is None or len(classifier_predictors) == 0:
        classifier_predictors = baseline.get("predictors")
    if classifier_predictors is None or len(classifier_predictors) == 0:
        result = unavailable.copy()
        result["message"] = "The paper-facing lemma model has no coefficient table."
        return result

    classifier_terms = classifier_predictors.copy().rename(
        columns={
            "coefficient": "mythic_log_odds_coefficient",
            "p_value": "mythic_p_value",
            "q_value": "mythic_q_value",
        }
    )
    merged = residual_terms.merge(
        classifier_terms[
            [
                "phrase",
                "mythic_log_odds_coefficient",
                "mythic_count",
                "historical_count",
                "mythic_p_value",
                "mythic_q_value",
            ]
        ],
        on="phrase",
        how="inner",
    )
    if len(merged) == 0:
        result = unavailable.copy()
        result["message"] = "None of the Greek residual terms are features in the paper-facing lemma model."
        return result

    merged["classification_direction"] = np.where(
        merged["mythic_log_odds_coefficient"] >= 0,
        "mythic",
        "historical",
    )
    merged["abs_mythic_log_odds_coefficient"] = merged[
        "mythic_log_odds_coefficient"
    ].abs()
    merged = merged.sort_values(
        ["abs_translation_residual_coefficient", "abs_mythic_log_odds_coefficient"],
        ascending=[False, False],
    ).reset_index(drop=True)

    x = merged["translation_residual_coefficient"].to_numpy(dtype=float)
    y = merged["mythic_log_odds_coefficient"].to_numpy(dtype=float)
    abs_x = np.abs(x)
    abs_y = np.abs(y)
    metrics = {
        "matched_term_count": int(len(merged)),
        "residual_term_count": int(len(residual_terms)),
        "baseline_feature_count": int(baseline.get("feature_count", 0)),
        "linear_pearson": _safe_correlation(x, y, method="pearson"),
        "linear_spearman": _safe_correlation(x, y, method="spearman"),
        "extremity_pearson": _safe_correlation(abs_x, abs_y, method="pearson"),
        "extremity_spearman": _safe_correlation(abs_x, abs_y, method="spearman"),
        "quadratic_abs_r2": _quadratic_r2(x, abs_y),
    }

    return {
        "available": True,
        "message": "",
        "points": merged.reset_index(drop=True),
        "metrics": metrics,
    }


def calculate_translation_length_analysis(
    passages_df,
    max_features=1200,
    top_features=30,
    min_df=2,
    greek_stop_words=None,
):
    """Model English translation length residuals from Greek vocabulary.

    First fit English word count from Greek word count. Then regress the
    resulting residuals against Greek vocabulary to identify words and phrases
    associated with unexpectedly long or short English translations.
    """
    empty_result = {
        "available": False,
        "message": "No completed translations found.",
        "metrics": {},
        "longer_predictors": pd.DataFrame(),
        "shorter_predictors": pd.DataFrame(),
        "all_greek_predictors": pd.DataFrame(),
        "english_longer_predictors": pd.DataFrame(),
        "english_shorter_predictors": pd.DataFrame(),
        "all_english_predictors": pd.DataFrame(),
        "length_points": pd.DataFrame(),
        "longest_passages": pd.DataFrame(),
        "shortest_passages": pd.DataFrame(),
    }

    if passages_df is None or len(passages_df) == 0:
        return empty_result

    df = passages_df.copy()
    df = df.dropna(subset=["passage", "english_translation"])
    df["passage"] = df["passage"].astype(str)
    df["english_translation"] = df["english_translation"].astype(str)
    df = df[(df["passage"].str.strip() != "") & (df["english_translation"].str.strip() != "")]
    if len(df) < 5:
        result = empty_result.copy()
        result["message"] = "At least five completed translations are needed for the length model."
        return result

    df["greek_word_count"] = df["passage"].map(count_words)
    df["english_word_count"] = df["english_translation"].map(count_words)
    df = df[(df["greek_word_count"] > 0) & (df["english_word_count"] > 0)].copy()
    sample_count = len(df)
    if len(df) < 5:
        result = empty_result.copy()
        result["message"] = "At least five translations with non-empty Greek and English word counts are needed."
        return result

    greek_lengths = df[["greek_word_count"]].to_numpy(dtype=float)
    english_lengths = df["english_word_count"].to_numpy(dtype=float)

    length_model = LinearRegression()
    length_model.fit(greek_lengths, english_lengths)
    expected_lengths = length_model.predict(greek_lengths)
    residuals = english_lengths - expected_lengths

    df["expected_english_word_count"] = expected_lengths
    df["length_residual"] = residuals
    length_model_stats = simple_length_model_stats(
        greek_lengths,
        english_lengths,
        expected_lengths,
        length_model,
    )

    greek_vocabulary_column = "lemma_passage" if "lemma_passage" in df.columns else "passage"
    try:
        (
            longer_predictors,
            shorter_predictors,
            all_greek_predictors,
            greek_feature_count,
            greek_residual_r2,
        ) = calculate_residual_predictors(
            df[greek_vocabulary_column],
            residuals,
            max_features=max_features,
            top_features=top_features,
            min_df=min_df,
            stop_words=greek_stop_words,
        )
    except ValueError as exc:
        result = empty_result.copy()
        result["message"] = f"Could not build Greek vocabulary model: {exc}"
        return result

    try:
        (
            english_longer_predictors,
            english_shorter_predictors,
            all_english_predictors,
            english_feature_count,
            english_residual_r2,
        ) = calculate_residual_predictors(
            df["english_translation"],
            residuals,
            max_features=max_features,
            top_features=top_features,
            min_df=min_df,
        )
    except ValueError:
        english_longer_predictors = pd.DataFrame()
        english_shorter_predictors = pd.DataFrame()
        all_english_predictors = pd.DataFrame()
        english_feature_count = 0
        english_residual_r2 = 0.0

    if greek_feature_count == 0:
        result = empty_result.copy()
        result["message"] = "No repeated Greek vocabulary was available for the residual model."
        return result

    longest_passages = df.sort_values("length_residual", ascending=False).head(20)
    shortest_passages = df.sort_values("length_residual", ascending=True).head(20)
    length_points = df[
        [
            "id",
            "greek_word_count",
            "english_word_count",
            "expected_english_word_count",
            "length_residual",
        ]
    ].sort_values(["greek_word_count", "english_word_count", "id"])

    metrics = {
        "passage_count": int(sample_count),
        "feature_count": int(greek_feature_count),
        "english_feature_count": int(english_feature_count),
        "length_intercept": float(length_model.intercept_),
        "length_slope": float(length_model.coef_[0]),
        "length_r2": float(r2_score(english_lengths, expected_lengths)),
        "residual_std": float(np.std(residuals)),
        "vocabulary_residual_r2": float(greek_residual_r2),
        "english_vocabulary_residual_r2": float(english_residual_r2),
        "greek_vocabulary_source": "lemma" if greek_vocabulary_column == "lemma_passage" else "surface",
        "min_df": int(min_df),
        "max_features": int(max_features),
    }
    metrics.update(length_model_stats)

    return {
        "available": True,
        "message": "",
        "metrics": metrics,
        "longer_predictors": longer_predictors.reset_index(drop=True),
        "shorter_predictors": shorter_predictors.reset_index(drop=True),
        "all_greek_predictors": all_greek_predictors.reset_index(drop=True),
        "english_longer_predictors": english_longer_predictors.reset_index(drop=True),
        "english_shorter_predictors": english_shorter_predictors.reset_index(drop=True),
        "all_english_predictors": all_english_predictors.reset_index(drop=True),
        "length_points": length_points.reset_index(drop=True),
        "longest_passages": longest_passages.reset_index(drop=True),
        "shortest_passages": shortest_passages.reset_index(drop=True),
    }


TRANSLATION_BUCKET_LABELS = {
    "mythic": "Mythic",
    "historical": "Historical",
    "other": "Other",
}


def _empty_sentence_translation_bucket_analysis(message="No tagged sentence translations found."):
    return {
        "available": False,
        "message": message,
        "metrics": {},
        "bucket_summary": pd.DataFrame(),
        "bucket_analyses": {},
        "sentence_analysis": {},
    }


def _sentence_bucket_id(row):
    passage_id = str(row.get("passage_id", "")).strip()
    sentence_number = str(row.get("sentence_number", "")).strip()
    if passage_id and sentence_number:
        return f"{passage_id}#{sentence_number}"
    return ""


def _fit_bucket_length_model(bucket_rows):
    x = bucket_rows["greek_word_count"].to_numpy(dtype=float).reshape(-1, 1)
    y = bucket_rows["english_word_count"].to_numpy(dtype=float)
    if len(bucket_rows) < 3 or float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return None, None

    model = LinearRegression()
    model.fit(x, y)
    predicted = model.predict(x)
    return float(model.coef_[0]), float(r2_score(y, predicted))


def calculate_sentence_translation_bucket_analysis(
    sentences_df,
    max_features=1200,
    top_features=20,
    min_df=2,
    greek_stop_words=None,
):
    """Compare sentence-level translation length residuals across Greta buckets."""
    required_columns = {"sentence", "english_sentence", "myth_history_bucket"}
    if sentences_df is None or len(sentences_df) == 0:
        return _empty_sentence_translation_bucket_analysis()
    missing_columns = required_columns.difference(sentences_df.columns)
    if missing_columns:
        return _empty_sentence_translation_bucket_analysis(
            f"Tagged sentence translation data is missing: {', '.join(sorted(missing_columns))}."
        )

    df = sentences_df.copy()
    df = df.dropna(subset=["sentence", "english_sentence", "myth_history_bucket"])
    df["sentence"] = df["sentence"].astype(str)
    df["english_sentence"] = df["english_sentence"].astype(str)
    df["myth_history_bucket"] = df["myth_history_bucket"].astype(str)
    df = df[
        (df["sentence"].str.strip() != "")
        & (df["english_sentence"].str.strip() != "")
        & (df["myth_history_bucket"].isin(TRANSLATION_BUCKET_LABELS))
    ].copy()
    if len(df) < 5:
        return _empty_sentence_translation_bucket_analysis(
            "At least five tagged sentence translations are needed for the bucket length model."
        )

    if "id" not in df.columns:
        df["id"] = df.apply(_sentence_bucket_id, axis=1)
    df["id"] = df["id"].astype(str)
    missing_ids = df["id"].str.strip() == ""
    if missing_ids.any():
        df.loc[missing_ids, "id"] = [f"sentence-{i}" for i in range(1, int(missing_ids.sum()) + 1)]

    analysis_df = df[
        [
            "id",
            "sentence",
            "english_sentence",
            "myth_history_bucket",
        ]
    ].rename(columns={"sentence": "passage", "english_sentence": "english_translation"})
    if "lemma_sentence" in df.columns:
        analysis_df = analysis_df.copy()
        analysis_df["lemma_passage"] = df["lemma_sentence"].astype(str)

    sentence_analysis = calculate_translation_length_analysis(
        analysis_df,
        max_features=max_features,
        top_features=top_features,
        min_df=min_df,
        greek_stop_words=greek_stop_words,
    )
    if not sentence_analysis.get("available"):
        return _empty_sentence_translation_bucket_analysis(
            f"Could not calculate the shared sentence baseline: {sentence_analysis.get('message', '')}"
        )

    length_points = sentence_analysis["length_points"][
        [
            "id",
            "greek_word_count",
            "english_word_count",
            "expected_english_word_count",
            "length_residual",
        ]
    ]
    bucket_points = df[["id", "myth_history_bucket"]].merge(length_points, on="id", how="inner")
    if len(bucket_points) == 0:
        return _empty_sentence_translation_bucket_analysis(
            "No sentence bucket rows matched the shared sentence baseline."
        )

    summary_rows = []
    bucket_analyses = {}
    for bucket, label in TRANSLATION_BUCKET_LABELS.items():
        bucket_rows = bucket_points[bucket_points["myth_history_bucket"] == bucket].copy()
        if len(bucket_rows) == 0:
            continue

        bucket_slope, bucket_r2 = _fit_bucket_length_model(bucket_rows)
        greek_total = float(bucket_rows["greek_word_count"].sum())
        english_total = float(bucket_rows["english_word_count"].sum())
        summary_rows.append(
            {
                "bucket": bucket,
                "label": label,
                "sentence_count": int(len(bucket_rows)),
                "mean_greek_word_count": float(bucket_rows["greek_word_count"].mean()),
                "mean_english_word_count": float(bucket_rows["english_word_count"].mean()),
                "english_per_greek_word": english_total / greek_total if greek_total else math.nan,
                "mean_expected_english_word_count": float(
                    bucket_rows["expected_english_word_count"].mean()
                ),
                "mean_global_residual": float(bucket_rows["length_residual"].mean()),
                "median_global_residual": float(bucket_rows["length_residual"].median()),
                "global_residual_std": float(np.std(bucket_rows["length_residual"])),
                "bucket_length_slope": bucket_slope,
                "bucket_length_r2": bucket_r2,
            }
        )

        bucket_ids = set(bucket_rows["id"])
        bucket_analysis_df = analysis_df[analysis_df["id"].isin(bucket_ids)].copy()
        if len(bucket_analysis_df) >= 5:
            bucket_analyses[bucket] = calculate_translation_length_analysis(
                bucket_analysis_df,
                max_features=max_features,
                top_features=top_features,
                min_df=min_df,
                greek_stop_words=greek_stop_words,
            )
        else:
            bucket_analyses[bucket] = _empty_sentence_translation_bucket_analysis(
                "At least five sentence translations are needed for this bucket model."
            )

    bucket_summary = pd.DataFrame(summary_rows)
    if len(bucket_summary) > 0:
        bucket_summary["_order"] = bucket_summary["bucket"].map(
            {bucket: index for index, bucket in enumerate(TRANSLATION_BUCKET_LABELS)}
        )
        bucket_summary = bucket_summary.sort_values("_order").drop(columns=["_order"])

    metrics = {
        "sentence_count": int(len(bucket_points)),
        "bucket_count": int(len(bucket_summary)),
        "length_slope": sentence_analysis["metrics"]["length_slope"],
        "length_r2": sentence_analysis["metrics"]["length_r2"],
        "residual_std": sentence_analysis["metrics"]["residual_std"],
        "vocabulary_residual_r2": sentence_analysis["metrics"]["vocabulary_residual_r2"],
        "greek_vocabulary_source": sentence_analysis["metrics"].get("greek_vocabulary_source"),
        "min_df": int(min_df),
        "max_features": int(max_features),
    }

    return {
        "available": True,
        "message": "",
        "metrics": metrics,
        "bucket_summary": bucket_summary.reset_index(drop=True),
        "bucket_analyses": bucket_analyses,
        "sentence_analysis": sentence_analysis,
    }


def get_sentence_translation_bucket_analysis(conn):
    """Get sentence-level translation length residuals by Greta myth/history bucket."""
    if not table_exists(conn, "greek_sentences") or not table_exists(conn, "sentence_greta_tags"):
        return _empty_sentence_translation_bucket_analysis(
            "Sentence translations or Greta bucket tags are not available."
        )

    df = get_greta_sentence_annotations(conn)
    if len(df) == 0:
        return _empty_sentence_translation_bucket_analysis()

    greek_stop_words = None
    if table_exists(conn, "greek_word_lemmas"):
        lemma_lookup = load_word_lemma_lookup(conn)
        if lemma_lookup:
            lemma_texts, _ = build_lemma_texts(df["sentence"], lemma_lookup)
            df = df.copy()
            df["lemma_sentence"] = lemma_texts
            if table_exists(conn, "proper_nouns") and table_exists(conn, "manual_stopwords"):
                stopword_query = """
                SELECT exact_form AS word FROM proper_nouns
                UNION
                SELECT reference_form AS word FROM proper_nouns
                UNION
                SELECT word FROM manual_stopwords
                """
                stopword_df = read_sql_query(stopword_query, conn)
                greek_stop_words = expand_stopwords_with_lemma_forms(
                    stopword_df["word"].tolist(),
                    lemma_lookup,
                )

    return calculate_sentence_translation_bucket_analysis(
        df,
        greek_stop_words=greek_stop_words,
    )


def get_translation_length_analysis(conn):
    """Get translation-length residual model output for the website."""
    query = """
    SELECT p.id, p.passage, t.english_translation
    FROM passages p
    JOIN translations t ON p.id = t.passage_id
    WHERE t.english_translation IS NOT NULL
      AND btrim(t.english_translation) <> ''
    ORDER BY p.id
    """
    df = read_sql_query(query, conn)
    if len(df) > 0:
        df["sort_key"] = df["id"].apply(passage_id_sort_key)
        df = df.sort_values("sort_key").drop(columns=["sort_key"])
        if table_exists(conn, "greek_word_lemmas"):
            lemma_lookup = load_word_lemma_lookup(conn)
            if lemma_lookup:
                lemma_texts, _ = build_lemma_texts(df["passage"], lemma_lookup)
                df = df.copy()
                df["lemma_passage"] = lemma_texts
                stopword_query = """
                SELECT exact_form AS word FROM proper_nouns
                UNION
                SELECT reference_form AS word FROM proper_nouns
                UNION
                SELECT word FROM manual_stopwords
                """
                stopword_df = read_sql_query(stopword_query, conn)
                greek_stop_words = expand_stopwords_with_lemma_forms(
                    stopword_df["word"].tolist(),
                    lemma_lookup,
                )
                return calculate_translation_length_analysis(
                    df,
                    greek_stop_words=greek_stop_words,
                )
    return calculate_translation_length_analysis(df)


def get_progress_data(conn):
    """Get progress data for all pipeline tasks."""
    from math import ceil
    from datetime import date, timedelta

    cursor = conn.cursor()
    today = date.today()

    def fetch_scalar(sql, params=None, default=0):
        cursor.execute(sql, params or ())
        row = cursor.fetchone()
        if not row:
            return default
        value = row[0]
        return default if value is None else value

    def has_tables(*table_names):
        return all(table_exists(conn, table_name) for table_name in table_names)

    def count_if_table(table_name, sql, params=None):
        if not table_exists(conn, table_name):
            return None
        return fetch_scalar(sql, params)

    def status_counts(table_name, where="", params=None):
        if not table_exists(conn, table_name):
            return []
        where_sql = f"WHERE {where}" if where else ""
        cursor.execute(
            f"""
            SELECT status, COUNT(*) AS runs
            FROM {table_name}
            {where_sql}
            GROUP BY status
            ORDER BY status
            """,
            params or (),
        )
        return [(status, int(count)) for status, count in cursor.fetchall()]

    def format_status_counts(counts):
        if not counts:
            return ""
        return "; ".join(
            f"{status.replace('_', ' ')}: {count:,}" for status, count in counts
        )

    def predictor_done(*table_names):
        done = 0
        for table_name in table_names:
            if table_exists(conn, table_name) and fetch_scalar(f"SELECT COUNT(*) FROM {table_name}") > 0:
                done += 1
        return done

    def add_task(
        *,
        name,
        area,
        script,
        done,
        total,
        batch_size=None,
        cadence=None,
        status=None,
        details="",
    ):
        if done is None:
            done = 0
        if total is not None and total > 0:
            percent = round(100 * done / total, 1)
        else:
            percent = None

        if status is None:
            if total is None:
                status = "Tracking"
            elif total <= 0:
                status = "No target rows"
            elif done >= total:
                status = "Complete"
            elif done > 0:
                status = "In progress"
            else:
                status = "Not started"

        if total is None or total <= 0:
            est_completion = "n/a"
        else:
            remaining = total - done
            if remaining <= 0:
                est_completion = "Done"
            elif isinstance(batch_size, (int, float)) and batch_size > 0:
                days_needed = ceil(remaining / batch_size)
                est_completion = (today + timedelta(days=days_needed)).isoformat()
            else:
                est_completion = "Unknown"

        tasks.append(
            {
                "name": name,
                "area": area,
                "script": script,
                "batch_size": batch_size,
                "cadence": cadence or (f"{batch_size:,}/day" if batch_size else "ad hoc"),
                "total": total,
                "done": int(done),
                "percent": percent,
                "status": status,
                "details": details,
                "est_completion": est_completion,
            }
        )

    total_passages = fetch_scalar("SELECT COUNT(*) FROM passages")
    total_sentences = count_if_table("greek_sentences", "SELECT COUNT(*) FROM greek_sentences") or 0
    passages_with_sentences = count_if_table(
        "greek_sentences",
        "SELECT COUNT(DISTINCT passage_id) FROM greek_sentences",
    ) or 0
    total_nouns = count_if_table(
        "proper_nouns",
        "SELECT COUNT(DISTINCT reference_form || '|' || entity_type) FROM proper_nouns",
    ) or 0

    if passages_with_sentences and total_sentences:
        sentence_total_target = total_sentences
    else:
        sentence_total_target = total_passages

    tasks = []

    add_task(
        name="Passage mythic/skeptic labels",
        area="Core labels",
        script="mythic_sceptic_analyser.py",
        batch_size=50,
        done=fetch_scalar("SELECT COUNT(*) FROM passages WHERE references_mythic_era IS NOT NULL"),
        total=total_passages,
        details="Passage-level mythic-era and scepticism flags.",
    )
    add_task(
        name="Proper-noun extraction",
        area="Names and places",
        script="extract_proper_nouns.py",
        batch_size=50,
        done=count_if_table(
            "noun_extraction_status",
            "SELECT COUNT(*) FROM noun_extraction_status WHERE is_processed",
        ),
        total=total_passages,
        details="Sections processed for proper nouns.",
    )
    add_task(
        name="Wikidata linking",
        area="Names and places",
        script="link_wikidata.py",
        batch_size=100,
        done=count_if_table("wikidata_links", "SELECT COUNT(*) FROM wikidata_links"),
        total=total_nouns,
        details="Unique name/type pairs linked or reviewed.",
    )
    add_task(
        name="Translation",
        area="Text preparation",
        script="translate_pausanias.py",
        batch_size=50,
        done=count_if_table(
            "translations",
            """
            SELECT COUNT(*)
            FROM translations
            WHERE english_translation IS NOT NULL
              AND btrim(english_translation) <> ''
            """,
        ),
        total=total_passages,
        details="Passage-level English translations.",
    )
    add_task(
        name="Sentence splitting",
        area="Text preparation",
        script="split_sentences.py",
        batch_size=200,
        done=passages_with_sentences,
        total=total_passages,
        details=f"{total_sentences:,} aligned Greek/English sentences available.",
    )
    add_task(
        name="Passage summaries",
        area="Text preparation",
        script="summarise_passages.py",
        batch_size=50,
        done=count_if_table("passage_summaries", "SELECT COUNT(*) FROM passage_summaries"),
        total=total_passages,
        details="Short summaries used on reader pages.",
    )

    passage_predictor_tables = (
        "mythicness_predictors",
        "skepticism_predictors",
        "simplified_mythicness_predictors",
        "simplified_skepticism_predictors",
    )
    add_task(
        name="Passage predictor models",
        area="Statistical models",
        script="find_predictors.py",
        done=predictor_done(*passage_predictor_tables),
        total=len(passage_predictor_tables),
        cadence="refresh",
        details="Full and simplified passage-level TF-IDF models.",
    )

    sentence_predictor_tables = (
        "sentence_mythicness_predictors",
        "sentence_skepticism_predictors",
        "sentence_simplified_mythicness_predictors",
        "sentence_simplified_skepticism_predictors",
    )
    add_task(
        name="Sentence predictor models",
        area="Statistical models",
        script="find_sentence_predictors.py",
        done=predictor_done(*sentence_predictor_tables),
        total=len(sentence_predictor_tables),
        cadence="refresh",
        details="Sentence-level TF-IDF model artifacts.",
    )
    add_task(
        name="Proper-noun network",
        area="Names and places",
        script="analyse_noun_network.py",
        done=count_if_table(
            "noun_centrality",
            "SELECT COUNT(DISTINCT reference_form || '|' || entity_type) FROM noun_centrality",
        ),
        total=total_nouns,
        cadence="refresh",
        details="Co-occurrence network and centrality rows.",
    )

    greta_both_status = format_status_counts(
        status_counts(
            "sentence_tagging_runs",
            "mode = %s AND prompt_version = %s",
            ("greta-both-batch", GRETA_INSPIRED_CLASSIFIER_VERSION),
        )
    )
    add_task(
        name="Greta-inspired sentence tags",
        area="Sentence labels",
        script="sentence_tagging_daily.sh",
        batch_size=max(1, 1_500_000 // 680),
        cadence="Batch API, ~2,205/day",
        done=count_if_table(
            "sentence_greta_both_tags",
            "SELECT COUNT(*) FROM sentence_greta_both_tags WHERE prompt_version = %s",
            (GRETA_INSPIRED_CLASSIFIER_VERSION,),
        ),
        total=sentence_total_target,
        details=greta_both_status or "Calibrated two-flag production sentence tagger.",
    )
    greta_status = format_status_counts(
        status_counts(
            "sentence_tagging_runs",
            "mode = %s AND prompt_version = %s",
            ("greta-batch", ORIGINAL_CLASSIFIER_VERSION),
        )
    )
    add_task(
        name="Original sentence tags",
        area="Sentence labels",
        script="sentence_tagging_daily.sh",
        batch_size=max(1, 500_000 // 545),
        cadence="Batch API, ~917/day",
        done=count_if_table(
            "sentence_greta_tags",
            "SELECT COUNT(*) FROM sentence_greta_tags WHERE prompt_version = %s",
            (ORIGINAL_CLASSIFIER_VERSION,),
        ),
        total=sentence_total_target,
        details=greta_status or "Original single-bucket production comparison tagger.",
    )
    legacy_status = format_status_counts(
        status_counts(
            "sentence_tagging_runs",
            "mode = %s",
            ("legacy-batch",),
        )
    )
    add_task(
        name="Legacy sentence classifier",
        area="Sentence labels",
        script="sentence_tagging_daily.sh",
        batch_size=5,
        cadence="5/day comparison",
        done=count_if_table(
            "greek_sentences",
            "SELECT COUNT(*) FROM greek_sentences WHERE references_mythic_era IS NOT NULL",
        ),
        total=sentence_total_target,
        details=legacy_status or "Slow legacy boolean classifier retained for comparison.",
    )

    grammar_done = count_if_table(
        "sentence_llm_grammar_analyses",
        """
        SELECT COUNT(*)
        FROM sentence_llm_grammar_analyses
        WHERE model = %s
          AND prompt_version = %s
        """,
        (DEFAULT_LLM_GRAMMAR_MODEL, "greek-sentence-grammar-v1"),
    )
    grammar_tokens = 0
    if table_exists(conn, "sentence_llm_grammar_analyses"):
        grammar_tokens = fetch_scalar(
            """
            SELECT COALESCE(SUM(input_tokens + output_tokens), 0)
            FROM sentence_llm_grammar_analyses
            WHERE model = %s
              AND prompt_version = %s
            """,
            (DEFAULT_LLM_GRAMMAR_MODEL, "greek-sentence-grammar-v1"),
        )
    grammar_batch_size = 400
    if grammar_done and grammar_tokens:
        grammar_batch_size = max(1, int(1_000_000 // max(1, grammar_tokens / grammar_done)))
    grammar_status = format_status_counts(
        status_counts(
            "sentence_llm_grammar_runs",
            "model = %s AND prompt_version = %s",
            (DEFAULT_LLM_GRAMMAR_MODEL, "greek-sentence-grammar-v1"),
        )
    )
    add_task(
        name="LLM grammar analysis",
        area="Grammar",
        script="sentence_llm_grammar_daily.sh",
        batch_size=grammar_batch_size,
        cadence=f"1M tokens/day, ~{grammar_batch_size:,}/day",
        done=grammar_done,
        total=sentence_total_target,
        details=grammar_status or "LLM-generated CoNLL-U-style grammar parses.",
    )

    discourse_status = format_status_counts(
        status_counts(
            "sentence_tagging_runs",
            "mode = %s AND prompt_version = %s",
            ("discourse-batch", DISCOURSE_MODE_PROMPT_VERSION),
        )
    )
    add_task(
        name="Discourse mode sentence tags",
        area="Sentence labels",
        script="sentence_tagging_daily.sh",
        batch_size=max(1, 100_000 // 1000),
        cadence="Batch API, 100k tokens/day",
        done=count_if_table(
            "sentence_discourse_mode_tags",
            "SELECT COUNT(*) FROM sentence_discourse_mode_tags WHERE prompt_version = %s",
            (DISCOURSE_MODE_PROMPT_VERSION,),
        ),
        total=grammar_done,
        details=(
            discourse_status
            or "Pilot classifier over the grammar-parsed subset for aorist content controls."
        ),
    )

    if has_tables("sentence_udpipe_analyses"):
        add_task(
            name="UDPipe grammar analysis",
            area="Grammar",
            script="sentence_udpipe.py",
            cadence="parser pass",
            done=count_if_table(
                "sentence_udpipe_analyses",
                "SELECT COUNT(*) FROM sentence_udpipe_analyses",
            ),
            total=sentence_total_target,
            details=format_status_counts(status_counts("sentence_udpipe_runs")),
        )
    if has_tables("sentence_trankit_analyses"):
        add_task(
            name="Trankit grammar analysis",
            area="Grammar",
            script="sentence_trankit.py",
            cadence="parser pass",
            done=count_if_table(
                "sentence_trankit_analyses",
                "SELECT COUNT(*) FROM sentence_trankit_analyses",
            ),
            total=sentence_total_target,
            details=format_status_counts(status_counts("sentence_trankit_runs")),
        )

    if has_tables("sentence_lemmatizations"):
        add_task(
            name="Sentence lemmatization",
            area="Lemmas",
            script="sentence_lemmatizer.py",
            cadence="auxiliary LLM pass",
            done=count_if_table(
                "sentence_lemmatizations",
                "SELECT COUNT(*) FROM sentence_lemmatizations",
            ),
            total=sentence_total_target,
            details=format_status_counts(status_counts("sentence_lemmatization_runs")),
        )
    if has_tables("greek_word_lemmas"):
        word_status = format_status_counts(status_counts("word_lemmatization_runs"))
        add_task(
            name="Word-form lemmatization",
            area="Lemmas",
            script="word_lemmatizer.py",
            cadence="Batch API/ad hoc",
            done=count_if_table("greek_word_lemmas", "SELECT COUNT(*) FROM greek_word_lemmas"),
            total=None,
            status="Tracking",
            details=word_status or "Distinct Greek surface forms with lemma choices.",
        )

    people_status = format_status_counts(
        status_counts(
            "section_people_runs",
            "prompt_version = %s",
            (SECTION_PEOPLE_PROMPT_VERSION,),
        )
    )
    people_mentions = count_if_table(
        "section_people_mentions",
        "SELECT COUNT(*) FROM section_people_mentions WHERE prompt_version = %s",
        (SECTION_PEOPLE_PROMPT_VERSION,),
    )
    people_done = None
    if has_tables("section_people_batch_items", "section_people_runs"):
        people_done = fetch_scalar(
            """
            SELECT COUNT(DISTINCT bi.passage_id)
            FROM section_people_batch_items bi
            JOIN section_people_runs r ON r.run_id = bi.run_id
            WHERE bi.status = 'completed'
              AND r.prompt_version = %s
              AND r.status IN ('completed', 'completed_with_failures')
            """,
            (SECTION_PEOPLE_PROMPT_VERSION,),
        )
    add_task(
        name="People/name analysis",
        area="Names and gender",
        script="section_people_daily.sh",
        batch_size=max(1, 100_000 // 2_500),
        cadence="Batch API, ~40 sections/day",
        done=people_done,
        total=total_passages,
        details=(
            f"{people_status}; {int(people_mentions or 0):,} mention rows"
            if people_status or people_mentions
            else "Named and anonymous person mentions by sentence."
        ),
    )

    # Token usage by source
    token_sources = [
        ("Passage analysis", "content_queries"),
        ("Noun extraction", "noun_extraction_status"),
        ("Translation", "translations"),
        ("Summarisation", "passage_summaries"),
        ("Phrase translation", "phrase_translations"),
        ("Sentence tagging", "sentence_tagging_runs"),
        ("LLM grammar", "sentence_llm_grammar_runs"),
        ("Sentence lemmatization", "sentence_lemmatization_runs"),
        ("Word lemmatization", "word_lemmatization_runs"),
        ("Section people extraction", "section_people_runs"),
    ]
    token_usage = []
    for label, table in token_sources:
        if not table_exists(conn, table):
            continue
        cursor.execute(
            f"""
            SELECT COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0)
            FROM {table}
            """
        )
        inp, out = cursor.fetchone()
        token_usage.append(
            {
                "name": label,
                "input_tokens": int(inp or 0),
                "output_tokens": int(out or 0),
                "total_tokens": int((inp or 0) + (out or 0)),
            }
        )

    return {"tasks": tasks, "token_usage": token_usage}


def add_phrase_translations(df: pd.DataFrame, conn, client: Optional[OpenAI] = None,
                           model: str = "gpt-5") -> pd.DataFrame:
    """Add English translations to a predictor dataframe.

    Args:
        df: Dataframe with a 'phrase' column containing Greek phrases
        conn: Database connection
        client: Optional OpenAI client for fetching new translations
        model: Model to use for new translations

    Returns:
        Dataframe with added 'english_translation' and 'is_proper_noun' columns
    """
    import sys
    import os
    # Add parent directory to path to import phrase_translator
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from phrase_translator import get_translations_for_phrases

    if 'phrase' not in df.columns:
        raise ValueError("Dataframe must have a 'phrase' column")

    # Get unique phrases
    phrases = df['phrase'].unique().tolist()

    # Get translations (returns dict of phrase -> (translation, is_proper_noun))
    translations = get_translations_for_phrases(conn, client, model, phrases)

    # Add columns
    df = df.copy()
    df['english_translation'] = df['phrase'].map(lambda p: translations.get(p, ('', False))[0])
    df['is_proper_noun'] = df['phrase'].map(lambda p: translations.get(p, ('', False))[1])

    # Fill any missing values
    df['english_translation'] = df['english_translation'].fillna('')
    df['is_proper_noun'] = df['is_proper_noun'].fillna(False)

    return df
