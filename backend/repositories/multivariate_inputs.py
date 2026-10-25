"""Auditable monthly weather inputs; complete months only, with two-month lag."""
import calendar
import csv
from datetime import date, timedelta
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / 'data/raw/meteorology/openmeteo/openmeteo_all_stations_daily.csv'
EXTERNAL = ROOT / 'data/external/multivariate_weather'
ALIASES = {'MYTHO': 'MyTho', 'TANCHAU': 'TanChau', 'MRC_VN_019805': 'MyTho',
           'MRC_VN_019803': 'TanChau', '019805': 'MyTho', '019803': 'TanChau'}


class WeatherInputUnavailable(ValueError):
    """The requested input has absent, incomplete or invalid daily evidence."""


def normalize_station(station):
    key = str(station).upper().replace(' ', '')
    if key not in ALIASES:
        raise WeatherInputUnavailable(f'Unsupported weather station: {station}')
    return ALIASES[key]


def _month(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}', value):
        raise ValueError('Month must use YYYY-MM')
    return date.fromisoformat(value + '-01')


def _aggregate(station, month, rows, provenance):
    first = _month(month)
    last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    expected = {(first + timedelta(days=i)).isoformat() for i in range(last.day)}
    if len(rows) != last.day or {r[0] for r in rows} != expected:
        raise WeatherInputUnavailable(f'Incomplete or duplicate weather days: {station} {month}')
    try:
        values = [[float(v) for v in r[1:]] for r in rows]
    except (ValueError, TypeError) as exc:
        raise WeatherInputUnavailable(f'Missing weather values: {station} {month}') from exc
    if any(not all(math.isfinite(v) for v in row) or row[0] < 0 or row[2] < 0 for row in values):
        raise WeatherInputUnavailable(f'Invalid weather values: {station} {month}')
    return dict(station=station, input_month=month,
                rainfall_mm=sum(v[0] for v in values),
                temperature_degC=sum(v[1] for v in values) / last.day,
                wind_source_units=sum(v[2] for v in values) / last.day,
                observed_through=last.isoformat(), assumed_available_at=(last + timedelta(days=5)).isoformat(),
                daily_count=last.day, complete=True,
                availability_note='Month end + 5 days is an assumed ERA5 release lag, not a historical publication timestamp.',
                **provenance)


def _signature():
    files = [CANONICAL, EXTERNAL / 'manifest.json']
    if EXTERNAL.exists():
        files.extend(sorted(EXTERNAL.glob('era5_*.json')))
    return tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files if p.exists())


@lru_cache(maxsize=2)
def _load(signature):
    grouped = {}
    if CANONICAL.exists():
        raw = CANONICAL.read_bytes()
        provenance = dict(source=str(CANONICAL.relative_to(ROOT)).replace('\\', '/'),
                          sha256=hashlib.sha256(raw).hexdigest(), wind_unit='unknown source units',
                          wind_unit_status='UNCONFIRMED', wind_statistic='monthly mean of daily maximum 10m wind speed',
                          source_model='legacy model not retained', retrieved_at=None)
        for row in csv.DictReader(raw.decode('utf-8-sig').splitlines()):
            station = normalize_station(row['station'])
            key = (station, row['date'][:7])
            group = grouped.setdefault(key, {'rows': [], 'provenance': provenance})
            group['rows'].append((row['date'], row['precipitation_sum'], row['temperature_2m_mean'], row['windspeed_10m_max']))
    manifest_path = EXTERNAL / 'manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text('utf-8'))
        # Latest retrieved whole-month version wins deterministically; never splice days.
        for record in sorted(manifest['retrievals'], key=lambda r: (r['retrieved_at'], r['file'])):
            filename = record['file']
            if Path(filename).name != filename:
                raise WeatherInputUnavailable('Invalid weather manifest path')
            raw = (EXTERNAL / filename).read_bytes()
            if hashlib.sha256(raw).hexdigest() != record['sha256']:
                raise WeatherInputUnavailable(f'Weather source hash mismatch: {filename}')
            payload = json.loads(raw)
            units = payload['daily_units']
            if units.get('wind_speed_10m_mean') != 'm/s' or units.get('precipitation_sum') != 'mm' or units.get('temperature_2m_mean') not in ('\u00b0C', 'celsius'):
                raise WeatherInputUnavailable(f'Unexpected weather units: {filename}')
            params = record['request_parameters']
            if params.get('models') != 'era5' or params.get('timezone') != 'Asia/Ho_Chi_Minh':
                raise WeatherInputUnavailable(f'Unexpected weather model/timezone: {filename}')
            daily = payload['daily']; station = normalize_station(record['station'])
            keys = ['time', 'precipitation_sum', 'temperature_2m_mean', 'wind_speed_10m_mean']
            if len({len(daily[k]) for k in keys}) != 1:
                raise WeatherInputUnavailable(f'Unequal daily arrays: {filename}')
            new_groups = {}
            for row in zip(*(daily[k] for k in keys)):
                new_groups.setdefault((station, row[0][:7]), []).append(row)
            provenance = dict(source=f'data/external/multivariate_weather/{filename}', sha256=record['sha256'],
                              wind_unit='m/s', wind_unit_status='VERIFIED_RESPONSE_UNITS',
                              wind_statistic='monthly mean of daily mean 10m wind speed', source_model='ERA5',
                              retrieved_at=record['retrieved_at'], source_url=record['url'])
            for key, rows in new_groups.items():
                grouped[key] = {'rows': rows, 'provenance': provenance}
    result = {}; invalid = {}
    for key, group in grouped.items():
        try:
            result[key] = _aggregate(*key, group['rows'], group['provenance'])
        except WeatherInputUnavailable as exc:
            invalid[key] = str(exc)
    return result, invalid


def get_monthly_weather(station, require_verified_wind=True):
    """Complete months in chronological order; verified ERA5 wind by default."""
    station = normalize_station(station)
    records, _ = _load(_signature())
    return [dict(record) for (site, month), record in sorted(records.items())
            if site == station and (not require_verified_wind or record['wind_unit_status'] == 'VERIFIED_RESPONSE_UNITS')]


def get_weather_input(station, target_month):
    """Return target-2 input; legacy provenance remains explicit when not refreshed."""
    target = _month(target_month)
    index = target.year * 12 + target.month - 1 - 2
    input_month = f'{index // 12:04d}-{index % 12 + 1:02d}'
    station = normalize_station(station)
    records, invalid = _load(_signature())
    key = (station, input_month)
    if key not in records:
        raise WeatherInputUnavailable(invalid.get(key, f'No complete weather input for {station}, month {input_month} (target {target_month})'))
    return dict(records[key], target_month=target_month)
