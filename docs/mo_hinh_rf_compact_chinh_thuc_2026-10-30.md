# Báo cáo nghiên cứu: Mô hình dự báo EC RF_compact

**Ngày báo cáo:** 30/10/2026; hiệu đính sau rà soát ngày 01/11/2026.

**Phạm vi:** Dự báo một mẫu đo độ dẫn điện EC trong tháng tại Mỹ Tho, đơn vị mS/m; không phải trung bình tháng hay nồng độ muối quy đổi.

**Trạng thái:** Kết quả nghiên cứu hồi cứu được đóng gói vào WebGIS. Chưa đủ bằng chứng xác nhận khả năng cảnh báo vận hành hoặc quyết định đóng/mở cống.

## 1. Kết quả chính và giới hạn diễn giải

RF_compact là Random Forest dùng tám đặc trưng mùa, mưa và thủy văn. Tính lại từ dự báo đã lưu, MAE tổng thể thấp hơn Persistence trên các giai đoạn 2010–2018, 2019–2021 và 2022–2023. Đây là kết quả theo giả định về ngày dữ liệu có sẵn, không phải kiểm toán dự báo đã thực sự phát hành trong lịch sử.

Giai đoạn 2019–2021 với giả định công bố nhãn +5 ngày được dùng lựa chọn mô hình. Trường hợp +35 ngày là đánh giá độ nhạy, giữ nguyên lựa chọn RF_compact từ trường hợp +5 ngày. Giai đoạn 2022–2023 đã được xem trong quá trình nghiên cứu, nên chỉ là kiểm tra hồi cứu, **không phải tập kiểm định mù độc lập**. Các năm 2010–2018 cũng đã được khảo sát trước đó. Năm 1985 là đầu lịch sử dữ liệu huấn luyện, không phải đầu một chuỗi kiểm định độc lập kéo dài đến 2023.

MAE tổng thể thấp hơn không đồng nghĩa tốt hơn ở mọi mùa hoặc mọi thước đo. Mô hình vẫn dự báo thấp đáng kể ở các sự kiện EC cao; trong mùa khô 2022–2023, Persistence có MAE thấp hơn. Các giới hạn này cần được giữ cùng kết quả trên giao diện và artifact tải về.

## 2. Tám đặc trưng đầu vào

Gọi `t` là tháng đích. Các biến quan trắc dùng tháng `t−2`; biến mùa biểu diễn tháng đích. Chúng là biến dự báo thống kê có liên hệ thủy văn hợp lý, không chứng minh quan hệ nhân quả hoặc mô phỏng truyền mặn.

| Đặc trưng | Định nghĩa trong mã nguồn |
|---|---|
| `month_sin` | `sin(2*pi*month/12)`, mã hóa chu kỳ mùa. |
| `month_cos` | `cos(2*pi*month/12)`, thành phần còn lại của mã hóa mùa; không phải phép đo pha triều. |
| `rainfall_mm` | Tổng lượng mưa ERA5 tại Mỹ Tho của tháng `t−2`, đơn vị mm. |
| `kratie_q_t2` | Trung bình lưu lượng Kratie tháng `t−2`, từ giá trị ngày, đơn vị m³/s; tháng cần ít nhất 20 ngày quan trắc. |
| `kratie_q3_t2` | Trung bình trượt ba tháng kết thúc ở `t−2`, cần ít nhất hai tháng hợp lệ. |
| `kratie_q_ratio_t2` | Lưu lượng tháng nguồn chia trung vị cùng tháng của tối đa 15 năm trước, cần ít nhất năm giá trị lịch sử; tỷ số chặn trong khoảng 0–5. |
| `tc_stage_t2` | Trung vị các mực nước ngày tại Tân Châu trong tháng `t−2`, đơn vị m; mỗi ngày dùng trung vị số đo, tháng cần ít nhất 20 ngày. |
| `tc_stage3_t2` | **Trung vị trượt** ba tháng của mực nước tháng, kết thúc ở `t−2`, cần ít nhất hai tháng hợp lệ. |

Việc chọn bộ biến gọn là lựa chọn thực nghiệm trong các ứng viên đã thử. Kết quả hiện có không chứng minh đây là bộ biến tối ưu toàn cục, cũng không chứng minh gió hay ENSO không có giá trị dự báo ở dữ liệu khác.

## 3. Cấu hình và giao thức hồi cứu

| Thành phần | Cấu hình tạo các kết quả báo cáo |
|---|---|
| Thuật toán | `RandomForestRegressor` |
| `n_estimators` | 100 |
| `max_depth` | 7 |
| `min_samples_leaf` | 3 |
| `max_features` | 0.8 |
| `random_state` | 42 |
| Tiền xử lý | `SimpleImputer(strategy='median', add_indicator=True, keep_empty_features=True)` |
| Trọng số mẫu | Đồng đều đối với RF_compact; không phải các ứng viên tăng trọng số EC cao. |

Các giá trị này khớp `scripts/experiment_ec_extreme_robust.py` và `outputs/ec_compact_candidate_20261029/manifest.json`. Bộ điền khuyết được fit trong tập huấn luyện của mỗi lượt hồi cứu.

Với tháng đích `t`, ngày phát hành giả định là ngày 06 của tháng `t−1`. Mô hình được huấn luyện lại theo từng thời điểm, lọc nhãn EC theo giả định công bố sau cuối tháng **5 ngày hoặc 35 ngày**. Khí tượng và thủy văn dùng tháng `t−2`, giả định có sẵn sau cuối tháng nguồn 5 ngày.

MRC/ERA5 không có đầy đủ lịch sử phiên bản và dấu thời gian công bố thật. Việc lọc thời gian chỉ kiểm tra tính nhất quán với giả định đã đặt ra; không đủ cơ sở khẳng định “zero look-ahead bias” ngoài thực tế. Tên thí nghiệm `LAG0` và `LAG30` trên WebGIS là định danh kế thừa; độ trễ nhãn tương ứng ở đây là **5 và 35 ngày**.

## 4. Kết quả tính từ dự báo đã lưu

### MAE tổng thể, đơn vị mS/m

| Giai đoạn | Số tháng | Persistence | RF_old | RF_compact | Giảm MAE so với Persistence |
|---|---:|---:|---:|---:|---:|
| Lịch sử 2010–2018, +5 ngày | 108 | 22.17 | — | 14.76 | 33.4% |
| Lựa chọn 2019–2021, +5 ngày | 36 | 93.39 | 71.56 | 50.87 | 45.5% |
| Lựa chọn 2019–2021, +35 ngày | 36 | 125.84 | 71.26 | 55.30 | 56.1% |
| Hồi cứu 2022–2023, +5 ngày | 24 | 12.62 | 18.63 | 11.07 | 12.3% |
| Hồi cứu 2022–2023, +35 ngày | 24 | 15.09 | 18.61 | 11.25 | 25.5% |

Dấu “—” nghĩa là bộ dự báo lịch sử được dẫn ở đây không có cột RF_old để đối chiếu cùng 108 tháng. Các giá trị được làm tròn sau tính toán; phần trăm cải thiện dùng giá trị chưa làm tròn.

### Nhóm mùa khô và EC cao, 2019–2021, +5 ngày

| Nhóm | Số tháng | MAE Persistence | MAE RF_old | MAE RF_compact |
|---|---:|---:|---:|---:|
| Toàn bộ | 36 | 93.39 | 71.56 | 50.87 |
| Mùa khô, tháng 12–4 | 15 | 109.66 | 128.94 | 106.86 |
| EC ≥ 100 mS/m | 6 | 305.71 | 324.24 | 259.37 |

Sáu tháng EC cao gồm bốn tháng năm 2020 và hai tháng năm 2021. RF_compact dự báo thấp hơn thực tế ở cả sáu tháng. Ví dụ tháng 02/2020: thực tế **558.0**, dự báo **98.86**; tháng 03/2020: thực tế **692.0**, dự báo **182.48** mS/m. Ngưỡng 100 mS/m ở đây chỉ dùng phân nhóm đánh giá, không tự động là ngưỡng điều hành cống.

### Những trường hợp Persistence vẫn tốt hơn, 2022–2023

| Thước đo | Độ trễ nhãn | Persistence | RF_compact |
|---|---|---:|---:|
| RMSE toàn bộ 24 tháng | +5 ngày | 18.91 | 24.95 |
| MAE mùa khô, 10 tháng | +5 ngày | 16.91 | 22.22 |
| RMSE toàn bộ 24 tháng | +35 ngày | 20.68 | 24.74 |
| MAE mùa khô, 10 tháng | +35 ngày | 16.07 | 22.37 |

Kỳ 2022–2023 không có mẫu EC ≥ 100 mS/m, nên không xác nhận được khả năng tổng quát hóa sang một đợt cực đoan mới. Nghiên cứu cũng chưa có nhãn EC sau năm 2023 để kiểm chứng dự báo năm 2026.

## 5. Đối chiếu với Adaptive Q50/Q90

Các MAE dưới đây dùng giả định nhãn +5 ngày và cùng nhóm tháng:

| Giai đoạn | RF_compact | Adaptive Q50/Q90 |
|---|---:|---:|
| 2010–2018, 108 tháng | 14.76 | 20.66 |
| 2019–2021, 36 tháng | 50.87 | 46.17 |
| 2022–2023, 24 tháng | 11.07 | 16.23 |

Adaptive có MAE thấp hơn trong giai đoạn 2019–2021, kể cả nhóm sáu tháng EC cao (201.64 so với 259.37 mS/m), nhưng MAE cao hơn ở hai giai đoạn còn lại. Đây là đánh đổi thực nghiệm, không chứng minh Adaptive sai ở mọi tháng còn lại hoặc RF_compact ưu việt trên mọi tiêu chí. RF_compact được giữ làm ứng viên nghiên cứu hiển thị trong các artifact hiện tại; cần đánh giá dữ liệu mới trước khi quyết định triển khai vận hành.

## 6. Phạm vi WebGIS và tái tạo artifact

Trong `workspace.html`, mục “Dự báo EC” (`#forecasts`) hiển thị kết quả hồi cứu của `MYTHO_MONTHLY_LAG0` và `MYTHO_MONTHLY_LAG30`. Việc chọn RF_compact ở đây là chọn bộ kết quả nghiên cứu đã đóng gói. **Form dự báo trực tiếp dùng năm đặc trưng khí tượng là luồng mô hình riêng**, không tự chuyển thành RF_compact tám đặc trưng khi cập nhật workspace. Không dùng MAE của RF_compact để mô tả độ chính xác của form đó.

Từ thư mục gốc dự án, trong môi trường Python đã cài phụ thuộc, tái tạo hai bộ artifact và cập nhật chỉ mục WebGIS bằng:

```powershell
python -m scripts.pack_rf_compact_run
python -m scripts.pack_rf_compact_lag30
python -m scripts.update_workspace_with_rf_compact
```

Quy trình đóng gói dùng kết quả nghiên cứu đã lưu; không thay thế việc chạy lại huấn luyện/backtest. Kiểm tra `predictions.csv`, `metrics.csv`, `run_manifest.json` và biểu đồ của từng run sau tái tạo. Mọi dự báo tương lai cần có ngày phát hành, tháng nguồn, cấu hình và nguồn gốc phép tính tương ứng; không suy ra dự báo mới chỉ từ bảng MAE.

`high_ec_metrics.csv` dùng ngưỡng P90 tính từ các nhãn có sẵn tại ngày phát hành đầu tiên của giai đoạn lựa chọn 2019–2021, rồi giữ ngưỡng đó khi đánh giá hồi cứu. Định nghĩa này khác nhóm EC ≥ 100 mS/m trong các bảng trên; ngưỡng, số mẫu và sai số được tính từ dữ liệu, ghi trong manifest của từng giả định độ trễ.

`next_forecast.json` được tính lại bằng thuật toán RF_compact cho tháng sau mẫu EC cuối, với tập huấn luyện khả dụng tại ngày phát hành giả định. Đây là kết quả nghiên cứu lưu cho tháng 01/2024, không phải dự báo hiện thời. Biểu đồ được vẽ từ chính `predictions.csv` của run; dữ liệu quan trắc gốc không được thay bằng dự báo.

## 7. Nguồn đối chiếu

- `outputs/ec_extreme_robust_20261029/predictions_5d.csv` và `predictions_35d.csv`: dự báo từng tháng 2019–2023.
- `outputs/ec_compact_history_20261029/predictions_2010_2018.csv`: đối chiếu 108 tháng lịch sử.
- `outputs/ec_compact_summary_20261029/matched_metrics.csv`: MAE, RMSE và bias theo cùng nhóm tháng.
- `outputs/ec_adaptive_asof_audit_20261030/metrics.csv`: đối chiếu Adaptive.
- `outputs/ec_compact_candidate_20261029/manifest.json`: cấu hình, thứ tự đặc trưng và giới hạn của ứng viên nghiên cứu (`deployment_ready=false`, `gate_decision_eligible=false`).
- `docs/ec_compact_recalibration_2026-10-29.md`: giao thức và giới hạn nghiên cứu ban đầu.
