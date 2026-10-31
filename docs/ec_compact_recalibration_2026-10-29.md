# Hiệu chỉnh khẩn cấp mô hình EC Mỹ Tho: chọn đặc trưng thủy văn gọn

Ngày 29/10/2026. Mục tiêu là **EC (mS/m) của một mẫu MRC trong tháng mục tiêu tại Mỹ Tho**, dự báo theo giả định phát hành ngày 06 tháng trước. Đây không phải EC trung bình tháng, độ mặn tại cống hoặc trường mặn trên mạng sông. Không xóa/hiệu chỉnh nhãn EC cực trị.

## Giao thức và phương án

`scripts/experiment_ec_extreme_robust.py` huấn luyện lại ở **mỗi ngày phát hành hồi cứu**, chỉ từ nhãn EC đã có theo hai giả định công bố cuối tháng +5/+35 ngày. Dữ liệu khí tượng, Q Kratie và mực nước Tân Châu dùng tháng `t−2`, giả định có sau cuối tháng nguồn +5 ngày. Tập 2019–2021 dùng chọn; 2022–2023 là kiểm tra hồi cứu **đã từng được xem**. Mỗi phương án chấm đúng cùng 36 hoặc 24 tháng. MRC/ERA5 không có lịch sử phiên bản và ngày công bố thật, nên đây là backtest theo giả định, không phải kiểm toán dự báo đã phát hành.

Phương án thắng theo **MAE toàn kỳ 2019–2021, giả định chính +5 ngày** là `RF_compact`: Random Forest 100 cây, `max_depth=7`, `min_samples_leaf=3`, `max_features=0.8`, seed 42, impute trung vị và cờ thiếu. Chỉ giữ 8 biến: sin/cos tháng mục tiêu, mưa `t−2`, Q Kratie tháng `t−2`, trung bình Q ba tháng kết thúc ở `t−2`, tỷ số Q so với trung vị cùng tháng của 15 năm **trước**, mực nước Tân Châu tháng `t−2` và trung vị ba tháng đến `t−2`. **Không dùng EC quá khứ làm biến**, để ước tính 2026 không phụ thuộc nhãn cuối 2023. Q Kratie và mực nước Tân Châu là chỉ báo nước ngọt; chúng không phải Q tại phân lưu hay thời gian truyền muối đã đo.

Đã thử thêm trọng số 3/8 lần cho nhãn EC ≥100 mS/m và Extra Trees. Trọng số 8 giảm MAE sáu tháng EC cao ở validation từ 259,37 xuống 234,13 mS/m, nhưng MAE toàn kỳ 2022–2023 tăng từ 11,07 lên 14,25 mS/m và không có tháng EC cao mới ở kỳ này để xác nhận lợi ích cực trị. Vì vậy **không chọn mô hình có trọng số**. Các thử nghiệm XGBoost/LightGBM trước cũng không thắng ổn định trên kỳ chọn, xem `docs/ec_data_substitutes_and_model_check_2026-10-29.md`.

## Sai số đối chiếu cùng tháng

MAE, đơn vị mS/m. Mùa khô = tháng XII–IV. EC cao = thực đo ≥100 mS/m; kỳ 2022–2023 có **0 tháng** thuộc nhóm này nên không có điểm kiểm tra cực trị độc lập.

| Giả định | Kỳ / nhóm (n) | RF cũ | RF thủy văn đầy đủ | **RF_compact** | Persistence |
|---|---|---:|---:|---:|---:|
| +5 ngày | 2019–2021 / toàn kỳ (36) | 71,56 | 58,68 | **50,87** | 93,39 |
| +5 ngày | 2019–2021 / mùa khô (15) | 128,94 | 118,68 | **106,86** | 109,66 |
| +5 ngày | 2019–2021 / EC cao (6) | 324,24 | 286,28 | **259,37** | 305,71 |
| +5 ngày | 2022–2023 / toàn kỳ (24) | 18,63 | 13,52 | **11,07** | 12,62 |
| +5 ngày | 2022–2023 / mùa khô (10) | 35,38 | 26,91 | 22,22 | **16,91** |
| +35 ngày | 2019–2021 / toàn kỳ (36) | 71,26 | 60,72 | **55,30** | 125,84 |
| +35 ngày | 2019–2021 / mùa khô (15) | 127,56 | 121,36 | **110,13** | 149,06 |
| +35 ngày | 2019–2021 / EC cao (6) | 321,74 | 302,66 | **285,24** | 378,73 |
| +35 ngày | 2022–2023 / toàn kỳ (24) | 18,61 | 13,19 | **11,25** | 15,09 |
| +35 ngày | 2022–2023 / mùa khô (10) | 35,19 | 26,10 | 22,37 | **16,07** |

Theo giả định chính +5 ngày, chọn đặc trưng gọn giảm MAE validation **13,3%** so với RF thủy văn đầy đủ và **28,9%** so với RF cũ. Kỳ 2022–2023 giảm **18,1%** so với RF thủy văn đầy đủ, nhưng đây không phải test mù. Trong mùa khô 2022–2023, Persistence vẫn tốt hơn `RF_compact`. Bảng đầy đủ MAE/RMSE/bias theo nhóm ở `outputs/ec_compact_summary_20261029/matched_metrics.csv`; 15 tháng sai số lớn nhất mỗi kỳ ở `largest_15_errors_per_split.csv` cùng thư mục. Dự báo từng tháng, cấu hình và nguồn ở `outputs/ec_extreme_robust_20261029/`.

Kiểm tra độ bền bổ sung `scripts/validate_ec_compact_history.py` chạy cuốn chiếu 108 tháng **2010–2018**, vẫn chỉ dùng nhãn có thể biết ở ngày phát hành giả định. `RF_compact` đạt MAE toàn kỳ **14,76** so với Persistence **22,17 mS/m**; ở 45 tháng mùa khô thì RF **25,59**, Persistence **20,00**. Năm 2016 có MAE RF **54,76**. Đây là lịch sử đã được xem trong dự án, không phải tập kiểm tra mù mới. File từng tháng và bảng nhóm ở `outputs/ec_compact_history_20261029/`.

## Lỗi còn lại và ý nghĩa vật lý

Hai tháng nặng nhất vẫn là **03/2020: thực 692, RF_compact 182,48, sai 509,52 mS/m** và **02/2020: thực 558, RF_compact 98,86, sai 459,14 mS/m**. Cả sáu tháng EC cao trong tập chọn đều bị dự báo thấp. Tín hiệu Q `t−2` và mực nước `t−2` không mô tả triều, nước dâng, phân chia dòng ở Vàm Nao/Mỹ Thuận, hình học cửa sông hoặc thời điểm lấy mẫu EC trong tháng. Tài liệu [Eslami và cộng sự (2021)](https://esurf.copernicus.org/articles/9/953/2021/) và [mô hình 3D Mekong](https://www.nature.com/articles/s43247-021-00208-5) cho thấy vai trò của Q, triều, bathymetry và gió/nước dâng; đó là giải thích cơ chế có cơ sở, **không phải chứng minh nguyên nhân riêng của từng mẫu MRC 2020**.

[MRC State of the Basin Report 2023](https://www.mrcmekong.org/?document_id=01YJPZCU65YTEFSMP7ORH325YZGOOGE5MZ&download_document=1&name=Mekong-River-Basin-2023-State-of-the-Basin-Report.pdf) cũng ghi nhận ranh mặn >4 g/L vào sông Mekong trong tháng 04/2020 xa hơn mức trung bình. Đây là bằng chứng độc lập rằng 2020 là năm xâm nhập mặn mạnh trên lưu vực; nó **không xác minh trực tiếp** từng số EC tại Mỹ Tho, không cho phép sửa hoặc thay nhãn MRC.

Thí nghiệm EC Tân Châu trễ trước đó làm lỗi Mỹ Tho 2022–2023 tăng; không xem đây là bằng chứng lan truyền mặn. FES `south` đã kiểm tra với dao động mực nước Vàm Kênh nhưng thêm vào mô hình EC tháng chưa giảm lỗi ổn định. GRIT mới là topology sơ bộ, thiếu Q phân lưu, mặt cắt, độ sâu và cấu trúc cống. Nghiên cứu [Cổ Chiên–Hậu bằng mô hình thủy lực](https://www.mdpi.com/2225-1154/11/3/66) đã dùng Q giờ Mỹ Thuận/Cần Thơ, mực nước triều giờ nhiều cửa và độ mặn giờ nhiều trạm để hiệu chỉnh; [tài liệu MIKE 11 AD](https://manuals.mikepoweredbydhi.help/2021/Water_Resources/Mike_11_ref.pdf) yêu cầu điều kiện biên nồng độ/vận chuyển khi dòng đổi chiều. **Chưa thể hiệu chuẩn vận tốc hoặc thời gian truyền muối từ thượng nguồn ra hạ nguồn hay từ biển vào sông** bằng một mẫu EC/tháng/trạm. Không xuất bản trường mặn nội suy như quan trắc.

## Dữ liệu cần thêm theo thứ tự tác động

1. **EC25/Cl⁻/độ mặn đo đồng thời theo giờ hoặc ngày**, nhiều mùa khô, từ Mỹ Thuận–Mỹ Tho–Vàm Kênh và cửa Đại/Hàm Luông/Cổ Chiên; kèm giờ, múi giờ, độ sâu, đơn vị, nhiệt độ, QA và ngày công bố. Dữ liệu mới 2024–2026 là cần thiết để kiểm chứng dự báo hiện nay. Không đổi EC sang g/L nếu không có hiệu chuẩn ion/nhiệt độ tại địa phương.
2. **Q hai chiều và phân lưu** tại Tân Châu, Vàm Nao, Mỹ Thuận và các nhánh, kèm quy ước dấu; đo mực nước đồng thời và mốc cao độ chung. Q Kratie là biến dự báo hữu ích nhưng không cho biết tỉ lệ dòng qua mỗi cửa.
3. **Bathymetry/mặt cắt, mạng kênh–cống và lịch vận hành**, cùng mực nước/triều thực đo từng cửa trong cùng hệ cao độ. FES chỉ là triều thiên văn ngoài biển; TopoDEM không chứa đáy sông; GRIT không có mặt cắt.

Nếu không lấy được các nguồn trên, phương án có bằng chứng tốt nhất hiện là **RF_compact để nghiên cứu EC tại trạm**, kèm cảnh báo riêng cho tháng mặn cực trị và không dùng cho quyết định cống. `scripts/train_ec_compact_candidate.py` đã fit lại trên 463 nhãn Mỹ Tho đến 12/2023, lưu mô hình và manifest trong `outputs/ec_compact_candidate_20261029/`. Ước tính nghiên cứu cho mẫu 11/2026 là **15,005 mS/m**, nhưng chưa có nhãn EC sau 2023 để kiểm chứng và không thay mô hình trong API/registry. Để tái lập: chạy `python -m scripts.experiment_ec_extreme_robust --delay 5`, `--delay 35`, `python -m scripts.summarize_ec_compact`, rồi `python -m scripts.train_ec_compact_candidate`.
