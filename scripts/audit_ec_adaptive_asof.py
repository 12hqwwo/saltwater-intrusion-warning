"""Re-score adaptive EC candidates against matched, issue-time baselines.

Historical Q50/Q90 are percentiles across tree predictions, not calibrated
conditional quantiles. No 2022-2023 results are used to tune the risk rule.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer

from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_feature_enhanced import load_climate
from scripts.experiment_ec_final_candidates import COMPACT
from scripts.experiment_ec_long_hydrology import data_matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/ec_adaptive_asof_audit_20261030'


def risk_weight(frame):
    month = pd.to_datetime(frame.target_month).dt.month
    q = frame.kratie_q_t2
    oni = frame.oni_lag3
    if q.isna().any() or oni.isna().any():
        raise ValueError('Risk rule requires Q and ONI known under lag assumption')
    stress = 1 - (q.clip(1500, 4000) - 1500) / 2500
    weight = .4 * stress + .3 * oni.clip(0, 2) / 2 + .3
    return np.where(month.isin([12, 1, 2, 3, 4, 5]), weight.clip(0, .85), 0.)


def metrics(frame, label):
    rows = []
    names = ['RF_compact_asof', 'Persistence_asof', 'tree_q50', 'tree_q90', 'adaptive_q50_q90']
    for split, group in frame.groupby('split'):
        m = pd.to_datetime(group.target_month).dt.month
        for subset, mask in {'all': np.ones(len(group), bool),
                             'dry_dec_apr': m.isin([12, 1, 2, 3, 4]).to_numpy(),
                             'high_ge_100': group.actual.ge(100).to_numpy()}.items():
            if not mask.any(): continue
            for model in names:
                error = group.loc[mask, model].to_numpy() - group.loc[mask, 'actual'].to_numpy()
                rows.append(dict(cohort=label, split=split, subset=subset, model=model,
                                 n=int(mask.sum()), mae=float(np.abs(error).mean()),
                                 rmse=float(np.sqrt(np.mean(error ** 2))), bias=float(error.mean())))
    return pd.DataFrame(rows)


def score_recent(delay):
    p = pd.read_csv(ROOT / f'outputs/ec_final_candidates_20261029/predictions_{delay}d.csv')
    b = pd.read_csv(ROOT / f'outputs/ec_extreme_robust_20261029/predictions_{delay}d.csv')
    matrix = load_climate(data_matrix(delay))
    matrix['target_month'] = matrix.month_start.dt.strftime('%Y-%m-%d')
    frame = p.merge(b[['target_month', 'actual', 'RF_compact', 'Persistence', 'issue_date']],
                    on='target_month', suffixes=('_candidate', '_asof'), validate='one_to_one')
    frame = frame.merge(matrix[['target_month', 'kratie_q_t2', 'oni_lag3']],
                        on='target_month', validate='one_to_one')
    if len(frame) != 60 or not np.allclose(frame.actual_candidate, frame.actual_asof):
        raise ValueError('Recent cohorts or actuals differ')
    if not (pd.to_datetime(frame.issue_date) ==
            pd.to_datetime(frame.target_month) - pd.DateOffset(months=1) + pd.Timedelta(days=5)).all():
        raise ValueError('Unexpected issue dates')
    frame = frame.rename(columns={'actual_candidate': 'actual', 'RF_compact_q50': 'tree_q50',
                                  'RF_compact_q90': 'tree_q90'})
    frame['risk_weight'] = risk_weight(frame)
    frame['adaptive_q50_q90'] = (1 - frame.risk_weight) * frame.tree_q50 + frame.risk_weight * frame.tree_q90
    return frame


def historical_tree_heads():
    matrix = load_climate(data_matrix(5))
    trusted = pd.read_csv(ROOT / 'outputs/ec_compact_history_20261029/predictions_2010_2018.csv')
    rows = []
    for _, target in matrix[matrix.month_start.dt.year.between(2010, 2018)].iterrows():
        issue = target.issue_date
        train = matrix[(matrix.month_start < target.month_start) &
                       (matrix.month_start.map(lambda t: available_date_for(t, 5)) <= issue) &
                       (matrix.weather_available_at <= issue)]
        month = target.month_start.strftime('%Y-%m-%d')
        base = trusted[trusted.target_month.eq(month)]
        if len(train) < 96 or len(base) != 1 or float(base.iloc[0].actual) != float(target.conductivity_mS_per_m):
            raise ValueError(f'Historical cohort mismatch {month}')
        imp = SimpleImputer(strategy='median', add_indicator=True, keep_empty_features=True)
        x = imp.fit_transform(train[COMPACT])
        xt = imp.transform(target[COMPACT].to_frame().T)
        rf = RandomForestRegressor(n_estimators=300, max_depth=8, min_samples_leaf=2,
                                   max_features=.7, random_state=42, n_jobs=-1)
        rf.fit(x, train.conductivity_mS_per_m)
        trees = np.array([est.predict(xt)[0] for est in rf.estimators_])
        rows.append(dict(target_month=month, split='history_2010_2018', actual=float(base.iloc[0].actual),
                         RF_compact_asof=float(base.iloc[0].RF_compact),
                         Persistence_asof=float(base.iloc[0].Persistence),
                         tree_q50=float(np.percentile(trees, 50)), tree_q90=float(np.percentile(trees, 90)),
                         kratie_q_t2=float(target.kratie_q_t2), oni_lag3=float(target.oni_lag3)))
    frame = pd.DataFrame(rows)
    if len(frame) != 108: raise ValueError('Expected 108 historical months')
    frame['risk_weight'] = risk_weight(frame)
    frame['adaptive_q50_q90'] = (1 - frame.risk_weight) * frame.tree_q50 + frame.risk_weight * frame.tree_q90
    return frame


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    all_metrics = []
    for delay in (5, 35):
        recent = score_recent(delay)
        recent.to_csv(OUT / f'predictions_{delay}d.csv', index=False)
        all_metrics.append(metrics(recent, f'recent_{delay}d'))
    history = historical_tree_heads()
    history.to_csv(OUT / 'predictions_history_2010_2018.csv', index=False)
    all_metrics.append(metrics(history, 'history_5d'))
    result = pd.concat(all_metrics, ignore_index=True)
    result.to_csv(OUT / 'metrics.csv', index=False)
    print(result[result.subset.eq('all')][['cohort', 'split', 'model', 'n', 'mae']].to_string(index=False))


if __name__ == '__main__': run()
