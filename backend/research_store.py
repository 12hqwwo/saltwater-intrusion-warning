"""Relational snapshot reader sharing the existing read-only PG connection."""
import os
from backend.database import read_connection


def read_snapshot():
    with read_connection() as conn:
        wanted = os.getenv('WEBGIS_RESEARCH_SNAPSHOT_ID')
        if wanted:
            item = conn.execute('SELECT snapshot_id,metadata FROM webgis_research.snapshot WHERE snapshot_id=%s', (wanted,)).fetchone()
        else:
            item = conn.execute('SELECT snapshot_id,metadata FROM webgis_research.snapshot ORDER BY imported_at DESC,snapshot_id LIMIT 1').fetchone()
        if not item:
            raise ValueError('No imported research snapshot.')
        snapshot_id, data = item['snapshot_id'], item['metadata']
        data['sources'] = [dict(r['metadata'], source_id=r['source_id']) for r in conn.execute('SELECT source_id,metadata FROM webgis_research.source WHERE snapshot_id=%s ORDER BY source_id', (snapshot_id,)).fetchall()]
        data['stations'] = [dict(r['metadata'], site_code=r['site_code'], site_name=r['site_name'], geometry=r['geometry']) for r in conn.execute('SELECT site_code,site_name,metadata,ST_AsGeoJSON(geom,15)::jsonb AS geometry FROM webgis_research.site WHERE snapshot_id=%s ORDER BY site_code', (snapshot_id,)).fetchall()]
        data['observations'] = []
        for r in conn.execute('SELECT * FROM webgis_research.ec_observation WHERE snapshot_id=%s ORDER BY site_code,observed_date', (snapshot_id,)).fetchall():
            data['observations'].append(dict(r['metadata'], site_code=r['site_code'], observed_date=r['observed_date'].isoformat(),
                observed_at=r['observed_at'].isoformat() if r['observed_at'] else None, time_precision=r['time_precision'],
                ec_mS_m=r['ec_ms_m'], quality_flag=r['quality_flag'], source_id=r['source_id']))
        data['gates'] = [dict(r['metadata'], gate_code=r['gate_code'], gate_name=r['gate_name'], source_id=r['source_id'], geometry=r['geometry']) for r in conn.execute('SELECT gate_code,gate_name,source_id,metadata,ST_AsGeoJSON(geom,15)::jsonb AS geometry FROM webgis_research.gate_catalog WHERE snapshot_id=%s ORDER BY gate_code', (snapshot_id,)).fetchall()]
        data['experiments'] = [dict(r['metadata'], experiment_id=r['experiment_id'], site_code=r['site_code']) for r in conn.execute('SELECT experiment_id,site_code,metadata FROM webgis_research.experiment WHERE snapshot_id=%s ORDER BY experiment_id', (snapshot_id,)).fetchall()]
    return data
