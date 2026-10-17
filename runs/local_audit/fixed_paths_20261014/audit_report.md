# Kiểm tra dữ liệu cục bộ WebGIS

Thời điểm UTC: 2026-10-14T12:11:22.063782+00:00

Kết quả: **FAILED**.

Phạm vi: file trong dự án. Chưa kết nối PostgreSQL; không xác nhận chất lượng chuyên môn hoặc khả năng vận hành.

## EC gốc

| Khu vực | Số dòng | Quan trắc đầu | Quan trắc cuối | Đơn vị |
|---|---:|---|---|---|
| TANCHAU | 464 | 1985-05-15T00:00:00+07:00 | 2023-12-15T00:00:00+07:00 | mS/m |
| MYTHO | 463 | 1985-06-26T00:00:00+07:00 | 2023-12-15T00:00:00+07:00 | mS/m |

## Dữ liệu tháng

| Khu vực | Số tháng lịch | Tháng có EC | Tháng có DAHITI | Tháng có GloFAS |
|---|---:|---:|---:|---:|

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
| WARN | archived_master | Auditing archived master explicitly; not an active training input |
| FAIL | master_validation | HEADER_MISMATCH: expected ['station', 'month_start', 'conductivity_mS_per_m', 'precipitation_sum', 'temperature_mean', 'temperature_max', 'temperature_min', 'evapotranspiration_sum', 'windspeed_mean', 'humidity_mean', 'shortwave_rad_sum', 'water_level_m', 'glofas_discharge_m3s']; got ['station', 'month_start', 'conductivity_mS_per_m', 'precipitation_sum', 'temperature_mean', 'temperature_max', 'temperature_min', 'evapotranspiration_sum', 'windspeed_mean', 'humidity_mean', 'shortwave_rad_sum', 'water_level_m', 'glofas_discharge_m3s', 'tide_max_m'] |
| FAIL | source_manifest | Source manifest mismatch: master_timeseries.csv |
| PASS | boundary_structure_Tiền Giang - 63.geojson | Polygon type and numeric coordinate bounds checked only |
| PASS | boundary_structure_Đồng Tháp (phường xã) - 34.geojson | Polygon type and numeric coordinate bounds checked only |
| PASS | boundary_structure_Đồng Tháp - 63.geojson | Polygon type and numeric coordinate bounds checked only |
| WARN | boundary_provenance | Source, effective dates, topology and database import need separate verification |
| WARN | gate_catalog | Template rows: 0; this is not the database gate count or evidence of real gates |
| WARN | forecast_method | Forecast issue time, data availability and validation protocol are not certified by this audit |
| WARN | database_state | No database connection made; existing database contents remain unknown to this run |

Chi tiết, SHA-256 và độ phủ từng biến nằm trong audit_report.json. Các giới hạn phải được xử lý trước khi công bố chức năng tương ứng.
