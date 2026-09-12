import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Paths
DATA_DIR = Path("data")
PROCESSED_DIR = DATA_DIR / "processed"
MASTER_CSV = PROCESSED_DIR / "master_timeseries.csv"
OUT_PLOT = PROCESSED_DIR / "cross_correlation_plot.png"

def main():
    if not MASTER_CSV.exists():
        print(f"Error: Cannot find {MASTER_CSV}")
        return

    print("Loading data...")
    df = pd.read_csv(MASTER_CSV)
    df['month_start'] = pd.to_datetime(df['month_start'])

    # Tách dữ liệu Tân Châu (Lưu lượng - Thượng nguồn) và Mỹ Tho (Độ mặn - Hạ lưu)
    # Giả định dữ liệu độ mặn có cột 'conductivity_mS_per_m'
    df_tanchau = df[df['station'] == 'TanChau'][['month_start', 'glofas_discharge_m3s']].dropna()
    df_mytho = df[df['station'] == 'MyTho'][['month_start', 'conductivity_mS_per_m']].dropna()

    if df_tanchau.empty or df_mytho.empty:
        print("Không đủ dữ liệu để tính Cross-Correlation.")
        return

    # Merge lại theo thời gian
    merged = pd.merge(df_mytho, df_tanchau, on='month_start', how='inner').sort_values('month_start')

    salinity = merged['conductivity_mS_per_m']
    discharge = merged['glofas_discharge_m3s']

    print(f"Dữ liệu hợp lệ từ {merged['month_start'].min().date()} đến {merged['month_start'].max().date()} ({len(merged)} tháng)")

    # Tính cross-correlation theo các độ trễ (lag) từ 0 đến 6 tháng
    # Ý nghĩa lag = k: Tương quan giữa Độ mặn ở tháng t và Lưu lượng ở tháng (t - k)
    lags = range(0, 7)
    corrs = []

    for lag in lags:
        if lag == 0:
            corr = salinity.corr(discharge)
        else:
            # Shift lưu lượng k tháng về phía trước (tức là lưu lượng của k tháng trước ứng với độ mặn hiện tại)
            corr = salinity.corr(discharge.shift(lag))
        corrs.append(corr)

    # Hiển thị
    for lag, corr in zip(lags, corrs):
        print(f"Lag {lag} month(s): Correlation = {corr:.4f}")

    best_lag = lags[np.nanargmin(corrs)]  # Tìm lag có tương quan âm mạnh nhất (lưu lượng cao -> độ mặn thấp)
    print(f"-> Độ trễ tốt nhất (tương quan âm lớn nhất) là: {best_lag} tháng")

    # Vẽ biểu đồ
    plt.figure(figsize=(10, 6))
    sns.barplot(x=list(lags), y=corrs, color='skyblue', edgecolor='black')
    plt.axhline(0, color='black', linewidth=1)
    plt.title("Cross-Correlation giữa Lưu lượng (Tân Châu) và Độ mặn (Mỹ Tho)", fontsize=14)
    plt.xlabel("Độ trễ (Tháng) - Lưu lượng đi trước Độ mặn", fontsize=12)
    plt.ylabel("Hệ số Tương quan Pearson", fontsize=12)
    
    # Highlight best lag
    best_idx = lags.index(best_lag)
    plt.bar(best_idx, corrs[best_idx], color='salmon', edgecolor='black')
    
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(OUT_PLOT, dpi=300)
    print(f"Đã lưu biểu đồ tại: {OUT_PLOT}")

if __name__ == '__main__':
    main()
