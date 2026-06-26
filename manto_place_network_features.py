#!/usr/bin/env python
"""Build explainable MANTO network features for Pausanias places."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import networkx as nx
from psycopg.types.json import Jsonb

from pausanias_db import add_database_argument, connect, initialize_schema


FEATURE_SET_VERSION = "manto-place-network-v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_database_argument(parser)
    parser.add_argument("--release-record-id", type=int, default=None)
    parser.add_argument("--feature-set-version", default=FEATURE_SET_VERSION)
    parser.add_argument(
        "--include-non-pre-pausanias",
        action="store_true",
        help="Use all MANTO edges. Default is strict pre-Pausanias-only edges.",
    )
    parser.add_argument("--betweenness-sample", type=int, default=200)
    parser.add_argument(
        "--community-node-limit",
        type=int,
        default=50000,
        help=(
            "Use connected-component size instead of greedy modularity when "
            "the graph has more nodes than this limit."
        ),
    )
    parser.add_argument(
        "--skip-clustering",
        action="store_true",
        help="Set clustering coefficients to 0.0 instead of computing weighted clustering.",
    )
    parser.add_argument(
        "--skip-components",
        action="store_true",
        help="Set component/community sizes to 1 instead of walking connected components.",
    )
    return parser.parse_args()


def latest_release_id(conn) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT record_id
            FROM manto_releases
            WHERE import_status IN ('imported', 'partial_imported')
            ORDER BY COALESCE(imported_at, updated_at) DESC, record_id DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
    if not row:
        raise RuntimeError("No imported MANTO release found.")
    return int(row[0])


def load_edges(conn, release_id: int, *, pre_pausanias_only: bool) -> list[tuple]:
    where = "AND is_pre_pausanias" if pre_pausanias_only else ""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT source_manto_id, target_manto_id, relation_type
            FROM manto_edges
            WHERE release_record_id = %s
              {where}
            """,
            (release_id,),
        )
        return cursor.fetchall()


def load_links(conn, release_id: int) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT reference_form, entity_type, english_transcription,
                   manto_id, manto_label
            FROM manto_place_links
            WHERE release_record_id = %s
              AND confidence <> 'rejected'
            ORDER BY reference_form, confidence
            """,
            (release_id,),
        )
        rows = cursor.fetchall()
    return [
        {
            "reference_form": row[0],
            "entity_type": row[1],
            "english_transcription": row[2],
            "manto_id": row[3],
            "manto_label": row[4],
        }
        for row in rows
    ]


def build_graph(edges: list[tuple], links: list[dict]) -> nx.Graph:
    graph = nx.Graph()
    for source_id, target_id, relation_type in edges:
        if not source_id or not target_id or source_id == target_id:
            continue
        if graph.has_edge(source_id, target_id):
            graph[source_id][target_id]["weight"] += 1
            graph[source_id][target_id]["relations"].add(relation_type or "related")
        else:
            graph.add_edge(
                source_id,
                target_id,
                weight=1,
                relations={relation_type or "related"},
            )
    for link in links:
        graph.add_node(link["manto_id"])
    return graph


def component_sizes_for_targets(graph: nx.Graph, target_nodes: set[str]) -> dict[str, int]:
    sizes = {}
    remaining = {node for node in target_nodes if node in graph}
    while remaining:
        node = next(iter(remaining))
        component = nx.node_connected_component(graph, node)
        size = len(component)
        for target in target_nodes & component:
            sizes[target] = size
        remaining -= component
    for node in target_nodes:
        sizes.setdefault(node, 1)
    return sizes


def community_sizes(
    graph: nx.Graph,
    *,
    node_limit: int,
    target_nodes: set[str],
    component_fallback: dict[str, int],
) -> dict[str, int]:
    if graph.number_of_edges() == 0:
        return {node: 1 for node in target_nodes}
    if graph.number_of_nodes() > node_limit:
        return dict(component_fallback)
    communities = nx.algorithms.community.greedy_modularity_communities(
        graph,
        weight="weight",
    )
    sizes = {}
    for community in communities:
        size = len(community)
        for node in target_nodes & set(community):
            sizes[node] = size
    for node in target_nodes:
        sizes.setdefault(node, component_fallback.get(node, 1))
    return sizes


def safe_betweenness(graph: nx.Graph, sample_size: int) -> dict[str, float]:
    if graph.number_of_nodes() <= 1:
        return {node: 0.0 for node in graph.nodes}
    if sample_size <= 0:
        return {node: 0.0 for node in graph.nodes}
    if graph.number_of_nodes() > sample_size:
        return nx.betweenness_centrality(
            graph,
            k=sample_size,
            seed=42,
            weight="weight",
        )
    return nx.betweenness_centrality(graph, weight="weight")


def jaccard(a: set, b: set) -> float:
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def build_feature_rows(
    *,
    release_id: int,
    feature_set_version: str,
    graph: nx.Graph,
    links: list[dict],
    pre_pausanias_only: bool,
    betweenness_sample: int,
    community_node_limit: int,
    skip_clustering: bool,
    skip_components: bool,
) -> list[tuple]:
    timestamp = now_iso()
    print("Computing degree centrality...", flush=True)
    degree_centrality = nx.degree_centrality(graph) if graph.number_of_nodes() > 1 else {}
    print("Computing PageRank...", flush=True)
    pagerank = nx.pagerank(graph, weight="weight") if graph.number_of_edges() else {
        node: 0.0 for node in graph.nodes
    }
    print("Computing betweenness centrality...", flush=True)
    betweenness = safe_betweenness(graph, betweenness_sample)
    print("Computing clustering coefficients...", flush=True)
    clustering = {} if skip_clustering else nx.clustering(graph, weight="weight") if graph.number_of_edges() else {
        node: 0.0 for node in graph.nodes
    }
    target_nodes = {link["manto_id"] for link in links}
    print("Computing target components and communities...", flush=True)
    if skip_components:
        components = {node: 1 for node in target_nodes}
        communities = {node: 1 for node in target_nodes}
        component_mode = "skipped"
    else:
        components = component_sizes_for_targets(graph, target_nodes)
        communities = community_sizes(
            graph,
            node_limit=community_node_limit,
            target_nodes=target_nodes,
            component_fallback=components,
        )
        component_mode = "target_nodes"
    sorted_pagerank = sorted(pagerank.values(), reverse=True)
    top_count = max(1, min(50, int(len(sorted_pagerank) * 0.05) or 1))
    top_nodes = {
        node for node, value in pagerank.items()
        if value >= (sorted_pagerank[top_count - 1] if sorted_pagerank else 0.0)
    }
    top_neighbor_sets = {node: set(graph.neighbors(node)) for node in top_nodes}

    rows = []
    for link in links:
        node = link["manto_id"]
        neighbors = set(graph.neighbors(node)) if node in graph else set()
        high_neighbors = neighbors & top_nodes
        max_neighbor_pagerank = max((pagerank.get(neighbor, 0.0) for neighbor in neighbors), default=0.0)
        shared_score = max(
            (jaccard(neighbors, top_neighbors) for top_neighbors in top_neighbor_sets.values()),
            default=0.0,
        )
        features = {
            "degree": int(graph.degree(node)) if node in graph else 0,
            "degree_centrality": float(degree_centrality.get(node, 0.0)),
            "pagerank": float(pagerank.get(node, 0.0)),
            "betweenness_centrality": float(betweenness.get(node, 0.0)),
            "clustering_coefficient": float(clustering.get(node, 0.0)),
            "component_size": int(components.get(node, 1)),
            "community_size": int(communities.get(node, 1)),
            "high_centrality_neighbor_count": int(len(high_neighbors)),
            "max_neighbor_pagerank": float(max_neighbor_pagerank),
            "shared_neighbor_high_centrality_score": float(shared_score),
            "graph_node_count": int(graph.number_of_nodes()),
            "graph_edge_count": int(graph.number_of_edges()),
            "component_mode": component_mode,
            "clustering_skipped": bool(skip_clustering),
            "betweenness_sample": int(betweenness_sample),
        }
        rows.append(
            (
                release_id,
                feature_set_version,
                link["reference_form"],
                link["entity_type"],
                link["english_transcription"],
                node,
                link["manto_label"],
                pre_pausanias_only,
                features["degree"],
                features["degree_centrality"],
                features["pagerank"],
                features["betweenness_centrality"],
                features["clustering_coefficient"],
                features["component_size"],
                features["community_size"],
                features["high_centrality_neighbor_count"],
                features["max_neighbor_pagerank"],
                features["shared_neighbor_high_centrality_score"],
                Jsonb(features),
                timestamp,
            )
        )
    return rows


def save_rows(
    conn,
    *,
    release_id: int,
    feature_set_version: str,
    pre_pausanias_only: bool,
    rows: list[tuple],
) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM manto_place_network_features
            WHERE release_record_id = %s
              AND feature_set_version = %s
              AND pre_pausanias_only = %s
            """,
            (release_id, feature_set_version, pre_pausanias_only),
        )
        cursor.executemany(
            """
            INSERT INTO manto_place_network_features (
                release_record_id, feature_set_version, reference_form, entity_type,
                english_transcription, manto_id, manto_label, pre_pausanias_only,
                degree, degree_centrality, pagerank, betweenness_centrality,
                clustering_coefficient, component_size, community_size,
                high_centrality_neighbor_count, max_neighbor_pagerank,
                shared_neighbor_high_centrality_score, features, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (
                release_record_id, feature_set_version, reference_form, entity_type, manto_id
            ) DO UPDATE
            SET english_transcription = EXCLUDED.english_transcription,
                manto_label = EXCLUDED.manto_label,
                pre_pausanias_only = EXCLUDED.pre_pausanias_only,
                degree = EXCLUDED.degree,
                degree_centrality = EXCLUDED.degree_centrality,
                pagerank = EXCLUDED.pagerank,
                betweenness_centrality = EXCLUDED.betweenness_centrality,
                clustering_coefficient = EXCLUDED.clustering_coefficient,
                component_size = EXCLUDED.component_size,
                community_size = EXCLUDED.community_size,
                high_centrality_neighbor_count = EXCLUDED.high_centrality_neighbor_count,
                max_neighbor_pagerank = EXCLUDED.max_neighbor_pagerank,
                shared_neighbor_high_centrality_score = EXCLUDED.shared_neighbor_high_centrality_score,
                features = EXCLUDED.features,
                created_at = EXCLUDED.created_at
            """,
            rows,
        )
    conn.commit()


def main() -> None:
    args = parse_arguments()
    pre_pausanias_only = not args.include_non_pre_pausanias
    with connect(args.database_url) as conn:
        initialize_schema(conn)
        release_id = args.release_record_id or latest_release_id(conn)
        print("Loading MANTO edges...", flush=True)
        edges = load_edges(conn, release_id, pre_pausanias_only=pre_pausanias_only)
        print("Loading Pausanias-MANTO links...", flush=True)
        links = load_links(conn, release_id)
        print("Building graph...", flush=True)
        graph = build_graph(edges, links)
        rows = build_feature_rows(
            release_id=release_id,
            feature_set_version=args.feature_set_version,
            graph=graph,
            links=links,
            pre_pausanias_only=pre_pausanias_only,
            betweenness_sample=args.betweenness_sample,
            community_node_limit=args.community_node_limit,
            skip_clustering=args.skip_clustering,
            skip_components=args.skip_components,
        )
        print("Saving feature rows...", flush=True)
        save_rows(
            conn,
            release_id=release_id,
            feature_set_version=args.feature_set_version,
            pre_pausanias_only=pre_pausanias_only,
            rows=rows,
        )
    print(
        f"Saved {len(rows):,} MANTO place feature rows for release {release_id} "
        f"from {graph.number_of_nodes():,} nodes and {graph.number_of_edges():,} edges "
        f"({ 'pre-Pausanias only' if pre_pausanias_only else 'all edges' })."
    )


if __name__ == "__main__":
    main()
