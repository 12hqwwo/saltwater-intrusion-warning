# Weekly Progress Report

## Việc hoàn thành
1. **Kiểm kê dự án**: Đã review mã nguồn, schema CSDL, ETL, model baseline hiện có. Tổng hợp tình trạng vào `current_state.md`.
2. **Chốt CSDL / Công cụ GIS**:
   - Viết bản audit v2 (`sql/checks/01_audit_v2.sql`) bổ sung đếm số dòng, ngày quan trắc, phân bố cờ chất lượng (VALIDATED/UNVERIFIED), tỷ lệ O/E, và đếm hình học cống.
   - Viết template nhập cống chuẩn (`data/irrigation_gates_template.csv`) map đúng với các trường của bảng `irrigation_gate` trong CSDL.
   - Cung cấp script GIS query (`sql/checks/02_gate_queries.sql`) kiểm tra cống trong ranh giới, bán kính, và validity hình học.
3. **Thí nghiệm dự báo EC Mỹ Tho (trước 1 tháng)**:
   - Xây dựng `run_forecast.py` đảm bảo nguyên tắc: không trộn dữ liệu, không dùng tương lai (lag = 1 tháng tương ứng forecast origin). 
   - Duy trì các tháng trống trong chuỗi liên tục (continuous calendar).
   - Đã chạy thành công 3 baseline (Persistence, Seasonal Naive, Random Forest) trên 24 tháng kiểm thử.

## Bằng chứng
- File kết quả đầu ra nằm tại `runs/forecast_exp/` bao gồm: `predictions.csv`, `metrics.csv`, `split_manifest.csv` và biểu đồ dự báo `forecast_chart.png`.
- Các file SQL audit và template đã sẵn sàng ở `sql/checks/` và `data/`.

## Việc còn thiếu và bị chặn
- **SQL Audit trực tiếp**: Quá trình chạy audit SQL tự động bị chặn do database cần cấu hình quyền truy cập (mật khẩu Postgres) cho môi trường script.
- **Nạp cống**: Chưa có file cống thật điền theo template. Cần người dùng điền tọa độ và nguồn trước khi nạp vào DB.
- **Tích hợp API Backend**: Sau khi thống nhất mô hình, cần xây dựng API Backend cung cấp lịch sử và dự báo cho frontend bản đồ.
