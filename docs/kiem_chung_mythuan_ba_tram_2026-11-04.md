# Kiểm chứng mô hình Mỹ Thuận và nội suy ba trạm · 04/11/2026

Đã hoàn thành Bước 1 và Bước 2 theo yêu cầu báo cáo trước khi sửa giao diện. Mô hình Mỹ Thuận dùng EC của chính trạm làm biến mục tiêu. Đợt này chưa thay registry mô hình, database quan trắc, chuỗi bản đồ hoặc mã giao diện. Không dùng thêm trạm thứ tư.

## Dữ liệu và giao thức

- EC nguồn MRC: Tân Châu 464 mẫu, Mỹ Thuận 451 mẫu, Mỹ Tho 463 mẫu; mỗi trạm có đủ 24 tháng 2022–2023. Mỹ Thuận phủ 15/05/1985–15/12/2023. Kiểm checksum, đơn vị mS/m, giá trị hữu hạn không âm và tháng không trùng; giữ nguyên QA `UNVERIFIED` và cơ sở bù nhiệt `UNKNOWN`.
- Tải khí tượng ERA5 tại chính tọa độ MRC Mỹ Thuận `[105.9263229, 10.27532005]`, giữ JSON gốc và manifest/SHA-256 trong `data/external/mythuan_weather_20261104/`. Đơn vị mưa mm, nhiệt độ °C, gió m/s và tháng đủ ngày đều được kiểm tra. Không dùng khí tượng Mỹ Tho thay cho Mỹ Thuận.
- Tái sử dụng quy trình rolling-origin của [backtest theo ngày khả dụng](asof_backtest_2026-10-29.md): dự báo tháng t phát hành ngày 06 tháng t−1; khí tượng tháng t−2 có sẵn giả định từ cuối tháng +5 ngày. Mỗi lần fit chỉ dùng EC đã khả dụng tại ngày phát hành; chạy cả giả định công bố EC +5 và +35 ngày.
- RF giữ cố định 300 cây, sâu tối đa 8, lá tối thiểu 3 mẫu, seed 42; ba biến khí tượng và sin/cos tháng. Validation 2019–2021, kiểm tra hồi cứu 2022–2023. Không chọn siêu tham số dựa trên sai số 2022–2023. Đây là kiểm tra hồi cứu theo giả định công bố, không phải holdout mù mới; dữ liệu nguồn hiện có không lưu lịch sử ngày công bố.
- Persistence lấy EC mới nhất đã khả dụng; MonthlyClimatology lấy trung bình tháng lịch từ tập huấn luyện đã khả dụng. Ba trạm và mọi phương án được chấm trên cùng các tháng.

Chạy lại hai đầu mút cho 240 dự báo khớp với backtest hiện có; chênh dự báo RF lớn nhất chỉ `5.684341886080802e-14 mS/m` do tính toán số thực. Do đó phép so sánh không thay mô hình hai đầu mút để tạo mức cải thiện.

## Bước 1 — Mô hình Mỹ Thuận

Kỳ 2022–2023, 24 tháng; giả định công bố EC cuối tháng +5 ngày. MAE và RMSE đều tính bằng mS/m.

| Mô hình | MAE | RMSE |
|---|---:|---:|
| RF Mỹ Thuận | 3.917425 | 4.856469 |
| Persistence | 4.806250 | 5.772399 |
| MonthlyClimatology | 3.956993 | 4.720397 |

RF tốt hơn Persistence ở cả MAE/RMSE. So với MonthlyClimatology, RF chỉ tốt hơn nhẹ về MAE và kém hơn về RMSE; chưa có cơ sở gọi RF vượt mọi baseline. Ở giả định +35 ngày, RF đạt MAE `3.895723`, RMSE `4.832235`; kết luận này không thay đổi.

## Bước 2 — Ước tính tại vị trí Mỹ Thuận

Giữ nguyên trục sông WebGIS hiện có. Chiếu tọa độ nguồn Mỹ Thuận lên trục được km `85.217605`, giữa Tân Châu km 0 và Mỹ Tho km 125; tỷ lệ dọc tuyến `0.68174084`, khoảng cách từ trạm tới trục `0.863 km`. Đây là chainage quy đổi của trục hiện tại, không phải cự ly thủy lực đã kiểm chứng hoặc khoảng cách đường thẳng.

Nội suy tuyến tính dùng `EC = (1 − r) × EC_Tân_Châu + r × EC_Mỹ_Tho`. Phương án ba trạm tại đúng Mỹ Thuận lấy **dự báo ngoài mẫu của RF Mỹ Thuận**, không lấy thực đo Mỹ Thuận làm điểm neo khi tính sai số.

| Phương án tại Mỹ Thuận, 24 tháng 2022–2023 | MAE | RMSE |
|---|---:|---:|
| Hai trạm, thực đo hai đầu mút, tuyến tính | 5.442903 | 9.838450 |
| Hai trạm, dự báo hai đầu mút, tuyến tính | 11.250346 | 33.124660 |
| Ba trạm, thêm dự báo RF Mỹ Thuận làm điểm neo | 3.917425 | 4.856469 |
| Hai trạm, thực đo hai đầu mút, IDW² lịch sử | 6.527530 | 11.747552 |
| Hai trạm, dự báo hai đầu mút, IDW² kiểm độ nhạy | 13.608517 | 40.230285 |

Lớp phủ dự báo hiện tại dùng tuyến tính dọc trục sông; mô phỏng lịch sử dùng IDW². Báo cáo giữ cả hai để không đánh đồng công thức.

| Thêm điểm neo RF Mỹ Thuận, so với | Giảm MAE | Giảm RMSE |
|---|---:|---:|
| Hai đầu mút thực đo, tuyến tính | 28.03% | 50.64% |
| Hai đầu mút dự báo, tuyến tính | 65.18% | 85.34% |
| Hai đầu mút thực đo, IDW² | 39.99% | 58.66% |
| Hai đầu mút dự báo, IDW² | 71.21% | 87.93% |

23/24 tháng có mẫu cùng ngày ở cả ba trạm. Tháng 12/2022 khác ngày: Tân Châu 12/12, hai trạm còn lại 15/12. Chấm riêng 23 tháng cùng ngày: MAE/RMSE ba trạm là `3.970534 / 4.928970`, so với tuyến tính thực đo hai trạm `5.677069 / 10.050046` và tuyến tính dự báo hai trạm `11.686035 / 33.836129`; xu hướng cải thiện giữ nguyên. Cùng ngày không xác nhận cùng giờ hoặc pha triều.

Phép chấm này chứng minh cải thiện **tại Mỹ Thuận** trong kỳ đã xét. Tại điểm neo thứ ba, sai số bằng sai số mô hình Mỹ Thuận ở Bước 1. Không diễn giải tỷ lệ giảm thành mức giảm sai số toàn tuyến sông. Nội suy từ thực đo hai đầu mút là tái dựng hồi cứu cùng tháng, không phải dữ liệu đã biết tại ngày phát hành dự báo.

## Tái tạo, kiểm thử và trạng thái tích hợp

```powershell
.venv/Scripts/python.exe scripts/evaluate_mythuan_three_station.py --fetch-weather
.venv/Scripts/python.exe -m unittest tests.test_mythuan_three_station tests.test_backtest_asof_ec
```

Đã chạy 13/13 kiểm thử đạt, gồm quy tắc ngày khả dụng, tính duy nhất/cùng cohort, nguồn và checksum đầu ra, phép chiếu dọc tuyến, công thức nội suy và xác nhận điểm neo thứ ba dùng dự báo thay vì nhãn thực đo. Toàn bộ 360 dự báo của ba trạm/hai độ trễ không có dòng dùng nhãn hoặc khí tượng sau ngày phát hành giả định.

- [Báo cáo số liệu tự sinh](../outputs/mythuan_three_station_20261104/report.md).
- [Sai số mô hình](../outputs/mythuan_three_station_20261104/model_metrics.csv), [sai số nội suy](../outputs/mythuan_three_station_20261104/interpolation_metrics.csv), [mức cải thiện](../outputs/mythuan_three_station_20261104/improvements.csv).
- [Dự báo từng tháng](../outputs/mythuan_three_station_20261104/predictions.csv), [nội suy từng tháng và ngày mẫu](../outputs/mythuan_three_station_20261104/interpolation_predictions.csv).
- [Manifest, giao thức và checksum](../outputs/mythuan_three_station_20261104/run_manifest.json).

Artifact `mythuan_model.joblib` đã được fit lại trên toàn bộ 451 nhãn để chuẩn bị Bước 3; không dùng mô hình fit toàn bộ này để tính các sai số hồi cứu ở trên. Bước 3 — bổ sung trạm vào dữ liệu/API, registry, lịch sử và chuỗi dự báo, rồi nội suy hai chặng trên WebGIS — chưa thực hiện ở mốc báo cáo trước giao diện này.
