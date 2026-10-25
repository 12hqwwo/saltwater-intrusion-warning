# Lưu trữ bổ trợ DSS

Kho mới dùng schema `dss_reference`, độc lập với dữ liệu quan trắc `public` và snapshot nghiên cứu. Không ghi lại EC, không huấn luyện mô hình và không thay đổi bảng hiện có. Kết quả suy luận và nháp được thêm thành phiên bản mới; API không có sửa/xóa lịch sử.

## Cài đặt có chủ đích

Migration `sql/30_dss_storage.sql` tạo danh mục ngưỡng kịch bản, lịch sử dự báo và nháp cống. Chạy từ thư mục gốc bằng môi trường API/model đã có psycopg:

```powershell
.\.venv\Scripts\python.exe scripts/apply_dss_storage.py
.\.venv\Scripts\python.exe scripts/apply_dss_storage.py --apply
```

Lệnh đầu chỉ in kế hoạch, không kết nối DB. Lệnh `--apply` đọc `.env` qua `load_local_env`, dùng cấu hình PG*, thực hiện trong một transaction và khóa migration. Checksum được ghi vào `dss_reference.schema_migrations`. Chạy lại cùng checksum không thay đổi gì; checksum khác hoặc bảng có sẵn chưa được đăng ký sẽ gây lỗi và rollback, không ghi đè. Không chạy riêng SQL để bỏ qua cơ chế theo dõi này.

Sau khi cài thành công, bật `WEBGIS_DSS_WRITES_ENABLED=true` trong `.env` rồi khởi động lại server. Mặc định thao tác ghi bị tắt. Kết nối đọc vẫn dùng `read_connection()` với transaction chỉ đọc. Kết nối ghi bắt buộc có `DSS_PGUSER` riêng; không fallback sang `PGUSER`. Chạy `scripts/setup_security.py --apply` để tạo hai role và bật ghi an toàn. Cấu hình mật khẩu/SSL theo libpq PG* hoặc passfile, không ghi mật khẩu vào SQL.

Tài khoản đọc cần `USAGE` schema và `SELECT` ba bảng DSS. Tài khoản ghi cần thêm `INSERT` bảng lịch sử/nháp, `SELECT` cột trả về và `USAGE` sequence draft_id; không cần quyền sửa/xóa bảng hoặc ghi bảng quan trắc. Migration dùng tài khoản quản trị do người triển khai chọn, không tự cấp quyền rộng.

## Hợp đồng API

Tất cả đường dẫn dưới `/api/v1/workspace`:

- `GET /threshold-presets`: `{items, source, is_operational_rule:false}`. Các trường: `preset_code`, `usage_purpose`, `threshold_ms_m`, `ec_basis`, hai cận lấy/ngừng nước có thể null, `source_note`, `evidence_status`. Ba ví dụ 50/100/150 mS/m chỉ là giá trị minh họa người dùng cung cấp, cơ sở EC `UNKNOWN`; không gán FAO/cây trồng/quy chuẩn/phân vị. Cặp cận lấy/ngừng minh họa tương ứng 50/80, 100/150, 120/200 mS/m, chỉ áp dụng vào kịch bản mô phỏng chưa xác minh; không phải cận vận hành đã phê duyệt.
- `POST /multivariate/history`: nhận cùng body với `/multivariate/predict`: `station`, `target_month`, `input_mode` là `ARCHIVE` hoặc `MANUAL`, ba biến khí tượng khi MANUAL. Server chạy lại pipeline đã lưu rồi lưu chính kết quả server; không nhận kết quả hay số làm tròn do client gửi. ARCHIVE luôn lấy khí tượng nguồn server. Trả `{prediction, saved_at}` với toàn bộ payload gốc, mã dự báo mới, số đầu vào đầy đủ độ chính xác, provenance, model version và metrics. Đây là một lượt suy luận mới, không giữ UUID của lượt chưa lưu trước đó.
- `GET /multivariate/history`: lọc tùy chọn `station`, `target_month`; `limit=20` (1–100), `offset=0` (0–1000000). Trả `{items:[{prediction,saved_at}],total,limit,offset}`, thứ tự `saved_at DESC, prediction_id DESC`. Count và page cùng snapshot transaction.
- `GET /multivariate/history/{prediction_id}`: trả một wrapper đã lưu; UUID không có trả 404.
- `POST /gate-drafts`: `{gate_code,input,policy}`; mỗi object giữ schema_version 1 và cùng gate_code. Cho phép hồ sơ chưa đủ số đo/ngưỡng, nhưng không cho số vô hạn, sai kiểu số, mã cống lẫn nhau hay timestamp không timezone. Tối đa body 256 KiB. Trả trực tiếp `{draft_id,gate_code,input,policy,created_at,status:'DRAFT_UNVERIFIED',declarations_verified_by_server:false}`. Full JSON giữ cả metadata tham khảo, không biến nó thành quan trắc được xác minh.
- `GET /gate-drafts?gate_code=...`: cùng limit/offset, trả `{items,total,limit,offset}`; mới nhất trước theo created_at rồi draft_id.

JSONB giữ số gốc không dùng NUMERIC(10,3) để làm tròn; các cột riêng chỉ phục vụ lọc/định danh. Dữ liệu EC và mức độ sẵn sàng vẫn thuộc phạm vi thực nghiệm. Bản nháp và trường khai báo không chứng minh pháp lý, liên kết thủy lực hay quyền vận hành.

## Trạng thái lỗi và phạm vi triển khai

Các lỗi DSS trả 503 có mã trong thông điệp: `DSS_WRITES_DISABLED`, `DSS_SCHEMA_MISSING`, `DSS_PERMISSION_DENIED`, `DSS_DATABASE_UNAVAILABLE`. UI có thể tiếp tục dự báo không lưu và giữ bản nháp trình duyệt; không âm thầm lưu sang nguồn khác. Request không hợp lệ trả 422; nháp quá lớn trả 413. API ghi yêu cầu JSON và kiểm tra Origin trình duyệt.

Ứng dụng phục vụ local, dùng hai role PostgreSQL reader/writer và audit INSERT, không có màn hình đăng nhập. Kho DSS là lịch sử chung; API key ghi là tùy chọn. Xem [bảo mật DB](database-security.md) để thiết lập và hiểu giới hạn khi triển khai qua mạng.
