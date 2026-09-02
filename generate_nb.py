import json

cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Project: Dự Báo Xâm Nhập Mặn - Frequency: Monthly\n",
            "Đồ án tốt nghiệp: **XÂY DỰNG NỀN TẢNG WEBGIS DỰ BÁO XÂM NHẬP MẶN VÀ ĐIỀU PHỐI VẬN HÀNH CỐNG THỦY LỢI TẠI ĐỒNG BẰNG SÔNG CỬU LONG**\n\n",
            "File này dùng để: **Bước 1:** Tiền xử lý dữ liệu và **Bước 2 (đầu):** Feature Engineering."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import pandas as pd\n",
            "import numpy as np\n",
            "import xarray as xr\n",
            "import glob\n",
            "from pathlib import Path\n",
            "import warnings\n",
            "warnings.filterwarnings('ignore')\n",
            "\n",
            "DATA_DIR = Path(r'd:/Study/TLCN/data')"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 1. Xử lý Dữ liệu Độ mặn (Mỹ Tho)\n",
            "- Đọc dữ liệu `conductivity_MyTho_monthly_clean.csv`\n",
            "- Chuyển đổi EC sang Độ mặn: `salinity_ppt = EC * 0.64`"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "ec_files = glob.glob(str(DATA_DIR / 'interim' / 'conductivity_MyTho_monthly_clean.csv'))\n",
            "df_ec = pd.read_csv(ec_files[0])\n",
            "# Chuyển date về 1 ngày đầu tháng để đồng bộ với GloFAS\n",
            "df_ec['date'] = pd.to_datetime(df_ec['date']).dt.to_period('M').dt.to_timestamp()\n",
            "df_ec['salinity_ppt'] = df_ec['conductivity_mS_per_m'] * 0.64\n",
            "\n",
            "df_mytho = df_ec[['date', 'conductivity_mS_per_m', 'salinity_ppt']].rename(columns={\n",
            "    'conductivity_mS_per_m': 'MyTho_EC',\n",
            "    'salinity_ppt': 'MyTho_Salinity'\n",
            "})\n",
            "df_mytho.head()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 2. Xử lý Dữ liệu GloFAS (Tân Châu)\n",
            "GloFAS là dữ liệu theo ngày, ta tính trung bình để chuyển về định dạng **Tháng (Monthly)**."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "dfs = []\n",
            "nc_files = glob.glob(str(DATA_DIR / 'raw' / 'waterlevel' / 'glofas_tanchau' / 'glofas_*.nc'))\n",
            "for f in nc_files:\n",
            "    try:\n",
            "        ds = xr.open_dataset(f)\n",
            "        var_name = [v for v in ds.data_vars if v != 'crs'][0]\n",
            "        dims = [d for d in ds.dims if d in ('lat', 'lon', 'latitude', 'longitude')]\n",
            "        df_nc = ds[var_name].mean(dim=dims).to_dataframe().reset_index()\n",
            "        \n",
            "        # Trích xuất cột date\n",
            "        if 'time' in df_nc.columns: df_nc = df_nc.rename(columns={'time': 'date'})\n",
            "        elif 'valid_time' in df_nc.columns: df_nc = df_nc.rename(columns={'valid_time': 'date'})\n",
            "        \n",
            "        df_nc = df_nc.rename(columns={var_name: 'TanChau_Discharge'})\n",
            "        # Đưa về ngày đầu tháng để groupby cho chính xác\n",
            "        df_nc['date'] = pd.to_datetime(df_nc['date']).dt.to_period('M').dt.to_timestamp()\n",
            "        df_month = df_nc.groupby('date')['TanChau_Discharge'].mean().reset_index()\n",
            "        dfs.append(df_month)\n",
            "    except Exception as e:\n",
            "        pass # Bỏ qua lỗi\n",
            "\n",
            "df_tanchau = pd.concat(dfs).groupby('date').mean().reset_index()\n",
            "print(\"Tổng số tháng được lấy từ GloFAS:\", len(df_tanchau))\n",
            "df_tanchau.head()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 3. Ghép Dữ liệu (Date Join)\n",
            "Ghép ngang theo `date` để xây dựng tập dữ liệu đồng nhất."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "master_df = pd.merge(df_tanchau, df_mytho, on='date', how='outer')\n",
            "master_df = master_df.sort_values('date').reset_index(drop=True)\n",
            "master_df.head()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 4. Phân tích đặc trưng (Feature Engineering)\n",
            "- **Độ trễ thời gian (Time-lag):** Nước từ Tân Châu đổ về Mỹ Tho mất nhiều tuần, nên lưu lượng Tân Châu của 1 hoặc 2 tháng trước (`Lag 1`, `Lag 2`) có ảnh hưởng mạnh tới độ mặn Mỹ Tho của tháng này.\n",
            "- **Yếu tố tự quy (Salinity Autoregression):** Bản thân độ mặn tháng trước (`Lag 1`) sẽ quyết định trực tiếp tới mặn tháng kế.\n",
            "- **Mùa vụ (Seasonality):** Rút trích tháng trong năm `Month` (1-12) làm biến nhận diện mùa mưa/mùa khô."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Lag Features: Lưu lượng Tân Châu (1 tháng trước và 2 tháng trước)\n",
            "master_df['TanChau_Discharge_lag_1'] = master_df['TanChau_Discharge'].shift(1)\n",
            "master_df['TanChau_Discharge_lag_2'] = master_df['TanChau_Discharge'].shift(2)\n",
            "\n",
            "# Lag Features: Độ mặn 1 tháng trước\n",
            "master_df['MyTho_Salinity_lag_1'] = master_df['MyTho_Salinity'].shift(1)\n",
            "\n",
            "# Đặc trưng Mùa vụ (Tháng trong năm)\n",
            "master_df['Month'] = master_df['date'].dt.month\n",
            "\n",
            "# Loại bỏ các tháng bị NaN do quá trình Shift Lag sinh ra hoặc lệch timeline\n",
            "ml_df = master_df.dropna().reset_index(drop=True)\n",
            "\n",
            "print('Dataset Shape sau Feature Engineering:', ml_df.shape)\n",
            "ml_df.head(10)"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 5. Xuất File CSV Hoàn thiện\n",
            "Tập dữ liệu này sẵn sàng để phân chia Train/Test cho các thuật toán ARIMA, Random Forest hoặc LSTM."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "PROCESSED_DIR = DATA_DIR / 'processed'\n",
            "PROCESSED_DIR.mkdir(parents=True, exist_ok=True)\n",
            "ml_df.to_csv(PROCESSED_DIR / 'ml_monthly_features.csv', index=False)\n",
            "print('Đã lưu dữ liệu: ml_monthly_features.csv')"
        ]
    }
]

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

with open(r'd:/Study/TLCN/ML_Pipeline.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, ensure_ascii=False, indent=2)
