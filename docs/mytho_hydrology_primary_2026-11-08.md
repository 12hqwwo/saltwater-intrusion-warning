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

## Phụ lục 19/11/2026: thử chọn lại đặc trưng và thêm chỉ số El Niño

**Câu hỏi:** các biến có `feature_importance` thấp có thể bỏ đi, hoặc thêm ONI (chỉ số ENSO lưu trong dự án), để giảm lỗi EC Mỹ Tho không? Đây là thử nghiệm hồi cứu, không thay model đang phục vụ.

Thí nghiệm ENSO ngày 29/10 đã có trong `scripts/experiment_ec_enso_climate.py`, nhưng dùng RF 100 cây và giao thức rolling origin. Điểm số của nó không thể so trực tiếp với RF 300 cây và giao thức mất EC liên tục của model hiện hành; phần dưới thử ONI lại trong cùng giao thức với `full10`.

### Dữ liệu và cách so sánh

- Dùng `data_matrix(5)` và `data_matrix(35)` của `tools/feature_building.py`; lần lượt giả định nhãn EC sẵn có sau cuối tháng 5 hoặc 35 ngày. Mỗi kỳ mất EC dùng `freeze_training` của `scripts/evaluate_frozen_ec_gap.py`, fit một lần trước kỳ mất EC, chỉ dùng nhãn trong kỳ để chấm. Các cửa sổ: 2019–2021 (36 tháng), 2021–2023 (36 tháng), 2022–2023 (24 tháng). Hai cửa sổ sau **chồng lấn**, không được cộng như hai tập kiểm định độc lập.
- Mọi phương án cùng `pipeline()` trong `tools/model_training.py`: impute trung vị và Random Forest 300 cây, `max_depth=8`, `min_samples_leaf=3`, seed 42, `n_jobs=1`. Chỉ đổi danh sách cột, giữ nguyên tháng huấn luyện và tháng đánh giá. Dự báo `full10` tái lập đúng từng giá trị `WeatherHydrology` đã công bố trong `outputs/frozen_ec_remedies_20261108/predictions.csv` (sai lệch tuyệt đối tối đa dưới `1e-8`).
- ONI lấy từ `data/external/climate_indices_20261029/oni_monthly.csv` (SHA-256 `f128e6262960f5516779a6d54ea001bf1d53586dc448a36ef93d9c7b8117d649`), dùng giá trị có **tháng tâm `t−4`** cho tháng EC đích `t`. ONI tháng tâm `t−4` phản ánh ba tháng SST kết thúc ở `t−3`; đây là giả định trễ bảo thủ, nhưng **không có bản lưu ngày phát hành/vintage lịch sử** để chứng minh từng giá trị đã biết ở ngày phát hành dự báo.
- Tám tập cột được xác định trước một lượt chạy: `full10`; bỏ `month_sin, month_cos` (`no_calendar`); bỏ hai mực nước Tân Châu (`no_stage`); bỏ nhiệt độ và gió (`no_temp_wind`); chỉ giữ mưa và ba biến lưu lượng Kratie (`core4`); bỏ mưa (`no_rain`, đối chứng); `full10` cộng `oni_t4`; và `core4` cộng `oni_t4`. Không đổi cấu hình RF hoặc chọn lại tham số theo kết quả.

Để tái lập phép so sánh, với mỗi `delay` và mỗi cửa sổ trong `EXPERIMENTS`, lấy `frame = data_matrix(delay)`, gắn `oni_t4` bằng cách ánh xạ `frame.month_start - 4 tháng` sang chuỗi ONI, rồi lấy `known = freeze_training(frame, start, delay)` và các dòng `start..end` làm tập dự báo. Với từng danh sách cột ở trên, fit `pipeline().set_params(randomforestregressor__n_jobs=1)` trên `known[columns]` và EC của `known`, dự báo chỉ từ `future[columns]`, sau đó mới lấy EC bị giữ lại để tính MAE, RMSE và số tháng bỏ sót/báo cao giả tại ngưỡng 100. Thử nghiệm chạy trong bộ nhớ, không ghi artifact mới.

### Kết quả chính: độ trễ nhãn EC +5 ngày

MAE/RMSE đều tính bằng mS/m. `Bỏ sót 2019–21` là số tháng EC thực ≥100 mS/m nhưng dự báo <100; ngưỡng này chỉ để chẩn đoán, không phải chuẩn vận hành cống.

| Tập đặc trưng | 2019–21 MAE / RMSE | Bỏ sót 2019–21 | 2021–23 MAE / RMSE | 2022–23 MAE / RMSE |
| --- | ---: | ---: | ---: | ---: |
| `full10` hiện hành | 57,808 / 133,815 | 2 | 16,569 / 31,210 | 12,190 / 25,431 |
| `no_calendar` | 57,454 / 133,076 | 2 | 16,744 / 31,732 | 12,199 / 24,812 |
| `no_stage` | 58,730 / 135,571 | 2 | 17,635 / 34,075 | 12,040 / 24,625 |
| `no_temp_wind` | **56,696** / 133,040 | **3** | 16,506 / 30,154 | 13,387 / 28,887 |
| `core4` | 56,788 / 132,982 | 2 | 17,349 / 32,546 | 13,350 / 27,534 |
| `no_rain` | 65,534 / 158,584 | 3 | 18,890 / 37,641 | 13,726 / 28,472 |
| `full10_ONI_t4` | 60,033 / 143,063 | 2 | **16,168** / **30,420** | **11,475** / **23,107** |
| `core4_ONI_t4` | 58,567 / 140,907 | 3 | 17,773 / 33,839 | 13,051 / 25,852 |

Kiểm độ nhạy +35 ngày giữ cùng kết luận: `full10` đạt MAE 57,908 ở 2019–21 và 12,126 ở 2022–23; `no_calendar` là 57,552 và 12,081; `full10_ONI_t4` là 60,007 và 11,362. ONI cải thiện kỳ gần đây nhưng làm kỳ cực trị xấu hơn dưới cả hai giả định độ trễ.

Mẫu 03/2020 có EC nguồn **692 mS/m**. `full10` dự báo 213,665; `no_calendar` 207,619; `no_temp_wind` 219,324; `full10_ONI_t4` chỉ 177,980. Vì vậy, giảm MAE trung bình ở một cửa sổ không có nghĩa là giảm rủi ro bỏ hụt đỉnh mặn.

### Kết luận và giới hạn

- **Không thay tập 10 biến hiện hành.** Bỏ mưa làm lỗi tăng rõ ở cả ba cửa sổ. Bỏ biến có trọng số thấp chỉ đem lại cải thiện nhỏ hoặc không nhất quán; `no_temp_wind` có MAE 2019–21 thấp nhất nhưng bỏ sót thêm một tháng EC cao và làm 2022–23 xấu hơn. `no_calendar` cải thiện rất nhỏ ở 2019–21, song MAE 2021–23 và 2022–23 không giảm.
- **Chưa thêm ONI vào model chính.** `full10_ONI_t4` giảm MAE 2022–23 từ 12,190 xuống 11,475 nhưng tăng MAE 2019–21 từ 57,808 lên 60,033 và hạ dự báo đỉnh 03/2020 thêm khoảng 35,7 mS/m. Nguồn ONI hiện có giá trị đến tháng tâm 08/2026; tháng đích 01/2027 sẽ cần ONI 09/2026 theo quy tắc `t−4`, hiện còn thiếu.
- Các cửa sổ đã từng được xem trong những lần phát triển trước, nên đây là **khảo sát sau khi biết dữ liệu**, không phải kiểm định mù hay bằng chứng về độ chính xác vận hành tương lai. `feature_importance` của RF phân chia độ giảm impurity giữa các biến tương quan; trọng số thấp không chứng minh biến vô ích. Cần nhãn EC độc lập sau 2023 và lịch công bố đầu vào thật trước khi cân nhắc thay model.

### Thử thay thế trực tiếp các biến trọng số thấp

Sau lượt bỏ biến ở trên, thử các **biến thay thế thật** trên cùng cohort, cùng `pipeline()` RF 300 cây và cùng quy tắc đóng băng nhãn EC. Nhóm luôn giữ là mưa và ba biến lưu lượng Kratie. Các tên viết tắt: `TW` = nhiệt độ + gió; `CAL` = sin/cos tháng; `TC` = hai biến mực nước Tân Châu; `MT` = hai biến mực nước Mỹ Thuận; `ONI` = `oni_t4`; `wet` = tỷ lệ lưu lượng trung bình mùa mưa Kratie gần nhất so với trung vị mùa mưa trước (`kratie_wet_ratio_last`, tính chỉ từ tháng không muộn hơn tháng đầu vào). `soil` và `windU/V` là độ ẩm đất/hai thành phần gió ERA5 tháng `t−2`.

| Thay thế (các biến khác giữ nguyên) | 2019–21 MAE / RMSE | 2021–23 MAE / RMSE | Bỏ sót EC ≥100 ở 2021–23 | 2022–23 MAE / RMSE |
| --- | ---: | ---: | ---: | ---: |
| `full10` đối chứng | 57,808 / 133,815 | 16,569 / 31,210 | 1 | 12,190 / 25,431 |
| `TW → ONI + wet` | 59,003 / 143,289 | 17,259 / 30,167 | 0 | 13,243 / 28,457 |
| `CAL → ONI + wet` | 59,400 / 143,003 | 17,190 / 30,639 | 0 | 12,268 / 24,756 |
| `TC → MT` | 58,145 / 133,467 | 16,435 / 33,237 | **2** | **10,350 / 19,441** |
| Cả sáu biến yếu `→ ONI + wet + MT` | 57,978 / 140,272 | 17,715 / 32,053 | 1 | 12,305 / 23,521 |
| `TW → soil + windU` | 62,886 / 141,262 | 19,825 / 42,233 | 2 | 13,688 / 30,407 |
| `TW → windU + windV` | 62,345 / 141,729 | 19,499 / 41,596 | 2 | 13,219 / 29,850 |
| Sáu biến yếu `→ ONI + wet + MT + soil + windU` | 64,245 / 145,698 | 18,783 / 39,138 | 2 | 11,847 / 23,847 |
| `TC → ONI + wet` (kiểm nguồn hiện có) | 59,824 / 143,784 | 17,908 / 32,617 | 0 | 12,806 / 25,874 |

`TC → MT` giảm MAE 2022–23 **1,840 mS/m (15,1%)** và RMSE **5,990 mS/m (23,6%)** so với `full10`, đồng thời số báo cao giả tại ngưỡng chẩn đoán 100 mS/m giảm từ 2 xuống 0. Tuy nhiên, MAE 2019–21 tăng 57,808→58,145; trong cửa sổ 2021–23, RMSE tăng 31,210→33,237 và số tháng EC cao bị bỏ sót tăng từ 1 lên 2. Kết quả +35 ngày giữ cùng chiều: MAE 2022–23 là 10,278 so với 12,126, nhưng RMSE 2021–23 là 33,638 so với 31,537.

**Khả năng dùng cho tháng đích 12/2026:** `mt_stage_t2` từ nguồn MRC chỉ đủ ngày đến **12/2023** (`mt_stage3_t2` hữu hạn đến 01/2024), nên không có giá trị tháng đầu vào 10/2026. Nguồn ERA5 extra cho `soil` và `windU/V` chỉ đến **08/2026**, cũng thiếu 10/2026. ONI `t−4` cần 08/2026 và `wet` cần Kratie đến 10/2026, hai giá trị này hiện có; nhưng phương án `TC → ONI + wet` làm MAE tăng ở cả ba cửa sổ. Mọi phương án thay thế đều cần adapter đầu vào và kiểm ngày công bố thực tế trước khi xét triển khai.

Vì vậy, **Mỹ Thuận thay Tân Châu là ứng viên nghiên cứu đáng theo dõi**, không phải phương án đã chứng minh tốt hơn toàn kỳ hoặc có thể dùng ngay. Không đổi model, registry, dự báo đã lưu hay dữ liệu DB. Các lần thử này dùng lại cửa sổ đã được xem; không chọn phương án để báo cáo như một kiểm định độc lập.
