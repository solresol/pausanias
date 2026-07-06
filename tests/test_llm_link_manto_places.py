import unittest

from link_manto_places import name_variants, transliteration_keys
from llm_link_manto_places import matching_keys, shortlist_candidates


def entity(manto_id: str, label: str, parent_label: str = "") -> dict:
    variants = name_variants(
        label,
        include_location_container=False,
        include_generic_head=False,
    )
    return {
        "manto_id": manto_id,
        "label": label,
        "parent_label": parent_label,
        "keys": variants | transliteration_keys(variants),
    }


class LlmLinkMantoPlacesTests(unittest.TestCase):
    def test_matching_keys_include_transliteration_and_head_place_variants(self):
        keys = matching_keys("acropolis of Gythium")
        self.assertIn("gythium", keys)
        self.assertIn("gythion", keys)

    def test_shortlist_ranks_near_name_matches_first(self):
        entities = [
            entity("1", "🌍 Amyklai (Lakonia)", "Lakonia"),
            entity("2", "🌍 Athens (Attica)", "Attica"),
            entity("3", "🌍 Amymone (spring at Lerna)", "Lerna"),
        ]
        shortlist = shortlist_candidates("ancient Amyclae", entities, limit=2)
        self.assertTrue(shortlist)
        self.assertEqual(shortlist[0]["manto_id"], "1")
        self.assertNotIn("2", [item["manto_id"] for item in shortlist])

    def test_shortlist_returns_empty_for_unmatchable_names(self):
        entities = [entity("2", "🌍 Athens (Attica)", "Attica")]
        self.assertEqual(
            shortlist_candidates("Arabian desert", entities, limit=5),
            [],
        )


if __name__ == "__main__":
    unittest.main()
