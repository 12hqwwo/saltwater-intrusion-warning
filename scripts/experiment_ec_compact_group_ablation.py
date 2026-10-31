"""Matched-month as-of grouped feature ablation for My Tho EC prediction."""
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_extreme_robust import COMPACT, fit_predict
from scripts.experiment_ec_long_hydrology import data_matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/ec_compact_group_ablation_20261029'
GROUPS = {'season': ['month_sin', 'month_cos'],
          'rain': ['rainfall_mm'],
          'kratie_q': ['kratie_q_t2', 'kratie_q3_t2', 'kratie_q_ratio_t2'],
          'tan_chau_stage': ['tc_stage_t2', 'tc_stage3_t2']}


def run():
    matrix = data_matrix(5)
    baseline = pd.read_csv(ROOT / 'outputs/ec_extreme_robust_20261029/predictions_5d.csv')
    predictions = []
    for _, target in matrix[matrix.month_start.dt.year.between(2019, 2023)].iterrows():
        issue = target.issue_date
        train = matrix[(matrix.month_start < target.month_start) &
                       (matrix.month_start.map(lambda t: available_date_for(t, 5)) <= issue) &
                       (matrix.weather_available_at <= issue)]
        month = target.month_start.strftime('%Y-%m-%d')
        row = baseline[baseline.target_month.eq(month)]
        if len(train) < 96 or len(row) != 1 or float(row.iloc[0].actual) != float(target.conductivity_mS_per_m):
            raise ValueError(f'Cohort mismatch: {month}')
        result = dict(target_month=month, actual=float(row.iloc[0].actual),
                      split='validation_2019_2021' if target.month_start.year <= 2021 else 'retrospective_2022_2023',
                      RF_compact=float(row.iloc[0].RF_compact))
        for group, dropped in GROUPS.items():
            cols = [col for col in COMPACT if col not in dropped]
            result[f'without_{group}'] = fit_predict('rf', cols, 1.0, train, target)
        predictions.append(result)
    frame = pd.DataFrame(predictions)
    if len(frame) != 60 or frame.target_month.duplicated().any():
        raise ValueError('Expected 60 matched months')
    metrics = []
    for split, part in frame.groupby('split'):
        masks = {'all': np.ones(len(part), dtype=bool),
                 'dry_dec_apr': pd.to_datetime(part.target_month).dt.month.isin([12, 1, 2, 3, 4]).to_numpy(),
                 'high_ge_100': part.actual.ge(100).to_numpy()}
        for subset, mask in masks.items():
            if not mask.any(): continue
            for model in ['RF_compact', *(f'without_{group}' for group in GROUPS)]:
                err = part.loc[mask, model].to_numpy() - part.loc[mask, 'actual'].to_numpy()
                metrics.append(dict(split=split, subset=subset, model=model, n=int(mask.sum()),
                                    mae=float(np.abs(err).mean()), rmse=float(np.sqrt(np.mean(err**2))),
                                    bias=float(err.mean())))
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT / 'predictions.csv', index=False)
    pd.DataFrame(metrics).to_csv(OUT / 'metrics.csv', index=False)
    print(pd.DataFrame(metrics).to_string(index=False))


if __name__ == '__main__': run()
