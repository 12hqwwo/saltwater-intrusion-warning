# WebGIS EC và hỗ trợ lập kế hoạch cống

Sản phẩm nghiên cứu dự báo **giá trị mẫu EC tháng kế tiếp tại từng trạm**, đối chiếu thực tế–dự báo, tra cứu nguồn và rà soát hồ sơ công trình. Phạm vi này không thay đổi tên đề tài trong văn bản chính thức.

## Chạy trên Windows

Từ gốc repository, dùng môi trường Python hiện có:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-prototype.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.venv\Scripts\python.exe run_webgis.py --mode snapshot
```

Mở http://127.0.0.1:8000/research.html. `snapshot` đọc tệp nghiên cứu có nguồn và kiểm tra checksum; không phải dữ liệu demo. `--mode postgres` đọc PostgreSQL/PostGIS, lỗi kết nối được báo rõ và không chuyển sang tệp. Trang `/index.html` luôn đọc PostgreSQL. Hồ sơ tiếp nhận v3 đọc từ tệp riêng, chưa nhập vào quan trắc hay huấn luyện.

## Dữ liệu và giới hạn

- 977 mẫu EC: 927 MRC tại Mỹ Tho/Tân Châu, 50 RIA2 tại 10 điểm. MRC giữ cờ nguồn chưa xác minh; chuỗi kết thúc năm 2023.
- Bốn thí nghiệm tháng: hai trạm × giả định độ trễ 0/30 ngày. Giữ train/validation/test theo thời gian, baseline, metrics, predictions và manifest. Kết quả hồi cứu không phải dự báo hiện tại.
- EC dùng mS/m. **Chưa đủ căn cứ ước tính độ mặn**: chưa xác định cơ sở EC25/phương pháp hiệu chuẩn, phạm vi và sai số phù hợp. Không dùng hệ số chuyển đổi tùy ý.
- Bản đồ hiển thị điểm có tọa độ; không tạo bề mặt mặn liên tục. Chưa đủ ngưỡng và số đo để phân loại nguy cơ hoặc định lượng độ tin cậy.
- Danh mục bốn cống có nguồn nhưng thiếu tọa độ đã xác minh, quan hệ thủy lực, số đo hai phía và quy trình. Công cụ chỉ rà soát hồ sơ lập kế hoạch; không tính giờ đóng/mở.

## Tái lập và kiểm toán

```powershell
.venv\Scripts\python.exe scripts/audit_research_data.py
.venv\Scripts\python.exe scripts/build_research_workspace.py --fit
.venv\Scripts\python.exe scripts/import_research_workspace.py
.venv\Scripts\python.exe scripts/check_webgis_setup.py
```

Lệnh import mặc định chỉ kiểm tra, không ghi DB. Hướng dẫn cấu hình/nhập DB: [docs/run_guide.md](docs/run_guide.md). Kết quả làm sạch, các kiểm tra và khôi phục: [docs/handover.md](docs/handover.md).

## Cấu trúc

```text
backend/                 FastAPI: quan trắc DB, nghiên cứu, tiếp nhận
frontend/                WebGIS và biểu đồ hiện tại
run_webgis.py            Trình chạy Windows
run_monthly_ec.py        Đánh giá dự báo mẫu EC tháng
run_gate_advisor.py      Rà soát hồ sơ kế hoạch cống
run_station_gate_link.py Kiểm tra bằng chứng liên kết trạm–cống
scripts/                 Thu thập, chuẩn hóa, kiểm toán, xây/nạp dữ liệu
etl/, pipelines/         ETL có QA và đánh giá baseline
sql/                     Schema, migration và truy vấn kiểm toán
config/                  Cấu hình nguồn dữ liệu
 data/raw/, external/    Nguồn gốc và hồ sơ tải/biến đổi
 data/research/          Snapshot, registry và khu vực tiếp nhận riêng
 data/archive/           Bằng chứng nghiên cứu lịch sử, không nạp tự động
runs/local_ec_backtest/  Metrics, predictions, split và manifest
 docs/                   Hướng dẫn và báo cáo khoa học
```

Các phân tích cũ được giữ để truy vết; không dùng làm chứng nhận chất lượng mô hình hiện tại. Bộ kiểm thử phần mềm đã chuyển ra bản sao lưu ngoài repository theo yêu cầu bàn giao; kiểm tra chất lượng dữ liệu và mã đánh giá khoa học vẫn được giữ.
