# Chạy và tái lập trên Windows

Thực hiện trong PowerShell tại gốc repository. Giữ `.venv` và `.venv-api` hiện có. Nếu máy nhận bàn giao chưa có Python environment, cài Python 3.12 và chạy `py -3.12 -m venv .venv` trước khi cài dependency.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-prototype.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.venv\Scripts\python.exe run_webgis.py --mode snapshot
```

Mở http://127.0.0.1:8000/research.html. Có thể đổi cổng bằng `--port 8016`. Phát triển frontend bằng `npm.cmd --prefix frontend run dev`; Vite chuyển `/api` tới backend cổng 8000.

## Chọn nguồn rõ ràng

- `snapshot`: đọc `data/research/workspace.json`, kiểm tra SHA-256 với `workspace_manifest.json`. Đây là quan trắc có nguồn và kết quả hồi cứu, không phải dữ liệu trực tiếp.
- `postgres`: đọc schema `webgis_research` qua tài khoản PG*. Không fallback nếu kết nối hoặc schema lỗi.
- `/index.html` và `/api/v1/health`, `/api/v1/stations` luôn truy cập DB thật. `/api/v1/app-health` chỉ xác nhận tiến trình, không chứng nhận DB.
- Tiếp nhận v3 luôn đọc tệp riêng; chưa nhập vào quan trắc hay huấn luyện, dù chọn chế độ PostgreSQL.

## PostgreSQL/PostGIS

Sao chép `.env.example` thành `.env` nếu chưa có; điền PGHOST, PGPORT, PGDATABASE, PGUSER và cấu hình mật khẩu cục bộ bằng PGPASSWORD hoặc PGPASSFILE. Không ghi mật khẩu vào báo cáo/Git. `run_webgis.py` nạp `.env`; lệnh uvicorn trực tiếp không tự nạp.

```powershell
.venv\Scripts\python.exe scripts/check_webgis_setup.py
.venv\Scripts\python.exe scripts/import_research_workspace.py
```

Lệnh import trên là dry-run, không xác nhận DB hoạt động. Trước khi ghi DB, người quản trị rà soát schema hiện hữu, quyền và bản sao lưu PostgreSQL. `sql/04_research_workspace.sql` định nghĩa schema nghiên cứu; các schema `public` nằm trong `sql/`. Không chạy bootstrap lên DB đã có dữ liệu.

Sau khi schema và tài khoản đã sẵn sàng:

```powershell
.venv\Scripts\python.exe scripts/import_research_workspace.py --apply
.venv\Scripts\python.exe run_webgis.py --mode postgres
```

## Tái lập khoa học và thu thập

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

## Kiểm tra bàn giao

Xem [handover.md](handover.md) để biết lệnh đã thực chạy, kết quả, giới hạn DB và đường dẫn khôi phục. File test tự động không còn trong bản bàn giao theo yêu cầu; QA dữ liệu, baseline và bằng chứng khoa học vẫn tồn tại.
