## 2.B. Backend xử lý nghiệp vụ: services (người điều phối) và domain (bộ não tính toán)

Hãy hình dung một quán ăn. **API** (thư mục `backend/api/`) là người phục vụ bàn: nhận yêu cầu của khách (trình duyệt) rồi mang món ra. **Services** (`backend/services/`) là **người điều phối bếp**: nhận phiếu gọi món, đi lấy nguyên liệu ở kho (gọi các file `backend/repositories/` để đọc CSV, JSON, PostgreSQL), giao cho đầu bếp, kiểm tra món trước khi bưng ra, và nếu thiếu nguyên liệu thì báo lỗi lịch sự (mã lỗi HTTP như 404, 422, 503). **Domain** (`backend/domain/`) là **đầu bếp chính, tức bộ não tính toán**: chứa các công thức thuần (nội suy dọc sông, so ngưỡng, kiểm tra hồ sơ cống, chạy mô hình Random Forest). Domain thường không quan tâm dữ liệu đến từ đâu; nó chỉ nhận số và trả kết quả. Nhờ chia như vậy, khi muốn đổi *công thức* bạn vào domain; khi muốn đổi *cách lấy dữ liệu, cách ghép kết quả, cách báo lỗi* bạn vào services.

Một vài từ dùng lặp lại trong phần này:
- **dict**: "cái hộp có ngăn dán nhãn" trong Python, ví dụ `{"station": "MyTho", "ec": 120}`. FastAPI tự đổi dict thành **JSON** (dạng chữ mà trình duyệt đọc được).
- **hash / sha256**: "dấu vân tay" của một file. Chỉ cần sửa một byte trong file, dấu vân tay đổi hoàn toàn. Mã dùng nó để chắc file mô hình hay file kết quả không bị sửa lén.
- **cache**: "ghi nhớ kết quả đã tính" để lần sau khỏi tính lại, như học thuộc bảng cửu chương thay vì cộng lại mỗi lần.
- **registry**: "sổ đăng ký" (file `data/models/multivariate_registry.json`) ghi trạm nào dùng file mô hình nào và dấu vân tay của nó.
- **artifact**: "sản phẩm đã đóng gói" của một lần huấn luyện/thí nghiệm, ví dụ `model.joblib`, `manifest.json`, `predictions.csv`.
- **joblib**: định dạng file lưu nguyên một mô hình Python đã học xong để lần sau mở ra dùng ngay, không phải học lại.
- **manifest**: "phiếu lý lịch" đi kèm mô hình/thí nghiệm: tham số, thứ tự đặc trưng, nguồn dữ liệu, điểm đánh giá, hash.
- **nội suy**: ước lượng giá trị ở chỗ không đo bằng cách dựa vào các điểm có số ở hai bên. Kết quả nội suy **không phải số đo**.
- **WorkspaceError**: loại lỗi riêng của dự án, mang theo mã HTTP (ví dụ 503 = "dịch vụ tạm không dùng được", 422 = "dữ liệu gửi lên không hợp lệ", 404 = "không tìm thấy", 409 = "trùng lặp").

---

### `backend/domain/__init__.py`
- **Vai trò trong đời sống:** File rỗng (0 dòng). Nó chỉ là "tấm biển" báo cho Python biết thư mục `domain` là một gói (package) để các file khác viết được `from backend.domain import ...`.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: không có. Đầu ra: không có.
- **Các hàm cốt lõi:** Không có hàm nào.
- **Muốn sửa … thì có tìm đến file này không?:** Không — mọi logic nằm ở các file `.py` khác trong cùng thư mục.

### `backend/services/__init__.py`
- **Vai trò trong đời sống:** Cũng là file rỗng (0 dòng), "tấm biển" để `backend/services` thành một gói Python.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Không có.
- **Các hàm cốt lõi:** Không có.
- **Muốn sửa … thì có tìm đến file này không?:** Không — hãy mở file dịch vụ cụ thể bên dưới.

---

### `backend/domain/data_freshness.py`
- **Vai trò trong đời sống:** Giống người kiểm tra hạn sử dụng sữa trong tủ lạnh: nhìn tháng dữ liệu nguồn mới nhất và cho biết dữ liệu còn "tươi" (FRESH), "sắp hết hạn" (DUE) hay "đã cũ" (STALE). Dựa trên **giả định** dữ liệu tháng được công bố sau cuối tháng + 5 ngày, chưa phải lịch công bố đã xác minh.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: chuỗi tháng nguồn cuối (ví dụ `"2026-09"`), ngày hôm nay, số ngày trễ giả định (mặc định 5). Không đọc file. Đầu ra: dict gồm `status`, `days_until_stale`, `next_target_month_supported`, `availability_basis` (câu ghi rõ đây là giả định). Được gọi bởi `backend/api/data_freshness.py`.
- **Các hàm cốt lõi:**
  - `_shift_month(month, count)`: cộng/trừ tháng. Đổi năm-tháng thành một số đếm (năm × 12 + tháng − 1), cộng `count`, rồi đổi ngược. Ví dụ tháng 11/2026 + 2 = tháng 01/2027.
  - `assess(last_source_month, today, assumed_lag_days=5, retrieved_at=None)`: tính hạn. Ví dụ đời thường: nguồn mới nhất là `2026-09`. Tháng kế là 10/2026, cuối tháng 10 là 31/10, cộng 5 ngày thành hạn 05/11/2026. Nếu hôm nay là 17/11/2026 thì còn −12 ngày → `STALE`. Nếu còn từ 0 đến 7 ngày → `DUE`; nhiều hơn 7 → `FRESH`. `next_target_month_supported` = tháng nguồn + 2 (vì mô hình dùng dữ liệu tháng t−2), ở ví dụ là `2026-11`. Nếu số ngày trễ âm thì báo lỗi.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi quy tắc "cuối tháng + 5 ngày" hoặc mốc 7 ngày để báo `DUE`.
  - Không — muốn đổi đường dẫn API hay giao diện hiện trạng thái thì sang `backend/api/data_freshness.py` và frontend.

### `backend/domain/workspace.py`
- **Vai trò trong đời sống:** Như người thủ kho kiểm hàng nhập: trước khi cho bộ dữ liệu quan trắc (snapshot) vào dùng, kiểm từng thùng có đúng nhãn, đúng đơn vị, không trùng, không số âm.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: một dict "bundle" (gói dữ liệu) đã đọc sẵn bởi `backend/repositories/workspace.py` (và `backend/research.py`). Không tự đọc file. Đầu ra: trả lại chính dict đó nếu hợp lệ, hoặc báo lỗi `ValueError`.
- **Các hàm cốt lõi:**
  - `validate_bundle(data)`: kiểm các điều kiện sau. `schema_version` phải là 1; đơn vị phải là `mS/m`; `live_forecast_available` phải là `False` (không được giả là dự báo sống). Mã trạm không trùng. Mỗi bản ghi EC: ngày hợp lệ, không trùng cặp (trạm, ngày), trạm và nguồn phải tồn tại, EC là số hữu hạn không âm, đơn vị `mS/m`, `gate_decision_eligible` phải `False` (dữ liệu này không được dùng ra quyết định cống). Nếu `time_precision` là `DATE_ONLY` (chỉ có ngày) thì không được ghi giờ lấy mẫu — đúng với lưu ý trong CLAUDE.md rằng dấu `00:00` không chứng minh giờ thật. Tọa độ trạm phải là Point, kinh độ −180..180, vĩ độ −90..90. Thí nghiệm phải có `deployment_ready=False` và `selected_on='validation'`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm một luật kiểm tra mới cho snapshot (ví dụ bắt buộc thêm trường QA).
  - Không — muốn đổi nơi đọc file `data/research/workspace.json` hoặc PostgreSQL thì sang `backend/repositories/workspace.py`.

### `backend/domain/river_interpolation.py`
- **Vai trò trong đời sống:** Như ước nhiệt độ ở giữa hai cái nhiệt kế treo dọc hành lang: nếu đầu hành lang 20 độ, cuối hành lang 30 độ thì chính giữa đoán khoảng 25 độ. Ở đây "hành lang" là sông Tiền, "nhiệt kế" là các trạm EC.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: vị trí trên sông tính bằng km (gọi là chainage, "số cây số dọc tuyến") và danh sách mốc `(km, EC)`. Không đọc file. Đầu ra: một số EC (mS/m) ước lượng. Được `backend/services/spatial_simulation.py` và `spatial_inputs.py` dùng.
- **Hằng số:** `MY_THUAN_COORDINATE = [105.9263229, 10.27532005]`, `MY_THUAN_KM = 85.217605`, `MY_THUAN_RATIO = 0.68174084`, tên chế độ `PIECEWISE_3_STATION` (đủ 3 trạm) và `TWO_STATION_FALLBACK_MISSING_MYTHUAN` (thiếu Mỹ Thuận, chỉ dùng 2 trạm).
- **Các hàm cốt lõi:**
  - `interpolate_anchors(chainage, anchors)`: **nội suy tuyến tính từng chặng**. Kiểm đầu vào hữu hạn, EC không âm, km tăng dần. Tìm hai mốc kẹp vị trí, tính tỷ lệ `u = (km − km_trái)/(km_phải − km_trái)` (bị giới hạn trong 0..1), rồi `EC = EC_trái + (EC_phải − EC_trái) × u`. Ví dụ: Tân Châu km 0 EC 20; Mỹ Thuận km 85,2 EC 40; Mỹ Tho km 125 EC 100. Tại km 105: `u = (105 − 85,2)/(125 − 85,2) ≈ 0,497`, nên EC ≈ 40 + 60 × 0,497 ≈ 69,8 mS/m. Đây là **ước lượng để vẽ màu**, không phải số đo tại km 105; mô hình này không tính triều hay dòng chảy.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi công thức nội suy (ví dụ thử cách khác thay tuyến tính) hoặc đổi km của Mỹ Thuận.
  - Không — muốn đổi điều kiện biên cửa sông (km 175) hay chia 35 đoạn sông thì sang `backend/services/spatial_simulation.py`.

### `backend/domain/multivariate_ec.py`
- **Vai trò trong đời sống:** Đây là "thầy bói có sổ sách": mở mô hình Random Forest đã học sẵn (không học lại), kiểm tra con dấu (hash) để chắc mô hình không bị đánh tráo, đưa vào các con số thời tiết/thủy văn của tháng t−2, và đọc ra EC dự báo cho tháng cần hỏi.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: registry `data/models/multivariate_registry.json`; với mỗi trạm, file `model.joblib` và `manifest.json` (Mỹ Tho: `runs/multivariate_ec/mytho/20261108T_HYDROLOGY_PRIMARY_V1/`); `predictions.csv` cạnh manifest (để hiển thị hồi cứu); danh sách đặc trưng thủy văn lấy từ `backend/repositories/hydrology_inputs.py`. Đầu ra: dict dự báo, dict danh mục mô hình, dict bản ghi đánh giá. Không ghi file.
- **Hằng số:** `WEATHER_AGG` (mưa = tổng, nhiệt độ = trung bình, gió = trung bình), `FEATURES` = 3 biến thời tiết + `month_sin`, `month_cos`; `HYDRO_FEATURES` (5 biến thủy văn từ `hydrology_inputs.FEATURES`); `STATIONS` ánh xạ `MYTHO`→`MRC_VN_019805`, `MYTHUAN`→`MRC_VN_019804`, `TANCHAU`→`MRC_VN_019803`; `LABELS`, `UNITS` để hiển thị tiếng Việt và đơn vị.
- **Các hàm cốt lõi:**
  - `normalize_station(station)`: chuẩn hóa tên trạm, ví dụ `"My Tho"`, `"MRC_VN_019805"` đều thành `MYTHO`. Tên lạ thì báo lỗi.
  - `sha256(path)`: tính dấu vân tay file.
  - `monthly_weather(frame)`: gộp số liệu ngày thành tháng. Nếu tháng thiếu ngày (ví dụ tháng 30 ngày mà chỉ có 28 ngày mưa) thì đặt NaN (trống), để tổng mưa thiếu ngày không giả làm tổng đủ tháng.
  - `load_model(station, registry_path=None)`: đọc registry, **mỗi lần gọi đều** so sha256 của manifest và model với registry; kiểm `feature_order` (thứ tự đặc trưng) và trạm khớp. Mỹ Tho được phép dùng 5 biến thời tiết+chu kỳ cộng 5 biến thủy văn; trạm khác chỉ 5 biến đầu. Sau đó gọi `_load_cached_artifact`.
  - `_load_cached_artifact(...)`: phần đắt nhất (mở file joblib) được **cache** tối đa 8 bản bằng `lru_cache`. Kiểm phiên bản scikit-learn trùng với manifest, kiểm hash lần nữa trên đúng các byte vừa đọc, rồi mở bằng `joblib.load`. Đặt `n_jobs = 1` cho rừng cây. Ví dụ: lần đầu mở mất vài giây; lần sau dùng bản đã nhớ, nhưng hash vẫn được kiểm lại trong `load_model`, nên file bị sửa sẽ bị bắt.
  - `warmup_models()`: được `backend/main.py` gọi lúc khởi động để mở trước mô hình cả 3 trạm; trạm nào lỗi chỉ ghi tên lỗi, không làm sập web. Không huấn luyện, không đọc thời tiết.
  - `ensemble_distribution(model, features)`: Random Forest là "hội đồng" 300 cây quyết định (với Mỹ Tho); mỗi cây đoán một số. Hàm lấy dự báo của từng cây rồi tính P10, P25, P50, P75, P90, IQR và độ lệch chuẩn. Ví dụ đơn giản với 10 cây đoán 80, 85, 90, 95, 100, 100, 105, 110, 130, 200: P10 khoảng 84,5, P90 khoảng 137. Mã ghi rõ: đây chỉ là **độ phân tán giữa các cây, không phải khoảng tin cậy đã hiệu chuẩn**.
  - `model_catalog(registry_path=None)`: liệt kê mô hình mỗi trạm: phiên bản, mốc huấn luyện, số mẫu, điểm đánh giá, đặc trưng, mức quan trọng đặc trưng; gắn thêm `gap_validation` từ `ec_gap_evaluation.summary` nếu manifest chưa có. Luôn `deployment_ready=False`.
  - `evaluation_records(station, ...)`: đọc `predictions.csv` (kiểm hash theo `predictions_sha256`), lấy phần `holdout` 2022-01..2023-12, kiểm số dòng khớp `n` trong manifest; trả từng tháng thực đo và dự báo của các phương pháp (Random Forest, giữ EC cuối, trung bình tháng...).
  - `predict_month(station, target_month, weather_features, ...)`: tháng đích phải là ngày 1. Kiểm 3 biến thời tiết là số hữu hạn. Tính chu kỳ tháng: `month_sin = sin(2π × tháng/12)`, `month_cos = cos(2π × tháng/12)`; ví dụ tháng 3: sin(π/2) = 1, cos(π/2) = 0 — giúp mô hình hiểu tháng 12 và tháng 1 "gần nhau". Nếu mô hình cần thủy văn thì kiểm thêm 5 biến thủy văn. Dự báo, tính phân tán cây, trả dict có `weather_month` = tháng đích − 2 (ví dụ dự báo 05/2027 dùng dữ liệu 03/2027), `quality_status='EXPERIMENTAL_SOURCE_EC_UNVERIFIED'`, `gate_decision_eligible=False` và câu `availability_assumption` nói rõ độ trễ công bố là giả định.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi cách kiểm hash, cách tính P10–P90 hay danh sách trạm có mô hình.
  - Không — muốn đổi file mô hình đang dùng thì sửa registry/artifact có chủ đích (xem CLAUDE.md mục 10), không sửa code này. Muốn đổi cách đọc ERA5/Kratie thì sang `backend/repositories/multivariate_inputs.py`, `hydrology_inputs.py`.
  - Không — muốn đổi thông báo lỗi người dùng thấy khi bấm dự báo thì sang `backend/services/multivariate.py`.

### `backend/domain/ec_gap_evaluation.py`
- **Vai trò trong đời sống:** Như cuốn sổ điểm thi đã niêm phong: đọc kết quả thí nghiệm "nếu EC trạm ngừng cập nhật lâu thì dự báo sai bao nhiêu" (giao thức khóa EC), nhưng chỉ đọc sau khi kiểm niêm phong (sha256) còn nguyên.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: file chỉ mục `data/models/frozen_ec_gap_evaluation.json` → trỏ tới `run_manifest.json` của thí nghiệm, rồi `metrics.csv` và `predictions.csv` cùng thư mục (mỗi file đều kiểm hash). Với Mỹ Tho gọi thêm `ec_gap_remedies.summary` và `ec_gap_followup.summary`. Đầu ra: dict tóm tắt và bảng từng tháng. Không ghi.
- **Hằng số:** `PROTOCOL = 'FROZEN_EC_WEATHER_ONLY_V1'`; `LABELS` gồm 5 phương pháp: `RandomForest`, `FrozenPersistence` (giữ EC cuối), `MonthlyClimatology` (trung bình từng tháng), `FrozenSeasonalRepeat` (lặp EC cùng tháng gần nhất), `SeasonalityOnlyRF`.
- **Các hàm cốt lõi:**
  - `_verified(path, expected)`: file phải nằm trong thư mục dự án và sha256 phải khớp, nếu không báo lỗi.
  - `evidence()`: đọc chỉ mục và manifest, kiểm đúng giao thức.
  - `_table(manifest, directory, filename)`: đọc CSV sau khi kiểm hash, trả bảng pandas.
  - `summary(station)`: lấy MAE/RMSE của 5 phương pháp cho kỳ chính, độ trễ EC chính, nhóm `all`. Thiếu phương pháp nào thì báo lỗi.
  - `records(station, experiment=None, ec_delay_days=5)`: trả bảng từng tháng (thực đo + 5 dự báo), điểm, quy tắc khóa EC, giới hạn. Kiểm số tháng khớp `n` trong điểm. Gắn `model_version='RF_FIXED_300_DEPTH8_LEAF3_SEED42_FROZEN'`. Đây là **bằng chứng hồi cứu**, không phải dự báo mới.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm cột/phương pháp mới vào biểu đồ hồi cứu khóa EC.
  - Không — muốn chạy lại thí nghiệm thì dùng script `scripts/evaluate_frozen_ec_gap.py` (ghi `outputs/`), không sửa file này.

### `backend/domain/ec_gap_remedies.py`
- **Vai trò trong đời sống:** Bảng so sánh "thuốc chữa" khi EC Mỹ Tho mất dữ liệu: chỉ thời tiết, thêm thủy văn, thêm EC trạm lân cận, hay kết hợp — xem cách nào đỡ sai hơn. Chỉ để đọc kết quả nghiên cứu.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `outputs/frozen_ec_remedies_20261108/run_manifest.json`, `metrics.csv`, `predictions.csv` (kiểm sha256). Đầu ra: dict có `data_kind='RESEARCH_ABLATION'`, `deployment_ready=False`, `threshold_mS_m=100`, điểm MAE/RMSE, số báo cao giả (`false_alerts_100`) và bỏ sót EC cao (`missed_high_100`), chuỗi dự báo của phương án thủy văn.
- **Các hàm cốt lõi:**
  - `summary(experiment, delay)`: kiểm giao thức `FROZEN_EC_REMEDY_RESEARCH_V1` và trạm `MYTHO`; số tháng phải là 24 (kỳ `gap_2022_2023`) hoặc 36 (kỳ khác). Đặc biệt: tự tính lại MAE và RMSE từ `predictions.csv` và so với `metrics.csv` (sai lệch > 1e−8 thì báo lỗi). Ví dụ: 3 tháng sai 10, −20, 30 → MAE = (10+20+30)/3 = 20; RMSE = căn((100+400+900)/3) ≈ 21,6. RMSE lớn hơn MAE vì phạt mạnh lỗi lớn.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi nhãn tiếng Việt của các phương án hoặc thêm chỉ số hiển thị.
  - Không — muốn đổi mô hình đang phục vụ thì đây không phải chỗ; xem registry và `multivariate_ec.py`.

### `backend/domain/ec_gap_followup.py`
- **Vai trò trong đời sống:** "Phiếu theo dõi" sau đợt thử thuốc ở trên: thử thêm EC Mỹ Thuận, EC Tân Châu, hồi quy Ridge, và Ridge + RF học phần sai. Cũng chỉ đọc bằng chứng nghiên cứu.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `outputs/frozen_ec_followup_20261108/run_manifest.json`, `metrics.csv` (kiểm sha256). Đầu ra: dict `data_kind='RESEARCH_FOLLOWUP'`, `deployment_ready=False`, điểm của 5 phương pháp (`WeatherHydrology` là đối chứng).
- **Các hàm cốt lõi:**
  - `summary(experiment, delay)`: kiểm giao thức `FROZEN_EC_FOLLOWUP_RESEARCH_V1`, trạm Mỹ Tho, đủ phương pháp, số tháng 24/36; trả MAE, RMSE, báo cao giả, bỏ sót ở mốc 100 mS/m. Mốc 100 là mốc phân tích, không phải chuẩn nước tưới.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một phương pháp follow-up mới vào bảng.
  - Không — muốn chạy lại thì dùng `scripts/evaluate_frozen_ec_followup.py`.

### `backend/domain/field_measurement.py`
- **Vai trò trong đời sống:** Như người nhận phiếu đo của cán bộ thực địa: đổi đơn vị về chung một chuẩn, kiểm giờ đo, tọa độ, thiết bị, người đo, và dán cờ "cần xem lại" nếu nghi ngờ. Số này **không** được nâng thành số đo MRC.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: dict phiếu do người dùng gửi, giờ hiện tại, (tùy chọn) trung vị EC tham khảo. Không đọc file. Đầu ra: dict đã chuẩn hóa kèm danh sách `flags`. Được `backend/services/field_measurements.py` gọi.
- **Các hàm cốt lõi:**
  - `normalize(raw, now, reference_median_mS_m=None)`: đổi đơn vị theo `CONVERSIONS`: `µS/cm` × 0,1; `dS/m` × 100; `mS/cm` × 100; `mS/m` × 1. Ví dụ 1.500 µS/cm → 150 mS/m. EC phải 0..6000 mS/m. Giờ đo phải có múi giờ, không quá tương lai 10 phút, không cũ hơn 365 ngày. Tọa độ hợp lệ, `position_kind` là `RIVER` hoặc `FIELD`, có thiết bị, có người gửi (1–120 ký tự), nhiệt độ nước −5..50 °C nếu có, ngày hiệu chuẩn không sau ngày đo. Cờ: `REVIEW_HIGH` nếu EC > 3 lần trung vị tham khảo (ví dụ trung vị 40, đo 130 → bị cờ); `NO_EC25` nếu không ghi EC chuẩn 25 °C; `CALIBRATION_UNVERIFIED` nếu chưa hiệu chuẩn, hiệu chuẩn quá 30 ngày hoặc thiếu mã tham chiếu. Lỗi trả mã chữ như `UNIT_UNKNOWN`, `FUTURE_TIMESTAMP`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm đơn vị đo mới hoặc đổi giới hạn 6000 mS/m / 30 ngày hiệu chuẩn.
  - Không — muốn đổi cách lưu phiếu vào PostgreSQL thì sang `backend/repositories/field_measurements.py`.

### `backend/domain/forecast_issue.py`
- **Vai trò trong đời sống:** Như quy định "nộp bài đúng giờ, niêm phong rồi mới chấm": mỗi tháng mục tiêu có một lịch phát hành dự báo cố định; bản phát hành được niêm phong (ghi hash mô hình và hash dữ liệu) để sau này chấm điểm công bằng với số đo thật.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: dict dự báo (từ `backend/services/multivariate.py`), thời điểm phát hành, dict quan trắc dùng để chấm. Không đọc file. Đầu ra: dict bản phát hành hoặc dict điểm. Hằng số `SCHEDULE_CODE='MONTHLY_D06_PREV'`, `LABEL_PROTOCOL_VERSION='MONTHLY_EC_LABEL_V1_20261114'`, `LEDGER_START_LOCAL = 14/11/2026`, ba trạm `MYTHO`, `MYTHUAN`, `TANCHAU`.
- **Các hàm cốt lõi:**
  - `_shift_month(month, offset)`: cộng/trừ tháng (giống `data_freshness.py`).
  - `schedule(target_month)`: lịch phát hành = 9 giờ sáng ngày 6 của tháng **trước** tháng đích, giờ Việt Nam. Ví dụ tháng đích 01/2027 → phát hành 06/12/2026 lúc 09:00.
  - `build_issue(prediction, issued_at)`: bắt buộc dự báo dùng dữ liệu lưu trữ (`ARCHIVE`) đúng tháng t−2, có hash mô hình 64 ký tự, EC hữu hạn không âm. Tạo `data_version` = sha256 của nguồn thời tiết + thủy văn, để biết dữ liệu nào đã dùng.
  - `score(issue, observation)`: chỉ chấm khi nguồn là `MRC` hoặc `FIELD_APPROVED`, nhãn tương đương tháng, đúng phiên bản giao thức, ngày đo thuộc đúng tháng đích. Trả `abs_error_mS_m` = |thực − dự báo|. Ví dụ dự báo 80, đo 95 → sai 15 mS/m. Không đủ điều kiện thì trả `None` (không chấm).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi lịch phát hành (ngày 6, 9 giờ) hoặc điều kiện một số đo được dùng để chấm.
  - Không — muốn đổi cách ghi slot/bản phát hành vào DB thì sang `backend/services/forecast_issues.py` và `backend/repositories/forecast_issues.py`.

### `backend/domain/gates.py`
- **Vai trò trong đời sống:** Như người tiếp nhận hồ sơ xin phép: kiểm hồ sơ cống có đủ giấy tờ, ngày tháng có hợp lý không. Nó **không bao giờ** quyết định giờ đóng/mở cống; luôn trả `recommendation=None`, `actuator_command=None` (không có lệnh điều khiển).
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: hai dict `policy` (quy trình cống) và `data` (hồ sơ số đo). Không đọc file. Đầu ra: dict kết quả có `status`, `reasons`, `planning_actions`, `requires_operator_review=True`. Hằng số `VERSION = "2.0.0"`.
- **Các hàm cốt lõi:**
  - `stamp(value)`: đọc chuỗi thời gian ISO, bắt buộc có múi giờ, đổi về UTC. Thiếu múi giờ → lỗi `GateInputError`.
  - `validate_chronology(data)`: kiểm thứ tự thời gian: thời điểm đổi trạng thái không được sau lúc lập hồ sơ; thời điểm "có dữ liệu" không trước lúc đo; số đo không được xuất hiện sau thời điểm lập hồ sơ (tránh dùng dữ liệu "từ tương lai"). Ví dụ lập hồ sơ 8:00 mà số đo ghi 9:00 → bị từ chối.
  - `numeric(value, name)`, `nonempty(value)`: kiểm số hữu hạn và chuỗi không rỗng.
  - `evaluate(policy, data)`: phiên bản schema phải 1; `is_demo` phải là `False` (cần hồ sơ thật). Luôn ghi lý do `SERVER_VERIFIED_GATE_EVIDENCE_NOT_AVAILABLE` và `MONTHLY_EC_CANNOT_DETERMINE_SWITCHING_TIMES` (EC tháng không quyết được giờ đóng/mở). Thiếu mực nước/EC hai phía thì thêm lý do `..._MISSING`. Trả danh sách việc cần làm (bổ sung số đo hai phía, xác minh liên hệ trạm–cống, người vận hành rà soát).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi thông điệp/lý do trả về cho hồ sơ cống hoặc luật kiểm thời gian.
  - Không — muốn đổi kịch bản mô phỏng có ngưỡng EC và chênh mực nước thì sang `backend/domain/gate_simulation.py`.

### `backend/domain/gate_simulation.py`
- **Vai trò trong đời sống:** "Thử trên giấy": nếu số đo hai phía cống như thế này và quy trình đặt ngưỡng như thế kia, thì kịch bản lấy nước/xả nước có hợp không. Mã ghi rõ: kịch bản giả định, không phải lệnh đóng/mở.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: dict `policy` (ngưỡng EC `open_below`, `close_at_or_above`, giới hạn mực nước `min_head_m`, `max_abs_head_m`, `inside_min_m`, `inside_max_m`, hệ cao độ, cơ sở EC) và dict `data` (4 số đo `outside_level`, `inside_level`, `outside_quality`, `inside_quality`, chế độ `INTAKE` = lấy nước hoặc `DRAIN` = tiêu/xả). Dùng `numeric`, `stamp`, `validate_chronology` của `backend/domain/gates.py`. Đầu ra: dict `status` (`SIMULATED`, `INVALID_INPUT`, `INSUFFICIENT_DATA`), `simulation_outcome` (`BLOCKED`, `REVIEW_REQUIRED`, `CONDITIONS_MET`), lý do, `actuator_command=None`.
- **Các hàm cốt lõi:**
  - `simulate(policy, data)`: kiểm đủ dữ liệu, đúng đơn vị (`mS/m`, `m`), cùng mã cống, cùng hệ cao độ, cùng cơ sở EC, **bốn số đo phải cùng thời điểm**; cận dưới phải nhỏ hơn cận trên. Sau đó tính chênh mực nước `head = ngoài − trong`; với `DRAIN` đảo dấu. Ví dụ `INTAKE`, ngoài 1,20 m, trong 1,00 m → chênh 0,20 m; nếu `min_head_m = 0,10` thì đạt. Kiểm EC ngoài: ≥ ngưỡng chặn → `BLOCKED`; nằm giữa ngưỡng cho phép và ngưỡng chặn → `REVIEW_REQUIRED`; dưới ngưỡng cho phép → có thể `CONDITIONS_MET`. Ví dụ ngưỡng 120/150, EC ngoài 135 → "dải chuyển tiếp, không kết luận đủ điều kiện". Nếu chế độ `DRAIN` và `allow_drainage_with_saline_outside=True` thì bỏ qua kiểm EC ngoài.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm điều kiện mô phỏng (ví dụ mực nước trong tối thiểu khi lấy nước).
  - Không — muốn đổi luật rà soát phần B có tuổi mẫu 6 giờ/2 giờ thì sang `backend/domain/gate_intake_rules.py`.

### `backend/domain/gate_intake_rules.py`
- **Vai trò trong đời sống:** Như bảng kiểm tra trước khi cất cánh của phi công: từng mục (mẫu còn mới không, EC ngoài/trong dưới ngưỡng không, cao độ cùng hệ không, mực nước ngoài cao hơn trong đủ chưa, máy móc sẵn sàng chưa, có người đo không) được đánh dấu đạt/không đạt/thiếu. Kết quả chỉ là "đề nghị xem xét", không thay quy trình pháp lý và không phát lệnh.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: dict số đo phần B, (tùy chọn) hồ sơ quy tắc, bối cảnh dự báo (`mythoEc`, `projectedGateEc`, `p90Threshold`, `isHighVigilance`), thời điểm đánh giá ISO có múi giờ. Không đọc file. Đầu ra: dict `status`, `checks`, hash quy tắc và hash đầu vào, `validUntilIso`, `requiresOperatorReview=True`, `actuatorCommand=None`. Được `backend/api/gate_screening.py` gọi.
- **Hằng số `DEFAULT_PROFILE`:** EC ngoài tối đa `156.25` mS/m, EC trong tối đa `125`, chênh mực nước dương tối thiểu `0.05` m, tuổi mẫu tối đa `6` giờ bình thường và `2` giờ khi cảnh giác cao, EC tham chiếu P90 `60.42`.
- **Các hàm cốt lõi:**
  - `_text`, `_number`, `_nonnegative`, `_timestamp`, `_iso`: làm sạch chữ, số, thời gian (múi giờ không quá ±14 giờ).
  - `_hash(value)`: sha256 của dict sắp xếp khóa — "dấu vân tay" để sau này chứng minh đã đánh giá với đúng quy tắc và đúng đầu vào nào.
  - `_profile(value)`: kiểm hồ sơ quy tắc hợp lệ (ngưỡng không âm, tuổi mẫu cảnh giác cao không dài hơn bình thường).
  - `evaluate(...)`: Bước 1, quyết định có "cảnh giác cao" không: nếu EC Mỹ Tho ≥ P90 (60,42), hoặc EC dự kiến tại cống ≥ 0,8 × 156,25 = 125, hoặc bối cảnh đánh dấu cảnh giác. Ví dụ dự báo Mỹ Tho 80 ≥ 60,42 → cảnh giác cao → mẫu chỉ được cũ tối đa 2 giờ. Bước 2, kiểm từng mục; ví dụ đo lúc 7:00, đánh giá 10:00 → tuổi 3 giờ > 2 giờ → `MISSING_OR_EXPIRED`. Bước 3: có mục thiếu → `INSUFFICIENT_OR_EXPIRED_DATA`; có mục trượt → `NOT_SUITABLE`; tất cả đạt → `ELIGIBLE_FOR_REVIEW` ("Đề nghị xem xét lấy nước"). Nếu dữ liệu là `SIMULATION` thì thêm mục `FIELD_MEASUREMENT` thiếu, tức không chấp nhận số mô phỏng thay số đo.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi ngưỡng mặc định 156,25/125, tuổi mẫu 6/2 giờ, hay hệ số 0,8.
  - Có — nếu muốn thêm một mục kiểm (ví dụ độ đục).
  - Không — quy tắc tương tự phía giao diện nằm ở `frontend/src/shared/gate-intake-rules.js`; phải sửa cả hai cho khớp.

---

### `backend/services/workspace.py`
- **Vai trò trong đời sống:** Lễ tân chính của dữ liệu quan trắc: mở "thùng hàng" dữ liệu (bundle) rồi soạn các câu trả lời: tóm tắt, danh sách trạm, quan trắc của một trạm, danh mục cống, ranh giới tỉnh, mẫu hồ sơ cống. Cũng định nghĩa `WorkspaceError` dùng chung cho mọi service.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `backend/repositories/workspace.py` (`load_bundle`, `read_json`, `database_gates`, `candidate_stations`); file ranh giới `data/biengioi/Đồng Tháp - 63.geojson`, `Tiền Giang - 63.geojson`; mẫu `data/contracts/gate_input.json`, `gate_policy.json`, `station_gate_link.json`; thư mục artifact `runs/local_ec_backtest`. Đầu ra: dict/GeoJSON (GeoJSON là JSON dành cho bản đồ, mỗi điểm là một "Feature"). Không ghi.
- **Các hàm cốt lõi:**
  - `WorkspaceError(status_code, detail)`: lỗi kèm mã HTTP.
  - `load_bundle()`: gọi repository; nếu nguồn không dùng được thì báo 503 (không tự chuyển sang snapshot).
  - `summary()`: đếm trạm, mẫu, mẫu RIA2 (mã bắt đầu `RIA2_`), cống, ngày mẫu mới nhất; luôn ghi `live_forecast_available=False`, `gate_advice_available=False`, ước tính độ mặn `INSUFFICIENT_BASIS`.
  - `stations()`: trả FeatureCollection các trạm cho bản đồ.
  - `observations(site_code, date_from, date_to)`: lọc mẫu EC của một trạm theo khoảng ngày; mã trạm lạ → 404; ngày đảo ngược → 422.
  - `experiment(id)`, `artifact_path(id, filename)`: tìm thí nghiệm; chỉ cho phép một danh sách tên file cố định (ví dụ `metrics.csv`, `next_forecast.json`) và file phải nằm trong `runs/local_ec_backtest` (chống đọc file ngoài).
  - `boundaries()`: ghép ranh giới hai tỉnh, ghi chú "chưa xác minh nguồn".
  - `gates()`, `database_gates()`, `candidate_stations(gate_code, radius_km=50)`: danh mục cống và trạm gần cống trong bán kính (khoảng cách không chứng minh liên thông thủy lực).
  - `gate_template(kind, gate_code)`: trả mẫu hồ sơ `input`/`policy`/`link`, điền sẵn mã cống.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm một con số vào thẻ Tổng quan (`summary`).
  - Có — nếu muốn đổi bán kính mặc định tìm trạm gần cống.
  - Không — muốn đổi câu lệnh SQL đọc trạm/EC thì sang `backend/repositories/workspace.py`.

### `backend/services/multivariate.py`
- **Vai trò trong đời sống:** Người điều phối khi bạn bấm nút "Dự báo": kiểm tháng hợp lệ, tìm mô hình của trạm, đi lấy thời tiết tháng t−2 và (với Mỹ Tho) thủy văn tháng t−2, đưa cho bộ não `multivariate_ec.py` tính, rồi gói kết quả kèm nguồn gốc.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: dữ liệu request (`station`, `target_month`, `input_mode` = `ARCHIVE` hoặc nhập tay, 3 số thời tiết nếu nhập tay); `backend/repositories/multivariate_inputs.py` (`get_weather_input`), `hydrology_inputs.py` (`get_hydrology_input`); `backend/domain/multivariate_ec.py`. Đầu ra: dict dự báo có `prediction_id` (mã ngẫu nhiên uuid), `inputs`, `input_provenance`, `hydrology_provenance`, `training`, `metrics`. Không ghi (việc lưu nằm ở `dss_storage.py`).
- **Các hàm cốt lõi:**
  - `_target(value)`: tháng phải đúng dạng `YYYY-MM`, nếu không → 422.
  - `_input_month(target)`: tháng đích − 2. Ví dụ `2027-01` → `2026-11`.
  - `_catalog()`, `_station(station)`: lấy danh mục mô hình; lỗi → 503 kèm hướng dẫn.
  - `catalog()`: trả danh mục + tháng đích mặc định là tháng sau tháng hiện tại, `weather_lag_months=2`.
  - `evaluation(station, protocol, experiment, ec_delay_days)`: nếu giao thức `FROZEN_EC_WEATHER_ONLY_V1` thì đọc `ec_gap_evaluation.records`, không thì `evaluation_records` của mô hình.
  - `inputs(station, target_month)`: Mỹ Tho thiếu thủy văn → 422 ("Chưa đủ lưu lượng Kratie hoặc mực nước Tân Châu tháng t−2"), không tự thay bằng 0. Thời tiết phải đủ ngày, gió đơn vị `m/s`, `observed_through` đúng ngày cuối tháng t−2, và thời điểm "giả định có dữ liệu" không ở tương lai. Ví dụ hôm nay 17/11/2026 mà dữ liệu tháng 11 giả định có vào 05/12 → bị từ chối. Quy tắc mỗi tháng thủy văn cần ít nhất 20 ngày nằm trong `hydrology_inputs.py`, không ở file này.
  - `predict(payload)`: từ chối tháng đích ≤ tháng cuối huấn luyện (tránh hỏi mô hình điều nó đã học). Ghép thời tiết + thủy văn, gọi `models.predict_month`. Nếu phiên bản mô hình vừa đổi so với danh mục → 503. Gắn nguồn cho từng đặc trưng (`CALENDAR`, nguồn thủy văn, nguồn thời tiết), `conditional_on_user_inputs` khi nhập tay.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi thông báo lỗi khi thiếu thủy văn/khí tượng hoặc thêm thông tin vào kết quả trả về.
  - Không — muốn đổi công thức Random Forest hay kiểm hash thì sang `backend/domain/multivariate_ec.py`.
  - Không — muốn đổi luật ≥20 ngày/tháng thì sang `backend/repositories/hydrology_inputs.py`.

### `backend/services/forecasts.py`
- **Vai trò trong đời sống:** Người trưng bày "hồ sơ dự báo cũ" để đối chứng: dự báo thử nghiệm ngay sau mẫu quan trắc cuối và bảng ước tính EC theo thời tiết đã lưu. Luôn ghi rõ không phải dự báo hôm nay, không dùng để vận hành cống.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: file `next_forecast.json` của thí nghiệm (qua `artifact_path` trong `services/workspace.py`); `estimate_rows()` của `backend/repositories/workspace.py` (bảng ước tính cũ, theo CLAUDE.md là `data/models/future_ec_forecast_2024_2026.csv`). Đầu ra: dict có `deployment_ready=False`, `gate_decision_eligible=False`.
- **Các hàm cốt lõi:**
  - `next_forecast(experiment_id)`: kiểm `data_kind` là `EXPERIMENTAL_NEXT_AFTER_LAST_OBSERVATION`, mô hình chọn khớp, tháng đích là ngày 1 và sau ngày gốc dự báo, mỗi dòng đúng trạm/đơn vị, dòng thất bại không được có số EC. Sai → 503.
  - `normalize_station(value)`: viết thường, bỏ khoảng trắng và gạch dưới.
  - `monthly_estimates(station=None)`: kiểm từng dòng (tháng `YYYY-MM`, không trùng, số hữu hạn, EC/mưa/gió không âm), lọc theo trạm, tính EC lớn nhất, nhỏ nhất, trung bình. Ví dụ ba tháng 50, 70, 90 → trung bình 70.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm thống kê (ví dụ trung vị) cho bảng ước tính lịch sử.
  - Không — dự báo Mỹ Tho hiện hành nằm ở `backend/services/multivariate.py`; CSV cũ không thay được nó.

### `backend/services/gates.py`
- **Vai trò trong đời sống:** Người nhận hồ sơ cống ở quầy: tùy loại hồ sơ, chuyển cho "phòng mô phỏng" (`gate_simulation.simulate`) hoặc "phòng rà soát" (`gates.evaluate`), rồi đính kèm danh sách kiểm còn thiếu gì.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: dict `policy` và `data` từ request. Gọi `backend/domain/gates.py` và `backend/domain/gate_simulation.py`. Đầu ra: dict kết quả + `checklist` 4 mục (mực nước ngoài/trong, EC ngoài/trong), `missing_evidence`, `declarations_verified_by_server=False`, `evaluated_at`, ghi chú "EC tháng không xác định được giờ đóng/mở".
- **Các hàm cốt lõi:**
  - `review_dossier(policy, data)`: nếu `evaluation_mode == 'SIMULATION'` → `simulate`, ngược lại → `evaluate`. Gộp danh sách thiếu, loại trùng bằng `dict.fromkeys`. Với rà soát thật, luôn thêm `SERVER_VERIFIED_GATE_EVIDENCE` vào danh sách thiếu (máy chủ không tự xác minh được lời khai).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi nhãn tiếng Việt của 4 mục kiểm (`OBSERVATION_LABELS`).
  - Không — muốn đổi luật đạt/trượt thì sang `backend/domain/gate_simulation.py` hoặc `gates.py`.

### `backend/services/dss_storage.py`
- **Vai trò trong đời sống:** Thủ kho lưu trữ PostgreSQL cho DSS (hệ hỗ trợ ra quyết định): lưu dự báo, lưu bản nháp hồ sơ cống, đọc lại; và "phiên dịch" lỗi cơ sở dữ liệu thành câu dễ hiểu.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: request; gọi `backend/repositories/dss_storage.py` (đọc/ghi DB), `backend/services/multivariate.py` (tính lại dự báo). Đầu ra: dict từ DB. **Có ghi** vào PostgreSQL khi lưu dự báo/bản nháp (nếu đã bật).
- **Các hàm cốt lõi:**
  - `storage_errors(function)`: "lớp bọc" (decorator) đổi lỗi DB thành `WorkspaceError`: chưa bật lưu → 503 `DSS_WRITES_DISABLED`; mã SQL `23505` (trùng) → 409; `23514/23503/23502` (vi phạm ràng buộc) → 422; `42P01/42703/3F000` (thiếu bảng/schema) → 503; `42501` (thiếu quyền) → 503; khác → 503. Được `field_measurements.py` và `forecast_issues.py` dùng lại.
  - `presets()`: đọc các bộ ngưỡng có sẵn, ghi `is_operational_rule=False`.
  - `save_prediction(payload)`: **tính lại dự báo** từ request bằng `multivariate.predict` rồi mới lưu, không tin con số trình duyệt gửi lên.
  - `predictions(...)`, `prediction(id)`: đọc lịch sử dự báo; không thấy → 404.
  - `validate_draft(gate_code, data, policy)`: kiểm bản nháp: không quá 240.000 byte, lồng không quá 12 tầng, số hữu hạn, mã cống khớp ở mọi tầng, schema 1, chế độ `INTAKE`/`DRAIN`, chỉ cho chế độ `SIMULATION`, đơn vị `m` và `mS/m`. Sai → 422.
  - `save_draft(...)`, `drafts(...)`: lưu/đọc bản nháp.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi câu báo lỗi khi DB mất kết nối hay giới hạn kích thước bản nháp.
  - Không — muốn đổi câu SQL hay bảng lưu thì sang `backend/repositories/dss_storage.py` và `sql/`.

### `backend/services/field_measurements.py`
- **Vai trò trong đời sống:** Hộp thư nhận phiếu đo thực địa và bàn duyệt phiếu: nhận phiếu, chuẩn hóa, so với trung vị lịch sử để dán cờ, lưu ở trạng thái "chờ duyệt", rồi cho người duyệt chấp nhận/từ chối.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: dict phiếu; gọi `backend/domain/field_measurement.normalize` và `backend/repositories/field_measurements.py` (`historical_month_median`, `insert_measurement`, `list_measurements`, `insert_review`). Đầu ra: dict phiếu đã lưu (`status='PENDING'`, cờ). **Có ghi** vào DB.
- **Các hàm cốt lõi:**
  - `submit(raw)`: phiếu > 16 KiB → 413. Chuẩn hóa theo giờ Việt Nam; lỗi → 422. Nếu EC > 3 × trung vị lịch sử cùng khu vực/tháng thì thêm cờ `REVIEW_HIGH` (ví dụ trung vị 30, đo 100 → cờ).
  - `list_measurements(status, bbox)`: lọc theo trạng thái `PENDING/APPROVED/REJECTED` và khung bản đồ `minLon,minLat,maxLon,maxLat`.
  - `review(measurement_id, decision, reviewer, note)`: ghi quyết định duyệt; không thấy phiếu → 404.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi giới hạn 16 KiB hay hệ số 3 lần trung vị ở bước lưu.
  - Không — muốn đổi luật đổi đơn vị thì sang `backend/domain/field_measurement.py`.

### `backend/services/forecast_issues.py`
- **Vai trò trong đời sống:** Người giữ "sổ phát hành dự báo": đến lịch thì phát hành dự báo cho từng trạm, mỗi ô lịch (slot) chỉ phát hành **một lần**; nếu trễ hoặc thiếu dữ liệu thì ghi "bỏ lỡ" (MISSED) chứ không phát hành bù lặng lẽ; và tính điểm sai số tách riêng phát hành đúng giờ và trễ.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: trạm, tháng đích, giờ hiện tại; gọi `backend/domain/forecast_issue.py`, `backend/services/multivariate.py`, `backend/repositories/forecast_issues.py`, `write_connection` của `backend/repositories/dss_storage.py`. Đầu ra: dict trạng thái. **Có ghi** slot, bản phát hành, sự kiện bỏ lỡ vào DB.
- **Các hàm cốt lõi:**
  - `issue_for_station(station, target_month, now)`: chưa đến lịch → 422. Chạy dự báo `ARCHIVE`. Tạo slot; đã có bản phát hành → 409. Lấy giờ từ DB; trễ ≥ 1 giờ sau lịch → ghi `JOB_NOT_RUN`. Dự báo lỗi → ghi `MISSING_INPUT` (lỗi 422) hoặc `RUN_FAILED`. Thành công → `build_issue` rồi lưu.
  - `issue_month(target_month, schedule_code)`: phát hành cho 3 trạm. Không phát hành cho lịch trước ngày mở sổ 14/11/2026, không phát hành cho tháng hiện tại hoặc đã qua.
  - `audit_due(target_month, now)`: kiểm định kỳ; quá lịch 1 giờ mà chưa có bản phát hành → ghi `JOB_NOT_RUN`.
  - `list_issues(...)`: liệt kê slot, sự kiện, bản phát hành, điểm; tính MAE riêng theo nguồn (`MRC`, `FIELD_APPROVED`) và theo đúng giờ/trễ. Trường tóm tắt cũ chỉ dùng MRC để không trộn nguồn. Ví dụ 2 lần đúng giờ sai 10 và 20 → MAE đúng giờ = 15.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi khoảng trễ 1 giờ hay cách tính MAE theo nhóm.
  - Không — muốn đổi ngày/giờ lịch phát hành thì sang `backend/domain/forecast_issue.py`.

### `backend/services/spatial_inputs.py`
- **Vai trò trong đời sống:** Người chuẩn bị "bảng số từng tháng" cho bản đồ timeline: với mỗi tháng từ 06/1985 tới khoảng 12 tháng sau hiện tại, ghi EC ở Tân Châu, Mỹ Thuận, Mỹ Tho; tháng nào thiếu số đo thì lấp tạm và **dán nhãn là lấp**; tháng tương lai thì lấy dự báo hoặc kịch bản mùa. Kết quả được nhớ lại (cache) để kéo timeline không phải tính lại.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: bundle quan trắc (`load_bundle`), `estimate_rows()` và `data/models/future_ec_forecast_2024_2026.csv` (tính sha256), thời tiết tháng `get_monthly_weather`, thủy văn `get_hydrology_input`, gió `data/external/ec_feature_research_20261019/era5_extra_{trạm}.json`, registry `data/models/multivariate_registry.json` và file mô hình (để biết khi nào cần làm mới cache), `predict_month` của `multivariate_ec.py`. Đầu ra: dict theo tháng, mỗi tháng có `tan_chau_ec_mS_m`, `my_thuan_ec_mS_m`, `my_tho_ec_mS_m`, chế độ nội suy, g/L quy đổi, `boundary_provenance` (nguồn từng mốc), `data_regime`, `imputed`, `gate_decision_eligible=False`. Không ghi file.
- **Hằng số:** `STATIONS` (TanChau/MyThuan/MyTho → mã MRC), `SALINITY_FACTOR = 0.0064`.
- **Các hàm cốt lõi:**
  - `_number`, `_index`, `_months`: kiểm số; đổi tháng thành số đếm; liệt kê các tháng giữa hai mốc.
  - `_wind_file(path, mtime_ns, size)` (cache 4 bản) và `_winds(station)`: đọc gió ngày, đổi tốc độ + hướng thành hai thành phần u, v (`u = −tốc độ × sin(hướng)`, `v = −tốc độ × cos(hướng)`), lấy trung bình tháng; chỉ nhận tháng đủ ngày. Ghi chú: không phải u10/v10 gốc theo giờ của ERA5.
  - `_seasonal_wind_visuals(winds)`: trung bình vectơ gió cùng tháng 2010–2023 (cần ≥ 10 năm) chỉ để vẽ minh họa, không là đầu vào mô hình.
  - `_observed_months(bundle, site)`: gom mẫu EC đến 12/2023 theo tháng, bỏ mẫu cờ `INVALID`, lấy **trung bình cộng các mẫu có trong tháng** (không phải EC trung bình liên tục của tháng). Ví dụ tháng có 2 mẫu 40 và 60 → 50.
  - `_observation_or_fill(month, records)`: tháng có số → dùng. Thiếu → nếu có tháng trước và sau thì **nội suy theo thời gian**: ví dụ 01 có 40, 04 có 100, cần 02: trọng số = 1/3 → 40 × 2/3 + 100 × 1/3 = 60. Nếu chỉ có một phía (mép chuỗi) → lấy tháng gần nhất. Gắn `imputed=True`, `evidence_kind='SIMULATION_ONLY_IMPUTATION'`; không sửa mẫu gốc.
  - `_model_forecast(...)` (cache 48 bản): gọi `predict_month`; khóa cache có hash nguồn thời tiết/thủy văn nên dữ liệu đổi thì tính lại.
  - `_future_boundaries(month, station, observed, weather, today)`: cho tháng tương lai, nếu thời tiết tháng t−2 đủ, đúng `m/s` và đã "có" trước hôm nay (và Mỹ Tho có thủy văn) → dự báo bằng mô hình. Nếu không → **kịch bản mùa**: trung vị EC cùng tháng 2010–2023 (cần ≥ 10 năm). Ví dụ trung vị EC tháng 3 các năm = 120 → dùng 120, gắn `SEASONAL_MEDIAN_SCENARIO`.
  - `_monthly_inputs()`: dựng toàn bộ bảng. Trước 2024: dùng số đo/lấp; Mỹ Thuận thiếu thì để `None` và chế độ `TWO_STATION_FALLBACK_MISSING_MYTHUAN`. Từ 2024: dùng ước tính cũ, nhưng Mỹ Tho được thay bằng mô hình đang đăng ký khi đủ đầu vào. Quy đổi tham khảo g/L = EC × 0,0064 (ví dụ 150 mS/m → 0,96 g/L).
  - `_file_stamp`, `source_stamp(today)`: tạo "tem nguồn" gồm ngày hôm nay, tem bundle, tem các file CSV/registry/mô hình/gió và chữ ký nguồn thời tiết/thủy văn. Tem đổi ⇒ cache cũ không dùng nữa.
  - `monthly_inputs()`: tra cache theo tem; có → `FRESH`. Không có → tính mới, giữ tối đa 2 bản. Nếu tính mới lỗi nhưng có bản cũ **cùng ngày** → trả bản cũ kèm `cache_status='STALE'` (báo rõ, không giấu). `cache_metadata()`, `_clear_monthly_cache()`: đọc trạng thái cache, xóa cache.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi cách lấp tháng thiếu (nội suy thời gian / tháng gần nhất) hoặc mốc 10 năm của kịch bản mùa.
  - Có — nếu thấy timeline không cập nhật sau khi đổi dữ liệu: kiểm `source_stamp`.
  - Không — muốn đổi màu sông, 35 đoạn hay biên cửa sông thì sang `backend/services/spatial_simulation.py`.

### `backend/services/spatial_simulation.py`
- **Vai trò trong đời sống:** Họa sĩ vẽ bản đồ sông theo tháng: chia sông Tiền thành 35 đoạn 5 km, tô màu theo EC nội suy, tìm "vạch mặn" 1 g/L và 4 g/L, và chấm màu cho từng cống theo EC ước lượng phía ngoài cống. Đầu file ghi rõ: trục sông, biên cửa sông, liên kết thủy lực và hệ số dòng chảy là **giả định minh họa**; không ghi gì vào dữ liệu quan trắc hay quy trình cống.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `data/biengioi/tien_river_corridor.geojson` (đường sông, đối tượng `TIEN_MAIN`), `data/8file/03_sluice_gates_190_and_27_verified_gis.csv` (danh mục cống, chỉ dòng `is_verified_27_headworks = true`), cống trong bundle và PostgreSQL (`store.database_gates`), bảng tháng từ `spatial_inputs.monthly_inputs`, hàm `interpolate_anchors`. Đầu ra: dict/GeoJSON cho API bản đồ, luôn kèm `gate_decision_eligible=False`, `actuator_command=None`. Không ghi.
- **Hằng số:** tọa độ trục `TAN_CHAU`, `MY_THO`, `ESTUARY`; `METHODOLOGY` mô tả nội suy tuyến tính 3 trạm và quy đổi 0,0064 g/L mỗi mS/m; `GATE_ADVISORIES` gồm 3 mức màu xanh `#10b981`, vàng `#f59e0b`, đỏ `#ef4444`.
- **Các hàm cốt lõi:**
  - `ec_to_salinity_g_l(ec)`: g/L ≈ 0,0064 × EC, làm tròn 3 số. Ví dụ 200 mS/m → 1,28 g/L. Chỉ là quy đổi tham khảo, không phải độ mặn đo.
  - `gate_state(ec, open_below=120.0, close_at_or_above=150.0)`: EC < 120 → `OPEN_INTAKE`; EC ≥ 150 → `CLOSED_SALINITY_BARRIER`; giữa → `CAUTION_TRANSITION`. Ví dụ 100 → xanh, 135 → vàng, 160 → đỏ. Tên mức nghe như "mở/đóng" nhưng chỉ là **mức cảnh báo màu theo EC nội suy và cặp ngưỡng đang chọn**; không phản ánh cống thực sự đang mở hay đóng, và không phải lệnh.
  - `_read_corridor()`: đọc và kiểm đường sông (bắt đầu đúng Tân Châu, kết thúc đúng cửa sông, Mỹ Tho ở giữa). `_point`: kiểm tọa độ. `_distance_km`: khoảng cách trên mặt cầu Trái Đất (công thức haversine, bán kính 6371,0088 km).
  - `RiverAxis`: "thước đo dọc sông". Tính khoảng cách thực giữa các đỉnh đường sông rồi **co giãn** để Tân Châu = km 0, Mỹ Tho = km 125, cửa sông = km 175. `coordinate(km)` đổi km thành tọa độ; `section(start, end)` cắt một đoạn; `project(point)` chiếu một cống lên trục sông gần nhất, trả km và khoảng cách tới trục, kèm `hydrological_link_validated=False` (chưa chứng minh nối thủy lực).
  - `_catalog_gates(bundle, corridor)`: gộp cống từ CSV, bundle, PostgreSQL; cống không có tọa độ thì **không bịa** vị trí mà đưa vào danh sách loại trừ.
  - `simulation_corridor()`, `simulation_timeline()`: trả đường sông + cống; trả toàn bộ bảng tháng + trạng thái cache.
  - `_month(year_month)`: kiểm `YYYY-MM`, lấy dữ liệu tháng; không có → 404.
  - `_anchors(month)`: tạo mốc: (0, Tân Châu), (85,2, Mỹ Thuận nếu có), (125, Mỹ Tho), (175, cửa sông). Cửa sông là **kịch bản chưa hiệu chuẩn**: mùa khô (tháng 12, 1, 2, 3, 4) nhân 6,0, mùa khác 1,5, cộng thêm 0,4 × chênh Mỹ Tho − Tân Châu nếu dương. Ví dụ mùa khô Mỹ Tho 100, Tân Châu 20 → 100 × 6 + 80 × 0,4 = 632 mS/m. Tháng từ 2024 mà thiếu Mỹ Thuận → 503.
  - `_idw(chainage, anchors)`: tên cũ (IDW là "trọng số nghịch đảo khoảng cách") được giữ để không vỡ chỗ gọi cũ, nhưng **bên trong đã là nội suy tuyến tính** (gọi `interpolate_anchors`).
  - `_segments(month, axis, threshold)`: 35 đoạn × 5 km; EC tại giữa đoạn, đầu, cuối và các điểm đổi màu; quy đổi g/L; hướng chảy minh họa (`UPSTREAM_SALINE_INTRUSION` khi mùa khô và EC ≥ ngưỡng) với hệ số tốc độ 0,2–1,5 (`flow_basis='ILLUSTRATIVE_SEASON_AND_EC_PROXY'`, không đo dòng chảy).
  - `interpolate_river_profile(year_month, threshold=150.0)`: trả các đoạn sông của một tháng.
  - `_isohalines(anchors, axis)`: tìm chỗ EC chạm 1 g/L (= 1/0,0064 = 156,25 mS/m) và 4 g/L (= 625 mS/m) bằng **chia đôi** 45 lần (giống đoán số: "lớn hơn hay nhỏ hơn?" rồi thu hẹp một nửa mỗi lần). Trả vị trí "vạch mặn" và quãng xâm nhập tính từ km 175; nếu cửa sông còn dưới ngưỡng → `NOT_REACHED_AT_ESTUARY`.
  - `simulation_frame(year_month, open_below_ec=120.0, close_above_ec=150.0)`: hàm chính cho một khung bản đồ: kiểm ngưỡng (ngưỡng mở phải nhỏ hơn ngưỡng chặn, sai → 422), chiếu từng cống lên trục, nội suy EC ngoài cống, gán mức màu, trả đoạn sông, vạch mặn, gió, điều kiện biên, và khối `assumptions` liệt kê mọi giả định (`estuary_calibration_status='UNCALIBRATED_SCENARIO'`, `flow_is_measured=False`, `geometry_status='REPRESENTATIVE_SCHEMATIC'`).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi ngưỡng mặc định 120/150, hệ số khuếch đại cửa sông 6,0/1,5, số đoạn 35, hay tháng mùa khô.
  - Có — nếu muốn thêm vạch mặn khác (ví dụ 2 g/L) vào `_isohalines`.
  - Không — muốn đổi màu vẽ, chấm cống tròn, hay không tô đoạn sau cống thì sang frontend `frontend/src/features/observations-map.js`, `gated-waterways.js`, `simulation.css`.
