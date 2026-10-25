# Chạy và tái lập trên Windows

Thực hiện trong PowerShell tại gốc repository. Giữ `.venv` và `.venv-api` hiện có. Nếu máy nhận bàn giao chưa có Python environment, cài Python 3.12 và chạy `py -3.12 -m venv .venv` trước khi cài dependency.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-prototype.txt
npm.cmd --prefix frontend ci
.venv\Scripts\python.exe scripts/apply_dss_storage.py --apply
.venv\Scripts\python.exe scripts/setup_security.py --apply
.\start.ps1
```

Mở http://127.0.0.1:8000/workspace.html. Script mặc định chọn PostgreSQL, kiểm tra build thành công rồi chạy máy chủ ngay trong terminal hiện tại; Ctrl+C để dừng. Có thể dùng `.\start.ps1 -Mode postgres -Port 8016`. Chỉ dùng `-SkipBuild` khi bản build đã cập nhật; script không báo khởi động thành công trước khi Uvicorn sẵn sàng.

Có thể chạy từng bước:

```powershell
npm.cmd --prefix frontend run build
.venv\Scripts\python.exe run_webgis.py --mode postgres --port 8000
```

Phát triển frontend bằng `npm.cmd --prefix frontend run dev`; Vite chuyển `/api` tới backend cổng 8000. Chạy backend bằng `.venv\Scripts\python.exe run_webgis.py --mode postgres --api-only` nếu chưa cần build giao diện. Trong Vite mở `/workspace.html`; `/index.html` là trang lịch sử PostgreSQL. Trang cũ `/research.html` chuyển tới workspace.

## Chọn nguồn rõ ràng

- `snapshot`: đọc `data/research/workspace.json`, kiểm tra SHA-256 với `workspace_manifest.json`. Đây là quan trắc có nguồn và kết quả hồi cứu, không phải dữ liệu trực tiếp.
- `postgres`: quan trắc đọc `public.measurement_site`, `public.source_dataset`, `public.conductivity_observation` qua tài khoản WEBGIS_DB_USER chỉ đọc. Mỗi trạm chọn RAW_EC được nhập gần nhất (hoặc phiên bản được ghim); không trộn phiên bản. Kết quả mô hình và danh mục cống vẫn đọc bộ tệp có manifest. Không fallback khi DB lỗi.
- `/index.html` và `/api/v1/health`, `/api/v1/stations` luôn truy cập DB thật. `/api/v1/app-health` chỉ xác nhận tiến trình, không chứng nhận DB.
- Tiếp nhận v3 luôn đọc tệp riêng; chưa nhập vào quan trắc hay huấn luyện, dù chọn chế độ PostgreSQL.
- Ước tính EC từ khí tượng 2024–2026 luôn đọc artifact tệp. Đây là ước tính hồi cứu dùng khí tượng cùng tháng, không phải dự báo hiện tại hoặc căn cứ vận hành cống.
- API chính của workspace là `/api/v1/workspace`; `/api/v1/research` vẫn hoạt động để giữ tương thích.

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
node --test tests/frontend_api.test.mjs
npm.cmd --prefix frontend run build
```

Bộ kiểm thử dùng snapshot và client trong tiến trình; không truy cập DB để thay đổi dữ liệu. Xem [kiến trúc](architecture.md) và [kế hoạch triển khai](implementation-plan.md) để nắm cấu trúc mới và phạm vi nghiệm thu. [handover.md](handover.md) là bằng chứng lịch sử ngày 16/10, không phải kết quả kiểm tra phiên bản hiện tại.

Xem [bảo mật PostgreSQL và lưu lịch sử](database-security.md) về hai role, audit, API key tùy chọn và cách kiểm tra quyền.
