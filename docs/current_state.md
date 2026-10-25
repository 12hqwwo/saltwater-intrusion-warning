# Tình trạng hiện tại của đồ án

Cập nhật: **24/10/2026, khoảng 13:51 (UTC+7)**.

Tài liệu ghi nhận trạng thái đã đối chiếu với mã nguồn, artifact và API đang chạy tại `http://127.0.0.1:8000`. Những hướng đang trao đổi được đánh dấu riêng, không tính là chức năng đã hoàn thành. Số lượng bản ghi phản ánh thời điểm kiểm tra và có thể thay đổi khi nhập dữ liệu hoặc lưu dự báo mới.

## 1. Phạm vi đồ án ở thời điểm hiện tại

Đồ án đã có **WebGIS tra cứu EC lịch sử, dự báo EC theo tháng tại Mỹ Tho và Tân Châu, cùng mô phỏng điều kiện lấy/thoát nước tại cống từ dữ liệu người dùng khai báo**.

Phần dự báo đa biến chạy suy luận trực tiếp từ mô hình đã huấn luyện. Giá trị của phần này hiện là nghiên cứu dự báo tại hai trạm, đánh giá sai số và so sánh kịch bản. Chưa có bằng chứng để coi kết quả là dự báo EC tại mọi cống hoặc hệ thống vận hành cống đã được kiểm chứng.

Các giới hạn chính:

- Quan trắc EC MRC hiện có kết thúc ngày **15/12/2023**; chưa có EC thực đo MRC giai đoạn 2024–2026 trong bộ đang dùng.
- Mô hình đang phục vụ chỉ áp dụng cho **Mỹ Tho và Tân Châu**; chưa có mô hình dự báo cho các vị trí khác.
- Chưa đủ căn cứ chuyển EC sang độ mặn tại các vị trí nghiên cứu bằng một quan hệ hiệu chuẩn đã kiểm chứng.
- Phần cống đánh giá kịch bản theo dữ liệu và ngưỡng khai báo; chưa có lịch vận hành thực tế đã kiểm chứng hoặc kết nối điều khiển thiết bị.

## 2. Nguồn dữ liệu và tình trạng database

### 2.1. Nguồn web đang đọc

| Thành phần | Trạng thái xác nhận ngày 24/10/2026 |
| --- | --- |
| Workspace đang chạy | `snapshot`, xác nhận qua `/api/v1/app-health` và `/api/v1/workspace/summary` |
| Quan trắc trong snapshot | **12 điểm / 977 mẫu EC**: 2 trạm MRC và 10 điểm RIA2 |
| Quan trắc thật trong PostgreSQL | **2 trạm / 927 mẫu RAW_EC**: Tân Châu 464, Mỹ Tho 463 |
| Danh mục cống trong snapshot | **4 cống**, đều chưa có geometry |
| Danh mục cống thật trong PostgreSQL | `/api/v1/workspace/database-gates` trả danh sách rỗng |
| Mô hình đa biến | Artifact tệp, được chọn qua `data/models/multivariate_registry.json` |
| Hồ sơ tiếp nhận v3 | Tệp rà soát riêng, chưa nhập vào quan trắc hoặc nhãn huấn luyện |
| Tám CSV mới người dùng gửi | Đã được rà soát trong trao đổi; chưa nhập DB, chưa thay snapshot hoặc mô hình |

Chế độ workspace và nguồn dữ liệu của từng khối là hai thông tin riêng. Khối **Lịch sử quan trắc PostgreSQL** luôn gọi API database, kể cả khi workspace chính đang chạy snapshot. Trong chế độ PostgreSQL, artifact mô hình, thí nghiệm và một số danh mục vẫn có nguồn tệp riêng.

Không suy ra chế độ của tiến trình đang chạy chỉ từ `.env`; cần xem API runtime. Lỗi PostgreSQL không tự chuyển sang snapshot.

### 2.2. Các phần lưu trữ đã có

- `public.measurement_site`: danh mục trạm.
- `public.source_dataset`: thông tin bộ dữ liệu nguồn.
- `public.conductivity_observation`: quan trắc EC.
- `public.irrigation_gate`: danh mục cống; hiện API không trả cống thật nào.
- `dss_reference`: kho bổ trợ cho ngưỡng kịch bản, lịch sử dự báo đa biến và nháp hồ sơ cống.

API đọc kho DSS hiện hoạt động: có **3 mẫu ngưỡng minh họa** và **1 bản ghi lịch sử dự báo** tại thời điểm kiểm tra. Chức năng lưu mới phụ thuộc migration, quyền DB và `WEBGIS_DSS_WRITES_ENABLED`; phiên cập nhật tài liệu này không thử ghi thêm dữ liệu.

**Có thể lưu danh mục trạm/cống dù chưa có EC.** Danh mục địa điểm và bảng số đo có trách nhiệm riêng. Điểm chưa có EC phải thể hiện chưa có dữ liệu; không thay bằng 0, không gán EC trạm khác thành số đo tại điểm đó. Kết quả dự báo được lưu riêng với quan trắc.

## 3. Quan trắc EC đang sử dụng

| Nhóm/trạm | Số mẫu | Thời gian | Vai trò hiện tại |
| --- | ---: | --- | --- |
| Tân Châu — `MRC_VN_019803` | 464 | 15/05/1985–15/12/2023 | Tra cứu EC và nhãn huấn luyện mô hình tháng |
| Mỹ Tho — `MRC_VN_019805` | 463 | 26/06/1985–15/12/2023 | Tra cứu EC và nhãn huấn luyện mô hình tháng |
| 10 điểm RIA2 — `RIA2_DT_01` đến `RIA2_DT_10` | 5/điểm, tổng 50 | 08–11/2025 | Tra cứu quan trắc theo đợt trong snapshot; không tham gia mô hình đa biến |

Hai trạm MRC có **463 tháng chung từ 06/1985 đến 12/2023**. Chênh lệch một mẫu do Tân Châu có thêm tháng 05/1985; không cần tạo thêm số đo để cân bằng. Kiểm đếm trước đó không thấy tháng trống bên trong chuỗi của từng trạm.

EC dùng đơn vị **mS/m**. Mẫu trong một tháng không mặc nhiên là trung bình hoặc cực đại cả tháng. Cơ sở bù nhiệt EC hiện chưa được xác nhận; các bản ghi MRC giữ cờ nguồn `UNVERIFIED`. Độ dài và độ đầy đủ của chuỗi không thay thế việc xác minh chất lượng số đo.

RIA2 có ít mẫu và thiếu tọa độ/CRS được xác nhận để dùng làm lớp điểm chính. Hướng trao đổi gần nhất là tập trung hai trạm MRC trên giao diện, bảo toàn dữ liệu RIA2 để tham khảo. **Việc loại RIA2 khỏi workspace chưa được triển khai**; API hiện vẫn trả 12 điểm.

## 4. Mô hình dự báo EC đa biến hiện tại

### 4.1. Cấu hình và đầu vào

- Phiên bản đang phục vụ: **`20261023T041813Z`**.
- Hai mô hình Random Forest độc lập: một cho Mỹ Tho, một cho Tân Châu.
- Mỗi mô hình có 300 cây, độ sâu tối đa 8, tối thiểu 3 mẫu mỗi lá, seed 42.
- Nhãn: 463 mẫu tháng Mỹ Tho và 464 mẫu tháng Tân Châu từ `data/research/mrc_ec_monthly_samples.csv`, kết thúc 12/2023.
- Ba biến khí tượng: tổng mưa tháng, nhiệt độ trung bình tháng, tốc độ gió 10 m trung bình tháng; thêm sin/cos của tháng mục tiêu để biểu diễn mùa vụ.
- Nguồn khí tượng: ERA5 qua Open-Meteo, lưu trong `data/external/multivariate_weather/`, có manifest, đơn vị và checksum; dữ liệu đã có đến **09/2026** cho hai trạm.
- Dự báo tháng `t` dùng khí tượng tháng **`t−2`**. Ví dụ mặc định hiện tại là tháng 11/2026, dùng khí tượng 09/2026. Giả định độ trễ công bố nguồn cần được giữ rõ khi trình bày.
- Mô hình **không dùng** EC trễ, lưu lượng, mực nước, triều, trạng thái cống, tọa độ hay liên kết sông/kênh làm feature.

Do không dùng EC trễ, mô hình vẫn tính được kết quả mới khi chỉ cập nhật khí tượng. Điều này không bổ sung EC thực đo và không chứng minh độ chính xác ở giai đoạn sau 2023. Muốn kiểm chứng và cập nhật mô hình cần quan trắc EC cùng kỳ.

### 4.2. Kết quả kiểm chứng đang có

Đánh giá theo thời gian tại từng trạm: huấn luyện đến 2018, validation 2019–2021; huấn luyện đến 2021, holdout 2022–2023. Mô hình phục vụ được fit lại trên toàn bộ nhãn đến 2023. Mỗi trạm có **24 tháng holdout**; chưa có kiểm chứng bằng cách giữ riêng một trạm mới ngoài tập huấn luyện.

Sai số trên holdout 2022–2023, đơn vị mS/m; thấp hơn là tốt hơn:

| Trạm | RF MAE | RF RMSE | Baseline đơn giản có sai số thấp hơn |
| --- | ---: | ---: | --- |
| Mỹ Tho | 18,32 | 49,31 | Persistence: MAE 12,62; RMSE 18,91 |
| Tân Châu | 4,45 | 5,84 | Seasonal Naive: MAE 2,38; RMSE 3,19 |

Các baseline được đánh giá trên cùng tập tháng, với đầu vào quá khứ được giới hạn theo thời điểm giả định. Persistence dùng EC gần nhất đến `t−2`; Seasonal Naive dùng EC cùng tháng năm trước. Đây là đánh giá hồi cứu khi có EC lịch sử, không xác nhận rằng đã có đủ EC mới để chạy các baseline đó trong năm 2026.

Kết quả hiện tại **chưa chứng minh mô hình đa biến vượt các cách đơn giản tại cả hai trạm**. Dự báo 2024–2026 chưa có EC thực đo MRC cùng kỳ trong bộ hiện có để đánh giá. Các cờ `deployment_ready=false`, `gate_decision_eligible=false` được giữ trong đầu ra mô hình; MAE/RMSE lịch sử không phải khoảng tin cậy cho từng lần dự báo mới.

### 4.3. Dự báo tại trạm khác có khả thi không?

| Bài toán | Kết luận theo dữ liệu và mô hình hiện có |
| --- | --- |
| EC lịch sử Mỹ Tho + khí tượng Mỹ Tho → EC Mỹ Tho | Có thể nghiên cứu và kiểm chứng theo thời gian; đã triển khai |
| EC lịch sử Tân Châu + khí tượng Tân Châu → EC Tân Châu | Có thể nghiên cứu và kiểm chứng theo thời gian; đã triển khai |
| Mô hình một trong hai trạm + khí tượng tại cống/trạm khác → EC tại vị trí mới | Chưa đủ căn cứ; chưa có kiểm chứng khả năng chuyển mô hình giữa các vị trí |

API chỉ đăng ký mô hình cho hai trạm MRC. Nếu nhập thủ công khí tượng nơi khác nhưng chọn Mỹ Tho, kết quả vẫn là ước tính có điều kiện của **mô hình Mỹ Tho**, không tự trở thành dự báo được kiểm chứng cho nơi cung cấp khí tượng.

EC chịu ảnh hưởng của dòng chảy, truyền triều, vị trí trên sông/kênh, khoảng cách tới biển và hoạt động công trình. Để mở rộng cần quan trắc EC tại vị trí mới để hiệu chỉnh/đánh giá, hoặc một mô hình có các biến không gian/thủy văn phù hợp đã vượt kiểm chứng trên các trạm chưa dùng huấn luyện. Tọa độ và khí tượng riêng chưa đủ để xác lập độ chính xác tại cống.

## 5. Chức năng web đã có và giá trị sử dụng

| Chức năng | Trạng thái và ý nghĩa |
| --- | --- |
| Tra cứu quan trắc | Bản đồ, biểu đồ, bảng, lọc thời gian và xuất CSV |
| Lịch sử PostgreSQL | Đọc DB riêng, chọn nguồn/trạm, lọc thời gian và loại O/E, phân trang |
| Dự báo đa biến | Chọn một trong hai trạm, chọn tháng, lấy khí tượng lưu trữ hoặc nhập tay, chạy suy luận từ artifact |
| Đánh giá mô hình | Xem thực đo–dự báo hồi cứu và sai số so với baseline |
| Kết quả dự báo trên bản đồ | Có lớp hiển thị dự báo tại đúng trạm, tách khỏi giá trị quan trắc |
| So sánh và lưu dự báo | So sánh các lượt chạy trong phiên, xuất JSON/CSV; có API/giao diện lưu và đọc lịch sử PostgreSQL |
| Hồ sơ cống | Nhập số đo và giới hạn kịch bản, mô phỏng lấy/thoát nước, xem điều kiện đạt/chặn/còn thiếu |
| Nháp hồ sơ | Có lưu/khôi phục trên trình duyệt và chức năng lưu/đọc PostgreSQL theo cấu hình DSS |
| Đính kèm dự báo vào hồ sơ cống | Lưu dưới `forecast_context`, loại `MONTHLY_FORECAST_REFERENCE_ONLY`, `gate_observation=false` |
| Chất lượng và tiếp nhận | Khu vực rà soát dữ liệu riêng, vẫn có trên điều hướng chính |

Phần đa biến đã có liên kết ra bản đồ và hồ sơ cống. Tuy nhiên, liên kết hiện tại là **tham khảo**: không tự điền dự báo tháng thành EC ngoài cống hoặc số đo tức thời, và không xác lập quan hệ thủy lực giữa trạm với cống. Giá trị hỗ trợ vận hành còn phụ thuộc dữ liệu địa phương và kiểm chứng mô hình.

Khối lịch sử PostgreSQL đã được đơn giản hóa theo yêu cầu ngày 24/10: bỏ bộ chọn phiên bản dữ liệu, bộ lọc/cột chất lượng và màu chất lượng trên biểu đồ của khối này; tự chọn bộ RAW_EC được nhập mới nhất của trạm. Metadata phiên bản và chất lượng vẫn được giữ trong backend/CSV. **Chưa xóa toàn bộ mục “Chất lượng dữ liệu” hoặc các trường chất lượng trên những giao diện khác.**

Điểm cần đồng bộ sau: API tổng quan vẫn trả `live_forecast_available=false` trong khi API đa biến đã có thể tính kết quả mới. Cờ tổng quan này không đủ để kết luận toàn bộ web chưa có chức năng suy luận dự báo. Tài liệu này mô tả rõ từng nhánh thay vì gộp các sản phẩm thành một trạng thái.

## 6. Những sản phẩm dữ liệu khác cần phân biệt

- **Bốn thí nghiệm EC trễ cũ:** kết quả hồi cứu tại hai trạm, với giả định độ trễ 0/30 ngày; artifact trong `runs/local_ec_backtest/`. Không phải hai mô hình đa biến đang phục vụ.
- **CSV ước tính 2024–2026:** `data/models/future_ec_forecast_2024_2026.csv`, dùng khí tượng cùng tháng để ước tính giai đoạn thiếu nhãn. Không dùng kết quả này làm EC thực đo hoặc làm bằng chứng dự báo trước tháng mục tiêu.
- **Bộ tiếp nhận v3 cũ:** CSV ML 640 dòng/47 trạm và bộ chuẩn hóa từ workbook có 890 bản ghi; manifest ghi 21 mục bị loại. Đây là các sản phẩm khác nhau trong cùng khu vực rà soát, không cộng thành số đo EC độc lập. Hiện chưa đủ điều kiện huấn luyện hoặc làm căn cứ vận hành cống.
- **DAHITI/GloFAS và các nghiên cứu feature:** là nguồn/nghiên cứu phụ trợ; chưa tham gia bộ feature của hai mô hình đa biến đang phục vụ. Có tệp không đồng nghĩa có chuỗi giá trị hợp lệ hoặc đã tích hợp.
- **Bản đồ:** nền OSM và hai tệp ranh giới Đồng Tháp/Tiền Giang trong `data/biengioi/`; chưa có bề mặt độ mặn liên tục đã kiểm chứng.

## 7. Tám CSV mới: trạng thái tiếp nhận và các điểm cần xử lý

Các số dưới đây là kết quả rà soát những tệp người dùng đã gửi trong cuộc trao đổi ngày 24/10/2026. Tệp gốc ở thư mục tạm, chưa được đưa thành nguồn chính thức của ứng dụng. Tên có `verified` hoặc `cleaned` không thay thế việc xác minh nội dung và tài liệu nguồn.

| Tệp | Nội dung đã rà soát | Tình trạng sử dụng |
| --- | --- | --- |
| `01_ec_salinity_calibration_and_lookup.csv` | 31 dòng, chỉ 2 dòng tự mô tả cặp IoT đo đồng thời; có benchmark, ngưỡng và bảng tra | Chưa đủ để hiệu chuẩn EC–độ mặn; benchmark MRC có sai khác với bộ đang dùng |
| `02_stations_master_catalog_63.csv` | 63 trạm, không phải tất cả có chuỗi quan trắc | Có thể làm danh mục sau khi chuẩn hóa mã và xác minh tọa độ; có Plus Code sai/mâu thuẫn |
| `03_sluice_gates_190_and_27_verified_gis.csv` | 190 công trình, 27 có tọa độ; có các cặp công trình trùng tọa độ | Chưa nhập DB/map; cần phân biệt cống/trạm bơm và kiểm tra vị trí |
| `04_sluice_gate_operation_rules_and_risk_matrix.csv` | 13 dòng quy tắc/kế hoạch | Có mâu thuẫn số và văn bản; chưa được dùng làm luật vận hành |
| `05_sluice_gate_operation_logs_57.csv` | 57 dòng tường thuật | Chưa phải log đóng/mở có thời điểm, thời lượng và mã cống đầy đủ |
| `06_river_and_interior_salinity_ec_observations_759.csv` | 759 dòng, trộn vị trí trong/ngoài và cách thống kê | EC phần lớn là quy đổi; cần tách thực đo, dẫn xuất và số liệu tái dựng |
| `07_hydro_meteo_waterlevel_drivers_533.csv` | 533 dòng nhưng chỉ 30 ngày phân biệt; có thiếu giá trị | Cần thống nhất thời điểm, hệ cao độ và nguồn; một số dòng chỉ mô tả nguồn dữ liệu |
| `08_ml_timeseries_642_and_pilot_154_cleaned.csv` | 642 dòng/49 trạm; pilot 154 dòng; chuỗi ngày liên tiếp dài nhất 7 ngày | 640 EC dẫn xuất, 2 EC tự mô tả thực đo IoT; chưa huấn luyện mô hình từ bộ này |

Nhiều dòng ở tệp 08 được tạo từ tệp 06, không phải quan trắc độc lập. Bộ mới có thể hỗ trợ danh mục bản đồ, tra cứu nguồn và nghiên cứu độ mặn theo ngày sau khi xử lý các vấn đề; chưa đủ căn cứ thay chuỗi EC MRC hoặc nối trực tiếp vào khuyến nghị cống.

## 8. Hướng đã trao đổi và phần chưa triển khai

| Hướng xử lý | Trạng thái tại thời điểm cập nhật |
| --- | --- |
| Tập trung Tân Châu và Mỹ Tho cho nghiên cứu EC theo tháng | Mô hình hiện đã chỉ dùng hai trạm; hướng thu gọn giao diện đã được trao đổi |
| Bỏ RIA2 khỏi danh sách/bản đồ chính, giữ dữ liệu gốc tham khảo | **Chưa triển khai**; snapshot vẫn có RIA2 |
| Lọc các trạm/công trình có tọa độ trong bộ mới để đưa lên bản đồ | **Chưa triển khai**; 27 công trình là tập ứng viên cần kiểm tra |
| Chọn 3–5 cống làm pilot | Mới là đề xuất; chưa chốt danh sách cống |
| Tìm dữ liệu địa phương phục vụ các cống pilot | Chưa có đợt tìm kiếm/xác minh nguồn riêng cho tập pilot đã chốt |
| Gán trạm đại diện cho từng cống | Chưa có quan hệ được kiểm chứng; khoảng cách chỉ sàng lọc ứng viên |
| Dự báo EC cho trạm/cống khác bằng khí tượng tại đó | Chưa có mô hình hoặc kiểm chứng phù hợp |

Đề xuất thứ tự thực hiện tiếp:

1. Hoàn thiện phạm vi hiển thị: hai trạm MRC cho nghiên cứu EC; dữ liệu RIA2 được bảo toàn ở phần tham khảo nếu thu gọn giao diện.
2. Xác minh mã, tọa độ và nguồn của công trình ứng viên; chọn pilot theo mức độ có dữ liệu thực tế.
3. Chuẩn hóa danh mục trạm/cống và nhập DB, tách danh mục khỏi quan trắc và dự báo.
4. Thu thập độ mặn/EC, mực nước trong–ngoài, thời điểm đo, triều, quy trình riêng và log thực tế tại pilot; kiểm tra hệ cao độ và cơ sở EC.
5. Xác minh liên kết trạm–cống theo sông/kênh và điều kiện truyền mặn; trình bày rõ điều kiện đã có và còn thiếu trong mô phỏng.
6. Bổ sung EC mới và đánh giá lại mô hình trên cùng tập dữ liệu với baseline trước khi tăng vai trò của dự báo trong hỗ trợ quyết định.

## 9. Mã nguồn, cách chạy và bằng chứng kiểm tra

Các vị trí chính:

- Giao diện: `frontend/workspace.html`, `frontend/src/app/workspace.js`, `frontend/src/features/`.
- Backend: `backend/api/`, `backend/services/`, `backend/repositories/`, `backend/domain/`.
- Snapshot: `data/research/workspace.json` và `workspace_manifest.json`.
- Đa biến: `backend/domain/multivariate_ec.py`, `scripts/train_multivariate_ec.py`, registry và hai manifest trong `runs/multivariate_ec/{mytho,tanchau}/20261023T041813Z/`.
- Lưu DSS: `sql/30_dss_storage.sql`, `backend/repositories/dss_storage.py`, `backend/services/dss_storage.py`.

Chạy từ gốc dự án bằng môi trường hiện có:

```powershell
.\start.ps1                 # Workspace đọc snapshot
.\start.ps1 -Mode postgres  # Workspace đọc quan trắc PostgreSQL
```

Chỉ chạy một chế độ tại một thời điểm trên cùng cổng. Trang chính: `http://127.0.0.1:8000/workspace.html`.

Các API đã đối chiếu khi cập nhật tài liệu:

- `GET /api/v1/app-health`
- `GET /api/v1/stations` và `/api/v1/stations/{site_code}/datasets` cho hai trạm MRC
- `GET /api/v1/workspace/summary`
- `GET /api/v1/workspace/database-gates`
- `GET /api/v1/workspace/multivariate/catalog`
- `GET /api/v1/workspace/threshold-presets`
- `GET /api/v1/workspace/multivariate/history?limit=1`

Các lần đọc API xác nhận nguồn runtime, số trạm, metadata số đo, artifact đang phục vụ và khả năng đọc kho DSS. Chúng không thay thế kiểm chứng chất lượng đo, kiểm chứng dự báo ngoài mẫu mới hoặc nghiệm thu toàn bộ giao diện. Phiên cập nhật này chỉ sửa tài liệu; không huấn luyện lại, nhập/xóa dữ liệu hoặc chạy lại toàn bộ bộ kiểm thử.

Tài liệu liên quan: [README](../README.md), [hướng dẫn chạy](run_guide.md), [kiến trúc](architecture.md), [dự báo đa biến](multivariate-forecast.md), [lưu trữ DSS](dss-storage.md). Khi hướng dẫn cũ khác với nội dung giao diện vừa sửa, đối chiếu mã hiện tại và bằng chứng có ngày cập nhật thay vì coi kế hoạch là chức năng đã hoàn thành.
