# FES2022 đã đủ để tính triều thiên văn; vì sao kiểm thêm trạm đo

FES2022b đã có tại `data/raw/tide/fes2022b/`. Atlas 34 thành phần và mask được `scripts/experiment_ec_fes_day15_fixed.py` dùng để tính lại triều thiên văn ở điểm `south` (106,7833°E; 10,05°N) cho ngày cố định 13–17 của từng tháng 1985–2023. Cửa sổ được chốt theo ngày lấy mẫu EC thường quanh ngày 15, **không dùng ngày mẫu thực tế của tháng cần dự báo**. Đầu ra là 55.560 giờ, 463 đặc trưng tháng và manifest ở `outputs/ec_fes_day15_fixed_20261030/`.

| Kỳ, giả định EC công bố +5 ngày | RF_compact MAE | +FES ngày 13–17 MAE | Số tháng |
|---|---:|---:|---:|
| 2010–2018 | **14,76** | 14,83 | 108 |
| 2019–2021 | **50,87** | 52,69 | 36 |
| 2022–2023 | **11,07** | 12,26 | 24 |
| EC ≥100 trong 2019–2021 | **259,37** | 265,64 | 6 |

Ở giả định +35 ngày, FES giảm nhẹ MAE 2010–2018 (15,44→15,11) và 2019–2021 (55,30→55,29), nhưng tăng 2022–2023 (11,25→12,15). **Không đưa FES ngày 13–17 vào RF_compact**, vì lợi ích không ổn định. Điều này không phủ nhận vai trò vật lý của triều; EC MRC chỉ một mẫu/tháng, không có giờ pha triều, còn FES cho triều thiên văn ngoài biển chứ không đo mực nước tổng/nước dâng trong sông.

Chuỗi [UHSLC Vũng Tàu-B 383B](https://uhslc.soest.hawaii.edu/erddap/tabledap/global_hourly_gesla.subset) được lấy thêm **để đối chiếu FES và quan sát mực nước ven biển**, không phải tải lại FES. Mực nước đo bao gồm các thành phần ngoài triều thiên văn; trạm Vũng Tàu cũng không nằm ngay cửa Tiểu và có mốc cao độ riêng. Bản research-quality 383B đã chuẩn hóa từ 150.900 hàng giờ UTC (2007-10-15 đến 2024-12-31), 4.332 giá trị thiếu; chỉ số biên độ ngày yêu cầu ≥22 giờ hợp lệ, được 6.000 ngày. Manifest và chuỗi sạch ở `data/external/uhslc_vungtau_hourly_20261030/`. Đối với backtest phát hành ngày 06 tháng trước, chỉ dùng cửa sổ đo **trước** ngày phát hành với giả định trễ công bố rõ ràng; không dùng mực nước đo trong tháng mục tiêu.

Kiểm tra metadata [UHSLC Fast Delivery](https://uhslc.soest.hawaii.edu/erddap/tabledap/global_hourly_fast.subset) xác nhận **id142 là Langkawi, Malaysia**; [catalogue UHSLC](https://uhslc.soest.hawaii.edu/erddap/tabledap/global_hourly_gesla.subset) ghi **Vũng Tàu là 383/383B**. Tệp cũ tên `uhslc_tides_VungTau_id142_daily.csv` đã bị gắn nhãn sai. Đã sửa mã tải, đường đọc ETL/nghiên cứu và inventory để không còn đưa tệp đó vào đặc trưng Vũng Tàu; giữ nguyên tệp cũ làm bằng chứng nguồn, không dùng khi huấn luyện. Các kết quả legacy từng dùng `tide_max_m` từ id142 cần chạy lại trước khi trích trong báo cáo; RF_compact hiện tại không dùng cột này.
