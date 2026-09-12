import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

def main():
    # Setup
    sns.set_theme(style='whitegrid')
    MASTER_CSV = Path(r'd:/Study/TLCN/data/processed/master_timeseries.csv')
    OUT_DIR = Path(r'd:/Study/TLCN/data/processed/plots')
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(MASTER_CSV)
    df['month_start'] = pd.to_datetime(df['month_start'])

    df_tanchau = df[df['station'] == 'TanChau'].set_index('month_start')
    df_mytho = df[df['station'] == 'MyTho'].set_index('month_start')
    df_vungtau = df[df['station'] == 'VungTau'].set_index('month_start')

    # Merge
    df_merged = pd.merge(
        df_mytho[['conductivity_mS_per_m', 'temperature_mean', 'evapotranspiration_sum', 'precipitation_sum']],
        df_tanchau[['glofas_discharge_m3s']], 
        left_index=True, right_index=True, how='inner'
    )
    df_merged = pd.merge(
        df_merged,
        df_vungtau[['tide_max_m']],
        left_index=True, right_index=True, how='inner'
    )
    
    df_merged['salinity_ppt'] = df_merged['conductivity_mS_per_m'] * 0.64
    df_merged['month'] = df_merged.index.month

    # 1. Line plot 
    fig, ax1 = plt.subplots(figsize=(14, 6))
    color = 'tab:blue'
    ax1.set_xlabel('Thời Gian (Năm)', fontsize=12)
    ax1.set_ylabel('Lưu lượng Tân Châu (m³/s)', color=color, fontsize=12, fontweight='bold')
    ax1.plot(df_merged.index, df_merged['glofas_discharge_m3s'], color=color, linewidth=1.5, alpha=0.8)
    ax1.tick_params(axis='y', labelcolor=color)
    
    ax2 = ax1.twinx()  
    color = 'tab:red'
    ax2.set_ylabel('Độ mặn Mỹ Tho (ppt)', color=color, fontsize=12, fontweight='bold')  
    ax2.plot(df_merged.index, df_merged['salinity_ppt'], color=color, linewidth=1.5, linestyle='--', alpha=0.8)
    ax2.tick_params(axis='y', labelcolor=color)
    
    plt.title('Đối chiếu Biến động Lưu lượng Tân Châu và Độ mặn Mỹ Tho (1985-2023)', fontsize=15, fontweight='bold')
    fig.tight_layout()
    plt.savefig(OUT_DIR / 'line_plot.png', dpi=300)
    plt.close()

    # 2. Boxplot
    plt.figure(figsize=(12, 6))
    sns.boxplot(x='month', y='salinity_ppt', data=df_merged, palette='coolwarm')
    plt.title('Phân bố Độ mặn Mỹ Tho theo tháng (Chu kỳ Mùa vụ)', fontsize=15, fontweight='bold')
    plt.xlabel('Tháng trong năm', fontsize=12)
    plt.ylabel('Độ mặn (ppt)', fontsize=12)
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'boxplot.png', dpi=300)
    plt.close()

    # 3. Heatmap
    corr_cols = ['precipitation_sum', 'glofas_discharge_m3s', 'tide_max_m', 'temperature_mean', 'evapotranspiration_sum', 'salinity_ppt']
    corr_matrix = df_merged[corr_cols].corr()
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, cmap='RdBu', vmin=-1, vmax=1, fmt=".2f", linewidths=.5)
    plt.title('Ma trận Tương quan (Pearson) giữa các Đặc trưng', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'heatmap.png', dpi=300)
    plt.close()

    # 4. Scatter
    plt.figure(figsize=(9, 6))
    sns.scatterplot(x='glofas_discharge_m3s', y='salinity_ppt', hue='month', palette='viridis', data=df_merged, s=60, alpha=0.7)
    plt.axvline(x=10000, color='red', linestyle='--', linewidth=1.5, label='Ngưỡng lưu lượng cạn (10.000 m³/s)')
    plt.title('Scatter Plot: Tương quan Lưu lượng Thượng nguồn và Nồng độ Mặn', fontsize=15, fontweight='bold')
    plt.xlabel('Lưu lượng Tân Châu (m³/s)', fontsize=12)
    plt.ylabel('Độ mặn Mỹ Tho (ppt)', fontsize=12)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'scatter.png', dpi=300)
    plt.close()
    
    print("Đã tạo và lưu thành công 4 biểu đồ vào data/processed/plots/")

if __name__ == '__main__':
    main()
