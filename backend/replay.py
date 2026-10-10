"""Read-only, explicitly configured historical forecast results; no database writes."""
from functools import lru_cache
import json
import math
import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1/replay", tags=["Dự báo hồi cứu"])


@lru_cache(maxsize=2)
def _read(path, mtime_ns, size):
    if size > 10_000_000: raise ValueError("Replay file too large.")
    result = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(result, dict) or not isinstance(result.get("metadata"), dict):
        raise ValueError("Replay metadata must be an object.")
    meta = result["metadata"]
    if meta.get("schema_version") != 1 or meta.get("mode") != "HISTORICAL_STATION_FORECAST":
        raise ValueError("Unexpected replay mode/schema.")
    if meta.get("station") != "GFZ_SONDOC" or meta.get("unit") != "g/L" or meta.get("deployment_validated") is not False:
        raise ValueError("Unrecognized station, unit or qualification.")
    records = result["records"]
    if not isinstance(records, list) or not records: raise ValueError("No replay data.")
    seen = set()
    from datetime import datetime, timedelta
    for row in records:
        if not isinstance(row, dict): raise ValueError("Replay records must be objects.")
        if row.get("site_code") != meta["station"] or row.get("unit") != meta["unit"] or row.get("gate_decision_eligible") is not False:
            raise ValueError("Replay record identity mismatch.")
        if row.get("horizon_hours") not in (2, 6, 12) or row.get("selected_on_validation") is not True:
            raise ValueError("Only selected historical forecasts are supported.")
        for key in ("predicted", "actual", "salinity_at_issue", "lower", "upper"):
            value = row[key]
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid numeric value.")
        if not row["lower"] <= row["predicted"] <= row["upper"]: raise ValueError("Reversed interval.")
        issue, target, last_train = [datetime.fromisoformat(row[k]) for k in ("forecast_origin", "target_time", "train_last_target")]
        if any(t.tzinfo is None for t in (issue, target, last_train)) or last_train >= issue or target - issue != timedelta(hours=row["horizon_hours"]):
            raise ValueError("Invalid replay timeline.")
        delay = meta.get("observation_delay_hours", 0)
        if type(delay) is not int or delay not in (0, 2, 6) or row.get("observation_delay_hours", 0) != delay:
            raise ValueError("Invalid publication-delay scenario.")
        if delay or "last_available_observation_at" in row:
            last_observation = datetime.fromisoformat(row["last_available_observation_at"])
            last_available_label = datetime.fromisoformat(row["train_last_label_available_at"])
            if last_observation.tzinfo is None or last_available_label.tzinfo is None:
                raise ValueError("Missing time offset.")
            if issue - last_observation != timedelta(hours=delay) or last_available_label >= issue:
                raise ValueError("Observation or training label unavailable at issue.")
        key = (row["horizon_hours"], row["forecast_origin"])
        if key in seen: raise ValueError("Duplicate replay record.")
        seen.add(key)
    return result


def dataset():
    value = os.getenv("WEBGIS_REPLAY_FILE")
    if not value: raise HTTPException(503, detail="Chưa chọn kết quả hồi cứu: đặt WEBGIS_REPLAY_FILE tới replay.json.")
    try:
        path = Path(value).resolve()
        stat = path.stat()
        return _read(str(path), stat.st_mtime_ns, stat.st_size)
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        raise HTTPException(503, detail="Không đọc được bộ kết quả hồi cứu hợp lệ.") from None


@router.get("")
def metadata():
    source = dataset()
    return {"metadata": source["metadata"], "count": len(source["records"]), "mode": "HISTORICAL_REPLAY",
            "station_feature": {"type": "Feature", "geometry": {"type": "Point", "coordinates": [106.45747, 10.06425]},
                                "properties": {"site_code": "GFZ_SONDOC", "site_name": "Sơn Đốc · GFZ",
                                               "location_status": "REPORTED_CONFLICT_UNRESOLVED",
                                               "location_reference": "10.5880/GFZ.4.4.2024.004"}}}


@router.get("/forecasts")
def forecasts(horizon_hours: Annotated[int, Query(ge=1, le=24)] = 6,
              include_actual: bool = False,
              limit: Annotated[int, Query(ge=1, le=2000)] = 2000,
              offset: Annotated[int, Query(ge=0, le=100000)] = 0):
    if horizon_hours not in (2, 6, 12): raise HTTPException(422, detail="Chọn chân trời 2, 6 hoặc 12 giờ.")
    rows = [r for r in dataset()["records"] if r["horizon_hours"] == horizon_hours]
    rows.sort(key=lambda r: r["forecast_origin"])
    visible = []
    for row in rows[offset:offset+limit]:
        item = {k:v for k,v in row.items() if k != "actual"}
        if include_actual: item["actual_for_evaluation"] = row["actual"]
        visible.append(item)
    return {"mode": "HISTORICAL_REPLAY", "unit": "g/L", "items": visible, "total": len(rows),
            "offset": offset, "limit": limit, "has_more": offset + len(visible) < len(rows),
            "actuals_included": include_actual, "gate_decision_eligible": False}
