## 2.F. Kịch bản (scripts) chạy tay: thu thập, kiểm tra, thí nghiệm, huấn luyện

Phần này mô tả các tệp trong `scripts/` (kể cả `scripts/utilities/`), `data_collection/` và `etl/etl_csv.py`. Hãy hình dung chúng là **"công cụ chạy tay"**: giống bộ dụng cụ trong kho, chỉ lấy ra khi cần. Khi bạn mở trang web bằng `.\start.ps1`, **không có tệp nào ở đây được gọi**. Trang web chỉ đọc kết quả mà các công cụ này đã để lại từ trước (mô hình đã lưu, tệp CSV/JSON, bảng trong cơ sở dữ liệu).

**Cảnh báo quan trọng trước khi chạy bất kỳ tệp nào:**

- Một số kịch bản **GHI vào cơ sở dữ liệu PostgreSQL (GHI DB)**. Phần lớn chỉ ghi khi bạn thêm cờ `--apply`. Không có `--apply` thì chúng chỉ "xem trước" (in kế hoạch). Đừng thêm `--apply` để "thử cho biết".
- Nhiều kịch bản **GHI đè tệp trong `outputs/`, `runs/`, `data/`**. Các thư mục này là bằng chứng của báo cáo. Chạy lại có thể làm số liệu khác với báo cáo đã nộp.
- `scripts/train_mytho_hydrology_primary.py` **ghi vào `data/models/multivariate_registry.json`**, tức là đổi mô hình mà trang web dùng. Không chạy khi chưa có quyết định rõ ràng.
- Một số kịch bản tải dữ liệu từ Internet. Chạy lại có thể nhận số liệu đã bị nguồn sửa đổi.
- Nhiều kịch bản nhập hàm từ thư mục `tools/` (ví dụ `tools.feature_building`, `tools.model_training`, `tools.backtest_protocols`). Tại thời điểm viết, `tools/` **chưa được commit vào Git**. Nếu thiếu thư mục này, các kịch bản đó sẽ báo lỗi khi chạy.

**Giải thích nhanh vài thuật ngữ dùng nhiều lần bên dưới:**

- **Artifact (sản phẩm mô hình):** tệp mô hình đã học xong và được lưu lại, ví dụ `model.joblib`, kèm `manifest.json` mô tả cách tạo ra nó. Giống một chiếc bánh đã nướng xong, kèm tờ công thức.
- **Manifest:** tệp JSON ghi "lý lịch" của một lần chạy: dùng tệp nào, mã băm (hash) của tệp, tham số, điểm số. Mã băm SHA-256 giống dấu vân tay của tệp: chỉ cần tệp đổi một byte, mã băm đổi hoàn toàn.
- **Backtest (kiểm tra hồi cứu):** giả vờ quay lại quá khứ, dự báo cho các tháng đã có kết quả thật, rồi so sánh. Giống làm lại đề thi năm cũ để xem mình được bao nhiêu điểm.
- **As-of ("biết được tới thời điểm"):** khi giả vờ dự báo vào ngày X, chỉ được dùng dữ liệu thực sự đã công bố trước ngày X. Ví dụ: dự báo tháng 03 được phát hành ngày 06/02; số liệu tháng 12 được giả định công bố vào cuối tháng +5 ngày (05/01), nên được dùng; số liệu tháng 01 phải đợi tới 05/02, cũng kịp; nhưng EC tháng 02 thì chưa có.
- **Rolling origin (điểm gốc lăn):** mỗi tháng học lại mô hình với toàn bộ dữ liệu đã biết tới lúc đó, rồi dự báo tháng kế tiếp. Giống mỗi tuần ôn bài thêm rồi làm một bài kiểm tra mới.
- **Khóa EC (frozen EC):** giả định trạm Mỹ Tho ngừng gửi EC suốt 24 hoặc 36 tháng. Mô hình chỉ được học một lần trước lúc ngừng; EC thật sau đó chỉ dùng để chấm điểm.
- **MAE / RMSE:** hai cách đo sai số, đơn vị mS/m. MAE là sai lệch trung bình. Ví dụ dự báo 120 khi thật là 100 (sai 20), dự báo 50 khi thật là 80 (sai 30), thì MAE = (20 + 30) / 2 = 25. RMSE bình phương sai số trước khi lấy trung bình rồi khai căn, nên phạt nặng các lần sai lớn: RMSE = căn((400 + 900) / 2) ≈ 25,5. Số càng nhỏ càng tốt, nhưng chỉ so được khi cùng tháng, cùng giao thức.
- **Persistence (giữ giá trị cuối):** cách dự báo "ngây thơ": tháng sau bằng EC lần đo cuối cùng. Dùng làm mốc so sánh.
- **Migration (di chuyển cấu trúc CSDL):** một tệp SQL tạo hoặc sửa bảng trong cơ sở dữ liệu. Giống bản vẽ thêm phòng cho ngôi nhà. Áp dụng xong là thay đổi thật.
- **Dry run / plan only (chạy nháp):** chỉ in ra việc sẽ làm, không làm thật.
- **Rollback (hoàn tác):** chạy trong giao dịch (transaction) rồi hủy, để cơ sở dữ liệu không đổi.

---

### (1) Huấn luyện và dự báo mô hình đang phục vụ

### `scripts/train_mytho_hydrology_primary.py`
- **Vai trò trong đời sống:** Đây là "lò nướng" tạo ra mô hình Mỹ Tho mà trang web đang dùng (`20261108T_HYDROLOGY_PRIMARY_V1`). Giống thợ làm bánh nướng mẻ bánh chính thức, dán nhãn, rồi đặt lên kệ bán hàng (registry).
- **I/O:**
  - Đọc: `data/research/mrc_ec_monthly_samples.csv` (EC Mỹ Tho), `data/external/multivariate_weather/manifest.json` và dữ liệu khí tượng qua `backend.repositories.multivariate_inputs`, CSV thủy văn Kratie/Tân Châu qua `backend.repositories.hydrology_inputs.source_paths()`, `outputs/frozen_ec_remedies_20261108/predictions.csv` và `outputs/frozen_ec_gap_20261104/predictions.csv` (điểm đánh giá đã có sẵn).
  - Ghi: **GHI runs/**: `runs/multivariate_ec/mytho/20261108T_HYDROLOGY_PRIMARY_V1/model.joblib`, `predictions.csv`, `manifest.json`. **GHI cấu hình mô hình đang phục vụ**: thay mục `MYTHO` trong `data/models/multivariate_registry.json`. Không ghi DB.
  - Thư mục đích được tạo với `exist_ok=False`: nếu thư mục phiên bản đã tồn tại, kịch bản báo lỗi và dừng, không ghi đè.
- **Hàm chính:**
  - `train()` — hàm làm mọi việc. Các bước:
    1. Lấy bảng học bằng `data_matrix(5)` (từ `tools.feature_building`, độ trễ công bố EC 5 ngày). Kiểm tra: tháng cuối phải là 12/2023, không trùng tháng, ít nhất 400 dòng, EC hữu hạn.
    2. Đọc lại điểm ba kỳ khóa EC (`gap_2019_2021` gọi là validation, `gap_2022_2023` gọi là holdout, `gap_2021_2023` gọi là primary_gap) bằng `evaluation_rows()`.
    3. Tính MAE/RMSE bằng `metrics()` cho 4 cách: `RandomForest`, `FrozenPersistence`, `MonthlyClimatology`, `FrozenSeasonalRepeat`.
    4. Học Random Forest (300 cây, sâu tối đa 8, tối thiểu 3 mẫu/lá, seed 42) trên 10 đặc trưng `FEATURES + HYDRO_FEATURES`.
    5. So khớp: giá trị thủy văn dùng khi học phải trùng khớp tuyệt đối với giá trị mà trang web sẽ tính khi phục vụ (`_matrix(_signature())`). Lệch là dừng.
    6. Lưu mô hình, ghi manifest (thứ tự đặc trưng, đơn vị, hash nguồn, độ quan trọng đặc trưng, `deployment_ready=False`), rồi cập nhật registry với hash mô hình và hash manifest.
  - `evaluation_rows(experiment, split)` — ghép bảng dự báo của hai thí nghiệm khóa EC, kiểm tra số tháng (24 hoặc 36) và giá trị thật phải trùng nhau.
  - `metrics(rows)` — tính MAE/RMSE cho từng cách dự báo.
  - `sha(path)` — tính dấu vân tay SHA-256 của tệp.
  - Ví dụ số: ở kỳ 2021–2023, RF khí tượng + thủy văn đạt MAE 16,57 và RMSE 31,21 mS/m (theo CLAUDE.md). Nghĩa là trung bình mỗi tháng lệch khoảng 16,6 mS/m, nhưng có vài tháng lệch lớn kéo RMSE lên gần gấp đôi.
- **Có tìm đến file này không?:** Có. Khi cần biết mô hình Mỹ Tho đang chạy được tạo ra thế nào. Chỉ đọc, đừng chạy khi chưa quyết định đổi mô hình.

### `scripts/forecast_mytho_ec_hydrology.py`
- **Vai trò trong đời sống:** Bản "dự báo thử" EC Mỹ Tho cho **tháng 11/2026** bằng dòng chảy thượng nguồn, không cần EC gần đây. Giống bản nháp làm ở nhà, không phải bài nộp chính thức. Nó **không** dùng mô hình đang phục vụ: nó tự học một RF khác (100 cây, sâu 7, `max_features=0.8`) với bộ đặc trưng khác (thêm `soil_t2`, `wind_u_t2`, `wind_v_t2`).
- **I/O:**
  - Đọc: `data/research/mrc_ec_monthly_samples.csv`, `data/external/ec_hydrology_current_20261029/era5_extra_MyTho_2026-09.json`, khí tượng qua `get_weather_input("MYTHO", ...)`, Kratie và Tân Châu qua `tools.feature_building` (`data/external/mrc_kratie_discharge_20261029/...`, `data/external/tien_manual_long_20261029/019803_Water_Level_Manual_3bd17f3a.csv`, `data/external/tien_manual_2024_2026_20261029/...`), điểm backtest ở `outputs/ec_long_hydrology_20261029/no_recent_ec/predictions_{5,35}d.csv`.
  - Ghi: **GHI outputs/**: `outputs/ec_hydrology_forecast_20261029/mytho_no_recent_ec_model.joblib`, `forecast_2026_11.csv`, `manifest.json`. Không ghi DB, không đổi registry.
- **Hàm chính:**
  - `current_row()` — dựng một dòng đặc trưng cho tháng đích 2026-11 từ thời tiết tháng 2026-09 (t−2). Kiểm tra tháng thời tiết đầy đủ 30 ngày và "đã có" trước ngày phát hành giả định 06/10/2026. Đổi hướng gió sang hai thành phần u, v.
  - `main()` — học mô hình bằng `fit_candidate_model("rf", ...)` trên dữ liệu đến 12/2023, dự báo (giá trị âm bị cắt về 0), tính lại MAE backtest cho độ trễ 5 và 35 ngày, rồi lưu kết quả với nhãn `RESEARCH_FORECAST_NO_POST_2023_EC_VALIDATION`.
  - `sha(path)` — dấu vân tay tệp.
- **Có tìm đến file này không?:** Ít. Chỉ khi cần xem lối dự báo nghiên cứu bằng dòng lệnh (CLI). Trang web không gọi tệp này. Lưu ý: mô hình ở đây khác mô hình chính.

### `scripts/issue_monthly_forecast.py`
- **Vai trò trong đời sống:** "Thư ký phát hành bản tin dự báo hằng tháng". Mỗi tháng, vào 09:00 ngày 06 của tháng trước tháng đích (lịch `MONTHLY_D06_PREV`), nó phát hành dự báo cho ba trạm và ghi vào sổ. Giống đóng dấu ngày lên phong bì rồi niêm phong, để sau này không ai sửa lùi được.
- **I/O:**
  - Đọc: cấu hình cục bộ qua `run_webgis.load_local_env` (không in ra), dữ liệu đầu vào qua `backend.services.forecast_issues`.
  - Ghi: **GHI DB** (chỉ khi `--apply` hoặc `--audit-due`) vào các bảng sổ phát hành trong schema `dss_reference` (ví dụ `dss_reference.forecast_slot`, `forecast_slot_event`, `forecast_issue`, thông qua `backend/repositories/forecast_issues.py`). Không có cờ thì chỉ in xem trước.
- **Tùy chọn:** `--target-month YYYY-MM` (mặc định: tháng kế tiếp theo giờ Việt Nam), `--apply` (phát hành dự báo cho 3 trạm MYTHO, MYTHUAN, TANCHAU), `--audit-due` (ghi lại các lượt lịch đã quá hạn mà không phát hành). Hai cờ `--apply` và `--audit-due` không dùng chung được.
- **Hàm chính:**
  - `main()` — tính tháng đích hợp lệ: bỏ qua lịch trước ngày mở sổ 14/11/2026 (`LEDGER_START_LOCAL`) và lịch đã qua hơn 1 giờ. Sau đó gọi `issue_month(target)` hoặc `audit_due(target)`.
  - `next_month(value)` (hàm lồng bên trong) — cộng thêm một tháng.
  - Ví dụ: tháng đích 2027-01 thì lịch phát hành là 06/12/2026 09:00. Hệ thống từ chối phát hành lùi cho tháng hiện tại hoặc tháng đã qua.
- **Có tìm đến file này không?:** Có, khi làm phần "sổ phát hành dự báo" và cách chấm điểm dự báo thật sau này.

### `scripts/score_forecast_issues.py`
- **Vai trò trong đời sống:** "Giám khảo chấm bài sau khi có đáp án". Khi có EC đo thật cho tháng đã dự báo, nó tính sai số tuyệt đối và ghi điểm vào sổ.
- **I/O:**
  - Đọc: danh sách bản phát hành qua `backend.services.forecast_issues.list_issues`; nhãn EC MRC qua `backend.repositories.forecast_issues.candidate_mrc_label`; nhãn đo hiện trường đã duyệt qua `backend.repositories.field_measurements.candidate_field_label`.
  - Ghi: **GHI DB** (chỉ khi `--apply`): thêm một dòng điểm vào `dss_reference.forecast_score` qua `repo.insert_score`.
- **Hàm chính:**
  - `main()` — duyệt từng lượt (trạm + tháng). Bỏ qua lượt không có bản phát hành (MISSED), lượt đã chấm, và tháng ≤ 12/2023 (nằm trong giai đoạn học). Tìm nhãn MRC trước, không có thì tìm nhãn hiện trường. Gọi `score()` (giao thức `MONTHLY_EC_LABEL_V1_20261114`). In sai số; nếu có `--apply` thì ghi.
  - Ví dụ: dự báo 120 mS/m, đo thật 95 mS/m, thì sai số tuyệt đối = 25 mS/m.
- **Có tìm đến file này không?:** Có, cùng nhóm với `issue_monthly_forecast.py`.

### `scripts/run_future_forecast_2024_2026.py`
- **Vai trò trong đời sống:** Dùng các mô hình chỉ có khí tượng (t−2) đã đăng ký để ước tính EC cho ba trạm trong giai đoạn 2024–2026 khi thiếu EC đo. Giống đoán điểm thi của các năm chưa có bảng điểm.
- **I/O:** Đọc registry và khí tượng qua `backend.domain.multivariate_ec`, `backend.repositories.multivariate_inputs`. **GHI data/**: `data/models/future_ec_forecast_2024_2026.csv` và tệp manifest đi kèm (`.manifest.json`); có nhắc thư mục lưu trữ `outputs/frozen_ec_gap_20261104/archive_before_sync`.
- **Hàm chính:** `run_future_forecast()` — chạy dự báo cho các tháng thiếu EC; `digest()` — mã băm.
- **Có tìm đến file này không?:** Ít. Theo CLAUDE.md, CSV này là bản nghiên cứu cũ, không phải đầu ra của mô hình Mỹ Tho chính hiện hành.

### `scripts/integrate_mythuan.py`
- **Vai trò trong đời sống:** Đóng gói mô hình trạm Mỹ Thuận và bổ sung số đo Mỹ Thuận có nguồn vào bộ dữ liệu nghiên cứu. Giống thêm một học sinh mới vào sổ lớp, kèm hồ sơ.
- **I/O:** Đọc `data/external/tien_multisite_20261029_verified`, `data/external/mythuan_weather_20261104`, `outputs/mythuan_three_station_20261104/run_manifest.json`. **GHI data/ và runs/**: `data/research/mrc_ec_monthly_samples.csv`, `data/research/workspace.json`, `runs/multivariate_ec/mythuan/.../manifest.json` và `predictions.csv`, **ghi `data/models/multivariate_registry.json`**.
- **Hàm chính:** `mythuan_records()` — dựng các dòng số đo; `integrate_data()` — ghép vào workspace; `register_model()` — đăng ký mô hình Mỹ Thuận vào registry; `extend_forecasts()` — nối thêm dự báo; `archive_audit_inputs()` — lưu bản sao đầu vào để kiểm tra.
- **Có tìm đến file này không?:** Ít, chỉ khi truy nguồn mô hình/dữ liệu Mỹ Thuận. Ghi registry, nên không chạy tùy tiện.

### `scripts/train_ec_compact_candidate.py`
- **Vai trò trong đời sống:** Học mô hình "RF_compact" (ứng viên gọn, chọn theo kỳ kiểm định) làm sản phẩm nghiên cứu. Đây là ứng viên cũ, không phải mô hình đang phục vụ.
- **I/O:** Đọc `data/research/mrc_ec_monthly_samples.csv`, `data/external/ec_feature_research_20261019/era5_extra_MyTho.json`, `data/external/ec_hydrology_current_20261029/era5_extra_MyTho_2026-09.json`, CSV mực nước Tân Châu, `outputs/ec_extreme_robust_20261029`. **GHI outputs/**: `outputs/ec_compact_candidate_20261029` (có `joblib`).
- **Hàm chính:** `main()` — học và lưu; `sha()` — mã băm.
- **Có tìm đến file này không?:** Ít, chỉ để truy lịch sử chọn mô hình.

### `scripts/rf_compact_artifacts.py`
- **Vai trò trong đời sống:** Đóng gói lại kết quả backtest của RF_compact thành "hồ sơ thí nghiệm" chuẩn và tính một dự báo tháng kế tiếp để lưu trữ.
- **I/O:** Đọc `data/research/mrc_ec_monthly_samples.csv`, khí tượng, CSV Tân Châu, `outputs/ec_extreme_robust_20261029`. **GHI runs/**: `runs/local_ec_backtest/...` (CSV, JSON, hình vẽ qua `savefig`).
- **Tùy chọn:** `--lag`.
- **Hàm chính:** `historical_predictions()` — lấy lại dự báo cũ; `make_metrics()`, `make_high_ec_metrics()` — điểm chung và điểm cho tháng EC cao; `next_forecast()` — dự báo tháng tới; `plot_predictions()` — vẽ biểu đồ; `build_run()`, `main()` — ghép lại.
- **Có tìm đến file này không?:** Ít.

### `scripts/update_workspace_with_rf_compact.py`
- **Vai trò trong đời sống:** Cập nhật bộ dữ liệu snapshot của trang web để gắn thêm hai thí nghiệm RF_compact, không đụng vào số đo gốc.
- **I/O:** Đọc `runs/local_ec_backtest/MYTHO_RF_COMPACT_20261030`, `runs/local_ec_backtest/MYTHO_RF_COMPACT_LAG30_20261030`. **GHI data/**: `data/research/workspace.json`, `workspace_manifest.json`, `experiment_registry.json`.
- **Hàm chính:** `update_workspace()`, `read_json()`.
- **Có tìm đến file này không?:** Ít.

---

### (2) Đánh giá và thí nghiệm giảm sai số (nghiên cứu)

Các tệp ở đây **không** thay mô hình đang phục vụ. Chúng ghi vào `outputs/`. Kết quả là bằng chứng cho báo cáo, không phải nâng cấp đã đưa lên web.

### `scripts/evaluate_frozen_ec_gap.py`
- **Vai trò trong đời sống:** Diễn tập tình huống "trạm Mỹ Tho mất liên lạc 2–3 năm, nhưng thời tiết vẫn có hằng tháng". Mô hình được học một lần ngay trước lúc mất EC, rồi dự báo từng tháng. EC thật chỉ đưa cho người chấm. Giống học sinh ôn thi xong thì bị thu sách, phải làm liên tục 36 bài mà không được xem đáp án.
- **I/O:**
  - Đọc: `data/research/mrc_ec_monthly_samples.csv`, `data/external/multivariate_weather/manifest.json` (qua `tools.model_training.training_frame`), `data/models/multivariate_registry.json` (chỉ để ghi hash mô hình đang chạy vào manifest), `data/models/future_ec_forecast_2024_2026.csv` (chỉ lấy hash).
  - Ghi: **GHI outputs/**: `outputs/frozen_ec_gap_20261104/{predictions.csv, metrics.csv, interpolation_predictions.csv, interpolation_metrics.csv, baseline_availability.csv, run_manifest.json}`. Với `--publish`: **ghi thêm `data/models/frozen_ec_gap_evaluation.json`** (tệp mà API đọc để hiển thị điểm đánh giá). Không đổi trọng số mô hình.
- **Tùy chọn:** `--output` (thư mục ghi), `--publish`.
- **Hàm chính:**
  - `freeze_training(data, first_target, ec_delay_days)` — "khóa sổ": chỉ giữ các tháng EC và thời tiết đã công bố trước ngày phát hành đầu tiên.
  - `forecast_gap(known, weather_features)` — học RF (cùng tham số 300/8/3/42) và 4 mốc so sánh: `FrozenPersistence` (giữ EC cuối), `MonthlyClimatology` (trung bình cùng tháng các năm), `FrozenSeasonalRepeat` (EC gần nhất của cùng tháng), `SeasonalityOnlyRF` (RF chỉ biết tháng mấy). Kiểm tra nghiêm ngặt: thời tiết phải là tháng t−2 và đã có trước ngày phát hành.
  - `station_metrics(predictions)` — tính điểm theo nhiều nhóm: toàn kỳ, từng năm, mùa khô tháng 12–4, tháng EC cao (≥ phân vị 90 của tập học).
  - `spatial_predictions()` / `spatial_metrics()` — thử nội suy dọc sông tại Mỹ Thuận từ dự báo hai đầu (Tân Châu, Mỹ Tho) và ba mốc.
  - `run()` — vòng lặp 3 kỳ (`gap_2019_2021`, `gap_2021_2023`, `gap_2022_2023`) × 2 độ trễ EC (5 và 35 ngày) × 3 trạm. `publish()` — trỏ API tới manifest.
  - Ví dụ: kỳ `gap_2019_2021` với độ trễ 5 ngày. Ngày phát hành đầu tiên là 06/12/2018, nên EC cuối được học là 11/2018 (cuối tháng 30/11 cộng 5 ngày = 05/12). Mô hình dự báo 36 tháng từ 01/2019 tới 12/2021 mà không thấy EC mới nào.
- **Có tìm đến file này không?:** Có. Đây là gốc của giao thức "khóa EC" mà báo cáo dùng.

### `scripts/evaluate_frozen_ec_gap_remedies.py`
- **Vai trò trong đời sống:** Cùng tình huống mất EC như trên, nhưng thử "thuốc chữa": thêm dữ liệu thủy văn (Kratie, Tân Châu), thêm EC của trạm hàng xóm, hoặc cả hai. Giống thử xem học sinh làm bài tốt hơn nếu được tham khảo thêm bản đồ hoặc bài của bạn bên cạnh.
- **I/O:** Đọc `data/research/mrc_ec_monthly_samples.csv`, `data/external/multivariate_weather/manifest.json`, dữ liệu thủy văn qua `tools.feature_building`. **GHI outputs/**: `outputs/frozen_ec_remedies_20261108/{predictions.csv, metrics.csv, run_manifest.json}`.
- **Tùy chọn:** `--output`.
- **Hàm chính:**
  - `CANDIDATES` (bảng cấu hình) — 4 ứng viên: `WeatherOnly`, `WeatherHydrology`, `WeatherNeighborEC`, `WeatherHydrologyNeighborEC`. Thủy văn gồm `kratie_q_t2`, `kratie_q3_t2`, `kratie_q_ratio_t2`, `tc_stage_t2`, `tc_stage3_t2`.
  - `neighbor_asof_features(months, samples, delay)` — lấy EC mới nhất của Mỹ Thuận/Tân Châu **đã công bố** trước ngày phát hành.
  - `forecast_candidates(known, future)` — học từng ứng viên một lần, kiểm tra không có EC Mỹ Tho bị giấu lọt vào đầu vào.
  - `metrics()`, `run()` — tính điểm và ghi manifest.
  - Ví dụ số (CLAUDE.md): `WeatherHydrology` đạt MAE/RMSE 57,81/133,82 ở 2019–2021; 16,57/31,21 ở 2021–2023; 12,19/25,43 ở 2022–2023. Ở 2022–2023, cách giữ EC cuối lại tốt hơn (10,76/16,46). Mẫu 692 mS/m (15/03/2020) vẫn bị dự báo thấp (213,67).
- **Có tìm đến file này không?:** Có. Đây là bằng chứng chính cho việc chọn mô hình khí tượng + thủy văn.

### `scripts/evaluate_frozen_ec_followup.py`
- **Vai trò trong đời sống:** Vòng thử tiếp theo: thêm EC của từng trạm riêng, hoặc dùng mô hình đường thẳng (Ridge), hoặc Ridge kết hợp RF sửa phần sai còn lại.
- **I/O:** Đọc `data/research/mrc_ec_monthly_samples.csv`, `data/external/multivariate_weather/manifest.json`, kết quả của `evaluate_frozen_ec_gap_remedies.py`. **GHI outputs/**: `outputs/frozen_ec_followup_20261108/{predictions.csv, metrics.csv, run_manifest.json}`.
- **Tùy chọn:** `--output`.
- **Hàm chính:**
  - `NEW_CANDIDATES` — `HydroMyThuanEC`, `HydroTanChauEC`, `HydroRidge`, `HydroRidgeResidualRF`.
  - `ridge_model()` — Ridge (alpha 10) có điền giá trị thiếu bằng trung vị và chuẩn hóa thang đo.
  - `predict_extensions(known, future)` — chạy lại 4 ứng viên cũ rồi thêm 4 ứng viên mới trên đúng cùng các tháng.
  - `run()`, `sha()` (bỏ khác biệt xuống dòng Windows/Linux khi băm tệp `.py`).
  - Ví dụ số (CLAUDE.md): thêm cả hai EC giảm RMSE 2021–2023 từ 31,21 xuống 29,59, nhưng tăng RMSE 2019–2021 lên 136,58. Kết luận: chưa đủ để thay RF chính.
- **Có tìm đến file này không?:** Có, khi viết phần "đã thử gì nhưng không dùng".

### `scripts/experiment_ec_error_reduction.py`
- **Vai trò trong đời sống:** Thử các "mẹo giảm sai số" cho RF_compact: cây sâu hơn, thêm đặc trưng "thiếu nước kéo dài", tăng trọng số tháng EC cao, Gradient Boosting với hàm mất mát Huber (ít bị kéo bởi điểm bất thường), và trộn thích ứng.
- **I/O:** Đọc `data/research/mrc_ec_monthly_samples.csv` và các thư mục nguồn `data/external/multivariate_weather`, `ec_feature_research_20261019`, `mrc_kratie_discharge_20261029`, `tien_manual_long_20261029`, `tien_manual_history_20261029`, `tien_multisite_supplement_20261029`, `tien_manual_2024_2026_20261029` (để băm). **GHI outputs/**: `outputs/ec_error_reduction_20261108/predictions_{5,35}d.csv`, `metrics_{5,35}d.csv`, `protocol_{5,35}d.json`. Thư mục được tạo ngay khi nhập tệp (dòng `OUT.mkdir` ở đầu).
- **Tùy chọn:** `--delay` (5 hoặc 35).
- **Hàm chính:**
  - `add_deficit_features(df)` — thêm `q_deficit_months` và `q_range3`, rồi lùi 2 tháng để luôn có sẵn lúc phát hành.
  - `_rf_compact()`, `_rf_fine()` (200 cây, sâu 9, lá 2), `_gb_huber()` — tạo các mô hình.
  - `_predict()`, `_predict_q75()`, `adaptive_q75_blend()` — dự báo, dự báo phân vị 75 giữa các cây, và trộn khi lưu lượng thấp.
  - `run(delay)` — chạy rolling origin; chọn ứng viên chỉ bằng MAE kỳ 2019–2021.
  - Ví dụ số (CLAUDE.md, +5 ngày): `RF_fine_compact` giảm MAE 2019–2021 từ 51,71 xuống 49,40, nhưng làm MAE 2022–2023 tăng từ 12,01 lên 13,88. Không đưa lên trang.
  - Lưu ý: CLAUDE.md ghi tệp này dựa trên `scripts/backtest_asof_ec.py`, nhưng tệp đó hiện đã bị xóa khỏi thư mục làm việc (chưa commit việc xóa); mã nay lấy quy tắc từ `tools.backtest_protocols`. Tệp `outputs/ec_error_reduction_20261108/experiment_ec_error_reduction.original.py` là bản dự phòng chưa theo dõi, không động vào.
- **Có tìm đến file này không?:** Có, khi viết mục thử giảm sai số.

### `scripts/audit_ec_tide_windows_20261108.py`
- **Vai trò trong đời sống:** Hỏi: "Nếu biết thủy triều quanh ngày 13–17 mỗi tháng thì có đoán đúng hơn mẫu 03/2020 không?". Dùng triều thiên văn tính từ atlas FES2022b ở một điểm ngoài biển (106,783°E; 10,05°N), luôn theo ngày lịch cố định, không dùng ngày lấy mẫu thật.
- **I/O:** Đọc atlas FES qua `data/raw/tide/fes2022b/collection_status.json` (cần đủ 34 thành phần), `data/research/mrc_ec_monthly_samples.csv`, `data/raw/ec/mrc/Conductivity.Water Quality@VN_019805_[My Tho].csv`, `outputs/frozen_ec_remedies_20261108/predictions.csv`, `outputs/ec_fes_day15_fixed_20261030/fes_south_feature_days13_17_1985_2023.csv`. **GHI outputs/**: `outputs/ec_tide_windows_20261108/{fes_fixed_windows.csv, frozen_predictions.csv, metrics.csv, audit.json}`. Cần thư viện `pyfes`.
- **Tùy chọn:** `--source-root`, `--output`.
- **Hàm chính:**
  - `tide_features(root)` — tính triều theo giờ (giờ Việt Nam) cho 1985–2023 và tóm thành 4 đặc trưng: `fes_daytime_max_13_17_cm`, `fes_daytime_mean_13_17_cm`, `fes_first_half_max_cm`, `fes_early_range_05_12_cm`.
  - `sample_day_summary(root)` — thống kê ngày lấy mẫu trong tệp gốc (chỉ để mô tả).
  - `evaluate(root, monthly, output)` — thêm từng đặc trưng triều vào ứng viên `WeatherHydrology` và chấm theo giao thức khóa EC.
  - Ví dụ số (CLAUDE.md): trung bình triều ban ngày 13–17 giảm MAE 2021–2023 từ 16,57 xuống 15,59, nhưng 2019–2021 tăng nhẹ từ 57,81 lên 57,93; tháng 03/2020 vẫn chỉ dự báo 229,86 (thật 692).
- **Có tìm đến file này không?:** Có, khi viết về thử nghiệm thủy triều.

### `scripts/experiment_ec_math_physics_20261108.py`
- **Vai trò trong đời sống:** Thử nhiều ý tưởng "toán – vật lý": tăng trọng số khi lưu lượng thấp, học trên thang log, mô hình nghịch đảo lưu lượng kèm RF sửa phần dư, dữ liệu thủy văn ngày gần lúc phát hành, và một "khoảng trên" để cảnh báo.
- **I/O:** Đọc `data/research/mrc_ec_monthly_samples.csv`, `data/external/multivariate_weather/manifest.json`, `data/external/mrc_kratie_discharge_20261029`, `data/external/tien_manual_long_20261029`, `outputs/frozen_ec_remedies_20261108/predictions.csv`. **GHI outputs/**: `outputs/ec_math_physics_20261108/{recent_daily_features.csv, predictions.csv, metrics.csv, calibration.csv, interval_audit.csv, protocol.json}`.
- **Tùy chọn:** `--source-root`, `--output`.
- **Hàm chính:**
  - `LABELS` — 8 ứng viên: `baseline`, `regime_weighted`, `regime_weighted_085`, `regime_gb_weighted`, `rf_log`, `rf_log_smear`, `ridge_inverse_q_residual_rf`, `rf_recent_daily`.
  - `daily_series()`, `recent_daily_features()` — dựng 4 đặc trưng ngày (`q_min7_asof`, `q_delta7_asof`, `tc_stage_min7_asof`, `tc_stage_delta7_asof`), giả định công bố sau 5 ngày.
  - `forest()`, `fit_forest()` — RF có trọng số; quy tắc "chế độ": tháng 1–5 và tỷ lệ Q Kratie t−2 < 0,75 hoặc < 0,85 thì tăng trọng số 5.
  - `log_candidates()` — RF học trên log, có hiệu chỉnh "smearing" khi đổi ngược.
  - `inverse_q_hybrid()` — Ridge theo 1/Q rồi RF sửa phần dư.
  - `conformal_upper()` — khoảng trên dựa trên sai số quá khứ.
  - `evaluate()`, `main()`.
  - Ví dụ số (CLAUDE.md): ngưỡng Q < 0,85 giảm MAE 2019–2021 từ 57,81 xuống 56,19, nhưng số tháng EC ≥ 100 bị bỏ sót tăng từ 2 lên 3; tháng 02/2020 thật 558 nhưng chỉ dự báo 85,74. Khoảng trên mùa khô chỉ bao được 10/15 tháng (66,7%).
- **Có tìm đến file này không?:** Có, khi viết phần ứng viên chưa triển khai.

### `scripts/experiment_ec_conformal_20261112.py` (mới, chưa commit)
- **Vai trò trong đời sống:** Thử tạo "khoảng dự báo" (khoảng giá trị có thể xảy ra, danh nghĩa 90%) cho đúng cấu hình mô hình đang phục vụ, bằng phương pháp conformal trực tuyến. Không tải hay sửa artifact đã đăng ký: nó học lại cùng cấu hình tại mỗi tháng (rolling origin).
- **I/O:** Đọc `data/research/mrc_ec_monthly_samples.csv`, `data/external/multivariate_weather/manifest.json`, `runs/multivariate_ec/mytho/20261108T_HYDROLOGY_PRIMARY_V1/manifest.json` (để kiểm cấu hình). **GHI outputs/**: `outputs/ec_conformal_20261112/{predictions.csv, metrics.csv, run_manifest.json}`.
- **Hàm chính:** `check_configuration()` — so tham số với manifest mô hình chính; `rolling_forecasts()` — dự báo từng tháng; `conformal_width()`, `intervals()` — tính khoảng theo ba cách `online_quantile`, `online_quantile_season`, `aci` (alpha thích ứng); `metrics()`, `main()`.
- **Có tìm đến file này không?:** Có thể, nếu báo cáo bàn về khoảng không chắc chắn. Đây là nghiên cứu mới, chưa có trong Git.

### `scripts/experiment_ec_peak_risk_20261112.py` (mới, chưa commit)
- **Vai trò trong đời sống:** Thử dự báo **xác suất EC vượt ngưỡng** (nguy cơ đỉnh mặn) bằng đặc trưng "trí nhớ mùa" của lưu lượng và chỉ số ENSO (ONI), theo giao thức khóa EC. Thử riêng các giả định độ trễ nguồn: EC {5, 35} ngày, thời tiết {5, 35}, thủy văn {5, 35, 90}.
- **I/O:** Đọc `data/research/mrc_ec_monthly_samples.csv`, `data/external/climate_indices_20261029/oni_monthly.csv`, khí tượng và thủy văn qua `backend`. **GHI outputs/**: `outputs/ec_peak_risk_20261112/{predictions.csv, metrics.csv, run_manifest.json}`. Không đổi registry/mô hình.
- **Tùy chọn:** `--output`.
- **Hàm chính:** `anchor_month()` — tìm tháng nguồn mới nhất đã có; `kratie_monthly()`, `season_features()`, `hydro_table()`, `weather_table()`, `oni_table()` — dựng đặc trưng; `scenario_frame()` — ghép theo kịch bản độ trễ; `classifiers()` — các mô hình phân loại; `run()`.
- **Có tìm đến file này không?:** Có thể, cho hướng phát triển "cảnh báo đỉnh". Chưa có trong Git.

### `scripts/evaluate_mythuan_three_station.py`
- **Vai trò trong đời sống:** Đánh giá ngoại tuyến cho cả ba trạm (Tân Châu, Mỹ Thuận, Mỹ Tho) và thử nội suy dọc sông. Không đổi registry, DB hay giao diện.
- **I/O:** Đọc `data/research/mrc_ec_monthly_samples.csv`, `data/external/multivariate_weather`, `data/external/mythuan_weather_20261104`, `data/external/tien_multisite_20261029_verified`, `data/external/mrc_20261014_network`, `data/biengioi/tien_river_corridor.geojson`. **GHI outputs/** `outputs/mythuan_three_station_20261104` (có `joblib`). Với `--fetch-weather`: tải thời tiết qua Internet (`urlopen`) vào `data/external/mythuan_weather_20261104`.
- **Tùy chọn:** `--fetch-weather`, `--fetch-only`, `--output-dir`.
- **Hàm chính:** `load_targets()`, `build_frame()`, `known_training_rows()` — chuẩn bị dữ liệu as-of; `score()` — MAE/RMSE (nhiều tệp khác nhập hàm này); `interpolation_benchmark()` — so nội suy; `write_report()`, `run()`.
- **Có tìm đến file này không?:** Có, vì `score()` được dùng chung.

### `scripts/experiment_ec_long_hydrology.py`
- **Vai trò trong đời sống:** Thử thêm chuỗi mực nước dài của MRC và mô hình chống nhiễu, theo kiểu as-of.
- **I/O:** Đọc `outputs/ec_upstream_asof_20261029/predictions.csv`. **GHI outputs/** `outputs/ec_long_hydrology_20261029` (hoặc thư mục con `ec_delay_35d`).
- **Tùy chọn:** `--delay` (5/35).
- **Hàm chính:** `run()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/experiment_ec_no_recent_label.py`
- **Vai trò trong đời sống:** Backtest dự báo EC Mỹ Tho **không dùng EC gần đây**, chỉ dùng thủy văn và thời tiết; nhắm vào tình trạng không có EC sau 2023.
- **I/O:** **GHI outputs/** `outputs/ec_long_hydrology_20261029/no_recent_ec/{predictions,metrics}_{delay}d.csv`, `protocol_{delay}d.json`.
- **Tùy chọn:** `--delay` (5/35).
- **Hàm chính:** `run()`. Biến `WEATHER` được `forecast_mytho_ec_hydrology.py` dùng lại.
- **Có tìm đến file này không?:** Ít.

### `scripts/experiment_ec_extreme_robust.py`
- **Vai trò trong đời sống:** Thử thủy văn gọn và tăng trọng số tháng EC cao. Kỳ 2022–2023 không được dùng để chọn.
- **I/O:** Đọc `outputs/ec_long_hydrology_20261029/no_recent_ec`, `outputs/ec_upstream_asof_20261029/predictions.csv`. **GHI outputs/** `outputs/ec_extreme_robust_20261029`.
- **Tùy chọn:** `--delay`.
- **Hàm chính:** `fit_predict()`, `evaluate()`, `run()`. Nhiều tệp khác nhập từ đây.
- **Có tìm đến file này không?:** Ít.

### `scripts/experiment_ec_upstream_asof.py`
- **Vai trò trong đời sống:** Thử đặc trưng tháng và trạm thượng nguồn, có kiểm soát rò rỉ thông tin, phát hành ngày 06.
- **I/O:** Đọc `outputs/multivariate_ec_asof_20261029/asof_predictions.csv`. **GHI outputs/** `outputs/ec_upstream_asof_20261029`.
- **Hàm chính:** `fit_predict()`, `run()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/experiment_ec_issue_daily_hydro.py`
- **Vai trò trong đời sống:** Thử dùng Q Kratie và mực nước Tân Châu **theo ngày** gần ngày phát hành, với độ trễ nguồn giả định.
- **I/O:** Đọc `data/external/tien_manual_long_20261029/019803_Water_Level_Manual_3bd17f3a.csv`, `outputs/ec_extreme_robust_20261029`. **GHI outputs/** `outputs/ec_issue_daily_hydro_20261030`.
- **Tùy chọn:** `--ec-delay`, `--source-delay`, `--start-year`.
- **Hàm chính:** `daily_sources()`, `summarize_windows()`, `add_issue_features()`, `fit_predict()`, `metrics()`, `run()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/experiment_ec_enso_climate.py`
- **Vai trò trong đời sống:** Thử thêm chỉ số khí hậu ENSO (ONI), học trên thang log, và dự báo phân vị 90 để bắt đỉnh.
- **I/O:** Đọc `data/external/climate_indices_20261029/climate_indices_combined.csv`. **GHI outputs/** `outputs/ec_enso_experiment_20261029`.
- **Hàm chính:** `fit_predict_standard()`, `fit_predict_log()`, `fit_predict_quantile90()`, `load_climate()`, `evaluate()`, `run()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/experiment_ec_feature_enhanced.py`
- **Vai trò trong đời sống:** Đánh giá độ quan trọng đặc trưng và thử bộ đặc trưng mở rộng (ví dụ gió hướng đông–tây `wind_u_t2`).
- **I/O:** Đọc `data/external/climate_indices_20261029/climate_indices_combined.csv`. **GHI outputs/** `outputs/ec_feature_enhanced_20261029`.
- **Hàm chính:** `add_derived_features()`, `load_climate()`, `fit_predict()`, `fit_predict_q90()`, `evaluate()`, `run()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/experiment_ec_final_candidates.py`
- **Vai trò trong đời sống:** Vòng chọn cuối (đợt 29/10): ghép đặc trưng tốt nhất với các thuật toán (RF phân vị 90, Gradient Boosting Huber, xếp chồng).
- **I/O:** **GHI outputs/** `outputs/ec_final_candidates_20261029`.
- **Hàm chính:** `_q90_prediction()`, `_q50_prediction()`, `_rf_mean()`, `_hgb_huber()`, `evaluate()`, `run()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/experiment_ec_fes_day15_fixed.py`
- **Vai trò trong đời sống:** Thử triều FES quanh ngày 15 cố định (ngày 13–17), không dùng ngày lấy mẫu thật.
- **I/O:** Đọc `outputs/fes_ec_multipoint_20261026/summary.json`, `outputs/ec_extreme_robust_20261029`, `outputs/ec_compact_history_20261029/predictions_2010_2018.csv`. **GHI outputs/** `outputs/ec_fes_day15_fixed_20261030`. Cần `pyfes`.
- **Tùy chọn:** `--delay`.
- **Hàm chính:** `calculate_fes()`, `score()`, `evaluate()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/experiment_fes_ec.py`
- **Vai trò trong đời sống:** Thí nghiệm đầu tiên thêm triều thiên văn FES2022b vào dự báo EC tháng. Triều FES là triều ngoài biển tính toán, không phải triều đo trên sông.
- **I/O:** Đọc `data/raw/tide/fes2022b/ocean_tide_extrapolated`, `data/raw/tide/fes2022b/collection_status.json`, `data/research/mrc_ec_monthly_samples.csv`. **GHI outputs/** `outputs/fes_ec_experiment_20261026`.
- **Hàm chính:** `choose_native_ocean_point()`, `predict_monthly_tide()`, `metrics()`, `evaluate()`, `main()`. Hằng `ATLAS`, `CONFIG`, `MASK`, `STATUS` được tệp khác dùng lại.
- **Có tìm đến file này không?:** Ít.

### `scripts/experiment_fes_ec_multipoint.py`
- **Vai trò trong đời sống:** Như trên nhưng lấy triều ở nhiều điểm ngoài khơi để xem độ nhạy theo vị trí.
- **I/O:** Đọc khí tượng, `data/research/mrc_ec_monthly_samples.csv`. **GHI outputs/** `outputs/fes_ec_offshore_sensitivity_20261026` (có `joblib`).
- **Hàm chính:** `select_points()`, `tide_features()`, `compare()`, `forecast()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/experiment_tien_multisite_asof.py`
- **Vai trò trong đời sống:** Thử dùng EC Mỹ Thuận đo được và mực nước sông Tiền để dự báo EC Mỹ Tho.
- **I/O:** Đọc `data/external/tien_manual_history_20261029`, `tien_multisite_20261029_verified`, `tien_multisite_supplement_20261029`, `outputs/ec_upstream_asof_20261029/predictions.csv`. **GHI outputs/** `outputs/tien_multisite_asof_20261029`.
- **Hàm chính:** `middle_ec()`, `level_monthly()`, `manual_monthly()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/validate_ec_compact_history.py`
- **Vai trò trong đời sống:** Kiểm tra thêm RF_compact trên 2010–2018 bằng rolling origin. Chỉ là kiểm độ bền, không phải kiểm định mù.
- **I/O:** **GHI outputs/** `outputs/ec_compact_history_20261029`.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/validate_ec_feature_enhanced_history.py`
- **Vai trò trong đời sống:** Kiểm tra bộ đặc trưng mở rộng trên 2010–2018.
- **I/O:** **GHI outputs/** `outputs/ec_feature_enhanced_history_20261029`.
- **Hàm chính:** `run()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/scan_ec_release_lag.py`
- **Vai trò trong đời sống:** Xem kết quả backtest thay đổi ra sao khi giả định độ trễ công bố EC khác nhau (đây là giả định về nguồn, không phải tham số mô hình).
- **I/O:** Đọc `outputs/ec_extreme_robust_20261029/predictions_{delay}d.csv`. **GHI outputs/** `outputs/ec_release_lag_scan_20261030`.
- **Tùy chọn:** `--max-delay`.
- **Hàm chính:** `run()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/research_ec_features.py`
- **Vai trò trong đời sống:** Bộ nghiên cứu đặc trưng EC tháng (đợt 19/10): bước `prepare` dựng ma trận đặc trưng, bước `evaluate` so sánh nhóm đặc trưng.
- **I/O:** Đọc `data/raw/meteorology/openmeteo/openmeteo_all_stations_daily.csv`, `data/raw/dahiti`, `data/external/research_tls_20261010_215230/tanchau_discharge_monthly.csv`, `data/external/uhslc_vungtau_hourly_20261030/vungtau_383b_daily_max.csv`, `data/features/10_monthly_feature_v2.csv`, `data/research/mrc_ec_monthly_samples.csv`. **GHI outputs/** `outputs/ec_feature_research_20261019` (gồm `selection.json`).
- **Tùy chọn:** lệnh vị trí `prepare` hoặc `evaluate`.
- **Hàm chính:** `prepare()`, `daily_features()`, `longest_dry()`, `evaluate()`, `evaluate_year()`, `paired_gain()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/research_ec_hydrology.py`
- **Vai trò trong đời sống:** Thử riêng các nhóm thủy văn trên cùng tập tháng có dữ liệu.
- **I/O:** Đọc `outputs/ec_feature_research_20261019/feature_matrix.csv`. **GHI outputs/** `hydrology_predictions.csv`, `hydrology_metrics.csv`, `hydrology_protocol.json` trong cùng thư mục.
- **Hàm chính:** `main()`. Nhập từ `research_ec_features` bằng tên trần (cần chạy trong `scripts/`).
- **Có tìm đến file này không?:** Ít.

### `scripts/summarize_ec_feature_research.py`
- **Vai trò trong đời sống:** Tóm tắt kết quả nghiên cứu đặc trưng thành bảng và biểu đồ cho báo cáo.
- **I/O:** Đọc các CSV trong `outputs/ec_feature_research_20261019`. **GHI outputs/** `feature_gain_summary.csv`, `drop_group_summary.csv`, hình.
- **Tùy chọn:** `--plot-only`.
- **Hàm chính:** `prepare_summary()`, `plot()`, `mdtable()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/generate_ec_final_report.py`
- **Vai trò trong đời sống:** Sinh tài liệu Markdown so sánh hiệu chỉnh EC, ENSO và giới hạn phân vị (đợt 29/10).
- **I/O:** **GHI docs/**: `docs/ec_enso_and_extreme_recalibration_2026-10-29.md`. Đường dẫn gốc là `Path(".")`, nên phải chạy từ thư mục gốc dự án. Tệp không có hàm; mã chạy thẳng khi gọi.
- **Có tìm đến file này không?:** Ít.

### `scripts/check_ec_feature_research.py`
- **Vai trò trong đời sống:** Kiểm tra căn chỉnh thời gian và tính toàn vẹn của bộ nghiên cứu đặc trưng (nguồn không bị sửa).
- **I/O:** Đọc `data/raw/meteorology/openmeteo/openmeteo_all_stations_daily.csv` và bộ nghiên cứu; in JSON.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

---

### (3) Kiểm tra / audit dữ liệu

"Audit" ở đây nghĩa là soát lại dữ liệu hoặc kết quả mà không sửa số gốc, giống kiểm kê kho.

### `scripts/build_research_workspace.py`
- **Vai trò trong đời sống:** "Đóng gói hộp dữ liệu snapshot" mà trang web đọc khi chạy chế độ `snapshot`. Giống soạn một cuốn album: gom trạm, số đo, nguồn, danh mục cống, kết quả thí nghiệm vào một tệp, kèm phiếu kiểm (manifest có mã băm).
- **I/O:**
  - Đọc: `data/external/ec_recovery_20261011/ec_recovery_manifest.json` và các tệp nguồn liệt kê trong đó (kiểm hash từng tệp), `data/metadata/gate_catalog_reviewed.json`, `data/metadata/ria2_issue12_transcription.json`, `data/raw/gis/spatial`, `data/research/experiment_registry.json`, và mỗi `run_manifest.json` + `predictions.csv` của thí nghiệm trong registry.
  - Ghi: **GHI data/**: `data/research/mrc_ec_monthly_samples.csv`, `data/research/workspace.json`, `data/research/workspace_manifest.json`. Với `--fit`: **GHI runs/** `runs/local_ec_backtest/...` và ghi lại `data/research/experiment_registry.json`. Không ghi DB, không tải mạng.
- **Tùy chọn:** `--fit` (chạy lại backtest tháng cho MYTHO, TANCHAU với độ trễ 0 và 30 ngày, qua `run_monthly_ec.py` ở thư mục gốc).
- **Hàm chính:**
  - `compile_data()` — kiểm hash, đọc trạm/số đo/nguồn RIA2 và MRC, đọc danh mục cống.
  - `monthly_master(observations)` — gom số đo MRC theo tháng cho 3 trạm (MRC_VN_019805 = MYTHO, 019803 = TANCHAU, 019804 = MYTHUAN). Bắt buộc mỗi tháng đúng 1 mẫu; nếu có tháng 2 mẫu thì báo lỗi.
  - `experiments(registry)` — đọc kết quả thí nghiệm đã hoàn tất, kiểm hash từng tệp đầu ra.
  - `write_json(path, value)` — ghi qua tệp tạm `.tmp` rồi thay thế, tránh làm hỏng tệp nếu bị ngắt giữa chừng.
  - `main()` — ghép lại thành `workspace.json` với `live_forecast_available=False`, `gate_advice_available=False`.
  - Ví dụ: nếu một tệp trong `ec_recovery_20261011` bị sửa một ký tự, mã băm lệch và kịch bản dừng với lỗi `Input hash mismatch`.
- **Có tìm đến file này không?:** Có. Đây là nơi sinh ra dữ liệu của chế độ snapshot.

### `scripts/audit_research_data.py`
- **Vai trò trong đời sống:** Tính lại bằng chứng từ dữ liệu cục bộ; không sửa giá trị gốc, không nâng cờ chất lượng.
- **I/O:** Đọc `data/raw`, `data/raw/dahiti`, `data/raw/meteorology/openmeteo`, `data/raw/tide/uhslc`, `data/external/mrc_20261014_network`, `data/external/research_tls_20261010_215230`. **GHI data/** `data/research/audit`.
- **Hàm chính:** `summarize()`, `digest()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/audit_local_data.py`
- **Vai trò trong đời sống:** Soát các tệp dữ liệu được giao và xuất GeoJSON trạm; không cần DB hay mạng, chỉ dùng thư viện chuẩn.
- **I/O:** Đọc `data/raw/ec/mrc`, `data/raw/mrc_conductivity`, `data/processed/master_timeseries.csv`, `data/archive/legacy_analysis/master_timeseries.csv`, `data/biengioi`, `data/raw/gis/spatial`, `data/irrigation_gates_template.csv`, `docs/etl/source_manifest.csv`, `runs/forecast_exp`. **GHI runs/** `runs/local_audit` (JSON + báo cáo Markdown).
- **Tùy chọn:** `--root`, `--out`.
- **Hàm chính:** `audit_project()`, `compare_monthly_ec()`, `station_feature()`, `forecast_summary()`, `boundary_summary()`, `markdown_report()`. Nhập `etl_csv` bằng tên trần.
- **Có tìm đến file này không?:** Ít.

### `scripts/audit_multivariate_errors.py`
- **Vai trò trong đời sống:** Tái tạo bảng soát lỗi dự báo EC của một phiên bản mô hình mà không học lại mô hình.
- **I/O:** Đọc `data/research/mrc_ec_monthly_samples.csv`, `runs/multivariate_ec/...`. **GHI outputs/** `outputs/multivariate_error_audit_20261029`.
- **Tùy chọn:** `--root`, `--version`, `--output-dir`, `--top-n` (mặc định 15 tháng lỗi lớn nhất), `--mrc-zip`.
- **Hàm chính:** `audit()`, `metrics()`, `season_for_month()`, `percentile_nearest_rank()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/audit_ec_adaptive_asof.py`
- **Vai trò trong đời sống:** Chấm lại các ứng viên EC thích ứng so với mốc cùng thời điểm phát hành. Ghi rõ: Q50/Q90 là phân vị giữa các cây, không phải khoảng tin cậy đã hiệu chuẩn.
- **I/O:** Đọc `outputs/ec_compact_history_20261029/predictions_2010_2018.csv`, `outputs/ec_extreme_robust_20261029/...`, `outputs/ec_final_candidates_20261029/...`. **GHI outputs/** `outputs/ec_adaptive_asof_audit_20261030`.
- **Hàm chính:** `risk_weight()`, `metrics()`, `score_recent()`, `historical_tree_heads()`, `run()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/audit_ec_annual_robustness.py`
- **Vai trò trong đời sống:** Tóm tắt kết quả backtest as-of theo từng năm 2019–2023, chỉ để mô tả.
- **I/O:** Đọc `outputs/ec_extreme_robust_20261029`. **GHI outputs/** `outputs/ec_annual_robustness_20261030`.
- **Tùy chọn:** `--source-dir`, `--output-dir`.
- **Hàm chính:** `build_tables()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/audit_ec_feature_association.py`
- **Vai trò trong đời sống:** Đo mức liên quan (tương quan) giữa đặc trưng và EC, có điều chỉnh theo mùa. Không phải quan hệ nhân quả.
- **I/O:** **GHI outputs/** `outputs/ec_feature_association_20261030`.
- **Hàm chính:** `correlation()`, `run()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/audit_ec_station_pair.py`
- **Vai trò trong đời sống:** So mẫu EC cùng tháng giữa Mỹ Tho và Mỹ Thuận, không nội suy.
- **I/O:** Đọc `data/external/mrc_20261014_network/`, `data/external/tien_multisite_20261029_verified/`. **GHI outputs/** `outputs/ec_station_pair_20261030`.
- **Tùy chọn:** `--output-dir`.
- **Hàm chính:** `read_station()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/audit_station_hydrology_20261110.py`
- **Vai trò trong đời sống:** Sàng lọc đặc trưng thủy văn cho Tân Châu và Mỹ Thuận; không bao giờ đổi mô hình đang phục vụ.
- **I/O:** Đọc `data/external`, `data/external/multivariate_weather/manifest.json`, `data/models/multivariate_registry.json` (chỉ đọc), `data/research/mrc_ec_monthly_samples.csv`, `outputs/frozen_ec_gap_20261104/predictions.csv`. **GHI outputs/** `outputs/station_hydrology_screening_20261110`.
- **Hàm chính:** `scores()`, `run()`.
- **Có tìm đến file này không?:** Có thể, khi giải thích vì sao trạm khác chưa dùng thủy văn.

### `scripts/audit_supplied_v3.py`
- **Vai trò trong đời sống:** Soát (chỉ đọc) bộ sổ Excel/CSV/danh mục không gian "v3" được giao; không nhập vào dữ liệu chính.
- **I/O:** Đọc thư mục nguồn truyền vào (tham số vị trí `source`). **GHI** vào thư mục `--out` (bắt buộc) các tệp JSON.
- **Hàm chính:** `audit()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/normalize_v3_observations.py`
- **Vai trò trong đời sống:** Chuẩn hóa các dòng độ mặn được giao thành "sổ chờ duyệt"; không suy diễn nhãn, không ghi DB.
- **I/O:** Đọc thư mục `--folder` (mặc định `data/external/user_v3_review_20261015`). **GHI data/** vào chính thư mục đó (JSON). Cần `openpyxl`.
- **Hàm chính:** `normalize()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/prepare_ec_qc.py`
- **Vai trò trong đời sống:** Tạo "sổ kiểm tra chất lượng" (QC) cho bản xuất EC MRC đã mua, không sửa dữ liệu.
- **I/O:** Đọc tệp zip (tham số vị trí `zip_path`) và `--monthly` (mặc định `data/research/mrc_ec_monthly_samples.csv`). **GHI outputs/** `--output-dir` (mặc định `outputs/multivariate_error_audit_20261029`).
- **Hàm chính:** `build()`, `next_month()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/audit_tien_multisite.py`
- **Vai trò trong đời sống:** Kiểm hash các tệp MRC đã tải dọc sông Tiền và tóm tắt mức phủ dữ liệu, không lấp chỗ trống.
- **I/O:** Đọc các thư mục `data/external/mrc_kratie_discharge_20261029`, `tien_ec_extended_20261029`, `tien_manual_2024_2026_20261029`, `tien_manual_history_20261029`, `tien_manual_long_20261029`, `tien_multisite_20261029_verified`, `tien_multisite_supplement_20261029`. **GHI outputs/** `outputs/tien_multisite_audit_20261029`.
- **Hàm chính:** `sha()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/audit_tien_manual_telemetry.py`
- **Vai trò trong đời sống:** Kiểm tra mực nước đo tay và đo tự động có khớp nhau trong những ngày trùng.
- **I/O:** Đọc `data/external/tien_manual_long_20261029`, `tien_multisite_20261029_verified`, `tien_multisite_supplement_20261029`. **GHI outputs/** `outputs/tien_multisite_audit_20261029/manual_telemetry_agreement.json`.
- **Hàm chính:** `daily()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/audit_grit_gate_connectivity.py`
- **Vai trò trong đời sống:** Kiểm tra sơ bộ mạng sông GRIT và khoảng cách tới cống. Chỉ là hình học, không chứng minh liên thông thủy lực.
- **I/O:** Đọc `data/8file/03_sluice_gates_190_and_27_verified_gis.csv`, `data/biengioi`, `data/raw/gis/spatial/dong_thap_boundary.geojson`, `outputs/grit_delta_network_20261029/{audit.json, grit_lower_mekong_subset.gpkg}`, `data/external/tien_multisite_20261029_verified/inventory.json`. **GHI outputs/** `outputs/grit_gate_audit_20261029`. Cần `geopandas`.
- **Hàm chính:** `main()`, `sha()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/audit_grit_gate_tide_phase.py`
- **Vai trò trong đời sống:** Đo độ trễ sóng mực nước từ Vàm Kênh tới Mỹ Thuận. Không ước tính thời gian lan truyền mặn.
- **I/O:** Đọc `data/external/tien_multisite_20261029_verified`, `tien_multisite_supplement_20261029`. **GHI outputs/** `outputs/grit_gate_audit_20261029`.
- **Hàm chính:** `load_stage()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/build_tien_network_audit.py`
- **Vai trò trong đời sống:** Dựng tạm đường tâm sông Tiền từ dữ liệu OSM đã lưu và chiếu vị trí trạm lên đó.
- **I/O:** Đọc `data/biengioi/tien_osm_waterways_source.json`, `data/external/tien_multisite_20261029_verified/inventory.json`. **GHI outputs/** `outputs/tien_network_20261029`.
- **Hàm chính:** `project()`, `distance()`, `xy()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/validate_fes_vamkenh.py`
- **Vai trò trong đời sống:** So hình dạng triều FES ngoài khơi với mực nước đo tự động ở Vàm Kênh (so dạng sóng, không so cao độ chuẩn).
- **I/O:** Đọc `data/external/tien_multisite_20261029_verified/985203_Water_Level_Telemetry_9305ab16.csv`, bản trong `tien_multisite_supplement_20261029`, `data/raw/tide/fes2022b/collection_status.json`, `outputs/fes_ec_multipoint_20261026/summary.json`. **GHI outputs/** `outputs/fes_vamkenh_validation_20261029`. Cần `pyfes`.
- **Hàm chính:** `observed_hourly()`, `predicted_hourly()`, `metrics()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/export_fes_multimouth_boundaries.py`
- **Vai trò trong đời sống:** Xuất chuỗi triều thiên văn tạm cho các cửa sông Tiền. Chỉ cửa Tiểu đã được đối chiếu với số đo.
- **I/O:** Đọc `outputs/grit_delta_network_20261029/audit.json`. **GHI outputs/** `outputs/fes_multimouth_candidates_20261029`. Cần `pyfes`.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/extract_grit_delta_network.py`
- **Vai trò trong đời sống:** Cắt một phần mạng sông GRIT vùng hạ Mekong để soát, không có thủy lực.
- **I/O:** Đọc `data/external/grit_20261029/GRITv1.0_segments_simple_GLOBAL_EPSG4326.gpkg.zip`. **GHI outputs/** `outputs/grit_delta_network_20261029`.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/inspect_observation_archive.py`
- **Vai trò trong đời sống:** Trích chữ từ PDF bản tin để người xem xét lại; không biến chữ thành số đo chính thức.
- **I/O:** Đọc thư mục truyền vào (tham số vị trí `folder`), kiểm hash. **GHI** các tệp `*.pages.json` và `inspection.json` cạnh đó. Cần `pypdf`.
- **Hàm chính:** `inspect(folder)`.
- **Có tìm đến file này không?:** Ít.

---

### (4) Thu thập dữ liệu từ nguồn ngoài

Các tệp này **tải dữ liệu qua Internet** và ghi vào `data/raw/` hoặc `data/external/`. Không ghi DB. Chạy lại có thể nhận số liệu nguồn đã sửa đổi.

### `data_collection/extract_boundary_no_geopandas.py`
- **Vai trò trong đời sống:** Cắt ranh giới Đồng Tháp + Tiền Giang (cũ) từ bản đồ hành chính GADM và gộp thành một vùng "Đồng Tháp mới", chỉ dùng thư viện chuẩn.
- **I/O:** Đọc `gadm41_VNM_1.json` ở thư mục gốc dự án. **GHI data/** `data/raw/gis/spatial/dong_thap_boundary.geojson`.
- **Hàm chính:** Không có hàm; mã chạy thẳng.
- **Có tìm đến file này không?:** Ít, chỉ khi cần biết ranh giới tỉnh lấy từ đâu.

### `data_collection/extract_dong_thap_new_boundary.py`
- **Vai trò trong đời sống:** Cùng việc như trên nhưng dùng `geopandas`/`shapely`.
- **I/O:** Đọc GADM Level 1. **GHI data/** `data/raw/gis/spatial/dong_thap_boundary.geojson`.
- **Hàm chính:** Không có hàm; mã chạy thẳng.
- **Có tìm đến file này không?:** Ít.

### `data_collection/fetch_dahiti.py`
- **Vai trò trong đời sống:** Tải mực nước đo bằng vệ tinh (DAHITI) gần Tân Châu, Mỹ Tho và lưu lượng gần Tân Châu.
- **I/O:** Gọi API DAHITI (`requests`). **GHI data/** `data/raw/dahiti`.
- **Hàm chính:** `api_post()`, `list_targets_bbox()`, `get_nearest_target()`, `choose_best_target()`, `download_water_level()`, `download_discharge()`.
- **Có tìm đến file này không?:** Ít.

### `data_collection/fetch_glofas.py`
- **Vai trò trong đời sống:** Tải lưu lượng mô phỏng GloFAS tại Tân Châu qua dịch vụ Copernicus (`cdsapi`); nếu năm chưa có bản "consolidated" thì thử bản "intermediate".
- **I/O:** **GHI data/** `data/raw/glofas/tanchau`. Cần tài khoản Copernicus cấu hình sẵn trên máy.
- **Hàm chính:** Không có hàm; mã chạy thẳng.
- **Có tìm đến file này không?:** Ít.

### `data_collection/fetch_uhslc.py`
- **Vai trò trong đời sống:** Tải mực nước biển từ UHSLC (Đại học Hawaii), có hỗ trợ tải tiếp khi bị ngắt.
- **I/O:** **GHI data/** `data/raw/tide/uhslc`.
- **Hàm chính:** `download_with_resume()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/fetch_public_research_data.py`
- **Vai trò trong đời sống:** Tải số đo công khai và (tùy chọn) thời tiết ERA5; ghi nguồn gốc và QA. Nhiều tệp khác dùng lại hàm tải của nó.
- **I/O:** Đọc `data/metadata/forecast_sources.json`, `data/processed/master_timeseries.csv`. **GHI data/** `--out` (mặc định `data/external/research_step07`).
- **Tùy chọn:** `--out`, `--weather-start`, `--weather-end`, `--master`.
- **Hàm chính:** `download()`, `create_tls_context()`, `normalize_sondoc()`, `normalize_discharge()`, `weather_tables()`, `combine_targets()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/fetch_mrc_public.py`
- **Vai trò trong đời sống:** Tải danh mục và số đo công khai của MRC (Ủy hội sông Mê Công), giữ nguyên cờ QA của nguồn, không đăng nhập.
- **I/O:** **GHI data/** `--out` (mặc định `data/external/mrc_step07`). Không ghi PostgreSQL.
- **Tùy chọn:** `--out`, `--hydrology-from`, `--hydrology-until`.
- **Hàm chính:** `normalize()`, `active_values()`, `paired_ec_temperature()`, `instant()`, `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/collect_tien_observations.py`
- **Vai trò trong đời sống:** Gom số đo MRC công khai dọc sông Tiền (EC, mực nước, lưu lượng Kratie). Không đổi EC sang độ mặn, không coi mực nước là lưu lượng.
- **I/O:** **GHI data/** một trong các thư mục `data/external/mrc_kratie_discharge_20261029`, `tien_ec_extended_20261029`, `tien_manual_2024_2026_20261029`, `tien_manual_history_20261029`, `tien_manual_long_20261029`, `tien_multisite_20261029`, `tien_multisite_supplement_20261029` tùy `--profile`.
- **Tùy chọn:** `--profile`, `--out`.
- **Hàm chính:** `download()`, `periods()`, `main()`.
- **Có tìm đến file này không?:** Có thể, khi truy nguồn các CSV thủy văn của mô hình chính.

### `scripts/collect_observation_archive.py`
- **Vai trò trong đời sống:** Thu một số lượng giới hạn tài liệu bản tin chính thức (giữ bản gốc, đường dẫn, lỗi). Không tự biến thành số đo.
- **I/O:** **GHI data/** thư mục mới trong `data/external` mỗi lần chạy.
- **Tùy chọn:** `--pages`, `--max-articles`, `--out`.
- **Hàm chính:** `collect()`, `inventory()`, `links()`, `is_bulletin()`, `is_document()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/refresh_review_sources.py`
- **Vai trò trong đời sống:** Tải lại tài liệu nguồn gốc mà không thay bản cũ; giữ lại cả lần thất bại.
- **I/O:** Đọc `data/external/ec_recovery_20261011`. **GHI data/** `data/external`.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/collect_climate_indices.py`
- **Vai trò trong đời sống:** Tải chỉ số khí hậu ONI (El Niño) và PDO từ NOAA PSL.
- **I/O:** **GHI data/** `data/external/climate_indices_20261029` (CSV ONI, PDO, bảng gộp).
- **Hàm chính:** `collect_oni()`, `collect_pdo()`, `build_combined()`, `_parse_psl_matrix()`, `_download()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/collect_grit_simple.py`
- **Vai trò trong đời sống:** Tải từng đoạn nhỏ của tệp mạng sông GRIT, có thể tải tiếp khi bị ngắt.
- **I/O:** **GHI data/** `data/external/grit_20261029`.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/collect_new_gfz.py`
- **Vai trò trong đời sống:** Tải và soát dữ liệu công khai GFZ (độ mặn Sơn Đốc, lưu lượng Tân Châu), giữ CSV gốc.
- **I/O:** **GHI data/** `data/external/new_data_search_20261029/gfz_apel_2024`.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/collect_new_8file_safe_subset.py`
- **Vai trò trong đời sống:** Giữ lại một phần nhỏ, truy được nguồn, của bộ "8file" cục bộ: số đo **độ mặn g/L**, không phải EC và không phải nhãn MRC.
- **I/O:** Đọc `data/8file/02_stations_master_catalog_63.csv`, `data/8file/06_river_and_interior_salinity_ec_observations_759.csv`. **GHI data/** `data/external/new_data_search_20261029/official_tiengiang_salinity_2026_sep_oct_preserved.csv` và JSON.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/collect_tien_osm_network.py`
- **Vai trò trong đời sống:** Lấy các đường sông/kênh có tên quanh sông Tiền từ OpenStreetMap làm mạng tạm.
- **I/O:** **GHI data/** `data/external/tien_osm_network_20261029`.
- **Tùy chọn:** `--count`.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/refine_tien_osm.py`
- **Vai trò trong đời sống:** Dựng hành lang sông Tiền từ các đường sông OSM đã lưu (giản lược đường), để bản đồ web không cần gọi mạng.
- **I/O:** Đọc/ghi `data/biengioi/tien_osm_waterways_source.json`. **GHI data/** `data/biengioi/tien_river_corridor.geojson` (tệp hình học sông dùng cho nội suy). Với `--refresh`: tải lại OSM.
- **Tùy chọn:** `--refresh`.
- **Hàm chính:** `fetch_source()`, `xml_ways()`, `simplify()`, `point_segment_distance()`, `main()`.
- **Có tìm đến file này không?:** Có thể, khi hỏi đường sông trên bản đồ lấy từ đâu.

### `scripts/fetch_ec_feature_candidates.py`
- **Vai trò trong đời sống:** Tải các đầu vào ứng viên công khai vào một snapshot nghiên cứu riêng.
- **I/O:** Đọc `data/raw/meteorology/openmeteo/openmeteo_all_stations_daily.csv`. **GHI data/** `--output` (mặc định `data/external/ec_feature_research_20261019`).
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/fetch_ec_recent_era5_extra.py`
- **Vai trò trong đời sống:** Tải thêm các biến ERA5 tháng 9/2026 tại điểm lưới Mỹ Tho.
- **I/O:** **GHI data/** `data/external/ec_hydrology_current_20261029`.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/prepare_uhslc_vungtau.py`
- **Vai trò trong đời sống:** Chuẩn hóa mực nước biển Vũng Tàu-B (trạm 383B) của UHSLC về giờ UTC và mm.
- **I/O:** Đọc `data/external/uhslc_vungtau_hourly_20261030/h383b.csv`. **GHI data/** trong cùng thư mục.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/utilities/collect_fes2022b.py`
- **Vai trò trong đời sống:** Kiểm kê hoặc tải toàn bộ atlas triều FES2022b qua SFTP. Mật khẩu chỉ hỏi khi dùng `--download` và không được lưu.
- **I/O:** **GHI data/** `data/raw/tide/fes2022b` (gồm `collection_status.json`). Không ghi đè tệp đã có.
- **Tùy chọn:** `--download`, `--verify-existing`, `--transport`, `--max-attempts`.
- **Hàm chính:** `SFTPDownloader` (lớp tải), `download_one()`, `check_archive()`, `inventory()`, `save()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/utilities/requirements_fes_collection.txt`
- **Vai trò trong đời sống:** Danh sách thư viện cần thêm cho tệp trên: chỉ `paramiko>=4.0,<5` (dùng cho SFTP).
- **I/O:** Không đọc/ghi gì; dùng với `pip install -r`.
- **Có tìm đến file này không?:** Không, trừ khi cần tải lại FES.

---

### (5) Cơ sở dữ liệu: migration, đồng bộ, xác minh

Nhóm này làm việc trực tiếp với PostgreSQL. Cấu hình kết nối được nạp từ `.env` qua `run_webgis.load_local_env` hoặc `backend.database`; **không mở hay in `.env`**.

### `scripts/apply_dss_storage.py`
- **Vai trò trong đời sống:** "Thợ xây thêm phòng" cho cơ sở dữ liệu: áp migration `sql/30_dss_storage.sql`, tạo schema `dss_reference` và các bảng lưu trữ cho hệ hỗ trợ quyết định (DSS). Có dấu vân tay để không xây trùng.
- **I/O:**
  - Đọc: `sql/30_dss_storage.sql` (tính SHA-256).
  - Ghi: **GHI DB** (chỉ khi `--apply`): `CREATE SCHEMA IF NOT EXISTS dss_reference`, bảng sổ `dss_reference.schema_migrations`, rồi chạy tệp SQL (tạo `dss_reference.ec_threshold_presets`, `dss_reference.multivariate_prediction_log`, `dss_reference.gate_simulation_drafts` và ba ví dụ so sánh EC được đánh dấu chưa xác minh). Không sửa bảng `public`.
- **Tùy chọn:** `--apply`. Không có cờ: chỉ in mã băm và kế hoạch.
- **Hàm chính:**
  - `main()` — các bước:
    1. Tính mã băm tệp SQL và in ra.
    2. Không có `--apply` thì in "Plan only" và dừng.
    3. Kết nối với giới hạn thời gian (câu lệnh 30 giây, chờ khóa 5 giây), giữ khóa tư vấn `pg_advisory_xact_lock` để hai người không chạy cùng lúc.
    4. Nếu `30_dss_storage` đã có trong sổ: trùng mã băm thì báo "đã áp dụng"; khác mã băm thì báo lỗi và từ chối ghi đè.
    5. Chạy SQL và ghi một dòng vào sổ migration. Tất cả trong một giao dịch: lỗi giữa chừng thì không thay đổi gì.
  - Ví dụ: chạy lần hai với cùng tệp SQL sẽ in "Already applied with matching checksum; no changes."
- **Có tìm đến file này không?:** Có, khi thiết lập DB lần đầu cho phần lưu dự báo/hồ sơ cống.

### `scripts/apply_dss_migration.py`
- **Vai trò trong đời sống:** Bản tổng quát của tệp trên: áp **một** tệp migration bất kỳ trực tiếp trong `sql/`, kèm số phiên bản.
- **I/O:** Đọc tệp `--file`. **GHI DB** (chỉ khi `--apply`): chạy SQL và thêm dòng vào `dss_reference.schema_migrations`. Từ chối tệp ngoài `sql/`, không có đuôi `.sql`, hoặc tệp hoàn tác `*_down.sql`.
- **Tùy chọn:** `--file` (bắt buộc), `--version` (bắt buộc), `--apply`.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Có, khi thêm bảng mới (ví dụ migration 32, 33, 35).

### `scripts/rollback_dss_prediction_stations.py`
- **Vai trò trong đời sống:** Hoàn tác migration 32 (thêm trạm cho nhật ký dự báo), nhưng chỉ khi chưa có dự báo Mỹ Thuận nào được lưu.
- **I/O:** Đọc `sql/32_dss_prediction_stations.sql`, `sql/32_dss_prediction_stations_down.sql`. **GHI DB** (chỉ khi `--apply`), có câu `DELETE`.
- **Tùy chọn:** `--apply`.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít. Rủi ro cao, không chạy thử.

### `scripts/import_research_workspace.py`
- **Vai trò trong đời sống:** Kiểm tra trước, rồi (với `--apply`) nhập snapshot `workspace.json` thành một bản không đổi vào PostgreSQL/PostGIS.
- **I/O:** Đọc `data/research/workspace.json`, `sql/04_research_workspace.sql`. **GHI DB** (chỉ khi `--apply`) vào `webgis_research.snapshot`, `webgis_research.source`, `webgis_research.site`, `webgis_research.ec_observation`, `webgis_research.gate_catalog`, `webgis_research.experiment`.
- **Tùy chọn:** `--apply`.
- **Hàm chính:** `main()`, `rest()`.
- **Có tìm đến file này không?:** Có thể, khi truy cách dữ liệu snapshot vào DB.

### `scripts/sync_ria2_to_postgres.py`
- **Vai trò trong đời sống:** Thêm (không ghi đè) snapshot 50 dòng RIA2 hiện hành vào bảng `public`. Bản 40 dòng cũ vẫn giữ nguyên làm bằng chứng nguồn gốc.
- **I/O:** Đọc `data/research/workspace.json`, `data/metadata/ria2_issue12_transcription.json`, `data/external/ec_recovery_20261011`. **GHI DB** (chỉ khi `--apply`) vào `public.measurement_site`, `public.conductivity_observation`, `public.source_dataset`, `public.data_source`. Nếu dòng đã có mà khác giá trị thì dừng, không ghi đè.
- **Tùy chọn:** `--apply`.
- **Hàm chính:** `synchronize()`, `ensure_row()`, `load_snapshot()`, `load_legacy_snapshot()`, `core_fingerprint()`, `predecessor_fingerprint()`.
- **Có tìm đến file này không?:** Có thể, khi hỏi RIA2 trong DB từ đâu ra.

### `scripts/sync_mythuan_to_postgres.py`
- **Vai trò trong đời sống:** Thêm EC Mỹ Thuận đã kiểm hash vào bảng EC thô trong `public`; số đo cũ giữ nguyên.
- **I/O:** Đọc `data/external/tien_multisite_20261029_verified/manifest.json`. **GHI DB** (chỉ khi `--apply`) vào `public.measurement_site`, `public.conductivity_observation`.
- **Tùy chọn:** `--apply`.
- **Hàm chính:** `synchronize()`.
- **Có tìm đến file này không?:** Ít.

### `etl/etl_csv.py`
- **Vai trò trong đời sống:** Dây chuyền "ETL" (Extract – Transform – Load: lấy ra, làm sạch, nạp vào): đọc CSV EC MRC, kiểm tra, tách dòng lỗi, xuất CSV chuẩn và tệp SQL. Mặc định không kết nối DB.
- **I/O:** Đọc CSV MRC hoặc `master_timeseries.csv`. **GHI** vào `--out` (mặc định `runs`) CSV chuẩn, CSV dòng bị loại, tệp SQL, báo cáo JSON. Với `--load`: gọi chương trình `psql` để **GHI DB**; mật khẩu do `psql` tự hỏi, kịch bản không giữ.
- **Tùy chọn:** `--station`, `--db`, `--out`, `--load`, `--psql`, `--host`, `--port`, `--user`.
- **Hàm chính:** `normalize()`, `validate()`, `make_sql()`, `write_csv()`, `literal()`, `number()`, `main()`.
- **Có tìm đến file này không?:** Ít. Đây là lối nạp cũ.

### `scripts/inspect_database.py`
- **Vai trò trong đời sống:** Xem hiện trạng DB: có những schema nào, bảng nào, bao nhiêu dòng. Chỉ đọc. Nếu thiếu snapshot, nó gợi ý lệnh `import_research_workspace.py --apply` (chỉ in gợi ý, không tự chạy).
- **I/O:** Đọc DB qua `backend.database`. Không ghi.
- **Hàm chính:** `inspect()`.
- **Có tìm đến file này không?:** Có, khi cần biết DB đang có gì.

### `scripts/check_webgis_setup.py`
- **Vai trò trong đời sống:** Chẩn đoán cài đặt trên Windows (có snapshot không, đã build giao diện chưa, kết nối DB được không) mà không lộ mật khẩu.
- **I/O:** Đọc `data/research/workspace.json`, `frontend/dist/workspace.html`, thử kết nối DB. **GHI runs/** `runs/setup_checks`.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Có, khi máy mới chạy không lên.

### `scripts/verify_database_security.py`
- **Vai trò trong đời sống:** Kiểm tra quyền thật của các vai trò DB bằng cách thử ghi rồi hủy (rollback); không in thông tin đăng nhập.
- **I/O:** Dùng `backend.db_security`. **GHI docs/** `docs/database-security-verification.json`. Các lệnh `INSERT/UPDATE/DELETE/CREATE` thử đều được hủy.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Có thể, cho phần bảo mật.

### `scripts/verify_db_pools.py`
- **Vai trò trong đời sống:** Kiểm tra bể kết nối (pool) được dùng lại, giao dịch chỉ đọc đúng là chỉ đọc, và người ghi được tách biệt.
- **I/O:** Kết nối DB qua `backend.database`, `backend.repositories.dss_storage`, `backend.security`. Không giữ dữ liệu.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/verify_dss_station_migration.py`
- **Vai trò trong đời sống:** Thử ghi dự báo cho ba trạm vào PostgreSQL để kiểm hợp đồng dữ liệu, rồi hủy các dòng thử.
- **I/O:** Kết nối DB; `INSERT` rồi rollback.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/verify_forecast_migration.py`
- **Vai trò trong đời sống:** Chạy migration 33 (sổ phát hành dự báo) bên trong một giao dịch rồi luôn hủy, để chắc tệp SQL hợp lệ.
- **I/O:** Đọc `sql/33_forecast_issue.sql`. Kết nối DB, rollback.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/verify_forecast_runtime.py`
- **Vai trò trong đời sống:** Kiểm quyền người ghi và các trigger (bộ kích hoạt) của sổ dự báo bằng dòng giả, rồi hủy.
- **I/O:** Kết nối DB; rollback.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/verify_field_migration.py`
- **Vai trò trong đời sống:** Kiểm migration 35 (số đo hiện trường) và quy tắc "lần duyệt mới nhất", luôn hủy dòng giả.
- **I/O:** Đọc `sql/35_field_measurement.sql`. Kết nối DB; rollback.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/verify_field_runtime.py`
- **Vai trò trong đời sống:** Kiểm người ghi và người duyệt số đo hiện trường bằng dòng giả, không giữ lại.
- **I/O:** Kết nối DB; rollback.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

### `scripts/verify_field_api.py`
- **Vai trò trong đời sống:** Kiểm khóa API của cán bộ hiện trường với lệnh ghi giả lập (mock); không lưu bản gửi nào.
- **I/O:** Nhập `backend.main`, `backend.services`. Không ghi DB.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Ít.

---

### (6) Tiện ích khác

### `scripts/collect_webgis_evidence.py`
- **Vai trò trong đời sống:** Chụp lại phản hồi API thật của trang web đang chạy để làm bằng chứng cho báo cáo. Giống chụp màn hình có ngày giờ.
- **I/O:** Gọi `--url` (mặc định `http://127.0.0.1:8000`). **GHI runs/** `runs/webgis_evidence`. Với `--include-database`: thêm các endpoint đọc DB.
- **Tùy chọn:** `--url`, `--include-database`.
- **Hàm chính:** `main()`.
- **Có tìm đến file này không?:** Có thể, khi cần bằng chứng giao diện/API cho báo cáo. Trang web phải đang chạy.

---

**Tổng kết nhanh để tra cứu:**

| Muốn biết | Mở tệp |
| --- | --- |
| Mô hình Mỹ Tho đang chạy được tạo thế nào | `scripts/train_mytho_hydrology_primary.py` |
| Điểm MAE/RMSE ba kỳ khóa EC từ đâu ra | `scripts/evaluate_frozen_ec_gap.py`, `scripts/evaluate_frozen_ec_gap_remedies.py` |
| Đã thử gì để giảm sai số mà không dùng | `scripts/evaluate_frozen_ec_followup.py`, `scripts/experiment_ec_error_reduction.py`, `scripts/audit_ec_tide_windows_20261108.py`, `scripts/experiment_ec_math_physics_20261108.py` |
| Dữ liệu snapshot của trang web được đóng gói ra sao | `scripts/build_research_workspace.py` |
| Phát hành và chấm dự báo hằng tháng | `scripts/issue_monthly_forecast.py`, `scripts/score_forecast_issues.py` |
| Tạo bảng DB cho DSS | `scripts/apply_dss_storage.py`, `scripts/apply_dss_migration.py` |
