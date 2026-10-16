"""Pilot-5 distances and location-held-out EC baselines on the approved network.

Uses the user-approved OSM + KML geometry as an undirected, unweighted-by-flow
waterway graph. Each snapped monitoring point is inserted along its edge.
Campaigns are evaluated independently; no campaign dates or later covariates
are inferred.
"""

from __future__ import annotations

from collections import defaultdict
import csv
from datetime import date
import hashlib
import heapq
import json
import math
from pathlib import Path

from qgis.core import QgsApplication, QgsGeometry, QgsPointXY, QgsSpatialIndex, QgsVectorLayer


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/gis/go_cong_network/pilot5_baselines"
NETWORK = ROOT / "data/processed/gis/go_cong_network/go_cong_user_trace_candidate_32648.gpkg"
KML = ROOT / "data/raw/gis/user_review_20261017/ban_do_nhanh_song_v2.kml"
EC = ROOT / "data/processed/gis/tiengiang_monitoring/ec_campaigns_136.csv"
CODES = ("NM29", "NM30", "NM31", "NM32", "NM34")
CAMPAIGNS = ("I", "II", "III", "IV")
MODELS = ("Nearest", "Euclidean-IDW", "River-IDW")


def node(point: QgsPointXY) -> tuple[int, int]:
    return round(point.x() * 100), round(point.y() * 100)


def add_edge(graph: dict, left: tuple, right: tuple, length: float) -> None:
    if length < 0:
        raise ValueError("Negative edge length")
    graph[left].append((right, length))
    graph[right].append((left, length))


def shortest_paths(graph: dict, start: tuple) -> dict:
    distances = {start: 0.0}
    queue = [(0.0, start)]
    while queue:
        current, here = heapq.heappop(queue)
        if current > distances[here]:
            continue
        for neighbor, weight in graph[here]:
            candidate = current + weight
            if candidate < distances.get(neighbor, math.inf):
                distances[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    return distances


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    app = QgsApplication([], False)
    app.initQgis()
    edges = QgsVectorLayer(f"{NETWORK}|layername=augmented_network_edges_candidate", "edges", "ogr")
    sites = QgsVectorLayer(f"{ROOT / 'data/processed/gis/go_cong_network/go_cong_waterway_network_32648.gpkg'}|layername=pilot5_reviewed_coordinates", "sites", "ogr")
    snaps = QgsVectorLayer(f"{NETWORK}|layername=pilot5_augmented_snap_candidates", "snaps", "ogr")
    if not all(layer.isValid() for layer in (edges, sites, snaps)):
        raise RuntimeError("Missing network, reviewed site, or snap layer")
    if edges.crs().authid() != "EPSG:32648" or sites.crs().authid() != "EPSG:32648":
        raise RuntimeError("Expected metric EPSG:32648 layers")

    edge_rows = {feature.id(): feature for feature in edges.getFeatures()}
    index = QgsSpatialIndex(edges.getFeatures())
    graph = defaultdict(list)
    for edge in edge_rows.values():
        start, end = edge.geometry().asPolyline()
        add_edge(graph, node(start), node(end), edge.geometry().length())

    original = {feature["site_code"]: feature.geometry() for feature in sites.getFeatures()}
    snapped = {feature["site_code"]: feature for feature in snaps.getFeatures()}
    if set(original) != set(CODES) or set(snapped) != set(CODES):
        raise RuntimeError("Pilot site set differs from the five approved sites")

    edge_stations = defaultdict(list)
    snap_info = {}
    for code in CODES:
        point = snapped[code].geometry()
        candidates = [edge_rows[identifier] for identifier in index.nearestNeighbor(point.asPoint(), 32)]
        edge = min(candidates, key=lambda item: item.geometry().distance(point))
        residual = edge.geometry().distance(point)
        if residual > 0.02:
            raise RuntimeError(f"Snapped point {code} is {residual:.3f} m from chosen edge")
        along = edge.geometry().lineLocatePoint(point)
        if along < 0:
            raise RuntimeError(f"Could not locate {code} along edge")
        start, end = edge.geometry().asPolyline()
        length = edge.geometry().length()
        station = ("site", code)
        add_edge(graph, station, node(start), along)
        add_edge(graph, station, node(end), length - along)
        edge_stations[edge.id()].append((along, station))
        snap_info[code] = {"edge_id": int(edge["edge_id"]),
                           "component": int(edge["component"]),
                           "snap_m": float(snapped[code]["aug_snap_m"])}
    for stations in edge_stations.values():
        for (along_a, station_a), (along_b, station_b) in zip(sorted(stations), sorted(stations)[1:]):
            add_edge(graph, station_a, station_b, along_b - along_a)

    river = {}
    for code in CODES:
        paths = shortest_paths(graph, ("site", code))
        for other in CODES:
            river[code, other] = paths.get(("site", other), math.inf)
    euclidean = {(a, b): original[a].distance(original[b]) for a in CODES for b in CODES}

    distances = []
    for i, a in enumerate(CODES):
        for b in CODES[i + 1:]:
            direct = euclidean[a, b]
            route = river[a, b]
            distances.append({
                "site_a": a, "site_b": b,
                "euclidean_m": round(direct, 3),
                "river_m": round(route, 3) if math.isfinite(route) else "",
                "river_over_euclidean": round(route / direct, 4) if math.isfinite(route) else "",
                "snap_a_m": round(snap_info[a]["snap_m"], 3),
                "snap_b_m": round(snap_info[b]["snap_m"], 3),
                "connected": math.isfinite(route),
            })

    with EC.open(newline="", encoding="utf-8-sig") as handle:
        all_ec = list(csv.DictReader(handle))
    observed = {(row["site_code"], row["campaign"]): float(row["ec_ms_m"])
                for row in all_ec if row["site_code"] in CODES and row["campaign"] in CAMPAIGNS}
    if len(observed) != len(CODES) * len(CAMPAIGNS):
        raise RuntimeError("Incomplete EC I-IV observations for pilot five")

    predictions = []
    for campaign in CAMPAIGNS:
        for target in CODES:
            for model in MODELS:
                metric = river if model == "River-IDW" else euclidean
                donors = [(code, metric[target, code], observed[code, campaign])
                          for code in CODES if code != target and math.isfinite(metric[target, code])]
                if not donors:
                    estimate = None
                    nearest = ""
                else:
                    nearest = min(donors, key=lambda item: (item[1], item[0]))[0]
                    if model == "Nearest":
                        estimate = observed[nearest, campaign]
                    elif any(distance < 1e-9 for _, distance, _ in donors):
                        coincident = [value for _, distance, value in donors if distance < 1e-9]
                        estimate = sum(coincident) / len(coincident)
                    else:
                        weights = [1 / distance ** 2 for _, distance, _ in donors]
                        estimate = sum(weight * donor[2] for weight, donor in zip(weights, donors)) / sum(weights)
                truth = observed[target, campaign]
                predictions.append({
                    "campaign": campaign, "held_out_site": target, "model": model,
                    "observed_ms_m": round(truth, 6),
                    "predicted_ms_m": round(estimate, 6) if estimate is not None else "",
                    "absolute_error_ms_m": round(abs(estimate - truth), 6) if estimate is not None else "",
                    "squared_error_ms_m2": round((estimate - truth) ** 2, 6) if estimate is not None else "",
                    "donor_count": len(donors), "nearest_donor": nearest,
                })

    metrics = []
    for campaign in (*CAMPAIGNS, "ALL"):
        for model in MODELS:
            selected = [row for row in predictions if row["model"] == model
                        and (campaign == "ALL" or row["campaign"] == campaign)
                        and row["predicted_ms_m"] != ""]
            metrics.append({
                "campaign": campaign, "model": model,
                "n_predictions": len(selected),
                "mae_ms_m": round(sum(row["absolute_error_ms_m"] for row in selected) / len(selected), 3) if selected else "",
                "rmse_ms_m": round(math.sqrt(sum(row["squared_error_ms_m2"] for row in selected) / len(selected)), 3) if selected else "",
            })

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "pilot5_pairwise_distances.csv", distances)
    write_csv(OUT / "pilot5_lolo_predictions.csv", predictions)
    write_csv(OUT / "pilot5_lolo_metrics.csv", metrics)
    manifest = {
        "scenario": "USER_APPROVED_NETWORK_2026-10-17",
        "crs": "EPSG:32648", "sites": CODES, "campaigns": CAMPAIGNS,
        "distance_definition": "Shortest undirected path along noded OSM + user KML centreline, between perpendicular snap positions; Euclidean distance between reviewed site coordinates",
        "network_geometry_source": str(NETWORK),
        "user_kml": str(KML), "user_kml_sha256": hashlib.sha256(KML.read_bytes()).hexdigest(),
        "ec_source": str(EC), "ec_unit": "mS/m",
        "validation": "Leave one location out, independently within each campaign; IDW power fixed at 2; no parameter tuning",
        "campaign_date_known": False,
        "interpretation_limit": "User-approved mapped connectivity; OSM and KML intersections, sluice states, direction, tide, and flow have no independent hydrological validation. Scores are internal interpolation baselines, not EC-at-gate predictive validation.",
        "graph_nodes": len(graph), "all_site_pairs_connected": all(row["connected"] for row in distances),
        "output_files": ["pilot5_pairwise_distances.csv", "pilot5_lolo_predictions.csv", "pilot5_lolo_metrics.csv"],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"connected_pairs": sum(row["connected"] for row in distances),
                      "pairs": len(distances), "predictions": len(predictions),
                      "metrics": metrics, "out": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
