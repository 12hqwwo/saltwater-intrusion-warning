"""Descriptive EC feature associations, with season-adjusted sensitivity.

These are not causal effects or a feature-selection score by themselves.
"""
from pathlib import Path
import pandas as pd
from scipy.stats import spearmanr
from scripts.experiment_ec_feature_enhanced import load_climate
from scripts.experiment_ec_long_hydrology import data_matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/ec_feature_association_20261030'
FEATURES = ['wind_u_t2', 'wind_v_t2', 'kratie_q_t2', 'kratie_q_ratio_t2',
            'rainfall_mm', 'tc_stage_t2', 'oni_lag3']


def correlation(frame, feature):
    part = frame[['conductivity_mS_per_m', feature, 'month']].dropna()
    if len(part) < 30: return None
    raw = spearmanr(part[feature], part.conductivity_mS_per_m).statistic
    # Remove each calendar month's median from both variables before ranking.
    x = part[feature] - part.groupby('month')[feature].transform('median')
    y = part.conductivity_mS_per_m - part.groupby('month').conductivity_mS_per_m.transform('median')
    adjusted = spearmanr(x, y).statistic
    return len(part), float(raw), float(adjusted)


def run():
    data = load_climate(data_matrix(5))
    data['month'] = data.month_start.dt.month
    rows = []
    for period, frame in [('development_1985_2018', data[data.month_start.dt.year <= 2018]),
                          ('recent_2019_2023', data[data.month_start.dt.year >= 2019])]:
        for subset, part in [('all', frame), ('dry_dec_apr', frame[frame.month.isin([12, 1, 2, 3, 4])])]:
            for feature in FEATURES:
                result = correlation(part, feature)
                if result:
                    n, raw, adjusted = result
                    rows.append(dict(period=period, subset=subset, feature=feature, n=n,
                                     spearman_raw=raw, spearman_month_median_removed=adjusted))
    OUT.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(rows)
    table.to_csv(OUT / 'associations.csv', index=False)
    print(table.to_string(index=False))


if __name__ == '__main__': run()
