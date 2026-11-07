# WebGIS và dự báo EC theo tháng

[Bản đồ tài liệu, dữ liệu và kết quả nghiên cứu](docs/README.md) giúp tìm đúng tệp trước khi chỉnh sửa hoặc dọn dẹp.

[Cập nhật logic và tiến trình 01/11/2026](docs/cap_nhat_logic_va_tien_trinh_2026-11-01.md) ghi các file đã sửa, luồng RF_compact, artifact/kiểm thử và nội suy màu sông. [Hiện trạng](docs/current_state.md) phân biệt phần vừa kiểm tra với các bằng chứng DB/trình duyệt cũ.

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

Mở http://127.0.0.1:8000/ để vào trang Tổng quan mới; `/workspace.html` mở cùng không gian làm việc. `start.ps1` build giao diện rồi chạy một máy chủ phục vụ cả API và web; Ctrl+C để dừng. Mặc định dùng PostgreSQL; dùng `-Mode snapshot` để xem bộ tệp, `-Port 8016` để đổi cổng hoặc `-SkipBuild` khi đã có bản build mới nhất.

Để chạy đúng bản `TinBranch` có trạm Mỹ Thuận với thiết lập PostgreSQL hiện có, chạy `start-tinbranch.ps1 -SettingsRoot 'D:\Study\TLCN' -Port 8000` từ worktree giao diện này. Lệnh dựng giao diện mới, dùng backend và snapshot của `TinBranch`, đọc cấu hình PostgreSQL của checkout chính; dừng máy chủ cũ trên cổng 8000 trước khi chạy. Dùng `-SkipBuild` khi đã dựng giao diện.

`snapshot` đọc tệp có nguồn và kiểm tra checksum. `postgres` đọc trạm và EC trực tiếp từ các bảng `public` hiện có, mỗi trạm chọn một phiên bản RAW_EC; lỗi DB được báo rõ. Lịch sử PostgreSQL đã nằm ngay trong mục Quan trắc; `/index.html` chuyển tới trang Tổng quan. Thí nghiệm, danh mục cống, hồ sơ tiếp nhận và ước tính khí tượng đọc từ bộ tệp riêng; phần Tổng quan ghi rõ nguồn. Trang `/research.html` chuyển tới workspace.

## Luồng sử dụng

Mục **Dự báo EC đa biến** chạy suy luận thật từ model đã lưu; không huấn luyện theo request và không lấy kết quả từ CSV ước tính cũ. Dùng ERA5 tháng `t−2` để dự báo EC tháng `t`; ví dụ tháng 11/2026 dùng khí tượng tháng 9/2026. Mô hình khí tượng không yêu cầu EC trễ mới để chạy. Chuỗi EC mới vẫn cần để đánh giá chất lượng dự báo ở giai đoạn hiện tại. [Chi tiết mô hình và cách cập nhật](docs/multivariate-forecast.md).

1. **Tổng quan:** xem phạm vi dữ liệu, số trạm và tình trạng nguồn; mở nhanh mô phỏng mùa khô 04/2024, mùa mưa 10/2022, ngưỡng mẫu sầu riêng hoặc công cụ dự báo. Nếu thiếu đúng tháng, dòng thời gian chọn tháng gần nhất và hiển thị tháng thực sự đang xem.
2. **Quan trắc:** chọn trạm → lọc ngày → xem bản đồ, biểu đồ, nguồn → xuất CSV. Nhập ngưỡng EC hoặc chọn ví dụ từ danh mục PostgreSQL để đổi màu điểm và vẽ đường đối chiếu. Các ví dụ chưa được xác nhận là ngưỡng cây trồng/cấp nước. Tra cứu PostgreSQL có chọn nguồn, trạm, phiên bản, QA và phân trang ngay trong cùng mục.
3. **Dự báo EC đa biến:** chọn trạm và tháng → nạp khí tượng hoặc cung cấp đầu vào đúng đơn vị → chạy dự báo → xem EC, độ quan trọng biến, kỳ huấn luyện và sai số → xem trên bản đồ / tải JSON hoặc CSV. Có bảng so sánh các lượt chạy trong phiên và chức năng chạy lại, lưu, lọc lịch sử trong PostgreSQL. Các mô hình EC trễ và kết quả hồi cứu cũ nằm trong phần tham khảo riêng.
4. **Chất lượng dữ liệu:** xem nguồn, độ phủ và hồ sơ tiếp nhận chưa xác minh.
5. **Hồ sơ cống:** chọn công trình → nhập EC, mực nước và ngưỡng → mô phỏng INTAKE/DRAIN → xem điều kiện đạt/chặn/thiếu → lưu và khôi phục nháp trên trình duyệt hoặc PostgreSQL, nhập/xuất JSON. Có thể đính kèm dự báo tháng để tham khảo riêng; dự báo không thay số đo hai phía cống. Chưa có phê duyệt trực tuyến.

Bản đồ có lớp mô phỏng trục Sông Tiền, thống kê trạng thái cống theo cặp ngưỡng EC đang chọn và 10 tuyến kênh có hình học đi qua cống. Đoạn từ sông tới cống dùng mức cảnh báo theo EC mô phỏng ngoài cống; đoạn sau cống là nét đứt xám vì chưa có EC nội kênh. Chọn nhánh hoặc cống để xem chi tiết; bấm vùng trống để tra cứu đoạn sông, cống và trạm gần nhất. Thông tin nước thuộc đoạn sông lân cận, không phải phép đo tại điểm chọn.

Lưu trữ bổ trợ sử dụng schema `dss_reference`, không sửa bảng quan trắc `public`. Xem [cấu hình và migration DSS](docs/dss-storage.md). Nếu chưa cấu hình kho DSS, dự báo, tải JSON/CSV và bản nháp trình duyệt vẫn hoạt động.

## Dữ liệu và giới hạn

- Snapshot `TinBranch` có 1.428 mẫu EC: 1.378 mẫu MRC tại Tân Châu, Mỹ Thuận, Mỹ Tho và 50 mẫu RIA2 tại 10 điểm. PostgreSQL đang phục vụ 1.378 mẫu tại ba trạm MRC; Mỹ Thuận có 451 mẫu đã đồng bộ. Chuỗi MRC kết thúc năm 2023; cờ chất lượng nguồn được giữ nguyên.
- Bốn thí nghiệm tháng tại hai trạm, có baseline, metrics, predictions và manifest. Hai định danh Mỹ Tho `LAG0`/`LAG30` hiện đóng gói RF_compact với giả định nhãn khả dụng sau cuối tháng **5/35 ngày**; các thí nghiệm Tân Châu giữ cấu hình riêng đã lưu. Kết quả hồi cứu không phải dự báo hiện tại.
- EC quan trắc, dự báo và các mức cảnh báo trên bản đồ dùng mS/m. Giao diện không dùng mốc độ mặn g/L để tô màu; các ngưỡng EC mẫu chưa được hiệu chuẩn tại địa phương và không xác nhận nước tưới hoặc sinh hoạt.
- Bản đồ phân biệt ba trạm MRC có vị trí trong PostgreSQL với 10 điểm RIA2 dùng tọa độ tham khảo từ nguồn khi bật lớp tương ứng; tọa độ tham khảo không trở thành tọa độ DB đã xác minh. Các đoạn sông là nội suy một chiều qua Tân Châu, Mỹ Thuận, Mỹ Tho, không phải bề mặt mặn đo liên tục hoặc mô hình thủy động lực.
- Hồ sơ nghiên cứu bốn cống và lớp công trình đầu mối phục vụ mô phỏng là các phạm vi khác nhau; số cống hiển thị lấy từ khung API đang xem. Trạng thái trên bản đồ được tính từ EC mô phỏng và ngưỡng đang chọn, không phản ánh lệnh vận hành thật. Ngưỡng mẫu sầu riêng 50/80, cây có múi 100/150 và lúa 120/200 mS/m chưa phải tiêu chuẩn tưới đã xác nhận. Không suy ra mọi cống cùng thuận lợi hoặc cùng ngăn mặn nếu khung dữ liệu không cho kết quả đó.

## Tái lập và kiểm toán

```powershell
.venv\Scripts\python.exe scripts/audit_research_data.py
.venv\Scripts\python.exe scripts/build_research_workspace.py --fit
.venv\Scripts\python.exe scripts/import_research_workspace.py
.venv\Scripts\python.exe scripts/check_webgis_setup.py
```

Lệnh import mặc định chỉ kiểm tra, không ghi DB. Hướng dẫn cấu hình/nhập DB: [docs/run_guide.md](docs/run_guide.md). Kết quả làm sạch, các kiểm tra và khôi phục: [docs/handover.md](docs/handover.md).

Để tái tạo đúng hai run RF_compact đã sửa, dùng các wrapper đóng gói rồi cập nhật workspace theo [hướng dẫn riêng](docs/run_guide.md#tái-tạo-artifact-rf_compact-sau-rà-soát-01112026). Builder tổng quát với `--fit` ở trên chạy lại thí nghiệm và có thể thay registry.

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
node --test tests/*.test.mjs
npm.cmd --prefix frontend run build
```

Kiểm thử dùng snapshot và client trong tiến trình, không ghi DB hoặc huấn luyện lại. [Kiến trúc](docs/architecture.md) giải thích trách nhiệm từng lớp; [kế hoạch triển khai](docs/implementation-plan.md) ghi phạm vi khả thi, tiêu chí nghiệm thu và điều kiện để phát triển tiếp. [Hướng dẫn chạy](docs/run_guide.md) mô tả cấu hình môi trường và chế độ dữ liệu.

[Bảo mật cơ sở dữ liệu](docs/database-security.md): hai role đọc/ghi riêng, audit và lưu dự báo/nháp trực tiếp, không cần màn hình đăng nhập.
