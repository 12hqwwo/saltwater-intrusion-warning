"""
Script: generate_synthetic_ec.py
Mục đích: Khắc phục việc thiếu dữ liệu thực tế từ trạm KTTV bằng cách tạo ra
một tập dữ liệu Độ dẫn điện (EC - mS/cm) giả lập có logic khoa học:
1. Trạm càng gần biển (Kinh độ càng đông) thì EC càng cao.
2. Mùa khô (tháng 12 - tháng 5) EC cao hơn mùa mưa (tháng 6 - tháng 11).
3. Dao động theo chu kỳ triều (bán nhật triều/nhật triều).
"""
import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).parent.parent
STATIONS_CSV = ROOT / "data" / "raw" / "spatial" / "sluice_gates_dong_thap_new.csv"
OUT_CSV = ROOT / "data" / "raw" / "hydrological" / "synthetic_ec_data.csv"

def generate_ec_data(start_date="2024-01-01", end_date="2024-06-30", freq="h"):
    # Đọc tọa độ trạm/cống
    try:
        df_stations = pd.read_csv(STATIONS_CSV)
    except FileNotFoundError:
        print(f"Không tìm thấy {STATIONS_CSV}. Đảm bảo đã có dữ liệu cống.")
        return
        
    df_stations = df_stations.dropna(subset=['longitude', 'latitude'])
    
    # Tạo dải thời gian (Time series)
    date_rng = pd.date_range(start=start_date, end=end_date, freq=freq)
    
    all_data = []
    
    # Tham số biển (Giả lập Biển Đông ở kinh độ ~106.8, vĩ độ ~10.2)
    sea_lon, sea_lat = 106.8, 10.25
    
    print(f"Bắt đầu tạo dữ liệu cho {len(df_stations)} trạm, từ {start_date} đến {end_date}...")
    
    for idx, row in df_stations.iterrows():
        station_id = row['gate_id']
        lon, lat = row['longitude'], row['latitude']
        
        # Khoảng cách tương đối tới biển (càng gần thì ngập mặn càng nặng)
        dist_to_sea = np.sqrt((lon - sea_lon)**2 + (lat - sea_lat)**2)
        base_ec = max(0.5, 30.0 - dist_to_sea * 80) # Giảm mạnh khi đi sâu vào đất liền
        
        for dt in date_rng:
            # 1. Hiệu ứng mùa (Tháng 3, 4 là cao điểm mặn)
            month = dt.month
            season_factor = np.sin((month - 1) * np.pi / 6) # Đỉnh vào tháng 4
            
            # 2. Hiệu ứng thủy triều (2 chu kỳ/ngày - Bán nhật triều)
            hour = dt.hour
            tide_factor = np.sin((hour / 12) * np.pi * 2) 
            
            # 3. Nhiễu ngẫu nhiên (noise)
            noise = np.random.normal(0, 0.5)
            
            # Tính toán EC cuối cùng
            current_ec = base_ec + (season_factor * base_ec * 0.5) + (tide_factor * base_ec * 0.3) + noise
            current_ec = max(0.1, round(current_ec, 2)) # Không âm, nhỏ nhất là 0.1 ngọt
            
            all_data.append({
                "timestamp": dt,
                "station_id": station_id,
                "station_name": row['gate_name'],
                "ec_value_mS_cm": current_ec,
                "is_synthetic": True
            })
            
    # Lưu ra CSV
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_out = pd.DataFrame(all_data)
    df_out.to_csv(OUT_CSV, index=False)
    
    print(f"✅ Đã tạo thành công {len(df_out)} dòng dữ liệu EC giả lập!")
    print(f"✅ Lưu tại: {OUT_CSV}")

if __name__ == "__main__":
    # Sinh dữ liệu 6 tháng đầu năm 2024 (mùa khô), mỗi giờ 1 nhịp
    generate_ec_data(start_date="2024-01-01", end_date="2024-05-31", freq="1h")
