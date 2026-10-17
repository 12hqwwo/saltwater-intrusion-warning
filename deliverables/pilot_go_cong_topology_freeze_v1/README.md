# Pilot Gò Công – Kiểm chứng topology và kết nối trạm

Phiên bản: `freeze-v1`  
Ngày đóng gói: 2026-10-17

## Tuyên bố phạm vi

**Gò Công là khu vực thí điểm để kiểm chứng phương pháp, không đại diện cho toàn bộ vùng nghiên cứu.**

Bộ kết quả này kiểm chứng khả năng xây dựng đồ thị sông/kênh, gắn 5 trạm và tính đường đi theo mạng. Đây là mô hình liên thông hình học, chưa phải mô hình thủy lực hoặc bằng chứng về hướng/thông nước.

## Nguồn và quy tắc dữ liệu

- OSM: truy xuất bằng Overpass ngày 2026-10-16 (OSM base `2026-10-16T11:46:35Z`), bbox `(10.18, 106.42, 10.50, 106.82)`, lọc `waterway` thuộc `river|canal|stream|drain|ditch|tidal_channel`. Sau khi loại phần tử không có LineString hợp lệ, giữ 609 way. Bản quyền © OpenStreetMap contributors, ODbL 1.0.
- KML: `ban_do_nhanh_song_v2.kml`, do người dùng cung cấp ngày 2026-10-17, gồm 4 trace dùng để giảm sai lệch vị trí tại NM29/NM31. KML chỉ được chấp nhận cho phạm vi pilot.
- Giao KML–OSM: 15 giao cắt hình học thô được gom thành 13 nút duy nhất trên OSM way `510175774`. Các nút được noding trong kịch bản A; kịch bản B tách chúng để kiểm tra độ nhạy. Chưa xác minh thông nước tại hiện trường.
- Khoảng cách: tính trên CRS EPSG:32648 bằng Dijkstra với trọng số chiều dài đoạn.

## Kết quả chính

- 21,447 nút và 21,736 cạnh trong graph mở rộng.
- 289 đầu mút bậc 1 cần phân loại thêm; không mặc định xem mọi đầu mút là lỗi.
- 9,549 articulation point và 9,646 bridge trên toàn graph.
- 10/10 cặp trong 5 trạm có đường đi ở kịch bản A.
- NM29–NM34: 24,924.569 m, 175 đoạn cạnh; hệ số đường vòng 3.6121.
- Ba điểm mở rộng NM26/NM28/NM33 đã đóng QA bằng quyết định `EXCLUDED_FROM_FREEZE`; không snap cưỡng bức và không đưa vào Pilot-5.

## Nhật ký QA topology

| Nhóm | Số bản ghi ứng viên/đã xử lý |
|---|---:|
| Sai vị trí | 5 |
| Nhánh cụt | 289 |
| Giao cắt/chạm gần nhưng chưa nối | 9 |
| Tuyến nối nhân tạo | 11 |

Xem chi tiết tại `qa/topology_error_log.csv`. Nhãn `CANDIDATE_REVIEW` và `REVIEW_REQUIRED` thể hiện đối tượng cần đối chiếu thêm, không phải lỗi đã được khẳng định ngoài thực địa.

## Cấu trúc gói

- `data/go_cong_waterways_cleaned.geojson`: snapshot 609 way để demo độc lập.
- `data/pilot5_shortest_routes.geojson`: 10 đường ngắn nhất giữa 5 trạm.
- `data/pilot5_stations.geojson`: tọa độ 5 trạm được dùng trong freeze.
- `qa/topology_error_log.csv`: error log bốn nhóm.
- `qa/coordinate_candidates_resolution.csv`: quyết định đóng ba điểm QA.
- `metrics/station_distance_matrix_km.csv`: ma trận khoảng cách sông.
- `metrics/route_metrics.csv`: số đoạn cạnh và chỉ số từng tuyến.
- `metrics/pilot_route_articulation_points.csv` và `pilot_route_bridges.csv`: ứng viên điểm nghẽn trên các tuyến Pilot.
- `pilot_go_cong_qa_metrics.xlsx`: workbook tổng hợp để đưa vào báo cáo.
- `figures/pilot_go_cong_topology_map_300dpi.png`: ảnh bản đồ 300 dpi.
- `metadata.json` và `manifest_sha256.csv`: nguồn, quy tắc và checksum.

## Hạn chế và hướng phát triển

1. OSM có thể thiếu nhánh hoặc chứa lỗi topology; 289 đầu mút bậc 1 phải được phân loại bằng ảnh/hiện trường.
2. Graph chưa có hướng dòng chảy, cao độ, mặt cắt, lưu lượng hoặc vận tốc.
3. Chưa mô hình hóa trạng thái đóng/mở của hệ thống cống ngăn mặn.
4. Chưa ghép nhịp thủy triều và chuỗi thời gian EC vào mô phỏng lan truyền động.
5. Các connector dưới 5 m và connector KML là giả định topology, không được diễn giải như thủy đạo đã khảo sát.
6. Bước tiếp theo là xác minh các bottleneck ưu tiên, bổ sung hướng/cống/thủy triều, rồi mới mở rộng địa bàn. PostGIS chỉ cần thiết khi dữ liệu tăng theo vùng/thời gian hoặc cần truy vấn đa người dùng; freeze này tiếp tục dùng GeoJSON.

## Tái tạo

Chạy từ thư mục gốc dự án:

```powershell
python -m pip install -r requirements-gis.txt
python scripts/freeze_go_cong_pilot.py
```
