import unittest

from place_state_candidate_importer import regex_candidates_for_sentence


class PlaceStateCandidateImporterTests(unittest.TestCase):
    def test_regex_candidates_find_ruined_houses(self):
        rows = regex_candidates_for_sentence(
            source_version="test-v1",
            passage_id="1.38.9",
            sentence_number=3,
            greek_sentence="ἦν δὲ καὶ οἰκιῶν ἐρείπια",
            english_sentence="As for Eleutherae, some of the city wall still remains, as well as ruins of houses.",
            created_at="now",
        )

        categories = {row["category"] for row in rows}
        self.assertIn("ruin", categories)
        self.assertIn("greek_place_state_marker", categories)
        self.assertTrue(all(row["source_version"] == "test-v1" for row in rows))


if __name__ == "__main__":
    unittest.main()
