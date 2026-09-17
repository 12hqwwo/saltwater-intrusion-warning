"""
Script: extract_boundary_no_geopandas.py
Không cần geopandas, chỉ dùng thư viện chuẩn Python.
Trích xuất polygon Đồng Tháp + Tiền Giang từ GADM và gộp thành dong_thap_boundary.geojson.
"""
import json
from pathlib import Path

ROOT      = Path(__file__).parent.parent
GADM_PATH = ROOT / "gadm41_VNM_1.json"
OUT_PATH  = ROOT / "data" / "raw" / "spatial" / "dong_thap_boundary.geojson"

print("Đọc GADM...")
with open(GADM_PATH, "r", encoding="utf-8") as f:
    gadm = json.load(f)

all_features = gadm["features"]
print(f"Tổng số features: {len(all_features)}")

# In tất cả tên tỉnh để kiểm tra
names = [feat["properties"]["NAME_1"] for feat in all_features]
print("\n--- Danh sách tỉnh ---")
for n in sorted(names):
    print(" ", n)

# Lọc Đồng Tháp + Tiền Giang
target_features = []
for feat in all_features:
    name = feat["properties"].get("NAME_1", "")
    if "ngTh" in name or "ng Th" in name:          # ĐồngTháp
        print(f"\n✅ Tìm thấy: {name} (GID={feat['properties']['GID_1']})")
        target_features.append(feat)
    elif "nGiang" in name or "n Giang" in name:    # TiềnGiang
        print(f"✅ Tìm thấy: {name} (GID={feat['properties']['GID_1']})")
        target_features.append(feat)

print(f"\nSố tỉnh được chọn: {len(target_features)}")

if len(target_features) == 0:
    raise ValueError("Không tìm thấy tỉnh! Hãy đọc danh sách tỉnh ở trên và điều chỉnh điều kiện lọc.")

# --- Gộp thành FeatureCollection ---
# Không dùng dissolve (cần geopandas); thay vào đó giữ nguyên từng polygon
# nhưng đặt tên chung – QGIS có thể overlay để xem phạm vi nghiên cứu
merged_geojson = {
    "type": "FeatureCollection",
    "name": "dong_thap_new_boundary",
    "crs": {
        "type": "name",
        "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
    },
    "features": []
}

for feat in target_features:
    new_props = {
        "NAME_1":      feat["properties"]["NAME_1"],
        "GID_1":       feat["properties"]["GID_1"],
        "PROVINCE_ROLE": "Đồng Tháp mới – thành phần tỉnh",
        "NOTE": "Sáp nhập vào tỉnh Đồng Tháp mới từ 12/6/2025 (Nghị quyết sắp xếp ĐVHCNC)",
        "SOURCE": "GADM v4.1 (gadm.org)",
        "CRS": "EPSG:4326 WGS84"
    }
    merged_geojson["features"].append({
        "type": "Feature",
        "properties": new_props,
        "geometry": feat["geometry"]
    })

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(merged_geojson, f, ensure_ascii=False, indent=2)

print(f"\n✅ Đã lưu: {OUT_PATH}")
print(f"   Gồm {len(merged_geojson['features'])} polygon (1 Đồng Tháp + 1 Tiền Giang)")
print("   → Mở cả hai polygon trong QGIS để xem phạm vi nghiên cứu tổng thể.")
print("   → Để dissolve thành 1 polygon: Layer > Dissolve trong QGIS,")
print("     hoặc chạy lại script này sau khi `pip install geopandas`.")
