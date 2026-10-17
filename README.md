# WebGIS xâm nhập mặn Đồng Tháp - data pipeline

## Mốc Pilot Gò Công đã đóng gói

Mốc **“Pilot Gò Công – Kiểm chứng topology và kết nối trạm”** được đóng gói tại
[`deliverables/pilot_go_cong_topology_freeze_v1`](deliverables/pilot_go_cong_topology_freeze_v1/README.md).
Mốc này giữ GeoJSON/CSV để demo độc lập, gồm QA topology bốn nhóm, ma trận khoảng
cách 5 trạm, chỉ số articulation/bridge, workbook tổng hợp, ảnh 300 dpi, metadata
và checksum. Gò Công là khu vực thí điểm phương pháp, không đại diện toàn bộ vùng nghiên cứu.

Pipeline chính đi theo luồng `RAW immutable -> STAGING -> QA/PROCESSED -> FEATURES -> MODELS`. Dữ liệu synthetic và pipeline cũ không được dùng để tuyên bố kết quả khoa học.

## Cấu trúc

```text
data/
├── raw/
│   ├── ec/mrc/
│   ├── glofas/tanchau/
│   ├── dahiti/
│   ├── tide/
│   │   ├── fes2022b/
│   │   └── uhslc/
│   ├── meteorology/openmeteo/
│   └── gis/
│       ├── gates/
│       └── spatial/
├── staging/
├── processed/
│   ├── ec/
│   ├── glofas/
│   ├── gis/
│   └── tide/
├── features/
└── models/

data/external/
├── sources/
│   ├── sondoc/
│   └── tanchau_discharge/
└── download_runs/

pipelines/
├── etl/12_etl_update.py
├── features/13_feature_pipeline.py
├── models/
│   ├── 14_model_baseline.py
│   ├── run_forecast_multivariate.py
│   └── run_sondoc_forecast.py
├── advisory/
│   ├── run_gate_advisor.py
│   └── run_station_gate_link.py
└── legacy/
    ├── run_forecast.py
    └── data_processing/

scripts/utilities/extract_fes2022b.py

sql/migrations/11_schema_migration.sql
docs/reports/01_data_audit.md
docs/reports/16_IMPLEMENTATION_REPORT.md
```

## Chạy lại pipeline

```powershell
python pipelines/etl/12_etl_update.py
python pipelines/features/13_feature_pipeline.py
python pipelines/models/14_model_baseline.py
```

Các script phải được chạy theo thứ tự trên. `monthly_feature_v2` chỉ lấy EC `VERIFIED` làm target. Mỹ Tho GloFAS vẫn NULL; Tide FES vẫn NULL cho đến khi điểm offshore, datum và chuỗi dự báo được xác minh.

Các file trong `data/external/sources/` là bản nguồn chuẩn dùng chung. Mỗi thư mục trong `data/external/download_runs/` chỉ lưu bằng chứng riêng của một lần tải; manifest trỏ về nguồn chuẩn để tránh nhân bản dữ liệu.

## Trạng thái 16 đầu ra

| # | file | vị trí | trạng thái |
|---:|---|---|---|
| 01 | `01_data_audit.md` | `docs/reports/` | hoàn thành |
| 02 | `02_ec_qa_report.csv` | `data/processed/ec/` | hoàn thành |
| 03 | `03_ec_clean.csv` | `data/processed/ec/` | hoàn thành |
| 04 | `04_tide_points.geojson` | `data/processed/tide/` | chưa tạo; thiếu điểm offshore đã xác minh |
| 05 | `05_tide_hourly.csv` | `data/processed/tide/` | chưa tạo; thiếu FES2022b/PyFES input |
| 06 | `06_tide_monthly.csv` | `data/processed/tide/` | chưa tạo; phụ thuộc 05 |
| 07 | `07_glofas_mytho_daily.csv` | `data/processed/glofas/` | hoàn thành với NULL/MISSING có lý do |
| 08 | `08_glofas_mytho_monthly.csv` | `data/processed/glofas/` | hoàn thành với NULL/MISSING có lý do |
| 09 | `09_gate_coordinate_qa.csv` | `data/processed/gis/` | hoàn thành |
| 10 | `10_monthly_feature_v2.csv` | `data/features/` | hoàn thành |
| 11 | `11_schema_migration.sql` | `sql/migrations/` | đã soạn; chưa áp dụng DB |
| 12 | `12_etl_update.py` | `pipelines/etl/` | hoàn thành |
| 13 | `13_feature_pipeline.py` | `pipelines/features/` | hoàn thành |
| 14 | `14_model_baseline.py` | `pipelines/models/` | hoàn thành |
| 15 | `15_model_comparison.csv` | `data/models/` | hoàn thành |
| 16 | `16_IMPLEMENTATION_REPORT.md` | `docs/reports/` | hoàn thành |

Chi tiết lỗi, QA, schema và các phần còn NULL nằm trong hai báo cáo ở `docs/reports/`.
