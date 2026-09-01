"""
Post-processing: Merge du lieu da tai thanh master_timeseries
- Du lieu Open-Meteo: da co trong raw/openmeteo_rainfall/
- Du lieu MRC: da co trong raw/mrc_conductivity/
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR    = Path(r"d:\Study\TLCN\data")
RAW_MRC    = BASE_DIR / "raw" / "mrc_conductivity"
RAW_METEO  = BASE_DIR / "raw" / "openmeteo_rainfall"
RAW_WATER  = BASE_DIR / "raw" / "waterlevel"
INTERIM    = BASE_DIR / "interim"
PROCESSED  = BASE_DIR / "processed"
METADATA_DIR = BASE_DIR / "metadata"

STATIONS = {
    "TanChau": {"lat": 10.804, "lon": 105.234, "mrc_code": "019803"},
    "MyTho":   {"lat": 10.360, "lon": 106.360, "mrc_code": "019805"},
}

# ============================================================
# Xu ly MRC Conductivity
# ============================================================
def process_mrc():
    print("\n=== Xu ly MRC Conductivity -> interim/ ===")
    results = []
    for name, info in STATIONS.items():
        code = info["mrc_code"]
        csv_files = list(RAW_MRC.glob(f"*{code}*.csv"))
        if not csv_files:
            print(f"  WARN: khong tim thay CSV cho {code}")
            continue
        df = pd.read_csv(csv_files[0])
        df.columns = [c.strip() for c in df.columns]
        ts_col = next(c for c in df.columns if "Timestamp" in c)
        df = df.rename(columns={
            ts_col: "date",
            "Value": "conductivity_mS_per_m",
            "Unit": "unit",
            "Grade": "grade",
            "Observed or Estimated": "obs_type",
            "Approval Level": "approval",
        })
        df["date"] = pd.to_datetime(df["date"], utc=False)
        df["date"] = df["date"].dt.tz_localize(None)  # Strip timezone
        df["station"] = name
        df["lat"] = info["lat"]
        df["lon"] = info["lon"]
        keep = ["date","station","lat","lon","conductivity_mS_per_m","unit","grade","approval","obs_type"]
        df = df[[c for c in keep if c in df.columns]]
        df = df.sort_values("date").reset_index(drop=True)

        out = INTERIM / f"conductivity_{name}_monthly_clean.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"  {name}: {len(df)} rows | {df['date'].min().date()} -> {df['date'].max().date()}")
        results.append(df)
    return results

# ============================================================
# Xu ly Open-Meteo (ngay -> thang)
# ============================================================
def process_meteo():
    print("\n=== Xu ly Open-Meteo (ngay -> thang) -> interim/ ===")
    results = {}
    for name in STATIONS:
        csv_path = RAW_METEO / f"openmeteo_{name}_daily.csv"
        if not csv_path.exists():
            print(f"  WARN: Khong co {csv_path.name}")
            continue
        df = pd.read_csv(csv_path, parse_dates=["date"])
        df["date"] = df["date"].dt.tz_localize(None)
        df["ym"] = df["date"].dt.to_period("M")

        agg_map = {
            "precipitation_sum": "sum",
            "temperature_2m_max": "mean",
            "temperature_2m_min": "mean",
            "temperature_2m_mean": "mean",
            "et0_fao_evapotranspiration": "sum",
            "windspeed_10m_max": "mean",
            "relative_humidity_2m_mean": "mean",
            "shortwave_radiation_sum": "sum",
        }
        # Chi giu cac cot ton tai
        valid_agg = {k: v for k, v in agg_map.items() if k in df.columns}

        monthly = df.groupby("ym").agg(valid_agg).reset_index()
        monthly.columns = ["ym"] + [
            {"precipitation_sum": "precip_mm",
             "temperature_2m_max": "temp_max_c",
             "temperature_2m_min": "temp_min_c",
             "temperature_2m_mean": "temp_mean_c",
             "et0_fao_evapotranspiration": "et0_mm",
             "windspeed_10m_max": "wind_max_ms",
             "relative_humidity_2m_mean": "rh_pct",
             "shortwave_radiation_sum": "radiation_mj"}.get(c, c)
            for c in monthly.columns[1:]
        ]
        monthly["date"] = monthly["ym"].dt.to_timestamp()
        monthly = monthly.drop(columns=["ym"])

        out = INTERIM / f"meteo_{name}_monthly.csv"
        monthly.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"  {name}: {len(monthly)} thang | {monthly['date'].min().date()} -> {monthly['date'].max().date()}")
        results[name] = monthly
    return results

# ============================================================
# Merge master
# ============================================================
def build_master(cond_dfs, meteo_monthly):
    print("\n=== Merge Master Time Series ===")
    frames = []
    for name, info in STATIONS.items():
        cond = next((df for df in cond_dfs if df["station"].iloc[0] == name), None)
        if cond is None:
            continue

        # Tao year-month key kieu string "YYYY-MM"
        cond = cond.copy()
        cond["ym"] = cond["date"].dt.to_period("M").dt.strftime("%Y-%m")

        # Merge voi meteo
        if name in meteo_monthly:
            m = meteo_monthly[name].copy()
            m["ym"] = m["date"].dt.to_period("M").dt.strftime("%Y-%m")
            m = m.drop(columns=["date"])
            merged = cond.merge(m, on="ym", how="outer")
        else:
            merged = cond.copy()
            merged["ym"] = merged["ym"]

        # Tao cot date chuyen nghiep tu ym
        merged["date"] = pd.to_datetime(merged["ym"] + "-01")
        merged = merged.sort_values("date").reset_index(drop=True)

        # Them thong tin tram tu conductivity (fill NaN)
        merged["station"] = merged.get("station", pd.Series([name]*len(merged))).fillna(name)
        merged["lat"] = info["lat"]
        merged["lon"] = info["lon"]

        # Sap xep cot
        first_cols = ["date", "station", "lat", "lon", "conductivity_mS_per_m"]
        rest_cols = [c for c in merged.columns if c not in first_cols + ["ym"]]
        merged = merged[[c for c in first_cols if c in merged.columns] + rest_cols]

        frames.append(merged)

    master = pd.concat(frames, ignore_index=True)
    master = master.sort_values(["station","date"]).reset_index(drop=True)

    # Luu
    PROCESSED.mkdir(exist_ok=True)
    csv_out = PROCESSED / "master_timeseries.csv"
    master.to_csv(csv_out, index=False, encoding="utf-8-sig")
    print(f"\n  Saved CSV: {csv_out} ({len(master)} rows, {len(master.columns)} cols)")

    try:
        master.to_parquet(PROCESSED / "master_timeseries.parquet", index=False)
        print(f"  Saved Parquet: master_timeseries.parquet")
    except Exception as e:
        print(f"  Parquet skip: {e}")

    # Tom tat
    print("\n  --- Tom tat ---")
    for s in master["station"].unique():
        if not isinstance(s, str):
            continue
        sub = master[master["station"] == s]
        print(f"  {s}: {len(sub)} hang | {sub['date'].min().date()} -> {sub['date'].max().date()}")
        print(f"    Missing conductivity: {sub['conductivity_mS_per_m'].isna().sum()}")
        if "precip_mm" in sub.columns:
            print(f"    Missing precip:        {sub['precip_mm'].isna().sum()}")
    return master

# ============================================================
# Data Dictionary
# ============================================================
def write_dict():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    text = f"""# Data Dictionary -- Mo hinh du bao xam nhap man DBSCL
*Tao: {now}*

## Tram quan trac
| Ten tram | Lat | Lon | Ma MRC | Song |
|---|---|---|---|---|
| TanChau | 10.804 | 105.234 | 019803 | Mekong (song Tien, thuong) |
| MyTho   | 10.360 | 106.360 | 019805 | Song Tien (cua song) |

## Bien du lieu
| Bien | Don vi | Tan suat goc | Tan suat processed | Nguon | Ngay tai | Pham vi |
|---|---|---|---|---|---|---|
| conductivity_mS_per_m | mS/m | Thang | Thang | MRC Data Portal | 2026-08-31 | 1985-05 -> 2023-12 |
| precip_mm | mm | Ngay | Thang (tong) | Open-Meteo ERA5-Land | {now[:10]} | 1985-01 -> 2026-08 |
| temp_max/min/mean_c | C | Ngay | Thang (TB) | Open-Meteo ERA5-Land | {now[:10]} | 1985-01 -> 2026-08 |
| et0_mm | mm | Ngay | Thang (tong) | Open-Meteo FAO PM | {now[:10]} | 1985-01 -> 2026-08 |
| wind_max_ms | m/s | Ngay | Thang (TB) | Open-Meteo | {now[:10]} | 1985-01 -> 2026-08 |
| rh_pct | % | Ngay | Thang (TB) | Open-Meteo | {now[:10]} | 1985-01 -> 2026-08 |
| radiation_mj | MJ/m2 | Ngay | Thang (tong) | Open-Meteo | {now[:10]} | 1985-01 -> 2026-08 |
| water_level_m | m | -- | -- | DAHITI altimetry | MISSING (xem PLACEHOLDER) | -- |

## Khoang trong (Gaps)
- conductivity: 2024-01 -> 2026-08 (32 thang)
  -> Can mua MRC hoac lien he SIWRR / Dai KTTV Nam Bo
- water_level: Toan bo
  -> Dang ky DAHITI (https://dahiti.dgfi.tum.de) hoac xin so lieu Dai KTTV

## Ghi chu ky thuat
- Temporal alignment: conductivity la thang -> meteo downsample ve thang
- Oulier conductivity: gia tri > 80 mS/m co the la loi cam bien (kiem tra 1998)
- Open-Meteo nguon: ERA5-Land reanalysis (5 km resolution)
- Timezone: UTC+07:00

## Tham khao
- MRC: https://portal.mrcmekong.org/time-series
- Open-Meteo: https://open-meteo.com/en/docs/historical-weather-api
- DAHITI: https://dahiti.dgfi.tum.de/
- SIWRR: https://www.siwrr.org.vn/
"""
    METADATA_DIR.mkdir(exist_ok=True)
    out = METADATA_DIR / "data_dictionary.md"
    out.write_text(text, encoding="utf-8")
    print(f"\n=== Data Dictionary -> {out} ===")

# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("POST-PROCESSING: MERGE MASTER TIMESERIES")
    print("=" * 50)

    cond_dfs = process_mrc()
    meteo_monthly = process_meteo()
    master = build_master(cond_dfs, meteo_monthly)
    write_dict()

    print("\n=== XONG ===")
