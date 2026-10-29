# Backtest EC theo ngày phát hành

Script `scripts/backtest_asof_ec.py` tạo dự báo hồi cứu cho Mỹ Tho và Tân Châu từ 01/2019 đến 12/2023. Mỗi tháng mục tiêu `t` có ngày phát hành giả định là **ngày 06 của tháng `t−1` theo giờ Việt Nam**. Mô hình RandomForest được huấn luyện lại cho từng lần phát hành, chỉ từ các nhãn EC và đặc trưng khí tượng có ngày sẵn có giả định không muộn hơn ngày phát hành. Siêu tham số giữ nguyên bản gốc: 300 cây, `max_depth=8`, `min_samples_leaf=3`, seed 42. Không thay model đang phục vụ hoặc dữ liệu MRC.

## Giả định sẵn có

| Nguồn | Quy tắc áp dụng trong backtest |
| --- | --- |
| Mưa, nhiệt độ, gió ERA5 | Dùng trọn tháng `t−2`; giả định có từ **cuối tháng đó + 5 ngày**, như adapter hiện tại. |
| EC MRC, kịch bản nhanh | Giả định phép đo của một tháng được công bố vào **cuối tháng + 5 ngày**. |
| EC MRC, kịch bản chậm | Giả định công bố vào **cuối tháng + 35 ngày**. |
| Tháng mục tiêu | Chỉ dùng số tháng và sin/cos của tháng, đã biết theo lịch. |
| Persistence, Seasonal Naive, Monthly Climatology | Cùng dùng tập nhãn EC được xem là đã công bố ở ngày phát hành. Climatology chỉ tính trung bình tháng lịch từ tập đó. |

Hai độ trễ EC là **giả định để kiểm tra độ nhạy**, không phải ngày công bố do MRC xác nhận. Bản xuất MRC được tạo năm 2026 và không có lịch sử ngày công bố từng mẫu. ERA5 lịch sử cũng được lấy lại về sau, nên các giá trị có thể không trùng chính xác bản dữ liệu tồn tại vào từng ngày trong quá khứ. Kết quả này là **backtest hồi cứu theo quy tắc sẵn có**, chưa phải kiểm toán dự báo tiền cứu.

Ví dụ, dự báo 01/2019 phát hành giả định 06/12/2018, dùng khí tượng 11/2018 (giả định sẵn có 05/12/2018). Nhãn EC mới nhất có thể dùng là **11/2018** nếu công bố sau 5 ngày, hoặc **10/2018** nếu sau 35 ngày. EC 12/2018 không vào huấn luyện. Với 01/2022, các nhãn mới nhất tương ứng là 11/2021 và 10/2021. Script ghi ngày phát hành, tháng khí tượng, ngày sẵn có và nhãn cuối cùng của **từng** dự báo vào `asof_predictions.csv`; kiểm tra tự động cho thấy 0/240 dòng dùng khí tượng hoặc nhãn sau ngày phát hành giả định.

## Kết quả chính

MAE tính bằng mS/m. `validation` = 2019–2021 (36 tháng/trạm); `historical_2022_2023` = 2022–2023 (24 tháng/trạm). Các bảng đầy đủ gồm RMSE, bias, mùa khô 12–4, ngoài mùa khô 5–11 và EC cao ở `asof_metrics.csv`.

| Trạm | Độ trễ EC | RF validation | RF 2022–2023 | Baseline tốt nhất 2022–2023 |
| --- | --- | ---: | ---: | ---: |
| Mỹ Tho | Cuối tháng + 5 ngày | 71,56 | 18,63 | Persistence 12,62 |
| Mỹ Tho | Cuối tháng + 35 ngày | 71,26 | 18,61 | Persistence 15,09 |
| Tân Châu | Cuối tháng + 5 ngày | 3,70 | 4,34 | Seasonal Naive 2,38 |
| Tân Châu | Cuối tháng + 35 ngày | 3,71 | 4,34 | Seasonal Naive 2,38 |

Trên mùa khô 12–4 của giai đoạn 2022–2023, MAE RF là **35,38/35,19** ở Mỹ Tho và **5,27/5,27** ở Tân Châu (kịch bản EC +5/+35 ngày). Mô hình vẫn chưa thắng baseline mạnh nhất trên toàn tập tại cả hai trạm. Sự khác biệt nhỏ giữa hai kịch bản không chứng minh ngày công bố thực tế có ít tác động; nó chỉ cho biết RandomForest với đặc trưng hiện tại cho điểm số gần nhau dưới hai quy tắc đã thử.

## Cách đọc và tái tạo

Chạy `.venv\Scripts\python.exe scripts/backtest_asof_ec.py` tại gốc dự án. Kết quả ở `outputs/multivariate_ec_asof_20261029/`: `asof_predictions.csv` (240 dòng), `asof_metrics.csv` (128 dòng) và `protocol.json` ghi quy tắc, phiên bản scikit-learn 1.9.1 cùng checksum đầu vào. Không có mô hình mới được lưu vào registry.

Backtest mới **huấn luyện lại hằng tháng**, trong khi bản cũ huấn luyện cố định theo split. Vì thế không nên diễn giải chênh lệch MAE giữa hai bản chỉ là tác động của việc sửa lỗi thông tin tương lai; hai bản còn khác chính sách cập nhật mô hình. Giai đoạn 2022–2023 đã được xem trong các phân tích trước, nên đây là mốc lịch sử để chẩn đoán, không phải holdout mù cho việc chọn mô hình tiếp theo. Khi có ngày công bố thật của EC hoặc bản lưu ERA5 theo thời điểm, thay giả định bằng dấu thời gian nguồn và chạy lại.
