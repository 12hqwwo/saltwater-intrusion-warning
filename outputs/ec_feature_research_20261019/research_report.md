# Nghiên cứu feature dự báo EC theo tháng

Ngày: 19/10/2026. Phạm vi: Mỹ Tho và Tân Châu, dự báo giá trị mẫu EC của tháng kế tiếp. Đây là nghiên cứu hồi cứu và bản xem trước, chưa thay đổi mô hình/API đang phục vụ WebGIS.

## 1. Kết quả cần chú ý

- Hướng gió gần đúng u/v là ứng viên tốt nhất trong nhánh Random Forest Tân Châu: MAE validation giảm khoảng 4,60%, cải thiện cả sáu năm; giai đoạn 2020–2023 giảm khoảng 2,40% so với RF nền. Mức cải thiện nhỏ và chưa qua tiêu chí lợi ích tối thiểu 5% đã đặt trước.
- Độ ẩm đất giảm MAE RF Mỹ Tho khoảng 14,12% ở giả định EC trễ 0 ngày, nhưng khoảng bootstrap còn chứa mức không cải thiện. Với trễ 30 ngày, mức giảm khoảng 21,41% qua bộ lọc thăm dò; vẫn chưa vượt mô hình Ridge chỉ dùng EC và mùa vụ trên validation. Không mặc định triển khai.
- Thêm toàn bộ nhóm biến làm RF xấu hơn ở cả hai trạm trong validation. ET0, mưa tích lũy, độ ẩm/bức xạ và ENSO có cơ sở để thử, nhưng phép thử này chưa chứng minh lợi ích tăng thêm ổn định.
- Mô hình được chọn bằng validation cho Mỹ Tho không thắng Persistence trên 2020–2023 ở giả định trễ EC 0 ngày. Các mẫu EC cao vẫn là điểm yếu lớn.
- Các nhánh lưu lượng/mực nước/ven biển được thử riêng trên cùng tập tháng giữa BASE và PLUS. Chưa có bằng chứng cải thiện mạnh và ổn định, nhiều nguồn còn vấn đề đại diện không gian hoặc thiếu dữ liệu.

## 2. Bộ dữ liệu đã chuẩn bị

`feature_matrix.csv`: 2.000 dòng = 2 trạm × 500 tháng (1985-01 đến 2026-08) × 2 giả định độ trễ EC. Sau 2023 không tự sinh nhãn EC. Khóa ghép là `station + target_month + ec_delay_days`.

`candidate_daily_era5.csv`: 30.436 dòng ngày-trạm mới tải, gồm độ ẩm đất 0–100 cm, tốc độ gió trung bình ngày và hướng gió trội. Yêu cầu ghim `models=era5`; lưu JSON, URL, đơn vị, tọa độ ô trả về và SHA-256.

`noaa_nino34_monthly.csv`: chuỗi Niño 3.4 NOAA, tệp tải ngày 19/10/2026 ghi **ERSST V6**, chuẩn dị thường 1981–2010. Không gắn nhãn V5 theo các trang mô tả cũ. Chỉ dùng các tháng nguồn đủ điều kiện khả dụng khi tạo feature.

`glofas_preview_2021.csv`: 730 dòng ngày-trạm để rà vị trí ô lưới. Bản API trả mặc định, không xác nhận phiên bản trong phản hồi; không đưa mẫu này vào thí nghiệm dự báo. Chuỗi tại ô Mỹ Tho trung bình khoảng 5,02 m3/s là dấu hiệu cần kiểm tra chọn nhánh sông, không tự coi là lưu lượng sông Tiền tại trạm. Nhánh mô hình chỉ thử chuỗi GloFAS Tân Châu cũ và giữ cờ SUSPECT.

`preview_2023.csv`: 24 dòng của hai trạm để xem trước. `feature_catalog.csv`: nguồn, biến, đơn vị, độ phủ, trạng thái tải và giả định khả dụng. Giữ trống khi thiếu; không thay thiếu bằng số 0.

Các biến ET0, độ ẩm không khí và bức xạ đã có đầy đủ trong CSV khí tượng cũ nhưng chưa được pipeline v2 đưa vào. Gió cũ thiếu hồ sơ đơn vị đủ rõ trong CSV nên vẫn dùng nhãn `source_units`, không tự ghi là m/s.

### Xem trước bốn tháng Mỹ Tho

| target_month | ec_target | ec_latest | rain_30d_mm | et0_30d_mm | soil_moisture_30d_m3_m3 | nino34_lag2_c |
| --- | --- | --- | --- | --- | --- | --- |
| 2023-01-01 | 19.360 | 17.150 | 56.700 | 114.800 | 0.380 | -0.740 |
| 2023-02-01 | 25.900 | 19.360 | 129.900 | 101.480 | 0.340 | -0.630 |
| 2023-03-01 | 78.300 | 25.900 | 27.900 | 130.950 | 0.301 | — |
| 2023-04-01 | 45.100 | 78.300 | 1.900 | 155.800 | 0.284 | -0.470 |

EC mục tiêu chỉ dùng chấm kết quả. Các feature trong cùng dòng được căn theo thời điểm phát hành trước tháng mục tiêu; không phải khí tượng thực tế của tháng tương lai. Ô ENSO trống tháng 3 là do giả định trễ 30 ngày chưa cho phép dùng số tháng 1 vào cuối tháng 2.

## 3. Kiểm tra nhãn EC trước khi so sánh

| station | source_samples | v2_labels | absent_from_v2 | median_dropped | max_dropped | max_retained_v2 |
| --- | --- | --- | --- | --- | --- | --- |
| MYTHO | 463 | 365 | 98 | 58.550 | 841.000 | 50.700 |
| TANCHAU | 464 | 445 | 19 | 13.300 | 60.900 | 30.400 |

Pipeline v2 lọc EC bằng cờ QA `VERIFIED`; bộ quy tắc IQR và biến động được tính trên toàn chuỗi trong mã ETL. Nguồn MRC ban đầu vẫn là `UNVERIFIED`. Vì vậy việc đạt QA kỹ thuật không đồng nghĩa nguồn đã xác minh, và xóa các cực trị dựa trên toàn chuỗi có thể làm mất chính các mẫu cần dự báo.

Nghiên cứu này giữ các mẫu nguồn hữu hạn, không âm trong bộ monthly nghiên cứu, bảo toàn cờ nguồn, và không dùng ngưỡng thống kê toàn chuỗi để bỏ nhãn. Điều đó cũng **không xác nhận 841 mS/m là phép đo đúng**: cần kiểm chứng nguồn/thiết bị cho các giá trị đáng ngờ. Cột `ec_target_v2` được giữ riêng để đối chiếu. Không so trực tiếp MAE ở đây với kết quả trước trên tập nhãn đã lọc.

## 4. Nguồn và lý do chọn feature

| group | source | download_status | source_url |
| --- | --- | --- | --- |
| EC quá khứ | MRC tại Mỹ Tho và Tân Châu | Có sẵn | https://portal.mrcmekong.org/ |
| Mùa vụ | Lịch tháng cần dự báo | Tự tính |  |
| Mưa tích lũy và khô hạn | Open-Meteo trong dữ liệu gốc | Có sẵn, tạo thêm đặc trưng | https://open-meteo.com/en/docs/historical-weather-api |
| ET0 và cân bằng khí hậu | Open-Meteo trong dữ liệu gốc | Có sẵn nhưng pipeline v2 chưa dùng | https://open-meteo.com/en/docs/historical-weather-api |
| Độ ẩm và bức xạ | Open-Meteo trong dữ liệu gốc | Có sẵn nhưng pipeline v2 chưa dùng | https://open-meteo.com/en/docs/historical-weather-api |
| Độ ẩm đất | ERA5 qua Open-Meteo, models=era5 | Đã tải mới | https://open-meteo.com/en/docs/historical-weather-api |
| Hướng gió | ERA5 qua Open-Meteo, models=era5 | Đã tải mới | https://open-meteo.com/en/docs/historical-weather-api |
| ENSO | NOAA PSL, ERSST V6 theo footer tệp thực tải | Đã tải mới | https://psl.noaa.gov/data/correlation/nina34.anom.data |
| Lưu lượng Tân Châu đo/truy dựng | GFZ, Apel và cộng sự 2024 | Đã có bản nguồn và bản chuẩn hóa | https://doi.org/10.5880/GFZ.4.4.2024.004 |
| Lưu lượng GloFAS | GloFAS cũ Tân Châu; mẫu API mới cho hai vị trí | Có chuỗi cũ và đã tải mẫu mới | https://open-meteo.com/en/docs/flood-api |
| Mực nước vệ tinh | DAHITI 627 và 3316 trong dự án | Có sẵn; thử nghiệm riêng | https://dahiti.dgfi.tum.de/en/627/ |
| Mực nước ven biển Vũng Tàu | UHSLC trong dự án | Có sẵn; thử nghiệm riêng | https://uhslc.soest.hawaii.edu/data/ |
| Mưa toàn lưu vực | CHIRPS, ERA5 theo polygon lưu vực | Nguồn đã xác định, chưa tải lớp lưới | https://www.chc.ucsb.edu/data/chirps |
| Nhiệt độ nước và vận hành | Số đo trạm, hồ sơ cơ quan quản lý | Chưa có bộ dữ liệu đủ dùng |  |

Cơ sở nghiên cứu: [Apel và cộng sự (2020)](https://nhess.copernicus.org/articles/20/1609/2020/) xem xét ENSO và lưu lượng Tân Châu cho xâm nhập mặn theo mùa ở đồng bằng Mekong. [Wullems và cộng sự (2023)](https://hess.copernicus.org/articles/27/3823/2023/) dùng nồng độ chloride quá khứ, mực nước, lưu lượng và gió trong bài toán dự báo cửa sông. Hai nghiên cứu hỗ trợ lựa chọn giả thuyết vật lý; chúng không chứng minh các feature sẽ cải thiện EC tháng tại Mỹ Tho/Tân Châu, và các biến mục tiêu không đồng nhất.

Mưa tại trạm khác mưa toàn lưu vực. Độ ẩm đất và ET0 là chỉ báo điều kiện khí hậu, không phải đo độ dẫn điện hay cân bằng nước sông. Độ dẫn điện còn phụ thuộc ion hòa tan, nhiệt độ nước và cơ sở bù nhiệt; đặc biệt EC thấp ở Tân Châu không nên diễn giải mọi biến động thành nước biển xâm nhập.

GFZ thực có 444 tháng từ 1980 đến 2016 dù tên tệp nói 1964–2017; phần trước 1995 có truy dựng. Chỉ thử đoạn nguồn mô tả là số đo từ 1996. Với Mỹ Tho, cột này mang nghĩa lưu lượng thượng nguồn Tân Châu, không phải số đo tại Mỹ Tho. Dữ liệu độ mặn Sơn Đốc cùng bộ GFZ không được trộn làm nhãn EC.

## 5. Quy trình kiểm chứng đã thực hiện

1. Cố định mục tiêu là mẫu EC tháng M, phát hành cuối tháng M-1. Giữ đơn vị mS/m, không đổi sang độ mặn.
2. Lưu `protocol.json` trước chạy. EC dùng hai giả định cuối tháng +0/+30 ngày. Khí tượng dùng các cửa sổ 30/90 ngày kết thúc trước phát hành 5 ngày. ENSO dùng tháng trễ 2/3/6 và trung bình trượt quá khứ, kiểm tra chính xác điều kiện cuối tháng nguồn +30 ngày. Không dùng cửa sổ giữa tâm có dữ liệu tương lai.
3. Mỗi năm huấn luyện lại bằng các nhãn giả định đã có trước tháng 1, sau đó giữ mô hình trong năm; feature được cập nhật hàng tháng. Train mở rộng từ 1986, tối thiểu 96 nhãn cho nhánh chính.
4. Validation 2014–2019 để so sánh. Khóa lựa chọn trong `selection.json`, rồi mới chấm 2020–2023. Giai đoạn sau đã từng được xem trong dự án nên đây là holdout hồi cứu, không phải kiểm định mù mới.
5. So Persistence, Seasonal Naive, trung bình lịch theo tháng, Random Forest cố định 120 cây và Ridge trên log(1+EC). Điền thiếu và chuẩn hóa học riêng từ train. Không dùng deep learning trên chuỗi tháng ngắn này.
6. BASE = EC quá khứ + mùa vụ + mưa/nhiệt độ/gió hiện có, đã căn thời gian. Thử thêm riêng sáu nhóm, thử ALL và bỏ từng nhóm khỏi ALL. Mọi cấu hình nhánh chính dùng cùng 72 tháng validation và 48 tháng kiểm tra cho mỗi trạm/kịch bản.
7. Chấm MAE, RMSE, bias, MAE tháng 12–4 và các mẫu trên phân vị 90% **của train năm đó**. Ngưỡng này chỉ phục vụ đánh giá mẫu EC cao, không phải ngưỡng cảnh báo vận hành.
8. Tính số năm cải thiện và bootstrap theo block 12 tháng, 1.000 lượt, cho chênh lệch sai số tuyệt đối giữa hai mô hình trên cùng tháng. Tiêu chí thăm dò: giảm MAE ít nhất 5%, thắng ít nhất 4/6 năm, khoảng 95% của lợi ích hoàn toàn dương. Đây là tiêu chí nghiên cứu đặt trước, chưa hiệu chỉnh thử nhiều giả thuyết.
9. Xáo trộn theo nhóm bằng dịch vòng 3/6/9 tháng trên validation của ALL để xem độ nhạy. Đây là chẩn đoán phụ: biến tương quan hoặc mô hình ALL kém có thể làm importance khó diễn giải. Không dùng impurity importance để tuyên bố quan hệ nhân quả.
10. Chạy audit khóa trạm-tháng, thời điểm khả dụng, dữ liệu nguồn không đổi, cùng tập chấm và train trước test. Thay dữ liệu mưa tương lai bằng giá trị cực lớn không làm thay đổi feature của dự báo quá khứ.

## 6. Lợi ích tăng thêm của các nhóm biến

Giả định EC trễ 0 ngày, cùng Random Forest. Phần trăm dương là giảm MAE so với BASE. Đây là validation 2014–2019.

| station | Nhóm | mae | Giảm MAE (%) | Số năm tốt hơn | CI lợi ích thấp | CI lợi ích cao |
| --- | --- | --- | --- | --- | --- | --- |
| MYTHO | Độ ẩm đất 0-100 cm | 21.555 | 14.115 | 4.000 | -0.355 | 7.782 |
| MYTHO | Mưa tích lũy và chuỗi ngày khô | 26.472 | -5.474 | 2.000 | -8.632 | 6.784 |
| MYTHO | ENSO Niño 3.4 | 27.445 | -9.352 | 3.000 | -6.134 | 1.391 |
| MYTHO | Hướng gió dạng u/v gần đúng | 27.583 | -9.900 | 2.000 | -7.164 | 2.821 |
| MYTHO | ET0 và chênh lệch mưa - ET0 | 28.856 | -14.972 | 2.000 | -12.218 | 4.786 |
| MYTHO | Độ ẩm, bức xạ, biên độ nhiệt | 29.370 | -17.022 | 3.000 | -12.519 | 3.968 |
| TANCHAU | Hướng gió dạng u/v gần đúng | 1.268 | 4.600 | 6.000 | 0.016 | 0.110 |
| TANCHAU | ENSO Niño 3.4 | 1.526 | -14.806 | 1.000 | -0.477 | 0.009 |
| TANCHAU | Mưa tích lũy và chuỗi ngày khô | 1.540 | -15.881 | 0.000 | -0.325 | -0.102 |
| TANCHAU | ET0 và chênh lệch mưa - ET0 | 1.604 | -20.692 | 1.000 | -0.465 | -0.103 |
| TANCHAU | Độ ẩm đất 0-100 cm | 1.633 | -22.853 | 1.000 | -0.569 | -0.103 |
| TANCHAU | Độ ẩm, bức xạ, biên độ nhiệt | 1.645 | -23.735 | 1.000 | -0.578 | -0.095 |

Khoảng CI ở bảng có đơn vị mS/m, không phải phần trăm. `drop_group_summary.csv` ghi chênh lệch MAE khi bỏ nhóm khỏi ALL; `group_permutation.csv` ghi chẩn đoán độ nhạy từng nhóm.

### Kiểm tra mô hình đã chọn trên 2020–2023

| station | algorithm | configuration | n | mae | rmse | high_mae |
| --- | --- | --- | --- | --- | --- | --- |
| MYTHO | PERSISTENCE | PERSISTENCE | 48 | 40.848 | 104.691 | 165.086 |
| MYTHO | RF | BASE | 48 | 45.595 | 114.282 | 233.569 |
| MYTHO | RIDGE_LOG | AR | 48 | 48.688 | 139.938 | 300.620 |
| TANCHAU | PERSISTENCE | PERSISTENCE | 48 | 2.810 | 3.691 | 2.455 |
| TANCHAU | RF | BASE | 48 | 2.308 | 3.221 | 3.540 |
| TANCHAU | RF | PLUS_wind_direction | 48 | 2.253 | 3.128 | 3.428 |

Tân Châu: mô hình thêm hướng gió giảm MAE từ khoảng 2,308 xuống 2,253 mS/m so với RF BASE; vẫn có xu hướng dự báo thấp. Mỹ Tho: mô hình Ridge AR được chọn trên validation có MAE khoảng 48,688, kém Persistence 40,848 mS/m; không thể công bố mô hình phức tạp đã tốt hơn baseline ở trạm này. Kết quả có thể chịu ảnh hưởng của các phép đo cao chưa được xác minh.

### Các nhánh thủy văn riêng

| station | study | algorithm | n | start | end | gain_pct |
| --- | --- | --- | --- | --- | --- | --- |
| MYTHO | GFZ_TANCHAU_UPSTREAM_PROXY | RF | 77 | 2010-01-01 | 2016-12-01 | 0.322 |
| MYTHO | GFZ_TANCHAU_UPSTREAM_PROXY | RIDGE_LOG | 77 | 2010-01-01 | 2016-12-01 | 1.927 |
| MYTHO | VUNGTAU_DAILY_MAX_PROXY | RF | 72 | 2014-01-01 | 2019-12-01 | 3.934 |
| MYTHO | VUNGTAU_DAILY_MAX_PROXY | RIDGE_LOG | 72 | 2014-01-01 | 2019-12-01 | 0.545 |
| MYTHO | DAHITI_LOCAL_PROXY | RF | 72 | 2018-01-01 | 2023-12-01 | 0.237 |
| MYTHO | DAHITI_LOCAL_PROXY | RIDGE_LOG | 72 | 2018-01-01 | 2023-12-01 | -1.084 |
| TANCHAU | GFZ_TANCHAU_UPSTREAM_PROXY | RF | 77 | 2010-01-01 | 2016-12-01 | 1.112 |
| TANCHAU | GFZ_TANCHAU_UPSTREAM_PROXY | RIDGE_LOG | 77 | 2010-01-01 | 2016-12-01 | -0.380 |
| TANCHAU | VUNGTAU_DAILY_MAX_PROXY | RF | 72 | 2014-01-01 | 2019-12-01 | 2.573 |
| TANCHAU | VUNGTAU_DAILY_MAX_PROXY | RIDGE_LOG | 72 | 2014-01-01 | 2019-12-01 | 0.467 |
| TANCHAU | DAHITI_LOCAL_PROXY | RF | 49 | 2010-01-01 | 2016-08-01 | -3.262 |
| TANCHAU | DAHITI_LOCAL_PROXY | RIDGE_LOG | 49 | 2010-01-01 | 2016-08-01 | 1.164 |
| TANCHAU | GLOFAS_SUSPECT_CELL | RF | 67 | 2014-01-01 | 2019-12-01 | -1.039 |
| TANCHAU | GLOFAS_SUSPECT_CELL | RIDGE_LOG | 67 | 2014-01-01 | 2019-12-01 | -1.013 |

Những bảng này chỉ so BASE và PLUS trong từng dòng/cặp. Không xếp hạng MAE giữa các nguồn vì khoảng thời gian và số mẫu khác nhau. DAHITI Tân Châu thiếu chuỗi mới; dùng tối thiểu 48 nhãn cho nhánh thăm dò này và công bố giới hạn. GloFAS giữ cờ ô lưới chưa xác minh. UHSLC là cực đại mực nước ngày Vũng Tàu, không phải biên độ triều hay dự báo triều tại cống.

## 7. Quyết định đề xuất

- Giữ EC quá khứ và mùa vụ làm lõi. Giữ các baseline trong mọi lần kiểm tra.
- Ưu tiên xác minh các mẫu EC bị loại, đơn vị gió cũ, cơ sở EC/bù nhiệt và tính đại diện không gian; đây có thể quan trọng hơn thêm thuật toán.
- Hướng gió Tân Châu: giữ làm ứng viên, lợi ích nhỏ; cần kiểm chứng thêm các thời kỳ mới trước khi thay mô hình đang dùng.
- Độ ẩm đất Mỹ Tho: giữ làm ứng viên cho nghiên cứu độ trễ, chưa đủ bằng chứng chọn làm cấu hình cuối.
- ET0/khô hạn/ENSO: giữ trong kho dữ liệu để thử các giả thuyết theo mùa hoặc mưa lưu vực; chưa thêm mặc định vào mô hình chính từ kết quả hiện tại.
- Bước dữ liệu tiếp theo có giá trị: mưa tổng hợp theo lưu vực, lưu lượng/mực nước đo có chuỗi mới, nhiệt độ nước và nhật ký vận hành. Phải có tập EC đồng thời để kiểm chứng.
- Khi có dữ liệu sau 2023 đã xác minh: đóng băng cấu hình chọn trước, chấm một giai đoạn mới độc lập, kiểm tra drift và các đợt EC cao. Chỉ sau đó mới quyết định cập nhật API dự báo.

## 8. Tái lập

Chạy từ gốc dự án trong môi trường Python có pandas/numpy/scikit-learn. Không ghi PostgreSQL hay thay WebGIS:

```powershell
python scripts/fetch_ec_feature_candidates.py
python scripts/research_ec_features.py prepare
python scripts/research_ec_features.py evaluate
python scripts/research_ec_hydrology.py
python scripts/check_ec_feature_research.py
python scripts/summarize_ec_feature_research.py
```

Lần tải lại dùng cache các tệp đã có. Muốn snapshot nguồn mới, dùng `--output` cho script tải và tạo nhánh cấu hình nghiên cứu riêng; không ghi đè dữ liệu gốc. Các lần chạy phân tích ghi lại đầu ra trong thư mục nghiên cứu của ngày này. `data_manifest.json`, `download_manifest.json`, `evaluation_manifest.json` giữ checksum và tham số để truy vết.

Giới hạn quan trọng: bản tái phân tích/NOAA tải hôm nay có thể đã được sửa hồi cứu, nên căn độ trễ chưa thay thế kiểm chứng bằng bản dữ liệu thực sự phát hành trong quá khứ. Kết quả là đóng góp dự báo có điều kiện theo tập dữ liệu, mô hình và giai đoạn đã thử; không phải kết luận nhân quả.
