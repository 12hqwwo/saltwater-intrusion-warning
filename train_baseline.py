import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import root_mean_squared_error, mean_absolute_error
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Paths
DATA_DIR = Path("data")
PROCESSED_DIR = DATA_DIR / "processed"
MASTER_CSV = PROCESSED_DIR / "master_timeseries.csv"

def prepare_data(df, target_col='conductivity_mS_per_m', lag_months=1):
    # Lấy dữ liệu Mỹ Tho
    df_mytho = df[df['station'] == 'MyTho'][['month_start', target_col]].dropna()
    df_tanchau = df[df['station'] == 'TanChau'][['month_start', 'glofas_discharge_m3s']].dropna()
    
    # Merge
    merged = pd.merge(df_mytho, df_tanchau, on='month_start', how='inner').sort_values('month_start')
    merged.set_index('month_start', inplace=True)
    
    # Tạo lag features
    merged[f'discharge_lag_{lag_months}'] = merged['glofas_discharge_m3s'].shift(lag_months)
    merged['salinity_lag_1'] = merged[target_col].shift(1)
    
    merged.dropna(inplace=True)
    return merged

def naive_forecast(series):
    # Dự báo tháng này = thực tế tháng trước
    return series.shift(1).dropna()

def main():
    if not MASTER_CSV.exists():
        print(f"Error: Cannot find {MASTER_CSV}")
        return

    df = pd.read_csv(MASTER_CSV)
    df['month_start'] = pd.to_datetime(df['month_start'])

    # Giả định độ trễ lý tưởng là 2 tháng (dựa theo kết quả cross-correlation)
    # Có thể điều chỉnh lại sau khi chạy cross_correlation.py
    best_lag = 2
    data = prepare_data(df, lag_months=best_lag)
    
    if data.empty:
        print("Không đủ dữ liệu để train.")
        return

    # Train/Test Split (80/20)
    train_size = int(len(data) * 0.8)
    train, test = data.iloc[:train_size], data.iloc[train_size:]
    
    print(f"Train size: {len(train)} months, Test size: {len(test)} months")

    # --- 1. Naive Baseline ---
    # Naive model trên tập test
    y_true = test['conductivity_mS_per_m']
    y_pred_naive = data['conductivity_mS_per_m'].shift(1).loc[test.index]
    
    rmse_naive = root_mean_squared_error(y_true, y_pred_naive)
    print(f"[Baseline Naive] RMSE: {rmse_naive:.4f}")

    # --- 2. Random Forest ---
    features = [f'discharge_lag_{best_lag}', 'salinity_lag_1']
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(train[features], train['conductivity_mS_per_m'])
    
    y_pred_rf = rf.predict(test[features])
    rmse_rf = root_mean_squared_error(y_true, y_pred_rf)
    print(f"[Random Forest] RMSE: {rmse_rf:.4f}")

    # --- 3. SARIMA ---
    # Exogenous variable là discharge
    exog_train = train[[f'discharge_lag_{best_lag}']]
    exog_test = test[[f'discharge_lag_{best_lag}']]
    
    try:
        # Order cơ bản (1,0,0) - (0,1,1,12) cho chuỗi tháng
        sarima = SARIMAX(train['conductivity_mS_per_m'], exog=exog_train, order=(1, 0, 0), seasonal_order=(0, 1, 1, 12))
        res = sarima.fit(disp=False)
        y_pred_sarima = res.predict(start=test.index[0], end=test.index[-1], exog=exog_test)
        rmse_sarima = root_mean_squared_error(y_true, y_pred_sarima)
        print(f"[SARIMAX] RMSE: {rmse_sarima:.4f}")
    except Exception as e:
        print(f"Lỗi khi train SARIMA: {e}")

if __name__ == '__main__':
    main()
