"""As-of My Tho EC experiment with recent daily Kratie Q and Tan Chau stage.

All feature windows end at issue date minus an explicit assumed source delay.
Historical source-publication vintages are unavailable; results are sensitivity
tests, not a reconstruction of actual issued forecasts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_extreme_robust import COMPACT
from scripts.experiment_ec_long_hydrology import data_matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/ec_issue_daily_hydro_20261030"
Q_PATH = ROOT / "data/external/mrc_kratie_discharge_20261029/014901_Discharge_Calculated daily discharge_22a8130e.csv"
H_PATH = ROOT / "data/external/tien_manual_long_20261029/019803_Water_Level_Manual_3bd17f3a.csv"
QH_COMPACT = ["kratie_q_t2", "kratie_q3_t2", "kratie_q_ratio_t2",
              "tc_stage_t2", "tc_stage3_t2"]
QH_AVAILABLE = [f"available_{name}" for name in QH_COMPACT]
SHORT = ["q_mean_7d", "h_median_7d"]
WINDOWS = ["q_mean_7d", "q_mean_30d", "q_mean_60d", "q_ratio_7_60",
           "h_median_7d", "h_median_30d", "h_median_60d", "h_delta_7_60"]
OTHER = ["month_sin", "month_cos", "rainfall_mm"]


def daily_sources() -> tuple[pd.Series, pd.Series]:
    q = pd.read_csv(Q_PATH, usecols=["observed_at", "value", "unit"])
    h = pd.read_csv(H_PATH, usecols=["observed_at", "value", "unit"])
    if q.unit.ne("m^3/s").any() or h.unit.ne("m").any() or q.value.lt(0).any():
        raise ValueError("Unexpected daily source units/values")
    q["day"] = pd.to_datetime(q.observed_at).dt.tz_localize(None).dt.normalize()
    h["day"] = pd.to_datetime(h.observed_at).dt.tz_localize(None).dt.normalize()
    qday = q.groupby("day").value.mean().sort_index()
    hday = h.groupby("day").value.median().sort_index()
    if qday.index.duplicated().any() or hday.index.duplicated().any():
        raise ValueError("Duplicate daily source dates")
    return qday, hday


def summarize_windows(series: pd.Series, cutoff: pd.Timestamp, kind: str) -> dict:
    values = series.reindex(pd.date_range(cutoff - pd.Timedelta(days=59), cutoff))
    result = {}
    for length, min_valid in ((7, 5), (30, 20), (60, 40)):
        sample = values.iloc[-length:]
        value = sample.mean() if kind == "q" else sample.median()
        result[f"{kind}_{'mean' if kind == 'q' else 'median'}_{length}d"] = (
            float(value) if sample.notna().sum() >= min_valid else np.nan)
        result[f"{kind}_observed_days_{length}d"] = int(sample.notna().sum())
    return result


def add_issue_features(matrix: pd.DataFrame, source_delay: int) -> pd.DataFrame:
    if source_delay not in (5, 35):
        raise ValueError("Only 5 and 35 day source-delay assumptions were predeclared")
    matrix = matrix.sort_values("month_start").copy()
    shift = 0 if source_delay == 5 else 1
    for original, available in zip(QH_COMPACT, QH_AVAILABLE):
        matrix[available] = matrix[original].shift(shift)
    qday, hday = daily_sources()
    window_rows = []
    for issue in matrix.issue_date:
        cutoff = pd.Timestamp(issue) - pd.Timedelta(days=source_delay)
        row = {"hydro_cutoff": cutoff.strftime("%Y-%m-%d")}
        row.update(summarize_windows(qday, cutoff, "q"))
        row.update(summarize_windows(hday, cutoff, "h"))
        q7, q60 = row["q_mean_7d"], row["q_mean_60d"]
        h7, h60 = row["h_median_7d"], row["h_median_60d"]
        row["q_ratio_7_60"] = q7 / q60 if np.isfinite(q7) and np.isfinite(q60) and q60 > 0 else np.nan
        row["h_delta_7_60"] = h7 - h60 if np.isfinite(h7) and np.isfinite(h60) else np.nan
        if cutoff > pd.Timestamp(issue):
            raise ValueError("Hydrology feature after issue date")
        window_rows.append(row)
    windows = pd.DataFrame(window_rows, index=matrix.index)
    matrix = pd.concat([matrix, windows], axis=1)
    return matrix


def fit_predict(train: pd.DataFrame, target: pd.Series, columns: list[str]) -> float:
    model = make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
        RandomForestRegressor(n_estimators=100, max_depth=7, min_samples_leaf=3,
                              max_features=.8, random_state=42, n_jobs=-1),
    )
    model.fit(train[columns], train.conductivity_mS_per_m)
    return max(0.0, float(model.predict(target[columns].to_frame().T)[0]))


def metrics(pred: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    records = []
    for split, part in pred.groupby("split", sort=False):
        months = pd.to_datetime(part.target_month).dt.month
        masks = {"all": np.ones(len(part), bool),
                 "dry_dec_apr": months.isin([12, 1, 2, 3, 4]).to_numpy(),
                 "high_ge_100": part.actual.ge(100).to_numpy()}
        for subset, mask in masks.items():
            if not mask.any():
                continue
            for name in names:
                error = part.loc[mask, name].to_numpy() - part.loc[mask, "actual"].to_numpy()
                records.append(dict(split=split, subset=subset, model=name,
                                    n=int(mask.sum()), mae=float(np.abs(error).mean()),
                                    rmse=float(np.sqrt(np.mean(error ** 2))),
                                    bias=float(error.mean())))
    return pd.DataFrame(records)


def run(ec_delay: int, source_delay: int, start_year: int = 2010) -> None:
    matrix = add_issue_features(data_matrix(ec_delay), source_delay)
    if matrix.month_start.duplicated().any():
        raise ValueError("Duplicate EC target months")
    base = OTHER + QH_AVAILABLE
    candidates = {
        "RF_coarse_available": base,
        "RF_coarse_plus_latest7d": base + SHORT,
        "RF_daily_7_30_60": OTHER + WINDOWS,
    }
    selected = matrix[matrix.month_start.dt.year.between(start_year, 2023)]
    rows = []
    for _, target in selected.iterrows():
        issue = target.issue_date
        train = matrix[(matrix.month_start < target.month_start) &
                       (matrix.month_start.map(lambda t: available_date_for(t, ec_delay)) <= issue) &
                       (matrix.weather_available_at <= issue)]
        if len(train) < 96 or available_date_for(target.weather_month, 5) > issue:
            raise ValueError("As-of labels/weather not satisfied")
        split = ("development_2010_2018" if target.month_start.year <= 2018 else
                 "validation_2019_2021" if target.month_start.year <= 2021 else
                 "retrospective_2022_2023")
        row = dict(ec_delay_days=ec_delay, source_delay_days=source_delay,
                   target_month=target.month_start.strftime("%Y-%m-%d"),
                   issue_date=str(issue), hydro_cutoff=target.hydro_cutoff,
                   split=split, actual=float(target.conductivity_mS_per_m), train_n=len(train))
        for name, columns in candidates.items():
            row[name] = fit_predict(train, target, columns)
        for feature in WINDOWS:
            row[feature] = target[feature]
        rows.append(row)
        if target.month_start.month == 12:
            print(ec_delay, source_delay, target.month_start.year, flush=True)
    pred = pd.DataFrame(rows)
    if len(pred) != (2024 - start_year) * 12 or pred.target_month.duplicated().any():
        raise ValueError("Unmatched monthly cohort")
    for delay in (ec_delay,):
        basepath = ROOT / "outputs/ec_extreme_robust_20261029" / f"predictions_{delay}d.csv"
        reference = pd.read_csv(basepath).set_index("target_month")
        check = pred[pred.split != "development_2010_2018"].set_index("target_month")
        if not np.allclose(check.actual, reference.loc[check.index, "actual"]):
            raise ValueError("Different evaluation labels/cohort")
        if source_delay == 5:
            err = np.abs(check.RF_coarse_available.to_numpy() - reference.loc[check.index, "RF_compact"].to_numpy())
            if err.max() > 1e-8:
                raise ValueError(f"Primary compact replication mismatch: max {err.max()}")
    score = metrics(pred, list(candidates))
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"ec{ec_delay}_hydro{source_delay}"
    pred.to_csv(OUT / f"predictions_{stem}.csv", index=False)
    score.to_csv(OUT / f"metrics_{stem}.csv", index=False)
    (OUT / f"protocol_{stem}.json").write_text(json.dumps(dict(
        ec_release_delay_days=ec_delay, hydro_release_delay_days=source_delay,
        issue="day 6 of previous month", source_cutoff="issue minus hydro_release_delay_days",
        source_window_days=[7, 30, 60], source_window_min_valid_days=[5, 20, 40],
        coarse_hydrology_month="t-2 if hydro delay 5d, t-3 if hydro delay 35d",
        weather_month="t-2, assumed released end of source month +5d",
        selection="development_2010_2018 only; historical period previously inspected",
        validation="2019-2021; previously inspected",
        retrospective="2022-2023; previously inspected; no high-EC months",
        historical_publication_vintages="unavailable",
        target="single My Tho EC sample in target month, mS/m; not monthly mean",
        models=candidates), indent=2), encoding="utf-8")
    print(score.to_string(index=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ec-delay", type=int, choices=[5, 35], required=True)
    parser.add_argument("--source-delay", type=int, choices=[5, 35], required=True)
    parser.add_argument("--start-year", type=int, choices=[2010, 2019], default=2010)
    args = parser.parse_args()
    run(args.ec_delay, args.source_delay, args.start_year)
