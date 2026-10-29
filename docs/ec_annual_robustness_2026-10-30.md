# Sai số EC Mỹ Tho theo từng năm trên cùng tháng

`scripts/audit_ec_annual_robustness.py` đọc dự báo đã chấm theo ngày phát hành ở `outputs/ec_extreme_robust_20261029/`, kiểm đủ 60 tháng duy nhất 2019–2023 và ba cột dự báo không khuyết, sau đó tính sai số tuyệt đối ghép cặp. Đầu ra là `outputs/ec_annual_robustness_20261030/annual_metrics.csv` và `paired_monthly_errors.csv`. EC là **một mẫu MRC trong tháng** tại Mỹ Tho, đơn vị mS/m; mùa khô là tháng XII–IV, nhóm cao là EC đo ≥100 mS/m. Ngày công bố lịch sử không có trong MRC, nên các hàng dùng giả định công bố cuối tháng +5 hoặc +35 ngày. Đây là **hồi cứu đã nhiều lần được xem**, không phải kiểm định mù.

| Năm (12 tháng/năm) | RF cũ MAE | RF_compact MAE | EC gần nhất MAE | Số tháng RF_compact thắng RF cũ |
|---|---:|---:|---:|---:|
| 2019 | 26,85 | **6,82** | 12,86 | 8/12 |
| 2020 | 139,31 | **120,34** | 207,96 | 6/12 |
| 2021 | 48,51 | **25,44** | 59,35 | 10/12 |
| 2022 | 24,69 | 14,63 | **9,78** | 7/12 |
| 2023 | 12,57 | **7,51** | 15,46 | 8/12 |

Các số trên dùng giả định nhãn EC +5 ngày, cùng 60 tháng. MAE gộp 2019–2023 là RF cũ **50,39**, RF_compact **34,95**, EC gần nhất **61,08 mS/m**; RF_compact thắng RF cũ ở 39/60 tháng và cả năm năm theo MAE năm. Với giả định +35 ngày, MAE gộp lần lượt **50,20**, **37,68**, **81,54 mS/m**; RF_compact thắng 41/60 tháng và cả năm năm theo MAE năm. Cải thiện giữa hai mô hình có mặt trong từng năm nhưng không đồng nghĩa sai số thấp ở mọi chế độ.

Mùa khô 2020 còn MAE **269,94 mS/m** với RF_compact; bốn tháng EC ≥100 của năm đó MAE **343,04 mS/m**. Năm 2022, baseline EC gần nhất tốt hơn RF_compact (9,78 so với 14,63 mS/m), đặc biệt mùa khô (16,10 so với 31,46). Cần báo cáo các kết quả này cạnh MAE gộp, tránh kết luận quá mức về đỉnh mặn và vận hành cống. Chưa có quan trắc EC Mỹ Tho sau 12/2023 từ nguồn MRC đang dùng để kiểm dự báo trong giai đoạn gần hiện tại.
