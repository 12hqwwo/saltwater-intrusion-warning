## 2.E. Lối khởi động, công cụ, cơ sở dữ liệu SQL và bộ kiểm thử

Phần này giới thiệu các tệp nằm ngay ở thư mục gốc `D:\Study\TLCN`, thư mục `tools/`, `config/`, `sql/` và `tests/`. Nếu ví dự án như một quán ăn, thì các tệp ở gốc là cửa chính và công tắc điện, `tools/` là hộp đồ nghề, `sql/` là sổ thiết kế kho lưu trữ, còn `tests/` là người kiểm tra món ăn trước khi mang ra cho khách.

Vài từ cần biết trước:

- **Tham số dòng lệnh**: chữ bạn gõ thêm sau tên lệnh, ví dụ `--port 8016`, để đổi cách chạy mà không phải sửa mã.
- **Cờ `--apply` / `--commit`**: nhiều công cụ ở đây mặc định chỉ "nói trước sẽ làm gì" (chạy thử). Chỉ khi gõ thêm cờ này chúng mới ghi thật vào ổ đĩa hoặc cơ sở dữ liệu. Đừng gõ cờ này chỉ để "thử xem".
- **Cơ sở dữ liệu PostgreSQL**: chương trình lưu dữ liệu dạng bảng, giống nhiều trang Excel được quản lý chặt. Tên cơ sở dữ liệu của dự án là `dongthap_gis`.

---

### 2.E.1. Các tệp chạy được ở thư mục gốc

### `start.ps1`
- **Vai trò trong đời sống:** Nút "bật máy" của cả ứng dụng trên Windows. Nó dựng lại giao diện web rồi bật máy chủ, giống như bật bếp và mở cửa quán cùng một lúc.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: tham số `-Mode` (`postgres` mặc định hoặc `snapshot`), `-Port` (mặc định 8000), `-SkipBuild`; tìm Python ở `.venv\Scripts\python.exe`, nếu không có thì `.venv-api\Scripts\python.exe`. Đầu ra: chạy `npm.cmd --prefix frontend run build` để tạo `frontend/dist/`, kiểm tra có `frontend/dist/workspace.html`, rồi gọi `run_webgis.py --mode ... --port ...`. In ra địa chỉ `http://127.0.0.1:<cổng>/workspace.html` và `/docs`.
- **Các hàm cốt lõi:** Không có hàm; là một kịch bản PowerShell chạy từ trên xuống. Báo lỗi và dừng nếu thiếu môi trường Python, thiếu Node/npm, dựng giao diện thất bại hoặc máy chủ thoát với mã lỗi.
- **Muốn sửa … thì có tìm đến file này không?:** Có, nếu muốn đổi cổng mặc định, chế độ nguồn mặc định hay thứ tự "dựng giao diện rồi chạy". Không, nếu muốn đổi giao diện hay API (xem `frontend/` và `backend/`).

### `start-tinbranch.ps1`
- **Vai trò trong đời sống:** Giống `start.ps1` nhưng dành cho trường hợp đặc biệt: chạy mã của một bản sao khác (worktree) nhưng mượn cấu hình mật khẩu và môi trường Python của bản chính `D:\Study\TLCN`. Giống mượn chìa khóa nhà chính để mở một căn nhà phụ.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `-SettingsRoot` (mặc định `D:\Study\TLCN`), `-Mode`, `-Port`, `-SkipBuild`; Python lấy từ `SettingsRoot`. Đầu ra: dựng `frontend/dist/` của thư mục đang chứa tệp này, rồi chạy một đoạn Python nhúng sẵn: nạp `.env` của thư mục chính bằng `run_webgis.load_local_env()`, đặt `WEBGIS_RESEARCH_MODE` và `WEBGIS_RESEARCH_FILE`, kiểm tra bảo mật đã bật, thử kết nối PostgreSQL (`SELECT 1`) khi ở chế độ `postgres`, rồi phục vụ ở `127.0.0.1`.
- **Các hàm cốt lõi:** Không có hàm riêng; đoạn mã Python nhúng dùng lại `run_webgis` và `backend.main.app`.
- **Muốn sửa … thì có tìm đến file này không?:** Chỉ khi chạy một worktree khác. Khi đang ở chính `D:\Study\TLCN` thì dùng `start.ps1`, không cần tệp này.

### `run_webgis.py`
- **Vai trò trong đời sống:** Người gác cổng của máy chủ. Trước khi mở cửa, nó đọc sổ cấu hình, kiểm tra ổ khóa bảo mật, gọi thử cơ sở dữ liệu, rồi mới mở một máy chủ phục vụ cả API lẫn trang web.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: tệp `.env` ở gốc (chỉ đọc, đưa vào biến môi trường), tham số `--mode`, `--host` (mặc định `127.0.0.1`), `--port` (mặc định 8000), `--api-only`. Đầu ra: một máy chủ Uvicorn chạy ứng dụng FastAPI trong `backend/main.py`, kèm thư mục `frontend/dist/`. Không ghi tệp.
- **Các hàm cốt lõi:**
  - `load_local_env()`: đọc từng dòng `KEY=value` trong `.env`, bỏ dòng trống và dòng `#`; dòng sai dạng thì báo lỗi. Không ghi đè biến đã có sẵn.
  - `port_number(value)`: kiểm tra số cổng nằm trong 1–65535.
  - `bind_host(value)`: kiểm tra địa chỉ máy là một địa chỉ IP hợp lệ.
  - `validate_lan_host(host)`: nếu muốn mở cho máy khác trong mạng (không phải `127.0.0.1`), bắt buộc phải có `WEBGIS_WRITE_API_KEY` và danh sách `WEBGIS_ALLOWED_HOSTS` rõ ràng.
  - `main()`: ghép tất cả: nạp `.env`, đọc tham số, kiểm tra bảo mật bằng `backend.security.enabled()`, thử kết nối PostgreSQL, gắn trang `/` chuyển tới `/workspace.html`, phục vụ `frontend/dist/`, rồi chạy Uvicorn.
- **Muốn sửa … thì có tìm đến file này không?:** Có, nếu cần đổi cách nạp `.env`, quy tắc mở mạng LAN, kiểm tra trước khi chạy. Không, nếu muốn thêm API (xem `backend/main.py`).

### `run_gate_advisor.py`
- **Vai trò trong đời sống:** Một "cửa sổ dòng lệnh" để rà soát hồ sơ một cống mà không cần mở trang web. Giống gọi điện hỏi kết quả thay vì đến tận quầy. Nó chỉ rà soát hồ sơ, không phát lệnh đóng/mở cống.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: hai tệp JSON qua `--policy` (quy tắc) và `--input` (số liệu cống). Đầu ra: in kết quả JSON ra màn hình, không ghi tệp.
- **Các hàm cốt lõi:** `main()`: đọc hai tệp, gọi `evaluate()` của `backend/domain/gates.py`, in kết quả. Tệp này cũng chuyển tiếp (re-export) `stamp`, `numeric`, `nonempty`, `GateInputError` cho `run_station_gate_link.py` dùng.
- **Muốn sửa … thì có tìm đến file này không?:** Ít khi. Quy tắc rà soát thật nằm ở `backend/domain/gates.py`. `tests/test_workspace_api.py` dùng tệp này để chắc chắn kết quả dòng lệnh khớp với API.

### `run_station_gate_link.py`
- **Vai trò trong đời sống:** Kiểm tra xem số đo ở một trạm có được phép dùng "thay mặt" cho một cống hay không. Giống hỏi "nhiệt kế ở phòng khách có đại diện được cho phòng ngủ không?": chỉ gần nhau thì chưa đủ, phải có bằng chứng hai nơi thông nhau.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `--link` (JSON mô tả liên kết trạm–cống), `--record` (JSON một số đo), `--issue-time` (thời điểm xét). Đầu ra: ghi một tệp JSON mới ở `--out` (mở ở chế độ `"x"`, nghĩa là báo lỗi nếu tệp đã tồn tại, không ghi đè) và in tóm tắt trạng thái ra màn hình.
- **Các hàm cốt lõi:**
  - `distance_m(a, b)`: tính khoảng cách đường chim bay (mét) giữa hai tọa độ kinh/vĩ độ.
  - `evaluate_link(record, link, issue_time)`: kiểm tra hàng loạt điều kiện (cùng trạm, cùng đơn vị, thời điểm đo không ở tương lai, liên kết đã được kiểm tra thực địa, có bằng chứng thông nước, số đo còn mới, sai lệch đại diện trong giới hạn). Trả về trạng thái `INVALID_INPUT`, `PROXY_FOR_SCREENING` hoặc `REPRESENTATION_REVIEW_PASSED`, kèm danh sách lý do. Luôn đặt `actuator_command=None` và `gate_decision_eligible=False`.
  - `main()`: đọc tham số, gọi `evaluate_link`, ghi tệp kết quả.
- **Muốn sửa … thì có tìm đến file này không?:** Có, nếu cần đổi điều kiện để coi trạm đại diện được cho cống. Trang web hiện không gọi tệp này.

### `run_monthly_ec.py`
- **Vai trò trong đời sống:** Một thí nghiệm độc lập, kiểu "phòng thí nghiệm riêng": thử nhiều cách đoán EC tháng tới chỉ dựa vào các mẫu EC trước đó, chọn cách tốt nhất trên đoạn kiểm tra (validation), rồi chấm trên đoạn thi (test). Không chạm cơ sở dữ liệu, không sửa dữ liệu gốc. Đây không phải mô hình Mỹ Tho đang phục vụ trên web.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `--data` (mặc định `data/research/mrc_ec_monthly_samples.csv`), `--station` (mặc định `MYTHO`), số tháng validation/test, số cây, seed, `--availability-lag-days`. Đầu ra: tạo thư mục mới trong `runs/local_ec_backtest/<TRẠM>_<mã chạy>/` chứa `run_manifest.json`, `split_manifest.csv`, `feature_audit.csv`, `validation_predictions.csv`, `validation_metrics.csv`, `selection.json`, `high_ec_metrics.csv`, `predictions.csv`, `metrics.csv`, `evaluation_cohort.csv`, `next_forecast.json`, `model_bundle.joblib`, `forecast_chart.png`.
- **Các hàm cốt lõi:**
  - `Config` (lớp cấu hình) và `Config.validate()`: giữ và kiểm tra các con số cài đặt.
  - `load_monthly_data(path, station, availability_lag_days)`: đọc CSV, lọc trạm, tính ngày dữ liệu "có trong tay".
  - `build_features(data)`: tạo đặc trưng như EC gần nhất, EC trước đó, tuổi mẫu, EC cùng tháng năm trước, trung bình 3/12 tháng, sin/cos của tháng.
  - `candidates()`: liệt kê các ứng viên: `Persistence` (giữ EC cuối), `Seasonal Naive` (lấy cùng tháng năm trước) và 6 cấu hình Random Forest.
  - `predict_one(...)`, `walk_forward(...)`: dự báo từng tháng, chỉ dùng dữ liệu trước tháng đó.
  - `split_calendar(...)`, `score_predictions(...)`, `choose_on_validation(...)`: chia lịch train/validation/test, tính sai số MAE/RMSE, chọn mô hình theo validation.
  - `run_experiment(...)`, `save_chart(...)`, `main()`: chạy cả quy trình và lưu kết quả.
- **Muốn sửa … thì có tìm đến file này không?:** Chỉ khi làm lại thí nghiệm "chỉ dùng EC quá khứ". Muốn đổi dự báo trên web thì không (xem `backend/domain/multivariate_ec.py` và registry). Lưu ý: chuỗi mô tả đầu tệp nhắc tới `docs/reports/20261015_repository_review.md`, nhưng tệp này hiện không có trong checkout.

---

### 2.E.2. Tệp cấu hình và tài liệu ở thư mục gốc

### `requirements.txt`, `requirements-prototype.txt`, `requirements-forecast-multivariate.txt`, `requirements-dev.txt`
- **Vai trò:** "Danh sách đi chợ" các thư viện Python cần cài. Lệnh cài: `.venv\Scripts\python.exe -m pip install -r requirements-prototype.txt`.
- `requirements-prototype.txt`: tệp nên dùng; gộp `backend/requirements-api.txt` (fastapi 0.141.1, uvicorn 0.53.0, psycopg 3.3.5, psycopg-pool, pydantic, tzdata) với `requirements-forecast-multivariate.txt`, thêm matplotlib, joblib, openpyxl.
- `requirements-forecast-multivariate.txt`: numpy, pandas, **scikit-learn==1.9.1** (bắt buộc đúng phiên bản vì mô hình đã lưu được tạo bằng phiên bản này), truststore, certifi (kiểm chứng chứng chỉ HTTPS khi tải dữ liệu).
- `requirements.txt`: danh sách rộng, cũ hơn cho phân tích dữ liệu: pandas, numpy, xarray, netCDF4, matplotlib, seaborn, scikit-learn 1.9.1, statsmodels, fastapi, uvicorn, psycopg-pool, cdsapi, pyarrow, openpyxl.
- `requirements-dev.txt`: gộp `requirements-prototype.txt` và thêm `httpx` (để test gọi thử API).

### `.env.example`
- **Vai trò:** Mẫu sổ cấu hình. Sao chép thành `.env` rồi điền giá trị thật trên máy mình. Tệp `.env` thật chứa mật khẩu, không bao giờ đưa lên Git hay in ra.
- **Nội dung chính (chỉ tên biến):** kết nối PostgreSQL (`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`), chế độ nguồn `WEBGIS_RESEARCH_MODE`, `WEBGIS_DSS_WRITES_ENABLED`, `WEBGIS_CORS_ORIGINS`, tài khoản chạy ứng dụng `WEBGIS_DB_USER`/`DSS_PGUSER`, `WEBGIS_SECURITY_ENABLED`, `WEBGIS_ALLOWED_HOSTS`, khóa tùy chọn `WEBGIS_WRITE_API_KEY`.
- Lưu ý: chú thích trong tệp vẫn nhắc `scripts/setup_security.py`, nhưng tệp đó không còn; lệnh hiện hành là `python -m tools security roles --apply` (README đã ghi ánh xạ này).

### `.gitignore`
- **Vai trò:** Danh sách những thứ Git "làm như không thấy": `.env` và mọi `.env.*` (trừ `.env.example`), `.claude/`, `.security/`, `.venv/`, `.venv-api/`, `node_modules/`, `frontend/dist/`, bộ nhớ đệm Python, `tmp/`, `.vscode/`, nhật ký `*.log`, `runs/setup_checks/`, `runs/webgis_evidence/`, `data/archive/`. Muốn ngăn một loại tệp lọt vào Git thì sửa ở đây.

### `.gitattributes`
- **Vai trò:** Ép kiểu xuống dòng (CRLF của Windows hoặc LF) cho một số tệp. Lý do: nhiều manifest lưu mã băm (hash, "dấu vân tay" của tệp); chỉ cần đổi kiểu xuống dòng là dấu vân tay đổi và bằng chứng không còn khớp. Ví dụ `scripts/evaluate_frozen_ec_gap.py`, `backend/repositories/multivariate_inputs.py`, `backend/domain/river_interpolation.py` được giữ CRLF; một số bản sao trong `outputs/.../source_snapshots/` được đánh dấu `-text` để Git không đụng vào.

### `README.md`, `CLAUDE.md`, `DESIGN.md`, `REPO_MAP_FOR_THESIS.md`
- `README.md`: cửa vào cho người mới: cách cài, cách chạy, luồng dùng, giới hạn dữ liệu, bảng đổi tên lệnh cũ sang `python -m tools ...`.
- `CLAUDE.md`: biên bản bàn giao giữa các phiên làm việc: nhánh chính thức, cách chạy, luồng dữ liệu, mô hình đang phục vụ, việc còn phải kiểm chứng.
- `DESIGN.md`: nguyên tắc giao diện (màu, phông Funnel Display/Funnel Sans, quy tắc màu EC trên bản đồ, cách xử lý màn hình hẹp).
- `REPO_MAP_FOR_THESIS.md`: bản đồ repository dài (khảo sát 15/11/2026) phục vụ viết luận văn: cây thư mục, API, SQL, mô hình, test, nhật ký dọn dẹp.

---

### 2.E.3. Thư mục `tools/`: hộp đồ nghề dòng lệnh

Tất cả công cụ gọi chung qua một cửa: `.venv\Scripts\python.exe -m tools <nhóm> <lệnh>`. Gõ `python -m tools --help` để xem danh sách.

### `tools/__main__.py`
- **Vai trò trong đời sống:** Cái công tắc giúp lệnh `python -m tools` chạy được. Không có nó, Python không biết thư mục `tools` là một chương trình.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Không đọc/ghi gì; chỉ gọi `main()` trong `tools/cli.py`.
- **Các hàm cốt lõi:** Không có hàm riêng.
- **Muốn sửa … thì có tìm đến file này không?:** Không.

### `tools/cli.py`
- **Vai trò trong đời sống:** Tổng đài viên: bạn nói tên nhóm và lệnh, nó chuyển tới đúng người phụ trách.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: chữ gõ sau `python -m tools`. Đầu ra: gọi hàm `main` của mô-đun tương ứng; lệnh `check` chạy các test bằng tiến trình con.
- **Các hàm cốt lõi:**
  - `COMMANDS` (bảng tra): `weather update` → `tools.weather_inputs`; `feature hydrology-study` → `scripts.experiment_ec_long_hydrology`; `model train` → `tools.model_training`; `model package-rf` → `scripts.rf_compact_artifacts`; `backtest rolling` → `tools.backtest_protocols`; `observation verify-mrc` → `tools.observation_cleaning`; `security roles` và `security field-keys` → `tools.security_setup`; `source fes` → `scripts.utilities.collect_fes2022b`.
  - `run_checks(full)`: `check smoke` chạy 6 test Python chọn sẵn (`test_model_loading`, `test_backend_audit`, `test_security`, `test_spatial_inputs_cache`, `test_dss_storage_errors`, `test_sql_migrations`) rồi 2 test Node (`gate_intake_rules`, `river_interpolation`); `check full` chạy toàn bộ `tests/test_*.py` rồi hai test Node đó.
  - `main(argv)`: in trợ giúp, xử lý `check`, hoặc tra bảng rồi gọi đúng mô-đun.
- **Muốn sửa … thì có tìm đến file này không?:** Có, nếu muốn thêm/đổi tên một lệnh `python -m tools`, hoặc đổi danh sách test của `check smoke`.

### `tools/weather_inputs.py`
- **Vai trò trong đời sống:** Người đi chợ mua số liệu thời tiết: tải dữ liệu khí tượng ERA5 theo ngày từ dịch vụ Open-Meteo cho các trạm, rồi ghi sổ đã mua gì.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: Internet (`https://archive-api.open-meteo.com/v1/archive`), tham số `--history`, `--start-month`, `--end-month` (dạng `YYYY-MM`). Đầu ra: ghi tệp `era5_<trạm>_<từ>_<đến>.json` và cập nhật `manifest.json` trong `data/external/multivariate_weather/`. Không sửa CSV cũ.
- **Các hàm cốt lõi:**
  - `verified_context()`: tạo kết nối HTTPS có kiểm tra chứng chỉ (dùng `truststore` hoặc `certifi`).
  - `month(value)`: kiểm tra chữ nhập đúng dạng `YYYY-MM`.
  - `fetch_archive(url, context)`: tải dữ liệu, tự thử lại khi máy chủ lỗi tạm (mã 408, 429, 500, 502, 503, 504).
  - `main(argv)`: chia khoảng thời gian thành từng đợt, bỏ qua đợt đã có, tải và ghi tệp.
- **Muốn sửa … thì có tìm đến file này không?:** Có, khi cần đổi nguồn khí tượng, tọa độ điểm lấy thời tiết (`SITES`) hoặc cách lưu. Lệnh: `python -m tools weather update`. Lệnh này ghi tệp thật.

### `tools/model_training.py`
- **Vai trò trong đời sống:** Lò đào tạo mô hình đa biến cho từng trạm (bản khí tượng): dạy Random Forest đoán EC từ thời tiết tháng `t−2`, rồi đóng gói kèm "giấy khai sinh" (manifest).
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `data/research/mrc_ec_monthly_samples.csv`, `data/external/multivariate_weather/manifest.json` (qua `get_monthly_weather`), `data/research/workspace.json`. Đầu ra (chỉ khi có `--apply`): thư mục mới trong `runs/multivariate_ec/` gồm mô hình, `predictions.csv`, `manifest.json`; và **ghi đè** `data/models/multivariate_registry.json`.
- **Các hàm cốt lõi:**
  - `pipeline()`: dựng mô hình: điền giá trị thiếu bằng trung vị, rồi Random Forest 300 cây, sâu tối đa 8, tối thiểu 3 mẫu/lá, seed 42.
  - `training_frame(target_path, weather_path)`: ghép mẫu EC với thời tiết tháng `t−2`, thêm sin/cos của tháng; báo lỗi nếu trùng tháng hoặc thiếu thời tiết.
  - `train()`: huấn luyện cho từng trạm, đánh giá, lưu mô hình, manifest và registry.
  - `main(argv)`: không có `--apply` thì chỉ in kế hoạch, không ghi gì.
- **Muốn sửa … thì có tìm đến file này không?:** Cẩn thận. Chạy với `--apply` sẽ thay registry, có thể làm trang web dùng mô hình khác (kể cả bỏ mất mục Mỹ Tho thủy văn đang phục vụ). Mô hình Mỹ Tho chính được đóng gói bằng `scripts/train_mytho_hydrology_primary.py`, không phải tệp này. Các script nghiên cứu khác mượn `pipeline()` và `training_frame()` từ đây.

### `tools/backtest_protocols.py`
- **Vai trò trong đời sống:** Trọng tài của cuộc thi "đoán trước": quy định ngày nào được phát hành dự báo và ngày nào dữ liệu mới coi là có trong tay, để không ai "nhìn trộm đáp án".
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `data/research/mrc_ec_monthly_samples.csv`, `data/external/multivariate_weather/manifest.json`. Đầu ra: các CSV/JSON trong `outputs/multivariate_ec_asof_20261029/` (khi chạy `python -m tools backtest rolling`).
- **Các hàm cốt lõi:**
  - `issue_date_for(target_month)`: ngày phát hành dự báo là ngày 6 của tháng trước tháng cần đoán.
  - `available_date_for(month_start, lag_days)`: dữ liệu một tháng chỉ coi là có từ cuối tháng cộng thêm `lag_days` ngày.
  - `split_for(target)`: 2019–2021 là `validation`, 2022–2023 là `historical_2022_2023`.
  - `scores(rows, model)`, `write_csv(path, rows)`: tính sai số và ghi bảng.
  - `run(output_dir)`: so sánh RandomForest với Persistence, SeasonalNaive, MonthlyClimatology theo hai kịch bản +5 và +35 ngày.
  - `main(argv)`: điểm vào dòng lệnh.
- **Muốn sửa … thì có tìm đến file này không?:** Có, nếu muốn đổi quy tắc ngày phát hành/ngày dữ liệu có sẵn. Nhiều script và test dùng chung các hàm ngày này, nên đổi ở đây ảnh hưởng rộng.

### `tools/feature_building.py`
- **Vai trò trong đời sống:** Bếp sơ chế nguyên liệu cho các thí nghiệm: biến dữ liệu thô (mực nước, lưu lượng, EC trạm khác) thành các cột số theo tháng mà mô hình có thể "ăn".
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: CSV trong `data/external/tien_manual_long_20261029/`, `tien_manual_history_20261029/`, `tien_multisite_supplement_20261029/`, `tien_manual_2024_2026_20261029/`, `mrc_kratie_discharge_20261029/`, `ec_feature_research_20261019/`. Đầu ra: bảng dữ liệu trong bộ nhớ, không ghi tệp.
- **Các hàm cốt lõi:**
  - `ec_features(series, target, issue, delay, prefix)`: từ chuỗi EC một trạm, lấy giá trị gần nhất, trước đó, tuổi mẫu, cùng tháng năm trước, trung bình 3/12 tháng, chỉ dùng mẫu đã "có trong tay" ở ngày phát hành.
  - `build_matrix(delay)`, `data_matrix(delay=5)`: dựng bảng đặc trưng cho Mỹ Tho, ghép mực nước nhiều trạm và lưu lượng Kratie.
  - `monthly_stage(code, prefix)`: mực nước tháng của một trạm (tháng `t−2` và trung bình 3 tháng).
  - `monthly_kratie_flow()`: lưu lượng Kratie theo tháng, trung bình 3 tháng và tỷ lệ so với trung vị cùng mùa.
  - `fit_candidate_model(kind, columns, train)`, `predictor(...)`: huấn luyện một trong bốn loại mô hình thử (`rf`, `rf_log`, `extra`, `hgb_log`) và đoán một tháng.
- **Muốn sửa … thì có tìm đến file này không?:** Có, khi làm thí nghiệm mới về đặc trưng thủy văn. Không phải đường chạy của trang web, nhưng `tests/test_mytho_hydrology_primary.py` dùng `monthly_kratie_flow` và `monthly_stage` để đối chiếu rằng đặc trưng trên web khớp với nghiên cứu.

### `tools/observation_cleaning.py`
- **Vai trò trong đời sống:** Người soát hóa đơn: so tệp ZIP tải gốc từ MRC với bảng EC tháng của dự án để chắc chắn không lệch con số nào. Chỉ đọc, không ghi.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: đường dẫn ZIP MRC (phải chứa đúng 2 CSV "Conductivity.Water Quality" của trạm 019805 Mỹ Tho và 019803 Tân Châu), `--monthly` (mặc định `data/research/mrc_ec_monthly_samples.csv`). Đầu ra: in kết quả đối chiếu ra màn hình.
- **Các hàm cốt lõi:** `verify(zip_path, monthly_path)`: đọc hai CSV trong ZIP, đếm cấp chất lượng, so với bảng tháng. `main(argv)`: điểm vào; lệnh `python -m tools observation verify-mrc <tệp.zip>`.
- **Muốn sửa … thì có tìm đến file này không?:** Có, khi nhận bản tải MRC mới và cần kiểm tra trước khi dùng.

### `tools/security_setup.py`
- **Vai trò trong đời sống:** Thợ khóa: tạo tài khoản cơ sở dữ liệu riêng cho ứng dụng (một tài khoản chỉ được đọc, một tài khoản chỉ được thêm), gắn camera ghi nhật ký, và cất chìa khóa vào tệp được bảo vệ.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `.env` (qua `load_local_env`), `sql/31_database_security.sql`, kết nối PostgreSQL bằng tài khoản quản trị. Đầu ra (chỉ khi có `--apply`): tạo/sửa role `webgis_reader`, `webgis_writer` trong PostgreSQL, cấp quyền, tạo schema `webgis_security`, chạy `sql/31_database_security.sql`; ghi thông tin đăng nhập vào `.env` và thư mục `.security/`, khóa quyền tệp bằng `icacls` (Windows).
- **Các hàm cốt lõi:**
  - `protect(path, directory)`: chỉ cho người dùng hiện tại và hệ thống đọc tệp/thư mục.
  - `update_env(path, values)`: thêm hoặc thay biến trong `.env` rồi khóa tệp.
  - `setup_runtime_roles(apply)`: tạo hai role, đặt giới hạn thời gian truy vấn, cấp quyền đọc cho `webgis_reader` và quyền đọc+thêm vào bảng DSS cho `webgis_writer`.
  - `setup_field_keys(apply)`: sinh hai khóa API khác nhau `WEBGIS_WRITE_API_KEY` và `WEBGIS_REVIEW_API_KEY` nếu còn thiếu; không in giá trị ra.
  - `main(argv)`: lệnh `roles` hoặc `field-keys`, kèm `--apply`.
- **Muốn sửa … thì có tìm đến file này không?:** Có, khi đổi quyền tài khoản ứng dụng. Cảnh báo: `--apply` ghi thật vào PostgreSQL và `.env`; không chạy để "thử". `run_webgis.py` sẽ từ chối chạy nếu bảo mật chưa bật và nhắc chạy lệnh này.

---

### 2.E.4. Thư mục `config/`: các tệp cài đặt cho nguồn dữ liệu ngoài

- `config/fes2022b_full.yaml`: cấu hình cho thư viện tính thủy triều FES2022b: đường dẫn 34 tệp atlas sóng triều (`${FES_DATA}/m2_fes2022.nc`...). Dòng đầu ghi rõ không phê duyệt các điểm cửa sông ứng viên. Dùng cho thí nghiệm triều, không dùng khi chạy web.
- `config/aviso_sftp_known_hosts`: một dòng "dấu vân tay" của máy chủ AVISO (`ftp-access.aviso.altimetry.fr`, cổng 2221) để khi tải atlas FES qua SFTP, máy biết chắc đang nói chuyện với đúng máy chủ. Dùng bởi `scripts/utilities/collect_fes2022b.py`.
- `config/glofas/constraints.json`, `glofas_form.json`, `glofas_schema.json`: bản lưu biểu mẫu, ràng buộc và mô tả bộ dữ liệu lưu lượng mô phỏng GloFAS (`cems-glofas-historical`) của dịch vụ Copernicus, để biết khi gửi yêu cầu tải thì chọn những giá trị nào hợp lệ. Chỉ là tài liệu tham chiếu cho thu thập dữ liệu.

Muốn đổi giao diện hay mô hình web thì không cần đụng `config/`.

---

### 2.E.5. Thư mục `sql/`: bản thiết kế cơ sở dữ liệu

Giải thích vài từ trước:

- **Bảng (table):** một trang tính có cột cố định, mỗi dòng là một bản ghi (ví dụ một mẫu EC).
- **Khóa chính (primary key):** cột "số chứng minh thư" của mỗi dòng, không trùng nhau.
- **View:** một "bảng ảo", thực chất là câu hỏi đã lưu sẵn; mở ra thì thấy kết quả như một bảng nhưng không chứa dữ liệu riêng.
- **Schema:** một ngăn kéo chứa nhiều bảng. Dự án dùng `public` (dữ liệu nghiệp vụ), `dss_reference` (lưu dự báo, bản nháp cống, đo thực địa), `webgis_research` (bộ nghiên cứu), `webgis_security` (nhật ký kiểm toán).
- **Role/quyền (GRANT):** tài khoản trong cơ sở dữ liệu và những việc nó được phép làm (đọc, thêm...).
- **Trigger:** "chuông báo" tự chạy khi có ai thêm/sửa dòng, ví dụ để ghi nhật ký hoặc chặn sửa.
- **Index:** mục lục giúp tìm nhanh; GiST là loại mục lục cho dữ liệu bản đồ.
- **Migration:** một bước nâng cấp cấu trúc cơ sở dữ liệu, chạy theo thứ tự số.
- **PostGIS geometry:** cột chứa hình học (điểm, đường, vùng) với tọa độ, ở đây dùng hệ WGS84 (`4326`, kinh/vĩ độ GPS).
- **Transaction (`BEGIN ... COMMIT/ROLLBACK`):** gói việc thành một khối; `COMMIT` là lưu thật, `ROLLBACK` là hủy toàn bộ như chưa làm gì.

Các tệp có ghi chú "**GHI DB**" sẽ thay đổi cơ sở dữ liệu khi chạy. Chỉ chạy khi đúng yêu cầu, sau khi sao lưu.

### `sql/00_preflight_v1.sql`
- **Vai trò trong đời sống:** Kiểm tra trước khi xây: xem đang ở đúng cơ sở dữ liệu, tài khoản nào, phiên bản PostgreSQL, múi giờ.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Chỉ đọc. Chạy trong Query Tool của `dongthap_gis`.
- **Bảng/view/hàm SQL tạo ra:** Không tạo gì.
- **Muốn sửa … thì có tìm đến file này không?:** Không, trừ khi muốn thêm mục kiểm tra trước.

### `sql/01_core_schema_if_new.sql`
- **Vai trò trong đời sống:** Bản móng nhà (schema v1). Chỉ chạy một lần trên cơ sở dữ liệu mới.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (CREATE). Gói trong `BEGIN ... COMMIT`. Ghi chú đầu tệp: không xóa/sửa bảng đã có.
- **Bảng/view/hàm SQL tạo ra:** bật PostGIS (`CREATE EXTENSION IF NOT EXISTS postgis`); bảng `public.data_source`, `public.admin_boundary`, `public.salinity_station`, `public.salinity_observation`, `public.water_level_observation`, `public.irrigation_gate`; view `public.v_station_latest`, `public.v_station_training`; các index thời gian/nguồn và index hình học (`idx_station_geom`, `idx_gate_geom`, `idx_boundary_geom`...).
- **Muốn sửa … thì có tìm đến file này không?:** Không sửa trên cơ sở dữ liệu đã có; chỉ đọc để hiểu cấu trúc nền.

### `sql/01_toa_do_tram_MyTho_TanChau.sql`
- **Vai trò trong đời sống:** Ghim tọa độ cho hai trạm MRC Tân Châu (`MRC_VN_019803`) và Mỹ Tho (`MRC_VN_019805`) lấy nguyên văn từ hai tệp KML, trạng thái `REPORTED`.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (`UPDATE public.measurement_site`), nhưng mặc định kết thúc bằng `ROLLBACK` (chỉ xem trước). Muốn lưu phải đổi dòng cuối thành `COMMIT`. Có chốt chặn: dừng nếu sai cơ sở dữ liệu, thiếu 2 trạm, hoặc trạm đã có tọa độ khác (không ghi đè).
- **Bảng/view/hàm SQL tạo ra:** Chỉ bảng tạm `expected_site_location` (tự xóa khi kết thúc).
- **Muốn sửa … thì có tìm đến file này không?:** Chỉ khi cần nạp lại tọa độ trạm. Chú ý: trùng số thứ tự `01` với tệp schema, nhưng phải chạy sau `10_...` và `11_...` vì cần bảng `measurement_site` đã có dữ liệu.

### `sql/02_irrigation_gate_dong_thap.sql`
- **Vai trò trong đời sống:** Nạp danh sách 15 cống thủy lợi (nguồn `sluice_gates_dong_thap_new.geojson`, hệ tọa độ WGS84) vào sổ cống.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (`INSERT INTO public.data_source`, `INSERT INTO public.irrigation_gate`), mặc định kết thúc bằng `ROLLBACK`; đổi thành `COMMIT` sau khi xem kết quả đúng.
- **Bảng/view/hàm SQL tạo ra:** Không tạo bảng mới; thêm dòng vào hai bảng có sẵn.
- **Muốn sửa … thì có tìm đến file này không?:** Có, nếu cần nạp lại danh mục cống vào PostgreSQL.

### `sql/03_admin_boundary_dong_thap.py`
- **Vai trò trong đời sống:** Người vẽ ranh giới hành chính: tải ranh giới tỉnh Đồng Tháp mới (mã tỉnh `82`) và 102 xã/phường từ GitHub, kiểm tra đủ 103 tệp, rồi tự viết ra tệp SQL để nạp vào bảng ranh giới. Chỉ dùng thư viện có sẵn của Python.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: Internet (GeoJSON thô trên GitHub), tham số `--db` (mặc định `dongthap_gis`), `--host`, `--port`, `--user`, `--psql` (mặc định `C:\Program Files\PostgreSQL\17\bin\psql.exe`), `--out` (mặc định `D:\TLCN_ADMIN_RUNS`), `--load`, `--commit`. Đầu ra: thư mục chạy `<thời điểm>_admin_boundary_03` chứa GeoJSON, `manifest.json`, `report.json`, `load.sql`. Với `--load` sẽ gọi `psql` để chạy `load.sql`. **GHI DB** chỉ khi có cả `--load` và `--commit` (SQL thêm nguồn `TLQ_VNM_ADMIN_GIS_2026` vào `public.data_source`, xóa các ranh giới cũ có mã bắt đầu bằng `GADM41` rồi chèn/cập nhật vào `public.admin_boundary`). Không có `--commit` thì SQL kết thúc bằng `ROLLBACK`.
- **Các hàm cốt lõi:**
  - `parse_args()`: đọc tham số dòng lệnh.
  - `fetch(url)`: tải một tệp từ Internet.
  - `load_feature(data, expected_code, label)`: kiểm tra GeoJSON đúng mã, đúng loại hình học.
  - `sql_text(value)`, `sql_utf8_expr(value)`, `geom_expr(geom)`: chuyển chữ và hình học thành đoạn SQL an toàn (chỉ ký tự ASCII).
  - `boundary_upsert(code, name, level, geom)`: viết câu SQL "thêm mới hoặc cập nhật nếu đã có" cho một ranh giới.
  - `make_sql(records, commit)`: ghép toàn bộ tệp SQL, kèm kiểm tra bảng `public.admin_boundary` phải có trước và các câu đếm kết quả.
  - `main()`: chạy cả quy trình tải, kiểm tra, sinh SQL, gọi `psql`.
- **Muốn sửa … thì có tìm đến file này không?:** Có, nếu cần cập nhật ranh giới hành chính. Đây là tệp Python nằm trong thư mục `sql/`, không phải tệp SQL.

### `sql/04_research_workspace.sql`
- **Vai trò trong đời sống:** Thêm một ngăn kéo riêng `webgis_research` để chứa bộ dữ liệu nghiên cứu mà không đụng các bảng nghiệp vụ.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (CREATE). Chạy qua `scripts/import_research_workspace.py --apply`. Dùng `IF NOT EXISTS` nên chạy lại không lỗi.
- **Bảng/view/hàm SQL tạo ra:** schema `webgis_research`; bảng `source`, `snapshot`, `site`, `gate_catalog`, `experiment`, `ec_observation`; index hình học `research_site_geom`, `research_gate_geom`.
- **Muốn sửa … thì có tìm đến file này không?:** Chỉ khi đổi cấu trúc bộ nghiên cứu trong PostgreSQL.

### `sql/10_extend_realdata_schema.sql`
- **Vai trò trong đời sống:** Nâng cấp v2: thêm các bảng chứa dữ liệu thật đã được cung cấp (trạm đo, EC dẫn điện, đặc trưng tháng).
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (CREATE) trong `BEGIN ... COMMIT`. Không DROP/ALTER bảng v1.
- **Bảng/view/hàm SQL tạo ra:** bảng `public.source_dataset`, `public.analysis_area`, `public.measurement_site`, `public.conductivity_observation`, `public.monthly_feature`; view `public.v_monthly_coverage`; các index (`idx_ec_site_time`, `idx_measurement_site_geom`...).
- **Muốn sửa … thì có tìm đến file này không?:** Đọc để hiểu bảng EC mà chế độ `postgres` đọc ra; không chạy lại trên DB đã có.

### `sql/11_import_supplied_real_data.sql`
- **Vai trò trong đời sống:** Bê dữ liệu thật vào kho: tệp dài khoảng 1.500 dòng, được sinh tự động, chứa sẵn các giá trị EC (giữ đơn vị mS/m, thiếu thì để trống) và đặc trưng tháng.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (INSERT) trong `BEGIN ... COMMIT`. Có chốt kiểm tra: số dòng EC của bộ phải đúng 464, nếu không thì dừng.
- **Bảng/view/hàm SQL tạo ra:** Không tạo bảng chính mới (chỉ bảng tạm `tmp_v...`); thêm dòng vào `public.data_source`, `public.source_dataset`, `public.analysis_area`, `public.measurement_site`, `public.conductivity_observation`, `public.monthly_feature`.
- **Muốn sửa … thì có tìm đến file này không?:** Không sửa tay; chạy sau tệp `10_...`.

### `sql/12_verify_real_data.sql`
- **Vai trò trong đời sống:** Kiểm kho sau khi nhập hàng. Kỳ vọng: EC gốc 464 dòng, dữ liệu tháng 1.000 dòng, đối chiếu 464 cặp, 0 sai lệch.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Chỉ đọc. Chạy sau tệp `11_...`.
- **Bảng/view/hàm SQL tạo ra:** Không tạo gì.
- **Muốn sửa … thì có tìm đến file này không?:** Chỉ khi thêm câu kiểm tra.

### `sql/20_alert_threshold_gate_rule_freshness.sql`
- **Vai trò trong đời sống:** Thêm sổ quy tắc: hồ sơ ngưỡng cảnh báo, quy tắc cống cần những đầu vào gì, chính sách dữ liệu bao lâu thì cũ.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (CREATE + INSERT) trong `BEGIN ... COMMIT`. Không DROP/ALTER bảng cũ.
- **Bảng/view/hàm SQL tạo ra:** bảng `public.alert_threshold_profile`, `public.gate_rule_profile`, `public.gate_rule_required_input`, `public.data_freshness_policy`, `public.system_capability_snapshot`; index `idx_capabilities_time`; thêm dòng mẫu vào `alert_threshold_profile` và `system_capability_snapshot`.
- **Muốn sửa … thì có tìm đến file này không?:** Chỉ khi đổi cấu trúc quy tắc trong DB.

### `sql/30_dss_storage.sql`
- **Vai trò trong đời sống:** Tạo ngăn kéo `dss_reference` để lưu lịch sử dự báo đã bấm, bản nháp mô phỏng cống và bộ ngưỡng EC có sẵn.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (CREATE + INSERT). Chạy qua `scripts/apply_dss_storage.py --apply`. Không ghi vào bảng `public`; nếu bảng DSS đã có mà không tương thích thì báo lỗi chứ không ghi đè.
- **Bảng/view/hàm SQL tạo ra:** schema `dss_reference`; bảng `ec_threshold_presets` (kèm dữ liệu mẫu), `gate_simulation_drafts`, `multivariate_prediction_log`; index `idx_dss_prediction_station_month`, `idx_dss_prediction_saved`, `idx_dss_draft_gate_created`.
- **Muốn sửa … thì có tìm đến file này không?:** Có, nếu đổi cấu trúc lưu dự báo/bản nháp (cần sửa kèm `backend/repositories/dss_storage.py`).

### `sql/31_database_security.sql`
- **Vai trò trong đời sống:** Camera an ninh: mỗi khi có dòng mới được thêm vào bảng dự báo hoặc bản nháp cống, tự ghi một dòng nhật ký "ai, lúc nào, bảng nào, mã bản ghi nào" (không lưu mật khẩu hay số đo).
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (CREATE). Được `tools/security_setup.py roles --apply` chạy bằng tài khoản quản trị.
- **Bảng/view/hàm SQL tạo ra:** bảng `webgis_security.audit_log` (khóa chính `audit_id`); hàm `webgis_security.audit_dss_insert()`; trigger `audit_gate_draft` (trên `dss_reference.gate_simulation_drafts`) và `audit_prediction` (trên `dss_reference.multivariate_prediction_log`). Thu hồi quyền chạy hàm khỏi `PUBLIC`.
- **Muốn sửa … thì có tìm đến file này không?:** Chỉ khi đổi cách ghi nhật ký kiểm toán.

### `sql/32_dss_prediction_stations.sql`
- **Vai trò trong đời sống:** Mở cửa cho trạm thứ ba: cho phép bảng lưu dự báo nhận thêm Mỹ Thuận (`MyThuan`, mã `MRC_VN_019804`) bên cạnh Mỹ Tho và Tân Châu. Không viết lại dòng cũ.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (`ALTER TABLE dss_reference.multivariate_prediction_log`: bỏ ràng buộc cũ, thêm `prediction_station_key_check` và `prediction_station_site_check`). Từ chối chạy nếu không phải `dongthap_gis`.
- **Bảng/view/hàm SQL tạo ra:** Không tạo bảng; chỉ thay "luật kiểm tra" (ràng buộc CHECK) của bảng.
- **Muốn sửa … thì có tìm đến file này không?:** Có, nếu thêm trạm dự báo mới vào lịch sử lưu.

### `sql/32_dss_prediction_stations_down.sql`
- **Vai trò trong đời sống:** Nút "quay lại" của tệp trên: bỏ hai ràng buộc mới để trở về chỉ hai trạm. Tự dừng với lỗi nếu bảng đã có dòng dự báo Mỹ Thuận.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (`ALTER TABLE`, `DROP CONSTRAINT`). Chạy qua script hoàn tác.
- **Bảng/view/hàm SQL tạo ra:** Không tạo gì; xóa `prediction_station_key_check`, `prediction_station_site_check` và khôi phục ràng buộc cũ.
- **Muốn sửa … thì có tìm đến file này không?:** Chỉ khi cần hoàn tác. `tests/test_sql_migrations.py` kiểm tra cặp tệp 32.

### `sql/33_forecast_issue.sql`
- **Vai trò trong đời sống:** Sổ cái phát hành dự báo hằng tháng, kiểu sổ biên lai không tẩy xóa được: mỗi suất dự báo, lần phát hành, điểm chấm đều không sửa/xóa được sau khi ghi.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (CREATE, GRANT, INSERT vào nhật ký). Chạy qua `scripts/apply_dss_migration.py --file ...`. Từ chối chạy ngoài `dongthap_gis`.
- **Bảng/view/hàm SQL tạo ra:** bảng `dss_reference.forecast_slot`, `forecast_slot_event`, `forecast_issue`, `forecast_score`; hàm `dss_reference.stamp_forecast_event`, `reject_forecast_mutation`, `guard_forecast_score`; cập nhật `webgis_security.audit_dss_insert`; các trigger chặn sửa (`forecast_*_immutable`), trigger canh (`forecast_issue_guard`, `forecast_score_guard`), trigger ghi nhật ký (`audit_forecast_*`); index `forecast_slot_month_idx`, `forecast_score_issue_idx`. Cấp quyền: `webgis_reader` được đọc, `webgis_writer` được đọc và thêm.
- **Muốn sửa … thì có tìm đến file này không?:** Có, khi đổi quy tắc sổ phát hành dự báo (kèm `backend/domain/forecast_issue.py`).

### `sql/33b_forecast_issue_guard.sql`
- **Vai trò trong đời sống:** Bản vá cho tệp 33: sửa trigger canh để đọc được các suất dự báo mà không cần quyền UPDATE.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (`CREATE OR REPLACE FUNCTION`). Từ chối chạy ngoài `dongthap_gis`.
- **Bảng/view/hàm SQL tạo ra:** thay hàm `dss_reference.guard_forecast_issue`.
- **Muốn sửa … thì có tìm đến file này không?:** Chỉ khi trigger canh phát hành gặp lỗi quyền.

### `sql/35_field_measurement.sql`
- **Vai trò trong đời sống:** Sổ ghi EC đo tại hiện trường do cán bộ nhập, phải qua duyệt; để riêng hẳn khỏi các bảng EC của MRC.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (CREATE, GRANT, INSERT nhật ký). Từ chối chạy ngoài `dongthap_gis`.
- **Bảng/view/hàm SQL tạo ra:** bảng `dss_reference.field_measurement`, `dss_reference.field_measurement_review`; view `dss_reference.v_field_measurement_status`; hàm `dss_reference.stamp_field_event`, cập nhật `webgis_security.audit_dss_insert`; trigger đóng dấu, chặn sửa và ghi nhật ký (`field_measurement_*`, `field_review_*`, `audit_field_*`); index `field_measurement_observed_idx`, `field_review_latest_idx`, index bản đồ `field_measurement_geom_gist`. Cấp quyền đọc cho `webgis_reader`, đọc+thêm cho `webgis_writer`.
- **Muốn sửa … thì có tìm đến file này không?:** Có, khi đổi cách lưu/duyệt EC thực địa.

### `sql/checks/` (năm tệp, chỉ đọc)
- `00_kiem_tra_hien_trang.sql`: 12 khối kiểm tra A01–A12 (kết nối, PostGIS, bảng, cột, khóa, index, snapshot, độ phủ EC, đối tượng không gian, ranh giới, cống). Chạy từng khối, lưu CSV.
- `01_audit_v2.sql`: đếm số dòng các bảng nghiệp vụ và vài kiểm tra bổ sung.
- `01_erd_query.sql`: liệt kê bảng, cột, khóa ngoại để vẽ sơ đồ quan hệ (ERD) trong pgAdmin.
- `02_gate_queries.sql`: ví dụ truy vấn không gian: cống nào nằm trong ranh giới được chọn.
- `03_webgis_readiness.sql`: đối chiếu DB trước khi xây API trạm/lịch sử EC; chạy trong `BEGIN READ ONLY`.
Không tệp nào tạo bảng hay ghi DB. Dùng khi cần chứng minh hiện trạng DB.

### `sql/migrations/11_schema_migration.sql`
- **Vai trò trong đời sống:** Bản nâng cấp cho đường ống dữ liệu: thêm bảng lưu lượng, điểm thủy văn, triều, nguồn tọa độ cống, cờ chất lượng.
- **Đọc/ghi dữ liệu ở đâu (I/O):** **GHI DB** (CREATE, INSERT) trong `BEGIN ... COMMIT`, dùng `IF NOT EXISTS`. Ghi chú trong tệp: repository không có bằng chứng tệp này đã từng chạy trên DB thật.
- **Bảng/view/hàm SQL tạo ra:** bảng `public.hydro_point`, `public.discharge_observation`, `public.tide_point`, `public.tide_prediction`, `public.gate_coordinate_source`, `public.data_quality_flag` (kèm dữ liệu mẫu); index duy nhất `uq_gate_coordinate_primary` và các index thời gian/hình học.
- **Muốn sửa … thì có tìm đến file này không?:** Chỉ khi làm tiếp đường ống ETL; đối chiếu với DB thật trước khi chạy.

---

### 2.E.6. Thư mục `tests/`: bộ kiểm thử tự động

**Kiểm thử tự động là gì?** Hãy nghĩ tới người nếm thử món ăn trước khi mang ra cho khách. Mỗi tệp test là một danh sách câu hỏi kiểu "đưa đầu vào X thì phải ra kết quả Y". Máy tự chạy hết các câu hỏi và báo câu nào sai. Khi sửa mã, chạy lại test để chắc chắn không làm hỏng chỗ khác.

- Tệp `*.test.mjs` kiểm phần giao diện (JavaScript), chạy bằng Node: `node --test tests/<tên>.test.mjs`. Chạy tất cả: `node --test tests/*.test.mjs`. Lưu ý: còn một test nằm ngoài thư mục này, `frontend/src/features/gate-simulation-draft.test.js`; lệnh trên không chạy nó, phải chạy riêng `node --test frontend/src/features/gate-simulation-draft.test.js`.
- Tệp `test_*.py` kiểm phần máy chủ và mô hình (Python): `.venv\Scripts\python.exe -m unittest tests.<tên> -v`. Chạy tất cả: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v`.
- Lối tắt: `python -m tools check smoke` (nhanh) hoặc `python -m tools check full`.
- Nếu test Node báo `spawn EPERM` trong môi trường hạn chế, đó là lỗi quyền tạo tiến trình, không phải mã hỏng.

#### Test giao diện (JavaScript)

**`tests/database_history.test.mjs`** — Kiểm `frontend/src/features/database-history.js`. Tình huống: đổi ngày/loại dữ liệu thì xóa ngay biểu đồ, bảng, thống kê, CSV cũ; đổi bộ lọc thì bỏ qua kết quả trả về muộn của lần trước. Chạy: `node --test tests/database_history.test.mjs`.

**`tests/field_measurements.test.mjs`** — Kiểm `frontend/src/features/field-measurements.js` và `observations-map.js`. Tình huống: đổi đơn vị EC hiện đúng giá trị quy đổi trước khi gửi; số đo đang chờ duyệt hoặc bị từ chối không bao giờ lên bản đồ. Chạy: `node --test tests/field_measurements.test.mjs`.

**`tests/forecast_flows.test.mjs`** — Kiểm `forecasts.js`, `multivariate-forecast.js`, `next-forecast.js`, `prediction-history.js`. Tình huống: yêu cầu bằng chứng khóa EC và hiển thị mốc so sánh; tách kết quả thủy văn khỏi mô hình khí tượng; đổi thí nghiệm thì bỏ phản hồi cũ; tách đánh giá nhiều năm khỏi dữ liệu huấn luyện. Chạy: `node --test tests/forecast_flows.test.mjs`.

**`tests/forecast_issue_panel.test.mjs`** — Kiểm `frontend/src/features/forecast-issue-panel.js`. Tình huống: suất dự báo bị bỏ lỡ vẫn hiện; phát hành muộn tách khỏi điểm đúng hạn; EC MRC và EC thực địa đã duyệt được chấm riêng. Chạy: `node --test tests/forecast_issue_panel.test.mjs`.

**`tests/forecast_map_overlay.test.mjs`** — Kiểm `frontend/src/shared/forecast-map-overlay.js`, `river-interpolation.js`, `river-geometry.js`. Tình huống: 35 đoạn sông giữ đủ ba mốc gồm Mỹ Thuận; từ chối tháng/EC/ngưỡng sai; lớp dự báo lỗi thì khôi phục bản gốc; chỉ cho dùng hai trạm khi Mỹ Thuận thiếu mẫu lịch sử thật. Chạy: `node --test tests/forecast_map_overlay.test.mjs`.

**`tests/forecast_month_choice.test.mjs`** — Kiểm `multivariate-forecast.js`. Tình huống: các nút chọn nhanh tháng dự báo đi theo tháng hiện tại, kể cả khi qua năm mới. Chạy: `node --test tests/forecast_month_choice.test.mjs`.

**`tests/frontend_api.test.mjs`** — Kiểm `frontend/src/api.js`. Tình huống: gửi hồ sơ cống dạng JSON; đổi trạm thì hủy yêu cầu cũ mà không báo lỗi máy chủ; thông báo lỗi của API đến được giao diện; phản hồi không phải JSON không được coi là thành công. Chạy: `node --test tests/frontend_api.test.mjs`.

**`tests/gate_dossiers.test.mjs`** — Kiểm `gate-dossiers.js` và `gate-simulation-draft.js`. Tình huống: chọn/bỏ chọn cống xóa số đo cũ; chuyển từ bản đồ không chép EC mô phỏng thành số đo thực địa; dự báo tới muộn không ghi đè ngữ cảnh mới. Chạy: `node --test tests/gate_dossiers.test.mjs`.

**`tests/gate_forecast_context.test.mjs`** — Kiểm `gate-forecast-context.js` (cùng `gate-intake-rules.js`, `river-interpolation.js`). Tình huống: chiếu EC dự báo lên vị trí cống theo các mốc trạm; giữ EC Mỹ Tho phía hạ lưu; dữ liệu sai thì không dùng lại kết quả cống trước; không sửa đối tượng đầu vào. Chạy: `node --test tests/gate_forecast_context.test.mjs`.

**`tests/gate_intake_parity.test.mjs`** — Kiểm `frontend/src/shared/gate-intake-rules.js` với các ca trong `tests/fixtures/gate_intake_cases.json`. Mỗi ca tạo một test `gate fixture <id>`. Cùng tệp mẫu này được `tests/test_gate_intake_rules.py` dùng, để quy tắc phía giao diện và phía máy chủ cho cùng kết quả. Chạy: `node --test tests/gate_intake_parity.test.mjs`.

**`tests/gate_intake_rules.test.mjs`** — Kiểm `gate-intake-rules.js` và `gate-simulation-draft.js`. Tình huống: bộ quy tắc mặc định không bị sửa; ngưỡng tính cả dấu bằng; phải xác nhận cùng mốc cao độ mới tính chênh mực nước; thiếu nguồn hoặc tình trạng cơ khí không rõ thì phải bổ sung; mẫu thiếu múi giờ hoặc ở tương lai là không đủ; hạn dùng mẫu chính xác tới mili giây. Chạy: `node --test tests/gate_intake_rules.test.mjs`.

**`tests/gate_intake_screening.test.mjs`** — Kiểm `frontend/src/features/gate-intake-screening.js`. Tình huống: máy chủ và giao diện đồng ý thì mới cho xuất; tách mục dự báo và mục đo thực địa; hiện hạn dùng theo GMT+7; sửa số đo thì bỏ kết luận cũ. Chạy: `node --test tests/gate_intake_screening.test.mjs`.

**`tests/gated_waterways.test.mjs`** — Kiểm `frontend/src/features/gated-waterways.js`. Tình huống: mức cảnh báo chỉ theo cặp ngưỡng EC đang chọn; mỗi nhánh kênh được cắt đúng tại cống của nó. Chạy: `node --test tests/gated_waterways.test.mjs`.

**`tests/map_particles.test.mjs`** — Kiểm `frontend/src/features/map-particles.js` (hạt chuyển động thể hiện gió và dòng chảy). Tình huống: hướng gió đúng quy ước khí tượng; dữ liệu gió thiếu/cũ thì không vẽ; hạt sông chỉ thể hiện dòng chảy, không tô màu mặn; tắt được và dừng vẽ khi đóng. Chạy: `node --test tests/map_particles.test.mjs`.

**`tests/observations_contract.test.mjs`** — Kiểm `frontend/src/shared/observation-contract.js` và `research-utils.js`. Tình huống: giữ EC bằng 0, ngày chỉ có ngày (không bịa giờ), cờ O/E; từ chối sai trạm, sai đơn vị, thiếu nguồn; bỏ qua kết quả về muộn của trạm trước. Chạy: `node --test tests/observations_contract.test.mjs`.

**`tests/observations_map_gates.test.mjs`** — Kiểm `frontend/src/features/observations-map.js`. Tình huống: cống lấy từ DB giữ hình học GeoJSON tách khỏi thuộc tính hiển thị. Cần đã chạy `npm.cmd --prefix frontend ci` vì test đọc thư viện `ol` trong `frontend/node_modules/`. Chạy: `node --test tests/observations_map_gates.test.mjs`.

**`tests/overview_freshness.test.mjs`** — Kiểm `frontend/src/features/overview.js`. Tình huống: nêu đúng tháng đo và tháng dự báo được hỗ trợ; nhãn EC bị khóa không có tháng hỗ trợ dự báo. Chạy: `node --test tests/overview_freshness.test.mjs`.

**`tests/point_inspection.test.mjs`** — Kiểm `frontend/src/features/point-inspection.js` (bấm vào bản đồ để xem). Tình huống: tìm điểm gần nhất trên đoạn sông chứ không chỉ đỉnh gần nhất; tọa độ sai không ra kết quả; giữ EC bằng 0; cần cờ mô phỏng rõ ràng. Chạy: `node --test tests/point_inspection.test.mjs`.

**`tests/river_geometry.test.mjs`** — Kiểm `frontend/src/features/river-geometry.js`. Tình huống: làm mượt 35 đoạn sông mà vẫn giữ nguyên các mốc; dải màu cắt theo khoảng cách thật và cắt đúng tại ngưỡng EC; kênh tách riêng. Chạy: `node --test tests/river_geometry.test.mjs`.

**`tests/river_interpolation.test.mjs`** — Kiểm `frontend/src/shared/river-interpolation.js` và `river-profile.js`. Tình huống: nội suy tuyến tính từng chặng giữ mốc giữa (Mỹ Thuận); chỉ dùng hai trạm khi thiếu mẫu lịch sử; mốc sai không ra con số. Chạy: `node --test tests/river_interpolation.test.mjs`.

**`tests/river_profile.test.mjs`** — Kiểm `frontend/src/features/river-profile.js` (biểu đồ dọc sông 175 km). Tình huống: đổi đơn vị thì đổi cả giá trị lẫn ngưỡng; đủ 27 cống, cống trùng vị trí được tách làn; chọn trên biểu đồ thì bản đồ nhảy theo. Chạy: `node --test tests/river_profile.test.mjs`.

**`tests/simulation_display.test.mjs`** — Kiểm `frontend/src/shared/simulation-display.js`. Tình huống: nhãn phân biệt ước tính, số 0 và không có dữ liệu; dải màu liên tục ở ngưỡng; màu chuyển tiếp của cống là hổ phách, không phải xanh "được lấy nước". Chạy: `node --test tests/simulation_display.test.mjs`.

**`tests/timeline_months.test.mjs`** — Kiểm `frontend/src/shared/timeline-months.js` và `timeline-scrubber.js`. Tình huống: tháng ngoài khoảng có dữ liệu bị kẹp về tháng gần nhất và có thông báo; dữ liệu thưa không sinh ra tháng giả; 12/2023 và 01/2024 có nhãn nguồn khác nhau. Chạy: `node --test tests/timeline_months.test.mjs`.

**`tests/timeline_scrubber.test.mjs`** — Kiểm `timeline-scrubber.js` và `overview.js`. Tình huống: bộ ngưỡng theo cây trồng giữ đơn vị EC; từ chối ngưỡng trống, âm, bằng nhau hoặc ngược; tháng mới hơn luôn thắng phản hồi cũ; lỗi mạng được báo, hủy yêu cầu thì im lặng. Chạy: `node --test tests/timeline_scrubber.test.mjs`.

**`tests/water_advisory.test.mjs`** — Kiểm `frontend/src/shared/water-advisory.js`. Tình huống: so sánh với kịch bản cây trồng ở đúng biên mà không khẳng định "phù hợp"; EC thiếu, không phải số hoặc vô lý thì để "chưa biết". Chạy: `node --test tests/water_advisory.test.mjs`.

**`tests/fixtures/gate_intake_cases.json`** — Không phải test mà là "đề bài mẫu": thời điểm xét, một bộ số đo cống gốc (EC ngoài/trong, mực nước, cùng mốc cao độ, tình trạng cơ khí) và danh sách các ca biến thể có kết quả mong đợi. Dùng chung cho `gate_intake_parity.test.mjs` và `test_gate_intake_rules.py`.

#### Test máy chủ và mô hình (Python)

**`tests/test_backend_audit.py`** — Kiểm nhiều chỗ ở `backend/` (`domain/gates.py`, `domain/gate_simulation.py`, `services/dss_storage.py`, `forecasts.py`, `multivariate.py`, `spatial_inputs.py`, `repositories/workspace.py`). Tình huống: chế độ postgres vẫn giữ điểm RIA2 tham khảo; bản nháp cống sai đơn vị bị từ chối trước khi lưu; thứ tự thời gian sai bị chặn; thời tiết phải khớp đúng tháng. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_backend_audit -v`.

**`tests/test_backtest_asof_ec.py`** — Kiểm `tools/backtest_protocols.py`. Tình huống: dự báo tháng đầu không được biết mẫu tháng 12 trước; ranh giới năm và cách chia kỳ đúng. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_backtest_asof_ec -v`.

**`tests/test_collect_fes2022b.py`** — Kiểm `scripts/utilities/collect_fes2022b.py` (tải atlas triều). Tình huống: kiểm tra rồi giải nén, bỏ qua tệp đã có; tệp nén hỏng không bao giờ được công bố; tải dở thì tiếp tục được; kiểm danh sách máy chủ trước khi mở. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_collect_fes2022b -v`.

**`tests/test_data_freshness.py`** — Kiểm `backend/domain/data_freshness.py` và `backend/api/data_freshness.py`. Tình huống: ranh giới trạng thái mới/cũ; báo cáo thời tiết giữ nguồn tải; API trả báo cáo; báo cáo thật liệt kê thời tiết, thủy văn, EC bị khóa. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_data_freshness -v`.

**`tests/test_database_pool.py`** — Kiểm `backend/database.py` và `backend/repositories/dss_storage.py`. Tình huống: nhóm kết nối đọc được dùng lại và có giới hạn; kết nối ghi dùng role riêng, dung lượng nhỏ, không dùng chung với role đọc. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_database_pool -v`.

**`tests/test_dss_postgres_contract.py`** — Kiểm lưu phát hành dự báo và EC thực địa trên PostgreSQL thật (`backend/domain/forecast_issue.py`, `field_measurement.py`, `repositories/field_measurement`). Tình huống: thêm và đọc lại vẫn giữ đúng đơn vị API. Tự bỏ qua nếu chưa đặt biến `WEBGIS_TEST_PG_DSN` (một cơ sở dữ liệu thử có quyền TEMP và PostGIS). Chạy: `.venv\Scripts\python.exe -m unittest tests.test_dss_postgres_contract -v`.

**`tests/test_dss_storage_errors.py`** — Kiểm `backend/services/dss_storage.py`. Tình huống: trùng khóa thành lỗi 409; vi phạm ràng buộc thành 422; thiếu schema và thiếu quyền được báo riêng. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_dss_storage_errors -v`.

**`tests/test_experiment_ec_upstream_asof.py`** — Kiểm `tools/feature_building.py` (`ec_features`). Tình huống: mẫu tháng 12 chưa được coi là có khi dự báo tháng 1. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_experiment_ec_upstream_asof -v`.

**`tests/test_field_measurement.py`** — Kiểm `backend/domain/field_measurement.py`, `services/field_measurements.py`, `repositories/field_measurements.py`. Tình huống: quy đổi µS/cm và các đơn vị; giá trị cao được gắn cờ chứ không bị loại; so với trung vị tháng của trạm gần nhất; thời điểm tương lai, giá trị âm, đơn vị lạ bị từ chối. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_field_measurement -v`.

**`tests/test_forecast_issue.py`** — Kiểm `backend/domain/forecast_issue.py` và `services/forecast_issues.py`. Tình huống: lịch phát hành là ngày 6 tháng trước; phát hành ghim đúng mô hình và dữ liệu; chấm điểm từ chối mẫu ngoài tháng; không được điền ngược lịch trước khi triển khai; API đúng hợp đồng. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_forecast_issue -v`.

**`tests/test_frozen_ec_followup.py`** — Kiểm `backend/domain/ec_gap_followup.py` và `scripts/evaluate_frozen_ec_followup.py`. Tình huống: EC bị giữ lại không lọt vào thí nghiệm; kết quả đã công bố khớp với API. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_frozen_ec_followup -v`.

**`tests/test_frozen_ec_gap.py`** — Kiểm `backend/domain/ec_gap_evaluation.py`, `multivariate_ec.py` và `scripts/evaluate_frozen_ec_gap.py`. Tình huống: lần phát hành đầu khóa nhãn; EC bị giữ lại không thay đổi dự báo; mô hình chỉ học một lần trên nhãn đã khóa; thời tiết sai bị từ chối. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_frozen_ec_gap -v`.

**`tests/test_frozen_ec_remedies.py`** — Kiểm `backend/domain/ec_gap_remedies.py` và `scripts/evaluate_frozen_ec_gap_remedies.py`. Tình huống: EC trạm lân cận tuân theo mốc phát hành; mỗi ứng viên chỉ học một lần; số liệu đã công bố khớp tệp kết quả. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_frozen_ec_remedies -v`.

**`tests/test_gate_intake_rules.py`** — Kiểm `backend/domain/gate_intake_rules.py` và API. Tình huống: các ca trong `fixtures/gate_intake_cases.json` cho đúng trạng thái; ứng viên p90 tái lập được nhưng không bật; API không lưu trạng thái và giới hạn kích thước gửi lên. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_gate_intake_rules -v`.

**`tests/test_model_loading.py`** — Kiểm `backend/domain/multivariate_ec.py`, `repositories/workspace.py`, `tools/model_training.py`, `tools/weather_inputs.py`. Tình huống: bộ nhớ đệm không bỏ qua kiểm tra mã băm; hâm nóng mô hình từng trạm; `model_training` không ghi gì nếu thiếu `--apply`; chỉ thử lại tải thời tiết khi lỗi tạm. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_model_loading -v`.

**`tests/test_multivariate_error_audit.py`** — Kiểm `scripts/audit_multivariate_errors.py`. Tình huống: ngưỡng phân vị chỉ từ dữ liệu huấn luyện; sai số giữ dấu lệch; lùi 2 tháng qua năm mới đúng; mùa khô kết thúc tháng 4. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_multivariate_error_audit -v`.

**`tests/test_mytho_hydrology_primary.py`** — Kiểm mô hình Mỹ Tho đang phục vụ: `backend/domain/multivariate_ec.py`, `repositories/hydrology_inputs.py`, `services/multivariate.py`, so với `tools/feature_building.py`. Tình huống: đặc trưng thủy văn trên web khớp nghiên cứu; tháng chưa có dữ liệu bị từ chối; mô hình đăng ký dùng đúng 10 đặc trưng. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_mytho_hydrology_primary -v`.

**`tests/test_mythuan_three_station.py`** — Kiểm `scripts/evaluate_mythuan_three_station.py`. Tình huống: dự báo tháng 1 tôn trọng cả hai độ trễ công bố; nội suy tuyến tính dọc sông khác IDW; giá trị sai không bị âm thầm điền; mốc thứ ba dùng dự báo ngoài mẫu, không dùng số thật. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_mythuan_three_station -v`.

**`tests/test_rf_compact_artifacts.py`** — Kiểm `scripts/rf_compact_artifacts.py` (dùng `tools/backtest_protocols.py`, `tools/feature_building.py`). Tình huống: giữ nguyên dự báo nguồn và ngày phát hành; nhãn nguồn bị đổi thì từ chối; metrics tính lại từ dự báo đã đóng gói; ghi mã băm thật. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_rf_compact_artifacts -v`.

**`tests/test_run_webgis_args.py`** — Kiểm `run_webgis.py` (`bind_host`, `validate_lan_host`). Tình huống: `127.0.0.1` luôn chạy được; mở LAN cần khóa API và danh sách máy cho phép; địa chỉ máy phải là IP. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_run_webgis_args -v`.

**`tests/test_security.py`** — Kiểm `backend/main.py`, `backend/db_security.py`, `repositories/dss_storage.py`. Tình huống: giao diện không cần đăng nhập và không lưu đệm; khóa API được bắt buộc khi đã cấu hình; chặn ghi từ trang khác và máy lạ; role có quyền cao bị từ chối; kết nối ghi không bao giờ dùng tài khoản quản trị. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_security -v`.

**`tests/test_spatial_inputs_cache.py`** — Kiểm `backend/services/spatial_inputs.py`. Tình huống: yêu cầu lặp lại dùng cùng kết quả; nhiều yêu cầu song song chỉ dựng một lần; nguồn đổi thì dựng lại; qua ngày mới không trả dự báo cũ. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_spatial_inputs_cache -v`.

**`tests/test_spatial_simulation.py`** — Kiểm `backend/services/spatial_simulation.py`. Tình huống: quy đổi g/L giữ thang EC; ngưỡng cống tính cả dấu bằng và có vùng đệm; từ chối số âm/vô hạn; mọi khung thời gian cần xác nhận lấy nước thủ công; hành lang sông liền mạch với 27 cống. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_spatial_simulation -v`.

**`tests/test_sql_migrations.py`** — Kiểm nội dung chữ của `sql/32_dss_prediction_stations.sql` và `sql/32_dss_prediction_stations_down.sql` (không kết nối DB). Tình huống: bản nâng cấp mở rộng cả hai ràng buộc trạm; bản hoàn tác kiểm tra còn dòng Mỹ Thuận hay không. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_sql_migrations -v`.

**`tests/test_three_station_integration.py`** — Kiểm phối hợp ba trạm: `backend/domain/river_interpolation.py`, `services/spatial_simulation.py`, `spatial_inputs.py`, `multivariate_ec.py`. Tình huống: nội suy từng chặng giữ đúng mốc; dùng hai trạm đúng 13 tháng thiếu Mỹ Thuận; thiếu mốc dự báo thì báo không có, không tự dùng hai trạm; API cả hai tiền tố đường dẫn. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_three_station_integration -v`.

**`tests/test_workspace_api.py`** — Kiểm API workspace trong `backend/main.py`, `backend/domain/gates.py` và so với `run_gate_advisor.py`. Tình huống: đường dẫn cũ và mới cùng hợp đồng; cống sai không được "nâng cấp" bởi lời khai của trình duyệt; thiếu bằng chứng thì vẫn chưa xác minh; trạm lạ không trả dự báo rỗng giả an toàn; xuất dữ liệu đúng trạm. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_workspace_api -v`.

**`tests/test_workspace_workflows.py`** — Kiểm luồng dùng thật qua API và `backend/repositories/workspace.py`. Tình huống: số mẫu và nguồn từng trạm khớp danh mục; lọc ngày tính cả hai đầu; metrics thí nghiệm khớp dự báo cùng cohort; tải tệp ngoài danh sách cho phép bị chặn; lỗi PostgreSQL không tự chuyển sang snapshot. Chạy: `.venv\Scripts\python.exe -m unittest tests.test_workspace_workflows -v`.
