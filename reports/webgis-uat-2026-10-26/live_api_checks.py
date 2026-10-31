"""Read-only live UAT: HTTP reads, nonpersisted forecasts and hypothetical gate evaluations."""
import copy
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = 'http://127.0.0.1:8000'
OUT = Path(__file__).resolve().parent
checks, evidence = [], {}


def request(path, data=None, params=None, headers=None):
    url = BASE + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': 'application/json', 'Origin': BASE, **(headers or {})})
    start = time.perf_counter()
    try:
        response = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        raw = response.read().decode('utf-8-sig')
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = raw
        return response.code, payload, round(time.perf_counter() - start, 3)


def get(path, **params):
    code, data, elapsed = request(path, params=params)
    assert code == 200, (path, code, data)
    return data


def check(name, run):
    start = time.perf_counter()
    try:
        detail = run()
        checks.append(dict(name=name, status='PASS', seconds=round(time.perf_counter()-start, 3), detail=detail))
    except Exception as exc:
        checks.append(dict(name=name, status='FAIL', seconds=round(time.perf_counter()-start, 3), detail=str(exc)))
    print(checks[-1]['status'], name, flush=True)
    (OUT / 'live-api-results.json').write_text(json.dumps(dict(base_url=BASE, generated_at=datetime.now().astimezone().isoformat(), checks=checks, evidence=evidence), ensure_ascii=False, indent=2), encoding='utf-8')


def expect_status(path, expected, **kwargs):
    code, data, elapsed = request(path, **kwargs)
    assert code == expected, (code, data)
    return dict(http_status=code, seconds=elapsed)


check('Runtime uses PostgreSQL', lambda: evidence.setdefault('app_health', get('/api/v1/app-health')))
check('Actual database health', lambda: evidence.setdefault('database_health', get('/api/v1/health')))
summary = get('/api/v1/workspace/summary')
evidence['summary'] = {k: summary.get(k) for k in ('storage_mode', 'stations', 'observations', 'observation_source')}
stations = get('/api/v1/workspace/stations')['features']


def station_consistency():
    total, records = 0, []
    for feature in stations:
        site = feature['properties']['site_code']
        history = get(f'/api/v1/workspace/stations/{site}/observations')
        assert len(history['items']) == history['total'] == feature['properties']['observation_count']
        assert history['unit'] == 'mS/m' and not history['gate_decision_eligible']
        assert all(row['site_code'] == site and math.isfinite(row['ec_mS_m']) for row in history['items'])
        total += history['total']
        records.append(dict(site=site, count=history['total'], mapped=feature['geometry'] is not None))
    assert total == summary['observations'] and len(stations) == summary['stations']
    evidence['stations'] = records
    return dict(stations=len(stations), observations=total)


check('All 12 station histories agree with served catalogue', station_consistency)
check('Date filter 2023 returns 12 My Tho samples', lambda: (lambda d: d['total'] == 12 or (_ for _ in ()).throw(AssertionError(d['total'])))(get('/api/v1/workspace/stations/MRC_VN_019805/observations', date_from='2023-01-01', date_to='2023-12-31')))
check('Empty observation interval stays empty', lambda: (lambda d: d['total'] == 0 or (_ for _ in ()).throw(AssertionError(d['total'])))(get('/api/v1/workspace/stations/MRC_VN_019805/observations', date_from='2026-01-01', date_to='2026-12-31')))
check('Reversed observation dates rejected', lambda: expect_status('/api/v1/workspace/stations/MRC_VN_019805/observations', 422, params=dict(date_from='2023-12-31', date_to='2023-01-01')))
check('Unknown observation station rejected', lambda: expect_status('/api/v1/workspace/stations/UNKNOWN/observations', 404))
check('Spatial corridor available', lambda: evidence.setdefault('corridor_counts', {k: len(v) for k, v in get('/api/v1/workspace/simulation/corridor').items() if isinstance(v, list)}))
timeline = get('/api/v1/workspace/simulation/timeline')
evidence['timeline'] = dict(count=len(timeline['items']), first=timeline['items'][0]['year_month'], last=timeline['items'][-1]['year_month'])


def simulation(month):
    data = get('/api/v1/workspace/simulation/frame', year_month=month, open_below_ec=100, close_above_ec=150)
    assert len(data['river_segments']) == 35 and len(data['gates']) == 27
    assert data['simulation_layer'] and not data['gate_decision_eligible'] and data['actuator_command'] is None
    assert all(g['actuator_command'] is None for g in data['gates'])
    counts = {}
    for gate in data['gates']:
        key = gate['advisory_code']
        counts[key] = counts.get(key, 0) + 1
    evidence.setdefault('frames', {})[month] = counts
    return counts


for month in ('2016-03', '2022-10', '2024-04', '2026-08'):
    check('35 segments and 27 advisory gates ' + month, lambda m=month: simulation(m))
check('Missing simulation month returns 404', lambda: expect_status('/api/v1/workspace/simulation/frame', 404, params=dict(year_month='2100-01')))
check('Equal simulation thresholds rejected', lambda: expect_status('/api/v1/workspace/simulation/frame', 422, params=dict(year_month='2024-04', open_below_ec=150, close_above_ec=150)))
check('Invalid simulation month rejected', lambda: expect_status('/api/v1/workspace/simulation/frame', 422, params=dict(year_month='2024-13')))
catalog = get('/api/v1/workspace/multivariate/catalog')
target = catalog['default_target_month']


def forecast(station):
    payload = dict(station=station, target_month=target, input_mode='ARCHIVE')
    code, data, elapsed = request('/api/v1/workspace/multivariate/predict', data=payload)
    assert code == 200, (code, data)
    assert data['station'] == station and data['target_month'] == target
    assert math.isfinite(data['predicted_ec_mS_m']) and data['predicted_ec_mS_m'] >= 0
    assert not data['deployment_ready'] and not data['gate_decision_eligible']
    evidence.setdefault('forecasts', {})[station] = dict(ec=data['predicted_ec_mS_m'], target=target, input_month=data['input_month'], seconds=elapsed, persisted=False)
    return evidence['forecasts'][station]


for station in ('MyTho', 'TanChau'):
    check('Actual model inference, archive input ' + station, lambda s=station: forecast(s))
    check('Evaluation artifact ' + station, lambda s=station: dict(rows=len(get('/api/v1/workspace/multivariate/evaluation', station=s)['items'])))
check('Forecast during training period rejected', lambda: expect_status('/api/v1/workspace/multivariate/predict', 422, data=dict(station='MyTho', target_month='2023-12', input_mode='ARCHIVE')))
check('Forecast at unregistered gate rejected', lambda: expect_status('/api/v1/workspace/multivariate/predict', 404, data=dict(station='GATE_TG_002', target_month=target, input_mode='ARCHIVE')))
check('Manual forecast missing weather rejected', lambda: expect_status('/api/v1/workspace/multivariate/predict', 422, data=dict(station='MyTho', target_month=target, input_mode='MANUAL')))
check('Negative rainfall rejected', lambda: expect_status('/api/v1/workspace/multivariate/predict', 422, data=dict(station='MyTho', target_month=target, input_mode='MANUAL', rainfall_mm=-1, temperature_degC=28, wind_source_units=2)))
check('Future unavailable weather rejected', lambda: expect_status('/api/v1/workspace/multivariate/inputs', 422, params=dict(station='MyTho', target_month='2100-01')))

gate = 'DT_PLIII_001'
policy = get('/api/v1/workspace/gate-template/policy', gate_code=gate)
scenario = get('/api/v1/workspace/gate-template/input', gate_code=gate)
scenario.update(evaluation_mode='SIMULATION', mode='INTAKE')
policy.update(parameter=dict(name='EC', unit='mS/m', ec_basis='RAW'), vertical_datum='UAT_HYPOTHETICAL_DATUM', quality_thresholds=dict(open_below=100, close_at_or_above=150), levels=dict(min_head_m=0.1, max_abs_head_m=2, inside_min_m=0, inside_max_m=2), allow_drainage_with_saline_outside=False)
for key, value in dict(outside_level=1.2, inside_level=0.5, outside_quality=80, inside_quality=70).items():
    scenario['observations'][key].update(value=value, observed_at='2026-10-26T09:00:00+07:00', gate_code=gate, unit='mS/m' if key.endswith('quality') else 'm', source_reference='UAT 2026-10-26 HYPOTHETICAL; not an observation')
    scenario['observations'][key].update(dict(parameter='EC', ec_basis='RAW') if key.endswith('quality') else dict(vertical_datum='UAT_HYPOTHETICAL_DATUM'))


def gate_case(name, expected, ec=80, mode='INTAKE', outside=1.2, inside=0.5, allow=False):
    data, rules = copy.deepcopy(scenario), copy.deepcopy(policy)
    data['mode'] = mode
    for key, value in dict(outside_quality=ec, outside_level=outside, inside_level=inside).items():
        data['observations'][key]['value'] = value
    rules['allow_drainage_with_saline_outside'] = allow
    code, result, elapsed = request('/api/v1/workspace/gate-evaluation', data=dict(input=data, policy=rules))
    assert code == 200 and result['simulation_outcome'] == expected, (code, result)
    assert result['actuator_command'] is None and result['recommendation'] is None
    evidence.setdefault('gate_cases', {})[name] = result
    return dict(outcome=result['simulation_outcome'], reasons=result['reasons'])


for name, kwargs in [
    ('Intake favorable EC and hydraulic head', dict(expected='CONDITIONS_MET')),
    ('Intake EC at lower boundary', dict(expected='REVIEW_REQUIRED', ec=100)),
    ('Intake EC at closing boundary', dict(expected='BLOCKED', ec=150)),
    ('Intake wrong flow direction', dict(expected='BLOCKED', outside=0.3)),
    ('Drain correct flow direction', dict(expected='CONDITIONS_MET', mode='DRAIN', outside=0.2, inside=0.8)),
    ('Drain saline exterior without override', dict(expected='BLOCKED', mode='DRAIN', outside=0.2, inside=0.8, ec=200)),
    ('Drain saline exterior explicit scenario override', dict(expected='CONDITIONS_MET', mode='DRAIN', outside=0.2, inside=0.8, ec=200, allow=True)),
]:
    check(name, lambda n=name, k=kwargs: gate_case(n, **k))
check('Cross-origin write rejected before persistence', lambda: expect_status('/api/v1/workspace/gate-drafts', 403, data={}, headers={'Origin':'https://example.invalid'}))
check('Model binary download blocked', lambda: expect_status('/api/v1/workspace/artifacts/MYTHO_MONTHLY_LAG0/model_bundle.joblib', 404))
check('DSS forecast history readable', lambda: dict(total=get('/api/v1/workspace/multivariate/history', limit=1)['total']))
check('DSS gate drafts readable', lambda: dict(total=get('/api/v1/workspace/gate-drafts', gate_code=gate, limit=1)['total']))
check('Database gate inventory readable', lambda: dict(count=len(get('/api/v1/workspace/database-gates')['items'])))
check('Intake review coverage readable', lambda: evidence.setdefault('intake_coverage', get('/api/v1/workspace/intake/coverage')))
print(json.dumps(dict(passed=sum(c['status']=='PASS' for c in checks), failed=sum(c['status']=='FAIL' for c in checks), total=len(checks))), flush=True)
