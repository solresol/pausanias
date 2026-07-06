import unittest

from manto_place_connectedness_features import (
    FEATURE_ROW_COLUMNS,
    NO_ATTESTATION_EARLIEST,
    NO_ATTESTATION_LATEST,
    PERSON_PREFIX,
    PLACE_PREFIX,
    PlaceDetail,
    TypedEdge,
    build_feature_rows,
    build_parent_neighbors,
    build_person_kinship,
    build_place_graph,
    build_place_person_maps,
    cosine_similarity,
    figure_place_counts,
    kin_linked_places,
    place_attestation_summary,
    profile_entropy,
    shared_action_patterns,
    shared_figure_counts_for,
    shared_figure_null_stats,
    zscore,
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
        # hero-a is exclusive to p1, hero-shared spans p1 and p2.
        self.assertEqual(row["exclusive_figure_count"], 1)
        self.assertEqual(row["panhellenic_figure_count"], 0)
        self.assertEqual(row["figure_max_ubiquity"], 2)
        self.assertAlmostEqual(row["figure_mean_ubiquity"], 1.5)
        self.assertEqual(row["kin_linked_place_count"], 0)
        self.assertEqual(row["archaic_story_count"], 0)
        self.assertEqual(row["earliest_attestation_year"], NO_ATTESTATION_EARLIEST)
        self.assertEqual(row["latest_attestation_year"], NO_ATTESTATION_LATEST)
        self.assertEqual(row["shared_figure_count_zscore"], 0.0)

    def test_figure_place_counts_counts_places_per_figure(self):
        counts = figure_place_counts(
            {
                "p1": {"hero-a", "hero-shared"},
                "p2": {"hero-shared"},
            }
        )
        self.assertEqual(counts, {"hero-a": 1, "hero-shared": 2})

    def test_build_person_kinship_only_links_person_person_kin_edges(self):
        kinship = build_person_kinship(
            [
                TypedEdge("hero-a", "hero-b", "son_of", PERSON_PREFIX, PERSON_PREFIX),
                TypedEdge("hero-a", "hero-c", "killed_by", PERSON_PREFIX, PERSON_PREFIX),
                TypedEdge("hero-a", "p1", "son_of", PERSON_PREFIX, PLACE_PREFIX),
            ]
        )
        self.assertEqual(kinship, {"hero-a": {"hero-b"}, "hero-b": {"hero-a"}})

    def test_kin_linked_places_excludes_kin_who_are_own_figures(self):
        person_places = {
            "hero-a": {"p1"},
            "hero-b": {"p2"},
            "hero-c": {"p1", "p3"},
        }
        kinship = {
            "hero-a": {"hero-b", "hero-c"},
            "hero-b": {"hero-a"},
            "hero-c": {"hero-a"},
        }
        linked = kin_linked_places("p1", {"hero-a", "hero-c"}, person_places, kinship)
        # hero-b (kin, elsewhere) links p2; hero-c is one of p1's own figures.
        self.assertEqual(linked, {"p2"})

    def test_profile_entropy_and_cosine_similarity(self):
        self.assertEqual(profile_entropy({}), 0.0)
        self.assertEqual(profile_entropy({"foundation": 4}), 0.0)
        self.assertAlmostEqual(
            profile_entropy({"foundation": 1, "burial_at": 1}), 1.0
        )
        self.assertAlmostEqual(
            cosine_similarity({"foundation": 2}, {"foundation": 4}), 1.0
        )
        self.assertEqual(
            cosine_similarity({"foundation": 2}, {"burial_at": 3}), 0.0
        )
        self.assertEqual(cosine_similarity({}, {"foundation": 1}), 0.0)

    def test_place_attestation_summary_buckets_years_by_stratum(self):
        summaries = place_attestation_summary(
            [
                TypedEdge("p1", "hero-a", "founded_by", PLACE_PREFIX, PERSON_PREFIX, -700),
                TypedEdge("p1", "hero-b", "cult_site_of", PLACE_PREFIX, PERSON_PREFIX, -400),
                TypedEdge("p1", "hero-c", "buried_at", PLACE_PREFIX, PERSON_PREFIX, 50),
                TypedEdge("p1", "hero-d", "source_attributes", PLACE_PREFIX, PERSON_PREFIX, -650),
                TypedEdge("p1", "hero-e", "dies_at", PLACE_PREFIX, PERSON_PREFIX, None),
            ]
        )
        summary = summaries["p1"]
        self.assertEqual(summary["archaic"], 1)
        self.assertEqual(summary["classical"], 1)
        self.assertEqual(summary["hellenistic"], 0)
        self.assertEqual(summary["early_imperial"], 1)
        self.assertEqual(summary["earliest"], -700)
        self.assertEqual(summary["latest"], 50)

    def test_shared_figure_null_stats_are_deterministic_and_zscore_guards_zero_std(self):
        place_people = {
            "p1": {"hero-a", "hero-shared"},
            "p2": {"hero-shared"},
            "p3": {"hero-b"},
        }
        neighbors = {"p1": {"p2", "p3"}}
        first = shared_figure_null_stats(place_people, neighbors, samples=10, seed=7)
        second = shared_figure_null_stats(place_people, neighbors, samples=10, seed=7)
        self.assertEqual(first, second)
        self.assertIn("p1", first)
        observed_count, observed_neighbors = shared_figure_counts_for(
            "p1", neighbors["p1"], place_people
        )
        self.assertEqual((observed_count, observed_neighbors), (1, 1))
        self.assertEqual(zscore(3.0, 1.0, 0.0), 0.0)
        self.assertAlmostEqual(zscore(3.0, 1.0, 2.0), 1.0)


if __name__ == "__main__":
    unittest.main()
