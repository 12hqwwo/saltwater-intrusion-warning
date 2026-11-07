"""Read verified frozen-label outage evidence, separate from rolling-origin scores."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'FROZEN_EC_WEATHER_ONLY_V1'
INDEX = ROOT / 'data/models/frozen_ec_gap_evaluation.json'
LABELS = {
    'RandomForest': 'Random Forest · khí tượng t−2 và chu kỳ tháng',
    'FrozenPersistence': 'Giữ EC cuối cùng trước khi mất dữ liệu',
    'MonthlyClimatology': 'Trung bình từng tháng từ EC trước khi mất dữ liệu',
    'FrozenSeasonalRepeat': 'Lặp EC gần nhất của từng tháng trước khi mất dữ liệu',
    'SeasonalityOnlyRF': 'Random Forest chỉ dùng chu kỳ tháng (đối chứng khí tượng)',
}


def _verified(path, expected):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError('Evaluation artifact must stay inside repository')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Frozen EC evaluation checksum mismatch')
    return raw


def evidence():
    index = json.loads(INDEX.read_text('utf-8'))
    manifest_path = ROOT / index['run_manifest_path']
    manifest = json.loads(_verified(manifest_path, index['run_manifest_sha256']))
    registry = json.loads((ROOT / 'data/models/multivariate_registry.json').read_text('utf-8'))
    if index['protocol_id'] != PROTOCOL or manifest['protocol_id'] != PROTOCOL:
        raise ValueError('Unexpected EC gap protocol')
    if any(entry['model_sha256'] != manifest['deployed_model_sha256'].get(station)
           for station, entry in registry['models'].items()):
        raise ValueError('Frozen EC evaluation refers to different deployed model artifacts')
    return manifest, manifest_path.parent


def _table(manifest, directory, filename):
    import pandas as pd
    from io import BytesIO
    return pd.read_csv(BytesIO(_verified(directory / filename, manifest['output_sha256'][filename])))


def summary(station):
    manifest, directory = evidence()
    frame = _table(manifest, directory, 'metrics.csv')
    rows = frame[(frame.station == station) & (frame.experiment == manifest['primary_experiment'])
                 & (frame.ec_delay_days == manifest['primary_ec_delay_days']) & (frame.cohort == 'all')]
    if set(rows.model) != set(LABELS) or len(rows) != len(LABELS):
        raise ValueError('Incomplete frozen EC summary cohort')
    period = manifest['experiments'][manifest['primary_experiment']]
    return dict(protocol_id=PROTOCOL, experiment=manifest['primary_experiment'],
        period=period['start'] + '..' + period['end'], ec_delay_days=manifest['primary_ec_delay_days'],
        metrics={r.model: dict(n=int(r.n), mae_mS_m=float(r.mae_mS_m), rmse_mS_m=float(r.rmse_mS_m))
                 for r in rows.itertuples()},
        freeze_rule=manifest['freeze_rule'], weather_scope=manifest['weather_scope'])


def records(station, experiment=None, ec_delay_days=5):
    from backend.domain.multivariate_ec import STATIONS, normalize_station
    key = normalize_station(station)
    manifest, directory = evidence()
    experiment = experiment or manifest['primary_experiment']
    if experiment not in manifest['experiments'] or ec_delay_days not in manifest['ec_delay_days']:
        raise ValueError('Unknown frozen EC experiment or availability delay')
    predictions = _table(manifest, directory, 'predictions.csv')
    rows = predictions[(predictions.station == key) & (predictions.experiment == experiment)
                       & (predictions.ec_delay_days == ec_delay_days)].sort_values('target_month')
    scores = _table(manifest, directory, 'metrics.csv')
    scores = scores[(scores.station == key) & (scores.experiment == experiment)
                    & (scores.ec_delay_days == ec_delay_days) & (scores.cohort == 'all')]
    if rows.empty or rows.target_month.duplicated().any() or set(scores.model) != set(LABELS):
        raise ValueError('Incomplete frozen EC evaluation cohort')
    if any(int(n) != len(rows) for n in scores.n):
        raise ValueError('Frozen EC scores do not match prediction cohort')
    period = manifest['experiments'][experiment]
    remedy_research = None
    if key == 'MYTHO':
        from backend.domain import ec_gap_remedies
        remedy_research = ec_gap_remedies.summary(experiment, ec_delay_days)
    return dict(station=STATIONS[key][0], site_code=STATIONS[key][1], protocol_id=PROTOCOL,
        model_version='RF_FIXED_300_DEPTH8_LEAF3_SEED42_FROZEN', unit='mS/m',
        experiment=experiment, experiments=manifest['experiments'], ec_delay_days=ec_delay_days,
        period=period['start'] + '..' + period['end'],
        frozen_ec_through=rows.last_training_ec_month.iloc[0],
        first_issue_date_local=rows.first_issue_date_local.iloc[0],
        items=rows[['target_month', 'actual_mS_m'] + list(LABELS)].rename(columns={'actual_mS_m': 'actual'}).to_dict('records'),
        methods=[dict(key=key, label=label) for key, label in LABELS.items()],
        metrics={r.model: dict(n=int(r.n), mae_mS_m=float(r.mae_mS_m), rmse_mS_m=float(r.rmse_mS_m))
                 for r in scores.itertuples()},
        seasonal_naive=dict(available_months=int(rows.seasonal_naive_available.sum()), total_months=len(rows),
            note='SeasonalNaive trực tiếp chỉ khả dụng khi EC t−12 có trong tập EC đã khóa; không xếp hạng trên toàn kỳ.'),
        freeze_rule=manifest['freeze_rule'], weather_scope=manifest['weather_scope'],
        limitations=manifest['limitations'], remedy_research=remedy_research)
