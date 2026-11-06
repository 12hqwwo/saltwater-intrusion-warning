"""Append hash-checked My Thuan EC to public RAW_EC; existing observations stay intact."""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import psycopg
from psycopg.rows import dict_row
from scripts.integrate_mythuan import mythuan_records, SOURCE_FILE, sha
from scripts.sync_ria2_to_postgres import ensure_row
from run_webgis import load_local_env


def synchronize(apply=False):
    load_local_env()
    station, rows, source = mythuan_records()
    changes = {}
    with psycopg.connect(host=os.getenv('PGHOST','127.0.0.1'), port=os.getenv('PGPORT','5432'),
        dbname=os.getenv('PGDATABASE','dongthap_gis'), user=os.getenv('PGUSER','postgres'),
        connect_timeout=5, row_factory=dict_row, options='-c timezone=Asia/Ho_Chi_Minh -c lock_timeout=5000') as conn:
        conn.read_only = not apply
        if apply:
            conn.execute('SELECT pg_advisory_xact_lock(724031651)')
        fingerprint = """SELECT count(*) AS n, md5(coalesce(string_agg(row_to_json(o)::text,'' ORDER BY ec_observation_id),'')) AS hash
            FROM public.conductivity_observation o JOIN public.measurement_site s USING(site_id)
            WHERE s.site_code <> 'MRC_VN_019804'"""
        before = conn.execute(fingerprint).fetchone()
        sid = ensure_row(conn,'data_source',{'source_code':'MRC_MYTHUAN'},dict(source_name='MRC My Thuan Conductivity',
            source_type='OFFICIAL',is_demo=False,reference=source['url']),'source_id',apply,changes)
        metadata = dict(time_precision='DATE_ONLY', ec_temperature_basis='UNKNOWN',
            timestamp_storage_warning='Midnight+07 is a date placeholder; sampling hour is unknown.',
            quality_flag='UNVERIFIED', source_manifest='data/external/tien_multisite_20261029_verified/manifest.json',
            rows=rows, station=station)
        did = ensure_row(conn,'source_dataset',{'sha256':sha(SOURCE_FILE)},dict(dataset_code='MRC_MYTHUAN_EC_'+sha(SOURCE_FILE)[:16],
            source_id=sid,is_demo=False,dataset_kind='RAW_EC',data_product_kind='IN_SITU_OBSERVATION',
            source_filename=SOURCE_FILE.relative_to(ROOT).as_posix(),source_row_count=451,metadata=metadata),'dataset_id',apply,changes)
        site = conn.execute('SELECT site_id,source_id,ST_X(geom) AS lon,ST_Y(geom) AS lat FROM public.measurement_site WHERE site_code=%s',
                            (station['site_code'],)).fetchone()
        if site:
            if site['source_id'] != sid or site['lon'] != 105.9263229 or site['lat'] != 10.27532005:
                raise ValueError('Existing My Thuan identity differs; no overwrite performed')
            site_id = site['site_id']
        else:
            changes['measurement_site'] = 1
            site_id = None
            if apply:
                site_id = conn.execute("""INSERT INTO public.measurement_site
                    (site_code,source_id,is_demo,country_code,external_site_code,site_name,geom,location_status,location_reference)
                    VALUES(%s,%s,false,'VN','019804',%s,ST_SetSRID(ST_MakePoint(%s,%s),4326),'REPORTED',%s) RETURNING site_id""",
                    (station['site_code'],sid,station['site_name'],105.9263229,10.27532005,station['location_reference'])).fetchone()['site_id']
        for index, row in enumerate(rows,2):
            if did is None:
                changes['conductivity_observation'] = changes.get('conductivity_observation',0)+1
                continue
            ensure_row(conn,'conductivity_observation',{'dataset_id':did,'source_row':index},
                dict(dataset_kind='RAW_EC',source_id=sid,site_id=site_id,
                    observed_at=datetime.fromisoformat(row['source_observed_at']),conductivity_ms_per_m=row['ec_mS_m'],
                    unit='mS/m',source_label=row['source_locator']+'; DATE_ONLY; EC temperature basis UNKNOWN',
                    observed_or_estimated='O',approval_level='NOT_INDEPENDENTLY_VERIFIED',grade='UNVERIFIED',quality_flag='UNVERIFIED'),
                'ec_observation_id',apply,changes)
        if before != conn.execute(fingerprint).fetchone():
            raise ValueError('Non-MyThuan observations changed; transaction rolls back')
        return dict(mode='applied' if apply else 'dry_run',changes=changes,source_sha256=sha(SOURCE_FILE),other_observations_unchanged=before)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    print(json.dumps(synchronize(parser.parse_args().apply),indent=2))
