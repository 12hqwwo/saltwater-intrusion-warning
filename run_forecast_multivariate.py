"""Monthly multivariate EC experiments and explicit-time inference.

python run_forecast_multivariate.py train --station MYTHO
python run_forecast_multivariate.py predict --contract PATH --request PATH
See docs/forecast_and_gate_step06.md. Never issues gate commands.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
from uuid import uuid4

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
TZ = "Asia/Ho_Chi_Minh"
VERSION = "1.0.1"
TARGET = "conductivity_mS_per_m"
WEATHER = ("precipitation_sum", "temperature_mean", "evapotranspiration_sum")
BASELINES = ("PERSISTENCE", "SEASONAL_NAIVE", "MONTHLY_CLIMATOLOGY")
PATHS = ("AR", "ARX", "EXOG", "EXOG_DELAYED")
MODEL_SPECS = ({"algorithm": "RF", "max_depth": 4, "min_samples_leaf": 5},
               {"algorithm": "RF", "max_depth": None, "min_samples_leaf": 8},
               {"algorithm": "RIDGE_LOG", "alpha": 10.0})


class ForecastError(ValueError):
    pass


@dataclass
class Settings:
    validation_months: int = 12
    calibration_months: int = 12
    test_months: int = 24
    min_train: int = 60
    min_eval: int = 12
    trees: int = 100
    seed: int = 42
    interval_coverage: float = 0.9

    def validate(self):
        for name in ("validation_months", "calibration_months", "test_months", "min_train", "min_eval", "trees"):
            if not isinstance(getattr(self, name), int) or isinstance(getattr(self, name), bool) or getattr(self, name) < 1:
                raise ForecastError(f"{name} phải là số nguyên dương.")
        if self.min_train < 24 or self.min_eval < 3 or not 0 < self.interval_coverage < 1:
            raise ForecastError("Cần ít nhất 24 mẫu train, 3 mẫu đánh giá, coverage thuộc (0,1).")
        if min(self.validation_months, self.calibration_months, self.test_months) < self.min_eval:
            raise ForecastError("Mỗi giai đoạn phải dài ít nhất min_eval.")


def station_code(value):
    key = str(value).upper().replace("_", "").replace(" ", "")
    names = {"MYTHO": "MYTHO", "TANCHAU": "TANCHAU", "MRCVN019805": "MYTHO", "MRCVN019803": "TANCHAU"}
    if key not in names:
        raise ForecastError(f"Mã trạm chưa hỗ trợ: {value}")
    return names[key]


def aware(value):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ForecastError("Timestamp cần múi giờ rõ ràng.")
    return stamp.tz_convert(TZ)


def month(value):
    result = pd.Timestamp(value)
    if pd.isna(result) or result.tzinfo is not None or result != result.to_period("M").to_timestamp():
        raise ForecastError("Nhãn tháng phải là ngày 01, 00:00:00, không kèm múi giờ.")
    return result


def end_of_month(value):
    return (month(value) + pd.DateOffset(months=1) - pd.Timedelta(seconds=1)).tz_localize(TZ)


def origin_for(target):
    return end_of_month(month(target) - pd.DateOffset(months=1))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def save_json(path, value):
    Path(path).write_text(json.dumps(clean(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def new_run(root, prefix):
    path = Path(root) / f"{prefix}_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def read_data(path, registry_path):
    registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    if registry.get("schema_version") != 1:
        raise ForecastError("Sai schema_version của registry.")
    variables = registry["variables"]
    required = {"station", "month_start", TARGET, *WEATHER}
    frame = pd.read_csv(path)
    if not required.issubset(frame.columns):
        raise ForecastError(f"Thiếu cột {sorted(required - set(frame.columns))}")
    frame["station"] = frame.station.map(station_code)
    frame["month_start"] = frame.month_start.map(month)
    if frame.duplicated(["station", "month_start"]).any():
        raise ForecastError("Trùng trạm/tháng; không tự gộp snapshot.")
    series, availability, coverage = {}, {}, []
    for station, group in frame.groupby("station"):
        group = group.set_index("month_start").sort_index()
        calendar = pd.date_range(group.index.min(), group.index.max(), freq="MS")
        group = group.reindex(calendar)
        for variable, definition in variables.items():
            if variable not in group:
                continue
            values = pd.to_numeric(group[variable], errors="raise").astype(float)
            if np.isinf(values).any():
                raise ForecastError(f"Số vô hạn trong {variable}.")
            if definition.get("nonnegative") and (values.dropna() < 0).any():
                raise ForecastError(f"Giá trị âm trong {variable}.")
            key = (station, variable)
            series[key] = values
            column = variable + "__available_at"
            if column in group:
                stamps = []
                for when, value in values.items():
                    if pd.isna(value):
                        stamps.append(pd.NaT)
                        continue
                    stamp = aware(group.at[when, column])
                    if stamp < end_of_month(when):
                        raise ForecastError("Giá trị tổng hợp tháng chưa hoàn tất không được khai báo có sẵn trước cuối tháng.")
                    stamps.append(stamp)
                mode = "DECLARED_TIMESTAMPS_NO_VINTAGE_CERTIFICATION"
            else:
                delay = definition["assumed_release_delay_days"]
                if not isinstance(delay, int) or isinstance(delay, bool) or delay < 0:
                    raise ForecastError("Độ trễ khả dụng phải là số nguyên không âm.")
                stamps = [end_of_month(t) + pd.Timedelta(days=delay) if pd.notna(v) else pd.NaT
                          for t, v in values.items()]
                mode = "ASSUMED_RELEASE_DELAY"
            availability[key] = pd.Series(pd.array(stamps, dtype=f"datetime64[ns, {TZ}]"), index=calendar)
            present = values.dropna()
            coverage.append(dict(station=station, variable=variable, count=len(present),
                                 first_month=present.index.min() if len(present) else None,
                                 last_month=present.index.max() if len(present) else None,
                                 unit=definition["unit"], metadata_status=definition["metadata_status"],
                                 availability_mode=mode))
    return {"series": series, "available": availability, "coverage": coverage, "registry": registry,
            "data_path": str(Path(path).resolve()), "data_sha256": sha(path),
            "registry_sha256": sha(registry_path)}


def feature_definitions(station, path):
    definitions = []
    if path in ("AR", "ARX"):
        definitions += [(station, TARGET, lag) for lag in (1, 2, 12)]
    if path in ("ARX", "EXOG", "EXOG_DELAYED", "HYDRO_PROXY"):
        lags = (3, 4) if path == "EXOG_DELAYED" else (2, 3)
        definitions += [(station, variable, lag) for variable in WEATHER for lag in lags]
    if path == "HYDRO_PROXY":
        definitions += [(station, "water_level_m", 2), ("TANCHAU", "glofas_discharge_m3s", 2)]
    return definitions


def snapshot(data, station, target, issued_at, path):
    target, issued_at = month(target), aware(issued_at)
    values = {"month_sin": float(np.sin(2 * np.pi * target.month / 12)),
              "month_cos": float(np.cos(2 * np.pi * target.month / 12))}
    evidence, missing = [], []
    for source_station, variable, lag in feature_definitions(station, path):
        source_month = target - pd.DateOffset(months=lag)
        key = (source_station, variable)
        name = f"{source_station}__{variable}__lag{lag}"
        value = data["series"].get(key, pd.Series(dtype=float)).get(source_month, np.nan)
        available = data["available"].get(key, pd.Series(dtype=object)).get(source_month, pd.NaT)
        reason = None
        if pd.isna(value):
            reason = "MISSING_VALUE"
        elif pd.isna(available) or available > issued_at:
            reason = "NOT_AVAILABLE_AT_ISSUE"
        values[name] = float(value) if reason is None else np.nan
        record = dict(feature=name, source_month=str(source_month.date()),
                      available_at=available.isoformat() if pd.notna(available) else None,
                      value=float(value) if reason is None else None, reason=reason)
        evidence.append(record)
        if reason:
            missing.append(record)
    return values, evidence, missing


def design_matrix(data, station, path):
    target = data["series"].get((station, TARGET))
    if target is None or target.notna().sum() == 0:
        raise ForecastError("Trạm không có nhãn EC.")
    rows = []
    for target_month in target.index:
        values, _, _ = snapshot(data, station, target_month, origin_for(target_month), path)
        rows.append(values)
    return pd.DataFrame(rows, index=target.index)


def training_rows(data, matrix, station, target, issued_at):
    y = data["series"][(station, TARGET)]
    availability = data["available"][(station, TARGET)]
    mask = (matrix.index < month(target)) & y.notna() & (availability <= aware(issued_at))
    mask &= np.isfinite(matrix.to_numpy(dtype=float)).all(axis=1)
    return matrix.loc[mask], y.loc[mask]


def estimator(spec, settings):
    if spec["algorithm"] == "RF":
        return RandomForestRegressor(n_estimators=settings.trees, random_state=settings.seed, n_jobs=1,
                                     max_depth=spec["max_depth"], min_samples_leaf=spec["min_samples_leaf"])
    return make_pipeline(StandardScaler(), Ridge(alpha=spec["alpha"]))


def predict_at(data, matrix, station, target, issued_at, path, spec, settings):
    target, issued_at = month(target), aware(issued_at)
    y = data["series"][(station, TARGET)]
    av = data["available"][(station, TARGET)]
    result = dict(station=station, path=path, model_id=spec.get("model_id", path),
                  target_month=str(target.date()), forecast_origin=issued_at.isoformat(),
                  actual=float(y.get(target, np.nan)), predicted=None, status="BLOCKED",
                  n_train=0, missing_features=[], source_grade="UNVERIFIED_RETAINED_NOT_VALIDATED")
    if path in BASELINES:
        known = y.loc[(y.index < target) & y.notna() & (av <= issued_at)]
        if path == "MONTHLY_CLIMATOLOGY":
            selected = known.loc[known.index.month == target.month]
            if len(selected) >= 3:
                result.update(predicted=float(selected.median()), n_train=len(known), status="OK")
        else:
            lag = 1 if path == "PERSISTENCE" else 12
            source = target - pd.DateOffset(months=lag)
            if source in known.index:
                result.update(predicted=float(known.loc[source]), n_train=len(known), status="OK")
            else:
                result["missing_features"] = [dict(feature=f"EC_exact_lag{lag}", source_month=str(source.date()))]
        return result
    values, evidence, missing = snapshot(data, station, target, issued_at, path)
    result["feature_evidence"] = evidence
    result["missing_features"] = missing
    if missing:
        return result
    x_train, y_train = training_rows(data, matrix, station, target, issued_at)
    result["n_train"] = len(y_train)
    if len(y_train) < settings.min_train:
        result["status"] = "INSUFFICIENT_TRAIN"
        return result
    fitted = estimator(spec, settings)
    response = np.log1p(y_train) if spec["algorithm"] == "RIDGE_LOG" else y_train
    fitted.fit(x_train, response)
    x = pd.DataFrame([values], columns=matrix.columns)
    predicted = float(fitted.predict(x)[0])
    if spec["algorithm"] == "RIDGE_LOG":
        predicted = float(np.expm1(predicted))
    if not np.isfinite(predicted):
        raise ForecastError("Mô hình trả kết quả không hữu hạn.")
    result.update(predicted=max(0.0, predicted), nonnegative_projection_applied=predicted < 0, status="OK",
                  train_last_target_month=str(y_train.index.max().date()),
                  max_train_label_available_at=av.loc[y_train.index].max().isoformat(),
                  out_of_training_range=[column for column in matrix.columns
                                         if x.at[0, column] < x_train[column].min() - 1e-10
                                         or x.at[0, column] > x_train[column].max() + 1e-10])
    return result


def metrics(rows):
    good = [r for r in rows if r["status"] == "OK" and r["actual"] is not None and np.isfinite(r["actual"])]
    if not good:
        return dict(n=0, mae=None, rmse=None, bias=None, interval_coverage=None, mean_interval_width=None)
    errors = np.array([r["predicted"] - r["actual"] for r in good])
    bands = [r for r in good if r.get("lower") is not None]
    return dict(n=len(good), mae=float(np.mean(abs(errors))), rmse=float(np.sqrt(np.mean(errors ** 2))),
                bias=float(np.mean(errors)), interval_coverage=float(np.mean([r["lower"] <= r["actual"] <= r["upper"] for r in bands])) if bands else None,
                mean_interval_width=float(np.mean([r["upper"] - r["lower"] for r in bands])) if bands else None)


def residual_radius(rows, coverage, min_count):
    errors = sorted(abs(r["predicted"] - r["actual"]) for r in rows
                    if r["status"] == "OK" and r["actual"] is not None and np.isfinite(r["actual"]))
    rank = math.ceil((len(errors) + 1) * coverage)
    if len(errors) < min_count or rank > len(errors):
        return None
    return float(errors[rank - 1])


def add_band(result, radius):
    result.update(lower=None, upper=None, interval_kind="EMPIRICAL_TIME_SERIES_RESIDUAL_BAND")
    if radius is not None and result["status"] == "OK":
        result.update(lower=max(0.0, result["predicted"] - radius), upper=result["predicted"] + radius)
    return result


def split_periods(y, settings):
    last = y.last_valid_index()
    if last is None:
        raise ForecastError("Không có nhãn.")
    calendar = pd.date_range(y.index.min(), last, freq="MS")
    total = settings.validation_months + settings.calibration_months + settings.test_months
    if len(calendar) < total + settings.min_train:
        raise ForecastError("Không đủ lịch sử cho train/validation/calibration/test.")
    test_start = len(calendar) - settings.test_months
    calibration_start = test_start - settings.calibration_months
    validation_start = calibration_start - settings.validation_months
    return {"train": calendar[:validation_start],
            "validation": calendar[validation_start:calibration_start],
            "calibration": calendar[calibration_start:test_start], "test": calendar[test_start:]}


def compact_csv(path, rows):
    records = []
    for row in rows:
        record = {key: value for key, value in row.items() if key != "feature_evidence"}
        for key, value in record.items():
            if isinstance(value, (dict, list)):
                record[key] = json.dumps(clean(value), ensure_ascii=False)
        records.append(record)
    pd.DataFrame(records).to_csv(path, index=False, encoding="utf-8-sig")


def evaluate_period(data, matrix, station, months, path, spec, settings, stage, radius=None, label_cutoff=None):
    rows = []
    for target in months:
        row = predict_at(data, matrix, station, target, origin_for(target), path, spec, settings)
        # Late labels cannot select hyperparameters or calibrate an interval before they exist.
        label_time = data["available"][(station, TARGET)].get(target, pd.NaT)
        if label_cutoff is not None and (pd.isna(label_time) or label_time > label_cutoff):
            row["actual"] = None
        row["stage"] = stage
        rows.append(add_band(row, radius))
    return rows


def train(data_path, registry_path, station, output_root, settings, include_hydro=False):
    settings.validate()
    station = station_code(station)
    data = read_data(data_path, registry_path)
    periods = split_periods(data["series"][(station, TARGET)], settings)
    paths = list(PATHS) + (["HYDRO_PROXY"] if include_hydro else [])
    matrices = {path: design_matrix(data, station, path) for path in paths}
    selection, val_all, cal_all, test_all = {}, [], [], []
    cutoff = origin_for(periods["calibration"][0])
    calibration_cutoff = origin_for(periods["test"][0])
    for path in [*BASELINES, *paths]:
        candidates = [{"model_id": path, "algorithm": path}] if path in BASELINES else [
            {**spec, "model_id": f"{path}_{i}"} for i, spec in enumerate(MODEL_SPECS)]
        tested = []
        for spec in candidates:
            rows = evaluate_period(data, matrices.get(path), station, periods["validation"], path, spec,
                                   settings, "validation", label_cutoff=cutoff)
            val_all.extend(rows)
            score = metrics(rows)
            if score["n"] >= settings.min_eval:
                tested.append((score["mae"], spec, score))
        if not tested:
            selection[path] = {"status": "NO_ELIGIBLE_VALIDATION", "spec": None}
            print(f"{station} {path}: thiếu tháng validation đủ điều kiện", flush=True)
            continue
        _, spec, score = min(tested, key=lambda item: (item[0], item[1]["model_id"]))
        selection[path] = {"status": "SELECTED_ON_VALIDATION", "spec": spec, "validation": score}
        print(f"{station} {path}: {spec['model_id']}, validation MAE={score['mae']:.4f}", flush=True)
    # Selection is complete before any calibration/test outcome is inspected.
    for path, selected in selection.items():
        if selected["spec"] is None:
            continue
        spec = selected["spec"]
        cal = evaluate_period(data, matrices.get(path), station, periods["calibration"], path, spec,
                              settings, "calibration", label_cutoff=calibration_cutoff)
        radius = residual_radius(cal, settings.interval_coverage, settings.min_eval)
        selected.update(residual_radius=radius, calibration_count=metrics(cal)["n"])
        cal_all.extend(cal)
        test_all.extend(evaluate_period(data, matrices.get(path), station, periods["test"], path, spec,
                                        settings, "test", radius=radius))
    metric_rows = []
    successful_months = {path: {r["target_month"] for r in test_all if r["path"] == path
                               and r["status"] == "OK" and r["actual"] is not None and np.isfinite(r["actual"])}
                         for path in selection if selection[path]["spec"] is not None}
    core = [p for p in successful_months if p != "HYDRO_PROXY"]
    common = set.intersection(*(successful_months[p] for p in core)) if core else set()
    for path in successful_months:
        own = [r for r in test_all if r["path"] == path]
        metric_rows.append(dict(path=path, cohort="AVAILABLE", **metrics(own)))
        metric_rows.append(dict(path=path, cohort="COMMON_CORE", **metrics([r for r in own if r["target_month"] in common])))
    if len(common) < settings.min_eval:
        raise ForecastError("Không đủ tháng test chung giữa các nhánh chính; không công bố so sánh thiếu độ phủ.")
    out = new_run(output_root, station)
    contract = dict(schema_version=1, script_version=VERSION, station=station, target=TARGET, unit="mS/m",
                    temporal_resolution="MONTH", spatial_scope="MRC_STATION", settings=asdict(settings),
                    selection=selection, selection_cutoff=cutoff.isoformat(),
                    calibration_cutoff=calibration_cutoff.isoformat(),
                    selection_rule="Validation MAE within each fixed feature path; no test-based fallback choice",
                    interval_note="Residual band from a separate historical period; no guaranteed coverage under dependence or drift.",
                    gate_decision_eligible=False, deployment_ready=False,
                    core_validation_ranking=sorted((p for p in core), key=lambda p: (selection[p]["validation"]["mae"], p)),
                    input_data_sha256=data["data_sha256"], registry_sha256=data["registry_sha256"],
                    last_observed_target=str(data["series"][(station, TARGET)].last_valid_index().date()),
                    source_quality="UNVERIFIED_RETAINED", registry=data["registry"])
    save_json(out / "model_contract.json", contract)
    save_json(out / "coverage.json", data["coverage"])
    save_json(out / "split_manifest.json", {name: dict(first=str(index.min().date()), last=str(index.max().date()), months=len(index)) for name, index in periods.items()})
    compact_csv(out / "validation_predictions.csv", val_all)
    compact_csv(out / "calibration_predictions.csv", cal_all)
    compact_csv(out / "test_predictions.csv", test_all)
    pd.DataFrame(metric_rows).to_csv(out / "metrics.csv", index=False, encoding="utf-8-sig")
    for path, matrix in matrices.items():
        matrix.to_csv(out / f"features_{path}.csv", index_label="target_month", encoding="utf-8-sig")
    report = [f"# Dự báo EC đa biến — {station}", "", "Đây là thí nghiệm lịch sử, chưa đủ điều kiện ra quyết định vận hành cống.", "",
              "| Nhánh | Số tháng test chung | MAE (mS/m) | RMSE (mS/m) | Độ phủ dải sai số thực nghiệm |", "|---|---:|---:|---:|---:|"]
    for record in metric_rows:
        if record["cohort"] == "COMMON_CORE":
            render = lambda value: "—" if value is None else f"{value:.4f}"
            report.append(f"| {record['path']} | {record['n']} | {render(record['mae'])} | {render(record['rmse'])} | {render(record['interval_coverage'])} |")
    report += ["", "AR: EC quá khứ; ARX: EC và khí tượng; EXOG: khí tượng trễ 2/3 tháng; EXOG_DELAYED: trễ 3/4 tháng.",
               "HYDRO_PROXY nếu có là thí nghiệm trên biến đại diện khu vực chưa chứng nhận tại trạm/cống.",
               "Nhãn EC vẫn UNVERIFIED. Khí tượng là snapshot tái phân tích, không có đầy đủ lịch sử phiên bản phát hành.",
               "Test 2022–2023 đã từng được xem trong các đợt trước của dự án; không coi là test mù độc lập.",
               "Mỗi kỳ chỉ dùng giá trị đủ thời gian khả dụng theo hồ sơ. Thiếu tháng giữ thiếu; không nội suy nhãn/điền lưu lượng bằng 0.",
               "Không thay đổi lựa chọn mô hình theo kết quả test. Dải sai số được hiệu chỉnh trên giai đoạn riêng trước test."]
    (out / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    if sha(data_path) != data["data_sha256"] or sha(registry_path) != data["registry_sha256"]:
        raise ForecastError("Đầu vào thay đổi trong lúc chạy.")
    save_json(out / "run_manifest.json", dict(status="EXPERIMENT_COMPLETE", software=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__, sklearn=sklearn.__version__),
              script_sha256=sha(__file__), source_files_unchanged=True, data_sha256=data["data_sha256"], registry_sha256=data["registry_sha256"],
              common_test_months=len(common), generated_at=datetime.now(timezone.utc).isoformat(), gate_decision_eligible=False,
              output_hashes={p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()}))
    return out, contract, metric_rows


def infer(data_path, registry_path, contract_path, request_path, output_root):
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    if contract.get("schema_version") != 1 or contract.get("script_version") != VERSION:
        raise ForecastError("Contract không tương thích phiên bản script.")
    station = station_code(request["station"])
    if station != contract["station"]:
        raise ForecastError("Trạm trong request khác contract.")
    issued = aware(request["issue_time"])
    target = month(request["target_month"])
    issue_month = issued.tz_localize(None).to_period("M").to_timestamp()
    if target != issue_month + pd.DateOffset(months=1):
        raise ForecastError("Phiên bản này chỉ nhận tháng mục tiêu kế tiếp tháng phát hành.")
    if issued > pd.Timestamp.now(tz=TZ):
        raise ForecastError("Không khai báo thời điểm phát hành trong tương lai.")
    if issued < max(aware(contract["selection_cutoff"]), aware(contract["calibration_cutoff"])):
        raise ForecastError("Contract còn dùng kết quả chọn mô hình/hiệu chỉnh sai số sau thời điểm yêu cầu suy luận.")
    data = read_data(data_path, registry_path)
    if data["registry_sha256"] != contract["registry_sha256"]:
        raise ForecastError("Registry khác contract; cần huấn luyện/kiểm định lại sau thay đổi định nghĩa hoặc độ trễ.")
    settings = Settings(**contract["settings"])
    results = []
    for path, chosen in contract["selection"].items():
        if chosen["spec"] is None:
            results.append(dict(path=path, status="NO_ELIGIBLE_VALIDATION", predicted=None))
            continue
        matrix = None if path in BASELINES else design_matrix(data, station, path)
        row = predict_at(data, matrix, station, target, issued, path, chosen["spec"], settings)
        add_band(row, chosen["residual_radius"])
        row["validation_mae"] = chosen["validation"]["mae"]
        # Never echo a target actual in an inference result, even if the CSV contains it.
        row.pop("actual", None)
        results.append(row)
    by_path = {r["path"]: r for r in results}
    eligible = [p for p in contract["core_validation_ranking"] if by_path[p]["status"] == "OK"]
    selected = by_path[eligible[0]] if eligible else None
    available_y = data["series"][(station, TARGET)].loc[data["available"][(station, TARGET)] <= issued].dropna()
    last_label = available_y.index.max() if len(available_y) else None
    label_age = (target.year - last_label.year) * 12 + target.month - last_label.month if last_label is not None else None
    result = dict(status="EXPERIMENTAL_FORECAST" if selected else "BLOCKED_MISSING_INPUTS", station=station,
                  target_month=str(target.date()), forecast_origin=issued.isoformat(), generated_at=datetime.now(timezone.utc).isoformat(),
                  horizon_calendar_months=1, temporal_resolution="MONTH", spatial_scope="MRC_STATION", unit="mS/m", parameter="EC",
                  source_quality="UNVERIFIED_RETAINED", ec_temperature_basis="UNKNOWN",
                  selected=selected, all_paths=results, last_available_label=str(last_label.date()) if last_label is not None else None,
                  label_age_months=label_age, gate_decision_eligible=False, deployment_ready=False,
                  required_feature_updates=[r for row in results for r in row.get("missing_features", [])],
                  limitations=["No recent EC validation after the last available target; old residual bands can be miscalibrated.",
                               "Availability assumptions do not certify historical release vintages or sensor QA.",
                               "Monthly station prediction cannot be substituted for a gate-local hourly forecast."],
                  selection_rule="First available path in the frozen validation ranking; no selection using target/test errors.",
                  data_sha256=data["data_sha256"], contract_sha256=sha(contract_path), registry_sha256=data["registry_sha256"])
    out = new_run(output_root, station + "_inference")
    save_json(out / "forecast.json", result)
    return out, result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("train", "predict"):
        p = sub.add_parser(name)
        p.add_argument("--data", type=Path, default=ROOT / "data/processed/master_timeseries.csv")
        p.add_argument("--registry", type=Path, default=ROOT / "data/metadata/forecast_sources.json")
        p.add_argument("--output-dir", type=Path, default=ROOT / "runs/forecast_multivariate")
        if name == "train":
            p.add_argument("--station", required=True)
            p.add_argument("--include-hydro-proxies", action="store_true")
        else:
            p.add_argument("--contract", type=Path, required=True)
            p.add_argument("--request", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "train":
            out, _, _ = train(args.data, args.registry, args.station, args.output_dir, Settings(), args.include_hydro_proxies)
            summary = dict(status="EXPERIMENT_COMPLETE", output=str(out))
        else:
            out, result = infer(args.data, args.registry, args.contract, args.request, args.output_dir)
            summary = dict(status=result["status"], output=str(out), selected_path=result["selected"]["path"] if result["selected"] else None,
                           target_month=result["target_month"], gate_decision_eligible=False)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2 if summary["status"].startswith("BLOCKED") else 0
    except (ValueError, KeyError, OSError) as exc:
        print(json.dumps(dict(status="ERROR", message=str(exc)), ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
