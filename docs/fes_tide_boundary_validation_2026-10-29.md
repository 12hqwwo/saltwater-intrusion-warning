# Chọn điểm FES làm biên triều cửa Tiểu và kiểm tra với Vàm Kênh

Ngày kiểm tra: 29/10/2026. Mục tiêu là chọn **biên triều thiên văn ngoài biển** từ FES2022b đã tải, kiểm tra với mực nước quan trắc Vàm Kênh, rồi thử xem đặc trưng triều có giảm lỗi EC Mỹ Tho khi ghép với Q Kratie/mực nước Tân Châu hay không. FES là mực nước triều mô hình, không phải EC, lưu lượng, triều thực đo đầy đủ hay cao độ đáy.

## 1. Bộ FES và ba ô biển

Theo [CNES/AVISO FES2022](https://www.aviso.altimetry.fr/index.php?id=1279), atlas FES2022b có 34 thành phần triều trên lưới 1/30°; bản `ocean_tide_extrapolated` mở rộng ra bờ. Gói ở `data/raw/tide/fes2022b/ocean_tide_extrapolated/` đã kiểm 34/34 file và mask trong `collection_status.json`. Ba ô lưới đã được chọn trước ở nghiên cứu FES cũ; cả bốn nút lân cận của mỗi ô đều có mask biển gốc, cờ `pyfes=4` khi dự báo giờ 2019–2023. Không nội suy từ một nút đất hay dự báo FES tại tọa độ trạm nằm trong sông.

| Ký hiệu | Kinh độ | Vĩ độ | Khoảng cách xấp xỉ từ cửa Tiểu | Vai trò |
|---|---:|---:|---:|---|
| near | 106,78333 | 10,21667 | 6,3 km | Ô gần nhất đã thử |
| ese | 106,85000 | 10,18333 | 14,1 km | Ô lệch đông nam |
| **south** | **106,78333** | **10,05000** | **24,0 km** | Ứng viên biên triều sau đối chiếu |

Các khoảng cách chỉ là vị trí hình học ngoài biển, không phải đường truyền thủy lực. Trạm Vàm Kênh MRC ở khoảng (106,73714; 10,27430). Toàn bộ thời gian đổi từ UTC sang Asia/Ho_Chi_Minh; FES được tính theo giờ địa phương, còn telemetry MRC 15 phút được gộp trung vị theo giờ khi có ít nhất hai mẫu. Ngày so biên độ cần ít nhất 20 giờ hợp lệ. Dữ liệu MRC giữ cờ `UNVERIFIED`.

## 2. Đối chiếu FES với trạm, không trộn hệ cao độ

Vì chưa có bằng chứng cùng hệ cao độ giữa FES và mốc trạm, chỉ so **biên độ ngày** (cao nhất trừ thấp nhất) và **dao động giờ sau khi bỏ trung bình từng ngày**. Không áp một độ lệch mực nước tuyệt đối. 2019–2021 chọn điểm; 2022–2023 và 2024–2026 kiểm tra độc lập cho mục tiêu mực nước. Script `scripts/validate_fes_vamkenh.py` lưu từng ngày và bảng chỉ số trong `outputs/fes_vamkenh_validation_20261029/`.

| Điểm FES | 2019–2021: r / MAE (cm), 228 ngày | 2022–2023: r / MAE (cm), 702 ngày | 2024–2026: r / MAE (cm), 944 ngày |
|---|---:|---:|---:|
| near | 0,829 / 58,28 | 0,799 / 54,09 | 0,800 / 52,04 |
| ese | 0,908 / 32,68 | 0,886 / 31,40 | 0,886 / 29,93 |
| **south** | **0,947 / 17,43** | **0,931 / 18,38** | **0,929 / 17,35** |

Điểm **south** thắng trên cả ba thời kỳ. Với sóng giờ đã bỏ trung bình ngày, tương quan ở lag 0 giờ là **0,825 trên 5.997 giờ** chọn điểm, **0,971 trên 16.934 giờ** của 2022–2023 và **0,977 trên 22.867 giờ** của 2024–2026; MAE dao động lần lượt 28,49, 15,85 và 14,59 cm. Thử lag 1–6 giờ không giảm MAE so với lag 0. Giai đoạn 2019–2021 chỉ có 113 ngày đủ mẫu ở 2019, 57 ngày ở 2020 và 58 ngày ở 2021; độ phủ hạn chế phải được ghi trong báo cáo.

Nếu cần ước tính **biên độ triều thiên văn tại Vàm Kênh** để dựng biên mô hình, hệ số tỷ lệ không chặn gốc học trên 228 ngày 2019–2021 là `0,9495 × FES_south_range`. MAE biên độ giảm từ 17,43 xuống **15,63 cm** trong kỳ hiệu chỉnh, từ 18,38 xuống **17,13 cm** trên 702 ngày 2022–2023 và từ 17,35 xuống **17,22 cm** trên 944 ngày 2024–2026. Hệ số này **không biến FES thành mực nước tuyệt đối**, không mô tả dâng do gió, áp suất, Q sông hay triều ở các cửa khác. Với mô hình thủy lực cần mặt cắt, độ sâu, hệ cao độ và biên nước ngọt để hiệu chuẩn thêm.

Đã xuất chuỗi biên đã chọn: `south_hourly_boundary_2019_2026.csv` (**70.128 giờ**) và `south_daily_boundary_2019_2026.csv` (**2.922 ngày**) trong `outputs/fes_vamkenh_validation_20261029/`. File giờ chứa dao động triều FES, trung bình ngày và dao động sau khi bỏ trung bình ngày; file ngày chứa biên độ FES và biên độ nhân hệ số 0,9495. Cả hai không có giá trị thiếu. Trường `fes_ocean_tide_cm` không được đọc như cao trình mực nước Vàm Kênh cùng datum.

### Ứng viên cho ba cửa khác

Bảng 5.1 của [luận án Thanh](https://macau.uni-kiel.de/servlets/MCRFileNodeServlet/dissertation_derivate_00004674/Thanh-Thesis_060213.pdf) ghi tọa độ **trạm triều gần cửa**, gồm Bình Đại (Cửa Đại), An Thuận (Hàm Luông) và Bến Trại (Cổ Chiên). Đây là điểm neo để nhận diện **nút cửa biển sơ bộ** trong [GRIT](https://zenodo.org/records/17435232), không phải tọa độ chính xác của tiết diện cửa sông. `scripts/export_fes_multimouth_boundaries.py` chọn tâm ô FES gần nút cửa GRIT nhất mà cả bốn nút FES đều mang mask biển gốc, rồi kiểm tra cờ dự báo `pyfes=4` ở mọi giờ 2019–2026.

| Cửa | Điểm neo trạm (kinh, vĩ độ) | Nút cửa GRIT (ID) | Ô FES ứng viên (kinh, vĩ độ) | Cách nút GRIT |
|---|---|---|---|---:|
| Cửa Đại | 106,711222; 10,197028 | 330069160 | 106,783333; 10,216667 | 5,04 km |
| Hàm Luông | 106,605222; 9,966667 | 330069187 | 106,683333; 9,950000 | 5,27 km |
| Cổ Chiên | 106,529000; 9,880889 | 330069201 | 106,583333; 9,783333 | 2,43 km |

Chuỗi giờ 70.128 dòng và biên độ ngày 2.922 dòng cho cả ba cửa ở `outputs/fes_multimouth_candidates_20261029/`, có manifest và SHA-256. **Chưa có trạm mực nước cùng thời kỳ tại ba cửa để chọn điểm bằng sai số như Vàm Kênh**, do đó chúng chỉ là biên thiên văn ngoài biển ứng viên; không gán hệ số 0,9495 của Vàm Kênh cho chúng. Ô Cửa Đại trùng ô `near` đã thử cho Vàm Kênh; lưới FES và địa hình ven bờ không tách được hai cửa chỉ bằng phép lấy ô gần nhất. Muốn dùng trong mô hình đa nhánh cần định vị tiết diện biên trên mạng thủy lực, đối chiếu từng cửa và xử lý hệ cao độ trước.

## 3. Có cải thiện dự báo EC tháng khi thêm FES đã chọn không?

Đã thử trên đúng RF thủy văn đang nghiên cứu: thời tiết, Q Kratie và mực nước Tân Châu tháng t−2, không dùng EC gần đây. Chỉ thêm một biến FES tại điểm south theo **cửa sổ cố định ngày 9–15 tháng mục tiêu**, biết về mặt thiên văn trước phát hành; biến toàn tháng cũng được thử riêng. Không dùng ngày lấy mẫu EC thực tế vì ngày đó chưa chắc được biết vào lúc phát hành. Hai giả định công bố nhãn EC +5 và +35 ngày vẫn được giữ. Kết quả ở `outputs/ec_fes_validated_20261029/`.

| MAE EC Mỹ Tho (mS/m) | 2019–2021 +5 ngày | 2022–2023 +5 ngày | 2019–2021 +35 ngày | 2022–2023 +35 ngày |
|---|---:|---:|---:|---:|
| RF thủy văn, không FES | **58,68** | 13,52 | **60,72** | 13,19 |
| + FES south ngày 9–15 | 61,31 | **12,51** | 64,45 | **12,05** |
| + FES south cả tháng | 62,44 | 13,92 | 65,16 | 13,42 |

FES đúng hơn về **đại diện biên triều** sau khi so với trạm nhưng **không giảm MAE EC trên giai đoạn chọn**; sáu tháng EC ≥100 mS/m cũng xấu hơn (từ 286,28 lên 294,01 mS/m ở +5 ngày). Không thêm FES vào mô hình EC đang phục vụ hoặc gọi đây là cải thiện dự báo. FES2022b ra đời sau các ngày phát hành 2019–2021, nên thử nghiệm đó là hindcast theo atlas hiện tại, không phải bản dự báo đã tồn tại lúc ấy.

## 4. Hình học và dữ liệu cao độ vừa tìm

Đã tải [TopoDEM v2 của Seeger và Minderhoud (2026)](https://zenodo.org/records/18348609), lưu ZIP và SHA-256 trong `data/external/topodem_20261029/`. README ghi lưới **500 m, EPSG:32648**, quy chiếu cao độ địa phương về mực biển trung bình theo MDT HYBRID-CNES-CLS2022. **Vùng nước bị mask**: đây là địa hình đất, không phải cao độ đáy sông hay mặt cắt thủy lực. Không chuyển mốc trạm Vàm Kênh sang TopoDEM nếu chưa có benchmark/datum transformation tại trạm.

[GRIT Global River Topology](https://zenodo.org/records/17435232) có các đường sông, nút phân lưu và ID kết nối. Đã tải lại bản giản lược toàn cầu **111.044.252 byte**, MD5 `f5f378620eb1e59da7682a991bb51ccc` khớp Zenodo và kiểm ZIP không lỗi. `scripts/extract_grit_delta_network.py` cắt vùng 105–107°E, 9,5–11,5°N thành `outputs/grit_delta_network_20261029/grit_lower_mekong_subset.gpkg`: **585 đoạn, 484 nút**, trong đó 111 nút phân lưu và 16 nút ra biển. Có 9 đầu thượng lưu và 7 đầu hạ lưu nằm ngoài vùng cắt, nên tệp này **không phải graph khép kín**. Bốn nút cửa gần trạm triều trong luận án: Tiểu `330013181` (cách trạm 1,31 km), Đại `330069160` (3,45 km), Hàm Luông `330069187` (3,49 km), Cổ Chiên `330069201` (10,05 km). Các cặp này dựa trên khoảng cách và là **ứng viên topology**, chưa kiểm tra hình học cửa hay tên nhánh bằng đo đạc tại chỗ. GRIT vẫn cần kiểm tra kênh/cống địa phương và không có bathymetry. [Nghiên cứu trắc diện hạ lưu sông Tiền](https://www.apn-gcr.org/wp-content/uploads/2025/04/Copy-of-Appendix-4.1_Ahmed-et-al.-2025_Geomorphology-%E5%9C%A7%E7%B8%AE.pdf) mô tả đợt đo 2020–2021 ở Tiểu, Đại, Hàm Luông, Cổ Chiên, nhưng trang bài báo chưa phải tệp mặt cắt số có thể nạp trực tiếp.

**Kết luận thực dụng:** dùng ô FES south (106,78333°E; 10,05000°N) làm *ứng viên biên triều thiên văn cho cửa Tiểu*, kèm kiểm định Vàm Kênh và hệ số biên độ 0,9495 trong artifact nghiên cứu. Ba cửa Đại, Hàm Luông, Cổ Chiên hiện có chuỗi FES ứng viên ngoài biển nhưng chưa có trạm đối chiếu riêng; không sao chép hệ số Vàm Kênh qua nhánh khác. Độ mặn lan ngược từ biển, nước ngọt đi xuống từ thượng lưu, và mạng kênh có phân nhánh nên chưa thể tạo trường mặn chính xác bằng FES + GRIT + TopoDEM khi vẫn thiếu Q tại phân lưu, mặt cắt, đáy sông và nhãn mặn đồng thời.
