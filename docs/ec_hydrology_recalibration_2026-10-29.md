# Hiệu chỉnh EC Mỹ Tho bằng lưu lượng Kratie và mực nước Tân Châu

Ngày kiểm tra: 29/10/2026. **Mục tiêu là EC (mS/m) của một mẫu MRC trong tháng tại Mỹ Tho, không phải EC trung bình tháng, độ mặn g/L hay ranh mặn.** Nhãn EC hiện có kết thúc 12/2023. Mọi số liệu dưới đây là kiểm tra hồi cứu theo giả định ngày phát hành; chưa chứng minh dự báo vận hành 2024–2026.

## 1. Dữ liệu tìm và kiểm tra

Từ [MRC Data Portal](https://www.mrcmekong.org/data-and-information-systems-and-services/) và inventory công khai đã tải **lưu lượng tính toán Kratie (Campuchia) 1985–28/10/2026, 22.161 bản ghi, m³/s**; **mực nước thủ công Tân Châu 1985–2026**; lịch sử Mỹ Thuận, Vàm Kênh, Vàm Nao; bốn chuỗi EC vùng lân cận còn thiếu. Tổng cộng **28 chuỗi** trong các gói lưu ở `data/external/`. File JSON gốc, CSV trích xuất, URL, thời điểm lấy, đơn vị, cờ MRC và SHA-256 nằm trong từng `manifest.json`. `scripts/audit_tien_multisite.py` kiểm đủ 28 chuỗi: checksum, số dòng, thời điểm không trùng và EC không âm. Bảng chi tiết: `outputs/tien_multisite_audit_20261029/series_coverage.csv`.

Kratie và Tân Châu đều có **60/60 tháng 2019–2023**; ở đúng 60 tháng nguồn t−2 của tập chấm 2019–2023, cả hai đều đạt điều kiện **ít nhất 20 ngày/tháng**. Đối chiếu ngày trùng giữa mực nước thủ công và telemetry Tân Châu có **1.809 ngày, tương quan 0,986, trung vị chênh lệch tuyệt đối 0,05 m** (`manual_telemetry_agreement.json`). Điều này hỗ trợ kiểm tra chuỗi, **không xác nhận hai thiết bị có cùng mốc cao độ**. MRC gắn cờ `UNVERIFIED` cho các chuỗi lấy được; không tự nâng cấp cờ. EC cực trị gốc được giữ nguyên.

Đã rà **10 chuỗi EC MRC trong inventory vùng**. Mỹ Thuận và Tứ Thường có đủ 60 tháng 2019–2023; Cái Mơn, An Long, Tuyên Nhơn, Hồng Ngự, Phong Mỹ chỉ có lịch sử cũ; Cần Thơ thuộc nhánh Hậu. Thử thêm EC Mỹ Thuận và EC Tân Châu cũ đã làm MAE Mỹ Tho tăng trong backtest trước (xem `tien_multisite_acquisition_2026-10-29.md` và `ec_model_recalibration_2026-10-29.md`). Do đó không ghép các trạm theo khoảng cách địa lý. Đã tải bộ [Q Tân Châu 1980–2015 trên Mendeley Data](https://data.mendeley.com/datasets/xnzvfcyy68/1): 8.869 ngày trong hai sheet huấn luyện/kiểm tra, không có Q 2019–2023 ở phân lưu; **chưa đưa vào mô hình**. Nghiên cứu [Thanh và cộng sự (2022)](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2021WR031048) cho thấy Q Tân Châu trong vùng có triều không thể suy bằng một quan hệ mực nước–lưu lượng cố định. Kết quả thử XGBoost/LightGBM và các nguồn thay thế ở [báo cáo bổ sung](ec_data_substitutes_and_model_check_2026-10-29.md).

## 2. Giao thức không nhìn tương lai

- Phát hành ngày **06 tháng trước**. Cho EC tháng mục tiêu là công bố sau cuối tháng **+5 ngày**, và lặp lại với **+35 ngày**. MRC không có lịch sử ngày công bố nên đây là giả định nhạy cảm.
- Chỉ đưa nhãn EC có `available_date <= issue_date` vào huấn luyện, huấn luyện lại ở **từng lần phát hành**. Thời tiết, lưu lượng Kratie và mực nước Tân Châu sử dụng tháng **t−2**. Giả định tháng thủy văn/thời tiết hoàn tất và có thể dùng sau cuối tháng +5 ngày. Bộ ERA5 hồi cứu không có bản lưu theo ngày phát hành, nên chưa loại bỏ được mọi rủi ro do phiên bản dữ liệu hiệu chỉnh về sau.
- Lưu lượng Kratie: trung bình các ngày có quan trắc trong tháng, cần ít nhất 20 ngày; trung bình 3 tháng và tỷ số so với trung vị cùng tháng của 15 năm **trước đó**. Mực nước Tân Châu: trung vị theo ngày rồi trung vị tháng, cần ít nhất 20 ngày; trung vị 3 tháng, cần 2 tháng. Mọi tỷ số chuẩn khí hậu chỉ dùng dữ liệu quá khứ.
- Tập phát triển 2015–2018; **2019–2021** chọn phương án; **2022–2023** kiểm tra hồi cứu. Hai năm sau đã từng được xem trong dự án, không phải test mù mới. Một mẫu EC/tháng gây sai số do thời điểm lấy mẫu và pha triều; không coi đó là trung bình tháng.
- MAE/RMSE đều tính trên **cùng 36 tháng** hoặc **24 tháng** với RF cũ được chấm lại bằng giao thức trên. Mùa khô ở đây là **tháng XII–IV**. Nhóm EC cao là **EC ≥100 mS/m**, ngưỡng phân tích lỗi, không phải ngưỡng vận hành.

## 3. Chọn đặc trưng và mô hình

Thử RF không biến đổi, RF log, Extra Trees, HGB; kết hợp hoặc bỏ đặc trưng EC quá khứ, mực nước một/bốn trạm và Q Kratie. Các thử nghiệm tái lập trong `scripts/experiment_ec_long_hydrology.py` và `scripts/experiment_ec_no_recent_label.py`. Đặc trưng Mỹ Thuận/Vàm Kênh/Vàm Nao, EC các trạm khác và mô hình log/Extra Trees/HGB **không thắng ổn định** RF đơn giản có Q Kratie/Tân Châu qua hai giả định công bố, nên không đưa vào ứng viên cuối. Chọn ứng viên **RF_flow_stage_no_ec** cho trường hợp hiện nay không còn EC mới: thời tiết và lịch, Q Kratie tháng t−2, Q 3 tháng, tỷ số Q với lịch sử, mực nước Tân Châu tháng t−2 và trung vị 3 tháng. RF 100 cây, sâu tối đa 7, lá tối thiểu 3, `max_features=0.8`, cố định seed 42; thiếu biến được điền bằng trung vị của tập huấn luyện từng lần.

| Mô hình, MAE mS/m | 2019–2021 +5 ngày (36) | 2022–2023 +5 ngày (24) | 2019–2021 +35 ngày (36) | 2022–2023 +35 ngày (24) |
|---|---:|---:|---:|---:|
| RF cũ chấm cùng giao thức | 71,56 | 18,63 | 71,26 | 18,61 |
| RF + Q Kratie + mực nước Tân Châu + EC quá khứ | **56,98** | **12,00** | 62,99 | **12,63** |
| **RF + Q Kratie + mực nước Tân Châu, không dùng EC quá khứ** | **58,68** | **13,52** | **60,72** | **13,19** |

Ứng viên không cần EC mới giảm MAE 2019–2021 khoảng **18% (+5 ngày)** và **15% (+35 ngày)** so với RF cũ; 2022–2023 giảm khoảng **27% và 29%**. RMSE 2019–2021 giảm từ 151,55 xuống 139,05 mS/m ở kịch bản +5, nhưng còn rất lớn. Nếu EC của Mỹ Tho được công bố đều, ứng viên có EC quá khứ đạt MAE thấp hơn ở +5; **không dùng nó cho 2026** vì nhãn cuối 12/2023.

### Lỗi chưa giải quyết

| Phân nhóm +5 ngày | RF cũ | RF không EC mới | Số tháng |
|---|---:|---:|---:|
| Năm 2020 | 139,31 | **129,14** | 12 |
| Mùa khô 2019–2021 | 128,94 | **118,68** | 15 |
| EC ≥100 mS/m 2019–2021 | 324,24 | **286,28** | 6 |
| EC <100 mS/m 2019–2021 | 21,02 | **13,16** | 30 |

Ở +35 ngày, riêng 2020 vẫn MAE **136,15 mS/m** (RF cũ 138,07); sáu tháng EC cao vẫn **302,66 mS/m**. Đỉnh EC 02–04/2020 có giá trị thật 558, 692, 607 mS/m, lớn hơn nhiều phần lớn nhãn huấn luyện từng thời điểm. RF không ngoại suy đỉnh này tốt. Không xóa hoặc “sửa” đỉnh bằng tin báo chí. Hạ MAE chung không đồng nghĩa mô hình đã giải quyết xâm nhập mặn cực đoan; phải trình bày bảng phân nhóm trong báo cáo.

## 4. Mạng sông và lan truyền

Lưu lượng Kratie là **biên nước ngọt thượng lưu thống kê**. Nó đi qua Tonle Sap, phân lưu và chịu triều trước khi đến Mỹ Tho, nên không được gọi là Q trực tiếp ở Tân Châu hoặc Vàm Nao. Trong cửa sông, nước ngọt đi xuống hạ lưu, còn nước mặn xâm nhập từ phía biển lên thượng lưu theo triều; không có một phép nội suy EC một chiều Tân Châu → Mỹ Tho. [Apel và cộng sự (2020)](https://nhess.copernicus.org/articles/20/1609/2020/) dùng tín hiệu lưu lượng để dự báo xâm nhập mặn theo mùa; [HESS (2020)](https://hess.copernicus.org/articles/24/189/2020/) mô tả các phân lưu và ảnh hưởng mạng đê; [Eslami và cộng sự (2021)](https://esurf.copernicus.org/articles/9/953/2021/) trình bày tương tác triều–dòng chảy–hình thái ở đồng bằng. Các nghiên cứu bổ sung về [tác động Q thượng lưu và mực biển (2024)](https://www.sciencedirect.com/science/article/pii/S2352485524003827) và [biến động mặn giữa các năm (2025)](https://www.sciencedirect.com/science/article/pii/S0022169425010832) củng cố lý do đưa Q vào mô hình; chúng không cung cấp nhãn EC đồng thời mới để tự động ghép vào dữ liệu này.

Mạng OSM trong `outputs/tien_network_20261029/` chỉ là một tuyến tham khảo Cửa Tiểu với 5 đoạn; chưa có kênh ngang, toàn bộ cửa sông, mặt cắt, độ sâu, lưu lượng hai chiều và hiệu chuẩn trạm. Vì vậy **chưa có mô hình lan truyền mặn vật lý chính xác**. Mô hình mới dự báo tại một trạm với biến thủy văn thượng lưu, không tạo trường mặn dọc sông. Nội suy mạng sông chỉ phù hợp khi có nhiều trạm đo đồng thời cùng đơn vị và đường kết nối xác minh; hiện không dùng để tạo nhãn giả.

## 5. Dữ liệu còn thiếu, theo tác động dự kiến

1. **EC/độ mặn theo giờ hoặc ngày cùng thời điểm tại Mỹ Tho, Mỹ Thuận, Vàm Kênh và các nhánh Cửa Đại, Hàm Luông, Cổ Chiên**. Đây là điều kiện quan trọng nhất để nhận ra đỉnh triều và đo thời gian trễ. Cần đơn vị, hiệu chỉnh nhiệt độ EC, độ sâu lấy mẫu, múi giờ, QA và lịch công bố. [Bài báo Vàm Kênh 2026](https://www.mdpi.com/2073-4441/18/19/2379) dùng 721 quan trắc ngày nhưng chưa công bố tệp đo tải trực tiếp. Người dùng đã liên hệ mà chưa được phản hồi; **không dựa kế hoạch tiến độ vào việc nhận bộ này**.
2. **Q tại Tân Châu, Vàm Nao, Mỹ Thuận và các nhánh**, có quy ước dấu và dữ liệu hai chiều dưới triều. Q Kratie đã có nhưng không cho biết phân chia lưu lượng. Bộ [Mendeley 1980–2015](https://data.mendeley.com/datasets/xnzvfcyy68/1) không phủ giai đoạn chấm gần đây. Mực nước thủ công không được đổi thành Q nếu chưa có quan hệ thủy lực hiệu chỉnh.
3. **Mực nước/triều cửa sông và hình học**: dữ liệu cùng datum, mạng kênh, mặt cắt, độ sâu, cống và lịch đóng mở. Đã thử chỉ số triều FES trước đây nhưng chưa giảm lỗi ổn định trên giao thức cũ (`outputs/fes_ec_multipoint_20261026/summary.json`), nên không đưa thêm chỉ số triều như thể là số đo mặn. Có thể dùng cho mô hình thủy lực sau khi có biên và số đo hiệu chuẩn.
4. **Nhãn EC mới từ 2024 trở đi** để chấm phát hành gần thời gian thực. Hiện hoàn toàn không có chuỗi đó trong dữ liệu truy cập được; không thể chứng minh độ chính xác 2026 bằng backtest 2019–2023.

## 6. Artifact và giới hạn dùng

Đã huấn luyện RF **không dùng EC gần đây** trên 463 nhãn Mỹ Tho đến 12/2023, lưu tại `outputs/ec_hydrology_forecast_20261029/mytho_no_recent_ec_model.joblib`. Với dữ liệu tháng 09/2026 có thể biết theo giả định vào 06/10/2026, script `scripts/forecast_mytho_ec_hydrology.py` tạo kết quả nghiên cứu cho **EC mẫu tháng 11/2026: 18,54 mS/m**. Đây là phép tính từ dữ liệu hồi cứu, **không có EC quan trắc sau 2023 để kiểm chứng** và không phải cảnh báo mặn hay quyết định vận hành. `manifest.json` lưu đặc trưng, nguồn, checksum, thời điểm và giới hạn. Đã nạp lại artifact và xác nhận dự báo bằng đúng giá trị đã ghi.

Không thay registry/API đang phục vụ bằng một mô hình chưa kiểm tra được trên nhãn 2024–2026. Để tái lập: chạy `python scripts/audit_tien_multisite.py`, `python scripts/experiment_ec_long_hydrology.py --delay 5` và `--delay 35`, `python scripts/experiment_ec_no_recent_label.py --delay 5` và `--delay 35`, `python scripts/summarize_ec_hydrology.py`, `python scripts/forecast_mytho_ec_hydrology.py`. File dự báo từng tháng và bảng lỗi theo năm/mùa khô/EC cao ở `outputs/ec_long_hydrology_20261029/`. Nguồn gốc và giới hạn tải dữ liệu được ghi trong `docs/tien_multisite_acquisition_2026-10-29.md`.
