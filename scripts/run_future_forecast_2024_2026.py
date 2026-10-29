"""Dự báo ngoại suy EC (mS/m) cho các tháng 2024 - 2026 dựa trên mô hình học máy đa biến kết hợp khí tượng Open-Meteo."""
import sys
from pathlib import Path
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer

FEATURE_FILE = ROOT / "data" / "features" / "10_monthly_feature_v2.csv"
OUTPUT_FILE = ROOT / "data" / "models" / "future_ec_forecast_2024_2026.csv"

def run_future_forecast():
    print("=" * 65)
    print("MÔ HÌNH HỌC MÁY ĐA BIẾN: DỰ BÁO XU THẾ EC TỪ 2024 ĐẾN 2026")
    print("=" * 65)

    df = pd.read_csv(FEATURE_FILE)
    features_list = ["month", "rainfall", "temperature", "wind"]
    
    results = []

    for station in ["TanChau", "MyTho"]:
        sub = df[df["location_id"] == station].sort_values("year_month").copy()
        
        # 1. Tập huấn luyện: các tháng có nhãn EC thực đo (1985 - 2023)
        train_mask = sub["ec_target"].notna()
        train_data = sub[train_mask]
        
        # 2. Tập cần dự báo: các tháng từ 2024-01 đến 2026-08
        future_mask = sub["year_month"] >= "2024-01"
        future_data = sub[future_mask].copy()

        # Tiền xử lý
        imputer = SimpleImputer(strategy="median")
        X_train = imputer.fit_transform(train_data[features_list])
        y_train = train_data["ec_target"].values
        X_future = imputer.transform(future_data[features_list])

        # Huấn luyện Random Forest
        rf = RandomForestRegressor(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=1
        )
        rf.fit(X_train, y_train)

        # Dự báo 32 tháng tương lai
        future_preds = rf.predict(X_future)
        future_data["predicted_ec_mS_m"] = np.round(future_preds, 3)
        
        for _, row in future_data.iterrows():
            results.append({
                "station": station,
                "year_month": row["year_month"],
                "predicted_ec_mS_m": row["predicted_ec_mS_m"],
                "rainfall_mm": row["rainfall"],
                "temperature_degC": row["temperature"],
                "wind_m_s": row["wind"],
                "model": "RandomForest_Multivariate_Weather"
            })

    res_df = pd.DataFrame(results)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    res_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n[OK] Đã hoàn thành dự báo và lưu kết quả vào:\n     {OUTPUT_FILE.relative_to(ROOT)}")
    
    # Mùa khô của đồ án: tháng 12 đến tháng 4 năm sau.
    print("\n--- MẪU DỰ BÁO CÁC THÁNG MÙA KHÔ TẠI MỸ THO VÀ TÂN CHÂU ---")
    dry_season = res_df[res_df["year_month"].str.endswith(("-12", "-01", "-02", "-03", "-04"))]
    print(f"{'Trạm':<10} | {'Tháng':<8} | {'EC Dự Báo (mS/m)':<18} | {'Lượng mưa (mm)':<15} | {'Nhiệt độ (°C)':<12}")
    print("-" * 75)
    for _, r in dry_season.head(16).iterrows():
        print(f"{r['station']:<10} | {r['year_month']:<8} | {r['predicted_ec_mS_m']:>12.2f} mS/m | {r['rainfall_mm']:>10.1f} mm  | {r['temperature_degC']:>8.1f} °C")
    print("=" * 75)

if __name__ == "__main__":
    run_future_forecast()
