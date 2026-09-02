import os, glob
import pandas as pd
import numpy as np
import xarray as xr
from pathlib import Path

DATA_DIR = Path(r"d:\Study\TLCN\data")
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# 1. Ham xu ly Conductivity (Monthly)
def get_conductivity():
    print("Loading Conductivity...")
    dfs = []
    for f in glob.glob(str(DATA_DIR / "interim" / "conductivity_*_monthly_clean.csv")):
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['date'])
        df['month_start'] = df['date'].dt.to_period('M').dt.to_timestamp()
        
        # Nhieu khi co the trung lap trong 1 thang -> Resample lai
        df = df.groupby(['station', 'month_start']).agg(
            conductivity_mS_per_m=('conductivity_mS_per_m', 'mean')
        ).reset_index()
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# 2. Ham xu ly Open-Meteo (Daily -> Monthly)
def get_meteo():
    print("Loading Open-Meteo...")
    dfs = []
    for f in glob.glob(str(DATA_DIR / "raw" / "openmeteo_rainfall" / "openmeteo_*_daily.csv")):
        # Bo qua file all_stations hoac file cu
        if "all_stations" in f or "1985_2026" in f:
            continue
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['date'])
        df['month_start'] = df['date'].dt.to_period('M').dt.to_timestamp()
        
        # Thong ke theo thang
        df_month = df.groupby(['station', 'month_start']).agg(
            precipitation_sum=('precipitation_sum', 'sum'),
            temperature_mean=('temperature_2m_mean', 'mean'),
            temperature_max=('temperature_2m_max', 'max'),
            temperature_min=('temperature_2m_min', 'min'),
            evapotranspiration_sum=('et0_fao_evapotranspiration', 'sum'),
            windspeed_mean=('windspeed_10m_max', 'mean'),
            humidity_mean=('relative_humidity_2m_mean', 'mean'),
            shortwave_rad_sum=('shortwave_radiation_sum', 'sum')
        ).reset_index()
        dfs.append(df_month)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# 3. Ham xu ly Dahiti Water Level (Irregular -> Monthly)
def get_dahiti():
    print("Loading DAHITI Water Level...")
    dfs = []
    for f in glob.glob(str(DATA_DIR / "raw" / "waterlevel" / "dahiti_waterlevel_*.csv")):
        df = pd.read_csv(f)
        if df.empty: continue
        df['date'] = pd.to_datetime(df['date'])
        df['month_start'] = df['date'].dt.to_period('M').dt.to_timestamp()
        # Lay mean water level
        df_month = df.groupby(['station', 'month_start']).agg(
            water_level_m=('water_level_m', 'mean')
        ).reset_index()
        dfs.append(df_month)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# 4. Ham xu ly GloFAS Discharge (Daily NC -> Monthly)
def get_glofas():
    print("Loading GloFAS Discharge NetCDF...")
    dfs = []
    nc_files = glob.glob(str(DATA_DIR / "raw" / "waterlevel" / "glofas_tanchau" / "glofas_*.nc"))
    if not nc_files:
        print("  Không tìm thấy file nc GloFAS")
        return pd.DataFrame()
        
    for f in nc_files:
        try:
            ds = xr.open_dataset(f)
            # GloFAS bien ten la 'qrtp' hoac 'dis24'
            var_name = [v for v in ds.data_vars if v != 'crs'][0]  # lay bien chinh phai la data
            
            # Xu ly theo chieu thoi gian
            dims = [d for d in ds.dims if d in ('lat', 'lon', 'latitude', 'longitude')]
            df_nc = ds[var_name].mean(dim=dims).to_dataframe().reset_index()
            # Rename cho chuan
            df_nc = df_nc.rename(columns={'time': 'date', "valid_time": "date", var_name: "glofas_discharge_m3s"})
            
            if 'date' not in df_nc.columns:
                print(f"  Cannot infer time col for {f}: cols = {df_nc.columns}")
                continue
                
            df_nc['date'] = pd.to_datetime(df_nc['date'])
            df_nc['month_start'] = df_nc['date'].dt.to_period('M').dt.to_timestamp()
            df_month = df_nc.groupby('month_start').agg(
                glofas_discharge_m3s=('glofas_discharge_m3s', 'mean')
            ).reset_index()
            df_month['station'] = 'TanChau'  # Danh rieng cho Tan Chau
            dfs.append(df_month)
        except Exception as e:
            print(f"  Error reading {f}: {e}")
            
    if dfs:
        df_all = pd.concat(dfs, ignore_index=True)
        # Vi co the trung lap giua cac file NC (do request chong cheo), group lai luon
        return df_all.groupby(['station', 'month_start']).mean().reset_index()
    return pd.DataFrame()

def main():
    cond = get_conductivity()
    meteo = get_meteo()
    water = get_dahiti()
    disch = get_glofas()
    
    print("\nMerging data...")
    # Ta dung outer merge kieu full de co matrix day du
    # Danh sach tat ca stations o day la MyTho va TanChau
    
    # 1. Merge Cond + Meteo tren (station, month_start)
    master = pd.merge(cond, meteo, on=['station', 'month_start'], how='outer')
    
    # 2. Merge voi DAHITI
    if not water.empty:
        master = pd.merge(master, water, on=['station', 'month_start'], how='outer')
    else:
        master['water_level_m'] = np.nan
        
    # 3. Merge voi GloFAS
    if not disch.empty:
        master = pd.merge(master, disch, on=['station', 'month_start'], how='outer')
    else:
        master['glofas_discharge_m3s'] = np.nan
        
    master = master.sort_values(['station', 'month_start']).reset_index(drop=True)
    
    out_csv = PROCESSED_DIR / "master_timeseries.csv"
    out_pq = PROCESSED_DIR / "master_timeseries.parquet"
    
    print(f"Saving to {out_csv} ...")
    master.to_csv(out_csv, index=False)
    master.to_parquet(out_pq, index=False)
    
    print("\nCheck shapes:")
    print(f"Cond: {cond.shape}")
    print(f"Meteo: {meteo.shape}")
    print(f"Dahiti: {water.shape}")
    print(f"Glofas: {disch.shape}")
    print(f"Master: {master.shape}")
    print("\nDate range per station:")
    print(master.groupby('station')['month_start'].agg(['min', 'max', 'count']))

if __name__ == '__main__':
    main()
