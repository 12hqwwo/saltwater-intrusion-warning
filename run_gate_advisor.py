"""Gate planning dossier review; never determines switching times.

python run_gate_advisor.py --policy data/contracts/gate_policy.json --input data/contracts/gate_input.json
Thresholds belong to an evidenced gate-specific policy. No real thresholds are supplied.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = "2.0.0"


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


def evaluate(policy, data):
    """Review planning inputs only; never derive a gate switching schedule."""
    result = dict(schema_version=1, advisor_version=VERSION, status="INSUFFICIENT_DATA",
                  recommendation=None, actuator_command=None, deployment_ready=False,
                  requires_operator_review=True, reasons=[], evidence={},
                  data_kind="GATE_PLANNING", gate_code=None)
    if not isinstance(policy, dict) or not isinstance(data, dict):
        result.update(status="INVALID_INPUT", reasons=["POLICY_AND_INPUT_MUST_BE_OBJECTS"])
        return result
    result['gate_code'] = data.get('gate_code')
    if policy.get('schema_version') != 1 or data.get('schema_version') != 1:
        result.update(status="INVALID_INPUT", reasons=["SCHEMA_VERSION_MISMATCH"])
        return result
    if policy.get('is_demo') is not False or data.get('is_demo') is not False:
        result.update(status="INVALID_INPUT", reasons=["REAL_SOURCED_RECORDS_REQUIRED"])
        return result
    result['reasons'] = ["SERVER_VERIFIED_GATE_EVIDENCE_NOT_AVAILABLE",
                         "MONTHLY_EC_CANNOT_DETERMINE_SWITCHING_TIMES"]
    if not nonempty(data.get('gate_code')) or policy.get('gate_code') != data['gate_code']:
        result['reasons'].append("GATE_ID_MISSING_OR_POLICY_MISMATCH")
    observations = data.get('observations')
    if not isinstance(observations, dict):
        result['reasons'].append("LOCAL_OBSERVATIONS_MISSING")
    else:
        for key in ['outside_level', 'inside_level', 'outside_quality', 'inside_quality']:
            record = observations.get(key)
            if not isinstance(record, dict) or record.get('value') is None:
                result['reasons'].append(key.upper() + "_MISSING")
            else:
                try:
                    numeric(record['value'], key)
                except GateInputError:
                    result.update(status="INVALID_INPUT", reasons=["OBSERVATION_MUST_BE_FINITE_NUMBER"])
                    return result
    result['planning_actions'] = [
        'Bổ sung số đo EC và mực nước hai phía cùng thời điểm, có nguồn và hệ cao độ.',
        'Xác minh tọa độ công trình, quan hệ thủy lực trạm–cống và quy trình được phê duyệt.',
        'Dùng đánh giá EC tháng để chuẩn bị kế hoạch quan trắc và rà soát nhu cầu lấy nước.',
        'Người vận hành rà soát điều kiện thực tế trước mọi quyết định đóng/mở.',
    ]
    return result


def main():
    parser = argparse.ArgumentParser(description='Rà soát hồ sơ lập kế hoạch cống; không phát lệnh vận hành.')
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(json.loads(args.policy.read_text(encoding='utf-8-sig')),
                      json.loads(args.input.read_text(encoding='utf-8-sig')))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
