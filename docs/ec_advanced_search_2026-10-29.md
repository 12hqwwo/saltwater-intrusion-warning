# Tìm tiếp phương án giảm lỗi EC Mỹ Tho sau RF_compact

Ngày 29/10/2026. Các script `scripts/experiment_ec_advanced_models.py` và `scripts/experiment_ec_advanced_blend.py` giữ mục tiêu **EC của một mẫu trong tháng**, ngày phát hành giả định 06 tháng trước, EC công bố sau cuối tháng +5 hoặc +35 ngày, thủy văn/khí tượng tháng `t−2`. Huấn luyện lại tại từng ngày phát hành từ nhãn đã giả định có. Hai kịch bản chấm cùng 36 tháng 2019–2021 và 24 tháng 2022–2023. Kỳ sau đã bị xem nhiều lần và không phải test mù. MRC/ERA5 không có lịch sử phiên bản theo ngày phát hành.

## 1. Mô hình không cần EC gần đây

Bốn cấu hình cố định thử thêm trên đặc trưng `RF_compact` hoặc tập con thủy văn: RF cây mịn hơn (`RF_fine`), Extra Trees cây mịn, Gradient Boosting loss Huber và KNN tương tự theo Q/mực nước. Không dùng 2022–2023 để chọn siêu tham số. Bảng MAE (mS/m):

| Giả định / kỳ | RF_compact | RF_fine | ET_fine | GB_huber | KNN_analog |
|---|---:|---:|---:|---:|---:|
| +5, 2019–2021, toàn kỳ | 50,87 | **49,29** | 53,80 | 69,36 | 60,52 |
| +5, 2019–2021, EC ≥100 (6 tháng) | 259,37 | **235,40** | 274,96 | 368,91 | 297,89 |
| +5, 2022–2023, toàn kỳ | **11,07** | 14,24 | 15,52 | 9,97 | 29,33 |
| +35, 2019–2021, toàn kỳ | 55,30 | **53,33** | 55,27 | 70,46 | 60,53 |
| +35, 2019–2021, EC ≥100 (6 tháng) | 285,24 | **259,78** | 282,27 | 374,64 | 297,90 |
| +35, 2022–2023, toàn kỳ | **11,25** | 14,45 | 15,25 | 10,07 | 29,36 |

`RF_fine` thắng MAE kỳ chọn và giảm lỗi cực trị hơn RF_compact, nhưng thua rõ trên 2022–2023 ở **cả hai** giả định công bố. `GB_huber` có MAE hồi cứu thấp nhưng bỏ lỡ đỉnh 2020, nên thất bại ở kỳ chọn. Không có bằng chứng đủ vững để thay `RF_compact` bằng các cấu hình này. Các bảng theo mùa khô, RMSE và từng tháng ở `outputs/ec_advanced_20261029/metrics_{5,35}d.csv` và `predictions_{5,35}d.csv`.

## 2. Phối baseline khi EC gần nhất còn mới

Trên 108 dự báo rolling-origin 2010–2018 do tác vụ chính đã tạo với giả định +5 ngày, thử trước các tỷ trọng RF_compact `0, 0,25, 0,5, 0,75, 1` **chỉ trong tháng XII–IV**, còn tháng khác dùng RF_compact. Trọng số 0,25 RF + 0,75 Persistence giảm MAE toàn kỳ 2010–2018 từ RF 14,76 xuống **11,98 mS/m**; là phương án tốt nhất trong lưới cố định. Thêm cổng chỉ dùng Persistence nếu nhãn EC gần nhất cách tháng mục tiêu không quá 3 tháng. Đây là lựa chọn theo lịch sử đã xem, không phải test mù.

| Giả định / kỳ | RF_compact toàn kỳ | Blend mùa khô toàn kỳ | RF_compact mùa khô | Blend mùa khô |
|---|---:|---:|---:|---:|
| +5, 2019–2021 | **50,87** | 51,35 | **106,86** | 108,03 |
| +5, 2022–2023 | 11,07 | **7,96** | 22,22 | **14,77** |
| +35, 2019–2021 | **55,30** | 64,98 | **110,13** | 133,38 |
| +35, 2022–2023 | 11,25 | **8,85** | 22,37 | **16,60** |

Blend cải thiện mạnh trên 2022–2023 nhưng **xấu hơn trên cả hai kỳ 2019–2021**, đặc biệt nếu EC ra chậm. Sáu tháng EC cao trong validation có MAE +5 tăng từ 259,37 (RF) lên 264,89 mS/m khi blend; +35 tăng từ 285,24 lên 342,79. Kỳ 2022–2023 không có tháng EC ≥100 để kiểm tra lại. Sau 2023 không có nhãn EC mới, nên tại thời điểm 2026 tuổi nhãn quá 3 tháng và quy tắc buộc dùng **RF_compact**, không có lợi ích blend cho dự báo hiện tại. File `dry_blend_development_grid.csv`, `dry_blend_predictions.csv`, `dry_blend_metrics.csv` và `dry_blend_protocol.json` lưu phép thử.

**Quyết định:** tiếp tục giữ RF_compact là ứng viên nghiên cứu dùng được với nguồn hiện có, không đổi API/registry theo RF_fine, Huber, KNN hoặc blend. Sai số đỉnh mặn còn hàng trăm mS/m; không được suy ra thời gian truyền mặn từ dự báo một mẫu EC/tháng. Để giảm sai số ngoài giai đoạn đã thấy, cần EC/Cl⁻ đồng thời theo giờ/ngày ở các nhánh, Q phân lưu, triều đo cùng mốc cao độ và mặt cắt/độ sâu; đặc biệt cần nhãn EC mới 2024–2026 để kiểm tra tiền cứu.
