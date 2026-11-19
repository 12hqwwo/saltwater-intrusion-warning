# Kiểm tra triển khai PostgreSQL ngày 16/11/2026

> Đây là biên bản lịch sử trước khi TinBranch được tích hợp vào `refactor`. Ở mã sau tích hợp, giao diện lưu dự báo bằng phiên đăng nhập và vai người dùng; ô nhập API key dự báo mô tả bên dưới không còn. `run_deploy_tunnel.ps1` kiểm tra thêm khóa ký phiên và bảng tài khoản trước khi mở tunnel. Xem [bảo mật hiện hành](database-security.md).

Đích triển khai: origin `127.0.0.1:8000`, tên miền `https://webgis.huutin.xyz` qua Cloudflare Tunnel. Kiểm tra DB dùng `.venv/Scripts/python.exe` và cấu hình được nạp bằng `run_webgis.load_local_env()`. Báo cáo không chứa mật khẩu hoặc API key.

## 1. PostgreSQL thực tế

- DB `dongthap_gis` tại `127.0.0.1:5432`: PostgreSQL 17.11, PostGIS 3.6.2.
- `webgis_reader` và `webgis_writer` đều kết nối thành công bằng cấu hình hiện tại. Cả hai không có quyền superuser, tạo database hoặc tạo role.
- Chuỗi `30_dss_storage → 31_database_security → 32_dss_prediction_stations → 33_forecast_issue → 33b_forecast_issue_guard → 35_field_measurement` đã áp dụng đầy đủ. SHA-256 trong DB khớp byte của các file SQL hiện tại. Migration 31 được ghi ở `webgis_security.migrations`; các migration còn lại ở `dss_reference.schema_migrations`. Không cần chạy lại các migration này.
- Các bảng/view được tạo trong các file 01, 04, 10, 30, 31, 33 và 35 đều hiện diện. Migration 32/33b còn được xác minh qua kiểm tra ràng buộc và ghi thực tế bằng role writer.

| Trạm | Số dòng EC trong DB | Số dòng khai báo của snapshot | Khoảng thời gian |
| --- | ---: | ---: | --- |
| `MRC_VN_019803` — Tân Châu | 464 | 464 | 15/05/1985–15/12/2023 |
| `MRC_VN_019804` — Mỹ Thuận | 451 | 451 | 15/05/1985–15/12/2023 |
| `MRC_VN_019805` — Mỹ Tho | 463 | 463 | 26/06/1985–15/12/2023 |

Ba trạm đều là dữ liệu không demo; số thứ tự dòng nguồn không trùng và không có EC NULL. Kết quả xác nhận đủ dòng theo các snapshot đã nhập, không xác nhận có dữ liệu mới sau năm 2023 hoặc chuỗi tháng liên tục.

Các đối tượng trọng tâm đều có: `dss_reference.forecast_slot`, `dss_reference.forecast_issue`, `dss_reference.field_measurement`, `dss_reference.v_field_measurement_status`, `webgis_security.audit_log`. Bốn bảng/view đầu hiện có 0 dòng; audit có 2 dòng trước kiểm tra. Các phép ghi thử đều rollback.

Các phần schema/dữ liệu còn thiếu được ghi nhận, chưa tự áp dụng hoặc nhập bổ sung:

- `sql/20_alert_threshold_gate_rule_freshness.sql`: thiếu cả 5 bảng `public.alert_threshold_profile`, `public.gate_rule_profile`, `public.gate_rule_required_input`, `public.data_freshness_policy`, `public.system_capability_snapshot`.
- `sql/migrations/11_schema_migration.sql`: thiếu 6 bảng pipeline `public.data_quality_flag`, `public.tide_point`, `public.hydro_point`, `public.tide_prediction`, `public.discharge_observation`, `public.gate_coordinate_source`.
- `public.irrigation_gate` và `public.admin_boundary` tồn tại nhưng đang trống. `public.monthly_feature` có 1.000 dòng; `webgis_research.ec_observation` có 977 dòng.

## 2. X-API-Key

`requestJSON()` trong `frontend/src/api.js` hỗ trợ header tùy chỉnh, nhưng không tự lấy key từ `.env`, config hay storage. `field-measurements.js` có ô nhập mật khẩu riêng cho gửi và duyệt, rồi truyền `headers: { 'X-API-Key': ... }`; key chỉ nằm trong các ô nhập của trang hiện tại.

Sau khi người dùng chọn ô nhập mật khẩu, đã thêm trường “API key lưu dự báo” cạnh phần chạy dự báo. `prediction-history.js` quản lý một ô nhập duy nhất, dùng chung với nhánh “Lưu lượt chạy vào PostgreSQL” trong `multivariate-forecast.js`. Cả hai luồng lưu gửi key qua header `X-API-Key`. Thiếu key được báo trước khi gửi yêu cầu; key sai hiển thị lỗi từ API và cho phép nhập lại. Chạy không lưu không cần key.

Key chỉ nằm trong ô nhập của trang hiện tại, không lưu vào localStorage/sessionStorage, URL, payload dự báo, bảng so sánh hoặc file xuất. Ô nhập có `type=password`, tắt autocomplete, spellcheck và autocapitalize. Đọc lịch sử và chạy không lưu không gửi key. Trang mới bắt đầu với ô key rỗng; không nhúng key từ `.env` vào frontend build.

Đã thêm hai alias `/api/v1/research/gate-drafts` và `/api/v1/research/multivariate/history` vào `backend/security.py::WRITE_PATHS`, đồng thời mở rộng test bảo mật. Kiểm tra xác nhận thiếu/sai key bị từ chối; key đúng đi tiếp đến bước validation payload. Các đường dẫn kết thúc bằng `/` cũng bị kiểm tra key.

## 3. Cấu hình .env

Đã ghi chính xác:

```dotenv
WEBGIS_RESEARCH_MODE=postgres
WEBGIS_SECURITY_ENABLED=true
WEBGIS_DSS_WRITES_ENABLED=true
WEBGIS_ALLOWED_HOSTS=webgis.huutin.xyz,localhost,127.0.0.1,[::1],testserver
WEBGIS_CORS_ORIGINS=https://webgis.huutin.xyz,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173
```

Hai biến `WEBGIS_WRITE_API_KEY` và `WEBGIS_REVIEW_API_KEY` trước đó đều chưa có giá trị. Đã sinh hai chuỗi khác nhau bằng `secrets.token_urlsafe(48)` và chỉ ghi vào `.env`. Mật khẩu DB hiện có được giữ nguyên và đã được so sánh trước/sau trong bộ nhớ. Quyền truy cập `.env` được bảo vệ bằng hàm có sẵn của dự án; `.env` vẫn bị Git ignore.

## 4. Build và kiểm tra

- `npm.cmd run build` trong `frontend/`: đã chạy lại thành công sau khi bổ sung ô key, cập nhật `frontend/dist`. Vite có cảnh báo chunk JS 546,19 kB vượt 500 kB; không phải lỗi build. Thư mục dist bị Git ignore.
- Python: 55 test đạt trong các module `test_security`, `test_run_webgis_args`, `test_dss_postgres_contract`, `test_dss_storage_errors`, `test_database_pool`, `test_sql_migrations`, `test_forecast_issue`, `test_field_measurement`, `test_workspace_api`. Lượt đầu có 2 test contract bị skip vì chưa đặt DSN; sau đó cả 2 đã được chạy đạt trên các bảng `pg_temp`, với rollback, không sửa bảng ứng dụng.
- JavaScript: 34 test đạt từ `tests/frontend_api.test.mjs`, `tests/forecast_flows.test.mjs`, `tests/field_measurements.test.mjs`, `tests/forecast_issue_panel.test.mjs`, `frontend/src/features/gate-simulation-draft.test.js`. Bốn ca bổ sung kiểm tra thiếu key, dùng chung key giữa hai luồng lưu, chạy không lưu và xử lý key sai/nhập lại; kiểm tra key không đi vào yêu cầu đọc, URL, payload hoặc CSV.
- Sau thay đổi frontend, chạy lại `test_security.py`: cả 7 test đạt. `git diff --check` không có lỗi khoảng trắng.
- Script DB thật đều đạt: `verify_database_security.py`, `verify_dss_station_migration.py`, `verify_forecast_runtime.py`, `verify_field_runtime.py`. Các INSERT kiểm tra đều rollback; PostgreSQL sequence có thể tăng dù rollback.
- FastAPI với cấu hình mới và DB thật: health, summary, stations, lịch sử, forecast issues và phiếu đã duyệt trả 200; CORS preflight từ tên miền public trả 200; origin lạ trả 403, host lạ trả 400.
- Origin HTTP thực tế: chạy server tạm bằng `run_webgis.py --mode postgres --host 127.0.0.1 --port 8000`, kiểm tra `/`, `/workspace.html`, `/api/v1/health` và Host `webgis.huutin.xyz` đều trả 200. Health xác nhận DB `dongthap_gis` và transaction chỉ đọc. Server tạm đã dừng sau kiểm tra.
- Chưa kiểm chứng kết nối công khai qua Cloudflare Tunnel. Cần chạy origin bằng lệnh trên khi vận hành. Server đang chạy từ trước cần khởi động lại để nạp `.env` và mã middleware mới.

Khi sử dụng: nhập giá trị `WEBGIS_WRITE_API_KEY` từ `.env` vào ô “API key lưu dự báo”. Cần nhập lại khi tải lại trang.
