# Migration 33 — sổ phát hành dự báo

Ngày 14/11/2026, áp dụng trên `dongthap_gis`:

- `33_forecast_issue`: SHA-256 `02cf796124f12fb26a2f96e41d0993b32b97308d6f5e93b391746f1f6eb2c3f3`.
- `33b_forecast_issue_guard`: SHA-256 `44a1346688f715941f7e6b19b94643244657d7df5a52909c8bb8be7a62a2d088`. Migration bổ sung bỏ `FOR SHARE` trong trigger đọc slot bất biến, để role ghi không cần quyền `UPDATE`.

Kiểm `scripts/verify_forecast_runtime.py` bằng `webgis_writer`: INSERT slot, `MISSED`, issue `LATE` và score thử trong một transaction; DB ghi `detected_at`/`issued_at` thật và ép trạng thái `LATE`. Transaction rollback, kiểm bằng `webgis_reader` xác nhận không còn dòng thử. `scripts/score_forecast_issues.py` ở chế độ xem trước báo chưa có slot và chưa có nhãn để chấm. Không có bản phát hành vận hành nào được tạo trong bước triển khai.

Sổ mở ngày 14/11/2026. Lịch đầu tiên được phép là `MONTHLY_D06_PREV` lúc 09:00 ngày 06/12/2026 cho tháng 01/2027; lịch trước đó không được phát hành hồi tố. Cửa sổ `ON_TIME` dài một giờ kể từ 09:00; mọi issue sau đó là `LATE`. Nếu lệnh không chạy, `scripts/issue_monthly_forecast.py --audit-due` ghi `MISSED/JOB_NOT_RUN` tại thời điểm kiểm tra thật. Script này cần được gọi theo lịch vận hành; chưa có lịch tự động trên máy chủ.
