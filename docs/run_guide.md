# Chạy và tái lập trên Windows

Thực hiện trong PowerShell tại gốc repository. Giữ `.venv` và `.venv-api` hiện có. Nếu máy nhận bàn giao chưa có Python environment, cài Python 3.12 và chạy `py -3.12 -m venv .venv` trước khi cài dependency.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-prototype.txt
npm.cmd --prefix frontend ci
.venv\Scripts\python.exe scripts/apply_dss_storage.py --apply
.venv\Scripts\python.exe -m tools.security_setup roles --apply
.venv\Scripts\python.exe -m tools.security_setup auth-secret --apply
.venv\Scripts\python.exe scripts/apply_dss_migration.py --file sql/36_app_user.sql --version 36_app_user --apply
.venv\Scripts\python.exe scripts/apply_dss_migration.py --file sql/37_app_registration.sql --version 37_app_registration --apply
.\start.ps1
```

Mở http://127.0.0.1:8000/workspace.html. Script mặc định chọn PostgreSQL, kiểm tra build thành công rồi chạy máy chủ ngay trong terminal hiện tại; Ctrl+C để dừng. Có thể dùng `.\start.ps1 -Mode postgres -Port 8016`. Chỉ dùng `-SkipBuild` khi bản build đã cập nhật; script không báo khởi động thành công trước khi Uvicorn sẵn sàng.

Tạo tài khoản quản trị ban đầu sau migration bằng `scripts/create_app_user.py --username <tên> --display-name <tên hiển thị> --role INSPECTOR --apply`. Script hỏi mật khẩu qua terminal, không nhận mật khẩu trên dòng lệnh. Người mới bấm **Đăng ký**; tài khoản `FIELD_STAFF` chỉ đăng nhập được sau khi `INSPECTOR` bấm **Duyệt tài khoản**. Đăng xuất xóa phiên trong tab hiện tại. Khách không truy cập được dự báo EC đa biến.

Có thể chạy từng bước:

```powershell
npm.cmd --prefix frontend run build
.venv\Scripts\python.exe run_webgis.py --mode postgres --port 8000
```

Phát triển frontend bằng `npm.cmd --prefix frontend run dev`; Vite chuyển `/api` tới backend cổng 8000. Chạy backend bằng `.venv\Scripts\python.exe run_webgis.py --mode postgres --api-only` nếu chưa cần build giao diện. Trong Vite mở `/workspace.html`; `/index.html` là trang lịch sử PostgreSQL. Trang cũ `/research.html` chuyển tới workspace.

## Chọn nguồn rõ ràng

- `snapshot`: đọc `data/research/workspace.json`, kiểm tra SHA-256 với `workspace_manifest.json`. Đây là quan trắc có nguồn và kết quả hồi cứu, không phải dữ liệu trực tiếp.
- `postgres`: quan trắc đọc `public.measurement_site`, `public.source_dataset`, `public.conductivity_observation` qua tài khoản WEBGIS_DB_USER chỉ đọc. Mỗi trạm chọn RAW_EC được nhập gần nhất (hoặc phiên bản được ghim); không trộn phiên bản. Kết quả mô hình và danh mục cống vẫn đọc bộ tệp có manifest. Không fallback khi DB lỗi.
- `/index.html` và `/api/v1/health`, `/api/v1/stations` luôn truy cập DB thật. `/api/v1/app-health` chỉ xác nhận tiến trình; `/api/v1/ready` kiểm tra DB khi chạy chế độ PostgreSQL và được Docker dùng làm healthcheck.
- Tiếp nhận v3 luôn đọc tệp riêng; chưa nhập vào quan trắc hay huấn luyện, dù chọn chế độ PostgreSQL.
- Ước tính EC từ khí tượng 2024–2026 luôn đọc artifact tệp. Đây là ước tính hồi cứu dùng khí tượng cùng tháng, không phải dự báo hiện tại hoặc căn cứ vận hành cống.
- API chính của workspace là `/api/v1/workspace`. `/api/v1/research` chỉ còn các route workspace lõi và tiếp nhận cũ; không chứa route multivariate hoặc DSS storage. Lịch sử dự báo đã lưu vẫn có ở `/api/v1/workspace/multivariate/history` và `/api/v1/multivariate/history`, đều yêu cầu đăng nhập.

## Phiên đăng nhập và giới hạn yêu cầu

`POST /api/v1/auth/login` và `/register` mặc định giới hạn 10 yêu cầu/IP trong 60 giây; login còn giới hạn 5 lần theo cặp `(IP, username viết thường)`. Có thể đặt `WEBGIS_AUTH_RATE_LIMIT_WINDOW_SECONDS`, `WEBGIS_AUTH_RATE_LIMIT_MAX_ATTEMPTS`, `WEBGIS_AUTH_USERNAME_RATE_LIMIT_MAX_ATTEMPTS` **trước khi khởi động** máy chủ. Bộ đếm ở trong bộ nhớ từng worker và tối đa 10.000 khóa; khởi động lại sẽ xóa bộ đếm. Khi đặt sau reverse proxy, cấu hình `--forwarded-allow-ips` của Uvicorn chỉ cho IP proxy tin cậy để `request.client.host` là IP người dùng. Ứng dụng không tự đọc `X-Forwarded-For`.

File `sql/38_app_user_username_case_insensitive.sql` kiểm tra tài khoản trùng khác hoa/thường trước khi tạo unique index. Ngày 18/11/2026, migration đã được chạy riêng bằng `--apply` trên DB cục bộ `dongthap_gis`, phiên bản `38_app_user_username_case_insensitive`, checksum `93cbb62439f8ce7636787971555ef82f179e139e50d1654b8b0526ef7a1d5c92`. DB khác vẫn cần rà dữ liệu và triển khai migration riêng; không chạy lại chỉ vì file có trong repo.

API phiếu EC thực địa dùng phân trang theo `(submitted_at, measurement_id)` với `limit` tối đa 200, `total`, `has_more` và `next_cursor`. Khi gọi trang tiếp, chuyển hai trường trong `next_cursor` thành `before_submitted_at` và `before_measurement_id`. Response `status=APPROVED` cho khách và nhân viên đo không chứa danh tính người gửi, người duyệt hoặc ghi chú duyệt; người kiểm tra xem được thông tin này sau đăng nhập. Để tăng tốc phân trang trên DB đã có bảng phiếu đo, xem kế hoạch rồi áp dụng migration bổ sung:

```powershell
.venv\Scripts\python.exe scripts/apply_dss_migration.py --file sql/39_field_measurement_pagination.sql --version 39_field_measurement_pagination
.venv\Scripts\python.exe scripts/apply_dss_migration.py --file sql/39_field_measurement_pagination.sql --version 39_field_measurement_pagination --apply
```

Migration 39 đã áp dụng trên DB cục bộ `dongthap_gis` ngày 19/11/2026, checksum `6c82beda201af6eb5771e2b68fab9668c7e32a767b306898fb8edcbfcd5fd16e`. Đã xác minh bản ghi migration và hai index phân trang.

Cache workspace PostgreSQL dùng `public.workspace_cache_version` (một dòng) thay cho `count(*)` trên toàn bảng quan trắc mỗi chu kỳ. Trigger mức statement trên `source_dataset`, `conductivity_observation`, `measurement_site`, `data_source` tăng `version` trong cùng giao dịch ETL; rollback không đổi version. Tài khoản `webgis_reader` chỉ được `SELECT` bảng phiên bản. Migration 40 đã áp dụng trên DB cục bộ `dongthap_gis` ngày 19/11/2026, checksum `97edf140f8455fe179372cf42b4c7d51797104e56fdcdb2a9be0bc7d6ab3da81`. Với DB khác, chạy:

```powershell
.venv-api\Scripts\python.exe scripts/apply_dss_migration.py --file sql/40_workspace_cache_version.sql --version 40_workspace_cache_version
.venv-api\Scripts\python.exe scripts/apply_dss_migration.py --file sql/40_workspace_cache_version.sql --version 40_workspace_cache_version --apply
```

Không cần thêm cột vào bảng quan trắc hoặc chạy lại ETL. Cache có thể giữ dữ liệu cũ tối đa 30 giây sau một giao dịch nhập liệu; mỗi worker kiểm tra một dòng phiên bản rồi tự dựng lại bundle khi phiên bản đổi. Danh sách dataset trong workspace chỉ chứa dataset đang được chọn cho mỗi trạm; các mã phiên bản còn lại nằm trong `available_dataset_codes` và chi tiết đầy đủ vẫn ở `/api/v1/stations/{site_code}/datasets`.

Hai test hợp đồng PostgreSQL trong `tests/test_dss_postgres_contract.py` đã đạt trên DB tách biệt `webgis_test_20261118` có PostGIS; chúng dùng bảng tạm và rollback. Migration 38 cũng được thử trên DB này với username trùng, chạy lặp và ràng buộc unique. Test bằng chứng nguồn Mỹ Thuận dùng bản manifest lịch sử đã khôi phục vào `outputs/mythuan_three_station_20261104/source_snapshots/`; checksum khớp với run cũ, trong khi manifest dữ liệu hiện tại được giữ nguyên.

`tools/feature_building.py` hiện loại file `*_daily.csv` khi chọn CSV mực nước MRC, để luôn đọc file quan trắc gốc có cột `observed_at`, `value`, `unit`. Trước bản sửa, thứ tự liệt kê file có thể khiến script chọn nhầm file tổng hợp ngày. Chưa xác định từng run nghiên cứu cũ đã chọn file nào; giữ nguyên `outputs/` đã công bố, không tái tạo chúng chỉ để khớp mã hiện tại.

## Đo hiệu năng cục bộ

Chạy `.venv\Scripts\python.exe -m scripts.benchmark_api --samples 10` khi PostgreSQL cục bộ và một tài khoản nhân viên đang hoạt động. Script dùng TestClient trong cùng tiến trình, đọc DB thật, bỏ lượt khởi động đầu tiên của từng endpoint và đếm lệnh `Connection.execute`; nó không đo mạng hay tải đồng thời.

| Endpoint | Trước P1 p50/p95 (ms) | Sau P1 p50/p95 (ms) | Số truy vấn trước → sau |
|---|---:|---:|---:|
| `/simulation/frame` | 42,15 / 50,92 | 28,37 / 41,36 | 17 → 1 |
| `/stations` | 2,90 / 3,28 | 2,72 / 3,18 | 1 → 1 |
| `/multivariate/predict` | 83,01 / 109,82 | 73,85 / 88,83 | 2 → 2 |

Mỗi bên dùng 10 mẫu tuần tự trên cùng máy và payload trong script; số liệu mang tính tham khảo cho lần chạy này. Các lần đo lại sau P1 dao động theo tải máy (p50 frame khoảng 18–28 ms, predict khoảng 53–74 ms), còn số truy vấn là 1 và 2. Cache mô hình kiểm tra checksum khi nạp hoặc khi `mtime_ns`/kích thước thay đổi. File bị sửa nhưng giữ nguyên cả hai metadata có thể chưa được phát hiện cho tới lần nạp sau.

## Docker và CI

`Dockerfile` tạo frontend rồi chạy API ở chế độ snapshot mặc định; có thể đổi bằng `-e WEBGIS_RESEARCH_MODE=postgres` cùng cấu hình DB. Healthcheck Docker gọi `/api/v1/ready`: chế độ PostgreSQL phải truy vấn DB thành công, chế độ snapshot chỉ kiểm tra tiến trình. Cần cấp `WEBGIS_AUTH_SECRET` (ít nhất 32 ký tự) lúc chạy container; không đưa bí mật vào image. Ví dụ sau khi đặt biến môi trường trên máy chủ: `docker build -t webgis-tlcn .` và `docker run --rm -p 127.0.0.1:8000:8000 -e WEBGIS_AUTH_SECRET webgis-tlcn`. Workflow `.github/workflows/ci.yml` chạy kiểm thử Python với DB PostGIS riêng, kiểm thử frontend, build Vite, đồng thời build và smoke-test Docker image khi push hoặc tạo PR. [Lượt GitHub Actions 44324276115](https://github.com/12hqwwo/saltwater-intrusion-warning/actions/runs/44324276115) trên commit `feaf5dc` đã đạt cả job `test` và `container-smoke`.

`requirements-dev.txt` thêm `paramiko>=4.0,<5` để kiểm thử nhánh xử lý lỗi SFTP của `scripts/utilities/collect_fes2022b.py` trong CI; dịch vụ web không cần thư viện này khi chạy bình thường.

## PostgreSQL/PostGIS

Sao chép `.env.example` thành `.env` nếu chưa có; điền PGHOST, PGPORT, PGDATABASE, PGUSER và cấu hình mật khẩu cục bộ bằng PGPASSWORD hoặc PGPASSFILE. Không ghi mật khẩu vào báo cáo/Git. `run_webgis.py` nạp `.env`; lệnh uvicorn trực tiếp không tự nạp.

```powershell
.venv\Scripts\python.exe scripts/check_webgis_setup.py
.venv\Scripts\python.exe scripts/import_research_workspace.py
```

Lệnh import trên là dry-run, không xác nhận DB hoạt động. Trước khi ghi DB, người quản trị rà soát schema hiện hữu, quyền và bản sao lưu PostgreSQL. `sql/04_research_workspace.sql` định nghĩa schema nghiên cứu; các schema `public` nằm trong `sql/`. Không chạy bootstrap lên DB đã có dữ liệu.

Nếu các bảng `public` đã có dữ liệu, chạy trực tiếp:

```powershell
.venv\Scripts\python.exe run_webgis.py --mode postgres
```

## Tái lập khoa học và thu thập

Workspace PostgreSQL không cần nhập lại schema nghiên cứu. Mục Quan trắc có sẵn phần tra cứu nguồn / trạm / phiên bản. Muốn ghim bộ dữ liệu, đặt biến `WEBGIS_WORKSPACE_DATASETS` thành JSON ánh xạ mã trạm sang mã dataset; cấu hình sai hoặc thiếu phiên bản sẽ báo lỗi. Bỏ biến này để dùng phiên bản nhập gần nhất.

```powershell
.venv\Scripts\python.exe scripts/audit_research_data.py
.venv\Scripts\python.exe scripts/build_research_workspace.py --fit
```

`--fit` chạy lại bốn thí nghiệm, tạo thư mục run mới rồi cập nhật registry/snapshot. Giữ bản run cũ để truy vết. Target là mẫu EC của tháng kế tiếp, hiện mỗi tháng có một mẫu; không nội suy thành nhãn ngày/giờ. Mô hình được chọn trên validation; test là hồi cứu, không độc lập với toàn bộ lịch sử phát triển.

## Tái tạo artifact RF_compact sau rà soát 01/11/2026

Khi cần tái tạo đúng hai run Mỹ Tho đang được tham chiếu, chạy tuần tự từ gốc repository:

```powershell
.venv\Scripts\python.exe -m scripts.rf_compact_artifacts --lag 5
.venv\Scripts\python.exe -m scripts.rf_compact_artifacts --lag 35
.venv\Scripts\python.exe -m scripts.update_workspace_with_rf_compact
```

Hai bước đầu kiểm tra và giữ dự báo nghiên cứu nguồn 2019–2023, đóng gói 24 tháng hồi cứu, tính lại metrics/P90, vẽ biểu đồ và tạo manifest/hash. Chúng có fit RF_compact cho riêng dự báo lưu sau mẫu cuối, đích 01/2024; không huấn luyện lại chuỗi dự báo lịch sử. Bước cuối kiểm checksum/hợp đồng trước khi cập nhật thí nghiệm trong snapshot và manifest workspace.

`MYTHO_MONTHLY_LAG0` tương ứng nhãn +5 ngày; `MYTHO_MONTHLY_LAG30` tương ứng +35 ngày. Lựa chọn RF_compact từ validation +5 ngày được giữ khi đánh giá độ nhạy +35 ngày. Dự báo lưu 01/2024 được tính lại là 27.903151 và 22.022199 mS/m, không phải dự báo hiện tại. Tên thư mục run giữ mốc 30/10; manifest ghi thời điểm tái tạo thật.

Ba lệnh này ghi artifact và snapshot cục bộ, không ghi PostgreSQL hoặc thay model RF 300 cây/năm biến của form trực tiếp. Không thay bằng `build_research_workspace.py --fit` khi mục tiêu chỉ là đóng gói RF_compact: builder tổng quát có thể tạo run và thay registry theo cấu hình riêng. Chi tiết thay đổi từng file, kiểm tra đã chạy và giới hạn: [bản cập nhật 01/11](cap_nhat_logic_va_tien_trinh_2026-11-01.md).

## Script thu thập và chuẩn hóa nguồn

Các script `fetch_mrc_public.py`, `fetch_public_research_data.py`, `collect_observation_archive.py` giữ nguồn, checksum và hồ sơ tải. Kiểm tra `--help` trước khi tải thêm. `normalize_v3_observations.py`, `audit_supplied_v3.py` và `inspect_observation_archive.py` phục vụ chuẩn hóa/kiểm toán; dữ liệu tiếp nhận chưa được coi là quan trắc đã xác minh.

`etl/etl_csv.py --help` mô tả chuẩn hóa CSV và tạo SQL. Dùng nguồn EC trong `data/raw/ec/mrc/`. Không dùng `master_timeseries.csv` lịch sử nếu chưa đối chiếu đúng header; phiên bản có thêm cột thủy triều không khớp hợp đồng ETL master cũ.

## Chức năng cống và độ mặn

```powershell
.venv\Scripts\python.exe run_gate_advisor.py --policy data/contracts/gate_policy.json --input data/contracts/gate_input.json
```

Các mẫu thiếu dữ liệu phải trả `INSUFFICIENT_DATA`, `recommendation=null`. Chức năng này lập danh sách thông tin cần bổ sung, không phát lệnh hoặc lịch vận hành. Chưa có căn cứ chuyển EC sang độ mặn, nên API trả trạng thái thiếu căn cứ, giá trị/unit/phương pháp/sai số là null; không có cột độ mặn suy diễn được ghi vào DB EC.

Trong giao diện, mục Hồ sơ cống có chế độ mô phỏng riêng. Nhập bốn số đo, thời điểm, hệ cao độ, cơ sở EC và giới hạn kịch bản; chọn lấy hoặc thoát nước rồi chạy. Nút Lưu nháp lưu cục bộ theo mã cống; Khôi phục nháp mở lại trên cùng trình duyệt. JSON xuất ra gồm đầu vào và quy trình kịch bản, chưa phải hồ sơ được phê duyệt. Xem [luồng trình bày](user-flow.md).

## Kiểm tra bàn giao

Kiểm thử hồi quy hiện tại:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
node --test tests/*.test.mjs frontend/src/features/gate-simulation-draft.test.js
npm.cmd --prefix frontend run build
```

Bộ kiểm thử chủ yếu dùng snapshot và client trong tiến trình. Hai test PostgreSQL chỉ chạy khi đặt `WEBGIS_TEST_PG_DSN` trỏ tới DB test riêng có PostGIS; không đặt biến này trỏ tới DB chứa dữ liệu thật. Xem [kiến trúc](architecture.md) và [kế hoạch triển khai](implementation-plan.md) để nắm cấu trúc mới và phạm vi nghiệm thu. [handover.md](handover.md) là bằng chứng lịch sử ngày 16/10, không phải kết quả kiểm tra phiên bản hiện tại.

Xem [bảo mật PostgreSQL và lưu lịch sử](database-security.md) về hai role DB, tài khoản cán bộ, audit và cách kiểm tra quyền.
