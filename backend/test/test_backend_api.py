"""Kiểm thử hợp đồng API và cách bind SQL; không kết nối hoặc sửa database thật."""

import copy
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import psycopg
from fastapi.testclient import TestClient

from backend.database import DatasetNotFound, Repository, SiteNotFound, history_predicate
from backend.main import app, get_repository


# Synthetic fixtures belong to tests only, never to an ETL/import path.
STAMP = datetime(2023, 12, 14, 17, 0, tzinfo=timezone.utc)
DATASET = {
    "dataset_id": 101, "dataset_code": "TEST_SNAPSHOT_A", "sha256": "a" * 64,
    "source_filename": "test_only.csv", "source_code": "TEST_SOURCE",
    "imported_at": STAMP, "observation_count": 2,
    "first_observation": STAMP, "last_observation": STAMP,
    "observed_rows": 2, "estimated_rows": 0, "unverified_rows": 2,
    "validated_rows": 0, "suspect_rows": 0, "invalid_rows": 0,
}
OBSERVATION = {
    "ec_observation_id": 301, "source_row": 2, "observed_at": STAMP,
    "conductivity_ms_per_m": 12.2, "unit": "mS/m", "observed_or_estimated": "O",
    "quality_flag": "UNVERIFIED", "approval_level": "Raw - Not Yet Reviewed",
    "grade": "Unverified data", "source_label": "test_only",
}
STATION = {
    "site_code": "TEST_SITE", "site_name": "Trạm kiểm thử", "external_site_code": "test",
    "location_status": "REPORTED", "location_reference": "test_only",
    "source_code": "TEST_SOURCE", "source_name": "Nguồn kiểm thử",
    "source_reference": "test_only",
    "geometry": {"type": "Point", "coordinates": [105.2480164, 10.80062008]},
}
HISTORY_PATH = "/api/v1/stations/TEST_SITE/observations"


class APIContractTests(unittest.TestCase):
    def setUp(self):
        self.repo = Mock(spec=Repository)
        self.repo.health.return_value = {"database_name": "test_only", "transaction_read_only": True}
        self.repo.stations.return_value = [copy.deepcopy(STATION)]
        self.repo.datasets.return_value = [copy.deepcopy(DATASET)]
        self.repo.history.return_value = {
            "dataset": copy.deepcopy(DATASET), "total": 2, "items": [copy.deepcopy(OBSERVATION)]
        }
        app.dependency_overrides[get_repository] = lambda: self.repo
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.addCleanup(app.dependency_overrides.clear)

    def test_geojson_uses_longitude_latitude_and_keeps_reported_status(self):
        response = self.client.get("/api/v1/stations")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["type"], "FeatureCollection")
        self.assertEqual(body["features"][0]["geometry"]["coordinates"], [105.2480164, 10.80062008])
        self.assertEqual(body["features"][0]["properties"]["location_status"], "REPORTED")

    def test_station_without_coordinates_is_not_given_a_fake_location(self):
        self.repo.stations.return_value[0].update(
            geometry=None, location_status="UNKNOWN", location_reference=None
        )
        body = self.client.get("/api/v1/stations").json()
        self.assertEqual(body["count"], 1)
        self.assertIsNone(body["features"][0]["geometry"])

    def test_dataset_timestamps_have_explicit_vietnam_offset(self):
        response = self.client.get("/api/v1/stations/TEST_SITE/datasets")
        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertEqual(item["first_observation"], "2023-12-15T00:00:00+07:00")
        self.assertEqual(item["sha256"], "a" * 64)

    def test_snapshot_is_required_even_when_only_one_exists(self):
        self.assertEqual(self.client.get(HISTORY_PATH).status_code, 422)
        self.repo.history.assert_not_called()

    def test_history_keeps_unit_quality_and_pagination(self):
        response = self.client.get(HISTORY_PATH, params={"dataset_code": "TEST_SNAPSHOT_A", "limit": 1})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["unit"], "mS/m")
        self.assertEqual(body["items"][0]["quality_flag"], "UNVERIFIED")
        self.assertEqual(body["items"][0]["conductivity_ms_per_m"], 12.2)
        self.assertEqual(body["items"][0]["observed_at"], "2023-12-15T00:00:00+07:00")
        self.assertTrue(body["has_more"])
        self.assertIsNone(self.repo.history.call_args.kwargs["quality_flag"])

    def test_filter_values_reach_repository_without_changing_snapshot(self):
        self.repo.history.return_value["dataset"]["dataset_code"] = "TEST_SNAPSHOT_B"
        response = self.client.get(HISTORY_PATH, params={
            "dataset_code": "TEST_SNAPSHOT_B", "date_from": "2022-01-01", "date_to": "2023-12-31",
            "quality_flag": "SUSPECT", "observed_or_estimated": "E", "limit": 25, "offset": 50,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["dataset"]["dataset_code"], "TEST_SNAPSHOT_B")
        self.repo.history.assert_called_once_with(
            site_code="TEST_SITE", dataset_code="TEST_SNAPSHOT_B",
            date_from=date(2022, 1, 1), date_to=date(2023, 12, 31),
            quality_flag="SUSPECT", observed_or_estimated="E", limit=25, offset=50,
        )

    def test_invalid_date_ranges_are_rejected_before_querying(self):
        for params in [
            {"date_from": "2024-01-01", "date_to": "2023-12-31"},
            {"date_from": "2023-02-30"}, {"date_to": "9999-12-31"},
        ]:
            with self.subTest(params=params):
                response = self.client.get(HISTORY_PATH, params={"dataset_code": "TEST", **params})
                self.assertEqual(response.status_code, 422)
        self.repo.history.assert_not_called()

    def test_invalid_flags_and_page_sizes_are_rejected(self):
        for params in [
            {"quality_flag": "VERIFIED"}, {"observed_or_estimated": "X"},
            {"limit": 0}, {"limit": 1001}, {"offset": -1}, {"dataset_code": ""},
        ]:
            with self.subTest(params=params):
                response = self.client.get(HISTORY_PATH, params={"dataset_code": "TEST", **params})
                self.assertEqual(response.status_code, 422)
        self.repo.history.assert_not_called()

    def test_empty_date_window_is_success_with_no_rows(self):
        self.repo.history.return_value.update(total=0, items=[])
        response = self.client.get(HISTORY_PATH, params={"dataset_code": "TEST", "date_from": "2026-01-01"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertFalse(response.json()["has_more"])

    def test_unknown_station_and_wrong_snapshot_are_404(self):
        for exc, code in [(SiteNotFound, "SITE_NOT_FOUND"), (DatasetNotFound, "DATASET_NOT_FOUND")]:
            with self.subTest(code=code):
                self.repo.history.side_effect = exc
                response = self.client.get(HISTORY_PATH, params={"dataset_code": "TEST"})
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["detail"]["code"], code)

    def test_database_failure_is_not_reported_as_empty_success_or_leaked(self):
        self.repo.health.side_effect = psycopg.OperationalError("password=do-not-expose")
        with self.assertLogs("webgis.api", level="ERROR") as logs:
            response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("do-not-expose", response.text + " ".join(logs.output))

    def test_no_write_endpoint_and_cors_only_allows_configured_origin(self):
        self.assertEqual(self.client.post("/api/v1/stations", json={}).status_code, 405)
        allowed = self.client.get("/api/v1/stations", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(allowed.headers.get("access-control-allow-origin"), "http://localhost:5173")
        other = self.client.get("/api/v1/stations", headers={"Origin": "https://other.example"})
        self.assertNotIn("access-control-allow-origin", other.headers)


class QueryBoundaryTests(unittest.TestCase):
    def test_whole_local_day_uses_exclusive_next_midnight(self):
        where, params = history_predicate(7, 101, date(2023, 12, 15), date(2023, 12, 15), None, None)
        start, end = params[2:]
        self.assertEqual(start.astimezone(timezone.utc), STAMP)
        self.assertEqual(end - start, timedelta(days=1))
        self.assertEqual(end.astimezone(timezone.utc), datetime(2023, 12, 15, 17, tzinfo=timezone.utc))
        self.assertIn("o.observed_at < %s", where)
        self.assertNotIn("o.observed_at <=", where)

    def test_client_values_are_bound_not_formatted_into_predicate(self):
        dangerous = "UNVERIFIED' OR true --"
        where, params = history_predicate(7, 101, None, None, dangerous, "O")
        self.assertNotIn(dangerous, where)
        self.assertEqual(params, [7, 101, dangerous, "O"])

    def test_repository_enforces_station_and_dataset_in_count_and_page(self):
        conn = MagicMock()
        site_cursor, dataset_cursor, count_cursor, page_cursor = [Mock() for _ in range(4)]
        site_cursor.fetchone.return_value = {"site_id": 7}
        dataset_cursor.fetchone.return_value = copy.deepcopy(DATASET)
        count_cursor.fetchone.return_value = {"total": 2}
        page_cursor.fetchall.return_value = [copy.deepcopy(OBSERVATION)]
        conn.execute.side_effect = [site_cursor, dataset_cursor, count_cursor, page_cursor]
        malicious_code = "x'; DROP TABLE public.measurement_site; --"
        with patch("backend.database.read_connection") as connection:
            connection.return_value.__enter__.return_value = conn
            result = Repository().history("TEST_SITE", malicious_code, None, None, None, None, 1, 0)
        calls = conn.execute.call_args_list
        self.assertEqual(calls[1].args[1], (7, malicious_code))
        for call in calls:
            self.assertNotIn(malicious_code, call.args[0])
        for call in calls[2:]:
            self.assertIn("o.site_id = %s", call.args[0])
            self.assertIn("o.dataset_id = %s", call.args[0])
            self.assertEqual(call.args[1][:2], [7, 101])
        self.assertEqual(result["total"], 2)

    def test_wrong_dataset_never_falls_back_to_another_snapshot(self):
        conn = MagicMock()
        site_cursor, dataset_cursor = Mock(), Mock()
        site_cursor.fetchone.return_value = {"site_id": 7}
        dataset_cursor.fetchone.return_value = None
        conn.execute.side_effect = [site_cursor, dataset_cursor]
        with patch("backend.database.read_connection") as connection:
            connection.return_value.__enter__.return_value = conn
            with self.assertRaises(DatasetNotFound):
                Repository().history("TEST_SITE", "WRONG", None, None, None, None, 500, 0)
        self.assertEqual(conn.execute.call_count, 2)


if __name__ == "__main__":
    unittest.main()
