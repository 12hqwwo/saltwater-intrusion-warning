"""Download and audit public GFZ Son Doc salinity/Tan Chau Q data; preserve raw CSV."""
from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/new_data_search_20261029/gfz_apel_2024"
BASE = "https://datapub.gfz-potsdam.de/download/10.5880.GFZ.4.4.2024.004-QWn/"
FILES = ["2024-004_Apel_salinity_SONDOC_1996-2016.csv",
         "2024-004_Apel-et-al_discharge_Qmonthly_TanChau_1964-2017_gaps-filled.csv"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    payload = []
    for name in FILES:
        path = OUT / name
        if path.exists():
            content = path.read_bytes()
        else:
            response = requests.get(BASE + name, timeout=60)
            response.raise_for_status()
            content = response.content
        if len(content) < 500 or b"<html" in content[:200].lower():
            raise ValueError(f"Bad CSV response {name}")
        path.write_bytes(content)
        payload.append(dict(name=name,url=BASE+name,bytes=len(content),
                            sha256=hashlib.sha256(content).hexdigest()))
    salinity_raw = (OUT / FILES[0]).read_text(encoding="utf-8-sig")
    discharge_raw = (OUT / FILES[1]).read_text(encoding="utf-8-sig")
    salinity = pd.read_csv(io.StringIO(salinity_raw[salinity_raw.index("DATETIME;"):]), sep=";", dtype=str)
    discharge = pd.read_csv(io.StringIO(discharge_raw[discharge_raw.index("year;month;"):]), sep=";")
    salinity["observed_at_local_unconfirmed"] = pd.to_datetime(salinity["DATETIME"], errors="coerce")
    salinity["salinity_g_l"] = pd.to_numeric(salinity["SALINITY [g/l]"], errors="coerce")
    salinity["duplicate_timestamp"] = salinity["DATETIME"].duplicated(keep=False)
    if salinity.observed_at_local_unconfirmed.isna().any() or salinity.salinity_g_l.dropna().lt(0).any():
        raise ValueError("Invalid GFZ salinity date or negative value")
    discharge["month_start"] = pd.to_datetime(discharge[["year", "month"]].assign(day=1))
    if discharge.month_start.duplicated().any() or discharge["Q [m3/s]"].le(0).any():
        raise ValueError("Invalid GFZ Q series")
    salinity[["DATETIME", "salinity_g_l", "duplicate_timestamp"]].to_csv(
        OUT / "sondoc_salinity_preserved.csv", index=False)
    discharge[["year", "month", "Q [m3/s]"]].to_csv(OUT / "tanchau_q_monthly_preserved.csv", index=False)
    payload[0]["audit"] = dict(rows=len(salinity),numeric_values=int(salinity.salinity_g_l.notna().sum()),
        missing_values=int(salinity.salinity_g_l.isna().sum()),
        duplicate_timestamp_rows=int(salinity.duplicate_timestamp.sum()),
        start=str(salinity.observed_at_local_unconfirmed.min()),
        end=str(salinity.observed_at_local_unconfirmed.max()),
        min_g_l=float(salinity.salinity_g_l.min()),max_g_l=float(salinity.salinity_g_l.max()),
        timezone="not specified by source; do not join to hourly series as UTC")
    payload[1]["audit"] = dict(rows=len(discharge),start=str(discharge.month_start.min()),
        end=str(discharge.month_start.max()),min_m3_s=int(discharge["Q [m3/s]"].min()),
        max_m3_s=int(discharge["Q [m3/s]"].max()),
        reconstructed_months_1980_1994=int(discharge.year.lt(1995).sum()),
        official_gauge_months_1995_2016=int(discharge.year.ge(1995).sum()),
        note="Filename says 1964-2017 but rows cover 1980-2016; source text specifies m3/s despite heading comment typo")
    manifest = dict(doi="10.5880/GFZ.4.4.2024.004", license="CC BY 4.0",
        checked_at_utc=datetime.now(timezone.utc).isoformat(), files=payload,
        use="historical mechanism/independent corroboration only; no 2019-2023 overlap")
    (OUT / "manifest.json").write_text(json.dumps(manifest,indent=2,default=str,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(payload,indent=2))


if __name__ == "__main__":
    main()
