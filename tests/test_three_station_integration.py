import hashlib
import json
import os
import unittest
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi.testclient import TestClient
from backend.main import app
from backend.domain.river_interpolation import interpolate_anchors, MY_THUAN_KM
from backend.services import spatial_simulation, spatial_inputs
from backend.domain import multivariate_ec
from backend.repositories.multivariate_inputs import get_weather_input
from backend.services.workspace import WorkspaceError
from scripts.integrate_mythuan import ROOT, SOURCE_FILE


class ThreeStationIntegration(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, WEBGIS_RESEARCH_MODE='snapshot')
        env.start()
        self.addCleanup(env.stop)

    def test_piecewise_exact_anchors_local_midpoints_and_reversal(self):
        anchors = [(0, 10), (MY_THUAN_KM, 100), (125, 20)]
        for x, ec in anchors:
            self.assertAlmostEqual(interpolate_anchors(x, anchors), ec)
        self.assertAlmostEqual(interpolate_anchors(MY_THUAN_KM / 2, anchors), 55)
        self.assertAlmostEqual(interpolate_anchors((MY_THUAN_KM + 125) / 2, anchors), 60)
        self.assertAlmostEqual(interpolate_anchors(MY_THUAN_KM-1e-7, anchors), 100, places=5)
        self.assertAlmostEqual(interpolate_anchors(MY_THUAN_KM+1e-7, anchors), 100, places=5)
        with self.assertRaises(ValueError):
            interpolate_anchors(5, [(0,10),(0,20)])

    def test_historical_fallback_is_exactly_the_13_missing_months(self):
        timeline = spatial_inputs.monthly_inputs()
        missing = [m for m, item in timeline.items() if m < '2024-01' and item['my_thuan_ec_mS_m'] is None]
        self.assertEqual(len(missing), 13)
        for month in missing:
            item = timeline[month]
            self.assertEqual(item['interpolation_mode'], 'TWO_STATION_FALLBACK_MISSING_MYTHUAN')
            self.assertEqual(item['boundary_provenance']['MyThuan']['sample_count'], 0)
            self.assertFalse(item['boundary_provenance']['MyThuan']['imputed'])
        frame = spatial_simulation.simulation_frame(missing[0])
        self.assertEqual(len(frame['boundary_conditions']), 3)  # two stations plus scenario estuary
        anchors = [(a['chainage_km'],a['ec_mS_m']) for a in frame['boundary_conditions']]
        self.assertAlmostEqual(spatial_simulation._idw(62.5, anchors),
            (frame['inputs']['tan_chau_ec_mS_m'] + frame['inputs']['my_tho_ec_mS_m'])/2)
        for month, item in timeline.items():
            if month >= '2024-01':
                self.assertIsNotNone(item['my_thuan_ec_mS_m'])
                self.assertEqual(item['interpolation_mode'], 'PIECEWISE_3_STATION')

    def test_future_map_has_rolling_year_with_explicit_input_kind(self):
        timeline = spatial_inputs.monthly_inputs()
        now = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))
        index = now.year * 12 + now.month - 1 + 12
        expected_end = f'{index // 12:04d}-{index % 12 + 1:02d}'
        self.assertGreaterEqual(max(timeline), expected_end)
        item = timeline[expected_end]
        self.assertEqual(item['interpolation_mode'], 'PIECEWISE_3_STATION')
        self.assertIn(item['data_regime'], {'ML_FORECAST_ERA5', 'SEASONAL_SCENARIO'})
        for station in ('TanChau', 'MyThuan', 'MyTho'):
            provenance = item['boundary_provenance'][station]
            self.assertIn(provenance['evidence_kind'], {'ML_FORECAST_ERA5', 'SEASONAL_MEDIAN_SCENARIO'})
            self.assertFalse(provenance['verified_observation'])

    def test_frame_ribbon_knot_and_gate_projection_share_piecewise_values(self):
        frame = spatial_simulation.simulation_frame('2022-03')
        anchors = [(a['chainage_km'],a['ec_mS_m']) for a in frame['boundary_conditions']]
        segment = next(s['properties'] for s in frame['river_segments'] if s['properties']['chainage_start_km'] < MY_THUAN_KM < s['properties']['chainage_end_km'])
        self.assertEqual(len(segment['ec_stops']),3)
        self.assertAlmostEqual(segment['ec_stops'][1]['ec_mS_m'], frame['inputs']['my_thuan_ec_mS_m'])
        for gate in frame['gates']:
            self.assertAlmostEqual(gate['simulated_outside_ec_mS_m'], interpolate_anchors(gate['chainage_km'],anchors),places=4)

    def test_missing_forecast_anchor_is_unavailable_instead_of_two_station_fallback(self):
        item = dict(spatial_inputs.monthly_inputs()['2024-01'], my_thuan_ec_mS_m=None)
        with self.assertRaises(WorkspaceError):
            spatial_simulation._anchors(item)
        rows = [r for r in spatial_inputs.estimate_rows() if not (r['station'] == 'MyThuan' and r['year_month'] == '2024-01')]
        with patch.object(spatial_inputs, 'estimate_rows', return_value=rows):
            with self.assertRaises(WorkspaceError) as result:
                spatial_inputs.monthly_inputs()
            self.assertEqual(result.exception.status_code, 503)

    def test_registered_model_weather_and_both_api_prefixes(self):
        self.assertEqual(multivariate_ec.normalize_station('MRC_VN_019804'), 'MYTHUAN')
        weather = get_weather_input('MYTHUAN','2024-04')
        self.assertEqual(weather['input_month'],'2024-02')
        self.assertIn('mythuan_weather_',weather['source'])
        with TestClient(app) as client:
            for prefix in ('/api/v1/multivariate','/api/v1/workspace/multivariate'):
                catalog = client.get(prefix+'/catalog').json()
                self.assertEqual({s['station'] for s in catalog['stations']},{'TanChau','MyThuan','MyTho'})
                for name in ('TANCHAU','MYTHUAN','MYTHO'):
                    result = client.post(prefix+'/predict',json=dict(station=name,target_month='2024-04',input_mode='ARCHIVE'))
                    self.assertEqual(result.status_code,200,result.text)
                evaluation = client.get(prefix+'/evaluation',params={'station':'MYTHUAN'})
                self.assertEqual(evaluation.status_code,200,evaluation.text)
                self.assertEqual(len(evaluation.json()['items']),24)
                self.assertAlmostEqual(evaluation.json()['metrics']['RandomForest']['mae_mS_m'],3.917424685935801)

    def test_dataset_quality_and_complete_future_station_cohorts(self):
        bundle = json.loads((ROOT/'data/research/workspace.json').read_text('utf-8'))
        rows = [r for r in bundle['observations'] if r['site_code']=='MRC_VN_019804']
        self.assertEqual(len(rows),451)
        self.assertTrue(all(r['quality_flag']=='UNVERIFIED' and r['ec_temperature_basis']=='UNKNOWN' for r in rows))
        station = next(s for s in bundle['stations'] if s['site_code']=='MRC_VN_019804')
        self.assertEqual(station['geometry']['coordinates'],[105.9263229,10.27532005])
        self.assertEqual(station['chainage_km'],MY_THUAN_KM)
        targets = pd.read_csv(ROOT/'data/research/mrc_ec_monthly_samples.csv')
        middle_targets = targets[targets.station.eq('MYTHUAN')]
        self.assertEqual(len(middle_targets),451)
        self.assertEqual(set(middle_targets.quality_flag),{'UNVERIFIED'})
        self.assertEqual(set(middle_targets.ec_temperature_basis),{'UNKNOWN'})
        future = pd.read_csv(ROOT/'data/models/future_ec_forecast_2024_2026.csv')
        for _, group in future.groupby('year_month'):
            self.assertEqual(set(group.station), {'TanChau','MyThuan','MyTho'})
            self.assertEqual(len(group),3)
        registry = json.loads((ROOT/'data/models/multivariate_registry.json').read_text('utf-8'))
        self.assertEqual(registry['models']['MYTHUAN']['model_sha256'],
            hashlib.sha256((ROOT/'outputs/mythuan_three_station_20261104/mythuan_model.joblib').read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
