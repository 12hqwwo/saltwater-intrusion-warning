# Mạng tim sông–kênh Gò Công và QA snap 5 điểm

Đây là mạng làm việc cho pilot EC, tạo từ dữ liệu OpenStreetMap tải lúc
`2026-10-16T11:48:33Z` trong khung WGS84 `10.18–10.50°N,
106.42–106.82°E`. Nguồn: © OpenStreetMap contributors, ODbL 1.0,
<https://www.openstreetmap.org/copyright>. Đây không phải mạng thủy văn đo
đạc tại hiện trường. Snapshot năm 2026 chỉ là lớp hình học hỗ trợ; nếu đề tài
yêu cầu đóng băng mọi đầu vào tại 2023 thì cần thay bằng snapshot lịch sử.

## Sản phẩm

- `go_cong_waterway_network_32648.gpkg`: dữ liệu trong CRS mét
  WGS 84 / UTM zone 48N (`EPSG:32648`).
- `go_cong_waterway_network_qa.qgs`: dự án QGIS đã cấu hình lớp và ký hiệu.
- `pilot5_snap_qa_updated.csv`: khoảng cách, tuyến OSM gần nhất, cầu OSM gần nhất,
  tọa độ PDF, tọa độ đối chiếu, độ lệch giữa hai tọa độ, thành phần mạng và
  kết luận QA của từng điểm.
- `pilot5_coordinate_review.csv`: tên làm việc, tọa độ đối chiếu và bằng chứng
  ảnh do người dùng gửi ngày 2026-10-17, tách khỏi số liệu PDF gốc.
- `data/raw/gis/user_review_20261017/`: ảnh bản đồ người dùng gửi để
  đối chiếu vị trí cầu/cống và bối cảnh các nhánh sông quanh NM29, NM31.
- `network_topology_summary.json`: thống kê topology và nguồn.
- `go_cong_user_trace_candidate_32648.gpkg` và
  `go_cong_user_trace_candidate_qa.qgs`: mạng ứng viên bổ sung từ KML do người
  dùng vẽ; dự án QGIS này hiển thị cả mạng OSM nền và nét vẽ mới.
- `pilot5_user_trace_snap_qa.csv` và `user_trace_topology_qa.json`: QA khoảng
  snap và các chỗ nối/giao của KML.
- `pilot5_baselines/`: khoảng cách 10 cặp điểm, 60 dự báo leave-one-location-out
  và MAE/RMSE cho Nearest, Euclidean-IDW, River-IDW sau khi người dùng chốt
  mạng làm việc; xem `pilot5_baselines/README.md` để biết giới hạn diễn giải.

Các lớp trong GeoPackage:

- `waterways_osm_raw`: 609 tuyến OSM gốc, giữ `osm_id`, loại đường thủy,
  tên và thời điểm snapshot.
- `network_edges_noded`: 21.011 cạnh; mọi giao điểm hình học đã thành node.
- `topology_gap_candidates`: 9 đầu tuyến nguồn cách một tuyến khác dưới 5 m.
- `topology_connectors_lt5m`: 9 đoạn nối tự động dưới 5 m, đang chờ xem lại
  trên ảnh hoặc bản đồ thủy lợi; từng đoạn giữ ID của hai tuyến và chiều dài.
- `osm_bridges_context`: cầu OSM từ truy vấn ban đầu quanh tọa độ PDF;
  không bao phủ đầy đủ mọi tọa độ đối chiếu mới.
- `pilot5_original`: năm tọa độ PDF, giữ nguyên để đối chiếu.
- `pilot5_reviewed_coordinates`: năm tọa độ đối chiếu; thuộc tính `pdf_name`
  giữ tên in trong PDF, còn `site_name` là tên làm việc.
- `pilot5_snap_candidates`: năm vị trí gần nhất trên mạng để QA. Ứng viên
  quá xa vẫn được giữ để thấy chỗ thiếu tim kênh, không dùng trong mô hình.
- `pilot5_snapped_accepted`: chỉ chứa điểm thỏa đồng thời ngưỡng khoảng cách
  và bằng chứng đúng tuyến. Hiện lớp này có 3 đối tượng: NM30, NM32, NM34.

## Kết quả topology

Sau khi node hóa và thêm chín đoạn nối tự động dưới 5 m, mạng có 20.896 node,
21.011 cạnh và 48 thành phần liên thông. Lớp cạnh cuối không có cạnh trùng
hoặc cạnh dài bằng 0. Các thành phần rời còn lại được giữ nguyên vì có thể
là kênh độc lập thật hoặc liên kết chưa được OSM lập bản đồ; không tự nối
qua khoảng cách lớn. Năm vị trí snap ứng viên đều nằm trên thành phần 1,
thành phần chính dài khoảng 1.368,2 km. Chín đoạn nối nhỏ vẫn chỉ là giả định
hình học, chưa được kiểm chứng là có dòng chảy thông nhau.

## Kết quả snap

Ngưỡng nhận tự động là 100 m. Mật độ kênh ở đồng bằng cao nên tăng ngưỡng
có thể bắt nhầm tuyến. Vị trí ứng viên vẫn được lưu để kiểm tra trực quan,
nhưng không được dùng làm đầu vào RiverDistance khi trạng thái chưa phải
`ACCEPTED`.

| Điểm | Tọa độ dùng để QA | SnapDistance (m) | Bằng chứng gần điểm | Kết luận |
| --- | --- | ---: | --- | --- |
| NM29 – Cầu Kinh Nhiễm | 10,26788889 N; 106,63872222 E | 400,06 | Ảnh cho thấy đường nước nhỏ gần cầu và các nhánh Mê Kông xung quanh; kênh OSM gần nhất cách quá xa | Chưa nhận; cần số hóa và kiểm tra kết nối đường nước |
| NM30 – Cầu Long Chánh | 10,36122222 N; 106,67133333 E | 9,85 | Ảnh cầu qua sông; tim OSM `Rạch Gò Công` ở gần | Nhận theo đối chiếu ảnh và khoảng cách |
| NM31 – Cầu Tân Hòa | Trùng PDF | 200,05 | Ảnh xác nhận cầu qua nhánh sông; OSM có cầu cùng tên cách 13,51 m | Chưa nhận; thiếu tim nhánh sông sát cầu |
| NM32 – Cống Cần Lộc | 10,403545 N; 106,756315 E | 1,28 | Ảnh cho thấy cống cạnh mặt nước; tuyến OSM `stream` không tên ở gần | Nhận theo đối chiếu ảnh và khoảng cách |
| NM34 – Cầu Lý Quàn | 10,245803 N; 106,697629 E | 1,51 | Ảnh cầu qua kênh; cầu OSM cùng tên cách 7,93 m | Nhận theo đối chiếu ảnh và OSM |

Quy tắc nhận điểm dùng ngưỡng chung 100 m và một trong ba bằng chứng đúng
tuyến: tên kênh OSM khớp, tên cầu OSM khớp trong 100 m, hoặc ảnh người dùng
cho thấy cầu/cống qua nước cùng với tim OSM cách không quá 25 m. Quy tắc ảnh
chỉ áp dụng cho điểm có ảnh lưu trong `user_review_20261017`. SnapDistance
đo tới hình học OSM, không phải sai số tọa độ đo đạc. Ba điểm đã nhận có thể
dùng cho bước thử RiverDistance; mạng vẫn cần QA các đoạn nối tự động trước
khi coi khoảng cách theo sông là đáng tin cậy.

Ảnh rộng mới cho thấy NM29 nằm trong vùng nhiều kênh nhỏ giữa các nhánh Mê
Kông; NM31 ở gần một nhánh sông lớn và ảnh cận cảnh xác nhận nước ngay dưới
cầu. Đây là bối cảnh để ưu tiên hai điểm khi bổ sung mạng. Ảnh chưa cho biết
đường nước liên thông qua những đoạn nào, có cống/đập chặn hay không, hoặc
hướng dòng theo triều. Ở giai đoạn mạng OSM nền, chưa gán RiverDistance
cho NM29/NM31; kết quả sau khi bổ sung KML nằm trong `pilot5_baselines/`.

Nguồn tọa độ đối chiếu là thông tin và ảnh người dùng cung cấp ngày
2026-10-17, bổ sung bảng `doi_chieu_toa_do_pilot5.xlsx` trước đó (sheet
`Đối chiếu tọa độ`). Đối chiếu trên bản đồ không phải phép đo GPS hiện
trường. Vị trí PDF và tọa độ mới được giữ trong hai trường riêng; không sửa
lại số gốc.

## KML nhánh sông do người dùng vẽ

Tệp hiện hành `data/raw/gis/user_review_20261017/ban_do_nhanh_song_v2.kml`
là bản người dùng xem và đồng ý trên Google Earth ngày 2026-10-17. Bản KML
trước vẫn được giữ ở cùng thư mục. Ba nét đầu của bản mới giống hệt bản cũ;
bản mới thêm nét thứ tư dài 2,741 km ở phía tây tuyến Cầu Tân Hòa. Bốn
LineString gồm một nét 1,842 km qua NM29 và ba nét dài 3,728 km, 23,454 km,
2,741 km qua khu vực NM31. Tổng chiều dài là 31,765 km. Giữa ba nét Tân Hòa
có hai khe 0,74 m và 1,57 m; cả hai được giữ thành đoạn nối riêng để
thấy rõ giả định kết nối mà người dùng đã chốt cho pilot. Mạng OSM + KML có
21.736 cạnh và 47 thành phần liên
thông, so với 21.011 cạnh và 48 thành phần ở mạng OSM nền.

| Điểm | Snap tới OSM nền | Snap tới mạng có KML | Trạng thái trên KML |
| --- | ---: | ---: | --- |
| NM29 – Cầu Kinh Nhiễm | 400,06 m | 1,40 m | Người dùng chốt để thử pilot |
| NM31 – Cầu Tân Hòa | 200,05 m | 16,55 m | Người dùng chốt để thử pilot |

Đường NM29 giao một tuyến kênh OSM và đầu gần Sông Cửa Trung cách tim sông
OSM 128,62 m. Ba đường Tân Hòa giao các tuyến OSM tại 14 lượt giao hình
học; đầu gần Sông Cửa Tiểu cách tim sông OSM 172,75 m. Đầu tây mới cách
kênh OSM gần nhất 10,42 m. Giao hình học không tự chứng minh nước thông
qua chỗ đó; trạng thái cống/đập và dòng theo triều chưa có kiểm định thủy
lực độc lập. Người dùng đã chốt mạng này làm giả thuyết kết nối cho pilot,
nên NM29/NM31 nằm trong lớp `pilot5_user_trace_snap_approved` và được dùng
để tính RiverDistance thử nghiệm. Đây chưa phải khoảng cách truyền EC đã
được kiểm định bằng số đo độc lập. Ba điểm NM30, NM32, NM34 giữ nguyên kết
quả snap trước.

## Tái tạo

Chạy `scripts/download_go_cong_osm_waterways.py` để tải snapshot và ngữ cảnh
cầu, sau đó chạy `scripts/build_go_cong_waterway_network.py` bằng
`python-qgis-ltr.bat` của QGIS 3.44.14. Trước khi gọi QGIS Python trên máy
này, đặt `TEMP` và `TMP` vào thư mục có quyền ghi trong workspace.
Chạy tiếp `scripts/build_go_cong_user_trace_candidate.py` để tạo dự án và
GeoPackage ứng viên từ KML đã lưu trong `data/raw/gis/user_review_20261017`.
