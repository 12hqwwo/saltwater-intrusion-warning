"""
Script tai du lieu DAHITI:
- Water Level (altimetry) tai tram gan Tan Chau va My Tho
- Discharge tai tram gan Tan Chau
"""

import sys, os, json, requests, math
import pandas as pd
from pathlib import Path
from datetime import datetime

# Load .env
ENV_PATH = Path(__file__).parent / ".env"
for line in ENV_PATH.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

API_KEY = os.environ.get("DAHITI_API_KEY", "")
if not API_KEY:
    print("ERROR: DAHITI_API_KEY not found in .env")
    sys.exit(1)

BASE_URL = "https://dahiti.dgfi.tum.de/api/v2/"
RAW_WATER = Path(r"d:\Study\TLCN\data\raw\waterlevel")
RAW_WATER.mkdir(parents=True, exist_ok=True)

STATIONS = {
    "TanChau": {"lat": 10.804, "lon": 105.234},
    "MyTho":   {"lat": 10.360, "lon": 106.360},
}


def api_post(endpoint, args, add_format=False):
    """POST request DAHITI API v2, tra ve dict hoac None neu loi."""
    args = dict(args)
    args["api_key"] = API_KEY
    if add_format:
        args["format"] = "json"
    r = requests.post(BASE_URL + endpoint, data=args, timeout=60)
    if r.status_code != 200:
        print(f"    HTTP {r.status_code}: {r.text[:300]}")
        return None
    try:
        return json.loads(r.text)
    except Exception as e:
        print(f"    JSON parse error: {e} | raw: {r.text[:200]}")
        return None


def list_targets_bbox(lat, lon, radius_km=200):
    """Liet ke tram DAHITI trong vong radius_km quanh (lat, lon)."""
    d = radius_km / 111.0
    return api_post("list-targets/", {
        "min_lat": lat - d, "max_lat": lat + d,
        "min_lon": lon - d, "max_lon": lon + d,
    }, add_format=True)


def get_nearest_target(lat, lon):
    # format param KHONG ho tro o endpoint nay
    return api_post("get-nearest-target/", {"latitude": lat, "longitude": lon}, add_format=False)


def choose_best_target(targets_data, ref_lat, ref_lon, prefer_type="River"):
    """Chon tram co water_level_altimetry public, gan nhat, uu tien River."""
    if not targets_data:
        return None
    items = targets_data if isinstance(targets_data, list) else targets_data.get("data", [])

    candidates = []
    for t in items:
        da = t.get("data_access", {}) or {}
        if da.get("water_level_altimetry") == "public":
            tlat = float(t.get("latitude", 0))
            tlon = float(t.get("longitude", 0))
            dist = math.sqrt((tlat - ref_lat)**2 + (tlon - ref_lon)**2) * 111
            candidates.append({**t, "_dist_km": dist})

    if not candidates:
        print("    ! Khong co tram nao co water_level_altimetry = public")
        return None

    # Uu tien River, roi theo khoang cach
    rivers = [c for c in candidates if "river" in str(c.get("type", "")).lower()]
    pool = rivers if rivers else candidates
    pool.sort(key=lambda x: x["_dist_km"])
    best = pool[0]
    print(f"    Best: id={best.get('dahiti_id')} | {best.get('target_name')} "
          f"| type={best.get('type')} | dist={best['_dist_km']:.1f} km")
    return best


def download_water_level(dahiti_id, station_name):
    print(f"  Tai Water Level dahiti_id={dahiti_id}...")
    data = api_post("download-water-level/", {"dahiti_id": int(dahiti_id)}, add_format=True)
    if not data:
        return None
    records = data.get("data", [])
    if not records:
        print("    Khong co records")
        return None
    df = pd.DataFrame(records)
    # Tim cot date (co the la 'date' hoac 'datetime')
    date_col = next((c for c in df.columns if "date" in c.lower() or "time" in c.lower()), None)
    if date_col is None:
        print(f"    WARN: Khong tim thay cot date. Cot co san: {list(df.columns)}")
        print(f"    Data mau: {records[:2]}")
        date_col = df.columns[0]  # fallback
    df["date"] = pd.to_datetime(df[date_col])
    if date_col != "date":
        df = df.drop(columns=[date_col])
    df = df.sort_values("date").reset_index(drop=True)
    # Rename theo tieu chuan
    rename = {"wse": "water_level_m", "wse_u": "water_level_err_m", "water_level": "water_level_m", "error": "water_level_err_m"}
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df.insert(0, "station", station_name)
    df.insert(1, "dahiti_id", dahiti_id)
    tgt = data.get("target", {})
    df.insert(2, "target_name", tgt.get("target_name", ""))
    df.insert(3, "target_lat", tgt.get("latitude", ""))
    df.insert(4, "target_lon", tgt.get("longitude", ""))

    out = RAW_WATER / f"dahiti_waterlevel_{station_name}_id{dahiti_id}.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    dmin = df["date"].min().date()
    dmax = df["date"].max().date()
    print(f"    OK: {len(df)} records | {dmin} -> {dmax}")
    print(f"    Saved: {out.name}")
    return df


def download_discharge(dahiti_id, station_name):
    print(f"  Tai Discharge dahiti_id={dahiti_id}...")
    data = api_post("download-discharge/", {"dahiti_id": int(dahiti_id)}, add_format=True)
    if not data:
        return None
    records = data.get("data", [])
    if not records:
        print("    Khong co discharge cho tram nay")
        return None
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df.insert(0, "station", station_name)
    df.insert(1, "dahiti_id", dahiti_id)
    out = RAW_WATER / f"dahiti_discharge_{station_name}_id{dahiti_id}.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    dmin = df["date"].min().date()
    dmax = df["date"].max().date()
    print(f"    OK: {len(df)} records | {dmin} -> {dmax}")
    print(f"    Saved: {out.name}")
    return df


if __name__ == "__main__":
    print("=" * 55)
    print("TAI DU LIEU DAHITI v2 (Water Level + Discharge)")
    print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print("=" * 55)

    summary = {}

    for sname, sinfo in STATIONS.items():
        lat, lon = sinfo["lat"], sinfo["lon"]
        print(f"\n{'='*45}\nTram: {sname} ({lat}, {lon})\n{'='*45}")

        # 1. Liet ke tram trong vung rong
        print("  Tim tat ca tram trong vong 200km...")
        targets_data = list_targets_bbox(lat, lon, radius_km=200)
        if targets_data:
            items = targets_data if isinstance(targets_data, list) else targets_data.get("data", [])
            print(f"  Tim thay {len(items)} tram trong vung:")
            for t in items[:15]:
                da = t.get("data_access", {}) or {}
                wl = da.get("water_level_altimetry", "-")
                disch = da.get("discharge", "-")
                print(f"    id={t.get('dahiti_id')} | {t.get('target_name','?'):<30} "
                      f"| type={str(t.get('type','?')):<10} | wl={wl} discharge={disch}")
        else:
            print("  Khong tim thay tram nao (thu get-nearest-target)...")

        # 2. Chon tram tot nhat
        best = choose_best_target(targets_data, lat, lon)

        if best is None:
            # Thu get-nearest-target
            nearest_resp = get_nearest_target(lat, lon)
            if nearest_resp and nearest_resp.get("code") == 200:
                nd = nearest_resp.get("data", {})
                print(f"    Nearest (bat ky): id={nd.get('id')} | {nd.get('target_name')}")
                # Dung id do thu download
                best = {"dahiti_id": nd.get("id"), "target_name": nd.get("target_name")}
            else:
                print(f"  SKIP {sname}: khong tim thay tram phu hop")
                continue

        dahiti_id = best.get("dahiti_id") or best.get("id")
        summary[sname] = {"dahiti_id": dahiti_id, "target_name": best.get("target_name")}

        # 3. Download Water Level
        wl_df = download_water_level(dahiti_id, sname)

        # 4. Download Discharge (chi TanChau)
        # if sname == "TanChau":
        #     disch_df = download_discharge(dahiti_id, sname)
        #     if disch_df is None: ...

    # Luu summary
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sp = RAW_WATER / "dahiti_download_summary.json"
    sp.write_text(json.dumps({"downloaded_at": now, "stations": summary}, indent=2, ensure_ascii=False))
    print(f"\nSummary: {sp.name}")
    print("\n=== HOAN THANH ===")
