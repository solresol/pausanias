"""Database operations and data retrieval functions."""

import pandas as pd
import sqlite3
from typing import Optional
from openai import OpenAI

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
    SELECT phrase, coefficient, is_mythic, mythic_count, non_mythic_count,
           p_value, q_value
    FROM mythicness_predictors
    ORDER BY coefficient DESC
    """

    df = pd.read_sql_query(query, conn)
    return df

def get_skepticism_predictors(conn):
    """Get words/phrases that predict skepticism/non-skepticism."""
    query = """
    SELECT phrase, coefficient, is_skeptical, skeptical_count,
           non_skeptical_count, p_value, q_value
    FROM skepticism_predictors
    ORDER BY coefficient DESC
    """

    df = pd.read_sql_query(query, conn)
    return df


def get_sentence_mythicness_predictors(conn):
    """Get sentence-level words/phrases that predict mythicness/historicity."""
    query = """
    SELECT phrase, coefficient, is_mythic, mythic_count, non_mythic_count,
           p_value, q_value
    FROM sentence_mythicness_predictors
    ORDER BY coefficient DESC
    """

    df = pd.read_sql_query(query, conn)
    return df


def get_sentence_skepticism_predictors(conn):
    """Get sentence-level words/phrases that predict skepticism/non-skepticism."""
    query = """
    SELECT phrase, coefficient, is_skeptical, skeptical_count,
           non_skeptical_count, p_value, q_value
    FROM sentence_skepticism_predictors
    ORDER BY coefficient DESC
    """

    df = pd.read_sql_query(query, conn)
    return df


def get_all_sentences(conn):
    """Retrieve all Greek and English sentences with analysis flags."""
    query = """
    SELECT passage_id, sentence_number, sentence, english_sentence,
           references_mythic_era, expresses_scepticism
    FROM greek_sentences
    ORDER BY passage_id, sentence_number
    """

    df = pd.read_sql_query(query, conn)
    return df


def get_passage_mythicness_metrics(conn):
    """Get classification metrics for passage-level mythicness prediction."""
    query = """
    SELECT accuracy, precision_0, recall_0, f1_0, support_0,
           precision_1, recall_1, f1_1, support_1, timestamp
    FROM passage_mythicness_metrics
    ORDER BY id DESC
    LIMIT 1
    """
    df = pd.read_sql_query(query, conn)
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def get_passage_skepticism_metrics(conn):
    """Get classification metrics for passage-level skepticism prediction."""
    query = """
    SELECT accuracy, precision_0, recall_0, f1_0, support_0,
           precision_1, recall_1, f1_1, support_1, timestamp
    FROM passage_skepticism_metrics
    ORDER BY id DESC
    LIMIT 1
    """
    df = pd.read_sql_query(query, conn)
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def get_sentence_mythicness_metrics(conn):
    """Get classification metrics for sentence-level mythicness prediction."""
    query = """
    SELECT accuracy, precision_0, recall_0, f1_0, support_0,
           precision_1, recall_1, f1_1, support_1, timestamp
    FROM sentence_mythicness_metrics
    ORDER BY id DESC
    LIMIT 1
    """
    df = pd.read_sql_query(query, conn)
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def get_sentence_skepticism_metrics(conn):
    """Get classification metrics for sentence-level skepticism prediction."""
    query = """
    SELECT accuracy, precision_0, recall_0, f1_0, support_0,
           precision_1, recall_1, f1_1, support_1, timestamp
    FROM sentence_skepticism_metrics
    ORDER BY id DESC
    LIMIT 1
    """
    df = pd.read_sql_query(query, conn)
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()


def get_map_data(conn):
    """Get place coordinates with their associated passage IDs for the map."""
    cursor = conn.cursor()

    # Check if the place_coordinates table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='place_coordinates'
    """)
    if not cursor.fetchone():
        return []

    # Get all places with coordinates
    cursor.execute("""
        SELECT pc.wikidata_qid, pc.reference_form, pc.english_transcription,
               pc.latitude, pc.longitude, pc.pleiades_id
        FROM place_coordinates pc
        WHERE pc.latitude IS NOT NULL AND pc.longitude IS NOT NULL
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
            WHERE reference_form = ? AND entity_type = 'place'
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
    # Check if wikidata_links table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='wikidata_links'
    """)
    has_wikidata = cursor.fetchone() is not None

    if has_wikidata:
        cursor.execute("""
            SELECT pn.passage_id, pn.reference_form, pn.english_transcription,
                   pn.entity_type, w.wikidata_qid, pc.latitude, pc.longitude,
                   pc.pleiades_id
            FROM proper_nouns pn
            LEFT JOIN wikidata_links w
                ON pn.reference_form = w.reference_form
                AND pn.entity_type = w.entity_type
            LEFT JOIN place_coordinates pc
                ON w.wikidata_qid = pc.wikidata_qid
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

    # Check if the table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='passage_summaries'
    """)
    if not cursor.fetchone():
        return {}

    cursor.execute("SELECT passage_id, summary FROM passage_summaries")
    return dict(cursor.fetchall())


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
