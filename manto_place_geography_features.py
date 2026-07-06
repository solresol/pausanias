#!/usr/bin/env python
"""Build geography-network hybrid features for Pausanias places.

Combines the MANTO narrative place graph with Pleiades representative
coordinates: how physically far is the nearest large place, how localized is a
place's mythology (fraction of narrative ties within 25/50/100 km), and how
dense the surrounding mythic landscape is.
"""

from __future__ import annotations

import argparse
import math
from datetime import datetime, timezone

from manto_place_connectedness_features import (
    build_parent_neighbors,
    build_place_graph,
    large_places,
    load_place_details,
    load_typed_edges,
    local_neighbors_for,
)
from manto_place_network_features import (
    latest_release_id,
    load_links,
    load_manto_status_targets,
)
from pausanias_db import add_database_argument, connect, initialize_schema


FEATURE_SET_VERSION = "manto-place-geography-v1"
LABEL_SOURCE_VERSION = "manto-entity-info-v1"
EARTH_RADIUS_KM = 6371.0088
# Sentinel for "no coordinates available", far beyond any real distance in Greece.
UNKNOWN_DISTANCE_KM = 9999.0


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
    )
    parser.add_argument("--label-source-version", default=LABEL_SOURCE_VERSION)
    parser.add_argument(
        "--include-non-pre-pausanias",
        action="store_true",
        help="Use all MANTO edges. Default is strict pre-Pausanias-only edges.",
    )
    parser.add_argument("--large-place-quantile", type=float, default=0.95)
    return parser.parse_args()


def haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    phi_a = math.radians(lat_a)
    phi_b = math.radians(lat_b)
    delta_phi = math.radians(lat_b - lat_a)
    delta_lambda = math.radians(lon_b - lon_a)
    half_chord = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * math.asin(math.sqrt(half_chord))


def load_place_coordinates(conn, release_id: int) -> dict[str, tuple[float, float]]:
    """Map MANTO place object ids to Pleiades representative coordinates."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT d.object_id, p.representative_latitude, p.representative_longitude
            FROM manto_entity_details d
            JOIN pleiades_places p ON p.pleiades_id = d.pleiades_id
            WHERE d.release_record_id = %s
              AND d.pleiades_id IS NOT NULL
              AND d.pleiades_id <> ''
              AND p.representative_latitude IS NOT NULL
              AND p.representative_longitude IS NOT NULL
            """,
            (release_id,),
        )
        rows = cursor.fetchall()
    return {str(row[0]): (float(row[1]), float(row[2])) for row in rows}


def nearest_distance_km(
    origin: tuple[float, float],
    candidates: dict[str, tuple[float, float]],
    *,
    exclude: str,
) -> float:
    best = UNKNOWN_DISTANCE_KM
    for place_id, coordinates in candidates.items():
        if place_id == exclude:
            continue
        distance = haversine_km(origin[0], origin[1], coordinates[0], coordinates[1])
        if distance < best:
            best = distance
    return best


def build_feature_rows(
    *,
    release_id: int,
    feature_set_version: str,
    links: list[dict],
    place_coordinates: dict[str, tuple[float, float]],
    large_place_ids: set[str],
    local_neighbor_sets: dict[str, set[str]],
    pre_pausanias_only: bool,
) -> list[tuple]:
    timestamp = now_iso()
    large_coordinates = {
        place_id: coordinates
        for place_id, coordinates in place_coordinates.items()
        if place_id in large_place_ids
    }
    rows: list[tuple] = []
    for link in links:
        node = str(link["manto_id"])
        origin = place_coordinates.get(node)
        has_coordinates = origin is not None
        nearest_large = UNKNOWN_DISTANCE_KM
        nearest_any = UNKNOWN_DISTANCE_KM
        places_within_50km = 0
        neighbor_distances: list[float] = []
        if origin is not None:
            nearest_large = nearest_distance_km(origin, large_coordinates, exclude=node)
            nearest_any = nearest_distance_km(origin, place_coordinates, exclude=node)
            for place_id, coordinates in place_coordinates.items():
                if place_id == node:
                    continue
                if haversine_km(origin[0], origin[1], coordinates[0], coordinates[1]) <= 50.0:
                    places_within_50km += 1
            for neighbor in local_neighbor_sets.get(node, set()):
                neighbor_coordinates = place_coordinates.get(neighbor)
                if neighbor_coordinates is None:
                    continue
                neighbor_distances.append(
                    haversine_km(
                        origin[0], origin[1],
                        neighbor_coordinates[0], neighbor_coordinates[1],
                    )
                )
        within_25 = sum(1 for distance in neighbor_distances if distance <= 25.0)
        within_50 = sum(1 for distance in neighbor_distances if distance <= 50.0)
        within_100 = sum(1 for distance in neighbor_distances if distance <= 100.0)
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
                bool(has_coordinates),
                float(nearest_large),
                float(nearest_any),
                int(places_within_50km),
                int(len(neighbor_distances)),
                float(
                    sum(neighbor_distances) / len(neighbor_distances)
                    if neighbor_distances
                    else UNKNOWN_DISTANCE_KM
                ),
                float(min(neighbor_distances, default=UNKNOWN_DISTANCE_KM)),
                float(max(neighbor_distances, default=UNKNOWN_DISTANCE_KM)),
                int(within_25),
                int(within_50),
                int(within_100),
                float(within_50 / len(neighbor_distances) if neighbor_distances else 0.0),
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
            DELETE FROM manto_place_geography_features
            WHERE release_record_id = %s
              AND feature_set_version = %s
              AND pre_pausanias_only = %s
            """,
            (release_id, feature_set_version, pre_pausanias_only),
        )
        cursor.executemany(
            """
            INSERT INTO manto_place_geography_features (
                release_record_id, feature_set_version, reference_form, entity_type,
                english_transcription, manto_id, manto_label, pre_pausanias_only,
                has_coordinates, geo_distance_to_nearest_large_place_km,
                geo_distance_to_nearest_place_km, places_within_50km_count,
                narrative_neighbor_count_with_coords,
                mean_narrative_neighbor_distance_km,
                min_narrative_neighbor_distance_km,
                max_narrative_neighbor_distance_km,
                neighbors_within_25km_count, neighbors_within_50km_count,
                neighbors_within_100km_count, local_tie_fraction_50km, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s)
            ON CONFLICT (
                release_record_id, feature_set_version, reference_form, entity_type, manto_id
            ) DO UPDATE
            SET english_transcription = EXCLUDED.english_transcription,
                manto_label = EXCLUDED.manto_label,
                pre_pausanias_only = EXCLUDED.pre_pausanias_only,
                has_coordinates = EXCLUDED.has_coordinates,
                geo_distance_to_nearest_large_place_km =
                    EXCLUDED.geo_distance_to_nearest_large_place_km,
                geo_distance_to_nearest_place_km = EXCLUDED.geo_distance_to_nearest_place_km,
                places_within_50km_count = EXCLUDED.places_within_50km_count,
                narrative_neighbor_count_with_coords =
                    EXCLUDED.narrative_neighbor_count_with_coords,
                mean_narrative_neighbor_distance_km =
                    EXCLUDED.mean_narrative_neighbor_distance_km,
                min_narrative_neighbor_distance_km =
                    EXCLUDED.min_narrative_neighbor_distance_km,
                max_narrative_neighbor_distance_km =
                    EXCLUDED.max_narrative_neighbor_distance_km,
                neighbors_within_25km_count = EXCLUDED.neighbors_within_25km_count,
                neighbors_within_50km_count = EXCLUDED.neighbors_within_50km_count,
                neighbors_within_100km_count = EXCLUDED.neighbors_within_100km_count,
                local_tie_fraction_50km = EXCLUDED.local_tie_fraction_50km,
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
            links = load_links(conn, release_id)
        else:
            links = load_manto_status_targets(
                conn,
                release_id,
                label_source_version=args.label_source_version,
            )
        print("Loading Pleiades coordinates...", flush=True)
        place_coordinates = load_place_coordinates(conn, release_id)
        if not place_coordinates:
            raise RuntimeError(
                "No MANTO places have Pleiades coordinates; "
                "run import_pleiades_coordinates.py first."
            )
        print("Building place graph...", flush=True)
        place_graph, direct_neighbors, _ = build_place_graph(place_details, edges)
        parent_neighbors = build_parent_neighbors(place_details)
        large_place_ids, _, _ = large_places(
            place_graph,
            quantile=args.large_place_quantile,
        )
        local_neighbor_sets = {
            str(link["manto_id"]): local_neighbors_for(
                str(link["manto_id"]), place_details, direct_neighbors, parent_neighbors
            )
            for link in links
        }
        rows = build_feature_rows(
            release_id=release_id,
            feature_set_version=args.feature_set_version,
            links=links,
            place_coordinates=place_coordinates,
            large_place_ids=large_place_ids,
            local_neighbor_sets=local_neighbor_sets,
            pre_pausanias_only=pre_pausanias_only,
        )
        print("Saving geography feature rows...", flush=True)
        save_rows(
            conn,
            release_id=release_id,
            feature_set_version=args.feature_set_version,
            pre_pausanias_only=pre_pausanias_only,
            rows=rows,
        )
    with_coordinates = sum(1 for row in rows if row[8])
    print(
        f"Saved {len(rows):,} geography rows for release {release_id}; "
        f"{with_coordinates:,} targets have coordinates out of "
        f"{len(place_coordinates):,} coordinate-bearing MANTO places."
    )


if __name__ == "__main__":
    main()
