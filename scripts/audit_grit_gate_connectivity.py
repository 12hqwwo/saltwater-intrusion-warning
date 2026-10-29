"""Audit provisional GRIT routing and gate proximity without predicting salt.

Nearest line and directed paths are geometric/topological diagnostics only.
GRIT does not encode local canal/gate hydraulic connectivity or tidal reversal.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import networkx as nx
import pandas as pd
import pyogrio
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "outputs/grit_delta_network_20261029/grit_lower_mekong_subset.gpkg"
NETWORK_AUDIT = ROOT / "outputs/grit_delta_network_20261029/audit.json"
GATES = ROOT / "data/8file/03_sluice_gates_190_and_27_verified_gis.csv"
MRC = ROOT / "data/external/tien_multisite_20261029_verified/inventory.json"
NEW_DT = ROOT / "data/raw/gis/spatial/dong_thap_boundary.geojson"
LEGACY_TG = next((ROOT / "data/biengioi").glob("Ti*n Giang - 63.geojson"))
OUT = ROOT / "outputs/grit_gate_audit_20261029"
STATIONS = {"tan_chau":"019803", "vam_nao":"980601", "my_thuan":"019804",
            "my_tho":"019805", "vam_kenh":"985203"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    network_audit = json.loads(NETWORK_AUDIT.read_text(encoding="utf-8"))
    if sha(NETWORK) != network_audit["output_sha256"]:
        raise ValueError("GRIT subset differs from verified audit")
    lines = pyogrio.read_dataframe(NETWORK, layer="lines")
    nodes = pyogrio.read_dataframe(NETWORK, layer="nodes")
    raw_node_rows = len(nodes)
    if nodes.global_id.duplicated().any():
        duplicate_groups = nodes[nodes.global_id.duplicated(keep=False)].groupby("global_id")
        if any(len({geometry.wkb for geometry in group.geometry}) != 1
               for _, group in duplicate_groups):
            raise ValueError("Conflicting duplicate GRIT node geometry")
        nodes = nodes.drop_duplicates("global_id").copy()
    if len(lines) != 585 or len(nodes) != 484 or lines.crs.to_epsg() != 4326:
        raise ValueError("Unexpected GRIT network")
    local_lines = lines.to_crs(32648)
    graph = nx.DiGraph()
    for rec in lines.itertuples():
        u, v = int(rec.upstream_node_id), int(rec.downstream_node_id)
        length = float(rec.length_adjusted)
        if not (length > 0):
            raise ValueError("Invalid GRIT segment length")
        if not graph.has_edge(u, v) or length < graph[u][v]["weight"]:
            graph.add_edge(u, v, weight=length, line_id=int(rec.global_id))
    outlets = {name:int(item["global_id"]) for name,item in
               network_audit["mouth_outlet_candidates"].items()}
    if not set(outlets.values()).issubset(set(nodes.global_id.astype(int))):
        raise ValueError("Outlet missing from subset")

    def closest(lon, lat):
        point = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(32648).iloc[0]
        distances = local_lines.distance(point)
        pos = int(distances.argmin())
        line = lines.iloc[pos]
        return line, float(distances.iloc[pos]/1000)

    inventory = json.loads(MRC.read_text(encoding="utf-8"))
    station_rows = []
    for name, code in STATIONS.items():
        records = [r for r in inventory if r.get("stationCode") == code and
                   r.get("longitude") is not None and r.get("latitude") is not None]
        coordinates = {(float(r["longitude"]),float(r["latitude"])) for r in records}
        if len(coordinates) != 1:
            raise ValueError(f"Ambiguous MRC station location: {code}")
        lon, lat = coordinates.pop()
        line, distance = closest(lon, lat)
        start_node = int(line.downstream_node_id)
        row = dict(station_code=code, station_name=name, lon=lon, lat=lat,
                   nearest_grit_line_id=int(line.global_id),
                   distance_to_line_km=distance,
                   start_downstream_node_id=start_node,
                   association_status="NEAREST_LINE_ONLY_NOT_HYDRAULIC_LINK")
        for outlet, endpoint in outlets.items():
            row[f"route_to_{outlet}_km"] = (
                round(nx.shortest_path_length(graph,start_node,endpoint,weight="weight")/1000,3)
                if nx.has_path(graph,start_node,endpoint) else None)
        station_rows.append(row)

    legacy = gpd.read_file(LEGACY_TG).geometry.iloc[0]
    merged = gpd.read_file(NEW_DT).geometry.iloc[0]
    with GATES.open(encoding="utf-8-sig",newline="") as handle:
        catalog = [r for r in csv.DictReader(handle)
                   if r["is_verified_27_headworks"].lower() == "true"]
    if len(catalog) != 27 or len({r["gate_code"] for r in catalog}) != 27:
        raise ValueError("Expected 27 unique coordinate-bearing gate records")
    gate_rows = []
    for rec in catalog:
        lon, lat = float(rec["lon_wgs84"]), float(rec["lat_wgs84"])
        point = Point(lon,lat)
        line,distance=closest(lon,lat)
        node = int(line.downstream_node_id)
        gate_rows.append(dict(gate_code=rec["gate_code"],gate_name=rec["gate_name"],
            lon=lon,lat=lat,location_status=rec["location_status"],
            within_legacy_tien_giang=bool(legacy.covers(point)),
            within_new_dong_thap=bool(merged.covers(point)),
            nearest_grit_line_id=int(line.global_id),nearest_line_name=line["name"],
            distance_to_line_km=round(distance,3),
            nearest_line_downstream_node_id=node,
            outlets_reachable_in_grit=",".join(name for name,endpoint in outlets.items()
                if nx.has_path(graph,node,endpoint)),
            association_status="NEAREST_LINE_ONLY_NOT_GATE_CANAL_CONNECTION"))
    gates_df = pd.DataFrame(gate_rows)
    stations_df = pd.DataFrame(station_rows)
    OUT.mkdir(parents=True,exist_ok=True)
    gates_df.to_csv(OUT/"gate_nearest_grit.csv",index=False,encoding="utf-8-sig")
    stations_df.to_csv(OUT/"station_routes.csv",index=False,encoding="utf-8-sig")
    gate_gdf = gpd.GeoDataFrame(gates_df,geometry=gpd.points_from_xy(gates_df.lon,gates_df.lat),crs=4326)
    gate_gdf.to_file(OUT/"gate_proximity.geojson",driver="GeoJSON")
    audit = dict(source_sha256={str(p.relative_to(ROOT)):sha(p) for p in
                                [NETWORK,NETWORK_AUDIT,GATES,MRC,NEW_DT,LEGACY_TG]},
        grit_node_count=graph.number_of_nodes(),grit_unique_directed_edges=graph.number_of_edges(),
        source_gpkg_node_rows=raw_node_rows,source_gpkg_unique_node_ids=len(nodes),
        gate_count=len(gates_df),gate_in_legacy_tien_giang=int(gates_df.within_legacy_tien_giang.sum()),
        gate_in_new_dong_thap=int(gates_df.within_new_dong_thap.sum()),
        gate_distance_km=dict(min=float(gates_df.distance_to_line_km.min()),
                              median=float(gates_df.distance_to_line_km.median()),
                              max=float(gates_df.distance_to_line_km.max()),
                              within_0_5_km=int((gates_df.distance_to_line_km<=.5).sum()),
                              beyond_2_km=int((gates_df.distance_to_line_km>2).sum())),
        station_distance_km={r.station_name:float(r.distance_to_line_km)
                             for r in stations_df.itertuples()},
        route_method="GRIT directed path from nearest segment downstream node; excludes partial segment and ignores tidal reversal",
        gate_method="nearest line only; no link from gate into GRIT canal graph was verified",
        warning="No gate EC or Q, no bathymetry/cross-sections, no calibrated salinity transport or travel times",
        output_sha256={p.name:sha(p) for p in [OUT/"gate_nearest_grit.csv",
            OUT/"station_routes.csv",OUT/"gate_proximity.geojson"]})
    (OUT/"audit.json").write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({k:audit[k] for k in ["gate_count","gate_in_legacy_tien_giang",
        "gate_in_new_dong_thap","gate_distance_km","station_distance_km"]},indent=2))


if __name__ == "__main__":
    main()
