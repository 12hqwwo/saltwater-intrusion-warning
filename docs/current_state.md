# Hiện trạng dự án — rà soát ngày 02/10/2026

Phạm vi: mã nguồn và dữ liệu trong gói ZIP được cung cấp. Đợt này không kết nối PostgreSQL trên máy người thực hiện. Tiến độ ETL đã có được kế thừa; kiểm tra file không thay thế truy vấn database hiện tại.

## Các phần đã có và đã kiểm tra

| Thành phần | Bằng chứng | Kết luận |
|---|---|---|
| Schema v1/v2 | Các file SQL tạo 11 bảng nghiệp vụ | Đã có mã schema; không cần tạo lại database đang hoạt động. |
| EC Tân Châu | CSV gốc: 464 dòng; SHA-256 khớp manifest | Toàn bộ file qua kiểm tra ETL. |
| EC Mỹ Tho | CSV gốc: 463 dòng; SHA-256 khớp manifest | Toàn bộ file qua kiểm tra ETL. |
| Master tháng | 1.000 dòng, 500 tháng/khu vực; 927 giá trị EC khác NULL | Lịch liên tục 1985-01–2026-08; EC chỉ đến tháng 12/2023. |
| Tổng hợp EC | Đối chiếu raw với master theo tháng | Không sai khác giá trị hoặc trạng thái thiếu; chưa xác minh chuyên môn phép đo. |
| ETL CSV | etl/etl_csv.py; 7 test chạy đạt sau sửa đường dẫn fixture | Giữ logic ETL; tài liệu nhập lặp/rollback ngày 25/09 được kế thừa. |
| Tọa độ hai trạm | Hai KML gốc và bản sao khớp byte; hash khớp manifest | Có lớp điểm REPORTED; chưa biết đã COMMIT vào DB chính hay chưa. |
| Ranh giới | 3 GeoJSON: 1 đối tượng Đồng Tháp, 1 Tiền Giang, 102 đơn vị phường/xã | Đọc được cấu trúc và miền tọa độ; chưa kiểm tra topology hoặc nguồn/ngày hiệu lực. |
| Backtest | run_forecast.py và runs/forecast_exp/ | Có kết quả thí nghiệm; chưa phải chức năng dự báo trên Web. |
| Kiểm tra cục bộ | scripts/audit_local_data.py và 4 test bổ sung | Chạy được bằng thư viện chuẩn Python, không cần database. |

Raw có 927 dòng O, không có E; tất cả giữ Grade = Unverified data và Approval Level = Raw - Not Yet Reviewed. Đây không phải bằng chứng lỗi nhập. Cờ quality_flag hiện tại phải đọc từ database; schema/ETL mặc định UNVERIFIED, không tự nâng VALIDATED.

## Độ phủ đã đếm lại

| Khu vực | Tháng lịch | Có EC | Có DAHITI | Có GloFAS |
|---|---:|---:|---:|---:|
| Mỹ Tho | 500 | 463 | 217 | 0 |
| Tân Châu | 500 | 464 | 108 | 469 |

GloFAS Tân Châu trong master có tháng cuối 2024-01, dù tên bộ file tải đề cập 1985–2023. Cần kiểm tra thời gian bên trong NetCDF và cách gộp file trước khi dùng cho mô hình; chưa kết luận giá trị đó sai chỉ từ tên file.

## Phần chưa hoàn thành hoặc chưa có bằng chứng hiện tại

- backend/ trống: chưa có API.
- frontend/ có cấu hình Vite/OpenLayers/Bootstrap và lockfile; chưa có index.html hoặc mã trang bản đồ.
- audit_results.txt có dung lượng 0 byte: không phải bằng chứng audit database.
- Mẫu cống cũ có hai dòng minh họa, một dòng mang tọa độ và VERIFIED nhưng URL là giá trị giữ chỗ. Đã chuyển thành mẫu chỉ có header. Chưa có danh mục cống thật trong gói; không suy ra DB hiện tại có 0 cống.
- Ranh giới chưa có hồ sơ nguồn/ngày hiệu lực. Tên file 63/34 không đủ để tự chọn phiên bản nghiên cứu.
- Không có dự án QGIS .qgz/.qgs trong ZIP; không suy ra người thực hiện chưa dựng bản đồ ở nơi khác.
- forecast_result, gate_recommendation, giao diện dự báo và hỗ trợ vận hành cống thuộc phần phát triển tiếp theo.

## Mô hình hiện có

Đã tính lại từ predictions.csv và đối chiếu actual với master:

| Mô hình | Số tháng | MAE (mS/m) | RMSE (mS/m) |
|---|---:|---:|---:|
| Persistence | 24 | 9,1546 | 15,5594 |
| Seasonal Naive | 24 | 20,1496 | 47,8423 |
| Random Forest | 24 | 18,9450 | 31,1290 |

Cả ba dùng cùng 24 tháng từ 2022-01 đến 2023-12 trong kết quả này. Hai phương pháp đầu là baseline; Random Forest là ứng viên. Chưa chạy lại huấn luyện trong đợt này.

run_forecast.py cần hoàn thiện thời điểm phát hành và giả định dữ liệu sẵn có; đánh giá validation; bảo vệ trường hợp RF chưa fit; hash snapshot thật; tập tháng chung khi có giá trị thiếu. Kết quả hiện tại không chứng minh khả năng dự báo thời gian thực năm 2026.

## Mục tiêu phát triển kế tiếp

API đọc measurement_site và conductivity_observation, giữ mS/m, cờ chất lượng và định danh snapshot. API lịch sử có thể phát triển trước khi hoàn thiện mô hình dự báo. Tọa độ thiếu phải được thể hiện rõ, không đặt điểm thay thế.
