"""Kiểm định EC một tháng tới: dữ liệu khả dụng -> validation -> test.

Chạy từ repo: python run_monthly_ec.py --station MYTHO
Quy trình và giới hạn: docs/reports/20261015_repository_review.md.
Không sửa dữ liệu gốc, không truy cập database, không quy đổi EC sang ppt.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import platform
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import unicodedata
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error


ROOT = Path(__file__).resolve().parent
TZ = "Asia/Ho_Chi_Minh"
SCRIPT_VERSION = "2.0.0"
BASIC_FEATURES = (
    "ec_latest", "ec_previous", "age_latest_months", "age_previous_months",
    "month_sin", "month_cos",
)
SEASONAL_FEATURES = BASIC_FEATURES + (
    "ec_lag12", "ec_mean3", "ec_mean12", "ec_std12",
)


class ForecastError(ValueError):
    """Đầu vào hoặc độ phủ chưa đủ để thực hiện thí nghiệm đã khai báo."""


@dataclass(frozen=True)
class Config:
    station: str = "MYTHO"
    validation_months: int = 12
    test_months: int = 24
    min_train_samples: int = 36
    min_eval_months: int = 6
    trees: int = 100
    seed: int = 42
    availability_lag_days: int = 0

    def validate(self):
        if min(self.validation_months, self.test_months) < self.min_eval_months:
            raise ForecastError("Validation và test phải dài ít nhất min_eval_months.")
        if self.min_eval_months < 1 or self.min_train_samples < 2 or self.trees < 1:
            raise ForecastError("Số tháng đánh giá, mẫu huấn luyện hoặc số cây không hợp lệ.")
        if self.availability_lag_days < 0:
            raise ForecastError("Độ trễ công bố không được âm.")
        if not 0 <= self.seed < 2**32:
            raise ForecastError("seed phải nằm trong [0, 2**32).")


def normalize_station(value):
    text = unicodedata.normalize("NFD", str(value))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = "".join(c for c in text.upper() if c.isalnum())
    aliases = {"MRCVN019805": "MYTHO", "MRCVN019803": "TANCHAU"}
    return aliases.get(text, text)


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def month_end(month):
    """Cuối tháng lịch, 23:59:59 giờ Việt Nam; nhãn tháng là ngày 01."""
    return (pd.Timestamp(month) + pd.DateOffset(months=1)
            - pd.Timedelta(seconds=1)).tz_localize(TZ)


def forecast_origin(target_month):
    return month_end(pd.Timestamp(target_month) - pd.DateOffset(months=1))


def iso(value):
    return None if pd.isna(value) else pd.Timestamp(value).isoformat()


def load_monthly_data(path, station, availability_lag_days=0):
    """Chỉ nhận EC >= 0 hoặc thiếu; không nội suy, không đổi nhãn chất lượng."""
    path = Path(path)
    if availability_lag_days < 0:
        raise ForecastError("Độ trễ công bố không được âm.")
    if not path.is_file():
        raise ForecastError(f"Không tìm thấy file: {path}")
    input_bytes = path.read_bytes()
    original = pd.read_csv(BytesIO(input_bytes))
    required = {"station", "month_start"}
    if not required.issubset(original.columns):
        raise ForecastError("CSV phải có station và month_start.")
    target_names = [c for c in ("conductivity_mS_per_m", "conductivity_ms_per_m")
                    if c in original.columns]
    if len(target_names) != 1:
        raise ForecastError("Cần đúng một cột EC conductivity_mS_per_m hoặc conductivity_ms_per_m.")
    selected = original.loc[
        original["station"].map(normalize_station) == normalize_station(station)
    ].copy()
    if selected.empty:
        raise ForecastError(f"Không tìm thấy trạm {station}.")
    try:
        months = pd.DatetimeIndex(pd.to_datetime(selected["month_start"], errors="raise"))
    except (ValueError, TypeError) as exc:
        raise ForecastError("month_start có ngày không hợp lệ.") from exc
    if (months.hasnans or months.tz is not None or not (months.day == 1).all()
            or not months.equals(months.normalize())):
        raise ForecastError("month_start phải là ngày 01, 00:00:00, không kèm múi giờ.")
    if months.has_duplicates:
        raise ForecastError("Trùng trạm/tháng; cần xử lý snapshot trước khi huấn luyện.")
    try:
        ec = pd.to_numeric(selected[target_names[0]], errors="raise").to_numpy(dtype=float)
    except (ValueError, TypeError) as exc:
        raise ForecastError("EC có giá trị không phải số.") from exc
    if np.isinf(ec).any() or (ec[np.isfinite(ec)] < 0).any():
        raise ForecastError("EC phải hữu hạn, không âm, hoặc để trống.")
    if not np.isfinite(ec).any():
        raise ForecastError("Trạm không có EC thực tế để huấn luyện/đánh giá.")

    # Nếu không có nhật ký công bố, ghi rõ đây là giả định hồi cứu.
    supplied_availability = "ec_available_at" in selected.columns
    if supplied_availability and availability_lag_days:
        raise ForecastError("Đã có ec_available_at: không cộng thêm availability_lag_days.")
    available = []
    for position, month in enumerate(months):
        if not np.isfinite(ec[position]):
            available.append(pd.NaT)
            continue
        end = month_end(month)
        if supplied_availability:
            raw = selected.iloc[position]["ec_available_at"]
            try:
                stamp = pd.Timestamp(raw)
            except (ValueError, TypeError) as exc:
                raise ForecastError("ec_available_at có timestamp không hợp lệ.") from exc
            if pd.isna(stamp) or stamp.tzinfo is None:
                raise ForecastError("Mỗi EC phải có ec_available_at kèm múi giờ.")
            stamp = stamp.tz_convert(TZ)
            if stamp < end:
                raise ForecastError("EC tổng hợp tháng chỉ được coi là hoàn tất từ cuối tháng.")
        else:
            stamp = end + pd.Timedelta(days=availability_lag_days)
        available.append(stamp)
    source = pd.DataFrame({"actual": ec,
                           "available_at": pd.array(available, dtype=f"datetime64[ns, {TZ}]")},
                          index=months).sort_index()
    last_actual = source["actual"].last_valid_index()
    calendar = pd.date_range(source.index.min(), last_actual, freq="MS")
    data = source.reindex(calendar)
    data.index.name = "target_month"
    metadata = {
        "file_name": path.name, "sha256": hashlib.sha256(input_bytes).hexdigest(),
        "station": normalize_station(station), "target_column": target_names[0],
        "unit": "mS/m", "input_station_rows": len(selected),
        "calendar_months": len(data), "observed_target_months": int(data.actual.notna().sum()),
        "last_target_month": str(last_actual.date()),
        "trailing_calendar_months_without_ec": int((source.index > last_actual).sum()),
        "availability_mode": "provided_ec_available_at" if supplied_availability
                             else "assumed_month_end_plus_lag",
        "availability_lag_days": availability_lag_days,
        "source_quality_validation": "not_performed; retain upstream quality flags",
    }
    return data, metadata


def month_age(target, source):
    return (target.year - source.year) * 12 + target.month - source.month


def build_features(data):
    """Tái dựng đầu vào theo thông tin khả dụng tại TỪNG thời điểm dự báo.

    Persistence dùng số đo gần nhất đã công bố; age_* cho biết tuổi dữ liệu.
    Khi dữ liệu liên tục và không trễ, ec_latest/ec_previous chính là lag_1/lag_2.
    Không điền EC thiếu; không sử dụng khí tượng chưa rõ thời điểm khả dụng.
    """
    rows = []
    targets = pd.date_range(data.index.min(), data.index.max() + pd.DateOffset(months=1), freq="MS")
    for target in targets:
        origin = forecast_origin(target)
        known = data.loc[(data.index < target) & data.actual.notna()
                         & (data.available_at <= origin)]
        row = {name: np.nan for name in SEASONAL_FEATURES}
        row.update(target_month=target, forecast_origin=origin,
                   latest_source_month=pd.NaT, persistence_available_at=pd.NaT,
                   seasonal_naive_available_at=pd.NaT,
                   basic_available_at=pd.NaT, seasonal_available_at=pd.NaT)
        row["month_sin"] = np.sin(2 * np.pi * target.month / 12)
        row["month_cos"] = np.cos(2 * np.pi * target.month / 12)
        if not known.empty:
            latest = known.index[-1]
            row.update(ec_latest=float(known.actual.iloc[-1]),
                       age_latest_months=month_age(target, latest),
                       latest_source_month=latest,
                       persistence_available_at=known.available_at.iloc[-1],
                       basic_available_at=known.available_at.iloc[-1])
        if len(known) >= 2:
            row.update(ec_previous=float(known.actual.iloc[-2]),
                       age_previous_months=month_age(target, known.index[-2]),
                       basic_available_at=known.available_at.iloc[-2:].max())
        seasonal_month = target - pd.DateOffset(months=12)
        if seasonal_month in known.index:
            row["ec_lag12"] = float(known.at[seasonal_month, "actual"])
            row["seasonal_naive_available_at"] = known.at[seasonal_month, "available_at"]
        window12 = known.loc[known.index >= target - pd.DateOffset(months=12)]
        window3 = window12.loc[window12.index >= target - pd.DateOffset(months=3)]
        if not window3.empty:
            row["ec_mean3"] = float(window3.actual.mean())
        if not window12.empty:
            row["ec_mean12"] = float(window12.actual.mean())
            row["ec_std12"] = float(window12.actual.std(ddof=0))
        stamps = [row["basic_available_at"], window12.available_at.max()]
        stamps = [s for s in stamps if pd.notna(s)]
        row["seasonal_available_at"] = max(stamps) if stamps else pd.NaT
        rows.append(row)
    return pd.DataFrame(rows).set_index("target_month")


def candidates():
    specs = [dict(name="Persistence", family="persistence", features=(), params={}),
             dict(name="Seasonal Naive", family="seasonal_naive", features=(), params={})]
    for family, feature_names in (("basic", BASIC_FEATURES), ("seasonal", SEASONAL_FEATURES)):
        for depth, leaf in ((3, 5), (5, 3), (None, 5)):
            name = f"RF_{family}_depth{depth}_leaf{leaf}"
            specs.append(dict(name=name, family=family, features=feature_names,
                              params=dict(max_depth=depth, min_samples_leaf=leaf)))
    return specs


def predict_one(data, features, target, spec, config, stage):
    target = pd.Timestamp(target)
    origin = forecast_origin(target)
    row = features.loc[target]
    prediction = dict(
        stage=stage, station=normalize_station(config.station), model=spec["name"],
        candidate_id=spec.get("candidate_id", spec["name"]),
        forecast_origin=origin.isoformat(), target_month=str(target.date()), horizon=1,
        unit="mS/m", actual=float(data.at[target, "actual"]) if target in data.index else np.nan,
        actual_available_at=iso(data.at[target, "available_at"]) if target in data.index else None,
        predicted=np.nan, status="SKIP_MISSING_FEATURES", n_train_samples=0,
        train_last_target_month=None, max_train_target_available_at=None,
        max_feature_available_at=None, latest_source_month=iso(row.latest_source_month),
        age_latest_months=float(row.age_latest_months),
    )
    family = spec["family"]
    if family in ("persistence", "seasonal_naive"):
        column = "ec_latest" if family == "persistence" else "ec_lag12"
        value = row[column]
        available = row[f"{family}_available_at"]
        prediction["max_feature_available_at"] = iso(available)
        if np.isfinite(value):
            if pd.isna(available) or available > origin:
                raise AssertionError("Baseline dùng dữ liệu chưa khả dụng.")
            prediction.update(predicted=float(value), status="SUCCESS")
        return prediction, None

    columns = list(spec["features"])
    if not np.isfinite(row[columns].to_numpy(dtype=float)).all():
        return prediction, None
    prediction["max_feature_available_at"] = iso(row[f"{family}_available_at"])
    if pd.isna(row[f"{family}_available_at"]) or row[f"{family}_available_at"] > origin:
        raise AssertionError("RF dùng đầu vào chưa khả dụng.")
    history = features.loc[features.index < target, columns].join(data)
    finite_features = np.isfinite(history[columns].to_numpy(dtype=float)).all(axis=1)
    history = history.loc[finite_features & history.actual.notna()
                          & (history.available_at <= origin)]
    prediction["n_train_samples"] = len(history)
    if len(history) < config.min_train_samples:
        prediction["status"] = "SKIP_INSUFFICIENT_TRAIN"
        return prediction, None
    prediction["train_last_target_month"] = str(history.index.max().date())
    prediction["max_train_target_available_at"] = iso(history.available_at.max())
    estimator = RandomForestRegressor(n_estimators=config.trees, random_state=config.seed,
                                      n_jobs=1, **spec["params"])
    estimator.fit(history[columns], history.actual)
    value = float(estimator.predict(features.loc[[target], columns])[0])
    if not np.isfinite(value) or value < 0:
        raise ForecastError("Mô hình sinh giá trị EC không hợp lệ.")
    prediction.update(predicted=value, status="SUCCESS")
    return prediction, estimator


def split_calendar(data, config):
    config.validate()
    train_size = len(data) - config.validation_months - config.test_months
    if train_size < config.min_train_samples:
        raise ForecastError("Lịch dữ liệu quá ngắn cho train/validation/test đã khai báo.")
    pieces = {"train": data.index[:train_size],
              "validation": data.index[train_size:-config.test_months],
              "test": data.index[-config.test_months:]}
    manifest = pd.DataFrame([
        dict(split=name, start=str(months.min().date()), end=str(months.max().date()),
             calendar_months=len(months), actual_months=int(data.loc[months].actual.notna().sum()))
        for name, months in pieces.items()
    ])
    return pieces, manifest


def walk_forward(data, features, months, specs, config, stage, verbose=True):
    results = []
    for position, month in enumerate(months, start=1):
        for spec in specs:
            result, _ = predict_one(data, features, month, spec, config, stage)
            results.append(result)
        if verbose and (position % 6 == 0 or position == len(months)):
            print(f"{stage}: {position}/{len(months)} tháng", flush=True)
    return pd.DataFrame(results)


def score_predictions(predictions, actual_available_by=None):
    """Báo cả độ phủ riêng và sai số trên giao tập tháng CHUNG của mọi mô hình."""
    models = predictions.model.drop_duplicates().tolist()
    label_available = predictions.actual.notna()
    if actual_available_by is not None:
        available = pd.to_datetime(predictions.actual_available_at, utc=True)
        label_available = label_available & (available <= pd.Timestamp(actual_available_by))
    usable = predictions.loc[label_available & (predictions.status == "SUCCESS")
                              & np.isfinite(predictions.actual)
                              & np.isfinite(predictions.predicted)]
    sets = {model: set(usable.loc[usable.model == model, "target_month"]) for model in models}
    common = set.intersection(*sets.values())
    scored = predictions.copy()
    scored["label_available_for_evaluation"] = label_available
    scored["in_common_cohort"] = scored.target_month.isin(common)
    actual_months = predictions.loc[predictions.actual.notna(), "target_month"].nunique()
    metrics = []
    for model in models:
        own = usable.loc[usable.model == model]
        for cohort, frame in (("model_available", own), ("common", own.loc[own.target_month.isin(common)])):
            months = sorted(frame.target_month.tolist())
            metrics.append(dict(
                stage=predictions.stage.iloc[0], model=model, cohort=cohort,
                mae_mS_m=mean_absolute_error(frame.actual, frame.predicted) if len(frame) else np.nan,
                rmse_mS_m=root_mean_squared_error(frame.actual, frame.predicted) if len(frame) else np.nan,
                eval_samples=len(frame), target_months_with_actual=actual_months,
                evaluation_label_cutoff=iso(actual_available_by),
                coverage_fraction=len(frame) / actual_months if actual_months else 0.0,
                evaluation_months_sha256=hashlib.sha256("\n".join(months).encode()).hexdigest(),
            ))
    cohort_rows = []
    for target, frame in predictions.groupby("target_month", sort=True):
        missing = [m for m in models if target not in sets[m]]
        cohort_rows.append(dict(stage=frame.stage.iloc[0], target_month=target,
                                actual=frame.actual.iloc[0], in_common_cohort=target in common,
                                excluded_models="; ".join(missing)))
    return scored, pd.DataFrame(metrics), pd.DataFrame(cohort_rows)


def choose_on_validation(metrics, config):
    if set(metrics.stage) != {"validation"}:
        raise ForecastError("Chỉ được chọn cấu hình/mô hình bằng validation.")
    ranked = metrics.loc[metrics.cohort == "common"].copy()
    if ranked.empty or (ranked.eval_samples < config.min_eval_months).any():
        raise ForecastError("Không đủ tháng validation chung; xem độ phủ và trạng thái bỏ qua.")
    # Stable sort giữ ưu tiên mô hình đơn giản khi MAE bằng nhau.
    ranked = ranked.sort_values("mae_mS_m", kind="stable")
    rf_rows = ranked.loc[ranked.model.str.startswith("RF_")]
    if rf_rows.empty:
        raise ForecastError("Không có cấu hình RF hợp lệ trên validation.")
    return str(ranked.iloc[0].model), str(rf_rows.iloc[0].model)


def safe_json(value):
    if isinstance(value, dict):
        return {str(k): safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(safe_json(value), indent=2, ensure_ascii=False,
                                    allow_nan=False) + "\n", encoding="utf-8")


def save_chart(predictions, metrics, path, station, selected_model):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    fig, (ax, bars) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [3, 1]})
    actual = predictions.drop_duplicates("target_month").sort_values("target_month")
    dates = pd.to_datetime(actual.target_month)
    ax.plot(dates, actual.actual, color="#162f3a", marker="o", label="Observed EC", linewidth=2)
    colors = {"Persistence": "#168475", "Seasonal Naive": "#b0781f", "Random Forest": "#6879c0"}
    for model, frame in predictions.groupby("model", sort=False):
        frame = frame.sort_values("target_month")
        values = frame.predicted.where(frame.status == "SUCCESS")
        ax.plot(pd.to_datetime(frame.target_month), values, label=model,
                color=colors[model], alpha=0.9, linewidth=1.4)
    ax.set_ylabel("EC (mS/m)")
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.18)
    ax.legend(ncol=2, frameon=False)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    common = metrics.loc[metrics.cohort == "common"]
    bars.barh(common.model, common.mae_mS_m, color=[colors[m] for m in common.model])
    bars.set_xlabel(f"Test MAE (mS/m) | same {int(common.eval_samples.iloc[0])} target months")
    bars.grid(axis="x", alpha=0.18)
    fig.suptitle(f"{station}: monthly historical backtest | selected on validation: {selected_model}", fontsize=13)
    fig.text(0.5, 0.01, "Experimental; availability rule in run_manifest.json. Not a current operational forecast.",
             ha="center", fontsize=9, color="#53646b")
    fig.tight_layout(rect=(0, 0.035, 1, 0.97))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_experiment(data_path, output_root, config):
    config.validate()
    data, provenance = load_monthly_data(data_path, config.station, config.availability_lag_days)
    features = build_features(data)
    splits, split_manifest = split_calendar(data, config)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    out = Path(output_root) / f"{normalize_station(config.station)}_{run_id}"
    out.mkdir(parents=True, exist_ok=False)
    manifest = dict(
        status="RUNNING", run_id=run_id, script_version=SCRIPT_VERSION,
        script_sha256=file_hash(__file__), created_at_utc=datetime.now(timezone.utc).isoformat(),
        config=asdict(config), input=provenance,
        software=dict(python=platform.python_version(), pandas=pd.__version__, numpy=np.__version__,
                      scikit_learn=sklearn.__version__, joblib=joblib.__version__),
        protocol=dict(
            target="EC sample in the next calendar month, mS/m; no target imputation; not continuous monthly mean",
            forecast_origin="23:59:59 Asia/Ho_Chi_Minh on the last day of the preceding month",
            horizon="One calendar month after forecast_origin's month",
            evaluation="Expanding-window walk-forward; refit RF at every origin",
            validation="Select RF configuration and overall model by common-cohort validation MAE",
            test="Frozen choices; earlier test observations may enter later fits only when available",
            historical_test_caveat="2022-2023 results were inspected in earlier project experiments; not a blind test",
        ),
        limitations=[
            "Historical backtest, not an operational warning or gate-control recommendation.",
            "No scientific validation of source EC quality; UNVERIFIED is not promoted to VALIDATED.",
            "Availability is only a scenario unless ec_available_at has documented provenance.",
            "A month label identifies an aggregate; it is not the original measurement timestamp.",
            "Input has no historical revision vintages; real-time reproducibility is not certified.",
        ],
    )
    write_json(out / "run_manifest.json", manifest)
    try:
        split_manifest.to_csv(out / "split_manifest.csv", index=False)
        features.join(data).to_csv(out / "feature_audit.csv", index_label="target_month")
        specs = candidates()
        validation = walk_forward(data, features, splits["validation"], specs, config, "validation")
        # Nhãn validation công bố sau origin test đầu tiên cũng chưa được phép
        # tham gia lựa chọn mô hình (kể cả khi feature từng dự báo đã đúng).
        selection_cutoff = forecast_origin(splits["test"][0])
        validation, val_metrics, val_cohort = score_predictions(validation, selection_cutoff)
        validation.to_csv(out / "validation_predictions.csv", index=False)
        val_metrics.to_csv(out / "validation_metrics.csv", index=False)
        selected_candidate, rf_candidate = choose_on_validation(val_metrics, config)
        rf_spec = next(s for s in specs if s["name"] == rf_candidate).copy()
        rf_spec.update(name="Random Forest", candidate_id=rf_candidate)
        selected_model = "Random Forest" if selected_candidate.startswith("RF_") else selected_candidate
        # Quyết định được lưu TRƯỚC khi chạy test, không được thay theo sai số test.
        selection = dict(selection_stage="validation", criterion="MAE on common target months",
                         selection_available_at=selection_cutoff.isoformat(),
                         selected_model=selected_model, selected_candidate=selected_candidate,
                         selected_rf_candidate=rf_candidate, rf_features=rf_spec["features"],
                         rf_parameters={"n_estimators": config.trees, "random_state": config.seed,
                                        **rf_spec["params"]},
                         validation_ranking=val_metrics.loc[val_metrics.cohort == "common"]
                         .sort_values("mae_mS_m", kind="stable").to_dict("records"))
        write_json(out / "selection.json", selection)
        print(f"Chọn bằng validation: {selected_model}; RF: {rf_candidate}", flush=True)
        test_specs = specs[:2] + [rf_spec]
        test = walk_forward(data, features, splits["test"], test_specs, config, "test")
        test, metrics, test_cohort = score_predictions(test)
        # Fixed from training only, never tuned to the test extremes.
        high_threshold = float(data.loc[splits['train'], 'actual'].quantile(0.9))
        high_rows = test.loc[test.in_common_cohort & (test.actual >= high_threshold)]
        high_metrics = []
        for model in test.model.unique():
            part = high_rows.loc[high_rows.model == model]
            high_metrics.append(dict(model=model, train_p90_mS_m=high_threshold,
                eval_samples=len(part), mae_mS_m=float(np.abs(part.actual-part.predicted).mean()) if len(part) else None,
                rmse_mS_m=float(np.sqrt(np.mean((part.actual-part.predicted)**2))) if len(part) else None))
        pd.DataFrame(high_metrics).to_csv(out / 'high_ec_metrics.csv', index=False)
        manifest['high_ec_metrics'] = high_metrics
        test.to_csv(out / "predictions.csv", index=False)
        metrics.to_csv(out / "metrics.csv", index=False)
        pd.concat([val_cohort, test_cohort], ignore_index=True).to_csv(out / "evaluation_cohort.csv", index=False)
        common_metrics = metrics.loc[metrics.cohort == "common"]
        if (common_metrics.eval_samples < config.min_eval_months).any():
            raise ForecastError("Không đủ tháng test chung; đã lưu dự báo và độ phủ để kiểm tra.")
        scores = common_metrics.set_index("model").mae_mS_m
        baseline_mae = float(scores["Persistence"])
        selected_mae = float(scores[selected_model])
        assessment = dict(
            selected_on_validation=selected_model, selected_test_mae_mS_m=selected_mae,
            persistence_test_mae_mS_m=baseline_mae,
            selected_beats_persistence_on_test=selected_mae < baseline_mae,
            mae_skill_vs_persistence=(1 - selected_mae / baseline_mae) if baseline_mae > 0 else None,
            deployment_ready=False,
            note="Test diagnoses generalization; it does not change the selection already frozen on validation.",
        )

        # Kỳ sau tháng EC cuối. Không tự gọi đây là dự báo cho tháng hiện tại.
        next_month = data.index.max() + pd.DateOffset(months=1)
        next_rows, rf_estimator = [], None
        for spec in test_specs:
            result, estimator = predict_one(data, features, next_month, spec, config, "next_after_last_observation")
            next_rows.append(result)
            if spec["name"] == "Random Forest":
                rf_estimator = estimator
        chosen_next = next(r for r in next_rows if r["model"] == selected_model)
        today_local = pd.Timestamp.now(tz=TZ)
        next_info = dict(
            data_kind="experimental_next_after_last_observation", selected_model=selected_model,
            target_month=str(next_month.date()), forecast_origin=forecast_origin(next_month).isoformat(),
            target_is_before_current_month=next_month.to_period("M") < today_local.tz_localize(None).to_period("M"),
            availability_mode=provenance["availability_mode"], quality_status="EXPERIMENTAL",
            deployment_ready=False,
            selected_prediction=chosen_next, all_predictions=next_rows,
            note="This date follows the last EC observation; it is not automatically a forecast for today.",
        )
        write_json(out / "next_forecast.json", next_info)
        # Chỉ estimator sklearn và metadata chuẩn: không pickle hàm/lớp __main__.
        bundle = dict(format_version=1, station=normalize_station(config.station), unit="mS/m",
                      usage="historical_experiment", deployment_ready=False,
                      selected_model=selected_model, rf_estimator=rf_estimator,
                      rf_features=list(rf_spec["features"]), selection=selection,
                      input_sha256=provenance["sha256"], software=manifest["software"],
                      forecast_origin=forecast_origin(next_month).isoformat(),
                      availability_mode=provenance["availability_mode"],
                      baseline_state={"ec_latest": safe_json(features.at[next_month, "ec_latest"]),
                                      "ec_lag12": safe_json(features.at[next_month, "ec_lag12"])},
                      next_feature_values={k: safe_json(features.at[next_month, k]) for k in rf_spec["features"]})
        joblib.dump(bundle, out / "model_bundle.joblib", compress=3)
        save_chart(test, metrics, out / "forecast_chart.png", normalize_station(config.station), selected_model)
        if file_hash(data_path) != provenance["sha256"]:
            raise ForecastError("File đầu vào đã thay đổi trong lúc chạy; kết quả không được chấp nhận.")
        manifest.update(status="COMPLETED", selection=selection, test_assessment=assessment,
                        test_common_metrics=common_metrics.to_dict("records"),
                        selected_next_status=chosen_next["status"],
                        finished_at_utc=datetime.now(timezone.utc).isoformat())
        manifest["output_sha256"] = {p.name: file_hash(p) for p in sorted(out.iterdir())
                                      if p.is_file() and p.name != "run_manifest.json"}
        write_json(out / "run_manifest.json", manifest)
        print(common_metrics[["model", "mae_mS_m", "rmse_mS_m", "eval_samples"]].to_string(index=False))
        if selected_model != "Persistence" and not assessment["selected_beats_persistence_on_test"]:
            print("Kết luận test: mô hình chọn trên validation chưa vượt Persistence; chưa đủ căn cứ triển khai.")
        print(json.dumps(dict(status="COMPLETED", output=str(out.resolve()), selected_model=selected_model,
                              next_target_month=str(next_month.date()),
                              next_is_historical=next_info["target_is_before_current_month"]), ensure_ascii=False))
        return out
    except Exception as exc:
        manifest.update(status="FAILED", error_type=type(exc).__name__, error=str(exc))
        write_json(out / "run_manifest.json", manifest)
        print(f"Đã lưu chẩn đoán: {out}", file=sys.stderr)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/research/mrc_ec_monthly_samples.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs/local_ec_backtest")
    parser.add_argument("--station", default="MYTHO", help="Ví dụ MYTHO hoặc TANCHAU")
    parser.add_argument("--validation-months", type=int, default=12)
    parser.add_argument("--test-months", type=int, default=24)
    parser.add_argument("--min-train-samples", type=int, default=36)
    parser.add_argument("--min-eval-months", type=int, default=6)
    parser.add_argument("--trees", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--availability-lag-days", type=int, default=0,
                        help="Giả định EC khả dụng sau cuối tháng bao nhiêu ngày; mặc định 0.")
    args = parser.parse_args(argv)
    config = Config(**{key: value for key, value in vars(args).items()
                       if key not in ("data", "output_dir")})
    try:
        run_experiment(args.data, args.output_dir, config)
    except (ForecastError, OSError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
