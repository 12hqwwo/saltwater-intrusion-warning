# WebGIS dự báo xâm nhập mặn và hỗ trợ vận hành cống tại tỉnh Đồng Tháp mới

Dự án thu thập và hợp nhất các dữ liệu thủy văn, khí tượng và độ dẫn điện (Conductivity mS/m) tại ĐBSCL. Trọng tâm là tỉnh Đồng Tháp (mới), với trạm Tân Châu đóng vai trò là upstream explanatory station outside study area. Hệ thống kết hợp toàn bộ features vào một Master Timeseries (theo tháng) để dùng cho các mô hình Machine Learning dự báo xâm nhập mặn/độ dẫn điện.

## Tiến trình & Kết quả đạt được hiện tại

1. **Dữ liệu Khí tượng (Open-Meteo ERA5):**
   - Đã thu thập dạng CSV hàng ngày (lượng mưa, bốc hơi, gió max, nhiệt độ max/min/mean, độ ẩm, bức xạ).

2. **Dữ liệu Mực nước Vệ tinh (DAHITI):**
   - Giải quyết thành công lỗi định dạng tải của DAHITI thông qua `fetch_dahiti.py`.
   - Kết quả: Đã tải được Mực nước (Water level m) cho trạm Tân Châu (id 627) và Mỹ Tho (id 3316).

3. **Dữ liệu Lưu lượng (GloFAS - Copernicus):**
   - Đã phát triển `fetch_glofas.py` và tải thành công Lưu lượng (Discharge m³/s) cho trạm Tân Châu từ mô hình LISFLOOD (1985-2023).

4. **Dữ liệu Thủy triều cực đại (UHSLC):**
   - Đã lấy dữ liệu độ cao mực nước thủy triều lịch sử tại Vũng Tàu.

5. **Tổng hợp Dữ liệu (Master Timeseries):**
   - Đã viết sẵn tập lệnh `process_data.py`.
   - Chức năng: Tự động đọc toàn bộ CSV + NetCDF từ Conductivity, DAHITI, Open-Meteo, UHSLC và GloFAS, resample từ Ngày (Daily) sang Tháng (Monthly) (`resample` qua pandas DataFrame) và áp dụng **Outer Join** để làm giàu bộ dataset cuối.
   - Đầu ra xuất dưới dạng `master_timeseries.parquet` siêu nhẹ cho Model.

## Hướng dẫn chạy
Khi quá trình thu thập GloFAS hoàn tất, bạn chỉ cần mở terminal và chạy:
```bash
python process_data.py
```
> *(Tham khảo `data_dictionary.md` để xem mô tả cấu trúc của file parquet thu được)*.
