import unittest

from link_manto_places import (
    candidate_links,
    curated_link_rows,
    name_variants,
    normalize_name,
    transliteration_key,
    transliteration_keys,
)


def manto_entity(manto_id: str, label: str, pleiades_id: str = "") -> dict:
    norm_variants = name_variants(
        label,
        include_location_container=False,
        include_generic_head=False,
    )
    return {
        "manto_id": manto_id,
        "label": label,
        "entity_kind": "place",
        "pleiades_id": pleiades_id,
        "norm_label": normalize_name(label),
        "norm_variants": norm_variants,
        "translit_variants": transliteration_keys(norm_variants),
    }


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

    def test_transliteration_keys_bridge_latin_and_greek_romanizations(self):
        pairs = [
            ("Amyclae", "Amyklai"),
            ("Aegae", "Aigai"),
            ("Bassai", "Bassae"),
            ("Rhium", "Rion"),
            ("Asopus", "Asopos"),
            ("Alipherae", "Aliphera"),
        ]
        for latin, greek in pairs:
            latin_keys = transliteration_keys(name_variants(latin))
            greek_keys = transliteration_keys(name_variants(greek))
            self.assertTrue(
                latin_keys & greek_keys,
                f"{latin} and {greek} should share a transliteration key",
            )
        self.assertEqual(transliteration_key("Rhium"), "rion")
        self.assertEqual(transliteration_key(""), "")

    def test_candidate_links_fall_back_to_transliteration_matches(self):
        candidates = candidate_links(
            {
                "reference_form": "Ἀμύκλαι",
                "english_transcription": "Amyclae",
                "pleiades_id": "",
            },
            [manto_entity("9001", "🌍 Amyklai (Lakonia)")],
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["match_method"], "transliteration")
        self.assertEqual(candidates[0]["confidence"], "medium")

    def test_curated_link_rows_skip_rejected_covered_and_stale_links(self):
        entities = [manto_entity("9001", "🌍 Amyklai (Lakonia)")]
        curated = [
            {
                "place_name": "ancient Amyclae",
                "manto_id": "9001",
                "manto_label": "",
                "source": "llm",
                "rationale": "LLM matched the Laconian town.",
                "reviewed": False,
                "rejected": False,
            },
            {
                "place_name": "Arabian desert",
                "manto_id": "",
                "manto_label": "",
                "source": "llm",
                "rationale": "No MANTO place candidate.",
                "reviewed": False,
                "rejected": True,
            },
            {
                "place_name": "Lost Town",
                "manto_id": "gone-in-this-release",
                "manto_label": "🌍 Lost Town",
                "source": "manual",
                "rationale": "",
                "reviewed": True,
                "rejected": False,
            },
            {
                "place_name": "Amyklai",
                "manto_id": "9001",
                "manto_label": "",
                "source": "manual",
                "rationale": "",
                "reviewed": True,
                "rejected": False,
            },
        ]
        rows = curated_link_rows(
            curated,
            entities,
            release_id=1,
            existing_keys={("Amyklai", "9001")},
            timestamp="now",
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row[1], "ancient Amyclae")
        self.assertEqual(row[6], "9001")
        self.assertEqual(row[8], "curated-llm")
        self.assertEqual(row[9], "medium")


if __name__ == "__main__":
    unittest.main()
