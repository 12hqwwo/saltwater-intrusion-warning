# Quyết định hiện tại cho dự báo EC và hỗ trợ cống Đồng Tháp mới

Ngày 29/10/2026. Đây là điểm chốt sau các thử nghiệm có thể thực hiện với dữ liệu hiện có, không phải công bố mô hình thủy lực đã hiệu chuẩn. Mục tiêu mô hình chấm là **EC của một mẫu MRC trong tháng tại Mỹ Tho** (mS/m); đó không phải đỉnh mặn giờ, độ mặn tại từng cống hoặc thời gian truyền muối.

## 1. Mô hình có bằng chứng tốt nhất hiện tại

Giữ **RF_compact** làm ứng viên nghiên cứu. Tám biến biết được theo giả định ngày phát hành: mùa bằng sin/cos, mưa t−2, Q Kratie t−2/trung bình ba tháng/tỷ số lịch sử, và mực nước Tân Châu t−2/trung vị ba tháng. Không có EC lag nên mô hình vẫn tính được khi nhãn mới nhất chỉ đến 12/2023. Backtest huấn luyện lại tại mỗi ngày phát hành giả định, dùng nhãn EC công bố sau cuối tháng +5 hoặc +35 ngày. Ngày công bố thực của từng mẫu và lịch sử phiên bản MRC/ERA5 không có, vì vậy kết quả chỉ đúng **theo giả định**.

| MAE mS/m, cùng tháng | RF cũ | RF_compact | Diễn giải |
|---|---:|---:|---|
| 2019–2021 toàn kỳ, +5 ngày, 36 tháng | 71,56 | **50,87** | Giảm 28,9%; đây là kỳ chọn đã xem. |
| 2019–2021 EC ≥100, +5 ngày, 6 tháng | 324,24 | **259,37** | Đỉnh mặn vẫn sai rất lớn, đều dự báo thấp. |
| 2022–2023 toàn kỳ, +5 ngày, 24 tháng | 18,63 | **11,07** | Cải thiện hồi cứu, kỳ này đã được xem; không có tháng EC ≥100. |
| 2019–2021 toàn kỳ, +35 ngày | 71,26 | **55,30** | Kết quả nhạy với giả định công bố. |

Đã thử RF cây mịn, Extra Trees, Gradient Boosting Huber, KNN, XGBoost, LightGBM, FES triều và phối với Persistence. RF cây mịn cải thiện chút ở 2019–2021 nhưng xấu đi 2022–2023; phối Persistence cải thiện 2022–2023 nhưng xấu đi 2019–2021 và không có tác dụng khi nhãn 2026 đã cũ. Chưa có phương án thắng ổn định qua các kỳ. Dự báo 03/2020 là 182,48 so với thực đo 692 mS/m, lệch 509,52. Vì vậy chưa dùng ứng viên cho lệnh cống. Chi tiết và dữ liệu từng tháng: `docs/ec_compact_recalibration_2026-10-29.md`, `docs/ec_advanced_search_2026-10-29.md`, `outputs/ec_compact_summary_20261029/`.

## 2. Thủy lực và vị trí cống đã chứng minh được gì

FES2022b điểm `south` (106,78333°E; 10,05000°N) là ứng viên **biên triều thiên văn ngoài cửa Tiểu** đã đối chiếu dao động với Vàm Kênh. Các ô cửa Đại, Hàm Luông và Cổ Chiên chỉ là ứng viên chưa có kiểm định tại từng cửa. GRIT cho tuyến sông có hướng tham khảo: từ nút gần Tân Châu đến Cửa Tiểu xấp xỉ 196,69 km, Mỹ Thuận 88,94 km, Mỹ Tho 43,17 km. Đây không phải khoảng cách thủy lực khảo sát, vận tốc hay độ trễ mặn. Trong 27 cống có tọa độ của Tiền Giang cũ, cả 27 nằm trong Đồng Tháp mới nhưng 10 cống cách đường GRIT gần nhất hơn 2 km; GRIT thiếu nhiều kênh và kết nối cống. Bốn hồ sơ cống Đồng Tháp cũ chưa có tọa độ.

Quan trắc mực nước MRC Vàm Kênh–Mỹ Thuận cho thấy pha sóng triều thường trễ khoảng 2–3 giờ; cố định lag 135 phút chọn ở 2019–2021 cho tương quan 0,958 ở 2022–2023 và 0,947 ở 2024–2026. **Đó là sóng mực nước**, không phải dòng nước hay muối đi 88,94 km trong 135 phút. Không áp lag này để chuyển EC giữa trạm. Chi tiết: `docs/fes_tide_boundary_validation_2026-10-29.md`, `docs/grit_gate_feasibility.3_2026-10-29.md`.

## 3. Quyết định về dữ liệu mới và việc tiếp tục

Đã tải [GFZ Sơn Đốc/Tân Châu](https://doi.org/10.5880/GFZ.4.4.2024.004) và bảo toàn 67 hàng độ mặn từ [bản tin thủy lợi Tiền Giang](https://thuyloitiengiang.vn/en-AU/web/thuyloitiengiang/chi-tiet-tin-tuc?id=486406). Chúng là g/L, khác EC, thiếu thời kỳ chồng thích hợp với kỳ chấm; không dùng để tạo nhãn EC giả. [GTSM-ERA5-E](https://essd.copernicus.org/articles/18/5759/2026/) là ứng viên nước dâng/mực nước tổng 1950–2024, chưa tải vì CDS cần tài khoản và chấp nhận điều khoản, và không thay mực nước đo tại cửa. Audit nguồn: `docs/new_data_search_2026-10-29.md`.

Việc có thể làm với dữ liệu sẵn có là giữ bảng sai số RF_compact có phân nhóm, hiển thị quan trắc độ mặn g/L của bản tin ở lớp riêng kèm nguồn/giờ, dùng FES và GRIT để chuẩn bị biên/mạng mô hình. **Không phát hành trường mặn dọc sông hoặc thời điểm đóng/mở cống dựa trên nội suy EC tháng**: chưa có cặp đo đồng thời EC/Cl⁻ ở nhiều trạm, Q phân lưu hai chiều, bathymetry/mặt cắt và kết nối kênh–cống được xác minh. Muốn giảm sai số dự báo hiện hành và đánh giá ngoài mẫu, ưu tiên lấy nhãn EC25 2024–2026 tại Mỹ Tho và các trạm dọc Tiền, kèm giờ đo, nhiệt độ, độ sâu, QA, ngày công bố. Sau đó mới thử mô hình đa trạm và hiệu chuẩn vận chuyển chất trên các mùa khô chưa dùng chọn mô hình. Bất kỳ mô hình nào trước đó đều chỉ là minh họa/kịch bản.
