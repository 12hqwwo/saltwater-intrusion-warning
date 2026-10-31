# Kiểm toán GRIT, cống Đồng Tháp mới và pha triều quan trắc

Ngày 29/10/2026. Mục tiêu là xác định **kết nối hình học và mực nước triều có bằng chứng**, không suy diễn nồng độ mặn hay giờ đóng/mở cống. Script: `scripts/audit_grit_gate_connectivity.py` và `scripts/audit_grit_gate_tide_phase.py`. Các bảng và GeoJSON ở `outputs/grit_gate_audit_20261029/`.

## 1. Tuyến GRIT có hướng và trạm MRC

Nguồn là [GRIT simplified global river topology](https://zenodo.org/records/17435232) đã kiểm MD5 và trích vùng 105–107°E, 9,5–11,5°N. Tệp sau sửa có **585 đoạn và 484 nút duy nhất**. Audit dùng `upstream_node_id → downstream_node_id` và `length_adjusted` của GRIT để kiểm tra đường có hướng; không dùng khoảng cách đường chim bay làm tuyến nước. Đầu của trạm là **nút hạ lưu của đoạn GRIT gần trạm nhất**; chiều dài dưới đây bỏ qua phần đoạn từ trạm đến nút, nên chỉ là chỉ số topology xấp xỉ.

| Trạm MRC | Cách đoạn GRIT gần nhất | Tuyến tới Cửa Tiểu | Tuyến tới Cửa Đại | Hàm Luông / Cổ Chiên |
|---|---:|---:|---:|---|
| Tân Châu | 0,41 km | 196,69 km | 195,59 km | Có trong GRIT |
| Vàm Nao | 0,19 km | 164,49 km | 163,39 km | Có trong GRIT |
| Mỹ Thuận | 0,59 km | 88,94 km | 87,84 km | Có trong GRIT |
| Mỹ Tho | **1,51 km** | 43,17 km | 42,07 km | Không có tuyến GRIT cùng hướng từ đoạn gắn |
| Vàm Kênh | 0,61 km | 0 km | Không | Không |

Các tuyến là **reachability của mạng tham khảo**, không phải chiều dài thủy lực khảo sát, vận tốc, thời gian truyền mặn hoặc bằng chứng trạm nằm đúng nhánh. GRIT thiếu kênh/cống và mặt cắt, có 9/7 đầu tuyến ra khỏi vùng cắt; trong vùng triều, lưu lượng có thể đảo chiều dù ID GRIT được định hướng xuống biển. Trạm Mỹ Tho cách đoạn gần nhất 1,51 km là dấu hiệu cần kiểm tra thủ công hình học/điểm gắn trước khi dùng mô hình 1D. Bảng đầy đủ ở `station_routes.csv`.

## 2. Cống trong tỉnh Đồng Tháp mới

Danh mục ứng dụng `data/8file/03_sluice_gates_190_and_27_verified_gis.csv` có 27 cống được gắn cờ `is_verified_27_headworks=True`. Đối chiếu tọa độ với hai đa giác lưu trong dự án: **27/27 nằm trong Tiền Giang cũ và 27/27 nằm trong ranh Đồng Tháp mới**. Bốn hồ sơ cống lấy từ danh mục Đồng Tháp cũ trong `data/metadata/gate_catalog_reviewed.json` vẫn **không có tọa độ**, nên không gắn chúng vào mạng.

Khoảng cách của 27 cống đến **đoạn GRIT gần nhất**: nhỏ nhất 0,221 km, trung vị **0,852 km**, lớn nhất **8,319 km**; **8/27** trong 0,5 km và **10/27** xa hơn 2 km. Ví dụ `GATE_TG_071` cách 8,319 km, `GATE_TG_095` 4,496 km. Đây không chứng minh cống cách nước xa: GRIT giản lược có thể bỏ kênh cấp nhỏ. Ngay cả cống sát đoạn GRIT cũng **chưa có liên kết thủy lực xác minh** giữa phía trong/phía ngoài cống và đoạn sông đó. `gate_nearest_grit.csv` và `gate_proximity.geojson` đều gắn trạng thái `NEAREST_LINE_ONLY`, không cấp tọa độ hay nồng độ giả cho cống.

## 3. Quan trắc pha sóng triều Vàm Kênh → Mỹ Thuận

Hai chuỗi mực nước telemetry MRC (2019–2026, cờ nguồn `UNVERIFIED`) được giữ giá trị gốc, đổi UTC sang `Asia/Ho_Chi_Minh`, gộp theo khoảng 15 phút. Chỉ ngày **mỗi trạm có ít nhất 80/96 khoảng** được dùng: 2019 **112**, 2020 **56**, 2021 **58**, 2022 **342**, 2023 **358**, 2024 **354**, 2025 **358**, 2026 đến kỳ tải **231** ngày. Bỏ trung bình từng ngày của từng trạm để tránh so mực nước tuyệt đối khác datum; sau đó trượt sóng Vàm Kênh 0–8 giờ theo bước 15 phút và so tương quan với Mỹ Thuận. Lag dương nghĩa dao động ở Mỹ Thuận tới sau Vàm Kênh.

| Giai đoạn | Lag chọn từ 2019–2021: 135 phút | Tương quan ở lag 0 | Lag có tương quan lớn nhất riêng kỳ |
|---|---:|---:|---:|
| 2019–2021, 21.480 cặp ở lag chọn | **r=0,860** | 0,506 | 135 phút |
| 2022–2023, 67.094 cặp ở lag chọn | **r=0,958** | 0,456 | 165 phút, r=0,972 |
| 2024–2026, 90.288 cặp ở lag chọn | **r=0,947** | 0,426 | 165 phút, r=0,971 |

Vậy có bằng chứng hồi cứu rằng **sóng mực nước triều** tại Mỹ Thuận thường trễ Vàm Kênh khoảng **2–3 giờ**. Kỳ 2021 riêng lẻ cho lag tối ưu khác (30 phút) và giai đoạn chọn có ít ngày đủ mẫu; không áp một hằng số lag duy nhất để tính mặn. Dao động triều không di chuyển như khối nước hay muối; pha mực nước không phải vận tốc nước, Q, hay thời gian truyền xâm nhập mặn. Mưa, Q sông, gió/nước dâng và điều kiện biên còn ảnh hưởng tín hiệu. Bảng mọi lag và từng năm ở `tide_wave_lag_metrics.csv`; độ phủ ở `tide_stage_day_coverage.csv`.

## 4. Cần gì trước mô hình lan truyền đủ tin cậy

1. EC25/Cl⁻/độ mặn cùng thời điểm theo giờ/ngày ở các nhánh và hai phía cống; đơn vị, độ sâu mẫu, QA, lịch công bố. Không quy đổi mS/m → g/L theo một hệ số chung khi chưa hiệu chuẩn.
2. Q hai chiều tại Tân Châu–Vàm Nao–Mỹ Thuận và các cửa, kèm quy ước dấu, mực nước và hệ cao độ chung. `length_adjusted` của GRIT không cho vận tốc.
3. Bathymetry/mặt cắt, kết nối kênh–cống tại địa phương, trạng thái mở cống theo thời gian, biên mực nước và mặn từng cửa. FES là triều thiên văn ngoài biển, không đủ tổng mực nước hoặc biên nồng độ.

Chỉ khi các dữ liệu đó chồng thời gian mới hiệu chỉnh được mô hình thủy lực–vận chuyển chất và kiểm tra tại trạm/cống độc lập. Hiện có thể dùng GRIT và lag mực nước để **thiết kế mạng/thí nghiệm**, không xuất bản trường mặn hay khuyến nghị vận hành.
