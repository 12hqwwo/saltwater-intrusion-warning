# Hệ thống kiến thức dự án WebGIS EC Đồng Tháp — bản ôn tập ra hội đồng

**Ngày lập:** 13/11/2026. **Checkout đối chiếu:** `D:\Study\TLCN`, nhánh `TinBranch`, HEAD `0cc62ca` (`feat: animate river and seasonal wind map layers`).
**Trang chạy thực tế lúc kiểm tra:** `http://127.0.0.1:8000/workspace.html`, tiến trình `run_webgis.py --mode postgres --port 8000` chạy từ checkout chính, `/api/v1/health` trả `database_name=dongthap_gis`, `transaction_read_only=true`.

Tài liệu đi theo đúng dòng chảy của dữ liệu: **thu thập → xử lý → nạp → cơ sở dữ liệu → mô hình → nội suy → giảm sai số → WebGIS**. Mỗi mục có ba lớp: *kiến thức nền* (khái niệm bạn phải giải thích được), *dự án làm gì* (có đường dẫn file), *câu cần nhớ* (số liệu, giới hạn). Số liệu đã đối chiếu với mã, manifest và giao diện đang chạy; chỗ nào là giả định đều ghi rõ.

---

## 0. Một trang tóm tắt để mở đầu bảo vệ

- **Bài toán:** dự báo **độ dẫn điện EC** (đơn vị mS/m) theo **tháng** tại trạm Mỹ Tho trên sông Tiền, hiển thị bối cảnh mặn dọc sông trên WebGIS và hỗ trợ **rà soát điều kiện** lấy nước tại cống. Hệ thống **không** phát lệnh đóng/mở cống.
- **Dữ liệu nhãn:** mẫu EC MRC — Mỹ Tho 463 tháng (06/1985–12/2023), Tân Châu 464, Mỹ Thuận 451. Mỗi tháng **một mẫu đơn lẻ**, không phải trung bình tháng. Mẫu cuối 15/12/2023.
- **Mô hình chính:** Random Forest 300 cây, sâu tối đa 8, tối thiểu 3 mẫu/lá, seed 42, 10 đặc trưng (mưa, nhiệt, gió, sin/cos tháng, 3 biến lưu lượng Kratie, 2 biến mực nước Tân Châu), tất cả lấy tháng **t−2**. Phiên bản `20261108T_HYDROLOGY_PRIMARY_V1`.
- **Đánh giá:** giao thức “khóa EC” mô phỏng cảnh mất EC dài hạn. MAE/RMSE (mS/m): 2019–2021 **57,81/133,82**; 2021–2023 **16,57/31,21**; 2022–2023 **12,19/25,43**. Đây là **hồi cứu**, không phải kiểm định mù.
- **Nội suy:** tuyến tính từng chặng dọc trục sông Tiền 175 km với mốc Tân Châu 0 km, Mỹ Thuận 85,2 km, Mỹ Tho 125 km, biên cửa sông giả định 175 km.
- **Giới hạn trung thực:** chưa có EC Mỹ Tho sau 2023 để kiểm định độc lập; mô hình bỏ hụt đỉnh 692 mS/m (03/2020, dự báo 213,67); lịch công bố dữ liệu lịch sử là giả định; màu sau cống không tô vì không có EC nội kênh.

---

## 1. Bài toán và kiến thức nền về xâm nhập mặn

### 1.1 EC là gì và vì sao chọn EC thay vì “độ mặn”

- **EC (Electrical Conductivity, độ dẫn điện)** đo khả năng dẫn điện của nước. Nước càng nhiều ion muối hòa tan (Na⁺, Cl⁻…) thì EC càng cao. Đây là đại lượng **đo trực tiếp** bằng điện cực.
- **Quy đổi đơn vị cần thuộc:** 1 dS/m = 100 mS/m = 1000 µS/cm; nên **µS/cm ÷ 10 = mS/m**. Dự án dùng mS/m thống nhất (`conductivity_ms_per_m` trong PostgreSQL, CHECK `unit='mS/m'`). Dữ liệu RIA2 gốc là µS/cm và được chia 10 khi dựng snapshot (`scripts/build_research_workspace.py`).
- **Độ mặn (g/L, ‰, PSU)** là đại lượng suy ra, phụ thuộc nhiệt độ và thành phần ion. Quan hệ EC–độ mặn không tuyến tính tuyệt đối (công thức chuẩn là PSS-78). Dự án chỉ dùng **quy đổi tham khảo** `g/L ≈ 0,0064 × EC (mS/m)` để hiển thị; **mức cảnh báo màu luôn tính theo EC**. Quy tắc dữ liệu (`.claude/rules/data-contracts.md`) cấm dùng hệ số cố định này trong pipeline mô hình.
- **Lý do chọn EC:** nhãn MRC là EC đo thật; quy đổi sang độ mặn sẽ thêm sai số và giả định nhiệt độ (cột `ec_temperature_basis` hiện là `UNKNOWN` — chưa rõ đã bù nhiệt về 25 °C hay chưa).

### 1.2 Cơ chế xâm nhập mặn sông Tiền (cần nói được bằng lời)

- Mặn từ Biển Đông theo **thủy triều** đi ngược vào cửa sông. Nước ngọt từ thượng nguồn Mekong **đẩy** mặn ra. Ranh mặn dịch vào sâu khi **lưu lượng thượng nguồn thấp** (mùa khô, khoảng 12–5) và triều cường.
- Vì vậy các yếu tố giải thích EC Mỹ Tho gồm: **lưu lượng Kratie** (trạm thủy văn ở Campuchia, đại diện nguồn nước Mekong đổ xuống), **mực nước Tân Châu** (đầu nguồn sông Tiền tại Việt Nam), **mưa** tại chỗ, **mùa** (sin/cos tháng), và triều (đã thử FES, chưa đưa vào mô hình chính).
- **Mỹ Tho** ở hạ lưu (cách cửa khoảng 50 km theo trục mô phỏng), nên EC biến động mạnh: mùa mưa ~10–20 mS/m, mùa khô hạn nặng có thể vài trăm. **Tân Châu và Mỹ Thuận** ở thượng/trung lưu, EC gần như luôn thấp (cao nhất ~58–61 mS/m năm 1998).
- **Đỉnh lịch sử Mỹ Tho** (từ `data/research/mrc_ec_monthly_samples.csv`): 841 (04/1998), 797 (04/1988), 699 (04/1994), **692 (03/2020)**, 607 (04/2020). Có **26/463** tháng ≥150 mS/m và **4** tháng ≥620 mS/m. Dữ liệu lệch phải mạnh: số đỉnh ít, khó học.
- Mùa khô 2019–2020 là đợt hạn mặn lịch sử ở ĐBSCL; đó là lý do kỳ 2019–2021 khó nhất trong mọi phép đánh giá.

### 1.3 Mức tham chiếu

- Tham chiếu MRC cho Mỹ Tho trong quy tắc dự án: NORMAL < 150, WATCH 150–620, SEVERE ≥ 620 mS/m — **để trực quan hóa rủi ro, không phải luật vận hành cống**.
- Trên giao diện, người dùng chọn **cặp ngưỡng kịch bản** theo mục đích: Sầu riêng 50/80, Cây có múi 100/150 (mặc định), Lúa & nước ngọt 120/200, hoặc tự nhập. Các ngưỡng này là **minh họa**, bảng `dss_reference.ec_threshold_presets` có CHECK `is_operational_rule = false`.
- Tài liệu 12/11 (`docs/giai_phap_van_de_mo_2026-11-12.md`) ghi tham chiếu chuyên môn: MRC cho lúa < 200 / 200–480 / > 480 mS/m; FAO cho lúa ECw 2,0 dS/m (=200 mS/m); QCVN 39:2011 là chuẩn chất lượng nước tưới, **không** phải luật mở cống.

---

## 2. Thu thập dữ liệu

### 2.1 Kiến thức nền

- **Dữ liệu sơ cấp vs thứ cấp:** dự án không tự đo; mọi dữ liệu là thứ cấp từ MRC, Copernicus/ERA5, AVISO, DGFI-TUM, NOAA, OpenStreetMap…
- **Provenance (truy nguồn):** mỗi tệp giữ tên gốc, nguồn, số dòng, **SHA-256**, đơn vị, độ phân giải thời gian, vị trí, thời điểm tải. SHA-256 là hàm băm: đổi 1 byte thì chuỗi băm đổi hoàn toàn → chứng minh tệp không bị sửa.
- **Raw bất biến:** `data/raw/` không sửa; bản làm sạch/biến đổi để ở lớp sau.

### 2.2 Bảng nguồn (cần thuộc)

| Nguồn | Nội dung, đơn vị, tần suất | Tệp/thư mục | Cách lấy | Vai trò |
|---|---|---|---|---|
| MRC EC Mỹ Tho (VN_019805), Tân Châu (VN_019803) | EC mS/m, 1 mẫu/tháng, giờ UTC+7 | `data/raw/ec/mrc/Conductivity.Water Quality@VN_0198xx_[...].csv`; kèm `data-request-e-receipt.pdf`, `data-use-license.pdf` | Yêu cầu dữ liệu MRC (thủ công, có biên nhận và giấy phép) | **Nhãn mục tiêu** |
| MRC EC Mỹ Thuận (VN_019804) | 451 mẫu, cờ `UNVERIFIED` | `data/external/tien_multisite_20261029_verified/019804_...csv` | MRC public API | Mốc nội suy giữa, mô hình khí tượng riêng |
| MRC public API | EC, nhiệt độ nước, mực nước | `scripts/fetch_mrc_public.py` → `data/external/mrc_20261014_network/` | `timeseries.api.mrcmekong.org`, không cần đăng nhập, không ghi DB | Đối chiếu, bổ sung |
| Kratie discharge (014901) | Lưu lượng m³/s, ngày, 22.161 bản ghi 1985–10/2026 | `data/external/mrc_kratie_discharge_20261029/` | MRC API `timeSeriesList` | Đặc trưng thủy văn chính |
| Mực nước Tân Châu (thủ công, `HGSTAFF`) | m, nhiều lần/ngày | `data/external/tien_manual_long_20261029/`, `tien_manual_2024_2026_20261029/` | MRC API | Đặc trưng thủy văn |
| ERA5 qua Open-Meteo | Mưa mm, nhiệt °C, gió m/s; ngày → tháng | `data/external/multivariate_weather/` (JSON theo khối 5 năm + `manifest.json`) | `scripts/update_multivariate_weather.py`, `archive-api.open-meteo.com`, `models=era5`, giấy phép CC-BY-4.0 | Đặc trưng khí tượng |
| RIA2 (bản tin quan trắc nuôi trồng) | EC µS/cm → mS/m; 10 điểm × 5 mẫu (08–11/2025) | `data/external/ec_recovery_20261011/` + chép tay bản tin số 12 | Tải bản tin PDF/DOC, nhập thủ công | **Chỉ tham khảo**, không vào mô hình; CRS không ghi trong bản tin |
| GloFAS v4 | Lưu lượng mô hình, NetCDF ngày | `data/raw/glofas/tanchau/` (117 tệp) | `data_collection/fetch_glofas.py`, Copernicus EWDS | Nợ kỹ thuật: lấy trung bình bbox; không dùng trong mô hình chính |
| DAHITI | Mực nước vệ tinh đo cao, không đều | `data/raw/dahiti/` | API DGFI-TUM | **Không phải triều**, không có datum đứng |
| FES2022b | Hằng số điều hòa triều | `data/raw/tide/fes2022b/` (35 tệp `VERIFIED_PAIR`) | AVISO THREDDS | Thử nghiệm đặc trưng triều |
| UHSLC Vũng Tàu | Mực nước triều | `data/raw/tide/uhslc/`, `data/external/uhslc_vungtau_hourly_20261030/` | `fetch_uhslc.py` | Đối chiếu FES |
| ONI, PDO (NOAA PSL) | Chỉ số khí hậu tháng | `data/external/climate_indices_20261029/` | `scripts/collect_climate_indices.py` | Thử nghiệm ENSO |
| Cống | 15 dòng kiểm kê, 12 có tọa độ; danh mục PDF | `data/raw/gis/gates/`, `data/raw/gates/dongthap_gate_catalog_2025.pdf` | Tài liệu tỉnh, số hóa | Lớp cống |
| Ranh giới hành chính | 1 tỉnh + 102 xã/phường, hiệu lực 01/07/2025 | `sql/03_admin_boundary_dong_thap.py` | GitHub `thanglequoc/vietnamese-provinces-database` | Lớp nền |
| Hình học sông | OSM, giấy phép ODbL | `data/biengioi/tien_river_corridor.geojson` | OpenStreetMap | Trục sông 175 km |

### 2.3 Câu cần nhớ

- Nhãn MRC mang cờ nguồn “Raw – Not Yet Reviewed” / “Unverified”; dự án **giữ nguyên cờ**, không tự nâng thành “đã kiểm định”.
- Tệp MRC chỉ ghi **ngày**; dấu giờ `00:00` không chứng minh giờ lấy mẫu thật. Điều này quan trọng vì EC hạ lưu dao động theo triều trong ngày.
- **Không có EC Mỹ Tho sau 12/2023** từ MRC, SIWRR hay sở ngành (đã tìm, ghi trong `docs/giai_phap_van_de_mo_2026-11-12.md`). Bản tin độ mặn g/L của tỉnh không thể dùng kiểm định EC vì khác đại lượng, khác điểm đo.

---

## 3. Xử lý dữ liệu

### 3.1 Kiến thức nền

- **Tổng hợp thời gian (temporal aggregation):** chuyển ngày → tháng bằng tổng (mưa), trung bình (nhiệt, gió, lưu lượng) hoặc trung vị (mực nước — bền với ngoại lai).
- **Ngưỡng đầy đủ dữ liệu:** tháng chỉ hợp lệ khi đủ số ngày; thiếu thì để NaN thay vì đoán.
- **Ngoại lai thống kê vs lỗi thật:** giá trị cực trị chưa chắc là lỗi. Xóa đỉnh mặn thật sẽ làm mô hình “đẹp” giả tạo.

### 3.2 Dự án làm gì

1. **Nhãn EC tháng** — `data/research/mrc_ec_monthly_samples.csv` (1379 dòng: Mỹ Tho 463, Tân Châu 464, Mỹ Thuận 451), dựng bởi `scripts/build_research_workspace.py`. Script **báo lỗi nếu một tháng có hơn 1 mẫu**, nên giá trị tháng chính là mẫu đơn lẻ của tháng đó.
2. **Kế hoạch làm sạch** (`docs/ec_cleaning_plan_2026-10-29.md`): 927/927 tháng khớp gói zip MRC gốc; không trùng, không âm, không vô hạn, không khoảng trống. **Không xóa giá trị cao**: `ec_for_model = ec_original`. Cờ `HIGH_VS_CALENDAR_MEDIAN_REVIEW_ONLY` đánh dấu 41/927 dòng có EC ≥ 3× trung vị cùng tháng lịch — **chỉ để rà soát**, không loại, không làm đặc trưng.
3. **Mẫu 692 mS/m ngày 15/03/2020** đã được chủ dự án xác nhận đúng. Giữ nguyên trong dữ liệu và điểm chấm.
4. **Khí tượng:** `backend/repositories/multivariate_inputs.py` tổng hợp ERA5 ngày → tháng (mưa tổng, nhiệt trung bình, gió trung bình của tốc độ trung bình ngày ở 10 m). Tháng chưa đủ ngày → NaN.
5. **Thủy văn:** `backend/repositories/hydrology_inputs.py` — lưu lượng tháng = trung bình các ngày; mực nước tháng = trung vị các trung vị ngày; **tháng hợp lệ khi ≥ 20 ngày có dữ liệu**. Tạo 5 biến:
   - `kratie_q_t2`: Q tháng t−2;
   - `kratie_q3_t2`: trung bình Q ba tháng kết thúc ở t−2;
   - `kratie_q_ratio_t2`: Q t−2 chia trung vị Q cùng tháng lịch của **tối đa 15 năm trước** (chỉ dùng quá khứ → không rò rỉ), cắt trong [0, 5];
   - `tc_stage_t2`, `tc_stage3_t2`: mực nước Tân Châu t−2 và trung vị ba tháng.
6. **Snapshot nghiên cứu** `data/research/workspace.json` + `workspace_manifest.json`: 13 trạm, 1428 quan trắc (464 + 463 + 451 MRC, 50 RIA2), có SHA-256 của chính tệp, của script dựng, của đầu vào. Ghi tệp theo kiểu nguyên tử (`.tmp` rồi thay thế).

### 3.3 Điểm yếu nên chủ động thừa nhận

- Pipeline cũ `process_data.py` lấy **trung bình** EC trong tháng và lệch đường dẫn (`data/interim` không tồn tại, thực tế là `data/staging/interim`). Đã được thay bởi nhãn ở mục 3.2.
- **Hai chính sách QA cùng tồn tại:** ETL v2 (`pipelines/etl/12_etl_update.py`) gắn 117 dòng `SUSPECT` (IQR 3,5 và bước nhảy), migration 11 đặt `SUSPECT allow_training=FALSE`; trong khi mô hình hiện hành học trên **toàn bộ** nhãn. Lý do: cờ SUSPECT dựa thống kê sẽ gắn đúng vào các đỉnh mặn thật — loại chúng là xóa đúng hiện tượng cần dự báo.
- `data/raw/tide/fes2022/README.md` cũ vẫn ghi “chưa có FES2022b”, mâu thuẫn với thư mục `fes2022b/`.

---

## 4. Nạp dữ liệu và xây dựng cơ sở dữ liệu

### 4.1 Kiến thức nền

- **PostgreSQL** là CSDL quan hệ, ACID (giao dịch nguyên tử, nhất quán, cô lập, bền vững). **PostGIS** là extension không gian: kiểu `geometry`, hàm `ST_*`, chỉ mục **GiST**.
- **SRID 4326 = WGS84** kinh/vĩ độ. Tính khoảng cách đúng theo mét phải ép sang `::geography` (dự án dùng `ST_DWithin` với `geography`, bán kính mặc định 50 km).
- **ETL** = Extract–Transform–Load. **Idempotent**: chạy lại không nhân đôi dữ liệu (nhờ UNIQUE và khóa SHA-256 của dataset).
- **Ràng buộc CHECK/UNIQUE** đẩy hợp đồng dữ liệu xuống tầng CSDL, không phụ thuộc vào mã ứng dụng.
- **Nguyên tắc quyền tối thiểu (least privilege):** ứng dụng chỉ dùng tài khoản có đúng quyền cần.

### 4.2 ETL `etl/etl_csv.py`

- Chỉ dùng thư viện chuẩn Python. Luồng: CSV → kiểm tra → tách dòng lỗi → CSV chuẩn hóa → SQL giao dịch → (tùy chọn) `psql`.
- Kiểm tra: đúng tiêu đề; mã trạm VN; `Parameter=Conductivity`; đơn vị `mS/m`; múi giờ +07; cờ O/E hợp lệ; ngày đầu tháng cho bảng tháng; độ ẩm 0–100; nhiệt min ≤ mean ≤ max.
- Khóa trùng: **mọi dòng** của khóa trùng đều bị loại (`DUPLICATE_KEY_ALL_ROWS_REJECTED`). Có bất kỳ dòng lỗi → `REJECTED_NO_DATABASE_WRITE` (thoát mã 2), không ghi gì.
- Mỗi lần chạy sinh `runs/<thời điểm_uuid>/` gồm `report.json`, `rejects.csv`, `normalized.csv`, `load.sql`.

### 4.3 Lược đồ (thứ tự file SQL)

1. `sql/00_preflight_v1.sql` — chỉ đọc: phiên bản PG, PostGIS, trùng tên.
2. `sql/01_core_schema_if_new.sql` — bảng nền: `data_source`, `admin_boundary` (MultiPolygon 4326, `valid_from/valid_to`), `salinity_station`, `irrigation_gate` (Point 4326), `water_level_observation` (bắt buộc `vertical_datum`), chỉ mục GiST.
3. `sql/01_toa_do_tram_MyTho_TanChau.sql` — tọa độ KML hai trạm (Tân Châu 105,2480164 E, 10,80062008 N; Mỹ Tho 106,3529997 E, 10,35912163 N); mặc định ROLLBACK.
4. `sql/02_irrigation_gate_dong_thap.sql` — 15 cống; **DTG013–015 chưa có tọa độ tin cậy** và bản SQL này còn dùng tâm giả (đã ghi là nợ kỹ thuật, không coi là cuối cùng).
5. `sql/03_admin_boundary_dong_thap.py` — `ST_MakeValid`, `ST_CollectionExtract(...,3)`, `ST_Multi`; xem trước rồi mới `--commit`.
6. `sql/04_research_workspace.sql` — schema `webgis_research`.
7. `sql/10_extend_realdata_schema.sql` — **lõi EC mới**: `source_dataset` (`sha256` UNIQUE, `source_row_count`, `metadata jsonb`), `measurement_site` (geom có thể NULL chỉ khi `location_status='UNKNOWN'`), `conductivity_observation` (CHECK đơn vị `mS/m`, giá trị ≥ 0 và hữu hạn, O/E, `quality_flag` ∈ UNVERIFIED/VALIDATED/SUSPECT/INVALID, UNIQUE(dataset, site, observed_at)), `monthly_feature` (khóa chính có `month_start`, CHECK ngày = 1).
8. `sql/11_import_supplied_real_data.sql`, `sql/12_verify_real_data.sql` — nạp và kiểm đếm, đối chiếu bằng `EXCEPT`.
9. `sql/20_alert_threshold_gate_rule_freshness.sql` — hồ sơ ngưỡng, quy tắc, độ tươi dữ liệu; tiêu đề ghi rõ không dùng để đóng/mở cống.
10. `sql/30_dss_storage.sql` — schema `dss_reference`: `ec_threshold_presets` (3 kịch bản), `multivariate_prediction_log` (UUID; CHECK `input_month = target_month − 2 tháng`; payload bắt buộc `deployment_ready=false`, `gate_decision_eligible=false`), `gate_simulation_drafts` (≤ 262.144 byte).
11. `sql/31_database_security.sql` — `webgis_security.audit_log` và trigger `SECURITY DEFINER` ghi nhật ký sau mỗi INSERT vào hai bảng DSS.
- Bổ sung: `scripts/sync_mythuan_to_postgres.py` (451 dòng, `time_precision='DATE_ONLY'`), `scripts/sync_ria2_to_postgres.py` (50 dòng); cả hai chạy thử trừ khi có `--apply`.
- **Thực tế DB đang chạy:** `/api/v1/stations` trả 3 trạm MRC; dataset Mỹ Tho `MRC_EC_MYTHO_2cee9c9c1cb8e29e`, 463 dòng, 463 `UNVERIFIED`, mẫu đầu 26/06/1985, cuối 15/12/2023.

### 4.4 Bảo mật CSDL

- `scripts/setup_security.py` tạo `webgis_reader` (chỉ SELECT, `default_transaction_read_only=on`) và `webgis_writer` (chỉ SELECT/INSERT trên 2 bảng nhật ký DSS). Cả hai: NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOBYPASSRLS, giới hạn 12 kết nối; `statement_timeout` 10 s, `lock_timeout` 3 s. Thu hồi quyền CREATE trên `public` từ PUBLIC.
- `backend/database.py`: kết nối `read_only=True`, mức cô lập REPEATABLE READ, múi giờ Asia/Ho_Chi_Minh, từ chối nếu là vai trò quản trị; mọi SQL tham số hóa (chống SQL injection).
- `scripts/apply_dss_storage.py`: advisory lock + bảng `schema_migrations(version, sha256)`; checksum lệch thì dừng.
- Mật khẩu ở `.env` (không commit). Chưa cấu hình TLS, reverse proxy, sao lưu cho triển khai từ xa — đây là giới hạn đã ghi trong `docs/database-security.md`.

### 4.5 Hai chế độ nguồn

- `postgres`: đọc trạm/EC từ `public.measurement_site`, `conductivity_observation`; mỗi trạm một dataset (ghim bằng biến môi trường hoặc lấy bản nhập mới nhất), **không trộn**. RIA2 chưa vào DB thì lấy từ snapshot với nhãn `reference_only`.
- `snapshot`: đọc `workspace.json` đã kiểm SHA-256.
- **Lỗi DB không tự chuyển sang snapshot** (`WorkspaceUnavailable` “No fallback was used”) — tránh người dùng tưởng dữ liệu tĩnh là dữ liệu sống.

---

## 5. Backend và API

### 5.1 Kiến thức nền

- **FastAPI**: framework Python, khai báo kiểu bằng Pydantic, tự sinh OpenAPI tại `/docs`. **Vite** build frontend tĩnh; **OpenLayers** vẽ bản đồ.
- Kiến trúc **modular monolith**: một tiến trình, chia lớp `api/` (HTTP) → `services/` (điều phối) → `domain/` (tính toán thuần) → `repositories/` (đọc nguồn).

### 5.2 Nhóm endpoint (đã đối chiếu `/openapi.json` đang chạy)

| Nhóm | Ví dụ | Ghi chú |
|---|---|---|
| Sức khỏe | `GET /api/v1/app-health`, `GET /api/v1/health` | `health` kiểm kết nối DB thật, giao dịch chỉ đọc |
| DB trực tiếp | `GET /api/v1/stations`, `/stations/{site_code}/datasets`, `/observations` | `limit` ≤ 1000, lọc ngày, cờ chất lượng, O/E |
| Workspace | `/api/v1/workspace/summary`, `/stations`, `/gates`, `/boundaries` | Cũng có bí danh `/api/v1/research/...` để tương thích |
| Mô phỏng bản đồ | `/simulation/corridor`, `/simulation/timeline`, `/simulation/frame?year_month=&open_below_ec=&close_above_ec=` | Frame trả `gate_decision_eligible=false`, `actuator_command=null` |
| Dự báo | `GET /api/v1/multivariate/catalog`, `/inputs`, `/evaluation`; `POST /predict` | `predict` không cần DB; cấm trường thừa |
| Lưu DSS (ghi) | `POST /multivariate/history`, `POST /gate-drafts` | Máy chủ **tự chạy lại** dự báo, không tin kết quả từ trình duyệt |
| Tiếp nhận | `/intake`, `/intake/coverage`, `/intake/measurement-points`, `/intake/observations` | Luôn `UNVERIFIED`, `training_eligible=false` |
| Cống | `/database-gates`, `/database-gates/{code}/candidate-stations?radius_km=` | Cần DB |

- **Bảo mật HTTP** (`backend/security.py`): yêu cầu ghi phải cùng nguồn (`sec-fetch-site`, Origin), tùy chọn khóa `X-API-Key` so bằng `hmac.compare_digest` (chống tấn công đo thời gian), header `nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store` cho API, TrustedHost, CORS chỉ GET/POST. Lỗi DB được làm sạch thành 503 với mã `DB_SCHEMA_MISMATCH`/`DB_PERMISSION_DENIED`/`DATABASE_ERROR`.
- Ghi DSS cần `WEBGIS_DSS_WRITES_ENABLED=true` và user riêng; nếu không trả 503 `DSS_WRITES_DISABLED`.

---

## 6. Mô hình dự báo

### 6.1 Kiến thức nền bắt buộc

- **Random Forest hồi quy:** tập hợp nhiều cây quyết định, mỗi cây học trên mẫu bootstrap (lấy mẫu có hoàn lại) và tập con đặc trưng ngẫu nhiên tại mỗi nút (**bagging**). Dự báo = **trung bình** các cây → giảm phương sai so với một cây.
  - `max_depth=8`: giới hạn độ sâu → chống quá khớp. `min_samples_leaf=3`: mỗi lá ít nhất 3 mẫu. `random_state=42`: tái lập.
  - **Hệ quả quan trọng:** RF **không ngoại suy** — giá trị dự báo nằm trong khoảng trung bình của nhãn đã thấy trong lá. Lá chứa đỉnh hiếm sẽ bị “kéo” bởi các mẫu thấp → **dự báo hụt đỉnh**. Đây là giải thích kỹ thuật cho 03/2020 (692 thực, 213,67 dự báo).
  - **Feature importance (impurity-based):** mức giảm phương sai trung bình nhờ biến đó qua các nút; thiên vị biến liên tục nhiều giá trị, không phải quan hệ nhân quả.
- **Độ trễ t−2 (lag):** dự báo tháng t chỉ dùng thông tin tháng t−2 vì dữ liệu tháng t−1 có thể chưa công bố tại ngày phát hành. Giả định: nguồn tháng X sẵn có sau **cuối tháng X + 5 ngày**.
- **Rò rỉ dữ liệu (leakage):** dùng thông tin chưa có tại thời điểm phát hành (tháng tương lai trong lag, chuẩn hóa/điền thiếu trên toàn bộ dữ liệu, chọn mô hình bằng tập kiểm tra) → điểm số đẹp giả.
- **Chỉ số:** `MAE = (1/n)Σ|y−ŷ|` — sai lệch trung bình, dễ hiểu theo mS/m. `RMSE = √((1/n)Σ(y−ŷ)²)` — phạt nặng lỗi lớn; RMSE ≫ MAE nghĩa là có vài lỗi rất lớn (đúng như kỳ 2019–2021: 57,81 vs 133,82).
- **Baseline (đối chứng):**
  - **Persistence** — lấy EC mới nhất **đã công bố** tại ngày phát hành.
  - **Frozen persistence** — giữ EC cuối trước khi mất dữ liệu.
  - **Seasonal naive** — EC cùng tháng năm trước.
  - **Climatology** — trung bình tháng lịch từ các nhãn có sẵn.
  - Mô hình chỉ có giá trị khi thắng baseline trên cùng giao thức.
- **Đánh giá theo thời gian:** không xáo trộn ngẫu nhiên (sẽ rò tương lai vào quá khứ). Dùng train trước–test sau, rolling origin, hoặc khóa EC.

### 6.2 Mô hình chính Mỹ Tho `20261108T_HYDROLOGY_PRIMARY_V1`

- Registry `data/models/multivariate_registry.json` trỏ tới `runs/multivariate_ec/mytho/20261108T_HYDROLOGY_PRIMARY_V1/{model.joblib, manifest.json}` cùng SHA-256 của cả hai.
- **Thứ tự 10 đặc trưng:** `rainfall_mm, temperature_degC, wind_source_units, month_sin, month_cos, kratie_q_t2, kratie_q3_t2, kratie_q_ratio_t2, tc_stage_t2, tc_stage3_t2`.
- **Mã hóa chu kỳ tháng:** `sin(2πm/12)`, `cos(2πm/12)` để tháng 12 và tháng 1 gần nhau trên vòng tròn.
- **Độ quan trọng:** mưa 0,341; tỷ lệ Q 0,231; Q 0,160; Q3 0,092; gió 0,041; mực nước 3 tháng 0,040; nhiệt 0,038; mực nước 0,035; sin 0,013; cos 0,010. Nhóm Kratie cộng lại ~0,48 → lưu lượng thượng nguồn là nhóm thông tin quan trọng nhất.
- Học trên **463 mẫu đến 12/2023**; thiếu `kratie_q_ratio_t2` 57 tháng và mực nước 12 tháng → imputer trung vị bên trong pipeline (fit trong từng lần huấn luyện).
- Manifest ghi: chọn bởi người dùng sau khi xem các kỳ hồi cứu, **không tuyên bố chọn mù**; `deployment_ready=false`.
- Mã đóng gói: `scripts/train_mytho_hydrology_primary.py` (có thể ghi artifact; **không** chạy khi khởi động web).

### 6.3 Đường chạy một dự báo trên web

1. Frontend gọi `GET /multivariate/inputs?station=MYTHO&target_month=...` lấy khí tượng và thủy văn tháng t−2.
2. `POST /multivariate/predict` → `backend/services/multivariate.py` kiểm đầu vào; thiếu thủy văn trả **422** “Chưa đủ lưu lượng Kratie hoặc mực nước Tân Châu tháng t−2…”; chọn tháng trong kỳ huấn luyện cũng bị chặn.
3. `backend/domain/multivariate_ec.py`:
   - đọc registry, kiểm SHA-256 model và manifest **mỗi lần gọi** (sai → “Model artifact checksum mismatch”);
   - kiểm thứ tự đặc trưng và phiên bản scikit-learn;
   - giá trị phải hữu hạn; EC âm/vô hạn → lỗi;
   - trả `gate_decision_eligible=False`, `quality_status='EXPERIMENTAL_SOURCE_EC_UNVERIFIED'`.
4. **P10–P90 giữa các cây:** chạy từng cây trong 300 cây, lấy phân vị 10/25/50/75/90. Đây là **độ phân tán giữa các cây**, **không phải khoảng tin cậy đã hiệu chuẩn**.
5. **Kết quả thật đo ngày 13/11/2026:** Mỹ Tho tháng 12/2026 (đầu vào tháng 10/2026) = **24,794 mS/m**; P10–P90 15,39–40,07; P50 18,29. Đầu vào: mưa 278,8 mm, nhiệt 28,09 °C, gió 1,526 m/s, Q Kratie 13.582 m³/s, Q3 28.984 m³/s, tỷ lệ 0,61, mực nước Tân Châu 2,38 m (trung vị 3 tháng 2,465 m). Ngày khả dụng thủy văn giả định 05/11/2026.

### 6.4 Mỹ Thuận và Tân Châu

- Chỉ 5 đặc trưng khí tượng + mùa, RF 300/8/3/42, `deployment_ready=false`, nhãn nguồn chưa nâng QA.
- Tân Châu (`tanchau/20261023T041813Z`, 464 tháng): MAE holdout RF 4,45, Persistence 4,86, **Seasonal naive 2,38**.
- Mỹ Thuận (`mythuan/20261104T_MYTHUAN_3STATION`, 451 tháng): MAE holdout RF 3,92, **Seasonal naive 1,89**.
- **Phải tự nói:** ở hai trạm thượng/trung lưu, EC thấp và rất đều theo mùa nên seasonal naive thắng RF. Hai mô hình này phục vụ việc đặt mốc nội suy, không phải trọng tâm khoa học.

---

## 7. Lịch sử phát triển mô hình (để trả lời “vì sao đi đến mô hình này”)

| Giai đoạn | Làm gì | Kết quả chính (MAE mS/m) | Quyết định |
|---|---|---|---|
| 0 — đầu 10/2026 | `run_forecast.py`: chia cố định train 1985–2020, val 2021, test 2022–2023; `run_monthly_ec.py`: walk-forward với EC trễ | Test: Persistence 9,15; RF 18,94; Seasonal naive 20,15. SARIMAX được import nhưng **chưa chạy** | Persistence thắng khi còn EC mới → cần bài toán “mất EC” |
| 1 — 23/10 | RF khí tượng 5 biến (mưa, nhiệt, gió t−2, sin/cos), registry v1 | Val 2019–21: RF 69,61 vs Persistence 93,39; holdout 2022–23: RF 18,32 vs Persistence 12,62 | Phục vụ tạm; mưa quan trọng nhất (0,625) |
| 2 — 29/10 | Backtest **as-of** (`scripts/backtest_asof_ec.py`): huấn luyện lại mỗi tháng, phát hành ngày 06 của t−1 | 0/240 dòng dùng dữ liệu sau ngày phát hành; RF 71,56 / 18,63 | Mốc đối chứng “RF cũ” |
| 3 — 29/10 | Thêm EC Tân Châu quá khứ; trộn RF + persistence | 2022–23 xấu đi 21,68 → 28,06 | Loại |
| 4 — 29/10 | **Thêm thủy văn** Kratie + Tân Châu (không EC quá khứ) | 58,68 / 13,52 (+5 ngày) | Bước tiến chính |
| 5 — 29/10 | XGBoost, LightGBM | XGB log 9,74 ở 2022–23 nhưng chỉ dự báo 378–379 ở tháng EC cao | Loại (không ổn định ở đỉnh) |
| 6 — 29–30/10 | **RF_compact** 100 cây, 8 biến | 2010–18: 14,76 vs Persistence 22,17; 2019–21: 50,87 vs 93,39; 2022–23: 11,07 vs 12,62 | Ứng viên nghiên cứu mạnh, chưa vào registry |
| 7 — 30/10 | ENSO, log, phân vị Q90, adaptive | Phát hiện báo cáo ngoài dùng persistence **không lọc ngày khả dụng** (52,19 sai vs 93,39 đúng) | Loại; bài học về rò rỉ trong baseline |
| 8 — 30/10 | Độ nhạy độ trễ công bố 0–70 ngày; độ bền theo năm; thủy văn ngày | RF_compact gộp 2019–23: 34,95 vs Persistence 61,08, thắng 39/60 tháng | Không chọn độ trễ bằng MAE |
| 9 — 04/11 & 08/11 | Thêm Mỹ Thuận; đóng gói **mô hình chính** khí tượng + thủy văn theo giao thức khóa EC | 57,81 / 16,57 / 12,19 | Đang phục vụ |

**Lý do mô hình chính có 300 cây/10 biến chứ không phải RF_compact:** mô hình chính được đánh giá và chọn trong **giao thức khóa EC** — đúng tình huống thực tế (không có EC Mỹ Tho mới sau 2023). RF_compact tốt trong giao thức rolling origin vốn **giả định EC vẫn cập nhật**. Hai giao thức không cùng bảng xếp hạng.

---

## 8. Giao thức đánh giá (phần hội đồng hay hỏi nhất)

### 8.1 Ba giao thức

| Giao thức | Câu hỏi trả lời | Cách làm |
|---|---|---|
| Train/test cố định | Mô hình khớp dữ liệu sau mốc chia ra sao? | Học đến mốc, chấm sau mốc; không xét ngày công bố |
| **Rolling origin / as-of** | Nếu phát hành mỗi tháng với dữ liệu đang có thì sai bao nhiêu? | Mỗi tháng đích t, phát hành ngày 06 của t−1, học lại trên dòng có `available_date ≤ issue_date`. EC giả định khả dụng +5 ngày (độ nhạy +35) |
| **Khóa EC (frozen EC)** | Nếu EC Mỹ Tho ngừng cập nhật lâu dài thì sao? | Fit **một lần** trước đoạn mất EC (24/36 tháng); đầu vào t−2 vẫn cập nhật hằng tháng; EC trong đoạn chỉ dùng chấm điểm |

Ví dụ giao diện ghi: kỳ 2021-01..2023-12 khóa EC đến 2020-11 tại lần phát hành đầu 2020-12-06.

### 8.2 Bảng điểm giao thức khóa EC (đã đối chiếu tab Dự báo đang chạy)

**Kỳ 2021–2023 (36 tháng):**

| Mô hình | MAE | RMSE |
|---|---:|---:|
| **RF khí tượng + thủy văn (chính)** | **16,569** | **31,21** |
| RF khí tượng t−2 + chu kỳ tháng | 28,312 | 64,232 |
| Giữ EC cuối cùng | 19,133 | 42,574 |
| Trung bình từng tháng trước khi mất dữ liệu | 21,532 | 42,575 |
| Lặp EC gần nhất của từng tháng | 172,458 | 292,083 |
| RF chỉ chu kỳ tháng | 21,863 | 42,842 |

Lệch lớn nhất: 03/2021, thực 191,5, dự báo 82,797.

**Kỳ 2019–2021 (36 tháng):**

| Mô hình | MAE | RMSE |
|---|---:|---:|
| **RF khí tượng + thủy văn (chính)** | **57,808** | **133,815** |
| RF khí tượng | 69,545 | 147,725 |
| Giữ EC cuối cùng | 80,196 | 191,229 |
| Trung bình từng tháng | 70,222 | 167,379 |
| RF chỉ chu kỳ tháng | 70,285 | 167,081 |

Lệch lớn nhất: 03/2020, thực 692, dự báo 213,665.

**Kỳ 2022–2023 (24 tháng):** RF chính 12,19/25,43 nhưng **giữ EC cuối 10,76/16,46 tốt hơn** — phải nói thẳng.

### 8.3 Cách diễn giải đúng

- Các kỳ **chồng lấn** và **đã được xem khi chọn phương án** → đây là **đánh giá hồi cứu**, không phải kiểm định mù.
- Không so điểm giao thức khóa EC với rolling origin.
- Seasonal naive dùng EC t−12 chỉ có 11/36 tháng trong kỳ khóa → không xếp hạng toàn kỳ.
- 04/2022: dự báo 100,04 khi thực 25,7 — **báo cao giả**. 03/2020 — **bỏ sót đỉnh**. Hai lỗi này được giữ trong bảng.

---

## 9. Nội suy không gian dọc sông

### 9.1 Kiến thức nền

- **Nội suy tuyến tính từng chặng (piecewise linear):** giữa hai mốc (x₁, y₁), (x₂, y₂), giá trị tại x là `y = y₁ + (y₂ − y₁)·(x − x₁)/(x₂ − x₁)`.
- **Lý trình (chainage):** khoảng cách dọc trục sông tính từ đầu tuyến, không phải đường chim bay.
- **Nội suy thời gian:** lấp tháng thiếu bằng nội suy giữa hai tháng có số liệu; ở mép chuỗi dùng giá trị gần nhất.
- Phân biệt với **mô hình thủy lực** (giải phương trình Saint-Venant, khuếch tán–đối lưu mặn): dự án **không** có mô hình này.

### 9.2 Dự án làm gì

- Trục sông Tiền chuẩn hóa **175 km**, chia **35 đoạn × 5 km**; mốc **Tân Châu 0**, **Mỹ Thuận 85,2176**, **Mỹ Tho 125**, **cửa sông 175** (`backend/services/spatial_simulation.py`). Khoảng cách địa lý được co giãn riêng cho hai phần 0–125 và 125–175.
- **Biên cửa sông giả định, chưa hiệu chuẩn:** `EC_cửa = EC_MỹTho × k + 0,4 × max(0, EC_MỹTho − EC_TânChâu)`, với k = 6,0 vào tháng 12–4 (mùa khô), k = 1,5 các tháng còn lại. Mã ghi rõ: không có điểm biên mô phỏng nào là quan trắc.
- **Thiếu Mỹ Thuận** (13 tháng lịch sử) → fallback 2 trạm, **chỉ cho phép trước 2024-01**; từ 2024 trở đi bắt buộc đủ 3 mốc, nếu không trả lỗi 503.
- `backend/services/spatial_inputs.py` lấp tháng thiếu và **gắn cờ `imputed`**; giá trị lấp không thành mẫu MRC.
- **Nguồn từng tháng trên dòng thời gian:**
  - đến 12/2023: mẫu MRC (“Mẫu nguồn MRC”);
  - 2024–2026: ước tính hồi cứu từ khí tượng (`data/models/future_ec_forecast_2024_2026.csv`, bản nghiên cứu cũ); riêng Mỹ Tho được thay bằng **mô hình chính hiện hành** khi có đủ đầu vào;
  - các tháng xa hơn chưa có đầu vào t−2: **kịch bản trung vị cùng tháng 2010–2023** (`SEASONAL_SCENARIO`).
- **Ranh mặn (isohaline):** đánh dấu nơi EC quy đổi đạt 1 và 4 g/L, kèm km.
- **Kênh có cống:** màu kéo từ sông đến cống bằng EC nội suy tại lý trình của cống; **đoạn sau cống không tô** vì không có EC nội kênh.
- Phương pháp do API khai báo: `Piecewise 3-Station River-Axis Linear Interpolation & Empirical EC-Salinity Conversion (0.0064 g/L per mS/m)`, `tier: 2`.

### 9.3 Ví dụ kiểm được trên trang

Tháng 03/2016, kênh Xoài Hột (`GATE_TG_020`): lý trình 120,9 km, cách trục 0,88 km, EC từ sông tới cống **347,09 mS/m**, ngưỡng cây có múi 100/150 → “EC mô phỏng đạt hoặc vượt ngưỡng ngừng lấy của kịch bản”.

### 9.4 Lớp hoạt ảnh (commit `0cc62ca`)

- **Vệt sáng trên sông:** hướng ngược dòng khi mùa khô và EC ≥ ngưỡng ngăn mặn (`UPSTREAM_SALINE_INTRUSION`), ngược lại xuôi dòng. Nhãn trên trang: “hướng lan mặn/nước ngọt theo kịch bản EC; **không phải dòng chảy đo thực**” (`flow_basis = ILLUSTRATIVE_SEASON_AND_EC_PROXY`).
- **Hướng gió:** một vectơ vùng từ ERA5 tổng hợp tháng (ví dụ 04/2024: về Tây Bắc 2,4 m/s). Tháng chưa có ERA5 dùng **khí hậu hướng gió cùng tháng 2010–2023**, ghi “không phải dự báo gió tháng này”. Gió trên bản đồ **không** phải đầu vào mô hình.
- Tôn trọng `prefers-reduced-motion`; có nút tạm dừng.

---

## 10. Các phương pháp giảm sai số đã thử

**Nguyên tắc chung:** so cùng cohort, cùng giao thức; đọc `predictions.csv` từng tháng chứ không chỉ MAE tổng; đếm riêng bỏ sót EC ≥ 100 và báo cao giả. **Không** phương án nào dưới đây thay mô hình chính.

| Phương pháp | Bằng chứng | Kết quả | Vì sao chưa dùng |
|---|---|---|---|
| Thêm thủy văn vào RF khí tượng | `outputs/frozen_ec_remedies_20261108/` | Tốt hơn RF khí tượng cả 3 kỳ | **Đã chọn** làm mô hình chính |
| Thêm EC Mỹ Thuận/Tân Châu | `outputs/frozen_ec_followup_20261108/` | RMSE 2021–23 31,21 → 29,59 nhưng 2019–21 tăng lên 136,58; 2022–23 lên 28,09 | Không ổn định; EC thượng lưu không phản ánh đỉnh hạ lưu (34 tháng Mỹ Tho ≥ 100 thì Mỹ Thuận chưa lần nào ≥ 100) |
| Ridge, Ridge + RF phần dư | cùng thư mục | Ridge+RF RMSE 2022–23 21,92 nhưng MAE tăng, bỏ sót thêm đỉnh | Không thắng đồng thời các tiêu chí |
| RF mịn, Huber GB, tăng trọng số EC cao, thiếu hụt lưu lượng | `outputs/ec_error_reduction_20261108/` (rolling origin) | RF_fine 2019–21 51,71 → 49,40 nhưng 2022–23 12,01 → 13,88 | Đổi chỗ lỗi, 692 vẫn thấp |
| Đặc trưng triều FES theo cửa sổ | `outputs/ec_tide_windows_20261108/` | 2021–23 16,57 → 15,59; 2019–21 57,81 → 57,93; 03/2020 chỉ 229,86 | FES2022b phát hành sau thời điểm hồi cứu; không biết giờ lấy mẫu |
| Chuyển mạch Q thấp (Q < 0,85) | `outputs/ec_math_physics_20261108/` | 2019–21 57,81 → 56,19 nhưng bỏ sót EC ≥ 100 tăng 2 → 3; 02/2020 thực 558, dự báo 85,74 | Tăng bỏ sót |
| RF log + smearing | cùng thư mục | Không ổn định | — |
| Thủy văn ngày gần phát hành | cùng thư mục | 2019–21 xấu đi 57,81 → 64,82 | Loại |
| Khoảng trên mùa khô | cùng thư mục | Bao phủ 10/15 tháng (66,7%) | Không phải trần an toàn |
| **Conformal trực tuyến** (12/11, chưa commit) | `scripts/experiment_ec_conformal_20261112.py`, `outputs/ec_conformal_20261112/` | Mục tiêu phủ 90%: 2019–21 đạt 30–31/36, 2022–23 22–23/24; **mọi phương pháp trượt 02 và 03/2020**; dải mùa khô rộng ~165 | Đề xuất hiển thị dải theo mùa, ghi rõ “không phải cận an toàn” |
| **Rủi ro đỉnh / phân loại P(EC ≥ 150)** (12/11, chưa commit) | `scripts/experiment_ec_peak_risk_20261112.py`, `outputs/ec_peak_risk_20261112/` | Brier 2019–21: RF phân loại 0,072 vs khí hậu 0,122, nhưng thua ở 2 kỳ còn lại; 02/2020 chỉ được xác suất 0,08–0,35. Thủy văn chậm +35 ngày làm MAE 2021–23 tăng 16,57 → 24,61 | Không triển khai; cho thấy mô hình **nhạy với độ trễ công bố thủy văn** |

### 10.1 Kiến thức nền cho bảng trên

- **Conformal prediction:** dùng phân phối sai số quá khứ (điểm “không phù hợp”) để dựng khoảng có xác suất phủ danh nghĩa 1−α, chỉ cần giả định **trao đổi được (exchangeability)**. Chuỗi thời gian vi phạm giả định này → dùng biến thể trực tuyến, **ACI** (Gibbs & Candès, điều chỉnh α theo phản hồi, γ = 0,02). Dự án dùng điểm `|log1p(y) − log1p(ŷ)|` và α = 0,1.
- **Brier score** = trung bình (p − o)², với o ∈ {0,1}; càng nhỏ càng tốt; so với xác suất khí hậu.
- **Huber loss:** bình phương khi sai số nhỏ, tuyến tính khi lớn → bớt nhạy ngoại lai.
- **Smearing (Duan):** hiệu chỉnh độ chệch khi dự báo trên thang log rồi đổi ngược.

### 10.2 Kết luận khoa học cần thuộc

> Đã thử hơn 10 hướng trên các kỳ đã xem; không hướng nào cải thiện đồng thời mọi kỳ mà không tăng bỏ sót đỉnh. Tiếp tục tinh chỉnh trên dữ liệu đã xem có nguy cơ quá khớp vào lịch sử. Bước tiếp theo đúng là **thu EC mới sau 2023** và **lịch công bố thật** để kiểm định mù.

---

## 11. Trang WebGIS thực tế (5 tab)

| Tab | Nội dung chính | Kiến thức đi kèm |
|---|---|---|
| **Tổng quan** | Huy hiệu nguồn “PostgreSQL”; nút “Kiểm tra PostgreSQL”; thẻ: 50 mẫu RIA2, 13 điểm, 1428 số đo, quan trắc gần nhất 11/11/2025 (RIA2), 3 trạm dự báo; 4 kịch bản nhanh; bảng EC gần nhất 8/13 trạm, ghi rõ “không phải EC hiện thời” | Ngày mẫu khác nhau giữa trạm |
| **Quan trắc** | Bản đồ OpenLayers; EC/g/L; cặp ngưỡng; hướng mô phỏng, hướng gió, hoạt ảnh; chọn kênh có cống; nền sáng/tối/vệ tinh; dòng thời gian 1985-06 → 2027-11; nút nhanh: đỉnh mặn 03/2016, mùa lũ 10/2022, mùa khô 04/2024; cắt dọc sông; đối chiếu ngưỡng; tra cứu lịch sử PostgreSQL | Nội suy, ngưỡng kịch bản, O/E |
| **Dự báo EC đa biến** | Chọn trạm/tháng, đầu vào lưu trữ hoặc tự nhập; P10–P90; bảng đối chiếu cây trồng; độ quan trọng; tải JSON/CSV; đưa lên bản đồ; chuyển sang kiểm tra cống; kiểm chứng khóa EC với 3 kỳ và độ trễ 5/35 ngày; lịch sử dự báo đã lưu | RF, t−2, giao thức đánh giá |
| **Chất lượng dữ liệu** | 640 dòng tệp nguồn, 47 trạm, 890 giá trị giữ rà soát — **chưa xác minh**, không vào huấn luyện; ước tính EC hồi cứu từ khí tượng | Phân biệt dữ liệu đo và dữ liệu đang rà soát |
| **Hồ sơ cống** | Phần A: ngữ cảnh dự báo chiếu về lý trình cống; Phần B: EC và mực nước đo hai phía, thời điểm, người đo, trạng thái cơ khí, xác nhận cùng hệ cao độ → 3 kết luận | Quy tắc kỹ thuật, con người quyết định |

### 11.1 Quy tắc rà soát cống `TECH_SCREENING_RULE_V1.0` (`frontend/src/shared/gate-intake-rules.js`)

- EC ngoài sông ≤ **156,25 mS/m** (≈ 1 g/L ÷ 0,0064); EC trong đồng ≤ **125 mS/m**.
- Chênh mực nước ngoài − trong **ΔH ≥ 0,05 m** (nước tự chảy vào đồng).
- Bắt buộc xác nhận hai mực nước **cùng hệ cao độ**; trạng thái cơ khí `READY`; có người đo/nguồn.
- **Độ tươi mẫu:** ≤ 6 giờ thường; ≤ 2 giờ khi **cảnh giác cao**. Cảnh giác cao khi dự báo Mỹ Tho ≥ **P90 tham chiếu 60,42 mS/m** (P90 của tập huấn luyện ban đầu thí nghiệm RF_compact, `high_ec_metrics`; mặc định khi không có mốc khác — P90 toàn chuỗi 463 mẫu là 68,52), hoặc EC chiếu tại cống ≥ 80% × 156,25 = **125**, hoặc ngữ cảnh đã bật cờ.
- **Thứ tự kết luận:** có mục thiếu/quá hạn → “Cần bổ sung hoặc đo lại”; có mục không đạt → “Chưa phù hợp để lấy nước”; tất cả đạt → “Đề nghị xem xét lấy nước” (có hạn hiệu lực bằng hạn của mẫu).
- Kết quả luôn có `requiresOperatorReview: true`, `actuatorCommand: null`. **Dự báo không bao giờ thay số đo hiện trường.**

---

## 12. Kiểm thử và tái lập

- **Đã chạy ngày 13/11/2026:** `node --test tests/*.test.mjs` → **156/156 đạt** (21 tệp test frontend). Bộ Python: **110/116 đạt**; 6 test lệch vì test/bằng chứng cũ chưa cập nhật theo mã (chi tiết ở mục F của `02_kich_ban_demo.md`). Cần sửa trước khi tuyên bố “toàn bộ test đạt”.
- Test Python bao gồm: chống rò rỉ của giao thức khóa EC, nạp model kiểm hash, mô hình chính dùng đúng thủy văn của nghiên cứu, bảo mật API key/ghi từ trình duyệt, hợp đồng frame mô phỏng.
- **Tái lập:** mọi thí nghiệm có `predictions.csv`, `metrics.csv`, `manifest/protocol.json` với hash nguồn; chuỗi băm 3 tầng registry → manifest → predictions.

---

## 13. Giới hạn và hướng phát triển (nói trước khi bị hỏi)

1. **Không có EC Mỹ Tho sau 12/2023** → chưa kiểm định mù. Cần thu thập, khóa tiêu chí trước khi xem kết quả, chấm riêng mùa khô, đỉnh, bỏ sót, báo cao giả.
2. **Lịch công bố dữ liệu** (ERA5, Kratie, Tân Châu, EC) là giả định +5 ngày; thử nghiệm cho thấy thủy văn chậm +35 ngày làm sai số tăng mạnh.
3. **Nhãn là mẫu đơn lẻ trong tháng**, không có giờ lấy mẫu, chưa rõ bù nhiệt.
4. **RF hụt đỉnh** do bản chất trung bình và ít mẫu đỉnh.
5. **Bản đồ một chiều**: nội suy tuyến tính, biên cửa sông giả định; không có mô hình thủy lực; không có EC nội kênh; khoảng cách trạm–cống không chứng minh liên thông thủy lực.
6. **Cống:** 3 cống chưa có tọa độ tin cậy; màu cống không phải trạng thái đóng/mở.
7. **Hướng phát triển** (`docs/de_xuat_chuc_nang_mo_rong_2026-11-12.md`): bảng `forecast_issue`/`forecast_score` bất biến để tự chấm dự báo khi có EC mới; nhập số đo hiện trường; nhật ký vận hành cống; bản tin; năm tương tự; kịch bản what-if; kiểm định leave-one-station-out; dải conformal theo mùa có nhãn rõ.

---

## 14. Bảng số liệu “học thuộc”

| Mục | Giá trị |
|---|---|
| Số mẫu EC MRC | Mỹ Tho 463, Tân Châu 464, Mỹ Thuận 451 (tổng 1378); RIA2 50 |
| Kỳ nhãn Mỹ Tho | 06/1985 – 12/2023, mẫu cuối 15/12/2023 |
| Đỉnh Mỹ Tho | 841 (04/1998); 692 (03/2020, đã xác nhận đúng) |
| Số tháng Mỹ Tho ≥ 150 / ≥ 620 | 26 / 4 |
| Mô hình chính | RF 300 cây, sâu 8, lá 3, seed 42, 10 biến t−2 |
| MAE/RMSE khóa EC | 2019–21: 57,81/133,82 · 2021–23: 16,57/31,21 · 2022–23: 12,19/25,43 |
| Persistence 2022–23 | 10,76/16,46 (tốt hơn RF chính ở kỳ này) |
| Dự báo 03/2020 | 213,67 vs thực 692 |
| Báo cao giả 04/2022 | 100,04 vs thực 25,7 |
| Trục sông | 175 km, 35 đoạn × 5 km; mốc 0 / 85,2 / 125 / 175 km |
| Biên cửa sông | ×6,0 mùa khô (12–4), ×1,5 mùa mưa, + 0,4 × chênh Mỹ Tho − Tân Châu |
| Quy đổi tham khảo | g/L ≈ 0,0064 × EC (mS/m) |
| Rà soát cống | EC ngoài ≤ 156,25; trong ≤ 125; ΔH ≥ 0,05 m; mẫu ≤ 6 h (≤ 2 h khi cảnh giác); P90 = 60,42 |
| Thủy văn tháng hợp lệ | ≥ 20 ngày; khả dụng giả định cuối tháng + 5 ngày |
| Tỷ lệ Q | so với trung vị cùng tháng tối đa 15 năm trước, cắt [0, 5] |
| Dự báo demo 12/2026 | Mỹ Tho 24,794 mS/m; P10–P90 15,39–40,07 |

---

## 15. Thuật ngữ nhanh

- **Anchor (mốc neo):** trạm có giá trị dùng làm điểm cố định cho nội suy.
- **As-of / issue date:** ngày phát hành dự báo; chỉ dùng dữ liệu có trước ngày đó.
- **Bootstrap / bagging:** lấy mẫu có hoàn lại / trung bình nhiều mô hình học trên các mẫu đó.
- **Chainage (lý trình):** khoảng cách dọc tuyến.
- **Cohort:** cùng tập tháng chấm điểm.
- **Datum (hệ cao độ):** mặt quy chiếu để so mực nước; khác datum thì không trừ được.
- **ERA5:** tái phân tích khí hậu của ECMWF; số liệu “hoàn chỉnh” có độ trễ phát hành.
- **Frozen EC:** khóa EC — giả lập mất nhãn dài hạn.
- **GiST:** chỉ mục cây tổng quát cho dữ liệu không gian.
- **Hindcast / hồi cứu:** chạy dự báo cho quá khứ để chấm điểm.
- **Imputation:** điền thiếu (ở đây là trung vị, fit trong tập huấn luyện).
- **Leakage:** rò rỉ thông tin tương lai.
- **Manifest:** tệp mô tả lần chạy: tham số, nguồn, hash, điểm số.
- **O/E:** Observed / Estimated.
- **Persistence:** dự báo bằng giá trị đã biết gần nhất.
- **Registry:** tệp chọn artifact đang phục vụ cho từng trạm.
- **SRID 4326:** hệ tọa độ WGS84.
- **t−2:** đặc trưng lấy từ hai tháng trước tháng đích.
