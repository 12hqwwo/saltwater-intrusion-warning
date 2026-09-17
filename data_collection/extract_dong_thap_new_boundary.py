"""
Script: extract_dong_thap_new_boundary.py
Mục đích: Từ GADM Level 1 (toàn quốc VN), trích xuất và gộp ranh giới
          tỉnh Đồng Tháp (cũ) + Tiền Giang (cũ) thành 1 polygon "Đồng Tháp mới"
          rồi lưu vào data/raw/spatial/dong_thap_boundary.geojson

Yêu cầu: pip install geopandas shapely
"""
import json
import geopandas as gpd
from pathlib import Path

# ─── Đường dẫn ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent  # thư mục gốc dự án (TLCN/)
GADM_PATH = ROOT / "gadm41_VNM_1.json"
OUT_PATH  = ROOT / "data" / "raw" / "spatial" / "dong_thap_boundary.geojson"

# ─── Đọc GADM ────────────────────────────────────────────────────────────────
print("Đọc GADM Level 1...")
gdf = gpd.read_file(GADM_PATH)

# Kiểm tra các tên tỉnh có liên quan (để debug nếu cần)
tinh_list = sorted(gdf["NAME_1"].tolist())
print(f"Tổng số tỉnh/thành: {len(tinh_list)}")
# In các tỉnh có thể là DT / TG để xác nhận tên chính xác
dt_candidates = [t for t in tinh_list if "ng Th" in t or "Giang" in t]
print("Tỉnh ứng viên:", dt_candidates)

# ─── Lọc Đồng Tháp và Tiền Giang ─────────────────────────────────────────────
TARGET_PROVINCES = {"ĐồngTháp", "TiềnGiang", "Dong Thap", "Tien Giang"}
mask = gdf["NAME_1"].str.replace(' ', '').isin({"ĐồngTháp", "TiềnGiang", "DongThap", "TienGiang"})
subset = gdf[mask].copy()
print(f"\nTìm thấy {len(subset)} tỉnh:")
print(subset[["NAME_1", "GID_1"]].to_string(index=False))

if len(subset) == 0:
    raise ValueError("Không tìm thấy tỉnh Đồng Tháp / Tiền Giang! Hãy kiểm tra lại tên trong NAME_1.")

# ─── Gộp ranh giới ────────────────────────────────────────────────────────────
merged = subset.dissolve().copy()
merged["NAME_1"]      = "Đồng Tháp (mới)"
merged["NOTE"]        = "Gộp từ Đồng Tháp + Tiền Giang sau sắp xếp hành chính 12/6/2025"
merged["SOURCE"]      = "GADM v4.1 – https://gadm.org/"
merged["CRS"]         = "EPSG:4326 (WGS84)"
merged["COMPONENT_PROVINCES"] = "Đồng Tháp + Tiền Giang"

print("\nKiểm tra CRS:", merged.crs)

# Đảm bảo đầu ra là EPSG:4326
if merged.crs.to_epsg() != 4326:
    merged = merged.to_crs(epsg=4326)
    print("Đã chuyển về EPSG:4326")

# ─── Lưu file ─────────────────────────────────────────────────────────────────
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
merged.to_file(OUT_PATH, driver="GeoJSON")
print(f"\n✅ Đã lưu ranh giới Đồng Tháp mới vào: {OUT_PATH}")

# ─── Kiểm tra nhanh ───────────────────────────────────────────────────────────
result = gpd.read_file(OUT_PATH)
bounds = result.total_bounds
print(f"Bounding box: minX={bounds[0]:.4f}, minY={bounds[1]:.4f}, maxX={bounds[2]:.4f}, maxY={bounds[3]:.4f}")
print(f"  → Phải nằm trong khoảng lon ~104.5–107.0°E, lat ~9.5–11.0°N (vùng ĐBSCL + Tiền Giang)")
