## 2.A. Backend lõi: khởi động, API, kết nối dữ liệu

Phần này giải thích các tệp trong `backend/` (trừ `backend/domain/` và `backend/services/`, được mô tả ở phần khác). Trước khi đọc, cần nắm vài từ dùng nhiều lần:

- **Backend**: chương trình chạy ở máy chủ, nhận yêu cầu từ trang web và trả dữ liệu. Ở dự án này backend viết bằng Python với thư viện **FastAPI**.
- **API**: "quầy giao dịch" của backend. Trang web gửi một yêu cầu tới một địa chỉ (ví dụ `/api/v1/stations`), backend trả lại dữ liệu.
- **Endpoint (điểm cuối)**: một địa chỉ cụ thể của API, kèm một **phương thức HTTP**: `GET` là "xin xem", `POST` là "gửi lên để xử lý hoặc lưu".
- **JSON**: dạng văn bản có cấu trúc (giống phiếu điền sẵn các ô `"tên": giá trị`) mà backend và trang web dùng để trao đổi.
- **Router (bộ định tuyến)**: một nhóm endpoint gom chung, giống một "tổ" trong cơ quan. `main.py` gắn các tổ này vào ứng dụng, có thể thêm **tiền tố** (prefix) như `/api/v1` vào trước mọi địa chỉ của tổ.
- **Repository (kho truy xuất)**: lớp mã chỉ lo việc đọc/ghi dữ liệu (cơ sở dữ liệu hoặc tệp), không quyết định nghiệp vụ.
- **Service (dịch vụ)**: lớp ở giữa, nhận yêu cầu từ API, gọi repository, xử lý rồi trả kết quả. Mô tả ở phần khác.
- **PostgreSQL / PostGIS**: hệ quản trị cơ sở dữ liệu (DB) và phần mở rộng để lưu tọa độ bản đồ. **Bảng** trong DB giống một sheet Excel; **schema** trong DB là một "ngăn tủ" chứa nhiều bảng (`public`, `dss_reference`...).
- **SQL**: ngôn ngữ để hỏi DB ("lấy các dòng trạm không phải dữ liệu mẫu").

Đường đi chung của một yêu cầu: trang web → `main.py` (cổng vào, kiểm tra an ninh) → tệp trong `backend/api/` (nhận và kiểm tra phiếu yêu cầu) → `backend/services/` (xử lý) → `backend/repositories/` hoặc `backend/database.py` (lấy dữ liệu) → trả JSON ngược lại.

---

### `backend/__init__.py`
- **Vai trò trong đời sống:** Tấm biển "đây là thư mục mã Python của backend". Python cần tệp này để coi `backend` là một gói (package) và cho phép viết `from backend.xxx import ...`. Trong tệp chỉ có một dòng mô tả, không có mã chạy.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: không. Đầu ra: không.
- **Các hàm cốt lõi:** Không có hàm.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Không — nếu muốn thêm API hay sửa logic, hãy sang `backend/main.py` hoặc thư mục `backend/api/`.
  - Không — tệp này gần như không bao giờ cần sửa.

### `backend/main.py`
- **Vai trò trong đời sống:** Cổng chính và ông bảo vệ của cả backend. Khi máy chủ khởi động, tệp này dựng ứng dụng FastAPI, mở sẵn đường kết nối DB, gắn tất cả các "tổ" API vào đúng địa chỉ, cài các lớp kiểm tra an ninh và quy định cách báo lỗi. Ngoài ra nó tự chứa vài endpoint đọc trạm/EC trực tiếp từ PostgreSQL.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: biến môi trường (thiết lập lấy từ `.env`, ví dụ `WEBGIS_RESEARCH_MODE`, `WEBGIS_CORS_ORIGINS`, `WEBGIS_ALLOWED_HOSTS`, `WEBGIS_DSS_WRITES_ENABLED`, `DSS_PGUSER`); yêu cầu HTTP từ trình duyệt; DB PostgreSQL qua `backend/database.py` (bảng `public.measurement_site`, `public.data_source`, `public.source_dataset`, `public.conductivity_observation`). Đầu ra: JSON trả về trang web; không ghi DB.
- **Các hàm cốt lõi:**
  - `lifespan(app)`: việc làm lúc "mở cửa" và "đóng cửa" máy chủ. Lúc mở: gọi `warmup_models()` trong `backend/domain/multivariate_ec.py` để nạp sẵn mô hình dự báo (nạp lỗi chỉ ghi cảnh báo, không dừng máy chủ); nếu chế độ là `postgres` thì gọi `open_read_pool()` (mở **pool kết nối**, tức một nhóm đường dây DB mở sẵn để dùng lại, khỏi quay số mỗi lần); nếu cho phép ghi DSS và có `DSS_PGUSER` thì gọi `open_write_pool()` trong `backend/repositories/dss_storage.py`. Lúc đóng: đóng cả hai pool.
  - `app = FastAPI(...)` và các dòng `app.add_middleware(...)`: tạo ứng dụng và cài **middleware** (lớp lọc mà mọi yêu cầu phải đi qua trước khi tới endpoint, như cửa soát vé). Gồm `CORSMiddleware` (chỉ cho các trang web ở địa chỉ được phép gọi API, chỉ cho `GET`/`POST`), `SecurityMiddleware` (từ `backend/security.py`) và `TrustedHostMiddleware` (chỉ nhận yêu cầu gửi tới tên máy hợp lệ như `localhost`, `127.0.0.1`).
  - Các dòng `app.include_router(...)`: bảng phân địa chỉ. `workspace_router` gắn ở `/api/v1/workspace`; `multivariate_router`, `multivariate_history_router`, `data_freshness_router`, `gate_screening_router`, `forecast_issues_router`, `field_measurements_router` gắn ở `/api/v1`; `intake_router` gắn hai lần ở `/api/v1/workspace` và `/api/v1/research`; `research_router` tự có tiền tố `/api/v1/research`.
  - `workspace_error`, `site_not_found`, `dataset_not_found`, `database_error`: các "bộ phiên dịch lỗi". Khi lỗi xảy ra, chúng đổi thành JSON dễ hiểu: không có trạm → 404 `SITE_NOT_FOUND`; không có bộ dữ liệu → 404 `DATASET_NOT_FOUND`; lỗi DB → 503 với mã `DB_SCHEMA_MISMATCH` / `DB_PERMISSION_DENIED` / `DATABASE_ERROR`, cố ý không lộ câu SQL hay mật khẩu.
  - `app_health()`: `GET /api/v1/app-health`. Trả `status: ok` và chế độ nguồn đang chạy; không chạm DB.
  - `get_repository()`: tạo đối tượng `Repository` (trong `backend/database.py`) cho mỗi yêu cầu. Đây là một **dependency** (thứ FastAPI tự chuẩn bị và đưa vào hàm, giống người phụ việc đưa sẵn dụng cụ).
  - `health(repo)`: `GET /api/v1/health`. Gọi `Repository.health()` để thử kết nối thật và xác nhận giao dịch chỉ đọc.
  - `stations(repo)`: `GET /api/v1/stations`. Gọi `Repository.stations()`, đóng gói thành GeoJSON (dạng JSON chuẩn cho điểm bản đồ, tọa độ [kinh độ, vĩ độ]).
  - `datasets(site_code, repo)`: `GET /api/v1/stations/{site_code}/datasets`. Gọi `Repository.datasets()`, liệt kê các bộ dữ liệu EC (snapshot đã nhập) của một trạm.
  - `observations(site_code, repo, dataset_code, date_from, date_to, quality_flag, observed_or_estimated, limit, offset)`: `GET /api/v1/stations/{site_code}/observations`. Bắt buộc chọn `dataset_code`; lọc theo ngày, cờ chất lượng, đo/ước tính; chia trang (`limit` tối đa 1000). Từ chối 422 nếu `date_from > date_to`. Gọi `Repository.history()`, trả `ECHistory` có `has_more` cho biết còn trang sau.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm một nhóm API mới vào ứng dụng (phải `include_router` ở đây) hoặc đổi tiền tố địa chỉ.
  - Có — nếu muốn đổi danh sách trang được gọi API (CORS) hoặc cách báo lỗi DB.
  - Không — nếu muốn sửa câu SQL đọc trạm/EC thì sang `backend/database.py`; sửa API dự báo thì sang `backend/api/multivariate.py`.

### `backend/database.py`
- **Vai trò trong đời sống:** Thủ kho chỉ-được-xem của DB. Tệp này giữ "chùm chìa khóa" (pool kết nối chỉ đọc) và các câu SQL cố định để lấy trạm và lịch sử EC. Mọi kết nối đều bị khóa ở chế độ chỉ đọc, nên dù có lỗi mã cũng không ghi đè dữ liệu gốc.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: biến môi trường `PGHOST`, `PGPORT`, `PGDATABASE` (mặc định `dongthap_gis`), `WEBGIS_DB_USER` (mặc định `webgis_reader`), `WEBGIS_DB_PASSWORD`, `WEBGIS_DB_POOL_MAX`; các bảng `public.measurement_site`, `public.data_source`, `public.source_dataset`, `public.conductivity_observation`. Đầu ra: danh sách dòng dạng từ điển (dict) cho `main.py` và các repository; không ghi gì.
- **Các hàm cốt lõi:**
  - `SiteNotFound`, `DatasetNotFound`: hai loại lỗi riêng, nghĩa là "không có trạm thật mang mã này" và "bộ dữ liệu không có EC của trạm này".
  - `_read_config()`: gom thông số kết nối từ biến môi trường.
  - `_configure_reader(conn)`: mỗi khi mở đường dây mới thì đặt chế độ chỉ đọc, mức cô lập `REPEATABLE READ` (đếm số dòng và lấy trang cùng nhìn một "ảnh chụp" DB), rồi gọi `assert_application_role()` trong `backend/db_security.py` để từ chối tài khoản quản trị.
  - `open_read_pool()` / `close_read_pool()`: mở/đóng pool kết nối chỉ đọc (tối đa 1–10 đường, giới hạn câu lệnh 10 giây, múi giờ Việt Nam). Có khóa luồng (`RLock`) để hai yêu cầu cùng lúc không mở hai pool.
  - `read_connection()`: mượn một đường dây từ pool, dùng xong tự trả lại. Nhiều repository khác cũng gọi hàm này.
  - `STATIONS_SQL`, `SITE_SQL`, `DATASETS_SELECT`, `DATASETS_GROUP`: các câu SQL cố định; đều loại bỏ dữ liệu mẫu (`is_demo = false`). `DATASETS_SELECT` đếm số dòng đo (`O`), ước tính (`E`) và từng cờ chất lượng `UNVERIFIED/VALIDATED/SUSPECT/INVALID`.
  - `history_predicate(site_id, dataset_id, date_from, date_to, quality_flag, observed_or_estimated)`: ghép điều kiện lọc; giá trị người dùng gửi được truyền riêng (tham số hóa) để tránh bị chèn SQL độc. `date_to` được tính trọn ngày theo giờ Việt Nam.
  - Lớp `Repository` với `health()`, `stations()`, `datasets(site_code)`, `history(...)`: bốn câu hỏi DB phục vụ bốn endpoint trong `main.py`. `history` trả `{"dataset", "total", "items"}`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm cột trả về cho danh sách trạm hoặc lịch sử EC.
  - Có — nếu muốn đổi giới hạn thời gian câu lệnh hoặc số kết nối tối đa của pool đọc.
  - Không — nếu muốn sửa cách ghi bản lưu dự báo/hồ sơ cống thì sang `backend/repositories/dss_storage.py`.

### `backend/db_security.py`
- **Vai trò trong đời sống:** Người soát thẻ ở cửa kho. Mỗi lần ứng dụng mở đường dây DB, tệp này hỏi DB "tài khoản đang đăng nhập có phải quản trị viên, chủ sở hữu bảng hay thành viên nhóm đặc quyền không?". Nếu có thì từ chối, vì ứng dụng web không nên cầm chìa khóa vạn năng.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: bảng hệ thống của PostgreSQL (`pg_roles`, `pg_auth_members`, `pg_database`, `pg_namespace`, `pg_class`); xét các schema `public`, `dss_reference`, `webgis_security`, `webgis_research`. Đầu ra: không trả gì nếu ổn; báo lỗi `InsufficientPrivilege` nếu tài khoản có quyền quá cao.
- **Các hàm cốt lõi:**
  - `assert_application_role(conn)`: chạy một câu SQL đệ quy dò mọi nhóm quyền tài khoản thuộc về (superuser, tạo DB, tạo vai trò, bỏ qua bảo mật dòng, chủ DB/schema/bảng). Được `backend/database.py` (pool đọc) và `backend/repositories/dss_storage.py` (pool ghi) gọi.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm một schema mới vào danh sách cần kiểm chủ sở hữu.
  - Không — nếu bị lỗi "thiếu quyền đọc" thì xem cấp quyền trong `sql/` và `docs/database-security.md`, không nới lỏng kiểm tra ở đây.

### `backend/security.py`
- **Vai trò trong đời sống:** Bảo vệ đứng ở cửa API. Mọi yêu cầu gửi lên (không phải chỉ xem) phải đến từ đúng trang web của mình; các yêu cầu ghi dữ liệu quan trọng phải trình đúng "API key" (một mật mã dài cấp riêng). Bảo vệ còn dán thêm vài "nhãn an toàn" lên mọi câu trả lời.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: header của yêu cầu HTTP (`origin`, `sec-fetch-site`, `x-api-key`); biến môi trường `WEBGIS_SECURITY_ENABLED`, `WEBGIS_CORS_ORIGINS`, `WEBGIS_WRITE_API_KEY`. Đầu ra: cho qua, hoặc trả JSON lỗi 403/401; thêm header `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`, và `Cache-Control: no-store` cho đường dẫn `/api/` (không cho trình duyệt **cache**, tức lưu bản sao cũ để dùng lại).
- **Các hàm cốt lõi:**
  - `actor`: biến ngữ cảnh ghi "ai đang thao tác" (`LOCAL_APPLICATION`, `API_KEY_CLIENT`...). Repository ghi DB đọc biến này để đóng dấu người thực hiện.
  - `WRITE_PATHS`: danh sách địa chỉ ghi cần API key nếu có cấu hình: `/api/v1/workspace/gate-drafts`, `/api/v1/workspace/multivariate/history`, `/api/v1/multivariate/history`, `/api/v1/forecast-issues`, `/api/v1/field-measurements`.
  - `enabled()`: kiểm tra có bật bảo vệ không (mặc định bật).
  - `same_origin(request)`: từ chối 403 nếu yêu cầu đến từ trang web lạ.
  - `SecurityMiddleware.dispatch(request, call_next)`: quy trình soát cho từng yêu cầu: kiểm nguồn gốc với mọi yêu cầu không phải `GET/HEAD/OPTIONS` tới `/api/`; kiểm API key (so sánh kiểu chống đoán thời gian bằng `hmac.compare_digest`) với `POST` vào `WRITE_PATHS`; rồi gắn header an toàn.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một endpoint ghi mới và muốn nó cũng phải trình API key (thêm vào `WRITE_PATHS`).
  - Có — nếu muốn đổi header an toàn trả về.
  - Không — nếu muốn đổi quyền đọc/ghi của tài khoản DB thì sang `sql/` và `scripts/setup_security.py`.

### `backend/schemas.py`
- **Vai trò trong đời sống:** Bộ mẫu phiếu in sẵn. Mỗi lớp ở đây là một "mẫu đơn" quy định câu trả lời JSON phải có những ô nào, kiểu gì (gọi là **schema dữ liệu**). FastAPI dùng mẫu để kiểm tra và tự sinh tài liệu ở `/docs`.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: dữ liệu từ `backend/database.py`. Đầu ra: JSON đúng mẫu cho các endpoint trạm/EC trong `main.py`. Không đọc tệp hay DB trực tiếp.
- **Các hàm cốt lõi:**
  - `LOCAL_TZ`: múi giờ `Asia/Ho_Chi_Minh`, dùng ở nhiều tệp khác.
  - `QualityFlag` (`UNVERIFIED`, `VALIDATED`, `SUSPECT`, `INVALID`) và `ObservationKind` (`O` = đo, `E` = ước tính): danh sách giá trị hợp lệ.
  - `local_timestamp(value)`: đổi thời điểm sang giờ Việt Nam; báo lỗi nếu thời điểm từ DB không có múi giờ.
  - `Health`, `PointGeometry`, `StationProperties`, `StationFeature`, `StationCollection`: mẫu cho kết quả kiểm tra sức khỏe và danh sách trạm GeoJSON (hệ tọa độ `EPSG:4326`).
  - `DatasetSummary`, `DatasetCollection`: mẫu tóm tắt một bộ dữ liệu EC (mã, `sha256`, tên tệp nguồn, số dòng theo từng cờ...). `sha256` là **hash**: "dấu vân tay" của tệp, đổi một byte là đổi dấu.
  - `ECObservation`, `HistoryFilters`, `ECHistory`: mẫu cho một dòng EC (đơn vị luôn `mS/m`, giá trị không âm) và cả trang lịch sử, ghi rõ `data_kind = historical_observations`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một cột mới vào JSON lịch sử EC (phải thêm cả ở đây lẫn câu SQL trong `database.py`).
  - Không — các API dự báo, hồ sơ cống không dùng mẫu ở đây; mẫu yêu cầu của chúng nằm trong từng tệp `backend/api/*.py`.

### `backend/intake.py`
- **Vai trò trong đời sống:** Bàn tiếp nhận hồ sơ chưa thẩm định. Tệp này cho xem bộ số liệu người dùng gửi (đợt 15/10/2026) nhưng luôn đóng dấu "CHƯA XÁC MINH, không dùng huấn luyện, không dùng quyết định cống". Trước khi cho xem, nó kiểm dấu vân tay từng tệp; sai dấu thì từ chối, không thay bằng dữ liệu mẫu.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: thư mục `data/external/user_v3_review_20261015/` gồm `audit.json`, các tệp gốc liệt kê trong đó, `station_coverage.json`, `normalized_review.json`, `normalized_review.manifest.json`. Đầu ra: JSON cho tab Chất lượng dữ liệu (`frontend/src/intake.js`). Không ghi gì.
- **Các hàm cốt lõi:**
  - `read_intake()`: đọc `audit.json`, kiểm tên tệp không thoát khỏi thư mục và so `sha256` từng tệp; lỗi → 503.
  - `summary()`: `GET /api/v1/workspace/intake` (và bản trùng `/api/v1/research/intake`). Trả trạng thái `UNVERIFIED`, danh sách tệp, số đếm, các vấn đề phát hiện.
  - `coverage()`: `GET .../intake/coverage`. Trả độ phủ theo trạm từ `station_coverage.json`.
  - `read_normalized()`: đọc bảng chuẩn hóa, kiểm hash khớp manifest, kiểm bảng thuộc đúng tệp Excel gốc, và mọi dòng phải là `REVIEW_ONLY`, không được phép dùng huấn luyện/quyết định cống.
  - `points()`: `GET .../intake/measurement-points`. Danh sách điểm đo kèm số bản ghi.
  - `observations(point, offset, limit)`: `GET .../intake/observations?point=...`. Các dòng của một điểm đo, chia trang (tối đa 200); không có điểm → 404.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi thư mục hồ sơ tiếp nhận hoặc thêm thông tin trả về cho tab Chất lượng dữ liệu.
  - Không — nếu muốn sửa cách hiển thị bảng tiếp nhận thì sang `frontend/src/intake.js`.
  - Không — muốn đưa số liệu này thành quan trắc chính thức thì không làm ở đây; phải qua quy trình nhập/kiểm định riêng.

### `backend/research.py`
- **Vai trò trong đời sống:** Biển chỉ đường cũ còn giữ lại. Trước đây các API nằm dưới `/api/v1/research`; tệp này giữ địa chỉ cũ chạy được bằng cách gắn lại toàn bộ `workspace_router` dưới tiền tố đó, và cho các script cũ tiếp tục `import` hai hàm quen thuộc.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào/đầu ra: giống hệt các endpoint của `backend/api/workspace.py`, chỉ khác tiền tố `/api/v1/research`.
- **Các hàm cốt lõi:**
  - `router`: router tiền tố `/api/v1/research`, chứa `workspace_router`. Ví dụ `GET /api/v1/research/summary` chạy cùng hàm với `GET /api/v1/workspace/summary`.
  - Nhập lại `validate_bundle` (từ `backend/domain/workspace.py`) và `load_bundle` (từ `backend/services/workspace.py`): để `scripts/check_webgis_setup.py` và `scripts/import_research_workspace.py` vẫn chạy.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Không — muốn sửa một API workspace thì sang `backend/api/workspace.py`; thay đổi sẽ tự có ở cả hai địa chỉ.
  - Có — chỉ khi quyết định bỏ hẳn địa chỉ cũ `/api/v1/research` (cần kiểm script và trang nào còn gọi).

### `backend/requirements-api.txt`
- **Vai trò trong đời sống:** Danh sách đồ nghề cần mua trước khi chạy backend. Mỗi dòng là một **dependency** (thư viện bên ngoài mà mã cần) kèm phiên bản cố định đã thử cùng nhau trên Python 3.12 ngày 16/10/2026.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: được `pip install -r` đọc khi cài môi trường `.venv`. Đầu ra: không.
- **Các hàm cốt lõi (thư viện):** `fastapi==0.141.1` (khung API), `uvicorn==0.53.0` (máy chạy web), `psycopg[binary]==3.3.5` (trình kết nối PostgreSQL), `psycopg-pool==3.3.3` (pool kết nối), `pydantic==2.13.5` (kiểm tra mẫu dữ liệu), `tzdata==2026.4` (dữ liệu múi giờ). Lưu ý: các thư viện mô hình như pandas, scikit-learn không có trong danh sách này (cài ở nơi khác, xem `README.md`/`docs/run_guide.md`).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu nâng cấp FastAPI hay psycopg, hoặc thêm thư viện mới cho API.
  - Không — muốn đổi thông số kết nối DB thì sửa `.env` (không commit), không phải tệp này.

---

### `backend/api/__init__.py`
- **Vai trò trong đời sống:** Tấm biển đánh dấu `backend/api` là gói Python. Tệp rỗng.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Không.
- **Các hàm cốt lõi:** Không có.
- **Muốn sửa … thì có tìm đến file này không?:** Không — mọi thay đổi API nằm ở các tệp cùng thư mục.

### `backend/api/workspace.py`
- **Vai trò trong đời sống:** Quầy tiếp dân lớn nhất. Hầu hết các tab trên trang (Tổng quan, Quan trắc, bản đồ, Hồ sơ cống) hỏi qua quầy này. Quầy chỉ nhận phiếu, kiểm tra sơ bộ rồi chuyển sang service; không tự tính toán.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: tham số URL và thân yêu cầu JSON từ trang web. Đầu ra: JSON; tệp CSV tải về; tệp kết quả thí nghiệm trong `runs/local_ec_backtest/`; tệp PDF `data/raw/gates/dongthap_gate_catalog_2025.pdf`. Toàn bộ gắn dưới tiền tố `/api/v1/workspace` (và trùng ở `/api/v1/research`).
- **Các hàm cốt lõi:** (viết tắt `WS` = `/api/v1/workspace`)
  - Gắn sẵn hai router con: `multivariate_router` (nên các API dự báo cũng có ở `WS/multivariate/...`) và `dss_storage_router`.
  - Đăng ký trực tiếp (đều `GET`): `WS/summary` → `summary()`, `WS/stations` → `stations()`, `WS/stations/{site_code}/observations` → `observations()`, `WS/experiments/{experiment_id}` → `experiment()`, `WS/boundaries` → `boundaries()`, `WS/gates` → `gates()`, `WS/database-gates` → `database_gates()`, tất cả trong `backend/services/workspace.py`; `WS/experiments/{experiment_id}/next-forecast` → `next_forecast()` và `WS/future-forecast`, `WS/monthly-estimates` → `monthly_estimates()` trong `backend/services/forecasts.py`.
  - `simulation_corridor()`: `GET WS/simulation/corridor`. Gọi `simulation_corridor()` trong `backend/services/spatial_simulation.py`, trả hình tuyến sông.
  - `simulation_timeline()`: `GET WS/simulation/timeline`. Gọi `simulation_timeline()` cùng tệp, trả danh sách tháng cho thanh thời gian.
  - `simulation_frame(year_month, open_below_ec, close_above_ec)`: `GET WS/simulation/frame`. Cần tháng `YYYY-MM` và cặp ngưỡng EC (mặc định 120 và 150 mS/m). Gọi `simulation_frame()` để lấy màu sông và chấm cống của tháng đó.
  - `candidate_stations(gate_code, radius_km)`: `GET WS/database-gates/{gate_code}/candidate-stations`. Bán kính 0–200 km, mặc định 50. Gọi `candidate_stations()` trong `backend/services/workspace.py`.
  - `gate_template(kind, gate_code)`: `GET WS/gate-template/{kind}`. Gọi `gate_template()` trong `backend/services/workspace.py`, trả mẫu hồ sơ cống.
  - `gate_evaluation(request)`: `POST WS/gate-evaluation`. Đọc thân yêu cầu tối đa 256 KiB, từ chối số vô cực/NaN, cần hai ô `policy` và `input` là đối tượng. Gọi `review_dossier()` trong `backend/services/gates.py`. Sai mẫu → 422.
  - `export_estimates(station)`: `GET WS/monthly-estimates/export`. Gọi `monthly_estimates()` rồi ghi thành CSV tải về tên `monthly-ec-estimates.csv`.
  - `artifact(experiment_id, filename)`: `GET WS/artifacts/{experiment_id}/{filename}`. Gọi `artifact_path()` trong `backend/services/workspace.py` (chỉ cho các tên tệp trong danh sách cho phép) và gửi tệp.
  - `gate_source()`: `GET WS/gate-source`. Gửi tệp PDF danh mục cống.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một địa chỉ mới cho bản đồ hoặc đổi ngưỡng EC mặc định của khung bản đồ.
  - Có — nếu đổi giới hạn kích thước hồ sơ cống gửi lên.
  - Không — muốn đổi cách tính màu sông/nội suy thì sang `backend/services/spatial_simulation.py`, `spatial_inputs.py` và `backend/domain/river_interpolation.py`.

### `backend/api/multivariate.py`
- **Vai trò trong đời sống:** Quầy nhận phiếu đặt dự báo EC theo tháng. Quầy kiểm tra phiếu (tên trạm, tháng đúng dạng, số mưa/nhiệt/gió trong khoảng hợp lý) rồi chuyển cho bộ phận dự báo.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: tham số URL hoặc JSON gửi lên. Đầu ra: JSON danh mục mô hình, đầu vào, điểm đánh giá, kết quả dự báo. Không ghi gì. Có ở hai địa chỉ: `/api/v1/multivariate/...` và `/api/v1/workspace/multivariate/...`.
- **Các hàm cốt lõi:**
  - `Month`: kiểu "tháng" phải dạng `YYYY-MM`, tháng 01–12.
  - `ForecastRequest`: mẫu phiếu dự báo: `station`, `target_month`, `input_mode` (`ARCHIVE` = lấy đầu vào lưu trữ, `MANUAL` = người dùng tự nhập), `rainfall_mm` (0–20000), `temperature_degC` (−90 đến 65), `wind_source_units` (0–150). Không nhận ô lạ (`extra='forbid'`). Tệp `dss_storage.py` dùng lại mẫu này.
  - `catalog()`: `GET /api/v1/multivariate/catalog`. Gọi `catalog()` trong `backend/services/multivariate.py`.
  - `inputs(station, target_month)`: `GET /api/v1/multivariate/inputs`. Gọi `inputs()`, trả đầu vào khí tượng/thủy văn tháng `t−2`.
  - `evaluation(station, protocol, experiment, ec_delay_days)`: `GET /api/v1/multivariate/evaluation`. `protocol` là `HISTORICAL` hoặc `FROZEN_EC_WEATHER_ONLY_V1`; `experiment` là `gap_2019_2021`, `gap_2021_2023`, `gap_2022_2023`; `ec_delay_days` là `5` hoặc `35`. Gọi `evaluation()`.
  - `predict(payload)`: `POST /api/v1/multivariate/predict`. Gọi `predict()` trong `backend/services/multivariate.py`; không huấn luyện lại mô hình.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn nới/siết khoảng giá trị mưa, nhiệt, gió được nhập tay.
  - Có — nếu thêm một kỳ đánh giá mới vào danh sách `experiment` cho phép.
  - Không — muốn đổi mô hình hay đặc trưng thì sang `backend/services/multivariate.py`, `backend/domain/multivariate_ec.py` và `data/models/multivariate_registry.json`.

### `backend/api/dss_storage.py`
- **Vai trò trong đời sống:** Quầy lưu trữ hồ sơ. DSS là "hệ hỗ trợ quyết định": ở đây cho lưu và xem lại các lần dự báo đã chạy và các bản nháp hồ sơ cống. Đây là phần tùy chọn, tách khỏi việc dự báo (dự báo vẫn chạy được khi không lưu).
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: JSON từ trang web; header `origin`, `content-type`; biến `WEBGIS_CORS_ORIGINS`. Đầu ra: JSON; việc ghi thật vào bảng `dss_reference.multivariate_prediction_log` và `dss_reference.gate_simulation_drafts` do service/repository làm.
- **Các hàm cốt lõi:** (`router` không có tiền tố riêng nên nằm dưới `/api/v1/workspace`; `multivariate_history_router` có tiền tố `/multivariate`, được gắn cả trong `router` lẫn trực tiếp ở `/api/v1` trong `main.py`)
  - `same_origin_write(request)`: kiểm tra phụ trước khi ghi: nguồn phải hợp lệ (403 nếu không) và nội dung phải là `application/json` (415 nếu không).
  - `DraftRequest`: mẫu bản nháp cống gồm `gate_code` (chữ, số, `_`, `-`; tối đa 64 ký tự), `input`, `policy`.
  - `presets()`: `GET /api/v1/workspace/threshold-presets`. Gọi `presets()` trong `backend/services/dss_storage.py`, trả các bộ ngưỡng EC tham khảo.
  - `history(station, target_month, limit, offset)`: `GET /api/v1/multivariate/history` (và `/api/v1/workspace/multivariate/history`). Gọi `predictions()` trong service; tối đa 100 dòng/trang.
  - `saved_prediction(prediction_id)`: `GET /api/v1/multivariate/history/{prediction_id}`. Gọi `prediction()`.
  - `save_prediction(payload)`: `POST /api/v1/multivariate/history`. Qua `same_origin_write`, nhận `ForecastRequest`, gọi `save_prediction()` trong service.
  - `drafts(gate_code, limit, offset)`: `GET /api/v1/workspace/gate-drafts`. Gọi `drafts()`.
  - `save_draft(request)`: `POST /api/v1/workspace/gate-drafts`. Giới hạn 256 KiB, từ chối số vô cực, kiểm mẫu `DraftRequest`, rồi gọi `save_draft()` trong service ở luồng phụ (để không chặn máy chủ).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm ô lọc mới cho lịch sử dự báo đã lưu.
  - Không — muốn đổi bảng hoặc câu SQL lưu thì sang `backend/repositories/dss_storage.py`; muốn đổi quy tắc kiểm bản nháp thì sang `backend/services/dss_storage.py`.

### `backend/api/data_freshness.py`
- **Vai trò trong đời sống:** Bảng "hạn dùng" của các nguồn số liệu. Giống tờ giấy dán ở tủ lạnh ghi món nào mua tháng nào, còn dùng được tới đâu. Tab Tổng quan dùng để báo nguồn nào còn mới, nguồn nào đã cũ.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: dữ liệu khí tượng qua `get_monthly_weather()` (`backend/repositories/multivariate_inputs.py`); bảng thủy văn tháng qua `_matrix()` và `_signature()` (`backend/repositories/hydrology_inputs.py`); ngày hôm nay theo giờ Việt Nam. Đầu ra: JSON `as_of` và `sources`. Không ghi gì.
- **Các hàm cốt lõi:**
  - `_weather(station, today)`: lấy tháng ERA5 đầy đủ mới nhất của một trạm và gọi `assess()` trong `backend/domain/data_freshness.py`; không có thì `UNAVAILABLE`.
  - `_hydrology(today)`: tìm tháng gần nhất có số hợp lệ cho `KRATIE_Q` (cột `kratie_q_t2`) và `TANCHAU_STAGE` (cột `tc_stage_t2`), rồi gọi `assess()`.
  - `report(today)`: gom kết quả cho `ERA5_MYTHO`, `ERA5_TANCHAU`, `ERA5_MYTHUAN`, hai nguồn thủy văn và `MRC_EC_MYTHO`. Riêng `MRC_EC_MYTHO` được ghi cứng là `STALE`, tháng cuối `2023-12`, mẫu cuối `2023-12-15`.
  - `data_freshness()`: `GET /api/v1/data-freshness`. Gọi `report()`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu có EC Mỹ Tho mới sau 2023 (dòng `MRC_EC_MYTHO` đang ghi cứng, cần cập nhật).
  - Có — nếu muốn thêm một nguồn mới vào bảng hạn dùng.
  - Không — muốn đổi quy tắc tính "còn mấy ngày thì cũ" thì sang `backend/domain/data_freshness.py`.

### `backend/api/gate_screening.py`
- **Vai trò trong đời sống:** Máy chấm phiếu kiểm tra điều kiện lấy nước tại cống. Người dùng đưa số đo, máy trả kết quả rà soát; máy không lưu gì và không ra lệnh đóng/mở cống.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: JSON gửi lên gồm `measurement`, `profile` (tùy chọn), `forecast_context` (tùy chọn), `now_iso`. Đầu ra: JSON kết quả rà soát. Không đọc/ghi DB hay tệp.
- **Các hàm cốt lõi:**
  - `ScreeningRequest`: mẫu phiếu, không nhận ô lạ; `now_iso` tối đa 40 ký tự.
  - `gate_screening(request)`: `POST /api/v1/gate-screening/evaluate`. Giới hạn 64 KiB (413 nếu vượt), sai mẫu → 422. Gọi `evaluate()` trong `backend/domain/gate_intake_rules.py` (gọi thẳng domain, không qua service).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm ô mới vào phiếu kiểm tra gửi lên.
  - Không — muốn đổi quy tắc chấm điều kiện lấy nước thì sang `backend/domain/gate_intake_rules.py` (và bản phía trình duyệt `frontend/src/shared/gate-intake-rules.js`).

### `backend/api/forecast_issues.py`
- **Vai trò trong đời sống:** Sổ phát hành dự báo, giống sổ công văn đi: mỗi lần "phát hành" dự báo cho một tháng thì ghi một dòng, không tẩy xóa; sau này có số đo thật thì chấm điểm đúng/sai, tách riêng bản phát hành đúng hạn và trễ hạn.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: JSON hoặc tham số URL. Đầu ra: JSON. Việc ghi/đọc bảng `dss_reference.forecast_slot`, `forecast_slot_event`, `forecast_issue`, `forecast_score` do service và `backend/repositories/forecast_issues.py` làm.
- **Các hàm cốt lõi:**
  - `IssueRequest`: mẫu phiếu gồm `target_month` (`YYYY-MM`) và `schedule_code` (chỉ nhận `MONTHLY_D06_PREV`).
  - `issue(payload)`: `POST /api/v1/forecast-issues` (trả mã 201). Gọi `issue_month()` trong `backend/services/forecast_issues.py`. Địa chỉ này nằm trong `WRITE_PATHS` của `backend/security.py`.
  - `history(station, date_from, date_to, with_scores)`: `GET /api/v1/forecast-issues?station=&from=&to=&with_scores=`. Gọi `list_issues()` trong cùng service.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một lịch phát hành mới (mở rộng `schedule_code`).
  - Không — muốn đổi cách tính điểm hay thời hạn phát hành thì sang `backend/services/forecast_issues.py` và `backend/domain/forecast_issue.py`.

### `backend/api/field_measurements.py`
- **Vai trò trong đời sống:** Hộp thư nhận phiếu EC đo ngoài thực địa của cán bộ. Người gửi phải có "chìa khóa gửi"; người duyệt phải có "chìa khóa duyệt" khác. Ai cũng xem được phiếu đã duyệt, còn phiếu chờ duyệt hoặc bị từ chối chỉ người duyệt xem được.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: JSON gửi lên; header `x-api-key`; biến `WEBGIS_WRITE_API_KEY`, `WEBGIS_REVIEW_API_KEY`. Đầu ra: JSON. Ghi/đọc thật vào `dss_reference.field_measurement`, `field_measurement_review` qua service và `backend/repositories/field_measurements.py`.
- **Các hàm cốt lõi:** (tiền tố `/api/v1/field-measurements`)
  - `_key(request, name)`, `require_submit_key`, `require_review_key`: so API key người gửi với biến môi trường; chưa cấu hình → 503, sai → 401.
  - `FieldRequest`: mẫu phiếu đo: `ec`, `unit` (`µS/cm`, `dS/m`, `mS/cm`, `mS/m`), `observed_at`, `longitude`, `latitude`, `position_kind` (`RIVER`/`FIELD`), `device`, `submitted_by`, `ec_basis` (`EC25`/`RAW`/`UNKNOWN`), `calibrated_at`, `calibration_reference`, `water_temp_degC`.
  - `ReviewRequest`: mẫu phiếu duyệt: `decision` (`APPROVED`/`REJECTED`), `reviewer`, `note`.
  - `submit(request)`: `POST /api/v1/field-measurements` (201). Cần đúng nguồn và chìa khóa gửi; giới hạn 16 KiB. Gọi `submit()` trong `backend/services/field_measurements.py`.
  - `measurements(request, status, bbox)`: `GET /api/v1/field-measurements?status=&bbox=`. Nếu không phải `APPROVED` thì cần chìa khóa duyệt. Gọi `list_measurements()`.
  - `review(measurement_id, payload)`: `POST /api/v1/field-measurements/{measurement_id}/review`. Cần chìa khóa duyệt; đánh dấu người thao tác là `REVIEW_KEY_CLIENT` rồi gọi `review()` trong service.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một đơn vị EC được chấp nhận hoặc thêm ô vào phiếu đo.
  - Không — muốn đổi cách quy đổi đơn vị hay cờ cảnh báo thì sang `backend/services/field_measurements.py`; đổi câu SQL thì sang `backend/repositories/field_measurements.py`.

---

### `backend/repositories/__init__.py`
- **Vai trò trong đời sống:** Tấm biển đánh dấu `backend/repositories` là gói Python. Tệp rỗng.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Không.
- **Các hàm cốt lõi:** Không có.
- **Muốn sửa … thì có tìm đến file này không?:** Không.

### `backend/repositories/workspace.py`
- **Vai trò trong đời sống:** Thủ kho của "bộ hồ sơ nghiên cứu". Tùy công tắc `WEBGIS_RESEARCH_MODE`, thủ kho lấy hồ sơ từ tệp ảnh chụp đã niêm phong (`snapshot`) hoặc từ PostgreSQL (`postgres`). Nếu nguồn đã chọn hỏng, thủ kho báo lỗi chứ không lén đưa nguồn kia thay thế.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `data/research/workspace.json` và `data/research/workspace_manifest.json` (hoặc đường dẫn trong `WEBGIS_RESEARCH_FILE`); biến `WEBGIS_WORKSPACE_DATASETS` (chọn bộ dữ liệu cho từng trạm); bảng `public.measurement_site`, `public.data_source`, `public.source_dataset`, `public.conductivity_observation`, `public.irrigation_gate`; tệp `data/models/future_ec_forecast_2024_2026.csv`. Đầu ra: từ điển Python cho `backend/services/workspace.py`, `forecasts.py`, `spatial_inputs.py`. Không ghi gì.
- **Các hàm cốt lõi:**
  - `WorkspaceUnavailable`: lỗi "nguồn hồ sơ không dùng được".
  - `_file_bundle(path, stamp, manifest_stamp)`: đọc `workspace.json` (tối đa 8 MB), so `sha256` với manifest, rồi gọi `validate_bundle()` trong `backend/domain/workspace.py`. Kết quả được **cache** (nhớ tạm) theo thời điểm sửa tệp nên không đọc lại khi tệp không đổi.
  - `load_bundle()`: hàm chính. Luôn đọc snapshot trước; nếu chế độ `postgres` thì gọi `_postgres_bundle()`. Gắn nhãn `storage_mode`, `observation_source`, `dataset_selection`. Mọi lỗi → `WorkspaceUnavailable` với câu "No fallback was used".
  - `bundle_stamp()`: tạo "dấu phiên bản" rẻ (thời điểm sửa tệp, số dòng EC, mã bộ dữ liệu) để service mô phỏng biết khi nào cần tính lại.
  - `_snapshot_reference_points(bundle, database_site_codes, database_source_codes)`: lấy riêng các điểm RIA2 (mã bắt đầu `RIA2_`) từ snapshot, gắn `reference_only=True`, để vẫn hiện trên bản đồ mà không giả làm số đo từ DB.
  - `_postgres_bundle(bundle)`: với mỗi trạm trong DB, chọn một bộ dữ liệu `RAW_EC` (theo `WEBGIS_WORKSPACE_DATASETS`, nếu không thì bộ nhập mới nhất), đọc toàn bộ dòng EC, xử lý trường hợp nguồn chỉ có ngày (`DATE_ONLY`), tính khoảng cách giữa các lần đo, ghi chú `gate_decision_eligible=False`; rồi nối thêm điểm RIA2 tham khảo.
  - `read_json(relative_path)`: đọc một tệp JSON trong dự án (dùng cho ranh giới hành chính).
  - `estimate_rows()`: đọc `data/models/future_ec_forecast_2024_2026.csv` (bản lưu nghiên cứu cũ, không phải dự báo Mỹ Tho hiện hành).
  - `database_gates()`: đọc danh mục cống từ `public.irrigation_gate`; kèm ghi chú `is_active` là trạng thái danh mục, không phải đang mở/đóng.
  - `candidate_stations(gate_code, radius_km)`: tìm tối đa 5 trạm trong bán kính quanh cống bằng `ST_DWithin`/`ST_Distance` (hàm đo khoảng cách của PostGIS, đơn vị mét); ghi rõ `hydrological_link_validated=False` (gần không có nghĩa là thông nước).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi cách chọn bộ dữ liệu EC cho từng trạm ở chế độ PostgreSQL.
  - Có — nếu đổi vị trí tệp snapshot hay cách xử lý điểm RIA2.
  - Không — muốn đổi nội dung JSON trả về tab Tổng quan/Quan trắc thì sang `backend/services/workspace.py`.

### `backend/repositories/multivariate_inputs.py`
- **Vai trò trong đời sống:** Người ghi sổ thời tiết. Từ số liệu mưa, nhiệt, gió theo ngày, người này cộng/tính trung bình thành số liệu tháng, và chỉ nhận tháng đủ ngày, không trùng, không thiếu. Mô hình dự báo dùng tháng `t−2` (hai tháng trước tháng cần dự báo).
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `data/raw/meteorology/openmeteo/openmeteo_all_stations_daily.csv` (nguồn cũ, đơn vị gió chưa xác nhận); thư mục `data/external/multivariate_weather/` và `data/external/mythuan_weather_20261104/`, mỗi thư mục có `manifest.json` và các tệp `era5_*.json`. Đầu ra: từ điển số liệu tháng cho `backend/services/multivariate.py`, `spatial_inputs.py`, `backend/api/data_freshness.py`. Không ghi gì.
- **Các hàm cốt lõi:**
  - `ALIASES`, `normalize_station(station)`: quy đổi các cách gọi tên trạm (`MYTHO`, `MRC_VN_019805`, `019805`...) về `MyTho`, `TanChau`, `MyThuan`; tên lạ → lỗi.
  - `WeatherInputUnavailable`: lỗi "thiếu, sai hoặc không đủ ngày".
  - `_month(value)`: kiểm chuỗi tháng `YYYY-MM`.
  - `_aggregate(station, month, rows, provenance)`: kiểm đủ từng ngày của tháng, không âm, không vô cực; tính tổng mưa, trung bình nhiệt, trung bình gió; ghi giả định "cuối tháng + 5 ngày mới có số liệu".
  - `_signature()` và `_load(signature)`: `_signature` lấy dấu (đường dẫn, thời điểm sửa, kích thước) các tệp nguồn; `_load` đọc tất cả (có cache theo dấu đó), kiểm `sha256` từng tệp ERA5 với manifest, kiểm đơn vị (`m/s`, `mm`, `°C`), mô hình `era5`, múi giờ; bản tải về sau cùng thay trọn tháng, không ghép ngày lẻ.
  - `get_monthly_weather(station, require_verified_wind=True)`: mọi tháng đủ của một trạm theo thứ tự thời gian; mặc định chỉ lấy tháng có gió đã xác minh đơn vị.
  - `get_weather_input(station, target_month)`: lấy số liệu tháng `t−2` cho tháng cần dự báo; thiếu → `WeatherInputUnavailable` kèm lý do.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một trạm khí tượng mới hoặc một thư mục ERA5 mới.
  - Có — nếu đổi giả định "cuối tháng + 5 ngày".
  - Không — muốn đổi mô hình dùng đặc trưng nào thì sang `backend/domain/multivariate_ec.py` và manifest mô hình.

### `backend/repositories/hydrology_inputs.py`
- **Vai trò trong đời sống:** Người ghi sổ nước sông. Từ số liệu ngày của lưu lượng Kratie (Campuchia) và mực nước Tân Châu, người này tính ra 5 con số tháng mà mô hình Mỹ Tho cần. Tháng có ít hơn 20 ngày số liệu thì bỏ trống, không đoán.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: đúng một tệp khớp mẫu trong mỗi thư mục: `data/external/mrc_kratie_discharge_20261029/014901_Discharge_Calculated daily discharge_????????.csv`, `data/external/tien_manual_long_20261029/019803_Water_Level_Manual_????????.csv`, `data/external/tien_manual_2024_2026_20261029/019803_Water_Level_Manual_????????.csv`. Đầu ra: từ điển đặc trưng thủy văn cho `backend/services/multivariate.py`, `spatial_inputs.py`, `backend/domain/multivariate_ec.py`, `backend/api/data_freshness.py`. Không ghi gì.
- **Các hàm cốt lõi:**
  - `FEATURES`, `UNITS`, `LABELS`: tên, đơn vị và nhãn tiếng Việt của 5 đặc trưng: `kratie_q_t2` (m³/s), `kratie_q3_t2` (m³/s), `kratie_q_ratio_t2` (không đơn vị), `tc_stage_t2` (m), `tc_stage3_t2` (m).
  - `source_paths()`: tìm ba tệp nguồn; không đúng một tệp/thư mục → lỗi.
  - `_signature()`, `_source_hashes(signature)`: dấu phiên bản tệp và `sha256` từng tệp (có cache, chỉ băm một lần cho mỗi phiên bản).
  - `_monthly_stage(paths)`: gộp hai tệp mực nước, kiểm không trùng giờ và đơn vị là `m`, lấy trung vị theo ngày rồi trung vị theo tháng (cần ≥ 20 ngày).
  - `_monthly_flow(path)`: kiểm lưu lượng không trùng, đơn vị `m^3/s`, không âm; trung bình theo ngày rồi theo tháng (cần ≥ 20 ngày).
  - `_matrix(signature)`: dựng bảng từ 01/1985: lưu lượng tháng, trung bình 3 tháng, tỷ lệ so với trung vị cùng tháng của tối đa 15 năm trước (cắt trong 0–5), mực nước tháng và trung vị 3 tháng. Có cache.
  - `get_hydrology_input(target_month, now=None)`: lấy dòng tháng `t−2`; nếu chưa qua "cuối tháng + 5 ngày" hoặc thiếu số → báo lỗi, không thay bằng 0. Trả kèm tên nguồn, hash tệp và ghi chú giả định.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu tải tệp Kratie/Tân Châu mới vào thư mục khác (phải sửa đường dẫn/mẫu tên).
  - Có — nếu muốn đổi ngưỡng 20 ngày hoặc cách tính tỷ lệ lưu lượng.
  - Không — đổi các đặc trưng này sẽ không khớp mô hình đã lưu; muốn đổi mô hình thì phải huấn luyện bản mới bằng `scripts/train_mytho_hydrology_primary.py` và cập nhật registry.

### `backend/repositories/dss_storage.py`
- **Vai trò trong đời sống:** Thủ kho được phép ghi, nhưng chỉ vào ngăn "lưu trữ DSS". Thủ kho này dùng tài khoản DB riêng (khác tài khoản chỉ đọc) và phải có công tắc cho phép ghi mới hoạt động. Mỗi lần ghi đều đóng dấu "ai thao tác".
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: biến `WEBGIS_DSS_WRITES_ENABLED`, `DSS_PGUSER`, `DSS_PGPASSWORD`, `WEBGIS_DSS_POOL_MAX`, `PGHOST`, `PGPORT`, `PGDATABASE`, `WEBGIS_DB_USER`; bảng `dss_reference.ec_threshold_presets`. Đầu ra (ghi): `dss_reference.multivariate_prediction_log`, `dss_reference.gate_simulation_drafts`; đặt `webgis.actor` cho mỗi giao dịch ghi.
- **Các hàm cốt lõi:**
  - `StorageDisabled`: lỗi "chức năng lưu đang tắt".
  - `require_writes()`: báo `StorageDisabled` nếu `WEBGIS_DSS_WRITES_ENABLED` không phải `true`.
  - `_write_config()`, `_configure_writer(conn)`: thông số và kiểm vai trò (gọi `assert_application_role()`) cho pool ghi.
  - `open_write_pool()` / `close_write_pool()`: mở/đóng pool ghi (mặc định tối đa 2 đường). Bắt buộc `DSS_PGUSER` khác `WEBGIS_DB_USER`.
  - `write_connection()`: mượn đường dây ghi và ghi tên người thao tác lấy từ `actor` (`backend/security.py`). Các repository `field_measurements.py`, `forecast_issues.py` cũng dùng hàm này.
  - `threshold_presets()`: đọc các bộ ngưỡng EC tham khảo (qua đường chỉ đọc).
  - `save_prediction(prediction)`: thêm một dòng vào `multivariate_prediction_log`, lưu toàn bộ kết quả dạng JSON.
  - `predictions(station, target_month, limit, offset)`, `prediction(prediction_id)`: đọc danh sách/một bản dự báo đã lưu, mới nhất trước.
  - `save_draft(gate_code, data, policy)`, `drafts(gate_code, limit, offset)`: ghi/đọc bản nháp hồ sơ cống trong `gate_simulation_drafts`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu đổi tên bảng lưu hoặc thêm cột lưu cho bản dự báo.
  - Có — nếu đổi số kết nối tối đa của pool ghi.
  - Không — muốn tạo bảng mới trong DB thì viết SQL ở `sql/` và áp bằng `scripts/apply_dss_storage.py` (lệnh `--apply` ghi thật, chỉ chạy khi chắc chắn).

### `backend/repositories/field_measurements.py`
- **Vai trò trong đời sống:** Sổ lưu phiếu đo thực địa và sổ duyệt. Phiếu đã ghi thì không sửa; mỗi lần duyệt là một dòng mới. Tệp này còn có bộ lọc "phiếu nào đủ chuẩn để làm nhãn EC tháng" theo tiêu chí đã đăng ký trước ngày 14/11.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `dss_reference.field_measurement`, `dss_reference.v_field_measurement_status` (một **view**, tức bảng ảo ghép từ bảng khác), `public.measurement_site`, `public.conductivity_observation`, `public.source_dataset`. Đầu ra (ghi): `dss_reference.field_measurement`, `dss_reference.field_measurement_review`.
- **Các hàm cốt lõi:**
  - `insert_measurement(value, raw)`: ghi một phiếu đo, tạo điểm bản đồ từ kinh/vĩ độ (hệ 4326), lưu cả bản gốc người gửi.
  - `list_measurements(status, bbox, limit=200)`: đọc phiếu theo trạng thái và khung bản đồ `bbox`.
  - `insert_review(measurement_id, decision, reviewer, note)`: thêm một dòng duyệt; không có phiếu → trả `None`.
  - `LABEL_SITES`: `MYTHO` → `MRC_VN_019805`, `MYTHUAN` → `MRC_VN_019804`, `TANCHAU` → `MRC_VN_019803`.
  - `historical_month_median(longitude, latitude, observed_at)`: trung vị EC lịch sử cùng tháng ở trạm MRC gần nhất, dùng làm mốc so khi gắn cờ phiếu.
  - `field_label_from_rows(rows, target_month)`: lọc phiếu theo tiêu chí: ngày 13–17, giờ 9:00–16:00, hiệu chuẩn trong 30 ngày có ghi tham chiếu, `EC25`, vị trí `RIVER`; cần ≥ 2 phiếu cách nhau ≥ 30 phút và chênh lệch ≤ 20% trung vị. Đạt thì trả nhãn `FIELD_APPROVED` với mã tham chiếu băm.
  - `candidate_field_label(station, target_month)`: lấy phiếu đã duyệt trong 2 km quanh trạm trong tháng, rồi gọi `field_label_from_rows()`. Được `scripts/score_forecast_issues.py` dùng.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu đổi bán kính 2 km hoặc khung giờ/ngày đủ chuẩn làm nhãn (lưu ý đây là tiêu chí đã khóa trước, đổi phải ghi phiên bản giao thức mới).
  - Không — muốn đổi cách quy đổi đơn vị EC phiếu gửi thì sang `backend/services/field_measurements.py`.

### `backend/repositories/forecast_issues.py`
- **Vai trò trong đời sống:** Sổ cái của sổ phát hành dự báo: chỉ thêm, không xóa. Ghi "suất phát hành" (slot), sự kiện bỏ lỡ, bản phát hành và điểm chấm.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `dss_reference.forecast_slot`, `forecast_slot_event`, `forecast_issue`, `forecast_score`; bảng EC `public.conductivity_observation`, `public.source_dataset`, `public.data_source`, `public.measurement_site`. Đầu ra (ghi): bốn bảng `dss_reference.forecast_*` kể trên.
- **Các hàm cốt lõi:**
  - `insert_slot(conn, station, target_month, schedule_code, scheduled_at)`: tạo suất phát hành; đã có thì lấy cái cũ (không tạo trùng).
  - `insert_missed(conn, slot_id, reason_code)`: ghi sự kiện `MISSED` kèm lý do.
  - `existing_issue(conn, slot_id)`: xem suất đó đã có bản phát hành chưa.
  - `insert_issue(conn, slot_id, issue)`: ghi bản phát hành (phiên bản mô hình, `model_sha256`, số dự báo, toàn bộ dữ liệu); câu SQL tạm ghi `'LATE'`, nhưng trigger `forecast_issue_guard` trong `sql/33_forecast_issue.sql` (cập nhật ở `33b_forecast_issue_guard.sql`) tự sửa lại trước khi lưu: phát hành trước giờ hẹn thì bị từ chối; sau giờ hẹn dưới 1 giờ và slot chưa bị đánh dấu `MISSED` thì thành `ON_TIME`, còn lại `LATE`. Trigger giống người trực sổ: ai nộp bài thì ông ấy tự ghi giờ nộp và đóng dấu đúng hạn/trễ hạn, người nộp không tự khai được.
  - `list_slots(station, date_from, date_to, limit=200)`: ghép suất, sự kiện, bản phát hành và điểm (chỉ điểm theo giao thức `MONTHLY_EC_LABEL_V1_20261114`).
  - `insert_score(issue_id, score)`: ghi điểm chấm (số đo, sai số tuyệt đối). Được `scripts/score_forecast_issues.py` dùng.
  - `SITE_CODES`, `candidate_mrc_label(station, target_month)`: chọn đúng một mẫu MRC trong tháng làm nhãn, ưu tiên theo bộ nhập sớm nhất rồi ngày gần ngày 15 nhất; cố ý không chọn theo sai số.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu đổi quy tắc chọn mẫu MRC làm nhãn tháng.
  - Không — muốn đổi thời điểm phát hành theo lịch thì sang `backend/services/forecast_issues.py` và `backend/domain/forecast_issue.py`.
