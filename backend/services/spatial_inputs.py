"""Read-only monthly evidence adapted for the isolated spatial simulation."""
import calendar
from collections import Counter, defaultdict
from datetime import datetime
from functools import lru_cache
import hashlib
import json
import math
from statistics import mean, median
from zoneinfo import ZoneInfo

from backend.repositories.workspace import ROOT, load_bundle, estimate_rows
from backend.repositories.multivariate_inputs import get_monthly_weather
from backend.services.workspace import WorkspaceError
from backend.domain.river_interpolation import THREE_STATION_MODE, TWO_STATION_MODE

STATIONS = {'TanChau': 'MRC_VN_019803', 'MyThuan': 'MRC_VN_019804', 'MyTho': 'MRC_VN_019805'}
SALINITY_FACTOR = 0.0064


def _number(value, nonnegative=False):
    if isinstance(value, bool):
        raise ValueError('Boolean is not a simulation measurement.')
    result = float(value)
    if not math.isfinite(result) or (nonnegative and result < 0):
        raise ValueError('Non-finite or negative simulation measurement.')
    return result


def _index(month):
    year, mon = map(int, month.split('-'))
    if not 1 <= mon <= 12 or len(month) != 7:
        raise ValueError('Invalid simulation month.')
    return year * 12 + mon - 1


def _months(start, end):
    return [f'{i // 12:04d}-{i % 12 + 1:02d}' for i in range(_index(start), _index(end) + 1)]


@lru_cache(maxsize=4)
def _wind_file(path, mtime_ns, size):
    """Cache file parsing only; database observations are never cached here."""
    raw = path.read_bytes()
    payload = json.loads(raw)
    daily, units = payload['daily'], payload['daily_units']
    if units.get('wind_speed_10m_mean') != 'm/s':
        raise ValueError('Wind source must declare m/s.')
    if units.get('wind_direction_10m_dominant') not in ('\u00b0', 'degree', 'degrees'):
        raise ValueError('Wind direction must declare degrees.')
    keys = ('time', 'wind_speed_10m_mean', 'wind_direction_10m_dominant')
    if len({len(daily[key]) for key in keys}) != 1:
        raise ValueError('Unequal wind evidence arrays.')
    groups = defaultdict(list)
    for day, speed, direction in zip(*(daily[key] for key in keys)):
        if speed is None or direction is None:
            continue
        speed, direction = _number(speed, True), _number(direction)
        if not 0 <= direction <= 360:
            raise ValueError('Invalid meteorological wind direction.')
        radians = math.radians(direction)
        groups[day[:7]].append((day, -speed * math.sin(radians), -speed * math.cos(radians)))
    result = {}
    for month, rows in groups.items():
        year, mon = map(int, month.split('-'))
        expected = calendar.monthrange(year, mon)[1]
        if {r[0] for r in rows} != {f'{month}-{day:02d}' for day in range(1, expected + 1)} or len(rows) != expected:
            continue
        u, v = mean(row[1] for row in rows), mean(row[2] for row in rows)
        result[month] = dict(available=True, u10=u, v10=v, unit='m/s',
            resultant_speed_ms=math.hypot(u, v),
            direction_degrees=(math.degrees(math.atan2(-u, -v)) % 360),
            direction_from_degrees=(math.degrees(math.atan2(-u, -v)) % 360),
            source=str(path.relative_to(ROOT)).replace('\\', '/'),
            sha256=hashlib.sha256(raw).hexdigest(), source_month=month,
            source_dates=[rows[0][0], rows[-1][0]], daily_count=len(rows),
            method='MEAN_DAILY_SPEED_DOMINANT_DIRECTION_COMPONENTS',
            native_era5_components=False, imputed=False,
            note='Components derived from recorded daily mean speed and dominant direction; not native hourly ERA5 u10/v10.')
    return result


def _winds(station):
    path = ROOT / f'data/external/ec_feature_research_20261019/era5_extra_{station}.json'
    if not path.exists():
        return {}
    stat = path.stat()
    return _wind_file(path, stat.st_mtime_ns, stat.st_size)


def _observed_months(bundle, site):
    groups = defaultdict(list)
    excluded_invalid = Counter()
    for row in bundle['observations']:
        if row['site_code'] == site and row['observed_date'][:7] <= '2023-12':
            if row.get('quality_flag') == 'INVALID':
                excluded_invalid[row['observed_date'][:7]] += 1
                continue
            _number(row['ec_mS_m'], True)
            groups[row['observed_date'][:7]].append(row)
    return {month: dict(value=mean(_number(r['ec_mS_m'], True) for r in rows),
        site_code=site, imputed=False, evidence_kind='SOURCE_SAMPLE_MONTHLY_AGGREGATE',
        observed_or_estimated_counts=dict(Counter(r.get('observed_or_estimated') or 'UNKNOWN' for r in rows)),
        excluded_invalid_sample_count=excluded_invalid[month],
        aggregation='arithmetic mean of available source samples', sample_count=len(rows),
        temporal_coverage='AVAILABLE_SOURCE_SAMPLES_ONLY_NOT_CONTINUOUS_MONTHLY_MEAN',
        source_locators=sorted({r['source_locator'] for r in rows if r.get('source_locator')}),
        source_sha256=sorted({r['source_sha256'] for r in rows if r.get('source_sha256')}),
        dataset_codes=sorted({r['dataset_code'] for r in rows if r.get('dataset_code')}),
        source_months=[month], source_dates=sorted({r['observed_date'] for r in rows}),
        source_ids=sorted({r['source_id'] for r in rows}),
        quality_flags=sorted({r.get('quality_flag', 'UNKNOWN') for r in rows}),
        verified_observation=False) for month, rows in groups.items()}


def _observation_or_fill(month, records):
    if month in records:
        return dict(records[month])
    if not records:
        raise ValueError('No MRC evidence available for simulation boundary.')
    before = max((m for m in records if m < month), default=None)
    after = min((m for m in records if m > month), default=None)
    sources = [m for m in (before, after) if m]
    if before and after:
        weight = (_index(month) - _index(before)) / (_index(after) - _index(before))
        value = records[before]['value'] * (1 - weight) + records[after]['value'] * weight
        method = 'LINEAR_MONTHLY_INTERPOLATION'
    else:
        value = records[sources[0]]['value']
        method = 'NEAREST_AVAILABLE_MONTH'
    return dict(value=value, site_code=records[sources[0]]['site_code'], imputed=True,
        evidence_kind='SIMULATION_ONLY_IMPUTATION', imputation_method=method,
        source_months=sources, source_dates=sorted({d for m in sources for d in records[m]['source_dates']}),
        verified_observation=False, sample_count=0,
        source_ids=sorted({v for m in sources for v in records[m].get('source_ids', [])}),
        source_sha256=sorted({v for m in sources for v in records[m].get('source_sha256', [])}),
        dataset_codes=sorted({v for m in sources for v in records[m].get('dataset_codes', [])}),
        quality_flags=sorted({v for m in sources for v in records[m].get('quality_flags', [])}),
        observed_or_estimated_counts=dict(sum((Counter(records[m].get('observed_or_estimated_counts', {})) for m in sources), Counter())))


@lru_cache(maxsize=48)
def _model_forecast(station, month, rainfall, temperature, wind, source_sha, hydro_sha=None):
    """Cache deterministic inference; the source hash invalidates refreshed weather."""
    from backend.domain.multivariate_ec import predict_month
    values = dict(rainfall_mm=rainfall, temperature_degC=temperature,
                  wind_source_units=wind)
    if station == 'MyTho':
        from backend.repositories.hydrology_inputs import FEATURES, get_hydrology_input
        hydro = get_hydrology_input(month)
        values.update({key: hydro[key] for key in FEATURES})
    result = predict_month(station, month + '-01', values)
    return dict(value=_number(result['predicted_ec_mS_m'], True),
                model='RandomForestRegressor', model_version=result['model_version'],
                model_sha256=result['model_provenance'].get('model_sha256'),
                weather_source_sha256=source_sha,
                hydrology_source_sha256=hydro_sha)


def _future_boundaries(month, station, observed, weather, today):
    """Use released t-2 weather where possible; otherwise an explicit seasonal scenario."""
    index = _index(month) - 2
    input_month = f'{index // 12:04d}-{index % 12 + 1:02d}'
    record = weather.get(station, {}).get(input_month)
    if (record and record.get('complete') and record.get('wind_unit') == 'm/s'
            and record.get('assumed_available_at', '9999-12-31')[:10] <= today):
        hydro = None
        if station == 'MyTho':
            from backend.repositories.hydrology_inputs import get_hydrology_input
            try:
                hydro = get_hydrology_input(month)
            except (OSError, ValueError, KeyError, TypeError):
                hydro = None
        if station != 'MyTho' or hydro is not None:
            hydro_sha = '|'.join(hydro['source_files'].values()) if hydro else None
            prediction = _model_forecast(station, month,
                record['rainfall_mm'], record['temperature_degC'],
                record['wind_source_units'], record['sha256'], hydro_sha)
            return dict(prediction, site_code=STATIONS[station], imputed=False,
                input_month=input_month, source=record['source'], sha256=record['sha256'],
                source_months=[input_month], evidence_kind='ML_FORECAST_ERA5_HYDROLOGY' if hydro else 'ML_FORECAST_ERA5',
                hydrology_source_files=hydro['source_files'] if hydro else None,
                verified_observation=False, data_kind='MULTIVARIATE_MONTHLY_FORECAST',
                live_forecast_available=False, rainfall_mm=record['rainfall_mm'],
                temperature_degC=record['temperature_degC'],
                wind_speed_ms=record['wind_source_units'])
    season = month[5:]
    ec_history = [row['value'] for key, row in observed[station].items()
                  if '2010-01' <= key <= '2023-12' and key[5:] == season]
    weather_history = [row for key, row in weather.get(station, {}).items()
                       if '2010-01' <= key <= '2023-12' and key[5:] == season]
    if len(ec_history) < 10 or len(weather_history) < 10:
        raise ValueError(f'Insufficient seasonal scenario evidence: {station} {month}')
    return dict(value=median(ec_history), site_code=STATIONS[station],
        model='SEASONAL_MONTH_MEDIAN', imputed=True, input_month=input_month,
        source='MRC historical EC and ERA5 2010–2023',
        source_months=[key for key in observed[station] if '2010-01' <= key <= '2023-12' and key[5:] == season],
        evidence_kind='SEASONAL_MEDIAN_SCENARIO', verified_observation=False,
        data_kind='SEASONAL_SCENARIO', live_forecast_available=False,
        rainfall_mm=median(row['rainfall_mm'] for row in weather_history),
        temperature_degC=median(row['temperature_degC'] for row in weather_history),
        wind_speed_ms=median(row['wind_source_units'] for row in weather_history))


def _monthly_inputs():
    """Return 1985-06 onward; imputation never modifies Tier 1 source records."""
    bundle = load_bundle()
    observed = {station: _observed_months(bundle, site) for station, site in STATIONS.items()}
    invalid_samples = Counter((row['site_code'], row['observed_date'][:7])
        for row in bundle['observations'] if row.get('quality_flag') == 'INVALID')
    forecasts = {}
    forecast_sha = hashlib.sha256((ROOT / 'data/models/future_ec_forecast_2024_2026.csv').read_bytes()).hexdigest()
    for row in estimate_rows():
        month, station = row['year_month'], row['station']
        _index(month)
        if station not in STATIONS or month < '2024-01':
            continue
        if (station, month) in forecasts:
            raise ValueError('Duplicate simulation forecast station/month.')
        forecasts[station, month] = dict(value=_number(row['predicted_ec_mS_m'], True),
            site_code=STATIONS[station], model=row['model'], imputed=False,
            input_month=row.get('input_month') or month,
            model_version=row.get('model_version') or None,
            model_sha256=row.get('model_sha256') or None,
            source='data/models/future_ec_forecast_2024_2026.csv', sha256=forecast_sha, source_months=[month],
            evidence_kind='ML_FORECAST_ERA5', verified_observation=False,
            data_kind='RETROSPECTIVE_WEATHER_ESTIMATE', live_forecast_available=False,
            rainfall_mm=_number(row['rainfall_mm'], True),
            temperature_degC=_number(row['temperature_degC']),
            wind_speed_ms=_number(row['wind_m_s'], True))
    now = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))
    future_index = now.year * 12 + now.month - 1 + 12
    rolling_end = f'{future_index // 12:04d}-{future_index % 12 + 1:02d}'
    end = max(['2026-08', rolling_end] + [month for _, month in forecasts])
    weather = {station: {r['input_month']: r for r in get_monthly_weather(station)} for station in STATIONS}
    # The fixed archive remains historical evidence, while the live Timeline
    # uses the currently registered My Tho model wherever its inputs exist.
    for station, month in list(forecasts):
        if station == 'MyTho':
            forecasts[station, month] = _future_boundaries(
                month, station, observed, weather, now.date().isoformat())
    last_estimate = max(month for _, month in forecasts)
    for month in _months('2024-01', end):
        if month <= last_estimate:
            continue
        for station in STATIONS:
            forecasts[station, month] = _future_boundaries(month, station, observed, weather, now.date().isoformat())
    winds = {station: _winds(station) for station in STATIONS}
    result = {}
    for month in _months('1985-06', end):
        boundaries, station_weather = {}, {}
        for station in STATIONS:
            if month < '2024-01':
                if station == 'MyThuan' and month not in observed[station]:
                    boundaries[station] = dict(value=None, site_code=STATIONS[station], imputed=False,
                        evidence_kind='MISSING_HISTORICAL_SAMPLE', source_months=[], source_dates=[],
                        sample_count=0, verified_observation=False, quality_flags=[])
                else:
                    boundaries[station] = _observation_or_fill(month, observed[station])
                boundaries[station]['excluded_invalid_sample_count'] = invalid_samples[STATIONS[station], month]
            else:
                if (station, month) not in forecasts:
                    raise ValueError(f'Missing forecast boundary: {station} {month}')
                boundaries[station] = dict(forecasts[station, month])
            if month >= '2024-01':
                record = forecasts[station, month]
                station_weather[station] = dict(rainfall_mm=record['rainfall_mm'],
                    temperature_degC=record['temperature_degC'], wind_speed_ms=record['wind_speed_ms'],
                    source=record['source'], sha256=record.get('sha256'), source_month=record['input_month'], source_model=record['model'],
                    data_kind=record['data_kind'],
                    wind_unit='m/s', wind_unit_status='SEASONAL_MEDIAN_SCENARIO' if record['data_kind'] == 'SEASONAL_SCENARIO' else 'VERIFIED_RESPONSE_UNITS', imputed=record['imputed'])
            else:
                if month not in weather[station]:
                    raise ValueError(f'Missing verified-unit ERA5 weather: {station} {month}')
                record = weather[station][month]
                station_weather[station] = dict(rainfall_mm=_number(record['rainfall_mm'], True),
                    temperature_degC=_number(record['temperature_degC']),
                    wind_speed_ms=_number(record['wind_source_units'], True),
                    source=record['source'], sha256=record['sha256'], source_month=month,
                    source_model=record['source_model'], wind_unit=record['wind_unit'],
                    wind_unit_status=record['wind_unit_status'], imputed=False)
            wind = dict(winds[station].get(month, dict(available=False, u10=None, v10=None,
                resultant_speed_ms=None, direction_degrees=None, direction_from_degrees=None,
                method='UNAVAILABLE', note='No complete recorded wind direction for this month.', imputed=False)))
            wind['speed_ms'] = station_weather[station]['wind_speed_ms']
            wind['speed_source'] = station_weather[station]['source']
            wind['unit'] = 'm/s'
            station_weather[station]['wind'] = wind
        regional = station_weather['MyTho']
        tan_chau, my_tho = boundaries['TanChau']['value'], boundaries['MyTho']['value']
        my_thuan = boundaries['MyThuan']['value']
        result[month] = dict(year_month=month, tan_chau_ec_mS_m=tan_chau, my_tho_ec_mS_m=my_tho,
            my_thuan_ec_mS_m=my_thuan,
            interpolation_mode=THREE_STATION_MODE if my_thuan is not None else TWO_STATION_MODE,
            interpolation_fallback_reason=None if my_thuan is not None else 'MISSING_HISTORICAL_MYTHUAN_OBSERVATION',
            tan_chau_salinity_g_l=round(tan_chau * SALINITY_FACTOR, 3),
            my_tho_salinity_g_l=round(my_tho * SALINITY_FACTOR, 3),
            data_regime='OBSERVED_MRC' if month < '2024-01' else ('SEASONAL_SCENARIO' if any(r['data_kind'] == 'SEASONAL_SCENARIO' for r in boundaries.values()) else 'ML_FORECAST_ERA5'),
            imputed=any(r['imputed'] for r in boundaries.values()),
            rainfall_mm=regional['rainfall_mm'], temperature_degC=regional['temperature_degC'],
            wind_speed_ms=regional['wind_speed_ms'], wind=dict(regional['wind']),
            weather_representative_station='MyTho', weather_by_station=station_weather,
            boundary_provenance=boundaries, storage_mode=bundle.get('storage_mode'),
            observation_source=bundle.get('observation_source'), salinity_conversion_factor=SALINITY_FACTOR,
            simulation_only=True, gate_decision_eligible=False,
            live_forecast_available=False, deployment_ready=False,
            data_kind='MRC_HISTORICAL_SIMULATION_INPUT' if month < '2024-01' else ('SEASONAL_SCENARIO' if any(r['data_kind'] == 'SEASONAL_SCENARIO' for r in boundaries.values()) else 'MULTIVARIATE_MONTHLY_FORECAST' if month > last_estimate else 'RETROSPECTIVE_WEATHER_ESTIMATE'))
    return result


def monthly_inputs():
    """Expose source/schema failures as unavailable input, never an API 500."""
    try:
        return _monthly_inputs()
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError) as exc:
        raise WorkspaceError(503, 'Spatial simulation monthly evidence is unavailable or invalid.') from exc
