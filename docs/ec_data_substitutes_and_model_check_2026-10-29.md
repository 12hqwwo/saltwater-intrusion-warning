# Kiểm tra dữ liệu thay thế và đổi mô hình EC Mỹ Tho

Ngày 29/10/2026. Mục tiêu: EC của **một mẫu MRC trong tháng** tại Mỹ Tho, phát hành giả định ngày 06 tháng trước. Mọi so sánh 2019–2023 giữ nguyên 60 tháng, đơn vị mS/m và hai giả định EC được công bố sau cuối tháng 5 hoặc 35 ngày. Dữ liệu hồi cứu ERA5/MRC không có lịch sử phiên bản theo ngày phát hành, nên đây chưa phải kiểm định dự báo vận hành thực.

## Đổi thuật toán có giảm sai số không?

Đã thử RF dùng Q Kratie + mực nước Tân Châu + thời tiết, rồi thử XGBoost dạng thô/log và LightGBM dạng thô trên **cùng các đặc trưng, nhãn và từng tập huấn luyện theo ngày phát hành**. Các tham số cố định trong `scripts/experiment_ec_boosting_20261029.py`; không chọn tham số bằng tập 2022–2023. Kết quả ở `outputs/ec_boosting_20261029/`.

| Mô hình không dùng EC quá khứ | MAE 2019–2021, +5 ngày | MAE 2022–2023, +5 ngày | MAE 2019–2021, +35 ngày | MAE 2022–2023, +35 ngày |
|---|---:|---:|---:|---:|
| RF cũ | 71,56 | 18,63 | 71,26 | 18,61 |
| **RF Q Kratie + mực nước Tân Châu** | **58,68** | 13,52 | **60,72** | 13,19 |
| XGBoost thô | 66,82 | 14,28 | 67,56 | 14,57 |
| XGBoost log | 70,51 | **9,74** | 71,18 | **10,04** |
| LightGBM thô | 63,55 | 18,81 | 62,77 | 22,64 |

XGBoost log có điểm thấp hơn trên 2022–2023 nhưng **kém nhiều trên 2019–2021**, đặc biệt sáu tháng EC ≥100 mS/m có MAE 378–379 mS/m, so với RF 286–303 mS/m. Không đổi mô hình đang phục vụ theo kết quả riêng của hai năm hồi cứu vốn đã từng được xem. Giữ RF thủy văn làm ứng viên nghiên cứu tốt hơn ở kỳ chọn. Đây là kết quả của ba cấu hình boosting cụ thể, không phải phủ định mọi mô hình boosting.

## Dữ liệu đã kiểm tra thêm

| Nguồn | Đã có gì | Có thể dùng cho mô hình EC tháng hiện tại? |
|---|---|---|
| [MRC Data Portal](https://portal.mrcmekong.org/time-series) | Đã tải Q tính toán ngày Kratie 1985–2026, mực nước Tân Châu 1985–2026 và thêm EC/mực nước trạm vùng. Inventory Việt Nam có 17 chuỗi `Conductivity`, **không có chuỗi `Discharge` Việt Nam** trong snapshot đã lưu. | Q Kratie + mực nước Tân Châu đã giảm MAE khi chấm như trên. EC trạm vùng còn thưa; không tạo nhãn ngày/giờ. |
| [Binh và cộng sự, Mendeley Data 2021](https://data.mendeley.com/datasets/xnzvfcyy68/1) | **Đã tải** workbook Q ngày Tân Châu, 8.869 ngày không trùng khóa, 1980–2015, m³/s, hai sheet huấn luyện/kiểm tra; SHA-256 và URL trong `data/external/tanchau_discharge_mendeley_20261029/manifest.json`. | Hữu ích cho **hiệu chuẩn/kiểm tra lịch sử** Q thượng lưu. Không có Q 2019–2023 hoặc 2026; workbook không đánh dấu từng hàng là đo trực tiếp hay tái dựng. Không giả định là Q đo mới. |
| [ICOE MarineMekong](https://marinemekong.com/) | Đã kiểm tra giao diện: trạm được hiển thị, có bản đồ/biểu đồ dự báo triều 29/10–03/11/2026 và link NetCDF dòng chảy ngày hiện tại. | Đây là **dự báo/hiển thị hiện tại**; chưa thấy tệp lịch sử EC, Q hay triều đo đồng thời 2019–2023 có thể tải. Không trộn dự báo Delft3D vào nhãn quan trắc. |
| [SIWRR Mekong Forecast](https://siwrr.com/Forecast) | Ứng dụng mô tả giám sát độ mặn, nhiệt độ, mực nước, pH tại mạng trạm. | Trang công khai không cung cấp bảng lịch sử thô tải trực tiếp; không dựa tiến độ vào phản hồi xin dữ liệu. |
| [Bản đồ mặn Zenodo 2015–2025](https://zenodo.org/records/20003854) | Bản đồ mặn bề mặt 30 m được mô hình hóa, có metadata trạm. | Có ích để mô tả không gian hoặc so kiểm ngoài mẫu nếu xác minh độc lập. **Không dùng làm nhãn đo hay đặc trưng backtest 2019–2023** vì sản phẩm hậu nghiệm đã học từ quan trắc cùng thời kỳ, nguy cơ rò rỉ nhãn. |
| [Bài Vàm Kênh 2026](https://www.mdpi.com/2073-4441/18/19/2379) | Nghiên cứu sử dụng 721 quan trắc mặn ngày 2020–2025. | Chưa có file gốc công khai tải trực tiếp; không trích số liệu từ hình vẽ thành nhãn. |

## Kết luận thực hiện

Mức cải thiện kiểm chứng được đến từ **đặc trưng thủy văn thượng lưu** nhiều hơn việc đổi tên thuật toán. RF hiện giảm MAE 2019–2021 từ 71,56 xuống 58,68 mS/m với giả định +5 ngày, nhưng các tháng mặn cực trị còn sai rất lớn. Bộ Q Tân Châu vừa tải không thể thay thế Q ở Vàm Nao, Mỹ Thuận hay phân nhánh cửa sông trong 2019–2023. Không có dữ liệu công khai đã kiểm chứng để suy chính xác thời gian truyền mặn theo giờ/ngày. Nếu làm tiếp trong giới hạn dữ liệu hiện có, báo cáo nên trình bày mô hình **dự báo EC một trạm có tín hiệu Q thượng lưu**, cùng bảng lỗi riêng mùa khô/EC cao; không gọi nó là mô hình lan truyền mặn đã hiệu chuẩn.
