"""Contract checks for the frozen, file-backed Go Cong topology pilot."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import unittest

from backend.pilot_spatial_repository import FilePilotSpatialRepository


ROOT = Path(__file__).resolve().parents[1]
GIS = ROOT / "data/processed/gis/go_cong_network"
PACKAGE = ROOT / "deliverables/pilot_go_cong_topology_freeze_v1"


class GoCongPilotFreezeTests(unittest.TestCase):
    def test_file_repository_exposes_complete_map_bundle(self) -> None:
        repository = FilePilotSpatialRepository()
        self.assertEqual(len(repository.waterways()["features"]), 609)
        self.assertEqual(len(repository.routes()["features"]), 10)
        self.assertEqual(len(repository.crossings()["features"]), 13)
        self.assertEqual(len(repository.sites()["features"]), 5)

    def test_three_qa_sites_are_closed_without_inventing_coordinates(self) -> None:
        with (GIS / "pilot8_expansion_screen/pilot8_coordinate_review_v2.csv").open(
            newline="", encoding="utf-8-sig"
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual({row["site_code"] for row in rows}, {"NM26", "NM28", "NM33"})
        self.assertTrue(all(row["pilot_admission"] == "EXCLUDED_FROM_FREEZE" for row in rows))
        self.assertTrue(all(row["qa_resolution"] == "CLOSED_BY_SCOPE_EXCLUSION" for row in rows))
        self.assertTrue(all(row["reopen_condition"] for row in rows))

    def test_error_log_has_all_four_required_categories(self) -> None:
        with (PACKAGE / "qa/topology_error_log.csv").open(
            newline="", encoding="utf-8-sig"
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            {row["category_code"] for row in rows},
            {"SPATIAL_MISMATCH", "DANGLE", "MISSING_NODE", "ARTIFICIAL_CONNECTOR"},
        )
        self.assertEqual(sum(row["category_code"] == "MISSING_NODE" for row in rows), 9)
        self.assertEqual(sum(row["category_code"] == "ARTIFICIAL_CONNECTOR" for row in rows), 11)

    def test_distance_matrix_is_symmetric_and_contains_nm29_nm34(self) -> None:
        with (PACKAGE / "metrics/station_distance_matrix_km.csv").open(
            newline="", encoding="utf-8-sig"
        ) as handle:
            rows = list(csv.DictReader(handle))
        by_station = {row["station"]: row for row in rows}
        self.assertEqual(set(by_station), {"NM29", "NM30", "NM31", "NM32", "NM34"})
        for left, row in by_station.items():
            self.assertEqual(float(row[left]), 0.0)
            for right in by_station:
                self.assertAlmostEqual(float(row[right]), float(by_station[right][left]), places=9)
        self.assertAlmostEqual(float(by_station["NM29"]["NM34"]), 24.924569, places=6)

    def test_metadata_names_scope_and_file_storage(self) -> None:
        metadata = json.loads((PACKAGE / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["title"], "Pilot Gò Công – Kiểm chứng topology và kết nối trạm")
        self.assertIn("không đại diện cho toàn bộ vùng nghiên cứu", metadata["scope_statement"])
        self.assertIn("PostGIS not required", metadata["storage"])


if __name__ == "__main__":
    unittest.main()
