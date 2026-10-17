"""Check a documented station-to-gate link without relabelling a proxy as a sensor.

This bridge describes representativeness. It does not authorize a gate action.
Nearest distance alone never qualifies a link. No new gate coordinates are invented.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from run_gate_advisor import stamp, numeric, nonempty, GateInputError


def distance_m(a, b):
    def point(p):
        lon, lat = (numeric(p[k], k) for k in ("longitude", "latitude"))
        if not -180 <= lon <= 180 or not -90 <= lat <= 90: raise GateInputError("Coordinate outside valid range.")
        return math.radians(lon), math.radians(lat)
    lon1, lat1 = point(a); lon2, lat2 = point(b)
    v = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371008.8 * 2 * math.asin(min(1.0, math.sqrt(v)))


def evaluate_link(record, link, issue_time):
    result = dict(schema_version=1, status="INSUFFICIENT_EVIDENCE", reasons=[], proxy=None,
                  representation_review_passed=False, gate_decision_eligible=False,
                  requires_operator_review=True, actuator_command=None)
    if not isinstance(record, dict) or not isinstance(link, dict):
        result.update(status="INVALID_INPUT", reasons=["RECORD_AND_LINK_MUST_BE_OBJECTS"])
        return result
    try:
        if link.get("schema_version") != 1: raise GateInputError("SCHEMA_VERSION_MISMATCH")
        for key in ("gate_code", "site_code", "link_id", "source_reference"):
            if not nonempty(link.get(key)): raise GateInputError(f"MISSING_{key.upper()}")
        if record.get("site_code") != link["site_code"]: raise GateInputError("STATION_MISMATCH")
        if link.get("gate_side") not in ("INSIDE", "OUTSIDE"): raise GateInputError("GATE_SIDE_UNKNOWN")
        if link.get("method") != "IDENTITY_PROXY": raise GateInputError("TRANSFER_MODEL_NOT_IMPLEMENTED")
        for key in ("parameter", "unit"):
            if not nonempty(record.get(key)) or record.get(key) != link.get(key): raise GateInputError(f"{key.upper()}_MISMATCH")
        if (record["parameter"], record["unit"]) not in (("EC", "mS/m"), ("SALINITY_MASS", "g/L"), ("SP", "1")):
            raise GateInputError("UNSUPPORTED_PARAMETER_OR_UNIT")
        if record["parameter"] == "EC" and record.get("ec_basis") != link.get("ec_basis"):
            raise GateInputError("EC_BASIS_MISMATCH")
        value = numeric(record.get("value"), "value")
        if value < 0: raise GateInputError("NEGATIVE_QUALITY_VALUE")
        now, observed, available = stamp(issue_time), stamp(record.get("observed_at")), stamp(record.get("available_at"))
        if not observed <= available <= now: raise GateInputError("RECORD_NOT_AVAILABLE_AT_ISSUE")
        if not nonempty(record.get("source_reference")): raise GateInputError("RECORD_SOURCE_REFERENCE_MISSING")
        result["proxy"] = {"gate_code": link["gate_code"], "gate_side": link["gate_side"],
                           "representation": "STATION_PROXY_NOT_GATE_MEASUREMENT", "station_record": record.copy(),
                           "value": value, "parameter": record["parameter"], "unit": record["unit"],
                           "link_id": link["link_id"], "link_reference": link["source_reference"]}
        reasons = []
        if link.get("status") != "FIELD_REVIEWED": reasons.append("LINK_NOT_FIELD_REVIEWED")
        if record.get("quality_flag") != "VALIDATED": reasons.append("SOURCE_QUALITY_NOT_VALIDATED")
        if record.get("parameter") == "EC" and record.get("ec_basis") != "REFERENCE_25C": reasons.append("EC_BASIS_UNCONFIRMED")
        evidence = link.get("hydrological_evidence") or {}
        if evidence.get("connected") is not True or not nonempty(evidence.get("reference")):
            reasons.append("HYDROLOGICAL_CONNECTION_UNCONFIRMED")
        for key in ("station_branch", "gate_branch"):
            if not nonempty(evidence.get(key)): reasons.append(f"{key.upper()}_MISSING")
        if evidence.get("station_branch") != evidence.get("gate_branch"):
            reasons.append("DIFFERENT_BRANCH_REQUIRES_A_VALIDATED_TRANSFER_MODEL")
        if link.get("station_location") and link.get("gate_location"):
            result["straight_line_distance_m"] = distance_m(link["station_location"], link["gate_location"])
        else: reasons.append("LOCATION_EVIDENCE_INCOMPLETE")
        for key in ("station_location_reference", "gate_location_reference", "review_reference"):
            if not nonempty(link.get(key)): reasons.append(f"{key.upper()}_MISSING")
        try:
            if not stamp(link.get("valid_from")) <= observed <= now <= stamp(link.get("valid_to")):
                reasons.append("LINK_OUTSIDE_VALID_PERIOD")
            age = numeric(link.get("max_age_minutes"), "max_age_minutes")
            if age <= 0 or (now-observed).total_seconds()/60 > age: reasons.append("STALE_OR_INVALID_MAX_AGE")
            error = numeric(link.get("validated_max_difference"), "validated_max_difference")
            tolerance = numeric(link.get("policy_representation_tolerance"), "policy_representation_tolerance")
            if not 0 <= error <= tolerance: reasons.append("REPRESENTATION_ERROR_EXCEEDS_POLICY")
            if not nonempty(link.get("tolerance_policy_reference")): reasons.append("TOLERANCE_POLICY_NOT_DOCUMENTED")
            result["proxy"]["representativeness_range"] = {"lower": max(0, value-error), "upper":value+error} if error >= 0 else None
        except GateInputError:
            reasons.append("VALIDITY_TIMING_OR_ERROR_BUDGET_MISSING")
        result.update(status="PROXY_FOR_SCREENING" if reasons else "REPRESENTATION_REVIEW_PASSED",
                      reasons=reasons, representation_review_passed=not reasons)
        # Even a reviewed relationship still needs gate state, water levels, forecast qualification and a policy.
        return result
    except (GateInputError, TypeError, ValueError, KeyError) as exc:
        result.update(status="INVALID_INPUT", reasons=[str(exc)], proxy=None)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--link", required=True, type=Path)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--issue-time", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = evaluate_link(json.loads(args.record.read_text(encoding="utf-8")), json.loads(args.link.read_text(encoding="utf-8")), args.issue_time)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({"status": result["status"], "reasons":result["reasons"], "output":str(args.out)}, ensure_ascii=False))


if __name__ == "__main__": main()
