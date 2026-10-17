# Kiểm tra dữ liệu cục bộ WebGIS

Thời điểm UTC: 2026-10-03T05:03:11.983287+00:00

Kết quả: **PASS_WITH_LIMITATIONS**.

Phạm vi: file trong dự án. Chưa kết nối PostgreSQL; không xác nhận chất lượng chuyên môn hoặc khả năng vận hành.

## EC gốc

| Khu vực | Số dòng | Quan trắc đầu | Quan trắc cuối | Đơn vị |
|---|---:|---|---|---|
| TANCHAU | 464 | 1985-05-15T00:00:00+07:00 | 2023-12-15T00:00:00+07:00 | mS/m |
| MYTHO | 463 | 1985-06-26T00:00:00+07:00 | 2023-12-15T00:00:00+07:00 | mS/m |

## Dữ liệu tháng

| Khu vực | Số tháng lịch | Tháng có EC | Tháng có DAHITI | Tháng có GloFAS |
|---|---:|---:|---:|---:|
| MYTHO | 500 | 463 | 217 | 0 |
| TANCHAU | 500 | 464 | 108 | 469 |

Lịch tháng kéo dài không đồng nghĩa có quan trắc EC ở tất cả các tháng. Đối chiếu EC chỉ kiểm tra phép tổng hợp từ file gốc, không nâng cờ chất lượng.

## Tọa độ trạm từ KML

| Mã trạm | Kinh độ | Vĩ độ | Trạng thái |
|---|---:|---:|---|
| MRC_VN_019803 | 105.2480164 | 10.80062008 | REPORTED |
| MRC_VN_019805 | 106.3529997 | 10.35912163 | REPORTED |

GeoJSON được xuất từ KML đính kèm, giữ mã trạm và SHA-256. Đây không phải xác nhận vị trí đã nạp vào database.

## Kiểm tra

| Trạng thái | Nội dung | Kết quả |
|---|---|---|
| PASS | raw_019803 | 464 rows passed existing ETL validation |
| PASS | station_kml_019803 | Named point parsed; duplicate KML copies match; REPORTED |
| PASS | raw_019805 | 463 rows passed existing ETL validation |
| PASS | station_kml_019805 | Named point parsed; duplicate KML copies match; REPORTED |
| PASS | calendar_MYTHO | 500/500 calendar months present |
| PASS | calendar_TANCHAU | 500/500 calendar months present |
| PASS | master_validation | 1000 rows passed existing ETL validation |
| PASS | raw_master_ec | 0 month/value/missingness differences |
| PASS | source_manifest | All five original input hashes and sizes match |
| PASS | boundary_structure_Tiền Giang - 63.geojson | Polygon type and numeric coordinate bounds checked only |
| PASS | boundary_structure_Đồng Tháp (phường xã) - 34.geojson | Polygon type and numeric coordinate bounds checked only |
| PASS | boundary_structure_Đồng Tháp - 63.geojson | Polygon type and numeric coordinate bounds checked only |
| WARN | boundary_provenance | Source, effective dates, topology and database import need separate verification |
| WARN | gate_catalog | Template rows: 0; this is not the database gate count or evidence of real gates |
| PASS | exported_metrics | Recalculated from saved predictions; model fitting not rerun |
| PASS | forecast_cohort | 24 target months shared by all models |
| WARN | forecast_method | Forecast issue time, data availability and validation protocol are not certified by this audit |
| WARN | database_state | No database connection made; existing database contents remain unknown to this run |

## Tính lại kết quả dự báo đã lưu

| Mô hình | Số tháng chấm | MAE (mS/m) | RMSE (mS/m) |
|---|---:|---:|---:|
| Persistence | 24 | 9.154583333333333 | 15.559446889269553 |
| Random Forest | 24 | 18.944994953168138 | 31.129004527608814 |
| Seasonal Naive | 24 | 20.149583333333336 | 47.842282162330015 |

Chỉ tính lại sai số từ predictions.csv; chưa huấn luyện lại hoặc xác minh thời điểm phát hành dự báo.

Chi tiết, SHA-256 và độ phủ từng biến nằm trong audit_report.json. Các giới hạn phải được xử lý trước khi công bố chức năng tương ứng.
