import unittest

from manto_place_geography_features import (
    UNKNOWN_DISTANCE_KM,
    build_feature_rows,
    haversine_km,
    nearest_distance_km,
)


ATHENS = (37.9838, 23.7275)
SPARTA = (37.0819, 22.4297)
CORINTH = (37.9061, 22.8781)


class MantoPlaceGeographyFeatureTests(unittest.TestCase):
    def test_haversine_matches_known_distances(self):
        self.assertEqual(haversine_km(*ATHENS, *ATHENS), 0.0)
        athens_sparta = haversine_km(*ATHENS, *SPARTA)
        self.assertGreater(athens_sparta, 140.0)
        self.assertLess(athens_sparta, 165.0)

    def test_nearest_distance_excludes_self(self):
        candidates = {"athens": ATHENS, "corinth": CORINTH}
        distance = nearest_distance_km(ATHENS, candidates, exclude="athens")
        self.assertAlmostEqual(distance, haversine_km(*ATHENS, *CORINTH))
        self.assertEqual(
            nearest_distance_km(ATHENS, {"athens": ATHENS}, exclude="athens"),
            UNKNOWN_DISTANCE_KM,
        )

    def test_build_feature_rows_computes_neighbor_bands_and_sentinels(self):
        links = [
            {
                "reference_form": "Athens",
                "entity_type": "place",
                "english_transcription": "Athens",
                "manto_id": "athens",
                "manto_label": "🌍 Athens",
            },
            {
                "reference_form": "Nowhere",
                "entity_type": "place",
                "english_transcription": "Nowhere",
                "manto_id": "nowhere",
                "manto_label": "🌍 Nowhere",
            },
        ]
        place_coordinates = {
            "athens": ATHENS,
            "corinth": CORINTH,
            "sparta": SPARTA,
        }
        rows = build_feature_rows(
            release_id=1,
            feature_set_version="test",
            links=links,
            place_coordinates=place_coordinates,
            large_place_ids={"corinth"},
            local_neighbor_sets={"athens": {"corinth", "sparta", "uncharted"}},
            pre_pausanias_only=True,
        )

        athens = rows[0]
        self.assertTrue(athens[8])  # has_coordinates
        self.assertAlmostEqual(athens[9], haversine_km(*ATHENS, *CORINTH))
        self.assertEqual(athens[12], 2)  # two neighbors with coordinates
        self.assertEqual(athens[16], 0)  # none within 25 km
        self.assertEqual(athens[17], 0)  # none within 50 km
        self.assertEqual(athens[18], 1)  # Corinth within 100 km, Sparta beyond
        self.assertEqual(athens[19], 0.0)  # local_tie_fraction_50km

        nowhere = rows[1]
        self.assertFalse(nowhere[8])
        self.assertEqual(nowhere[9], UNKNOWN_DISTANCE_KM)
        self.assertEqual(nowhere[12], 0)


if __name__ == "__main__":
    unittest.main()
