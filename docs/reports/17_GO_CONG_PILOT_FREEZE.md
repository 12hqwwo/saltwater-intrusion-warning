# Pilot Gò Công – Kiểm chứng topology và kết nối trạm

Trạng thái: **đã đóng gói freeze-v1 ngày 17/10/2026**.

> Gò Công là khu vực thí điểm để kiểm chứng phương pháp, không đại diện cho toàn bộ vùng nghiên cứu.

## Kết quả đã chốt

- Giữ kiến trúc chạy bằng GeoJSON/CSV để demo độc lập; chưa cần PostgreSQL/PostGIS ở mốc này.
- Chốt graph mở rộng gồm 21.447 nút, 21.736 cạnh và 47 thành phần liên thông.
- Tính đủ 10/10 đường đi giữa 5 trạm bằng Dijkstra. Tuyến NM29–NM34 dài 24,924569 km và đi qua 175 đoạn cạnh.
- Ba điểm NM26, NM28 và NM33 đã đóng QA bằng quyết định `EXCLUDED_FROM_FREEZE`. Không hiệu chỉnh hoặc snap cưỡng bức khi chưa có bằng chứng độc lập.
- Lập error log bốn nhóm: 5 sai lệch vị trí, 289 đầu mút bậc 1, 9 khe nối dưới 5 m và 11 connector cần diễn giải có điều kiện.
- Phân tích articulation point/bridge đã được xuất riêng dưới dạng ứng viên điểm nghẽn topology; chưa coi là công trình hoặc điểm nghẽn thủy lực đã xác minh.
- Backend đã tách lớp truy cập tệp vào `pilot_spatial_repository.py`; WebGIS dùng `pilot_spatial_data_service.js` thay vì biết đường dẫn dữ liệu.

## Nguồn dữ liệu

- OpenStreetMap/Overpass snapshot ngày 16/10/2026, bbox `(10.18, 106.42, 10.50, 106.82)`, lọc `waterway=river|canal|stream|drain|ditch|tidal_channel`, giữ 609 way hợp lệ. Dữ liệu theo ODbL 1.0, © OpenStreetMap contributors.
- KML `ban_do_nhanh_song_v2.kml` do người dùng cung cấp ngày 17/10/2026, gồm 4 trace dùng trong phạm vi pilot.
- 15 giao cắt hình học thô giữa KML và OSM được gom thành 13 nút duy nhất để phân tích độ nhạy topology.

## Bộ giao nộp

Bộ đầy đủ nằm tại [`deliverables/pilot_go_cong_topology_freeze_v1`](../../deliverables/pilot_go_cong_topology_freeze_v1/README.md), gồm GeoJSON, CSV, Excel, ảnh 300 dpi, metadata và checksum SHA-256.

## Giới hạn bắt buộc khi diễn giải

Graph hiện chỉ biểu diễn liên thông hình học. Chưa có hướng dòng chảy, cao độ, mặt cắt, trạng thái cống ngăn mặn hoặc nhịp thủy triều. Các connector tự động/KML không phải bằng chứng thông nước. Vì vậy kết quả phù hợp để kiểm chứng phương pháp và ưu tiên vị trí cần khảo sát, chưa phù hợp cho quyết định vận hành thủy lợi.
