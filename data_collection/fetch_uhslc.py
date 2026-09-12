import pandas as pd
import requests
import time
from pathlib import Path

def download_with_resume(url, file_path):
    headers = {'User-Agent': 'Mozilla/5.0'}
    while True:
        file_size = 0
        if file_path.exists():
            file_size = file_path.stat().st_size
            
        resume_headers = headers.copy()
        if file_size > 0:
            resume_headers['Range'] = f'bytes={file_size}-'
            
        try:
            response = requests.get(url, stream=True, timeout=30, headers=resume_headers)
            
            if response.status_code == 416: # Range Not Satisfiable (đã tải xong)
                break
                
            if response.status_code == 206:
                mode = 'ab'
            elif response.status_code == 200:
                mode = 'wb'
                file_size = 0
            else:
                response.raise_for_status()
                
            with open(file_path, mode) as f:
                for chunk in response.iter_content(chunk_size=16384):
                    if chunk:
                        f.write(chunk)
                        file_size += len(chunk)
                        if file_size % (1024 * 1024) < 16384:
                            print(f"   ► Đã tải {file_size / (1024*1024):.1f} MB...")
            
            # Ra khỏi vòng lặp iter_content thành công tức là đã hết file
            break
            
        except requests.exceptions.RequestException as e:
            print(f"   [!] Rớt mạng hoặc Server ngắt. Tự động tải tiếp từ {file_size / (1024*1024):.1f} MB... (Chờ 3s)")
            time.sleep(3)

def main():
    RAW_WATER = Path(r"d:\Study\TLCN\data\raw\waterlevel")
    RAW_WATER.mkdir(parents=True, exist_ok=True)
    
    out_file = RAW_WATER / "uhslc_tides_VungTau_id142_daily.csv"
    temp_csv = RAW_WATER / "temp_uhslc.csv"
    
    print("⏳ Đang tải chuỗi dữ liệu Thủy triều Vũng Tàu (hỗ trợ Auto-Resume)...")
    url = "https://uhslc.soest.hawaii.edu/data/csv/fast/hourly/h142.csv"
    
    download_with_resume(url, temp_csv)
    
    print("📥 Đã tải file thô thành công. Đang tính toán Đỉnh Triều (High Tide)...")
    try:
        df = pd.read_csv(temp_csv, header=None, names=['year', 'month', 'day', 'hour', 'sea_level_mm'])
        
        # Xóa file tạm cho đỡ nặng máy
        if temp_csv.exists():
            temp_csv.unlink()
            
        import numpy as np
        df['sea_level_mm'] = df['sea_level_mm'].replace(-32767, np.nan)
        df['sea_level_m'] = df['sea_level_mm'].astype(float) / 1000.0
        df['date'] = pd.to_datetime(df[['year', 'month', 'day']])
        
        daily_max = df.groupby('date')['sea_level_m'].max().reset_index()
        daily_max.rename(columns={'sea_level_m': 'tide_max_m'}, inplace=True)
        daily_max['station'] = 'VungTau'
        
        daily_max['tide_max_m'] = daily_max['tide_max_m'].astype(float).interpolate()
        daily_max = daily_max[daily_max['date'].dt.year >= 1985].reset_index(drop=True)
        
        daily_max.to_csv(out_file, index=False)
        print(f"✅ Đã lưu tập dữ liệu chuẩn: {out_file.name}")
        print(f"   Tổng số ngày: {len(daily_max)} (từ {daily_max['date'].min().date()} đến {daily_max['date'].max().date()})")
    except Exception as e:
        print(f"❌ Có lỗi lúc xử lý dữ liệu: {e}")

if __name__ == '__main__':
    main()
