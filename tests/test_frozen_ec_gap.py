"""Leakage, availability and serving checks for a continuing-weather EC outage."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from backend.domain import ec_gap_evaluation, multivariate_ec
from backend.main import app
from scripts.evaluate_frozen_ec_gap import (
    FEATURES, MODELS, OUTPUT, ROOT, forecast_gap, freeze_training, spatial_predictions,
)


def synthetic():
    months = pd.date_range('2016-01-01', '2023-12-01', freq='MS')
    data = pd.DataFrame({'month_start': months, 'weather_month': months - pd.DateOffset(months=2),
                         'conductivity_mS_per_m': np.arange(len(months)) + 10.})
    data['rainfall_mm'] = 20. + np.arange(len(months))
    data['temperature_degC'], data['wind_source_units'] = 25., 2.
    data['month_sin'] = np.sin(2 * np.pi * months.month / 12)
    data['month_cos'] = np.cos(2 * np.pi * months.month / 12)
    return data


class SpyModel:
    def __init__(self, fits):
        self.fits = fits

    def fit(self, x, y):
        self.fits.append((x.copy(), y.copy()))
        self.mean = y.mean()
        return self

    def predict(self, x):
        return self.mean + x.iloc[:, 0].to_numpy()


class FrozenProtocolChecks(unittest.TestCase):
    def setUp(self):
        self.data = synthetic()
        self.known = freeze_training(self.data, '2021-01-01', 5)
        self.future = self.data[self.data.month_start >= '2021-01-01'].copy()
        self.fits = []

    def forecast(self, future=None):
        return forecast_gap(self.known, self.future if future is None else future,
                            model_factory=lambda: SpyModel(self.fits))

    def test_first_issue_freezes_labels_and_latency_sensitivity(self):
        self.assertEqual(self.known.month_start.max(), pd.Timestamp('2020-11-01'))
        delayed = freeze_training(self.data, '2021-01-01', 35)
        self.assertEqual(delayed.month_start.max(), pd.Timestamp('2020-10-01'))

    def test_withheld_ec_cannot_change_predictions_or_baselines(self):
        first = self.forecast()
        changed = self.future.copy()
        changed['conductivity_mS_per_m'] = 1e9
        second = self.forecast(changed)
        pd.testing.assert_frame_equal(first, second)
        self.assertNotIn('conductivity_mS_per_m', first.columns)

    def test_models_fit_once_only_on_frozen_labels_and_no_ec_features(self):
        result = self.forecast()
        self.assertEqual(len(result), 36)
        self.assertEqual(len(self.fits), 2)  # RF and calendar-only ablation, each fit once.
        for x, y in self.fits:
            self.assertEqual(len(x), len(self.known))
            np.testing.assert_array_equal(y, self.known.conductivity_mS_per_m)
            self.assertTrue(set(x.columns).issubset(FEATURES))

    def test_weather_can_change_rf_without_new_ec_or_changing_frozen_baselines(self):
        first = self.forecast()
        changed = self.future.copy()
        changed['rainfall_mm'] += 100
        second = self.forecast(changed)
        self.assertFalse(np.allclose(first.RandomForest, second.RandomForest))
        for model in MODELS[1:]:
            np.testing.assert_array_equal(first[model], second[model])

    def test_direct_seasonal_stops_when_source_ec_is_withheld(self):
        result = self.forecast()
        self.assertEqual(int(result.seasonal_naive_available.sum()), 11)
        self.assertTrue(result.loc[result.month_start >= '2022-01-01', 'SeasonalNaive'].isna().all())
        self.assertTrue(result.FrozenSeasonalRepeat.notna().all())
        january = result[result.month_start.dt.month == 1].FrozenSeasonalRepeat
        self.assertEqual(january.nunique(), 1)
        expected = self.known[self.known.month_start.dt.month == 1].conductivity_mS_per_m.iloc[-1]
        self.assertEqual(january.iloc[0], expected)

    def test_invalid_weather_and_label_overlap_are_rejected(self):
        for modification in ('future_weather', 'missing_weather', 'duplicate_month'):
            with self.subTest(modification=modification):
                changed = self.future.copy()
                if modification == 'future_weather':
                    changed['weather_month'] = changed.month_start - pd.DateOffset(months=1)
                elif modification == 'missing_weather':
                    changed.iloc[0, changed.columns.get_loc('rainfall_mm')] = np.nan
                else:
                    changed = pd.concat([changed, changed.iloc[:1]])
                with self.assertRaises(ValueError):
                    self.forecast(changed)
        with self.assertRaises(ValueError):
            forecast_gap(self.future, self.future, model_factory=lambda: SpyModel(self.fits))

    def test_spatial_anchor_uses_forecast_and_rejects_unmatched_months(self):
        data = pd.DataFrame([dict(experiment='gap', ec_delay_days=5, target_month=pd.Timestamp('2022-01-01'),
            gap_year=1, station=station, actual_mS_m=actual, RandomForest=predicted)
            for station, actual, predicted in [('TANCHAU', 10, 12), ('MYTHUAN', 20, 25), ('MYTHO', 110, 100)]])
        result = spatial_predictions(data).iloc[0]
        self.assertEqual(result.THREE_FORECAST_ANCHOR, 25)
        self.assertEqual(result.actual_mS_m, 20)
        with self.assertRaises(ValueError):
            spatial_predictions(data.iloc[:2])


class FrozenEvidenceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ec_gap_evaluation.INDEX.exists():
            raise unittest.SkipTest('Run scripts/evaluate_frozen_ec_gap.py --publish first')
        cls.manifest = json.loads((OUTPUT / 'run_manifest.json').read_text('utf-8'))
        cls.predictions = pd.read_csv(OUTPUT / 'predictions.csv')

    def test_checksums_and_no_deployed_weight_changes(self):
        for relative, expected in self.manifest['input_sha256'].items():
            with self.subTest(source=relative):
                if relative != 'backend/domain/multivariate_ec.py':
                    self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected)
        for relative, expected in self.manifest['weather_source_sha256'].items():
            with self.subTest(weather=relative):
                self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected)
        for filename, expected in self.manifest['output_sha256'].items():
            self.assertEqual(hashlib.sha256((OUTPUT / filename).read_bytes()).hexdigest(), expected)
        historical_paths = {'MYTHO': 'runs/multivariate_ec/mytho/20261023T041813Z/model.joblib',
                            'TANCHAU': 'runs/multivariate_ec/tanchau/20261023T041813Z/model.joblib',
                            'MYTHUAN': 'runs/multivariate_ec/mythuan/20261104T_MYTHUAN_3STATION/model.joblib'}
        self.assertEqual({station: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                          for station, path in historical_paths.items()}, self.manifest['deployed_model_sha256'])

    def test_all_months_use_the_same_frozen_labels_and_timely_weather(self):
        rows = self.predictions
        self.assertEqual(len(rows), 576)
        self.assertFalse(rows.duplicated(['experiment', 'ec_delay_days', 'station', 'target_month']).any())
        self.assertTrue((rows.refit_count == 1).all())
        self.assertTrue((pd.to_datetime(rows.last_training_ec_available_at) <= pd.to_datetime(rows.first_issue_date_local)).all())
        self.assertTrue((pd.to_datetime(rows.weather_assumed_available_at) <= pd.to_datetime(rows.issue_date_local)).all())
        for _, group in rows.groupby(['experiment', 'ec_delay_days', 'station']):
            self.assertEqual(group.last_training_ec_month.nunique(), 1)
            self.assertEqual(group.training_months.nunique(), 1)
            self.assertTrue(group.loc[group.gap_year > 1, 'SeasonalNaive'].isna().all())

    def test_both_api_prefixes_all_stations_and_alternate_protocols(self):
        with patch.dict(os.environ, WEBGIS_RESEARCH_MODE='snapshot'), TestClient(app) as client:
            for prefix in ('/api/v1/multivariate', '/api/v1/workspace/multivariate'):
                for station in ('TANCHAU', 'MYTHUAN', 'MYTHO'):
                    response = client.get(prefix + '/evaluation', params=dict(station=station, protocol=ec_gap_evaluation.PROTOCOL))
                    self.assertEqual(response.status_code, 200, response.text)
                    data = response.json()
                    self.assertEqual(len(data['items']), 36)
                    self.assertEqual(data['protocol_id'], ec_gap_evaluation.PROTOCOL)
                    self.assertEqual(data['frozen_ec_through'], '2020-11-01')
                    self.assertEqual(data['seasonal_naive']['available_months'], 11)
                    self.assertNotIn('SeasonalNaive', data['metrics'])
                response = client.get(prefix + '/evaluation', params=dict(station='MYTHUAN', protocol=ec_gap_evaluation.PROTOCOL,
                    experiment='gap_2022_2023', ec_delay_days=35))
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(len(response.json()['items']), 24)
                self.assertEqual(response.json()['frozen_ec_through'], '2021-10-01')
                invalid = client.get(prefix + '/evaluation', params=dict(station='MYTHUAN', protocol=ec_gap_evaluation.PROTOCOL, experiment='other'))
                self.assertEqual(invalid.status_code, 422)
                old = client.get(prefix + '/evaluation', params=dict(station='MYTHUAN'))
                self.assertEqual(old.status_code, 200, old.text)
                self.assertEqual(old.json()['protocol_id'], 'HISTORICAL')
                self.assertEqual(len(old.json()['items']), 24)

    def test_modified_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'outputs') as temporary:
            index = json.loads(ec_gap_evaluation.INDEX.read_text('utf-8'))
            index['run_manifest_sha256'] = '0' * 64
            path = Path(temporary) / 'index.json'
            path.write_text(json.dumps(index), encoding='utf-8')
            with patch.object(ec_gap_evaluation, 'INDEX', path), self.assertRaisesRegex(ValueError, 'checksum'):
                ec_gap_evaluation.records('MYTHUAN')

    def test_catalog_and_prediction_carry_frozen_evaluation_separately(self):
        catalog = multivariate_ec.model_catalog()
        for station in catalog:
            self.assertEqual(station['gap_validation']['metrics']['RandomForest']['n'], 36)
            self.assertIn('historical_evaluation_protocol', station)

    def test_archive_all_stations_match_registered_models_and_exact_weather_lag(self):
        from backend.repositories.multivariate_inputs import get_monthly_weather
        path = ROOT / 'data/models/future_ec_forecast_2024_2026.csv'
        manifest = json.loads(path.with_suffix('.manifest.json').read_text('utf-8'))
        self.assertEqual(manifest['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(self.manifest['deployment_archive_sha256'], manifest['sha256'])
        self.assertFalse(manifest['ec_required_at_inference'])
        archive = pd.read_csv(path)
        self.assertEqual(len(archive), 96)
        for station, rows in archive.groupby('station'):
            months = pd.to_datetime(rows.year_month)
            expected_input = (months - pd.DateOffset(months=2)).dt.strftime('%Y-%m')
            self.assertEqual(rows.input_month.tolist(), expected_input.tolist())
            weather = {r['input_month']: r for r in get_monthly_weather(station)}
            for row in rows.itertuples():
                source = weather[row.input_month]
                self.assertAlmostEqual(row.rainfall_mm, source['rainfall_mm'])
                self.assertAlmostEqual(row.wind_m_s, source['wind_source_units'])
                self.assertEqual(row.weather_sha256, source['sha256'])
            if station == 'MyTho':
                import joblib
                old_path = ROOT / 'runs/multivariate_ec/mytho/20261023T041813Z/model.joblib'
                model = joblib.load(old_path)
                expected_sha = hashlib.sha256(old_path.read_bytes()).hexdigest()
            else:
                model, info = multivariate_ec.load_model(station)
                expected_sha = info['model_sha256']
            self.assertTrue(rows.model_sha256.eq(expected_sha).all())
            features = pd.DataFrame(dict(rainfall_mm=rows.rainfall_mm, temperature_degC=rows.temperature_degC,
                wind_source_units=rows.wind_m_s, month_sin=np.sin(2*np.pi*months.dt.month/12),
                month_cos=np.cos(2*np.pi*months.dt.month/12)))
            np.testing.assert_allclose(rows.predicted_ec_mS_m, model.predict(features[FEATURES]), rtol=0, atol=1e-10)

    def test_synced_timeline_and_direct_forecast_share_all_three_anchors(self):
        from backend.services import spatial_simulation, multivariate
        with patch.dict(os.environ, WEBGIS_RESEARCH_MODE='snapshot'):
            frame = spatial_simulation.simulation_frame('2026-08')
            for name, field in [('TANCHAU', 'tan_chau_ec_mS_m'), ('MYTHUAN', 'my_thuan_ec_mS_m'), ('MYTHO', 'my_tho_ec_mS_m')]:
                prediction = multivariate.predict(dict(station=name, target_month='2026-08', input_mode='ARCHIVE'))
                self.assertAlmostEqual(frame['inputs'][field], prediction['predicted_ec_mS_m'], places=10)
                self.assertEqual(prediction['gap_validation']['metrics']['RandomForest']['n'], 36)


if __name__ == '__main__':
    unittest.main()
