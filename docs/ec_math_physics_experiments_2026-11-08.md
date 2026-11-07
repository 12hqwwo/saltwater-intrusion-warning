# Thử mô hình EC Mỹ Tho: chuyển mạch, log, dữ liệu ngày và khoảng trên

Ngày 08/11/2026. Mẫu EC Mỹ Tho **692 mS/m ngày 15/03/2020 là nhãn đúng** và được giữ nguyên trong mọi phép chấm. Mục tiêu của lượt này là thử các đề xuất mới mà không thay đổi mô hình đang phục vụ.

## Giao thức

Ba kỳ mất EC liên tục được chấm riêng: 2019–2021 (36 tháng), 2021–2023 (36 tháng), 2022–2023 (24 tháng). Tại đầu mỗi kỳ, RF 300 cây học một lần trên EC Mỹ Tho đã được giả định công bố đến ngày phát hành đầu; EC trong kỳ chỉ dùng chấm điểm. Đối chứng RF khí tượng + Kratie + Tân Châu khớp dự báo nghiên cứu đã lưu đến `1e-8` mS/m. Mọi ứng viên dùng cùng tập dự báo và được chạy với giả định độ trễ EC +5 và +35 ngày. Các kỳ đều đã được xem trước, **không phải kiểm định mù**.

Đề xuất “dùng hết tháng `t−1` khi phát hành ngày 06 của chính tháng đó” không khả thi: tháng `t−1` chưa kết thúc. Với tháng mục tiêu 03/2020, phát hành 06/02/2020 và giả định từng số đo ngày có trễ công bố 5 ngày, ngày 01/02/2020 chỉ có thể dùng nếu bản tin phát hành **sau** giờ số đo đó được công bố. Vì giờ phát hành chưa biết, phép thử lấy mốc chặt hơn **31/01/2020** (`issue_date − 6 ngày`). Nó dùng 7 ngày kết thúc tại mốc này và 7 ngày trước đó; tạo cực tiểu và chênh trung bình cửa sổ cho Q Kratie và mực nước Tân Châu. Đây chỉ là **giả định độ trễ** vì gói MRC không có dấu thời gian công bố lịch sử. Trong 60 tháng 2019–2023, 59 tháng có đủ hai cửa sổ; tháng 05/2019 thiếu và dùng dự báo đối chứng.

Các cấu hình được cố định trong `scripts/experiment_ec_math_physics_20261108.py`:

- **Chuyển mạch:** tháng 1–5 và tỷ lệ Q Kratie `t−2` dưới 0,75 hoặc 0,85 thì dùng RF 300 cây trọng số 5 cho nhãn EC ≥100; ngoài nhánh đó dùng RF chính. Thử riêng phương án dùng GB Huber ở nhánh thường.
- **Log + smearing:** RF học `log1p(EC)`; 20% nhãn cuối trong tập đã biết làm tập hiệu chỉnh theo thứ tự thời gian, tính trung bình `exp(sai số log)`, rồi RF học lại toàn tập. So với log không hiệu chỉnh.
- **Ridge nghịch đảo Q + RF phần dư:** Ridge học `log1p(EC)` từ `1000/Q`, mực nước Tân Châu, mưa và chu kỳ tháng; RF học phần dư EC trên tập huấn luyện. Không dùng nhãn trong kỳ mất EC. Phần dư được học trên dự báo Ridge trong tập, vì vậy kết quả cần kiểm tra thêm bằng phần dư ngoài mẫu trước khi đưa vào vận hành.
- **Khoảng trên thực nghiệm:** RF đối chứng huấn luyện trên phần cũ của tập đã biết; tối đa 120 tháng cuối dùng hiệu chỉnh phân vị 90% của sai số có dấu trong mùa khô. Mốc bù này cộng vào dự báo RF đã học toàn bộ nhãn trước kỳ mất. Vì chuỗi thời gian không chắc có tính hoán đổi, không gọi đây là bảo đảm bao phủ tương lai.

## Kết quả sai số

Đơn vị MAE/RMSE: mS/m. Bảng chính là giả định EC trễ **5 ngày**; kết quả 35 ngày ở `outputs/ec_math_physics_20261108/metrics.csv`.

| Phương án | 2019–2021 MAE / RMSE | 2021–2023 MAE / RMSE | 2022–2023 MAE / RMSE | Dự báo 03/2020 |
| --- | ---: | ---: | ---: | ---: |
| RF thủy văn chính | 57,81 / 133,82 | **16,57 / 31,21** | 12,19 / 25,43 | 213,67 |
| Chuyển mạch Q <0,75 | 59,35 / 136,33 | **16,57 / 31,21** | 12,19 / 25,43 | 213,67 |
| Chuyển mạch Q <0,85 | **56,19 / 128,17** | **16,57 / 31,21** | 12,19 / 25,43 | 225,95 |
| GB Huber thường, RF trọng số khi Q <0,75 | 68,48 / 163,57 | 18,38 / 39,19 | 11,03 / 20,86 | 95,96 |
| RF học log EC | 66,21 / 162,88 | 16,98 / 36,22 | 10,81 / 21,90 | 94,12 |
| RF log + smearing | 62,83 / 152,13 | 22,17 / 37,39 | 26,06 / 43,13 | 125,69 |
| Ridge nghịch đảo Q + RF phần dư | 57,43 / 129,75 | 17,48 / 32,88 | **10,33 / 19,29** | 216,83 |
| RF thêm dữ liệu ngày gần phát hành | 64,82 / 151,59 | 16,57 / 30,92 | 12,55 / 25,22 | 158,90 |

Ngưỡng `<0,75` không bật ở 03/2020 vì tỷ lệ Q tháng đầu vào là **0,811**. Ngưỡng `<0,85` bật ở 5/36 tháng của kỳ 2019–2021 và không bật trong hai kỳ sau. Nó giảm MAE toàn kỳ 2019–2021 nhưng số tháng EC ≥100 bị dự báo dưới 100 **tăng từ 2 lên 3**: riêng 02/2020 thực đo 558, dự báo đối chứng 108,63, chuyển mạch còn **85,74 mS/m**. Ngưỡng `<0,85` được kiểm tra thêm sau khi đã thấy tỷ lệ 03/2020, nên kết quả đặc biệt dễ bị chọn theo kỳ đã xem.

Ridge nghịch đảo Q + RF phần dư giảm sai số ở 2019–2021 và 2022–2023 nhưng làm cả MAE và RMSE kỳ 2021–2023 tăng. Tất cả ứng viên vẫn dự báo **rất thấp** so với mẫu EC 692. Phép thử dữ liệu ngày theo giả định +5 ngày và mốc an toàn thêm một ngày còn làm MAE 2019–2021 tăng 7,02 mS/m, dù đầu vào 03/2020 đầy đủ.

Nhánh dữ liệu ngày trong lượt này chỉ dùng **Q Kratie và mực nước Tân Châu**. Chưa dùng phép trừ trực tiếp mực nước Vũng Tàu 383B với FES: hai nguồn không có mốc cao độ chung, và chuỗi 383B chỉ bắt đầu năm 2007. Gió ERA5 theo ngày cũng chưa được thử ở nhánh này. Do đó kết quả không bác bỏ mọi mô hình dùng thông tin sát ngày phát hành; nó chỉ chấm cấu hình bốn biến ngày nêu trên.

## Khoảng trên và quyết định

Mốc bù mùa khô của phép hiệu chỉnh là **40,03 mS/m** khi khóa trước 2019; khoảng trên tại 03/2020 chỉ **253,69 mS/m**. Nó bao phủ **10/15 tháng mùa khô (66,7%)** của kỳ 2019–2021, thấp hơn mục tiêu 90%. Khi khóa trước 2021 và 2022, mốc bù tăng lên khoảng **257–261 mS/m** sau khi các nhãn cực trị 2020 đã vào tập; khoảng trên lúc đó rất rộng. Do đó chưa có một trần cảnh báo có bảo chứng từ dữ liệu hiện có.

**Giữ RF khí tượng + Kratie + Tân Châu làm mô hình chính.** Chưa đưa ứng viên chuyển mạch, hybrid, đặc trưng ngày hoặc khoảng trên vào WebGIS. Phương án chuyển mạch `<0,85` và Ridge nghịch đảo Q đáng giữ làm ứng viên nghiên cứu, nhưng cần kỳ EC mới chưa từng dùng chọn, lịch công bố đầu vào thực tế và kiểm riêng các tháng EC cao trước khi thay mô hình. Các kết quả trong lượt này không chứng minh quan hệ EC–Q là hàm mũ cụ thể; công thức truyền mặn trong tài liệu là giả thuyết cơ chế, không phải phương trình đã hiệu chuẩn cho Mỹ Tho.

Đầu ra tái lập ở `outputs/ec_math_physics_20261108/`: `predictions.csv`, `metrics.csv`, `recent_daily_features.csv`, `calibration.csv`, `interval_audit.csv` và `protocol.json` ghi mã băm nguồn. Chạy bằng `python scripts/experiment_ec_math_physics_20261108.py` trong thư mục dự án có bộ dữ liệu gốc.
