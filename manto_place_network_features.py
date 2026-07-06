#!/usr/bin/env python
"""Build explainable MANTO network features for Pausanias places."""

from __future__ import annotations

import argparse
import math
import re
from datetime import datetime, timezone

import networkx as nx
from networkx.algorithms import approximation as nx_approx

from pausanias_db import add_database_argument, column_exists, connect, initialize_schema


FEATURE_SET_VERSION = "manto-pausanias-place-network-v3"
LABEL_SOURCE_VERSION = "manto-entity-info-v1"

# MANTO bookkeeping relations describe the database and its bibliography, not
# the mythic network itself; keeping them would let citation volume masquerade
# as narrative connectivity.
BOOKKEEPING_RELATIONS = {
    "",
    "collection",
    "period",
    "source_attributes",
    "unesco_status",
    "mentioned_in_text",
    "depictions",
    "identified_in",
}

UNREACHABLE_HOP_DISTANCE = 99
DISJOINT_PATH_CUTOFF = 5
LOCAL_REACH_CUTOFF = 3

NEW_FEATURE_COLUMNS = {
    "k_core": "INTEGER",
    "hop_distance_to_large_place": "INTEGER",
    "nodes_within_two_hops": "INTEGER",
    "nodes_within_three_hops": "INTEGER",
    "disjoint_paths_to_large_place": "INTEGER",
    "bridge_edge_fraction": "DOUBLE PRECISION",
    "within_module_degree_zscore": "DOUBLE PRECISION",
    "participation_coefficient": "DOUBLE PRECISION",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_database_argument(parser)
    parser.add_argument("--release-record-id", type=int, default=None)
    parser.add_argument("--feature-set-version", default=FEATURE_SET_VERSION)
    parser.add_argument(
        "--target-source",
        choices=("manto-status-labels", "linked-proper-nouns"),
        default="manto-status-labels",
        help="Build target nodes from MANTO Pausanias place labels or from local proper-noun links.",
    )
    parser.add_argument("--label-source-version", default=LABEL_SOURCE_VERSION)
    parser.add_argument(
        "--include-non-pre-pausanias",
        action="store_true",
        help="Use all MANTO edges. Default is strict pre-Pausanias-only edges.",
    )
    parser.add_argument("--betweenness-sample", type=int, default=200)
    parser.add_argument(
        "--community-node-limit",
        type=int,
        default=500000,
        help=(
            "Use connected-component size instead of Louvain communities when "
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
    parser.add_argument(
        "--link-match-methods",
        default="",
        help=(
            "Comma-separated manto_place_links.match_method filter for "
            "linked-proper-nouns targets, e.g. 'exact_normalized_name' or "
            "'exact_normalized_name,transliteration'. Default: all methods."
        ),
    )
    parser.add_argument(
        "--include-bookkeeping-edges",
        action="store_true",
        help=(
            "Keep MANTO bookkeeping relations (source_attributes, collection, "
            "period, unesco_status, mentioned_in_text, depictions, identified_in) "
            "in the graph. Default excludes them so centralities measure the "
            "myth network rather than the bibliography."
        ),
    )
    return parser.parse_args()


def parse_match_methods(value: str | None) -> tuple[str, ...] | None:
    methods = tuple(part.strip() for part in (value or "").split(",") if part.strip())
    return methods or None


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


def load_links(
    conn,
    release_id: int,
    *,
    match_methods: tuple[str, ...] | None = None,
) -> list[dict]:
    method_filter = "AND match_method = ANY(%s)" if match_methods else ""
    parameters: tuple = (release_id, list(match_methods)) if match_methods else (release_id,)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT reference_form, entity_type, english_transcription,
                   manto_id, manto_label
            FROM manto_place_links
            WHERE release_record_id = %s
              AND confidence <> 'rejected'
              {method_filter}
            ORDER BY reference_form, confidence
            """,
            parameters,
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


def clean_place_name(value: str) -> str:
    text = re.sub(r"^[^\w]+", "", value or "").strip()
    return " ".join(text.split())


def load_manto_status_targets(
    conn,
    release_id: int,
    *,
    label_source_version: str,
) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT place_name, object_id
            FROM manto_place_status_labels
            WHERE release_record_id = %s
              AND label_source_version = %s
              AND target_label IN ('survives', 'does_not_survive')
            ORDER BY place_name, object_id
            """,
            (release_id, label_source_version),
        )
        rows = cursor.fetchall()
    return [
        {
            "reference_form": clean_place_name(row[0]),
            "entity_type": "place",
            "english_transcription": clean_place_name(row[0]),
            "manto_id": row[1],
            "manto_label": row[0],
        }
        for row in rows
    ]


def build_graph(
    edges: list[tuple],
    links: list[dict],
    *,
    include_bookkeeping: bool = False,
) -> nx.Graph:
    graph = nx.Graph()
    for source_id, target_id, relation_type in edges:
        if not source_id or not target_id or source_id == target_id:
            continue
        if not include_bookkeeping and (relation_type or "") in BOOKKEEPING_RELATIONS:
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


def detect_communities(
    graph: nx.Graph,
    *,
    node_limit: int,
) -> dict[str, int]:
    """Map each node to a Louvain community index, or {} when skipped."""
    if graph.number_of_edges() == 0 or graph.number_of_nodes() > node_limit:
        return {}
    communities = nx.algorithms.community.louvain_communities(
        graph,
        weight="weight",
        seed=42,
    )
    membership: dict[str, int] = {}
    for index, community in enumerate(communities):
        for node in community:
            membership[node] = index
    return membership


def community_sizes(
    membership: dict[str, int],
    *,
    target_nodes: set[str],
    component_fallback: dict[str, int],
) -> dict[str, int]:
    if not membership:
        return dict(component_fallback)
    counts: dict[int, int] = {}
    for community in membership.values():
        counts[community] = counts.get(community, 0) + 1
    sizes = {
        node: counts[membership[node]]
        for node in target_nodes
        if node in membership
    }
    for node in target_nodes:
        sizes.setdefault(node, component_fallback.get(node, 1))
    return sizes


def cartographic_roles(
    graph: nx.Graph,
    membership: dict[str, int],
    target_nodes: set[str],
) -> tuple[dict[str, float], dict[str, float]]:
    """Guimerà-Amaral within-module degree z-score and participation coefficient."""
    if not membership:
        return {}, {}
    module_degrees: dict[str, dict[int, int]] = {}
    for node in graph.nodes:
        per_module: dict[int, int] = {}
        for neighbor in graph.neighbors(node):
            community = membership.get(neighbor)
            if community is None:
                continue
            per_module[community] = per_module.get(community, 0) + 1
        module_degrees[node] = per_module

    within: dict[int, list[float]] = {}
    for node, per_module in module_degrees.items():
        community = membership.get(node)
        if community is None:
            continue
        within.setdefault(community, []).append(float(per_module.get(community, 0)))
    module_stats = {}
    for community, values in within.items():
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        module_stats[community] = (mean, math.sqrt(variance))

    zscores: dict[str, float] = {}
    participation: dict[str, float] = {}
    for node in target_nodes:
        per_module = module_degrees.get(node, {})
        degree = sum(per_module.values())
        community = membership.get(node)
        if community is not None and community in module_stats:
            mean, std = module_stats[community]
            own = float(per_module.get(community, 0))
            zscores[node] = (own - mean) / std if std > 0 else 0.0
        if degree > 0:
            participation[node] = 1.0 - sum(
                (count / degree) ** 2 for count in per_module.values()
            )
    return zscores, participation


def hop_distances_to_large_places(graph: nx.Graph, large_nodes: set[str]) -> dict[str, int]:
    sources = {node for node in large_nodes if node in graph}
    if not sources:
        return {}
    return nx.multi_source_dijkstra_path_length(graph, sources, weight=None)


def local_reach(graph: nx.Graph, node: str, cutoff: int) -> dict[int, int]:
    """Count nodes at each hop distance up to cutoff (excluding the node itself)."""
    counts = {distance: 0 for distance in range(1, cutoff + 1)}
    if node not in graph:
        return counts
    for _, distance in nx.single_source_shortest_path_length(graph, node, cutoff=cutoff).items():
        if distance >= 1:
            counts[distance] += 1
    return counts


def nearest_large_place(
    graph: nx.Graph,
    node: str,
    large_nodes: set[str],
    cutoff: int,
) -> str | None:
    if node not in graph:
        return None
    lengths = nx.single_source_shortest_path_length(graph, node, cutoff=cutoff)
    best_node = None
    best_distance = cutoff + 1
    for candidate, distance in lengths.items():
        if candidate == node or candidate not in large_nodes:
            continue
        if distance < best_distance:
            best_node = candidate
            best_distance = distance
    return best_node


def bridge_fractions(graph: nx.Graph, target_nodes: set[str]) -> dict[str, float]:
    bridges = set()
    for source, target in nx.bridges(graph):
        bridges.add(frozenset((source, target)))
    fractions = {}
    for node in target_nodes:
        if node not in graph:
            continue
        incident = list(graph.edges(node))
        if not incident:
            continue
        bridge_count = sum(
            1 for source, target in incident if frozenset((source, target)) in bridges
        )
        fractions[node] = bridge_count / len(incident)
    return fractions


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
        membership: dict[str, int] = {}
        component_mode = "skipped"
    else:
        components = component_sizes_for_targets(graph, target_nodes)
        membership = detect_communities(graph, node_limit=community_node_limit)
        communities = community_sizes(
            membership,
            target_nodes=target_nodes,
            component_fallback=components,
        )
        component_mode = "target_nodes"
    print("Computing cartographic roles...", flush=True)
    module_zscores, participation = cartographic_roles(graph, membership, target_nodes)
    print("Computing k-cores...", flush=True)
    core_numbers = nx.core_number(graph) if graph.number_of_nodes() else {}
    print("Computing bridge fractions...", flush=True)
    bridge_fraction = bridge_fractions(graph, target_nodes)
    sorted_pagerank = sorted(pagerank.values(), reverse=True)
    top_count = max(1, min(50, int(len(sorted_pagerank) * 0.05) or 1))
    top_nodes = {
        node for node, value in pagerank.items()
        if value >= (sorted_pagerank[top_count - 1] if sorted_pagerank else 0.0)
    }
    top_neighbor_sets = {node: set(graph.neighbors(node)) for node in top_nodes}
    print("Computing hop distances to large places...", flush=True)
    hop_distances = hop_distances_to_large_places(graph, top_nodes)

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
        reach = local_reach(graph, node, LOCAL_REACH_CUTOFF)
        hop_distance = int(hop_distances.get(node, UNREACHABLE_HOP_DISTANCE))
        disjoint_paths = 0
        nearest_large = nearest_large_place(graph, node, top_nodes - {node}, LOCAL_REACH_CUTOFF)
        if nearest_large is not None:
            disjoint_paths = int(
                nx_approx.local_node_connectivity(
                    graph, node, nearest_large, cutoff=DISJOINT_PATH_CUTOFF
                )
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
            "k_core": int(core_numbers.get(node, 0)),
            "hop_distance_to_large_place": (
                0 if node in top_nodes else hop_distance
            ),
            "nodes_within_two_hops": int(reach.get(1, 0) + reach.get(2, 0)),
            "nodes_within_three_hops": int(
                reach.get(1, 0) + reach.get(2, 0) + reach.get(3, 0)
            ),
            "disjoint_paths_to_large_place": disjoint_paths,
            "bridge_edge_fraction": float(bridge_fraction.get(node, 0.0)),
            "within_module_degree_zscore": float(module_zscores.get(node, 0.0)),
            "participation_coefficient": float(participation.get(node, 0.0)),
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
                features["k_core"],
                features["hop_distance_to_large_place"],
                features["nodes_within_two_hops"],
                features["nodes_within_three_hops"],
                features["disjoint_paths_to_large_place"],
                features["bridge_edge_fraction"],
                features["within_module_degree_zscore"],
                features["participation_coefficient"],
                timestamp,
            )
        )
    return rows


def ensure_feature_columns(conn) -> None:
    with conn.cursor() as cursor:
        for column_name, column_type in NEW_FEATURE_COLUMNS.items():
            if not column_exists(conn, "manto_place_network_features", column_name):
                cursor.execute(
                    f"ALTER TABLE manto_place_network_features ADD COLUMN {column_name} {column_type}"
                )
    conn.commit()


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
                shared_neighbor_high_centrality_score, k_core,
                hop_distance_to_large_place, nodes_within_two_hops,
                nodes_within_three_hops, disjoint_paths_to_large_place,
                bridge_edge_fraction, within_module_degree_zscore,
                participation_coefficient, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                k_core = EXCLUDED.k_core,
                hop_distance_to_large_place = EXCLUDED.hop_distance_to_large_place,
                nodes_within_two_hops = EXCLUDED.nodes_within_two_hops,
                nodes_within_three_hops = EXCLUDED.nodes_within_three_hops,
                disjoint_paths_to_large_place = EXCLUDED.disjoint_paths_to_large_place,
                bridge_edge_fraction = EXCLUDED.bridge_edge_fraction,
                within_module_degree_zscore = EXCLUDED.within_module_degree_zscore,
                participation_coefficient = EXCLUDED.participation_coefficient,
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
        ensure_feature_columns(conn)
        release_id = args.release_record_id or latest_release_id(conn)
        print("Loading MANTO edges...", flush=True)
        edges = load_edges(conn, release_id, pre_pausanias_only=pre_pausanias_only)
        if args.target_source == "linked-proper-nouns":
            print("Loading Pausanias-MANTO links...", flush=True)
            links = load_links(
                conn,
                release_id,
                match_methods=parse_match_methods(args.link_match_methods),
            )
        else:
            print("Loading MANTO Pausanias place-status targets...", flush=True)
            links = load_manto_status_targets(
                conn,
                release_id,
                label_source_version=args.label_source_version,
            )
        print("Building graph...", flush=True)
        graph = build_graph(
            edges,
            links,
            include_bookkeeping=args.include_bookkeeping_edges,
        )
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
