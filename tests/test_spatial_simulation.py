"""Spatial simulation contracts, numerical boundaries, and core isolation."""
import copy
import json
import math
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import psycopg

from backend.main import app
from backend.services import spatial_simulation


METHODOLOGY = '1D River-Axis IDW & Empirical EC-Salinity Conversion (0.0064 g/L per mS/m)'
EXPECTED_ADVISORIES = {
    'OPEN_INTAKE': ('ADVISORY_SAFE_INTAKE', '#10b981',
                    'Nguồn nước thuận lợi · Có thể xem xét lấy nước'),
    'CAUTION_TRANSITION': ('ADVISORY_CHECK_ONSITE', '#f59e0b',
                           'Chớm lợ / Chuyển tiếp · Cần đo kiểm tra tại mũi cống & canh chân triều'),
    'CLOSED_SALINITY_BARRIER': ('ADVISORY_HIGH_SALINITY_RISK', '#ef4444',
                              'Cảnh báo mặn vượt ngưỡng · Khuyến nghị ưu tiên ngăn mặn'),
}


class SpatialSimulationTests(unittest.TestCase):
    def setUp(self):
        environment = dict(os.environ, WEBGIS_RESEARCH_MODE='snapshot')
        environment.pop('WEBGIS_RESEARCH_FILE', None)
        configured = patch.dict(os.environ, environment, clear=True)
        configured.start()
        self.addCleanup(configured.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def read(self, resource, **params):
        response = self.client.get('/api/v1/workspace/simulation/' + resource, params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_empirical_conversion_keeps_ec_unit_scale(self):
        for ec, salinity in [(0, 0), (120, 0.768), (150, 0.96), (1000, 6.4)]:
            with self.subTest(ec=ec):
                self.assertAlmostEqual(spatial_simulation.ec_to_salinity_g_l(ec), salinity)

    def test_gate_threshold_equality_and_hysteresis_band(self):
        state = spatial_simulation.gate_state
        self.assertEqual(state(119.999), 'OPEN_INTAKE')
        self.assertEqual(state(120), 'CAUTION_TRANSITION')
        self.assertEqual(state(149.999), 'CAUTION_TRANSITION')
        self.assertEqual(state(150), 'CLOSED_SALINITY_BARRIER')
        self.assertEqual(state(151), 'CLOSED_SALINITY_BARRIER')

    def test_numeric_helpers_reject_negative_and_nonfinite_values(self):
        for value in [-1, float('nan'), float('inf'), float('-inf'), True]:
            for helper in [spatial_simulation.ec_to_salinity_g_l, spatial_simulation.gate_state]:
                with self.subTest(value=value, helper=helper.__name__), self.assertRaises(ValueError):
                    helper(value)

    def assert_gate_advisory(self, gate, expected_state):
        self.assertEqual(gate['simulated_gate_state'], expected_state)
        self.assertEqual(
            (gate['advisory_code'], gate['advisory_color'], gate['advisory_label']),
            EXPECTED_ADVISORIES[expected_state],
        )
        self.assertIs(gate['human_in_the_loop_Required'], True)
        self.assertIs(gate['canal_particle_intake_enabled'], False)
        self.assertIs(gate['gate_decision_eligible'], False)
        self.assertIsNone(gate['actuator_command'])

    def test_frame_advisories_at_both_threshold_equalities(self):
        cases = [(119.999999, 'OPEN_INTAKE'), (120, 'CAUTION_TRANSITION'),
                 (149.999999, 'CAUTION_TRANSITION'), (150, 'CLOSED_SALINITY_BARRIER')]
        for ec, expected in cases:
            with self.subTest(ec=ec), patch.object(spatial_simulation, '_idw', return_value=ec):
                frame = self.read('frame', year_month='2024-04')
                self.assertEqual(len(frame['gates']), 27)
                for gate in frame['gates']:
                    self.assertEqual(gate['simulated_outside_ec_mS_m'], ec)
                    self.assert_gate_advisory(gate, expected)

    def test_all_timeline_frames_require_manual_intake_confirmation(self):
        for month in self.read('timeline')['items']:
            with self.subTest(month=month['year_month']):
                frame = spatial_simulation.simulation_frame(month['year_month'])
                self.assertTrue(frame['gates'])
                for gate in frame['gates']:
                    ec = gate['simulated_outside_ec_mS_m']
                    expected = ('OPEN_INTAKE' if ec < 120 else
                                'CLOSED_SALINITY_BARRIER' if ec >= 150 else 'CAUTION_TRANSITION')
                    self.assert_gate_advisory(gate, expected)

    def test_corridor_has_connected_geographic_axis_and_27_gates(self):
        result = self.read('corridor')
        self.assertEqual(result['corridor']['type'], 'FeatureCollection')
        features = result['corridor']['features']
        self.assertTrue(features)
        for feature in features:
            self.assertEqual(feature['type'], 'Feature')
            self.assertEqual(feature['geometry']['type'], 'LineString')
            coordinates = feature['geometry']['coordinates']
            self.assertGreaterEqual(len(coordinates), 2)
            for lon, lat in coordinates:
                self.assertTrue(104 < lon < 108)
                self.assertTrue(9 < lat < 12)
        self.assertEqual(len(result['gates']), 27)

    def test_timeline_contains_drought_and_wet_season_frames(self):
        result = self.read('timeline')
        self.assertEqual(result['total'], 495)
        self.assertEqual(result['total'], len(result['items']))
        months = [item['year_month'] for item in result['items']]
        self.assertEqual(months, sorted(set(months)))
        self.assertEqual((months[0], months[-1]), ('1985-06', '2026-08'))
        for month in ['2016-03', '2024-04', '2022-10']:
            self.assertIn(month, months)
        indexed = {item['year_month']: item for item in result['items']}
        for month, upstream, downstream, regime in [
            ('2016-03', 21.8, 385.0, 'OBSERVED_MRC'),
            ('2024-04', 22.651, 26.68, 'ML_FORECAST_ERA5'),
            ('2022-10', 11.5, 13.53, 'OBSERVED_MRC'),
        ]:
            row = indexed[month]
            self.assertAlmostEqual(row['tan_chau_ec_mS_m'], upstream)
            self.assertAlmostEqual(row['my_tho_ec_mS_m'], downstream)
            self.assertEqual(row['data_regime'], regime)
            self.assertFalse(row['imputed'])
            self.assertFalse(row['gate_decision_eligible'])
            self.assertFalse(row['live_forecast_available'])
            self.assertEqual(row['wind']['unit'], 'm/s')
            for evidence in row['boundary_provenance'].values():
                self.assertIn(month, evidence['source_months'])
                self.assertFalse(evidence['verified_observation'])

    def test_frames_preserve_continuity_units_and_simulation_labels(self):
        corridor = self.read('corridor')['corridor']['features']
        axis = next(feature for feature in corridor
                    if feature['properties']['type'] == 'MAIN_RIVER')['geometry']['coordinates']
        for month in ['2016-03', '2024-04', '2022-10']:
            with self.subTest(month=month):
                frame = self.read('frame', year_month=month, open_below_ec=120, close_above_ec=150)
                self.assertTrue(frame['simulation_layer'])
                self.assertEqual(frame['methodology'], METHODOLOGY)
                self.assertEqual(len(frame['gates']), 27)
                self.assertIsInstance(frame['wind'], dict)
                self.assertIsInstance(frame['isohaline_boundaries'], list)
                segments = frame['river_segments']
                self.assertEqual(len(segments), 35)
                self.assertEqual(segments[0]['geometry']['coordinates'][0], axis[0])
                self.assertEqual(segments[-1]['geometry']['coordinates'][-1], axis[-1])
                previous_end = None
                for feature in segments:
                    self.assertEqual(feature['type'], 'Feature')
                    self.assertEqual(feature['geometry']['type'], 'LineString')
                    points = feature['geometry']['coordinates']
                    self.assertGreaterEqual(len(points), 2)
                    if previous_end is not None:
                        self.assertEqual(points[0], previous_end)
                    previous_end = points[-1]
                    properties = feature['properties']
                    ec = properties['ec_mS_m']
                    self.assertTrue(math.isfinite(ec))
                    self.assertGreaterEqual(ec, 0)
                    self.assertEqual(properties['salinity_g_l'], round(ec * 0.0064, 3))
                    self.assertIn('flow_direction', properties)
                    self.assertTrue(math.isfinite(properties['flow_velocity_factor']))
                    self.assertGreaterEqual(properties['flow_velocity_factor'], 0)
                self.assertNotEqual(segments[0]['geometry']['coordinates'][0], previous_end)
                for gate in frame['gates']:
                    ec = gate['simulated_outside_ec_mS_m']
                    self.assertEqual(gate['simulated_outside_salinity_g_l'], round(ec * 0.0064, 3))
                    expected = 'OPEN_INTAKE' if ec < 120 else 'CLOSED_SALINITY_BARRIER' if ec >= 150 else 'CAUTION_TRANSITION'
                    self.assert_gate_advisory(gate, expected)

    def test_invalid_month_and_thresholds_are_controlled_client_errors(self):
        cases = [({}, 422), ({'year_month': '2024-13'}, 422),
                 ({'year_month': '2024-4'}, 422), ({'year_month': '2099-01'}, 404),
                 ({'year_month': '0000-01'}, 422), ({'year_month': '1985-05'}, 404)]
        for params in [{'open_below_ec': -1}, {'open_below_ec': 150},
                       {'open_below_ec': 160}, {'close_above_ec': 'nan'},
                       {'open_below_ec': 'inf'}, {'close_above_ec': -1},
                       {'open_below_ec': 0, 'close_above_ec': 0}]:
            cases.append((dict(year_month='2024-04', **params), 422))
        for params, status in cases:
            with self.subTest(params=params):
                response = self.client.get('/api/v1/workspace/simulation/frame', params=params)
                self.assertEqual(response.status_code, status, response.text)

    def test_axis_anchors_projection_and_idw_reproduce_boundary_conditions(self):
        frame = self.read('frame', year_month='2024-04')
        corridor = self.read('corridor')['corridor']['features']
        coordinates = next(f for f in corridor if f['properties']['id'] == 'TIEN_MAIN')['geometry']['coordinates']
        axis = spatial_simulation.RiverAxis(coordinates)
        anchors = [(r['chainage_km'], r['ec_mS_m']) for r in frame['boundary_conditions']]
        self.assertEqual([x for x, _ in anchors], [0, 125, 175])
        for chainage, ec in anchors:
            with self.subTest(chainage=chainage):
                self.assertEqual(spatial_simulation._idw(chainage, anchors), ec)
                projection = axis.project(axis.coordinate(chainage))
                self.assertAlmostEqual(projection['chainage_km'], chainage, places=5)
                self.assertEqual(projection['distance_to_axis_km'], 0)
                self.assertFalse(projection['hydrological_link_validated'])
        self.assertEqual(axis.coordinate(125), [106.36, 10.35])
        for (a, ea), (b, eb) in zip(anchors, anchors[1:]):
            self.assertAlmostEqual(spatial_simulation._idw((a + b) / 2, anchors), (ea + eb) / 2)
        segments = spatial_simulation.interpolate_river_profile('2024-04')
        self.assertEqual(segments, frame['river_segments'])
        self.assertEqual(segments[0]['properties']['start_ec_mS_m'], anchors[0][1])
        self.assertEqual(segments[24]['properties']['end_ec_mS_m'], anchors[1][1])
        self.assertEqual(segments[-1]['properties']['end_ec_mS_m'], anchors[-1][1])

    def test_isohaline_crossings_and_seasonal_flow_are_consistent(self):
        for month in ['2016-03', '2024-04', '2022-10']:
            frame = self.read('frame', year_month=month)
            anchors = [(r['chainage_km'], r['ec_mS_m']) for r in frame['boundary_conditions']]
            directions = {f['properties']['flow_direction'] for f in frame['river_segments']}
            if month == '2022-10':
                self.assertEqual(directions, {'DOWNSTREAM_FRESHWATER'})
                self.assertFalse(frame['assumptions']['dry_season'])
            else:
                self.assertIn('UPSTREAM_SALINE_INTRUSION', directions)
                self.assertTrue(frame['assumptions']['dry_season'])
            self.assertEqual([r['salinity_g_l'] for r in frame['isohaline_boundaries']], [1, 4])
            for boundary in frame['isohaline_boundaries']:
                threshold = boundary['salinity_g_l'] / 0.0064
                self.assertEqual(boundary['threshold_ec_mS_m'], threshold)
                for crossing in boundary['crossings']:
                    self.assertAlmostEqual(spatial_simulation._idw(crossing['chainage_km'], anchors), threshold, places=3)
                if boundary['status'] == 'WITHIN_CORRIDOR':
                    self.assertAlmostEqual(boundary['intrusion_distance_km'], 175 - boundary['chainage_km'], places=5)
                elif boundary['status'] == 'NOT_REACHED_AT_ESTUARY':
                    self.assertLess(anchors[-1][1], threshold)
                    self.assertIsNone(boundary['coordinate'])

    def test_postgres_coordinates_override_catalog_without_inventing_missing_locations(self):
        corridor = self.read('corridor')['corridor']
        bundle = {'storage_mode': 'postgres', 'gates': []}
        database_rows = [
            {'gate_code': 'GATE_TG_000', 'geometry': {'type': 'Point', 'coordinates': [106.2, 10.4]}},
            {'gate_code': 'DATABASE_EXTRA', 'geometry': {'type': 'Point', 'coordinates': [106.3, 10.3]}},
            {'gate_code': 'MISSING', 'geometry': None},
        ]
        with patch.object(spatial_simulation.store, 'database_gates', return_value={'items': database_rows}):
            gates, audit = spatial_simulation._catalog_gates(bundle, corridor)
        indexed = {gate['gate_code']: gate for gate in gates}
        self.assertEqual(len(indexed), 28)
        self.assertEqual(indexed['GATE_TG_000']['coordinates'], [106.2, 10.4])
        self.assertEqual(indexed['GATE_TG_000']['coordinate_source'], 'POSTGRESQL')
        self.assertNotIn('MISSING', indexed)
        self.assertEqual(audit['excluded_gate_codes_without_coordinates'], ['MISSING'])
        self.assertEqual(audit['database_gate_count'], 3)
        self.assertEqual(database_rows[0]['geometry']['coordinates'], [106.2, 10.4])

    def test_invalid_corridor_geometry_returns_unavailable(self):
        corridor = self.read('corridor')['corridor']
        for mutation in ['duplicate_vertex', 'wrong_endpoint', 'missing_anchor']:
            damaged = copy.deepcopy(corridor)
            axis = next(f for f in damaged['features'] if f['properties']['id'] == 'TIEN_MAIN')
            points = axis['geometry']['coordinates']
            if mutation == 'duplicate_vertex':
                points.insert(1, points[0][:])
            elif mutation == 'wrong_endpoint':
                points[-1] = [106.8, 10.2]
            else:
                points.remove([106.36, 10.35])
            with self.subTest(mutation=mutation), patch.object(spatial_simulation, 'CORRIDOR_PATH') as source:
                source.read_text.return_value = json.dumps(damaged)
                response = self.client.get('/api/v1/workspace/simulation/corridor')
                self.assertEqual(response.status_code, 503, response.text)

    def test_database_gate_failure_is_not_hidden_by_local_catalog(self):
        bundle = {'storage_mode': 'postgres', 'gates': []}
        with patch.object(spatial_simulation, 'load_bundle', return_value=bundle):
            with patch.object(spatial_simulation.store, 'database_gates', side_effect=psycopg.OperationalError()):
                response = self.client.get('/api/v1/workspace/simulation/corridor')
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()['detail']['code'], 'DATABASE_ERROR')

    def test_simulation_requests_leave_core_outputs_unchanged(self):
        paths = ['summary', 'stations', 'gates', 'monthly-estimates?station=MyTho',
                 'multivariate/catalog', 'multivariate/evaluation?station=MyTho']
        before = {}
        for path in paths:
            response = self.client.get('/api/v1/workspace/' + path)
            self.assertEqual(response.status_code, 200, response.text)
            before[path] = response.json()
        item = {'schema_version': 1, 'is_demo': False, 'gate_code': 'G1'}
        payload = {'policy': item, 'input': item}
        evaluation = self.client.post('/api/v1/workspace/gate-evaluation', json=payload).json()
        self.read('corridor')
        self.read('timeline')
        for month in ['2016-03', '2024-04', '2022-10']:
            self.read('frame', year_month=month, open_below_ec=5, close_above_ec=10)
        for path in paths:
            self.assertEqual(self.client.get('/api/v1/workspace/' + path).json(), before[path])
        after = self.client.post('/api/v1/workspace/gate-evaluation', json=payload).json()
        after.pop('evaluated_at', None)
        evaluation.pop('evaluated_at', None)
        self.assertEqual(after, evaluation)
        self.assertIsNone(after['recommendation'])
        self.assertIsNone(after['actuator_command'])


if __name__ == '__main__':
    unittest.main()
