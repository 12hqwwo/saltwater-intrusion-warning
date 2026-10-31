# Quét giả định ngày công bố EC từ 0 đến 70 ngày

Ngày 30/10/2026. Script `scripts/scan_ec_release_lag.py` quét **từng số nguyên ngày 0–70** sau cuối tháng đo. Ngày phát hành giả định vẫn là **ngày 06 của tháng trước tháng mục tiêu**; khí tượng/thủy văn `t−2` vẫn theo giả định sẵn có cuối tháng nguồn +5 ngày. Chỉ thay **ngày nhãn EC có thể vào tập huấn luyện**. Đây là kiểm tra độ nhạy với độ trễ công bố, không phải tối ưu siêu tham số, lead time dự báo hay xác định lịch công bố thật của MRC.

Chấm RF_compact cùng 36 tháng 2019–2021 và 24 tháng 2022–2023, đối chiếu Persistence và climatology trên cùng tháng. 4.260 hàng dự báo cho 71 giả định × 60 tháng; chỉ cần 240 lượt fit khác nhau vì nhiều ngày dẫn tới đúng cùng một tập nhãn. Kết quả +5 và +35 được kiểm bằng mã, **khớp** artifact đã báo trước. CSV đầy đủ từng tháng và MAE/RMSE/bias theo toàn kỳ, mùa khô XII–IV và EC thực ≥100 mS/m ở `outputs/ec_release_lag_scan_20261030/`.

| Trễ EC sau cuối tháng | RF_compact MAE 2019–2021 | RF_compact MAE 2022–2023 | Persistence MAE 2019–2021 | Persistence MAE 2022–2023 |
|---|---:|---:|---:|---:|
| **0–6 ngày** | **50,87** | **11,07** | 93,39 | 12,62 |
| **7–34 ngày** | 55,16 | 11,21 | 125,82 | 15,04 |
| 35 ngày | 55,30 | 11,25 | 125,84 | 15,09 |
| 38–65 ngày | 56,67 | 11,31 | 148,02 | 18,09 |
| 70 ngày | 56,09 | 11,30 | 150,68 | 19,99 |

MAE mS/m, làm tròn 0,01. Những ngày 35–37 và 66–69 thay đổi theo độ dài tháng, nên xem CSV để có từng ngày chính xác. **Thấp nhất về MAE toàn kỳ trong phạm vi quét là bất kỳ ngày 0–6**, ở cả hai giai đoạn; +5 không phải một ngày tối ưu riêng. Trong nhóm EC cao của 2019–2021 (6 tháng), RF_compact cũng thấp nhất ở 0–6 ngày nhưng vẫn MAE **259,37 mS/m**. Mùa khô 2022–2023 có MAE thấp nhất ở 69–70 ngày, 22,17 so với 22,22 ở 0–6; chênh lệch rất nhỏ và không làm lựa chọn độ trễ 69–70 có cơ sở thực tế.

Lý do các đoạn ngày cho cùng điểm số: phát hành 06/12/2018 để dự báo 01/2019. Với trễ 0–6 ngày, nhãn EC 11/2018 có thể vào huấn luyện; từ ngày 7 đến 36 chỉ đến 10/2018; từ ngày 37 đến 67 chỉ đến 09/2018. Dù đổi trễ trong một đoạn, tập nhãn và dự báo không đổi. Ngưỡng chính xác của các tháng khác phụ thuộc ngày cuối tháng.

**Không được chọn “MRC công bố sau 0–6 ngày” vì MAE thấp nhất.** Độ trễ công bố là thuộc tính của nguồn dữ liệu, không phải núm vặn để làm điểm số đẹp hơn. Tệp MRC hiện có không kèm ngày công bố từng mẫu hoặc lịch sử phiên bản; kết quả là backtest theo giả định. Nếu không xác nhận được ngày thật, báo ít nhất hai miền nhạy cảm **0–6** và **7–34/35+**, kèm giới hạn; khi có ngày công bố thực, thay giả định bằng ngày từng hàng rồi chạy lại. Dự báo 2026 còn cần nhãn EC sau 2023 để kiểm định ngoài mẫu.

Kiểm thêm bản fit **toàn bộ nhãn đến 12/2023** cho ước tính nghiên cứu 11/2026 (ngày phát hành giả định 06/10/2026): huấn luyện lại độc lập ở trễ **0, 5, 6, 7, 15, 35 và 70 ngày** đều lấy đúng **463 nhãn**, nhãn cuối 12/2023, và đều cho **15,005298988 mS/m**. Đổi trễ công bố không thể bổ sung dữ liệu 2024–2026 vốn chưa có trong tập nhãn.
