# Pilot 5 điểm: khoảng cách mạng và đối chiếu EC

Mạng làm việc đã được người dùng chốt ngày 2026-10-17: OSM cộng bốn nét KML
trong `ban_do_nhanh_song_v2.kml`. Tọa độ năm điểm là bản đối chiếu của người
dùng, lưu riêng khỏi tọa độ in trong PDF. Mọi khoảng cách tính bằng mét trong
EPSG:32648. `RiverDistance` là đường ngắn nhất trên tim nước đã node hóa,
từ các vị trí snap; `EuclideanDistance` là đường thẳng giữa tọa độ đối chiếu.
Mạng được xem là vô hướng, không mô phỏng chiều dòng chảy, triều hay trạng
thái vận hành cống.

## Tệp kết quả

- `pilot5_pairwise_distances.csv`: 10 cặp điểm, hai loại khoảng cách, tỷ lệ
  đường sông/đường thẳng và SnapDistance của hai đầu.
- `pilot5_lolo_predictions.csv`: 60 dự báo; với mỗi đợt I–IV, lần lượt giữ
  lại một trong năm vị trí và dự báo từ bốn vị trí còn lại.
- `pilot5_lolo_metrics.csv`: MAE/RMSE theo đợt và gộp, đơn vị mS/m.
- `manifest.json`: dấu nguồn, quy tắc và giới hạn diễn giải.

## Kết quả

Đủ 10/10 cặp điểm có đường đi trên mạng đã chốt. Khoảng cách theo sông
dao động từ 7,848 đến 33,137 km; khoảng cách thẳng từ 6,170 đến 19,775 km.
Tỷ lệ River/Euclidean cao nhất là NM29–NM34 (3,612), cho thấy đường đi trên
mạng vòng xa dù hai điểm tương đối gần theo đường thẳng.

| Đợt | Phương pháp | MAE | RMSE | Số dự báo |
| --- | --- | ---: | ---: | ---: |
| I | Nearest | 1.646,800 | 2.028,031 | 5 |
| I | Euclidean-IDW | 1.308,171 | 1.724,703 | 5 |
| I | River-IDW | 1.346,379 | 1.711,636 | 5 |
| II | Nearest | 1.642,800 | 1.865,894 | 5 |
| II | Euclidean-IDW | 1.322,481 | 1.542,778 | 5 |
| II | River-IDW | 1.083,818 | 1.424,448 | 5 |
| III | Nearest | 276,200 | 413,478 | 5 |
| III | Euclidean-IDW | 277,581 | 368,292 | 5 |
| III | River-IDW | 254,689 | 377,857 | 5 |
| IV | Nearest | 126,468 | 183,003 | 5 |
| IV | Euclidean-IDW | 117,659 | 158,999 | 5 |
| IV | River-IDW | 107,978 | 160,253 | 5 |
| Gộp | Nearest | 923,067 | 1.396,328 | 20 |
| Gộp | Euclidean-IDW | 756,473 | 1.174,275 | 20 |
| Gộp | River-IDW | 698,216 | 1.132,167 | 20 |

`Nearest` chọn điểm gần nhất theo EuclideanDistance. Hai IDW dùng lũy thừa
2 cố định, không chỉnh tham số theo tập kiểm tra. EC lấy từ PDF, đã đổi
µS/cm sang mS/m theo hệ số 0,1. Đợt I–IV không có ngày lấy mẫu đủ chắc chắn,
nên đây là kiểm tra theo vị trí trong từng đợt, không phải đánh giá theo thời
gian. Số liệu gộp chịu ảnh hưởng mạnh của đợt I–II có EC cao hơn.

Kết quả là **mốc nội suy nội bộ cho 5 điểm**, chưa phải kiểm định EC tại
cống chưa đo, khoảng dự báo 90%, hay mô hình truyền mặn. Mạng được người dùng
chốt về đường đi trên bản đồ nhưng các giao cắt OSM–KML, cống/đập và chiều
thông nước chưa có kiểm định thủy lực độc lập. OSM tải năm 2026 và KML vẽ năm
2026 cũng không phải snapshot trước năm 2023; muốn khẳng định một phép kiểm
định không dùng thông tin sau 2023 cần thay hoặc kiểm chứng riêng lớp hình học
lịch sử. Chưa thêm Tide/Q/Weather vào phép so sánh này.

## Tái tạo

Chạy `scripts/evaluate_go_cong_pilot5_network.py` bằng Python của QGIS
3.44.14 sau khi tạo mạng ứng viên từ
`scripts/build_go_cong_user_trace_candidate.py`. Mã tính đường ngắn nhất từ
vị trí snap chèn trên cạnh, không làm tròn điểm đo về node đầu cạnh.
