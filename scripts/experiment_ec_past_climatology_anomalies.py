"""Test source-month anomalies computed from prior 15 same-calendar months only."""
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_extreme_robust import COMPACT, fit_predict
from scripts.experiment_ec_feature_enhanced import load_climate
from scripts.experiment_ec_long_hydrology import data_matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/ec_past_anomalies_20261030'
EXTRAS = {'stage_anomaly': ['tc_stage_anom_t2'],
          'wind_anomaly': ['wind_u_anom_t2'],
          'rain_anomaly': ['rain_anom_t2']}


def add_anomalies(frame):
    frame = frame.sort_values('month_start').copy()
    month = frame.month_start.dt.month
    for source, derived in [('tc_stage_t2', 'tc_stage_anom_t2'),
                            ('wind_u_t2', 'wind_u_anom_t2'),
                            ('rainfall_mm', 'rain_anom_t2')]:
        prior = frame.groupby(month)[source].transform(lambda s: s.shift(1).rolling(15, min_periods=5).median())
        frame[derived] = frame[source] - prior
    return frame


def run(delay=5):
    matrix = add_anomalies(load_climate(data_matrix(delay)))
    recent = pd.read_csv(ROOT / f'outputs/ec_extreme_robust_20261029/predictions_{delay}d.csv')
    old = pd.read_csv(ROOT / 'outputs/ec_compact_history_20261029/predictions_2010_2018.csv') if delay == 5 else None
    rows = []
    for _, target in matrix[matrix.month_start.dt.year.between(2010, 2023)].iterrows():
        issue = target.issue_date
        train = matrix[(matrix.month_start < target.month_start) &
                       (matrix.month_start.map(lambda t: available_date_for(t, delay)) <= issue) &
                       (matrix.weather_available_at <= issue)]
        key = target.month_start.strftime('%Y-%m-%d')
        baseline = old if target.month_start.year <= 2018 else recent
        if baseline is None: continue
        base = baseline[baseline.target_month.eq(key)]
        if len(train) < 96 or len(base) != 1 or float(base.iloc[0].actual) != float(target.conductivity_mS_per_m):
            raise ValueError(f'Month mismatch {key}')
        row = dict(target_month=key, actual=float(base.iloc[0].actual),
                   split=('history_2010_2018' if target.month_start.year <= 2018 else
                          'validation_2019_2021' if target.month_start.year <= 2021 else 'retrospective_2022_2023'),
                   RF_compact=float(base.iloc[0].RF_compact))
        for name, extra in EXTRAS.items():
            row[name] = fit_predict('rf', COMPACT + extra, 1.0, train, target)
        rows.append(row)
    frame = pd.DataFrame(rows)
    if len(frame) != (168 if delay == 5 else 60): raise ValueError('Wrong cohort')
    metrics = []
    for split, part in frame.groupby('split'):
        month = pd.to_datetime(part.target_month).dt.month
        for subset, mask in {'all': np.ones(len(part), bool),
                             'dry_dec_apr': month.isin([12, 1, 2, 3, 4]).to_numpy(),
                             'high_ge_100': part.actual.ge(100).to_numpy()}.items():
            if not mask.any(): continue
            for model in ['RF_compact', *EXTRAS]:
                err = part.loc[mask, model].to_numpy() - part.loc[mask, 'actual'].to_numpy()
                metrics.append(dict(split=split, subset=subset, model=model, n=int(mask.sum()),
                                    mae=float(np.abs(err).mean()), rmse=float(np.sqrt(np.mean(err ** 2)))))
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT / f'predictions_{delay}d.csv', index=False)
    metric = pd.DataFrame(metrics)
    metric.to_csv(OUT / f'metrics_{delay}d.csv', index=False)
    print(metric[metric.subset.eq('all')].to_string(index=False))


if __name__ == '__main__': run()
