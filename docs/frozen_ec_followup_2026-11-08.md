# Kiểm chứng tiếp: từng trạm EC lân cận và mô hình tuyến tính

Ngày 08/11/2026. Đây là **thí nghiệm hồi cứu đã xem trước**, không phải lựa chọn mô hình vận hành. Mã, dự báo từng tháng và nguồn đầu vào có tại [script](../scripts/evaluate_frozen_ec_followup.py), [predictions.csv](../outputs/frozen_ec_followup_20261108/predictions.csv), [metrics.csv](../outputs/frozen_ec_followup_20261108/metrics.csv) và [manifest](../outputs/frozen_ec_followup_20261108/run_manifest.json).

## Phương pháp

- Giữ nguyên Mỹ Tho bị khóa EC, ngày phát hành mùng 6 tháng trước, khí tượng và thủy văn tháng `t−2`, EC trạm khác theo giả định khả dụng sau 5 hoặc 35 ngày. Mỗi mô hình chỉ học EC Mỹ Tho **trước** kỳ mất tín hiệu; nhãn trong kỳ mất chỉ dùng chấm điểm.
- Trên cùng tập đầu vào khí tượng + thủy văn, thử thêm **riêng** EC Mỹ Thuận hoặc EC Tân Châu, giữ đúng Random Forest 300 cây của nghiên cứu trước.
- Thử Ridge có chuẩn hóa và điều chuẩn `alpha=10`; thử một phương án lai dùng Random Forest học phần sai số của Ridge trên tập huấn luyện trước kỳ mất. Giá trị dự báo âm được chặn ở 0. Đây là hai cấu hình cố định để kiểm tra khả năng ngoại suy, không dò tham số trên ba kỳ đã xem trước.
- Đối chiếu lại bốn phương án gốc từng tháng, sai khác tối đa cho phép `1e−8` mS/m; cùng 24/36 tháng, không thay cohort để làm đẹp điểm số. Mốc 100 mS/m chỉ phục vụ đếm báo cao giả và bỏ sót, không phải chuẩn dùng nước hay lệnh cống.

## Kết quả Mỹ Tho với giả định EC khả dụng sau 5 ngày

Các ô là **MAE / RMSE (mS/m); báo EC cao giả / bỏ sót EC cao**.

| Phương án | 2019–2021 (36 tháng) | 2021–2023 (36 tháng) | 2022–2023 (24 tháng) |
| --- | ---: | ---: | ---: |
| Chỉ khí tượng | 69,55 / 147,73; 3 / 2 | 28,31 / 64,23; 2 / 2 | 18,39 / 49,35; 1 / 0 |
| Khí tượng + thủy văn | **57,81 / 133,82; 1 / 2** | 16,57 / 31,21; 1 / 1 | **12,19 / 25,43; 2 / 0** |
| Thủy văn + EC Mỹ Thuận | 59,61 / 136,64; 1 / 2 | 15,91 / 29,96; 1 / 1 | 12,36 / 25,59; 1 / 0 |
| Thủy văn + EC Tân Châu | 58,65 / 135,51; 1 / 2 | 16,14 / 29,82; 1 / 1 | 13,33 / 28,13; 1 / 0 |
| Thủy văn + cả hai EC | 59,39 / 136,58; 1 / 2 | **15,97 / 29,59; 1 / 1** | 13,76 / 28,09; 1 / 0 |
| Ridge + thủy văn | 75,10 / 159,67; 3 / 3 | 30,68 / 42,19; 5 / 0 | 30,15 / 40,78; 4 / 0 |
| Ridge + RF phần sai số | 63,06 / 139,61; 1 / 3 | 21,51 / 36,77; 1 / 2 | 16,36 / **21,92**; 0 / 0 |

Với giả định EC chậm **35 ngày**, mô hình chỉ thủy văn đạt RMSE lần lượt **133,93; 31,54; 25,19**. Hai phương án Ridge vẫn không thắng ổn định; bảng đầy đủ trong `metrics.csv`.

## Diễn giải và quyết định

- Thêm thủy văn cải thiện sai số ở cả ba kỳ, nhưng **không dập tắt** báo cao sai 04/2022: kỳ 2022–2023 dự báo **100,04 mS/m** khi EC nguồn **25,7**. Cũng không bắt được đỉnh 03/2020: **213,67** so với **692,0 mS/m**.
- Không đủ bằng chứng để kết luận EC Tân Châu hay Mỹ Thuận luôn gây nhiễu. Thêm từng trạm thường làm kém hơn phương án thủy văn trong kỳ 2019–2021 và 2022–2023, nhưng lại cải thiện RMSE chút ít trong kỳ 2021–2023. Việc số báo giả thay đổi không xác nhận nguyên nhân là tương quan giả; muốn kiểm tra cần kiểm định độc lập và phân tích ảnh hưởng biến theo thời gian.
- Ridge thuần không cải thiện kỳ nào. Ridge lai giảm RMSE 2022–2023 xuống **21,92**, nhưng MAE tăng **12,19 → 16,36** so với chỉ thủy văn. Ở kỳ đỉnh mặn 2019–2021, Ridge lai dự báo **197,36** tại 03/2020 khi thực đo **692,0**, và bỏ sót **3** tháng EC cao thay vì **2**. Do vậy giả thuyết “mô hình tuyến tính sẽ giải quyết hụt đỉnh 2020” không được thí nghiệm này ủng hộ.
- Không thay mô hình đang phục vụ hoặc xóa đặc trưng EC khỏi mô hình khác. Tất cả các kỳ đã được phân tích trước khi thử phương án mới, chưa có kỳ kiểm định mù, và thời điểm công bố dữ liệu đầu vào lịch sử vẫn là giả định.

## Khả năng dùng trạm gần cửa sông

Kiểm kê dữ liệu dự án hiện tại không có **chuỗi EC trực tiếp, đủ tháng 2019–2023** tại Vàm Kênh, Hòa Định hay Bình Đại để chấm dự báo EC Mỹ Tho cùng giao thức. [Bản tin địa phương](new_data_search_2026-10-29.md) chứa độ mặn **g/L** Vàm Kênh trong 12 ngày năm 2026; không được đổi thành nhãn EC mS/m. Tệp `data/8file/08_ml_timeseries_642_and_pilot_154_cleaned.csv` có 6 mốc Hòa Định năm 2020 với EC **quy đổi từ độ mặn**, và một mốc IoT EC trực tiếp Hòa Định năm 2026; không đủ làm biến tháng cho kỳ đang chấm. MRC inventory trong `data/external/tien_ec_extended_20261029/inventory.json` có EC Mỹ Tho đến 2023, không có chuỗi Conductivity cho ba địa điểm vừa nêu. Vị trí gần cửa sông là giả thuyết chọn điểm đo hợp lý, chưa chứng minh sẽ “bắt gần như tuyệt đối” các đỉnh tại Mỹ Tho.

Để thử đầu vào cửa sông cần EC/EC25 hoặc chloride đo cùng quy ước, ngày giờ và lịch công bố, đủ trước **mỗi** ngày phát hành của chuỗi kiểm chứng mới. Cần kiểm riêng tính liên tục, QA, ảnh hưởng triều và khả năng các trạm cùng mất tín hiệu.
