import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from unittest.mock import MagicMock, patch

from backend.domain import multivariate_ec as models
from backend.repositories import workspace
from tools import model_training, weather_inputs


class ModelLoadingTests(unittest.TestCase):
    def test_cache_never_bypasses_checksums_and_registry_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / 'model.joblib'
            manifest = root / 'manifest.json'
            registry = root / 'registry.json'
            artifact.write_bytes(b'first model')
            manifest.write_text(json.dumps(dict(station='MYTHO', feature_order=models.FEATURES)))
            entry = dict(model_path=str(artifact), manifest_path=str(manifest),
                         model_sha256=models.sha256(artifact), manifest_sha256=models.sha256(manifest))
            registry.write_text(json.dumps(dict(models=dict(MYTHO=entry))))
            with patch.object(models, '_load_cached_artifact', return_value=('model', {})) as loader:
                models.load_model('MyTho', registry)
                with patch.object(models, 'sha256', wraps=models.sha256) as checksum:
                    models.load_model('MyTho', registry)
                    checksum.assert_not_called()
                artifact.write_bytes(b'corrupted model')
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    models.load_model('MyTho', registry)
                self.assertEqual(loader.call_count, 2)
                entry['model_sha256'] = models.sha256(artifact)
                registry.write_text(json.dumps(dict(models=dict(MYTHO=entry))))
                models.load_model('MyTho', registry)
                self.assertNotEqual(loader.call_args_list[0].args[1], loader.call_args_list[2].args[1])

    def test_tree_quantiles_use_transformed_pipeline_input(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest('numpy is optional in the API environment')
        class Tree:
            def __init__(self, offset):
                self.offset = offset
            def predict(self, values):
                return [float(values[0][0]) + self.offset]
        forest = MagicMock()
        forest.estimators_ = [Tree(i) for i in range(10)]
        pipeline = MagicMock()
        pipeline.steps = [('transform', object()), ('forest', forest)]
        pipeline.__getitem__.return_value.transform.return_value = np.array([[10.]])
        result = models.ensemble_distribution(pipeline, object())
        self.assertAlmostEqual(result['p10'], 10.9)
        self.assertAlmostEqual(result['p50'], 14.5)
        self.assertAlmostEqual(result['p90'], 18.1)
        self.assertAlmostEqual(result['iqr'], 4.5)
        self.assertAlmostEqual(result['std'], np.std(np.arange(10)))
        self.assertIn('not a calibrated', result['interpretation'])

    def test_warmup_is_best_effort_for_each_station(self):
        with patch.object(models, 'load_model', side_effect=ImportError('optional dependency')) as loader:
            self.assertEqual(models.warmup_models(), dict(MYTHO='ImportError', MYTHUAN='ImportError', TANCHAU='ImportError'))
            self.assertEqual(loader.call_count, 3)


class ReferenceStationTests(unittest.TestCase):
    def test_overview_latest_ec_skips_estimates_and_invalid_observations(self):
        rows = [dict(observed_or_estimated='O', quality_flag='VALIDATED',
                     observed_date='2026-01-01', ec_mS_m=80),
                dict(observed_or_estimated='E', quality_flag='VALIDATED',
                     observed_date='2026-02-01', ec_mS_m=500),
                dict(observed_or_estimated='O', quality_flag='INVALID',
                     observed_date='2026-03-01', ec_mS_m=900)]
        self.assertEqual(workspace._latest_display_observation(rows), rows[0])
        self.assertIsNone(workspace._latest_display_observation(rows[1:]))
        self.assertEqual(workspace._latest_display_observation([
            dict(observed_or_estimated='O', quality_flag='UNVERIFIED',
                 observed_date='2026-04-01', ec_mS_m=70)])['ec_mS_m'], 70)

    def test_postgres_restores_reference_fields_without_promoting_geometry(self):
        fallback = dict(site_code='RIA2_DT_01', source_coordinates=[105.3, 10.2],
                        admin_label_source='source label', coordinate_crs='EPSG:4326',
                        location_reference='snapshot reference')
        site = dict(site_code='RIA2_DT_01', source_code='RIA2', geometry=None,
                    location_status='UNVERIFIED', location_reference='DB reference')
        connection = MagicMock()
        results = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        results[0].fetchall.return_value = [site]
        results[1].fetchall.return_value = [dict(site_code='RIA2_DT_01', site_id=1)]
        results[2].fetchall.return_value = []
        results[3].fetchall.return_value = []
        connection.execute.side_effect = results
        with patch.object(workspace, 'read_connection') as read, patch.dict('os.environ', WEBGIS_WORKSPACE_DATASETS='{}'):
            read.return_value.__enter__.return_value = connection
            output = workspace._postgres_bundle(dict(stations=[fallback], sources=[], notes=[], observations=[]))
        station = output['stations'][0]
        self.assertIsNone(station['geometry'])
        self.assertEqual(station['location_status'], 'UNVERIFIED')
        self.assertEqual(station['source_coordinates'], fallback['source_coordinates'])
        self.assertEqual(station['coordinate_crs'], fallback['coordinate_crs'])
        self.assertEqual(station['admin_label_source'], fallback['admin_label_source'])
        self.assertEqual(station['location_reference'], 'DB reference')


class ToolCommandSafetyTests(unittest.TestCase):
    def test_model_training_needs_apply_before_writing(self):
        with patch.object(model_training, 'train') as train:
            model_training.main([])
            train.assert_not_called()
            model_training.main(['--apply'])
            train.assert_called_once_with()

    def test_weather_retry_only_for_transient_http_status(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'archive data'
        transient = HTTPError('https://example.test', 503, 'Unavailable', None, None)
        with patch.object(weather_inputs, 'urlopen', side_effect=[transient, response]) as opener, \
             patch.object(weather_inputs.time, 'sleep') as sleep:
            self.assertEqual(weather_inputs.fetch_archive('https://example.test', None), b'archive data')
            self.assertEqual(opener.call_count, 2)
            sleep.assert_called_once_with(3)

        permanent = HTTPError('https://example.test', 401, 'Unauthorized', None, None)
        with patch.object(weather_inputs, 'urlopen', side_effect=permanent) as opener, \
             patch.object(weather_inputs.time, 'sleep') as sleep:
            with self.assertRaises(HTTPError):
                weather_inputs.fetch_archive('https://example.test', None)
            opener.assert_called_once()
            sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
