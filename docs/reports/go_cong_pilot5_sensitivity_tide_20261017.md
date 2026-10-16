# Gò Công: kiểm tra độ nhạy pilot, mở rộng điểm và triều FES

Ngày thực hiện: 2026-10-17. Baseline v1 trong
`data/processed/gis/go_cong_network/pilot5_baselines/` được giữ nguyên.
Các phân tích bổ sung nằm ở các thư mục riêng.

## 0. Kết quả quyết định: giả định giao KML–OSM `510175774`

KML trace 1 và OSM way `510175774` cắt nhau **13 lần** trong cùng một
cụm hình học. Tách riêng một node trên tuyến NM29–NM34 làm quãng đường
chỉ tăng 0,412 m vì graph đi qua node lân cận. Vì vậy kịch bản B chính
thức tách **cả 13 node giao của đúng cặp nét này** thành phía KML và
phía OSM; các cạnh trùng hình học được biểu diễn ở hai phía, không cho
chuyển giữa hai phía tại 13 node. Các đoạn khác giữ nguyên. Đây là phép
thử giả định topology, chưa phải bằng chứng có hay không thông nước.

| Chỉ tiêu | A: giữ giao | B: tách giao |
| --- | ---: | ---: |
| NM29–NM34 RiverDistance | 24.924,569 m | Không có đường mạng |
| Cặp điểm có đường mạng | 10/10 | 6/10 |
| Dự báo River LOLO | 20/20 | 16/20 |
| River-Nearest MAE/RMSE, toàn bộ dự báo có thể tính | 752,738 / 1.078,031 | 736,010 / 1.148,191 |
| River-IDW MAE/RMSE, toàn bộ dự báo có thể tính | 698,216 / 1.132,167 | 753,405 / 1.261,005 |

Hai hàng sai số cuối có mẫu khác nhau nên **không dùng làm so sánh trực tiếp**.
Trên cùng 16 trường hợp NM30/NM31/NM32/NM34:

| Phương pháp | A MAE/RMSE | B MAE/RMSE |
| --- | ---: | ---: |
| River-Nearest | 811,435 / 1.169,385 | 736,010 / 1.148,191 |
| River-IDW, p=2 | 750,526 / 1.232,866 | 753,405 / 1.261,005 |

Đơn vị sai số: mS/m. Trong B, NM29 không có donor kết nối trong cả bốn
đợt; không có giá trị River-IDW/River-Nearest cho NM29 và không dùng
đường thẳng thay thế. Kết quả River-IDW tăng nhẹ trên cùng mẫu nhưng mất
20% độ phủ; điều này quan trọng hơn chênh lệch MAE nhỏ. Hồ sơ tái lập:
`pilot5_topology_scenarios/scenario_pairwise_delta.csv`,
`scenario_lolo_predictions.csv`, `scenario_metrics.csv`,
`scenario_site_metrics.csv`, `crossing_cluster.geojson` và `manifest.json`.

Ở baseline A, River-IDW theo từng điểm có MAE: NM29 488,978;
NM30 838,972; NM31 133,314; NM32 1.460,549; NM34 569,268 mS/m.
Thành công **không chỉ tập trung ở NM29/NM30/NM34**: NM31 rất tốt, còn
NM32 là nguồn sai số lớn nhất. Năm vị trí và bốn đợt vẫn là pilot nhỏ.

## 1. Sai số theo điểm và tham số IDW

`pilot5_sensitivity/pilot5_station_campaign_errors.csv` có 20 dòng, một
dòng cho mỗi cặp điểm–đợt I–IV, gồm EC thực đo, dự báo và sai số tuyệt đối
của Nearest, River-Nearest, Euclidean-IDW và River-IDW. Bảng trung bình theo
điểm: `pilot5_sensitivity/pilot5_station_summary.csv`.

| Phương pháp | MAE gộp | RMSE gộp |
| --- | ---: | ---: |
| Nearest theo đường thẳng | 923,067 | 1.396,328 |
| River-Nearest | 752,738 | 1.078,031 |
| Euclidean-IDW, p=2 | 756,473 | 1.174,275 |
| River-IDW, p=2 | 698,216 | 1.132,167 |

Đơn vị: mS/m. River-IDW có MAE gộp thấp nhất, River-Nearest có RMSE gộp
thấp nhất. River-IDW giảm MAE so với Euclidean-IDW ở NM29, NM30, NM31 và
NM34; tại NM32 cao hơn khoảng 0,24 mS/m (trung bình qua bốn đợt).

`pilot5_sensitivity/pilot5_p_sensitivity.csv` thử p=1; 1,5; 2; 2,5; 3
cho hai loại khoảng cách. Trên đúng 20 trường hợp LOLO cũ, River-IDW p=2
có MAE/RMSE thấp nhất trong lưới này. Đây là **độ nhạy thăm dò**, không
phải chọn tham số ngoài mẫu. Nếu muốn chọn p làm mô hình chính thức, cần
chọn bằng tập/kiểm định bên trong, rồi đánh giá trên điểm hoặc thời đoạn
độc lập.

## 2. Audit đường đi

`pilot5_route_audit/go_cong_pilot5_route_audit.qgs` hiển thị mười đường
ngắn nhất và tô đỏ đường NM29–NM34. GeoJSON và CSV cùng thư mục giữ hình
học tuyến, độ dài, tỷ lệ đường vòng và 15 lượt giao giữa KML với tuyến OSM.

NM29–NM34 dài 24,925 km theo mạng, so với 6,900 km đường thẳng (tỷ lệ
3,612). Tuyến dùng khoảng 752 m nét KML; một giao KML–OSM tại kênh OSM
`510175774` nằm ngay trên đường đi. Đây là nút cần xem kỹ vì thay đổi
kết nối có thể thay đổi RiverDistance. Danh mục cống hiện có đặt Cống Bà
Tài cách hình học đường đi khoảng 25,59 m, nhưng tọa độ cống là loại
`derived_endpoint`; gần tuyến **không chứng minh** dòng nước đi qua cống
đang mở. Việc node hóa các giao KML–OSM là giả định graph người dùng chốt
cho pilot, chưa được kiểm định thủy lực độc lập.

## 3. Mở rộng 8 điểm Gò Công

`pilot8_expansion_screen/pilot8_expansion_coordinate_screen.csv` sàng lọc
ba điểm còn lại bằng tọa độ PDF, không sửa số gốc và không đưa chúng vào
validation:

| Điểm | Khoảng tới mạng gần nhất | Quyết định |
| --- | ---: | --- |
| NM26 | 16.260,53 m | Giữ chờ xác minh kinh độ in lệch cụm Gò Công |
| NM28 | 159,37 m | Giữ chờ xác minh vị trí Cầu Vĩnh Bình |
| NM33 | 393,23 m | Giữ chờ xác minh Cống Vàm Tháp |

Khoảng gần mạng không xác nhận đúng kênh. Cả ba còn có cờ QA tọa độ từ
PDF. Không tăng số vị trí kiểm định bằng cách snap cưỡng bức.

`pilot8_expansion_screen/pilot8_coordinate_review_v2.csv` giữ riêng tọa
độ PDF và giả thuyết hiệu chỉnh. NM28 có giả thuyết **đảo dòng NM27/NM28**
theo vị trí trên Phụ lục 1: 10,345250 N, 106,579139 E; cách graph
169,36 m, so với tọa độ in 159,37 m. Cả hai vẫn ngoài ngưỡng 100 m và
chưa có chứng cứ vị trí cầu/kênh, nên không chọn giả thuyết chỉ vì gần
mạng. NM33 giữ tọa độ PDF, cách graph 393,23 m; chưa biết vị trí lấy mẫu
và phía cống. NM26 giữ nguyên kinh độ PDF 106°04′7,7″; không tạo sửa
kinh độ dự đoán. Cả ba có `pilot_admission=HOLD`, vì vậy **chưa có Pilot
Spatial v2 7–8 điểm hợp lệ** và không chạy LOLO v2 bằng tọa độ suy diễn.

## 4. Dự báo EC tháng riêng khỏi Spatial Pilot

Nhánh cũ `pipelines/models/14_model_baseline.py` đã so sánh Seasonal Naive,
SARIMA và Random Forest theo thời gian, nhưng RF có dùng mưa/nhiệt độ/gió
và DAHITI của **chính tháng mục tiêu**. Chúng chỉ sẵn có sau khi tháng đó
diễn ra, nên các điểm số RF cũ không đại diện cho dự báo phát hành từ cuối
tháng trước.

`pipelines/models/evaluate_monthly_ec_known_at_issue.py` giữ test
2022-01–2023-12, dùng RF chỉ với các EC trễ 1/2/3/12 tháng và tháng trong
năm. Giai đoạn đến 2018 dùng để huấn luyện ban đầu, 2019–2021 được gộp
vào lịch sử trước test; không dùng EC sau 2021 để fit mô hình RF/SARIMA
ban đầu. SARIMA cập nhật bằng EC quan trắc sau mỗi lượt dự báo. Cả ba phương
pháp được so trên cùng các tháng có mục tiêu hợp lệ:

| Trạm | Phương pháp | n | MAE | RMSE |
| --- | --- | ---: | ---: | ---: |
| Tân Châu | Seasonal Naive | 23 | 2,3117 | 3,1515 |
| Tân Châu | SARIMA | 23 | 1,8111 | 2,1748 |
| Tân Châu | RF chỉ EC trễ | 23 | 1,6062 | 2,0961 |
| Mỹ Tho | Seasonal Naive | 17 | 4,2759 | 5,6285 |
| Mỹ Tho | SARIMA | 17 | 3,2989 | 4,3584 |
| Mỹ Tho | RF chỉ EC trễ | 17 | 3,2484 | 4,5253 |

Đơn vị: mS/m. RF Tân Châu thấp nhất ở hai chỉ số; tại Mỹ Tho RF có MAE
thấp hơn SARIMA nhưng RMSE cao hơn. Giao thức này giả định EC quan trắc
tháng trước đã có khi dự báo tháng kế tiếp. Kết quả riêng ở
`data/models/temporal_ec_known_at_issue_2022_2023/`.

### Audit thời điểm EC thực sự có thể dùng

Đã đối chiếu README xuất MRC, metadata chuỗi và manifest tải dữ liệu.
README của hai trạm ghi **thời điểm tạo bản xuất 2026-09-01**; manifest
ghi thời điểm tải snapshot 2026-10-10. Metadata có thời gian quan trắc,
UTC offset và khoảng chuỗi đến 2023, nhưng **không có thời điểm công bố
từng quan trắc hoặc độ trễ cập nhật**. Do đó không thể chứng minh EC
tháng trước đã sẵn có vào ngày cuối tháng đó. Backtest nêu trên là
*one-step research backtest có điều kiện*, chưa phải kiểm định dự báo
vận hành theo đúng issue time. Muốn nâng cấp cần log bản phát hành lịch
sử hoặc xác nhận độ trễ cung cấp EC từ MRC; nếu trễ một tháng phải dùng
EC lag 2 làm thông tin gần nhất và chạy lại.

## 5. Ba điểm triều và PyFES

Ba tọa độ hiện hành từ `04_tide_points_candidates_UPDATED_20261010.csv`
(WGS84, vĩ độ rồi kinh độ):

| Mã | Vĩ độ | Kinh độ |
| --- | ---: | ---: |
| TIDE_CUA_TIEU | 10,300000 | 106,866667 |
| TIDE_MIDDLE | 10,200000 | 106,900000 |
| TIDE_CUA_DAI | 10,166667 | 106,933333 |

Đã cài PyFES 2026.5.2 vào `.venv-api` và tính hourly 1985–2023, sau đó
tổng hợp theo tháng giờ Việt Nam thành 1.404 dòng tại
`data/processed/tide/fes4_screening/fes4_screening_monthly_1985_2023.csv`.
Các ô lưới qua kiểm tra mask native, bốn thành phần và sàng lọc GEBCO;
trạng thái tọa độ vẫn là `REVIEW` do chưa xác minh độc lập đường bờ,
datum và tính đại diện cửa sông.

Nguồn triều độc lập hiện chỉ có chuỗi **cực đại theo ngày ở Vũng Tàu**
trong workspace. Nó khác vị trí ba điểm cửa sông và không có mực triều
theo giờ để so pha/biên độ; chưa đủ kiểm định FES tại Cửa Tiểu/Cửa Đại.
Điều kiện chấp nhận gồm đủ 34 atlas, tọa độ cửa biển và datum được chốt,
và chuỗi mực nước theo giờ ở trạm ven biển/cửa sông phù hợp với cùng
datum và giai đoạn. Chưa lấy Tide làm forcing đáng tin cậy cho Hybrid.

**Giới hạn quyết định:** máy chỉ có M2, S2, K1, O1, trong khi FES2022b
cung cấp 34 thành phần. PyFES ở đây dùng bốn atlas, suy diễn mặc định
và triều dài chu kỳ cân bằng. Đây là chuỗi sàng lọc, **không phải dự báo
FES2022b đầy đủ** và chưa ghép vào feature/model đã kiểm định. Không tạo
các đầu ra chính thức `04_tide_points.geojson`, `05_tide_hourly.csv` hay
`06_tide_monthly.csv` từ bộ thiếu 30 thành phần. Khi có đủ atlas và hoàn
tất QA điểm, dùng cấu hình PyFES chính thức để tái tính.

Nguồn phần mềm: [AVISO FES2022b](https://www.aviso.altimetry.fr/index.php?id=1279),
[hướng dẫn PyFES](https://cnes.github.io/aviso-fes/user_guide.html).

## 6. API và WebGIS đọc kết quả đã kiểm tra

`backend/pilot_spatial.py` bổ sung API chỉ đọc dưới `/pilot/spatial/`:
`sites`, `routes`, `crossings`, `coordinate-candidates`, `metrics`,
`predictions`. Trang `/pilot/spatial/map` ở
`webgis/pilot_spatial.html` hiển thị 5 điểm, EC I–IV, tuyến audit, 13
nút giao và ba điểm đang HOLD (NM28 có thêm giả thuyết tọa độ riêng).
Chọn A/B để xem sai số và độ phủ; trang không hiển thị một giá trị dự báo
River cho NM29 trong B. API chỉ đọc các artifact đã lưu, không tự suy
diễn dữ liệu mới và chưa đưa Tide/Hybrid vào bản đồ.

Đã kiểm tra trực tiếp các hàm API: 5 điểm, 10 tuyến, 13 nút giao, 4
phiên bản tọa độ cho ba điểm chờ, 80 hàng metric và 160 hàng dự báo.
Môi trường sandbox không cho bind socket nội bộ để thử HTTP/browser;
phần giao diện chưa được kiểm chứng trực quan trong trình duyệt. Lệnh
chạy tại máy: `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`,
sau đó mở `http://127.0.0.1:8000/pilot/spatial/map`.

## 7. Mốc quyết định

1. Trên 5 điểm hiện có, River-IDW p=2 có MAE thấp hơn Euclidean-IDW;
   chưa biết có giữ ưu thế ở 7–8 điểm vì NM26/NM28/NM33 chưa đủ QA.
2. River-Nearest có RMSE gộp thấp hơn River-IDW ở A, nhưng chỉ 5 vị trí.
3. Khi tách giao `510175774`, NM29 mất liên thông và River-IDW mất 4/20
   trường hợp LOLO. Do đó **chưa chốt phương pháp Spatial chính**; cần
   kiểm tra thực địa hoặc nguồn thủy lực độc lập tại cụm giao và cống.

Vì chưa có tọa độ hợp lệ cho ba điểm bổ sung, Pilot Spatial v2/LOLO v2
và lựa chọn phương pháp chính chưa thể hoàn tất trung thực. Vì chỉ có 4/34
atlas và chưa có đối chứng triều cùng vị trí/datum, nhánh Tide/Hybrid
vẫn ở mức sàng lọc. API/WebGIS hiện là giao diện xem bằng chứng pilot.

## Tái tạo và kiểm tra

- `scripts/analyze_go_cong_pilot5_sensitivity.py`: so sánh p=2 với baseline
  cũ trước khi xuất; lỗi nếu dự báo thay đổi.
- `scripts/audit_go_cong_pilot5_routes.py`: xuất QGIS/GeoJSON, mở lại dự án
  để xác nhận lớp hợp lệ.
- `scripts/analyze_nm29_crossing_scenarios.py`: đối chiếu A với baseline
  và tách toàn bộ 13 giao của trace 1 với way `510175774` trong B; xuất
  từng cặp, từng dự báo và độ phủ.
- `scripts/screen_go_cong_expansion_points.py`: đo snap ứng viên và giữ
  trạng thái `HOLD_COORDINATE_QA`.
- `scripts/review_go_cong_expansion_coordinates.py`: giữ tọa độ PDF và
  giả thuyết NM28 tách biệt; không nhận điểm chỉ nhờ snap gần.
- `scripts/generate_fes4_tide_screening.py`: kiểm tra mã, tọa độ, bốn
  thành phần và các cờ PyFES; giới hạn đến 2023.
- `pipelines/models/evaluate_monthly_ec_known_at_issue.py`: xuất dự báo
  từng tháng và metric, giữ mọi kết quả cũ nguyên trạng.

Các tệp kết quả có manifest riêng ghi nguồn và giới hạn diễn giải.
