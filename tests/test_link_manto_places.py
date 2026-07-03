import unittest

from link_manto_places import candidate_links, name_variants, normalize_name


class LinkMantoPlacesTests(unittest.TestCase):
    def test_name_variants_strip_parentheticals_and_alt_names(self):
        variants = name_variants("🌍 Argion (alt. Mycenae)")

        self.assertIn(normalize_name("Argion"), variants)
        self.assertIn(normalize_name("Mycenae"), variants)

    def test_name_variants_add_cautious_head_place_variants(self):
        variants = name_variants("ancient Mantinea")

        self.assertIn(normalize_name("Mantinea"), variants)

        variants = name_variants("Asea acropolis hill")

        self.assertIn(normalize_name("Asea"), variants)

    def test_candidate_links_match_parenthetical_place_labels(self):
        candidates = candidate_links(
            {
                "reference_form": "Μυκῆναι",
                "english_transcription": "Mycenae",
                "pleiades_id": "",
            },
            [
                {
                    "manto_id": "8194382",
                    "label": "🌍 Mycenae (Argolid)",
                    "entity_kind": "place",
                    "pleiades_id": "570491",
                    "norm_label": normalize_name("🌍 Mycenae (Argolid)"),
                    "norm_variants": name_variants("🌍 Mycenae (Argolid)"),
                }
            ],
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["match_method"], "exact_normalized_name")


if __name__ == "__main__":
    unittest.main()
