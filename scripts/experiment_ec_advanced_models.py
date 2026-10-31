"""Small predeclared as-of alternatives to compact RF for My Tho EC.

Research only. Candidates use no historical EC as predictors, so they remain
computable when the latest EC label is years old. Compare on identical months.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_extreme_robust import COMPACT
from scripts.experiment_ec_long_hydrology import data_matrix

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/ec_advanced_20261029'
ANALOG=['month_sin','month_cos','kratie_q_ratio_t2','tc_stage_t2','tc_stage3_t2']
MODELS={
    'RF_fine': (COMPACT, lambda:make_pipeline(SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True),
        RandomForestRegressor(n_estimators=150,max_depth=10,min_samples_leaf=2,max_features=1.0,random_state=42,n_jobs=-1))),
    'ET_fine': (COMPACT, lambda:make_pipeline(SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True),
        ExtraTreesRegressor(n_estimators=150,max_depth=10,min_samples_leaf=2,max_features=1.0,random_state=42,n_jobs=-1))),
    'GB_huber': (COMPACT, lambda:make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),
        GradientBoostingRegressor(loss='huber',alpha=.9,n_estimators=120,max_depth=2,
            learning_rate=.04,min_samples_leaf=8,random_state=42))),
    'KNN_analog': (ANALOG, lambda:make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),
        StandardScaler(),KNeighborsRegressor(n_neighbors=12,weights='distance'))),
}


def run(delay):
    matrix=data_matrix(delay)
    base=pd.read_csv(ROOT/'outputs/ec_extreme_robust_20261029'/f'predictions_{delay}d.csv')
    rows=[]
    for _,target in matrix[matrix.month_start.dt.year.between(2019,2023)].iterrows():
        issue=target.issue_date
        train=matrix[(matrix.month_start<target.month_start)&
                     (matrix.month_start.map(lambda t:available_date_for(t,delay))<=issue)&
                     (matrix.weather_available_at<=issue)]
        key=target.month_start.strftime('%Y-%m-%d')
        matched=base[base.target_month==key]
        if len(train)<96 or len(matched)!=1 or float(matched.iloc[0].actual)!=target.conductivity_mS_per_m:
            raise ValueError('As-of cohort mismatch')
        row=dict(delay_days=delay,target_month=key,split=matched.iloc[0]['split'],
                 issue_date=str(issue),actual=float(target.conductivity_mS_per_m),
                 RF_old=float(matched.iloc[0].RF_old),
                 RF_flow_stage_no_ec=float(matched.iloc[0].RF_flow_stage_no_ec),
                 RF_compact=float(matched.iloc[0].RF_compact),
                 Persistence=float(matched.iloc[0].Persistence),
                 MonthlyClimatology=float(matched.iloc[0].MonthlyClimatology))
        for name,(cols,builder) in MODELS.items():
            model=builder()
            model.fit(train[cols],train.conductivity_mS_per_m)
            row[name]=max(0.,float(model.predict(target[cols].to_frame().T)[0]))
        rows.append(row)
        if target.month_start.month==12: print(delay,target.month_start.year,flush=True)
    pred=pd.DataFrame(rows)
    if len(pred)!=60 or pred.target_month.duplicated().any(): raise ValueError('Expected 60 months')
    metrics=[]
    for split,group in pred.groupby('split'):
        months=pd.to_datetime(group.target_month).dt.month
        for subset,mask in {'all':np.ones(len(group),dtype=bool),
                            'dry_dec_apr':months.isin([12,1,2,3,4]).to_numpy(),
                            'high_ge_100':group.actual.ge(100).to_numpy()}.items():
            if not mask.any(): continue
            for model in ['RF_old','RF_flow_stage_no_ec','RF_compact','Persistence','MonthlyClimatology',*MODELS]:
                error=group.loc[mask,model].to_numpy()-group.loc[mask,'actual'].to_numpy()
                metrics.append(dict(delay_days=delay,split=split,subset=subset,model=model,n=int(mask.sum()),
                                    mae=float(np.abs(error).mean()),rmse=float(np.sqrt(np.mean(error**2)))))
    OUT.mkdir(parents=True,exist_ok=True)
    pred.to_csv(OUT/f'predictions_{delay}d.csv',index=False)
    pd.DataFrame(metrics).to_csv(OUT/f'metrics_{delay}d.csv',index=False)
    (OUT/f'protocol_{delay}d.json').write_text(json.dumps(dict(issue='day 6 of previous month',
        ec_release_delay_days=delay,features={name:cols for name,(cols,_) in MODELS.items()},
        selection='2019-2021 only',retrospective='2022-2023 previously inspected',
        historical_publication_vintages='unavailable',post2023_EC='unavailable'),indent=2),encoding='utf-8')
    print(pd.DataFrame(metrics).query("split=='validation_2019_2021' and subset in ['all','high_ge_100']")[['subset','model','n','mae']].to_string(index=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--delay',type=int,choices=[5,35],required=True)
    run(p.parse_args().delay)
