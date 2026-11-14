"""Offline three-station EC evaluation; never changes the registry, database or UI.

Reuses the rolling-origin issue/availability rules and fixed RF parameters of
backtest_asof_ec.py. My Thuan EC is a target, never an input to My Tho.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import math
import ssl
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import joblib
import numpy as np
import pandas as pd
import sklearn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.domain.multivariate_ec import FEATURES, UNITS
from backend.repositories.multivariate_inputs import get_monthly_weather, _aggregate
from backend.services.spatial_simulation import RiverAxis, _read_corridor
from scripts.backtest_asof_ec import available_date_for, issue_date_for, split_for
from scripts.train_multivariate_ec import pipeline

OUTPUT = ROOT / "outputs/mythuan_three_station_20261104"
WEATHER = ROOT / "data/external/mythuan_weather_20261104"
MID_SOURCE = ROOT / "data/external/tien_multisite_20261029_verified"
END_SOURCE = ROOT / "data/external/mrc_20261014_network"
SOURCES = {
    "TANCHAU": END_SOURCE / "019803_Conductivity_Water_Quality_bc365241.csv",
    "MYTHUAN": MID_SOURCE / "019804_Conductivity_Water Quality_4c105414.csv",
    "MYTHO": END_SOURCE / "019805_Conductivity_Water_Quality_acce65db.csv",
}
MODELS = ("RandomForest", "Persistence", "MonthlyClimatology")
METHODS = ("TWO_OBSERVED_LINEAR", "TWO_FORECAST_LINEAR",
           "THREE_FORECAST_ANCHOR", "TWO_OBSERVED_IDW2", "TWO_FORECAST_IDW2")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def station_metadata():
    manifest = json.loads((MID_SOURCE / "manifest.json").read_text("utf-8"))
    return next(r for r in manifest["series"] if r["file"] == SOURCES["MYTHUAN"].name)


def fetch_weather(directory=WEATHER):
    """Download ERA5 at the existing MRC My Thuan station, in an isolated archive."""
    from scripts.update_multivariate_weather import verified_context
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "manifest.json"
    manifest = json.loads(path.read_text("utf-8")) if path.exists() else {"schema_version": 1, "retrievals": []}
    site = station_metadata()
    for year in range(1985, 2027, 5):
        start = date(year, 1, 1)
        # Match the existing stations' complete ERA5 archive through 09/2026.
        # Do not accept incomplete recent rainfall totals as monthly inputs.
        end = min(date(year + 4, 12, 31), date(2026, 9, 30))
        filename = f"era5_MyThuan_{start}_{end}.json"
        cached = next((r for r in manifest["retrievals"] if r["file"] == filename), None)
        if cached and (directory / filename).exists() and digest(directory / filename) == cached["sha256"]:
            print(f"Cached {filename}", flush=True)
            continue
        params = dict(latitude=site["latitude"], longitude=site["longitude"],
                      start_date=str(start), end_date=str(end),
                      daily="precipitation_sum,temperature_2m_mean,wind_speed_10m_mean",
                      models="era5", timezone="Asia/Ho_Chi_Minh", wind_speed_unit="ms",
                      temperature_unit="celsius", precipitation_unit="mm")
        url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(params)
        with urlopen(url, context=verified_context(), timeout=60) as response:
            raw = response.read()
        payload = json.loads(raw)
        if payload.get("error"):
            raise ValueError(payload.get("reason"))
        units = payload["daily_units"]
        if (units.get("wind_speed_10m_mean") != "m/s" or units.get("precipitation_sum") != "mm"
                or units.get("temperature_2m_mean") not in ("\u00b0C", "celsius")):
            raise ValueError(f"Unexpected weather units: {filename}")
        daily = payload["daily"]
        expected = pd.date_range(start, end).strftime("%Y-%m-%d").tolist()
        if daily["time"] != expected:
            raise ValueError(f"Incomplete weather dates: {filename}")
        for key in ("precipitation_sum", "temperature_2m_mean", "wind_speed_10m_mean"):
            if len(daily[key]) != len(expected) or any(v is None or not math.isfinite(v) for v in daily[key]):
                raise ValueError(f"Incomplete weather values: {filename} {key}")
        (directory / filename).write_bytes(raw)
        record = dict(station="MyThuan", file=filename, sha256=digest(directory / filename),
                      retrieved_at=datetime.now(timezone.utc).isoformat(), url=url,
                      request_parameters=params, daily_units=units,
                      start_date=str(start), end_date=str(end),
                      source="Open-Meteo archive / ERA5", license="CC-BY-4.0",
                      citation="ERA5 / Copernicus Climate Change Service via Open-Meteo")
        manifest["retrievals"] = [r for r in manifest["retrievals"] if r["file"] != filename] + [record]
        manifest["updated_at"] = record["retrieved_at"]
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"Downloaded {filename}: {len(expected)} days", flush=True)


def load_mid_weather(directory=WEATHER):
    records = []
    manifest = json.loads((directory / "manifest.json").read_text("utf-8"))
    for record in manifest["retrievals"]:
        filename = record["file"]
        if Path(filename).name != filename or digest(directory / filename) != record["sha256"]:
            raise ValueError("My Thuan weather checksum/path mismatch")
        payload = json.loads((directory / filename).read_text("utf-8"))
        units, params = payload["daily_units"], record["request_parameters"]
        if (units["wind_speed_10m_mean"] != "m/s" or units["precipitation_sum"] != "mm"
                or units["temperature_2m_mean"] not in ("\u00b0C", "celsius")
                or params["models"] != "era5" or params["timezone"] != "Asia/Ho_Chi_Minh"):
            raise ValueError("Unverified My Thuan weather model/units")
        daily = payload["daily"]
        columns = ("time", "precipitation_sum", "temperature_2m_mean", "wind_speed_10m_mean")
        if len({len(daily[c]) for c in columns}) != 1:
            raise ValueError("Unequal daily weather arrays")
        groups = {}
        for row in zip(*(daily[c] for c in columns)):
            groups.setdefault(row[0][:7], []).append(row)
        records.extend(_aggregate("MyThuan", month, rows, {}) for month, rows in groups.items())
    result = pd.DataFrame(records)
    if result.input_month.duplicated().any():
        raise ValueError("Overlapping My Thuan weather months")
    return records


def load_targets():
    metadata = station_metadata()
    if digest(SOURCES["MYTHUAN"]) != metadata["extracted_sha256"]:
        raise ValueError("My Thuan EC checksum mismatch")
    pieces = []
    for station, path in SOURCES.items():
        raw = pd.read_csv(path)
        local = pd.to_datetime(raw.observed_at, utc=True).dt.tz_convert("Asia/Ho_Chi_Minh")
        piece = pd.DataFrame(dict(station=station,
            month_start=local.dt.tz_localize(None).dt.to_period("M").dt.to_timestamp(),
            conductivity_mS_per_m=pd.to_numeric(raw.value, errors="raise"),
            sample_date=local.dt.strftime("%Y-%m-%d"), quality_flag=raw.quality_flag,
            ec_temperature_basis=raw.ec_temperature_basis, sample_count=1))
        if (not raw.unit.eq("mS/m").all() or piece.month_start.duplicated().any()
                or not np.isfinite(piece.conductivity_mS_per_m).all()
                or piece.conductivity_mS_per_m.lt(0).any()):
            raise ValueError(f"Invalid or duplicate EC target: {station}")
        pieces.append(piece)
    result = pd.concat(pieces, ignore_index=True)
    if len(result[result.station.eq("MYTHUAN")]) != 451:
        raise ValueError("Expected exactly 451 original My Thuan EC samples")
    # Endpoint targets must agree with the currently deployed training dataset.
    canonical = pd.read_csv(ROOT / "data/research/mrc_ec_monthly_samples.csv", parse_dates=["month_start"])
    joined = canonical.merge(result, on=["station", "month_start"], validate="one_to_one", suffixes=("_old", "_new"))
    if len(joined) != len(canonical) or not np.allclose(joined.conductivity_mS_per_m_old, joined.conductivity_mS_per_m_new, rtol=0, atol=1e-12):
        raise ValueError("Endpoint targets differ from existing model targets")
    return result


def build_frame(targets, weather_directory=WEATHER):
    rows = [r for station in ("TANCHAU", "MYTHO") for r in get_monthly_weather(station)]
    rows.extend(load_mid_weather(weather_directory))
    weather = pd.DataFrame(rows)
    weather["station"] = weather.station.str.upper()
    weather["weather_month"] = pd.to_datetime(weather.input_month)
    targets = targets.copy()
    targets["weather_month"] = targets.month_start - pd.DateOffset(months=2)
    frame = targets.merge(weather[["station", "weather_month"] + list(UNITS)[:3]],
                          on=["station", "weather_month"], how="left", validate="many_to_one")
    if frame[list(UNITS)[:3]].isna().any().any():
        raise ValueError("Missing complete target-minus-two weather")
    frame["month_sin"] = np.sin(2 * np.pi * frame.month_start.dt.month / 12)
    frame["month_cos"] = np.cos(2 * np.pi * frame.month_start.dt.month / 12)
    frame["weather_available_at"] = frame.weather_month.map(lambda m: available_date_for(m, 5))
    return frame


def known_training_rows(data, target_month, ec_delay):
    issue = issue_date_for(target_month)
    ec_available = data.month_start.map(lambda m: available_date_for(m, ec_delay))
    return data[(data.month_start < target_month) & (ec_available <= issue)
                & (data.weather_available_at <= issue)].copy()


def score(actual, predicted):
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if len(actual) == 0 or actual.shape != predicted.shape or not np.isfinite([actual, predicted]).all():
        raise ValueError("Metrics require a nonempty, finite matched cohort")
    error = predicted - actual
    return dict(n=len(error), mae_mS_m=float(np.abs(error).mean()),
                rmse_mS_m=float(np.sqrt(np.square(error).mean())), bias_mS_m=float(error.mean()))


def endpoint_interpolation(upstream, downstream, fraction, power=1):
    if (not all(math.isfinite(float(v)) for v in (upstream, downstream, fraction))
            or upstream < 0 or downstream < 0 or not 0 <= fraction <= 1 or power <= 0):
        raise ValueError("Invalid EC, along-river fraction or interpolation power")
    if fraction in (0, 1):
        return upstream if fraction == 0 else downstream
    # power 1 is linear interpolation, power 2 reproduces the historical IDW.
    a, b = (1 - fraction) ** power, fraction ** power
    return (a * upstream + b * downstream) / (a + b)


def geometry():
    _, coordinates = _read_corridor()
    site = station_metadata()
    projection = RiverAxis(coordinates).project([site["longitude"], site["latitude"]])
    fraction = projection["chainage_km"] / 125.0
    if not 0 < fraction < 1:
        raise ValueError("My Thuan must project between Tan Chau and My Tho")
    return dict(**projection, coordinate=[site["longitude"], site["latitude"]],
                tan_chau_chainage_km=0.0, my_tho_chainage_km=125.0,
                along_river_fraction=fraction,
                corridor_sha256=digest(ROOT / "data/biengioi/tien_river_corridor.geojson"),
                note="Chainage uses the existing WebGIS rescaled river axis, not straight-line distance.")


def interpolation_benchmark(predictions, fraction):
    records = []
    for (delay, split, month), group in predictions.groupby(["ec_delay_days", "split", "target_month"]):
        stations = group.set_index("station")
        if set(stations.index) != set(SOURCES) or len(stations) != 3:
            raise ValueError("Interpolation requires exactly the three matched stations")
        tc, mt, my = (stations.loc[s] for s in ("TANCHAU", "MYTHUAN", "MYTHO"))
        record = dict(ec_delay_days=delay, split=split, target_month=month,
            actual_mS_m=mt.actual_mS_m, tan_chau_actual=tc.actual_mS_m,
            my_tho_actual=my.actual_mS_m, tan_chau_forecast=tc.RandomForest,
            my_tho_forecast=my.RandomForest, tan_chau_sample_date=tc.sample_date,
            my_thuan_sample_date=mt.sample_date, my_tho_sample_date=my.sample_date,
            all_three_same_sample_date=tc.sample_date == mt.sample_date == my.sample_date,
            TWO_OBSERVED_LINEAR=endpoint_interpolation(tc.actual_mS_m, my.actual_mS_m, fraction),
            TWO_FORECAST_LINEAR=endpoint_interpolation(tc.RandomForest, my.RandomForest, fraction),
            THREE_FORECAST_ANCHOR=float(mt.RandomForest),
            TWO_OBSERVED_IDW2=endpoint_interpolation(tc.actual_mS_m, my.actual_mS_m, fraction, 2),
            TWO_FORECAST_IDW2=endpoint_interpolation(tc.RandomForest, my.RandomForest, fraction, 2))
        records.append(record)
    return pd.DataFrame(records)


def write_report(output, metrics, spatial, improvements, axis):
    primary = metrics[(metrics.station == "MYTHUAN") & (metrics.ec_delay_days == 5)
                      & (metrics.split == "historical_2022_2023")]
    table = spatial[(spatial.ec_delay_days == 5) & (spatial.split == "historical_2022_2023")
                    & (spatial.cohort == "all_matched_months")]
    lines = ["# Kiểm chứng Mỹ Thuận và nội suy ba trạm · 04/11/2026", "",
        "Báo cáo Bước 1 và Bước 2; chưa thay registry, database hoặc giao diện.", "",
        "## Giao thức", "",
        "- Đúng ba trạm: Tân Châu → Mỹ Thuận → Mỹ Tho. EC mS/m, một mẫu/tháng; không đổi sang g/L.",
        "- Mỹ Thuận: 451 mẫu 05/1985–12/2023. Giữ QA UNVERIFIED và cơ sở bù nhiệt UNKNOWN.",
        "- Giữ nguyên RF 300 cây, sâu 8, lá tối thiểu 3, seed 42; mưa/nhiệt/gió ERA5 tháng t−2 và sin/cos tháng mục tiêu. Không chọn siêu tham số từ kỳ 2022–2023.",
        "- Rolling-origin giống backtest hiện có: phát hành ngày 06 tháng t−1; mỗi lần chỉ dùng nhãn đã khả dụng và khí tượng đã khả dụng. EC giả định công bố cuối tháng +5 ngày; +35 ngày là độ nhạy. ERA5 cuối tháng +5 ngày.",
        "- 2019–2021 là kỳ validation; 2022–2023 là kiểm tra hồi cứu đã được xem trước trong dự án, không phải holdout mù mới. Mô hình được huấn luyện lại từng ngày phát hành bằng tập quá khứ đang khả dụng.",
        "- Persistence dùng mẫu gần nhất đã khả dụng; MonthlyClimatology dùng trung bình đúng tháng trong tập huấn luyện đang khả dụng. Cùng cohort cho mọi phương án.",
        "- Khí tượng Mỹ Thuận được tải tại tọa độ MRC của chính trạm, không lấy khí tượng Mỹ Tho thay thế. Bản ERA5 hồi cứu hiện có không phải bản phát hành lịch sử.", "",
        "## Bước 1 — Dự báo EC Mỹ Thuận, 2022–2023 (+5 ngày)", "",
        "| Mô hình | n | MAE (mS/m) | RMSE (mS/m) |", "|---|---:|---:|---:|"]
    for r in primary.itertuples():
        lines.append(f"| {r.model} | {r.n} | {r.mae_mS_m:.6f} | {r.rmse_mS_m:.6f} |")
    lines += ["", "## Bước 2 — Ước tính tại Mỹ Thuận, 2022–2023 (+5 ngày)", "",
        f"Tọa độ Mỹ Thuận: {axis['coordinate']}; chiếu lên trục hiện tại tại km {axis['chainage_km']:.6f} trong đoạn 0–125 km. Tỷ lệ dọc tuyến {axis['along_river_fraction']:.9f}; khoảng cách đến trục {axis['distance_to_axis_km']:.3f} km. Giữ nguyên hình học và công thức trước khi xem sai số.", "",
        "| Phương án | n | MAE (mS/m) | RMSE (mS/m) |", "|---|---:|---:|---:|"]
    for r in table.itertuples():
        lines.append(f"| {r.method} | {r.n} | {r.mae_mS_m:.6f} | {r.rmse_mS_m:.6f} |")
    lines += ["", "LINEAR là phép nội suy theo khoảng cách dọc sông của lớp phủ dự báo hiện tại; IDW2 kiểm độ nhạy với công thức mô phỏng lịch sử. TWO_OBSERVED là tái dựng hồi cứu từ quan trắc cùng tháng ở hai đầu mút, không phải đầu vào có sẵn tại ngày phát hành dự báo.", "",
        "THREE_FORECAST_ANCHOR dùng dự báo Mỹ Thuận ngoài mẫu tại đúng vị trí Mỹ Thuận; không dùng EC thực đo Mỹ Thuận làm điểm neo khi chấm. Vì vậy sai số tại đây bằng sai số mô hình Mỹ Thuận ở Bước 1. Kết quả chỉ chứng minh tại vị trí trung lưu này, không đo được sai số toàn tuyến sông.", "",
        "Các mẫu ghép cùng tháng không mặc nhiên cùng ngày hoặc cùng pha triều. interpolation_metrics.csv có thêm cohort cùng ngày của cả ba trạm; interpolation_predictions.csv giữ ngày mẫu từng trạm.", "",
        "## Mức thay đổi so với hai trạm", "",
        "Giảm (%) = 100 × (lỗi hai trạm − lỗi điểm neo Mỹ Thuận dự báo) / lỗi hai trạm. Giá trị âm là sai số tăng.", "",
        "| So với | Giảm MAE (%) | Giảm RMSE (%) |", "|---|---:|---:|"]
    for r in improvements[(improvements.ec_delay_days == 5) & (improvements.split == "historical_2022_2023") & (improvements.cohort == "all_matched_months")].itertuples():
        lines.append(f"| {r.baseline} | {r.mae_reduction_pct:.3f} | {r.rmse_reduction_pct:.3f} |")
    lines += ["", "## Tái tạo và tệp kết quả", "", "```powershell",
        ".venv/Scripts/python.exe scripts/evaluate_mythuan_three_station.py --fetch-weather",
        ".venv/Scripts/python.exe -m unittest tests.test_mythuan_three_station", "```", "",
        "- targets.csv / feature_matrix.csv: nhãn và đặc trưng theo trạm/tháng.",
        "- predictions.csv / model_metrics.csv: dự báo, ngày phát hành, tháng nhãn cuối khả dụng, MAE/RMSE cho ba trạm, hai giả định trễ.",
        "- interpolation_predictions.csv / interpolation_metrics.csv / improvements.csv: từng tháng, cùng ngày, và tỷ lệ thay đổi.",
        "- source_audit.csv / run_manifest.json: kiểm kê và checksum nguồn, giao thức, hình học, phiên bản thư viện và checksum đầu ra.",
        "- mythuan_model.joblib: mô hình cuối fit 451 nhãn; chỉ là artifact offline, chưa thay mô hình phục vụ.", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")


def run(output=OUTPUT, delays=(5, 35)):
    output.mkdir(parents=True, exist_ok=True)
    targets = load_targets()
    frame = build_frame(targets)
    targets.to_csv(output / "targets.csv", index=False)
    frame.to_csv(output / "feature_matrix.csv", index=False)
    audit = []
    for station, data in targets.groupby("station"):
        holdout = data[data.month_start.between("2022-01-01", "2023-12-01")]
        if len(holdout) != 24:
            raise ValueError(f"Incomplete 2022-2023 cohort: {station}")
        audit.append(dict(station=station, rows=len(data), first_date=data.sample_date.min(),
                          last_date=data.sample_date.max(), evaluation_rows=len(holdout),
                          source_sha256=digest(SOURCES[station]), quality_flags="|".join(sorted(data.quality_flag.unique()))))
    pd.DataFrame(audit).to_csv(output / "source_audit.csv", index=False)
    predictions = []
    for station, data in frame.groupby("station", sort=True):
        data = data.sort_values("month_start")
        for delay in delays:
            for target in data.itertuples():
                split = split_for(target.month_start.date())
                if split is None:
                    continue
                issue = issue_date_for(target.month_start)
                if target.weather_available_at > issue:
                    raise ValueError("Target weather unavailable at issue date")
                known = known_training_rows(data, target.month_start, delay)
                if len(known) < 96:
                    raise ValueError("Too few known training labels")
                fitted = pipeline().set_params(randomforestregressor__n_jobs=1).fit(known[FEATURES], known.conductivity_mS_per_m)
                target_x = data.loc[data.month_start.eq(target.month_start), FEATURES]
                climate = known.loc[known.month_start.dt.month.eq(target.month_start.month), "conductivity_mS_per_m"].mean()
                predictions.append(dict(station=station, ec_delay_days=delay, split=split,
                    target_month=target.month_start.strftime("%Y-%m-%d"), issue_date_local=str(issue),
                    weather_month=str(target.weather_month.date()), weather_available_at=str(target.weather_available_at),
                    training_months=len(known), last_training_ec_month=str(known.month_start.iloc[-1].date()),
                    last_training_ec_available_at=str(available_date_for(known.month_start.iloc[-1], delay)),
                    sample_date=target.sample_date, actual_mS_m=target.conductivity_mS_per_m,
                    RandomForest=float(fitted.predict(target_x)[0]),
                    Persistence=float(known.conductivity_mS_per_m.iloc[-1]), MonthlyClimatology=float(climate)))
            print(f"Evaluated {station}, EC delay +{delay} days", flush=True)
            pd.DataFrame(predictions).to_csv(output / "predictions.partial.csv", index=False)
    predictions = pd.DataFrame(predictions)
    if len(predictions) != 3 * len(delays) * 60 or predictions.duplicated(["station", "ec_delay_days", "target_month"]).any():
        raise ValueError("Wrong evaluation cohort")
    predictions.to_csv(output / "predictions.csv", index=False)
    metrics = []
    for (station, delay, split), group in predictions.groupby(["station", "ec_delay_days", "split"]):
        for model in MODELS:
            metrics.append(dict(station=station, ec_delay_days=delay, split=split,
                                model=model, **score(group.actual_mS_m, group[model])))
    metrics = pd.DataFrame(metrics)
    metrics.to_csv(output / "model_metrics.csv", index=False)
    axis = geometry()
    bench = interpolation_benchmark(predictions, axis["along_river_fraction"])
    bench.to_csv(output / "interpolation_predictions.csv", index=False)
    spatial, improvements = [], []
    for (delay, split), group in bench.groupby(["ec_delay_days", "split"]):
        for cohort in ("all_matched_months", "all_three_same_sample_date"):
            selected = group if cohort == "all_matched_months" else group[group.all_three_same_sample_date]
            if selected.empty:
                continue
            anchor = score(selected.actual_mS_m, selected.THREE_FORECAST_ANCHOR)
            for method in METHODS:
                result = score(selected.actual_mS_m, selected[method])
                spatial.append(dict(ec_delay_days=delay, split=split, cohort=cohort, method=method, **result))
                if method != "THREE_FORECAST_ANCHOR":
                    improvements.append(dict(ec_delay_days=delay, split=split, cohort=cohort, baseline=method,
                        n=len(selected), mae_reduction_pct=100 * (result["mae_mS_m"] - anchor["mae_mS_m"]) / result["mae_mS_m"],
                        rmse_reduction_pct=100 * (result["rmse_mS_m"] - anchor["rmse_mS_m"]) / result["rmse_mS_m"]))
    spatial, improvements = pd.DataFrame(spatial), pd.DataFrame(improvements)
    spatial.to_csv(output / "interpolation_metrics.csv", index=False)
    improvements.to_csv(output / "improvements.csv", index=False)
    mid = frame[frame.station.eq("MYTHUAN")].sort_values("month_start")
    final = pipeline().set_params(randomforestregressor__n_jobs=1).fit(mid[FEATURES], mid.conductivity_mS_per_m)
    joblib.dump(final, output / "mythuan_model.joblib")
    write_report(output, metrics, spatial, improvements, axis)
    source_paths = list(SOURCES.values()) + [MID_SOURCE / "manifest.json", ROOT / "data/research/mrc_ec_monthly_samples.csv",
        ROOT / "data/external/multivariate_weather/manifest.json", WEATHER / "manifest.json", Path(__file__),
        ROOT / "scripts/backtest_asof_ec.py", ROOT / "scripts/train_multivariate_ec.py"]
    for directory in (ROOT / "data/external/multivariate_weather", WEATHER):
        archive = json.loads((directory / "manifest.json").read_text("utf-8"))
        source_paths.extend(directory / r["file"] for r in archive["retrievals"])
    manifest = dict(schema_version=1, created_at=datetime.now(timezone.utc).isoformat(),
        steps_completed=[1, 2], ui_modified=False, deployed_registry_modified=False,
        stations=list(SOURCES), target_unit="mS/m", feature_order=FEATURES, feature_units=UNITS,
        evaluation_protocol="Rolling-origin; validation 2019-2021; retrospective evaluation 2022-2023; no tuning on evaluation",
        issue_rule="day 6 of t-1 in Asia/Ho_Chi_Minh", weather_lag_months=2,
        weather_availability_days=5, ec_availability_days=list(delays),
        parameters=dict(n_estimators=300, max_depth=8, min_samples_leaf=3, random_state=42),
        sklearn_version=sklearn.__version__, numpy_version=np.__version__, pandas_version=pd.__version__,
        geometry=axis, interpolation_primary="LINEAR_DISTANCE_ALONG_EXISTING_RIVER_AXIS",
        interpolation_sensitivity="IDW_POWER_2", final_fit_samples=len(mid), final_fit_cutoff="2023-12-01",
        limitation="MRC QA UNVERIFIED, EC temperature basis unknown; same-month samples may have different dates; archive publication vintages unknown; anchor-site performance does not validate the whole river",
        input_sha256={str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in source_paths},
        output_sha256={p.name: digest(p) for p in output.iterdir() if p.is_file() and p.suffix in (".csv", ".joblib", ".md")})
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(metrics[(metrics.station == "MYTHUAN") & (metrics.split == "historical_2022_2023")].to_string(index=False), flush=True)
    print(spatial[(spatial.ec_delay_days == 5) & (spatial.split == "historical_2022_2023")].to_string(index=False), flush=True)
    print(f"Report: {output / 'report.md'}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-weather", action="store_true")
    parser.add_argument("--fetch-only", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.fetch_weather or args.fetch_only:
        fetch_weather()
    if not args.fetch_only:
        run(args.output_dir)
