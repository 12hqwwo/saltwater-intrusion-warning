# Kiểm toán mô hình thích ứng EC và tương quan đặc trưng

Ngày 30/10/2026. Kiểm lại báo cáo Adaptive Dual-Head do người dùng cung cấp, giữ nguyên tệp gốc. Đầu ra vẫn là **EC của một mẫu MRC trong tháng tại Mỹ Tho (mS/m)**. Script mới: `scripts/audit_ec_adaptive_asof.py`, `scripts/audit_ec_feature_association.py`; bảng từng tháng và metric ở `outputs/ec_adaptive_asof_audit_20261030/`, `outputs/ec_feature_association_20261030/`.

## 1. Sửa phép so sánh baseline

Trong `scripts/experiment_ec_feature_enhanced.py`, cột `Persistence` lấy `prev.conductivity_mS_per_m.iloc[-1]` theo tháng trước mục tiêu, **không lọc ngày nhãn EC được công bố**. Cả **60/60** tháng ở mỗi giả định +5 và +35 ngày khác baseline `Persistence` đã lọc ngày phát hành. Hai con số 5/35 là **giả định độ trễ công bố nhãn**, không phải hai lead time phát hành khác nhau: cùng ngày giả định 06 tháng trước mục tiêu. Không trộn MAE từ hai cột Persistence. Tất cả phép chấm lại khớp đúng 36 tháng 2019–2021 và 24 tháng 2022–2023 với nhãn gốc và RF_compact đã kiểm.

| Giai đoạn / giả định | Persistence chưa lọc nhãn | Persistence đúng ngày phát hành | RF_compact chuẩn | Adaptive Q50/Q90 |
|---|---:|---:|---:|---:|
| 2019–2021, +5, 36 tháng | 52,19 | 93,39 | 50,87 | **46,17** |
| 2019–2021, +35, 36 tháng | 52,19 | 125,84 | 55,30 | **44,02** |
| 2022–2023, +5, 24 tháng | 9,15 | 12,62 | **11,07** | 16,23 |
| 2022–2023, +35, 24 tháng | 9,15 | 15,09 | **11,25** | 15,80 |
| 2010–2018, +5, 108 tháng | — | 22,17 | **14,76** | 20,66 |

MAE mS/m. Hàng lịch sử 2010–2018 huấn luyện lại các đầu Q50/Q90 tại mỗi ngày phát hành với cấu hình cây của script báo cáo (300 cây, leaf 2, seed 42). Cả lịch sử 2010–2018 và kỳ 2022–2023 đã được xem trong quá trình phát triển dự án; không phải test mù. Đỉnh EC ≥100 ở 2019–2021 còn MAE **188,07** cho Adaptive +35 so với RF_compact **285,24**, nhưng chỉ **6 tháng**; ở lịch sử 2010–2018 có 5 tháng cao thì Adaptive MAE **196,57**, RF_compact **105,63**. Kỳ 2022–2023 không có đỉnh EC cao để xác nhận lợi ích này.

**Quyết định:** Adaptive là thử nghiệm có tín hiệu đáng nghiên cứu cho năm 2020 nhưng **không giảm lỗi ổn định qua các giai đoạn**. Giữ RF_compact trong phạm vi nghiên cứu; không thay model/API hoặc đưa ngưỡng này vào quy tắc cống. `RF_compact` trong báo cáo gốc còn dùng cấu hình cây khác bản chuẩn, nên phải phân biệt `RF_compact_candidate` và `RF_compact_asof` trong CSV audit.

## 2. Tương quan mạnh phần lớn trùng với mùa

Tính Spearman trên các cặp có giá trị, sau đó trừ **trung vị riêng từng tháng lịch** của cả EC và biến trước khi tính Spearman lần hai. Đây là phép kiểm nhạy mùa, không phải partial correlation hay tác động nhân quả. Bảng dưới là 1985–2018 trước khi xem kỳ gần đây.

| Biến ở t−2 / trễ | n | Spearman thô | Sau bỏ trung vị tháng |
|---|---:|---:|---:|
| Gió đông–tây ERA5 `wind_u_t2` | 403 | −0,717 | −0,195 |
| Q Kratie `kratie_q_t2` | 403 | −0,703 | −0,263 |
| Tỷ số Q Kratie với lịch sử cùng tháng | 346 | −0,038 | **−0,374** |
| Mưa `rainfall_mm` | 403 | −0,623 | −0,081 |
| Mực nước Tân Châu `tc_stage_t2` | 391 | −0,535 | **−0,363** |
| ONI trễ ba tháng | 403 | +0,117 | +0,290 |

Tương quan `wind_u` và mưa với EC rất mạnh trong bảng gốc **không tự chứng minh** chúng là hai biến cần nhất; nhiều tín hiệu là mùa. Sau bỏ mùa, tỷ số Q so với lịch sử cùng tháng và mực nước Tân Châu có liên hệ âm rõ hơn trong dữ liệu phát triển. Trên 2019–2023, ONI sau bỏ mùa gần 0,015; quan hệ ENSO không ổn định qua thời kỳ. Phép bỏ nhóm biến RF_compact trước đó vẫn cho thấy Q Kratie và mưa có giá trị **dự báo** trong mô hình hiện hành. Không chọn/loại biến chỉ bằng một hệ số tương quan; cần kiểm đúng ngày phát hành và MAE nhóm mùa khô/đỉnh mặn.

## 3. Kiểm nguồn và mô hình vật lý

[Eslami và cộng sự 2021](https://esurf.copernicus.org/articles/9/953/2021/index.html) cho thấy Q, triều, gió/nước dâng và đáy sông cùng chi phối mặn trong Mekong; đây là lý do thử biến tương tác, không phải bằng chứng một số `wind_u` đơn lẻ đủ đại diện triều cửa. [NOAA CPC](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/index.php) cho biết ONI là trung bình ba tháng và giá trị ban đầu có thể được cập nhật; tệp ONI hiện có **không có lịch sử phiên bản theo ngày phát hành**, vì vậy kiểm định as-of dùng ONI là theo giả định về tính sẵn có.

`tree_q90` trong script gốc là phân vị 90% của **300 dự báo trung bình ở từng cây**, không phải rừng phân vị được hiệu chuẩn hay cận trên 90% có kiểm định coverage. Hệ số đổi `100 mS/m ≈ 0,64 g/L` trong báo cáo gốc không được áp vào EC tại Mỹ Tho/cống khi thiếu EC25, thành phần ion và hiệu chuẩn địa phương. Mệnh đề “Q Kratie <2500 m³/s làm ranh 4‰ đi thêm 15–25 km” và chỉ thị đóng/mở cống trước 7–10 ngày **không được các phép thử EC tháng này xác minh**; không đưa vào sản phẩm như quy tắc vận hành.

Kiểm coverage thực nghiệm cho `tree_q90`: nhãn thực nằm **dưới hoặc bằng** đầu này ở 78,7% số tháng 2010–2018 và 66,7% số tháng 2019–2021 (ở cả +5/+35). Trong sáu tháng EC ≥100 giai đoạn 2019–2021, **bốn tháng vượt chính `tree_q90`**. Vì vậy không được ghi nó là “cận trên an toàn 90%” cho cống.

## 4. Thử tiếp có giá trị cao

Đã chạy thêm phép thử `scripts/experiment_ec_past_climatology_anomalies.py`: mỗi biến bất thường được tính bằng giá trị t−2 trừ **trung vị 15 năm trước cùng tháng**, không dùng tháng tương lai. So với RF_compact cùng tháng (+5 ngày), MAE toàn kỳ mS/m:

| Tập | RF_compact | + bất thường mực nước Tân Châu | + bất thường gió `u` | + bất thường mưa |
|---|---:|---:|---:|---:|
| 2010–2018, 108 tháng | 14,76 | 15,17 | **14,75** | 15,20 |
| 2019–2021, 36 tháng | **50,87** | 51,62 | 53,23 | 52,36 |
| 2022–2023, 24 tháng | **11,07** | 11,53 | 11,34 | 12,47 |

Biến gió bất thường gần như hòa trên lịch sử nhưng thua ở hai kỳ gần đây; các biến khác cũng không giảm MAE ổn định. Không đưa chúng vào mô hình đang phục vụ. Bảng theo mùa khô, EC cao và từng tháng ở `outputs/ec_past_anomalies_20261030/`.

1. Thu EC25/Cl⁻ cùng giờ/ngày ở Mỹ Thuận–Mỹ Tho–Vàm Kênh, các cửa và hai phía cống, cùng Q hai chiều/phân lưu, mực nước đo và datum. Khi đó mới chấm độ trễ nồng độ và hiệu chuẩn mô hình vận chuyển chất dọc nhánh.
2. Nếu chỉ có dữ liệu hiện tại, chốt RF_compact làm mốc và thử các biến **bất thường so với cùng tháng** (Q, mực nước) trên phép chấm cuốn chiếu, kèm kiểm riêng 2016/2020. Không dùng quan trắc tháng mục tiêu, ngày lấy mẫu hoặc ONI bản chỉnh sửa tương lai làm feature sẵn có.
3. Lấy nhãn EC mới 2024–2026 để đánh giá ngoài mẫu sau khi đã chốt một ứng viên. Nếu không có, không thể khẳng định mô hình nào chính xác cho cống Đồng Tháp mới hiện nay.
