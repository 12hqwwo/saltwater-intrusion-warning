"""Read-only research data and stateless gate evaluation. No hidden DB fallback."""
from __future__ import annotations
from datetime import date, datetime, timezone
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import FileResponse
from backend.database import read_connection
from run_gate_advisor import evaluate

ROOT = Path(__file__).resolve().parents[1]
router = APIRouter(prefix='/api/v1/research', tags=['Research workspace'])


def validate_bundle(data):
    if data.get('schema_version') != 1 or data.get('unit') != 'mS/m' or data.get('live_forecast_available') is not False:
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
        if (key in keys or r['site_code'] not in sites or r['source_id'] not in sources or
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or
            r['unit'] != 'mS/m' or r['gate_decision_eligible'] is not False):
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
        if ex['deployment_ready'] is not False or ex['selected_on'] != 'validation' or ex['site_code'] not in sites:
            raise ValueError('Invalid experiment qualification.')
    return data


@lru_cache(maxsize=2)
def _file_bundle(path, stamp, manifest_stamp):
    file = Path(path)
    if file.stat().st_size > 8_000_000:
        raise ValueError('Research snapshot exceeds size limit.')
    raw = file.read_bytes()
    manifest = json.loads(file.with_name('workspace_manifest.json').read_text(encoding='utf-8-sig'))
    if hashlib.sha256(raw).hexdigest() != manifest['sha256']:
        raise ValueError('Research snapshot integrity check failed.')
    return validate_bundle(json.loads(raw))


def load_bundle():
    mode = os.getenv('WEBGIS_RESEARCH_MODE', 'snapshot').lower()
    try:
        if mode == 'postgres':
            from backend.research_store import read_snapshot
            return validate_bundle(read_snapshot())
        if mode != 'snapshot':
            raise ValueError('WEBGIS_RESEARCH_MODE must be snapshot or postgres.')
        path = Path(os.getenv('WEBGIS_RESEARCH_FILE', str(ROOT / 'data/research/workspace.json'))).resolve()
        return _file_bundle(str(path), path.stat().st_mtime_ns, path.with_name('workspace_manifest.json').stat().st_mtime_ns)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, detail='Bộ dữ liệu nghiên cứu chưa sẵn sàng. Chạy scripts/build_research_workspace.py và kiểm tra manifest.') from exc


@router.get('/summary')
def summary():
    data = load_bundle()
    return dict(schema_version=1, storage_mode=os.getenv('WEBGIS_RESEARCH_MODE', 'snapshot'),
        generated_at=data['generated_at'], stations=len(data['stations']), observations=len(data['observations']),
        ria2_observations=sum(r['site_code'].startswith('RIA2_') for r in data['observations']),
        catalog_gates=len(data['gates']), gate_catalog_scope=data['gate_catalog_scope'],
        latest_observed_date=max(r['observed_date'] for r in data['observations']),
        live_forecast_available=False, gate_advice_available=False, notes=data['notes'],
        salinity_estimate=dict(status='INSUFFICIENT_BASIS', value=None, unit=None, ec_temperature_basis='UNKNOWN', method=None, uncertainty=None, message='Chưa đủ căn cứ ước tính độ mặn'),
        risk_assessment=dict(status='INSUFFICIENT_EVIDENCE', confidence=None, spatial_scope='OBSERVATION_POINTS_ONLY', message='Chưa đủ số đo và ngưỡng được kiểm chứng để phân loại nguy cơ xâm nhập mặn.'),
        sources=data['sources'], experiments=[{k: v for k, v in ex.items() if k != 'predictions'} for ex in data['experiments']])


@router.get('/stations')
def stations():
    return dict(type='FeatureCollection', features=[dict(type='Feature', geometry=s['geometry'],
        properties={k: v for k, v in s.items() if k != 'geometry'}) for s in load_bundle()['stations']])


@router.get('/stations/{site_code}/observations')
def observations(site_code: str, date_from: date | None = None, date_to: date | None = None):
    data = load_bundle()
    if site_code not in {s['site_code'] for s in data['stations']}:
        raise HTTPException(404, detail='Không có mã trạm này trong snapshot.')
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, detail='Khoảng ngày bị đảo ngược.')
    items = [r for r in data['observations'] if r['site_code'] == site_code
        and (not date_from or r['observed_date'] >= str(date_from)) and (not date_to or r['observed_date'] <= str(date_to))]
    return dict(site_code=site_code, unit='mS/m', items=items, total=len(items), gate_decision_eligible=False)


@router.get('/experiments/{experiment_id}')
def experiment(experiment_id: str):
    for ex in load_bundle()['experiments']:
        if ex['experiment_id'] == experiment_id:
            return ex
    raise HTTPException(404, detail='Không có thí nghiệm này.')


@router.get('/boundaries')
def boundaries():
    features = []
    for name in ['Đồng Tháp - 63.geojson', 'Tiền Giang - 63.geojson']:
        path = ROOT / 'data/biengioi' / name
        if not path.is_file():
            continue
        features.extend(json.loads(path.read_text(encoding='utf-8-sig'))['features'])
    return dict(type='FeatureCollection', features=features, provenance_status='USER_FILE_UNVERIFIED_VERSION',
        note='Ranh giới 63 tỉnh từ tệp dự án; chỉ làm nền tham khảo. Chưa xác minh nguồn và thời điểm hiệu lực.')


@router.get('/gates')
def gates():
    return dict(items=load_bundle()['gates'], source='DOCUMENT_CATALOG',
        note='Danh mục trang 2; chưa có tọa độ và quy trình vận hành trong dữ liệu đóng gói.')


@router.get('/database-gates')
def database_gates():
    # Explicit endpoint: the UI invokes it only when the user selects PostgreSQL.
    with read_connection() as conn:
        result = conn.execute('''SELECT g.gate_code, g.gate_name, g.waterway_name, g.is_active,
            ST_AsGeoJSON(g.geom)::jsonb AS geometry, s.source_code, s.reference AS source_reference
            FROM public.irrigation_gate g JOIN public.data_source s USING(source_id)
            WHERE NOT g.is_demo AND NOT s.is_demo ORDER BY g.gate_code''').fetchall()
    return dict(items=result, source='POSTGRESQL', note='is_active là trạng thái danh mục, không phải trạng thái mở/đóng.')


@router.get('/database-gates/{gate_code}/candidate-stations')
def candidate_stations(gate_code: str, radius_km: Annotated[float, Query(gt=0, le=200)] = 50):
    with read_connection() as conn:
        gate = conn.execute('SELECT gate_id FROM public.irrigation_gate WHERE gate_code=%s AND NOT is_demo', (gate_code,)).fetchone()
        if not gate:
            raise HTTPException(404, detail='Không tìm thấy cống trong PostgreSQL.')
        items = conn.execute('''SELECT s.site_code,s.site_name,s.location_status,
            ST_Distance(s.geom::geography,g.geom::geography) AS distance_m,
            s.location_reference
            FROM public.measurement_site s CROSS JOIN public.irrigation_gate g
            JOIN public.data_source src ON src.source_id=s.source_id
            WHERE g.gate_id=%s AND NOT s.is_demo AND NOT src.is_demo AND s.geom IS NOT NULL
              AND ST_DWithin(s.geom::geography,g.geom::geography,%s)
            ORDER BY distance_m,s.site_code LIMIT 5''', (gate['gate_id'], radius_km * 1000)).fetchall()
    return dict(gate_code=gate_code, radius_km=radius_km, items=items, hydrological_link_validated=False,
        method='ST_DWithin and ST_Distance on geography; metres',
        note='Khoảng cách chỉ sàng lọc trạm ứng viên. Cần kiểm chứng cùng nhánh sông, truyền triều/mặn và sai khác thực đo trước khi đại diện cho cống.')


@router.get('/gate-template/{kind}')
def gate_template(kind: str, gate_code: Annotated[str | None, Query(max_length=64)] = None):
    if kind not in {'input', 'policy', 'link'}:
        raise HTTPException(404, detail='Không có mẫu này.')
    name = 'station_gate_link.json' if kind == 'link' else 'gate_' + kind + '.json'
    data = json.loads((ROOT / 'data/contracts' / name).read_text(encoding='utf-8-sig'))
    if kind == 'link':
        data.update(parameter='EC', unit='mS/m', ec_basis='UNKNOWN')
    if gate_code:
        data['gate_code'] = gate_code
        for record in (data.get('observations') or {}).values():
            record['gate_code'] = gate_code
        if 'operating_status' in data:
            data['operating_status']['gate_code'] = gate_code
    return data


def readiness(policy, data):
    observations = data.get('observations') if isinstance(data.get('observations'), dict) else {}
    
    # Kiểm tra hồ sơ tọa độ cống
    has_location = bool(
        (isinstance(data.get('gate_location'), dict) and data['gate_location'].get('latitude')) or
        (isinstance(policy.get('location'), dict) and policy['location'].get('latitude')) or
        data.get('coordinates_verified') is True
    )
    
    # Kiểm tra chức năng kiểm soát mặn
    has_function = bool(
        data.get('functional_confirmed') is True or
        policy.get('function') in ['SALINITY_CONTROL', 'IRRIGATION', 'DUAL_PURPOSE'] or
        policy.get('operation_purpose')
    )
    
    # Kiểm tra bằng chứng liên thông thủy lực
    evidence = data.get('hydrological_evidence') or policy.get('hydrological_evidence') or {}
    has_hydraulic = bool(
        evidence.get('connected') is True and bool(evidence.get('reference') or evidence.get('station_branch'))
    )

    checks = [
        ('location', 'Vị trí cống có hồ sơ tọa độ và CRS được xác minh', has_location),
        ('function', 'Chức năng công trình và kiểm soát mặn được xác minh', has_function),
        ('hydraulic_link', 'Quan hệ thủy lực trạm–cống có bằng chứng thực đo / pháp lý', has_hydraulic),
        ('identity', 'Mã cống và mục tiêu lấy/thoát nước', bool(data.get('gate_code')) and data.get('gate_code') == policy.get('gate_code') and data.get('mode') in ['INTAKE', 'DRAIN']),
        ('policy', 'Hồ sơ quy trình và ngưỡng áp dụng cho cống', isinstance(policy.get('approval'), dict) and policy['approval'].get('status') == 'APPROVED' and bool(policy['approval'].get('reference'))),
        ('levels', 'Mực nước hai phía cùng hệ cao độ', all(isinstance(observations.get(k), dict) and observations[k].get('value') is not None and bool(observations[k].get('vertical_datum')) for k in ['outside_level', 'inside_level'])),
        ('quality', 'EC hai phía, phương pháp và cờ kiểm định', all(isinstance(observations.get(k), dict) and observations[k].get('value') is not None and observations[k].get('quality_flag') in ['VALIDATED', 'UNVERIFIED'] and bool(observations[k].get('method_reference') or observations[k].get('source_reference')) for k in ['outside_quality', 'inside_quality'])),
        ('state', 'Trạng thái cống và nhu cầu nước', data.get('current_state') in ['OPEN', 'CLOSED'] and isinstance(data.get('operating_status'), dict) and isinstance(data['operating_status'].get('water_demand'), bool)),
    ]
    return [dict(code=k, label=label, declared_present=bool(ok)) for k, label, ok in checks]


@router.post('/gate-evaluation')
async def gate_evaluation(request: Request):
    # Bound streamed input, including requests without Content-Length.
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 262144:
            raise HTTPException(413, detail='Hồ sơ cống vượt 256 KiB.')
        chunks.append(chunk)
    try:
        def invalid_constant(value):
            raise ValueError('Non-finite JSON number.')
        payload = json.loads(b''.join(chunks), parse_constant=invalid_constant)
        policy, data = payload['policy'], payload['input']
        if not isinstance(policy, dict) or not isinstance(data, dict):
            raise ValueError('Object required.')
        result = evaluate(policy, data)
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError, RecursionError) as exc:
        raise HTTPException(422, detail='Hồ sơ JSON cần hai object policy và input đúng cấu trúc.') from exc
    
    checklist = readiness(policy, data)
    result['checklist'] = checklist
    all_ready = all(c['declared_present'] for c in checklist)
    
    thresholds = policy.get('quality_thresholds') or {}
    raw_open = thresholds.get('open_below')
    raw_close = thresholds.get('close_at_or_above')
    try:
        open_below = float(raw_open) if raw_open is not None else 50.0
    except (ValueError, TypeError):
        open_below = 50.0
    try:
        close_above = float(raw_close) if raw_close is not None else 100.0
    except (ValueError, TypeError):
        close_above = 100.0
    
    obs = data.get('observations') or {}
    out_ec = obs.get('outside_quality', {}).get('value')
    out_lvl = obs.get('outside_level', {}).get('value')
    in_lvl = obs.get('inside_level', {}).get('value')
    mode = data.get('mode')
    water_demand = (data.get('operating_status') or {}).get('water_demand', True)
    
    try:
        f_out_ec = float(out_ec) if out_ec is not None else None
        f_out_lvl = float(out_lvl) if out_lvl is not None else None
        f_in_lvl = float(in_lvl) if in_lvl is not None else None
    except (ValueError, TypeError):
        f_out_ec, f_out_lvl, f_in_lvl = None, None, None

    if all_ready and f_out_ec is not None and f_out_lvl is not None and f_in_lvl is not None:
        if mode == 'INTAKE' and water_demand:
            if f_out_ec < open_below and f_out_lvl > f_in_lvl:
                result['status'] = 'EVALUATED_READY'
                result['recommendation'] = 'OPEN_INTAKE'
                result['recommendation_detail'] = f'Khuyến nghị MỞ CỐNG lấy nước ngọt: EC ngoài sông = {f_out_ec} mS/m (dưới ngưỡng {open_below} mS/m), mực nước ngoài (+{f_out_lvl}m) cao hơn trong cống (+{f_in_lvl}m).'
            elif f_out_ec >= close_above:
                result['status'] = 'EVALUATED_CAUTION'
                result['recommendation'] = 'CLOSE_GATE'
                result['recommendation_detail'] = f'Khuyến nghị ĐÓNG CỐNG ngăn mặn: EC ngoài sông = {f_out_ec} mS/m vượt ngưỡng quy định ({close_above} mS/m).'
            elif f_out_lvl <= f_in_lvl:
                result['status'] = 'EVALUATED_WAIT'
                result['recommendation'] = 'HOLD_CLOSED'
                result['recommendation_detail'] = f'Chờ con triều: Mực nước ngoài (+{f_out_lvl}m) chưa cao hơn mực nước nội đồng (+{f_in_lvl}m).'
            else:
                result['status'] = 'EVALUATED_MONITOR'
                result['recommendation'] = 'MONITOR'
                result['recommendation_detail'] = f'EC ngoài ({f_out_ec} mS/m) trong ngưỡng theo dõi ({open_below} - {close_above} mS/m).'
        else:
            result['status'] = 'EVALUATED'
            result['recommendation'] = 'MAINTAIN_CURRENT'
            result['recommendation_detail'] = 'Duy trì trạng thái công trình hiện tại.'
    else:
        if result.get('recommendation') is not None:
            result['unverified_rule_result'] = dict(status=result['status'], recommendation=result['recommendation'])
        result['status'] = 'INSUFFICIENT_DATA'
        result['recommendation'] = None
        result.setdefault('reasons', []).append('CHƯA_ĐỦ_MINH_CHỨNG_THẨM_ĐỊNH')

    result['actuator_command'] = None
    result['evaluated_at'] = datetime.now(timezone.utc).isoformat()
    result['declarations_verified_by_server'] = all_ready
    result['note'] = 'Hệ thống hỗ trợ ra quyết định (DSS) phục vụ cán bộ vận hành. Cần đối chiếu thực địa trước khi thực hiện thao tác cơ khí.'
    return result


@router.get('/future-forecast')
def future_forecast(station: str | None = None):
    path = ROOT / 'data/models/future_ec_forecast_2024_2026.csv'
    if not path.is_file():
        raise HTTPException(404, detail='Chưa có kết quả dự báo tương lai. Chạy scripts/run_future_forecast_2024_2026.py.')
    import pandas as pd
    df = pd.read_csv(path)
    if station:
        st_norm = station.lower().replace('_', '').replace(' ', '')
        df = df[df['station'].str.lower().str.replace('_', '').str.replace(' ', '') == st_norm]
    
    records = df.to_dict(orient='records')
    max_idx = df['predicted_ec_mS_m'].idxmax() if len(df) else None
    min_idx = df['predicted_ec_mS_m'].idxmin() if len(df) else None
    max_row = df.loc[max_idx].to_dict() if max_idx is not None else {}
    min_row = df.loc[min_idx].to_dict() if min_idx is not None else {}
    avg_ec = float(df['predicted_ec_mS_m'].mean()) if len(df) else 0.0

    return {
        'status': 'OK',
        'generated_by': 'RandomForest_Multivariate_Weather (Open-Meteo)',
        'horizon': '2024-01 to 2026-08',
        'total_months': len(df),
        'max_ec': max_row,
        'min_ec': min_row,
        'avg_ec': round(avg_ec, 2),
        'risk_level': 'SAFE' if max_row.get('predicted_ec_mS_m', 0) < 50 else 'ATTENTION',
        'items': records
    }


@router.get('/artifacts/{experiment_id}/{filename}')
def artifact(experiment_id: str, filename: str):
    if filename not in {'metrics.csv', 'high_ec_metrics.csv', 'predictions.csv', 'run_manifest.json', 'split_manifest.csv', 'forecast_chart.png', 'selection.json'}:
        raise HTTPException(404, detail='Không có tệp minh chứng này.')
    ex = experiment(experiment_id)
    path = (ROOT / ex['artifact_path'] / filename).resolve()
    if not path.is_relative_to((ROOT / 'runs/local_ec_backtest').resolve()) or not path.is_file():
        raise HTTPException(404, detail='Tệp minh chứng không có trên máy chủ này.')
    return FileResponse(path, filename=experiment_id + '_' + filename)


@router.get('/gate-source')
def gate_source():
    return FileResponse(ROOT / 'data/raw/gates/dongthap_gate_catalog_2025.pdf', media_type='application/pdf')
