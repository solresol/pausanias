import unittest

from link_manto_places import candidate_links, name_variants, normalize_name


class LinkMantoPlacesTests(unittest.TestCase):
    def test_name_variants_strip_parentheticals_and_alt_names(self):
        variants = name_variants("🌍 Argion (alt. Mycenae)")

        self.assertIn(normalize_name("Argion"), variants)
        self.assertIn(normalize_name("Mycenae"), variants)

    def test_name_variants_do_not_treat_region_parentheticals_as_aliases(self):
        variants = name_variants("🌍 Asea (Arcadia)")

        self.assertIn(normalize_name("Asea"), variants)
        self.assertNotIn(normalize_name("Arcadia"), variants)

        variants = name_variants(
            "the island (Rhodes)",
            include_parenthetical_content=True,
        )

        self.assertIn(normalize_name("Rhodes"), variants)
        self.assertNotIn(normalize_name("island"), variants)

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

    def test_manto_entity_variants_do_not_offer_container_places(self):
        variants = name_variants(
            "🌍 the Sanctuary of Apollo at Athens",
            include_location_container=False,
            include_generic_head=False,
        )

        self.assertIn(normalize_name("the Sanctuary of Apollo at Athens"), variants)
        self.assertNotIn(normalize_name("Athens"), variants)

    def test_plain_place_does_not_match_manto_subplaces_at_that_place(self):
        candidates = candidate_links(
            {
                "reference_form": "Ἀθῆναι",
                "english_transcription": "Athens",
                "pleiades_id": "",
            },
            [
                {
                    "manto_id": "8188815",
                    "label": "🌍 Athens (Attica)",
                    "entity_kind": "place",
                    "pleiades_id": "579885",
                    "norm_label": normalize_name("🌍 Athens (Attica)"),
                    "norm_variants": name_variants(
                        "🌍 Athens (Attica)",
                        include_location_container=False,
                        include_generic_head=False,
                    ),
                },
                {
                    "manto_id": "10157580",
                    "label": "🌍 the Sanctuary of Apollo at Athens",
                    "entity_kind": "place",
                    "pleiades_id": "",
                    "norm_label": normalize_name("🌍 the Sanctuary of Apollo at Athens"),
                    "norm_variants": name_variants(
                        "🌍 the Sanctuary of Apollo at Athens",
                        include_location_container=False,
                        include_generic_head=False,
                    ),
                },
            ],
        )

        self.assertEqual([candidate["manto_id"] for candidate in candidates], ["8188815"])


if __name__ == "__main__":
    unittest.main()
