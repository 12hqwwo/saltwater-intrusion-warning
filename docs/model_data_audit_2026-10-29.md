# Rà soát dữ liệu để củng cố dự báo EC tháng

Ngày kiểm tra: 29/10/2026. Mục tiêu hiện tại là **giá trị một mẫu EC trong tháng kế tiếp** tại Mỹ Tho và Tân Châu, đơn vị mS/m. Đây không phải dự báo độ mặn tại từng cống. Dữ liệu gốc và mô hình đang phục vụ không bị ghi đè trong đợt rà soát này.

## 1. Dữ liệu đã làm sạch và giữ lại

- Đối chiếu gói MRC gốc với `data/research/mrc_ec_monthly_samples.csv`: 927/927 nhãn khớp, không có tháng thiếu/trùng hay EC âm/không hữu hạn. Bảng `outputs/multivariate_error_audit_20261029/ec_qc_review.csv` giữ nguyên 927 giá trị và chỉ gắn 41 cờ cực trị để rà hồ sơ. Cờ này không loại nhãn.
- Dựng lại `outputs/ec_feature_research_20261019/feature_matrix.csv` với 2.000 dòng = hai trạm × 500 tháng × hai giả định độ trễ EC. Có 927 dòng mang nhãn gốc ở mỗi kịch bản trễ, giữ cả cực trị. Khóa ghép `station + target_month + ec_delay_days`; tháng sau 12/2023 không tự sinh EC. Thời điểm quan sát và thời điểm giả định khả dụng được ghi riêng. Giá trị thiếu giữ NULL, không thay bằng 0.
- Trong bảng đặc trưng v2 cũ, 98 nhãn Mỹ Tho và 19 nhãn Tân Châu không còn ở cột mục tiêu do cờ QA nội bộ dựa vào IQR/biến động. Giá trị EC cao nhất còn lại ở v2 Mỹ Tho chỉ 50,7 mS/m, trong khi nguồn có 841 mS/m. **Không dùng v2 cũ để kết luận mô hình dự báo EC cao.** Những nhãn v2 còn lại khớp nguồn; lỗi là loại nhãn, không phải đổi số. Script `scripts/train_multivariate_ec.py` của mô hình đa biến đang phục vụ đọc đủ bộ MRC ở `data/research/mrc_ec_monthly_samples.csv`, không đọc nhãn v2 này.
- Đã sửa `data/metadata/target_definition.md` và `data/metadata/data_dictionary.md`: EC là một phép đo/tháng; `1 mS/m = 0,01 mS/cm`, không phải 0,1 mS/cm; không suy độ mặn bằng hệ số cố định. Đã cập nhật `data/metadata/data_source_inventory.csv` về trạng thái FES2022b và provenance khí tượng cũ.

## 2. Kiểm tra khả dụng và độ tin cậy từng nguồn

| Nguồn | Độ phủ đã căn trước phát hành trong 927 tháng có nhãn | Quyết định hiện tại |
| --- | --- | --- |
| EC MRC | 463 Mỹ Tho + 464 Tân Châu, đến 12/2023 | Nhãn chính và EC trễ; giữ cờ `UNVERIFIED`, 41 cực trị chỉ rà hồ sơ. Không cắt ngọn hoặc xóa. |
| Mưa, nhiệt độ, ET0, độ ẩm, bức xạ, gió cũ | Đủ 927/927 sau căn 5 ngày trong thí nghiệm cuối tháng trước | Có thể thử đặc trưng quá khứ. CSV cũ thiếu metadata xác nhận đơn vị gió và phiên bản nguồn; không gán nhãn ERA5-Land hoặc m/s khi chưa có manifest. |
| Độ ẩm đất và hướng gió ERA5 tải riêng | Đủ 927/927; ô ERA5 là đại diện lưới, không trùng trạm đo EC | Ứng viên nghiên cứu. JSON có tọa độ ô và đơn vị; bản tải hồi cứu không phải bản đã có tại ngày dự báo lịch sử. |
| ENSO Niño 3.4 NOAA | Trễ 2 tháng: 425/463 và 426/464; trễ 3/6 tháng đủ | Giữ để thử giả thuyết khí hậu, chưa có lợi ích tăng thêm ổn định. Không dùng trị số được công bố sau ngày phát hành. |
| Lưu lượng GFZ Tân Châu | 350/463 và 351/464; kết thúc tháng mục tiêu 02/2017 | Không giúp chấm 2020–2023. 1980–1995 có phần tái dựng; chỉ xem nhánh số đo giai đoạn sau 1995 và giữ cờ nguồn. |
| Lưu lượng GloFAS | Mỹ Tho 0/463; Tân Châu 434/464 nhưng ô lưới chưa xác minh | Không gắn ô Mỹ Tho theo tên trạm. Ô Tân Châu chỉ nghiên cứu riêng, chưa nâng lên feature chính. |
| Mực nước DAHITI | Mỹ Tho 184/463; Tân Châu 136/464; trong 2020–2023 lần lượt 48/48 và 0/48 | Mẫu vệ tinh thưa; chưa xác nhận hệ cao độ/điểm đại diện; không nội suy khoảng trống dài. |
| Mực nước biển UHSLC Vũng Tàu | 453/463 và 453/464; trong 2020–2023 đủ 48/48 mỗi trạm | Là mực nước ven biển, không phải biên độ triều tại cống. Chỉ thử proxy với độ trễ giả định. |
| FES2022b | 34 thành phần và mask đã thu thập; không phải chuỗi EC quan trắc | Điểm lấy mẫu, bờ biển, hệ cao độ và đối chiếu với số đo triều chưa hoàn tất. Thí nghiệm FES trước chưa cải thiện Mỹ Tho, nên không thêm mặc định. |
| Nhiệt độ nước MRC | 500 cặp trùng timestamp với EC, 250/trạm, 2003–2023 | Chưa chứng minh cùng mẫu và cơ sở bù nhiệt EC vẫn `UNKNOWN`; không dùng để tự đổi EC sang độ mặn. Nếu làm feature, phải lấy **nhiệt độ trước ngày phát hành**, không lấy nhiệt độ cùng mẫu mục tiêu. |
| Bộ v3 người dùng cung cấp | 640 dòng/47 trạm; 387 nhãn ngày sau, 53 lệch lịch lag và 5 vị trí đo mơ hồ | Mục tiêu độ mặn ngày và vị trí khác EC tháng MRC. Giữ ở staging, không ghép trực tiếp để tăng số nhãn hoặc dùng cho khuyến nghị cống. |

Độ phủ ở bảng này là cho **giả định phát hành cuối tháng trước** trong `scripts/research_ec_features.py`. Nó không chứng minh nguồn đã công bố đúng lúc trong lịch sử. Giao thức backtest mới ở `scripts/backtest_asof_ec.py` dùng **ngày 06 tháng trước**, nên phải căn lại từng feature theo mốc đó rồi mới xét dùng trong mô hình chính.

## 3. Biến nào đã cho ích lợi dự báo?

Thí nghiệm riêng `outputs/ec_feature_research_20261019/`: validation 2014–2019, chọn cấu hình tại đây; chấm hồi cứu 2020–2023. Mô hình refit theo năm, so cùng tháng và giữ đủ nhãn. Dữ liệu hồi cứu và giả định công bố nguồn giới hạn kết luận; đây không phải kiểm định mù mới hay kết quả của mô hình WebGIS đang phục vụ.

| Trạm và kịch bản EC sẵn có | Kết quả cùng Random Forest trên validation | Kết luận |
| --- | --- | --- |
| Mỹ Tho, trễ 0 ngày | RF nền MAE 25,10; thêm độ ẩm đất 21,56 mS/m (giảm 14,1%), nhưng khoảng bootstrap lợi ích còn chứa 0 | Ứng viên, chưa đủ chắc chắn. |
| Mỹ Tho, trễ 30 ngày | RF nền 31,20; thêm độ ẩm đất 24,52 (giảm 21,4%, thắng 4/6 năm và qua sàng lọc thăm dò) | Đáng kiểm tra lại bằng giao thức phát hành ngày 06; chưa chứng minh thắng baseline tốt nhất. |
| Tân Châu, trễ 0 ngày | RF nền 1,329; thêm hướng gió 1,268 (giảm 4,6%, thắng 6/6 năm), dưới mức lợi ích tối thiểu 5% đã khóa | Có tín hiệu nhỏ, chưa đủ để thay mô hình. |
| Cả hai trạm | Thêm **tất cả** nhóm làm RF tăng MAE: Mỹ Tho 25,10 → 30,62; Tân Châu 1,329 → 1,843 mS/m | Không nhồi toàn bộ dữ liệu vào mô hình. |

Trên 2020–2023 (48 tháng/trạm, EC trễ 0), Mỹ Tho: cấu hình chọn Ridge chỉ dùng EC/mùa vụ MAE 48,69, cao hơn Persistence 40,85; 7 mẫu EC cao có MAE 300,62. Tân Châu: thêm hướng gió RF MAE 2,253 so với RF nền 2,308, nhưng vẫn còn bias âm. Nhánh GFZ, DAHITI, GloFAS và UHSLC thử trên **những tập tháng khác nhau** nên không xếp hạng chéo; chưa có bằng chứng ổn định và đủ tin cậy để tích hợp. Tất cả MAE tính bằng mS/m.

## 4. Dữ liệu cần bổ sung, theo thứ tự

1. **Ưu tiên cao nhất: EC đo thật tại chính hai trạm từ 01/2024 đến nay.** Xuất CSV/API với mã trạm MRC, timestamp (kèm múi giờ), giá trị, đơn vị, cờ QA và ngày công bố/chỉnh sửa nếu có. Đây là tập mới để chấm độc lập sau khi khóa cấu hình. Không dùng dự báo 2024–2026 làm nhãn.
2. **Metadata của EC gốc**: quy trình lấy mẫu, thiết bị, cơ sở bù nhiệt/EC25, quyết định duyệt QA, lịch sử công bố, nhất là hồ sơ các tháng EC rất cao. Không cần sửa EC dựa trên tin báo chí; tin chỉ giải thích bối cảnh vùng.
3. **Lưu lượng hoặc mực nước đo có chuỗi chồng với EC** tại Tân Châu và điểm hạ lưu gần Mỹ Tho, tốt nhất từ ít nhất 2016 đến nay. Mỗi dòng cần thời điểm đo, tọa độ/mã trạm, đơn vị, mốc cao độ nếu là mực nước, nguồn/phiên bản, thời điểm công bố. Chuỗi mực nước Tân Châu 2026 đã có trong kho nhưng chưa đi cùng EC 2024–2026 nên chưa thể dùng để chứng minh cải thiện lỗi dự báo mới.
4. **Nếu mục tiêu là quyết định theo cống/độ mặn:** chọn 1–3 cống pilot; cung cấp EC và độ mặn đo đồng thời cùng điểm, nhiệt độ nước, mực nước hai phía cùng hệ cao độ, trạng thái và timestamp đóng/mở, cùng bản đồ nối sông/kênh. Dữ liệu này phục vụ bài toán mới, không cộng thẳng vào 927 nhãn MRC.

Nếu chỉ bổ sung được một thứ ngay, hãy gửi **EC 2024–2026 đúng hai mã trạm**. Các biến thời tiết/ENSO mới ít giá trị hơn khi chưa có nhãn mới để chứng minh chúng cải thiện dự báo.

## 5. Kiểm chứng đã chạy

- `scripts/research_ec_features.py prepare/evaluate`, `scripts/research_ec_hydrology.py`, `scripts/summarize_ec_feature_research.py` tạo bảng dữ liệu, chấm đối chứng và báo cáo chi tiết.
- `scripts/check_ec_feature_research.py` đạt các kiểm tra khóa trạm-tháng, checksum nguồn, thời gian khả dụng giả định, chống dùng khí tượng tương lai, cùng tập tháng cho cấu hình so sánh và train trước test; lưu `outputs/ec_feature_research_20261019/verification.json`.
- Chưa đổi artifact mô hình WebGIS vì thử nghiệm feature dùng ngày phát hành khác giao thức chính và chưa thắng baseline một cách nhất quán. Bước tiếp theo sau khi có EC mới là khóa lại feature hợp lệ ở ngày 06 rồi chấm cùng một phép backtest theo ngày phát hành.
