# Saltwater Intrusion Warning / Phân tích dữ liệu Xâm nhập mặn ĐBSCL

Dự án thu thập và hợp nhất các dữ liệu thủy văn, khí tượng và độ mặn (Conductivity) tại ĐBSCL (trọng tâm là 2 trạm Tân Châu và Mỹ Tho). Mục lực cuối cùng là kết hợp toàn bộ features vào một Master Timeseries (theo tháng) để dùng cho các mô hình Machine Learning dự báo xâm nhập mặn.

## Tiến trình & Kết quả đạt được hiện tại

1. **Dữ liệu Khí tượng (Open-Meteo ERA5):**
   - Đã thu thập dạng CSV hàng ngày (lượng mưa, bốc hơi, gió max, nhiệt độ max/min/mean, độ ẩm, bức xạ).

2. **Dữ liệu Mực nước Vệ tinh (DAHITI):**
   - Giải quyết thành công lỗi định dạng tải của DAHITI thông qua `fetch_dahiti.py`.
   - Kết quả: Đã tải được Mực nước (Water level m) cho trạm Tân Châu (id 627) và Mỹ Tho (id 3316).

3. **Dữ liệu Lưu lượng (GloFAS - Copernicus):**
   - Phát triển `fetch_glofas.py` để tải Lưu lượng (Discharge m³/s) cho Tân Châu từ mô hình LISFLOOD (1985-2023).
   - Do API có giới hạn "cost limits", script đã được tùy chỉnh để tải từng năm tự động. **Chương trình tải đang được khởi chạy ngầm**. Cần một khoảng thời gian trước khi tải hoàn thành do file NC phân giải chậm.

4. **Tổng hợp Dữ liệu (Master Timeseries):**
   - Đã viết sẵn tập lệnh `process_data.py`.
   - Chức năng: Sau khi thư mục `data/raw` tải đầy đủ, script này tự động đọc toàn bộ CSV + NetCDF từ Conductivity, DAHITI, Open-Meteo và GloFAS, tính biến đổi lại từ Ngày (Daily) sang Tháng (Monthly) (`resample` qua pandas DataFrame) và áp dụng **Outer Join** để làm giàu bộ dataset cuối.
   - Đầu ra xuất dưới dạng `master_timeseries.parquet` siêu nhẹ cho Model.

## Hướng dẫn chạy
Khi quá trình thu thập GloFAS hoàn tất, bạn chỉ cần mở terminal và chạy:
```bash
python process_data.py
```
> *(Tham khảo `data_dictionary.md` để xem mô tả cấu trúc của file parquet thu được)*.
