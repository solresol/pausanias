import unittest

from stylometry_chunks import (
    Chunk,
    SentenceRecord,
    build_nonoverlapping_chunks,
    build_rolling_chunks,
    chunk_row,
    default_chunk_set,
    in_messenian_span,
    passage_key,
)


def sentence(passage_id: str, number: int, tokens: int) -> SentenceRecord:
    return SentenceRecord(
        passage_id=passage_id,
        sentence_number=number,
        token_count=tokens,
        book=passage_key(passage_id)[0],
        in_messenian=in_messenian_span(passage_id),
    )


class StylometryChunkTests(unittest.TestCase):
    def test_passage_key_orders_numerically_not_lexically(self):
        self.assertLess(passage_key("4.9.2"), passage_key("4.10.1"))
        self.assertLess(passage_key("9.9.9"), passage_key("10.1.1"))

    def test_messenian_span_bounds_are_inclusive(self):
        self.assertTrue(in_messenian_span("4.4.1"))
        self.assertTrue(in_messenian_span("4.27.1"))
        self.assertTrue(in_messenian_span("4.10.5"))
        self.assertFalse(in_messenian_span("4.3.9"))
        self.assertFalse(in_messenian_span("4.27.2"))
        self.assertFalse(in_messenian_span("5.4.1"))

    def test_nonoverlapping_chunks_respect_size_and_merge_small_tail(self):
        sentences = [sentence("1.1.1", index, 40) for index in range(1, 11)]
        chunks = build_nonoverlapping_chunks(sentences, chunk_size=100)
        # 10 x 40 tokens -> chunks of 120/120/120, tail of 40 merged into last.
        self.assertEqual(len(chunks), 3)
        self.assertEqual([chunk.token_count for chunk in chunks], [120, 120, 160])
        self.assertEqual(
            sum(len(chunk.sentences) for chunk in chunks), len(sentences)
        )

    def test_nonoverlapping_chunks_keep_large_tail(self):
        sentences = [sentence("1.1.1", index, 40) for index in range(1, 8)]
        chunks = build_nonoverlapping_chunks(sentences, chunk_size=100)
        # 280 tokens -> 120, 120, then a 40-token tail merges; 7*40=280.
        self.assertEqual([chunk.token_count for chunk in chunks], [120, 160])

    def test_rolling_chunks_overlap_and_drop_partial_tail(self):
        sentences = [sentence("1.1.1", index, 50) for index in range(1, 21)]
        chunks = build_rolling_chunks(sentences, chunk_size=200, step=100)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertGreaterEqual(chunk.token_count, 200)
        first = chunks[0].sentences[0].sentence_number
        second = chunks[1].sentences[0].sentence_number
        self.assertEqual(second - first, 2)  # 100-token step over 50-token sentences

    def test_chunk_row_flags_messenian_and_boundary(self):
        chunk = Chunk(
            chunk_index=0,
            sentences=[
                sentence("4.3.9", 1, 50),
                sentence("4.4.1", 1, 150),
            ],
        )
        row = chunk_row(
            chunk,
            chunk_set="test",
            tokenizer_version="test-v1",
            timestamp="now",
        )
        self.assertTrue(row[10])  # is_messenian_wars
        self.assertAlmostEqual(row[11], 0.75)  # overlap fraction
        self.assertTrue(row[12])  # is_book4
        self.assertFalse(row[13])  # is_book8
        self.assertFalse(row[14])  # is_control
        self.assertTrue(row[15])  # boundary: partial Messenian overlap

        control = Chunk(chunk_index=1, sentences=[sentence("2.1.1", 1, 100)])
        control_row = chunk_row(
            control,
            chunk_set="test",
            tokenizer_version="test-v1",
            timestamp="now",
        )
        self.assertFalse(control_row[10])
        self.assertTrue(control_row[14])
        self.assertFalse(control_row[15])

    def test_default_chunk_set_names(self):
        self.assertEqual(default_chunk_set(5000, 0), "pausanias_5000_nonoverlap_v1")
        self.assertEqual(default_chunk_set(5000, 500), "pausanias_5000_roll500_v1")


if __name__ == "__main__":
    unittest.main()
