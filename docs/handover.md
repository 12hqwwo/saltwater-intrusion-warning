# Biên bản làm sạch repository — 16/10/2026

Đã chỉnh sửa trực tiếp repository; không commit/push, không tạo dự án thay thế. Phạm vi là dự báo **giá trị mẫu EC tháng kế tiếp**, không phải EC liên tục trung bình cả tháng. Không đổi tên đề tài trong đề cương gốc.

## Giữ và tổ chức

- FastAPI, PostgreSQL/PostGIS, hai trang frontend hiện có, bản đồ trạm, biểu đồ EC và đối chiếu dự báo.
- Toàn bộ 273 tệp nguồn ban đầu dưới `data/raw` và `data/external` đã đối chiếu SHA-256, không đổi nội dung. Giữ URL, manifest, lịch sử biến đổi, dữ liệu tiếp nhận chưa xác minh và báo cáo nghiên cứu.
- `run_monthly_ec.py`, baseline, phân chia train/validation/test theo thời gian; `runs/local_ec_backtest` giữ metrics, predictions, manifest và model artifacts. Không huấn luyện lại trong lượt dọn này.
- ETL/QA, thu thập và chuẩn hóa dữ liệu, schema SQL và truy vấn kiểm toán. `sql/checks` là kiểm toán dữ liệu vận hành, không phải fixture kiểm thử phần mềm.
- `.venv`, `.venv-api`, cấu hình `.env` và PostgreSQL được giữ nguyên. Không có lệnh ghi DB đã chạy.
- Dữ liệu và kết quả riêng của bản tham khảo được giữ trong `data/archive/reference_evidence`; `relocation_manifest.json` có 439 ánh xạ đến nội dung giữ lại hoặc bản trùng checksum. Đề cương `decuong.txt` giữ nguyên byte. Bằng chứng kết quả giờ cũ được lưu riêng trong `data/archive/retired_hourly_evidence`, không được ứng dụng đọc.

## Loại bỏ và sửa tham chiếu

Danh mục khôi phục ghi **733 đường dẫn tệp gốc** đã loại bỏ (gồm tệp sinh tự động và bản trùng; không phải số file Git tracked).

- API, trang và JavaScript replay; runner thí nghiệm Sơn Đốc/dự báo giờ.
- Bản dự án `WebGIS_DongThap_Step08` sau đối chiếu hợp nhất và bảo toàn bằng chứng riêng.
- Script tạo dữ liệu giả và dữ liệu synthetic; script debug/tải cấu hình một lần, patch cũ, ảnh thử giao diện, cache ngoài môi trường Python, log tạm và build cũ. Build mới đã tạo lại.
- Các thư mục test phần mềm tại backend, frontend, scripts, ETL, gốc repo; SQL bootstrap DB test và dependency test-only. Kết quả kiểm thử chuyển ra bản sao lưu. Không xóa `test_predictions` hoặc split test của nghiên cứu.
- Bỏ npm script test và các thư viện frontend không được import (Bootstrap, jQuery, jQuery UI, layer switcher); lockfile cập nhật. Dependency API khớp phiên bản đã thực chạy trong `.venv`.
- README/hướng dẫn hiện tại đã rút gọn; tài liệu lịch sử được đánh dấu không dùng làm hướng dẫn chạy. Đường dẫn lịch sử trong bằng chứng/manifest giữ để truy vết, không phải import hoặc route đang hoạt động.
- Công cụ cống chuyển sang rà soát kế hoạch: checklist 8 mục, không tính lịch đóng/mở. API và UI tách EC khỏi trạng thái độ mặn ước tính; chưa đủ cơ sở thì value/method/uncertainty là null.
- `.gitignore` giữ bí mật, environment, build/cache ngoài Git; không còn bỏ qua toàn bộ scientific runs, dữ liệu nguồn hoặc GIS cần bàn giao.

## Sao lưu và khôi phục

Bản sao lưu nằm ngoài repository:

`C:\Users\TOAN TIEN COMPUTER\.codex\visualizations\2026\10\16\01a14295-ce8b-7451-933b-7b285387645f\repository-handover-backup-20261016`

- `files/`: snapshot 1.254 tệp trước chỉnh sửa, không chứa .env hay môi trường Python/node_modules.
- `removal-manifest.json`: đường dẫn gốc, relative_path, SHA-256 và lý do từng tệp loại bỏ; checksum đã kiểm tra lại.
- `manifest.json`, `git-status-before.txt`, `git-diff-before.patch`: trạng thái ban đầu, gồm thay đổi chưa commit.
- `RESTORE.md`: khôi phục từng tệp vào thư mục mới để so sánh trước khi ghi trở lại.
- Log kiểm thử gốc, lần lỗi sandbox, lần chạy lại và bản kiểm thử thích nghi nằm tại đây.

Hai tệp `minh_chung_tuan06_20261010_223956/MC01_MRC_*` đã ở trạng thái deleted từ trước khi bắt đầu; lượt dọn không tạo ra việc xóa đó. Không có nội dung .env hoặc mật khẩu trong báo cáo.

## Cấu trúc sau dọn

```text
backend/                         API dữ liệu thật và nghiên cứu
frontend/                        WebGIS; dist sinh bằng build
config/, sql/                    Cấu hình, schema, migration, kiểm toán
scripts/, etl/, pipelines/       Thu thập, QA, chuẩn hóa, nhập, baseline
 data/raw/, data/external/       Nguồn và hồ sơ tải
 data/research/                  Snapshot, registry, tiếp nhận riêng
 data/archive/                   Bằng chứng lịch sử; không nạp tự động
runs/local_ec_backtest/          Kết quả khoa học có thể tái lập
notebooks/, data_processing/     Phân tích kế thừa để truy vết
 docs/                          Hướng dẫn và báo cáo
run_webgis.py                    Chạy ứng dụng Windows
run_monthly_ec.py                Đánh giá mẫu EC tháng
run_gate_advisor.py              Rà soát kế hoạch công trình
run_station_gate_link.py         Kiểm tra bằng chứng đại diện trạm–cống
```

## Các kiểm tra thực sự đã chạy

| Kiểm tra | Kết quả và giới hạn |
|---|---|
| Frontend test trước xóa | 22/22 đạt; `frontend-tests.txt` ngoài repo |
| Mô hình/pipeline trước xóa | 26/26 đạt sau chuyển thư mục tạm khỏi vùng sandbox bị từ chối; `tests-retry.txt` |
| Audit scripts trước xóa | 7/7 đạt; `scripts-tests-retry.txt` |
| ETL legacy | Ban đầu 7 lỗi đường dẫn cũ; chạy với đường dẫn nguồn hiện tại đạt 5/7, còn 2 lỗi schema master thêm `tide_max_m`. Không tự bỏ cột hoặc sửa nguồn để làm test đạt |
| API gốc | Bị treo trong sandbox trước xóa; chạy từ bản sao lưu ngoài sandbox sau dọn đạt 35/36, một kỳ vọng checklist 9 mục đã lỗi thời |
| API theo phạm vi mới | 36/36 đạt; bản kiểm tra ngoài repo chỉ sửa kỳ vọng checklist thành 8. Bản gốc sao lưu không thay đổi |
| `npm --prefix frontend run build` | Đạt; 218 modules; chỉ có index/research entry point |
| `audit_research_data.py` | Đạt: 73 chuỗi, 148 tệp raw; MRC 464 + 463 bản ghi, không lệch giá trị khi đối chiếu nguồn |
| `import_research_workspace.py` | Dry-run `VALIDATED_NO_DB_WRITE`: 8 nguồn, 12 điểm, 977 quan trắc, 4 cống, 4 thí nghiệm; không gọi là kiểm thử ghi DB |
| `check_webgis_setup.py` ngoài sandbox | PostgreSQL thật kết nối được, có PostGIS và schema nghiên cứu; transaction health chỉ đọc |
| HTTP snapshot và PostgreSQL | Cả hai bộ thu minh chứng đều không lỗi HTTP; chế độ postgres đọc 977 mẫu. Xem JSON trong `docs/reports/handover_20261016/` |
| Route loại bỏ | `/api/v1/replay` và `/replay.html` trả 404; `/research.html`, `/index.html` trả 200 |
| Hồ sơ cống | Trả `INSUFFICIENT_DATA`, checklist 8 mục, recommendation và actuator_command null |
| Trình duyệt | Mở trang, thấy bản đồ OSM và trạm; chọn Mỹ Tho, chuyển thí nghiệm Tân Châu trễ 30 ngày, chọn cống Đồng Tiến; biểu đồ/checklist có dữ liệu; nút kiểm tra PostgreSQL xác nhận kết nối, console không có lỗi tại thời điểm kiểm tra |

Các lỗi kết nối do sandbox và phiên máy chủ hết hạn đã được giữ trong log, không tính là kết quả thành công. Lượt duyệt quyền bổ sung từng bị chặn vì hạn mức; sau khi tiếp tục, kiểm tra HTTP PostgreSQL đã chạy thành công. Không kiểm tra nạp DB thật, không sửa dữ liệu DB, không huấn luyện lại bốn mô hình trong lượt này.

## Chạy Windows

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-prototype.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.venv\Scripts\python.exe run_webgis.py --mode snapshot
```

Mở http://127.0.0.1:8000/research.html. Đổi sang `--mode postgres` để đọc DB đã cấu hình; không fallback. Chi tiết tại [run_guide.md](run_guide.md).

## Còn thiếu

Chưa có dự báo hiện tại từ dữ liệu đủ mới; MRC kết thúc 2023, RIA2 chỉ 5 đợt/điểm. Chưa có phương pháp quy đổi EC–độ mặn phù hợp, EC25/hiệu chuẩn và sai số. Chưa đủ ngưỡng/số đo để phân loại nguy cơ, chưa có độ tin cậy định lượng hoặc bản đồ mặn liên tục. Thiếu tọa độ cống xác minh, quan hệ thủy lực, số đo hai phía và quy trình công trình. 890 giá trị v3 còn đang rà soát. Contract ETL master lịch sử còn khác header dữ liệu phân tích. Đây là bàn giao repository đã làm sạch, không phải chứng nhận đồ án hoàn thiện hay mô hình đủ điều kiện vận hành.
