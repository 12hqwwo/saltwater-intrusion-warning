# Thử Q/mực nước ngay trước ngày phát hành

`scripts/experiment_ec_issue_daily_hydro.py` thử Q Kratie và mực nước Tân Châu ở cửa sổ 7/30/60 ngày **kết thúc trước ngày phát hành 06 tháng trước**, với độ trễ công bố nguồn giả định +5 hoặc +35 ngày. Nhãn EC Mỹ Tho giả định công bố cuối tháng +5 ngày. Mô hình được huấn luyện lại ở từng ngày phát hành; mọi phương án chấm cùng tháng. Dữ liệu MRC không có lịch sử ngày công bố thật, nên đây là phép thử theo giả định. Đầu ra và protocol ở `outputs/ec_issue_daily_hydro_20261030/`.

| Giả định Q/H +5 ngày, MAE mS/m | RF_compact hiện có | +Q/H 7 ngày | Thay bằng cửa sổ 7/30/60 ngày |
|---|---:|---:|---:|
| 2010–2018, 108 tháng | 14,76 | 14,25 | **14,09** |
| 2019–2021, 36 tháng | **50,87** | 56,53 | 67,31 |
| 2022–2023, 24 tháng | 11,07 | **9,65** | 10,43 |
| EC cao ≥100 ở 2019–2021, 6 tháng | **259,37** | 290,39 | 350,71 |

Ở giả định Q/H +35 ngày, biến 7 ngày cải thiện một ít MAE của từng kỳ so với **mốc Q/H sẵn có theo cùng giả định** (2010–2018: 17,56→16,27; 2019–2021: 64,10→63,66; 2022–2023: 9,91→8,42), nhưng mốc này phải dùng thủy văn t−3 nên không so trực tiếp với RF_compact t−2 ở giả định +5 ngày. Các biến 7/30/60 ngày làm nhóm EC cao và kỳ 2019–2021 xấu hơn ở giả định chính. Do đó **chưa thay RF_compact**; việc thêm dữ liệu gần ngày phát hành không tự giải đỉnh 2020. Các kỳ chấm đều từng được xem trong dự án, không phải tập mù mới.
