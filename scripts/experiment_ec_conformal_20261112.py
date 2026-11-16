"""Research: online conformal intervals for the served My Tho model configuration.

Model: the configuration of ``20261108T_HYDROLOGY_PRIMARY_V1`` (RF 300 trees,
max_depth 8, min_samples_leaf 3, seed 42, median imputer; 10 features: weather
t-2, month cycle, Kratie Q t-2, Q 3-month, Q ratio, Tan Chau stage t-2 and
3-month median).  The served artifact itself is fitted on all labels through
12/2023 and cannot produce out-of-sample errors, so this script *re-fits the
same configuration* at each monthly issue (rolling origin, expanding window).
It does not load or change the registered artifact.

Availability (assumed): EC label month end + {5, 35} days; weather and
hydrology use target t-2 (month end + 5 days).  The hydrology lag is not varied
here; see experiment_ec_peak_risk_20261112.py for that sensitivity.

Intervals (log1p scale; nominal 90 %):
* ``online_quantile``: at each issue, the order statistic
  k = ceil((n+1)(1-alpha)) of |log1p(y) - log1p(yhat)| over all residuals
  whose label is available at that issue (n of them).  If k > n the interval
  is unbounded and reported as such.  These residuals come from a rolling
  sequence of re-fitted models, so this is an online/sequential conformal
  procedure, not a split-conformal guarantee for one fixed model.
* ``online_quantile_season``: same, only residuals from the same season
  (Dec-May dry or Jun-Nov wet).
* ``aci``: Gibbs & Candes (2021) adaptive alpha, gamma 0.02, updated when a
  label becomes available.
* ``tree_p05_p95``: 5th-95th percentile of individual tree predictions of the
  same fitted model, for a like-for-like comparison.

Warm-up 2010-2018; scored on 2019-2021 and 2022-2023.  Writes only
outputs/ec_conformal_20261112/.  An interval is not a safe ceiling or gate rule.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.domain.multivariate_ec import FEATURES, HYDRO_FEATURES  # noqa: E402
from tools.backtest_protocols import available_date_for, issue_date_for  # noqa: E402
from tools.feature_building import data_matrix  # noqa: E402
from tools.model_training import pipeline  # noqa: E402

OUTPUT = ROOT / "outputs/ec_conformal_20261112"
REGISTRY_MANIFEST = ROOT / "runs/multivariate_ec/mytho/20261108T_HYDROLOGY_PRIMARY_V1/manifest.json"
ORDER = FEATURES + HYDRO_FEATURES
ALPHA, GAMMA = 0.1, 0.02
DRY = {12, 1, 2, 3, 4, 5}
START = pd.Timestamp("2010-01-01")
METHODS = ("online_quantile", "online_quantile_season", "aci", "tree_p05_p95")
CODE = ["scripts/experiment_ec_conformal_20261112.py", "tools/feature_building.py",
        "scripts/experiment_ec_upstream_asof.py", "tools/backtest_protocols.py",
        "tools/model_training.py", "backend/domain/multivariate_ec.py",
        "backend/repositories/multivariate_inputs.py"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_configuration():
    manifest = json.loads(REGISTRY_MANIFEST.read_text(encoding="utf-8"))
    if manifest["feature_order"] != ORDER:
        raise ValueError("Feature order differs from the served My Tho manifest")
    rf = pipeline().named_steps["randomforestregressor"]
    for key, value in manifest["parameters"].items():
        if getattr(rf, key) != value:
            raise ValueError(f"Parameter {key} differs from the served manifest")
    return manifest


def conformal_width(scores, level):
    """Order statistic ceil((n+1)*level) of n scores; inf when it exceeds n."""
    n = len(scores)
    if n == 0:
        return math.inf
    level = min(max(level, 0.0), 1.0)
    k = math.ceil((n + 1) * level)
    if k < 1:
        return 0.0
    if k > n:
        return math.inf
    return float(np.sort(scores)[k - 1])


def rolling_forecasts(delay):
    data = data_matrix(delay).sort_values("month_start").reset_index(drop=True)
    data["available"] = [available_date_for(m, delay) for m in data.month_start]
    rows = []
    for _, row in data[data.month_start >= START].iterrows():
        issue = issue_date_for(row.month_start)
        if available_date_for(row.weather_month, 5) > issue:
            raise ValueError("Weather unavailable at issue")
        train = data[(data.month_start < row.month_start) & (data.available <= issue)]
        model = pipeline().set_params(randomforestregressor__n_jobs=1)
        model.fit(train[ORDER], train.conductivity_mS_per_m)
        x = row[ORDER].to_frame().T.astype(float)
        imputed = model.named_steps["simpleimputer"].transform(x)
        trees = np.array([t.predict(imputed)[0] for t in model.named_steps["randomforestregressor"].estimators_])
        rows.append(dict(target_month=row.month_start, issue_date=issue, available=row.available,
                         actual=row.conductivity_mS_per_m, forecast=float(model.predict(x)[0]),
                         tree_p05=float(np.percentile(trees, 5)), tree_p95=float(np.percentile(trees, 95)),
                         n_train=len(train)))
    return pd.DataFrame(rows)


def intervals(frame):
    frame = frame.reset_index(drop=True)
    frame["score"] = np.abs(np.log1p(frame.actual) - np.log1p(frame.forecast.clip(lower=0)))
    alpha_t, applied, out = ALPHA, set(), []
    for i, row in frame.iterrows():
        known = frame[(frame.index < i) & (frame.available <= row.issue_date)]
        for j in known.index:
            if j not in applied and j in frame.index[:i]:
                alpha_t += GAMMA * (ALPHA - frame.at[j, "aci_miss"])
                applied.add(j)
        same = known[known.target_month.dt.month.isin(DRY) == (row.target_month.month in DRY)]
        widths = {"online_quantile": conformal_width(known.score.to_numpy(), 1 - ALPHA),
                  "online_quantile_season": conformal_width(same.score.to_numpy(), 1 - ALPHA),
                  "aci": conformal_width(known.score.to_numpy(), 1 - alpha_t)}
        center = math.log1p(max(row.forecast, 0.0))
        rec = dict(n_scores=len(known), n_scores_season=len(same), aci_alpha=alpha_t)
        for name, w in widths.items():
            rec[f"{name}_lo"] = max(0.0, math.expm1(center - w)) if math.isfinite(w) else 0.0
            rec[f"{name}_hi"] = math.expm1(center + w) if math.isfinite(w) else math.inf
        rec["tree_p05_p95_lo"], rec["tree_p05_p95_hi"] = row.tree_p05, row.tree_p95
        frame.at[i, "aci_miss"] = float(not (rec["aci_lo"] <= row.actual <= rec["aci_hi"]))
        out.append(rec)
    return pd.concat([frame, pd.DataFrame(out)], axis=1)


def metrics(pred):
    records = []
    periods = {"2019_2021": ("2019-01-01", "2021-12-01"), "2022_2023": ("2022-01-01", "2023-12-01")}
    for delay in sorted(pred.delay_days.unique()):
        for pname, (a, b) in periods.items():
            g = pred[(pred.delay_days == delay) & pred.target_month.between(a, b)]
            cohorts = {"all": np.ones(len(g), bool),
                       "dry_Dec_May": g.target_month.dt.month.isin(DRY).to_numpy(),
                       "high_EC_100": (g.actual >= 100).to_numpy()}
            for cohort, mask in cohorts.items():
                part = g[mask]
                if part.empty:
                    continue
                for m in METHODS:
                    lo, hi = part[f"{m}_lo"], part[f"{m}_hi"]
                    inside = (lo <= part.actual) & (part.actual <= hi)
                    records.append(dict(delay_days=int(delay), period=pname, cohort=cohort, method=m,
                                        n=len(part), covered=int(inside.sum()), coverage=float(inside.mean()),
                                        median_upper_mS_m=float(hi.median()),
                                        median_width_mS_m=float((hi - lo).median()),
                                        above_upper=int((part.actual > hi).sum()),
                                        missed_months=";".join(part.target_month[~inside].dt.strftime("%Y-%m"))))
            records.append(dict(delay_days=int(delay), period=pname, cohort="all", method="point_forecast",
                                n=len(g), mae_mS_m=float((g.forecast - g.actual).abs().mean()),
                                rmse_mS_m=float(np.sqrt(((g.forecast - g.actual) ** 2).mean()))))
    return pd.DataFrame(records)


def main():
    manifest = check_configuration()
    parts = []
    for delay in (5, 35):
        frame = intervals(rolling_forecasts(delay))
        frame["delay_days"] = delay
        parts.append(frame)
        print("delay", delay, "done", flush=True)
    pred = pd.concat(parts, ignore_index=True)
    met = metrics(pred)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for old in ("predictions.csv", "metrics.csv", "run_manifest.json"):
        (OUTPUT / old).unlink(missing_ok=True)
    pred.to_csv(OUTPUT / "predictions.csv", index=False)
    met.to_csv(OUTPUT / "metrics.csv", index=False)
    out = dict(
        schema_version=2, protocol_id="ROLLING_ONLINE_CONFORMAL_HYDROLOGY_PRIMARY_CONFIG_V1",
        model_configuration_of=manifest.get("model_version", "20261108T_HYDROLOGY_PRIMARY_V1"),
        refit_rule="Same features/parameters as the served manifest; re-fitted at every monthly issue on labels available then.",
        nominal_coverage=1 - ALPHA, aci_gamma=GAMMA, score="|log1p(actual) - log1p(forecast)|",
        order_statistic="k = ceil((n+1)(1-alpha)); unbounded when k > n",
        warmup_from=START.date().isoformat(), seasons=dict(dry=sorted(DRY)),
        availability=dict(ec_days=[5, 35], weather_days=5, hydrology_days=5),
        limitations=["Online/sequential conformal on a rolling model sequence, not split conformal for one fixed artifact.",
                     "Availability lags are assumptions.", "2019-2023 has been inspected before; not a blind test.",
                     "Interval is a statistical band, not a safe EC ceiling or gate rule."],
        sklearn_version=sklearn.__version__,
        source_sha256={p: sha(ROOT / p) for p in CODE + [
            "data/research/mrc_ec_monthly_samples.csv",
            "runs/multivariate_ec/mytho/20261108T_HYDROLOGY_PRIMARY_V1/manifest.json",
            "data/external/multivariate_weather/manifest.json"]},
        output_sha256={n: sha(OUTPUT / n) for n in ("predictions.csv", "metrics.csv")})
    (OUTPUT / "run_manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pd.set_option("display.width", 220)
    print(met.drop(columns=["missed_months"]).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
