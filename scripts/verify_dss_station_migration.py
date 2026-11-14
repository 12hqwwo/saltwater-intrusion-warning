"""Exercise three prediction station contracts in PostgreSQL and roll back test rows."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def main():
    load_local_env()
    import psycopg
    from psycopg.types.json import Jsonb
    from backend.services import multivariate
    from backend.repositories.dss_storage import write_connection

    predictions = [multivariate.predict(dict(station=station, target_month='2026-10',
                    input_mode='ARCHIVE')) for station in ('MyTho', 'MyThuan', 'TanChau')]
    with write_connection() as conn:
        try:
            for prediction in predictions:
                row = conn.execute('''INSERT INTO dss_reference.multivariate_prediction_log
                    (prediction_id,station_key,site_code,target_month,input_month,input_mode,model_version,payload)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING prediction_id,station_key,site_code''',
                    (prediction['prediction_id'], prediction['station'], prediction['site_code'],
                     prediction['target_month'] + '-01', prediction['input_month'] + '-01',
                     prediction['input_mode'], prediction['model_version'], Jsonb(prediction))).fetchone()
                assert row['station_key'] == prediction['station']
                assert row['site_code'] == prediction['site_code']
                fetched = conn.execute('''SELECT station_key FROM dss_reference.multivariate_prediction_log
                    WHERE prediction_id=%s''', (prediction['prediction_id'],)).fetchone()
                assert fetched['station_key'] == prediction['station']
                print('validated', prediction['station'])
        finally:
            conn.rollback()
    print('All verification inserts rolled back.')

    bad = dict(predictions[1], site_code='MRC_VN_019803')
    with write_connection() as conn:
        try:
            try:
                conn.execute('''INSERT INTO dss_reference.multivariate_prediction_log
                    (prediction_id,station_key,site_code,target_month,input_month,input_mode,model_version,payload)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (bad['prediction_id'], bad['station'], bad['site_code'],
                     bad['target_month'] + '-01', bad['input_month'] + '-01',
                     bad['input_mode'], bad['model_version'], Jsonb(bad)))
            except psycopg.errors.CheckViolation:
                print('validated wrong station/site rejection')
            else:
                raise AssertionError('Wrong station/site pair was accepted.')
        finally:
            conn.rollback()


if __name__ == '__main__':
    main()
