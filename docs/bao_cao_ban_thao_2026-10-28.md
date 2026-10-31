# Bản thảo nội dung báo cáo đồ án

Ngày khởi tạo: 28/10/2026. Đây là nội dung nền để đưa vào mẫu báo cáo chính thức khi có yêu cầu của giảng viên. Các vị trí `[CẦN BỔ SUNG]` là phần cần bằng chứng hoặc quy định trình bày, không phải kết quả đã có.

## Tên đề tài đề xuất

**Xây dựng WebGIS tra cứu EC, đánh giá dự báo theo tháng và hỗ trợ rà soát kịch bản đóng/mở cống trên sông Tiền**.

Nếu tên đề tài đã đăng ký là “cảnh báo xâm nhập mặn Đồng Tháp”, cần giải thích ranh giới giữa mục tiêu dài hạn và phạm vi đã đánh giá. Trạm Mỹ Tho ở Tiền Giang; 27 cống có tọa độ của lớp mô phỏng thuộc danh mục Tiền Giang. Không trình bày chúng thành 27 cống Đồng Tháp.

## Tóm tắt dự thảo

Đồ án xây dựng một ứng dụng WebGIS cho phép tra cứu quan trắc độ dẫn điện (EC), xem nguồn và chất lượng dữ liệu, chạy mô hình dự báo mẫu EC theo tháng tại hai trạm Mỹ Tho và Tân Châu, đồng thời **hỗ trợ rà soát kịch bản đóng/mở cống**. Phần cống hiển thị vị trí, ngưỡng kịch bản và trạng thái sàng lọc; hồ sơ riêng kiểm tra EC và mực nước hai phía, thời điểm đo, mốc cao độ và quy trình do người dùng nhập. Dữ liệu EC MRC hiện có 927 mẫu, gồm 463 mẫu Mỹ Tho và 464 mẫu Tân Châu, kết thúc tháng 12/2023. Mô hình Random Forest đang phục vụ dùng khí tượng và mùa vụ, nhưng không vượt baseline tốt nhất trong kiểm tra hồi cứu 2022–2023. Ứng viên nghiên cứu mới cho Mỹ Tho chọn 8 biến mùa–mưa–Q Kratie–mực nước Tân Châu, đạt MAE 11,07 mS/m trên cùng 24 tháng 2022–2023 so với Persistence 12,62; kỳ này đã được xem nhiều lần, chưa phải kiểm định mù. Ứng dụng công bố nguồn, thời đoạn, sai số và giới hạn của dự báo; kết quả sau 2023 chưa được kiểm định bằng EC MRC cùng kỳ. Kết quả sàng lọc cống là **mô phỏng hoặc rà soát hồ sơ khai báo**, chưa xác minh số đo tại cống và không phát lệnh vận hành.

Từ khóa: WebGIS, độ dẫn điện nước, sông Tiền, dự báo theo tháng, đánh giá theo thời gian.

## 1. Đặt vấn đề và mục tiêu

Xâm nhập mặn liên quan đến biến động nước sông và nhu cầu theo dõi chất lượng nước. Một giao diện bản đồ có thể giúp người dùng xem vị trí, thời điểm, nguồn và diễn biến EC cùng nhau. Tuy nhiên, giá trị EC tại một trạm, dự báo cho tháng tương lai và kết quả mô phỏng dọc sông có ý nghĩa khác nhau. Đồ án đặt mục tiêu trình bày các loại kết quả với phạm vi và mức bằng chứng rõ ràng.

Ba câu hỏi nghiên cứu là: (1) có thể chuẩn hóa và truy nguồn chuỗi EC để tra cứu trên WebGIS như thế nào; (2) mô hình dùng khí tượng và mùa vụ dự báo mẫu EC tháng ở Mỹ Tho/Tân Châu đạt sai số thế nào so với phương pháp đơn giản; (3) hệ thống có thể hỗ trợ sàng lọc kịch bản đóng/mở cống và chỉ ra bằng chứng còn thiếu như thế nào, mà không nhầm dự báo tại trạm với số đo tại cống hoặc lệnh vận hành.

Sản phẩm nghiệm thu gồm ứng dụng web chạy local, API và dữ liệu có phiên bản, mô hình cùng artifact đánh giá, **mô-đun bản đồ cống và hồ sơ sàng lọc kịch bản**, báo cáo phân tích kết quả và kịch bản demo. Phạm vi định lượng dự báo chính là EC đơn vị mS/m tại hai trạm MRC. Giao diện có thêm dữ liệu RIA2 trong snapshot và lớp mô phỏng cống, nhưng chúng không tự mở rộng tập nhãn hay miền kiểm định của mô hình chính.

## 2. Dữ liệu và tiền xử lý

Chuỗi EC MRC có 463 tháng chung từ 06/1985 đến 12/2023; Tân Châu có thêm tháng 05/1985. Mỗi bản ghi là mẫu tại thời điểm nguồn cung cấp, không mặc nhiên là trung bình hoặc cực đại của tháng. Tài liệu nguồn hiện chưa xác nhận cơ sở bù nhiệt của EC, vì vậy báo cáo giữ nguyên đơn vị và cờ chất lượng. Dữ liệu sau 2023 trong ứng dụng có thể gồm ước tính hoặc mô phỏng, không được tính là quan trắc EC MRC mới.

Khí tượng ERA5 qua Open-Meteo được lưu cùng phản hồi nguồn, đơn vị, thời gian và checksum. Đặc trưng dùng trong mô hình là tổng mưa tháng (mm), nhiệt độ trung bình (°C), tốc độ gió 10 m trung bình (m/s) ở tháng `t−2`, cộng sin/cos của tháng mục tiêu `t`. Độ trễ công bố dữ liệu là giả định của giao thức nghiên cứu. Báo cáo cần ghi rõ phiên bản tệp khí tượng và manifest mô hình khi chốt bản nộp.

Ứng dụng có hai đường đọc quan trắc: snapshot nghiên cứu có manifest/checksum và PostgreSQL/PostGIS với phiên bản nguồn được chọn. Số dòng toàn bảng DB có thể khác số quan trắc thuộc phiên bản đang phục vụ. Hồ sơ tiếp nhận chưa xác minh được giữ riêng, không thêm ngầm vào nhãn huấn luyện.

**Hình cần tạo:** bản đồ hai trạm và phạm vi sông Tiền; sơ đồ nguồn EC/khí tượng → QA → artifact → API → WebGIS. **Bảng cần tạo:** nguồn, số mẫu, thời đoạn, đơn vị, cờ chất lượng và vai trò từng bộ dữ liệu.

## 3. Phương pháp

Ứng dụng dùng FastAPI cho API, PostgreSQL/PostGIS cho quan trắc và lịch sử được cấu hình, frontend cho bản đồ, biểu đồ và các luồng tra cứu. Mã tách API, service, repository và quy tắc nghiệp vụ. Mô hình được huấn luyện ngoài request web; lúc người dùng yêu cầu dự báo, API đọc artifact đã đăng ký rồi suy luận theo đầu vào và tháng được chọn. Kết quả xuất JSON/CSV kèm trạm, phiên bản model và đặc trưng thực dùng.

Mỗi trạm có một Random Forest với 300 cây, độ sâu tối đa 8, tối thiểu 3 mẫu mỗi lá và seed 42. Giao thức đánh giá dùng thứ tự thời gian: huấn luyện đến 2018, validation 2019–2021; huấn luyện đến 2021, holdout hồi cứu 2022–2023. Sau đánh giá, artifact phục vụ được fit trên nhãn đến 2023. Các baseline gồm EC gần nhất có thể biết đến `t−2`, EC cùng tháng năm trước và trung bình theo tháng; chỉ so sánh khi dùng cùng trạm và tập tháng.

MAE là trung bình trị tuyệt đối sai số, RMSE nhấn mạnh các sai số lớn. Chúng mô tả tập kiểm tra, không phải khoảng tin cậy của một dự báo riêng. Giai đoạn 2022–2023 đã được xem nhiều lần trong quá trình phát triển; gọi đây là holdout hồi cứu, không gọi là kiểm định mù mới.

Lớp mô phỏng sông dùng trục hình học nguồn OSM đã giản lược và các quy tắc nội suy theo kịch bản. Giá trị độ mặn và trạng thái cống trên lớp này phụ thuộc hệ số/giả định chưa hiệu chuẩn tại địa phương. Mô-đun hồ sơ cống kiểm tra sự có mặt và tính nhất quán của EC, mực nước hai phía cùng thời điểm, hệ cao độ, ngưỡng và mục tiêu lấy/thoát nước. Khi người dùng cung cấp dữ liệu kịch bản, nó trả `BLOCKED`, `REVIEW_REQUIRED` hoặc `CONDITIONS_MET`; các trường `recommendation` và `actuator_command` luôn là `null`, người vận hành vẫn phải rà soát. Máy chủ chưa xác minh các khai báo này bằng số đo gốc, nên kết quả không được dùng để ra quyết định vận hành. Xem `backend/domain/gate_simulation.py` và `backend/domain/gates.py`.

## 4. Kết quả đã xác nhận từ artifact

Trên 24 tháng holdout hồi cứu 2022–2023 của từng trạm, kết quả hiện có là:

| Trạm | Random Forest MAE | Random Forest RMSE | Baseline có MAE thấp nhất | MAE baseline | Đơn vị |
| --- | ---: | ---: | --- | ---: | --- |
| Mỹ Tho | 18,32 | 49,31 | EC gần nhất đến `t−2` | 12,62 | mS/m |
| Tân Châu | 4,45 | 5,84 | EC cùng tháng năm trước | 2,38 | mS/m |

Các số trên là của **RF đang phục vụ**; nó chưa vượt cách dự báo đơn giản tốt nhất trong giai đoạn này. Thí nghiệm `RF_compact` nghiên cứu sau đó giảm MAE Mỹ Tho từ RF cũ 18,63 xuống **11,07 mS/m** theo giả định nhãn EC công bố +5 ngày, so với Persistence **12,62** trên cùng 24 tháng. Trên 36 tháng 2019–2021, RF cũ 71,56; RF thủy văn đầy đủ 58,68; `RF_compact` **50,87 mS/m**. Nhóm sáu tháng EC ≥100 mS/m còn MAE **259,37 mS/m**, nên cải thiện tổng thể không đồng nghĩa dự báo đỉnh mặn chính xác. Kỳ 2022–2023 đã bị xem nhiều lần, không phải kiểm định mù. Bảng đầy đủ và 15 tháng sai số lớn nhất mỗi kỳ ở [báo cáo hiệu chỉnh gọn](ec_compact_recalibration_2026-10-29.md). Chưa có nhãn EC MRC sau 12/2023 để tính sai số cho dự báo 2026; ứng viên chưa thay API/registry.

Phép kiểm tra ghép cặp theo năm trên đúng 60 tháng 2019–2023 cho thấy `RF_compact` có MAE thấp hơn RF cũ ở cả năm năm, nhưng 2020 vẫn đạt MAE **120,34 mS/m**, riêng mùa khô **269,94 mS/m**. Năm 2022, baseline EC gần nhất tốt hơn ứng viên (9,78 so với 14,63 mS/m). Đây là kiểm tra độ bền mô tả trên dữ liệu đã xem, không phải xác nhận độc lập cho tương lai; xem [bảng sai số từng năm](ec_annual_robustness_2026-10-30.md).

Thí nghiệm FES ngày 26/10 tại Mỹ Tho bổ sung đặc trưng biên độ triều biển thiên văn vào mô hình khí tượng + mùa vụ. Trên validation 2019–2021, MAE của mô hình không FES là 69,61; phương án FES tốt nhất được chọn trong năm biến là 69,64 mS/m. Trên holdout hồi cứu 2022–2023, hai giá trị tương ứng là 18,32 và 19,74 mS/m. Thí nghiệm không chứng minh đặc trưng FES đã thử cải thiện dự báo EC; nó cũng không chứng minh triều không có ảnh hưởng vật lý. Đây là kết quả nghiên cứu riêng, chưa thay artifact mô hình web.

Kiểm tra mới dùng chính atlas FES2022b đã tải để tính triều ngày cố định 13–17 của từng tháng trên 1985–2023. Khi thêm vào RF_compact theo giả định EC +5 ngày, MAE 2019–2021 tăng **50,87→52,69**, 2022–2023 tăng **11,07→12,26 mS/m**, nên không chọn biến này; xem [bảng FES và trạm đo](fes2022_vs_observed_tide_2026-10-30.md). Q Kratie/mực nước Tân Châu tính sát ngày phát hành giúp 2022–2023 nhưng làm 2019–2021 và nhóm EC cao xấu hơn, xem [phép thử thủy văn ngày](ec_issue_daily_hydro_2026-10-30.md).

**Hình/bảng còn cần hoàn thiện:** đường thực đo–dự báo theo từng trạm trên đúng tập tháng; đồ thị sai số theo tháng/mùa; bảng đầy đủ MAE/RMSE và số mẫu của cả baseline; ảnh chụp luồng tra cứu và dự báo trên giao diện. Tạo từ artifact đã lưu, ghi commit và ngày xuất hình.

## 5. Thảo luận và giới hạn

Kết quả dự báo chịu ảnh hưởng của độ phủ nhãn, thời điểm mẫu trong tháng, nguồn khí tượng, lựa chọn đặc trưng và biến động thủy văn chưa được mô hình hóa. Không có nhãn mới để kết luận độ chính xác của dự báo hiện tại. Mô hình tại Mỹ Tho hoặc Tân Châu chưa được kiểm định chuyển sang một cống khác. EC không tự quy đổi thành g/L khi thiếu thông tin bù nhiệt và hiệu chuẩn địa phương.

Một số điểm cống nằm trên lớp bản đồ mô phỏng, nhưng sự gần nhau về tọa độ không chứng minh liên kết thủy lực. Hồ sơ cống cần EC và mực nước hai phía cùng thời điểm và hệ quy chiếu, ngưỡng có nguồn, trạng thái công trình và người có thẩm quyền xác nhận trước khi bàn tới hỗ trợ vận hành. Lưu nháp mô phỏng trong DB chỉ ghi lại kịch bản người dùng nhập.

Kiểm toán mới trên GRIT xác nhận 27/27 cống có tọa độ thuộc ranh Đồng Tháp mới, song 10/27 cách đường GRIT gần nhất trên 2 km và chưa có nối kênh được xác minh. Pha mực nước triều Vàm Kênh–Mỹ Thuận chậm khoảng 2–3 giờ trong chuỗi quan trắc; đây không phải thời gian truyền muối. FES đã chọn điểm biên triều thiên văn ứng viên ở cửa Tiểu, còn ba cửa khác cần kiểm với mực nước đo riêng. Bộ GFZ tải thêm chỉ phủ đến 2016; 67 hàng bản tin địa phương năm 2026 là độ mặn g/L chứ không phải EC, nên không đưa vào tập nhãn EC MRC. Chi tiết và giới hạn định lượng ở [kiểm toán cống/GRIT](grit_gate_feasibility_2026-10-29.md), [kiểm biên FES](fes_tide_boundary_validation_2026-10-29.md) và [rà soát nguồn bổ sung](new_data_search_2026-10-29.md).

Đối chiếu 450 tháng EC Mỹ Tho–Mỹ Thuận cho thấy 387 cặp ghi cùng ngày, nhưng 34 tháng Mỹ Tho ≥100 mS/m đều có Mỹ Thuận <100 mS/m. Trong các đỉnh 02–05/2020, Mỹ Thuận chỉ 25,6–28,1 mS/m vào cùng ngày. Đây là lý do không dùng EC Mỹ Thuận như một phép truyền tuyến tính để suy đỉnh Mỹ Tho; xem [bảng cặp trạm](ec_mytho_mythuan_pair_2026-10-30.md). Dữ liệu mẫu tháng không cho giờ pha triều hoặc vận tốc truyền muối.

Rà nguồn UHSLC phát hiện tệp legacy gắn tên Vũng Tàu `id142` thật ra thuộc Langkawi (Malaysia); mã Vũng Tàu đúng là `383/383B`. Đã cô lập tệp cũ khỏi đường đọc và chuẩn hóa chuỗi Vũng Tàu-B 2007–2024. Những kết luận legacy dựa trên `tide_max_m` từ id142 không được trích cho Vũng Tàu cho tới khi chạy lại với nguồn đúng. RF_compact hiện không dùng cột này; xem [đính chính triều](fes2022_vs_observed_tide_2026-10-30.md).

Giá trị của đồ án hiện tại nằm ở việc thống nhất tra cứu không gian và chuỗi thời gian, giữ nguồn dữ liệu có thể kiểm tra, đưa baseline vào đánh giá, và diễn giải đúng các kết quả còn hạn chế. Các mở rộng có căn cứ là thu thập EC mới cùng QA, kiểm định mô hình trên giai đoạn mới, rồi mới thử mô hình hoặc địa điểm bổ sung theo giao thức chốt trước.

## 6. Kết luận dự thảo

Đồ án đã xây dựng nền tảng WebGIS cho tra cứu EC, nghiên cứu dự báo mẫu EC theo tháng ở hai trạm trên sông Tiền và **hỗ trợ rà soát kịch bản đóng/mở cống** bằng ngưỡng, kiểm tra hồ sơ và trạng thái sàng lọc. RF đang phục vụ còn kém baseline mạnh nhất; ứng viên nghiên cứu gọn cho Mỹ Tho có MAE hồi cứu thấp hơn, nhưng đỉnh EC 2020 vẫn bị dự báo thấp rất nhiều và kết quả năm 2026 chưa có quan trắc EC MRC cùng kỳ để xác minh. Phần cống chưa có số đo tại chỗ và quy trình được máy chủ xác minh để đưa ra lệnh vận hành. Giao diện và báo cáo cần giữ ranh giới giữa quan trắc, dự báo, nghiên cứu hồi cứu và mô phỏng cống. Bước tiếp theo có giá trị cao nhất là dữ liệu EC mới đạt QA, số đo hai phía cống và đánh giá ngoài mẫu trên đúng giao thức đã công bố.

## Bằng chứng nội bộ cần trích trong bản nộp

- [Trạng thái ứng dụng](tien_trinh_web_2026-10-25.md) và [kiến trúc](architecture.md).
- [Giao thức và mô hình đa biến](multivariate-forecast.md), registry `../data/models/multivariate_registry.json`, manifest và predictions trong `../runs/multivariate_ec/`.
- [Thí nghiệm FES nhiều điểm](../outputs/fes_ec_multipoint_20261026/README.md) và `summary.json` cùng thư mục.
- [Giới hạn mô phỏng](spatial-simulation.md), nguồn hình học `../data/biengioi/tien_river_corridor.geojson`.
- [Kế hoạch kiểm chứng và hoàn thiện](ke_hoach_4_tuan_2026-10-28.md).
- [Quyết định tích hợp EC, thủy lực và cống](integrated_ec_salinity_gate_2026-10-29.md).

Trước khi nộp: bổ sung tài liệu tham khảo học thuật/chính thức theo chuẩn trường; tạo hình và bảng từ dữ liệu; thay mọi mốc/tên phiên bản bằng trạng thái của bản cuối; rà soát chính tả và định dạng theo mẫu giảng viên.
