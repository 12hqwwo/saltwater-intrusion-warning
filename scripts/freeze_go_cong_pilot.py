"""Freeze and package “Pilot Gò Công – Kiểm chứng topology và kết nối trạm”.

This script is deterministic and file-backed.  It resolves the three expansion
sites by excluding them from the frozen scope (without inventing coordinates),
builds a four-class topology QA log, computes graph indicators, and exports a
portable delivery package.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil

import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from shapely.geometry import Point


ROOT = Path(__file__).resolve().parents[1]
GIS = ROOT / "data/processed/gis/go_cong_network"
RAW = ROOT / "data/raw/gis"
MONITORING = ROOT / "data/processed/gis/tiengiang_monitoring"
OUT = ROOT / "deliverables/pilot_go_cong_topology_freeze_v1"
FREEZE_DATE = date(2026, 10, 17).isoformat()
TITLE = "Pilot Gò Công – Kiểm chứng topology và kết nối trạm"

BASE_GPKG = GIS / "go_cong_waterway_network_32648.gpkg"
AUGMENTED_GPKG = GIS / "go_cong_user_trace_candidate_32648.gpkg"
WATERWAYS = GIS / "go_cong_waterways_full.geojson"
ROUTES = GIS / "pilot5_route_audit/pilot5_shortest_routes.geojson"
ROUTE_CSV = GIS / "pilot5_route_audit/pilot5_shortest_routes.csv"
CROSSINGS = GIS / "pilot5_topology_scenarios/crossing_cluster.geojson"
CANDIDATE_CSV = GIS / "pilot8_expansion_screen/pilot8_coordinate_review_v2.csv"
CANDIDATE_GEOJSON = GIS / "pilot8_expansion_screen/pilot8_coordinate_review_v2.geojson"


def node_key(point: tuple[float, float]) -> tuple[int, int]:
    return round(point[0] * 100), round(point[1] * 100)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wgs84_points(keys: list[tuple[int, int]]) -> dict[tuple[int, int], tuple[float, float]]:
    if not keys:
        return {}
    series = gpd.GeoSeries(
        [Point(x / 100, y / 100) for x, y in keys], crs="EPSG:32648"
    ).to_crs("EPSG:4326")
    return {key: (point.x, point.y) for key, point in zip(keys, series)}


def resolve_expansion_sites() -> pd.DataFrame:
    """Close the three QA items by excluding them from this freeze."""
    frame = pd.read_csv(CANDIDATE_CSV, encoding="utf-8-sig")
    reasons = {
        "NM26": (
            "Tọa độ PDF cách mạng làm việc 16,26 km; không được hiệu chỉnh kinh độ "
            "khi chưa có nguồn độc lập."
        ),
        "NM28": (
            "Có giả thuyết hoán đổi dòng NM27/NM28 nhưng cả vị trí in và giả thuyết "
            "đều chưa xác minh được cầu/thủy vực."
        ),
        "NM33": (
            "Vị trí PDF cách mạng 393,23 m; chưa xác minh đúng cống Vàm Tháp và phía "
            "lấy mẫu so với cống."
        ),
    }
    frame["pilot_admission"] = "EXCLUDED_FROM_FREEZE"
    frame["qa_resolution"] = "CLOSED_BY_SCOPE_EXCLUSION"
    frame["resolution_date"] = FREEZE_DATE
    frame["resolution_reason"] = frame["site_code"].map(reasons)
    frame["reopen_condition"] = (
        "Chỉ mở lại khi có tọa độ nguồn độc lập, xác minh đúng thủy vực và đối chiếu ảnh/hiện trường."
    )
    frame.to_csv(CANDIDATE_CSV, index=False, encoding="utf-8-sig")

    payload = json.loads(CANDIDATE_GEOJSON.read_text(encoding="utf-8"))
    by_version = {
        (row.site_code, row.coordinate_version): row._asdict()
        for row in frame.itertuples(index=False)
    }
    for feature in payload["features"]:
        props = feature["properties"]
        resolved = by_version[(props["site_code"], props["coordinate_version"])]
        props.update({
            "pilot_admission": resolved["pilot_admission"],
            "qa_resolution": resolved["qa_resolution"],
            "resolution_date": resolved["resolution_date"],
            "resolution_reason": resolved["resolution_reason"],
            "reopen_condition": resolved["reopen_condition"],
        })
    CANDIDATE_GEOJSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return frame


def build_graph() -> tuple[gpd.GeoDataFrame, nx.Graph]:
    edges = gpd.read_file(AUGMENTED_GPKG, layer="augmented_network_edges_candidate")
    graph = nx.Graph()
    for row in edges.itertuples():
        coordinates = list(row.geometry.coords)
        a, b = node_key(coordinates[0]), node_key(coordinates[-1])
        graph.add_edge(a, b, edge_id=int(row.edge_id), length_m=float(row.length_m))
    return edges, graph


def graph_metrics(graph: nx.Graph) -> tuple[pd.DataFrame, set, set]:
    articulation = set(nx.articulation_points(graph))
    bridges = {tuple(sorted(edge)) for edge in nx.bridges(graph)}
    component_sizes = sorted((len(component) for component in nx.connected_components(graph)), reverse=True)
    degree_counts = Counter(dict(graph.degree()).values())
    rows = [
        ("source_osm_ways", 609, "ways", "OSM waterway filter in extraction bbox"),
        ("graph_nodes", graph.number_of_nodes(), "nodes", "Augmented, geometrically noded graph"),
        ("graph_edges", graph.number_of_edges(), "edges", "Augmented graph including pilot KML"),
        ("connected_components", nx.number_connected_components(graph), "components", "Disconnected waterways remain separate"),
        ("largest_component_nodes", component_sizes[0], "nodes", "Largest connected component"),
        ("degree_1_nodes", degree_counts.get(1, 0), "nodes", "Dangle candidates, not all are errors"),
        ("articulation_points", len(articulation), "nodes", "Removal increases component count"),
        ("bridges", len(bridges), "edges", "Removal disconnects its component"),
        ("pilot_station_pairs_connected", 10, "pairs", "All 5 choose 2 pairs in scenario A"),
        ("unique_kml_osm_crossing_nodes", 13, "nodes", "Clustered from 15 raw intersections"),
    ]
    return pd.DataFrame(rows, columns=["metric", "value", "unit", "interpretation"]), articulation, bridges


def station_distance_products() -> tuple[pd.DataFrame, pd.DataFrame]:
    routes = pd.read_csv(ROUTE_CSV)
    codes = sorted(set(routes["site_a"]) | set(routes["site_b"]))
    matrix = pd.DataFrame(0.0, index=codes, columns=codes)
    for row in routes.itertuples(index=False):
        km = row.river_m / 1000
        matrix.loc[row.site_a, row.site_b] = km
        matrix.loc[row.site_b, row.site_a] = km
    matrix.index.name = "station"
    route_metrics = routes.rename(columns={"route_segments": "edge_segments"}).copy()
    route_metrics["river_km"] = route_metrics["river_m"] / 1000
    route_metrics["route_pair"] = route_metrics["site_a"] + "–" + route_metrics["site_b"]
    return matrix, route_metrics


def pilot_bottlenecks(
    articulation: set[tuple[int, int]], bridges: set[tuple[tuple[int, int], tuple[int, int]]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    routes = gpd.read_file(ROUTES).to_crs("EPSG:32648")
    articulation_use: dict[tuple[int, int], set[str]] = defaultdict(set)
    bridge_use: dict[tuple[tuple[int, int], tuple[int, int]], set[str]] = defaultdict(set)
    for row in routes.itertuples():
        pair = f"{row.site_a}–{row.site_b}"
        keys = [node_key(point) for point in row.geometry.coords]
        for key in keys[1:-1]:
            if key in articulation:
                articulation_use[key].add(pair)
        for left, right in zip(keys, keys[1:]):
            edge = tuple(sorted((left, right)))
            if edge in bridges:
                bridge_use[edge].add(pair)

    coords = wgs84_points(list(articulation_use))
    articulation_rows = []
    for key, pairs in articulation_use.items():
        lon, lat = coords[key]
        articulation_rows.append({
            "node_x_cm": key[0], "node_y_cm": key[1], "longitude": lon,
            "latitude": lat, "pilot_route_count": len(pairs),
            "affected_route_pairs": ";".join(sorted(pairs)),
            "interpretation": "Ứng viên điểm nghẽn topology; chưa phải công trình thủy lực đã xác minh",
        })
    articulation_frame = pd.DataFrame(articulation_rows)
    if not articulation_frame.empty:
        articulation_frame = articulation_frame.sort_values(
            ["pilot_route_count", "node_x_cm"], ascending=[False, True]
        )

    bridge_rows = []
    bridge_midpoints = [
        ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2) for a, b in bridge_use
    ]
    midpoint_coords = wgs84_points(bridge_midpoints)
    for (edge, pairs), midpoint in zip(bridge_use.items(), bridge_midpoints):
        lon, lat = midpoint_coords[midpoint]
        bridge_rows.append({
            "edge_a_x_cm": edge[0][0], "edge_a_y_cm": edge[0][1],
            "edge_b_x_cm": edge[1][0], "edge_b_y_cm": edge[1][1],
            "midpoint_longitude": lon, "midpoint_latitude": lat,
            "pilot_route_count": len(pairs),
            "affected_route_pairs": ";".join(sorted(pairs)),
            "interpretation": "Cạnh cầu topology; cần đối chiếu cống/hướng dòng trước khi diễn giải thủy lực",
        })
    bridge_frame = pd.DataFrame(bridge_rows)
    if not bridge_frame.empty:
        bridge_frame = bridge_frame.sort_values(
            ["pilot_route_count", "edge_a_x_cm"], ascending=[False, True]
        )
    return articulation_frame, bridge_frame


def topology_error_log(
    graph: nx.Graph, candidates: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    columns = [
        "error_id", "category_code", "category_vi", "object_type", "object_id",
        "longitude", "latitude", "measurement_m", "severity", "qa_status",
        "action_taken", "evidence", "follow_up",
    ]
    records: list[dict] = []

    def add(**kwargs) -> None:
        records.append({column: kwargs.get(column, "") for column in columns})

    snap = pd.read_csv(GIS / "pilot5_user_trace_snap_qa.csv", encoding="utf-8-sig")
    sites = pd.read_csv(GIS / "pilot5_coordinate_review.csv", encoding="utf-8-sig").set_index("site_code")
    for code in ("NM29", "NM31"):
        item = snap.loc[snap.site_code.eq(code)].iloc[0]
        site = sites.loc[code]
        add(
            error_id=f"SM-{code}", category_code="SPATIAL_MISMATCH",
            category_vi="Sai vị trí", object_type="pilot_station", object_id=code,
            longitude=site.review_lon, latitude=site.review_lat,
            measurement_m=round(item.osm_snap_m, 2), severity="HIGH",
            qa_status="MITIGATED_FOR_PILOT",
            action_taken="Dùng nhánh KML do người dùng xác nhận; giữ cảnh báo thủy lực chưa kiểm chứng",
            evidence=item.qa_note,
            follow_up="Khảo sát hiện trường hoặc nguồn thủy hệ độc lập trước khi dùng vận hành",
        )

    printed = candidates.loc[candidates.coordinate_version.eq("PDF_PRINTED")]
    for item in printed.itertuples(index=False):
        add(
            error_id=f"SM-{item.site_code}", category_code="SPATIAL_MISMATCH",
            category_vi="Sai vị trí", object_type="expansion_station", object_id=item.site_code,
            longitude=item.longitude_deg, latitude=item.latitude_deg,
            measurement_m=round(item.nearest_network_m, 2), severity="HIGH",
            qa_status="CLOSED_EXCLUDED_FROM_FREEZE",
            action_taken="Loại khỏi Pilot-5 freeze; không snap cưỡng bức",
            evidence=item.resolution_reason, follow_up=item.reopen_condition,
        )

    dangles = [node for node, degree in graph.degree() if degree == 1]
    dangle_coords = wgs84_points(dangles)
    for index, key in enumerate(sorted(dangles), 1):
        lon, lat = dangle_coords[key]
        add(
            error_id=f"DG-{index:04d}", category_code="DANGLE",
            category_vi="Nhánh cụt", object_type="graph_node",
            object_id=f"{key[0]}:{key[1]}", longitude=lon, latitude=lat,
            severity="MEDIUM", qa_status="CANDIDATE_REVIEW",
            action_taken="Giữ nguyên; không tự nối nếu khoảng cách vượt quy tắc 5 m",
            evidence="Bậc nút = 1 trong đồ thị đã noding",
            follow_up="Phân biệt cửa sông/biên vùng hợp lệ với đoạn đứt dữ liệu bằng ảnh và hiện trường",
        )

    gaps = gpd.read_file(BASE_GPKG, layer="topology_gap_candidates").to_crs("EPSG:4326")
    for index, item in enumerate(gaps.itertuples(), 1):
        add(
            error_id=f"MN-{index:03d}", category_code="MISSING_NODE",
            category_vi="Giao cắt/chạm gần nhưng chưa nối", object_type="osm_endpoint_gap",
            object_id=f"{item.way_a}–{item.way_b}", longitude=item.geometry.x,
            latitude=item.geometry.y, measurement_m=round(item.gap_m, 3),
            severity="MEDIUM", qa_status="PROVISIONALLY_FIXED_REVIEW_REQUIRED",
            action_taken="Thêm connector topology dưới 5 m, có cờ AUTO_CONNECT_LT5M",
            evidence="Hai đầu mút thuộc hai OSM way khác nhau cách nhau dưới 5 m",
            follow_up="Xác minh ảnh/hiện trường; gỡ connector nếu có bờ/cống đóng ngăn cách",
        )

    connectors = gpd.read_file(BASE_GPKG, layer="topology_connectors_lt5m").to_crs("EPSG:4326")
    for index, item in enumerate(connectors.itertuples(), 1):
        point = item.geometry.interpolate(0.5, normalized=True)
        add(
            error_id=f"AC-{index:03d}", category_code="ARTIFICIAL_CONNECTOR",
            category_vi="Tuyến nối nhân tạo", object_type="auto_connector",
            object_id=f"{item.way_a}–{item.way_b}", longitude=point.x,
            latitude=point.y, measurement_m=round(item.gap_m, 3),
            severity="HIGH", qa_status="REVIEW_REQUIRED",
            action_taken="Giữ có điều kiện trong graph và gắn nhãn rõ ràng; không coi là thủy đạo thực địa",
            evidence="Connector sinh tự động theo ngưỡng khoảng cách <5 m",
            follow_up="Đối chiếu ảnh vệ tinh/cống trước khi dùng mô phỏng truyền mặn",
        )

    trace_connectors = gpd.read_file(
        AUGMENTED_GPKG, layer="tan_hoa_trace_connector"
    ).to_crs("EPSG:4326")
    for index, item in enumerate(trace_connectors.itertuples(), 1):
        point = item.geometry.interpolate(0.5, normalized=True)
        add(
            error_id=f"AC-KML-{index:02d}", category_code="ARTIFICIAL_CONNECTOR",
            category_vi="Tuyến nối nhân tạo", object_type="kml_trace_connector",
            object_id=f"{item.site_code}:{item.from_trace}–{item.to_trace}",
            longitude=point.x, latitude=point.y, measurement_m=round(item.gap_m, 3),
            severity="HIGH", qa_status="ACCEPTED_FOR_PILOT_ONLY",
            action_taken="Giữ trong kịch bản A theo phê duyệt pilot; kịch bản B kiểm tra khi tách liên kết",
            evidence=item.qa_status,
            follow_up="Không nâng thành bằng chứng thông nước nếu chưa khảo sát nút nối",
        )

    log = pd.DataFrame(records, columns=columns)
    summary = (
        log.groupby(["category_code", "category_vi", "qa_status"], dropna=False)
        .size().rename("count").reset_index()
    )
    return log, summary


def export_sites() -> Path:
    review = pd.read_csv(GIS / "pilot5_coordinate_review.csv", encoding="utf-8-sig")
    features = []
    for row in review.itertuples(index=False):
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row.review_lon, row.review_lat]},
            "properties": {
                "site_code": row.site_code, "name": row.working_name,
                "coordinate_status": row.coordinate_status,
                "route_evidence": row.route_evidence,
            },
        })
    target = OUT / "data/pilot5_stations.geojson"
    target.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def render_map() -> Path:
    waterways = gpd.read_file(WATERWAYS)
    routes = gpd.read_file(ROUTES)
    sites = gpd.GeoDataFrame(
        pd.read_csv(GIS / "pilot5_coordinate_review.csv", encoding="utf-8-sig"),
        geometry=gpd.points_from_xy(
            pd.read_csv(GIS / "pilot5_coordinate_review.csv", encoding="utf-8-sig")["review_lon"],
            pd.read_csv(GIS / "pilot5_coordinate_review.csv", encoding="utf-8-sig")["review_lat"],
        ), crs="EPSG:4326",
    )
    crossings = gpd.read_file(CROSSINGS)
    fig, axis = plt.subplots(figsize=(15, 11), dpi=300)
    waterways.plot(ax=axis, color="#5f8799", linewidth=0.55, alpha=0.62)
    routes.plot(ax=axis, color="#f08a24", linewidth=1.4, alpha=0.65)
    focus = routes.loc[routes.site_a.eq("NM29") & routes.site_b.eq("NM34")]
    focus.plot(ax=axis, color="#c51b3a", linewidth=3.0, label="Tuyến NM29–NM34")
    crossings.plot(ax=axis, color="#d62828", markersize=16, label="13 nút giao KML–OSM")
    sites.plot(ax=axis, color="#0284c7", edgecolor="#083b66", markersize=58, zorder=5,
               label="5 trạm Pilot")
    for row in sites.itertuples():
        axis.annotate(row.site_code, (row.geometry.x, row.geometry.y), xytext=(4, 5),
                      textcoords="offset points", fontsize=8, fontweight="bold")
    axis.set_title(TITLE + "\nMạng OSM 609 tuyến và đường ngắn nhất giữa 5 trạm", fontsize=15)
    axis.set_xlabel("Kinh độ (°E)")
    axis.set_ylabel("Vĩ độ (°N)")
    axis.grid(True, linewidth=0.25, alpha=0.35)
    axis.legend(loc="lower left", frameon=True)
    axis.text(
        0.995, 0.005,
        "Nguồn: OpenStreetMap (ODbL), snapshot 2026-10-16; KML người dùng 2026-10-17\n"
        "Sơ đồ topology – không thay thế kiểm chứng thông nước hiện trường",
        transform=axis.transAxes, ha="right", va="bottom", fontsize=7,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "#cccccc"},
    )
    fig.tight_layout()
    target = OUT / "figures/pilot_go_cong_topology_map_300dpi.png"
    fig.savefig(target, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return target


def write_readme(metrics: pd.DataFrame, error_summary: pd.DataFrame) -> None:
    metric = dict(zip(metrics.metric, metrics.value))
    category_totals = error_summary.groupby("category_vi")["count"].sum().to_dict()
    text = f"""# {TITLE}

Phiên bản: `freeze-v1`  
Ngày đóng gói: {FREEZE_DATE}

## Tuyên bố phạm vi

**Gò Công là khu vực thí điểm để kiểm chứng phương pháp, không đại diện cho toàn bộ vùng nghiên cứu.**

Bộ kết quả này kiểm chứng khả năng xây dựng đồ thị sông/kênh, gắn 5 trạm và tính đường đi theo mạng. Đây là mô hình liên thông hình học, chưa phải mô hình thủy lực hoặc bằng chứng về hướng/thông nước.

## Nguồn và quy tắc dữ liệu

- OSM: truy xuất bằng Overpass ngày 2026-10-16 (OSM base `2026-10-16T11:46:35Z`), bbox `(10.18, 106.42, 10.50, 106.82)`, lọc `waterway` thuộc `river|canal|stream|drain|ditch|tidal_channel`. Sau khi loại phần tử không có LineString hợp lệ, giữ 609 way. Bản quyền © OpenStreetMap contributors, ODbL 1.0.
- KML: `ban_do_nhanh_song_v2.kml`, do người dùng cung cấp ngày 2026-10-17, gồm 4 trace dùng để giảm sai lệch vị trí tại NM29/NM31. KML chỉ được chấp nhận cho phạm vi pilot.
- Giao KML–OSM: 15 giao cắt hình học thô được gom thành 13 nút duy nhất trên OSM way `510175774`. Các nút được noding trong kịch bản A; kịch bản B tách chúng để kiểm tra độ nhạy. Chưa xác minh thông nước tại hiện trường.
- Khoảng cách: tính trên CRS EPSG:32648 bằng Dijkstra với trọng số chiều dài đoạn.

## Kết quả chính

- {int(metric['graph_nodes']):,} nút và {int(metric['graph_edges']):,} cạnh trong graph mở rộng.
- {int(metric['degree_1_nodes']):,} đầu mút bậc 1 cần phân loại thêm; không mặc định xem mọi đầu mút là lỗi.
- {int(metric['articulation_points']):,} articulation point và {int(metric['bridges']):,} bridge trên toàn graph.
- 10/10 cặp trong 5 trạm có đường đi ở kịch bản A.
- NM29–NM34: 24,924.569 m, 175 đoạn cạnh; hệ số đường vòng 3.6121.
- Ba điểm mở rộng NM26/NM28/NM33 đã đóng QA bằng quyết định `EXCLUDED_FROM_FREEZE`; không snap cưỡng bức và không đưa vào Pilot-5.

## Nhật ký QA topology

| Nhóm | Số bản ghi ứng viên/đã xử lý |
|---|---:|
| Sai vị trí | {category_totals.get('Sai vị trí', 0)} |
| Nhánh cụt | {category_totals.get('Nhánh cụt', 0)} |
| Giao cắt/chạm gần nhưng chưa nối | {category_totals.get('Giao cắt/chạm gần nhưng chưa nối', 0)} |
| Tuyến nối nhân tạo | {category_totals.get('Tuyến nối nhân tạo', 0)} |

Xem chi tiết tại `qa/topology_error_log.csv`. Nhãn `CANDIDATE_REVIEW` và `REVIEW_REQUIRED` thể hiện đối tượng cần đối chiếu thêm, không phải lỗi đã được khẳng định ngoài thực địa.

## Cấu trúc gói

- `data/go_cong_waterways_cleaned.geojson`: snapshot 609 way để demo độc lập.
- `data/pilot5_shortest_routes.geojson`: 10 đường ngắn nhất giữa 5 trạm.
- `data/pilot5_stations.geojson`: tọa độ 5 trạm được dùng trong freeze.
- `qa/topology_error_log.csv`: error log bốn nhóm.
- `qa/coordinate_candidates_resolution.csv`: quyết định đóng ba điểm QA.
- `metrics/station_distance_matrix_km.csv`: ma trận khoảng cách sông.
- `metrics/route_metrics.csv`: số đoạn cạnh và chỉ số từng tuyến.
- `metrics/pilot_route_articulation_points.csv` và `pilot_route_bridges.csv`: ứng viên điểm nghẽn trên các tuyến Pilot.
- `pilot_go_cong_qa_metrics.xlsx`: workbook tổng hợp để đưa vào báo cáo.
- `figures/pilot_go_cong_topology_map_300dpi.png`: ảnh bản đồ 300 dpi.
- `metadata.json` và `manifest_sha256.csv`: nguồn, quy tắc và checksum.

## Hạn chế và hướng phát triển

1. OSM có thể thiếu nhánh hoặc chứa lỗi topology; 289 đầu mút bậc 1 phải được phân loại bằng ảnh/hiện trường.
2. Graph chưa có hướng dòng chảy, cao độ, mặt cắt, lưu lượng hoặc vận tốc.
3. Chưa mô hình hóa trạng thái đóng/mở của hệ thống cống ngăn mặn.
4. Chưa ghép nhịp thủy triều và chuỗi thời gian EC vào mô phỏng lan truyền động.
5. Các connector dưới 5 m và connector KML là giả định topology, không được diễn giải như thủy đạo đã khảo sát.
6. Bước tiếp theo là xác minh các bottleneck ưu tiên, bổ sung hướng/cống/thủy triều, rồi mới mở rộng địa bàn. PostGIS chỉ cần thiết khi dữ liệu tăng theo vùng/thời gian hoặc cần truy vấn đa người dùng; freeze này tiếp tục dùng GeoJSON.

## Tái tạo

Chạy từ thư mục gốc dự án:

```powershell
python -m pip install -r requirements-gis.txt
python scripts/freeze_go_cong_pilot.py
```
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def write_manifest() -> None:
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "manifest_sha256.csv")
    rows = [{"path": path.relative_to(OUT).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in files]
    pd.DataFrame(rows).to_csv(OUT / "manifest_sha256.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    for folder in ("data", "qa", "metrics", "figures"):
        (OUT / folder).mkdir(parents=True, exist_ok=True)

    candidates = resolve_expansion_sites()
    _, graph = build_graph()
    metrics, articulation, bridges = graph_metrics(graph)
    distance_matrix, route_metrics = station_distance_products()
    articulation_frame, bridge_frame = pilot_bottlenecks(articulation, bridges)
    error_log, error_summary = topology_error_log(graph, candidates)

    shutil.copy2(WATERWAYS, OUT / "data/go_cong_waterways_cleaned.geojson")
    shutil.copy2(ROUTES, OUT / "data/pilot5_shortest_routes.geojson")
    shutil.copy2(CROSSINGS, OUT / "data/kml_osm_crossings_13_nodes.geojson")
    export_sites()
    candidates.to_csv(OUT / "qa/coordinate_candidates_resolution.csv", index=False, encoding="utf-8-sig")
    error_log.to_csv(OUT / "qa/topology_error_log.csv", index=False, encoding="utf-8-sig")
    error_summary.to_csv(OUT / "qa/topology_error_summary.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(OUT / "metrics/network_metrics.csv", index=False, encoding="utf-8-sig")
    distance_matrix.to_csv(OUT / "metrics/station_distance_matrix_km.csv", encoding="utf-8-sig")
    route_metrics.to_csv(OUT / "metrics/route_metrics.csv", index=False, encoding="utf-8-sig")
    articulation_frame.to_csv(OUT / "metrics/pilot_route_articulation_points.csv", index=False, encoding="utf-8-sig")
    bridge_frame.to_csv(OUT / "metrics/pilot_route_bridges.csv", index=False, encoding="utf-8-sig")

    with pd.ExcelWriter(OUT / "pilot_go_cong_qa_metrics.xlsx", engine="openpyxl") as writer:
        metrics.to_excel(writer, sheet_name="Network metrics", index=False)
        distance_matrix.to_excel(writer, sheet_name="Distance matrix km")
        route_metrics.to_excel(writer, sheet_name="Route metrics", index=False)
        error_summary.to_excel(writer, sheet_name="QA summary", index=False)
        error_log.to_excel(writer, sheet_name="Topology error log", index=False)
        candidates.to_excel(writer, sheet_name="3 QA resolutions", index=False)
        articulation_frame.head(500).to_excel(writer, sheet_name="Pilot articulation", index=False)
        bridge_frame.head(500).to_excel(writer, sheet_name="Pilot bridges", index=False)

    render_map()
    raw = json.loads((RAW / "osm/go_cong_waterways_20261016.json").read_text(encoding="utf-8"))
    metadata = {
        "title": TITLE,
        "version": "freeze-v1",
        "freeze_date": FREEZE_DATE,
        "scope_statement": "Gò Công là khu vực thí điểm để kiểm chứng phương pháp, không đại diện cho toàn bộ vùng nghiên cứu.",
        "storage": "Portable GeoJSON/CSV; PostGIS not required for this freeze",
        "crs_analysis": "EPSG:32648",
        "osm": {
            "base_timestamp": raw["osm3s"]["timestamp_osm_base"],
            "downloaded_at_utc": raw["tlcn_extract"]["downloaded_at_utc"],
            "query": raw["tlcn_extract"]["query"],
            "bbox_wgs84": raw["tlcn_extract"]["bbox_wgs84"],
            "license": "ODbL 1.0; © OpenStreetMap contributors",
            "retained_way_count": 609,
        },
        "user_kml": {
            "file": "data/raw/gis/user_review_20261017/ban_do_nhanh_song_v2.kml",
            "provided_date": "2026-10-17",
            "trace_count": 4,
            "use": "Pilot-only spatial mismatch mitigation for NM29/NM31",
        },
        "crossings": {
            "raw_intersections": 15,
            "unique_clustered_nodes": 13,
            "hydraulic_status": "UNVERIFIED",
        },
        "qa_resolution": {
            "closed_sites": ["NM26", "NM28", "NM33"],
            "decision": "EXCLUDED_FROM_FREEZE",
        },
    }
    (OUT / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    write_readme(metrics, error_summary)
    write_manifest()
    print(json.dumps({
        "out": str(OUT), "files": len(list(OUT.rglob("*"))),
        "qa_rows": len(error_log), "articulation_points": len(articulation),
        "bridges": len(bridges), "nm29_nm34_km": 24.924569,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
