# Ổn định vận hành và tính năng tương tác — Implementation Plan

> **Bản đồng bộ 14/11/2026:** `docs/ke_hoach_khac_phuc_danh_gia_2026-11-14.md` là quyết định phạm vi/phương pháp. Các bước Task 8 và Task 10 bên dưới là backlog sau giai đoạn lõi, không thuộc cam kết 1–2 tuần. Chưa triển khai mã hay migration bằng việc sửa plan này.

**Goal:** Trong 1–2 tuần, sửa test/bằng chứng, lưu Mỹ Thuận, cache, pool và quy tắc cống; tạo khung sổ phát hành dự báo cùng phiếu thực địa có kiểm duyệt. Cảnh báo điểm quan tâm và what-if cống là backlog tùy chọn. Chưa tuyên bố có sai số vận hành khi chưa có nhãn EC tháng đủ điều kiện.

**Architecture:** Giữ modular monolith FastAPI (`api/ → services/ → domain/ → repositories/`), frontend Vite + OpenLayers (không phải Leaflet — dự án dùng `ol` 6.15). Mọi dữ liệu mới nằm trong schema `dss_reference` mới bằng migration có checksum như `sql/30_dss_storage.sql`; không ghi vào bảng quan trắc `public.*`. Quy tắc nghiệp vụ thuần nằm ở `backend/domain/`, kiểm thử offline không cần DB.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, psycopg 3, PostgreSQL 17 + PostGIS, scikit-learn 1.9.1 (model sẵn có), Vite 5, OpenLayers 6, `node --test`, `unittest`.

**Spec:** Yêu cầu người dùng ngày 14/11/2026 (bottleneck + roadmap 1–2 tuần + ≥3 tính năng tương tác có workflow UI → FastAPI/PostGIS → DB). Nền tảng: `docs/on_tap_hoi_dong_2026-11-13/01_he_thong_kien_thuc.md`, `CLAUDE.md`, `docs/de_xuat_chuc_nang_mo_rong_2026-11-12.md`.

---

## Phần I. Đánh giá thẳng thắn: điểm nghẽn và lỗ hổng logic

Mỗi mục ghi **bằng chứng đã kiểm** (13–14/11/2026) và **hậu quả khi vận hành thật**.

### I.1 Điểm nghẽn hiệu năng / vận hành

| # | Vấn đề | Bằng chứng | Hậu quả thực tế |
|---|---|---|---|
| B1 | `monthly_inputs()` tính lại toàn bộ chuỗi 1985→2027 **mỗi request**, không cache | `curl` `/simulation/frame` 1,83–2,03 s mỗi lần, kể cả tháng lặp lại; `/simulation/timeline` 1,95 s; lần đầu trong tiến trình mới ~10,9 s (đo trực tiếp `monthly_inputs()`) | Kéo thanh trượt hoặc “Phát chu kỳ” gửi một request ~2 s mỗi tháng; 5 người dùng đồng thời là xếp hàng. Đây là nghẽn số 1. |
| B2 | `uvicorn.run(app, host='127.0.0.1', port=...)` — 1 tiến trình, chỉ nghe localhost | `run_webgis.py:57-58` | Không phục vụ được cán bộ ở máy khác; một request CPU nặng (frame, dự báo) chặn các request khác. |
| B3 | Kết nối DB mở mới cho mỗi request, không pool | `backend/database.py` `read_connection()`; `dss_storage.write_connection()` dùng `psycopg.connect` | Tăng tải sẽ tăng độ trễ và có thể chạm `CONNECTION LIMIT 12` của role. |
| B4 | Dữ liệu đầu vào cập nhật **thủ công** (ERA5, Kratie, Tân Châu) | `scripts/update_multivariate_weather.py`, các thư mục `data/external/*_20261029/` có ngày cố định | Hết dữ liệu là dự báo tháng mới trả 422; không có cảnh báo “dữ liệu sắp cũ” cho quản trị. |
| B5 | Bộ test Python 12 phút, 6 test lệch | `tmp/pytest_full_20261113.log`: 110/116 | Không dùng được làm cổng CI; người sau không phân biệt lỗi mới với lỗi cũ. |

### I.2 Lỗ hổng logic / dữ liệu

| # | Vấn đề | Bằng chứng | Hậu quả |
|---|---|---|---|
| L1 | **Không lưu được dự báo Mỹ Thuận** | DB thật: `multivariate_prediction_log_station_key_check` chỉ cho `MyTho`,`TanChau`; `check1` ghép site cũng chỉ 2 trạm; trong khi `backend/domain/multivariate_ec.py:18-19` phục vụ `MYTHUAN`. DB hiện có 15 bản Mỹ Tho, 1 Tân Châu, 0 Mỹ Thuận | Người dùng bấm “Lưu” với Mỹ Thuận nhận 503 `DSS_DATABASE_UNAVAILABLE` (lỗi CHECK 23514 rơi vào nhánh “else”) — thông báo sai bản chất. |
| L2 | Lỗi ràng buộc DB bị dán nhãn “không truy cập được kho” | `backend/services/dss_storage.py` `storage_errors`: chỉ map `42P01/42703/3F000/42501` | Mọi vi phạm CHECK/UNIQUE hiện ra như mất kết nối → chẩn đoán sai. |
| L3 | Dự báo không có “sổ phát hành” bất biến; không ai chấm điểm khi EC mới về | `multivariate_prediction_log` chỉ lưu khi người dùng bấm, có thể lưu nhiều lần cùng tháng; không bảng điểm | Không thể chứng minh sai số vận hành thật — đúng lỗ hổng khoa học lớn nhất của dự án. |
| L4 | Giả định “cuối tháng + 5 ngày” được **mã hóa cứng** nhưng không có cảnh báo khi giả định sai | `hydrology_inputs.py`; thử nghiệm 12/11: thủy văn +35 ngày làm MAE 2021–23 16,57 → 24,61 | Khi nguồn trễ thật, hệ thống vẫn chạy với tháng sai hoặc từ chối mà không giải thích lịch nguồn. |
| L5 | Mốc Tân Châu/Mỹ Thuận tương lai dùng RF thua seasonal naive trên holdout cũ | Registry: RF 4,45 vs SN 2,38 (TC); 3,92 vs 1,89 (MT) | Seasonal naive cần EC cùng tháng năm trước và không dùng được từ 2025 khi chuỗi EC dừng 12/2023. Ứng viên đúng là climatology trung vị/trung bình theo tháng, chấm theo giao thức khóa EC và chỉ dùng nhãn khả dụng trước từng ngày phát hành. |
| L6 | Hai chính sách QA mâu thuẫn | Báo cáo QA có 927 dòng hai trạm (810 `VERIFIED`, 117 `SUSPECT`); mô hình chính `20261108T_HYDROLOGY_PRIMARY_V1` học **463 mẫu Mỹ Tho đến 12/2023**, gồm các dòng `SUSPECT` | Cả 26 dòng Mỹ Tho EC ≥150 đều `SUSPECT`; loại theo cờ thống kê sẽ xóa cực trị cần dự báo. Giữ mặc định, chỉ loại khi có bằng chứng lỗi kỹ thuật. |
| L7 | P90 cảnh giác cao 60,42 là hằng số từ thí nghiệm RF_compact cũ | `frontend/src/shared/gate-intake-rules.js:29`, `forecast-map-overlay.js:4` | Mốc không gắn với mô hình đang phục vụ; P90 toàn chuỗi là 68,52. |
| L8 | Quy tắc cống chạy **ở client**; `/gate-evaluation` server là bản cũ | `gate-intake-rules.js`; giao diện không gọi `/gate-evaluation` | Kết quả rà soát không được máy chủ xác nhận; nếu sau này lưu/chia sẻ kết luận, client có thể gửi kết quả tùy ý. |
| L9 | Bằng chứng tái lập lệch script | `test_frozen_ec_remedies` hash `scripts/evaluate_frozen_ec_gap_remedies.py` lệch; `outputs/mythuan_three_station_20261104/source_snapshots/` thiếu tệp | Hội đồng yêu cầu tái lập sẽ không khớp. |
| L10 | Không xác thực người dùng; chỉ same-origin + API key tùy chọn | `backend/security.py` | Không thể mở cho người dân gửi dữ liệu: không biết ai gửi, không chống spam. |
| L11 | Người dùng chỉ **xem thụ động** | 5 tab hiện chỉ đọc, trừ lưu dự báo/nháp cống | Giá trị thực tiễn thấp: không có thông báo, không thu số đo thực địa, không kiểm chứng ngược. |

### I.3 Điều **không** nên làm (để giữ trung thực khoa học)

- Không đổi model phục vụ trong 2 tuần này: chưa có EC mới để kiểm định.
- Không biến kết quả mô phỏng cống thành lệnh; mọi bảng mới giữ `is_operational_rule=false`, `actuator_command` vắng mặt.
- Không đưa số đo người dân vào chuỗi EC MRC hay tập huấn luyện; chúng ở bảng riêng với trạng thái kiểm duyệt.

---

## Phần II. Roadmap 2 tuần

| Ngày | Task | Mục tiêu | Xử lý vấn đề |
|---|---|---|---|
| Tuần 1, N1 | Task 1 | Sửa 6 test lệch → suite xanh | B5, L9 |
| N1–N2 | Task 2 | Cache `monthly_inputs` + đo hiệu năng | B1 |
| N2 | Task 3 | Migration 32: cho phép Mỹ Thuận + map lỗi ràng buộc | L1, L2 |
| N3 | Task 4 | Pool kết nối + chạy LAN có cấu hình | B2, B3 |
| N3–N4 | Task 5 | Kiểm tra độ tươi nguồn + endpoint `/data-freshness` | B4, L4 |
| N5 | Task 6 | Đưa quy tắc cống lên server, endpoint tính không lưu, fixture JS/Python chung; chuẩn bị registry P90 mới nhưng chưa kích hoạt | L8, L7 |
| Tuần 2, N6–N8 | Task 7 + Task 9 | **Sổ phát hành** có slot `ON_TIME/MISSED/LATE` và **phiếu thực địa**; chốt tiêu chí nhãn trước phiếu đầu tiên. Có thể chưa có nhãn đủ điều kiện để chấm. | L3, L10, L11 |
| Sau phần lõi | Task 8 | Điểm theo dõi/cảnh báo EC | L11, tùy chọn |
| Sau phần lõi | Task 10 | Mô phỏng what-if cống (không tạo lệnh) | L11, tùy chọn |
| Sau 2 tuần | — | So RF với climatology theo tháng cho TC/MT (L5); chốt chính sách QA giữ `SUSPECT` (L6); cân nhắc Task 8/10 và xác thực mở rộng | Ngoài phạm vi lõi |

Ưu tiên đã duyệt: Task 1–3 trước, tiếp theo B3/Task 4 và L8/Task 6; Task 7 và Task 9 làm song song vì sổ phát hành cần nguồn nhãn mới. Task 5 chỉ kiểm độ tươi bằng nguồn hiện có, không tự động tải. Task 8/10 dời sau lõi. Trước bảo vệ chỉ chuẩn bị registry P90 mới, **chưa kích hoạt** hoặc đổi model đang phục vụ. Nếu đổi hành vi sau bảo vệ, cập nhật `docs/on_tap_hoi_dong_2026-11-13/` và demo.

---

## Phần III. Thiết kế 4 tính năng tương tác — workflow đầu–cuối

> Ghi chú công nghệ: dự án dùng **OpenLayers**, không phải Leaflet. Các luồng dưới đây dùng lớp `ol/layer/Vector` và sự kiện `map.on('singleclick')` đã có trong `frontend/src/features/observations-map.js`.

### A. Sổ phát hành dự báo + tự chấm điểm (Task 7)

**Giá trị:** tạo một lịch phát hành mù, có thể kiểm tra cả lần bỏ lỡ. Lịch `MONTHLY_D06_PREV` là 09:00 ngày 06 tháng `t−1` tại Asia/Ho_Chi_Minh cho tháng mục tiêu `t`. Nếu đầu vào thiếu hoặc lệnh không chạy đúng giờ, ghi `MISSED` với thời điểm phát hiện thật; bản bù là `LATE` và chấm riêng. Trong 1–2 tuần có thể chưa có nhãn EC tháng tương đương để tính sai số vận hành.

```
[Tab Dự báo] nút "Phát hành dự báo tháng" (quản trị)          [Tab Dự báo] khối "Sai số vận hành thật"
        │ POST /api/v1/forecast-issues  {target_month,schedule_code}   │ GET /api/v1/forecast-issues?station=&with_scores=true
        ▼                                                              ▼
backend/api/forecast_issues.py ── same_origin_write + X-API-Key   backend/api/forecast_issues.py
        │                                                              │
        ▼                                                              ▼
backend/services/forecast_issues.py                             services.list_issues()
  1. với mỗi trạm MYTHO/MYTHUAN/TANCHAU:                           │ JOIN forecast_score
     multivariate.predict({station,target_month,'ARCHIVE'})        ▼
  2. domain.forecast_issue.build_issue(prediction, issued_at)   Bảng: tháng · dự báo · EC thật · |sai số| · nguồn EC
  3. repo.insert_slot_event() — UNIQUE (station,target_month,schedule_code)
  4. repo.insert_issue() — tối đa một dự báo mỗi slot; lần 2 trả 409
        │
        ▼
dss_reference.forecast_slot (UNIQUE station+target_month+schedule_code)
  ├── forecast_slot_event: MISSED (lý do, detected_at thật)
  └── forecast_issue: ON_TIME hoặc LATE; UNIQUE slot_id, issued_at thật
        ▲
        │ scripts/score_forecast_issues.py --apply (chạy tay / lịch)
        │   đọc public.conductivity_observation (MRC mới)
        │   + dss_reference.field_measurement status='APPROVED' (Task 9)
        │     chỉ nếu đạt tiêu chí tương đương đã chốt trước phiếu đầu tiên
        │   domain.forecast_issue.score(issue, observation) → abs_error
        ▼
dss_reference.forecast_score (UNIQUE issue_id+label_protocol_version; observation_ref; obs_source)
```

**Quy tắc khoa học:** không bao giờ cập nhật `forecast_issue` sau khi phát hành; không ghi lùi `issued_at`. Bảng slot mang khóa lịch, bảng issue tham chiếu slot với `UNIQUE(slot_id)`; sự kiện `MISSED` vẫn còn khi có issue `LATE`. MAE chính chỉ dùng `ON_TIME`; `LATE` có báo cáo riêng. Điểm số chỉ dùng nhãn EC tháng đã được QA theo giao thức tương đương chốt trước, không chỉ dựa vào `observed_at` nằm trong tháng. Nếu không có nhãn đủ điều kiện, hiện “chưa có dữ liệu chấm”, không hiển thị MAE vận hành.

### B. Đăng ký cảnh báo EC theo điểm quan tâm (Task 8)

**Giá trị:** người dùng click một vị trí (vườn, cống) trên bản đồ, chọn cặp ngưỡng cây trồng, nhận danh sách tháng có rủi ro và trạng thái mỗi khi có frame/dự báo mới. Biến người xem thụ động thành người “theo dõi”.

```
[Tab Quan trắc] click bản đồ → thẻ point-inspection hiện EC đoạn sông
        │ nút "Theo dõi điểm này"
        ▼
Form: tên điểm · preset ngưỡng (50/80, 100/150, 120/200, tự nhập) · liên hệ (tùy chọn)
        │ POST /api/v1/watch-points  {name, lon, lat, open_below_ec, close_at_or_above_ec}
        ▼
backend/api/watch_points.py (same_origin_write, Pydantic: lon 104–107.5, lat 9.5–11.5)
        ▼
services.watch_points.create()
  1. repo: INSERT ... geom = ST_SetSRID(ST_MakePoint(lon,lat),4326)
  2. PostGIS: chiếu điểm lên trục sông → chainage_km, distance_to_axis_km
     (ST_LineLocatePoint trên dss_reference.river_axis hoặc dùng RiverAxis Python sẵn có)
  3. từ chối nếu distance_to_axis_km > 12 (cùng ngưỡng cảnh báo của point-inspection)
        ▼
dss_reference.watch_point (geom Point 4326, chainage_km, thresholds, created_at, is_operational_rule=false)

[Tab Quan trắc] lớp "Điểm theo dõi" + bảng "Cảnh báo của tôi"
        │ GET /api/v1/watch-points/{id}/alerts?from=2026-11&to=2027-05
        ▼
services.watch_points.alerts()
  với mỗi tháng: frame = spatial_simulation (đã cache, Task 2)
  ec = interpolate tại chainage_km → domain.watch_alerts.classify(ec, open, close)
  → [{month, ec_mS_m, level: SAFE|CAUTION|RISK, data_kind, basis}]
        ▼
Giao diện: dải màu theo tháng; nhãn data_kind (MRC / ước tính / kịch bản mùa)
```

**Giới hạn ghi rõ trên UI:** EC là nội suy đoạn sông, không phải tại vườn; “cảnh báo” là đối chiếu kịch bản, không phải khuyến cáo tưới. Gửi thông báo đẩy/SMS **ngoài phạm vi** (cần dịch vụ ngoài và xác thực).

### C. Phiếu số đo thực địa có kiểm duyệt (Task 9)

**Giá trị:** cán bộ nội bộ gửi số đo EC bằng bút đo cầm tay tại một điểm; người có API key duyệt; số đã duyệt hiện trên bản đồ như lớp riêng. Chỉ một tập con thỏa tiêu chí tương đương đã chốt trước mới có thể làm nhãn chấm dự báo tháng tại trạm; phiếu bất kỳ không tự thành nhãn MRC.

```
[Tab Chất lượng dữ liệu] nút "Gửi số đo thực địa" hoặc click bản đồ → "Gửi số đo tại đây"
Form: vị trí (click) · EC + đơn vị (mS/m | µS/cm | dS/m) · nhiệt độ nước °C (tùy chọn)
      · thời điểm (datetime-local, GMT+7) · vị trí đo: Trên sông | Nội đồng · thiết bị · người gửi
        │ POST /api/v1/field-measurements
        ▼
backend/api/field_measurements.py — same_origin_write, body ≤ 16 KiB, X-API-Key bắt buộc cho người gửi nội bộ
        ▼
domain.field_measurement.normalize(raw)
  - đổi đơn vị → mS/m (µS/cm ÷ 10; dS/m × 100)
  - từ chối: EC < 0 hoặc > 6000 mS/m; thời điểm tương lai > 10 phút; cũ hơn 365 ngày
  - gắn cờ (không từ chối): EC > 3 × trung vị lịch sử cùng tháng của trạm gần nhất → 'REVIEW_HIGH'
        ▼
repo.insert(...) status='PENDING', geom Point 4326, submitted_by, raw_payload jsonb
        ▼
dss_reference.field_measurement
        │
[Quản trị] GET /api/v1/field-measurements?status=PENDING
        │ POST /api/v1/field-measurements/{id}/review {decision: APPROVED|REJECTED, note}
        ▼
dss_reference.field_measurement_review (append-only; trigger audit_log)
        │
        ├──▶ GET /api/v1/field-measurements?status=APPROVED → lớp bản đồ "Số đo thực địa (đã duyệt)"
        └──▶ Task 7 scorer chỉ dùng nếu thỏa tiêu chí nhãn tháng đã chốt trước
```

**Ranh giới:** không ghi vào `public.conductivity_observation`, không vào huấn luyện; trạng thái duyệt là append-only (không UPDATE trạng thái, đọc bản review mới nhất). Trước khi nhận phiếu đầu tiên, lập tài liệu có ngày/phiên bản về bán kính quanh trạm, cửa sổ ngày, khung giờ, EC25 và cách quy đổi, hiệu chuẩn thiết bị, số mẫu tối thiểu và cách tổng hợp tháng. Duyệt phiếu xác nhận phép đo, chưa tự xác nhận nó tương đương nhãn mục tiêu.

### D. Mô phỏng what-if cống (Task 10)

**Giá trị:** cán bộ chọn cống, chọn tháng và giả định “mở/đóng” + EC nội đồng ban đầu, xem ước lượng EC nội đồng sau N ngày theo mô hình trộn đơn giản — để **so sánh kịch bản**, không ra lệnh.

```
[Tab Hồ sơ cống] khối "Thử kịch bản (không phải lệnh)"
Form: cống · tháng · trạng thái giả định OPEN|CLOSED · EC trong đồng ban đầu · tỷ lệ trao đổi/ngày r (0–0,5, mặc định 0,1) · số ngày N (1–30)
        │ POST /api/v1/gate-scenarios/preview  (không ghi DB)
        ▼
services.gate_scenarios.preview()
  ec_out = frame(tháng).gates[gate_code].ec_outside (Task 2 cache)
  domain.gate_scenario.simulate(ec_in0, ec_out, state, r, N)
     OPEN:   ec_in[t+1] = ec_in[t] + r·(ec_out − ec_in[t])
     CLOSED: ec_in[t+1] = ec_in[t]
  so với ngưỡng đang chọn → ngày đầu tiên vượt ngưỡng ngừng lấy (nếu có)
        ▼
Trả {series:[{day, ec_in}], first_exceed_day, assumptions:[...], actuator_command: null,
     is_operational_rule: false}
        │ nút "Lưu kịch bản" → POST /api/v1/workspace/gate-drafts (bảng sẵn có, schema_version 1)
        ▼
dss_reference.gate_simulation_drafts (đã có)
UI: biểu đồ 2 đường OPEN vs CLOSED, ghi "Mô hình trộn một bể, r giả định, chưa hiệu chuẩn".
```

---

## Global Constraints

- EC luôn ở đơn vị `mS/m`; tên trường `*_mS_m` / `conductivity_ms_per_m`. Không quy đổi g/L trong pipeline lưu trữ.
- Mọi bảng mới ở schema `dss_reference`; không INSERT/UPDATE/DELETE vào `public.*`.
- Migration mới là `sql/32_*.sql`, `sql/33_*.sql`…, áp dụng bằng script kiểu `scripts/apply_dss_storage.py` (advisory lock + bảng `dss_reference.schema_migrations` + checksum). Không sửa nội dung `sql/30_dss_storage.sql` đã áp dụng.
- Role: `webgis_reader` chỉ SELECT; `webgis_writer` chỉ SELECT/INSERT trên bảng append-only. Không cấp UPDATE/DELETE.
- Ghi dữ liệu: `Depends(same_origin_write)` + thêm đường dẫn vào `backend/security.py::WRITE_PATHS`.
- Mọi phản hồi liên quan cống: `is_operational_rule=false`, không có khóa lệnh điều khiển (hoặc `actuator_command: null`).
- Trước bảo vệ giữ nguyên registry đang phục vụ và artifact model; có thể chuẩn bị entry P90 mới nhưng chưa kích hoạt. Không đổi mô hình/ngưỡng trên trang trước khi cập nhật tài liệu ôn tập và kiểm chứng.
- Không commit `.env`, `.venv*`, `.claude/`, `outputs/ec_error_reduction_20261108/experiment_ec_error_reduction.original.py`.
- Lệnh test: `.venv\Scripts\python.exe -m unittest tests.<module> -v`; `node --test tests/<file>.test.mjs`; build `npm.cmd --prefix frontend run build`.
- Mỗi task kết thúc bằng commit riêng trên nhánh làm việc; không push khi chưa được yêu cầu.

## Review Focus

1. **Nhiều người cùng phát hành một slot** `(station,target_month,MONTHLY_D06_PREV)` → lần 2 trả 409; `MISSED` và một bản `LATE` có thể cùng tham chiếu slot. Test ở Task 7.
2. **Đơn vị EC thực địa nhập nhầm** (gõ 1500 với đơn vị mS/m trong khi thực ra là µS/cm) → không chặn được bằng đơn vị, nhưng phải gắn cờ `REVIEW_HIGH` khi > 3× trung vị cùng tháng; test ở Task 9 (`test_high_value_flagged_not_rejected`).
3. **Điểm theo dõi ở xa sông** (vườn 30 km trong nội đồng) → từ chối 422 với thông báo khoảng cách, không trả EC sông như thể đúng tại vườn; test ở Task 8 (`test_point_far_from_axis_rejected`).
4. **Cache bị cũ khi dữ liệu nguồn hoặc ngày địa phương đổi** → khóa gồm dấu nguồn/DB/model và ngày Asia/Ho_Chi_Minh; stale trả `cache_status: STALE`, `built_at`, hoặc lỗi nếu chuyển ngày làm sai điều kiện khả dụng. Test ở Task 2.
5. **Chấm điểm bằng quan trắc ngoài tháng đích, số đo chưa duyệt hoặc phiếu không tương đương** → bị loại; test ở Task 7/9.

---

### Task 1: Đưa bộ test Python về xanh

**Files:**
- Modify: `tests/test_spatial_simulation.py:178-193`
- Modify: `tests/test_model_loading.py:70-85`
- Modify: `tests/test_frozen_ec_remedies.py:71-78`
- Modify: `tests/test_mythuan_three_station.py:95-112`
- Create: `docs/evidence_drift_2026-11-14.md`
- Create: `scripts/check.ps1` (smoke test cục bộ; suite 12 phút chạy trước phát hành)

**Interfaces:**
- Consumes: `backend.services.spatial_inputs.monthly_inputs()`; `backend.repositories.workspace._postgres_bundle(bundle)`.
- Produces: smoke test xanh; suite đầy đủ không có FAIL/ERROR, các test bằng chứng chưa tái lập được phải ghi skip/lý do rõ và không dùng artifact đó làm bằng chứng chính.

- [ ] **Step 1: Sửa kỳ vọng Mỹ Tho 2024-04 trong `test_timeline_contains_drought_and_wet_season_frames`**

Mỹ Tho tháng ≥ 2024-01 lấy từ mô hình chính, không từ CSV. Thay kỳ vọng `forecast['MyTho']` bằng giá trị của `row['inputs']`/`boundary` có `model_version == '20261108T_HYDROLOGY_PRIMARY_V1'`:

```python
row = indexed['2024-04']
self.assertAlmostEqual(row['tan_chau_ec_mS_m'], forecast['TanChau'])
self.assertNotAlmostEqual(row['my_tho_ec_mS_m'], forecast['MyTho'], places=3)
self.assertEqual(row['my_tho_model_version'], '20261108T_HYDROLOGY_PRIMARY_V1')
```
Nếu khóa `my_tho_model_version` không có trong item timeline, đọc từ `simulation_frame('2024-04')['inputs']` thay vì thêm trường mới.

- [ ] **Step 2: Bổ sung `observations=[]` vào bundle giả trong `test_postgres_restores_reference_fields_without_promoting_geometry`**

`workspace._postgres_bundle(dict(stations=[fallback], sources=[], notes=[], observations=[]))`.

- [ ] **Step 3: Xử lý hai bộ bằng chứng lệch hash**

Ưu tiên tìm đúng phiên bản script gốc và tái tạo snapshot/manifest từ nguồn. Nếu không thể, test bằng chứng đó được `skipTest(...)` kèm lý do và ghi trong `docs/evidence_drift_2026-11-14.md` (tệp, hash manifest, hash hiện tại, commit đổi script). Artifact thiếu nguồn gốc **không dùng làm bằng chứng chính**; không sửa hash kỳ vọng để test xanh giả.

- [ ] **Step 4: Tạo `scripts/check.ps1` và chạy suite**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`
Expected: `OK (skipped=N)` với từng skip có hồ sơ, 0 failure, 0 error. `scripts/check.ps1` chạy nhóm smoke nhanh, không buộc chờ suite đầy đủ 12 phút mỗi lần sửa nhỏ.

- [ ] **Step 5: Commit**

```bash
git add tests/test_spatial_simulation.py tests/test_model_loading.py tests/test_frozen_ec_remedies.py tests/test_mythuan_three_station.py docs/evidence_drift_2026-11-14.md scripts/check.ps1
git commit -m "test: align stale expectations with served model and record evidence drift"
```

---

### Task 2: Cache `monthly_inputs` theo dấu nguồn

**Files:**
- Modify: `backend/services/spatial_inputs.py:225-345`
- Modify: `backend/repositories/workspace.py` (thêm `bundle_stamp()`)
- Test: `tests/test_spatial_inputs_cache.py`

**Interfaces:**
- Produces: `spatial_inputs.monthly_inputs() -> dict` (giữ nguyên chữ ký, nay cache); `spatial_inputs.source_stamp() -> tuple` gồm ngày Asia/Ho_Chi_Minh; `workspace.bundle_stamp() -> str` (snapshot: sha256 manifest; postgres: dấu dữ liệu của các dataset đang ghim). API frame/timeline kèm `cache_status` và `built_at`.

- [ ] **Step 1: Viết test**

```python
class MonthlyInputsCacheTests(unittest.TestCase):
    def test_second_call_hits_cache(self):
        with patch.object(spatial_inputs, '_monthly_inputs', wraps=spatial_inputs._monthly_inputs) as inner:
            spatial_inputs.monthly_inputs.cache_clear(); spatial_inputs.monthly_inputs(); spatial_inputs.monthly_inputs()
        self.assertEqual(inner.call_count, 1)
    def test_cache_invalidates_when_source_stamp_changes(self):
        with patch.object(spatial_inputs, 'source_stamp', side_effect=[('a',), ('b',)]), \
             patch.object(spatial_inputs, '_monthly_inputs', return_value={}) as inner:
            spatial_inputs.monthly_inputs.cache_clear(); spatial_inputs.monthly_inputs(); spatial_inputs.monthly_inputs()
        self.assertEqual(inner.call_count, 2)
    def test_month_rollover_is_part_of_stamp(self):
        self.assertIn(datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%Y-%m-%d'), spatial_inputs.source_stamp())
```

- [ ] **Step 2: Chạy test** — `.venv\Scripts\python.exe -m unittest tests.test_spatial_inputs_cache -v` → FAIL (`cache_clear` không tồn tại).

- [ ] **Step 3: Cài đặt**

`source_stamp()` trả tuple gồm: ngày hôm nay (Asia/Ho_Chi_Minh — vì `_future_boundaries` phụ thuộc `today`), `workspace.bundle_stamp()`, `(mtime_ns, size)` của `data/models/future_ec_forecast_2024_2026.csv`, `data/external/multivariate_weather/manifest.json`, các CSV thủy văn trong `hydrology_inputs`, `data/models/multivariate_registry.json`. Thêm `_cached(stamp)` bọc `@lru_cache(maxsize=2)` gọi `_monthly_inputs()`; `monthly_inputs()` gọi `_cached(source_stamp())` và expose `cache_clear = _cached.cache_clear`. Kết quả trả về phải là bản không bị sửa bởi caller: trả `copy.deepcopy` nếu `simulation_frame` có mutate (kiểm `spatial_simulation.py` trước; nếu không mutate thì không copy).

`lru_cache` đơn thuần không bảo đảm single-flight giữa các request. Bọc phần build bằng khóa theo stamp và kiểm tra cache lần hai sau khi lấy khóa. Lưu `built_at` cho bản đang dùng. Khi build lỗi, chỉ trả bản cũ nếu phản hồi ghi `cache_status: STALE`; riêng lúc đổi ngày làm thay tính khả dụng đầu vào tương lai thì trả lỗi thay vì kết quả hôm trước.

- [ ] **Step 4: Chạy test + đo** — test PASS; frame 2026-12 lần hai đặt mục tiêu < 0,3 s; giả lập đổi ngày, build lỗi, 5 request đồng thời, kiểm `STALE`/`built_at`. Chạy `tests.test_spatial_simulation` PASS.

- [ ] **Step 5: Commit** — `git commit -m "perf: cache monthly simulation inputs keyed by source stamp"`

---

### Task 3: Migration 32 — cho phép lưu dự báo Mỹ Thuận, phân loại lỗi ràng buộc

**Files:**
- Create: `sql/32_dss_prediction_stations.sql`
- Create: `sql/32_dss_prediction_stations_down.sql` (chỉ chạy nếu chưa có bản Mỹ Thuận)
- Create: `scripts/apply_dss_migration.py` (tổng quát hóa `apply_dss_storage.py`: tham số `--file sql/3x_*.sql --version 3x_name`)
- Modify: `backend/services/dss_storage.py` (`storage_errors`)
- Test: `tests/test_dss_storage_errors.py`, `tests/test_sql_migrations.py`

**Interfaces:**
- Produces: `scripts/apply_dss_migration.py --file <path> --version <name> [--apply]`; `23514`/`23503` → 422 `DSS_CONSTRAINT_VIOLATION`, `23505` → 409 `DSS_DUPLICATE`.

- [ ] **Step 1: Test phân loại lỗi**

```python
def test_check_violation_is_422_not_unavailable(self):
    err = psycopg.errors.CheckViolation();
    with patch.object(store, 'save_prediction', side_effect=err), patch.object(store, 'require_writes'):
        with self.assertRaises(WorkspaceError) as ctx: dss_storage.save_prediction(VALID_REQUEST)
    self.assertEqual(ctx.exception.status_code, 422); self.assertIn('DSS_CONSTRAINT_VIOLATION', ctx.exception.detail)
def test_unique_violation_is_409(self): ...  # tương tự với UniqueViolation, kỳ vọng 409 'DSS_DUPLICATE'
```
`patch.object(multivariate, 'predict', return_value=...)` để không chạy model.

- [ ] **Step 2: Test nội dung migration (offline, đọc file)**

```python
def test_32_extends_station_checks_to_mythuan(self):
    sql = Path('sql/32_dss_prediction_stations.sql').read_text('utf-8')
    self.assertIn("'MyThuan'", sql); self.assertIn("'MRC_VN_019804'", sql)
    self.assertIn('current_database()', sql); self.assertNotRegex(sql, r'(?i)\bdrop\s+table\b')
```

- [ ] **Step 3: Viết migration**

Guard `DO $$ BEGIN IF current_database() <> 'dongthap_gis' THEN RAISE EXCEPTION ...`. `ALTER TABLE dss_reference.multivariate_prediction_log DROP CONSTRAINT multivariate_prediction_log_station_key_check, DROP CONSTRAINT multivariate_prediction_log_check1, ADD CONSTRAINT prediction_station_key_check CHECK (station_key IN ('MyTho','TanChau','MyThuan')), ADD CONSTRAINT prediction_station_site_check CHECK ((station_key,site_code) IN (('MyTho','MRC_VN_019805'),('TanChau','MRC_VN_019803'),('MyThuan','MRC_VN_019804')));` (chỉ nới, không xóa dữ liệu). Sửa `storage_errors`: `23514|23503 → 422`, `23505 → 409`; mã khác phân loại theo nguyên nhân thực. Có migration ngược chỉ khi chưa có bản Mỹ Thuận; nếu đã có, giữ schema mới khi quay lui ứng dụng, không xóa dữ liệu.

- [ ] **Step 4: Chạy test** — hai module test PASS. Chạy `scripts/apply_dss_migration.py --file sql/32_dss_prediction_stations.sql --version 32_dss_prediction_stations` (không `--apply`) in kế hoạch + sha256. **Áp dụng thật chỉ khi người dùng đồng ý.**

- [ ] **Step 5: Commit** — `git commit -m "fix: allow saving My Thuan forecasts and classify DSS constraint errors"`

---

### Task 4: Pool kết nối và chế độ LAN có kiểm soát

**Files:**
- Modify: `backend/database.py`, `backend/repositories/dss_storage.py`
- Modify: `run_webgis.py:50-60`
- Modify: `requirements.txt` (thêm `psycopg-pool`)
- Test: `tests/test_database_pool.py`, `tests/test_run_webgis_args.py`

**Interfaces:**
- Produces: `database.read_connection()` giữ nguyên context-manager API, lấy từ `psycopg_pool.ConnectionPool(min_size=1, max_size=int(os.getenv('WEBGIS_DB_POOL_MAX','8')))`, `configure` đặt `read_only`, REPEATABLE READ, timezone và gọi `assert_application_role` một lần mỗi kết nối. `run_webgis.py --host <ip>`: mặc định `127.0.0.1`; host khác yêu cầu `WEBGIS_ALLOWED_HOSTS` chứa host đó và `WEBGIS_WRITE_API_KEY` khác rỗng, nếu không thì thoát mã 2 với thông báo.

- [ ] **Step 1: Test** — `test_pool_reuses_connections` (mock `ConnectionPool`, gọi `read_connection()` 3 lần → `getconn` 3 lần, `ConnectionPool` khởi tạo 1 lần); `test_lan_host_requires_api_key` (`parse_and_validate(['--host','0.0.0.0'])` với env rỗng → `SystemExit(2)`); `test_pool_max_respects_role_limit` (`WEBGIS_DB_POOL_MAX=20` → giới hạn về 10, vì role giới hạn 12).
- [ ] **Step 2: Chạy** → FAIL.
- [ ] **Step 3: Cài đặt** theo Interfaces; giữ `workers=1` (model cache trong tiến trình), dùng `uvicorn.run(..., host=args.host, timeout_keep_alive=5)`.
- [ ] **Step 4: Chạy** test mới + `tests.test_security` PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat: pooled DB connections and guarded LAN binding"`

---

### Task 5: Kiểm tra độ tươi nguồn dữ liệu

**Files:**
- Create: `backend/domain/data_freshness.py`, `backend/api/data_freshness.py`
- Modify: `backend/main.py` (include router `prefix='/api/v1'`)
- Modify: `frontend/src/features/overview.js` (thẻ “Độ tươi dữ liệu”)
- Test: `tests/test_data_freshness.py`, `tests/overview_freshness.test.mjs`

**Interfaces:**
- Produces: `data_freshness.assess(last_source_month: str, today: date, assumed_lag_days: int = 5) -> dict` trả `{last_source_month, next_target_month_supported, days_until_stale, status: 'FRESH'|'DUE'|'STALE', retrieved_at?, availability_basis}`. Quy tắc: tháng đích cao nhất dự báo được = `last_source_month + 2`; `STALE` nếu `today` > cuối (`last_source_month` + 1 tháng) + `assumed_lag_days`, tức nguồn đáng lẽ đã có tháng kế mà chưa có; `DUE` trong 7 ngày trước mốc đó. `GET /api/v1/data-freshness` trả mục cho `ERA5_MYTHO`, `ERA5_TANCHAU`, `ERA5_MYTHUAN`, `KRATIE_Q`, `TANCHAU_STAGE`, `MRC_EC_MYTHO` (MRC luôn `STALE` kèm `last_observation 2023-12-15`). `retrieved_at` chứng minh đã tải bản nguồn đó vào thời điểm ghi, không chứng minh ngày công bố đầu tiên; các dự báo trước khi lưu mốc này vẫn dựa trên giả định +5/+35 ngày.

- [ ] **Step 1: Test domain**

```python
def test_fresh_when_next_month_not_yet_due(self):
    r = assess('2026-10', date(2026, 11, 14)); self.assertEqual(r['status'], 'FRESH'); self.assertEqual(r['next_target_month_supported'], '2026-12')
def test_stale_after_lag(self):
    self.assertEqual(assess('2026-10', date(2026, 12, 6))['status'], 'STALE')
def test_due_within_7_days(self):
    self.assertEqual(assess('2026-10', date(2026, 11, 30))['status'], 'DUE')
```
- [ ] **Step 2: Chạy** → FAIL.
- [ ] **Step 3: Cài đặt** domain thuần + API đọc tháng cuối từ `get_monthly_weather(station)` và `hydrology_inputs` (tháng cuối đủ 20 ngày). UI: thẻ màu theo trạng thái, câu “Ngày khả dụng là giả định +5 ngày”.
- [ ] **Step 4: Chạy** Python + Node test PASS; build frontend.
- [ ] **Step 5: Commit** — `git commit -m "feat: report source freshness and next supported forecast month"`

---

### Task 6: Quy tắc rà soát cống ở server, đối chiếu với client

**Files:**
- Create: `backend/domain/gate_intake_rules.py`
- Create: `backend/api/gate_screening.py` (`POST /api/v1/gate-screening/evaluate`, không ghi DB)
- Create: `tests/fixtures/gate_intake_cases.json` (dùng chung Node + Python)
- Test: `tests/test_gate_intake_rules.py`, `tests/gate_intake_parity.test.mjs`
- Modify: `frontend/src/features/gate-intake-screening.js` (gọi server; hiển thị khác biệt nếu kết quả client ≠ server)

**Interfaces:**
- Produces: endpoint **tính không lưu** `evaluate(measurement: dict, profile: dict, forecast_context: dict | None, now_iso: str) -> dict` với `status ∈ {'ELIGIBLE_FOR_REVIEW','NOT_SUITABLE','INSUFFICIENT_OR_EXPIRED_DATA'}`, `checks`, `policy_version`, `input_hash`, `rule_profile_hash`, `requiresOperatorReview: True`, `actuatorCommand: None`. Dùng fixture chung JS/Python. `gate_simulation_drafts` tiếp tục chỉ lưu input/policy; khi mở nháp tính lại, không lưu kết quả. Trước bảo vệ giữ chính sách P90 hiện hành để demo không đổi; tạo entry/manifest P90 mới nhưng chưa kích hoạt. Khi kích hoạt sau bảo vệ, bỏ fallback 60,42; thiếu ngưỡng hợp lệ thì tuổi mẫu tối đa 2 giờ và hiển thị lý do.

- [ ] **Step 1:** Tạo fixture ≥ 8 ca (3 ca demo 13/11: EC 80/60 ΔH 0,15 tuổi 1 h → ELIGIBLE; EC ngoài 200 → NOT_SUITABLE; tuổi 8 h → INSUFFICIENT; thêm: ΔH = 0,05 biên → đạt; datum chưa xác nhận; FAULT; forecast Mỹ Tho 61 → giới hạn 2 h, mẫu 3 h → INSUFFICIENT; thời điểm tương lai).
- [ ] **Step 2:** Test Python `test_fixture_cases_match_expected` và Node `parity` gọi `evaluateIntake` của client cùng fixture; chạy → Python FAIL.
- [ ] **Step 3:** Cài domain Python theo đúng thứ tự ưu tiên của client; API Pydantic `extra='forbid'`, body ≤ 64 KiB; hash RuleProfile đã chuẩn hóa. Thêm test phiên bản chính sách hiện hành và phiên bản sau kích hoạt P90 để tránh đổi demo ngầm.
- [ ] **Step 4:** Hai test PASS; `tests/gate_intake_rules.test.mjs`, `tests/gate_intake_screening.test.mjs` vẫn PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat: server-side gate intake screening with client parity fixture"`

---

### Task 7: Tính năng A — Sổ phát hành dự báo và tự chấm điểm

**Files:**
- Create: `sql/33_forecast_issue.sql`
- Create: `backend/domain/forecast_issue.py`, `backend/repositories/forecast_issues.py`, `backend/services/forecast_issues.py`, `backend/api/forecast_issues.py`
- Create: `scripts/score_forecast_issues.py`
- Modify: `backend/main.py`, `backend/security.py::WRITE_PATHS` (thêm `/api/v1/forecast-issues`), `scripts/setup_security.py` (GRANT SELECT,INSERT cho writer trên 2 bảng mới)
- Modify: `frontend/src/features/multivariate-forecast.js` (khối “Sai số vận hành thật”)
- Test: `tests/test_forecast_issue.py`, `tests/forecast_issue_panel.test.mjs`

**Interfaces:**
- Consumes: `backend.services.multivariate.predict(payload: dict) -> dict` (sẵn có).
- Produces:
  - `dss_reference.forecast_slot(slot_id uuid PK, station_key, target_month date, schedule_code text, scheduled_at timestamptz, UNIQUE(station_key,target_month,schedule_code))`; lịch đầu tiên là `MONTHLY_D06_PREV` = 09:00 ngày 06 của tháng trước tháng mục tiêu, Asia/Ho_Chi_Minh.
  - `dss_reference.forecast_slot_event(event_id uuid PK, slot_id FK, event_type CHECK IN ('MISSED'), reason_code, detected_at timestamptz)` append-only; thiếu đầu vào hoặc không chạy lệnh đúng lịch vẫn để lại sự kiện `MISSED` với **thời điểm phát hiện thật**.
  - `dss_reference.forecast_issue(issue_id uuid PK, slot_id uuid FK UNIQUE, input_month date, model_version, model_sha256 char(64), data_version, predicted_ec_mS_m float8 ≥0, payload jsonb, issue_status CHECK IN ('ON_TIME','LATE'), issued_at timestamptz default clock_timestamp())`, CHECK `input_month = target_month − 2 months` thực hiện qua trigger do `target_month` ở slot. Slot có thể vừa có sự kiện `MISSED` vừa có **một** issue `LATE`; không UPDATE hoặc backdate issue. Cả ba trạm gồm `MyThuan`.
  - `dss_reference.forecast_score(score_id bigint identity PK, issue_id uuid FK, label_protocol_version, observation_ref, obs_source CHECK IN ('MRC','FIELD_APPROVED'), observed_ec_mS_m float8 ≥0, abs_error_mS_m float8, scored_at timestamptz, UNIQUE(issue_id,label_protocol_version))`; nhãn tháng được chọn/tổng hợp theo quy tắc công bố trước, không chấm mọi phiếu riêng lẻ rồi chọn kết quả đẹp.
  - `forecast_issue.build_issue(prediction: dict, issued_at: datetime) -> dict`; `forecast_issue.score(issue: dict, observation: dict) -> dict | None` (None nếu ngoài tháng đích hoặc nguồn không hợp lệ).
  - `POST /api/v1/forecast-issues {target_month,schedule_code:'MONTHLY_D06_PREV'}` → 201 với kết quả từng trạm; 409 nếu slot đã có issue; nếu đến lịch mà thiếu đầu vào, ghi `MISSED` và trả lý do 422 cho trạm đó; nếu gọi sau lịch, ghi `MISSED`/`JOB_NOT_RUN` nếu cần và issue (nếu có) là `LATE`. Không cho phát hành lùi tháng chỉ để cải thiện MAE.
  - `GET /api/v1/forecast-issues?station=&from=&to=&with_scores=true` → `{items:[{slot,events,issue?,score?}], summary:{on_time_n_scored,on_time_mae_mS_m,late_n_scored,late_mae_mS_m}}`; khi không có nhãn đạt chuẩn, MAE là `null`.

- [ ] **Step 1: Test domain**

```python
def test_build_issue_pins_model_identity(self):
    i = build_issue(PRED, ISSUED); self.assertEqual(i['model_sha256'], PRED['model_provenance']['model_sha256']); self.assertEqual(i['input_month'], '2026-10')
def test_score_ignores_pending_and_out_of_month(self):
    self.assertIsNone(score(ISSUE_2026_12, dict(OBS, observed_at='2027-01-02T08:00:00+07:00')))
    self.assertIsNone(score(ISSUE_2026_12, dict(OBS, obs_source='FIELD_PENDING')))
    self.assertIsNone(score(ISSUE_2026_12, dict(OBS, obs_source='FIELD_APPROVED', equivalent_monthly_label=False)))
def test_score_abs_error(self):
    self.assertAlmostEqual(score(ISSUE_2026_12, dict(OBS, observed_ec_mS_m=30.0))['abs_error_mS_m'], abs(30.0 - 24.794))
```
- [ ] **Step 2: Test service (mock repo)** — `test_second_issue_same_slot_conflicts` (repo ném `UniqueViolation` → 409); `test_missing_inputs_records_missed`; `test_late_issue_preserves_missed_event`; `test_job_not_run_uses_real_detection_time`; `test_late_scores_excluded_from_primary_mae`; `test_past_month_rejected`.
- [ ] **Step 3: Chạy** → FAIL.
- [ ] **Step 4: Cài đặt** domain, repo (INSERT tham số hóa, không UPDATE issue/event), service, API (`same_origin_write`), migration 33 (guard `current_database()`, ràng buộc `UNIQUE(slot_id)` cho issue, trigger kiểm `ON_TIME/LATE` theo `scheduled_at`, comment “append-only”). Lệnh phát hành chạy có kiểm soát tại lịch; nếu lệnh không chạy, lần kiểm tiếp theo ghi `MISSED`/`JOB_NOT_RUN` với `detected_at` thật. Script `score_forecast_issues.py`: mặc định in nhãn dự kiến và lý do đủ/không đủ điều kiện; `--apply` mới INSERT. MRC mới hoặc phiếu `APPROVED` chỉ được chấm nếu đạt tài liệu tiêu chí tương đương đã lập trước phiếu đầu tiên. Có thể không có điểm nào trong 1–2 tuần.
- [ ] **Step 5: UI** — khối “Sổ phát hành”: bảng slot/tháng/trạm/`ON_TIME|MISSED|LATE`/dự báo/nhãn nếu có; MAE đúng hạn và MAE trễ tách riêng. Khi n = 0 hiện “Chưa có EC tháng đủ điều kiện để chấm — mới kiểm chứng hạ tầng phát hành”. Test Node: slot bỏ lỡ, slot phát hành trễ, bảng chưa có điểm.
- [ ] **Step 6: Chạy** test Python + Node PASS, build frontend.
- [ ] **Step 7: Commit** — `git commit -m "feat: immutable monthly forecast issues with automatic scoring"`

---

### Task 8: Tính năng B — Điểm theo dõi và cảnh báo EC theo ngưỡng

**Files:**
- Create: `sql/34_watch_point.sql`
- Create: `backend/domain/watch_alerts.py`, `backend/repositories/watch_points.py`, `backend/services/watch_points.py`, `backend/api/watch_points.py`
- Create: `frontend/src/features/watch-points.js`
- Modify: `frontend/src/features/point-inspection.js` (nút “Theo dõi điểm này”), `frontend/src/features/observations-map.js` (lớp vector điểm theo dõi), `frontend/workspace.html` (khối “Cảnh báo của tôi”), `backend/security.py::WRITE_PATHS`
- Test: `tests/test_watch_alerts.py`, `tests/watch_points.test.mjs`

**Interfaces:**
- Consumes: `spatial_simulation.simulation_frame(year_month, open_below_ec, close_above_ec)` (cache Task 2); `RiverAxis` chiếu điểm trong `backend/services/spatial_simulation.py:103-126` (dùng lại, không viết lại phép chiếu).
- Produces:
  - Bảng `dss_reference.watch_point(watch_id uuid PK, name text 1–80 ký tự, geom geometry(Point,4326) NOT NULL, chainage_km float8 0–175, distance_to_axis_km float8 ≥0 ≤12, open_below_ec_mS_m float8 >0, close_at_or_above_ec_mS_m float8 > open, created_at, is_operational_rule boolean false CHECK NOT)`, GiST trên `geom`.
  - `watch_alerts.classify(ec_mS_m: float | None, open_below: float, close_at_or_above: float) -> str` ∈ `SAFE|CAUTION|RISK|UNKNOWN` (khớp `ecWarningLevel` trong `gated-waterways.js`).
  - `POST /api/v1/watch-points` → 201 `{watch_id, chainage_km, distance_to_axis_km}`; 422 `WATCH_POINT_FAR_FROM_RIVER` nếu > 12 km; `GET /api/v1/watch-points/{id}/alerts?from=YYYY-MM&to=YYYY-MM` (tối đa 24 tháng) → `{items:[{year_month, ec_mS_m, level, data_kind}]}`.

- [ ] **Step 1: Test domain** — `classify(99.9,100,150)=='SAFE'`, `classify(100,100,150)=='CAUTION'`, `classify(150,100,150)=='RISK'`, `classify(None,...)=='UNKNOWN'`, `classify(10,150,100)=='UNKNOWN'`.
- [ ] **Step 2: Test service** — `test_point_far_from_axis_rejected` (điểm 105.80 E, 10.80 N); `test_alerts_window_max_24_months`; `test_alert_uses_chainage_interpolation` (mock frame có 2 đoạn, EC kỳ vọng là nội suy tuyến tính tại chainage).
- [ ] **Step 3: Chạy** → FAIL.
- [ ] **Step 4: Cài đặt** backend + migration 34 (guard, GiST, grant writer INSERT).
- [ ] **Step 5: UI** — trong thẻ point-inspection thêm nút; form chọn preset từ `shared/threshold-presets.js`; lớp điểm (ký hiệu khác trạm/cống/RIA2); bảng dải màu theo tháng với nhãn `data_kind`; câu cố định “EC đoạn sông lân cận, không phải số đo tại điểm; không phải khuyến cáo tưới”. Lưu `watch_id` vào `localStorage` để người dùng thấy lại điểm của mình. Test Node: render dải 3 mức + UNKNOWN.
- [ ] **Step 6: Chạy** test, build.
- [ ] **Step 7: Commit** — `git commit -m "feat: watch points with threshold-based EC alerts along the river"`

---

### Task 9: Tính năng C — Phiếu số đo thực địa có kiểm duyệt

**Files:**
- Create: `sql/35_field_measurement.sql`, `docs/field_ec_label_protocol_2026-11-14.md` (lập và khóa trước phiếu đầu tiên)
- Create: `backend/domain/field_measurement.py`, `backend/repositories/field_measurements.py`, `backend/services/field_measurements.py`, `backend/api/field_measurements.py`
- Create: `frontend/src/features/field-measurements.js`
- Modify: `frontend/workspace.html` (tab Chất lượng dữ liệu: form + hàng chờ duyệt), `frontend/src/features/observations-map.js` (lớp “Số đo thực địa đã duyệt”), `backend/security.py::WRITE_PATHS`, `scripts/setup_security.py`
- Test: `tests/test_field_measurement.py`, `tests/field_measurements.test.mjs`

**Interfaces:**
- Produces:
  - `field_measurement.normalize(raw: dict, now: datetime, reference_median_mS_m: float | None) -> dict` trả `{ec_mS_m, unit_original, flags: list[str], observed_at}`; ném `ValueError` với mã: `EC_OUT_OF_RANGE` (<0 hoặc >6000 mS/m sau quy đổi), `FUTURE_TIMESTAMP` (> now + 10 phút), `TOO_OLD` (> 365 ngày), `UNIT_UNKNOWN`.
  - Hệ số: `µS/cm ÷ 10`, `dS/m × 100`, `mS/cm × 100`, `mS/m × 1`.
  - Cờ `REVIEW_HIGH` khi `reference_median` có và `ec > 3 × reference_median` (cùng quy tắc `HIGH_VS_CALENDAR_MEDIAN_REVIEW_ONLY`).
  - Bảng `dss_reference.field_measurement(measurement_id uuid PK, geom Point 4326, ec_mS_m float8 ≥0, unit_original text, water_temp_degC float8 NULL, observed_at timestamptz, position_kind text IN ('RIVER','FIELD'), device text, submitted_by text 1–120, flags text[], raw_payload jsonb ≤16384 byte, submitted_at)`; `dss_reference.field_measurement_review(review_id identity, measurement_id FK, decision IN ('APPROVED','REJECTED'), reviewer text, note text, reviewed_at)`; view `dss_reference.v_field_measurement_status` lấy review mới nhất, mặc định `PENDING`.
  - API: `POST /api/v1/field-measurements` → 201; `GET /api/v1/field-measurements?status=PENDING|APPROVED|REJECTED&bbox=minLon,minLat,maxLon,maxLat`; `POST /api/v1/field-measurements/{id}/review` — **cả gửi và duyệt** đều cần API key trong phạm vi cán bộ nội bộ; key duyệt riêng, từ chối khi chưa cấu hình. Chưa mở nhập công khai cho người dân.

- [ ] **Step 1: Test domain**

```python
def test_microsiemens_converted(self):
    self.assertAlmostEqual(normalize(dict(RAW, ec=1500, unit='µS/cm'), NOW, None)['ec_mS_m'], 150.0)
def test_high_value_flagged_not_rejected(self):
    self.assertIn('REVIEW_HIGH', normalize(dict(RAW, ec=1500, unit='mS/m'), NOW, 20.0)['flags'])
def test_future_timestamp_rejected(self):
    with self.assertRaisesRegex(ValueError, 'FUTURE_TIMESTAMP'): normalize(dict(RAW, observed_at=(NOW + timedelta(hours=1)).isoformat()), NOW, None)
def test_negative_rejected(self): ...  # EC_OUT_OF_RANGE
```
- [ ] **Step 2: Test service/API** — `test_review_requires_api_key_even_if_unset` (env key rỗng → 503); `test_submit_requires_internal_key`; `test_status_is_latest_review` (APPROVED rồi REJECTED → REJECTED); `test_submission_never_touches_public_tables` (mock repo, kiểm SQL không chứa `public.`); `test_approved_but_non_equivalent_not_scored`.
- [ ] **Step 3: Chạy** → FAIL.
- [ ] **Step 4: Trước khi nhận phiếu**, lập và ghi ngày/phiên bản tài liệu tiêu chí nhãn EC tháng: bán kính quanh trạm, cửa sổ ngày, khung giờ, EC25/cách quy đổi, hiệu chuẩn thiết bị, số mẫu tối thiểu, phép tổng hợp và thứ tự ưu tiên nguồn nhãn. Sau đó cài backend + migration 35 (guard, GiST, trigger audit dùng lại `webgis_security.audit_dss_insert` cho 2 bảng mới, grant writer INSERT).
- [ ] **Step 5: UI** — form (vị trí click bản đồ hoặc nhập tọa độ), chọn đơn vị bắt buộc, hiển thị giá trị đã quy đổi trước khi gửi; hàng chờ duyệt cho quản trị (nhập API key trong phiên, không lưu localStorage); lớp bản đồ chỉ APPROVED, ký hiệu tam giác, tooltip “Số đo thực địa đã duyệt · thời điểm · người gửi · không phải dữ liệu MRC”. Test Node: quy đổi hiển thị, ẩn PENDING khỏi lớp bản đồ.
- [ ] **Step 6: Chạy** test, build.
- [ ] **Step 7: Commit** — `git commit -m "feat: reviewed field EC submissions separate from MRC series"`

---

### Task 10: Tính năng D — Mô phỏng what-if cống

**Files:**
- Create: `backend/domain/gate_scenario.py`, `backend/api/gate_scenarios.py`
- Modify: `frontend/src/features/gate-dossiers.js` (khối “Thử kịch bản (không phải lệnh)”)
- Test: `tests/test_gate_scenario.py`, `tests/gate_scenario.test.mjs`

**Interfaces:**
- Consumes: `simulation_frame(...)['gates']` (lấy `ec_outside` theo `gate_code`).
- Produces: `simulate(ec_inside_0: float, ec_outside: float, state: Literal['OPEN','CLOSED'], exchange_rate: float, days: int, stop_at_or_above: float) -> dict` trả `{series: list[{day:int, ec_inside_mS_m: float}], first_exceed_day: int | None, assumptions: list[str]}`; ràng buộc `0 ≤ exchange_rate ≤ 0.5`, `1 ≤ days ≤ 30`, EC ≥ 0. `POST /api/v1/gate-scenarios/preview {gate_code, year_month, ec_inside_0, exchange_rate=0.1, days=14, open_below_ec, close_above_ec}` → `{open: simulate(...OPEN), closed: simulate(...CLOSED), is_operational_rule: false, actuator_command: null}`; không ghi DB; **không** thêm vào `WRITE_PATHS` (POST không ghi nhưng vẫn qua `same_origin`).

- [ ] **Step 1: Test domain**

```python
def test_open_converges_to_outside(self):
    s = simulate(20, 200, 'OPEN', 0.1, 30, 150)['series']; self.assertLess(abs(s[-1]['ec_inside_mS_m'] - 200), abs(20 - 200)); self.assertEqual(s[0]['ec_inside_mS_m'], 20)
def test_closed_constant(self):
    self.assertTrue(all(p['ec_inside_mS_m'] == 20 for p in simulate(20, 200, 'CLOSED', 0.1, 14, 150)['series']))
def test_first_exceed_day(self):
    # 20 + 180·(1 − 0.9^d) ≥ 150  ⇔ 0.9^d ≤ 0.2778  → d = 13 (EC ngày 13 ≈ 154,25)
    self.assertEqual(simulate(20, 200, 'OPEN', 0.1, 14, 150)['first_exceed_day'], 13)
def test_rate_out_of_range(self): ...  # 0.6 → ValueError
```
- [ ] **Step 2: Test API** — `test_preview_has_no_actuator_command`, `test_unknown_gate_404`.
- [ ] **Step 3: Chạy** → FAIL.
- [ ] **Step 4: Cài đặt** domain (công thức trong Phần III.D), API.
- [ ] **Step 5: UI** — form, biểu đồ hai đường OPEN/CLOSED + đường ngưỡng, câu cố định “Mô hình trộn một bể với tỷ lệ trao đổi giả định, chưa hiệu chuẩn; không phản ánh vận hành thật; không phải lệnh”; nút “Lưu kịch bản” dùng `/gate-drafts` sẵn có với `schema_version: 1`. Test Node: render 2 series, nhãn cảnh báo luôn hiện.
- [ ] **Step 6: Chạy** test, build, kiểm thủ công trên trang.
- [ ] **Step 7: Commit** — `git commit -m "feat: non-operational gate what-if mixing scenario"`

---

## Kiểm tra cuối (sau mọi task)

- `node --test tests/*.test.mjs` → 0 fail.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"` → 0 fail, 0 error.
- `npm.cmd --prefix frontend run build` thành công; khởi động lại `.\start.ps1`; chạy lại kịch bản `docs/on_tap_hoi_dong_2026-11-13/02_kich_ban_demo.md` T01–T22 (T22 có thể ghi skip bằng chứng đã công khai, không coi là pass tái lập).
- `curl -w "%{time_total}"` frame lặp lại < 0,3 s.
- `git diff --check`; không có `.env` trong `git status`.
- Migration 32–35 chỉ in kế hoạch cho tới khi người dùng cho phép `--apply`.
