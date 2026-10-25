"""Describe archived weather-based EC estimates without operational claims."""
from datetime import datetime
import json
import math
from backend.repositories.workspace import estimate_rows
from backend.services.workspace import WorkspaceError, artifact_path, experiment
from backend.schemas import LOCAL_TZ


def next_forecast(experiment_id: str):
    ex = experiment(experiment_id)
    path = artifact_path(experiment_id, 'next_forecast.json')
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict):
            raise ValueError('Expected a forecast object.')
        if (data['data_kind'].upper() != 'EXPERIMENTAL_NEXT_AFTER_LAST_OBSERVATION'
                or data['deployment_ready'] is not False
                or data['selected_model'] != ex['selected_model']
                or data.get('experiment_id', experiment_id) != experiment_id
                or ex['unit'] != 'mS/m'):
            raise ValueError('Forecast does not match experiment metadata.')
        origin = datetime.fromisoformat(data['forecast_origin'])
        target = datetime.strptime(data['target_month'], '%Y-%m-%d').date()
        if origin.tzinfo is None or target.day != 1 or target <= origin.astimezone(LOCAL_TZ).date():
            raise ValueError('Invalid forecast origin or target month.')
        rows, selected = data['all_predictions'], data['selected_prediction']
        if not isinstance(rows, list) or not rows or not isinstance(selected, dict):
            raise ValueError('Missing prediction records.')
        for row in rows:
            if not isinstance(row, dict) or (
                row['station'] != ex['station'] or row['unit'] != 'mS/m'
                or row['forecast_origin'] != data['forecast_origin']
                or row['target_month'] != data['target_month']
                or row['stage'] != 'next_after_last_observation'
            ):
                raise ValueError('Prediction metadata does not match forecast.')
            if row['status'] == 'SUCCESS':
                value = row['predicted']
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError('Invalid successful EC prediction.')
            elif row.get('predicted') is not None:
                raise ValueError('Failed prediction must not expose an EC value.')
        if selected not in rows or selected['model'] != ex['selected_model']:
            raise ValueError('Selected prediction does not match selected model.')
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise WorkspaceError(503, 'Next-after-last-observation artifact unavailable or invalid.') from exc
    return dict(data, experiment_id=experiment_id, site_code=ex['site_code'],
        station=ex['station'], availability_lag_days=ex['availability_lag_days'],
        data_kind='EXPERIMENTAL_NEXT_AFTER_LAST_OBSERVATION', unit='mS/m',
        target_is_before_current_month=target < datetime.now(LOCAL_TZ).date().replace(day=1),
        status='AVAILABLE' if selected['status'] == 'SUCCESS' else 'UNAVAILABLE',
        live_forecast_available=False, deployment_ready=False, gate_decision_eligible=False,
        note='Experimental forecast after the last archived observation; this is not a forecast for today.')


def normalize_station(value):
    return value.lower().replace('_', '').replace(' ', '')


def monthly_estimates(station: str | None = None):
    try:
        rows = estimate_rows()
        if not rows:
            raise ValueError('Empty estimate artifact.')
        keys = set()
        for row in rows:
            if not row['station'] or not row['model']:
                raise ValueError('Missing station or model.')
            datetime.strptime(row['year_month'], '%Y-%m')
            key = (row['station'], row['year_month'])
            if key in keys:
                raise ValueError('Duplicate station month.')
            keys.add(key)
            for field in ['predicted_ec_mS_m', 'rainfall_mm', 'temperature_degC', 'wind_m_s']:
                row[field] = float(row[field])
                if not math.isfinite(row[field]):
                    raise ValueError('Non-finite estimate value.')
            if row['predicted_ec_mS_m'] < 0:
                raise ValueError('Negative EC estimate.')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise WorkspaceError(503, 'Monthly estimate artifact unavailable or invalid.') from exc
    if station is not None:
        rows = [
            row for row in rows
            if normalize_station(row['station']) == normalize_station(station)
        ]
        if not rows:
            raise WorkspaceError(404, 'No monthly estimates for this station.')
    rows.sort(key=lambda row: (row['year_month'], row['station']))
    return dict(
        status='AVAILABLE',
        data_kind='RETROSPECTIVE_WEATHER_ESTIMATE',
        unit='mS/m',
        time_resolution='MONTHLY',
        issued_at=None,
        live_forecast_available=False,
        gate_decision_eligible=False,
        deployment_ready=False,
        validation_metrics=None,
        generated_by=', '.join(sorted({row['model'] for row in rows})),
        horizon=f"{min(row['year_month'] for row in rows)} to {max(row['year_month'] for row in rows)}",
        total_months=len(rows),
        max_ec=max(rows, key=lambda row: row['predicted_ec_mS_m']),
        min_ec=min(rows, key=lambda row: row['predicted_ec_mS_m']),
        avg_ec=round(sum(row['predicted_ec_mS_m'] for row in rows) / len(rows), 2),
        note=(
            'Archived monthly EC estimates using weather covariates. '
            'Input availability at a forecast issue time and independent validation '
            'are not established; these are not live forecasts or gate operating advice.'
        ),
        items=rows,
    )
