"""Additional rolling-origin diagnostic for compact RF in 2010-2018.

This is a robustness audit only: historical years have been explored in this
project, so the output is not a new blind test or a basis for retuning.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_extreme_robust import COMPACT, fit_predict
from scripts.experiment_ec_long_hydrology import data_matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/ec_compact_history_20261029"


def main():
    part = data_matrix(5)
    rows=[]
    for _, target in part[part.month_start.dt.year.between(2010,2018)].iterrows():
        issue=target.issue_date
        train=part[(part.month_start<target.month_start)&
                   (part.month_start.map(lambda t:available_date_for(t,5))<=issue)&
                   (part.weather_available_at<=issue)]
        if len(train)<96 or available_date_for(target.weather_month,5)>issue:
            raise ValueError("Unavailable input")
        pred=fit_predict("rf",COMPACT,1.0,train,target)
        same=train[train.month_start.dt.month==target.month_start.month]
        rows.append(dict(target_month=target.month_start.strftime("%Y-%m-%d"),
                         actual=float(target.conductivity_mS_per_m),RF_compact=pred,
                         Persistence=float(train.conductivity_mS_per_m.iloc[-1]),
                         MonthlyClimatology=float(same.conductivity_mS_per_m.mean()),
                         train_n=len(train)))
        if target.month_start.month==12:
            print(target.month_start.year,flush=True)
    frame=pd.DataFrame(rows)
    frame["year"]=pd.to_datetime(frame.target_month).dt.year
    frame["dry"]=pd.to_datetime(frame.target_month).dt.month.isin([12,1,2,3,4])
    frame["high"]=frame.actual.ge(100)
    scores=[]
    for key,mask in [("all",np.ones(len(frame),dtype=bool)),
                     ("dry_dec_apr",frame.dry),("high_ge_100",frame.high)]:
        if not np.any(mask): continue
        group=frame.loc[mask]
        for model in ["RF_compact","Persistence","MonthlyClimatology"]:
            e=group[model]-group.actual
            scores.append(dict(subset=key,model=model,n=len(group),
                               mae=float(e.abs().mean()),rmse=float(np.sqrt(np.mean(e*e)))))
    OUT.mkdir(parents=True,exist_ok=True)
    frame.to_csv(OUT/"predictions_2010_2018.csv",index=False)
    pd.DataFrame(scores).to_csv(OUT/"metrics_2010_2018.csv",index=False)
    print(pd.DataFrame(scores).to_string(index=False))
    print(frame.groupby("year").apply(lambda g:(g.RF_compact-g.actual).abs().mean(),include_groups=False).to_string())


if __name__=="__main__":
    main()
