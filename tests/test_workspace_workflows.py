"""Verify browsing and backtest evidence across the application's API boundary."""
import csv
import io
import math
import os
import unittest
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient

from backend.main import app
from backend.repositories import workspace as workspace_repository


class WorkspaceWorkflowTests(unittest.TestCase):
    def setUp(self):
        environment = dict(os.environ, WEBGIS_RESEARCH_MODE='snapshot')
        environment.pop('WEBGIS_RESEARCH_FILE', None)
        configured = patch.dict(os.environ, environment, clear=True)
        configured.start()
        self.addCleanup(configured.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def read(self, path, **params):
        response = self.client.get('/api/v1/workspace/' + path, params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_station_history_counts_and_sources_match_catalogue(self):
        summary = self.read('summary')
        stations = self.read('stations')['features']
        sources = {source['source_id'] for source in summary['sources']}
        total = 0
        for station in stations:
            properties = station['properties']
            code = properties['site_code']
            with self.subTest(station=code):
                history = self.read(f'stations/{code}/observations')
                self.assertEqual(history['total'], properties['observation_count'])
                self.assertEqual(history['unit'], 'mS/m')
                self.assertFalse(history['gate_decision_eligible'])
                for row in history['items']:
                    self.assertEqual(row['site_code'], code)
                    self.assertIn(row['source_id'], sources)
                total += history['total']
        self.assertEqual(total, summary['observations'])
        self.assertEqual(len(stations), summary['stations'])

    def test_date_filter_is_inclusive_and_empty_range_stays_empty(self):
        path = 'stations/MRC_VN_019805/observations'
        rows = self.read(path)['items']
        first, last = rows[5]['observed_date'], rows[8]['observed_date']
        filtered = self.read(path, date_from=first, date_to=last)
        expected = [row for row in rows if first <= row['observed_date'] <= last]
        self.assertEqual(filtered['items'], expected)
        self.assertEqual(filtered['total'], len(expected))
        empty = self.read(path, date_from='2100-01-01', date_to='2100-02-01')
        self.assertEqual(empty['items'], [])
        self.assertEqual(empty['total'], 0)
        reversed_range = self.client.get(
            '/api/v1/workspace/' + path,
            params={'date_from': last, 'date_to': first},
        )
        self.assertEqual(reversed_range.status_code, 422)

    def test_experiment_metrics_match_common_cohort_predictions_and_download(self):
        experiments = self.read('summary')['experiments']
        self.assertTrue(experiments)
        for summary in experiments:
            experiment_id = summary['experiment_id']
            with self.subTest(experiment=experiment_id):
                experiment = self.read(f'experiments/{experiment_id}')
                metrics = experiment['metrics']
                self.assertIn(experiment['selected_model'], {row['model'] for row in metrics})
                self.assertIn('Persistence', {row['model'] for row in metrics})
                self.assertEqual(experiment['selected_on'], 'validation')
                self.assertFalse(experiment['deployment_ready'])
                download = self.client.get(
                    f'/api/v1/workspace/artifacts/{experiment_id}/metrics.csv'
                )
                self.assertEqual(download.status_code, 200)
                downloaded_metrics = list(csv.DictReader(io.StringIO(download.text)))
                for metric in metrics:
                    predictions = [
                        row for row in experiment['predictions']
                        if row['model'] == metric['model']
                        and row['status'] == 'SUCCESS'
                        and row['in_common_cohort']
                        and row['label_available_for_evaluation']
                    ]
                    self.assertEqual(len(predictions), metric['eval_samples'])
                    errors = [row['predicted'] - row['actual'] for row in predictions]
                    self.assertAlmostEqual(
                        sum(abs(error) for error in errors) / len(errors),
                        metric['mae_mS_m'], places=8,
                    )
                    self.assertAlmostEqual(
                        math.sqrt(sum(error ** 2 for error in errors) / len(errors)),
                        metric['rmse_mS_m'], places=8,
                    )
                    exported = next(
                        row for row in downloaded_metrics
                        if row['model'] == metric['model'] and row['cohort'] == 'common'
                    )
                    self.assertAlmostEqual(float(exported['mae_mS_m']), metric['mae_mS_m'])

    def test_artifact_download_rejects_files_outside_allowlist(self):
        experiment = self.read('summary')['experiments'][0]['experiment_id']
        response = self.client.get(
            f'/api/v1/workspace/artifacts/{experiment}/model_bundle.joblib'
        )
        self.assertEqual(response.status_code, 404)

    def test_postgres_failure_does_not_switch_to_file_snapshot(self):
        with patch.dict(os.environ, WEBGIS_RESEARCH_MODE='postgres'):
            with patch.object(workspace_repository, 'read_connection',
                              side_effect=psycopg.OperationalError()) as database_reader:
                with patch.object(workspace_repository, '_file_bundle',
                                  wraps=workspace_repository._file_bundle) as file_reader:
                    response = self.client.get('/api/v1/workspace/summary')
        self.assertEqual(response.status_code, 503)
        database_reader.assert_called_once_with()
        # PostgreSQL mode loads model artifacts first; a failed RAW_EC read must
        # never retry the snapshot or return its observations as a fallback.
        file_reader.assert_called_once()
        self.assertIn('Workspace postgres unavailable', response.json()['detail'])
        self.assertIn('No fallback was used.', response.json()['detail'])


if __name__ == '__main__':
    unittest.main()
