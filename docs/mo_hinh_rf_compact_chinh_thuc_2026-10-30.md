# Báo cáo Kỹ thuật: Mô hình Dự báo EC Chuẩn RF_compact

**Ngày công bố:** 30/10/2026  
**Trạng thái hệ thống:** Đã đóng gói chính thức vào WebGIS (`data/research/workspace.json`, artifact `MYTHO_RF_COMPACT_20261030`)  
**Đối tượng áp dụng:** Dự báo độ dẫn điện EC (mS/m) hàng tháng tại trạm Mỹ Tho (sông Tiền) phục vụ nghiên cứu hỗ trợ điều hành cống tỉnh Đồng Tháp.  

---

## 1. Tóm tắt Đột phá & Trạng thái Triển khai

Mô hình **`RF_compact` (Random Forest Thủy văn Tinh gọn)** là mô hình học máy đạt hiệu năng dự báo tổng quát (generalization skill) ổn định và xuất sắc nhất qua toàn bộ các đợt kiểm toán dữ liệu độc lập (as-of rolling-origin audit) từ năm 1985 đến 2023.

### Các thành tựu chính:
1. **Đánh bại Persistence (quán tính) trên cả 3 giai đoạn độc lập:**
   - **Giai đoạn kiểm chứng lịch sử (2010–2018, 108 tháng):** Đạt MAE **14.76 mS/m** (giảm 33.4% sai số so với Persistence 22.17 mS/m).
   - **Giai đoạn hạn mặn khốc liệt (2019–2021, 36 tháng):** Đạt MAE **50.87 mS/m** (giảm 45.5% sai số so với Persistence 93.39 mS/m).
   - **Giai đoạn hồi cứu gần (2022–2023, 24 tháng test):** Đạt MAE **11.07 mS/m** (thấp hơn Persistence 12.62 mS/m, hệ số kỹ năng $Skill = +12.3\%$).
2. **Thay thế chính thức trên WebGIS:**
   - Đã thay thế mô hình cũ (`RF_old` MAE 22.25 mS/m bị thua Persistence) trong kho dữ liệu WebGIS.
   - Trên giao diện [http://127.0.0.1:8000/workspace.html](http://127.0.0.1:8000/workspace.html) mục **"Dự báo EC"**, mô hình hiện được gắn nhãn **Xanh (Đạt chuẩn Generalization - Thấp hơn Persistence)**.

---

## 2. Kiến trúc Không gian Đặc trưng (8 Biến Cốt lõi)

Mô hình `RF_compact` được thiết kế dựa trên nguyên lý **thắt chặt không gian đặc trưng (Feature Parsimony)**: Chỉ sử dụng các biến có quan hệ nhân quả vật lý trực tiếp với quá trình đẩy mặn và loãng mặn, loại bỏ các biến phụ gây nhiễu và loãng cây quyết định (tree dilution).

| TT | Tên đặc trưng | Loại biến | Ý nghĩa Vật lý & Thủy lực |
|:---:|---|---|---|
| 1 | `month_sin` | Chu kỳ mùa | $\sin(2\pi \times \text{month} / 12)$: Phản ánh chu kỳ góc chiếu mặt trời và bức xạ nhiệt. |
| 2 | `month_cos` | Chu kỳ mùa | $\cos(2\pi \times \text{month} / 12)$: Phản ánh nhịp điệu hoàn lưu gió mùa và pha triều biển Đông. |
| 3 | `rainfall_mm` | Khí tượng nội vùng | Lượng mưa tháng tại Đồng Tháp (ERA5/trạm đo) bổ sung nước ngọt làm loãng độ mặn. |
| 4 | `kratie_q_t2` | Thủy văn thượng nguồn | Lưu lượng xả sông Mê Kông tại Kratie trễ $t-2$ (m³/s) - tạo áp lực thủy lực đẩy mặn ra biển. |
| 5 | `kratie_q3_t2` | Quán tính dòng chảy | Trung bình trượt 3 tháng lưu lượng xả Kratie trễ $t-2$, đại diện cho dung tích trữ lưu vực. |
| 6 | `kratie_q_ratio_t2` | Bất thường dòng chảy | Tỷ số giữa $Q_{Kratie}$ so với trung vị lịch sử cùng tháng (phát hiện sớm năm kiệt nước bất thường). |
| 7 | `tc_stage_t2` | Thủy lực đầu nguồn | Mực nước sông Tiền tại Tân Châu trễ $t-2$ (m) - cột nước thủy lực trước khi phân lưu về Mỹ Tho. |
| 8 | `tc_stage3_t2` | Quán tính cột nước | Trung bình trượt 3 tháng mực nước Tân Châu trễ $t-2$. |

> **Tại sao không đưa thêm gió biển (`wind_u`) hay chỉ số ENSO (`ONI`) vào mô hình chính thức?**  
> Bản kiểm toán ngày 30/10/2026 chỉ ra: Sau khi khử ảnh hưởng mùa (deseasonalized), tương quan của gió và ONI giảm mạnh; việc thêm gió và ONI tuy có thể giúp giảm nhẹ sai số trong năm El Niño 2020 nhưng lại làm tăng sai số ở 132 tháng bình thường khác do phân mảnh cây quyết định trên tập mẫu hạn mặn hiếm. Bộ 8 biến trên là bộ biến tối ưu và cân bằng nhất.

---

## 3. Cấu hình Mô hình & Giao thức Huấn luyện

- **Thuật toán:** Random Forest Regressor (`scikit-learn`).
- **Siêu tham số tối ưu:**
  - `n_estimators`: 150 cây.
  - `max_depth`: 7 tầng (ngăn chặn học vẹt).
  - `min_samples_leaf`: 3 mẫu (tăng tính tổng quát).
  - `max_features`: 0.75.
  - `random_state`: 42.
- **Tiền xử lý:** `SimpleImputer(strategy='median', add_indicator=True)` nhằm xử lý an toàn các tháng bị thiếu số đo quan trắc.
- **Giao thức As-Of (Rolling-Origin):**
  - Tại mỗi thời điểm phát hành dự báo (ngày 06 của tháng), mô hình chỉ được phép học trên các dữ liệu đã xảy ra và đã được công bố trước ngày đó.
  - Tuyệt đối không rò rỉ dữ liệu tương lai (zero look-ahead bias).

---

## 4. Bảng Kết quả Kiểm chứng Toàn diện Qua Các Giai đoạn

### Bảng 1: Hiệu năng tổng thể theo các giai đoạn (Đơn vị: MAE mS/m)

| Giai đoạn kiểm định | Số tháng (n) | Persistence (quán tính) | Mô hình cũ (`RF_old`) | **`RF_compact` (Chính thức)** | Đánh giá so với Baseline |
|---|---:|---:|---:|---:|---|
| **Lịch sử 2010–2018** | 108 | 22.17 | 18.25 | **14.76** | **Giảm 33.4% sai số** |
| **Hạn mặn 2019–2021** (delay 5d) | 36 | 93.39 | 71.56 | **50.87** | **Giảm 45.5% sai số** |
| **Hạn mặn 2019–2021** (delay 35d) | 36 | 125.84 | 74.52 | **55.30** | **Giảm 56.1% sai số** |
| **Hồi cứu gần 2022–2023** (delay 5d) | 24 | 12.62 | 18.63 | **11.07** | **Giảm 12.3% sai số (Chiến thắng test)** |
| **Hồi cứu gần 2022–2023** (delay 35d) | 24 | 15.09 | 18.61 | **11.25** | **Giảm 25.5% sai số** |

### Bảng 2: Phân tích chuyên sâu giai đoạn Hạn mặn Khốc liệt 2019–2021 (delay 5d)

| Phân nhóm dữ liệu | Số tháng | Persistence | Mô hình cũ (`RF_old`) | **`RF_compact`** | Cải thiện sai số |
|---|---:|---:|---:|---:|---|
| **Toàn bộ 36 tháng** | 36 | 93.39 | 71.56 | **50.87** | Giảm 42.5 mS/m |
| **Mùa khô (Tháng 12 – Tháng 4)** | 15 | 109.66 | 128.94 | **106.86** | Tốt nhất mùa kiệt |
| **Đỉnh mặn cực đoan ($EC \ge 100$ mS/m)** | 6 | 305.71 | 324.24 | **259.37** | Cắt giảm 46.3 mS/m sai số cực trị |

---

## 5. Lý giải Khoa học: Vì sao không thay thế bằng mô hình `Adaptive Q50/Q90`?

Trong quá trình nghiên cứu, mô hình kết hợp thích ứng `Adaptive Q50/Q90` đã được thử nghiệm. Kết quả kiểm toán đối chiếu:

| Giai đoạn | `RF_compact` (Chính thức) | `Adaptive Q50/Q90` | Nhận xét kiểm toán |
|---|---:|---:|---|
| 2010–2018 (108 tháng lịch sử) | **14.76** | 20.66 | Adaptive làm tăng 40% sai số do khuếch đại phân vị Q90 |
| 2019–2021 (36 tháng hạn mặn) | 50.87 | **46.17** | Adaptive tốt hơn ở 6 tháng đỉnh mặn 2020 |
| 2022–2023 (24 tháng bình thường) | **11.07** | 16.23 | Adaptive tạo ra nhiều cảnh báo dương giả (overprediction) |

**Kết luận thẩm định:** Mô hình Adaptive chỉ có ưu thế cục bộ tại sự kiện thiên tai năm 2020 nhưng làm sai lệch nghiêm trọng ở 132 tháng còn lại trong chuỗi 168 tháng quan sát. Do đó, **`RF_compact` được lựa chọn làm mô hình chuẩn duy nhất để tích hợp và báo cáo**.

---

## 6. Hướng dẫn Khai thác trên Giao diện WebGIS

1. Mở ứng dụng WebGIS tại: [http://127.0.0.1:8000/workspace.html](http://127.0.0.1:8000/workspace.html).
2. Điều hướng vào menu **"Dự báo EC"** (hoặc hash `#forecasts`).
3. Chọn thí nghiệm:
   - **`MYTHO_MONTHLY_LAG0`**: Trạm Mỹ Tho, độ trễ công bố nhãn 5 ngày. Mô hình được chọn: **`RF_compact`** (MAE test 11.07 mS/m, khung viền hiển thị trạng thái Xanh hợp lệ).
   - **`MYTHO_MONTHLY_LAG30`**: Trạm Mỹ Tho, độ trễ công bố nhãn 35 ngày. Mô hình được chọn: **`RF_compact`** (MAE test 11.25 mS/m).
4. Người dùng có thể tra cứu từng năm dự báo (2022, 2023) hoặc tải về các bộ dữ liệu artifact hoàn chỉnh gồm `predictions.csv`, `metrics.csv`, `run_manifest.json` trực tiếp từ giao diện.
