import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.metrics import root_mean_squared_error, mean_absolute_error
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.statespace.sarimax import SARIMAX
import json

DATA_DIR = Path("data")
PROCESSED_DIR = DATA_DIR / "processed"
MASTER_CSV = PROCESSED_DIR / "master_timeseries.csv"
OUT_DIR = Path("runs/forecast_exp")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def create_continuous_calendar(df_station):
    # Đảm bảo index là datetime và có lịch tháng liên tục
    df_station['month_start'] = pd.to_datetime(df_station['month_start'])
    df_station.set_index('month_start', inplace=True)
    df_station = df_station.sort_index()
    
    # Tạo dải tháng liên tục từ min đến max
    full_range = pd.date_range(start=df_station.index.min(), end=df_station.index.max(), freq='MS')
    df_continuous = df_station.reindex(full_range)
    df_continuous.index.name = 'month_start'
    return df_continuous

def main():
    if not MASTER_CSV.exists():
        print(f"File not found: {MASTER_CSV}")
        return

    df = pd.read_csv(MASTER_CSV)
    
    # Chỉ tập trung vào Mỹ Tho
    df_mytho = df[df['station'] == 'MYTHO'].copy()
    if df_mytho.empty:
        # Trong data có thể station viết là MyTho
        df_mytho = df[df['station'] == 'MyTho'].copy()
        
    if df_mytho.empty:
        print("Không tìm thấy dữ liệu trạm Mỹ Tho.")
        return

    df_continuous = create_continuous_calendar(df_mytho)
    
    # Xây dựng thí nghiệm dự báo EC (horizon_months = 1)
    # Target là conductivity_mS_per_m (tại target_month)
    # forecast_origin = target_month - 1 month
    # Các biến lag phải được tính trước.
    
    target_col = 'conductivity_mS_per_m'
    if target_col not in df_continuous.columns:
        # Check original column
        if 'conductivity_ms_per_m' in df_continuous.columns:
             target_col = 'conductivity_ms_per_m'
    
    # Tính lags
    df_continuous['target'] = df_continuous[target_col]
    
    # Trim to last valid target so test set has ground truth
    valid_indices = df_continuous['target'].dropna().index
    if not valid_indices.empty:
        last_valid = valid_indices.max()
        df_continuous = df_continuous.loc[:last_valid].copy()
        
    df_continuous['lag_1'] = df_continuous['target'].shift(1)  # Giá trị tháng trước (Persistence)
    df_continuous['lag_12'] = df_continuous['target'].shift(12) # Giá trị cùng tháng năm trước (Seasonal Naive)
    df_continuous['month_num'] = df_continuous.index.month
    
    # Đánh dấu forecast_origin và target_month
    df_continuous['target_month'] = df_continuous.index
    df_continuous['forecast_origin'] = df_continuous.index - pd.DateOffset(months=1)
    
    # Split train/val/test theo thời gian
    # Lưu mốc chia cụ thể: giả sử test là 24 tháng cuối
    total_months = len(df_continuous)
    test_size = 24
    val_size = 12
    
    if total_months < test_size + val_size + 12:
        print("Dữ liệu quá ngắn để chia train/val/test.")
        # fallback
        test_size = int(total_months * 0.2)
        val_size = int(total_months * 0.1)
        
    train_end = total_months - test_size - val_size
    val_end = total_months - test_size
    
    train_df = df_continuous.iloc[:train_end].copy()
    val_df = df_continuous.iloc[train_end:val_end].copy()
    test_df = df_continuous.iloc[val_end:].copy()
    
    # Ghi nhận split manifest
    split_manifest = pd.DataFrame([
        {'split': 'train', 'start': train_df.index.min(), 'end': train_df.index.max(), 'size': len(train_df)},
        {'split': 'val', 'start': val_df.index.min(), 'end': val_df.index.max(), 'size': len(val_df)},
        {'split': 'test', 'start': test_df.index.min(), 'end': test_df.index.max(), 'size': len(test_df)}
    ])
    split_manifest.to_csv(OUT_DIR / "split_manifest.csv", index=False)
    
    predictions = []
    
    # Lặp qua tập test để đánh giá
    # Chỉ đánh giá trên các target_month có actual
    test_eval_df = test_df.dropna(subset=['target'])
    
    # Train Random Forest trên tập Train+Val (hoặc chỉ Train nếu tuning)
    # RF dùng lag_1, lag_2, month_num (biến đã biết tại forecast_origin)
    train_rf = pd.concat([train_df, val_df])
    train_rf['lag_2'] = train_rf['target'].shift(2)
    features_rf = ['lag_1', 'lag_2', 'month_num']
    train_rf_clean = train_rf.dropna(subset=['target'] + features_rf)
    
    rf = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
    if not train_rf_clean.empty:
        rf.fit(train_rf_clean[features_rf], train_rf_clean['target'])
    else:
        print("Không đủ dữ liệu sạch để train RF.")
        
    # ARIMA fit trên toàn chuỗi (thực tế nên fit roll, nhưng baseline giữ gọn)
    # Bỏ qua ARIMA nếu dữ liệu hổng nhiều
    
    for _, row in test_df.iterrows():
        target_month = row['target_month']
        forecast_origin = row['forecast_origin']
        actual = row['target']
        snapshot = 'master_latest' # Giả định snapshot
        station = 'Mỹ Tho'
        
        # 1. Persistence
        pred_persistence = row['lag_1']
        status = 'SUCCESS' if pd.notnull(pred_persistence) else 'SKIP_NULL_LAG1'
        predictions.append({
            'station': station, 'snapshot': snapshot, 'model': 'Persistence',
            'forecast_origin': forecast_origin, 'target_month': target_month, 'horizon': 1,
            'actual': actual, 'predicted': pred_persistence, 'status': status
        })
        
        # 2. Seasonal Naive
        pred_snaive = row['lag_12']
        status = 'SUCCESS' if pd.notnull(pred_snaive) else 'SKIP_NULL_LAG12'
        predictions.append({
            'station': station, 'snapshot': snapshot, 'model': 'Seasonal Naive',
            'forecast_origin': forecast_origin, 'target_month': target_month, 'horizon': 1,
            'actual': actual, 'predicted': pred_snaive, 'status': status
        })
        
        # 3. Random Forest
        # Cần features tại forecast origin
        lag_1 = row['lag_1']
        # Tính lag 2 (là giá trị tháng t-2)
        # Vì test_df có thể bị cắt mất history, ta lấy từ continuous
        loc_idx = df_continuous.index.get_loc(target_month)
        lag_2 = df_continuous.iloc[loc_idx - 2]['target'] if loc_idx >= 2 else np.nan
        
        if pd.notnull(lag_1) and pd.notnull(lag_2):
            pred_rf = rf.predict([[lag_1, lag_2, row['month_num']]])[0]
            status = 'SUCCESS'
        else:
            pred_rf = np.nan
            status = 'SKIP_MISSING_FEATURES'
            
        predictions.append({
            'station': station, 'snapshot': snapshot, 'model': 'Random Forest',
            'forecast_origin': forecast_origin, 'target_month': target_month, 'horizon': 1,
            'actual': actual, 'predicted': pred_rf, 'status': status
        })
        
    # Chuyển thành DataFrame
    df_preds = pd.DataFrame(predictions)
    df_preds.to_csv(OUT_DIR / "predictions.csv", index=False)
    
    # Tính metrics (chỉ trên những mẫu có actual và dự báo SUCCESS)
    metrics_list = []
    models = df_preds['model'].unique()
    
    for m in models:
        df_m = df_preds[(df_preds['model'] == m) & (df_preds['status'] == 'SUCCESS') & (df_preds['actual'].notnull())]
        if not df_m.empty:
            mae = mean_absolute_error(df_m['actual'], df_m['predicted'])
            rmse = root_mean_squared_error(df_m['actual'], df_m['predicted'])
            metrics_list.append({
                'model': m, 'mae_mS_m': mae, 'rmse_mS_m': rmse, 'eval_samples': len(df_m)
            })
            
    df_metrics = pd.DataFrame(metrics_list)
    df_metrics.to_csv(OUT_DIR / "metrics.csv", index=False)
    print("Metrics:")
    print(df_metrics)
    
    # Vẽ biểu đồ 1 model so sánh với actual
    plt.figure(figsize=(12, 6))
    df_plot = df_preds[(df_preds['model'] == 'Persistence') & df_preds['actual'].notnull()].set_index('target_month')
    plt.plot(df_plot.index, df_plot['actual'], label='Actual (Mỹ Tho)', marker='o')
    plt.plot(df_plot.index, df_plot['predicted'], label='Persistence Forecast', marker='x')
    
    df_rf = df_preds[(df_preds['model'] == 'Random Forest') & (df_preds['status'] == 'SUCCESS')].set_index('target_month')
    if not df_rf.empty:
        plt.plot(df_rf.index, df_rf['predicted'], label='Random Forest Forecast', marker='s', alpha=0.7)
        
    plt.title("Dự báo EC (mS/m) - Horizon = 1 tháng")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "forecast_chart.png")

if __name__ == "__main__":
    main()
