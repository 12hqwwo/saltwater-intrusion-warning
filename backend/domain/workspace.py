"""Validated observation and experiment snapshot contract."""
from datetime import date
import math

def validate_bundle(data):
    if (
        data.get('schema_version') != 1
        or data.get('unit') != 'mS/m'
        or data.get('live_forecast_available') is not False
    ):
        raise ValueError('Invalid research contract.')
    sites = {s['site_code'] for s in data['stations']}
    sources = {s['source_id'] for s in data['sources']}
    if len(sites) != len(data['stations']):
        raise ValueError('Duplicate station code.')
    keys = set()
    for r in data['observations']:
        key = (r['site_code'], r['observed_date'])
        value = r['ec_mS_m']
        date.fromisoformat(r['observed_date'])
        if (
            key in keys
            or r['site_code'] not in sites
            or r['source_id'] not in sources
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
            or r['unit'] != 'mS/m'
            or r['gate_decision_eligible'] is not False
        ):
            raise ValueError('Invalid EC record.')
        if r['time_precision'] == 'DATE_ONLY' and r['observed_at'] is not None:
            raise ValueError('Date-only observation cannot claim a sampling hour.')
        keys.add(key)
    for s in data['stations']:
        g = s['geometry']
        if g:
            lon, lat = g['coordinates']
            if g['type'] != 'Point' or not -180 <= lon <= 180 or not -90 <= lat <= 90:
                raise ValueError('Invalid station geometry.')
    for ex in data['experiments']:
        if (
            ex['deployment_ready'] is not False
            or ex['selected_on'] != 'validation'
            or ex['site_code'] not in sites
        ):
            raise ValueError('Invalid experiment qualification.')
    return data
