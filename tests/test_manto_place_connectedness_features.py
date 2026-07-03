import unittest

from manto_place_connectedness_features import (
    FEATURE_ROW_COLUMNS,
    PERSON_PREFIX,
    PLACE_PREFIX,
    PlaceDetail,
    TypedEdge,
    build_feature_rows,
    build_parent_neighbors,
    build_place_graph,
    build_place_person_maps,
    shared_action_patterns,
)


class MantoPlaceConnectednessFeatureTests(unittest.TestCase):
    def test_shared_action_patterns_require_distinct_figures_on_both_sides(self):
        self.assertEqual(
            shared_action_patterns(
                {"foundation": {"hero-a"}},
                {"foundation": {"hero-a"}},
            ),
            set(),
        )
        self.assertEqual(
            shared_action_patterns(
                {"foundation": {"hero-a"}},
                {"foundation": {"hero-b"}},
            ),
            {"foundation"},
        )

    def test_build_feature_rows_counts_shared_figures_and_distinct_action_patterns(self):
        place_details = {
            "p1": PlaceDetail("p1", "🌍 Place One", "region", "🌍 Region"),
            "p2": PlaceDetail("p2", "🌍 Place Two", "region", "🌍 Region"),
            "p3": PlaceDetail("p3", "🌍 Big Place", "", ""),
        }
        edges = [
            TypedEdge("p1", "p3", "founded_from", PLACE_PREFIX, PLACE_PREFIX),
            TypedEdge("p1", "hero-a", "founded_by", PLACE_PREFIX, PERSON_PREFIX),
            TypedEdge("hero-b", "p2", "founder_of", PERSON_PREFIX, PLACE_PREFIX),
            TypedEdge("p1", "hero-shared", "cult_site_of", PLACE_PREFIX, PERSON_PREFIX),
            TypedEdge("p2", "hero-shared", "cult_site_of", PLACE_PREFIX, PERSON_PREFIX),
        ]
        place_graph, direct_neighbors, direct_relations = build_place_graph(place_details, edges)
        parent_neighbors = build_parent_neighbors(place_details)
        place_people, place_action_people = build_place_person_maps(edges)
        rows = build_feature_rows(
            release_id=1,
            feature_set_version="test",
            links=[
                {
                    "reference_form": "Place One",
                    "entity_type": "place",
                    "english_transcription": "Place One",
                    "manto_id": "p1",
                    "manto_label": "🌍 Place One",
                }
            ],
            place_details=place_details,
            direct_neighbors=direct_neighbors,
            direct_relations=direct_relations,
            parent_neighbors=parent_neighbors,
            place_people=place_people,
            place_action_people=place_action_people,
            large_place_ids={"p3"},
            place_degree={"p1": 1, "p2": 0, "p3": 1},
            place_pagerank={"p1": 0.4, "p2": 0.0, "p3": 0.6},
            pre_pausanias_only=True,
        )

        row = dict(zip(FEATURE_ROW_COLUMNS, rows[0]))

        self.assertEqual(row["local_place_neighbor_count"], 2)
        self.assertEqual(row["direct_place_neighbor_count"], 1)
        self.assertEqual(row["same_parent_place_neighbor_count"], 1)
        self.assertEqual(row["large_place_neighbor_count"], 1)
        self.assertTrue(row["has_large_place_neighbor"])
        self.assertEqual(row["strong_place_tie_count"], 1)
        self.assertEqual(row["mythic_figure_count"], 2)
        self.assertEqual(row["action_pattern_count"], 2)
        self.assertEqual(row["shared_mythic_figure_neighbor_count"], 1)
        self.assertEqual(row["shared_mythic_figure_count"], 1)
        self.assertEqual(row["max_shared_mythic_figures_with_neighbor"], 1)
        self.assertEqual(row["shared_action_neighbor_count"], 1)
        self.assertEqual(row["shared_action_pattern_count"], 1)
        self.assertEqual(row["shared_action_neighbor_pattern_count"], 1)
        self.assertEqual(row["max_shared_action_patterns_with_neighbor"], 1)


if __name__ == "__main__":
    unittest.main()
