# Bảo mật PostgreSQL và lưu lịch sử

Ứng dụng dùng hai role kết nối PostgreSQL và tài khoản web riêng cho cán bộ. Quyền DB và quyền người dùng web được kiểm tra ở hai tầng.

| Role | Quyền |
| --- | --- |
| `webgis_reader` | SELECT quan trắc và dữ liệu DSS; transaction API chỉ đọc |
| `webgis_writer` | INSERT và SELECT để trả kết quả trên hai bảng lịch sử dự báo, nháp cống; USAGE sequence nháp |
| Tài khoản quản trị PG* | Chỉ dành cho thiết lập, nhập dữ liệu và bảo trì bằng script |

Hai role ứng dụng không có quyền superuser, tạo DB/role, sở hữu bảng, sửa/xóa/truncate quan trắc hoặc lịch sử, hay sửa audit. API từ chối kết nối bằng role quản trị hoặc role có quyền sở hữu. Mọi tham số dữ liệu được bind vào SQL. Lần đọc có timeout, transaction riêng và snapshot nhất quán.

## Thiết lập và chạy trong terminal Antigravity

Máy hiện tại đã được áp dụng. Máy khác cần PostgreSQL có schema/dữ liệu dự án và `.env` cấu hình PG* quản trị hợp lệ. Chạy ở thư mục gốc:

```powershell
.\.venv\Scripts\python.exe scripts/apply_dss_storage.py --apply
.\.venv\Scripts\python.exe -m tools.security_setup roles --apply
.\.venv\Scripts\python.exe -m tools.security_setup auth-secret --apply
.\.venv\Scripts\python.exe scripts/apply_dss_migration.py --file sql/36_app_user.sql --version 36_app_user --apply
.\.venv\Scripts\python.exe scripts/apply_dss_migration.py --file sql/37_app_registration.sql --version 37_app_registration --apply
.\.venv\Scripts\python.exe scripts/create_app_user.py --username canbo --display-name "Cán bộ đo" --role FIELD_STAFF --apply
.\.venv\Scripts\python.exe scripts/create_app_user.py --username kiemtra --display-name "Cán bộ kiểm tra" --role INSPECTOR --apply
.\start.ps1
```

Setup tạo mật khẩu ngẫu nhiên riêng cho hai role, cập nhật `.env`, bật `WEBGIS_DSS_WRITES_ENABLED=true` và chọn PostgreSQL. `.env` và `.security/` bị loại khỏi Git; Windows ACL giới hạn các tệp này cho tài khoản Windows hiện tại và SYSTEM. Bản `.env` cũ được giữ riêng trong `.security/env.before-hardening`. Không gửi các tệp này trong báo cáo hoặc gói bàn giao công khai. Setup thu hồi quyền CREATE schema public, TEMP của PUBLIC và quyền ghi bảng public/DSS từ PUBLIC trong DB dự án; tài khoản khác dùng chung DB cần được cấp quyền riêng nếu có.

`start.ps1` mặc định dùng PostgreSQL; `-Mode snapshot` chọn bản tệp để xem demo. Lịch sử DSS vẫn dùng PostgreSQL ngay cả khi xem snapshot. Không tự chuyển sang tệp khi DB lỗi. Dừng server cũ bằng Ctrl+C rồi chạy lại để nạp quyền và cấu hình mới.

Trong Dự báo EC đa biến, khách chỉ chạy thử; cán bộ đã đăng nhập mới được lưu lịch sử PostgreSQL. Hai vai `FIELD_STAFF` và `INSPECTOR` được lưu dự báo và nháp cống. Chỉ `INSPECTOR` được phát hành dự báo và duyệt phiếu EC. Các bản ghi không sửa số đo EC gốc và không trở thành lệnh vận hành cống.

## Audit và kiểm tra quyền

Trigger `webgis_security.audit_log` ghi thời gian, role PostgreSQL, nguồn ứng dụng, bảng và mã bản ghi khi thêm dự báo/nháp. Với thao tác có đăng nhập, nguồn ứng dụng là `USER:<username>`. Hai role ứng dụng không được sửa/xóa audit; quản trị PostgreSQL vẫn có quyền bảo trì.

```powershell
.\.venv\Scripts\python.exe scripts/verify_database_security.py
```

Lệnh dùng mật khẩu từ môi trường, thử các thao tác bị cấm và rollback các INSERT kiểm tra; không giữ bản ghi thử. Sequence có thể tăng dù rollback. Kết quả không chứa bí mật được ghi vào `docs/database-security-verification.json`. Chạy lại setup cùng migration được hỗ trợ; checksum khác bị từ chối.

Có thể kiểm tra lịch sử bằng tài khoản đọc trong pgAdmin:

```sql
SELECT prediction_id, station_key, target_month, saved_at
FROM dss_reference.multivariate_prediction_log ORDER BY saved_at DESC LIMIT 20;
SELECT draft_id, gate_code, created_at
FROM dss_reference.gate_simulation_drafts ORDER BY created_at DESC LIMIT 20;
SELECT * FROM webgis_security.audit_log ORDER BY audit_id DESC LIMIT 20;
```

## Đăng nhập và phạm vi

Tài khoản web nằm trong `webgis_security.app_user`; mật khẩu được băm bằng scrypt với salt riêng. Đăng ký công khai tạo `FIELD_STAFF` chưa kích hoạt; chỉ `INSPECTOR` được xem hàng chờ và kích hoạt, với người duyệt và thời điểm được lưu trong bảng. API cấp JWT HS256 sống 8 giờ, ký bằng `WEBGIS_AUTH_SECRET` trong `.env`. Trình duyệt giữ token trong `sessionStorage`, xác nhận lại qua `/api/v1/auth/me` khi tải trang và xóa khi đăng xuất. Các POST ghi kiểm vai ở router; khách không thể ghi bằng cách gọi API trực tiếp. Khách không truy cập API dự báo EC đa biến. Khách vẫn được chạy kiểm tra cống với ngưỡng mặc định nhưng chỉ nhận kết luận rút gọn. `webgis_reader` không được đọc bảng mật khẩu. Chế độ snapshot không có đăng nhập và đăng ký.

Khi `WEBGIS_WRITE_API_KEY` được cấu hình, middleware kiểm tra `X-API-Key` ở các POST ghi dữ liệu nếu yêu cầu chưa có phiên Bearer hợp lệ. API key là lớp kiểm tra bổ sung cho client ngoài trình duyệt, không cấp vai người dùng và không thay thế quyền `FIELD_STAFF`/`INSPECTOR` tại router. Giao diện web dùng phiên đăng nhập để lưu dự báo, không yêu cầu nhập API key. Các alias của đường ghi chịu cùng quy tắc. Kiểm tra cùng nguồn, CORS và Host vẫn áp dụng.

Server chạy ở `127.0.0.1`; phân quyền DB bảo vệ dữ liệu khỏi các thao tác mà ứng dụng không được phép thực hiện, không giới hạn ai được truy cập web local. Triển khai qua mạng cần xác thực ở reverse proxy, HTTPS, firewall và chính sách sao lưu riêng. PostgreSQL ở máy khác cần TLS với `PGSSLMODE=verify-full` và chứng chỉ tin cậy; thiết lập này không tự thay pg_hba.conf, firewall hoặc mã hóa ổ đĩa/backup. Máy hiện tại chưa được cấu hình các phần triển khai từ xa đó.
