"""Workspace use cases shared by the canonical and legacy HTTP routes."""
from datetime import date
from pathlib import Path
from backend.repositories import workspace as store
from backend.repositories.workspace import ROOT


class WorkspaceError(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def load_bundle():
    try:
        return store.load_bundle()
    except store.WorkspaceUnavailable as exc:
        raise WorkspaceError(503, str(exc)) from exc


def summary():
    data = load_bundle()
    return dict(
        schema_version=1,
        storage_mode=data['storage_mode'],
        observation_source=data['observation_source'],
        artifact_source=data.get('artifact_source', 'RESEARCH_SNAPSHOT'),
        dataset_selection=data['dataset_selection'],
        datasets=data.get('datasets', []),
        generated_at=data['generated_at'],
        stations=len(data['stations']),
        observations=len(data['observations']),
        ria2_observations=sum(r['site_code'].startswith('RIA2_') for r in data['observations']),
        catalog_gates=len(data['gates']),
        gate_catalog_scope=data['gate_catalog_scope'],
        latest_observed_date=max((r['observed_date'] for r in data['observations']), default=None),
        live_forecast_available=False,
        gate_advice_available=False,
        notes=data['notes'],
        salinity_estimate=dict(
            status='INSUFFICIENT_BASIS',
            value=None,
            unit=None,
            ec_temperature_basis='UNKNOWN',
            method=None,
            uncertainty=None,
            message='Chưa đủ căn cứ ước tính độ mặn',
        ),
        risk_assessment=dict(
            status='INSUFFICIENT_EVIDENCE',
            confidence=None,
            spatial_scope='OBSERVATION_POINTS_ONLY',
            message='Chưa đủ số đo và ngưỡng được kiểm chứng để phân loại nguy cơ xâm nhập mặn.',
        ),
        sources=data['sources'],
        artifact_sources=data.get('artifact_sources', data['sources']),
        experiments=[
            {k: v for k, v in ex.items() if k != 'predictions'}
            for ex in data['experiments']
        ],
    )


def stations():
    data = load_bundle()
    return dict(
        type='FeatureCollection',
        source=data['observation_source'],
        storage_mode=data['storage_mode'],
        features=[
            dict(
                type='Feature',
                geometry=s['geometry'],
                properties={k: v for k, v in s.items() if k != 'geometry'},
            )
            for s in data['stations']
        ],
    )


def observations(
    site_code: str,
    date_from: date | None = None,
    date_to: date | None = None,
):
    data = load_bundle()
    if site_code not in {s['site_code'] for s in data['stations']}:
        raise WorkspaceError(404, detail='Không có mã trạm này trong nguồn dữ liệu đã chọn.')
    if date_from and date_to and date_from > date_to:
        raise WorkspaceError(422, detail='Khoảng ngày bị đảo ngược.')
    items = [
        r for r in data['observations']
        if r['site_code'] == site_code
        and (not date_from or r['observed_date'] >= str(date_from))
        and (not date_to or r['observed_date'] <= str(date_to))
    ]
    return dict(
        site_code=site_code,
        source=data['observation_source'],
        storage_mode=data['storage_mode'],
        datasets=[d for d in data.get('datasets', []) if d['site_code'] == site_code],
        unit='mS/m',
        items=items,
        total=len(items),
        gate_decision_eligible=False,
    )


def experiment(experiment_id: str):
    for ex in load_bundle()['experiments']:
        if ex['experiment_id'] == experiment_id:
            return ex
    raise WorkspaceError(404, detail='Không có thí nghiệm này.')


def boundaries():
    features = []
    for name in ['Đồng Tháp - 63.geojson', 'Tiền Giang - 63.geojson']:
        path = ROOT / 'data/biengioi' / name
        if not path.is_file():
            continue
        features.extend(store.read_json(path)['features'])
    return dict(
        type='FeatureCollection',
        features=features,
        provenance_status='USER_FILE_UNVERIFIED_VERSION',
        note=(
            'Ranh giới 63 tỉnh từ tệp dự án; chỉ làm nền tham khảo. '
            'Chưa xác minh nguồn và thời điểm hiệu lực.'
        ),
    )


def gates():
    return dict(
        items=load_bundle()['gates'],
        source='DOCUMENT_CATALOG',
        note='Danh mục trang 2; chưa có tọa độ và quy trình vận hành trong dữ liệu đóng gói.',
    )


def gate_template(kind: str, gate_code: str | None = None):
    if kind not in {'input', 'policy', 'link'}:
        raise WorkspaceError(404, detail='Không có mẫu này.')
    name = 'station_gate_link.json' if kind == 'link' else 'gate_' + kind + '.json'
    try:
        data = store.read_json(Path('data/contracts') / name)
        if not isinstance(data, dict):
            raise ValueError('Template must be an object.')
        records = data.get('observations', {})
        if not isinstance(records, dict) or any(
            not isinstance(record, dict) for record in records.values()
        ):
            raise ValueError('Template observation records must be objects.')
        if 'operating_status' in data and not isinstance(data['operating_status'], dict):
            raise ValueError('Template operating status must be an object.')
    except (OSError, ValueError, TypeError) as exc:
        raise WorkspaceError(503, 'Gate template unavailable or invalid.') from exc
    if kind == 'link':
        data.update(parameter='EC', unit='mS/m', ec_basis='UNKNOWN')
    if gate_code:
        data['gate_code'] = gate_code
        for record in (data.get('observations') or {}).values():
            record['gate_code'] = gate_code
        if 'operating_status' in data:
            data['operating_status']['gate_code'] = gate_code
    return data


def database_gates():
    return store.database_gates()


def candidate_stations(gate_code: str, radius_km: float = 50):
    try:
        return store.candidate_stations(gate_code, radius_km)
    except LookupError as exc:
        raise WorkspaceError(404, str(exc)) from exc


def artifact_path(experiment_id: str, filename: str):
    if filename not in {
        'metrics.csv',
        'high_ec_metrics.csv',
        'predictions.csv',
        'run_manifest.json',
        'split_manifest.csv',
        'forecast_chart.png',
        'selection.json',
        'next_forecast.json',
    }:
        raise WorkspaceError(404, 'Artifact not available.')
    ex = experiment(experiment_id)
    path = (ROOT / ex['artifact_path'] / filename).resolve()
    if (
        not path.is_relative_to((ROOT / 'runs/local_ec_backtest').resolve())
        or not path.is_file()
    ):
        raise WorkspaceError(404, 'Artifact file not available.')
    return path
