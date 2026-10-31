"""As-of EC ablation of astronomical tide × antecedent freshwater flow.

FES is deterministic at forecast issue. The Q proxy is from t-2, never the
target month. This tests prediction, not physical salt travel time.
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
FES = ROOT / 'outputs/fes_ec_offshore_sensitivity_20261026/fes_features_1985_2026.csv'
OUT = ROOT / 'outputs/ec_tide_flow_interaction_20261029'
TIDE = 'fes_south_midmonth_range_cm'
VARIANTS = {
    'RF_compact': COMPACT,
    'RF_compact_fes': COMPACT + [TIDE],
    'RF_compact_fes_flow': COMPACT + [TIDE, 'tide_x_low_q'],
}


def run(delay, history=False):
    matrix = data_matrix(delay)
    tide = pd.read_csv(FES, usecols=['month_start', TIDE], parse_dates=['month_start'])
    if tide.month_start.duplicated().any() or tide[TIDE].isna().any():
        raise ValueError('FES monthly keys/values invalid')
    matrix = matrix.merge(tide, on='month_start', how='left', validate='one_to_one')
    # Multiplication makes a hypothesis about joint forcing, not a travel law.
    matrix['tide_x_low_q'] = matrix[TIDE] / matrix['kratie_q_ratio_t2'].clip(lower=.25)
    if history:
        if delay != 5:
            raise ValueError('2010–2018 history was saved only for +5 days')
        old = pd.read_csv(ROOT / 'outputs/ec_compact_history_20261029/predictions_2010_2018.csv')
        targets = matrix[matrix.month_start.dt.year.between(2010, 2018)]
    else:
        old = pd.read_csv(ROOT / 'outputs/ec_extreme_robust_20261029' / f'predictions_{delay}d.csv')
        targets = matrix[matrix.month_start.dt.year.between(2019, 2023)]
    rows = []
    for _, target in targets.iterrows():
        issue = target.issue_date
        train = matrix[(matrix.month_start < target.month_start) &
                       (matrix.month_start.map(lambda t: available_date_for(t, delay)) <= issue) &
                       (matrix.weather_available_at <= issue)]
        key = target.month_start.strftime('%Y-%m-%d')
        check = old[old.target_month.eq(key)]
        if len(train) < 96 or len(check) != 1 or float(check.iloc[0].actual) != float(target.conductivity_mS_per_m):
            raise ValueError(f'as-of cohort mismatch: {key}')
        row = dict(target_month=key, issue_date=str(issue), actual=float(target.conductivity_mS_per_m),
                   split=('history_2010_2018' if history else
                          'validation_2019_2021' if target.month_start.year <= 2021 else 'retrospective_2022_2023'),
                   RF_compact=float(check.iloc[0].RF_compact))
        for name in ('RF_compact_fes', 'RF_compact_fes_flow'):
            row[name] = fit_predict('rf', VARIANTS[name], 1.0, train, target)
        rows.append(row)
    pred = pd.DataFrame(rows)
    if len(pred) != (108 if history else 60) or pred.target_month.duplicated().any():
        raise ValueError('Wrong matched monthly cohort')
    metrics = []
    month = pd.to_datetime(pred.target_month).dt.month
    for split, part in pred.groupby('split'):
        for subset, mask in {'all': np.ones(len(part), dtype=bool),
                             'dry_dec_apr': month.loc[part.index].isin([12, 1, 2, 3, 4]).to_numpy(),
                             'high_ge_100': part.actual.ge(100).to_numpy()}.items():
            if not mask.any():
                continue
            for name in VARIANTS:
                err = part.loc[mask, name].to_numpy() - part.loc[mask, 'actual'].to_numpy()
                metrics.append(dict(split=split, subset=subset, model=name, n=int(mask.sum()),
                                    mae=float(np.abs(err).mean()), rmse=float(np.sqrt(np.mean(err**2))),
                                    bias=float(err.mean())))
    OUT.mkdir(parents=True, exist_ok=True)
    suffix = 'history_2010_2018' if history else f'{delay}d'
    pred.to_csv(OUT / f'predictions_{suffix}.csv', index=False)
    pd.DataFrame(metrics).to_csv(OUT / f'metrics_{suffix}.csv', index=False)
    print(pd.DataFrame(metrics).to_string(index=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--delay', type=int, choices=[5, 35], required=True)
    parser.add_argument('--history', action='store_true')
    args = parser.parse_args()
    run(args.delay, args.history)
