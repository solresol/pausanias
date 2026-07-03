#!/usr/bin/env python
"""Build Greta-style MANTO connectedness features for Pausanias places."""

from __future__ import annotations

import argparse
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

import networkx as nx

from manto_place_network_features import (
    latest_release_id,
    load_links,
    load_manto_status_targets,
)
from pausanias_db import add_database_argument, connect, initialize_schema


FEATURE_SET_VERSION = "manto-place-connectedness-v1"
LABEL_SOURCE_VERSION = "manto-entity-info-v1"
PLACE_PREFIX = "🌍"
PERSON_PREFIX = "👤"

EXCLUDED_RELATIONS = {
    "",
    "collection",
    "period",
    "source_attributes",
    "unesco_status",
}

ACTION_RELATIONS = {
    "born_at": "birth_at",
    "buried_at": "burial_at",
    "conceived_at": "conception_at",
    "conquered_by": "conquest",
    "created_at": "creation_at",
    "created_by": "creation",
    "creates": "creation",
    "cult_established_by": "cult_establishment",
    "cult_site_of": "cult_site",
    "cult_sites": "cult_site",
    "dedicated_at": "dedication",
    "dedicated_by": "dedication",
    "derives_etymology_from": "eponym_or_etymology",
    "destroyed_by": "destruction",
    "dies_at": "death_at",
    "disappears_at": "disappearance_at",
    "divine_patron_of": "divine_patronage",
    "dwelling": "dwelling",
    "dwelling_of": "dwelling",
    "eponym": "eponym_or_etymology",
    "eponym_of": "eponym_or_etymology",
    "establishes_games_at": "games_establishment",
    "fortified_by": "fortification",
    "founded_by": "foundation",
    "founder_of": "foundation",
    "games_established_by": "games_establishment",
    "games_held_by": "games",
    "has_post_mortem_existence_at": "post_mortem_presence",
    "herald_at": "ritual_office",
    "holds_games_at": "games",
    "humans_created_on_site_by": "creation",
    "lawgiver_at": "lawgiving",
    "named_by": "naming",
    "place_of_birth_of": "birth_at",
    "place_of_burial_of": "burial_at",
    "place_of_conception_of": "conception_at",
    "place_of_death_of": "death_at",
    "priest_at": "ritual_office",
    "priestess_at": "ritual_office",
    "prophet_at": "ritual_office",
    "resurrected_at": "resurrection_at",
    "ruled_by": "rule",
    "ruler_of": "rule",
    "settled_by": "settlement",
    "settles_in": "settlement",
    "transformed_from": "transformation",
    "transformed_into": "transformation",
}

STRONG_PLACE_RELATIONS = {
    "belongs_to",
    "conquered_by",
    "destroyed_by",
    "fortified_by",
    "founded_from",
    "ruled_by",
    "ruler_of",
    "settled_from",
}

FEATURE_ROW_COLUMNS = [
    "release_record_id",
    "feature_set_version",
    "reference_form",
    "entity_type",
    "english_transcription",
    "manto_id",
    "manto_label",
    "pre_pausanias_only",
    "place_graph_degree",
    "place_graph_pagerank",
    "local_place_neighbor_count",
    "direct_place_neighbor_count",
    "same_parent_place_neighbor_count",
    "large_place_neighbor_count",
    "large_place_max_degree",
    "large_place_max_pagerank",
    "has_large_place_neighbor",
    "strong_place_tie_count",
    "mythic_figure_count",
    "action_pattern_count",
    "shared_mythic_figure_neighbor_count",
    "shared_mythic_figure_count",
    "max_shared_mythic_figures_with_neighbor",
    "shared_mythic_figure_large_place_neighbor_count",
    "shared_action_neighbor_count",
    "shared_action_pattern_count",
    "shared_action_neighbor_pattern_count",
    "max_shared_action_patterns_with_neighbor",
    "shared_action_large_place_neighbor_count",
    "created_at",
]


@dataclass(frozen=True)
class PlaceDetail:
    object_id: str
    name: str
    parent_id: str
    parent_label: str


@dataclass(frozen=True)
class TypedEdge:
    source_id: str
    target_id: str
    relation_type: str
    source_prefix: str
    target_prefix: str


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
        help="Build target nodes from MANTO Pausanias labels or local Pausanias-MANTO links.",
    )
    parser.add_argument("--label-source-version", default=LABEL_SOURCE_VERSION)
    parser.add_argument(
        "--include-non-pre-pausanias",
        action="store_true",
        help="Use all MANTO edges. Default is strict pre-Pausanias-only edges.",
    )
    parser.add_argument(
        "--large-place-quantile",
        type=float,
        default=0.95,
        help="Places at or above this PageRank/degree quantile count as large-place neighbors.",
    )
    return parser.parse_args()


def entity_prefix(name: str | None) -> str:
    return (name or "")[:1]


def relation_key(value: str | None) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", (value or "").lower())).strip("_")


def canonical_action(relation_type: str | None) -> str | None:
    return ACTION_RELATIONS.get(relation_key(relation_type))


def percentile_threshold(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    clipped = min(max(quantile, 0.0), 1.0)
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.floor((len(ordered) - 1) * clipped)))
    return ordered[index]


def load_place_details(conn, release_id: int) -> dict[str, PlaceDetail]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT object_id, name, somewhere_in_or_near_object_id,
                   somewhere_in_or_near_label
            FROM manto_entity_details
            WHERE release_record_id = %s
              AND substring(name from 1 for 1) = %s
            """,
            (release_id, PLACE_PREFIX),
        )
        rows = cursor.fetchall()
    return {
        str(row[0]): PlaceDetail(
            object_id=str(row[0]),
            name=row[1] or "",
            parent_id=str(row[2] or ""),
            parent_label=row[3] or "",
        )
        for row in rows
    }


def load_typed_edges(conn, release_id: int, *, pre_pausanias_only: bool) -> list[TypedEdge]:
    where = "AND e.is_pre_pausanias" if pre_pausanias_only else ""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT e.source_manto_id, e.target_manto_id, e.relation_type,
                   sd.name AS source_name, td.name AS target_name
            FROM manto_edges e
            LEFT JOIN manto_entity_details sd
              ON sd.release_record_id = e.release_record_id
             AND sd.object_id = e.source_manto_id
            LEFT JOIN manto_entity_details td
              ON td.release_record_id = e.release_record_id
             AND td.object_id = e.target_manto_id
            WHERE e.release_record_id = %s
              {where}
            """,
            (release_id,),
        )
        rows = cursor.fetchall()
    return [
        TypedEdge(
            source_id=str(row[0]),
            target_id=str(row[1]),
            relation_type=relation_key(row[2]),
            source_prefix=entity_prefix(row[3]),
            target_prefix=entity_prefix(row[4]),
        )
        for row in rows
    ]


def add_weighted_edge(graph: nx.Graph, source_id: str, target_id: str, relation_type: str) -> None:
    if not source_id or not target_id or source_id == target_id:
        return
    if graph.has_edge(source_id, target_id):
        graph[source_id][target_id]["weight"] += 1
        graph[source_id][target_id]["relations"].add(relation_type)
    else:
        graph.add_edge(source_id, target_id, weight=1, relations={relation_type})


def build_place_graph(
    place_details: dict[str, PlaceDetail],
    edges: list[TypedEdge],
) -> tuple[nx.Graph, dict[str, set[str]], dict[frozenset[str], set[str]]]:
    place_ids = set(place_details)
    graph = nx.Graph()
    graph.add_nodes_from(place_ids)
    direct_neighbors: dict[str, set[str]] = defaultdict(set)
    direct_relations: dict[frozenset[str], set[str]] = defaultdict(set)

    for edge in edges:
        if edge.relation_type in EXCLUDED_RELATIONS:
            continue
        if edge.source_prefix != PLACE_PREFIX or edge.target_prefix != PLACE_PREFIX:
            continue
        if edge.source_id not in place_ids or edge.target_id not in place_ids:
            continue
        add_weighted_edge(graph, edge.source_id, edge.target_id, edge.relation_type)
        direct_neighbors[edge.source_id].add(edge.target_id)
        direct_neighbors[edge.target_id].add(edge.source_id)
        direct_relations[frozenset((edge.source_id, edge.target_id))].add(edge.relation_type)

    for place_id, detail in place_details.items():
        if detail.parent_id and detail.parent_id in place_ids and detail.parent_id != place_id:
            add_weighted_edge(graph, place_id, detail.parent_id, "somewhere_in_or_near")
            direct_neighbors[place_id].add(detail.parent_id)
            direct_neighbors[detail.parent_id].add(place_id)
            direct_relations[frozenset((place_id, detail.parent_id))].add("somewhere_in_or_near")

    return graph, direct_neighbors, direct_relations


def build_parent_neighbors(place_details: dict[str, PlaceDetail]) -> dict[str, set[str]]:
    parent_groups: dict[str, set[str]] = defaultdict(set)
    for place_id, detail in place_details.items():
        if detail.parent_id:
            parent_groups[detail.parent_id].add(place_id)

    parent_neighbors: dict[str, set[str]] = defaultdict(set)
    for place_id, detail in place_details.items():
        if not detail.parent_id:
            continue
        siblings = parent_groups.get(detail.parent_id, set()) - {place_id}
        parent_neighbors[place_id].update(siblings)
        if detail.parent_id in place_details:
            parent_neighbors[place_id].add(detail.parent_id)
    return parent_neighbors


def build_place_person_maps(
    edges: list[TypedEdge],
) -> tuple[dict[str, set[str]], dict[str, dict[str, set[str]]]]:
    place_people: dict[str, set[str]] = defaultdict(set)
    place_action_people: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for edge in edges:
        if edge.relation_type in EXCLUDED_RELATIONS:
            continue
        place_id = ""
        person_id = ""
        if edge.source_prefix == PLACE_PREFIX and edge.target_prefix == PERSON_PREFIX:
            place_id = edge.source_id
            person_id = edge.target_id
        elif edge.source_prefix == PERSON_PREFIX and edge.target_prefix == PLACE_PREFIX:
            place_id = edge.target_id
            person_id = edge.source_id
        if not place_id or not person_id:
            continue

        place_people[place_id].add(person_id)
        action = canonical_action(edge.relation_type)
        if action:
            place_action_people[place_id][action].add(person_id)

    return place_people, place_action_people


def large_places(
    graph: nx.Graph,
    *,
    quantile: float,
) -> tuple[set[str], dict[str, int], dict[str, float]]:
    degree = {node: int(graph.degree(node)) for node in graph.nodes}
    pagerank = nx.pagerank(graph, weight="weight") if graph.number_of_edges() else {
        node: 0.0 for node in graph.nodes
    }
    degree_threshold = percentile_threshold([float(value) for value in degree.values()], quantile)
    pagerank_threshold = percentile_threshold(list(pagerank.values()), quantile)
    large = {
        node for node in graph.nodes
        if degree.get(node, 0) >= degree_threshold
        or pagerank.get(node, 0.0) >= pagerank_threshold
    }
    return large, degree, pagerank


def shared_action_patterns(
    own_actions: dict[str, set[str]],
    neighbor_actions: dict[str, set[str]],
) -> set[str]:
    shared: set[str] = set()
    for action in set(own_actions) & set(neighbor_actions):
        own_people = own_actions[action]
        neighbor_people = neighbor_actions[action]
        if (own_people - neighbor_people) and (neighbor_people - own_people):
            shared.add(action)
    return shared


def build_feature_rows(
    *,
    release_id: int,
    feature_set_version: str,
    links: list[dict],
    place_details: dict[str, PlaceDetail],
    direct_neighbors: dict[str, set[str]],
    direct_relations: dict[frozenset[str], set[str]],
    parent_neighbors: dict[str, set[str]],
    place_people: dict[str, set[str]],
    place_action_people: dict[str, dict[str, set[str]]],
    large_place_ids: set[str],
    place_degree: dict[str, int],
    place_pagerank: dict[str, float],
    pre_pausanias_only: bool,
) -> list[tuple]:
    timestamp = now_iso()
    rows: list[tuple] = []
    for link in links:
        node = str(link["manto_id"])
        local_neighbors = (direct_neighbors.get(node, set()) | parent_neighbors.get(node, set())) - {node}
        local_neighbors = {neighbor for neighbor in local_neighbors if neighbor in place_details}
        direct_neighbor_set = direct_neighbors.get(node, set()) & set(place_details)
        same_parent_set = parent_neighbors.get(node, set()) & set(place_details)
        large_neighbors = local_neighbors & large_place_ids

        own_people = place_people.get(node, set())
        own_actions = place_action_people.get(node, {})
        shared_people_neighbors = 0
        shared_people_large_neighbors = 0
        shared_people_all: set[str] = set()
        max_shared_people = 0
        shared_action_neighbors = 0
        shared_action_large_neighbors = 0
        shared_action_all: set[str] = set()
        shared_action_neighbor_patterns = 0
        max_shared_actions = 0

        for neighbor in local_neighbors:
            neighbor_people = place_people.get(neighbor, set())
            shared_people = own_people & neighbor_people
            if shared_people:
                shared_people_neighbors += 1
                shared_people_all.update(shared_people)
                max_shared_people = max(max_shared_people, len(shared_people))
                if neighbor in large_place_ids:
                    shared_people_large_neighbors += 1

            actions = shared_action_patterns(own_actions, place_action_people.get(neighbor, {}))
            if actions:
                shared_action_neighbors += 1
                shared_action_all.update(actions)
                shared_action_neighbor_patterns += len(actions)
                max_shared_actions = max(max_shared_actions, len(actions))
                if neighbor in large_place_ids:
                    shared_action_large_neighbors += 1

        strong_place_ties = 0
        for neighbor in direct_neighbor_set & large_place_ids:
            relations = direct_relations.get(frozenset((node, neighbor)), set())
            if relations & STRONG_PLACE_RELATIONS:
                strong_place_ties += 1

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
                int(place_degree.get(node, 0)),
                float(place_pagerank.get(node, 0.0)),
                int(len(local_neighbors)),
                int(len(direct_neighbor_set)),
                int(len(same_parent_set)),
                int(len(large_neighbors)),
                int(max((place_degree.get(neighbor, 0) for neighbor in large_neighbors), default=0)),
                float(max((place_pagerank.get(neighbor, 0.0) for neighbor in large_neighbors), default=0.0)),
                bool(large_neighbors),
                int(strong_place_ties),
                int(len(own_people)),
                int(len(own_actions)),
                int(shared_people_neighbors),
                int(len(shared_people_all)),
                int(max_shared_people),
                int(shared_people_large_neighbors),
                int(shared_action_neighbors),
                int(len(shared_action_all)),
                int(shared_action_neighbor_patterns),
                int(max_shared_actions),
                int(shared_action_large_neighbors),
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
            DELETE FROM manto_place_connectedness_features
            WHERE release_record_id = %s
              AND feature_set_version = %s
              AND pre_pausanias_only = %s
            """,
            (release_id, feature_set_version, pre_pausanias_only),
        )
        cursor.executemany(
            """
            INSERT INTO manto_place_connectedness_features (
                release_record_id, feature_set_version, reference_form, entity_type,
                english_transcription, manto_id, manto_label, pre_pausanias_only,
                place_graph_degree, place_graph_pagerank, local_place_neighbor_count,
                direct_place_neighbor_count, same_parent_place_neighbor_count,
                large_place_neighbor_count, large_place_max_degree,
                large_place_max_pagerank, has_large_place_neighbor,
                strong_place_tie_count, mythic_figure_count, action_pattern_count,
                shared_mythic_figure_neighbor_count, shared_mythic_figure_count,
                max_shared_mythic_figures_with_neighbor,
                shared_mythic_figure_large_place_neighbor_count,
                shared_action_neighbor_count, shared_action_pattern_count,
                shared_action_neighbor_pattern_count,
                max_shared_action_patterns_with_neighbor,
                shared_action_large_place_neighbor_count, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (
                release_record_id, feature_set_version, reference_form, entity_type, manto_id
            ) DO UPDATE
            SET english_transcription = EXCLUDED.english_transcription,
                manto_label = EXCLUDED.manto_label,
                pre_pausanias_only = EXCLUDED.pre_pausanias_only,
                place_graph_degree = EXCLUDED.place_graph_degree,
                place_graph_pagerank = EXCLUDED.place_graph_pagerank,
                local_place_neighbor_count = EXCLUDED.local_place_neighbor_count,
                direct_place_neighbor_count = EXCLUDED.direct_place_neighbor_count,
                same_parent_place_neighbor_count = EXCLUDED.same_parent_place_neighbor_count,
                large_place_neighbor_count = EXCLUDED.large_place_neighbor_count,
                large_place_max_degree = EXCLUDED.large_place_max_degree,
                large_place_max_pagerank = EXCLUDED.large_place_max_pagerank,
                has_large_place_neighbor = EXCLUDED.has_large_place_neighbor,
                strong_place_tie_count = EXCLUDED.strong_place_tie_count,
                mythic_figure_count = EXCLUDED.mythic_figure_count,
                action_pattern_count = EXCLUDED.action_pattern_count,
                shared_mythic_figure_neighbor_count = EXCLUDED.shared_mythic_figure_neighbor_count,
                shared_mythic_figure_count = EXCLUDED.shared_mythic_figure_count,
                max_shared_mythic_figures_with_neighbor =
                    EXCLUDED.max_shared_mythic_figures_with_neighbor,
                shared_mythic_figure_large_place_neighbor_count =
                    EXCLUDED.shared_mythic_figure_large_place_neighbor_count,
                shared_action_neighbor_count = EXCLUDED.shared_action_neighbor_count,
                shared_action_pattern_count = EXCLUDED.shared_action_pattern_count,
                shared_action_neighbor_pattern_count =
                    EXCLUDED.shared_action_neighbor_pattern_count,
                max_shared_action_patterns_with_neighbor =
                    EXCLUDED.max_shared_action_patterns_with_neighbor,
                shared_action_large_place_neighbor_count =
                    EXCLUDED.shared_action_large_place_neighbor_count,
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
        print("Loading place details...", flush=True)
        place_details = load_place_details(conn, release_id)
        print("Loading typed MANTO edges...", flush=True)
        edges = load_typed_edges(conn, release_id, pre_pausanias_only=pre_pausanias_only)
        if args.target_source == "linked-proper-nouns":
            print("Loading Pausanias-MANTO links...", flush=True)
            links = load_links(conn, release_id)
        else:
            print("Loading MANTO Pausanias place-status targets...", flush=True)
            links = load_manto_status_targets(
                conn,
                release_id,
                label_source_version=args.label_source_version,
            )

        print("Building place graph and local neighbor pools...", flush=True)
        place_graph, direct_neighbors, direct_relations = build_place_graph(place_details, edges)
        parent_neighbors = build_parent_neighbors(place_details)
        print("Building place-person story maps...", flush=True)
        place_people, place_action_people = build_place_person_maps(edges)
        large_place_ids, place_degree, place_pagerank = large_places(
            place_graph,
            quantile=args.large_place_quantile,
        )
        rows = build_feature_rows(
            release_id=release_id,
            feature_set_version=args.feature_set_version,
            links=links,
            place_details=place_details,
            direct_neighbors=direct_neighbors,
            direct_relations=direct_relations,
            parent_neighbors=parent_neighbors,
            place_people=place_people,
            place_action_people=place_action_people,
            large_place_ids=large_place_ids,
            place_degree=place_degree,
            place_pagerank=place_pagerank,
            pre_pausanias_only=pre_pausanias_only,
        )
        print("Saving connectedness feature rows...", flush=True)
        save_rows(
            conn,
            release_id=release_id,
            feature_set_version=args.feature_set_version,
            pre_pausanias_only=pre_pausanias_only,
            rows=rows,
        )
    print(
        f"Saved {len(rows):,} MANTO connectedness rows for release {release_id}; "
        f"place graph={place_graph.number_of_nodes():,} nodes/"
        f"{place_graph.number_of_edges():,} edges; "
        f"large-place proxy={len(large_place_ids):,} places "
        f"({args.large_place_quantile:.2f} quantile)."
    )


if __name__ == "__main__":
    main()
