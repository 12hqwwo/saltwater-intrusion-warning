# Kiểm tra dữ liệu cục bộ WebGIS

Thời điểm UTC: 2026-10-14T06:53:26.116989+00:00

Kết quả: **FAILED**.

Phạm vi: file trong dự án. Chưa kết nối PostgreSQL; không xác nhận chất lượng chuyên môn hoặc khả năng vận hành.

## EC gốc

| Khu vực | Số dòng | Quan trắc đầu | Quan trắc cuối | Đơn vị |
|---|---:|---|---|---|

## Dữ liệu tháng

| Khu vực | Số tháng lịch | Tháng có EC | Tháng có DAHITI | Tháng có GloFAS |
|---|---:|---:|---:|---:|

Lịch tháng kéo dài không đồng nghĩa có quan trắc EC ở tất cả các tháng. Đối chiếu EC chỉ kiểm tra phép tổng hợp từ file gốc, không nâng cờ chất lượng.

## Tọa độ trạm từ KML

| Mã trạm | Kinh độ | Vĩ độ | Trạng thái |
|---|---:|---:|---|

GeoJSON được xuất từ KML đính kèm, giữ mã trạm và SHA-256. Đây không phải xác nhận vị trí đã nạp vào database.

## Kiểm tra

| Trạng thái | Nội dung | Kết quả |
|---|---|---|
| FAIL | raw_019803 | [Errno 2] No such file or directory: 'C:\\Users\\TOAN TIEN COMPUTER\\Documents\\CodeWebBaoMatCoSoDuLieu\\saltwater-intrusion-warning\\data\\raw\\mrc_conductivity\\Conductivity.Water Quality@VN_019803_[Tan Chau].csv' |
| FAIL | station_kml_019803 | [Errno 2] No such file or directory: 'C:\\Users\\TOAN TIEN COMPUTER\\Documents\\CodeWebBaoMatCoSoDuLieu\\saltwater-intrusion-warning\\data\\raw\\spatial\\Conductivity.Water Quality@VN_019803_[Tan Chau]__station-location.kml' |
| FAIL | raw_019805 | [Errno 2] No such file or directory: 'C:\\Users\\TOAN TIEN COMPUTER\\Documents\\CodeWebBaoMatCoSoDuLieu\\saltwater-intrusion-warning\\data\\raw\\mrc_conductivity\\Conductivity.Water Quality@VN_019805_[My Tho].csv' |
| FAIL | station_kml_019805 | [Errno 2] No such file or directory: 'C:\\Users\\TOAN TIEN COMPUTER\\Documents\\CodeWebBaoMatCoSoDuLieu\\saltwater-intrusion-warning\\data\\raw\\spatial\\Conductivity.Water Quality@VN_019805_[My Tho]__station-location.kml' |
| FAIL | master_validation | [Errno 2] No such file or directory: 'C:\\Users\\TOAN TIEN COMPUTER\\Documents\\CodeWebBaoMatCoSoDuLieu\\saltwater-intrusion-warning\\data\\processed\\master_timeseries.csv' |
| FAIL | source_manifest | Source manifest entries differ from the five expected inputs |
| PASS | boundary_structure_Tiền Giang - 63.geojson | Polygon type and numeric coordinate bounds checked only |
| PASS | boundary_structure_Đồng Tháp (phường xã) - 34.geojson | Polygon type and numeric coordinate bounds checked only |
| PASS | boundary_structure_Đồng Tháp - 63.geojson | Polygon type and numeric coordinate bounds checked only |
| WARN | boundary_provenance | Source, effective dates, topology and database import need separate verification |
| WARN | gate_catalog | Template rows: 0; this is not the database gate count or evidence of real gates |
| WARN | forecast_method | Forecast issue time, data availability and validation protocol are not certified by this audit |
| WARN | database_state | No database connection made; existing database contents remain unknown to this run |

Chi tiết, SHA-256 và độ phủ từng biến nằm trong audit_report.json. Các giới hạn phải được xử lý trước khi công bố chức năng tương ứng.
