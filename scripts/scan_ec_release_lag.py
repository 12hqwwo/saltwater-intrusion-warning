"""Sensitivity of My Tho EC backtest to assumed label-publication lag.

Lag is a source-availability assumption, not a model hyperparameter or a
forecast horizon. Fits are cached when multiple lag days yield identical
available training labels for the same issue date.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_extreme_robust import COMPACT, fit_predict
from scripts.experiment_ec_long_hydrology import data_matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/ec_release_lag_scan_20261030'


def run(max_delay=70):
    matrix = data_matrix(5)
    targets = matrix[matrix.month_start.dt.year.between(2019, 2023)]
    if len(targets) != 60:
        raise ValueError('Expected 60 target months')
    saved = {}
    rows = []
    for _, target in targets.iterrows():
        month = target.month_start.strftime('%Y-%m-%d')
        issue = target.issue_date
        eligible = matrix[(matrix.month_start < target.month_start) &
                          (matrix.weather_available_at <= issue)].copy()
        if available_date_for(target.weather_month, 5) > issue:
            raise ValueError('Target weather unavailable')
        for delay in range(max_delay + 1):
            train = eligible[eligible.month_start.map(lambda t: available_date_for(t, delay) <= issue)]
            if len(train) < 96:
                raise ValueError(f'Too few labels: {month}, +{delay}')
            last = train.month_start.iloc[-1]
            key = (month, str(last), len(train))
            if key not in saved:
                saved[key] = fit_predict('rf', COMPACT, 1.0, train, target)
            same = train[train.month_start.dt.month.eq(target.month_start.month)]
            rows.append(dict(delay_days=delay, target_month=month, issue_date=str(issue),
                             split='validation_2019_2021' if target.month_start.year <= 2021 else 'retrospective_2022_2023',
                             actual=float(target.conductivity_mS_per_m), train_n=len(train),
                             latest_training_month=last.strftime('%Y-%m'),
                             RF_compact=saved[key], Persistence=float(train.conductivity_mS_per_m.iloc[-1]),
                             MonthlyClimatology=float(same.conductivity_mS_per_m.mean())))
    pred = pd.DataFrame(rows)
    if len(pred) != 60 * (max_delay + 1) or pred.duplicated(['delay_days', 'target_month']).any():
        raise ValueError('Invalid prediction grid')
    # Reproduction check against the already published +5/+35 artifacts.
    for delay in (5, 35):
        if delay > max_delay: continue
        old = pd.read_csv(ROOT / f'outputs/ec_extreme_robust_20261029/predictions_{delay}d.csv')
        match = pred[pred.delay_days.eq(delay)].merge(old[['target_month', 'actual', 'RF_compact', 'Persistence']],
                                                    on='target_month', suffixes=('_scan', '_old'), validate='one_to_one')
        for field in ['actual', 'RF_compact', 'Persistence']:
            if len(match) != 60 or not np.allclose(match[f'{field}_scan'], match[f'{field}_old'], atol=1e-8):
                raise ValueError(f'Failed to reproduce +{delay} {field}')
    scores = []
    for (delay, split), part in pred.groupby(['delay_days', 'split']):
        months = pd.to_datetime(part.target_month).dt.month
        masks = {'all': np.ones(len(part), dtype=bool),
                 'dry_dec_apr': months.isin([12, 1, 2, 3, 4]).to_numpy(),
                 'high_ge_100': part.actual.ge(100).to_numpy()}
        for subset, mask in masks.items():
            if not mask.any(): continue
            group = part.loc[mask]
            for model in ['RF_compact', 'Persistence', 'MonthlyClimatology']:
                e = group[model].to_numpy() - group.actual.to_numpy()
                scores.append(dict(delay_days=delay, split=split, subset=subset, model=model,
                                   n=len(group), mae=float(np.abs(e).mean()),
                                   rmse=float(np.sqrt(np.mean(e ** 2))), bias=float(e.mean())))
    OUT.mkdir(parents=True, exist_ok=True)
    pred.to_csv(OUT / 'predictions.csv', index=False)
    metric = pd.DataFrame(scores)
    metric.to_csv(OUT / 'metrics.csv', index=False)
    print('model fits', len(saved), 'of', len(rows), 'forecast rows')
    print(metric[(metric.subset.eq('all')) & metric.model.eq('RF_compact')].pivot(index='delay_days', columns='split', values='mae').round(3).to_string())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-delay', type=int, default=70)
    args = parser.parse_args()
    if not 35 <= args.max_delay <= 120: raise ValueError('max-delay must be 35–120')
    run(args.max_delay)
