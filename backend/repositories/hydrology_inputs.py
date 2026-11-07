"""Monthly Kratie discharge and Tan Chau stage for the My Tho EC model."""
import calendar
import hashlib
import math
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
FEATURES = ["kratie_q_t2", "kratie_q3_t2", "kratie_q_ratio_t2",
            "tc_stage_t2", "tc_stage3_t2"]
UNITS = {"kratie_q_t2": "m³/s", "kratie_q3_t2": "m³/s",
         "kratie_q_ratio_t2": "1", "tc_stage_t2": "m",
         "tc_stage3_t2": "m"}
LABELS = {"kratie_q_t2": "Lưu lượng Kratie tháng đầu vào",
          "kratie_q3_t2": "Lưu lượng Kratie trung bình 3 tháng",
          "kratie_q_ratio_t2": "Tỷ lệ lưu lượng Kratie so với cùng mùa",
          "tc_stage_t2": "Mực nước Tân Châu tháng đầu vào",
          "tc_stage3_t2": "Mực nước Tân Châu trung vị 3 tháng"}


def source_paths():
    folders = [ROOT / "data/external/mrc_kratie_discharge_20261029",
               ROOT / "data/external/tien_manual_long_20261029",
               ROOT / "data/external/tien_manual_2024_2026_20261029"]
    patterns = ["014901_Discharge_Calculated daily discharge_????????.csv",
                "019803_Water_Level_Manual_????????.csv",
                "019803_Water_Level_Manual_????????.csv"]
    paths = []
    for folder, pattern in zip(folders, patterns):
        matches = sorted(folder.glob(pattern))
        if len(matches) != 1:
            raise ValueError(f"Expected one hydrology source in {folder}")
        paths.append(matches[0])
    return paths


def _signature():
    return tuple((str(path), path.stat().st_mtime_ns, path.stat().st_size)
                 for path in source_paths())


def _monthly_stage(paths):
    import pandas as pd

    frames = [pd.read_csv(path, usecols=["observed_at", "value", "unit"])
              for path in paths]
    frame = pd.concat(frames, ignore_index=True)
    if frame.observed_at.duplicated().any() or frame.unit.ne("m").any():
        raise ValueError("Invalid Tan Chau stage source")
    frame["day"] = pd.to_datetime(frame.observed_at).dt.date
    daily = frame.groupby("day").value.median().to_frame("stage")
    daily["month"] = pd.to_datetime(daily.index).to_period("M").to_timestamp()
    monthly = daily.groupby("month").stage.agg(["median", "count"])
    return monthly["median"].where(monthly["count"] >= 20)


def _monthly_flow(path):
    import pandas as pd

    frame = pd.read_csv(path, usecols=["observed_at", "value", "unit"])
    if (frame.observed_at.duplicated().any() or frame.unit.ne("m^3/s").any()
            or frame.value.isna().any() or (frame.value < 0).any()):
        raise ValueError("Invalid Kratie discharge source")
    frame["day"] = pd.to_datetime(frame.observed_at).dt.date
    daily = frame.groupby("day").value.mean().to_frame("q")
    daily["month"] = pd.to_datetime(daily.index).to_period("M").to_timestamp()
    monthly = daily.groupby("month").q.agg(["mean", "count"])
    return monthly["mean"].where(monthly["count"] >= 20)


@lru_cache(maxsize=3)
def _matrix(signature):
    import pandas as pd

    flow_path, old_stage_path, recent_stage_path = [Path(item[0]) for item in signature]
    q = _monthly_flow(flow_path)
    stage = _monthly_stage([old_stage_path, recent_stage_path])
    end = max(q.index.max(), stage.index.max())
    index = pd.date_range("1985-01-01", end, freq="MS")
    q = q.reindex(index)
    stage = stage.reindex(index)
    q3 = q.rolling(3, min_periods=2).mean()
    stage3 = stage.rolling(3, min_periods=2).median()
    prior_same_month = pd.Series(index=index, dtype=float)
    for month in range(1, 13):
        series = q[q.index.month == month]
        prior_same_month.loc[series.index] = series.shift(1).rolling(15, min_periods=5).median().values
    ratio = (q / prior_same_month).clip(0, 5)
    return pd.DataFrame(dict(weather_month=index, kratie_q_t2=q.values,
        kratie_q3_t2=q3.values, kratie_q_ratio_t2=ratio.values,
        tc_stage_t2=stage.values, tc_stage3_t2=stage3.values))


def get_hydrology_input(target_month, now=None):
    """Return complete t-2 features under the explicit month-end +5d assumption."""
    target = date.fromisoformat(str(target_month) + "-01")
    index = target.year * 12 + target.month - 1 - 2
    month = f"{index // 12:04d}-{index % 12 + 1:02d}"
    source_month = date.fromisoformat(month + "-01")
    end = source_month.replace(day=calendar.monthrange(source_month.year, source_month.month)[1])
    available = end + timedelta(days=5)
    today = (now or datetime.now(LOCAL_TZ)).astimezone(LOCAL_TZ).date()
    if available > today:
        raise ValueError("Hydrology month is not yet assumed available")
    frame = _matrix(_signature())
    rows = frame[frame.weather_month.eq(month + "-01")]
    if len(rows) != 1:
        raise ValueError("Missing hydrology source month")
    values = {key: float(rows.iloc[0][key]) for key in FEATURES}
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("Incomplete Kratie or Tan Chau monthly hydrology")
    paths = source_paths()
    return dict(values, input_month=month, observed_through=end.isoformat(),
                assumed_available_at=available.isoformat(), complete=True,
                source="MRC Kratie discharge + Tan Chau manual water level",
                source_files={path.relative_to(ROOT).as_posix():
                              hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
                availability_note="Month end + 5 days is assumed; historical publication time is unverified.")
