# WebGIS và dự báo EC theo tháng

[Bản đồ tài liệu, dữ liệu và kết quả nghiên cứu](docs/README.md) giúp tìm đúng tệp trước khi chỉnh sửa hoặc dọn dẹp.

Ứng dụng tiểu luận kết hợp WebGIS và **dự báo EC tháng bằng mô hình đa biến**. Luồng chính: chọn trạm/tháng → tải lượng mưa, nhiệt độ, gió và chu kỳ mùa vụ → chạy Random Forest đã huấn luyện → xem EC dự báo, đầu vào, sai số lịch sử và vị trí trên bản đồ → xuất JSON/CSV.

## Chạy trên Windows

Từ gốc repository, dùng môi trường Python hiện có. Chuẩn bị dependency khi cần:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-prototype.txt
npm.cmd --prefix frontend ci
.venv\Scripts\python.exe scripts/apply_dss_storage.py --apply
.venv\Scripts\python.exe scripts/setup_security.py --apply
.\start.ps1
```

Mở http://127.0.0.1:8000/workspace.html. `start.ps1` build giao diện rồi chạy một máy chủ phục vụ cả API và web; Ctrl+C để dừng. Mặc định dùng PostgreSQL; dùng `-Mode snapshot` để xem bộ tệp, `-Port 8016` để đổi cổng hoặc `-SkipBuild` khi đã có bản build mới nhất.

`snapshot` đọc tệp có nguồn và kiểm tra checksum. `postgres` đọc trạm và EC trực tiếp từ các bảng `public` hiện có, mỗi trạm chọn một phiên bản RAW_EC; lỗi DB được báo rõ. Lịch sử PostgreSQL đã nằm ngay trong mục Quan trắc; `/index.html` giữ cho liên kết cũ. Thí nghiệm, danh mục cống, hồ sơ tiếp nhận và ước tính khí tượng đọc từ bộ tệp riêng; phần Tổng quan ghi rõ nguồn. Trang `/research.html` chuyển tới workspace.

## Luồng sử dụng

Mục **Dự báo EC đa biến** chạy suy luận thật từ model đã lưu; không huấn luyện theo request và không lấy kết quả từ CSV ước tính cũ. Dùng ERA5 tháng `t−2` để dự báo EC tháng `t`; ví dụ tháng 11/2026 dùng khí tượng tháng 9/2026. Mô hình khí tượng không yêu cầu EC trễ mới để chạy. Chuỗi EC mới vẫn cần để đánh giá chất lượng dự báo ở giai đoạn hiện tại. [Chi tiết mô hình và cách cập nhật](docs/multivariate-forecast.md).

1. **Tổng quan:** xem phạm vi dữ liệu, số trạm và tình trạng nguồn.
2. **Quan trắc:** chọn trạm → lọc ngày → xem bản đồ, biểu đồ, nguồn → xuất CSV. Nhập ngưỡng EC hoặc chọn ví dụ từ danh mục PostgreSQL để đổi màu điểm và vẽ đường đối chiếu. Các ví dụ chưa được xác nhận là ngưỡng cây trồng/cấp nước. Tra cứu PostgreSQL có chọn nguồn, trạm, phiên bản, QA và phân trang ngay trong cùng mục.
3. **Dự báo EC đa biến:** chọn trạm và tháng → nạp khí tượng hoặc cung cấp đầu vào đúng đơn vị → chạy dự báo → xem EC, độ quan trọng biến, kỳ huấn luyện và sai số → xem trên bản đồ / tải JSON hoặc CSV. Có bảng so sánh các lượt chạy trong phiên và chức năng chạy lại, lưu, lọc lịch sử trong PostgreSQL. Các mô hình EC trễ và kết quả hồi cứu cũ nằm trong phần tham khảo riêng.
4. **Chất lượng dữ liệu:** xem nguồn, độ phủ và hồ sơ tiếp nhận chưa xác minh.
5. **Hồ sơ cống:** chọn công trình → nhập EC, mực nước và ngưỡng → mô phỏng INTAKE/DRAIN → xem điều kiện đạt/chặn/thiếu → lưu và khôi phục nháp trên trình duyệt hoặc PostgreSQL, nhập/xuất JSON. Có thể đính kèm dự báo tháng để tham khảo riêng; dự báo không thay số đo hai phía cống. Chưa có phê duyệt trực tuyến.

Lưu trữ bổ trợ sử dụng schema `dss_reference`, không sửa bảng quan trắc `public`. Xem [cấu hình và migration DSS](docs/dss-storage.md). Nếu chưa cấu hình kho DSS, dự báo, tải JSON/CSV và bản nháp trình duyệt vẫn hoạt động.

## Dữ liệu và giới hạn

- Snapshot có 977 mẫu EC: 927 MRC tại Mỹ Tho/Tân Châu, 50 RIA2 tại 10 điểm. PostgreSQL hiện có 927 mẫu tại 2 trạm. Chuỗi MRC kết thúc năm 2023; cờ chất lượng nguồn được giữ nguyên.
- Bốn thí nghiệm tháng: hai trạm × giả định độ trễ 0/30 ngày. Giữ train/validation/test theo thời gian, baseline, metrics, predictions và manifest. Kết quả hồi cứu không phải dự báo hiện tại.
- EC dùng mS/m. **Chưa đủ căn cứ ước tính độ mặn**: chưa xác định cơ sở EC25/phương pháp hiệu chuẩn, phạm vi và sai số phù hợp. Không dùng hệ số chuyển đổi tùy ý.
- Bản đồ hiển thị điểm có tọa độ; không tạo bề mặt mặn liên tục. Chưa đủ ngưỡng và số đo để phân loại nguy cơ hoặc định lượng độ tin cậy.
- Danh mục bốn cống có nguồn; mô phỏng dùng ngưỡng tự nhập, không tự coi là quy trình được phê duyệt. Lớp bản đồ và sàng lọc trạm ứng viên dùng tọa độ thật khi có trong PostgreSQL; danh mục DB hiện chưa có cống.

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
backend/api/             HTTP routes của workspace
backend/services/        Ca sử dụng quan trắc, kết quả tháng, hồ sơ
backend/repositories/    Đọc snapshot, artifact và PostgreSQL
backend/domain/          Hợp đồng dữ liệu và quy tắc độc lập HTTP
backend/research.py      Lớp tương thích API/import cũ
frontend/src/app/        Khởi tạo và điều hướng ứng dụng
frontend/src/features/   Quan trắc, dự báo, ước tính, hồ sơ, tổng quan
frontend/src/shared/     API client, biểu đồ chuỗi thời gian, ngưỡng và tiện ích
frontend/workspace.html Trang làm việc chính
tests/                   Kiểm thử hồi quy API và luồng dữ liệu
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

Các phân tích lịch sử không dùng làm chứng nhận chất lượng mô hình hiện tại. Nghiên cứu feature 19/10 chưa thay đổi bộ mô hình đang phục vụ; thư mục kết quả này hiện không còn trong checkout, nên cần có đủ artifact trước khi tích hợp.

## Kiểm tra và tài liệu

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
node --test tests/frontend_api.test.mjs
npm.cmd --prefix frontend run build
```

Kiểm thử dùng snapshot và client trong tiến trình, không ghi DB hoặc huấn luyện lại. [Kiến trúc](docs/architecture.md) giải thích trách nhiệm từng lớp; [kế hoạch triển khai](docs/implementation-plan.md) ghi phạm vi khả thi, tiêu chí nghiệm thu và điều kiện để phát triển tiếp. [Hướng dẫn chạy](docs/run_guide.md) mô tả cấu hình môi trường và chế độ dữ liệu.

[Bảo mật cơ sở dữ liệu](docs/database-security.md): hai role đọc/ghi riêng, audit và lưu dự báo/nháp trực tiếp, không cần màn hình đăng nhập.
