"""File-backed data layer for the frozen Go Cong spatial pilot.

The HTTP routes and the WebGIS deliberately know nothing about CSV/GeoJSON
locations.  A future PostGIS implementation only needs to provide the same
public methods as :class:`FilePilotSpatialRepository`.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GIS = ROOT / "data/processed/gis/go_cong_network"
MONITORING = ROOT / "data/processed/gis/tiengiang_monitoring"
RAW_OSM = ROOT / "data/raw/gis/osm/go_cong_waterways_20261016.json"
PILOT_CODES = {"NM29", "NM30", "NM31", "NM32", "NM34"}


class PilotArtifactUnavailable(RuntimeError):
    """Raised when a required frozen-pilot artifact is absent or incomplete."""


class FilePilotSpatialRepository:
    """Read the portable Pilot Gò Công snapshot from local files only."""

    def _rows(self, path: Path) -> list[dict]:
        if not path.is_file():
            raise PilotArtifactUnavailable(f"Pilot artifact unavailable: {path.name}")
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))

    def _geojson(self, path: Path) -> dict:
        if not path.is_file():
            raise PilotArtifactUnavailable(f"Pilot layer unavailable: {path.name}")
        return json.loads(path.read_text(encoding="utf-8"))

    def sites(self) -> dict:
        reviewed = self._rows(GIS / "pilot5_coordinate_review.csv")
        snap = {
            row["site_code"]: row
            for row in self._rows(GIS / "pilot5_user_trace_snap_qa.csv")
        }
        values = self._rows(MONITORING / "ec_campaigns_136.csv")
        ec: dict[str, dict[str, float]] = {}
        for row in values:
            if row["site_code"] in PILOT_CODES:
                ec.setdefault(row["site_code"], {})[row["campaign"]] = float(row["ec_ms_m"])

        features = []
        for row in reviewed:
            code = row["site_code"]
            if code not in PILOT_CODES:
                continue
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row["review_lon"]), float(row["review_lat"])],
                },
                "properties": {
                    "site_code": code,
                    "name": row["working_name"],
                    "coordinate_status": row["coordinate_status"],
                    "snap_distance_m": round(float(snap[code]["aug_snap_m"]), 2),
                    "snap_status": snap[code]["snap_status"],
                    "ec_ms_m_by_campaign": ec.get(code, {}),
                    "campaign_dates_known": False,
                    "topology_status": "GRAPH_APPROVED_HYDRAULICS_UNVERIFIED",
                },
            })
        if len(features) != 5 or any(
            len(feature["properties"]["ec_ms_m_by_campaign"]) != 4
            for feature in features
        ):
            raise PilotArtifactUnavailable("Pilot-5 source is incomplete")
        return {"type": "FeatureCollection", "features": features}

    def routes(self) -> dict:
        return self._geojson(GIS / "pilot5_route_audit/pilot5_shortest_routes.geojson")

    def crossings(self) -> dict:
        return self._geojson(GIS / "pilot5_topology_scenarios/crossing_cluster.geojson")

    def coordinate_candidates(self) -> dict:
        return self._geojson(
            GIS / "pilot8_expansion_screen/pilot8_coordinate_review_v2.geojson"
        )

    def metrics(self) -> dict:
        return {
            "unit": "mS/m",
            "validation": "leave-one-location-out per undated campaign I-IV",
            "rows": self._rows(
                GIS / "pilot5_topology_scenarios/scenario_metrics.csv"
            ),
        }

    def predictions(self) -> dict:
        return {
            "unit": "mS/m",
            "rows": self._rows(
                GIS / "pilot5_topology_scenarios/scenario_lolo_predictions.csv"
            ),
        }

    def waterways(self) -> dict:
        """Return the portable 609-way GeoJSON snapshot.

        Prefer the checked/packaged GeoJSON.  The raw Overpass JSON fallback
        keeps older checkouts runnable without changing the API contract.
        """
        packaged = GIS / "go_cong_waterways_full.geojson"
        if packaged.is_file():
            return self._geojson(packaged)
        if not RAW_OSM.is_file():
            raise PilotArtifactUnavailable("OSM waterway source unavailable")
        raw = json.loads(RAW_OSM.read_text(encoding="utf-8"))
        features = []
        for element in raw.get("elements", []):
            geometry = element.get("geometry")
            if not geometry or len(geometry) < 2:
                continue
            tags = element.get("tags", {})
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[point["lon"], point["lat"]] for point in geometry],
                },
                "properties": {
                    "osm_id": element["id"],
                    "waterway": tags.get("waterway", "unknown"),
                    "name": tags.get("name", ""),
                    "boat": tags.get("boat", ""),
                },
            })
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "source": "OpenStreetMap (ODbL)",
                "timestamp": raw.get("osm3s", {}).get("timestamp_osm_base", ""),
                "total_features": len(features),
            },
        }


repository = FilePilotSpatialRepository()
