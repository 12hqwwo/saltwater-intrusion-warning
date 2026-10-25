"""Reproducible, isolated monthly EC feature research; never modifies the web app.

Build: python scripts/research_ec_features.py prepare
Compare: python scripts/research_ec_features.py evaluate
Inputs are retrospective snapshots. Release delays are explicit assumptions,
not evidence that today's revised data existed at the historical issue time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/ec_feature_research_20261019"
EXTERNAL = ROOT / "data/external/ec_feature_research_20261019"
STATIONS = {"MYTHO": "MyTho", "TANCHAU": "TanChau"}
SEASON = ["month_sin", "month_cos"]
EC = ["ec_latest", "ec_previous", "ec_age_months", "ec_lag12", "ec_mean3", "ec_mean12"]
BASIC = ["rain_30d_mm", "temperature_30d_c", "wind_max_30d_source_units"]
GROUPS = {
    "rain_memory": ["rain_90d_mm", "dry_days_90d", "longest_dry_run_90d"],
    "water_balance": ["et0_30d_mm", "p_minus_et0_90d_mm"],
    "humidity_radiation": ["humidity_30d_pct", "radiation_30d_mj_m2", "temperature_range_30d_c"],
    "soil_moisture": ["soil_moisture_30d_m3_m3"],
    "wind_direction": ["wind_u_proxy_30d_ms", "wind_v_proxy_30d_ms"],
    "enso": ["nino34_lag2_c", "nino34_lag3_c", "nino34_lag6_c", "nino34_trailing3_c"],
}
BASE = SEASON + EC + BASIC
ALL_FEATURES = BASE + [c for cols in GROUPS.values() for c in cols]
CONFIGS = {"AR": SEASON + EC, "BASE": BASE,
           **{"PLUS_" + g: BASE + cols for g, cols in GROUPS.items()},
           "ALL": ALL_FEATURES,
           **{"MINUS_" + g: [c for c in ALL_FEATURES if c not in cols] for g, cols in GROUPS.items()}}
PROTOCOL = {
    "version": 1, "research_date": "2026-10-19", "target": "Monthly EC sample value, mS/m; not monthly maximum or salinity",
    "issue_time": "23:59:59 Asia/Ho_Chi_Minh on the final day of the previous calendar month",
    "data_status": "Retrospective revised snapshots, source EC UNVERIFIED; not live operational validation",
    "primary_ec_delay_days": 0, "sensitivity_ec_delay_days": 30,
    "weather_delay_days": 5, "enso_delay_days": 30, "dahiti_delay_days": 30,
    "dahiti_max_observation_age_days": 90, "tide_proxy_delay_days": 90, "glofas_consolidated_delay_days": 90,
    "gfz_discharge_delay_days": 30, "availability_warning": "Except current weather provider latency, release delays are unverified research assumptions. Final ERA5/ERSST snapshots are not historical vintages.",
    "validation_years": list(range(2014, 2020)), "retrospective_holdout_years": list(range(2020, 2024)),
    "refit": "Expanding training at January issue time; model frozen for that year, features update monthly using only assumed available inputs",
    "training_start": "1986-01", "minimum_training_labels": 96,
    "algorithms": {"RF": {"trees": 120, "max_depth": 6, "min_samples_leaf": 5, "seed": 42}, "RIDGE_LOG": {"alpha": 10}},
    "preprocessing": "Median imputation with missing indicators and scaling learned on training only; no EC outlier deletion based on full-series statistics",
    "selection": "Lowest pooled validation MAE over baseline and candidate configurations; holdout not used to select",
    "feature_acceptance_screen": "At least 5% validation MAE gain vs same-algorithm BASE, improvement in >=4/6 years, paired 12-month-block bootstrap 95% gain interval >0; exploratory, not multiple-testing corrected",
    "feature_importance": "Add-one-group and drop-one-group retraining; grouped circular shifts on validation only, diagnostic under dependent inputs",
    "metrics": ["MAE", "RMSE", "bias", "dry_season_MAE_Dec_Apr", "high_EC_MAE_training_p90", "coverage"],
    "limitations": ["No causal attribution", "Previously viewed historical test periods cannot be called a fresh blind test", "No EC-to-salinity conversion", "No gate-specific prediction", "Do not compare metrics with old filtered-label runs"],
    "configurations": CONFIGS,
}


def save_json(path, obj):
    def clean(v):
        if isinstance(v, dict): return {str(k): clean(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)): return [clean(x) for x in v]
        if isinstance(v, (np.integer, np.floating)): return clean(v.item())
        if isinstance(v, float) and not np.isfinite(v): return None
        if isinstance(v, (pd.Timestamp, datetime)): return v.isoformat()
        return v
    path.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def month_end(t):
    return pd.Timestamp(t) + pd.offsets.MonthBegin(1) - pd.Timedelta(seconds=1)


def longest_dry(values):
    longest = count = 0
    for v in values:
        count = count + 1 if v < 1 else 0
        longest = max(longest, count)
    return longest


def daily_features(weather, extra, dates):
    w = weather.set_index("date").sort_index()
    if w.index.has_duplicates: raise ValueError("Duplicate weather dates")
    daily_index = pd.date_range(w.index.min(), w.index.max(), freq="D")
    if not w.index.equals(daily_index): raise ValueError("Daily weather calendar has gaps")
    if extra.get("utc_offset_seconds") != 25200: raise ValueError("Wrong ERA5 daily timezone")
    if extra["daily_units"]["soil_moisture_0_to_100cm_mean"] != "m\u00b3/m\u00b3": raise ValueError("Wrong soil moisture unit")
    if extra["daily_units"]["wind_speed_10m_mean"] != "m/s": raise ValueError("Wrong wind unit")
    e = pd.DataFrame(extra["daily"])
    e["date"] = pd.to_datetime(e.pop("time"))
    e = e.set_index("date")
    if not e.index.equals(daily_index): raise ValueError("ERA5 extra calendar mismatch")
    w = w.join(e, validate="one_to_one")
    direction = np.deg2rad(w.wind_direction_10m_dominant)
    w["u_proxy"] = -w.wind_speed_10m_mean * np.sin(direction)
    w["v_proxy"] = -w.wind_speed_10m_mean * np.cos(direction)
    w["p_minus_et0"] = w.precipitation_sum - w.et0_fao_evapotranspiration
    w["temperature_range"] = w.temperature_2m_max - w.temperature_2m_min
    definitions = {
        "rain_30d_mm": ("precipitation_sum", 30, "sum"), "rain_90d_mm": ("precipitation_sum", 90, "sum"),
        "temperature_30d_c": ("temperature_2m_mean", 30, "mean"), "wind_max_30d_source_units": ("windspeed_10m_max", 30, "mean"),
        "et0_30d_mm": ("et0_fao_evapotranspiration", 30, "sum"), "p_minus_et0_90d_mm": ("p_minus_et0", 90, "sum"),
        "humidity_30d_pct": ("relative_humidity_2m_mean", 30, "mean"), "radiation_30d_mj_m2": ("shortwave_radiation_sum", 30, "sum"),
        "temperature_range_30d_c": ("temperature_range", 30, "mean"), "soil_moisture_30d_m3_m3": ("soil_moisture_0_to_100cm_mean", 30, "mean"),
        "wind_u_proxy_30d_ms": ("u_proxy", 30, "mean"), "wind_v_proxy_30d_ms": ("v_proxy", 30, "mean"),
    }
    rolled = pd.DataFrame(index=w.index)
    for name, (col, window, operation) in definitions.items():
        rolled[name] = getattr(w[col].rolling(window, min_periods=window), operation)()
    rolled["dry_days_90d"] = w.precipitation_sum.lt(1).astype(float).rolling(90, min_periods=90).sum()
    rolled["longest_dry_run_90d"] = w.precipitation_sum.rolling(90, min_periods=90).apply(longest_dry, raw=True)
    # Full local days only: a day ending at 23:59 plus five days must precede issue time.
    cutoffs = dates - pd.Timedelta(days=6)
    result = rolled.reindex(cutoffs).set_axis(dates)
    result["weather_observed_through"] = cutoffs.strftime("%Y-%m-%d")
    result["weather_assumed_available_at"] = (cutoffs + pd.Timedelta(days=6) - pd.Timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S+07:00")
    return result


def parse_nino():
    source = (EXTERNAL / "noaa_nino34_anomaly.txt").read_text(encoding="utf-8-sig")
    rows = []
    for line in source.splitlines():
        parts = line.split()
        if len(parts) == 13 and parts[0].isdigit() and 1800 <= int(parts[0]) <= 2200:
            for m, text in enumerate(parts[1:], 1):
                value = float(text)
                rows.append(dict(month=pd.Timestamp(int(parts[0]), m, 1), nino34_c=value if value > -90 else np.nan))
    frame = pd.DataFrame(rows).set_index("month")
    if frame.index.has_duplicates or frame.empty: raise ValueError("Invalid NOAA calendar")
    frame.to_csv(OUT / "noaa_nino34_monthly.csv", encoding="utf-8-sig")
    return frame.nino34_c, source.splitlines()[-9:]


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    save_json(OUT / "protocol.json", PROTOCOL)
    source_paths = [ROOT / "data/research/mrc_ec_monthly_samples.csv", ROOT / "data/features/10_monthly_feature_v2.csv",
                    ROOT / "data/raw/meteorology/openmeteo/openmeteo_all_stations_daily.csv",
                    ROOT / "data/raw/tide/uhslc/uhslc_tides_VungTau_id142_daily.csv",
                    ROOT / "data/external/research_tls_20261010_215230/tanchau_discharge_monthly.csv"]
    source_paths += [EXTERNAL / "noaa_nino34_anomaly.txt"] + sorted(EXTERNAL.glob("era5_extra_*.json"))
    source_paths += sorted((ROOT / "data/raw/dahiti").glob("*.csv"))
    target = pd.read_csv(source_paths[0], parse_dates=["month_start"])
    if target.duplicated(["station", "month_start"]).any(): raise ValueError("Duplicate EC station-month")
    if target.sample_count.gt(1).any(): raise ValueError("Target is no longer one sample per month; review target definition")
    if target.conductivity_mS_per_m.lt(0).any(): raise ValueError("Negative EC")
    v2 = pd.read_csv(source_paths[1]); v2["date"] = pd.to_datetime(v2.year_month)
    weather = pd.read_csv(source_paths[2], parse_dates=["date"])
    tide = pd.read_csv(source_paths[3], parse_dates=["date"]).set_index("date").sort_index().tide_max_m
    tide = tide.reindex(pd.date_range(tide.index.min(), tide.index.max()))
    tide_rolled = tide.rolling(30, min_periods=27).mean()
    discharge = pd.read_csv(source_paths[4], parse_dates=["month_start"]).set_index("month_start")
    nino, footer = parse_nino()
    calendar = pd.date_range("1985-01-01", "2026-08-01", freq="MS")
    tables, audit_rows = [], []
    for station, local in STATIONS.items():
        y = target[target.station.eq(station)].set_index("month_start").conductivity_mS_per_m.reindex(calendar)
        old = v2[v2.location_id.eq(local)].set_index("date").reindex(calendar)
        extra = json.loads((EXTERNAL / f"era5_extra_{local}.json").read_text(encoding="utf-8"))
        f = daily_features(weather[weather.station.eq(local)], extra, calendar)
        f["station"] = station; f["ec_target"] = y; f["ec_target_v2"] = old.ec_target
        f["ec_source_quality"] = "UNVERIFIED"; f["ec_temperature_basis"] = "UNKNOWN"
        f["month_sin"] = np.sin(2 * np.pi * calendar.month / 12)
        f["month_cos"] = np.cos(2 * np.pi * calendar.month / 12)
        for lag in [2, 3, 6]:
            source_months = calendar - pd.DateOffset(months=lag)
            available = pd.DatetimeIndex([month_end(t) + pd.Timedelta(days=30) for t in source_months]) < calendar
            f[f"nino34_lag{lag}_c"] = np.where(available, nino.reindex(source_months).to_numpy(), np.nan)
        f["nino34_trailing3_c"] = nino.rolling(3, min_periods=3).mean().reindex(calendar - pd.DateOffset(months=2)).to_numpy()
        f.loc[f.nino34_lag2_c.isna(), "nino34_trailing3_c"] = np.nan
        f["nino34_source_month"] = (calendar - pd.DateOffset(months=2)).strftime("%Y-%m")
        f["gfz_tanchau_q_lag2_m3s"] = discharge.discharge_m3s.reindex(calendar - pd.DateOffset(months=2)).to_numpy()
        f["gfz_tanchau_q_mean3_m3s"] = discharge.discharge_m3s.rolling(3, min_periods=3).mean().reindex(calendar - pd.DateOffset(months=2)).to_numpy()
        f["gfz_source_kind"] = discharge.source_kind.reindex(calendar - pd.DateOffset(months=2)).to_numpy()
        q_available = pd.DatetimeIndex([month_end(t) + pd.Timedelta(days=30) for t in calendar - pd.DateOffset(months=2)]) < calendar
        f.loc[~q_available, ["gfz_tanchau_q_lag2_m3s", "gfz_tanchau_q_mean3_m3s"]] = np.nan
        f["glofas_q_lag4_m3s"] = old.discharge_mean.shift(4) if station == "TANCHAU" else np.nan
        q_available = pd.DatetimeIndex([month_end(t) + pd.Timedelta(days=90) for t in calendar - pd.DateOffset(months=4)]) < calendar
        f.loc[~q_available, "glofas_q_lag4_m3s"] = np.nan
        f["glofas_quality"] = "SUSPECT_GRID_UNVALIDATED" if station == "TANCHAU" else "MISSING"
        tide_cutoff = calendar - pd.Timedelta(days=91)
        f["vungtau_daily_max_mean30_m"] = tide_rolled.reindex(tide_cutoff).to_numpy()
        dpath = next((ROOT / "data/raw/dahiti").glob(f"*_{local}_*.csv"))
        d = pd.read_csv(dpath, parse_dates=["date"]).sort_values("date")
        values, ages = [], []
        for t in calendar:
            origin = t - pd.Timedelta(seconds=1)
            valid = d[(d.date + pd.Timedelta(days=30) <= origin) & (d.date >= origin - pd.Timedelta(days=90))]
            values.append(valid.water_level_m.iloc[-1] if len(valid) else np.nan)
            ages.append((origin - valid.date.iloc[-1]).total_seconds() / 86400 if len(valid) else np.nan)
        f["dahiti_latest_m"] = values; f["dahiti_age_days"] = ages
        dropped = y.notna() & old.ec_target.isna()
        audit_rows.append(dict(station=station, source_samples=int(y.count()), v2_labels=int(old.ec_target.count()),
                               absent_from_v2=int(dropped.sum()), median_dropped=float(y[dropped].median()),
                               max_dropped=float(y[dropped].max()), max_retained_v2=float(old.ec_target.max())))
        for delay in [0, 30]:
            result = f.copy(); result["ec_delay_days"] = delay
            avail = pd.Series([month_end(t) + pd.Timedelta(days=delay) for t in calendar], index=calendar)
            ec_rows = []
            for t in calendar:
                origin = t - pd.Timedelta(seconds=1)
                known = y[(avail <= origin) & y.notna()]
                recent3 = known[known.index >= t - pd.DateOffset(months=3)]
                recent12 = known[known.index >= t - pd.DateOffset(months=12)]
                lag12_date = t - pd.DateOffset(months=12)
                ec_rows.append(dict(ec_latest=known.iloc[-1] if len(known) else np.nan,
                                    ec_previous=known.iloc[-2] if len(known) >= 2 else np.nan,
                                    ec_age_months=(t.year - known.index[-1].year) * 12 + t.month - known.index[-1].month if len(known) else np.nan,
                                    ec_latest_source_month=known.index[-1].strftime("%Y-%m") if len(known) else None,
                                    ec_latest_available_at=avail.loc[known.index[-1]].isoformat() + "+07:00" if len(known) else None,
                                    ec_lag12=known.get(lag12_date, np.nan),
                                    ec_mean3=recent3.mean(), ec_mean12=recent12.mean()))
            result = result.join(pd.DataFrame(ec_rows, index=calendar))
            result["issue_time"] = (calendar - pd.Timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S+07:00")
            result.index.name = "target_month"
            tables.append(result.reset_index())
    full = pd.concat(tables, ignore_index=True)
    if full.duplicated(["station", "target_month", "ec_delay_days"]).any(): raise ValueError("Join multiplied rows")
    full.to_csv(OUT / "feature_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(audit_rows).to_csv(OUT / "target_audit.csv", index=False, encoding="utf-8-sig")
    preview = full[full.ec_delay_days.eq(0) & full.target_month.between("2023-01-01", "2023-12-01")]
    preview.to_csv(OUT / "preview_2023.csv", index=False, encoding="utf-8-sig")
    coverage = []
    features = list(dict.fromkeys(ALL_FEATURES + ["gfz_tanchau_q_lag2_m3s", "glofas_q_lag4_m3s", "vungtau_daily_max_mean30_m", "dahiti_latest_m"]))
    for station, part in full[full.ec_delay_days.eq(0)].groupby("station"):
        labeled = part[part.ec_target.notna()]
        for feature in features:
            good = labeled[labeled[feature].notna()]
            coverage.append(dict(station=station, feature=feature, labels=len(labeled), available_labels=len(good),
                                 coverage=len(good)/len(labeled), first_target_month=good.target_month.min(), last_target_month=good.target_month.max()))
    pd.DataFrame(coverage).to_csv(OUT / "coverage.csv", index=False, encoding="utf-8-sig")
    manifest = dict(created_at=datetime.now(timezone.utc).isoformat(), protocol_sha256=digest(OUT / "protocol.json"),
                    inputs=[dict(path=str(p.relative_to(ROOT)), sha256=digest(p)) for p in source_paths],
                    outputs=dict(rows=len(full), stations=2, months_per_station=500, availability_scenarios=2),
                    target_audit=audit_rows, noaa_source_footer=footer,
                    noaa_warning="Actual retrieved source is ERSST V6, 1981-2010 anomaly baseline; do not label V5",
                    source_wind_unit="Legacy CSV does not carry unit metadata; keep as source units, not asserted m/s",
                    temperature_warning="Air temperature is not water temperature; EC compensation basis remains unknown")
    save_json(OUT / "data_manifest.json", manifest)
    print(json.dumps(manifest["outputs"]), flush=True)
    print(pd.DataFrame(audit_rows).to_string(index=False), flush=True)


def metrics(part):
    err = part.prediction.to_numpy() - part.actual.to_numpy()
    dry = part.target_month.dt.month.isin([12, 1, 2, 3, 4]).to_numpy()
    high = part.actual.to_numpy() >= part.high_threshold.to_numpy()
    return dict(n=len(part), mae=float(np.abs(err).mean()), rmse=float(np.sqrt(np.mean(err ** 2))), bias=float(err.mean()),
                dry_mae=float(np.abs(err[dry]).mean()) if dry.any() else np.nan,
                high_mae=float(np.abs(err[high]).mean()) if high.any() else np.nan, high_n=int(high.sum()))


def model_for(algorithm):
    from sklearn.compose import TransformedTargetRegressor
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    if algorithm == "RF":
        return make_pipeline(SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
                             RandomForestRegressor(n_estimators=120, max_depth=6, min_samples_leaf=5, random_state=42, n_jobs=1))
    return TransformedTargetRegressor(regressor=make_pipeline(SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
                                    StandardScaler(), Ridge(alpha=10)), func=np.log1p, inverse_func=np.expm1)


def evaluate_year(part, year, algorithm, name, columns, track, importance=False, min_train=96):
    jan = pd.Timestamp(year, 1, 1)
    delay = int(part.ec_delay_days.iloc[0])
    available = part.target_available
    train = part[(part.target_month >= "1986-01-01") & (available < jan) & part.ec_target.notna()]
    test = part[(part.target_month.dt.year == year) & part.ec_target.notna()]
    if len(train) < min_train or test.empty: return [], []
    threshold = float(train.ec_target.quantile(.9))
    if algorithm == "PERSISTENCE": pred = test.ec_latest.to_numpy()
    elif algorithm == "SEASONAL_NAIVE": pred = test.ec_lag12.to_numpy()
    elif algorithm == "CLIMATOLOGY": pred = test.target_month.dt.month.map(train.groupby(train.target_month.dt.month).ec_target.mean()).to_numpy()
    else:
        model = model_for(algorithm)
        model.fit(train[columns], train.ec_target)
        pred = np.maximum(0, model.predict(test[columns]))
    rows = []
    for (_, r), p in zip(test.iterrows(), pred):
        if not np.isfinite(p): continue
        rows.append(dict(station=r.station, ec_delay_days=delay, stage=track, year=year, target_month=r.target_month,
                         algorithm=algorithm, configuration=name, actual=r.ec_target, prediction=float(p),
                         high_threshold=threshold, train_n=len(train), train_last_month=train.target_month.max()))
    imported = []
    if importance and algorithm in ["RF", "RIDGE_LOG"] and len(test) >= 10:
        normal = np.mean(np.abs(test.ec_target.to_numpy() - pred))
        for group, cols in {"ec_history": EC, "season": SEASON, "basic_weather": BASIC, **GROUPS}.items():
            use = [c for c in cols if c in columns]
            if not use: continue
            for shift in [3, 6, 9]:
                changed = test[columns].copy()
                changed[use] = np.roll(changed[use].to_numpy(), shift, axis=0)
                altered = np.maximum(0, model.predict(changed))
                imported.append(dict(station=test.station.iloc[0], ec_delay_days=delay, year=year, algorithm=algorithm,
                                     configuration=name, feature_group=group, shift_months=shift,
                                     mae_increase=float(np.abs(test.ec_target.to_numpy() - altered).mean() - normal)))
    return rows, imported


def paired_gain(candidate, base):
    a = candidate[["target_month", "actual", "prediction"]].merge(base[["target_month", "prediction"]], on="target_month", suffixes=("", "_base"), validate="one_to_one")
    a = a.sort_values("target_month")
    delta = (a.prediction_base - a.actual).abs().to_numpy() - (a.prediction - a.actual).abs().to_numpy()
    rng = np.random.default_rng(42)
    n = len(delta); draws = []
    if n < 24: return dict(paired_n=n, gain_ci_low=np.nan, gain_ci_high=np.nan)
    for _ in range(1000):
        starts = rng.integers(0, n, int(np.ceil(n / 12)))
        indices = np.concatenate([(s + np.arange(12)) % n for s in starts])[:n]
        draws.append(delta[indices].mean())
    return dict(paired_n=n, gain_ci_low=float(np.quantile(draws, .025)), gain_ci_high=float(np.quantile(draws, .975)))


def evaluate():
    import sklearn
    matrix = pd.read_csv(OUT / "feature_matrix.csv", parse_dates=["target_month"])
    matrix["target_available"] = pd.to_datetime([month_end(t) + pd.Timedelta(days=int(d))
        for t, d in zip(matrix.target_month, matrix.ec_delay_days)])
    protocol = json.loads((OUT / "protocol.json").read_text())
    if protocol != PROTOCOL: raise ValueError("Protocol changed after preparation; rebuild explicitly")
    predictions, importances = [], []
    for (station, delay), part in matrix.groupby(["station", "ec_delay_days"]):
        for year in PROTOCOL["validation_years"]:
            for alg in ["PERSISTENCE", "SEASONAL_NAIVE", "CLIMATOLOGY"]:
                rows, _ = evaluate_year(part, year, alg, alg, [], "validation")
                predictions.extend(rows)
            for alg in ["RF", "RIDGE_LOG"]:
                for name, columns in CONFIGS.items():
                    rows, imp = evaluate_year(part, year, alg, name, columns, "validation", importance=name == "ALL" and delay == 0)
                    predictions.extend(rows); importances.extend(imp)
            print(f"validation {station} EC delay {delay} year {year}", flush=True)
    pred = pd.DataFrame(predictions)
    # Enforce a common evaluation cohort, including the seasonal baseline.
    group_keys = ["station", "ec_delay_days", "stage"]
    retained = []
    for _, group in pred.groupby(group_keys):
        totals = group.groupby(["algorithm", "configuration"]).ngroups
        dates = group.groupby("target_month").size()
        valid = dates[dates.eq(totals)].index
        retained.append(group[group.target_month.isin(valid)])
    pred = pd.concat(retained, ignore_index=True)
    keys = ["station", "ec_delay_days", "algorithm", "configuration"]
    summary_rows = []
    for values, group in pred.groupby(keys):
        info = dict(zip(keys, values)); info.update(metrics(group))
        base = pred[(pred.station == info["station"]) & (pred.ec_delay_days == info["ec_delay_days"]) & (pred.algorithm == info["algorithm"]) & pred.configuration.eq("BASE")]
        if len(base):
            bm = metrics(base)
            info["gain_vs_base_pct"] = 100 * (bm["mae"] - info["mae"]) / bm["mae"]
            win = 0
            for year, gy in group.groupby("year"):
                by = base[base.year.eq(year)]
                win += metrics(gy)["mae"] < metrics(by)["mae"]
            info["winning_years_vs_base"] = int(win)
            info.update(paired_gain(group, base))
            info["passes_exploratory_screen"] = bool(info["gain_vs_base_pct"] >= 5 and win >= 4 and info["gain_ci_low"] > 0)
        summary_rows.append(info)
    summary = pd.DataFrame(summary_rows).sort_values(["station", "ec_delay_days", "mae"])
    summary.to_csv(OUT / "validation_metrics.csv", index=False, encoding="utf-8-sig")
    pred.to_csv(OUT / "validation_predictions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(importances).to_csv(OUT / "group_permutation.csv", index=False, encoding="utf-8-sig")
    selections, hold = [], []
    for (station, delay), group in summary.groupby(["station", "ec_delay_days"]):
        choice = group.sort_values(["mae", "configuration"]).iloc[0]
        selections.append(dict(station=station, ec_delay_days=int(delay), algorithm=choice.algorithm, configuration=choice.configuration, validation_mae=float(choice.mae)))
    # Save frozen choices before reading any holdout model scores.
    save_json(OUT / "selection.json", dict(selected_on="validation_only", choices=selections))
    for choice in selections:
        part = matrix[matrix.station.eq(choice["station"]) & matrix.ec_delay_days.eq(choice["ec_delay_days"])]
        selected = (choice["algorithm"], choice["configuration"])
        comparisons = list(dict.fromkeys([selected, ("RF", "BASE"), ("RIDGE_LOG", "BASE"), ("PERSISTENCE", "PERSISTENCE"), ("SEASONAL_NAIVE", "SEASONAL_NAIVE"), ("CLIMATOLOGY", "CLIMATOLOGY")]))
        for year in PROTOCOL["retrospective_holdout_years"]:
            for alg, name in comparisons:
                rows, _ = evaluate_year(part, year, alg, name, CONFIGS.get(name, []), "retrospective_holdout")
                for row in rows: row["selected_on_validation"] = (alg, name) == selected
                hold.extend(rows)
    hold = pd.DataFrame(hold)
    common = []
    for _, group in hold.groupby(["station", "ec_delay_days"]):
        count = group.groupby(["algorithm", "configuration"]).ngroups
        months = group.groupby("target_month").size()
        common.append(group[group.target_month.isin(months[months.eq(count)].index)])
    hold = pd.concat(common, ignore_index=True)
    hm = []
    for values, group in hold.groupby(keys + ["selected_on_validation"]):
        hm.append(dict(zip(keys + ["selected_on_validation"], values)) | metrics(group))
    hold.to_csv(OUT / "holdout_predictions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(hm).to_csv(OUT / "holdout_metrics.csv", index=False, encoding="utf-8-sig")
    save_json(OUT / "evaluation_manifest.json", dict(created_at=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
              sklearn=sklearn.__version__, matrix_sha256=digest(OUT / "feature_matrix.csv"), script_sha256=digest(Path(__file__)),
              protocol_sha256=digest(OUT / "protocol.json"), validation_prediction_rows=len(pred), holdout_prediction_rows=len(hold)))
    print("SELECTION", json.dumps(selections), flush=True)
    print(pd.DataFrame(hm).to_string(index=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "evaluate"])
    args = parser.parse_args()
    prepare() if args.command == "prepare" else evaluate()
