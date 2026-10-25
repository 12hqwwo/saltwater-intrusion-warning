"""Download immutable, unit-verified ERA5 inputs without modifying legacy CSVs."""
import argparse
import calendar
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import ssl
import time
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/external/multivariate_weather'
SITES = {'MyTho': (10.36, 106.36), 'TanChau': (10.804, 105.234)}


def verified_context():
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())


def month(value):
    parsed = datetime.strptime(value, '%Y-%m').date()
    if parsed.strftime('%Y-%m') != value:
        raise argparse.ArgumentTypeError('Expected YYYY-MM')
    return parsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--start-month', type=month)
    parser.add_argument('--end-month', type=month)
    args = parser.parse_args()
    today = date.today()
    last = date(today.year, today.month, 1) - timedelta(days=1)
    start = args.start_month or (date(1985, 1, 1) if args.history else last.replace(day=1))
    end_month = args.end_month or last.replace(day=1)
    end = end_month.replace(day=calendar.monthrange(end_month.year, end_month.month)[1])
    if start > end or end > last:
        parser.error('Use completed months, with start <= end.')
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / 'manifest.json'
    manifest = json.loads(manifest_path.read_text('utf-8')) if manifest_path.exists() else {'schema_version': 1, 'retrievals': []}
    context = verified_context()
    for station, (lat, lon) in SITES.items():
        chunk_start = start
        while chunk_start <= end:
            chunk_end = min(date(chunk_start.year + 4, 12, 31), end)
            filename = f'era5_{station}_{chunk_start}_{chunk_end}.json'
            existing = next((r for r in manifest['retrievals'] if r['file'] == filename), None)
            path = OUT / filename
            if existing and path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == existing['sha256']:
                print(f'Cached {filename}', flush=True)
            else:
                params = dict(latitude=lat, longitude=lon, start_date=str(chunk_start), end_date=str(chunk_end),
                              daily='precipitation_sum,temperature_2m_mean,wind_speed_10m_mean',
                              models='era5', timezone='Asia/Ho_Chi_Minh', wind_speed_unit='ms',
                              temperature_unit='celsius', precipitation_unit='mm')
                url = 'https://archive-api.open-meteo.com/v1/archive?' + urlencode(params)
                for attempt in range(4):
                    try:
                        with urlopen(url, context=context, timeout=90) as response:
                            raw = response.read()
                        payload = json.loads(raw)
                        if payload.get('error'):
                            raise ValueError(payload.get('reason'))
                        units = payload['daily_units']
                        if units['wind_speed_10m_mean'] != 'm/s' or units['precipitation_sum'] != 'mm' or units['temperature_2m_mean'] not in ('\u00b0C', 'celsius'):
                            raise ValueError(f'Unexpected units: {units}')
                        expected = (chunk_end - chunk_start).days + 1
                        daily = payload['daily']
                        if len(daily['time']) != expected or daily['time'][0] != str(chunk_start) or daily['time'][-1] != str(chunk_end):
                            raise ValueError('Incomplete date range from archive')
                        for key in ('precipitation_sum', 'temperature_2m_mean', 'wind_speed_10m_mean'):
                            if len(daily[key]) != expected or any(v is None for v in daily[key]):
                                raise ValueError(f'Incomplete daily values: {key}')
                        break
                    except Exception:
                        if attempt == 3:
                            raise
                        time.sleep(3 * (attempt + 1))
                path.write_bytes(raw)
                record = dict(station=station, file=filename, sha256=hashlib.sha256(raw).hexdigest(),
                              retrieved_at=datetime.now(timezone.utc).isoformat(), url=url,
                              request_parameters=params, daily_units=units, start_date=str(chunk_start), end_date=str(chunk_end),
                              source='Open-Meteo archive / ERA5', wind_statistic='monthly mean of daily mean 10m wind speed',
                              license='CC-BY-4.0', citation='ERA5 / Copernicus Climate Change Service via Open-Meteo')
                manifest['retrievals'] = [r for r in manifest['retrievals'] if r['file'] != filename] + [record]
                manifest['updated_at'] = datetime.now(timezone.utc).isoformat()
                temporary = manifest_path.with_suffix('.tmp')
                temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding='utf-8')
                temporary.replace(manifest_path)
                print(f'Downloaded {filename}: {expected} days', flush=True)
            chunk_start = chunk_end + timedelta(days=1)


if __name__ == '__main__':
    main()
