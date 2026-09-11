import sys, os, time
from pathlib import Path
import cdsapi

ENV_PATH = Path(r"d:\Study\TLCN\.env")
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

API_KEY = os.environ.get("CDS_API_KEY")
URL = "https://ewds.climate.copernicus.eu/api"
c = cdsapi.Client(url=URL, key=API_KEY)

RAW_WATER = Path(r"d:\Study\TLCN\data\raw\waterlevel")
out_dir = RAW_WATER / "glofas_tanchau"
out_dir.mkdir(parents=True, exist_ok=True)
area = [10.9, 105.1, 10.7, 105.3]

groups = [
    ("31days", [1,3,5,7,8,10,12], 31),
    ("30days", [4,6,9,11], 30),
    ("29days", [2], 29)
]

print("Downloading GloFAS Discharge Tan Chau 1985-2023...")

for y in range(1985, 2024):
    y_str = str(y)
    
    for g_name, months, d_limit in groups:
        m_strs = [f"{m:02d}" for m in months]
        d_strs = [f"{d:02d}" for d in range(1, d_limit + 1)]
        out_file = out_dir / f"glofas_{y_str}_{g_name}.nc"
        
        if out_file.exists():
            continue
            
        print(f"Requesting {y_str} - {g_name}...")
        
        req = {
            'system_version': 'version_4_0',
            'hydrological_model': 'lisflood',
            'product_type': 'consolidated',
            'variable': 'average_river_discharge_in_the_last_24_hours',
            'timespan': 'time_mean',
            'year': [y_str],
            'month': m_strs,
            'day': d_strs,
            'area': area,
            'data_format': 'netcdf',
            'download_format': 'unarchived',
        }
        
        try:
            c.retrieve('cems-glofas-historical', req, str(out_file))
        except Exception as e:
            msg = str(e)
            if "valid combination" in msg:
                # Retry with intermediate if consolidated is not available for this year
                print(f"  [Retry] Consolidated fail for {y_str}. Trying intermediate...")
                req['product_type'] = 'intermediate'
                try:
                    c.retrieve('cems-glofas-historical', req, str(out_file))
                except Exception as e2:
                    print(f"  !! Failed {y_str} {g_name}: {e2}")
            else:
                print(f"  !! Error {y_str} {g_name}: {e}")

print("DONE")
