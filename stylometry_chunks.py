#!/usr/bin/env python
"""Build stylometry chunk inventories over the Greek sentence corpus.

Phase 1 of documentation/morphosyntactic_stylometry_plan.md: read Greek
sentences in passage order, tokenize with the shared Greek token regex, and
emit chunk inventories — non-overlapping chunks for statistical tables and
rolling windows for visualization — with Messenian Wars (Pausanias
4.4.1-4.27.1), Book 4, Book 8, and boundary flags.
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from lemma_text import tokenize_greek
from pausanias_db import add_database_argument, connect, initialize_schema


TOKENIZER_VERSION = "lemma-text-greek-v1"
MESSENIAN_START = (4, 4, 1)
MESSENIAN_END = (4, 27, 1)


@dataclass(frozen=True)
class SentenceRecord:
    passage_id: str
    sentence_number: int
    token_count: int
    book: int
    in_messenian: bool


@dataclass
class Chunk:
    chunk_index: int
    sentences: list[SentenceRecord]

    @property
    def chunk_id(self) -> str:
        return f"{self.chunk_index:04d}"

    @property
    def token_count(self) -> int:
        return sum(sentence.token_count for sentence in self.sentences)

    @property
    def messenian_token_count(self) -> int:
        return sum(
            sentence.token_count for sentence in self.sentences if sentence.in_messenian
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_database_argument(parser)
    parser.add_argument("--chunk-size", type=int, default=5000)
    parser.add_argument(
        "--step",
        type=int,
        default=0,
        help="Rolling-window step in tokens; 0 builds non-overlapping chunks.",
    )
    parser.add_argument(
        "--chunk-set",
        default=None,
        help="Chunk-set name; defaults to pausanias_<size>_nonoverlap_v1 or pausanias_<size>_roll<step>_v1.",
    )
    parser.add_argument("--tokenizer-version", default=TOKENIZER_VERSION)
    parser.add_argument("--csv-dir", default="output/stylometry")
    return parser.parse_args()


def default_chunk_set(chunk_size: int, step: int) -> str:
    if step > 0:
        return f"pausanias_{chunk_size}_roll{step}_v1"
    return f"pausanias_{chunk_size}_nonoverlap_v1"


def passage_key(passage_id: str) -> tuple[int, ...]:
    return tuple(int(part) for part in str(passage_id).split("."))


def in_messenian_span(passage_id: str) -> bool:
    return MESSENIAN_START <= passage_key(passage_id) <= MESSENIAN_END


def load_sentences(conn) -> list[SentenceRecord]:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT passage_id, sentence_number, sentence FROM greek_sentences"
        )
        rows = cursor.fetchall()
    records = []
    for passage_id, sentence_number, sentence in rows:
        token_count = len(tokenize_greek(sentence or ""))
        if token_count == 0:
            continue
        records.append(
            SentenceRecord(
                passage_id=str(passage_id),
                sentence_number=int(sentence_number),
                token_count=token_count,
                book=passage_key(passage_id)[0],
                in_messenian=in_messenian_span(passage_id),
            )
        )
    records.sort(key=lambda record: (passage_key(record.passage_id), record.sentence_number))
    return records


def build_nonoverlapping_chunks(
    sentences: list[SentenceRecord],
    *,
    chunk_size: int,
) -> list[Chunk]:
    """Greedy sentence-aligned chunks of about chunk_size tokens.

    A final fragment shorter than half a chunk is merged into the previous
    chunk rather than kept as an unbalanced observation.
    """
    chunks: list[Chunk] = []
    current: list[SentenceRecord] = []
    current_tokens = 0
    for sentence in sentences:
        current.append(sentence)
        current_tokens += sentence.token_count
        if current_tokens >= chunk_size:
            chunks.append(Chunk(chunk_index=len(chunks), sentences=current))
            current = []
            current_tokens = 0
    if current:
        if chunks and current_tokens < chunk_size // 2:
            chunks[-1].sentences.extend(current)
        else:
            chunks.append(Chunk(chunk_index=len(chunks), sentences=current))
    return chunks


def build_rolling_chunks(
    sentences: list[SentenceRecord],
    *,
    chunk_size: int,
    step: int,
) -> list[Chunk]:
    """Sentence-aligned rolling windows of about chunk_size tokens every ~step tokens."""
    starts: list[int] = []
    cumulative = 0
    next_start = 0
    for index, sentence in enumerate(sentences):
        if cumulative >= next_start:
            starts.append(index)
            next_start += step
        cumulative += sentence.token_count

    chunks: list[Chunk] = []
    seen_starts: set[int] = set()
    for start in starts:
        if start in seen_starts:
            continue
        seen_starts.add(start)
        window: list[SentenceRecord] = []
        window_tokens = 0
        for sentence in sentences[start:]:
            window.append(sentence)
            window_tokens += sentence.token_count
            if window_tokens >= chunk_size:
                break
        if window_tokens < chunk_size:
            # The corpus tail cannot fill a full window; stop emitting windows.
            break
        chunks.append(Chunk(chunk_index=len(chunks), sentences=window))
    return chunks


def chunk_row(
    chunk: Chunk,
    *,
    chunk_set: str,
    tokenizer_version: str,
    timestamp: str,
) -> tuple:
    books = [sentence.book for sentence in chunk.sentences]
    token_count = chunk.token_count
    messenian_tokens = chunk.messenian_token_count
    overlap_fraction = messenian_tokens / token_count if token_count else 0.0
    is_book4 = any(book == 4 for book in books)
    is_book8 = any(book == 8 for book in books)
    return (
        chunk_set,
        chunk.chunk_id,
        chunk.chunk_index,
        tokenizer_version,
        chunk.sentences[0].passage_id,
        chunk.sentences[-1].passage_id,
        books[0],
        books[-1],
        token_count,
        len(chunk.sentences),
        messenian_tokens > 0,
        float(overlap_fraction),
        is_book4,
        is_book8,
        not (is_book4 or is_book8),
        books[0] != books[-1] or 0.0 < overlap_fraction < 1.0,
        timestamp,
    )


def save_chunks(
    conn,
    *,
    chunk_set: str,
    tokenizer_version: str,
    chunks: list[Chunk],
) -> list[tuple]:
    timestamp = now_iso()
    rows = [
        chunk_row(
            chunk,
            chunk_set=chunk_set,
            tokenizer_version=tokenizer_version,
            timestamp=timestamp,
        )
        for chunk in chunks
    ]
    sentence_rows = [
        (
            chunk_set,
            chunk.chunk_id,
            sentence.passage_id,
            sentence.sentence_number,
            sentence.token_count,
        )
        for chunk in chunks
        for sentence in chunk.sentences
    ]
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM stylometry_chunks WHERE chunk_set = %s",
            (chunk_set,),
        )
        cursor.executemany(
            """
            INSERT INTO stylometry_chunks (
                chunk_set, chunk_id, chunk_index, tokenizer_version,
                passage_start, passage_end, book_start, book_end,
                token_count, sentence_count, is_messenian_wars,
                overlap_fraction_messenian_wars, is_book4, is_book8,
                is_control, is_boundary_chunk, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )
        cursor.executemany(
            """
            INSERT INTO stylometry_chunk_sentences (
                chunk_set, chunk_id, passage_id, sentence_number, token_count
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            sentence_rows,
        )
    conn.commit()
    return rows


CSV_COLUMNS = [
    "chunk_set",
    "chunk_id",
    "chunk_index",
    "tokenizer_version",
    "passage_start",
    "passage_end",
    "book_start",
    "book_end",
    "token_count",
    "sentence_count",
    "is_messenian_wars",
    "overlap_fraction_messenian_wars",
    "is_book4",
    "is_book8",
    "is_control",
    "is_boundary_chunk",
    "created_at",
]


def write_csv(rows: list[tuple], *, chunk_set: str, csv_dir: str) -> str:
    os.makedirs(csv_dir, exist_ok=True)
    path = os.path.join(csv_dir, f"chunks_{chunk_set}.csv")
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_COLUMNS)
        writer.writerows(rows)
    return path


def main() -> None:
    args = parse_arguments()
    chunk_set = args.chunk_set or default_chunk_set(args.chunk_size, args.step)
    with connect(args.database_url) as conn:
        initialize_schema(conn)
        print("Loading and tokenizing Greek sentences...", flush=True)
        sentences = load_sentences(conn)
        total_tokens = sum(sentence.token_count for sentence in sentences)
        if args.step > 0:
            chunks = build_rolling_chunks(
                sentences, chunk_size=args.chunk_size, step=args.step
            )
        else:
            chunks = build_nonoverlapping_chunks(sentences, chunk_size=args.chunk_size)
        rows = save_chunks(
            conn,
            chunk_set=chunk_set,
            tokenizer_version=args.tokenizer_version,
            chunks=chunks,
        )
    path = write_csv(rows, chunk_set=chunk_set, csv_dir=args.csv_dir)
    messenian = sum(1 for row in rows if row[10])
    print(
        f"Saved {len(rows)} chunks to chunk set {chunk_set} "
        f"({total_tokens:,} tokens over {len(sentences):,} sentences; "
        f"{messenian} chunks overlap the Messenian Wars span). CSV: {path}"
    )


if __name__ == "__main__":
    main()
