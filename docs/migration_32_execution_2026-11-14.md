# Migration 32: lưu dự báo Mỹ Thuận

Ngày 14/11/2026, trên DB `dongthap_gis`, trước migration có 15 bản `MyTho`, 3 bản `TanChau`, 0 bản `MyThuan`. Hai CHECK cũ chỉ nhận `MyTho` và `TanChau`.

Đã áp dụng `sql/32_dss_prediction_stations.sql` bằng `scripts/apply_dss_migration.py --file sql/32_dss_prediction_stations.sql --version 32_dss_prediction_stations --apply`. SHA-256 SQL: `62412f2b5ec1f3ce63d6b03e24c7ef9797ff044b4e49a1a491171222f4380a09`. Lần chạy thứ hai xác nhận migration đã áp dụng với cùng checksum và không thực hiện thay đổi.

`scripts/verify_dss_station_migration.py` đã INSERT và SELECT dự báo cho cả ba trạm trong transaction rồi ROLLBACK; cặp `MyThuan` + site Tân Châu bị CHECK từ chối. Không có bản test nào được giữ lại. Test phân loại lỗi xác nhận `23505` → HTTP 409, `23514`/`23503` → HTTP 422.

Rollback: `scripts/rollback_dss_prediction_stations.py` mặc định chỉ in kế hoạch. `--apply` chỉ hợp lệ khi chưa có bản `MyThuan`; script ngược từ chối nếu đã có, không xóa dữ liệu. Khi đã có dự báo Mỹ Thuận, quay lui mã ứng dụng bằng cách giữ schema mới tương thích thay vì thu hẹp CHECK.
