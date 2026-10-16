"""Pilot-5 topology sensitivity: preserve or isolate KML/OSM crossing 510175774.

Scenario B splits the single geometric crossing into two graph nodes, one for
each source line. It never creates a straight-line substitute for a missing
river route. Baseline v1 files are read only.
"""

from __future__ import annotations

from collections import defaultdict
import csv
import heapq
import itertools
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from qgis.core import (QgsApplication, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsGeometry, QgsPointXY,
                       QgsProject, QgsSpatialIndex, QgsVectorLayer)


ROOT = Path(__file__).resolve().parents[1]
NET = ROOT / "data/processed/gis/go_cong_network/go_cong_user_trace_candidate_32648.gpkg"
BASE = ROOT / "data/processed/gis/go_cong_network/go_cong_waterway_network_32648.gpkg"
KML = ROOT / "data/raw/gis/user_review_20261017/ban_do_nhanh_song_v2.kml"
EC = ROOT / "data/processed/gis/tiengiang_monitoring/ec_campaigns_136.csv"
FROZEN = ROOT / "data/processed/gis/go_cong_network/pilot5_baselines/pilot5_pairwise_distances.csv"
OUT = ROOT / "data/processed/gis/go_cong_network/pilot5_topology_scenarios"
CODES = ("NM29", "NM30", "NM31", "NM32", "NM34")
CAMPAIGNS = ("I", "II", "III", "IV")


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def save_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def node(point):
    return round(point.x() * 100), round(point.y() * 100)


def add(graph, a, b, distance):
    graph[a].append((b, distance))
    graph[b].append((a, distance))


def distance(graph, start, goal):
    count = itertools.count()
    queue = [(0.0, next(count), start)]
    best = {start: 0.0}
    while queue:
        length, _, here = heapq.heappop(queue)
        if length > best[here]:
            continue
        if here == goal:
            return length
        for there, weight in graph[here]:
            trial = length + weight
            if trial < best.get(there, math.inf):
                best[there] = trial
                heapq.heappush(queue, (trial, next(count), there))
    return math.inf


def predict(target, values, distances, power):
    donors = sorted(((code, distances[target, code], values[code])
                     for code in CODES if code != target and math.isfinite(distances[target, code])),
                    key=lambda row: (row[1], row[0]))
    if not donors:
        return None, None, 0
    if power is None:
        return donors[0][2], donors[0][0], len(donors)
    zeros = [row[2] for row in donors if row[1] < 1e-9]
    if zeros:
        return sum(zeros) / len(zeros), donors[0][0], len(donors)
    weights = [1 / row[1] ** power for row in donors]
    return sum(w * row[2] for w, row in zip(weights, donors)) / sum(weights), donors[0][0], len(donors)


def main():
    app = QgsApplication([], False)
    app.initQgis()
    crs_wgs = QgsCoordinateReferenceSystem("EPSG:4326")
    crs_m = QgsCoordinateReferenceSystem("EPSG:32648")
    forward = QgsCoordinateTransform(crs_wgs, crs_m, QgsProject.instance().transformContext())
    backward = QgsCoordinateTransform(crs_m, crs_wgs, QgsProject.instance().transformContext())
    edges = QgsVectorLayer(f"{NET}|layername=augmented_network_edges_candidate", "edges", "ogr")
    snaps = QgsVectorLayer(f"{NET}|layername=pilot5_augmented_snap_candidates", "snaps", "ogr")
    original = QgsVectorLayer(f"{BASE}|layername=pilot5_reviewed_coordinates", "original", "ogr")
    osm = QgsVectorLayer(f"{BASE}|layername=waterways_osm_raw", "osm", "ogr")
    if not all(layer.isValid() for layer in (edges, snaps, original, osm)):
        raise RuntimeError("Missing network, snap, reviewed site, or OSM layer")
    osm_way = next((feature for feature in osm.getFeatures() if int(feature["osm_id"]) == 510175774), None)
    if osm_way is None:
        raise RuntimeError("OSM way 510175774 was not found")
    root = ET.parse(KML).getroot()
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    traces = []
    for placemark in root.findall(".//k:Placemark", ns):
        raw = placemark.findtext(".//k:LineString/k:coordinates", default="", namespaces=ns)
        if raw.strip():
            line = QgsGeometry.fromPolylineXY([QgsPointXY(*map(float, item.split(",")[:2]))
                                               for item in raw.split()])
            line.transform(forward)
            traces.append(line)
    if len(traces) != 4:
        raise RuntimeError("Expected four approved KML lines")
    crossing = traces[0].intersection(osm_way.geometry())
    if crossing.isEmpty() or crossing.type() != 0:
        raise RuntimeError("Expected point crossing(s) between trace 1 and OSM 510175774")
    points = crossing.asMultiPoint() if crossing.isMultipart() else [crossing.asPoint()]
    route_layer = QgsVectorLayer(str(ROOT / "data/processed/gis/go_cong_network/pilot5_route_audit/pilot5_shortest_routes.geojson"),
                                 "routes", "ogr")
    route_feature = next((f for f in route_layer.getFeatures()
                          if f["site_a"] == "NM29" and f["site_b"] == "NM34"), None)
    if route_feature is None:
        raise RuntimeError("NM29-NM34 audited route missing")
    route_geom = QgsGeometry(route_feature.geometry())
    route_geom.transform(forward)
    crossing_xy = min(points, key=lambda p: route_geom.distance(QgsGeometry.fromPointXY(QgsPointXY(p))))
    if route_geom.distance(QgsGeometry.fromPointXY(QgsPointXY(crossing_xy))) > 0.05:
        raise RuntimeError("No crossing of trace 1 / OSM 510175774 lies on audited route")
    crossing_keys = {node(p) for p in points}
    if len(crossing_keys) != len(points):
        raise RuntimeError("Crossings collapse under centimeter network node precision")
    key = node(crossing_xy)
    edge_map = {feature.id(): feature for feature in edges.getFeatures()}
    index = QgsSpatialIndex(edges.getFeatures())
    incident = []
    graph_a, graph_b = defaultdict(list), defaultdict(list)
    for edge in edge_map.values():
        a, b = edge.geometry().asPolyline()
        ka, kb = node(a), node(b)
        weight = edge.geometry().length()
        add(graph_a, ka, kb, weight)
        crossing_ends = crossing_keys.intersection((ka, kb))
        if crossing_ends:
            midpoint = edge.geometry().interpolate(weight / 2)
            kml = traces[0].distance(midpoint) < 0.001
            osm_match = osm_way.geometry().distance(midpoint) < 0.001
            if not (kml or osm_match):
                raise RuntimeError(f"Incident edge {edge.id()} on neither source line")
            for crossing_key in crossing_ends:
                incident.append({"crossing_x_cm": crossing_key[0], "crossing_y_cm": crossing_key[1],
                                 "edge_fid": edge.id(), "edge_id": int(edge["edge_id"]),
                                 "length_m": round(weight, 3),
                                 "source_side": "BOTH" if kml and osm_match else "KML" if kml else "OSM"})
            for side, active in (("KML", kml), ("OSM", osm_match)):
                if active:
                    sa = (side, *ka) if ka in crossing_keys else ka
                    sb = (side, *kb) if kb in crossing_keys else kb
                    add(graph_b, sa, sb, weight)
        else:
            add(graph_b, ka, kb, weight)
    for crossing_key in crossing_keys:
        sides = {row["source_side"] for row in incident
                 if (row["crossing_x_cm"], row["crossing_y_cm"]) == crossing_key}
        if not sides.intersection(("KML", "BOTH")) or not sides.intersection(("OSM", "BOTH")):
            raise RuntimeError(f"Crossing {crossing_key} has incomplete source incidence: {sides}")

    for feature in snaps.getFeatures():
        code = feature["site_code"]
        point = feature.geometry()
        nearby = [edge_map[fid] for fid in index.nearestNeighbor(point.asPoint(), 32)]
        edge = min(nearby, key=lambda item: item.geometry().distance(point))
        if edge.geometry().distance(point) > 0.02:
            raise RuntimeError(f"Station {code} not on network")
        a, b = edge.geometry().asPolyline()
        along = edge.geometry().lineLocatePoint(point)
        station = ("site", code)
        for graph, is_b in ((graph_a, False), (graph_b, True)):
            ka, kb = node(a), node(b)
            if is_b and any(row["edge_fid"] == edge.id() and row["source_side"] in ("KML", "BOTH")
                            for row in incident):
                ka = ("KML", *ka) if ka in crossing_keys else ka
                kb = ("KML", *kb) if kb in crossing_keys else kb
            add(graph, station, ka, along)
            add(graph, station, kb, edge.geometry().length() - along)

    site_geom = {feature["site_code"]: feature.geometry() for feature in original.getFeatures()}
    frozen = {(row["site_a"], row["site_b"]): float(row["river_m"]) for row in read_csv(FROZEN)}
    distances = {}
    pair_rows = []
    for scenario, graph in (("A_connected", graph_a), ("B_crossing_closed", graph_b)):
        for code in CODES:
            distances[scenario, code, code] = 0.0
        for i, a in enumerate(CODES):
            for b in CODES[i + 1:]:
                river = distance(graph, ("site", a), ("site", b))
                euclidean = site_geom[a].distance(site_geom[b])
                distances[scenario, a, b] = distances[scenario, b, a] = river
                if scenario == "A_connected" and not math.isclose(river, frozen[a, b], abs_tol=0.002):
                    raise RuntimeError(f"Scenario A diverges from frozen baseline for {a}-{b}")
                pair_rows.append({"scenario": scenario, "site_a": a, "site_b": b,
                                  "connected": math.isfinite(river),
                                  "river_m": round(river, 3) if math.isfinite(river) else "",
                                  "euclidean_m": round(euclidean, 3),
                                  "river_distance_status": "AVAILABLE" if math.isfinite(river) else "NO_GRAPH_PATH"})

    observations = {(row["site_code"], row["campaign"]): float(row["ec_ms_m"])
                    for row in read_csv(EC) if row["site_code"] in CODES and row["campaign"] in CAMPAIGNS}
    if len(observations) != 20:
        raise RuntimeError("Missing pilot-5 observations")
    predictions = []
    for scenario in ("A_connected", "B_crossing_closed"):
        river = {(a, b): distances[scenario, a, b] for a in CODES for b in CODES}
        euclidean = {(a, b): 0.0 if a == b else site_geom[a].distance(site_geom[b])
                     for a in CODES for b in CODES}
        for campaign in CAMPAIGNS:
            values = {code: observations[code, campaign] for code in CODES}
            for target in CODES:
                for model, matrix, power in (("Nearest", euclidean, None),
                                             ("Euclidean-IDW", euclidean, 2),
                                             ("River-Nearest", river, None),
                                             ("River-IDW", river, 2)):
                    pred, donor, n_donors = predict(target, values, matrix, power)
                    observed = values[target]
                    predictions.append({"scenario": scenario, "campaign": campaign,
                                        "held_out_site": target, "model": model,
                                        "observed_ms_m": observed,
                                        "predicted_ms_m": round(pred, 6) if pred is not None else "",
                                        "error_ms_m": round(pred - observed, 6) if pred is not None else "",
                                        "absolute_error_ms_m": round(abs(pred - observed), 6) if pred is not None else "",
                                        "donor_count": n_donors, "nearest_donor": donor or "",
                                        "prediction_status": "AVAILABLE" if pred is not None else "NO_RIVER_DONOR_REACHABLE"})

    metrics = []
    for subset_name, accepted in (("all_eligible", set(CODES)),
                                  ("common_four_sites", set(CODES) - {"NM29"})):
        for scenario in ("A_connected", "B_crossing_closed"):
            for campaign in (*CAMPAIGNS, "ALL"):
                for model in ("Nearest", "Euclidean-IDW", "River-Nearest", "River-IDW"):
                    group = [row for row in predictions if row["scenario"] == scenario
                             and row["model"] == model and row["held_out_site"] in accepted
                             and (campaign == "ALL" or row["campaign"] == campaign)]
                    valid = [float(row["error_ms_m"]) for row in group if row["prediction_status"] == "AVAILABLE"]
                    metrics.append({"subset": subset_name, "scenario": scenario,
                                    "campaign": campaign, "model": model,
                                    "eligible_n": len(group), "predicted_n": len(valid),
                                    "coverage_pct": round(100 * len(valid) / len(group), 1),
                                    "mae_ms_m": round(sum(abs(e) for e in valid) / len(valid), 3) if valid else "",
                                    "rmse_ms_m": round(math.sqrt(sum(e * e for e in valid) / len(valid)), 3) if valid else "",
                                    "metric_scope": "AVAILABLE_PREDICTIONS_ONLY"})

    site_metrics = []
    for scenario in ("A_connected", "B_crossing_closed"):
        for site in CODES:
            for model in ("Nearest", "Euclidean-IDW", "River-Nearest", "River-IDW"):
                group = [row for row in predictions if row["scenario"] == scenario
                         and row["held_out_site"] == site and row["model"] == model]
                valid = [float(row["error_ms_m"]) for row in group if row["prediction_status"] == "AVAILABLE"]
                site_metrics.append({"scenario": scenario, "site_code": site, "model": model,
                                     "eligible_n": len(group), "predicted_n": len(valid),
                                     "mae_ms_m": round(sum(abs(e) for e in valid) / len(valid), 3) if valid else "",
                                     "rmse_ms_m": round(math.sqrt(sum(e * e for e in valid) / len(valid)), 3) if valid else ""})

    pair_deltas = []
    for i, a in enumerate(CODES):
        for b in CODES[i + 1:]:
            da = distances["A_connected", a, b]
            db = distances["B_crossing_closed", a, b]
            pair_deltas.append({"site_a": a, "site_b": b, "river_a_m": round(da, 3),
                                "river_b_m": round(db, 3) if math.isfinite(db) else "",
                                "b_minus_a_m": round(db-da, 3) if math.isfinite(db) else "",
                                "scenario_b_connected": math.isfinite(db)})

    point = QgsGeometry.fromPointXY(QgsPointXY(crossing_xy))
    point.transform(backward)
    crossing_feature = {"type": "Feature", "geometry": json.loads(point.asJson()),
                        "properties": {"osm_id": 510175774, "trace_id": 1,
                                       "graph_node_x_cm": key[0], "graph_node_y_cm": key[1],
                                       "same_way_intersection_count": len(crossing_keys),
                                       "scenario_b_action": "SPLIT_ALL_SAME_WAY_CROSSING_NODES"}}
    OUT.mkdir(parents=True, exist_ok=True)
    save_csv(OUT / "scenario_pairwise_distances.csv", pair_rows)
    save_csv(OUT / "scenario_lolo_predictions.csv", predictions)
    save_csv(OUT / "scenario_metrics.csv", metrics)
    save_csv(OUT / "scenario_site_metrics.csv", site_metrics)
    save_csv(OUT / "scenario_pairwise_delta.csv", pair_deltas)
    save_csv(OUT / "crossing_incident_edges.csv", incident)
    (OUT / "crossing_point.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [crossing_feature]},
                                                     ensure_ascii=False, indent=2), encoding="utf-8")
    crossing_features = []
    for candidate in points:
        geom = QgsGeometry.fromPointXY(QgsPointXY(candidate))
        geom.transform(backward)
        crossing_features.append({"type": "Feature", "geometry": json.loads(geom.asJson()),
                                  "properties": {"osm_id": 510175774,
                                                 "on_original_nm29_nm34_route": node(candidate) == key,
                                                 "scenario_b_split": True}})
    (OUT / "crossing_cluster.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": crossing_features}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps({
        "source_network": str(NET), "baseline_v1_unchanged": True,
        "crossing": {"osm_way": 510175774, "kml_trace": 1,
                     "representative_longitude": point.asPoint().x(), "representative_latitude": point.asPoint().y(),
                     "same_way_intersection_count": len(crossing_keys),
                     "incident_edges": incident},
        "scenario_a": "Approved pilot graph; KML and OSM share one crossing node",
        "scenario_b": "All geometric crossings of KML trace 1 and OSM way 510175774 split into separate source-side nodes; no direct KML/OSM transfer at those nodes",
        "topology_limit": "Source-coincident segments are duplicated on KML and OSM sides. This graph sensitivity is not field evidence of hydraulic disconnection",
        "disconnected_policy": "No Euclidean substitute for RiverDistance or river prediction",
        "metrics_policy": "Report coverage; common-four-site subset compares equal targets between scenarios",
        "ec_unit": "mS/m", "crs": "EPSG:32648",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"crossing_count": len(crossing_keys),
                      "disconnected_b_pairs": [row for row in pair_deltas if not row["scenario_b_connected"]],
                      "pooled": [row for row in metrics if row["campaign"] == "ALL"],
                      "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
