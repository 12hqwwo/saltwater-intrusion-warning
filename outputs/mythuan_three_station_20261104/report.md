# Kiểm chứng Mỹ Thuận và nội suy ba trạm · 04/11/2026

Báo cáo Bước 1 và Bước 2; chưa thay registry, database hoặc giao diện.

## Giao thức

- Đúng ba trạm: Tân Châu → Mỹ Thuận → Mỹ Tho. EC mS/m, một mẫu/tháng; không đổi sang g/L.
- Mỹ Thuận: 451 mẫu 05/1985–12/2023. Giữ QA UNVERIFIED và cơ sở bù nhiệt UNKNOWN.
- Giữ nguyên RF 300 cây, sâu 8, lá tối thiểu 3, seed 42; mưa/nhiệt/gió ERA5 tháng t−2 và sin/cos tháng mục tiêu. Không chọn siêu tham số từ kỳ 2022–2023.
- Rolling-origin giống backtest hiện có: phát hành ngày 06 tháng t−1; mỗi lần chỉ dùng nhãn đã khả dụng và khí tượng đã khả dụng. EC giả định công bố cuối tháng +5 ngày; +35 ngày là độ nhạy. ERA5 cuối tháng +5 ngày.
- 2019–2021 là kỳ validation; 2022–2023 là kiểm tra hồi cứu đã được xem trước trong dự án, không phải holdout mù mới. Mô hình được huấn luyện lại từng ngày phát hành bằng tập quá khứ đang khả dụng.
- Persistence dùng mẫu gần nhất đã khả dụng; MonthlyClimatology dùng trung bình đúng tháng trong tập huấn luyện đang khả dụng. Cùng cohort cho mọi phương án.
- Khí tượng Mỹ Thuận được tải tại tọa độ MRC của chính trạm, không lấy khí tượng Mỹ Tho thay thế. Bản ERA5 hồi cứu hiện có không phải bản phát hành lịch sử.

## Bước 1 — Dự báo EC Mỹ Thuận, 2022–2023 (+5 ngày)

| Mô hình | n | MAE (mS/m) | RMSE (mS/m) |
|---|---:|---:|---:|
| RandomForest | 24 | 3.917425 | 4.856469 |
| Persistence | 24 | 4.806250 | 5.772399 |
| MonthlyClimatology | 24 | 3.956993 | 4.720397 |

## Bước 2 — Ước tính tại Mỹ Thuận, 2022–2023 (+5 ngày)

Tọa độ Mỹ Thuận: [105.9263229, 10.27532005]; chiếu lên trục hiện tại tại km 85.217605 trong đoạn 0–125 km. Tỷ lệ dọc tuyến 0.681740840; khoảng cách đến trục 0.863 km. Giữ nguyên hình học và công thức trước khi xem sai số.

| Phương án | n | MAE (mS/m) | RMSE (mS/m) |
|---|---:|---:|---:|
| TWO_OBSERVED_LINEAR | 24 | 5.442903 | 9.838450 |
| TWO_FORECAST_LINEAR | 24 | 11.250346 | 33.124660 |
| THREE_FORECAST_ANCHOR | 24 | 3.917425 | 4.856469 |
| TWO_OBSERVED_IDW2 | 24 | 6.527530 | 11.747552 |
| TWO_FORECAST_IDW2 | 24 | 13.608517 | 40.230285 |

LINEAR là phép nội suy theo khoảng cách dọc sông của lớp phủ dự báo hiện tại; IDW2 kiểm độ nhạy với công thức mô phỏng lịch sử. TWO_OBSERVED là tái dựng hồi cứu từ quan trắc cùng tháng ở hai đầu mút, không phải đầu vào có sẵn tại ngày phát hành dự báo.

THREE_FORECAST_ANCHOR dùng dự báo Mỹ Thuận ngoài mẫu tại đúng vị trí Mỹ Thuận; không dùng EC thực đo Mỹ Thuận làm điểm neo khi chấm. Vì vậy sai số tại đây bằng sai số mô hình Mỹ Thuận ở Bước 1. Kết quả chỉ chứng minh tại vị trí trung lưu này, không đo được sai số toàn tuyến sông.

Các mẫu ghép cùng tháng không mặc nhiên cùng ngày hoặc cùng pha triều. interpolation_metrics.csv có thêm cohort cùng ngày của cả ba trạm; interpolation_predictions.csv giữ ngày mẫu từng trạm.

## Mức thay đổi so với hai trạm

Giảm (%) = 100 × (lỗi hai trạm − lỗi điểm neo Mỹ Thuận dự báo) / lỗi hai trạm. Giá trị âm là sai số tăng.

| So với | Giảm MAE (%) | Giảm RMSE (%) |
|---|---:|---:|
| TWO_OBSERVED_LINEAR | 28.027 | 50.638 |
| TWO_FORECAST_LINEAR | 65.180 | 85.339 |
| TWO_OBSERVED_IDW2 | 39.986 | 58.660 |
| TWO_FORECAST_IDW2 | 71.213 | 87.928 |

## Tái tạo và tệp kết quả

```powershell
.venv/Scripts/python.exe scripts/evaluate_mythuan_three_station.py --fetch-weather
.venv/Scripts/python.exe -m unittest tests.test_mythuan_three_station
```

- targets.csv / feature_matrix.csv: nhãn và đặc trưng theo trạm/tháng.
- predictions.csv / model_metrics.csv: dự báo, ngày phát hành, tháng nhãn cuối khả dụng, MAE/RMSE cho ba trạm, hai giả định trễ.
- interpolation_predictions.csv / interpolation_metrics.csv / improvements.csv: từng tháng, cùng ngày, và tỷ lệ thay đổi.
- source_audit.csv / run_manifest.json: kiểm kê và checksum nguồn, giao thức, hình học, phiên bản thư viện và checksum đầu ra.
- mythuan_model.joblib: mô hình cuối fit 451 nhãn; chỉ là artifact offline, chưa thay mô hình phục vụ.
