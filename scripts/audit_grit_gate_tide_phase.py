"""Measure river water-level waveform lag, Vam Kenh to My Thuan.

This is stage-wave phase only. It does not estimate salt travel time, discharge,
or an operational forecast. Raw MRC telemetry retains its UNVERIFIED grade.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/grit_gate_audit_20261029"
FOLDERS = [ROOT/"data/external/tien_multisite_20261029_verified",
           ROOT/"data/external/tien_multisite_supplement_20261029"]
SITES = {"my_thuan":"019804", "vam_kenh":"985203"}
TIMEZONE = "Asia/Ho_Chi_Minh"


def load_stage(code):
    files = [next(path for path in folder.glob(f"{code}_Water_Level_Telemetry_*.csv")
                  if "_daily" not in path.name) for folder in FOLDERS]
    frame = pd.concat([pd.read_csv(path,usecols=["observed_at","value","unit","quality_flag"])
                       for path in files],ignore_index=True)
    if frame.observed_at.duplicated().any() or frame.unit.ne("m").any() or frame.value.isna().any():
        raise ValueError(f"Bad gauge data for {code}")
    frame.index = pd.to_datetime(frame.observed_at,utc=True).dt.tz_convert(TIMEZONE)
    values = frame.value.resample("15min").median() * 100.0  # cm
    day_count = values.resample("D").count()
    complete_days = day_count[day_count >= 80].index
    values = values.where(values.index.floor("D").isin(complete_days))
    return values, files, day_count


def main():
    stage = {}
    source_files = []
    day_count = {}
    for name, code in SITES.items():
        stage[name], files, day_count[name] = load_stage(code)
        source_files.extend(files)
    paired = pd.concat(stage,axis=1)
    day_counts = pd.concat(day_count,axis=1)
    day_counts["both_complete"] = (day_counts.my_thuan >= 80) & (day_counts.vam_kenh >= 80)
    paired = paired[paired.index.floor("D").isin(day_counts.index[day_counts.both_complete])]
    # Remove each gauge's local-day mean; source and destination gauge datums differ.
    anomaly = paired - paired.groupby(paired.index.floor("D")).transform("mean")
    rows = []
    for split, start, end in [("selection_2019_2021",2019,2021),
                               ("check_2022_2023",2022,2023),
                               ("recent_2024_2026",2024,2026)]:
        for year in range(start,end+1):
            sample = anomaly[anomaly.index.year == year]
            for lag_quarters in range(33):
                # Positive lag means upstream My Thuan follows downstream Vam Kenh.
                shifted = sample.vam_kenh.shift(lag_quarters,freq="15min")
                aligned = pd.concat([sample.my_thuan,shifted],axis=1,sort=True).dropna()
                aligned.columns = ["my_thuan","vam_kenh_shifted"]
                if len(aligned) < 500:
                    continue
                rows.append(dict(split=split,year=year,lag_minutes=lag_quarters*15,
                    paired_quarters=len(aligned),corr=float(aligned.my_thuan.corr(aligned.vam_kenh_shifted)),
                    anomaly_mae_cm=float((aligned.my_thuan-aligned.vam_kenh_shifted).abs().mean())))
        sample = anomaly[(anomaly.index.year>=start)&(anomaly.index.year<=end)]
        for lag_quarters in range(33):
            shifted=sample.vam_kenh.shift(lag_quarters,freq="15min")
            aligned=pd.concat([sample.my_thuan,shifted],axis=1,sort=True).dropna()
            aligned.columns=["my_thuan","vam_kenh_shifted"]
            if len(aligned) < 500:
                continue
            rows.append(dict(split=split,year="all",lag_minutes=lag_quarters*15,
                paired_quarters=len(aligned),corr=float(aligned.my_thuan.corr(aligned.vam_kenh_shifted)),
                anomaly_mae_cm=float((aligned.my_thuan-aligned.vam_kenh_shifted).abs().mean())))
    metrics = pd.DataFrame(rows)
    if metrics.empty:
        raise ValueError("No overlapping telemetry with complete days")
    selection=metrics[(metrics.split=="selection_2019_2021") & (metrics.year=="all")]
    best=selection.loc[selection["corr"].idxmax()]
    OUT.mkdir(parents=True,exist_ok=True)
    metrics.to_csv(OUT/"tide_wave_lag_metrics.csv",index=False)
    day_counts.to_csv(OUT/"tide_stage_day_coverage.csv",index_label="date_local")
    audit=dict(source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in source_files},
        timezone=TIMEZONE,unit="cm",source_quality="UNVERIFIED",
        raw_interval_minutes=15,complete_day_threshold_quarters=80,
        comparison="daily-demeaned stage wave; positive lag: Vam Kenh leads My Thuan",
        selection_period="2019-2021",selection_lag_minutes=int(best.lag_minutes),
        selection_corr=float(best["corr"]),selection_n=int(best.paired_quarters),
        caveat="Water-level tide-wave phase, not salinity propagation; daily demeaning does not remove meteorological and river-flow effects",
        output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [OUT/"tide_wave_lag_metrics.csv",OUT/"tide_stage_day_coverage.csv"]})
    (OUT/"tide_wave_lag_audit.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
    print(metrics[metrics.year.eq("all")].sort_values(["split","corr"],ascending=[True,False]).groupby("split").head(3).to_string(index=False))
    print("selected lag",best.lag_minutes)


if __name__ == "__main__":
    main()
