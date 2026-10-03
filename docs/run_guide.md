# Hướng dẫn chạy từng bước

Mở terminal tại thư mục gốc dự án trong Antigravity. Các lệnh py dùng Python Launcher trên Windows; nếu không có py, dùng python hoặc .\.venv\Scripts\python.exe đang hoạt động.

## 1. Kiểm tra bộ dữ liệu hiện có

```powershell
py scripts/audit_local_data.py
```

Dùng thư viện chuẩn Python và hàm validation ETL đã có. Không cần cài requirements.txt, không cần mật khẩu, không kết nối hoặc ghi database.

Chương trình in một thư mục mới trong runs/local_audit/, gồm:

- audit_report.md: báo cáo dễ đọc.
- audit_report.json: số đếm, hash, độ phủ và chi tiết kiểm tra.
- stations_from_kml.geojson: hai trạm nếu cả hai KML đạt kiểm tra mã trạm/tọa độ.

PASS_WITH_LIMITATIONS cùng failures = 0 nghĩa là các kiểm tra file đạt, còn các phần ngoài phạm vi như PostgreSQL, nguồn ranh giới và phương pháp backtest. Không có nghĩa toàn bộ WebGIS đã hoàn thành. Nếu FAILED, đọc các dòng FAIL trước khi dùng dữ liệu cho bước tiếp theo.

Bộ kết quả bàn giao nằm tại runs/local_audit/review_20261002/. Mỗi lần chạy mặc định tạo thư mục riêng.

## 2. Kiểm tra mã liên quan khi có thay đổi

```powershell
py -m unittest discover -s etl/tests -v
py -m unittest discover -s scripts/tests -v
```

Đợt này đã chạy đạt lần lượt 7 và 4 test. Không cần làm lại kịch bản nhập lặp/rollback database đã đạt để dùng bản cập nhật.

## 3. Xem hai trạm trong QGIS

Kéo stations_from_kml.geojson từ thư mục kết quả vào QGIS; dùng site_name để đặt nhãn. Bảng thuộc tính có site_code, location_status, location_reference và source_sha256.

Tọa độ giữ nguyên KML, trạng thái REPORTED. Xem GeoJSON không tự nhập tọa độ vào PostgreSQL.

## 4. Đối chiếu DB trước API đầu tiên

Trong pgAdmin/DBeaver, kết nối database chính dongthap_gis, mở sql/checks/03_webgis_readiness.sql. File chỉ đọc dữ liệu và đặt giới hạn thời gian khi chạy toàn bộ; không nạp/xóa/sửa dữ liệu. Nếu Query Tool chỉ hiện kết quả SELECT cuối, bôi đen và chạy riêng từng khối SELECT W01–W05 để lưu từng bảng. Khối W02 bắt đầu từ WITH observation_summary.

Kết quả gồm tên database; trạm và tọa độ/nguồn/độ phủ EC; snapshot; ranh giới; số cống. Nếu đã có kết quả tương đương từ 00_kiem_tra_hien_trang.sql thì dùng lại, không cần chạy lại chỉ để tạo bằng chứng trùng.

File sql/01_toa_do_tram_MyTho_TanChau.sql kết thúc bằng ROLLBACK: chạy mà chưa đổi bước kết thúc sẽ không lưu tọa độ. Trước khi định nhập lại, xem dữ liệu hiện tại ở bước trên.

## 5. Các lệnh thuộc chặng sau

Thí nghiệm cũ:

```powershell
.\.venv\Scripts\python.exe run_forecast.py
```

Lệnh ghi vào runs/forecast_exp/; giữ bản kết quả trước nếu muốn so sánh. Phương pháp đánh giá còn các điểm cần sửa trong current_state.md.

Tổng hợp dữ liệu:

```powershell
.\.venv\Scripts\python.exe data_processing/process_data.py
```

Chạy tại thư mục gốc. Lệnh ghi đè master CSV/parquet; không cần chạy lại trong đợt này. Cần rà soát GloFAS và metadata trước khi mở rộng mô hình.

frontend/ chưa có mã giao diện nên các script npm chưa tạo thành WebGIS chạy được. API và trang bản đồ thuộc chặng tiếp theo.
