"""Build all three missing-EC station series using registered weather-t-2 models.

No EC labels or model training are needed at inference. Archived weather produces
retrospective estimates; it does not create observed EC or a scored future test.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT_FILE = ROOT / 'data/models/future_ec_forecast_2024_2026.csv'
BACKUP = ROOT / 'outputs/frozen_ec_gap_20261104/archive_before_sync'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_future_forecast(start='2024-01', end='2026-08', output=OUTPUT_FILE):
    import pandas as pd
    from backend.domain.multivariate_ec import STATIONS, load_model, predict_month
    from backend.repositories.multivariate_inputs import get_weather_input
    output = Path(output)
    months = pd.period_range(start, end, freq='M').astype(str).tolist()
    if not months or start < '2024-01' or len(start) != 7 or len(end) != 7:
        raise ValueError('Expected a nonempty post-training monthly range')
    records, models = [], {}
    for station in ('TANCHAU', 'MYTHUAN', 'MYTHO'):
        _, manifest = load_model(station)
        if any(month <= manifest['training_cutoff'][:7] for month in months):
            raise ValueError('Archive target overlaps model training labels')
        models[station] = dict(model_version=manifest['model_version'],
            model_sha256=manifest['model_sha256'], training_cutoff=manifest['training_cutoff'])
        for month in months:
            weather = get_weather_input(station, month)
            if weather.get('wind_unit') != 'm/s' or weather.get('complete') is not True:
                raise ValueError('Archive requires complete verified-unit weather')
            prediction = predict_month(station, month + '-01', weather)
            records.append(dict(station=STATIONS[station][0], year_month=month,
                predicted_ec_mS_m=prediction['predicted_ec_mS_m'],
                rainfall_mm=weather['rainfall_mm'], temperature_degC=weather['temperature_degC'],
                wind_m_s=weather['wind_source_units'], model='RandomForest_Multivariate_Weather',
                input_month=weather['input_month'], weather_lag_months=2,
                model_version=prediction['model_version'], model_sha256=prediction['model_provenance']['model_sha256'],
                training_cutoff=manifest['training_cutoff'], weather_source=weather['source'],
                weather_sha256=weather['sha256'], weather_assumed_available_at=weather['assumed_available_at'],
                data_kind='RETROSPECTIVE_WEATHER_ESTIMATE',
                estimation_method='ARCHIVE_WEATHER_T_MINUS_2_MODEL_ESTIMATE'))
    result = pd.DataFrame(records).sort_values(['year_month', 'station'])
    # Keep exact previous values and metadata once, including the former mixed-model archive.
    if output.resolve() == OUTPUT_FILE.resolve() and output.exists():
        BACKUP.mkdir(parents=True, exist_ok=True)
        for previous in (output, output.with_suffix('.manifest.json')):
            saved = BACKUP / previous.name
            if previous.exists() and not saved.exists():
                saved.write_bytes(previous.read_bytes())
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False, encoding='utf-8-sig')
    manifest = dict(schema_version=2, sha256=digest(output), stations=[STATIONS[s][0] for s in models],
        months=months, rows=len(result), models=models, weather_lag_months=2,
        ec_required_at_inference=False, builder='scripts/run_future_forecast_2024_2026.py',
        builder_sha256=digest(__file__),
        note='All three stations use their registered five-feature RF with weather t-2; no EC after training is used. '
             'Archive weather estimates are retrospective, not historical issue-time forecast records. '
             'No observed 2024-2026 EC is available for scoring. January 2024 is an estimate after EC December 2023 becomes available.')
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    frame = run_future_forecast()
    print(f'Wrote {len(frame)} estimates: 3 stations, weather t-2, no EC at inference.')
