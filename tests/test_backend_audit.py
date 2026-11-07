"""Regression tests for month alignment, dossier chronology and source labels."""
from datetime import date
import unittest
from unittest.mock import patch

from backend.domain.gates import evaluate
from backend.domain.gate_simulation import simulate
from backend.services import dss_storage, forecasts, multivariate, spatial_inputs
from backend.services.workspace import WorkspaceError
from backend.repositories import workspace as workspace_store


class BackendAuditTests(unittest.TestCase):
    def test_postgres_keeps_ria2_reference_points_from_verified_snapshot(self):
        path = workspace_store.ROOT / 'data/research/workspace.json'
        manifest = path.with_name('workspace_manifest.json')
        bundle = workspace_store._file_bundle(str(path), path.stat().st_mtime_ns,
                                              manifest.stat().st_mtime_ns)
        stations, observations, sources = workspace_store._snapshot_reference_points(
            bundle, {'MRC_VN_019803', 'MRC_VN_019804', 'MRC_VN_019805'}, set())
        self.assertEqual(len(stations), 10)
        self.assertEqual(len(observations), 50)
        self.assertTrue(all(station['reference_only'] and station['geometry'] is None
                            and station['observation_source'] == 'RESEARCH_SNAPSHOT_RIA2'
                            for station in stations))
        self.assertEqual({row['source_id'] for row in observations},
                         {source['source_id'] for source in sources})
        imported = stations[0]['site_code']
        remaining, rows, _ = workspace_store._snapshot_reference_points(
            bundle, {imported}, set())
        self.assertEqual(len(remaining), 9)
        self.assertFalse(any(row['site_code'] == imported for row in rows))

    def draft(self):
        policy = dict(schema_version=1, is_demo=False, gate_code='G1')
        data = dict(policy, issue_time='2026-10-28T12:00:00+07:00', observations={})
        return policy, data

    def test_draft_rejects_wrong_level_unit_before_persistence(self):
        policy, data = self.draft()
        data['observations']['outside_level'] = dict(value=100, unit='cm')
        with patch.object(dss_storage.store, 'save_draft') as save:
            with self.assertRaises(WorkspaceError) as caught:
                dss_storage.save_draft('G1', data, policy)
            self.assertEqual(caught.exception.status_code, 422)
            save.assert_not_called()

    def test_chronology_rejected_in_planning_simulation_and_saved_draft(self):
        policy, data = self.draft()
        cases = [
            dict(observed_at='2026-10-29T12:00:00+07:00'),
            dict(observed_at='2026-10-28T11:00:00+07:00', available_at='2026-10-28T10:00:00+07:00'),
            dict(observed_at='2026-10-28T11:00:00+07:00', available_at='2026-10-28T13:00:00+07:00'),
        ]
        for record in cases:
            with self.subTest(record=record):
                data['observations'] = dict(outside_level=dict(value=1, unit='m', **record))
                self.assertEqual(evaluate(policy, data)['status'], 'INVALID_INPUT')
                self.assertEqual(simulate(policy, data)['status'], 'INVALID_INPUT')
                with self.assertRaises(WorkspaceError):
                    dss_storage.validate_draft('G1', data, policy)

    def test_draft_accepts_incomplete_template_and_equivalent_timezone_instants(self):
        policy, data = self.draft()
        data['observations'] = dict(outside_level=dict(value=None, unit='m',
            observed_at='2026-10-28T04:00:00Z', available_at='2026-10-28T11:30:00+07:00'))
        dss_storage.validate_draft('G1', data, policy)
        for broken in ([], None, 'text'):
            with self.assertRaises(WorkspaceError):
                dss_storage.validate_draft('G1', broken, policy)

    def test_boolean_schema_is_not_version_one(self):
        policy, data = self.draft()
        data['schema_version'] = True
        self.assertEqual(evaluate(policy, data)['status'], 'INVALID_INPUT')
        self.assertEqual(simulate(policy, data)['status'], 'INVALID_INPUT')

    def test_archive_weather_must_match_station_input_month_and_month_end(self):
        selected = dict(station='MyTho')
        valid = dict(station='MyTho', input_month='2026-08', observed_through='2026-08-31',
                     assumed_available_at='2026-09-05', wind_unit='m/s', complete=True)
        with patch.object(multivariate, '_station', return_value=selected):
            with patch.object(multivariate.weather, 'get_weather_input', return_value=valid):
                self.assertEqual(multivariate.inputs('MyTho', '2026-10')['input_month'], '2026-08')
            for change in [dict(station='TanChau'), dict(input_month='2026-09'),
                           dict(observed_through='2026-08-30'), dict(assumed_available_at='2026-08-01')]:
                with self.subTest(change=change), patch.object(multivariate.weather, 'get_weather_input', return_value=dict(valid, **change)):
                    with self.assertRaises(WorkspaceError) as caught:
                        multivariate.inputs('MyTho', '2026-10')
                    self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(multivariate._input_month(date(2026, 1, 1)), '2025-11')

    def test_forecast_catalogue_and_loaded_artifact_cannot_mix_versions(self):
        selected = dict(station='MyTho', trained_through='2023-12-01', model_version='old')
        payload = dict(station='MyTho', target_month='2026-10', input_mode='MANUAL',
                       rainfall_mm=10, temperature_degC=28, wind_source_units=2)
        prediction = dict(model_version='new', training_cutoff='2023-12-01')
        with patch.object(multivariate, '_station', return_value=selected), patch.object(multivariate.models, 'predict_month', return_value=prediction):
            with self.assertRaises(WorkspaceError) as caught:
                multivariate.predict(payload)
            self.assertEqual(caught.exception.status_code, 503)

    def test_invalid_archived_month_or_negative_weather_is_unavailable(self):
        base = dict(station='MyTho', year_month='2024-01', model='RF', predicted_ec_mS_m='1',
                    rainfall_mm='1', temperature_degC='20', wind_m_s='1')
        for change in [dict(year_month='2024-1'), dict(rainfall_mm='-1'), dict(wind_m_s='-1')]:
            with self.subTest(change=change), patch.object(forecasts, 'estimate_rows', return_value=[dict(base, **change)]):
                with self.assertRaises(WorkspaceError):
                    forecasts.monthly_estimates()

    def test_monthly_boundary_excludes_invalid_and_retains_estimate_suspect_flags(self):
        base = dict(site_code='S', observed_date='2020-01-15', source_id='A')
        rows = [dict(base, ec_mS_m=10, observed_or_estimated='O', quality_flag='UNVERIFIED'),
                dict(base, ec_mS_m=30, observed_or_estimated='E', quality_flag='SUSPECT'),
                dict(base, ec_mS_m=900, observed_or_estimated='O', quality_flag='INVALID')]
        record = spatial_inputs._observed_months(dict(observations=rows), 'S')['2020-01']
        self.assertEqual(record['value'], 20)
        self.assertEqual(record['sample_count'], 2)
        self.assertEqual(record['excluded_invalid_sample_count'], 1)
        self.assertEqual(record['observed_or_estimated_counts'], dict(O=1, E=1))
        self.assertIn('SUSPECT', record['quality_flags'])
        self.assertEqual(record['evidence_kind'], 'SOURCE_SAMPLE_MONTHLY_AGGREGATE')
        self.assertFalse(record['verified_observation'])

    def test_available_sample_mean_retains_sources_through_imputation(self):
        rows = [dict(site_code='S', observed_date='2020-01-15', ec_mS_m=10,
                     source_id='A', source_sha256='digest-a', dataset_code='snapshot-a', source_locator='row1'),
                dict(site_code='S', observed_date='2020-03-15', ec_mS_m=30,
                     source_id='B', source_sha256='digest-b', dataset_code='snapshot-b', source_locator='row2')]
        records = spatial_inputs._observed_months(dict(observations=rows), 'S')
        self.assertIn('NOT_CONTINUOUS', records['2020-01']['temporal_coverage'])
        filled = spatial_inputs._observation_or_fill('2020-02', records)
        self.assertEqual(filled['value'], 20)
        self.assertEqual(filled['source_ids'], ['A', 'B'])
        self.assertEqual(filled['dataset_codes'], ['snapshot-a', 'snapshot-b'])
        self.assertTrue(filled['imputed'])
        self.assertFalse(filled['verified_observation'])


if __name__ == '__main__':
    unittest.main()
