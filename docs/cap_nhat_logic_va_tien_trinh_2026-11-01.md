# Cập nhật logic và tiến trình rà soát — 01/11/2026

**Phạm vi:** những thay đổi trong đợt rà soát RF_compact, artifact phục vụ WebGIS và dải màu sông. Tài liệu ghi trạng thái mã trong working tree, kết quả kiểm tra đã thực hiện và công việc còn lại; chưa có commit, push hoặc triển khai mới trong đợt này.

Đã sửa logic đóng gói để số dự báo, ngày phát hành, metrics, biểu đồ và manifest khớp nguồn. Đã cập nhật snapshot để API đọc kết quả đã sửa và chỉnh nội suy dải màu theo khoảng cách dọc đường vẽ. Chất lượng dự báo cực đoan và tính đại diện thủy lực của cống vẫn cần nghiên cứu tiếp.

Đọc cùng [luồng hoạt động](user-flow.md), [kiến trúc](architecture.md), [hiện trạng](current_state.md), [nhật ký tiến độ](weekly_progress.md) và [báo cáo RF_compact đã hiệu đính](mo_hinh_rf_compact_chinh_thuc_2026-10-30.md).

## 1. Nguồn gốc lỗi và tác động

Đối chiếu lịch sử Git cho thấy các lỗi đóng gói đã có trong commit `7b1f829`, ngày **30/10/2026 lúc 03:08:10 UTC+7**, khi đưa RF_compact vào WebGIS. Chúng được kế thừa trong phiên bản trước khi sửa. Những lỗi này nằm ở bước chuyển kết quả nghiên cứu thành artifact phục vụ web; chưa có căn cứ kết luận toàn bộ thuật toán học máy hoặc các bảng dự báo nguồn đều sai.

| Vấn đề trước sửa | Hậu quả | Logic hiện tại |
| --- | --- | --- |
| Gán trực tiếp dự báo kế tiếp `16.18` / `16.5` | Giá trị hiển thị không xuất phát từ việc gọi thuật toán cho đúng tập nhãn khả dụng | Gọi `fit_predict` của RF_compact với đầu vào `t−2` và tập huấn luyện lọc tại ngày phát hành giả định |
| Gán lại ngày phát hành về cuối tháng, điền thông tin huấn luyện/tuổi nguồn không đúng | Không truy vết được dữ liệu nào thực sự được phép dùng tại thời điểm dự báo | Giữ ngày 06 tháng trước theo nguồn; tính lại cutoff, số mẫu và ngày khả dụng |
| Điền tay metrics và bảng EC cao, có trường hợp một mẫu nhưng MAE khác RMSE | Số liệu không tái lập được từ từng dòng dự báo | Tính MAE/RMSE và số mẫu trực tiếp từ `predictions.csv` |
| Sao chép biểu đồ của run RF cũ | Biểu đồ không đại diện cho kết quả RF_compact đang công bố | Vẽ lại từ các dòng dự báo được đóng gói; lưu hash CSV nguồn của biểu đồ |
| Manifest/báo cáo ghi 150 cây, `max_features=0.75`, dấu vết script không phải SHA thật | Cấu hình và nguồn gốc công bố không khớp thuật toán | Ghi 100 cây, `max_features=0.8`, depth 7, leaf 3, seed 42 và checksum thật |
| Đường dẫn gắn máy `D:/Study/TLCN`, script chạy ngay khi import | Khó chạy tại checkout hiện tại; import có thể phát sinh ghi artifact | Tìm gốc repository từ `__file__`; chỉ thực thi wrapper dưới main guard |
| Chia màu sông theo chỉ số đỉnh | Các đỉnh cách nhau không đều làm vị trí chuyển màu lệch theo độ dày điểm vẽ | Chia đường thành các phần bằng nhau theo khoảng cách địa lý tích lũy |

Tập 2022–2023 đã được xem trong quá trình phát triển. Báo cáo được sửa để gọi đây là **đánh giá hồi cứu**, không phải kiểm định mù độc lập. Ngày khả dụng dữ liệu vẫn dựa trên giả định vì chưa có lịch sử phiên bản và thời điểm công bố thực tế đầy đủ.

## 2. Danh mục file mã và logic đã thay đổi

| File | Thay đổi và vai trò trong luồng |
| --- | --- |
| [`scripts/rf_compact_artifacts.py`](../scripts/rf_compact_artifacts.py) — mới | Bộ đóng gói dùng chung: kiểm tra nguồn, dựng metadata as-of, tính metrics/P90, giữ lựa chọn mô hình từ giả định chính, tính dự báo lưu kế tiếp, vẽ biểu đồ và ghi manifest/hash |
| [`scripts/pack_rf_compact_run.py`](../scripts/pack_rf_compact_run.py) | Wrapper gọi `build_run(5)`; bỏ nội dung gán tay và đường dẫn máy cũ; import không tự chạy |
| [`scripts/pack_rf_compact_lag30.py`](../scripts/pack_rf_compact_lag30.py) | Wrapper gọi `build_run(35)`; dùng cùng một cách tính với trường hợp +5 ngày |
| [`scripts/update_workspace_with_rf_compact.py`](../scripts/update_workspace_with_rf_compact.py) | `update_workspace(output=None)` cập nhật hai định danh Mỹ Tho, nạp thí nghiệm qua hàm kiểm hash, kiểm hợp đồng bundle rồi ghi snapshot/manifest/registry từ thư mục tạm |
| [`scripts/backtest_asof_ec.py`](../scripts/backtest_asof_ec.py) | `available_date_for` tính cuối tháng bằng lịch Gregorian và `timedelta`, có cache tối đa 4.096 khóa; giữ quy tắc cuối tháng cộng số ngày trễ |
| [`frontend/src/features/river-geometry.js`](../frontend/src/features/river-geometry.js) | Thêm `riverRibbon(features, count=8)`: khoảng cách tích lũy, vị trí cắt theo tỷ lệ chiều dài, giữ các đỉnh bên trong từng phần và các đầu mút; bỏ đường có chiều dài bằng 0 |
| [`frontend/src/features/observations-map.js`](../frontend/src/features/observations-map.js) | Gọi `riverRibbon` sau làm trơn hình học để dựng dải màu thay cho vòng lặp chia theo số đỉnh |
| [`tests/test_rf_compact_artifacts.py`](../tests/test_rf_compact_artifacts.py) — mới | Sáu kiểm thử về bảo toàn dự báo nguồn, ngày khả dụng, từ chối nguồn sai nhãn/số mẫu, metrics, lời gọi estimator và nguồn gốc artifact |
| [`tests/river_geometry.test.mjs`](../tests/river_geometry.test.mjs) | Thêm hai hồi quy về cạnh dài ngắn không đều, nối liền/giữ đỉnh, không sửa dữ liệu đầu vào, fallback EC và đường dài 0 |
| [`docs/mo_hinh_rf_compact_chinh_thuc_2026-10-30.md`](mo_hinh_rf_compact_chinh_thuc_2026-10-30.md) | Hiệu đính cấu hình, tám đặc trưng, giao thức chọn mô hình, giới hạn hồi cứu/cực đoan và cách tái tạo artifact |

Các module API, service và repository được nhắc ở phần dưới là đường đi hiện có của dữ liệu, không phải tất cả đều được sửa trong đợt này. Thuật toán tạo dự báo lịch sử trong `experiment_ec_extreme_robust.py` được giữ nguyên.

## 3. Luồng RF_compact từ nguồn nghiên cứu đến WebGIS

### 3.1. Đọc và kiểm tra dự báo nguồn

Hai file `outputs/ec_extreme_robust_20261029/predictions_5d.csv` và `predictions_35d.csv` phải có đúng **60 tháng**: 36 tháng lựa chọn 2019–2021 và 24 tháng hồi cứu 2022–2023.

`historical_predictions` đối chiếu từng dòng với ma trận đầu vào: tháng đích phải tồn tại đúng một lần, nhãn thực đo và `train_n` phải khớp, ngày phát hành đúng quy ước, dự báo hữu hạn và không âm. Persistence và MonthlyClimatology còn được tính lại để so với các nhãn khả dụng. Nguồn sai sẽ làm quy trình dừng.

Sau kiểm tra, chỉ 24 tháng hồi cứu được xuất ra dạng dài: **24 tháng × 3 mô hình = 72 dòng/run**. Các giá trị dự báo RF_compact lịch sử giữ nguyên từ nguồn; đóng gói không huấn luyện lại chuỗi dự báo đó. Manifest ghi `REPACKED_SOURCE_PREDICTIONS_NOT_RETRAINED`.

### 3.2. Xác định dữ liệu khả dụng tại ngày phát hành

Với tháng đích `t`, ngày phát hành giả định là **ngày 06 của tháng `t−1`**. `known_rows` chỉ lấy các tháng nhãn trước `t` có ngày khả dụng EC và khí tượng không muộn hơn ngày phát hành.

- EC: giả định khả dụng sau cuối tháng nguồn **5 hoặc 35 ngày**.
- Khí tượng/thủy văn: dùng tháng `t−2`, giả định khả dụng sau cuối tháng nguồn 5 ngày.
- Metadata ghi `train_last_target_month`, `n_train_samples`, `max_train_target_available_at`, `max_feature_available_at`, `weather_month`, `latest_source_month`, `age_latest_months` và `ec_age_months`.
- `age_latest_months` là tuổi nguồn mới nhất thực sự dùng, còn `ec_age_months` là tuổi nhãn EC mới nhất. Với baseline chỉ dùng EC, tháng nguồn và tuổi nguồn được xác định theo EC.

Nguồn chỉ cho biết ngày. Thời điểm `00:00:00+07:00` là **quy ước tuần tự hóa ngày**, được đánh dấu `DATE_ONLY_MIDNIGHT_CONVENTION`; không phải bằng chứng dữ liệu đã được công bố đúng lúc nửa đêm.

### 3.3. Chọn mô hình và tính chỉ số

RF_compact được chọn theo MAE trên validation 2019–2021 của **giả định chính +5 ngày**. Trường hợp **+35 ngày giữ nguyên lựa chọn đó để đánh giá độ nhạy**. Không chọn lại ứng viên trong từng trường hợp trễ: trên +35 ngày, ứng viên tăng trọng số `RF_compact_weight3` có MAE validation thấp hơn, nhưng không thay lựa chọn đã cố định từ +5 ngày.

`make_metrics` tính MAE/RMSE từ sai số từng dòng, kiểm tra trùng mô hình/tháng, ghi số mẫu, cutoff nhãn đánh giá, độ phủ và hash danh sách tháng. Kết quả được xuất cho `model_available` và `common`; trong hai run hiện tại, cả ba mô hình có đủ cùng 24 tháng.

`make_high_ec_metrics` dùng **ngưỡng P90 cố định từ nhãn khả dụng ở ngày phát hành đầu tiên của giai đoạn validation**. Ngưỡng này khác nhóm nghiên cứu EC ≥ 100 mS/m và khác nhóm mùa khô. Trong hồi cứu 2022–2023, chỉ tháng 03/2023 vượt ngưỡng P90; vì có một mẫu, MAE và RMSE phải bằng nhau.

| Chỉ số RF_compact, đơn vị mS/m | +5 ngày | +35 ngày |
| --- | ---: | ---: |
| MAE hồi cứu 24 tháng | 11.071766 | 11.247335 |
| RMSE hồi cứu 24 tháng | 24.947845 | 24.736572 |
| MAE Persistence cùng 24 tháng | 12.621250 | 15.094583 |
| Ngưỡng P90 huấn luyện ban đầu | 60.42 | 60.60 |
| Số mẫu hồi cứu EC cao theo P90 | 1 | 1 |
| MAE = RMSE RF_compact ở nhóm P90 | 40.607140 | 39.499010 |

MAE tổng thể thấp hơn Persistence không khẳng định mô hình tốt hơn ở mọi điều kiện. Ví dụ +5 ngày, RMSE Persistence chỉ 18.910941; MAE mùa khô của RF_compact khoảng 22.22 so với 16.91 của Persistence.

### 3.4. Tính dự báo lưu sau mẫu cuối bằng thuật toán thật

`next_forecast` xác định tháng sau nhãn EC cuối, lấy thời tiết qua adapter cùng lưu lượng Kratie và mực nước Tân Châu của `t−2`, kiểm tra đủ tám đặc trưng rồi gọi `fit_predict("rf", COMPACT, 1.0, train, features)`.

Cấu hình thuật toán: **100 cây, depth 7, leaf tối thiểu 3, `max_features=0.8`, seed 42**. Tám biến là `month_sin`, `month_cos`, `rainfall_mm`, `kratie_q_t2`, `kratie_q3_t2`, `kratie_q_ratio_t2`, `tc_stage_t2`, `tc_stage3_t2`. Đặc trưng cuối là **trung vị trượt**, không phải trung bình trượt.

| Trường của `next_forecast.json` | +5 ngày | +35 ngày |
| --- | --- | --- |
| Tháng đích | 01/2024 | 01/2024 |
| Ngày phát hành giả định | 06/12/2023 | 06/12/2023 |
| Tháng khí tượng/thủy văn | 11/2023 | 11/2023 |
| Nhãn EC cuối được phép huấn luyện | 11/2023 | 10/2023 |
| Số mẫu huấn luyện | 462 | 461 |
| RF_compact tính lại, mS/m | 27.903151156478184 | 22.022199245004803 |

Đây là **dự báo nghiên cứu lưu cho 01/2024**, không phải dự báo hiện tại ngày 01/11/2026. Bước này có fit mô hình thật; bước đóng gói dự báo lịch sử ở trên không fit lại. Cả Persistence và MonthlyClimatology được tính từ cùng các nhãn khả dụng để đi kèm kết quả đã chọn.

### 3.5. Sinh biểu đồ, manifest và cập nhật workspace

`plot_predictions` vẽ quan trắc và ba mô hình từ các dòng đã đóng gói, cùng biểu đồ MAE của chính cohort đó. Bộ đóng gói tạo xong các file trong thư mục tạm trước khi thay từng file của run đích.

Manifest ghi cấu hình thật, hash script tạo artifact, hash các file nguồn được liệt kê, phiên bản môi trường đóng gói/tính dự báo kế tiếp, hash bảy đầu ra và `chart_source_predictions_sha256`. Phiên bản thư viện hiện tại không được diễn giải là bằng chứng đã chạy lại toàn bộ dự báo lịch sử bằng phiên bản đó.

`update_workspace` thực hiện các bước:

1. Đảm bảo registry có cả hai định danh Mỹ Tho và trỏ đến hai thư mục run đã sửa.
2. Gọi `scripts.build_research_workspace.experiments` để kiểm checksum đầu ra và nạp thông tin thí nghiệm.
3. Thay phần `experiments` của snapshot, cập nhật thời điểm sinh và kiểm `validate_bundle`.
4. Chuẩn bị snapshot/manifest/registry trong thư mục tạm; manifest workspace có checksum snapshot và script cập nhật thật.
5. Thay các file đích sau khi các bước chuẩn bị thành công.

Nội dung registry vốn đã trỏ đúng hai thư mục nên không có diff nội dung sau cập nhật. Đối chiếu với HEAD xác nhận `observations`, `stations`, `gates`, `sources` và hai thí nghiệm Tân Châu được giữ nguyên.

Web đọc qua `backend/api/workspace.py` → service/repository hiện có. Hai route nghiên cứu là:

```text
GET /api/v1/workspace/experiments/{experiment_id}
GET /api/v1/workspace/experiments/{experiment_id}/next-forecast
```

`frontend/src/features/forecasts.js` trình bày thí nghiệm; `next-forecast.js` đọc kết quả lưu sau mẫu cuối. Các file frontend/API này không được thay thuật toán trong đợt sửa packer; thay đổi số hiển thị đến từ artifact và snapshot được cập nhật.

## 4. File kết quả đã sinh lại

Hai thư mục run được giữ tên ổn định để không làm hỏng định danh đã dùng trên web:

- [`runs/local_ec_backtest/MYTHO_RF_COMPACT_20261030/`](../runs/local_ec_backtest/MYTHO_RF_COMPACT_20261030/): giả định nhãn +5 ngày, định danh `MYTHO_MONTHLY_LAG0`.
- [`runs/local_ec_backtest/MYTHO_RF_COMPACT_LAG30_20261030/`](../runs/local_ec_backtest/MYTHO_RF_COMPACT_LAG30_20261030/): giả định nhãn +35 ngày, định danh `MYTHO_MONTHLY_LAG30`.

Tên `LAG0`/`LAG30` là định danh kế thừa; không có nghĩa độ trễ nhãn đang được dùng là 0/30 ngày.

| File trong mỗi run | Nội dung sau sửa |
| --- | --- |
| `predictions.csv` | 72 dòng dự báo hồi cứu, số liệu nguồn giữ nguyên và metadata thời gian dựng lại |
| `metrics.csv` | MAE/RMSE tính lại, cohort, số mẫu, ngày nhãn cuối có thể dùng để chấm và hash tháng |
| `high_ec_metrics.csv` | P90 có nguồn gốc, số mẫu thật và sai số thật của ba mô hình |
| `split_manifest.csv` | Mốc tập nhãn khả dụng ban đầu, validation 36 tháng và hồi cứu 24 tháng |
| `selection.json` | Lựa chọn theo +5 ngày và thông tin trường hợp trễ đang đánh giá |
| `next_forecast.json` | Kết quả tính thật cho 01/2024, đầu vào, cutoff, cấu hình và ba mô hình |
| `forecast_chart.png` | Biểu đồ vẽ lại từ dữ liệu đúng run |
| `run_manifest.json` | Cấu hình, quy trình, giới hạn, nguồn gốc và checksum đầu ra |

Snapshot và manifest cũng đã cập nhật tại [`data/research/workspace.json`](../data/research/workspace.json) và [`workspace_manifest.json`](../data/research/workspace_manifest.json). File nhãn MRC gốc và các bảng dự báo nghiên cứu nguồn không bị ghi đè bởi quy trình này.

## 5. Luồng bản đồ sau khi sửa nội suy màu

Luồng vẽ hiện tại: frame API → `smoothRiverSegments` → `riverRibbon` → style màu theo EC của từng phần. Với mỗi đường đã làm trơn, `riverRibbon` cộng khoảng cách địa lý giữa các đỉnh, chia mặc định tám phần bằng nhau theo chiều dài, thêm điểm cắt và giữ các đỉnh nằm bên trong phần đó. EC của phần được nội suy tại trung điểm theo tỷ lệ quãng đường.

Ví dụ đường có nhiều đỉnh tập trung gần đầu đoạn: vị trí nửa chiều dài được tính từ quãng đường tích lũy, không dùng đỉnh ở giữa danh sách. Khi thiếu EC đầu/cuối, hàm dùng EC đại diện của đoạn; đường dài 0 không tạo dải. Hàm sao chép tọa độ/thuộc tính cần thiết, không sửa trực tiếp frame đầu vào.

Đây là sửa cách hiển thị. Các đường hạt vẫn giữ 35 đoạn liên tục; phép tính EC trong API, đường trục danh nghĩa, ngưỡng cống và quy tắc nối cống không đổi trong đợt này. Hệ số g/L trên dải vẫn là giả định `0.0064 × EC`, chưa có hiệu chuẩn địa phương. Chi tiết: [mô phỏng không gian](spatial-simulation.md).

## 6. Phân biệt với form dự báo đa biến trực tiếp

| Luồng | Mô hình/nguồn | Trạng thái trong đợt này |
| --- | --- | --- |
| Tham khảo thí nghiệm Mỹ Tho | RF_compact 100 cây, tám biến mùa/mưa/thủy văn, hai run ở trên | Sửa cách đóng gói và số liệu cung cấp cho web; tính lại dự báo lưu 01/2024 |
| Form “Chạy dự báo đa biến” | RF 300 cây, năm biến khí tượng/mùa; registry `data/models/multivariate_registry.json`, phiên bản `20261023T041813Z` | Giữ mô hình hiện hữu; không được tự thay bằng RF_compact qua cập nhật snapshot |
| Timeline mô phỏng | EC MRC lịch sử và ước tính khí tượng lưu trong `future_ec_forecast_2024_2026.csv` | Sửa dải màu frontend; chưa mở rộng timeline hoặc kiểm chứng thêm nhãn EC |

Form trực tiếp đi qua `backend/api/multivariate.py`, `backend/services/multivariate.py`, `backend/domain/multivariate_ec.py`, `backend/repositories/multivariate_inputs.py` và `frontend/src/features/multivariate-forecast.js`. Nó suy luận từ model đã lưu, không gọi script đóng gói RF_compact theo mỗi request.

MAE holdout của model form hiện hữu khoảng **18.31819 mS/m ở Mỹ Tho** và **4.44794 mS/m ở Tân Châu**; không thay bằng MAE 11.07 của RF_compact. Artifact ứng viên nghiên cứu khác có dự báo 11/2026 khoảng 15.005299 mS/m được giữ nguyên, không trở thành kết quả mới đã kiểm chứng sau đợt sửa này. Xem [mô hình đa biến](multivariate-forecast.md).

## 7. Kiểm tra đã thực hiện và giới hạn bằng chứng

Các kết quả dưới đây thuộc đợt sửa mã ngay trước khi cập nhật tài liệu; lần bổ sung Markdown này không chạy lại huấn luyện, backtest hoặc toàn bộ bộ kiểm thử.

| Kiểm tra | Kết quả đã ghi nhận |
| --- | --- |
| Python discovery toàn bộ tại thời điểm có năm test packer mới | 73 test được chạy, 1 bỏ qua, kết quả OK |
| Packer sau khi bổ sung hồi quy thứ sáu | Chạy riêng đủ 6 test, tất cả đạt; không gọi đây là một lượt full-suite 74 test đã chạy |
| JavaScript | 85 test đạt, gồm hồi quy hình học |
| Vite production build | Thành công, 247 module |
| API TestClient | Hai thí nghiệm và hai route next-forecast trả 200, có giá trị dự báo đã sửa |
| Nguồn và artifact | Kiểm checksum nguồn/đầu ra; chart trỏ đúng hash `predictions.csv`; biểu đồ mới đã được mở kiểm tra hình ảnh |
| Bảo toàn dữ liệu | So với HEAD, các phần quan trắc/trạm/cống/nguồn và hai thí nghiệm Tân Châu bằng nhau |
| Whitespace | `git diff --check` đạt sau sửa mã |

Sáu test packer bao gồm một test dựng run +35 trong thư mục tạm, kiểm lựa chọn cố định từ +5, hash đầu vào/đầu ra và các dòng được đưa vào hàm vẽ. Test gọi estimator dùng sentinel để xác nhận luồng tính; các giá trị 27.903151/22.022199 ở artifact thật đến từ lần tái tạo run với thuật toán thật.

Chưa có lần kiểm chứng mới qua trình duyệt tương tác hoặc PostgreSQL thật trong đợt rà soát này. Các bằng chứng DB và ảnh trình duyệt trong báo cáo 24–25/10 hoặc Phase trước vẫn thuộc đúng mốc lịch sử của chúng.

## 8. Tiến trình hiện tại và công việc tiếp theo

| Hạng mục | Tiến trình đến 01/11/2026 | Phần tiếp theo |
| --- | --- | --- |
| Đóng gói RF_compact và nguồn gốc artifact | Đã sửa mã, sinh lại hai run và snapshot, kiểm thử/API/hash đạt trong phạm vi trên | Giữ quy trình kiểm tra này khi đổi dữ liệu hoặc cấu hình |
| Logic dải màu trên sông | Đã sửa theo khoảng cách và có hồi quy | Xem lại giao diện sau khi khởi động bản build mới trên máy người dùng |
| Tài liệu luồng và báo cáo | Đã hiệu đính báo cáo mô hình; cập nhật kiến trúc, luồng sử dụng và hiện trạng cùng đợt Markdown này | Khi đổi mô hình phục vụ, cập nhật đồng thời registry, metric và tài liệu đúng luồng |
| Đánh giá mô hình | Có bằng chứng hồi cứu; vẫn dự báo thấp sáu sự kiện EC ≥ 100 mS/m ở validation | Đánh giá theo mùa/cực đoan, tỷ lệ bỏ sót và dữ liệu mới trước quyết định vận hành |
| Nhãn EC sau 2023 | Chưa có quan trắc MRC mới trong bộ đang dùng | Thu thập nhãn, chất lượng và thời điểm công bố để kiểm chứng 2024–2026 |
| Timeline | 495 tháng, 06/1985–08/2026; yêu cầu frame 10/2026 hiện thiếu tháng và trả 404 | Chỉ mở rộng khi có bộ nguồn tương thích, có provenance; không tự biến dự báo tháng thành quan trắc |
| Thủy lực cống và truyền mặn | Vẫn chiếu cống về trục chính gần nhất, chưa xác minh kết nối thủy lực | Xác minh mạng kênh, số đo tại cống, triều, mực nước hai phía và cùng hệ cao độ |
| Quy đổi EC–độ mặn | Hệ số lớp mô phỏng chưa hiệu chuẩn; tình trạng bù nhiệt EC chưa khép lại | Có cặp số đo/metadata tại địa phương trước khi xác nhận phép đổi |

Không tìm thấy một số file mô hình phân nhánh/FES được nhắc trong tài liệu trao đổi đính kèm tại checkout này; chưa ghi nhận các chức năng đó là đã tích hợp chỉ từ mô tả. Mô phỏng hiện hữu và mô hình dự báo vẫn là công cụ nghiên cứu/hỗ trợ xem xét, chưa được xác nhận để phát lệnh đóng/mở cống.

## 9. Cách tái tạo đúng phần vừa sửa

Chạy trong PowerShell tại gốc repository bằng môi trường đã cài phụ thuộc:

```powershell
.venv\Scripts\python.exe -m scripts.pack_rf_compact_run
.venv\Scripts\python.exe -m scripts.pack_rf_compact_lag30
.venv\Scripts\python.exe -m scripts.update_workspace_with_rf_compact
```

Chạy hai bước pack trước rồi mới cập nhật workspace để checksum và số liệu trong snapshot cùng phiên bản. Tên thư mục run giữ mốc 30/10 để ổn định liên kết; thời điểm tái tạo thật được ghi trong manifest. Các lệnh này đọc nguồn nghiên cứu đã lưu, fit riêng dự báo kế tiếp, ghi artifact/snapshot cục bộ và không nhập dữ liệu vào PostgreSQL.

Muốn kiểm tra hồi quy và build sau một thay đổi mã tiếp theo:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
node --test tests/*.test.mjs frontend/src/features/gate-simulation-draft.test.js
npm.cmd --prefix frontend run build
git diff --check
```

`scripts/build_research_workspace.py --fit` là quy trình khác: chạy lại các thí nghiệm qua builder tổng quát và có thể thay registry. Khi chỉ cần tái tạo hai run RF_compact đã sửa, dùng ba lệnh đóng gói ở trên. Hướng dẫn chạy web và các chế độ dữ liệu: [run_guide.md](run_guide.md).

## 10. Tài liệu luồng và tiến trình đã đồng bộ

| Tài liệu | Nội dung bổ sung trong lần cập nhật Markdown |
| --- | --- |
| [README gốc](../README.md), [mục lục docs](README.md) | Liên kết bản cập nhật mới; làm rõ định danh độ trễ Mỹ Tho và cách tìm tài liệu hiện hành |
| [user-flow.md](user-flow.md) | Phân biệt hai luồng dự báo, cách đọc kết quả RF_compact, dải màu theo khoảng cách; sửa hướng dẫn chọn snapshot/PostgreSQL cho đúng mặc định hiện tại |
| [architecture.md](architecture.md), [sơ đồ nghiên cứu](diagrams/02_research_workflow.md) | Mô tả pipeline đóng gói/kiểm tra/cập nhật workspace, ranh giới suy luận trực tiếp và hiển thị mô phỏng |
| [current_state.md](current_state.md), [weekly_progress.md](weekly_progress.md) | Thêm mốc 01/11, bằng chứng kiểm tra và việc còn lại; giữ các phần cũ dưới nhãn lịch sử |
| [run_guide.md](run_guide.md) | Ba lệnh tái tạo RF_compact đúng thứ tự; phân biệt với builder `--fit`; lệnh chạy bộ test JavaScript đầy đủ |
| [multivariate-forecast.md](multivariate-forecast.md), [spatial-simulation.md](spatial-simulation.md) | Ghi phạm vi ảnh hưởng của bản sửa, metric đúng mô hình, thay đổi ribbon và timeline chưa mở rộng |
| [Tiến trình web 25/10](tien_trinh_web_2026-10-25.md) | Giữ nội dung có ngày lịch sử và dẫn tới tiến trình mới để không nhầm kết quả DB/trình duyệt cũ với kiểm tra mới |

Bốn liên kết cũ tới tài liệu không có trong checkout được đổi thành tên tham chiếu kèm ghi chú thiếu bản lưu trong kiến trúc/nhật ký; không tự tạo nội dung thay cho bằng chứng đã mất. Lần cập nhật Markdown kiểm tra lại đường dẫn liên kết cục bộ và `git diff --check`; các kết quả kiểm thử mã ở mục 7 giữ nguyên phạm vi của lần đã chạy.
