# Migration 35 — phiếu EC thực địa

Ngày 14/11/2026, áp dụng `sql/35_field_measurement.sql` lên `dongthap_gis`, SHA-256 `af1a39731c1a5c97dbcf45e2eb0cb621534522f04e7a92f8f7f3ea2224885eef`.

Giao thức [nhãn EC tháng](field_ec_label_protocol_2026-11-14.md) được lập trước khi nhận phiếu đầu tiên. `scripts/verify_field_migration.py` kiểm `PENDING → APPROVED → REJECTED` trong transaction rollback. `scripts/verify_field_runtime.py` kiểm INSERT bằng role `webgis_writer`, sau đó rollback và xác nhận `webgis_reader` không thấy dữ liệu thử. `scripts/verify_field_api.py` kiểm hai API key khác nhau với các lệnh ghi được mock; không lưu phiếu thử.

Hai key nội bộ đã sinh trong `.env` được bảo vệ, không in ra log hay tài liệu. Giao diện chỉ giữ key trong ô nhập của phiên hiện tại; không lưu localStorage. Server cần khởi động lại để nạp key. Chưa có phiếu thực địa thật, chưa có nhãn đủ điều kiện để chấm sai số vận hành.
