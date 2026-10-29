"""Development-selected dry-season blend, gated by latest EC age.

Uses the root project's as-of 2010-2018 compact/persistence hindcasts to choose
a fixed RF weight. +35-day release scenario is a sensitivity check only.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.experiment_ec_long_hydrology import data_matrix

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/ec_advanced_20261029'
HISTORY=ROOT/'outputs/ec_compact_history_20261029/predictions_2010_2018.csv'
GRID=[0,.25,.5,.75,1]


def predict(frame,rf_weight,age=None):
    months=pd.to_datetime(frame.target_month).dt.month
    use=months.isin([12,1,2,3,4]).to_numpy()
    if age is not None: use=use & (np.asarray(age)<=3)
    return np.where(use,rf_weight*frame.RF_compact+(1-rf_weight)*frame.Persistence,
                    frame.RF_compact)


def score(frame,estimate):
    dry=pd.to_datetime(frame.target_month).dt.month.isin([12,1,2,3,4]).to_numpy()
    high=frame.actual.ge(100).to_numpy()
    err=np.asarray(estimate)-frame.actual.to_numpy()
    return dict(n=len(frame),mae=float(np.abs(err).mean()),
                dry_n=int(dry.sum()),dry_mae=float(np.abs(err[dry]).mean()),
                high_n=int(high.sum()),high_mae=float(np.abs(err[high]).mean()) if high.any() else None)


def main():
    dev=pd.read_csv(HISTORY)
    if len(dev)!=108 or dev.target_month.duplicated().any():
        raise ValueError('Unexpected early development cohort')
    grid=[dict(rf_weight=w,**score(dev,predict(dev,w))) for w in GRID]
    selected=min(grid,key=lambda row:(row['mae'],row['rf_weight']))['rf_weight']
    if selected!=.25: raise ValueError('Development selection changed')
    OUT.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(grid).to_csv(OUT/'dry_blend_development_grid.csv',index=False)
    combined=[]; scores=[]
    for delay in (5,35):
        p=pd.read_csv(OUT/f'predictions_{delay}d.csv')
        matrix=data_matrix(delay)
        age=matrix[matrix.month_start.dt.year.between(2019,2023)][['month_start','ec_age_months']].copy()
        age['target_month']=age.month_start.dt.strftime('%Y-%m-%d')
        p=p.merge(age[['target_month','ec_age_months']],on='target_month',validate='one_to_one')
        p['dry_blend']=predict(p,selected,p.ec_age_months)
        for split,part in p.groupby('split'):
            for name in ('RF_compact','Persistence','dry_blend'):
                scores.append(dict(delay_days=delay,split=split,model=name,
                                   **score(part,part[name])))
        combined.append(p)
    pd.concat(combined,ignore_index=True).to_csv(OUT/'dry_blend_predictions.csv',index=False)
    pd.DataFrame(scores).to_csv(OUT/'dry_blend_metrics.csv',index=False)
    (OUT/'dry_blend_protocol.json').write_text(json.dumps(dict(
        development='2010-2018 rolling as-of +5d, previously inspected',
        weight_grid=GRID,selected_rf_weight=selected,
        rule='December-April and known EC age <=3 months: .25 RF_compact+.75 Persistence; otherwise RF_compact',
        selection='development overall MAE only; 2019-2021 and 2022-2023 inspected as evaluations',
        limitation='No 2024+ EC for current release. As-of age >3 months forces RF fallback; no new extreme-event independent check'),
        indent=2),encoding='utf-8')
    print('selected',selected); print(pd.DataFrame(scores).to_string(index=False))


if __name__=='__main__':main()
