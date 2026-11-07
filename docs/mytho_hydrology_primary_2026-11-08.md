# Mô hình chính Mỹ Tho: khí tượng và thủy văn thượng nguồn

Ngày 08/11/2026. Theo quyết định của người dùng, form dự báo EC Mỹ Tho và giá trị Mỹ Tho trên Timeline chuyển sang Random Forest 300 cây dùng **5 biến khí tượng/chu kỳ tháng + 5 biến thủy văn**. Hai trạm Tân Châu và Mỹ Thuận giữ mô hình riêng. Kết quả vẫn là **dự báo nghiên cứu**, không phải chỉ thị vận hành cống.

## Mô hình và đầu vào

- Cùng cấu hình Random Forest 300 cây, độ sâu tối đa 8, tối thiểu 3 mẫu/lá, seed 42 như [thí nghiệm](frozen_ec_remedies_2026-11-08.md). Huấn luyện lại trên 463 mẫu EC Mỹ Tho đến 12/2023, không dùng EC sau 2023. Artifact và manifest ở `runs/multivariate_ec/mytho/20261108T_HYDROLOGY_PRIMARY_V1/`; registry chỉ đổi mục Mỹ Tho.
- Mưa, nhiệt độ, gió ERA5 và chu kỳ tháng như trước. Thêm lưu lượng Kratie tháng `t−2`, trung bình 3 tháng kết thúc `t−2`, tỷ lệ so với trung vị cùng tháng của tối đa 15 năm trước; mực nước Tân Châu tháng `t−2` và trung vị 3 tháng kết thúc `t−2`. Bộ nạp API dùng cùng phép tính đã kiểm tra từng giá trị với script thí nghiệm.
- Nguồn Kratie và Tân Châu là CSV MRC lưu trong dự án, giữ mã băm trong manifest và trong từng dự báo. Tháng nguồn phải đủ ít nhất 20 ngày và được giả định sẵn có sau cuối tháng 5 ngày; **ngày công bố lịch sử thực tế chưa được xác minh**. Khi thiếu thủy văn, API không chạy mô hình. Người dùng có thể nhập khí tượng thủ công, nhưng không bỏ qua yêu cầu thủy văn.
- Timeline tính lại Mỹ Tho bằng mô hình mới ở những tháng có đủ khí tượng và thủy văn. Tệp `data/models/future_ec_forecast_2024_2026.csv` vẫn là bản lưu **dự báo khí tượng cũ**, dùng làm bằng chứng lịch sử; không được xem là đầu ra mô hình chính hiện hành.

## Điểm kiểm chứng hồi cứu

| Kỳ mất EC liên tục | RF chỉ khí tượng MAE / RMSE | RF thêm thủy văn MAE / RMSE | Giữ EC cuối cùng MAE / RMSE |
| --- | ---: | ---: | ---: |
| 2019–2021, 36 tháng | 69,55 / 147,73 | **57,81 / 133,82** | 80,20 / 191,23 |
| 2021–2023, 36 tháng | 28,31 / 64,23 | **16,57 / 31,21** | 19,13 / 42,57 |
| 2022–2023, 24 tháng | 18,39 / 49,35 | **12,19 / 25,43** | **10,76 / 16,46** |

Đơn vị: mS/m. Thủy văn giảm MAE/RMSE so với RF chỉ khí tượng ở cả ba kỳ, nhưng **không có RMSE thấp nhất trong kỳ 2022–2023**. Các kỳ đã được xem trước khi chọn phương án, nên không phải kiểm định mù. Trong kỳ 2019–2021, mô hình thủy văn vẫn dự báo **213,67** tại 03/2020 khi EC nguồn **692**; kỳ 2022–2023 vẫn dự báo **100,04** tại 04/2022 khi EC nguồn **25,7**. Vì vậy không diễn giải điểm số thành độ tin cậy cho một tháng tương lai hoặc cảnh báo cống.

## Phạm vi sản phẩm

API `/api/v1/multivariate/catalog`, `/inputs`, `/predict`, lịch sử dự báo mới và form WebGIS dùng version `20261108T_HYDROLOGY_PRIMARY_V1` tại Mỹ Tho. Mỗi dự báo ghi 10 giá trị đặc trưng, nguồn khí tượng, nguồn thủy văn, phiên bản mô hình và giả định thời điểm sẵn có. Các dự báo đã lưu trước đó giữ nguyên phiên bản cũ. Biểu đồ “Kiểm chứng dự báo khi EC ngừng cập nhật” vẽ đường hồi cứu của phương án thủy văn chính bên cạnh **đối chứng khí tượng cũ** và cách giữ EC cuối cùng; điểm số vẫn là hồi cứu.

Để kiểm tra độ tin cậy vận hành cần nhãn EC Mỹ Tho sau 2023 chưa dùng chọn mô hình, lịch công bố đầu vào thực tế, và kiểm riêng báo cao giả/bỏ sót các đỉnh trong kỳ mới.
