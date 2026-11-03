"""Identical noun graphs must report identical communities after a DB restore."""
from unittest.mock import patch

import networkx as nx
import pytest

from website.data import _community_rows


def noun_graph(reverse_nodes=False, reverse_edges=False):
    base = nx.watts_strogatz_graph(900, 4, 0.1, seed=7)
    key = lambda node: (f"noun-{node:04d}", "person")
    nodes = list(base)
    edges = list(base.edges())
    graph = nx.Graph()
    for node in reversed(nodes) if reverse_nodes else nodes:
        graph.add_node(key(node), reference_form=key(node)[0],
                       entity_type="person", english=f"Name {node}")
    for left, right in reversed(edges) if reverse_edges else edges:
        weight = 1 + (left + right) % 3
        graph.add_edge(key(left), key(right), weight=weight, distance=1 / weight)
    return graph


@pytest.mark.parametrize("reverse_nodes,reverse_edges", [(True, False), (False, True), (True, True)])
def test_community_results_ignore_node_and_edge_insertion_order(reverse_nodes, reverse_edges):
    expected = _community_rows(noun_graph())
    graph = noun_graph(reverse_nodes, reverse_edges)
    before_nodes = list(graph.nodes(data=True))
    before_edges = list(graph.edges(data=True))
    assert _community_rows(graph) == expected
    assert list(graph.nodes(data=True)) == before_nodes
    assert list(graph.edges(data=True)) == before_edges


def test_equal_size_communities_have_stable_numbers():
    graph = nx.Graph()
    nodes = [(letter, "person") for letter in "abcd"]
    for node in nodes:
        graph.add_node(node, reference_form=node[0], entity_type="person")
    graph.add_edge(nodes[0], nodes[1], weight=1)
    graph.add_edge(nodes[2], nodes[3], weight=1)
    groups = [{nodes[0], nodes[1]}, {nodes[2], nodes[3]}]
    with patch("website.data.nx.community.greedy_modularity_communities", return_value=groups):
        first = _community_rows(graph)
    with patch("website.data.nx.community.greedy_modularity_communities", return_value=list(reversed(groups))):
        assert _community_rows(graph) == first


def test_edgeless_graph_remains_empty():
    graph = nx.Graph()
    graph.add_node(("one", "person"))
    assert _community_rows(graph) == []
