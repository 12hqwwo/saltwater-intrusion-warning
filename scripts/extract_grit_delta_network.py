"""Extract an auditable lower-Mekong GRIT topology subset, without hydraulics."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pyogrio
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/external/grit_20261029/GRITv1.0_segments_simple_GLOBAL_EPSG4326.gpkg.zip"
SOURCE_MANIFEST = SOURCE.with_name("manifest.json")
OUT = ROOT / "outputs/grit_delta_network_20261029"
BBOX = (105.0, 9.5, 107.0, 11.5)  # wider than Tien mouths; edge links remain truncated
GAUGE_ANCHORS = {
    "cua_tieu": (106.740194, 10.269889),
    "cua_dai": (106.711222, 10.197028),
    "ham_luong": (106.605222, 9.966667),
    "co_chien": (106.529000, 9.880889),
}


def main():
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if (SOURCE.stat().st_size != manifest["size_bytes"] or
            hashlib.md5(SOURCE.read_bytes()).hexdigest() != manifest["md5"]):
        raise ValueError("GRIT archive does not match verified source manifest")
    uri = "zip://" + SOURCE.resolve().as_posix()
    lines = pyogrio.read_dataframe(uri, layer="lines", bbox=BBOX)
    nodes = pyogrio.read_dataframe(uri, layer="nodes", bbox=BBOX)
    if lines.empty or nodes.empty or lines.crs.to_epsg() != 4326 or nodes.crs.to_epsg() != 4326:
        raise ValueError("Missing or unexpected GRIT region")
    node_ids = set(nodes.global_id.astype(int))
    upstream_missing = int((~lines.upstream_node_id.astype(int).isin(node_ids)).sum())
    downstream_missing = int((~lines.downstream_node_id.astype(int).isin(node_ids)).sum())
    coastal = nodes[nodes.node_type.eq("coastal_outlet")]
    transformer = Transformer.from_crs(4326, 32648, always_xy=True)
    outlet_candidates = {}
    for name, (lon, lat) in GAUGE_ANCHORS.items():
        ax, ay = transformer.transform(lon, lat)
        nearest = min(coastal.itertuples(), key=lambda row:
            (transformer.transform(row.geometry.x, row.geometry.y)[0] - ax) ** 2 +
            (transformer.transform(row.geometry.x, row.geometry.y)[1] - ay) ** 2)
        ox, oy = transformer.transform(nearest.geometry.x, nearest.geometry.y)
        distance = ((ox-ax)**2 + (oy-ay)**2)**.5 / 1000
        if distance > 15:
            raise ValueError(f"No plausible coastal outlet near {name}: {distance:.1f} km")
        outlet_candidates[name] = {
            "global_id": int(nearest.global_id),
            "lon": float(nearest.geometry.x), "lat": float(nearest.geometry.y),
            "distance_to_published_gauge_km": round(distance, 3),
            "gauge_anchor_lon": lon, "gauge_anchor_lat": lat,
            "status": "PROVISIONAL_NEAREST_GRIT_COASTAL_OUTLET",
        }
    if len({item["global_id"] for item in outlet_candidates.values()}) != len(outlet_candidates):
        raise ValueError("Two gauges selected one coastal outlet")
    OUT.mkdir(parents=True, exist_ok=True)
    gpkg = OUT / "grit_lower_mekong_subset.gpkg"
    temporary = OUT / "grit_lower_mekong_subset.tmp.gpkg"
    if temporary.exists():
        temporary.unlink()
    pyogrio.write_dataframe(lines, temporary, layer="lines", driver="GPKG")
    pyogrio.write_dataframe(nodes, temporary, layer="nodes", driver="GPKG", append=True)
    check_lines = pyogrio.read_dataframe(temporary, layer="lines", read_geometry=False)
    check_nodes = pyogrio.read_dataframe(temporary, layer="nodes", read_geometry=False)
    if (len(check_lines) != len(lines) or len(check_nodes) != len(nodes) or
            check_lines.global_id.duplicated().any() or check_nodes.global_id.duplicated().any()):
        raise ValueError("Written GRIT subset contains missing or duplicated IDs")
    temporary.replace(gpkg)
    audit = {
        "source": "https://zenodo.org/records/17435232",
        "source_archive": str(SOURCE.relative_to(ROOT)),
        "source_md5": manifest["md5"],
        "bbox_epsg4326_lon_min_lat_min_lon_max_lat_max": BBOX,
        "line_count": len(lines), "node_count": len(nodes),
        "domain_counts": lines.domain.value_counts().to_dict(),
        "node_type_counts": nodes.node_type.value_counts().to_dict(),
        "named_lines": int(lines.name.notna().sum()),
        "upstream_node_ids_outside_subset": upstream_missing,
        "downstream_node_ids_outside_subset": downstream_missing,
        "continuity_violated_nodes": int(nodes.continuity_violated.fillna(0).sum()),
        "cycle_flagged_lines": int(lines.cycle.fillna(0).sum()),
        "mouth_outlet_candidates": outlet_candidates,
        "limitations": [
            "bbox clipping does not create a closed directed graph",
            "global simplified river topology may omit local canals, gates, and mouth geometry",
            "width_adjusted is an estimated width, not surveyed cross section or depth",
            "flow direction and reversal under tides are not calibrated",
            "no salt transport, flow split, travel time, or vertical datum is supplied",
        ],
        "output_sha256": hashlib.sha256(gpkg.read_bytes()).hexdigest(),
    }
    (OUT / "audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: audit[k] for k in ("line_count", "node_count", "node_type_counts",
        "upstream_node_ids_outside_subset", "downstream_node_ids_outside_subset")}, indent=2))


if __name__ == "__main__":
    main()
