# Thử giảm sai số EC Mỹ Tho — 08/11/2026

## Phạm vi

Thử bảy phương án dựa trên `RF_compact` cùng đối chứng giữ EC cuối cùng. Mỗi tháng 2019–2023 là một lần phát hành ngày 6 của tháng trước; chỉ nhãn EC và khí tượng được giả định đã sẵn có mới vào tập huấn luyện. Nhóm 2019–2021 có 36 tháng để chọn ứng viên; nhóm 2022–2023 có 24 tháng để xem độ bền. Cả hai giai đoạn đã được xem trong nghiên cứu trước, nên không phải kiểm định mù. Ngày công bố thực tế của nguồn thủy văn chưa được xác minh.

Các kết quả dưới đây được tính lại trong **cùng môi trường scikit-learn 1.9.1** và trên cùng mã/dữ liệu hiện tại. Không lấy số `RF_compact` 50,87/130,90 từ bản phân tích cũ làm mẫu số so sánh: bản lưu ấy ghi scikit-learn 1.8.0, và mã/dữ liệu hiện tại có mã băm khác bản lưu. Mốc so sánh cùng lượt chạy là 51,71/131,95 ở giả định trễ EC 5 ngày.

## Kết quả

Đơn vị các chỉ số MAE và RMSE: mS/m; số nhỏ hơn là tốt hơn.

| Trễ EC | Phương án | MAE 2019–2021 | RMSE 2019–2021 | MAE 2022–2023 | RMSE 2022–2023 |
| --- | --- | ---: | ---: | ---: | ---: |
| 5 ngày | RF_compact | 51,71 | 131,95 | 12,01 | 25,69 |
| 5 ngày | RF_fine_compact | **49,40** | 127,46 | 13,88 | 31,68 |
| 5 ngày | RF_deficit_w5 | 52,32 | **126,85** | 17,39 | 43,29 |
| 5 ngày | RF_fine_deficit | 51,60 | 133,31 | 12,13 | 26,32 |
| 5 ngày | GB_compact_huber | 64,96 | 159,11 | **10,28** | **19,20** |
| 35 ngày | RF_compact | 57,21 | 138,34 | 12,40 | **24,69** |
| 35 ngày | RF_fine_compact | **53,83** | 132,80 | **12,25** | 26,73 |
| 35 ngày | RF_deficit_w5 | 55,76 | **130,29** | 16,42 | 40,27 |

Ở 5 ngày, `RF_fine_compact` giảm MAE validation 2,31 mS/m (4,5%) và RMSE 4,49 mS/m (3,4%) so với `RF_compact` cùng lượt chạy. Đổi lại MAE hồi cứu 2022–2023 tăng 1,87 mS/m và RMSE tăng 5,99 mS/m. Kết quả 35 ngày cũng cho thấy MAE validation tốt hơn, nhưng RMSE hồi cứu vẫn tăng.

Sáu tháng EC thực đo từ 100 mS/m trở lên vẫn khó dự báo. Trong tháng 03/2020, EC thực đo là 692, `RF_compact` dự báo 204,36 và `RF_fine_compact` dự báo 192,74 mS/m. Vì vậy cải thiện trung bình **không** giải quyết được đỉnh cực đoan. `RF_deficit_w5` nâng dự báo tháng đó lên 217,58 nhưng tăng rõ sai số trên toàn bộ 2022–2023.

## Quyết định

Chưa thay mô hình chính của trang WebGIS. Mô hình đang phục vụ Mỹ Tho là RF 300 cây dùng khí tượng + thủy văn, với giao thức **khóa EC liên tục**; thí nghiệm này dùng `RF_compact` theo **rolling origin**. Điểm số của hai giao thức không thể xem là bảng xếp hạng trực tiếp. Việc chấm ứng viên theo cùng giao thức khóa EC, xác minh lịch công bố đầu vào và có nhãn EC mới sau 2023 là các điều kiện cần trước khi đổi mô hình phục vụ.

Đã thêm hàng RF thủy văn vào đầu bảng sai số của phần kiểm chứng hồi cứu khi phản hồi API có cùng trạm, kỳ, số tháng và dãy dự báo đầy đủ. Hàng này dùng điểm số của giao thức khóa EC, không dùng các điểm số `RF_compact` ở bảng trên.

## Dữ liệu để nghiên cứu tiếp

Để giảm sai số tháng hạn mặn cực đoan, ưu tiên chuỗi triều/mực nước cửa sông cùng ngày khả dụng lịch sử, kiểm tra tính nhất quán của EC đo tại Mỹ Tho, và đánh giá riêng các lần báo cao giả/bỏ sót EC cao. Con số “55,8% độ quan trọng thủy văn” trong phân tích trước là độ quan trọng nội bộ của Random Forest trên tập huấn luyện, không phải phần đóng góp nhân quả hay bảo đảm giảm sai số. Không suy ra khả năng vận hành từ độ quan trọng biến hoặc từ kết quả hồi cứu đã xem trước.

Kết quả đầy đủ nằm ở `outputs/ec_error_reduction_20261108/predictions_5d.csv`, `predictions_35d.csv`, `metrics_5d.csv`, `metrics_35d.csv` và các tệp `protocol_*.json`. Chạy lại bằng `python scripts/experiment_ec_error_reduction.py --delay 5` hoặc `--delay 35`.
