"""Check whether manual and telemetry water levels agree on overlapping days."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MANUAL_TC = ROOT / "data/external/tien_manual_long_20261029"
MANUAL_OTHER = ROOT / "data/external/tien_multisite_supplement_20261029"
TELEMETRY_TC = ROOT / "data/external/tien_multisite_20261029_verified"
OUT = ROOT / "outputs/tien_multisite_audit_20261029/manual_telemetry_agreement.json"


def daily(path):
    frame = pd.read_csv(path, usecols=["observed_at", "value"])
    frame["day"] = pd.to_datetime(frame.observed_at).dt.date
    return frame.groupby("day").value.agg(["median", "count"])


def main():
    result = {}
    for code, name in [("019803", "Tan Chau"), ("019804", "My Thuan"),
                       ("985203", "Vam Kenh"), ("980601", "Vam Nao")]:
        manual_folder = MANUAL_TC if code == "019803" else MANUAL_OTHER
        tele_folder = MANUAL_OTHER if code == "980601" else TELEMETRY_TC
        manual = daily(next(manual_folder.glob(f"{code}_Water_Level_Manual_*.csv")))
        tele_path = next(path for path in tele_folder.glob(f"{code}_Water_Level_Telemetry_*.csv")
                         if not path.name.endswith("_daily.csv"))
        tele = daily(tele_path)
        paired = manual.join(tele, how="inner", lsuffix="_manual", rsuffix="_telemetry")
        paired = paired[paired.count_telemetry >= 80]
        difference = paired.median_manual - paired.median_telemetry
        result[code] = dict(station=name, paired_days=len(paired),
            pearson_r=float(paired.median_manual.corr(paired.median_telemetry)) if len(paired)>1 else None,
            median_offset_manual_minus_telemetry_m=float(difference.median()) if len(paired) else None,
            median_absolute_difference_m=float(difference.abs().median()) if len(paired) else None,
            p95_absolute_difference_m=float(difference.abs().quantile(.95)) if len(paired) else None,
            caution="Agreement does not establish common gauge datum or verified quality")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
