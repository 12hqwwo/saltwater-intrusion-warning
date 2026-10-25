"""Separate exploratory hydrological ablations on matched available-data cohorts."""
from __future__ import annotations

import pandas as pd

from research_ec_features import BASE, OUT, evaluate_year, metrics, month_end, paired_gain, save_json


def main():
    data = pd.read_csv(OUT / "feature_matrix.csv", parse_dates=["target_month"])
    data = data[data.ec_delay_days.eq(0)].copy()
    data["target_available"] = pd.to_datetime([month_end(t) for t in data.target_month])
    studies = []
    for station in ["MYTHO", "TANCHAU"]:
        studies.append((station, "GFZ_TANCHAU_UPSTREAM_PROXY", ["gfz_tanchau_q_lag2_m3s", "gfz_tanchau_q_mean3_m3s"], range(2010, 2017), 96))
        studies.append((station, "VUNGTAU_DAILY_MAX_PROXY", ["vungtau_daily_max_mean30_m"], range(2014, 2020), 96))
        studies.append((station, "DAHITI_LOCAL_PROXY", ["dahiti_latest_m", "dahiti_age_days"], range(2018, 2024) if station == "MYTHO" else range(2010, 2017), 48))
    studies.append(("TANCHAU", "GLOFAS_SUSPECT_CELL", ["glofas_q_lag4_m3s"], range(2014, 2020), 96))
    rows, summary = [], []
    for station, study, extra, years, minimum in studies:
        part = data[data.station.eq(station)].dropna(subset=extra).copy()
        if study.startswith("GFZ"):
            part = part[part.target_month.ge("1996-05-01") & part.gfz_source_kind.eq("REPORTED_GAUGE_MONTHLY")]
        records = []
        for year in years:
            for algorithm in ["RF", "RIDGE_LOG"]:
                for name, features in [("BASE", BASE), ("PLUS", BASE + extra)]:
                    result, _ = evaluate_year(part, year, algorithm, name, features, study, min_train=minimum)
                    records.extend(result)
        if not records:
            summary.append(dict(station=station, study=study, status="INSUFFICIENT_DATA")); continue
        frame = pd.DataFrame(records); frame["study"] = study
        rows.extend(frame.to_dict("records"))
        for algorithm in ["RF", "RIDGE_LOG"]:
            base = frame[frame.algorithm.eq(algorithm) & frame.configuration.eq("BASE")]
            plus = frame[frame.algorithm.eq(algorithm) & frame.configuration.eq("PLUS")]
            assert tuple(base.target_month) == tuple(plus.target_month)
            b, p = metrics(base), metrics(plus)
            summary.append(dict(station=station, study=study, algorithm=algorithm, status="EXPLORATORY_SPATIAL_AND_RELEASE_ASSUMPTIONS",
                                start=str(plus.target_month.min().date()), end=str(plus.target_month.max().date()),
                                n=p["n"], minimum_train=minimum, base_mae=b["mae"], plus_mae=p["mae"],
                                gain_pct=100*(b["mae"]-p["mae"])/b["mae"], **paired_gain(plus, base)))
        print(f"Completed {station} {study}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "hydrology_predictions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(summary).to_csv(OUT / "hydrology_metrics.csv", index=False, encoding="utf-8-sig")
    save_json(OUT / "hydrology_protocol.json", dict(
        status="Exploratory separate cohorts; never used to select primary model",
        gfz="Gauge period only from 1996; Tanchau upstream discharge proxy for MyTho, not local flow. Source ends 2016.",
        dahiti="Latest observation assumed available after 30 days, discarded after 90 days old. Sparse proxy; min_train=48.",
        tide="Mean of Vung Tau daily sea-level maxima, NOT tidal range or gate tide; assumed 90-day latency.",
        glofas="Existing Tanchau cell remains SUSPECT; lag 4 plus exact 90-day availability mask. No MyTho imputation from Tanchau.",
        caveat="Different time cohorts cannot be ranked against primary validation or each other. Historical source vintages are unavailable."))


if __name__ == "__main__":
    main()
