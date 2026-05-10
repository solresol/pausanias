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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
    r2_score,
)
from sklearn.model_selection import train_test_split

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
GRETA_SENTENCE_PROMPT_VERSION = "greta-myth-history-other-no-scepticism-v1"
RHETORIC_MARKER_WORDS = [
    "λέγω",
    "λέγεται",
    "λέγουσι",
    "λέγουσιν",
    "λέγει",
    "λέγειν",
    "φημί",
    "φησί",
    "φησίν",
    "φασί",
    "φασίν",
    "φάσι",
    "φάσις",
    "φάσκω",
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


def _fit_greta_sentence_variant(
    df,
    *,
    label,
    token_source,
    include_books_4_8,
    remove_rhetoric_markers,
    proper_stopwords,
    lemma_lookup,
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
        "metrics": None,
        "available": False,
        "message": "",
    }

    if len(variant_df) < 20 or min_class_count < 5:
        result["message"] = "Not enough mythic and historical sentences are tagged yet."
        return result

    extra_stopwords = RHETORIC_MARKER_WORDS if remove_rhetoric_markers else []
    if token_source == "lemma":
        if not lemma_lookup:
            result["message"] = "No cached word-level lemmas are available."
            return result
        texts, lemma_stats = build_lemma_texts(variant_df["sentence"], lemma_lookup)
        stopwords = expand_stopwords_with_lemma_forms(
            proper_stopwords + extra_stopwords,
            lemma_lookup,
        )
        result["lemma_stats"] = {
            "token_count": lemma_stats.token_count,
            "lemmatized_token_count": lemma_stats.lemmatized_token_count,
            "missing_token_count": lemma_stats.missing_token_count,
            "unique_missing_count": lemma_stats.unique_missing_count,
        }
    else:
        texts = variant_df["sentence"].tolist()
        stopwords = normalize_stopwords(proper_stopwords + extra_stopwords)

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        min_df=min_df,
        ngram_range=(1, 2),
        token_pattern=TFIDF_TOKEN_PATTERN,
        preprocessor=casefold_preprocessor,
        stop_words=stopwords,
    )
    model = LogisticRegression(
        C=1.0,
        max_iter=1000,
        class_weight="balanced",
        random_state=42,
    )

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

    precision, recall, f1, support = precision_recall_fscore_support(
        y_test,
        y_pred,
        labels=[0, 1],
        zero_division=0,
    )
    actual_0_pred_0, actual_0_pred_1, actual_1_pred_0, actual_1_pred_1 = confusion_matrix(
        y_test,
        y_pred,
        labels=[0, 1],
    ).ravel()

    result.update(
        {
            "available": True,
            "feature_count": int(len(feature_names)),
            "predictors": pd.concat([top_negative, top_positive]).reset_index(drop=True),
            "metrics": {
                "accuracy": float(accuracy_score(y_test, y_pred)),
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
            },
        }
    )
    return result


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
                        "greta-sentence",
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
        "bucket_counts": bucket_counts,
        "book_counts": book_counts,
        "tagged_sentence_count": int(len(annotations)),
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
    else:
        class_subgraphs = _class_subgraph_analysis(sentence_nouns)
        bridge_nouns = _bridge_noun_rows(sentence_nouns)

    return {
        "available": True,
        "message": "",
        "sentence_matching": sentence_stats,
        "class_subgraphs": class_subgraphs,
        "bridge_nouns": bridge_nouns,
        "book_drift": _book_drift_analysis(passage_nouns),
        "bipartite": _bipartite_analysis(passage_nouns),
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
        return pd.DataFrame(), pd.DataFrame(), 0, 0.0

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
        int(len(feature_names)),
        float(r2_score(residuals, predicted_residuals)),
    )


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
        "english_longer_predictors": pd.DataFrame(),
        "english_shorter_predictors": pd.DataFrame(),
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

    greek_vocabulary_column = "lemma_passage" if "lemma_passage" in df.columns else "passage"
    try:
        (
            longer_predictors,
            shorter_predictors,
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
        english_feature_count = 0
        english_residual_r2 = 0.0

    if greek_feature_count == 0:
        result = empty_result.copy()
        result["message"] = "No repeated Greek vocabulary was available for the residual model."
        return result

    longest_passages = df.sort_values("length_residual", ascending=False).head(20)
    shortest_passages = df.sort_values("length_residual", ascending=True).head(20)

    return {
        "available": True,
        "message": "",
        "metrics": {
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
        },
        "longer_predictors": longer_predictors.reset_index(drop=True),
        "shorter_predictors": shorter_predictors.reset_index(drop=True),
        "english_longer_predictors": english_longer_predictors.reset_index(drop=True),
        "english_shorter_predictors": english_shorter_predictors.reset_index(drop=True),
        "longest_passages": longest_passages.reset_index(drop=True),
        "shortest_passages": shortest_passages.reset_index(drop=True),
    }


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

    # Total passages
    cursor.execute("SELECT COUNT(*) FROM passages")
    total_passages = cursor.fetchone()[0]

    # Sentences: count and passages that have been split
    cursor.execute("SELECT COUNT(*) FROM greek_sentences")
    total_sentences = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT passage_id) FROM greek_sentences")
    passages_with_sentences = cursor.fetchone()[0]

    # Estimate total sentences based on average per passage
    if passages_with_sentences > 0:
        avg_sentences_per_passage = total_sentences / passages_with_sentences
        estimated_total_sentences = int(total_passages * avg_sentences_per_passage)
    else:
        estimated_total_sentences = total_passages  # fallback estimate

    # Total unique proper nouns
    cursor.execute("SELECT COUNT(DISTINCT reference_form || '|' || entity_type) FROM proper_nouns")
    total_nouns = cursor.fetchone()[0]

    # Task progress
    tasks = []

    # 1. Mythic/skeptic analysis
    cursor.execute("SELECT COUNT(*) FROM passages WHERE references_mythic_era IS NOT NULL")
    done = cursor.fetchone()[0]
    tasks.append({"name": "Mythic/skeptic analysis", "script": "mythic_sceptic_analyser.py",
                  "batch_size": 50, "total": total_passages, "done": done})

    # 2. Proper noun extraction
    cursor.execute("SELECT COUNT(*) FROM noun_extraction_status")
    done = cursor.fetchone()[0]
    tasks.append({"name": "Proper noun extraction", "script": "extract_proper_nouns.py",
                  "batch_size": 50, "total": total_passages, "done": done})

    # 3. Wikidata linking
    cursor.execute("SELECT COUNT(*) FROM wikidata_links")
    done = cursor.fetchone()[0]
    tasks.append({"name": "Wikidata linking", "script": "link_wikidata.py",
                  "batch_size": 100, "total": total_nouns, "done": done})

    # 4. Translation
    cursor.execute("SELECT COUNT(*) FROM translations")
    done = cursor.fetchone()[0]
    tasks.append({"name": "Translation", "script": "translate_pausanias.py",
                  "batch_size": 50, "total": total_passages, "done": done})

    # 5. Sentence splitting
    tasks.append({"name": "Sentence splitting", "script": "split_sentences.py",
                  "batch_size": 20, "total": total_passages, "done": passages_with_sentences})

    # 6. Summarisation
    cursor.execute("SELECT COUNT(*) FROM passage_summaries")
    done = cursor.fetchone()[0]
    tasks.append({"name": "Passage summarisation", "script": "summarise_passages.py",
                  "batch_size": 50, "total": total_passages, "done": done})

    # 7. Sentence classification (total is estimated based on avg sentences per passage)
    cursor.execute("SELECT COUNT(*) FROM greek_sentences WHERE references_mythic_era IS NOT NULL")
    done = cursor.fetchone()[0]
    tasks.append({"name": "Sentence classification", "script": "sentence_mythic_sceptic_analyser.py",
                  "batch_size": 25, "total": estimated_total_sentences, "done": done})

    # Calculate percentages and estimated completion
    for task in tasks:
        task["percent"] = round(100 * task["done"] / task["total"], 1) if task["total"] > 0 else 0
        remaining = task["total"] - task["done"]
        if remaining <= 0:
            task["est_completion"] = "Done"
        else:
            days_needed = ceil(remaining / task["batch_size"])
            est_date = today + timedelta(days=days_needed)
            task["est_completion"] = est_date.isoformat()

    # Token usage by source
    token_sources = [
        ("Passage analysis", "content_queries"),
        ("Noun extraction", "noun_extraction_status"),
        ("Translation", "translations"),
        ("Summarisation", "passage_summaries"),
        ("Phrase translation", "phrase_translations"),
    ]
    token_usage = []
    for label, table in token_sources:
        try:
            cursor.execute(f"SELECT COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0) FROM {table}")
            inp, out = cursor.fetchone()
            token_usage.append({"name": label, "input_tokens": inp, "output_tokens": out,
                                "total_tokens": inp + out})
        except Exception:
            pass

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
