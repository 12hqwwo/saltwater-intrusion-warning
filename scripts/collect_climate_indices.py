"""Collect public climate indices (ONI, PDO) for EC salinity modelling.

Sources:
- ONI (Oceanic Nino Index): https://psl.noaa.gov/data/correlation/oni.data
- PDO (Pacific Decadal Oscillation): https://psl.noaa.gov/data/correlation/pdo.data

Research only. These publicly published teleconnection indices do not substitute
for observed EC, discharge or stage at local gauges.
"""
from __future__ import annotations
import urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/climate_indices_20261029"
OUT.mkdir(parents=True, exist_ok=True)


def _parse_psl_matrix(raw: str, missing_val: float = 99.9) -> pd.DataFrame:
    rows = []
    for line in raw.strip().splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            year = int(parts[0])
        except ValueError:
            continue
        for month_idx, v in enumerate(parts[1:], start=1):
            try:
                val = float(v)
            except ValueError:
                val = np.nan
            if abs(val) >= abs(missing_val) * 0.99:
                val = np.nan
            if month_idx > 12:
                break
            rows.append({"year": year, "month": month_idx, "value": val})
    df = pd.DataFrame(rows)
    df["month_start"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01"
    )
    df = df.drop_duplicates(subset="month_start", keep="last")
    return df[["month_start", "value"]].set_index("month_start").sort_index()


def _download(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 research"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def collect_oni() -> pd.DataFrame:
    print("Downloading ONI ...", flush=True)
    raw = _download("https://psl.noaa.gov/data/correlation/oni.data")
    df = _parse_psl_matrix(raw, missing_val=99.9)
    df.columns = ["oni"]
    df.to_csv(OUT / "oni_monthly.csv")
    print(f"  ONI: {len(df)} months, {df.index.min().date()} - {df.index.max().date()}")
    return df


def collect_pdo() -> pd.DataFrame:
    print("Downloading PDO ...", flush=True)
    raw = _download("https://psl.noaa.gov/data/correlation/pdo.data")
    df = _parse_psl_matrix(raw, missing_val=-9999.0)
    df.columns = ["pdo"]
    df.to_csv(OUT / "pdo_monthly.csv")
    print(f"  PDO: {len(df)} months, {df.index.min().date()} - {df.index.max().date()}")
    return df


def build_combined(oni: pd.DataFrame, pdo: pd.DataFrame) -> pd.DataFrame:
    idx = pd.date_range("1985-01-01", "2026-10-01", freq="MS")
    combined = oni.reindex(idx).join(pdo.reindex(idx), how="outer")
    combined.index.name = "month_start"
    for lag in [2, 3, 4, 6]:
        combined[f"oni_lag{lag}"] = combined["oni"].shift(lag)
    combined["oni3_t2"] = combined["oni"].shift(2).rolling(3, min_periods=2).mean()
    combined["pdo3_t2"] = combined["pdo"].shift(2).rolling(3, min_periods=2).mean()
    warm = (combined["oni"] >= 0.5).astype(float)
    combined["enso_warm3"] = warm.rolling(3, min_periods=3).min().shift(2)
    cold = (combined["oni"] <= -0.5).astype(float)
    combined["enso_cold3"] = cold.rolling(3, min_periods=3).min().shift(2)
    path = OUT / "climate_indices_combined.csv"
    combined.to_csv(path)
    print(f"  Combined: {len(combined)} months -> {path.name}")
    return combined


if __name__ == "__main__":
    oni = collect_oni()
    pdo = collect_pdo()
    combined = build_combined(oni, pdo)
    print("\n2019-10 to 2020-06:")
    print(combined.loc["2019-10-01":"2020-06-01",
                        ["oni", "pdo", "oni_lag3", "oni3_t2"]].to_string())

