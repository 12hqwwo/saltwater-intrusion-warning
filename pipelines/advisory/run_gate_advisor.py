"""Gate-local intake/drainage decision support; never sends actuator commands.

python pipelines/advisory/run_gate_advisor.py --policy data/contracts/gate_policy.json --input data/contracts/gate_input.json
Thresholds belong to an evidenced gate-specific policy. No real thresholds are supplied.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
VERSION = "1.0.0"


class GateInputError(ValueError):
    pass


def stamp(value):
    if not isinstance(value, str):
        raise GateInputError("Timestamp thiếu hoặc không phải chuỗi ISO.")
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GateInputError("Timestamp ISO không hợp lệ.") from exc
    if t.tzinfo is None or t.utcoffset() is None:
        raise GateInputError("Timestamp phải có múi giờ.")
    return t.astimezone(timezone.utc)


def numeric(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise GateInputError(f"{name}: cần số hữu hạn, không nhận giá trị thiếu.")
    return float(value)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def band(value, name, nonnegative=False):
    lo, point, hi = (numeric(value[k], f"{name}.{k}") for k in ("lower", "point", "upper"))
    if not lo <= point <= hi or (nonnegative and lo < 0):
        raise GateInputError(f"Dải dự báo không hợp lệ: {name}.")
    return lo, point, hi


def evaluate(policy, data):
    if not isinstance(policy, dict) or not isinstance(data, dict):
        return dict(schema_version=1, advisor_version=VERSION, status="INVALID_INPUT",
                    recommendation=None, reasons=["POLICY_AND_INPUT_MUST_BE_OBJECTS"],
                    requires_operator_review=True, actuator_command=None, deployment_ready=False)
    result = dict(schema_version=1, advisor_version=VERSION, gate_code=data.get("gate_code"),
                  issue_time=data.get("issue_time"), status="INSUFFICIENT_DATA", recommendation=None,
                  reasons=[], evidence={}, requires_operator_review=True, actuator_command=None,
                  deployment_ready=False, data_kind="SIMULATION_ONLY" if data.get("is_demo") is True else "GATE_ADVISORY")

    def stop(status, *reasons):
        result.update(status=status, recommendation=None, reasons=list(reasons))
        return result

    if policy.get("schema_version") != 1 or data.get("schema_version") != 1:
        return stop("INVALID_INPUT", "SCHEMA_VERSION_MISMATCH")
    if type(policy.get("is_demo")) is not bool or type(data.get("is_demo")) is not bool:
        return stop("INVALID_INPUT", "IS_DEMO_MUST_BE_BOOLEAN")
    if policy["is_demo"] != data["is_demo"]:
        return stop("INVALID_INPUT", "DO_NOT_MIX_DEMO_AND_REAL_INPUTS")
    if not nonempty(data.get("gate_code")) or policy.get("gate_code") != data["gate_code"]:
        return stop("INSUFFICIENT_DATA", "GATE_ID_MISSING_OR_POLICY_MISMATCH")
    approval = policy.get("approval")
    if not isinstance(approval, dict) or approval.get("status") != "APPROVED" or not nonempty(approval.get("reference")):
        return stop("INSUFFICIENT_DATA", "GATE_SPECIFIC_POLICY_NOT_DOCUMENTED")
    try:
        now = stamp(data["issue_time"])
        if not data["is_demo"] and now > datetime.now(timezone.utc):
            return stop("INVALID_INPUT", "REAL_ISSUE_TIME_CANNOT_BE_IN_THE_FUTURE")
        approval = policy["approval"]
        if not stamp(approval["valid_from"]) <= now <= stamp(approval["valid_to"]):
            return stop("REVIEW_REQUIRED", "POLICY_OUTSIDE_VALID_PERIOD")
        if not nonempty(policy.get("policy_id")) or not nonempty(policy.get("vertical_datum")):
            return stop("INSUFFICIENT_DATA", "POLICY_ID_OR_VERTICAL_DATUM_MISSING")
        result["policy_id"] = policy["policy_id"]
        parameter = policy["parameter"]
        allowed = {("EC", "mS/m"), ("SP", "1"), ("SALINITY_MASS", "g/L")}
        if (parameter.get("name"), parameter.get("unit")) not in allowed:
            return stop("INVALID_INPUT", "UNSUPPORTED_PARAMETER_OR_UNIT")
        if parameter["name"] == "EC" and parameter.get("ec_basis") != "REFERENCE_25C":
            return stop("REVIEW_REQUIRED", "EC_THRESHOLD_REQUIRES_DOCUMENTED_REFERENCE_25C_BASIS")
        thresholds = policy["quality_thresholds"]
        open_below = numeric(thresholds["open_below"], "open_below")
        close_at = numeric(thresholds["close_at_or_above"], "close_at_or_above")
        if not 0 <= open_below < close_at:
            return stop("INVALID_INPUT", "HYSTERESIS_THRESHOLDS_INVALID")
        levels = {k: numeric(v, k) for k, v in policy["levels"].items()}
        required_levels = {"inside_min_m", "inside_max_m", "inside_critical_m", "min_head_m", "max_abs_head_m"}
        if not required_levels.issubset(levels):
            return stop("INSUFFICIENT_DATA", "LEVEL_LIMITS_MISSING")
        if not levels["inside_min_m"] < levels["inside_max_m"] < levels["inside_critical_m"]:
            return stop("INVALID_INPUT", "INSIDE_LEVEL_LIMITS_INVALID")
        if not 0 < levels["min_head_m"] < levels["max_abs_head_m"]:
            return stop("INVALID_INPUT", "HEAD_LIMITS_INVALID")
        timing = {k: numeric(v, k) for k, v in policy["timing"].items()}
        required_times = {"max_observation_age_minutes", "max_forecast_age_minutes", "max_step_minutes", "horizon_minutes", "min_switch_interval_minutes"}
        if not required_times.issubset(timing) or any(timing[k] <= 0 for k in required_times):
            return stop("INVALID_INPUT", "TIMING_LIMITS_MISSING_OR_INVALID")
        mode, state = data.get("mode"), data.get("current_state")
        if mode not in {"INTAKE", "DRAIN"} or mode not in policy.get("allowed_modes", []):
            return stop("REVIEW_REQUIRED", "OPERATING_OBJECTIVE_NOT_SUPPORTED_BY_POLICY")
        if state not in {"OPEN", "CLOSED"}:
            return stop("INSUFFICIENT_DATA", "CURRENT_GATE_STATE_NOT_CONFIRMED")

        def recent(record, name):
            observed = stamp(record["observed_at"])
            available = stamp(record["available_at"])
            if observed > available or available > now:
                raise GateInputError(f"{name}: dữ liệu chưa khả dụng hoặc thời gian đảo ngược.")
            if (now - observed).total_seconds() / 60 > timing["max_observation_age_minutes"]:
                raise GateInputError(f"{name}: dữ liệu đã quá hạn sử dụng của policy.")
            if record.get("quality_flag") != "VALIDATED" or not nonempty(record.get("source_reference")):
                raise GateInputError(f"{name}: thiếu trạng thái kiểm định hoặc nguồn.")
            if record.get("gate_code") != data["gate_code"]:
                raise GateInputError(f"{name}: khác vị trí cống.")

        status = data["operating_status"]
        recent(status, "operating_status")
        for key in ("mechanical_ok", "emergency", "water_demand"):
            if type(status.get(key)) is not bool:
                return stop("INSUFFICIENT_DATA", f"{key.upper()}_NOT_CONFIRMED")
        if status["emergency"] or not status["mechanical_ok"]:
            return stop("REVIEW_REQUIRED", "EMERGENCY_OR_MECHANICAL_RESTRICTION")
        last_changed = stamp(data["last_changed_at"])
        if last_changed > stamp(status["observed_at"]):
            return stop("INVALID_INPUT", "STATE_CHANGE_AFTER_STATE_OBSERVATION")
        obs = data["observations"]
        measured = {}
        for name in ("outside_quality", "inside_quality", "outside_level", "inside_level"):
            record = obs[name]
            recent(record, name)
            value = numeric(record["value"], name)
            measured[name] = value
            if name.endswith("quality"):
                if record.get("parameter") != parameter["name"] or record.get("unit") != parameter["unit"]:
                    return stop("INVALID_INPUT", "QUALITY_PARAMETER_OR_UNIT_MISMATCH")
                if value < 0:
                    return stop("INVALID_INPUT", "NEGATIVE_QUALITY_VALUE")
                if parameter["name"] == "EC" and record.get("ec_basis") != parameter["ec_basis"]:
                    return stop("REVIEW_REQUIRED", "EC_TEMPERATURE_BASIS_MISMATCH")
                if not nonempty(record.get("method_reference")):
                    return stop("INSUFFICIENT_DATA", "QUALITY_MEASUREMENT_METHOD_MISSING")
            elif record.get("unit") != "m" or record.get("vertical_datum") != policy["vertical_datum"]:
                return stop("INVALID_INPUT", "WATER_LEVEL_UNIT_OR_DATUM_MISMATCH")

        forecast = data["forecast"]
        if forecast.get("temporal_resolution") not in {"MINUTE", "HOUR"}:
            return stop("INSUFFICIENT_DATA", "MONTHLY_OR_UNSPECIFIED_FORECAST_CANNOT_DRIVE_GATE_ADVICE")
        if forecast.get("spatial_scope") != "GATE" or forecast.get("gate_code") != data["gate_code"]:
            return stop("INSUFFICIENT_DATA", "FORECAST_NOT_VALIDATED_AT_THIS_GATE")
        if (forecast.get("qualification") != "REVIEWED_FOR_GATE_ADVICE"
                or not nonempty(forecast.get("field_validation_reference"))
                or not nonempty(forecast.get("source_reference"))
                or not nonempty(forecast.get("model_id"))):
            return stop("INSUFFICIENT_DATA", "FIELD_FORECAST_QUALIFICATION_MISSING")
        if forecast.get("interval_kind") != "VALIDATED_PREDICTION_INTERVALS":
            return stop("INSUFFICIENT_DATA", "UNCERTAINTY_NOT_QUALIFIED_FOR_GATE_ADVICE")
        if forecast.get("parameter") != parameter or forecast.get("vertical_datum") != policy["vertical_datum"]:
            return stop("INVALID_INPUT", "FORECAST_PARAMETER_OR_DATUM_MISMATCH")
        forecast_issued = stamp(forecast["issued_at"])
        age_minutes = (now - forecast_issued).total_seconds() / 60
        if not 0 <= age_minutes <= timing["max_forecast_age_minutes"]:
            return stop("INSUFFICIENT_DATA", "FORECAST_NOT_AVAILABLE_OR_STALE")
        steps = forecast.get("steps")
        if not isinstance(steps, list) or not steps:
            return stop("INSUFFICIENT_DATA", "FORECAST_WINDOW_EMPTY")
        horizon_end = now + timedelta(minutes=timing["horizon_minutes"])
        head_ranges, inside_ranges, quality_upper = [], [], [measured["outside_quality"]]
        cursor, used = None, 0
        for step in steps:
            start, end = stamp(step["valid_from"]), stamp(step["valid_to"])
            if end <= start or (end - start).total_seconds() / 60 > timing["max_step_minutes"]:
                return stop("INVALID_INPUT", "FORECAST_TIME_STEP_INVALID")
            if cursor is not None and start != cursor:
                return stop("INVALID_INPUT", "FORECAST_WINDOW_GAP_OR_OVERLAP")
            cursor = end
            if end <= now or start >= horizon_end:
                continue
            if used == 0 and start > now:
                return stop("INSUFFICIENT_DATA", "FORECAST_DOES_NOT_COVER_ISSUE_TIME")
            qlo, qmid, qhi = band(step["outside_quality"], "outside_quality", nonnegative=True)
            out_lo, _, out_hi = band(step["outside_level_m"], "outside_level_m")
            in_lo, _, in_hi = band(step["inside_level_m"], "inside_level_m")
            head_ranges.append((out_lo - in_hi, out_hi - in_lo))
            inside_ranges.append((in_lo, in_hi))
            quality_upper.append(qhi)
            used += 1
        if used == 0 or cursor < horizon_end:
            return stop("INSUFFICIENT_DATA", "FORECAST_HORIZON_INCOMPLETE")
        head_now = measured["outside_level"] - measured["inside_level"]
        head_ranges.append((head_now, head_now))
        inside_ranges.append((measured["inside_level"], measured["inside_level"]))
        result["evidence"] = dict(mode=mode, current_state=state, parameter=parameter,
                                  current_head_outside_minus_inside_m=head_now, forecast_steps_used=used,
                                  max_quality_upper=max(quality_upper), open_below=open_below,
                                  close_at_or_above=close_at, forecast_model_id=forecast["model_id"],
                                  policy_reference=approval["reference"], field_validation_reference=forecast["field_validation_reference"],
                                  declarations_are_not_automatically_certified=True)
        if max(high for _, high in inside_ranges) >= levels["inside_critical_m"]:
            return stop("REVIEW_REQUIRED", "FLOOD_RISK_REQUIRES_COORDINATED_OPERATION")
        if max(max(abs(low), abs(high)) for low, high in head_ranges) > levels["max_abs_head_m"]:
            return stop("REVIEW_REQUIRED", "HEAD_EXCEEDS_MECHANICAL_OPERATING_ENVELOPE")
        desired, reasons = None, []
        if mode == "INTAKE":
            if max(quality_upper) >= close_at:
                desired, reasons = "CLOSED", ["OUTSIDE_QUALITY_CLOSE_THRESHOLD_REACHED"]
            elif max(high for _, high in inside_ranges) >= levels["inside_max_m"]:
                desired, reasons = "CLOSED", ["INSIDE_STORAGE_UPPER_LIMIT"]
            elif min(low for low, _ in head_ranges) < levels["min_head_m"]:
                desired, reasons = "CLOSED", ["INTAKE_HEAD_NOT_FAVORABLE_THROUGH_WINDOW"]
            elif not status["water_demand"]:
                desired, reasons = "CLOSED", ["NO_DECLARED_WATER_DEMAND"]
            elif max(quality_upper) < open_below:
                desired, reasons = "OPEN", ["INTAKE_CONDITIONS_SATISFIED"]
            else:
                desired, reasons = state, ["QUALITY_WITHIN_HYSTERESIS_BAND"]
        else:
            if min(low for low, _ in inside_ranges) <= levels["inside_min_m"]:
                desired, reasons = "CLOSED", ["INSIDE_LEVEL_TOO_LOW_FOR_DRAINAGE"]
            elif min(-high for _, high in head_ranges) < levels["min_head_m"]:
                desired, reasons = "CLOSED", ["DRAINAGE_HEAD_NOT_FAVORABLE_THROUGH_WINDOW"]
            elif max(quality_upper) >= close_at and policy.get("allow_drainage_with_saline_outside") is not True:
                return stop("REVIEW_REQUIRED", "SALINE_OUTSIDE_DRAINAGE_NOT_COVERED_BY_POLICY")
            else:
                desired, reasons = "OPEN", ["DRAINAGE_CONDITIONS_SATISFIED"]
        if desired != state and (now - last_changed).total_seconds() / 60 < timing["min_switch_interval_minutes"]:
            return stop("REVIEW_REQUIRED", "SWITCH_INTERVAL_RESTRICTION", *reasons)
        result.update(status="ADVISORY_AVAILABLE", reasons=reasons,
                      recommendation=("KEEP_OPEN" if state == "OPEN" else "KEEP_CLOSED") if desired == state
                      else ("RECOMMEND_OPEN" if desired == "OPEN" else "RECOMMEND_CLOSE"))
        return result
    except (KeyError, TypeError, AttributeError, GateInputError) as exc:
        return stop("INSUFFICIENT_DATA", "REQUIRED_INPUT_MISSING_OR_INVALID", str(exc))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs/gate_advice")
    args = parser.parse_args(argv)
    try:
        policy_bytes, input_bytes = args.policy.read_bytes(), args.input.read_bytes()
        result = evaluate(json.loads(policy_bytes), json.loads(input_bytes))
        result["input_hashes"] = {"policy": hashlib.sha256(policy_bytes).hexdigest(), "input": hashlib.sha256(input_bytes).hexdigest()}
        result["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        out = args.output_dir / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid4().hex[:8]}"
        out.mkdir(parents=True, exist_ok=False)
        (out / "advice.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps(dict(status=result["status"], recommendation=result["recommendation"], reasons=result["reasons"], output=str(out)), ensure_ascii=False, indent=2))
        return 0 if result["status"] == "ADVISORY_AVAILABLE" else 2
    except (OSError, ValueError, AttributeError) as exc:
        print(json.dumps(dict(status="ERROR", message=str(exc)), ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
