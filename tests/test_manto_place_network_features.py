import unittest

import networkx as nx

from manto_place_network_features import (
    UNREACHABLE_HOP_DISTANCE,
    bridge_fractions,
    build_graph,
    cartographic_roles,
    community_sizes,
    detect_communities,
    hop_distances_to_large_places,
    local_reach,
    nearest_large_place,
)


def toy_graph() -> nx.Graph:
    # Path a-b-c plus triangle c-d-e, and a disconnected pair x-y.
    graph = nx.Graph()
    graph.add_edges_from(
        [("a", "b"), ("b", "c"), ("c", "d"), ("c", "e"), ("d", "e"), ("x", "y")]
    )
    return graph


class MantoPlaceNetworkFeatureTests(unittest.TestCase):
    def test_build_graph_excludes_bookkeeping_relations_by_default(self):
        edges = [
            ("p1", "p2", "founded_from"),
            ("p1", "src", "source_attributes"),
            ("p1", "txt", "mentioned_in_text"),
        ]
        graph = build_graph(edges, [])
        self.assertTrue(graph.has_edge("p1", "p2"))
        self.assertFalse(graph.has_node("src"))
        self.assertFalse(graph.has_node("txt"))

        kept = build_graph(edges, [], include_bookkeeping=True)
        self.assertTrue(kept.has_edge("p1", "src"))
        self.assertTrue(kept.has_edge("p1", "txt"))

    def test_hop_distances_and_local_reach(self):
        graph = toy_graph()
        distances = hop_distances_to_large_places(graph, {"d"})
        self.assertEqual(distances["d"], 0)
        self.assertEqual(distances["a"], 3)
        self.assertNotIn("x", distances)
        self.assertEqual(
            UNREACHABLE_HOP_DISTANCE,
            distances.get("x", UNREACHABLE_HOP_DISTANCE),
        )
        reach = local_reach(graph, "a", 3)
        self.assertEqual(reach, {1: 1, 2: 1, 3: 2})
        self.assertEqual(local_reach(graph, "missing", 3), {1: 0, 2: 0, 3: 0})

    def test_nearest_large_place_prefers_closest_candidate(self):
        graph = toy_graph()
        self.assertEqual(nearest_large_place(graph, "b", {"c", "e"}, 3), "c")
        self.assertIsNone(nearest_large_place(graph, "x", {"c"}, 3))

    def test_bridge_fractions_on_disconnected_graph(self):
        graph = toy_graph()
        fractions = bridge_fractions(graph, {"a", "c", "x"})
        self.assertEqual(fractions["a"], 1.0)
        self.assertEqual(fractions["x"], 1.0)
        # c has one bridge (b-c) out of three incident edges.
        self.assertAlmostEqual(fractions["c"], 1.0 / 3.0)

    def test_communities_and_cartographic_roles(self):
        graph = toy_graph()
        membership = detect_communities(graph, node_limit=1000)
        self.assertEqual(len(membership), graph.number_of_nodes())
        sizes = community_sizes(
            membership,
            target_nodes={"c", "x"},
            component_fallback={"c": 5, "x": 2},
        )
        self.assertGreaterEqual(sizes["c"], 1)
        self.assertGreaterEqual(sizes["x"], 1)

        zscores, participation = cartographic_roles(graph, membership, {"c", "x"})
        self.assertIn("c", participation)
        # x sits inside a single two-node community: no external ties.
        self.assertEqual(participation.get("x", 0.0), 0.0)

    def test_community_sizes_fall_back_when_detection_is_skipped(self):
        sizes = community_sizes(
            {},
            target_nodes={"a"},
            component_fallback={"a": 4},
        )
        self.assertEqual(sizes, {"a": 4})


if __name__ == "__main__":
    unittest.main()
