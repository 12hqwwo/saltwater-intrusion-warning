# Bảo mật PostgreSQL và lưu lịch sử

Ứng dụng dùng hai role kết nối PostgreSQL, không cần đăng nhập trên giao diện. Đây là phân quyền ở tầng DB, không phải hai tài khoản người dùng web.

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
.\.venv\Scripts\python.exe scripts/setup_security.py --apply
.\start.ps1
```

Setup tạo mật khẩu ngẫu nhiên riêng cho hai role, cập nhật `.env`, bật `WEBGIS_DSS_WRITES_ENABLED=true` và chọn PostgreSQL. `.env` và `.security/` bị loại khỏi Git; Windows ACL giới hạn các tệp này cho tài khoản Windows hiện tại và SYSTEM. Bản `.env` cũ được giữ riêng trong `.security/env.before-hardening`. Không gửi các tệp này trong báo cáo hoặc gói bàn giao công khai. Setup thu hồi quyền CREATE schema public, TEMP của PUBLIC và quyền ghi bảng public/DSS từ PUBLIC trong DB dự án; tài khoản khác dùng chung DB cần được cấp quyền riêng nếu có.

`start.ps1` mặc định dùng PostgreSQL; `-Mode snapshot` chọn bản tệp để xem demo. Lịch sử DSS vẫn dùng PostgreSQL ngay cả khi xem snapshot. Không tự chuyển sang tệp khi DB lỗi. Dừng server cũ bằng Ctrl+C rồi chạy lại để nạp quyền và cấu hình mới.

Trong Dự báo EC đa biến, tùy chọn **Lưu lượt chạy vào PostgreSQL** bật sẵn: mỗi lần bấm chạy tạo một dự báo và lưu chính kết quả đó, gồm đầu vào, phiên bản mô hình và thời điểm. Bỏ chọn nếu chỉ muốn xem thử; lỗi lưu được báo rõ, không báo thành công giả. Xem lại bằng **Lịch sử PostgreSQL**. Trong hồ sơ cống, dùng **Lưu nháp vào PostgreSQL** và khôi phục nháp mới nhất. Các bản ghi này không sửa số đo EC gốc và không trở thành lệnh vận hành cống.

## Audit và kiểm tra quyền

Trigger `webgis_security.audit_log` ghi thời gian, role PostgreSQL, nguồn ứng dụng, bảng và mã bản ghi khi thêm dự báo/nháp. Mặc định nguồn là `LOCAL_APPLICATION`; nếu dùng API key là `API_KEY_CLIENT`. Đây không phải danh tính cá nhân. Hai role ứng dụng không được sửa/xóa audit; quản trị PostgreSQL vẫn có quyền bảo trì.

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

## API key tùy chọn và phạm vi

Mặc định web local không yêu cầu API key. Đặt `WEBGIS_WRITE_API_KEY` trong `.env` nếu muốn yêu cầu header `X-API-Key` trên hai POST lưu lịch sử/nháp; đọc dữ liệu và chạy dự báo không lưu vẫn được phép. Không đưa key vào frontend hoặc URL. Giao diện mặc định không gửi key; khi bật cấu hình này, dùng API client có header hoặc bổ sung proxy xác thực phù hợp. CORS, Origin và Host được kiểm tra nhưng không thay thế xác thực người dùng.

Server chạy ở `127.0.0.1`; phân quyền DB bảo vệ dữ liệu khỏi các thao tác mà ứng dụng không được phép thực hiện, không giới hạn ai được truy cập web local. Triển khai qua mạng cần xác thực ở reverse proxy, HTTPS, firewall và chính sách sao lưu riêng. PostgreSQL ở máy khác cần TLS với `PGSSLMODE=verify-full` và chứng chỉ tin cậy; thiết lập này không tự thay pg_hba.conf, firewall hoặc mã hóa ổ đĩa/backup. Máy hiện tại chưa được cấu hình các phần triển khai từ xa đó.
