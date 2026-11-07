# Kiểm chứng đầu vào bổ sung khi Mỹ Tho mất EC dài hạn

Ngày kiểm tra: 08/11/2026. Đây là **thí nghiệm hồi cứu**, chưa thay mô hình đang phục vụ.

## Cách kiểm tra

- Khóa nhãn EC Mỹ Tho ở lần phát hành đầu của từng kỳ. Chỉ dùng nhãn trong kỳ mất tín hiệu để chấm điểm sau khi đã dự báo.
- Phát hành giả định ngày 6 của tháng trước tháng cần dự báo. Khí tượng ERA5, lưu lượng Kratie và mực nước Tân Châu lấy tháng `t−2`; giả định đủ dữ liệu sau cuối tháng nguồn 5 ngày. Lịch sử ngày công bố thực tế chưa có.
- Thử EC Mỹ Thuận và Tân Châu với giả định **hai trạm đó vẫn hoạt động**. Theo độ trễ công bố EC +5 ngày, tháng gần nhất khả dụng là `t−2`; theo +35 ngày là `t−3`. Không lấy EC Mỹ Tho sau mốc khóa làm đầu vào.
- Giữ cùng Random Forest 300 cây, độ sâu 8, tối thiểu 3 mẫu/lá và seed 42. Mỗi mô hình chỉ fit một lần trước kỳ mất EC. `WeatherOnly` khớp dự báo của [giao thức khóa EC gốc](../outputs/frozen_ec_gap_20261104/run_manifest.json) với sai khác số học dưới `1e−8`.

Mã tái tạo và dữ liệu từng tháng: [evaluate_frozen_ec_gap_remedies.py](../scripts/evaluate_frozen_ec_gap_remedies.py), [predictions.csv](../outputs/frozen_ec_remedies_20261108/predictions.csv), [metrics.csv](../outputs/frozen_ec_remedies_20261108/metrics.csv), [run_manifest.json](../outputs/frozen_ec_remedies_20261108/run_manifest.json).

## Kết quả Mỹ Tho, giả định nhãn EC khả dụng sau 5 ngày

| Kỳ mất EC | Chỉ khí tượng MAE / RMSE | Thêm thủy văn | Thêm EC trạm khác | Kết hợp cả hai | Giữ EC cuối cùng |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2019–2021, 36 tháng | 69,55 / 147,73 | **57,81 / 133,82** | 68,95 / 153,57 | 59,39 / 136,58 | 80,20 / 191,23 |
| 2021–2023, 36 tháng | 28,31 / 64,23 | 16,57 / 31,21 | 27,71 / 56,15 | **15,97 / 29,59** | 19,13 / 42,57 |
| 2022–2023, 24 tháng | 18,39 / 49,35 | **12,19 / 25,43** | 23,48 / 49,04 | 13,76 / 28,09 | **10,76 / 16,46** |

Đơn vị MAE/RMSE: mS/m. Các kỳ này đã được xem trước, nên bảng không thể dùng làm bằng chứng kiểm định mù để chọn mô hình.

Thủy văn giảm sai số cả ba kỳ, nhưng chưa xử lý được đỉnh cực trị. Tháng 03/2020, EC nguồn là **692,0 mS/m**; mô hình chỉ khí tượng là **133,65**, thêm thủy văn là **213,67 mS/m**. Với mốc phân tích **100 mS/m**, phương án thủy văn vẫn bỏ sót 2/6 tháng EC cao ở kỳ 2019–2021. Tháng 04/2022, EC nguồn **25,7**; mô hình khí tượng báo **253,76**, thêm thủy văn còn **100,04 mS/m**. Mốc 100 chỉ dùng đếm lỗi, không phải tiêu chuẩn tưới hay lệnh cống.

## Quyết định triển khai

Giao diện hiển thị phép so sánh này dưới phần “Kiểm chứng dự báo khi EC ngừng cập nhật”, kèm cảnh báo khi RMSE mô hình khí tượng cao hơn đối chứng. **Giữ nguyên mô hình và trọng số dự báo hiện tại**; không tự chuyển sang phương án thủy văn hoặc kết hợp vì các kỳ lịch sử đã được xem trước, phương án vẫn hụt đỉnh lớn, và chưa có EC thực đo mới để kiểm định mù.

Đề xuất giảm độ trễ khí tượng xuống `t−1` hoặc `t` chỉ có thể kiểm chứng công bằng khi có bản dự báo thời tiết được lưu đúng ngày phát hành; dùng ERA5 hoàn chỉnh sau sự kiện sẽ làm lộ thông tin tương lai. Chưa thêm triều thiên văn vì chưa có chuỗi đầu vào phù hợp với vị trí trạm và ngày phát hành. Nhận định về El Niño/La Niña, vận hành cống hay nguyên nhân trễ pha vẫn là **giả thuyết**, chưa được xác nhận từ phép thử này.

Trước khi xem xét thay mô hình đang phục vụ cần: lịch sử công bố nguồn thủy văn và EC lân cận, thử nghiệm trạm lân cận mất tín hiệu đồng thời, đánh giá độc lập trên nhãn EC mới sau 2023, và kiểm riêng báo động giả/bỏ sót đỉnh EC tại cả ba trạm.

Đã kiểm tra tiếp từng trạm EC riêng và phương án Ridge/RF tại [báo cáo kiểm chứng tiếp](frozen_ec_followup_2026-11-08.md).
