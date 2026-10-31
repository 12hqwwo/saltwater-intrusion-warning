# Kiểm tra đặc trưng EC và phương án kết hợp triều thủy văn

Ngày 29/10/2026. Đầu ra là **EC của một mẫu MRC trong tháng tại Mỹ Tho, mS/m**, không phải độ mặn g/L hay thời gian truyền mặn. Mỗi tháng hồi cứu huấn luyện lại từ nhãn giả định đã có tại ngày 06 tháng trước; dữ liệu Q/mưa/mực nước ở tháng t−2. FES triều thiên văn của cửa Tiểu tính trước được cho cửa sổ cố định ngày 09–15 của tháng mục tiêu. Không dùng ngày đo EC thực tế để chọn cửa sổ vì tại ngày phát hành chưa biết ngày đo. Hai giả định công bố nhãn +5/+35 ngày; 2019–2021 là kỳ chọn đã xem, 2022–2023 là kiểm tra hồi cứu cũng đã xem.

## Nhóm biến nào giúp dự báo

Bỏ **một nhóm** khỏi tám biến RF_compact, giữ cùng 60 tháng và giao thức +5 ngày. MAE mS/m; tăng MAE khi bỏ biến là đóng góp dự báo trong cấu hình này, **không phải tác động nhân quả của một yếu tố vật lý**.

| Nhóm bị bỏ | 2019–2021, 36 tháng | 2022–2023, 24 tháng | EC ≥100 ở 2019–2021, 6 tháng |
|---|---:|---:|---:|
| Không bỏ, RF_compact | **50,87** | **11,07** | **259,37** |
| Mùa sin/cos | 52,91 | 12,13 | 262,03 |
| Mưa t−2 | 62,39 | 14,42 | 310,33 |
| Q Kratie t−2 / trung bình / tỷ số lịch sử | **69,93** | **21,62** | 308,56 |
| Mực nước Tân Châu t−2 / 3 tháng | 52,07 | 11,84 | 265,57 |

**Q Kratie là nhóm có đóng góp dự báo lớn nhất trong phép thử bỏ nhóm này**, kế đến là mưa. Mực nước Tân Châu và mùa vẫn giúp một ít. Các biến có thể tương quan và Random Forest sẽ phân chia lại khi thiếu nhóm, nên không được diễn giải độ chênh MAE thành “phần trăm nguyên nhân xâm nhập mặn”. Q Kratie là dòng thượng nguồn, chưa thể hiện chia lưu tại Vàm Nao/Mỹ Thuận; mực nước Tân Châu không phải Q hai chiều.

## Ghép triều FES và Q

Thử thêm (1) biên độ triều FES `south` ngày 09–15 tháng mục tiêu, (2) thêm biến tương tác `FES_range / max(Q_ratio_t−2, 0,25)`. RF, seed và các tháng chấm giữ nguyên. Tệp từng tháng và chỉ số ở `outputs/ec_tide_flow_interaction_20261029/`; script `scripts/experiment_ec_tide_flow_interaction.py`.

| Kỳ / giả định | RF_compact | +FES | +FES và tương tác Q |
|---|---:|---:|---:|
| 2010–2018, +5, 108 tháng | **14,76** | 14,99 | 15,16 |
| 2019–2021, +5, 36 tháng | **50,87** | 50,84 | 52,50 |
| 2019–2021, +35, 36 tháng | 55,30 | **53,58** | 55,87 |
| 2022–2023, +5, 24 tháng | 11,07 | 10,84 | **9,98** |
| 2022–2023, +35, 24 tháng | 11,25 | 11,13 | **9,90** |

FES đơn lẻ có cải thiện nhỏ ở 2019–2023, nhưng **xấu hơn trên toàn kỳ 2010–2018**, nên chưa chứng minh lợi ích ổn định. Biến tương tác giúp kỳ hồi cứu 2022–2023 nhưng xấu hơn cả 2010–2018 và 2019–2021. Ở sáu tháng EC cao 2019–2021, MAE vẫn từ 256,84 đến 280,74 mS/m tùy giả định/cấu hình. **Giữ RF_compact; chưa đổi artifact/API.** 2010–2018 và 2022–2023 đều đã được xem trong quá trình nghiên cứu, vì vậy các so sánh không phải test mù mới. Thiếu nhãn EC từ 2024 để xác nhận cho hiện tại.

Pha sóng mực nước Vàm Kênh–Mỹ Thuận 2–3 giờ cho thấy triều vào sông và có lý do nghiên cứu triều kết hợp Q. Tuy nhiên EC một mẫu/tháng không cho biết pha triều lúc mẫu được lấy; FES là triều thiên văn, không có nước dâng/gió/biên nồng độ. [Eslami và cộng sự 2021](https://esurf.copernicus.org/articles/9/953/2021/index.html) cho thấy xâm nhập mặn Mekong phụ thuộc đồng thời Q, triều, gió/nước dâng và hình học/đáy sông. [Nghiên cứu dự báo mùa khô 2020](https://nhess.copernicus.org/articles/20/1609/2020/index.html) cung cấp cơ sở cho dòng chảy tiền mùa khô; những tài liệu này là **căn cứ chọn giả thuyết**, không xác nhận biến FES đã cải thiện EC Mỹ Tho.

## Kiến trúc kết hợp khi đủ dữ liệu

1. Mô hình thủy lực–vận chuyển chất dùng Q hai chiều/phân lưu, mực nước tổng từng cửa (triều + nước dâng), bathymetry/mặt cắt, kênh/cống và biên nồng độ. Hiệu chuẩn trên EC25 hoặc Cl⁻/độ mặn đồng thời nhiều trạm; phải đo quan hệ EC–độ mặn cùng nơi, nhiệt độ và độ sâu trước khi chuyển đại lượng.
2. Dùng kết quả vật lý tại **đúng trạm và thời điểm mẫu** làm biến trong mô hình dự báo EC hoặc học phần dư `EC đo - EC suy từ vật lý`. Chấm theo ngày phát hành: forcing nào không biết lúc phát hành phải là **dự báo forcing**, không lấy reanalysis tương lai. Giữ baseline và RF_compact trên đúng các tháng.
3. Chỉ đưa ra hỗ trợ cống sau kiểm định ngoài mẫu ở trạm/cống và mùa khô chưa dùng chọn mô hình; cần số đo hai phía cống cùng nguồn ngưỡng có thẩm quyền. Với dữ liệu hiện có, đây là thiết kế nghiên cứu, chưa phải mô hình đã hiệu chuẩn.

Để tái lập phép thử: `python -m scripts.experiment_ec_compact_group_ablation`; `python -m scripts.experiment_ec_tide_flow_interaction --delay 5`; thêm `--delay 35`; và `--delay 5 --history`. Mỗi script kiểm số tháng và khớp nhãn với baseline trước khi ghi kết quả.
