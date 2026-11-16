# Bản đồ dự án WebGIS EC Đồng Tháp (Project Map cho người mới)

**Ngày lập:** 17/11/2026. **Checkout:** `D:\Study\TLCN`, nhánh `temp` (HEAD `705ee73`).
**Phạm vi:** mô tả các tệp đang có trên đĩa tại ngày lập. Các tệp Git còn theo dõi nhưng đã bị xóa khỏi đĩa (chưa commit), ví dụ `pipelines/`, `data_processing/`, `run_forecast.py`, `run_forecast_multivariate.py`, `process_data.py`, `notebooks/legacy/`, một số `scripts/experiment_*`, **không** được mô tả. Thư mục `tools/` và vài script ngày 12/11 là **mới, chưa commit**.

Tài liệu này đứng ngoài mã vì mã nguồn không có comment. Đọc theo thứ tự:

1. Mục 0 (dưới đây): bức tranh 1 phút và 3 câu chuyện "bấm nút thì chạy file nào".
2. Phần 1: cây thư mục, mỗi dòng một câu ngắn.
3. Phần 2: từ điển từng tệp, chia 6 nhóm (2.A–2.F).
4. Phụ lục: bảng tra nhanh "muốn sửa X thì mở file nào" và từ điển thuật ngữ.

## 0. Bức tranh 1 phút

Hãy tưởng tượng dự án là một **quán ăn**:

- **Phòng ăn (frontend)** là trang web `workspace.html` người dùng nhìn thấy. Các file `.js` là nhân viên phục vụ: nhận yêu cầu khi người dùng bấm nút, chạy vào bếp lấy món, rồi bày lên bàn (vẽ bản đồ, biểu đồ, bảng).
- **Cửa chuyển món (API)** là các đường dẫn như `/api/v1/workspace/stations` hoặc `/api/v1/workspace/multivariate/predict`. Phòng ăn chỉ được gọi món qua cửa này, không được vào thẳng kho.
- **Bếp (backend, Python/FastAPI)** gồm ba lớp:
  - `backend/api/` và `backend/main.py`: **người nhận order** ở cửa, kiểm tra order hợp lệ rồi chuyển vào trong.
  - `backend/services/`: **bếp trưởng điều phối**, biết món này cần lấy nguyên liệu nào, gọi ai nấu.
  - `backend/domain/`: **đầu bếp làm toán**, chỉ lo công thức: nội suy EC dọc sông, chạy mô hình Random Forest, chấm điều kiện cống.
  - `backend/repositories/` và `backend/database.py`: **thủ kho**, người duy nhất mở kho lấy dữ liệu (PostgreSQL, CSV, JSON).
- **Kho (data/, runs/, PostgreSQL)**: số đo EC MRC, dữ liệu khí tượng, thủy văn, mô hình đã huấn luyện `model.joblib`.
- **Xưởng sau nhà (scripts/, tools/, sql/)**: dụng cụ chạy tay để thu thập dữ liệu, huấn luyện mô hình, tạo bảng DB. Trang web **không** gọi các file này khi đang chạy.
- **Phòng kiểm định (tests/)**: các bài kiểm tra tự động, chạy để chắc rằng sửa chỗ này không làm hỏng chỗ khác.

### 0.1. Câu chuyện 1: mở trang và xem bản đồ EC tháng

1. Chạy `.\start.ps1` → gọi `run_webgis.py` → mở `backend/main.py` (FastAPI) ở cổng 8000.
2. Trình duyệt mở `/workspace.html` → nạp `frontend/src/app/workspace.js`.
3. `workspace.js` gọi API `/api/v1/workspace/summary`, `/api/v1/workspace/stations`, `/api/v1/workspace/gates` → backend `backend/services/workspace.py` → `backend/repositories/workspace.py` đọc PostgreSQL (hoặc `data/research/workspace.json` ở chế độ snapshot).
4. Kéo thanh thời gian: `timeline-scrubber.js` → API `/api/v1/workspace/simulation/frame` (`backend/api/workspace.py`) → `backend/services/spatial_simulation.py` lấy EC 3 trạm từ `spatial_inputs.py` → nội suy dọc sông → trả về các đoạn sông có màu và chấm cống → `observations-map.js` vẽ lên OpenLayers.

Câu nói khi bảo vệ: "Khi kéo timeline, file `timeline-scrubber.js` gọi API `/api/v1/workspace/simulation/frame`; hàm `simulation_frame()` trong `spatial_simulation.py` nội suy EC giữa Tân Châu, Mỹ Thuận, Mỹ Tho rồi trả về màu từng đoạn sông."

### 0.2. Câu chuyện 2: bấm "Dự báo" EC Mỹ Tho

1. `frontend/src/features/multivariate-forecast.js` lấy trạm và tháng người dùng chọn, gửi `POST /api/v1/workspace/multivariate/predict` (cùng hàm này cũng mở ở `/api/v1/multivariate/predict`; giao diện dùng đường `/workspace`).
2. `backend/api/multivariate.py` hàm `predict()` → `backend/services/multivariate.py` hàm `predict()`.
3. Service gọi `backend/repositories/multivariate_inputs.py` (mưa, nhiệt, gió tháng `t−2`) và `hydrology_inputs.py` (lưu lượng Kratie, mực nước Tân Châu tháng `t−2`).
4. Service gọi `backend/domain/multivariate_ec.py` hàm `predict_month()`: đọc `data/models/multivariate_registry.json`, kiểm tra mã băm (hash) của `model.joblib`, cho 300 cây Random Forest cùng dự đoán, lấy trung bình và khoảng P10–P90 giữa các cây.
5. Kết quả JSON quay về frontend; `forecast-map-overlay.js` có thể đặt dự báo lên bản đồ.

### 0.3. Câu chuyện 3: mở Hồ sơ cống và rà soát điều kiện lấy nước

1. `frontend/src/features/gate-dossiers.js` hiển thị phần A (bối cảnh dự báo, qua `gate-forecast-context.js`) và phần B (số đo hai phía cống, qua `gate-intake-screening.js`).
2. Quy tắc rà soát chạy ở cả hai nơi giống hệt nhau: `frontend/src/shared/gate-intake-rules.js` (trên trình duyệt) và `backend/domain/gate_intake_rules.py` (trên máy chủ, API `/api/v1/gate-screening/evaluate`). Test `tests/gate_intake_parity.test.mjs` bảo đảm hai bản cho cùng kết quả.
3. Kết quả là **danh sách điều kiện đạt/chưa đạt**, không phải lệnh đóng/mở cống.

## Phần 1. Cây thư mục tổng quan

Ký hiệu: `[CHẠY WEB]` = được dùng khi trang web đang chạy; `[CHẠY TAY]` = chỉ dùng khi người chạy lệnh; `[DỮ LIỆU]` = nơi cất dữ liệu/bằng chứng, không phải mã. Thư mục chứa rất nhiều file cùng loại được tóm lại bằng `...`; danh sách đầy đủ có ở Phần 2.

```text
D:\Study\TLCN\
├── start.ps1                        [CHẠY WEB] Nút khởi động: build rồi chạy web
├── start-tinbranch.ps1              [CHẠY TAY] Chạy một worktree khác bằng cấu hình chính
├── run_webgis.py                    [CHẠY WEB] Nạp .env, chọn nguồn, bật máy chủ
├── run_monthly_ec.py                [CHẠY TAY] Thí nghiệm dự báo EC tháng kiểu cũ
├── run_gate_advisor.py              [CHẠY TAY] Chấm hồ sơ cống từ dòng lệnh
├── run_station_gate_link.py         [CHẠY TAY] Đánh giá liên kết trạm–cống
├── requirements*.txt                Danh sách thư viện Python cần cài
├── .env.example                     Mẫu cấu hình máy, không chứa mật khẩu thật
├── .env                             Cấu hình thật của máy, KHÔNG mở/commit
├── .gitignore / .gitattributes      Quy định Git bỏ qua/xử lý file nào
├── README.md                        Giới thiệu và cách chạy dự án
├── CLAUDE.md                        Biên bản bàn giao cho phiên làm việc sau
├── DESIGN.md                        Nguyên tắc thiết kế giao diện
├── REPO_MAP_FOR_THESIS.md           Bản đồ repo cũ, thiên về báo cáo
│
├── backend/                         [CHẠY WEB] Bếp: máy chủ Python FastAPI
│   ├── main.py                      Cửa chính: tạo app, gắn mọi API
│   ├── database.py                  Mở kết nối đọc PostgreSQL
│   ├── db_security.py               Kiểm tra tài khoản DB đúng vai trò
│   ├── security.py                  Lớp chặn request lạ, thêm header an toàn
│   ├── schemas.py                   Khuôn dạng JSON trả về cho trạm/EC
│   ├── intake.py                    API tab Chất lượng dữ liệu
│   ├── research.py                  Đường dẫn cũ /api/v1/research giữ tương thích
│   ├── requirements-api.txt         Thư viện riêng cho phần API
│   ├── api/                         Người nhận order: định nghĩa đường dẫn API
│   │   ├── workspace.py             Bản đồ, timeline, cống, xuất dữ liệu
│   │   ├── multivariate.py          Dự báo EC: catalog, inputs, predict
│   │   ├── dss_storage.py           Lưu/đọc lịch sử dự báo, bản nháp cống
│   │   ├── gate_screening.py        Rà soát điều kiện lấy nước qua cống
│   │   ├── forecast_issues.py       Sổ phát hành dự báo hằng tháng
│   │   ├── field_measurements.py    Phiếu EC thực địa: gửi, duyệt
│   │   └── data_freshness.py        Báo dữ liệu nguồn cũ hay mới
│   ├── services/                    Bếp trưởng: điều phối từng chức năng
│   │   ├── workspace.py             Tổng hợp trạm, quan trắc, cống
│   │   ├── spatial_inputs.py        Ghép EC 3 trạm theo tháng, lấp tháng thiếu
│   │   ├── spatial_simulation.py    Dựng khung bản đồ: sông màu, chấm cống
│   │   ├── multivariate.py          Ghép đầu vào rồi gọi mô hình dự báo
│   │   ├── forecasts.py             Biểu đồ hồi cứu, ước tính tháng cũ
│   │   ├── gates.py                 Chấm hồ sơ cống
│   │   ├── dss_storage.py           Kiểm tra rồi lưu dự báo/bản nháp
│   │   ├── forecast_issues.py       Phát hành và chấm điểm dự báo tháng
│   │   └── field_measurements.py    Nhận và duyệt phiếu thực địa
│   ├── domain/                      Đầu bếp làm toán: công thức thuần
│   │   ├── multivariate_ec.py       Nạp Random Forest, kiểm hash, dự báo
│   │   ├── river_interpolation.py   Nội suy tuyến tính EC dọc sông
│   │   ├── gates.py                 Luật chấm hồ sơ cống
│   │   ├── gate_intake_rules.py     Luật rà soát lấy nước (bản máy chủ)
│   │   ├── gate_simulation.py       Mô phỏng trạng thái cống theo luật
│   │   ├── ec_gap_*.py              Đọc kết quả thí nghiệm khóa EC
│   │   ├── forecast_issue.py        Lịch phát hành và cách chấm điểm
│   │   ├── field_measurement.py     Chuẩn hóa phiếu EC thực địa
│   │   ├── data_freshness.py        Tính độ trễ dữ liệu nguồn
│   │   └── workspace.py             Kiểm tra gói dữ liệu snapshot
│   └── repositories/                Thủ kho: đọc/ghi DB và file
│       ├── workspace.py             Đọc PostgreSQL hoặc workspace.json
│       ├── multivariate_inputs.py   Đọc khí tượng ERA5 theo tháng
│       ├── hydrology_inputs.py      Đọc lưu lượng Kratie, mực nước Tân Châu
│       ├── dss_storage.py           Ghi/đọc bảng lưu dự báo, bản nháp
│       ├── forecast_issues.py       Ghi/đọc bảng phát hành dự báo
│       └── field_measurements.py    Ghi/đọc bảng phiếu thực địa
│
├── frontend/                        [CHẠY WEB] Phòng ăn: giao diện trình duyệt
│   ├── workspace.html               Trang chính năm tab
│   ├── index.html / research.html   Trang cũ, tự chuyển sang workspace.html
│   ├── package.json                 Khai báo Vite và OpenLayers
│   ├── vite.config.js               Cấu hình đóng gói trang web
│   ├── scripts/generate-river-diagram.mjs  Vẽ sơ đồ sông SVG
│   ├── public/                      Font chữ, sơ đồ sông tĩnh
│   ├── dist/                        Bản đã build, máy chủ phục vụ (tự sinh)
│   └── src/
│       ├── api.js                   Hàm gọi API chung, có hẹn giờ
│       ├── main.js, map.js, style.css   Mã trang cũ, không trang nào nạp
│       ├── chart.js, intake.js, research-*.js  Biểu đồ, tab Chất lượng dữ liệu
│       ├── app/                     Khung ứng dụng: khởi động, tab, CSS
│       │   ├── workspace.js         Khởi động mọi tab, nối sự kiện
│       │   ├── navigation.js        Chuyển tab theo dấu # trên URL
│       │   ├── legacy.js            Chuyển trang cũ sang workspace.html
│       │   └── *.css                Màu, khoảng cách, bố cục
│       ├── features/                Từng chức năng trên màn hình
│       │   ├── observations*.js     Tab Quan trắc và bản đồ
│       │   ├── timeline-scrubber.js Thanh kéo chọn tháng
│       │   ├── river-*.js, gated-waterways.js, map-particles.js  Vẽ sông, nhánh, hạt chảy
│       │   ├── point-inspection.js  Bấm bản đồ xem giá trị ước tính
│       │   ├── multivariate-forecast.js, prediction-history.js  Tab Dự báo
│       │   ├── forecasts.js, next-forecast.js, forecast-issue-panel.js  Hồi cứu, sổ phát hành
│       │   ├── gate-*.js            Tab Hồ sơ cống
│       │   ├── field-measurements.js, weather-estimates.js  Phiếu thực địa, ước tính
│       │   ├── database-history.js  Bảng lịch sử EC PostgreSQL
│       │   └── overview.js          Tab Tổng quan
│       ├── shared/                  Công thức dùng chung cho nhiều tab
│       └── styles/simulation.css    CSS bản đồ mô phỏng
│
├── data/                            [DỮ LIỆU] Kho dữ liệu đầu vào
│   ├── raw/                         Dữ liệu gốc tải về (EC MRC, khí tượng...)
│   ├── external/                    Dữ liệu ngoài theo đợt thu thập
│   ├── research/                    workspace.json, mẫu EC tháng, registry thí nghiệm
│   ├── models/                      multivariate_registry.json, CSV dự báo cũ
│   ├── biengioi/                    Ranh giới hành chính, hành lang sông GeoJSON
│   ├── contracts/                   Khuôn dữ liệu cống, chính sách cống
│   ├── metadata/                    Từ điển dữ liệu, danh mục nguồn
│   ├── 8file/                       Bộ 8 CSV người dùng cung cấp
│   ├── processed/, staging/, features/  Dữ liệu trung gian đã xử lý
│   └── archive/                     Dữ liệu cũ, không dùng
│
├── runs/                            [DỮ LIỆU] Mô hình đã huấn luyện và lần chạy
│   └── multivariate_ec/mytho/20261108T_HYDROLOGY_PRIMARY_V1/  Mô hình Mỹ Tho đang phục vụ
│       ├── model.joblib             Bộ 300 cây Random Forest đã lưu
│       ├── manifest.json            Lý lịch mô hình: đặc trưng, hash, điểm
│       └── predictions.csv          Kết quả dự báo đã lưu
├── outputs/                         [DỮ LIỆU] Bằng chứng thí nghiệm giảm sai số
├── reports/                         [DỮ LIỆU] Biên bản UAT, dọn dẹp repo
│
├── scripts/                         [CHẠY TAY] ~115 kịch bản thu thập, thí nghiệm
│   └── utilities/                   Tải dữ liệu triều FES2022b
├── tools/                           [CHẠY TAY] Lệnh gộp: kiểm tra, huấn luyện, bảo mật (mới)
├── data_collection/                 [CHẠY TAY] Tải GloFAS, DAHITI, UHSLC, ranh giới
├── etl/etl_csv.py                   [CHẠY TAY] Nạp CSV vào DB kiểu cũ
├── sql/                             [CHẠY TAY] Lệnh tạo bảng, quyền PostgreSQL
│   ├── checks/                      Truy vấn kiểm tra hiện trạng DB
│   └── migrations/                  Lệnh nâng cấp cấu trúc DB
├── config/                          Cấu hình tải FES, GloFAS
├── tests/                           Bài kiểm tra tự động frontend + backend
│   └── fixtures/                    Dữ liệu mẫu cho test
└── docs/                            Tài liệu, báo cáo LaTeX, ôn tập
    ├── bao_cao_webgis_ec_mytho_2026_11_08/  Báo cáo đồ án LaTeX
    ├── on_tap_hoi_dong_2026-11-13/  Bộ ôn tập bảo vệ
    ├── project_map/                 Tài liệu bạn đang đọc
    └── *.md                         Ghi chép từng đợt thí nghiệm, hướng dẫn
```

Thư mục do máy tự sinh, không cần học: `.venv/`, `.venv-api/` (môi trường Python), `frontend/node_modules/` (thư viện JavaScript), `frontend/dist/` (bản build), `__pycache__/`.

## Phần 2. Từ điển từng file

Mỗi file trình bày theo 4 ý: vai trò đời sống, đọc/ghi dữ liệu (I/O), các hàm cốt lõi, và có nên tìm đến file này khi sửa không. Phần 2 chia 6 nhóm: 2.A backend lõi, 2.B backend nghiệp vụ, 2.C frontend bản đồ/quan trắc, 2.D frontend dự báo/cống, 2.E khởi động/SQL/test, 2.F scripts; cuối cùng 2.G là các điểm dễ bị hỏi vặn.

## 2.A. Backend lõi: khởi động, API, kết nối dữ liệu

Phần này giải thích các tệp trong `backend/` (trừ `backend/domain/` và `backend/services/`, được mô tả ở phần khác). Trước khi đọc, cần nắm vài từ dùng nhiều lần:

- **Backend**: chương trình chạy ở máy chủ, nhận yêu cầu từ trang web và trả dữ liệu. Ở dự án này backend viết bằng Python với thư viện **FastAPI**.
- **API**: "quầy giao dịch" của backend. Trang web gửi một yêu cầu tới một địa chỉ (ví dụ `/api/v1/stations`), backend trả lại dữ liệu.
- **Endpoint (điểm cuối)**: một địa chỉ cụ thể của API, kèm một **phương thức HTTP**: `GET` là "xin xem", `POST` là "gửi lên để xử lý hoặc lưu".
- **JSON**: dạng văn bản có cấu trúc (giống phiếu điền sẵn các ô `"tên": giá trị`) mà backend và trang web dùng để trao đổi.
- **Router (bộ định tuyến)**: một nhóm endpoint gom chung, giống một "tổ" trong cơ quan. `main.py` gắn các tổ này vào ứng dụng, có thể thêm **tiền tố** (prefix) như `/api/v1` vào trước mọi địa chỉ của tổ.
- **Repository (kho truy xuất)**: lớp mã chỉ lo việc đọc/ghi dữ liệu (cơ sở dữ liệu hoặc tệp), không quyết định nghiệp vụ.
- **Service (dịch vụ)**: lớp ở giữa, nhận yêu cầu từ API, gọi repository, xử lý rồi trả kết quả. Mô tả ở phần khác.
- **PostgreSQL / PostGIS**: hệ quản trị cơ sở dữ liệu (DB) và phần mở rộng để lưu tọa độ bản đồ. **Bảng** trong DB giống một sheet Excel; **schema** trong DB là một "ngăn tủ" chứa nhiều bảng (`public`, `dss_reference`...).
- **SQL**: ngôn ngữ để hỏi DB ("lấy các dòng trạm không phải dữ liệu mẫu").

Đường đi chung của một yêu cầu: trang web → `main.py` (cổng vào, kiểm tra an ninh) → tệp trong `backend/api/` (nhận và kiểm tra phiếu yêu cầu) → `backend/services/` (xử lý) → `backend/repositories/` hoặc `backend/database.py` (lấy dữ liệu) → trả JSON ngược lại.

---

### `backend/__init__.py`
- **Vai trò trong đời sống:** Tấm biển "đây là thư mục mã Python của backend". Python cần tệp này để coi `backend` là một gói (package) và cho phép viết `from backend.xxx import ...`. Trong tệp chỉ có một dòng mô tả, không có mã chạy.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: không. Đầu ra: không.
- **Các hàm cốt lõi:** Không có hàm.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Không — nếu muốn thêm API hay sửa logic, hãy sang `backend/main.py` hoặc thư mục `backend/api/`.
  - Không — tệp này gần như không bao giờ cần sửa.

### `backend/main.py`
- **Vai trò trong đời sống:** Cổng chính và ông bảo vệ của cả backend. Khi máy chủ khởi động, tệp này dựng ứng dụng FastAPI, mở sẵn đường kết nối DB, gắn tất cả các "tổ" API vào đúng địa chỉ, cài các lớp kiểm tra an ninh và quy định cách báo lỗi. Ngoài ra nó tự chứa vài endpoint đọc trạm/EC trực tiếp từ PostgreSQL.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: biến môi trường (thiết lập lấy từ `.env`, ví dụ `WEBGIS_RESEARCH_MODE`, `WEBGIS_CORS_ORIGINS`, `WEBGIS_ALLOWED_HOSTS`, `WEBGIS_DSS_WRITES_ENABLED`, `DSS_PGUSER`); yêu cầu HTTP từ trình duyệt; DB PostgreSQL qua `backend/database.py` (bảng `public.measurement_site`, `public.data_source`, `public.source_dataset`, `public.conductivity_observation`). Đầu ra: JSON trả về trang web; không ghi DB.
- **Các hàm cốt lõi:**
  - `lifespan(app)`: việc làm lúc "mở cửa" và "đóng cửa" máy chủ. Lúc mở: gọi `warmup_models()` trong `backend/domain/multivariate_ec.py` để nạp sẵn mô hình dự báo (nạp lỗi chỉ ghi cảnh báo, không dừng máy chủ); nếu chế độ là `postgres` thì gọi `open_read_pool()` (mở **pool kết nối**, tức một nhóm đường dây DB mở sẵn để dùng lại, khỏi quay số mỗi lần); nếu cho phép ghi DSS và có `DSS_PGUSER` thì gọi `open_write_pool()` trong `backend/repositories/dss_storage.py`. Lúc đóng: đóng cả hai pool.
  - `app = FastAPI(...)` và các dòng `app.add_middleware(...)`: tạo ứng dụng và cài **middleware** (lớp lọc mà mọi yêu cầu phải đi qua trước khi tới endpoint, như cửa soát vé). Gồm `CORSMiddleware` (chỉ cho các trang web ở địa chỉ được phép gọi API, chỉ cho `GET`/`POST`), `SecurityMiddleware` (từ `backend/security.py`) và `TrustedHostMiddleware` (chỉ nhận yêu cầu gửi tới tên máy hợp lệ như `localhost`, `127.0.0.1`).
  - Các dòng `app.include_router(...)`: bảng phân địa chỉ. `workspace_router` gắn ở `/api/v1/workspace`; `multivariate_router`, `multivariate_history_router`, `data_freshness_router`, `gate_screening_router`, `forecast_issues_router`, `field_measurements_router` gắn ở `/api/v1`; `intake_router` gắn hai lần ở `/api/v1/workspace` và `/api/v1/research`; `research_router` tự có tiền tố `/api/v1/research`.
  - `workspace_error`, `site_not_found`, `dataset_not_found`, `database_error`: các "bộ phiên dịch lỗi". Khi lỗi xảy ra, chúng đổi thành JSON dễ hiểu: không có trạm → 404 `SITE_NOT_FOUND`; không có bộ dữ liệu → 404 `DATASET_NOT_FOUND`; lỗi DB → 503 với mã `DB_SCHEMA_MISMATCH` / `DB_PERMISSION_DENIED` / `DATABASE_ERROR`, cố ý không lộ câu SQL hay mật khẩu.
  - `app_health()`: `GET /api/v1/app-health`. Trả `status: ok` và chế độ nguồn đang chạy; không chạm DB.
  - `get_repository()`: tạo đối tượng `Repository` (trong `backend/database.py`) cho mỗi yêu cầu. Đây là một **dependency** (thứ FastAPI tự chuẩn bị và đưa vào hàm, giống người phụ việc đưa sẵn dụng cụ).
  - `health(repo)`: `GET /api/v1/health`. Gọi `Repository.health()` để thử kết nối thật và xác nhận giao dịch chỉ đọc.
  - `stations(repo)`: `GET /api/v1/stations`. Gọi `Repository.stations()`, đóng gói thành GeoJSON (dạng JSON chuẩn cho điểm bản đồ, tọa độ [kinh độ, vĩ độ]).
  - `datasets(site_code, repo)`: `GET /api/v1/stations/{site_code}/datasets`. Gọi `Repository.datasets()`, liệt kê các bộ dữ liệu EC (snapshot đã nhập) của một trạm.
  - `observations(site_code, repo, dataset_code, date_from, date_to, quality_flag, observed_or_estimated, limit, offset)`: `GET /api/v1/stations/{site_code}/observations`. Bắt buộc chọn `dataset_code`; lọc theo ngày, cờ chất lượng, đo/ước tính; chia trang (`limit` tối đa 1000). Từ chối 422 nếu `date_from > date_to`. Gọi `Repository.history()`, trả `ECHistory` có `has_more` cho biết còn trang sau.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm một nhóm API mới vào ứng dụng (phải `include_router` ở đây) hoặc đổi tiền tố địa chỉ.
  - Có — nếu muốn đổi danh sách trang được gọi API (CORS) hoặc cách báo lỗi DB.
  - Không — nếu muốn sửa câu SQL đọc trạm/EC thì sang `backend/database.py`; sửa API dự báo thì sang `backend/api/multivariate.py`.

### `backend/database.py`
- **Vai trò trong đời sống:** Thủ kho chỉ-được-xem của DB. Tệp này giữ "chùm chìa khóa" (pool kết nối chỉ đọc) và các câu SQL cố định để lấy trạm và lịch sử EC. Mọi kết nối đều bị khóa ở chế độ chỉ đọc, nên dù có lỗi mã cũng không ghi đè dữ liệu gốc.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: biến môi trường `PGHOST`, `PGPORT`, `PGDATABASE` (mặc định `dongthap_gis`), `WEBGIS_DB_USER` (mặc định `webgis_reader`), `WEBGIS_DB_PASSWORD`, `WEBGIS_DB_POOL_MAX`; các bảng `public.measurement_site`, `public.data_source`, `public.source_dataset`, `public.conductivity_observation`. Đầu ra: danh sách dòng dạng từ điển (dict) cho `main.py` và các repository; không ghi gì.
- **Các hàm cốt lõi:**
  - `SiteNotFound`, `DatasetNotFound`: hai loại lỗi riêng, nghĩa là "không có trạm thật mang mã này" và "bộ dữ liệu không có EC của trạm này".
  - `_read_config()`: gom thông số kết nối từ biến môi trường.
  - `_configure_reader(conn)`: mỗi khi mở đường dây mới thì đặt chế độ chỉ đọc, mức cô lập `REPEATABLE READ` (đếm số dòng và lấy trang cùng nhìn một "ảnh chụp" DB), rồi gọi `assert_application_role()` trong `backend/db_security.py` để từ chối tài khoản quản trị.
  - `open_read_pool()` / `close_read_pool()`: mở/đóng pool kết nối chỉ đọc (tối đa 1–10 đường, giới hạn câu lệnh 10 giây, múi giờ Việt Nam). Có khóa luồng (`RLock`) để hai yêu cầu cùng lúc không mở hai pool.
  - `read_connection()`: mượn một đường dây từ pool, dùng xong tự trả lại. Nhiều repository khác cũng gọi hàm này.
  - `STATIONS_SQL`, `SITE_SQL`, `DATASETS_SELECT`, `DATASETS_GROUP`: các câu SQL cố định; đều loại bỏ dữ liệu mẫu (`is_demo = false`). `DATASETS_SELECT` đếm số dòng đo (`O`), ước tính (`E`) và từng cờ chất lượng `UNVERIFIED/VALIDATED/SUSPECT/INVALID`.
  - `history_predicate(site_id, dataset_id, date_from, date_to, quality_flag, observed_or_estimated)`: ghép điều kiện lọc; giá trị người dùng gửi được truyền riêng (tham số hóa) để tránh bị chèn SQL độc. `date_to` được tính trọn ngày theo giờ Việt Nam.
  - Lớp `Repository` với `health()`, `stations()`, `datasets(site_code)`, `history(...)`: bốn câu hỏi DB phục vụ bốn endpoint trong `main.py`. `history` trả `{"dataset", "total", "items"}`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm cột trả về cho danh sách trạm hoặc lịch sử EC.
  - Có — nếu muốn đổi giới hạn thời gian câu lệnh hoặc số kết nối tối đa của pool đọc.
  - Không — nếu muốn sửa cách ghi bản lưu dự báo/hồ sơ cống thì sang `backend/repositories/dss_storage.py`.

### `backend/db_security.py`
- **Vai trò trong đời sống:** Người soát thẻ ở cửa kho. Mỗi lần ứng dụng mở đường dây DB, tệp này hỏi DB "tài khoản đang đăng nhập có phải quản trị viên, chủ sở hữu bảng hay thành viên nhóm đặc quyền không?". Nếu có thì từ chối, vì ứng dụng web không nên cầm chìa khóa vạn năng.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: bảng hệ thống của PostgreSQL (`pg_roles`, `pg_auth_members`, `pg_database`, `pg_namespace`, `pg_class`); xét các schema `public`, `dss_reference`, `webgis_security`, `webgis_research`. Đầu ra: không trả gì nếu ổn; báo lỗi `InsufficientPrivilege` nếu tài khoản có quyền quá cao.
- **Các hàm cốt lõi:**
  - `assert_application_role(conn)`: chạy một câu SQL đệ quy dò mọi nhóm quyền tài khoản thuộc về (superuser, tạo DB, tạo vai trò, bỏ qua bảo mật dòng, chủ DB/schema/bảng). Được `backend/database.py` (pool đọc) và `backend/repositories/dss_storage.py` (pool ghi) gọi.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm một schema mới vào danh sách cần kiểm chủ sở hữu.
  - Không — nếu bị lỗi "thiếu quyền đọc" thì xem cấp quyền trong `sql/` và `docs/database-security.md`, không nới lỏng kiểm tra ở đây.

### `backend/security.py`
- **Vai trò trong đời sống:** Bảo vệ đứng ở cửa API. Mọi yêu cầu gửi lên (không phải chỉ xem) phải đến từ đúng trang web của mình; các yêu cầu ghi dữ liệu quan trọng phải trình đúng "API key" (một mật mã dài cấp riêng). Bảo vệ còn dán thêm vài "nhãn an toàn" lên mọi câu trả lời.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: header của yêu cầu HTTP (`origin`, `sec-fetch-site`, `x-api-key`); biến môi trường `WEBGIS_SECURITY_ENABLED`, `WEBGIS_CORS_ORIGINS`, `WEBGIS_WRITE_API_KEY`. Đầu ra: cho qua, hoặc trả JSON lỗi 403/401; thêm header `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`, và `Cache-Control: no-store` cho đường dẫn `/api/` (không cho trình duyệt **cache**, tức lưu bản sao cũ để dùng lại).
- **Các hàm cốt lõi:**
  - `actor`: biến ngữ cảnh ghi "ai đang thao tác" (`LOCAL_APPLICATION`, `API_KEY_CLIENT`...). Repository ghi DB đọc biến này để đóng dấu người thực hiện.
  - `WRITE_PATHS`: danh sách địa chỉ ghi cần API key nếu có cấu hình: `/api/v1/workspace/gate-drafts`, `/api/v1/workspace/multivariate/history`, `/api/v1/multivariate/history`, `/api/v1/forecast-issues`, `/api/v1/field-measurements`.
  - `enabled()`: kiểm tra có bật bảo vệ không (mặc định bật).
  - `same_origin(request)`: từ chối 403 nếu yêu cầu đến từ trang web lạ.
  - `SecurityMiddleware.dispatch(request, call_next)`: quy trình soát cho từng yêu cầu: kiểm nguồn gốc với mọi yêu cầu không phải `GET/HEAD/OPTIONS` tới `/api/`; kiểm API key (so sánh kiểu chống đoán thời gian bằng `hmac.compare_digest`) với `POST` vào `WRITE_PATHS`; rồi gắn header an toàn.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một endpoint ghi mới và muốn nó cũng phải trình API key (thêm vào `WRITE_PATHS`).
  - Có — nếu muốn đổi header an toàn trả về.
  - Không — nếu muốn đổi quyền đọc/ghi của tài khoản DB thì sang `sql/` và `scripts/setup_security.py`.

### `backend/schemas.py`
- **Vai trò trong đời sống:** Bộ mẫu phiếu in sẵn. Mỗi lớp ở đây là một "mẫu đơn" quy định câu trả lời JSON phải có những ô nào, kiểu gì (gọi là **schema dữ liệu**). FastAPI dùng mẫu để kiểm tra và tự sinh tài liệu ở `/docs`.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: dữ liệu từ `backend/database.py`. Đầu ra: JSON đúng mẫu cho các endpoint trạm/EC trong `main.py`. Không đọc tệp hay DB trực tiếp.
- **Các hàm cốt lõi:**
  - `LOCAL_TZ`: múi giờ `Asia/Ho_Chi_Minh`, dùng ở nhiều tệp khác.
  - `QualityFlag` (`UNVERIFIED`, `VALIDATED`, `SUSPECT`, `INVALID`) và `ObservationKind` (`O` = đo, `E` = ước tính): danh sách giá trị hợp lệ.
  - `local_timestamp(value)`: đổi thời điểm sang giờ Việt Nam; báo lỗi nếu thời điểm từ DB không có múi giờ.
  - `Health`, `PointGeometry`, `StationProperties`, `StationFeature`, `StationCollection`: mẫu cho kết quả kiểm tra sức khỏe và danh sách trạm GeoJSON (hệ tọa độ `EPSG:4326`).
  - `DatasetSummary`, `DatasetCollection`: mẫu tóm tắt một bộ dữ liệu EC (mã, `sha256`, tên tệp nguồn, số dòng theo từng cờ...). `sha256` là **hash**: "dấu vân tay" của tệp, đổi một byte là đổi dấu.
  - `ECObservation`, `HistoryFilters`, `ECHistory`: mẫu cho một dòng EC (đơn vị luôn `mS/m`, giá trị không âm) và cả trang lịch sử, ghi rõ `data_kind = historical_observations`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một cột mới vào JSON lịch sử EC (phải thêm cả ở đây lẫn câu SQL trong `database.py`).
  - Không — các API dự báo, hồ sơ cống không dùng mẫu ở đây; mẫu yêu cầu của chúng nằm trong từng tệp `backend/api/*.py`.

### `backend/intake.py`
- **Vai trò trong đời sống:** Bàn tiếp nhận hồ sơ chưa thẩm định. Tệp này cho xem bộ số liệu người dùng gửi (đợt 15/10/2026) nhưng luôn đóng dấu "CHƯA XÁC MINH, không dùng huấn luyện, không dùng quyết định cống". Trước khi cho xem, nó kiểm dấu vân tay từng tệp; sai dấu thì từ chối, không thay bằng dữ liệu mẫu.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: thư mục `data/external/user_v3_review_20261015/` gồm `audit.json`, các tệp gốc liệt kê trong đó, `station_coverage.json`, `normalized_review.json`, `normalized_review.manifest.json`. Đầu ra: JSON cho tab Chất lượng dữ liệu (`frontend/src/intake.js`). Không ghi gì.
- **Các hàm cốt lõi:**
  - `read_intake()`: đọc `audit.json`, kiểm tên tệp không thoát khỏi thư mục và so `sha256` từng tệp; lỗi → 503.
  - `summary()`: `GET /api/v1/workspace/intake` (và bản trùng `/api/v1/research/intake`). Trả trạng thái `UNVERIFIED`, danh sách tệp, số đếm, các vấn đề phát hiện.
  - `coverage()`: `GET .../intake/coverage`. Trả độ phủ theo trạm từ `station_coverage.json`.
  - `read_normalized()`: đọc bảng chuẩn hóa, kiểm hash khớp manifest, kiểm bảng thuộc đúng tệp Excel gốc, và mọi dòng phải là `REVIEW_ONLY`, không được phép dùng huấn luyện/quyết định cống.
  - `points()`: `GET .../intake/measurement-points`. Danh sách điểm đo kèm số bản ghi.
  - `observations(point, offset, limit)`: `GET .../intake/observations?point=...`. Các dòng của một điểm đo, chia trang (tối đa 200); không có điểm → 404.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi thư mục hồ sơ tiếp nhận hoặc thêm thông tin trả về cho tab Chất lượng dữ liệu.
  - Không — nếu muốn sửa cách hiển thị bảng tiếp nhận thì sang `frontend/src/intake.js`.
  - Không — muốn đưa số liệu này thành quan trắc chính thức thì không làm ở đây; phải qua quy trình nhập/kiểm định riêng.

### `backend/research.py`
- **Vai trò trong đời sống:** Biển chỉ đường cũ còn giữ lại. Trước đây các API nằm dưới `/api/v1/research`; tệp này giữ địa chỉ cũ chạy được bằng cách gắn lại toàn bộ `workspace_router` dưới tiền tố đó, và cho các script cũ tiếp tục `import` hai hàm quen thuộc.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào/đầu ra: giống hệt các endpoint của `backend/api/workspace.py`, chỉ khác tiền tố `/api/v1/research`.
- **Các hàm cốt lõi:**
  - `router`: router tiền tố `/api/v1/research`, chứa `workspace_router`. Ví dụ `GET /api/v1/research/summary` chạy cùng hàm với `GET /api/v1/workspace/summary`.
  - Nhập lại `validate_bundle` (từ `backend/domain/workspace.py`) và `load_bundle` (từ `backend/services/workspace.py`): để `scripts/check_webgis_setup.py` và `scripts/import_research_workspace.py` vẫn chạy.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Không — muốn sửa một API workspace thì sang `backend/api/workspace.py`; thay đổi sẽ tự có ở cả hai địa chỉ.
  - Có — chỉ khi quyết định bỏ hẳn địa chỉ cũ `/api/v1/research` (cần kiểm script và trang nào còn gọi).

### `backend/requirements-api.txt`
- **Vai trò trong đời sống:** Danh sách đồ nghề cần mua trước khi chạy backend. Mỗi dòng là một **dependency** (thư viện bên ngoài mà mã cần) kèm phiên bản cố định đã thử cùng nhau trên Python 3.12 ngày 16/10/2026.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: được `pip install -r` đọc khi cài môi trường `.venv`. Đầu ra: không.
- **Các hàm cốt lõi (thư viện):** `fastapi==0.141.1` (khung API), `uvicorn==0.53.0` (máy chạy web), `psycopg[binary]==3.3.5` (trình kết nối PostgreSQL), `psycopg-pool==3.3.3` (pool kết nối), `pydantic==2.13.5` (kiểm tra mẫu dữ liệu), `tzdata==2026.4` (dữ liệu múi giờ). Lưu ý: các thư viện mô hình như pandas, scikit-learn không có trong danh sách này (cài ở nơi khác, xem `README.md`/`docs/run_guide.md`).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu nâng cấp FastAPI hay psycopg, hoặc thêm thư viện mới cho API.
  - Không — muốn đổi thông số kết nối DB thì sửa `.env` (không commit), không phải tệp này.

---

### `backend/api/__init__.py`
- **Vai trò trong đời sống:** Tấm biển đánh dấu `backend/api` là gói Python. Tệp rỗng.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Không.
- **Các hàm cốt lõi:** Không có.
- **Muốn sửa … thì có tìm đến file này không?:** Không — mọi thay đổi API nằm ở các tệp cùng thư mục.

### `backend/api/workspace.py`
- **Vai trò trong đời sống:** Quầy tiếp dân lớn nhất. Hầu hết các tab trên trang (Tổng quan, Quan trắc, bản đồ, Hồ sơ cống) hỏi qua quầy này. Quầy chỉ nhận phiếu, kiểm tra sơ bộ rồi chuyển sang service; không tự tính toán.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: tham số URL và thân yêu cầu JSON từ trang web. Đầu ra: JSON; tệp CSV tải về; tệp kết quả thí nghiệm trong `runs/local_ec_backtest/`; tệp PDF `data/raw/gates/dongthap_gate_catalog_2025.pdf`. Toàn bộ gắn dưới tiền tố `/api/v1/workspace` (và trùng ở `/api/v1/research`).
- **Các hàm cốt lõi:** (viết tắt `WS` = `/api/v1/workspace`)
  - Gắn sẵn hai router con: `multivariate_router` (nên các API dự báo cũng có ở `WS/multivariate/...`) và `dss_storage_router`.
  - Đăng ký trực tiếp (đều `GET`): `WS/summary` → `summary()`, `WS/stations` → `stations()`, `WS/stations/{site_code}/observations` → `observations()`, `WS/experiments/{experiment_id}` → `experiment()`, `WS/boundaries` → `boundaries()`, `WS/gates` → `gates()`, `WS/database-gates` → `database_gates()`, tất cả trong `backend/services/workspace.py`; `WS/experiments/{experiment_id}/next-forecast` → `next_forecast()` và `WS/future-forecast`, `WS/monthly-estimates` → `monthly_estimates()` trong `backend/services/forecasts.py`.
  - `simulation_corridor()`: `GET WS/simulation/corridor`. Gọi `simulation_corridor()` trong `backend/services/spatial_simulation.py`, trả hình tuyến sông.
  - `simulation_timeline()`: `GET WS/simulation/timeline`. Gọi `simulation_timeline()` cùng tệp, trả danh sách tháng cho thanh thời gian.
  - `simulation_frame(year_month, open_below_ec, close_above_ec)`: `GET WS/simulation/frame`. Cần tháng `YYYY-MM` và cặp ngưỡng EC (mặc định 120 và 150 mS/m). Gọi `simulation_frame()` để lấy màu sông và chấm cống của tháng đó.
  - `candidate_stations(gate_code, radius_km)`: `GET WS/database-gates/{gate_code}/candidate-stations`. Bán kính 0–200 km, mặc định 50. Gọi `candidate_stations()` trong `backend/services/workspace.py`.
  - `gate_template(kind, gate_code)`: `GET WS/gate-template/{kind}`. Gọi `gate_template()` trong `backend/services/workspace.py`, trả mẫu hồ sơ cống.
  - `gate_evaluation(request)`: `POST WS/gate-evaluation`. Đọc thân yêu cầu tối đa 256 KiB, từ chối số vô cực/NaN, cần hai ô `policy` và `input` là đối tượng. Gọi `review_dossier()` trong `backend/services/gates.py`. Sai mẫu → 422.
  - `export_estimates(station)`: `GET WS/monthly-estimates/export`. Gọi `monthly_estimates()` rồi ghi thành CSV tải về tên `monthly-ec-estimates.csv`.
  - `artifact(experiment_id, filename)`: `GET WS/artifacts/{experiment_id}/{filename}`. Gọi `artifact_path()` trong `backend/services/workspace.py` (chỉ cho các tên tệp trong danh sách cho phép) và gửi tệp.
  - `gate_source()`: `GET WS/gate-source`. Gửi tệp PDF danh mục cống.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một địa chỉ mới cho bản đồ hoặc đổi ngưỡng EC mặc định của khung bản đồ.
  - Có — nếu đổi giới hạn kích thước hồ sơ cống gửi lên.
  - Không — muốn đổi cách tính màu sông/nội suy thì sang `backend/services/spatial_simulation.py`, `spatial_inputs.py` và `backend/domain/river_interpolation.py`.

### `backend/api/multivariate.py`
- **Vai trò trong đời sống:** Quầy nhận phiếu đặt dự báo EC theo tháng. Quầy kiểm tra phiếu (tên trạm, tháng đúng dạng, số mưa/nhiệt/gió trong khoảng hợp lý) rồi chuyển cho bộ phận dự báo.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: tham số URL hoặc JSON gửi lên. Đầu ra: JSON danh mục mô hình, đầu vào, điểm đánh giá, kết quả dự báo. Không ghi gì. Có ở hai địa chỉ: `/api/v1/multivariate/...` và `/api/v1/workspace/multivariate/...`.
- **Các hàm cốt lõi:**
  - `Month`: kiểu "tháng" phải dạng `YYYY-MM`, tháng 01–12.
  - `ForecastRequest`: mẫu phiếu dự báo: `station`, `target_month`, `input_mode` (`ARCHIVE` = lấy đầu vào lưu trữ, `MANUAL` = người dùng tự nhập), `rainfall_mm` (0–20000), `temperature_degC` (−90 đến 65), `wind_source_units` (0–150). Không nhận ô lạ (`extra='forbid'`). Tệp `dss_storage.py` dùng lại mẫu này.
  - `catalog()`: `GET /api/v1/multivariate/catalog`. Gọi `catalog()` trong `backend/services/multivariate.py`.
  - `inputs(station, target_month)`: `GET /api/v1/multivariate/inputs`. Gọi `inputs()`, trả đầu vào khí tượng/thủy văn tháng `t−2`.
  - `evaluation(station, protocol, experiment, ec_delay_days)`: `GET /api/v1/multivariate/evaluation`. `protocol` là `HISTORICAL` hoặc `FROZEN_EC_WEATHER_ONLY_V1`; `experiment` là `gap_2019_2021`, `gap_2021_2023`, `gap_2022_2023`; `ec_delay_days` là `5` hoặc `35`. Gọi `evaluation()`.
  - `predict(payload)`: `POST /api/v1/multivariate/predict`. Gọi `predict()` trong `backend/services/multivariate.py`; không huấn luyện lại mô hình.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn nới/siết khoảng giá trị mưa, nhiệt, gió được nhập tay.
  - Có — nếu thêm một kỳ đánh giá mới vào danh sách `experiment` cho phép.
  - Không — muốn đổi mô hình hay đặc trưng thì sang `backend/services/multivariate.py`, `backend/domain/multivariate_ec.py` và `data/models/multivariate_registry.json`.

### `backend/api/dss_storage.py`
- **Vai trò trong đời sống:** Quầy lưu trữ hồ sơ. DSS là "hệ hỗ trợ quyết định": ở đây cho lưu và xem lại các lần dự báo đã chạy và các bản nháp hồ sơ cống. Đây là phần tùy chọn, tách khỏi việc dự báo (dự báo vẫn chạy được khi không lưu).
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: JSON từ trang web; header `origin`, `content-type`; biến `WEBGIS_CORS_ORIGINS`. Đầu ra: JSON; việc ghi thật vào bảng `dss_reference.multivariate_prediction_log` và `dss_reference.gate_simulation_drafts` do service/repository làm.
- **Các hàm cốt lõi:** (`router` không có tiền tố riêng nên nằm dưới `/api/v1/workspace`; `multivariate_history_router` có tiền tố `/multivariate`, được gắn cả trong `router` lẫn trực tiếp ở `/api/v1` trong `main.py`)
  - `same_origin_write(request)`: kiểm tra phụ trước khi ghi: nguồn phải hợp lệ (403 nếu không) và nội dung phải là `application/json` (415 nếu không).
  - `DraftRequest`: mẫu bản nháp cống gồm `gate_code` (chữ, số, `_`, `-`; tối đa 64 ký tự), `input`, `policy`.
  - `presets()`: `GET /api/v1/workspace/threshold-presets`. Gọi `presets()` trong `backend/services/dss_storage.py`, trả các bộ ngưỡng EC tham khảo.
  - `history(station, target_month, limit, offset)`: `GET /api/v1/multivariate/history` (và `/api/v1/workspace/multivariate/history`). Gọi `predictions()` trong service; tối đa 100 dòng/trang.
  - `saved_prediction(prediction_id)`: `GET /api/v1/multivariate/history/{prediction_id}`. Gọi `prediction()`.
  - `save_prediction(payload)`: `POST /api/v1/multivariate/history`. Qua `same_origin_write`, nhận `ForecastRequest`, gọi `save_prediction()` trong service.
  - `drafts(gate_code, limit, offset)`: `GET /api/v1/workspace/gate-drafts`. Gọi `drafts()`.
  - `save_draft(request)`: `POST /api/v1/workspace/gate-drafts`. Giới hạn 256 KiB, từ chối số vô cực, kiểm mẫu `DraftRequest`, rồi gọi `save_draft()` trong service ở luồng phụ (để không chặn máy chủ).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm ô lọc mới cho lịch sử dự báo đã lưu.
  - Không — muốn đổi bảng hoặc câu SQL lưu thì sang `backend/repositories/dss_storage.py`; muốn đổi quy tắc kiểm bản nháp thì sang `backend/services/dss_storage.py`.

### `backend/api/data_freshness.py`
- **Vai trò trong đời sống:** Bảng "hạn dùng" của các nguồn số liệu. Giống tờ giấy dán ở tủ lạnh ghi món nào mua tháng nào, còn dùng được tới đâu. Tab Tổng quan dùng để báo nguồn nào còn mới, nguồn nào đã cũ.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: dữ liệu khí tượng qua `get_monthly_weather()` (`backend/repositories/multivariate_inputs.py`); bảng thủy văn tháng qua `_matrix()` và `_signature()` (`backend/repositories/hydrology_inputs.py`); ngày hôm nay theo giờ Việt Nam. Đầu ra: JSON `as_of` và `sources`. Không ghi gì.
- **Các hàm cốt lõi:**
  - `_weather(station, today)`: lấy tháng ERA5 đầy đủ mới nhất của một trạm và gọi `assess()` trong `backend/domain/data_freshness.py`; không có thì `UNAVAILABLE`.
  - `_hydrology(today)`: tìm tháng gần nhất có số hợp lệ cho `KRATIE_Q` (cột `kratie_q_t2`) và `TANCHAU_STAGE` (cột `tc_stage_t2`), rồi gọi `assess()`.
  - `report(today)`: gom kết quả cho `ERA5_MYTHO`, `ERA5_TANCHAU`, `ERA5_MYTHUAN`, hai nguồn thủy văn và `MRC_EC_MYTHO`. Riêng `MRC_EC_MYTHO` được ghi cứng là `STALE`, tháng cuối `2023-12`, mẫu cuối `2023-12-15`.
  - `data_freshness()`: `GET /api/v1/data-freshness`. Gọi `report()`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu có EC Mỹ Tho mới sau 2023 (dòng `MRC_EC_MYTHO` đang ghi cứng, cần cập nhật).
  - Có — nếu muốn thêm một nguồn mới vào bảng hạn dùng.
  - Không — muốn đổi quy tắc tính "còn mấy ngày thì cũ" thì sang `backend/domain/data_freshness.py`.

### `backend/api/gate_screening.py`
- **Vai trò trong đời sống:** Máy chấm phiếu kiểm tra điều kiện lấy nước tại cống. Người dùng đưa số đo, máy trả kết quả rà soát; máy không lưu gì và không ra lệnh đóng/mở cống.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: JSON gửi lên gồm `measurement`, `profile` (tùy chọn), `forecast_context` (tùy chọn), `now_iso`. Đầu ra: JSON kết quả rà soát. Không đọc/ghi DB hay tệp.
- **Các hàm cốt lõi:**
  - `ScreeningRequest`: mẫu phiếu, không nhận ô lạ; `now_iso` tối đa 40 ký tự.
  - `gate_screening(request)`: `POST /api/v1/gate-screening/evaluate`. Giới hạn 64 KiB (413 nếu vượt), sai mẫu → 422. Gọi `evaluate()` trong `backend/domain/gate_intake_rules.py` (gọi thẳng domain, không qua service).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn thêm ô mới vào phiếu kiểm tra gửi lên.
  - Không — muốn đổi quy tắc chấm điều kiện lấy nước thì sang `backend/domain/gate_intake_rules.py` (và bản phía trình duyệt `frontend/src/shared/gate-intake-rules.js`).

### `backend/api/forecast_issues.py`
- **Vai trò trong đời sống:** Sổ phát hành dự báo, giống sổ công văn đi: mỗi lần "phát hành" dự báo cho một tháng thì ghi một dòng, không tẩy xóa; sau này có số đo thật thì chấm điểm đúng/sai, tách riêng bản phát hành đúng hạn và trễ hạn.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: JSON hoặc tham số URL. Đầu ra: JSON. Việc ghi/đọc bảng `dss_reference.forecast_slot`, `forecast_slot_event`, `forecast_issue`, `forecast_score` do service và `backend/repositories/forecast_issues.py` làm.
- **Các hàm cốt lõi:**
  - `IssueRequest`: mẫu phiếu gồm `target_month` (`YYYY-MM`) và `schedule_code` (chỉ nhận `MONTHLY_D06_PREV`).
  - `issue(payload)`: `POST /api/v1/forecast-issues` (trả mã 201). Gọi `issue_month()` trong `backend/services/forecast_issues.py`. Địa chỉ này nằm trong `WRITE_PATHS` của `backend/security.py`.
  - `history(station, date_from, date_to, with_scores)`: `GET /api/v1/forecast-issues?station=&from=&to=&with_scores=`. Gọi `list_issues()` trong cùng service.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một lịch phát hành mới (mở rộng `schedule_code`).
  - Không — muốn đổi cách tính điểm hay thời hạn phát hành thì sang `backend/services/forecast_issues.py` và `backend/domain/forecast_issue.py`.

### `backend/api/field_measurements.py`
- **Vai trò trong đời sống:** Hộp thư nhận phiếu EC đo ngoài thực địa của cán bộ. Người gửi phải có "chìa khóa gửi"; người duyệt phải có "chìa khóa duyệt" khác. Ai cũng xem được phiếu đã duyệt, còn phiếu chờ duyệt hoặc bị từ chối chỉ người duyệt xem được.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: JSON gửi lên; header `x-api-key`; biến `WEBGIS_WRITE_API_KEY`, `WEBGIS_REVIEW_API_KEY`. Đầu ra: JSON. Ghi/đọc thật vào `dss_reference.field_measurement`, `field_measurement_review` qua service và `backend/repositories/field_measurements.py`.
- **Các hàm cốt lõi:** (tiền tố `/api/v1/field-measurements`)
  - `_key(request, name)`, `require_submit_key`, `require_review_key`: so API key người gửi với biến môi trường; chưa cấu hình → 503, sai → 401.
  - `FieldRequest`: mẫu phiếu đo: `ec`, `unit` (`µS/cm`, `dS/m`, `mS/cm`, `mS/m`), `observed_at`, `longitude`, `latitude`, `position_kind` (`RIVER`/`FIELD`), `device`, `submitted_by`, `ec_basis` (`EC25`/`RAW`/`UNKNOWN`), `calibrated_at`, `calibration_reference`, `water_temp_degC`.
  - `ReviewRequest`: mẫu phiếu duyệt: `decision` (`APPROVED`/`REJECTED`), `reviewer`, `note`.
  - `submit(request)`: `POST /api/v1/field-measurements` (201). Cần đúng nguồn và chìa khóa gửi; giới hạn 16 KiB. Gọi `submit()` trong `backend/services/field_measurements.py`.
  - `measurements(request, status, bbox)`: `GET /api/v1/field-measurements?status=&bbox=`. Nếu không phải `APPROVED` thì cần chìa khóa duyệt. Gọi `list_measurements()`.
  - `review(measurement_id, payload)`: `POST /api/v1/field-measurements/{measurement_id}/review`. Cần chìa khóa duyệt; đánh dấu người thao tác là `REVIEW_KEY_CLIENT` rồi gọi `review()` trong service.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một đơn vị EC được chấp nhận hoặc thêm ô vào phiếu đo.
  - Không — muốn đổi cách quy đổi đơn vị hay cờ cảnh báo thì sang `backend/services/field_measurements.py`; đổi câu SQL thì sang `backend/repositories/field_measurements.py`.

---

### `backend/repositories/__init__.py`
- **Vai trò trong đời sống:** Tấm biển đánh dấu `backend/repositories` là gói Python. Tệp rỗng.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Không.
- **Các hàm cốt lõi:** Không có.
- **Muốn sửa … thì có tìm đến file này không?:** Không.

### `backend/repositories/workspace.py`
- **Vai trò trong đời sống:** Thủ kho của "bộ hồ sơ nghiên cứu". Tùy công tắc `WEBGIS_RESEARCH_MODE`, thủ kho lấy hồ sơ từ tệp ảnh chụp đã niêm phong (`snapshot`) hoặc từ PostgreSQL (`postgres`). Nếu nguồn đã chọn hỏng, thủ kho báo lỗi chứ không lén đưa nguồn kia thay thế.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `data/research/workspace.json` và `data/research/workspace_manifest.json` (hoặc đường dẫn trong `WEBGIS_RESEARCH_FILE`); biến `WEBGIS_WORKSPACE_DATASETS` (chọn bộ dữ liệu cho từng trạm); bảng `public.measurement_site`, `public.data_source`, `public.source_dataset`, `public.conductivity_observation`, `public.irrigation_gate`; tệp `data/models/future_ec_forecast_2024_2026.csv`. Đầu ra: từ điển Python cho `backend/services/workspace.py`, `forecasts.py`, `spatial_inputs.py`. Không ghi gì.
- **Các hàm cốt lõi:**
  - `WorkspaceUnavailable`: lỗi "nguồn hồ sơ không dùng được".
  - `_file_bundle(path, stamp, manifest_stamp)`: đọc `workspace.json` (tối đa 8 MB), so `sha256` với manifest, rồi gọi `validate_bundle()` trong `backend/domain/workspace.py`. Kết quả được **cache** (nhớ tạm) theo thời điểm sửa tệp nên không đọc lại khi tệp không đổi.
  - `load_bundle()`: hàm chính. Luôn đọc snapshot trước; nếu chế độ `postgres` thì gọi `_postgres_bundle()`. Gắn nhãn `storage_mode`, `observation_source`, `dataset_selection`. Mọi lỗi → `WorkspaceUnavailable` với câu "No fallback was used".
  - `bundle_stamp()`: tạo "dấu phiên bản" rẻ (thời điểm sửa tệp, số dòng EC, mã bộ dữ liệu) để service mô phỏng biết khi nào cần tính lại.
  - `_snapshot_reference_points(bundle, database_site_codes, database_source_codes)`: lấy riêng các điểm RIA2 (mã bắt đầu `RIA2_`) từ snapshot, gắn `reference_only=True`, để vẫn hiện trên bản đồ mà không giả làm số đo từ DB.
  - `_postgres_bundle(bundle)`: với mỗi trạm trong DB, chọn một bộ dữ liệu `RAW_EC` (theo `WEBGIS_WORKSPACE_DATASETS`, nếu không thì bộ nhập mới nhất), đọc toàn bộ dòng EC, xử lý trường hợp nguồn chỉ có ngày (`DATE_ONLY`), tính khoảng cách giữa các lần đo, ghi chú `gate_decision_eligible=False`; rồi nối thêm điểm RIA2 tham khảo.
  - `read_json(relative_path)`: đọc một tệp JSON trong dự án (dùng cho ranh giới hành chính).
  - `estimate_rows()`: đọc `data/models/future_ec_forecast_2024_2026.csv` (bản lưu nghiên cứu cũ, không phải dự báo Mỹ Tho hiện hành).
  - `database_gates()`: đọc danh mục cống từ `public.irrigation_gate`; kèm ghi chú `is_active` là trạng thái danh mục, không phải đang mở/đóng.
  - `candidate_stations(gate_code, radius_km)`: tìm tối đa 5 trạm trong bán kính quanh cống bằng `ST_DWithin`/`ST_Distance` (hàm đo khoảng cách của PostGIS, đơn vị mét); ghi rõ `hydrological_link_validated=False` (gần không có nghĩa là thông nước).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn đổi cách chọn bộ dữ liệu EC cho từng trạm ở chế độ PostgreSQL.
  - Có — nếu đổi vị trí tệp snapshot hay cách xử lý điểm RIA2.
  - Không — muốn đổi nội dung JSON trả về tab Tổng quan/Quan trắc thì sang `backend/services/workspace.py`.

### `backend/repositories/multivariate_inputs.py`
- **Vai trò trong đời sống:** Người ghi sổ thời tiết. Từ số liệu mưa, nhiệt, gió theo ngày, người này cộng/tính trung bình thành số liệu tháng, và chỉ nhận tháng đủ ngày, không trùng, không thiếu. Mô hình dự báo dùng tháng `t−2` (hai tháng trước tháng cần dự báo).
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `data/raw/meteorology/openmeteo/openmeteo_all_stations_daily.csv` (nguồn cũ, đơn vị gió chưa xác nhận); thư mục `data/external/multivariate_weather/` và `data/external/mythuan_weather_20261104/`, mỗi thư mục có `manifest.json` và các tệp `era5_*.json`. Đầu ra: từ điển số liệu tháng cho `backend/services/multivariate.py`, `spatial_inputs.py`, `backend/api/data_freshness.py`. Không ghi gì.
- **Các hàm cốt lõi:**
  - `ALIASES`, `normalize_station(station)`: quy đổi các cách gọi tên trạm (`MYTHO`, `MRC_VN_019805`, `019805`...) về `MyTho`, `TanChau`, `MyThuan`; tên lạ → lỗi.
  - `WeatherInputUnavailable`: lỗi "thiếu, sai hoặc không đủ ngày".
  - `_month(value)`: kiểm chuỗi tháng `YYYY-MM`.
  - `_aggregate(station, month, rows, provenance)`: kiểm đủ từng ngày của tháng, không âm, không vô cực; tính tổng mưa, trung bình nhiệt, trung bình gió; ghi giả định "cuối tháng + 5 ngày mới có số liệu".
  - `_signature()` và `_load(signature)`: `_signature` lấy dấu (đường dẫn, thời điểm sửa, kích thước) các tệp nguồn; `_load` đọc tất cả (có cache theo dấu đó), kiểm `sha256` từng tệp ERA5 với manifest, kiểm đơn vị (`m/s`, `mm`, `°C`), mô hình `era5`, múi giờ; bản tải về sau cùng thay trọn tháng, không ghép ngày lẻ.
  - `get_monthly_weather(station, require_verified_wind=True)`: mọi tháng đủ của một trạm theo thứ tự thời gian; mặc định chỉ lấy tháng có gió đã xác minh đơn vị.
  - `get_weather_input(station, target_month)`: lấy số liệu tháng `t−2` cho tháng cần dự báo; thiếu → `WeatherInputUnavailable` kèm lý do.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu thêm một trạm khí tượng mới hoặc một thư mục ERA5 mới.
  - Có — nếu đổi giả định "cuối tháng + 5 ngày".
  - Không — muốn đổi mô hình dùng đặc trưng nào thì sang `backend/domain/multivariate_ec.py` và manifest mô hình.

### `backend/repositories/hydrology_inputs.py`
- **Vai trò trong đời sống:** Người ghi sổ nước sông. Từ số liệu ngày của lưu lượng Kratie (Campuchia) và mực nước Tân Châu, người này tính ra 5 con số tháng mà mô hình Mỹ Tho cần. Tháng có ít hơn 20 ngày số liệu thì bỏ trống, không đoán.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: đúng một tệp khớp mẫu trong mỗi thư mục: `data/external/mrc_kratie_discharge_20261029/014901_Discharge_Calculated daily discharge_????????.csv`, `data/external/tien_manual_long_20261029/019803_Water_Level_Manual_????????.csv`, `data/external/tien_manual_2024_2026_20261029/019803_Water_Level_Manual_????????.csv`. Đầu ra: từ điển đặc trưng thủy văn cho `backend/services/multivariate.py`, `spatial_inputs.py`, `backend/domain/multivariate_ec.py`, `backend/api/data_freshness.py`. Không ghi gì.
- **Các hàm cốt lõi:**
  - `FEATURES`, `UNITS`, `LABELS`: tên, đơn vị và nhãn tiếng Việt của 5 đặc trưng: `kratie_q_t2` (m³/s), `kratie_q3_t2` (m³/s), `kratie_q_ratio_t2` (không đơn vị), `tc_stage_t2` (m), `tc_stage3_t2` (m).
  - `source_paths()`: tìm ba tệp nguồn; không đúng một tệp/thư mục → lỗi.
  - `_signature()`, `_source_hashes(signature)`: dấu phiên bản tệp và `sha256` từng tệp (có cache, chỉ băm một lần cho mỗi phiên bản).
  - `_monthly_stage(paths)`: gộp hai tệp mực nước, kiểm không trùng giờ và đơn vị là `m`, lấy trung vị theo ngày rồi trung vị theo tháng (cần ≥ 20 ngày).
  - `_monthly_flow(path)`: kiểm lưu lượng không trùng, đơn vị `m^3/s`, không âm; trung bình theo ngày rồi theo tháng (cần ≥ 20 ngày).
  - `_matrix(signature)`: dựng bảng từ 01/1985: lưu lượng tháng, trung bình 3 tháng, tỷ lệ so với trung vị cùng tháng của tối đa 15 năm trước (cắt trong 0–5), mực nước tháng và trung vị 3 tháng. Có cache.
  - `get_hydrology_input(target_month, now=None)`: lấy dòng tháng `t−2`; nếu chưa qua "cuối tháng + 5 ngày" hoặc thiếu số → báo lỗi, không thay bằng 0. Trả kèm tên nguồn, hash tệp và ghi chú giả định.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu tải tệp Kratie/Tân Châu mới vào thư mục khác (phải sửa đường dẫn/mẫu tên).
  - Có — nếu muốn đổi ngưỡng 20 ngày hoặc cách tính tỷ lệ lưu lượng.
  - Không — đổi các đặc trưng này sẽ không khớp mô hình đã lưu; muốn đổi mô hình thì phải huấn luyện bản mới bằng `scripts/train_mytho_hydrology_primary.py` và cập nhật registry.

### `backend/repositories/dss_storage.py`
- **Vai trò trong đời sống:** Thủ kho được phép ghi, nhưng chỉ vào ngăn "lưu trữ DSS". Thủ kho này dùng tài khoản DB riêng (khác tài khoản chỉ đọc) và phải có công tắc cho phép ghi mới hoạt động. Mỗi lần ghi đều đóng dấu "ai thao tác".
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: biến `WEBGIS_DSS_WRITES_ENABLED`, `DSS_PGUSER`, `DSS_PGPASSWORD`, `WEBGIS_DSS_POOL_MAX`, `PGHOST`, `PGPORT`, `PGDATABASE`, `WEBGIS_DB_USER`; bảng `dss_reference.ec_threshold_presets`. Đầu ra (ghi): `dss_reference.multivariate_prediction_log`, `dss_reference.gate_simulation_drafts`; đặt `webgis.actor` cho mỗi giao dịch ghi.
- **Các hàm cốt lõi:**
  - `StorageDisabled`: lỗi "chức năng lưu đang tắt".
  - `require_writes()`: báo `StorageDisabled` nếu `WEBGIS_DSS_WRITES_ENABLED` không phải `true`.
  - `_write_config()`, `_configure_writer(conn)`: thông số và kiểm vai trò (gọi `assert_application_role()`) cho pool ghi.
  - `open_write_pool()` / `close_write_pool()`: mở/đóng pool ghi (mặc định tối đa 2 đường). Bắt buộc `DSS_PGUSER` khác `WEBGIS_DB_USER`.
  - `write_connection()`: mượn đường dây ghi và ghi tên người thao tác lấy từ `actor` (`backend/security.py`). Các repository `field_measurements.py`, `forecast_issues.py` cũng dùng hàm này.
  - `threshold_presets()`: đọc các bộ ngưỡng EC tham khảo (qua đường chỉ đọc).
  - `save_prediction(prediction)`: thêm một dòng vào `multivariate_prediction_log`, lưu toàn bộ kết quả dạng JSON.
  - `predictions(station, target_month, limit, offset)`, `prediction(prediction_id)`: đọc danh sách/một bản dự báo đã lưu, mới nhất trước.
  - `save_draft(gate_code, data, policy)`, `drafts(gate_code, limit, offset)`: ghi/đọc bản nháp hồ sơ cống trong `gate_simulation_drafts`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu đổi tên bảng lưu hoặc thêm cột lưu cho bản dự báo.
  - Có — nếu đổi số kết nối tối đa của pool ghi.
  - Không — muốn tạo bảng mới trong DB thì viết SQL ở `sql/` và áp bằng `scripts/apply_dss_storage.py` (lệnh `--apply` ghi thật, chỉ chạy khi chắc chắn).

### `backend/repositories/field_measurements.py`
- **Vai trò trong đời sống:** Sổ lưu phiếu đo thực địa và sổ duyệt. Phiếu đã ghi thì không sửa; mỗi lần duyệt là một dòng mới. Tệp này còn có bộ lọc "phiếu nào đủ chuẩn để làm nhãn EC tháng" theo tiêu chí đã đăng ký trước ngày 14/11.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `dss_reference.field_measurement`, `dss_reference.v_field_measurement_status` (một **view**, tức bảng ảo ghép từ bảng khác), `public.measurement_site`, `public.conductivity_observation`, `public.source_dataset`. Đầu ra (ghi): `dss_reference.field_measurement`, `dss_reference.field_measurement_review`.
- **Các hàm cốt lõi:**
  - `insert_measurement(value, raw)`: ghi một phiếu đo, tạo điểm bản đồ từ kinh/vĩ độ (hệ 4326), lưu cả bản gốc người gửi.
  - `list_measurements(status, bbox, limit=200)`: đọc phiếu theo trạng thái và khung bản đồ `bbox`.
  - `insert_review(measurement_id, decision, reviewer, note)`: thêm một dòng duyệt; không có phiếu → trả `None`.
  - `LABEL_SITES`: `MYTHO` → `MRC_VN_019805`, `MYTHUAN` → `MRC_VN_019804`, `TANCHAU` → `MRC_VN_019803`.
  - `historical_month_median(longitude, latitude, observed_at)`: trung vị EC lịch sử cùng tháng ở trạm MRC gần nhất, dùng làm mốc so khi gắn cờ phiếu.
  - `field_label_from_rows(rows, target_month)`: lọc phiếu theo tiêu chí: ngày 13–17, giờ 9:00–16:00, hiệu chuẩn trong 30 ngày có ghi tham chiếu, `EC25`, vị trí `RIVER`; cần ≥ 2 phiếu cách nhau ≥ 30 phút và chênh lệch ≤ 20% trung vị. Đạt thì trả nhãn `FIELD_APPROVED` với mã tham chiếu băm.
  - `candidate_field_label(station, target_month)`: lấy phiếu đã duyệt trong 2 km quanh trạm trong tháng, rồi gọi `field_label_from_rows()`. Được `scripts/score_forecast_issues.py` dùng.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu đổi bán kính 2 km hoặc khung giờ/ngày đủ chuẩn làm nhãn (lưu ý đây là tiêu chí đã khóa trước, đổi phải ghi phiên bản giao thức mới).
  - Không — muốn đổi cách quy đổi đơn vị EC phiếu gửi thì sang `backend/services/field_measurements.py`.

### `backend/repositories/forecast_issues.py`
- **Vai trò trong đời sống:** Sổ cái của sổ phát hành dự báo: chỉ thêm, không xóa. Ghi "suất phát hành" (slot), sự kiện bỏ lỡ, bản phát hành và điểm chấm.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `dss_reference.forecast_slot`, `forecast_slot_event`, `forecast_issue`, `forecast_score`; bảng EC `public.conductivity_observation`, `public.source_dataset`, `public.data_source`, `public.measurement_site`. Đầu ra (ghi): bốn bảng `dss_reference.forecast_*` kể trên.
- **Các hàm cốt lõi:**
  - `insert_slot(conn, station, target_month, schedule_code, scheduled_at)`: tạo suất phát hành; đã có thì lấy cái cũ (không tạo trùng).
  - `insert_missed(conn, slot_id, reason_code)`: ghi sự kiện `MISSED` kèm lý do.
  - `existing_issue(conn, slot_id)`: xem suất đó đã có bản phát hành chưa.
  - `insert_issue(conn, slot_id, issue)`: ghi bản phát hành (phiên bản mô hình, `model_sha256`, số dự báo, toàn bộ dữ liệu); câu SQL tạm ghi `'LATE'`, nhưng trigger `forecast_issue_guard` trong `sql/33_forecast_issue.sql` (cập nhật ở `33b_forecast_issue_guard.sql`) tự sửa lại trước khi lưu: phát hành trước giờ hẹn thì bị từ chối; sau giờ hẹn dưới 1 giờ và slot chưa bị đánh dấu `MISSED` thì thành `ON_TIME`, còn lại `LATE`. Trigger giống người trực sổ: ai nộp bài thì ông ấy tự ghi giờ nộp và đóng dấu đúng hạn/trễ hạn, người nộp không tự khai được.
  - `list_slots(station, date_from, date_to, limit=200)`: ghép suất, sự kiện, bản phát hành và điểm (chỉ điểm theo giao thức `MONTHLY_EC_LABEL_V1_20261114`).
  - `insert_score(issue_id, score)`: ghi điểm chấm (số đo, sai số tuyệt đối). Được `scripts/score_forecast_issues.py` dùng.
  - `SITE_CODES`, `candidate_mrc_label(station, target_month)`: chọn đúng một mẫu MRC trong tháng làm nhãn, ưu tiên theo bộ nhập sớm nhất rồi ngày gần ngày 15 nhất; cố ý không chọn theo sai số.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu đổi quy tắc chọn mẫu MRC làm nhãn tháng.
  - Không — muốn đổi thời điểm phát hành theo lịch thì sang `backend/services/forecast_issues.py` và `backend/domain/forecast_issue.py`.

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

## 2.C. Frontend: trang web, khung ứng dụng, bản đồ và quan trắc

Phần "frontend" là những gì chạy trong trình duyệt của người dùng. Có thể hình dung như một căn nhà:

- **HTML** (tệp `.html`) là *khung nhà*: nó khai báo có những phòng nào, cửa nào, nút nào, ô nhập nào. Mỗi phần tử có thể mang một **id** (tên riêng, ví dụ `id="researchMap"`) để mã JavaScript tìm đúng chỗ.
- **CSS** (tệp `.css`) là *sơn và nội thất*: màu, cỡ chữ, khoảng cách, vị trí. CSS không làm thay đổi dữ liệu.
- **JavaScript** (tệp `.js`) là *điện nước và người quản gia*: nó lấy dữ liệu từ máy chủ, đổ vào bảng, vẽ bản đồ, phản ứng khi người dùng bấm nút.

Một số từ dùng nhiều trong phần này:

- **DOM**: bản "cây" các phần tử của trang mà trình duyệt giữ trong bộ nhớ. "Sửa DOM" là thay chữ, thêm dòng bảng, ẩn/hiện một khung.
- **Sự kiện (event)**: một "tiếng chuông" báo có việc xảy ra (người dùng bấm nút, đổi tab, dữ liệu vừa về). Mã có thể *phát* sự kiện (`window.dispatchEvent(new CustomEvent('workspace:...'))`) và mã khác *nghe* (`addEventListener`). Dự án dùng tên sự kiện bắt đầu bằng `workspace:` để các tính năng nói chuyện với nhau mà không cần gọi hàm trực tiếp.
- **fetch / request**: trình duyệt gửi "thư hỏi" tới máy chủ FastAPI, ví dụ `GET /api/v1/workspace/stations`, và nhận về dữ liệu dạng JSON.
- **module, import/export**: mỗi tệp `.js` là một "hộp dụng cụ". `export` là đặt dụng cụ ra ngoài cho người khác mượn, `import` là mượn dụng cụ từ hộp khác.
- **OpenLayers (`ol`)**: thư viện vẽ bản đồ. Bản đồ gồm nhiều **lớp (layer)** chồng lên nhau như các tấm phim trong suốt: lớp nền (tile, ảnh bản đồ OpenStreetMap/Esri), lớp sông, lớp kênh, lớp chấm cống, lớp trạm...
- **canvas**: một tấm "bảng vẽ" bằng điểm ảnh, dùng để vẽ hoạt ảnh nhanh (vệt nước chảy, hạt gió).
- **SVG**: hình vẽ bằng đường và điểm (vector), dùng cho biểu đồ và sơ đồ sông.

**"Build bằng Vite ra `frontend/dist`"** nghĩa là: mã nguồn trong `frontend/src/` được viết thành nhiều tệp nhỏ cho dễ sửa. Trước khi phục vụ, công cụ **Vite** gom, nén và đóng gói chúng thành vài tệp gọn trong thư mục `frontend/dist/` (giống như gói hàng vào thùng trước khi giao). Máy chủ FastAPI (`run_webgis.py`, dòng `app.mount('/', StaticFiles(directory=frontend, html=True))`) phát chính thư mục `dist/` này. Vì vậy **sửa `frontend/src/` xong phải chạy `npm.cmd --prefix frontend run build`** (hoặc `.\start.ps1`) thì cổng 8000 mới thấy thay đổi.

**Chuỗi khởi động trang chính:** `workspace.html` nạp đúng một tệp JS là `/src/app/workspace.js`. Tệp này `import` các tính năng (quan trắc, dự báo, cống...) và các tệp CSS. Hai trang `index.html` và `research.html` chỉ là trang chuyển hướng về `workspace.html`.

**Cảnh báo về mã cũ (legacy):** `frontend/src/main.js`, `frontend/src/map.js` và `frontend/src/style.css` **không được trang nào nạp**. `main.js` tìm các id như `map`, `basemapToggle`, `datasetSelect`, `filterForm` vốn không còn trong HTML hiện tại. Đây là giao diện tra cứu PostgreSQL đời đầu. `chart.js` và `api.js` thì vẫn được dùng.

---

### `frontend/workspace.html`
- **Vai trò trong đời sống:** Đây là "bản vẽ mặt bằng" của cả ứng dụng: một trang duy nhất chia làm năm phòng (tab). Người dùng mở `http://127.0.0.1:8000/workspace.html` là vào đây.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: không tự gọi API. Nó chỉ khai báo khung và nạp `<script type="module" src="/src/app/workspace.js">`. Có một khối `<style>` nhỏ trong `<head>` để giữ viền tiêu điểm bàn phím khi CSS chính chưa tải xong. Ảnh `/river-diagram.svg` được chèn ở phần giới thiệu. Đầu ra: các phần tử rỗng (bảng, khung biểu đồ, host) để JS đổ dữ liệu vào.
- **Năm tab và cơ chế:** Thanh `<nav>` có 5 liên kết `#overview`, `#observations`, `#forecasts`, `#data-quality`, `#gates`. Mỗi khối `<section>` mang thuộc tính `data-view="..."`. `navigation.js` ẩn mọi khối có `data-view` khác tab đang chọn. Một tab có thể gồm nhiều `<section>` cùng `data-view`.

| Tab (hash) | Phần tử/id chính | JS điều khiển |
| --- | --- | --- |
| Tổng quan (`#overview`) | `modeBadge` (trên thanh đầu), `checkDatabase`, `dbStatus`, `loadError`, `retryWorkspace`, thẻ thống kê `statRia`, `statSites`, `observationCoverage`, `statLatest`, `statExperiments`; bảng `overviewEcStatus`, `overviewEcTable`; danh sách nguồn `sourceList`; khối `.workflow-cards` | `app/workspace.js`, `features/overview.js` (thêm động `quickSpatialScenarios`, `dataFreshnessPanel`) |
| Quan trắc (`#observations`) | Khung `mapLayout`; danh sách trạm `stationPanel`, `stationSearch`, `stationList`, `toggleStationList`; bản đồ `researchMap`; điều khiển `simulationThresholdPreset`, `simulationThresholdToggle`, `simulationThresholdPopover`, `simulationThresholdForm`, `simulationOpenBelow`, `simulationCloseAbove`, radio `name="simulationUnit"` (EC / độ mặn), `simulationRiverToggle`, `simulationWindToggle`, `simulationMotionToggle`, `simulationWaterwayPicker`, `fitMap`, `mapBaseTheme`; banner dự báo `mapForecastBanner`, `mapForecastValue`, `mapForecastContext`, `mapForecastDisclaimer`, `mapForecastDismiss`; chú giải `mapWarningToggle`, `mapWarningContent`, `simulationLegendTicks`, `simulationLegendGateThresholds`, `simulationConversionNote`, `mapLegendToggle`, `mapLegendPopover`, `showUnconfirmed`, `showBase`, `showBoundaries`, `coordinateNotice`, `mapComparisonLegend`, `mapForecastStatus`, `tileError`; phiếu cống `simulationGateCard`; dòng thời gian `simulationTimeline`; chi tiết trạm `stationDetails`, `ecComparisonForm`, `siteTitle`, `siteEC`, `dateFilter`, `dateFrom`, `dateTo`, `allDates`, `downloadRows`, `observationChart`, `observationRows`, `openStationForecast`; lịch sử PostgreSQL `databaseHistoryHost` | `features/observations.js`, `observations-map.js`, `timeline-scrubber.js`, `river-profile.js`, `database-history.js` (và các tệp hỗ trợ bản đồ) |
| Dự báo EC đa biến (`#forecasts`) | Khối `multivariate-forecast` với host `multivariateForecastHost`; khối `forecast` (phụ lục nghiên cứu cũ) với `experimentSelect`, `forecastChart`, `nextForecastRows`, `nextForecastApplyMap`, `predictionRows`, `metricsRows`, `artifactLinks` | `features/multivariate-forecast.js`, `forecasts.js`, `next-forecast.js`, `prediction-history.js` (phần của tác tử khác) |
| Chất lượng dữ liệu (`#data-quality`) | `retryIntake`, `fieldMeasurementsHost`, `intakeHost`; khối `future-forecast` với `futureStationSelect`, `futureEcChart`, `futureTableRows`, `downloadFutureCsv` | `src/intake.js`, `features/field-measurements.js`, `features/weather-estimates.js` |
| Hồ sơ cống (`#gates`) | `gateSelect`, `gateInfo`, `loadDatabaseGates`, `databaseGateStatus`, `databaseGateList`, `gateContextStatus`, `gateIntakeScreeningHost` | `features/gate-dossiers.js` và các tệp `gate-*` |

- **Các hàm cốt lõi:** Không có hàm; đây là tệp khai báo.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — đổi chữ tiêu đề tab, thêm một nút cố định, đổi nhãn ô nhập ngưỡng `simulationOpenBelow`/`simulationCloseAbove`.
  - Có — thêm một khối mới cho một tab: tạo `<section data-view="ten-tab">`.
  - Không — muốn nút làm việc gì khi bấm, sang tệp JS tương ứng trong bảng trên.

### `frontend/index.html`
- **Vai trò trong đời sống:** Như tấm biển "Văn phòng đã chuyển sang phòng bên cạnh". Ai mở `/index.html` sẽ được đẩy sang `workspace.html`.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: nạp `/src/app/legacy.js`. Đầu ra: một dòng chữ và liên kết "Vào trang Tổng quan" tới `/workspace.html#overview` (phòng khi JS chưa chạy).
- **Các hàm cốt lõi:** Không có.
- **Ghi chú:** Có lỗi gõ nhỏ vô hại `<link rel="icon" href="data,">` (thiếu dấu `:`). Tệp vẫn là một đầu vào build trong `vite.config.js` (tên `main`). Tệp **không** nạp `src/main.js`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — muốn đổi trang đích khi người dùng gõ địa chỉ cũ.
  - Không — muốn đổi giao diện chính, sang `workspace.html`.

### `frontend/research.html`
- **Vai trò trong đời sống:** Một biển chỉ đường khác cho đường dẫn cũ `/research.html`; cũng chuyển về `workspace.html`.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Nạp `/src/app/legacy.js`; hiển thị liên kết tới `/workspace.html`.
- **Các hàm cốt lõi:** Không có.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nếu muốn bỏ hẳn đường dẫn cũ (khi đó nhớ xóa cả đầu vào `research` trong `vite.config.js`).
  - Không — mọi nội dung nghiên cứu hiện nằm trong `workspace.html`.

### `frontend/package.json`
- **Vai trò trong đời sống:** "Danh sách đồ cần mua" của frontend: cần thư viện nào, và các lệnh tắt để chạy.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Được `npm` đọc. Khai báo `"type": "module"` (cho phép dùng `import`), thư viện chạy `ol` (OpenLayers, `^6.15.1`) và công cụ phát triển `vite` (`^5.4.21`). Ba lệnh: `dev` (`vite`, máy chủ thử ở cổng 5173), `build` (`vite build`, tạo `dist/`), `preview` (`vite preview`, cổng 4173).
- **Các hàm cốt lõi:** Không có.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — nâng phiên bản OpenLayers/Vite, thêm thư viện mới.
  - Có — đổi lệnh build.
  - Không — đổi cổng/proxy, sang `vite.config.js`.

### `frontend/package-lock.json`
- **Vai trò trong đời sống:** Hóa đơn ghi chính xác từng phiên bản thư viện đã cài, để máy khác cài ra y hệt. Do `npm` tự sinh, không sửa tay.
- **Đọc/ghi dữ liệu ở đâu (I/O):** `npm install` đọc và ghi tự động.
- **Các hàm cốt lõi:** Không có.
- **Muốn sửa … thì có tìm đến file này không?:** Không — sửa `package.json` rồi chạy `npm install`, tệp này tự cập nhật.

### `frontend/vite.config.js`
- **Vai trò trong đời sống:** Bảng hướng dẫn cho "người đóng gói" Vite: gói những trang nào, và khi chạy thử thì chuyển thư hỏi `/api` về đâu.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào build có ba trang: `workspace` (`workspace.html`), `main` (`index.html`), `research` (`research.html`). Máy chủ thử chạy `127.0.0.1:5173`, bản xem trước `127.0.0.1:4173`. Cả hai **proxy** (chuyển tiếp) mọi request `/api` sang `http://127.0.0.1:8000` (máy chủ FastAPI). Ghi chú trong mã: proxy chỉ dùng khi phát triển cục bộ.
- **Các hàm cốt lõi:** `defineConfig({...})`: hàm của Vite nhận cấu hình, không có logic riêng.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — thêm một trang HTML mới cần được build.
  - Có — FastAPI chạy cổng khác (ví dụ 8016) khi dùng `npm run dev`.
  - Không — đổi cổng của `start.ps1`, sang `start.ps1`/`run_webgis.py`.

### `frontend/scripts/generate-river-diagram.mjs`
- **Vai trò trong đời sống:** Một "máy in sơ đồ": đọc hình học sông Tiền và kênh từ dữ liệu dự án rồi in ra một bức vẽ SVG tĩnh để đặt ở trang Tổng quan.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đọc `data/biengioi/tien_river_corridor.geojson`. Ghi `frontend/public/river-diagram.svg` (ghi đè). Chạy tay bằng Node; không chạy khi build hay khi mở web.
- **Các hàm cốt lõi:**
  - `x(lon)`, `y(lat)`: đổi kinh độ/vĩ độ sang tọa độ điểm trên khung 800×420 (cắt theo vùng 105,18–106,79°Đ và 10,22–10,86°B).
  - `point([lon, lat])`, `path(coordinates)`: tạo chuỗi lệnh vẽ đường SVG (`M` = đặt bút, `L` = kẻ tới).
  - Phần chính: tìm đối tượng `type === 'MAIN_RIVER'` (trục sông, lấy 1/3 số đỉnh), các nhánh có `gate_code` (vẽ kênh và chấm tròn tại đỉnh `gate_path_index` là vị trí cống), rồi `writeFileSync`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — đổi màu/khung của sơ đồ ở trang Tổng quan (rồi chạy lại script).
  - Có — tệp GeoJSON trục sông thay đổi và cần vẽ lại sơ đồ.
  - Không — đổi bản đồ tương tác, sang `features/observations-map.js`.

### `frontend/public/river-diagram.svg`
- **Vai trò trong đời sống:** Bức tranh tĩnh "trục sông Tiền và mười kênh có cống" ở trang Tổng quan (`<img src="/river-diagram.svg">` trong `workspace.html`).
- **Đọc/ghi dữ liệu ở đâu (I/O):** Do `generate-river-diagram.mjs` sinh. Thư mục `public/` được Vite chép nguyên trạng vào `dist/`. Cùng thư mục còn có `public/fonts/` (phông Be Vietnam Pro).
- **Các hàm cốt lõi:** Không có (ảnh). Lớp CSS bên trong: `.paper`, `.grid`, `.river`, `.branch`, `.gate`.
- **Muốn sửa … thì có tìm đến file này không?:** Không sửa tay — sửa script `generate-river-diagram.mjs` rồi chạy lại.

### `frontend/src/main.js`
- **Vai trò trong đời sống:** Giao diện đời đầu "chọn trạm, chọn bộ dữ liệu, xem lịch sử EC từ PostgreSQL". **Hiện là mã cũ không dùng**: không trang HTML nào nạp tệp này (`index.html` nạp `legacy.js`), và các id nó cần (`map`, `basemapToggle`, `datasetSelect`, `filterForm`, `chart`, `dataRows`, `connectionStatus`...) không có trong `workspace.html`. Chức năng tương tự nay nằm ở `features/database-history.js`.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Nếu được chạy: gọi `/api/v1/health`, `/api/v1/stations`, `/api/v1/stations/{mã}/datasets`, `/api/v1/stations/{mã}/observations` (qua `api.js`). Vẽ bản đồ bằng `map.js`, biểu đồ bằng `chart.js`, nạp `style.css`.
- **Các hàm cốt lõi:**
  - `bootstrap()`: kiểm tra `/health`, tải danh sách trạm, vẽ lên bản đồ, chọn trạm đầu tiên.
  - `selectStation(code)`: tải các bộ dữ liệu của trạm (`getDatasets`), tự chọn nếu chỉ có một.
  - `selectDataset(code)`: hiện mã, tên tệp, hash; đặt khoảng 24 tháng gần nhất (`recentRange`) rồi gọi `refreshHistory`.
  - `refreshHistory()`: đọc bộ lọc (`readFilters`), tải toàn bộ lịch sử theo trang (`getHistory`), gọi `renderHistory`.
  - `renderHistory(data)`, `renderTable()`: tính thống kê (`describeSeries`), vẽ biểu đồ (`renderChart`), phân trang bảng 20 dòng, cảnh báo cờ chất lượng UNVERIFIED/SUSPECT/INVALID.
  - `renderStations()`, `renderSiteMetadata()`, `setBusy()`, `showError()`, `resetHistory()`: hàm phụ vẽ danh sách và trạng thái.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Không — sửa tra cứu PostgreSQL trên trang hiện hành, sang `features/database-history.js`.
  - Không — sửa bản đồ hiện hành, sang `features/observations-map.js`.
  - Có — chỉ khi quyết định khôi phục hoặc xóa hẳn giao diện cũ (cần thống nhất với chủ dự án trước).

### `frontend/src/api.js`
- **Vai trò trong đời sống:** "Bưu cục" chung: mọi thư hỏi gửi tới máy chủ đều qua đây. Nó dán tiền tố `/api/v1`, đặt hạn chờ, đọc thư trả lời và dịch lỗi sang tiếng Việt dễ hiểu.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: đường dẫn do tệp khác truyền vào. Tự gọi `/api/v1/stations`, `/api/v1/stations/{mã}/datasets`, `/api/v1/stations/{mã}/observations?dataset_code=...&limit=500&offset=...` (các API PostgreSQL). Đầu ra: dữ liệu JSON đã kiểm tra, hoặc ném lỗi `APIError`.
- **Các hàm cốt lõi:**
  - `requestJSON(path, {signal, method, body, timeoutMs=15000, headers})`: gửi `fetch` tới `/api/v1` + `path`; tự hủy sau 15 giây; báo lỗi "Không kết nối được API", "Yêu cầu quá ... giây", hoặc lấy `detail` từ máy chủ. Gần như mọi tệp khác đều gọi hàm này (trực tiếp hoặc qua `shared/workspace-api.js`).
  - `getStations(options)`: lấy danh sách trạm dạng GeoJSON; báo lỗi nếu mã trạm thiếu hoặc trùng.
  - `getDatasets(siteCode, options)`: lấy các bộ dữ liệu EC của một trạm; kiểm tra đơn vị phải là `mS/m`.
  - `getHistory(siteCode, datasetCode, filters, options)`: tải lịch sử theo từng trang 500 dòng, tối đa 20.000 dòng; kiểm tra rất chặt (không trùng id, cờ chất lượng hợp lệ, thời gian tăng dần, bộ dữ liệu không đổi hash giữa chừng).
  - `createRequestGate()`: "người gác cổng" — mỗi lần gọi `.next()` sẽ hủy request cũ và cấp vé mới; `isCurrent()` cho biết kết quả về có còn đúng lựa chọn mới nhất không. Dùng để khi người dùng bấm trạm A rồi trạm B thật nhanh, số liệu của A không đè lên B.
  - `localDate(iso)`: đổi thời điểm sang ngày theo giờ Việt Nam (`Asia/Ho_Chi_Minh`).
  - `recentRange(dataset)`: tính khoảng 24 tháng gần nhất của một bộ dữ liệu.
  - Lớp `APIError`: loại lỗi riêng để phân biệt lỗi API với lỗi khác.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — tăng thời gian chờ mặc định, đổi câu báo lỗi kết nối.
  - Có — đổi tiền tố `/api/v1` khi backend đổi phiên bản API.
  - Không — thêm endpoint mới của workspace, chỉ cần gọi `workspaceAPI('/duong-dan')` từ tệp tính năng (`shared/workspace-api.js`).

### `frontend/src/map.js`
- **Vai trò trong đời sống:** Bản đồ trạm đơn giản đời đầu (chấm trắng viền xanh, có nhãn tên). **Chỉ `main.js` (mã cũ không chạy) dùng tệp này**; bản đồ hiện hành là `features/observations-map.js`.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: GeoJSON trạm. Đầu ra: bản đồ OpenLayers với nền OpenStreetMap (`https://tile.openstreetmap.org/...`) và một lớp điểm trạm.
- **Các hàm cốt lõi:**
  - `hasCoordinates(feature)`: kiểm tra trạm có tọa độ điểm hợp lệ.
  - `createStationMap(target, {onSelect, onTileError})`: tạo bản đồ, trả về các nút điều khiển `setStations`, `select`, `fit`, `setBasemapVisible`, `destroy`. Bấm vào chấm sẽ gọi `onSelect(site_code)`.
- **Muốn sửa … thì có tìm đến file này không?:** Không — sửa bản đồ đang hiển thị, sang `features/observations-map.js`.

### `frontend/src/chart.js`
- **Vai trò trong đời sống:** "Người vẽ biểu đồ đường" cho lịch sử EC từ PostgreSQL: trục thời gian, trục giá trị, điểm tô màu theo cờ chất lượng.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: mảng số đo (`observed_at`, `conductivity_ms_per_m`, `quality_flag`, `observed_or_estimated`). Đầu ra: một SVG 960×300 chèn vào khung được truyền vào. Được `features/database-history.js` (đang dùng) và `main.js` (cũ) gọi.
- **Các hàm cốt lõi:**
  - `renderChart(container, items, {showQuality})`: vẽ lưới, nhãn trục, đường nối (đứt đoạn khi cách hơn một tháng hoặc gặp số đo INVALID), chấm từng mẫu (INVALID vẽ dấu ×, ước tính E vẽ chấm rỗng); mỗi chấm có chú thích khi rê chuột.
  - `describeSeries(items)`: đếm số đo, tính trung bình và cực đại, bỏ qua dòng INVALID.
  - `number(value)`, `dateLabel(iso)`: định dạng số và ngày kiểu Việt Nam.
  - `QUALITY_LABELS`: bảng dịch cờ chất lượng (UNVERIFIED → "Chưa xác minh"...).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — đổi màu đường, cỡ chấm của biểu đồ lịch sử PostgreSQL.
  - Không — biểu đồ quan trắc trong tab Quan trắc dùng `drawSeries` ở `shared/time-series.js`.

### `frontend/src/intake.js`
- **Vai trò trong đời sống:** "Phòng tiếp nhận hồ sơ": hiển thị các số đo độ mặn mới nhận (đơn vị g/L) đang chờ rà soát, tách riêng khỏi chuỗi EC chính thức.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: gọi `/api/v1/workspace/intake`, `/api/v1/workspace/intake/coverage`, `/api/v1/workspace/intake/measurement-points`; khi người dùng mở mục "Tra cứu số đo độ mặn chưa xác minh" hoặc đổi ô chọn điểm đo thì gọi `/api/v1/workspace/intake/observations?point=...`. Đầu ra: dựng khối `<section id="intake">` trong `#intakeHost` gồm ô tóm tắt, danh sách cần kiểm tra, bảng độ phủ theo trạm, bảng số đo, chi tiết kiểm tra nguồn.
- **Các hàm cốt lõi:**
  - `showIntake(host)`: hàm chính (được `app/workspace.js` gọi lúc mở trang và khi bấm `#retryIntake`); tải ba API song song rồi dựng toàn bộ khối.
  - `loadPoint()` (bên trong): tải số đo của điểm đang chọn, có `createRequestGate` chống kết quả cũ đè kết quả mới.
  - `table(headers, rows)`, `detail(summary, ...)`, `cell(tag, value)`: hàm phụ tạo bảng, khối gập mở, ô chữ.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — đổi câu giải thích "Cần kiểm tra gì?" hoặc thêm cột vào bảng độ phủ.
  - Không — đổi cách backend kiểm tra hồ sơ, sang `backend/intake.py`.
  - Không — khung nhập số đo thực địa, sang `features/field-measurements.js`.

### `frontend/src/research-chart.js`
- **Vai trò trong đời sống:** Một "biển chỉ dẫn" một dòng: chuyển tiếp hàm `drawSeries` từ `shared/time-series.js` để mã cũ vẫn tìm được.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Không có. Hiện chỉ `features/weather-estimates.js` import từ đây.
- **Các hàm cốt lõi:** `drawSeries` (tái xuất, hàm thật ở `shared/time-series.js`).
- **Muốn sửa … thì có tìm đến file này không?:** Không — sửa cách vẽ biểu đồ, sang `shared/time-series.js`.

### `frontend/src/research-utils.js`
- **Vai trò trong đời sống:** Hộp dụng cụ nhỏ dùng chung: định dạng ngày, lọc khoảng ngày, xử lý tọa độ chưa xác nhận.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Không gọi API, không đụng DOM. Là hàm thuần (vào gì ra nấy).
- **Các hàm cốt lõi:**
  - `dateOnly(value)`: `2024-04-15` → `15/04/2024`; sai định dạng thì trả "chưa có ngày".
  - `recentDateWindow(site)`: khoảng 24 tháng gần nhất của trạm (dùng ở `observations.js`).
  - `filterObservations(rows, from, to)`: lọc số đo theo ngày; báo lỗi nếu ngày bắt đầu sau ngày kết thúc.
  - `mapFeatures(collection, showUnconfirmed)`: giữ trạm có tọa độ; nếu bật "Điểm RIA2 tham khảo" thì dựng điểm từ `source_coordinates` và gắn cờ `assumed_crs` (vẽ viền đứt).
  - `experimentAssessment(ex)`: so mô hình được chọn với Persistence theo MAE (dùng ở `forecasts.js`).
  - `safeExternalURL(value)`: chỉ chấp nhận liên kết `https:` (dùng ở `shared/ui.js`).
  - `labels`: bảng dịch mã trạng thái sang tiếng Việt.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — đổi khoảng thời gian mặc định khi chọn trạm (24 tháng).
  - Có — đổi cách hiển thị điểm RIA2 tọa độ chưa xác nhận.
  - Không — đổi định dạng số, sang `shared/ui.js`.

### `frontend/src/app/legacy.js`
- **Vai trò trong đời sống:** "Người dẫn đường" cho địa chỉ cũ: đọc phần sau dấu `#` rồi chuyển sang đúng tab của `workspace.html`.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đọc `location.hash`; ghi `location.replace("/workspace.html" + ...)`. Được `index.html` và `research.html` nạp.
- **Các hàm cốt lõi:** Không có hàm đặt tên; bảng `aliases` đổi `#forecast`/`#future-forecast` → `#forecasts`, `#intake` → `#data-quality`, `#mapSection`/`#historySection` → `#observations`, `#mainContent` → `#overview`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — một liên kết cũ ngoài hệ thống đang trỏ tới hash lạ.
  - Không — điều hướng giữa các tab trong trang chính, sang `navigation.js`.

### `frontend/src/app/navigation.js`
- **Vai trò trong đời sống:** "Người trực cửa" giữa năm phòng: người dùng bấm tab nào thì mở phòng đó, khép các phòng khác.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `location.hash` và sự kiện `hashchange` (khi người dùng bấm liên kết `nav a`). Đầu ra: đặt `hidden` cho mọi phần tử `[data-view]`, đánh dấu `aria-current="page"` cho liên kết tab, đổi `document.title`, cuộn tới phần tử cùng id, và **phát sự kiện `workspace:viewchange`** với `{ view }`. `observations.js`, `observations-map.js`, `timeline-scrubber.js` nghe sự kiện này để bật/tắt bản đồ và hoạt ảnh.
- **Các hàm cốt lõi:**
  - `bindNavigation()`: gắn bộ nghe `hashchange` và chạy lần đầu. Năm view hợp lệ: `overview`, `observations`, `forecasts`, `data-quality`, `gates`; hash lạ quay về `overview`; bí danh `forecast`, `future-forecast`, `intake`, `main`.
  - `navigate()` (bên trong): thực hiện các bước ẩn/hiện ở trên.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — thêm tab thứ sáu (thêm tên vào tập `views`, rồi thêm liên kết và `<section data-view>` trong HTML).
  - Có — đổi tab mặc định khi vào trang.
  - Không — đổi chữ trên thanh tab, sang `workspace.html`.

### `frontend/src/app/workspace.js`
- **Vai trò trong đời sống:** "Tổng quản" của ứng dụng: bật đèn từng phòng, tải dữ liệu nền, và nối dây giữa các tính năng (ví dụ bấm "Dự báo EC cho trạm này" ở Quan trắc thì tab Dự báo chọn đúng trạm).
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: `import` ba tệp CSS (`workspace.css`, `../styles/simulation.css`, `refresh.css`) và các tính năng. Gọi song song `/api/v1/workspace/summary`, `/api/v1/workspace/stations`, `/api/v1/workspace/gates` (qua `workspaceAPI`). Nghe sự kiện `workspace:select-station`, `workspace:multivariate-catalog`, `workspace:multivariate-prediction`, `workspace:multivariate-clear`; nghe bấm `#retryWorkspace`, `#retryIntake`. Đầu ra: ghi `modeBadge`, `loadError`, `statExperiments`, `mapForecastStatus`; giao dữ liệu cho từng tính năng.
- **Các hàm cốt lõi:**
  - Phần khởi tạo (chạy ngay khi nạp): `bindDatabaseCheck()`, `createForecasts()`, `createMultivariateForecast()`, `createFieldMeasurements($("fieldMeasurementsHost"))`, `createObservations({ onForecast })`, `createDatabaseHistory()`, `createWeatherEstimates()`, `createGateDossiers(observations.map)` (tab cống dùng chung bản đồ của Quan trắc), `bindNavigation()`.
  - `loadWorkspace()`: tải summary/stations/gates bằng `Promise.allSettled` (một nguồn hỏng không làm sập các nguồn khác); thành công thì gọi `renderOverview` + `loadDataFreshness` (`overview.js`), `forecasts.load`, `observations.load` rồi `renderOverviewStations`, `gates.load`; lỗi thì hiện `loadError` và nút tải lại.
  - `loadIntake()`: gọi `showIntake()` (`intake.js`), khóa nút `retryIntake` khi đang tải.
  - `showMapForecast(prediction)`: khi có dự báo đa biến, đánh dấu vòng xanh trên bản đồ (`observations.map.setForecast`) và ghi chú thích rằng các điểm quan trắc vẫn giữ số đo riêng.
  - Cuối tệp gọi `loadWorkspace()`, `loadIntake()`, `weather.load()`, `multivariate.load()`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — thêm một tính năng mới cần khởi tạo khi mở trang.
  - Có — đổi thứ tự hoặc cách xử lý lỗi khi tải dữ liệu nền.
  - Không — sửa cách vẽ một tab cụ thể, sang tệp trong `features/`.

### `frontend/src/style.css`
- **Vai trò trong đời sống:** Bộ sơn của giao diện đời đầu (`main.js`). **Không được nạp bởi trang hiện hành** (chỉ `main.js` import nó).
- **Phần tô:** khung ứng dụng cũ: `.app-alert`, `.connection`, `.map-wrap #map`, `.metrics-strip`, `.filter-details`, `.chart-container`, `.history-panel`, `.station-button`...
- **Muốn sửa … thì có tìm đến file này không?:** Không — giao diện hiện hành dùng `app/*.css` và `styles/simulation.css`.

### `frontend/src/app/tokens.css`
- **Vai trò trong đời sống:** "Bảng màu và thước đo chuẩn" của cả trang: khai báo biến CSS trong `:root` để mọi tệp khác dùng chung.
- **Phần tô:** Không tô trực tiếp. Khai báo khoảng cách (`--space-*`), cỡ chữ (`--text-*`), thời gian chuyển động (`--dur-*`), lớp chồng (`--z-*`), màu giấy/mực/nhấn (`--color-paper`, `--color-ink`, `--color-accent`, `--color-focus`...), phông (`--font-body: "Be Vietnam Pro"`), bo góc (`--radius-card`...). Được `refresh.css` nạp bằng `@import`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — đổi màu nhấn chung hoặc phông toàn trang.
  - Không — đổi ba màu cảnh báo EC, sang `refresh.css` (`--ec-safe`, `--ec-caution`...).

### `frontend/src/app/base.css`
- **Vai trò trong đời sống:** "Lớp sơn lót": kiểu mặc định cho thẻ cơ bản trước khi tô chi tiết.
- **Phần tô:** `html`, `body`, `a`, `button`, `h1`, `p`, `img`, `svg`, `::selection`, `:focus-visible`; lớp tiện ích `.container`, `.lead`, `.num`, `.visually-hidden` (ẩn khỏi mắt nhưng trình đọc màn hình vẫn đọc); tắt chuyển động khi người dùng chọn `prefers-reduced-motion`. Được `refresh.css` nạp.
- **Muốn sửa … thì có tìm đến file này không?:** Có — đổi kiểu tiêu điểm bàn phím chung. Không — đổi một khung cụ thể, sang `workspace.css`/`simulation.css`.

### `frontend/src/app/workspace.css`
- **Vai trò trong đời sống:** Bộ sơn chính cho bố cục các tab (trừ phần bản đồ mô phỏng).
- **Phần tô:** Dòng đầu `@import 'ol/ol.css'` (kiểu mặc định của OpenLayers). Thanh đầu `.header`, `.brand`, `.badge`; thẻ thống kê `.stats`; `.workflow-card`, `.quick-scenario-card`; danh sách trạm `.station-panel`, `.station-button`; `.map-layout`, `#researchMap`; bộ lọc `.filters`, `.field-grid`; khung lịch sử `#databaseHistoryHost ...`; dự báo `.forecast-controls`, `.mv-prediction-history`, `.latest-value`; cống `.gate-layout`, `.gate-intake-form`, `.gate-intake-checks`, `.gate-intake-conclusion`, `.checklist`; biểu đồ `.chart`, `.legend`.
- **Muốn sửa … thì có tìm đến file này không?:** Có — đổi bố cục thẻ thống kê, khung hồ sơ cống, bảng lịch sử. Không — đổi thanh điều khiển bản đồ/timeline, sang `styles/simulation.css`.

### `frontend/src/app/refresh.css`
- **Vai trò trong đời sống:** "Lớp sơn mới" phủ sau cùng (được `workspace.js` import cuối) để làm mới giao diện: nền sáng, phông Be Vietnam Pro, và **ba màu cảnh báo EC**.
- **Phần tô:** `@import` `tokens.css` và `base.css`; khai báo `@font-face` cho các tệp `/fonts/BeVietnamPro-*.ttf`; trong `:root` có `--ec-safe: #087b80`, `--ec-caution: #9b5c10` và các biến `--ec-*` khác (bản đồ đọc các biến này qua `getComputedStyle`); thanh đầu `.header nav a[aria-current="page"]`; trang giới thiệu `.intro`; khối tiếp nhận `.intake-panel`, `.intake-summary`, `.intake-detail`; `.forecast-insight`, `.future-stats`; điểm ngắt màn hình 1100px và 700px.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — đổi màu xanh/cam/đỏ của mức cảnh báo EC trên sông và chấm cống.
  - Có — đổi giao diện tab Chất lượng dữ liệu.
  - Không — đổi ngưỡng số (mS/m) quyết định màu, đó là logic ở `gated-waterways.js` và giá trị trên form.

### `frontend/src/styles/simulation.css`
- **Vai trò trong đời sống:** Bộ sơn cho "buồng lái bản đồ" trong tab Quan trắc: thanh công cụ trên bản đồ, chú giải, phiếu cống, dòng thời gian.
- **Phần tô:** `.windy-map-panel`, `.map-scene`, `.map-toolbar`, `.simulation-hud`, `.threshold-popover`, `.simulation-units`, `.map-legend-popover`, `.map-direction-status`, `.forecast-map-banner`, `.simulation-gate-card`, `.simulation-river-tooltip`, `.inspect-water-highlight`, `.inspect-crop-item` (kết quả theo cây trồng); dòng thời gian `.simulation-timeline`, `.timeline-banner`, `.timeline-controls`, `.timeline-axis`, `.timeline-jumps`, `.timeline-status`; cắt dọc `#simulationProfilePanel`, `.river-profile-header`, `.river-profile-gates`, `.river-profile-anchors`; `#observations .map-layout.stations-open`, `.compact-details`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — phiếu cống che mất bản đồ, dòng thời gian quá cao.
  - Có — đổi giao diện popup ngưỡng hoặc chú giải.
  - Không — đổi màu cảnh báo chung, sang `refresh.css`.

### `frontend/src/features/overview.js`
- **Vai trò trong đời sống:** Trang "bảng tin đầu nhà": vài con số tổng, bảng EC gần nhất từng trạm, các thẻ "kịch bản nhanh", độ tươi của nguồn dữ liệu.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: dữ liệu summary và trạm do `workspace.js` truyền vào; tự gọi `/api/v1/data-freshness` và (khi bấm `#checkDatabase`) `/api/v1/health`. Đầu ra: ghi `modeBadge` ("PostgreSQL" hoặc "Snapshot có nguồn"), `statRia`, `statSites`, `statLatest`, `observationCoverage`, `sourceList`, `overviewEcTable`, `overviewEcStatus`, `dbStatus`; tạo động `#quickSpatialScenarios` và `#dataFreshnessPanel`. Phát sự kiện `workspace:simulation-scenario` (khi bấm thẻ kịch bản) và `workspace:select-station` (khi bấm "Mở trạm →").
- **Các hàm cốt lõi:**
  - `mountQuickScenarios()`: thêm bốn thẻ: "Mùa khô · 04/2024", "Mùa mưa · 10/2022", "Kịch bản sầu riêng" (ngưỡng mẫu `durian`), "Dự báo theo khí tượng" (chuyển sang tab `forecasts`). Thẻ có `detail` thì phát `workspace:simulation-scenario` để `timeline-scrubber.js` nhảy tháng/đổi ngưỡng.
  - `renderOverview(summary)`: điền con số và danh sách nguồn (dùng `sourceAnchor` của `shared/ui.js`).
  - `loadDataFreshness(options)`, `freshnessText(key, item)`: tải và dịch trạng thái từng nguồn (ERA5, Kratie, Tân Châu, EC Mỹ Tho) sang "Còn hạn / Sắp cần cập nhật / Đã quá hạn / Thiếu dữ liệu".
  - `renderOverviewStations(collection)`: bảng tối đa 8 trạm có mẫu mới nhất, kèm cảnh báo "đây không phải EC hiện thời".
  - `bindDatabaseCheck()`: gắn nút kiểm tra PostgreSQL.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — thêm một thẻ kịch bản nhanh (ví dụ "Mùa khô 03/2020").
  - Có — đổi số trạm hiện trong bảng tổng quan (đang là 8).
  - Không — đổi cách backend tính độ tươi dữ liệu, sang backend.

### `frontend/src/features/database-history.js`
- **Vai trò trong đời sống:** "Kho lưu trữ hồ sơ": tra cứu toàn bộ lịch sử EC đã nhập vào PostgreSQL theo nguồn, trạm, khoảng ngày, và xuất CSV. Chỉ kết nối khi người dùng tự bấm.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: người dùng bấm "Kết nối và tải danh sách trạm", chọn Nguồn/Trạm/Loại số đo/Từ ngày/Đến ngày. Gọi `/api/v1/stations`, `/api/v1/stations/{mã}/datasets`, `/api/v1/stations/{mã}/observations` (qua `getStations`, `getDatasets`, `getHistory` ở `api.js`). Đầu ra: tự dựng toàn bộ giao diện bên trong `#databaseHistoryHost` (nằm trong khối gập "Tra cứu lịch sử quan trắc PostgreSQL" ở tab Quan trắc): biểu đồ (`renderChart` của `chart.js`, không tô cờ chất lượng), bảng 20 dòng/trang, tệp `ec-history-<mã>.csv`.
- **Các hàm cốt lõi:**
  - `createDatabaseHistory({onSelectStation})`: hàm chính, trả về `{ load, selectStation, destroy }`.
  - `load()`: tải trạm, dựng ô chọn nguồn.
  - `chooseSource()`, `selectStation(code)`, `chooseDataset()`: lọc trạm theo nguồn; với mỗi trạm chỉ lấy bộ dữ liệu mới nhất (`datasets[0]`); đặt sẵn 24 tháng gần nhất.
  - `loadHistory()`: tải lịch sử, vẽ biểu đồ, tính trung bình/cao nhất (`describeSeries`).
  - `renderTable()`, `sync()`: phân trang, khóa/mở nút theo trạng thái.
  - Nút "Xuất CSV đã lọc": đặt mọi ô trong ngoặc kép và vô hiệu công thức bảng tính (ký tự đầu `=`, `+`, `@`, `-`) để an toàn khi mở bằng Excel.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — thêm cột cờ chất lượng vào bảng PostgreSQL.
  - Có — cho chọn phiên bản bộ dữ liệu thay vì luôn lấy bản mới nhất.
  - Không — đổi câu SQL hay quyền đọc DB, sang `backend/main.py`/`backend/database.py`.

### `frontend/src/features/observations.js`
- **Vai trò trong đời sống:** "Trưởng phòng Quan trắc": điều phối danh sách trạm, bản đồ, dòng thời gian, biểu đồ và bảng số đo của trạm đang chọn, cùng lớp dự báo đặt lên bản đồ.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào: summary và trạm từ `workspace.js`; gọi `/api/v1/workspace/stations/{mã}/observations` (qua `createObservationLoader` ở `shared/observation-contract.js`), `/api/v1/workspace/boundaries` (ranh giới), và `POST /api/v1/workspace/multivariate/predict` (bổ sung dự báo Tân Châu/Mỹ Thuận khi nhận `workspace:apply-forecast-overlay`). Đọc `sessionStorage` khóa `workspace.station` để nhớ trạm lần trước; mặc định ưu tiên Mỹ Tho `MRC_VN_019805`.
  - Người dùng: gõ `stationSearch`, bấm trạm, `toggleStationList`, `simulationThresholdToggle`, `mapLegendToggle`, `mapWarningToggle`, `simulationRiverToggle`, `simulationWindToggle`, `simulationMotionToggle`, `mapBaseTheme`, `showUnconfirmed`, `showBoundaries`, `showBase`, `fitMap`, `dateFilter`, `allDates`, `downloadRows`, `openStationForecast`, form `ecComparisonForm`, `mapForecastDismiss`, phím Esc để đóng popup.
  - Nghe sự kiện: `workspace:show-forecast-map`, `workspace:apply-forecast-overlay`, `workspace:simulation-selection`, `workspace:simulation-frame`, `workspace:simulation-loading`, `workspace:simulation-unit`, `workspace:simulation-profile-toggle`, `workspace:multivariate-prediction`, `workspace:multivariate-clear`, `workspace:restore-timeline`, `workspace:ec-comparison`, `workspace:viewchange`.
  - Đầu ra: phát `workspace:display-simulation-frame` (frame cho bản đồ vẽ); ghi `siteTitle`, `siteEC`, `siteWarning`, `observationStatus`, biểu đồ `observationChart` (qua `drawSeries`), bảng `observationRows`, `mapCount`, `mapForecastBanner`; tải tệp `<mã>_observations.csv`.
- **Các hàm cốt lõi:**
  - `createObservations({onForecast})`: hàm chính; tạo bản đồ `createResearchMap` (`observations-map.js`), dòng thời gian `createTimelineScrubber` (`timeline-scrubber.js`), cắt dọc `createRiverProfile` (`river-profile.js`), cầu nối dự báo `createForecastMapBridge` (`shared/forecast-map-overlay.js`). Tắt lớp cống cũ (`map.setGateVisible(false)`) và bật lớp chấm cống (`map.setMappedGateVisible(true)`). Trả về `{ map, load, showError, selectStation }`.
  - `load(summary, collection)`: đặt trạm lên bản đồ, chọn trạm ưu tiên, rồi tải ranh giới.
  - `selectStation(code)`: xóa lớp dự báo, ghi nhãn trạm, cảnh báo riêng cho điểm `RIA2_` (chỉ có ngày, CRS chưa xác nhận), hiện nút dự báo nếu trạm có mô hình, rồi tải số đo.
  - `renderObservations()`: lọc theo ngày (`filterObservations`), vẽ hai chuỗi "EC mẫu nguồn quan trắc" và "EC ước tính (E)", kèm đường ngưỡng đối chiếu (`comparisonLines`).
  - `renderStations()`: vẽ danh sách trạm có ô tìm kiếm.
  - `applyOverlay(context, req, prediction)`: chuyển timeline sang tháng dự báo (`timeline.selectMonth`), áp kịch bản dự báo ba trạm lên frame, đánh dấu trạm dự báo.
  - `renderForecastBanner()`: viết dòng "Tân Châu → Mỹ Thuận → Mỹ Tho" và ghi chú "nội suy 3 trạm" hoặc "nội suy 2 trạm: khuyết mẫu Mỹ Thuận".
  - `clearForecastBanner()`, `showOverlayError()`, `polishProfile()` (căn lại chấm cống trên cắt dọc), `refreshComparison()`/`renderStationComparison()` (ngưỡng tự nhập), `exportRows()`, `showError()`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — đổi trạm chọn mặc định khi mở tab.
  - Có — đổi cột/thứ tự bảng số đo hoặc tên file CSV xuất.
  - Không — đổi cách vẽ màu sông, chấm cống, nhãn trạm trên bản đồ, sang `observations-map.js`.

### `frontend/src/features/observations-map.js`
- **Vai trò trong đời sống:** "Họa sĩ bản đồ": dựng bản đồ OpenLayers với nền, ranh giới, dải màu sông Tiền theo mức cảnh báo EC, đoạn kênh từ sông tới cống, chấm cống tròn, điểm trạm, điểm đo thực địa, vòng dự báo; xử lý rê chuột, bấm, phiếu thông tin.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào: không tự gọi API; nhận dữ liệu qua hàm hoặc sự kiện: `workspace:simulation-corridor` (hình học kênh), `workspace:display-simulation-frame` (frame tháng), `workspace:simulation-unit`, `workspace:select-simulation-gate`, `workspace:focus-coordinate`, `workspace:approved-field-measurements`, `workspace:viewchange`. Nền bản đồ: OpenStreetMap, hoặc ảnh vệ tinh Esri `server.arcgisonline.com` khi chọn `satellite`. Đọc biến màu CSS `--ec-safe`, `--ec-caution`, `--ec-risk`, `--ec-unknown`.
  - Người dùng: bấm/rê vào chấm cống, đoạn kênh, trạm, sông, hoặc một điểm trống; chọn `simulationWaterwayPicker`.
  - Đầu ra: vẽ lên `#researchMap`; thêm hai canvas hoạt ảnh (sông, gió) và ô chú thích `#simulationRiverTooltip`; điền `simulationGateCard`, `mapDirectionStatus`, `mapWindDirectionText`. Phát `workspace:simulation-gate-selected` và `workspace:field-point-selected`.
- **Các lớp (layer), từ dưới lên:** nền tile, `boundaries` (ranh giới nét đứt), `canalLayer` (kênh; **đoạn `beyond_gate` trả về `null` nên không tô**), `riverDiffusion` + `riverLayer` (hai dải màu sông), `candidates`, `gates` (lớp cống cũ, mặc định ẩn), `simulationGates` (chấm cống tròn), `stations` (trạm; ba trạm chính Tân Châu/Mỹ Thuận/Mỹ Tho có nhãn kính dài, các điểm khác chấm nhỏ, RIA2 tọa độ giả định viền đứt), `fieldLayer` (tam giác tím: số đo thực địa đã duyệt), `forecastLayer` (vòng xanh dương dự báo), `isoLayer` (hiện không nạp dữ liệu), `inspection` (điểm tra cứu).
- **Các hàm cốt lõi:**
  - `createResearchMap(target, {onSelect, onTileError})`: hàm chính; trả về bộ điều khiển: `setSimulationCorridor`, `setSimulationFrame`, `setDisplayUnit`, `setRiverParticles`, `setWindVisible`, `setMotionEnabled`, `setBaseTheme`, `refresh`, `setStations`, `setUnconfirmed`, `setBoundaries`, `setBoundaryVisible`, `setGateVisible`, `setMappedGateVisible`, `refreshComparison`, `setForecast`, `setCandidates`, `setGates`, `select`, `fit`, `setBase`, `destroy`. `observations.js` và `gate-dossiers.js` dùng bộ này.
  - `setSimulationFrame(value)` (bên trong): làm mịn sông (`smoothRiverSegments`), cắt dải màu (`riverRibbon`, cả hai ở `river-geometry.js`), đặt chấm cho cống có `canal_ids`, giao frame cho hoạt ảnh (`particles.setFrame`).
  - `setSimulationCorridor(value)`: tách kênh thành "sông tới cống" và "sau cống" (`splitGatedWaterways` ở `gated-waterways.js`), điền ô chọn kênh.
  - `ribbonStyle(...)`, `gateWarningColor(gate)`: chọn màu theo `ecWarningLevel(ec, frame.thresholds)` (`gated-waterways.js`).
  - `selectSimulationGate(code, focus, interaction)`, `renderGateCard()`: chọn cống, phóng tới, hiện phiếu "Từ sông tới cống: ... Đoạn sau cống không tô màu vì chưa có EC nội kênh ... không suy ra trạng thái đóng hoặc mở thực tế".
  - `renderPointCard()`: khi bấm vào điểm trống, dùng `inspectWaterPoint` (`point-inspection.js`) tìm đoạn sông, cống, trạm gần nhất; hiện bảng đối chiếu ngưỡng theo cây trồng (`cropAdvisories` ở `shared/water-advisory.js`) và các câu nhắc "chưa phải số đo tại điểm chọn".
  - `inspectRiver(event)`: nội dung chú thích khi rê chuột.
  - `fitMap()`, `ensureMapMounted()`, `updateDirectionStatus()` (hướng gió dùng `mapWindVector` của `map-particles.js`), `updateForecast()`, `glassLabel(text)` (vẽ nhãn kính bằng SVG).
  - Hàm xuất thêm: `databaseGateFeatureCollection(items)` (đổi danh sách cống DB sang GeoJSON), `fieldMeasurementFeatureCollection(items)` (chỉ lấy số đo `APPROVED` có tọa độ).
  - Trạm hiển thị g/L khi chọn đơn vị độ mặn bằng `ec * 0.0064`, kèm chữ "ước tính".
- **Ghi chú:** Mã tìm `#simulationGatePicker` nhưng HTML hiện không có id này; mã đã kiểm tra `if (picker)` nên không lỗi.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — đổi kích thước chấm cống, nhãn trạm chính, độ dày dải sông.
  - Có — đổi nội dung phiếu cống hoặc phiếu tra cứu điểm.
  - Không — đổi quy tắc ba mức an toàn/chuyển tiếp/rủi ro, sang `gated-waterways.js`; đổi số EC nội suy, sang backend `river_interpolation.py`.

### `frontend/src/features/map-particles.js`
- **Vai trò trong đời sống:** "Hiệu ứng nước chảy và gió thổi": các vệt sáng trắng chạy dọc sông theo hướng kịch bản, và hạt gió màu xanh bay theo hướng gió tháng. Chỉ để minh họa, không phải số đo dòng chảy.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: frame (thuộc tính `flow_direction`, `flow_velocity_factor` của đoạn sông; `wind`), kênh, kích thước màn hình, tùy chọn giảm chuyển động của hệ điều hành. Đầu ra: vẽ lên hai canvas do `observations-map.js` tạo.
- **Các hàm cốt lõi:**
  - `createMapParticles({riverCanvas, windCanvas, project, isVisible, onFrame, ...})`: bộ máy hoạt ảnh; trả về `setFrame`, `setCanals`, `setIntakeGate`, `setVisible`, `setMotionEnabled`, `setTheme`, `setMoving`, `resize`, `start`, `stop`, `destroy`. Tạm dừng khi kéo bản đồ, khi tab ẩn, hoặc khi người dùng tắt hoạt ảnh (lúc đó vẽ mũi tên tĩnh).
  - `riverMotion(properties)`: `UPSTREAM_SALINE_INTRUSION` thì chạy ngược dòng; tốc độ 32 điểm ảnh/giây nhân hệ số (giới hạn 0,2–1,5).
  - `windVector(wind)`: đổi gió (u/v hoặc tốc độ + hướng "thổi từ") sang vectơ trên màn hình.
  - `mapWindVector(wind, targetMonth)`: ưu tiên gió ERA5 đúng tháng (`MONTHLY_ERA5`); nếu không có thì dùng hướng điển hình theo mùa (`SEASONAL_VECTOR_CLIMATOLOGY`).
  - `windParticleCount(width, height)`, `appendTrailPoint(...)`, `boundedDelta(...)`, `windAppearance(theme)`: số hạt, đuôi vệt, bước thời gian an toàn, màu theo nền.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — hoạt ảnh làm máy chậm (giảm `RIVER_PARTICLE_COUNT = 72` hoặc số hạt gió).
  - Có — đổi màu hạt gió trên nền tối/vệ tinh.
  - Không — đổi hướng dòng chảy của kịch bản, sang backend tạo frame.

### `frontend/src/features/timeline-scrubber.js`
- **Vai trò trong đời sống:** "Thanh tua thời gian" dưới bản đồ: kéo để chọn tháng, phát chu kỳ tự động, nhảy nhanh tới các tháng đáng chú ý; đồng thời giữ ngưỡng cảnh báo đang chọn.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào: gọi `/api/v1/workspace/simulation/corridor` và `/api/v1/workspace/simulation/timeline` khi khởi động; mỗi lần đổi tháng/ngưỡng gọi `/api/v1/workspace/simulation/frame?year_month=...&open_below_ec=...&close_above_ec=...` (chờ tối đa 60 giây). Người dùng: `simulationSlider`, `simulationPlay`, `simulationSpeed`, `simulationMonthPicker`, nút trong `simulationJumps`, `simulationRetry`, `simulationProfileToggle`, `simulationThresholdPreset`, `simulationThresholdForm`, `simulationOpenBelow`, `simulationCloseAbove`, radio `simulationUnit`. Nghe `workspace:simulation-scenario`, `workspace:active-forecast-context`, `workspace:viewchange`.
  - Đầu ra: tự viết HTML vào `#simulationTimeline` (các id `simulationMonth`, `simulationRegime`, `simulationTanChau`, `simulationMyThuan`, `simulationMyTho`, `simulationWeather`, `simulationStatus`, `simulationProfilePanel`, `simulationRiverProfile`...). Ghi chú giải `simulationLegendTicks`, `simulationLegendGateThresholds`, `simulationConversionNote`, tóm tắt `#simulationSpatialSummary` (nếu có). Phát `workspace:simulation-corridor`, `workspace:simulation-frame`, `workspace:simulation-loading`, `workspace:simulation-selection`, `workspace:simulation-unit`, `workspace:simulation-profile-toggle`.
- **Các hàm cốt lõi:**
  - `createTimelineScrubber()`: hàm chính; trả về `{ load, stop, selectMonth, selectScenario }`. Ngưỡng mặc định là `ADVISORY_PRESETS.citrus` (`shared/water-advisory.js`). Nút nhảy cố định: `2016-03` (đỉnh mặn lịch sử), `2022-10` (mùa lũ), `2024-04` (mùa khô), tháng cuối; và hai nút "Tháng này"/"Tháng sau".
  - `load()`: tải corridor và timeline, kiểm tra tháng tăng dần, điền ô chọn tháng, rồi `requestFrame()`.
  - `createSimulationFrameLoader({...})`: tải frame và **từ chối** frame nếu sai tháng, sai ngưỡng, thiếu `river_segments`/`gates`, hoặc EC cống không hợp lệ.
  - `validateThresholds(opening, closing)`: hai ngưỡng phải là số không âm và ngưỡng lấy nước < ngưỡng ngăn mặn.
  - `chooseIndex(index, debounce, source)`, `selectMonth(month)`, `selectScenario({month, preset})`, `requestFrame()`, `tick()` (phát tự động, 1500 ms chia tốc độ).
  - `renderBanner()`, `renderGateThresholds()`, `renderSpatialSummary(frame)` (đếm cống theo ba trạng thái), `simulationInputLabel(item)` (nhãn nguồn: "Mẫu nguồn MRC", "+ nội suy thời gian", "Kịch bản trung vị mùa", "Ước tính hồi cứu · khí tượng ERA5"...).
  - Đổi sang đơn vị độ mặn hiện ghi chú "1 mS/m ≈ 0,0064 g/L; màu cảnh báo vẫn theo EC".
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — thêm nút nhảy tới tháng 03/2020.
  - Có — đổi ngưỡng mặc định khi mở trang hoặc tốc độ phát.
  - Không — đổi nhóm ngưỡng mẫu (cam quýt, sầu riêng...), sang `shared/water-advisory.js`.

### `frontend/src/features/river-profile.js`
- **Vai trò trong đời sống:** "Mặt cắt dọc sông": một biểu đồ ngang 175 km từ Tân Châu (0 km) qua Mỹ Thuận, Mỹ Tho (125 km) tới Cửa Tiểu (175 km), cho thấy EC thay đổi dọc sông và chỗ nào vượt ngưỡng.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Đầu vào: frame và đơn vị (từ `observations.js`); người dùng bấm hoặc rê lên chấm cống; nghe `workspace:simulation-gate-selected`. Đầu ra: SVG trong `#simulationRiverProfile`; phát `workspace:select-simulation-gate` (bản đồ sẽ chọn và phóng tới cống đó).
- **Các hàm cốt lõi:**
  - `riverProfileData(frame, unit)`: gom điểm (km, EC) từ các đoạn sông, các đường ngưỡng, vị trí cống chia làn để không chồng nhau, và "mặt mặn" (điểm cắt ngưỡng).
  - `createRiverProfile(host)`: vẽ SVG; trả về `setFrame`, `setUnit`, `clear`.
  - `profileSelectionDetail(gate_code, interaction)`: gói thông tin cống gửi kèm sự kiện.
  - Dùng `advisoryColor`, `formatWater` (`shared/simulation-display.js`) và `MY_THUAN_KM` (`shared/river-interpolation.js`).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — đổi các mốc địa danh hoặc chiều cao biểu đồ cắt dọc.
  - Có — đổi màu đường ngưỡng trên cắt dọc.
  - Không — vị trí km của Mỹ Thuận lấy từ `shared/river-interpolation.js`.

### `frontend/src/features/river-geometry.js`
- **Vai trò trong đời sống:** "Thợ uốn đường": làm đường sông và kênh mềm mại hơn khi vẽ, và cắt sông thành nhiều khúc nhỏ để mỗi khúc mang đúng màu EC. Chỉ đổi hình vẽ, không đổi số liệu từ API.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Hàm thuần, không gọi API, không đụng DOM. Gọi `segmentEcAt` ở `shared/river-interpolation.js`.
- **Các hàm cốt lõi:**
  - `smoothCoordinates(coordinates, {samplesPerSpan, tension})`: chèn điểm trung gian theo đường cong Hermite. `observations-map.js` dùng `tension: 0` để mọi điểm vẽ vẫn nằm trên đoạn nối giữa hai đỉnh gốc.
  - `smoothRiverSegments(features, options)`: nối các đoạn sông thành một tuyến liền (báo lỗi nếu đứt), làm mịn chung rồi chia lại theo đoạn.
  - `riverRibbon(features, count=8, thresholds)`: cắt mỗi đoạn thành ít nhất 8 khúc, thêm điểm cắt tại mốc EC (`ec_stops`) và tại chỗ EC vượt ngưỡng, tính EC giữa khúc theo quãng đường đi, kèm `salinity_g_l = ec * 0.0064`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — chỗ đổi màu trên sông bị lệch so với mốc ngưỡng.
  - Có — sông trông gãy khúc, cần mịn hơn.
  - Không — đổi giá trị EC tại từng mốc, sang backend.

### `frontend/src/features/gated-waterways.js`
- **Vai trò trong đời sống:** "Luật tô màu kênh có cống": quyết định một giá trị EC thuộc mức nào, và cắt mỗi kênh làm hai phần tại vị trí cống.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Hàm thuần; được `observations-map.js` dùng.
- **Các hàm cốt lõi:**
  - `ecWarningLevel(ec, thresholds)`: trả `safe` nếu EC < ngưỡng lấy nước (`open_below_ec_ms_m`), `caution` nếu nằm giữa, `risk` nếu ≥ ngưỡng ngăn mặn (`close_at_or_above_ec_ms_m`); thiếu số hoặc ngưỡng sai thì `unknown`.
  - `splitGatedWaterways(features)`: với kênh có `gate_code` và `gate_path_index` hợp lệ, tạo hai đoạn `river_to_gate` (từ sông tới cống, được tô) và `beyond_gate` (sau cống, không tô vì chưa có EC nội kênh).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — đổi quy tắc "bằng đúng ngưỡng thì thuộc mức nào".
  - Có — muốn tô cả đoạn sau cống (chỉ khi đã có số đo nội kênh, xem `CLAUDE.md` mục 13).
  - Không — đổi màu hiển thị của từng mức, sang `refresh.css`.

### `frontend/src/features/point-inspection.js`
- **Vai trò trong đời sống:** "Thước đo khoảng cách": khi người dùng bấm một điểm trên bản đồ, tìm đoạn sông, cống và trạm gần nhất cùng khoảng cách đường chim bay.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Hàm thuần; đầu vào là tọa độ, frame, danh sách trạm; đầu ra là đối tượng kết quả để `observations-map.js` viết phiếu.
- **Các hàm cốt lõi:**
  - `validCoordinate(value)`: kiểm tra cặp kinh/vĩ độ hợp lệ.
  - `haversineKm(a, b)`: khoảng cách trên mặt cầu Trái Đất (bán kính 6371,0088 km).
  - `nearestRiverPoint(point, segments)`: chiếu điểm lên từng đoạn thẳng của sông để tìm điểm gần nhất.
  - `inspectWaterPoint(coordinate, frame, stationFeatures)`: gom kết quả `{ river, gate, station, yearMonth }`; trả `null` nếu frame không phải lớp mô phỏng.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có — tra cứu báo sai đoạn sông gần nhất.
  - Không — đổi chữ trên phiếu tra cứu, sang `observations-map.js` (`renderPointCard`).

## 2.D. Frontend: dự báo EC, hồ sơ cống, phiếu thực địa và thư viện dùng chung (shared)

Phần này giải thích các tệp JavaScript lo phần **dự báo EC**, **hồ sơ cống**, **phiếu đo EC thực địa** và các **thư viện dùng chung** trong `frontend/src/shared/`. Mã nguồn không có chú thích, nên mỗi tệp được giải thích theo cùng một khuôn: vai trò, dữ liệu vào/ra, các hàm chính, và khi nào cần mở tệp đó.

### Từ ngữ cần biết trước khi đọc

- **Module (mô-đun):** mỗi tệp `.js` là một "hộp đồ nghề". Tệp khác muốn dùng một món trong hộp thì phải **import** (mượn vào); tệp chủ phải **export** (cho mượn) món đó. Ví dụ `import { num } from '../shared/ui.js'` nghĩa là "mượn hàm `num` từ tệp `ui.js`".
- **API:** "cửa sổ giao dịch" của máy chủ FastAPI. Trình duyệt gửi yêu cầu tới một địa chỉ như `/api/v1/workspace/multivariate/catalog`, máy chủ trả lại dữ liệu dạng **JSON** (một dạng văn bản có cấu trúc, giống phiếu khai có ô tên và ô giá trị).
- **fetch / requestJSON:** hành động "gửi người đi lấy hồ sơ ở máy chủ rồi chờ mang về". Trong dự án, mọi lần gọi đều đi qua `requestJSON()` trong `frontend/src/api.js`. Hàm này tự gắn tiền tố `/api/v1`, đặt giờ chờ tối đa (mặc định 15 giây) và đổi lỗi kỹ thuật thành câu tiếng Việt dễ hiểu.
- **workspaceAPI:** viết tắt của "gọi `requestJSON` và thêm `/workspace` vào trước đường dẫn". Gọi `workspaceAPI('/multivariate/catalog')` thì địa chỉ thật là `/api/v1/workspace/multivariate/catalog`.
- **async / await / Promise:** "đặt hàng rồi chờ giao". Hàm `async` có thể dừng ở chữ `await` để chờ máy chủ trả lời mà không làm treo trang.
- **Request gate (`createRequestGate`, trong `frontend/src/api.js`):** cơ chế "chỉ nhận vé mới nhất". Người dùng đổi trạm ba lần liên tiếp thì ba yêu cầu bay đi. Chỉ câu trả lời của lần cuối được hiển thị; câu trả lời cũ về muộn bị bỏ qua bằng `req.isCurrent()`.
- **Sự kiện (event, `CustomEvent`):** giống "loa phát thanh trong xóm". Một tệp phát `window.dispatchEvent(new CustomEvent('workspace:...', { detail }))`. Tệp nào đã đăng ký nghe (`addEventListener`) tên đó thì nhận được gói `detail`. Hai bên không cần biết nhau. Các sự kiện của dự án đều bắt đầu bằng `workspace:`.
- **DOM và `id`:** trang HTML là một cây phần tử. `$('gateSelect')` (hàm trong `shared/ui.js`) nghĩa là "tìm phần tử có `id="gateSelect"` trong `frontend/workspace.html`".
- **localStorage / sessionStorage:** ngăn kéo nhỏ trong trình duyệt. `localStorage` giữ lâu kể cả khi đóng trình duyệt; `sessionStorage` mất khi đóng tab.
- **P10–P90:** Random Forest gồm nhiều "cây quyết định", mỗi cây đưa ra một con số riêng. Xếp 300 con số đó từ nhỏ tới lớn: P10 là mốc mà 10% số cây đoán thấp hơn, P90 là mốc mà 90% số cây đoán thấp hơn. P10–P90 chỉ cho biết **các cây bất đồng với nhau tới mức nào**. Đây **không phải** khoảng tin cậy đã hiệu chuẩn, và không bao trọn sai số thật.
- **MAE / RMSE:** MAE là trung bình độ lệch tuyệt đối. Ví dụ đoán 50, 60, 70 trong khi thực tế là 40, 60, 100 thì độ lệch là 10, 0, 30 và MAE = 13,3. RMSE phạt nặng lần lệch lớn: cũng ví dụ đó thì RMSE = √((100+0+900)/3) ≈ 18,3.

### Lưu ý khoa học phải giữ khi trình bày

- Dự báo EC là **dự báo tại trạm** (Tân Châu, Mỹ Thuận, Mỹ Tho), không phải số đo tại cống. Màu sông trên bản đồ sau khi áp dự báo là **nội suy hình học** dọc trục sông.
- Công cụ hồ sơ cống chỉ **rà soát điều kiện để người vận hành xem xét**. Mọi kết quả đều kèm `requiresOperatorReview: true` và `actuatorCommand: null` (không có lệnh điều khiển cống).
- Ngưỡng cây trồng và ngưỡng mẫu chỉ là **minh họa hoặc tham khảo**, chưa phải tiêu chuẩn tưới đã phê duyệt. Quy đổi `g/L ≈ 0,0064 × EC` chỉ để tham khảo.

---

### 2.D.1. Các tệp tính năng (`frontend/src/features/`)

### `frontend/src/features/multivariate-forecast.js`

- **Vai trò trong đời sống:** Đây là "quầy dự báo" của tab **Dự báo EC đa biến**. Người dùng chọn trạm (ví dụ Mỹ Tho) và tháng cần dự báo (ví dụ 2026-03). Quầy lấy dữ liệu thời tiết và thủy văn của **hai tháng trước** (2026-01), chuyển cho máy chủ chạy mô hình Random Forest đã lưu sẵn, rồi in kết quả: con số EC, mức phân tán P10–P90 và bảng đối chiếu với kịch bản cây trồng. Cách làm giống hỏi thầy thuốc: đưa sổ khám hai tháng trước, thầy đoán tình trạng tháng này.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào, gọi API qua `workspaceAPI`:
    - `GET /api/v1/workspace/multivariate/catalog`: danh sách trạm có mô hình, mốc huấn luyện, tên biến.
    - `GET /api/v1/workspace/multivariate/inputs?station=...&target_month=...`: số liệu khí tượng tháng `t−2`. Riêng Mỹ Tho có thêm khối `hydrology` gồm `kratie_q_t2`, `kratie_q3_t2`, `kratie_q_ratio_t2`, `tc_stage_t2`, `tc_stage3_t2`.
    - `POST /api/v1/workspace/multivariate/predict`: chạy dự báo nhưng không lưu.
    - `POST /api/v1/workspace/multivariate/history`: chạy dự báo và lưu vào PostgreSQL. Đây là lựa chọn mặc định vì ô "Lưu lượt chạy vào PostgreSQL" được tick sẵn.
    - `GET /api/v1/workspace/multivariate/evaluation?station=...&protocol=FROZEN_EC_WEATHER_ONLY_V1&experiment=...&ec_delay_days=5`: lấy dữ liệu đánh giá hồi cứu "khi EC ngừng cập nhật".
  - Đầu vào, HTML: chỉ cần khung `id="multivariateForecastHost"`. Tệp tự dựng toàn bộ form bên trong. Nếu không tìm thấy khung này, tệp trả về một đối tượng rỗng và không làm gì.
  - Đầu vào, người dùng nhập: trạm; tháng (có nút nhanh "Tháng này" và "Tháng sau"); nguồn đầu vào (`ARCHIVE` là dữ liệu lưu trữ, `MANUAL` là người dùng tự nhập); ba ô mưa (mm), nhiệt độ (°C), gió; ô tick lưu PostgreSQL; kỳ đánh giá `gap_2021_2023`, `gap_2022_2023` hoặc `gap_2019_2021`.
  - Đầu ra, vẽ trên trang: thẻ kết quả EC (mS/m); khối "Mức phân tán giữa các cây Random Forest" gồm P10–P90, P25, P50, P75, IQR, độ lệch chuẩn; bảng cây trồng; bảng biến đầu vào kèm nguồn; MAE/RMSE; độ quan trọng của biến; biểu đồ hồi cứu (EC thực đo, RF + thủy văn, RF chỉ khí tượng, giữ EC cuối) cùng hai bảng nghiên cứu bổ sung.
  - Đầu ra, sự kiện phát đi:
    - `workspace:multivariate-prediction`: có kết quả mới. `workspace.js` và `observations.js` nghe sự kiện này.
    - `workspace:multivariate-clear`: kết quả cũ không còn đúng.
    - `workspace:multivariate-catalog`: đã tải xong danh mục mô hình.
    - `workspace:show-forecast-map`: nút "Áp dụng kịch bản dự báo lên bản đồ".
    - `workspace:restore-timeline`: nút "Quay về dữ liệu Timeline gốc". Trang chuyển về `#observations`.
    - `workspace:apply-forecast-to-gate`: nút "Dùng dự báo để kiểm tra cống". Trang chuyển về `#gates`.
  - Đầu ra, sự kiện lắng nghe: `workspace:select-forecast-month` (nơi khác yêu cầu chọn sẵn một tháng).
  - Đầu ra, tệp tải về: `<trạm>_<tháng>_multivariate.json` và `.csv`.
- **Các hàm cốt lõi:**
  - `createMultivariateForecast({ onStation, onPrediction })`: hàm duy nhất được export. Nó dựng form, nối các nút với hành động, rồi trả về `{ load, selectStation }`. Hai tham số là hàm "gọi lại" (callback) để báo cho `workspace.js` khi đổi trạm hoặc khi có dự báo mới. Hàm này cũng gắn `createForecastIssuePanel` (sổ phát hành) và `createPredictionHistory` (lịch sử dự báo) vào cùng khung.
  - `load()`: gọi `/multivariate/catalog`, đổ danh sách trạm vào ô chọn. Tháng mặc định lấy theo thứ tự ưu tiên: tháng đang chờ từ sự kiện, rồi `default_target_month` của máy chủ, rồi "tháng sau" theo `forecastMonthFromToday(1)`. Cuối cùng gọi `loadInputs()`.
  - `loadInputs()`: tính tháng đầu vào bằng `inputMonthFor()` (tệp `shared/forecast-contract.js`). Ví dụ chọn 2026-03 thì đầu vào là 2026-01. Hàm gọi `/multivariate/inputs` rồi kiểm tra kỹ dữ liệu trả về: đúng trạm, đúng tháng, gió phải có đơn vị `m/s`, và với Mỹ Tho phải đủ 5 biến thủy văn. Sai một điều là báo lỗi và không cho chạy. Với Mỹ Tho, nếu thiếu thủy văn thì nút "Chạy" bị khóa kể cả khi người dùng nhập tay khí tượng, vì nhập khí tượng không bù được phần thủy văn còn thiếu.
  - `refreshButton()`: quyết định nút "Chạy dự báo đa biến" sáng hay tối. Nút tối khi: đang chạy dở; chưa có trạm; tháng sai; Mỹ Tho thiếu thủy văn; hoặc chọn `ARCHIVE` mà kho lưu trữ chưa đủ số liệu.
  - `applyMode()`: ở chế độ `ARCHIVE`, ba ô số bị khóa và tự điền từ kho. Ở chế độ `MANUAL`, ba ô mở cho người dùng gõ, và kết quả sẽ ghi nguồn là MANUAL.
  - Xử lý nút gửi form (`form.addEventListener("submit", ...)`): gom `station`, `target_month`, `input_mode` (cộng ba biến nếu là `MANUAL`), rồi gửi `POST` tới `/multivariate/history` hoặc `/multivariate/predict`. Giờ chờ tối đa là 120 giây. Kết quả phải qua `validPrediction()` mới được hiển thị.
  - `renderResult(data)`: vẽ thẻ kết quả.
    - Phần P10–P90 chỉ hiện khi máy chủ gửi `ensemble_distribution` hợp lệ. Câu ghi chú luôn nhắc rằng đây chưa phải khoảng tin cậy. Ví dụ "P10–P90: 40–95 mS/m" nghĩa là 80% số cây đoán trong khoảng đó.
    - Bảng cây trồng gọi `cropAdvisories()` trong `shared/water-advisory.js`.
    - Nếu tháng mục tiêu đã qua, hàm thêm dòng "Dự báo hồi cứu".
  - `loadEvaluation()`: vẽ biểu đồ "Kiểm chứng dự báo khi EC ngừng cập nhật" bằng `drawSeries()` (tệp `shared/time-series.js`).
    - Với Mỹ Tho, đường "RF + thủy văn (mô hình chính)" chỉ được vẽ khi `remedy_research` khớp đúng trạm, kỳ và độ trễ, và đủ số tháng.
    - Hàm tô đậm tháng lệch nhiều nhất. Nếu RMSE của mô hình cao hơn cách "giữ EC cuối", hàm ghi rõ điều đó.
    - Bảng "Báo EC cao giả ≥100" và "Bỏ sót EC ≥100" có câu ghi chú rằng 100 mS/m chỉ là mốc phân tích lỗi, không phải chuẩn tưới.
  - `clearResult(message)`: xóa kết quả cũ khi đầu vào đổi, khóa các nút tải/bản đồ/cống, rồi phát `workspace:multivariate-clear`.
  - `describeModel()`: in "huấn luyện đến ..." và đặt tháng nhỏ nhất được chọn là tháng ngay sau mốc huấn luyện.
  - `selectStation(code)`: được gọi khi người dùng bấm một trạm trên bản đồ. Nếu trạm có mô hình thì chọn trạm đó. Nếu không có thì báo "Điểm này chưa có mô hình đa biến đã đăng ký".
  - Nút CSV: mỗi biến đầu vào thành một dòng, cột chung gồm mã dự báo, phiên bản mô hình, tháng, EC, và các cột `ensemble_p10` ... `ensemble_std`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi chữ trên form dự báo, thêm ô nhập, hoặc đổi cách trình bày P10–P90 hay bảng kiểm chứng hồi cứu thì sửa ở đây.
  - Có. Muốn đổi điều kiện khóa nút "Chạy" (ví dụ quy tắc Mỹ Tho thiếu thủy văn) thì xem `refreshButton()` và `loadInputs()`.
  - Không. Muốn đổi cách mô hình tính EC thì sang `backend/domain/multivariate_ec.py` và `backend/services/multivariate.py`. Muốn đổi ngưỡng cây trồng thì sang `frontend/src/shared/water-advisory.js`.

### `frontend/src/features/prediction-history.js`

- **Vai trò trong đời sống:** Đây là "sổ ghi chép" đi kèm quầy dự báo. Nó có ba việc:
  1. Nút "Chạy và lưu dự báo vào PostgreSQL" cho lượt vừa chạy mà chưa lưu.
  2. Bảng **so sánh các lượt chạy trong phiên**. Ví dụ thử mưa 50 mm rồi 120 mm cho cùng tháng, bảng sẽ ghi EC thay đổi bao nhiêu so với lượt đầu.
  3. Bảng **lịch sử đã lưu** trong PostgreSQL, có lọc và phân trang.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào, gọi API:
    - `POST /api/v1/workspace/multivariate/history`: máy chủ chạy lại mô hình với cùng yêu cầu rồi lưu kết quả do chính máy chủ tạo ra. Trình duyệt không gửi con số EC lên để lưu.
    - `GET /api/v1/workspace/multivariate/history?limit=20&offset=...&station=...&target_month=...`: đọc lịch sử theo trang.
  - Đầu vào, HTML: nhận một khung `host` do `multivariate-forecast.js` truyền vào và tự dựng phần tử bên trong. Không đọc `id` cố định nào.
  - Đầu vào, người dùng nhập: bộ lọc trạm và tháng, nút trang trước/trang sau, nút xóa bảng phiên.
  - Đầu ra, vẽ: bảng so sánh phiên, bảng lịch sử, và mục "Xem đầu vào" cho từng lượt.
  - Đầu ra, sự kiện: nút "Bản đồ" của mỗi dòng lịch sử phát `workspace:show-forecast-map`.
  - Đầu ra, gọi lại: `onSaved(prediction)` báo cho quầy dự báo cập nhật kết quả.
  - Đầu ra, tệp tải về: `multivariate_scenarios_comparison.csv`, và JSON của từng lượt.
- **Các hàm cốt lõi:**
  - `createPredictionHistory(host, { onSaved })`: dựng giao diện và trả về `{ record, setCandidate, setStations }`.
  - `record(data)`: ghi một lượt dự báo hợp lệ vào bảng phiên.
  - `renderComparison()`: so sánh mỗi lượt với **lượt đầu tiên cùng trạm, cùng tháng, cùng phiên bản mô hình**. Ví dụ lượt 1 cho 80 mS/m, lượt 3 cho 95 mS/m thì cột chênh ghi "+15 mS/m". Bảng này mất khi tải lại trang.
  - `loadHistory(pageOffset)`: đọc mỗi trang 20 lượt. Từng dòng phải qua `validPrediction()` (tệp `shared/forecast-contract.js`) và phải khớp bộ lọc. Có một dòng sai là cả trang bị từ chối.
  - `setCandidate(payload)`: nhớ "yêu cầu đang chờ lưu" và tăng một số đếm phiên bản. Nếu người dùng đổi form trong lúc máy chủ đang lưu, kết quả lưu vẫn vào lịch sử nhưng không đè lên kết quả đang hiển thị.
  - `setStations(items)`: cập nhật ô lọc trạm theo danh mục mô hình mới.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi số dòng mỗi trang (hiện là 20) hoặc thêm cột vào bảng lịch sử thì sửa ở đây.
  - Có. Muốn đổi cách tính "chênh so với mốc cùng nhóm" thì xem `renderComparison()`.
  - Không. Muốn đổi bảng SQL lưu dự báo thì sang `backend/repositories/dss_storage.py` và thư mục `sql/`.

### `frontend/src/features/forecast-issue-panel.js`

- **Vai trò trong đời sống:** Đây là "sổ phát hành" giống sổ giao báo: mỗi tháng phải phát hành một bản dự báo vào giờ định sẵn. Lịch `MONTHLY_D06_PREV` nghĩa là 09:00 ngày 06 của tháng trước tháng mục tiêu. Sổ ghi bản nào đúng hạn, bản nào trễ (`LATE`), bản nào bị lỡ (`MISSED`). Khi có EC thật thì sổ chấm sai số.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào: `GET /api/v1/forecast-issues` qua `requestJSON('/forecast-issues')`. Router này không nằm dưới `/workspace`.
  - Đầu vào, HTML: nhận `host` từ `multivariate-forecast.js`.
  - Đầu vào, người dùng: nút "Làm mới sổ phát hành".
  - Đầu ra: bảng gồm Tháng, Trạm, Trạng thái, Dự báo, Nhãn EC, Sai số tuyệt đối; kèm dòng tổng hợp MAE.
- **Các hàm cốt lõi:**
  - `issueRow(item)`: biến một "slot" thành một dòng bảng. Trạng thái lấy từ `issue.issue_status`. Nếu không có thì xét danh sách sự kiện: có sự kiện `MISSED` thì ghi `MISSED`, ngược lại ghi `SCHEDULED`.
  - `scoreSummary(summary)`: viết MAE **tách riêng theo nguồn**: `MRC` và `FIELD_APPROVED` (EC25 thực địa đã duyệt). Lý do là cơ sở nhiệt độ của MRC chưa được xác nhận. Bản đúng hạn và bản trễ cũng được báo riêng. Nếu chưa có điểm chấm, hàm ghi rõ "mới kiểm chứng hạ tầng phát hành".
  - `createForecastIssuePanel(host, { load })`: dựng khung và gọi `reload()` ngay. Tham số `load` có thể được thay bằng hàm giả khi chạy test (xem `tests/forecast_issue_panel.test.mjs`).
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi chữ giải thích lịch phát hành hoặc cột của sổ thì sửa ở đây.
  - Không. Muốn đổi luật xác định `LATE` hay `MISSED` thì sang backend `backend/api/forecast_issues.py` và các tệp dịch vụ phía sau.

### `frontend/src/features/forecasts.js`

- **Vai trò trong đời sống:** Đây là "phòng xem lại bài thi cũ" (hồi kiểm). Với mỗi thí nghiệm đã lưu, tệp vẽ đường EC quan trắc, đường mô hình được chọn và đường `Persistence` (giữ nguyên EC tháng trước). Tệp cũng chỉ ra tháng mô hình đoán lệch nhiều nhất để người xem rà soát.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào, API: `GET /api/v1/workspace/experiments/{experiment_id}`. Các tệp tải về lấy theo đường `artifactURL()` dạng `/api/v1/workspace/artifacts/{id}/{tên tệp}`, gồm `metrics.csv`, `high_ec_metrics.csv`, `predictions.csv`, `run_manifest.json`, `split_manifest.csv`, `forecast_chart.png`.
  - Đầu vào, HTML (id): `experimentSelect`, `retryForecast`, `predictionYear`, `downloadPredictions`, `forecastStatus`, `forecastChart`, `metricsRows`, `artifactLinks`, `modelAssessment`, `forecastInsight`, `predictionRows`, `predictionStatus`, `predictionModelHeading`.
  - Đầu vào, bộ nhớ: `sessionStorage` khóa `workspace.experiment` để nhớ thí nghiệm đang chọn.
  - Đầu vào, sự kiện: nghe `workspace:ec-comparison` để vẽ lại đường ngưỡng do người dùng tự nhập.
  - Đầu ra: biểu đồ, bảng MAE/RMSE, bảng từng tháng, tệp `<id>_monthly.csv` (cột `data_kind` = `HISTORICAL_BACKTEST`).
- **Các hàm cốt lõi:**
  - `largestForecastError(rows)`: tìm tháng có |dự báo − thực đo| lớn nhất. Ví dụ ba tháng lệch lần lượt 5, 30, 12 mS/m thì hàm trả về tháng lệch 30.
  - `createForecasts()`: trả về `{ load, showError, selectStation }`. Hàm này tạo luôn `createNextForecast()` để đọc dự báo sau mẫu cuối.
  - `load(experiments)`: mỗi trạm chỉ giữ một thí nghiệm mặc định, là thí nghiệm có `availability_lag_days` nhỏ nhất.
  - `selectExperiment()`: tải thí nghiệm và kiểm tra đơn vị `mS/m`, tháng hợp lệ, cùng trạm. Hàm gọi `experimentAssessment()` (tệp `frontend/src/research-utils.js`) để viết câu so sánh MAE với mô hình đối chứng. Nếu RMSE cao hơn đối chứng, câu sẽ nhắc "sai số cực trị cần rà soát".
  - `renderPredictions()`: lọc theo năm, dựng bảng, vẽ biểu đồ bằng `drawSeries()`. Đường ngưỡng lấy từ `comparisonLines()` (tệp `shared/ec-scenario.js`).
  - `selectStation(siteCode)`: chọn thí nghiệm của trạm được bấm trên bản đồ.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi biểu đồ hồi kiểm, bảng MAE/RMSE, hoặc câu nhận xét tháng lệch lớn nhất thì sửa ở đây.
  - Không. Muốn đổi số liệu thí nghiệm thì sang `backend/services/forecasts.py` và `data/research/experiment_registry.json`. Đây là kết quả nghiên cứu, không phải mô hình đang phục vụ.

### `frontend/src/features/next-forecast.js`

- **Vai trò trong đời sống:** Đây là "phiếu dự báo lưu trữ" của một thí nghiệm cũ. Thí nghiệm đã đoán tháng ngay sau mẫu EC cuối cùng là bao nhiêu. Nếu thí nghiệm là `RF_compact` tại Mỹ Tho, người dùng có thể đưa con số đó lên bản đồ để xem thử.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào, API: `GET /api/v1/workspace/experiments/{id}/next-forecast`.
  - Đầu vào, HTML (id): `nextForecastValue`, `nextForecastTarget`, `nextForecastStatus`, `nextForecastRows`, `nextForecastDownload`, `nextForecastApplyMap`, `nextForecastModelInfo`, `nextForecastRestoreTimeline`.
  - Đầu ra: con số dự báo, bảng các mô hình, tệp `<id>_next_forecast.json`.
  - Đầu ra, sự kiện: `workspace:apply-forecast-overlay` với gói `detail` gồm `sourceModel`, `targetMonth`, `mythoEc`, `p90Threshold`, `experimentId`, `availabilityLagDays`; và `workspace:restore-timeline`.
- **Các hàm cốt lõi:**
  - `createNextForecast()`: trả về `{ reset, load }`.
  - `load(id, experiment)`: kiểm tra rất chặt gói dữ liệu trước khi hiển thị. Các điều kiện gồm:
    - `data_kind` phải là `EXPERIMENTAL_NEXT_AFTER_LAST_OBSERVATION`.
    - `live_forecast_available`, `deployment_ready`, `gate_decision_eligible` đều phải là `false`. Nói cách khác, gói dữ liệu phải tự nhận "không dùng cho vận hành".
    - Mốc phát hành phải nằm trước tháng mục tiêu.
    - Đơn vị phải là `mS/m`.
    - Ngưỡng P90 lấy từ `high_ec_metrics` của thí nghiệm. Nếu không có thì dùng mặc định `60.42` (`DEFAULT_P90_MYTHO_MS_M`).
  - `reset(message)`: đưa giao diện về trạng thái trống.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi điều kiện cho phép bấm "Áp lên bản đồ" thì sửa ở đây.
  - Không. Muốn đổi cách bản đồ tô màu theo con số này thì sang `frontend/src/shared/forecast-map-overlay.js` và `frontend/src/features/observations.js`.

### `frontend/src/features/weather-estimates.js`

- **Vai trò trong đời sống:** Đây là "bảng ước tính cũ" trong tab **Chất lượng dữ liệu**. Nó cho thấy EC từng được ước tính theo tháng chỉ từ khí tượng Open-Meteo. Đây là bản nghiên cứu hồi cứu, không phải dự báo Mỹ Tho hiện hành, và không dùng để quyết định lấy nước.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào, API: `GET /api/v1/workspace/monthly-estimates?station=...`.
  - Đầu vào, HTML (id): `futureStationSelect`, `retryFuture`, `downloadFutureCsv`, `futureStatus`, `futureTableRows`, `futureEcChart`, `kpiFutureMax`, `kpiFutureAvg`, `kpiFutureMaxMonth`.
  - Đầu ra: biểu đồ, bảng, ba ô số (giá trị lớn nhất, trung bình, tháng lớn nhất), tệp `<trạm>_ec_weather_estimate.csv`.
- **Các hàm cốt lõi:**
  - `createWeatherEstimates()`: trả về `{ load }`.
  - `load()`: yêu cầu `data_kind` là `RETROSPECTIVE_WEATHER_ESTIMATE`, và `live_forecast_available` cùng `gate_decision_eligible` đều là `false`. Mỗi dòng phải đúng trạm và không có tháng trùng. Hàm tính giá trị lớn nhất và trung bình. Ví dụ ba tháng 40, 70, 55 thì lớn nhất là 70, trung bình là 55. Biểu đồ vẽ bằng `drawSeries()`, mượn qua `frontend/src/research-chart.js`, tệp này chỉ chuyển tiếp từ `shared/time-series.js`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi bảng hoặc biểu đồ "ước tính hồi cứu" thì sửa ở đây.
  - Không. Muốn thay CSV nguồn thì sang `backend/services/forecasts.py` và `data/models/future_ec_forecast_2024_2026.csv`.

### `frontend/src/features/field-measurements.js`

- **Vai trò trong đời sống:** Đây là "phiếu đo EC ngoài hiện trường" cho cán bộ nội bộ. Cán bộ cầm máy đo ra sông hoặc ruộng, ghi số đo, gửi phiếu. Phiếu nằm ở **hàng chờ duyệt**. Người duyệt bấm Duyệt hoặc Từ chối. Chỉ phiếu đã duyệt mới hiện trên bản đồ (ký hiệu tam giác). Phiếu này tách khỏi chuỗi MRC và không tự trở thành nhãn EC tháng.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào và đầu ra, API qua `requestJSON`, tất cả dưới `/api/v1/field-measurements`:
    - `POST /api/v1/field-measurements`: gửi phiếu. Cần header `X-API-Key` là khóa gửi phiếu.
    - `GET /api/v1/field-measurements?status=APPROVED`: đọc phiếu đã duyệt.
    - `GET /api/v1/field-measurements?status=PENDING`: đọc hàng chờ. Cần khóa duyệt.
    - `POST /api/v1/field-measurements/{measurement_id}/review`: gửi quyết định `APPROVED` hoặc `REJECTED`, kèm người duyệt và ghi chú.
  - Đầu vào, HTML: khung `fieldMeasurementsHost`, do `frontend/src/app/workspace.js` truyền vào.
  - Đầu vào, người dùng: kinh độ, vĩ độ, EC gốc, đơn vị gốc, thời điểm đo (GMT+7), loại vị trí (`RIVER` hoặc `FIELD`), mã thiết bị, người gửi, cơ sở EC (`UNKNOWN`, `EC25`, `RAW`), ngày hiệu chuẩn, mã biên bản hiệu chuẩn, nhiệt độ nước, API key.
  - Đầu vào, sự kiện: nghe `workspace:field-point-selected`, do `observations-map.js` phát khi người dùng bấm lên bản đồ. Kinh độ và vĩ độ được tự điền.
  - Đầu ra, sự kiện: `workspace:approved-field-measurements`. `observations-map.js` nghe sự kiện này để vẽ tam giác.
- **Các hàm cốt lõi:**
  - `convertedEc(value, unit)`: đổi mọi đơn vị về mS/m. Hệ số: `µS/cm` × 0,1; `dS/m` × 100; `mS/cm` × 100; `mS/m` × 1. Ví dụ máy đo ghi 1500 µS/cm thì ra 150 mS/m; ghi 2 dS/m thì ra 200 mS/m. Giá trị rỗng, âm hoặc đơn vị lạ trả về `null`.
  - `approvedMapItems(items)`: chỉ giữ phiếu `APPROVED` có tọa độ là số hợp lệ.
  - `createFieldMeasurements(host)`: dựng form và hàng chờ, rồi trả về `{ loadApproved, loadPending }`. Khi gửi phiếu, thời điểm được ghép thêm `+07:00` (giờ Việt Nam). Trình duyệt gửi EC gốc và đơn vị gốc; con số quy đổi chỉ để người nhập tự kiểm tra trên màn hình.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn thêm ô nhập vào phiếu, hoặc thêm đơn vị đo mới vào bảng `FACTORS`, thì sửa ở đây. Backend cũng phải chấp nhận đơn vị đó.
  - Không. Muốn đổi cách kiểm khóa API hoặc lưu phiếu thì sang `backend/api/field_measurements.py` và `backend/security.py`.

### `frontend/src/features/gate-dossiers.js`

- **Vai trò trong đời sống:** Đây là "tủ hồ sơ cống" của tab **Hồ sơ cống**. Nó gom danh sách cống từ ba nguồn: danh mục gốc, PostgreSQL và lớp GIS trên bản đồ. Khi người dùng chọn một cống, tủ hiện thông tin cống (diện tích phục vụ, khẩu độ, lý trình km) và các trạm đo gần đó, rồi chuyển cống cho khung kiểm tra điều kiện (`gate-intake-screening.js`).
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào, API:
    - `GET /api/v1/workspace/database-gates`: danh mục cống trong PostgreSQL.
    - `GET /api/v1/workspace/database-gates/{gate_code}/candidate-stations`: các trạm ứng viên gần cống theo khoảng cách.
    - Gián tiếp `POST /api/v1/workspace/multivariate/predict`, qua `loadMultivariateForecastContext()`, để dự báo hai trạm còn lại cho cùng tháng.
  - Đầu vào, HTML (id): `gateSelect`, `gateInfo`, `databaseGateStatus`, `databaseGateList`, `loadDatabaseGates`, `gateContextStatus`, `gateIntakeScreeningHost`.
  - Đầu vào, sự kiện nghe:
    - `workspace:simulation-frame`: khung bản đồ tháng mới, chứa danh sách cống GIS.
    - `workspace:apply-simulation-gate`: người dùng chọn một cống trên bản đồ.
    - `workspace:apply-forecast-to-gate`: từ nút "Dùng dự báo để kiểm tra cống".
    - `workspace:active-forecast-context`.
  - Đầu ra: đổ danh sách vào ô chọn cống; gọi `map.setCandidates(...)` và `map.setGates(...)` để vẽ trạm ứng viên và cống trên bản đồ; chuyển trang về `#gates`.
- **Các hàm cốt lõi:**
  - `createGateDossiers(map)`: nhận đối tượng bản đồ từ `observations.js` (qua `workspace.js`) và trả về `{ load, destroy }`.
  - `rebuildOptions(preferred)`: trộn ba nguồn theo `gate_code`. Nếu hai nguồn cùng có một cống thì thông tin nguồn sau ghi đè nguồn trước. Nhãn cống ghi thêm " · PostgreSQL" hoặc " · GIS".
  - `selectGate()`: in thông tin cống. Nếu cống thuộc PostgreSQL, hàm gọi API trạm ứng viên. Nếu không có trạm trong bán kính 50 km, hàm báo "Chưa xác lập trạm đại diện cho cống". Khoảng cách gần **không** chứng minh có liên thông thủy lực.
  - `onMapGate(event)`: chỉ nhận cống từ bản đồ nếu `createSpatialGateDraft()` (tệp `gate-simulation-draft.js`) dựng được bản nháp hợp lệ.
  - `onForecast(event)`: lấy kết quả dự báo một trạm. Hàm gọi `loadMultivariateForecastContext()` (tệp `shared/forecast-map-overlay.js`) để chạy thêm hai trạm còn lại cùng tháng, rồi đưa ngữ cảnh cho `screening.setForecastContext()`. Câu trạng thái nhắc người dùng nhập số đo hiện trường ở Phần B.
  - `loadDatabaseGates()`: nút "đọc danh mục PostgreSQL".
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi cách gộp danh sách cống hoặc dòng mô tả cống thì sửa ở đây.
  - Có. Muốn đổi bán kính hoặc cách hiện trạm ứng viên thì xem `selectGate()`. Bán kính 50 km do backend quyết định.
  - Không. Muốn đổi luật "đạt hay không đạt" thì sang `frontend/src/shared/gate-intake-rules.js` và `backend/domain/gate_intake_rules.py`.

### `frontend/src/features/gate-forecast-context.js`

- **Vai trò trong đời sống:** Đây là "thước đo vị trí" của cống trên trục sông. Tệp xác định cống nằm ở km bao nhiêu tính từ Tân Châu, rồi nội suy EC dự báo tại vị trí đó từ ba con số dự báo của ba trạm. Kết quả chỉ là **ước tính hình học để sàng lọc**, không phải EC đo tại cống.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Tệp không gọi API và không đọc HTML. Đầu vào là ngữ cảnh dự báo, đối tượng cống và khung bản đồ hiện tại. Đầu ra là ngữ cảnh mới có thêm `projectedGateEc` và `projectionBasis`.
- **Các hàm cốt lõi:**
  - `projectForecastContextForGate(context, gate, baseFrame)`: hàm duy nhất của tệp. Các bước:
    1. Xóa các trường chiếu cũ.
    2. Tìm lý trình km của cống theo thứ tự: `gate.chainage_km`, rồi lý trình của cống trong khung bản đồ. Nếu vẫn chưa có, hàm tìm điểm gần nhất trên sông bằng `nearestRiverPoint()` và `haversineKm()` (tệp `features/point-inspection.js`) rồi tính km theo chiều dài đã đi trên đoạn sông.
    3. Nếu km nằm trong khoảng 0–175 và có EC Mỹ Tho, EC Tân Châu, hàm tính tỉ lệ = km ÷ km của Mỹ Tho (mặc định 125, lấy từ `assumptions.chainage_anchors_km[1]`). Tỉ lệ bị kẹp trong 0–1. Sau đó hàm gọi `interpolateStationEc()` (tệp `shared/river-interpolation.js`).
    4. Kết quả thành công gắn `projectionBasis = 'GEOMETRIC_AXIS_INTERPOLATION'`. Nếu không tính được thì `projectedGateEc = null` và `projectionBasis = 'STATION_FALLBACK_NO_PROJECTION'`.
  - Ví dụ: cống ở km 62,5, nên tỉ lệ = 62,5/125 = 0,5. Giả sử dự báo Tân Châu 20, Mỹ Thuận 40, Mỹ Tho 100 mS/m. Tỉ lệ 0,5 nằm trước Mỹ Thuận (0,6817), nên EC ≈ 20 + (40 − 20) × 0,5/0,6817 ≈ 34,7 mS/m. Cống ở km 150 vượt quá Mỹ Tho, nên tỉ lệ bị kẹp thành 1 và giữ EC Mỹ Tho là 100.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi cách tìm lý trình km của cống, hoặc giới hạn 175 km, thì sửa ở đây.
  - Không. Muốn đổi công thức nội suy giữa ba trạm thì sang `frontend/src/shared/river-interpolation.js`.

### `frontend/src/features/gate-intake-screening.js`

- **Vai trò trong đời sống:** Đây là "phiếu kiểm tra trước khi xem xét mở cống lấy nước". Phiếu có hai phần:
  - **Phần A** cho biết xu thế dự báo (mặn cao hay bình thường). Xu thế này chỉ quyết định số đo được "tươi" trong bao lâu.
  - **Phần B** là nơi người vận hành nhập **số đo thật tại cống**: EC hai phía, mực nước hai phía, giờ đo, người đo, tình trạng cơ khí. Phiếu chấm từng tiêu chí và đưa một trong ba kết luận: "Đề nghị xem xét lấy nước", "Chưa phù hợp", hoặc "Cần bổ sung/đo lại".

  Kết luận này **không phải lệnh mở cống**. Con người vẫn phải xem xét.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào, API: `POST /api/v1/gate-screening/evaluate`. Máy chủ chấm lại cùng phiếu để đối chiếu với kết quả của trình duyệt.
  - Đầu vào, HTML: khung `gateIntakeScreeningHost`, do `gate-dossiers.js` truyền vào. Tệp tự tạo các `id`: `gateIntakeForecastSummary`, `gateIntakeForm`, `gateIntakeConclusion`, `gateIntakeExpiry`, `gateIntakeServerStatus`, `gateIntakeCriteria`.
  - Đầu vào, người dùng:
    - EC ngoài sông và EC trong đồng (mS/m).
    - Mực nước ngoài và mực nước trong (m).
    - Thời điểm đo (GMT+7) và người đo.
    - Trạng thái cơ khí. Giao diện cho chọn READY, NOT_READY, MAINTENANCE, FAULT.
    - Ô tick "cùng hệ quy chiếu cao độ".
    - Mục "RuleProfile" để chỉnh ngưỡng. Nếu khác mặc định, phiên bản quy tắc được gắn thêm `+CUSTOM`.
  - Đầu vào, sự kiện nghe: `workspace:active-forecast-context`, `workspace:simulation-frame`. Ngoài ra, khi tab được xem lại (`visibilitychange`) hoặc cửa sổ được focus lại, phiếu tự chấm lại.
  - Đầu ra: bảng tiêu chí, kết luận, giờ hết hạn, trạng thái đối chiếu máy chủ, tệp `<mã cống>_intake_screening.json`. Nút tải chỉ mở khi máy chủ cho **cùng kết quả**.
- **Các hàm cốt lõi:**
  - `createGateIntakeScreening(host, { now, schedule, cancel, serverEvaluate, eventTarget, documentTarget })`: các tham số có giá trị mặc định là giờ thật, `setTimeout`, gọi API thật. Test thay chúng bằng bản giả để kiểm soát thời gian. Hàm trả về `{ setGate, setSpatialFrame, setForecastContext, evaluate, getResult, destroy }`.
  - `readProfile()`: đọc ngưỡng từ form bằng `gateMeasurementNumber()`, rồi kiểm tra bằng `validateGateRuleProfile()`. Cả hai hàm ở tệp `shared/gate-intake-rules.js`.
  - `gateContext()`: gọi `projectForecastContextForGate()` (tệp `gate-forecast-context.js`).
  - `renderForecast()`: vẽ Phần A dựa trên `deriveForecastAdvisoryForGate()`. Phần này ghi "Cảnh giác cao", "Chưa kích hoạt cảnh giác cao" hoặc "Chưa có ngữ cảnh dự báo", kèm ba con số Tân Châu, Mỹ Thuận, Mỹ Tho, và câu nhắc rằng EC tại vị trí chiếu chưa xác lập kết nối thủy lực.
  - `measurementInput()`: gom số đo. Giờ đo được ghép `+07:00`. Hàm gắn `dataKind: 'DECLARED_FIELD_MEASUREMENT'`.
  - `runEvaluation()`: các bước:
    1. Chấm ngay trên trình duyệt bằng `evaluateGateIntakeCondition()`.
    2. Gửi cùng phiếu lên máy chủ.
    3. So sánh trạng thái chung, danh sách `[id, status]` từng tiêu chí, và số giờ hiệu lực. Khớp thì báo "Máy chủ đã đối chiếu cùng kết quả". Lệch thì báo "Kết quả khác nhau" và khóa nút tải.
    4. Hẹn giờ tự chấm lại đúng lúc mẫu hết hạn. Ví dụ đo lúc 09:00, giới hạn 6 giờ, thì 15:00 phiếu tự chuyển sang "Cần bổ sung hoặc đo lại".
  - `invalidate(message)`: hễ người dùng sửa một ô là xóa kết luận cũ, buộc phải bấm kiểm tra lại.
  - `setGate(value)`: đổi cống thì xóa sạch số đo cũ.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi bố cục phiếu, thêm lựa chọn trạng thái cơ khí, hoặc đổi chữ Phần A và Phần B thì sửa ở đây.
  - Không. Muốn đổi ngưỡng mặc định (156,25 / 125 / 0,05 / 6 giờ / 2 giờ) hoặc luật chấm thì sang `frontend/src/shared/gate-intake-rules.js`, và phải sửa **cùng lúc** `backend/domain/gate_intake_rules.py`.

### `frontend/src/features/gate-simulation-draft.js`

- **Vai trò trong đời sống:** Đây là "mẫu hồ sơ nháp" cho một cống chọn từ bản đồ mô phỏng. Tệp điền sẵn EC phía ngoài cống bằng **EC mô phỏng** và để trống mọi ô cần đo thật (mực nước, giờ đo). Mọi trường đều gắn nhãn "mô phỏng, chưa xác minh", để không ai nhầm bản nháp là số đo thực.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Tệp không gọi API và không đọc HTML. Đầu vào là gói `detail` của sự kiện chọn cống trên bản đồ. Đầu ra là cặp đối tượng `{ input, policy }`, hoặc `null` nếu gói không hợp lệ. Tệp cũng chuyển tiếp (re-export) `DEFAULT_GATE_RULE_PROFILE`, `deriveForecastAdvisoryForGate`, `evaluateGateIntakeCondition` từ `shared/gate-intake-rules.js`.
- **Các hàm cốt lõi:**
  - `createSpatialGateDraft(detail)`: chỉ nhận gói khi `kind === 'SPATIAL_SIMULATION'`, có mã cống, EC mô phỏng không âm, và tháng hợp lệ. Nếu gói kèm khung bản đồ, EC của cống phải khớp với EC trong khung. Kết quả gồm:
    - `input`: `evaluation_mode: 'SIMULATION'`, `quality_flag: 'UNVERIFIED'`, `recommendation: null`, `actuator_command: null`, `requires_operator_review: true`. Trong bốn ô quan trắc, chỉ `outside_quality` có giá trị (EC mô phỏng); ba ô còn lại là `null`.
    - `policy`: `approval.status: 'DRAFT'`; ngưỡng `open_below` và `close_at_or_above` lấy từ ngưỡng của khung bản đồ.
  - `validateGateDraftPart(data, kind, code)`: kiểm một nửa hồ sơ (`input` hoặc `policy`). Các điều kiện: đúng mã cống; `schema_version` bằng 1; đơn vị `m` cho mực nước và `mS/m` cho EC; EC do người dùng sửa phải ghi nguồn `USER_SCENARIO:<mã cống>:<tháng>`; EC mô phỏng phải có `observed_at = null`.
  - `validateGateDraftPair(input, policy, code)`: kiểm cả hai nửa và yêu cầu nguồn mô phỏng của hai nửa khớp nhau.
  - `validForecastReference(forecast)`: dự báo tham khảo phải thuộc một trong ba trạm, với mã `MRC_VN_019805` (Mỹ Tho), `MRC_VN_019804` (Mỹ Thuận), `MRC_VN_019803` (Tân Châu); đơn vị `mS/m`; và không được tự nhận là quan trắc tại cống.
  - Hai hàm `validate...` và `validForecastReference` hiện chỉ được test gọi (`tests/gate_dossiers.test.mjs`), không được giao diện chính gọi.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi cấu trúc hồ sơ nháp hoặc các trường bắt buộc khi chọn cống từ bản đồ thì sửa ở đây.
  - Không. Muốn đổi cách tô màu chấm cống thì sang `frontend/src/features/observations-map.js`.

### `frontend/src/features/gate-simulation-draft.test.js`

- **Vai trò trong đời sống:** Đây là "bài kiểm tra tự động" cho tệp trên, giống người kiểm hàng thử từng món trước khi xuất kho. Chạy bằng trình chạy test có sẵn của Node (`node:test`).
- **Đọc/ghi dữ liệu ở đâu (I/O):** Tệp không gọi API và không đọc HTML. Đầu vào là dữ liệu giả viết ngay trong tệp. Đầu ra là kết quả đạt hoặc trượt.
- **Các hàm cốt lõi (hai ca kiểm tra):**
  - Ca 1, "giữ mã cống thật và nguồn mô phỏng". Cống giả `NEW-CATALOG-01` có EC mô phỏng 180, ngưỡng 120/150. Ca kiểm tra khẳng định:
    - EC ngoài bằng 180 và có cờ `UNVERIFIED`.
    - Mực nước, hệ cao độ và giờ đo đều `null`, dù gói gốc có ghi `outside_level: 5` và `vertical_datum: "OLD"`. Bản nháp không được chép số đo vận hành giả.
    - `actuator_command` và `recommendation` đều là `null`.
    - Ngưỡng 120/150 được chép đúng.
  - Ca 2, "gói hỏng hoặc kiểu cũ thì không tạo nháp". Gói thiếu `kind` hoặc có EC là `NaN` phải trả về `null`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Khi đổi cấu trúc hồ sơ nháp, phải cập nhật kỳ vọng trong tệp này.
  - Không. Phần lớn test khác của dự án nằm trong thư mục `tests/`, ví dụ `tests/gate_dossiers.test.mjs`. Tệp này nằm cạnh mã nguồn, nên lệnh `node --test tests/*.test.mjs` trong `CLAUDE.md` **không** tự chạy nó; phải chạy riêng `node --test frontend/src/features/gate-simulation-draft.test.js`.

---

### 2.D.2. Thư viện dùng chung (`frontend/src/shared/`)

Đây là "tủ đồ nghề chung" của cả trang: các hàm nhỏ, chủ yếu tính toán thuần (không vẽ, không gọi mạng). Tab nào cần thì mượn.

### `frontend/src/shared/workspace-api.js`

- **Vai trò trong đời sống:** Đây là "phong bì có in sẵn địa chỉ". Thay vì mỗi lần phải ghi `/workspace/...`, các tệp chỉ ghi phần sau.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Tệp không tự gọi gì. Nó bọc `requestJSON()` của `frontend/src/api.js`.
- **Các hàm cốt lõi:**
  - `workspaceAPI(path, options)`: gọi `requestJSON('/workspace' + path, options)`. Địa chỉ cuối cùng là `/api/v1/workspace` + `path`.
  - `artifactURL(id, name)`: tạo đường `/api/v1/workspace/artifacts/{id}/{name}` để tải tệp kết quả thí nghiệm. Cả hai phần đều được mã hóa an toàn bằng `encodeURIComponent`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Nếu backend đổi tiền tố `/workspace` thì sửa ở đây.
  - Không. Muốn đổi giờ chờ tối đa hoặc câu báo lỗi mạng thì sang `frontend/src/api.js`.

### `frontend/src/shared/ui.js`

- **Vai trò trong đời sống:** Đây là "hộp dụng cụ cầm tay" để thao tác giao diện: tìm phần tử, tạo phần tử, định dạng số kiểu Việt Nam, và tải tệp JSON/CSV về máy.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Tệp đọc DOM theo `id` và tạo tệp tải xuống. Nó không gọi API.
- **Các hàm cốt lõi:**
  - `$(id)`: viết tắt của `document.getElementById(id)`.
  - `num(v)`: định dạng số theo kiểu `vi-VN`, tối đa 3 chữ số thập phân. Ví dụ `1234.5` thành `1.234,5`. Giá trị không phải số thành `—`.
  - `node(tag, text, cls)`: tạo một phần tử HTML có chữ và lớp CSS.
  - `save(name, value, type)`: đóng gói nội dung thành tệp rồi bấm tải giùm người dùng.
  - `saveCSV(name, rows, keys)`: viết CSV. Có một bước bảo vệ: ô bắt đầu bằng `=`, `+`, `@`, `-` được thêm dấu `'` ở đầu, để Excel không hiểu nhầm thành công thức (chống "chèn công thức CSV"). Tệp có ký tự BOM để Excel đọc đúng tiếng Việt.
  - `sourceAnchor(source, text)`: tạo liên kết ra trang nguồn. Đường dẫn được kiểm bằng `safeExternalURL()` (tệp `frontend/src/research-utils.js`) và mở ở tab mới an toàn.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi số chữ số thập phân hiển thị chung, hoặc cách xuất CSV, thì sửa ở đây.
  - Không. Muốn đổi định dạng chỉ cho EC/g/L trên bản đồ thì sang `frontend/src/shared/simulation-display.js`.

### `frontend/src/shared/forecast-contract.js`

- **Vai trò trong đời sống:** Đây là "người gác cổng kiểm phiếu dự báo". Mọi kết quả dự báo trả về đều phải qua đây kiểm đúng tháng, đúng đơn vị và đúng biến đầu vào. Tệp cũng chứa quy tắc "dự báo tháng `t` dùng dữ liệu tháng `t−2`".
- **Đọc/ghi dữ liệu ở đâu (I/O):** Chỉ tính toán thuần, không gọi API, không đọc HTML.
- **Các hàm cốt lõi:**
  - `validMonth(value)`: kiểm chuỗi dạng `YYYY-MM`, tháng từ 01 đến 12, năm khác 0000. Ví dụ `'2026-13'` sai.
  - `validEc(value)`: kiểm EC là số hữu hạn và không âm.
  - `forecastMonthFromToday(offset, today)`: trả về tháng hiện tại cộng `offset`. Ví dụ hôm nay 17/11/2026, `offset = 1` cho `'2026-12'`.
  - `inputMonthFor(target)`: lùi 2 tháng. Ví dụ `'2026-03'` thành `'2026-01'`; `'2026-01'` thành `'2025-11'`.
  - `validPrediction(data, expected)`: kết quả dự báo hợp lệ khi:
    - Có trạm và `site_code`; đơn vị `mS/m`; EC không âm.
    - `input_month` đúng bằng `inputMonthFor(target_month)`.
    - `input_mode` là `ARCHIVE` hoặc `MANUAL`.
    - Có đúng một biến `rainfall_mm` (đơn vị `mm`), một `temperature_degC` (`degC`), một `wind_source_units` (`m/s`). Mưa và gió không âm.
    - Nếu là `MANUAL` thì giá trị phải đúng bằng số người dùng đã nhập.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Nếu đổi độ trễ đầu vào từ `t−2` sang mức khác, phải sửa `inputMonthFor()` ở đây, đồng thời sửa backend và mô hình.
  - Có. Nếu backend thêm biến khí tượng mới, phải cập nhật danh sách đơn vị trong `validPrediction()`.
  - Không. Muốn đổi cách hiện kết quả thì sang `frontend/src/features/multivariate-forecast.js`.

### `frontend/src/shared/forecast-map-overlay.js`

- **Vai trò trong đời sống:** Đây là "thợ tô màu dự báo lên sông". Đầu vào là ba con số EC dự báo tại ba trạm. Tệp nội suy dọc sông rồi tạo một **bản sao** của khung bản đồ có màu mới. Khung gốc (dữ liệu quan trắc) không bị đụng tới.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào, API: hàm `loadMultivariateForecastContext()` gọi `POST .../multivariate/predict` cho **hai trạm còn lại**. Hàm `api` được truyền vào; trong `gate-dossiers.js` đó là `workspaceAPI`, nên địa chỉ là `/api/v1/workspace/multivariate/predict`. Giờ chờ tối đa 120 giây.
  - Đầu ra, sự kiện: `workspace:active-forecast-context`, phát khi lớp phủ dự báo được bật hoặc tắt.
  - Đầu ra, biến dùng chung: `activeForecastContext`.
- **Các hàm và hằng cốt lõi:**
  - Hằng:
    - `DEFAULT_P90_MYTHO_MS_M = 60.42`: ngưỡng P90 mặc định của Mỹ Tho.
    - `EC_TO_SALINITY_GL_FACTOR = 0.0064`.
    - `DIRECT_FORECAST_MODEL = 'MULTIVARIATE_RF_5'` và `COMPACT_FORECAST_MODEL = 'RF_compact'`.
    - Các câu mô tả `DIRECT_FORECAST_SUBTITLE`, `COMPACT_FORECAST_SUBTITLE`, `FORECAST_SPATIAL_DISCLAIMER`.
  - `forecastModelLabel(sourceModel)`: trả về tên tiếng Việt của mô hình.
  - `normalizeForecastContext(context)`:
    - Bắt buộc có tháng hợp lệ, EC Mỹ Tho và EC Tân Châu.
    - Cần cả EC Mỹ Thuận. Ngoại lệ duy nhất: tháng trước `2024-01`, Mỹ Thuận là `null`, và chế độ là `TWO_STATION_FALLBACK_MISSING_MYTHUAN`; khi đó cho phép nội suy hai trạm.
    - Gắn `isHighVigilance = mythoEc >= p90Threshold`. Ví dụ Mỹ Tho 70 ≥ 60,42 thì bật "cảnh giác cao".
  - `loadMultivariateForecastContext(prediction, api, request)`: từ một dự báo (ví dụ Mỹ Tho), hàm chạy thêm Mỹ Thuận và Tân Châu với **cùng tháng và cùng chế độ đầu vào**. Nếu là `MANUAL` thì dùng cùng ba số khí tượng. Kết quả của hai trạm này không được lưu. Hàm ghép lại thành ngữ cảnh có `tanchauBasis: 'MODEL_PREDICTION'`.
  - `buildForecastOverlayFrame(baseFrame, forecastContext)`:
    - Sao chép khung bản đồ bằng `structuredClone`.
    - Với từng đoạn sông, hàm tính EC ở đầu, cuối và giữa đoạn bằng `interpolateStationEc()`. Nếu đoạn sông có đi qua Mỹ Thuận thì thêm một "điểm dừng màu" (`ec_stops`) đúng vị trí Mỹ Thuận.
    - Hàm ghi `salinity_g_l = EC × 0,0064`, chỉ để tham khảo.
    - Các đoạn sau Mỹ Tho (km 125 đến 175, phía cửa sông) giữ EC của Mỹ Tho.
    - Hàm **xóa danh sách cống, ranh giới đẳng mặn và điều kiện biên** trong bản sao. Lý do: trạng thái cống cũ không còn khớp với EC mới.
  - `createForecastMapBridge({ onFrame, onContext, onError, eventTarget })`: "cầu nối" giữa dự báo và bản đồ, có các lệnh `setBaseFrame`, `apply`, `clear`. Nếu dựng lớp phủ bị lỗi, cầu tự quay về khung gốc và báo lỗi.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi ngưỡng P90 mặc định, hoặc cách tô dự báo lên sông, thì sửa ở đây.
  - Có. Muốn đổi điều kiện cho phép nội suy hai trạm khi thiếu Mỹ Thuận thì xem `normalizeForecastContext()`.
  - Không. Muốn đổi công thức nội suy giữa các trạm thì sang `frontend/src/shared/river-interpolation.js`. Muốn đổi cách vẽ đường sông thì sang `frontend/src/features/observations-map.js`.

### `frontend/src/shared/river-interpolation.js`

- **Vai trò trong đời sống:** Đây là "cây thước kẻ nối ba cái cọc". Tân Châu là cọc ở vị trí 0, Mỹ Thuận ở 0,68174084 (km 85,217605), Mỹ Tho ở 1. Muốn biết EC ở giữa thì kẻ đường thẳng giữa hai cọc liền kề. Đây là nội suy **tuyến tính từng chặng**, không phải mô hình lan truyền mặn.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Chỉ tính toán thuần.
- **Các hàm và hằng cốt lõi:**
  - Hằng `MY_THUAN_RATIO`, `MY_THUAN_KM`, `THREE_STATION_MODE = 'PIECEWISE_3_STATION'`, `TWO_STATION_MODE = 'TWO_STATION_FALLBACK_MISSING_MYTHUAN'`.
  - `interpolateStationEc(ratio, context)`: tỉ lệ được kẹp trong 0–1.
    - Có Mỹ Thuận: nội suy hai chặng. Ví dụ Tân Châu 20, Mỹ Thuận 40, Mỹ Tho 100. Ở tỉ lệ 0,34: 20 + 20 × 0,34/0,6817 ≈ 30. Ở tỉ lệ 0,84: 40 + 60 × (0,84 − 0,6817)/(1 − 0,6817) ≈ 69,8.
    - Thiếu Mỹ Thuận: chỉ cho phép khi đúng chế độ hai trạm và tháng trước `2024-01`. Khi đó kẻ thẳng từ Tân Châu tới Mỹ Tho. Mọi trường hợp khác báo lỗi "Thiếu điểm neo dự báo Mỹ Thuận".
  - `segmentEcAt(properties, fraction)`: tìm EC tại một điểm nằm giữa một đoạn sông, dựa trên các điểm dừng `ec_stops`. Nếu đoạn không có `ec_stops` thì nội suy giữa EC đầu và EC cuối đoạn.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi vị trí Mỹ Thuận hoặc luật cho phép nội suy hai trạm phía giao diện thì sửa ở đây.
  - Không, hoặc chưa đủ. Bản đồ quan trắc theo tháng do backend nội suy ở `backend/domain/river_interpolation.py`; sửa một bên phải sửa đồng bộ bên kia.

### `frontend/src/shared/gate-intake-rules.js`

- **Vai trò trong đời sống:** Đây là "bộ luật chấm phiếu kiểm tra cống", viết dưới dạng hàm thuần. Cùng một đầu vào luôn ra cùng kết quả. Thời điểm "bây giờ" do bên gọi truyền vào, nên test và máy chủ có thể tái lập đúng kết quả.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Chỉ tính toán thuần. Tệp được dùng bởi `gate-intake-screening.js`, `gate-forecast-context.js`, `gate-simulation-draft.js`.
- **Bản song song ở backend:** `backend/domain/gate_intake_rules.py` (hàm `evaluate`) chứa **cùng bộ luật** cho máy chủ, chạy qua `POST /api/v1/gate-screening/evaluate` (tệp `backend/api/gate_screening.py`). Hai bên dùng cùng `DEFAULT_PROFILE` (156.25, 125, 0.05, 6, 2, 60.42), cùng ba tiêu đề trạng thái, cùng biểu thức kiểm số và kiểm giờ. Có hai bộ test cùng đọc chung tệp `tests/fixtures/gate_intake_cases.json` để bảo đảm hai bên cho cùng kết luận:
  - `tests/gate_intake_parity.test.mjs` (phía JavaScript): mỗi ca phải ra đúng `expected`, kèm `requiresOperatorReview === true` và `actuatorCommand === null`.
  - `tests/test_gate_intake_rules.py` (phía Python).

  Ngoài ra, ngay lúc chạy, giao diện còn so kết quả của mình với kết quả máy chủ (xem `gate-intake-screening.js`). Bản Python có thêm vài trường mà bản JS không có, ví dụ `rule_profile_hash` và `input_hash`. **Sửa luật ở bên nào phải sửa cả bên kia, và cập nhật fixture.**
- **Các hàm và hằng cốt lõi:**
  - `DEFAULT_GATE_RULE_PROFILE`, cấu hình mặc định, đã bị "đóng băng" (`Object.freeze`) để không bị sửa nhầm:
    - EC ngoài tối đa 156,25 mS/m (≈ 1 g/L theo quy đổi 0,0064).
    - EC trong tối đa 125 mS/m.
    - Chênh mực nước ngoài − trong tối thiểu 0,05 m.
    - Bắt buộc cùng hệ cao độ; bắt buộc cơ khí `READY`.
    - Mẫu đo còn hiệu lực 6 giờ khi bình thường, 2 giờ khi cảnh giác cao.
    - P90 tham chiếu 60,42 mS/m.
    - Tên quy tắc ghi rõ đây là "Quy tắc kỹ thuật cấu hình ... (không thay thế quy trình vận hành pháp lý ...)".
  - `GATE_INTAKE_STATUS_TITLES`: `ELIGIBLE_FOR_REVIEW` là "Đề nghị xem xét lấy nước"; `NOT_SUITABLE` là "Chưa phù hợp để lấy nước"; `INSUFFICIENT_OR_EXPIRED_DATA` là "Cần bổ sung hoặc đo lại".
  - `gateMeasurementNumber(value)`: nhận số hoặc chuỗi số (ví dụ `"1.05"`). Ô trống, `null`, `true`/`false` hay mảng **không** bị đổi thành 0 mà trả về `null`. Nhờ vậy ô bỏ trống không bị hiểu là "EC = 0".
  - `gateTimestampMs(value)`: chỉ nhận thời điểm ISO **có múi giờ** và là ngày có thật. Ví dụ `2026-02-30T08:00+07:00` bị loại vì tháng 2 không có ngày 30.
  - `validateGateRuleProfile(profile)`: kiểm cấu hình. Các ngưỡng phải là số không âm. Hạn mẫu cảnh giác cao không được dài hơn hạn bình thường. `requireSameDatum` phải là `true`.
  - `deriveForecastAdvisoryForGate(forecastContext, ruleProfile)`: quyết định "cảnh giác cao" khi gặp **một trong ba** điều kiện:
    1. Dự báo Mỹ Tho ≥ P90. Ví dụ 70 ≥ 60,42.
    2. EC chiếu tại cống ≥ 80% ngưỡng EC ngoài, tức 0,8 × 156,25 = 125. Ví dụ chiếu ra 130 thì đạt điều kiện. Nếu không có vị trí chiếu, hàm tạm lấy EC Mỹ Tho.
    3. Ngữ cảnh mô hình đã tự bật cờ `isHighVigilance`.

    Khi cảnh giác cao, hạn mẫu đo rút từ 6 xuống 2 giờ. **Dự báo chỉ làm thay đổi hạn mẫu đo, không thay số đo.**
  - `evaluateGateIntakeCondition(input, ruleProfile, forecastContext, evaluationTimeIso)`: chấm 6 tiêu chí, có thể thêm tiêu chí thứ 7:
    1. `SAMPLE_FRESHNESS`: mẫu còn hạn.
    2. `EXTERIOR_EC`: EC ngoài ≤ 156,25.
    3. `INTERIOR_EC`: EC trong ≤ 125.
    4. `ELEVATION_DATUM`: đã tick "cùng hệ cao độ".
    5. `HYDRAULIC_HEAD_DIFF`: ΔH = mực ngoài − mực trong, phải > 0 và ≥ 0,05 m. Có một dung sai cực nhỏ để phép trừ máy tính kiểu 1,05 − 1 không bị trượt oan.
    6. `MECHANICAL_READINESS`: cơ khí `READY`.
    7. `MEASUREMENT_PROVENANCE`: có ghi người đo hoặc nguồn.
    8. Nếu dữ liệu là `SIMULATION` hoặc ghi `gateObservation: false`, hàm thêm tiêu chí `FIELD_MEASUREMENT` ở trạng thái "thiếu". Nghĩa là EC mô phỏng hoặc dự báo **không bao giờ** được tính là số đo tại cống.

    Luật kết luận: có bất kỳ tiêu chí "thiếu/hết hạn" nào thì kết luận là `INSUFFICIENT_OR_EXPIRED_DATA` (ưu tiên trước). Nếu không thiếu mà có tiêu chí "không đạt" thì là `NOT_SUITABLE`. Đạt hết thì là `ELIGIBLE_FOR_REVIEW`, kèm `validUntilIso` = giờ đo + hạn mẫu.

    Ví dụ, theo fixture: đánh giá lúc 10:00, mẫu đo lúc 09:00, EC ngoài 80, EC trong 60, mực nước 1,15 và 1,00 (ΔH = 0,15), `READY`, có người đo. Kết quả là "Đề nghị xem xét lấy nước", hiệu lực đến 15:00. Đổi EC ngoài thành 200 thì ra "Chưa phù hợp". Nếu đang cảnh giác cao (hạn 2 giờ) mà mẫu đã 3 giờ tuổi thì ra "Cần bổ sung hoặc đo lại".

    Mọi kết quả đều có `requiresOperatorReview: true` và `actuatorCommand: null`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi ngưỡng mặc định, thêm tiêu chí, hoặc đổi luật cảnh giác cao thì sửa ở đây, **và** sửa `backend/domain/gate_intake_rules.py`, **và** cập nhật `tests/fixtures/gate_intake_cases.json`.
  - Không. Muốn đổi chữ hay bố cục phiếu thì sang `frontend/src/features/gate-intake-screening.js`.

### `frontend/src/shared/water-advisory.js`

- **Vai trò trong đời sống:** Đây là "bảng tra minh họa theo cây trồng". Với một con số EC, bảng cho biết con số đó nằm dưới, trong vùng chuyển tiếp, hay trên ngưỡng của từng kịch bản. Các ngưỡng là **minh họa**, chưa phải tiêu chuẩn tưới đã kiểm chứng.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Chỉ tính toán thuần. Tệp được dùng bởi `multivariate-forecast.js`, `observations-map.js`, `timeline-scrubber.js`.
- **Các hàm và hằng cốt lõi:**
  - `ADVISORY_PRESETS`: sầu riêng 50/80; cây có múi 100/150; lúa 120/200 (mS/m, ngưỡng thấp/cao).
  - `cropAdvisories(ec)`: với mỗi cây, phân loại:
    - `below` khi EC < ngưỡng thấp.
    - `transition` khi ngưỡng thấp ≤ EC < ngưỡng cao.
    - `above` khi EC ≥ ngưỡng cao.
    - `missing` khi EC không hợp lệ.

    Ví dụ EC = 90: sầu riêng `above` (90 ≥ 80), cây có múi `below` (90 < 100), lúa `below`. Mọi câu chữ đều nhắc "vẫn cần đo kiểm tại nơi lấy nước".
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi ngưỡng minh họa của cây trồng hoặc thêm cây mới thì sửa ở đây, và chạy `tests/water_advisory.test.mjs`.
  - Không. Ngưỡng mẫu lấy từ cơ sở dữ liệu là việc của `frontend/src/shared/threshold-presets.js`.

### `frontend/src/shared/threshold-presets.js`

- **Vai trò trong đời sống:** Đây là "danh mục ngưỡng tham khảo" lấy từ máy chủ, để người dùng chọn nhanh thay vì tự gõ. Mỗi mẫu đều ghi nguồn và trạng thái minh chứng, và ghi rõ không phải quy tắc vận hành đã phê duyệt.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào, API: `GET /api/v1/workspace/threshold-presets`, chỉ gọi một lần rồi nhớ kết quả.
  - Đầu ra: đổ các lựa chọn vào một ô `<select>` do bên gọi đưa vào (`observations.js`).
- **Các hàm cốt lõi:**
  - `loadThresholdPresets()`: tải danh mục và giữ lại để dùng chung. Nếu lỗi, hàm xóa bản nhớ để lần sau thử tải lại.
  - `populateThresholdPresets(select, presets, kind)`: với `kind === 'gate'`, mẫu phải có `stop_intake_from_ms_m` > `allow_intake_below_ms_m`. Ví dụ "lấy khi EC < 100; ngừng khi EC ≥ 150". Mẫu sai thứ tự bị bỏ qua. Với loại thường, hàm chỉ dùng `threshold_ms_m`.
  - `presetReference(preset)`: viết câu nguồn và trạng thái minh chứng, ví dụ "... trạng thái minh chứng: chưa xác minh. Mẫu đối chiếu tham khảo, không phải quy tắc vận hành được phê duyệt."
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi cách hiện tên mẫu ngưỡng trong ô chọn thì sửa ở đây.
  - Không. Muốn thêm hoặc sửa mẫu ngưỡng thì sửa dữ liệu phía backend (`backend/api/dss_storage.py` và `backend/repositories/dss_storage.py`, `sql/`).

### `frontend/src/shared/ec-scenario.js`

- **Vai trò trong đời sống:** Đây là "vạch kẻ do người dùng tự đặt". Người dùng nhập một ngưỡng EC, ví dụ 120 mS/m cho mục đích "tưới lúa". Vạch này hiện trên các biểu đồ và bản đồ, và được nhớ lại lần sau mở trang.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào: `localStorage` khóa `workspace.ec-comparison.v1`.
  - Đầu ra: ghi lại vào `localStorage`; phát sự kiện `workspace:ec-comparison`, được `forecasts.js`, `observations.js`, `observations-map.js` nghe.
- **Các hàm cốt lõi:**
  - `ecComparison()`: trả về ngưỡng đang đặt, hoặc `null`.
  - `setECComparison(value)`: ngưỡng phải > 0, nếu không thì báo "Ngưỡng EC phải là số lớn hơn 0 mS/m.". Truyền `null` thì xóa ngưỡng. Nếu trình duyệt chặn bộ nhớ, ngưỡng vẫn dùng được trong phiên hiện tại.
  - `comparisonLines()`: trả về danh sách vạch để vẽ, ví dụ `{ value: 120, label: 'Tưới lúa: 120 mS/m', color: '#bc6430' }`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi màu hoặc nhãn của vạch ngưỡng tự nhập thì sửa ở đây.
  - Không. Muốn đổi ô nhập ngưỡng trên giao diện thì sang `frontend/src/features/observations.js`.

### `frontend/src/shared/observation-contract.js`

- **Vai trò trong đời sống:** Đây là "người kiểm phiếu số đo trạm". Trước khi vẽ lịch sử EC của một trạm, mọi mẫu đều phải đúng trạm, đúng ngày, đúng đơn vị và có nguồn rõ ràng.
- **Đọc/ghi dữ liệu ở đâu (I/O):**
  - Đầu vào, API: `GET /api/v1/workspace/stations/{site_code}/observations`.
  - Đầu ra: gọi `onResult(data)` hoặc `onError(error)`. Bên gọi là `observations.js`.
- **Các hàm cốt lõi:**
  - `validateObservations(data, siteCode)`. Từng mẫu phải có:
    - Ngày thật dạng `YYYY-MM-DD`; EC không âm; `source_id` và `source_locator`.
    - `time_precision` là `DATE_ONLY` (nguồn chỉ ghi ngày) hoặc `SOURCE_TIMESTAMP`.
    - Mẫu `DATE_ONLY` **không được** có giờ, vì nguồn chỉ ghi ngày và dấu `00:00` không phải giờ lấy mẫu thật.
    - Mẫu `SOURCE_TIMESTAMP` phải có múi giờ, và ngày của nó tính theo giờ Việt Nam phải khớp `observed_date`.
    - `observed_or_estimated`, nếu có, là `O` (đo) hoặc `E` (ước tính).
  - `createObservationLoader({ api, onResult, onError })`: trả về `{ load, cancel }`. Hàm dùng request gate để bỏ câu trả lời cũ và bỏ qua lỗi "đã hủy".
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn nới hoặc siết điều kiện nhận mẫu EC trạm thì sửa ở đây, và chạy `tests/observations_contract.test.mjs`.
  - Không. Muốn đổi nguồn đọc PostgreSQL hay snapshot thì sang `backend/repositories/workspace.py`.

### `frontend/src/shared/simulation-display.js`

- **Vai trò trong đời sống:** Đây là "bảng màu và cách ghi số" của bản đồ: EC thì ghi đơn vị nào, quy đổi g/L ghi thế nào, và mức EC thành màu gì.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Chỉ tính toán thuần. Tệp được dùng bởi `observations-map.js`, `observations.js`, `river-profile.js`, `timeline-scrubber.js`.
- **Các hàm cốt lõi:**
  - `formatWater(ec, unit, salinity)`: chế độ EC ghi ví dụ "100 mS/m". Chế độ `salinity` ghi "0,64 g/L (ước tính; 100 mS/m)", luôn kèm EC gốc và chữ "ước tính".
  - `salinityColor(ec)`: đổi EC sang g/L ước tính (× 0,0064), rồi pha màu giữa các mốc 0, 1, 4, 6, 8 g/L, từ xanh lơ qua xanh lá, vàng cam, đỏ, tới đỏ sẫm. Ví dụ EC 100 cho 0,64 g/L, màu nằm giữa xanh lơ và xanh lá. Hàm này chỉ tô màu theo thang quy đổi tham khảo.
  - `advisoryColor(gate)`: màu chấm cống. Lấy theo `advisory_color` (`green`, `amber`, hoặc mã màu) hoặc theo trạng thái mô phỏng (`OPEN_INTAKE` cho xanh, `CAUTION_TRANSITION` cho vàng, còn lại đỏ). Màu chấm phản ánh mức cảnh báo EC của tháng, **không** phản ánh cống đang đóng hay mở thật.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi bảng màu sông hay chấm cống, hoặc cách ghi g/L, thì sửa ở đây, và chạy `tests/simulation_display.test.mjs`.
  - Không. Muốn đổi mức cảnh báo EC do backend gán cho cống thì sang `backend/services/spatial_simulation.py`.

### `frontend/src/shared/time-series.js`

- **Vai trò trong đời sống:** Đây là "cây bút vẽ biểu đồ đường" dùng chung, tự vẽ bằng SVG (hình vẽ dạng vector trong trang web), không dùng thư viện biểu đồ ngoài.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Tệp vẽ vào phần tử `container` do bên gọi đưa vào, không gọi API. Được dùng bởi `forecasts.js`, `multivariate-forecast.js`, `observations.js`, và mượn lại qua `frontend/src/research-chart.js`.
- **Các hàm cốt lõi:**
  - `drawSeries(container, series, { title, connected, referenceLines, monthTicks, highlightDate })`:
    - Trục ngang là ngày. Hàm dùng UTC chỉ để tính vị trí điểm, **không** bịa ra giờ lấy mẫu.
    - Trục đứng là mS/m, chia 4 nấc tròn số.
    - Có vạch ngưỡng nét đứt (`referenceLines`).
    - Khi `connected` bật, hàm chỉ nối hai điểm liền tháng. Tháng bị thiếu tạo ra một khoảng hở, không vẽ đường nối giả.
    - Điểm ở tháng `highlightDate` của **chuỗi thứ hai** (thường là chuỗi mô hình) được vẽ to hơn, viền đỏ.
    - Rê chuột vào điểm sẽ hiện "tên chuỗi · ngày · giá trị mS/m".
    - Không có dữ liệu thì ghi "Không có số đo trong khoảng đã chọn.".
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi kích thước, màu lưới, hoặc cách nối đường của mọi biểu đồ EC thì sửa ở đây.
  - Không. Muốn đổi dữ liệu hay màu của một biểu đồ cụ thể thì sửa ở tệp tính năng gọi nó (ví dụ `forecasts.js`).

### `frontend/src/shared/timeline-months.js`

- **Vai trò trong đời sống:** Đây là "người dẫn đường trên thanh thời gian". Người dùng kéo tới một tháng mà máy chủ không có dữ liệu thì tệp đưa về tháng có dữ liệu gần nhất trước đó, và cho biết tháng đó thuộc giai đoạn quan trắc MRC hay giai đoạn ước tính.
- **Đọc/ghi dữ liệu ở đâu (I/O):** Chỉ tính toán thuần. Bên gọi là `timeline-scrubber.js`.
- **Các hàm cốt lõi:**
  - `HISTORICAL_CUTOFF_MONTH = '2023-12'`.
  - `resolveValidTimelineMonth(requestedMonth, availableMonths)`: ví dụ yêu cầu `'2024-05'` trong danh sách `['2024-01','2024-03','2024-07']` cho kết quả `'2024-03'`, `clamped: true`. Vì sau 2023-12, nhãn là `EXTENDED_METEOROLOGICAL_ESTIMATE` ("Chuỗi ước tính khí tượng mở rộng (chưa phải quan trắc MRC)"). Tháng ≤ 2023-12 có nhãn `HISTORICAL_MRC_OBSERVED`. Danh sách rỗng cho `NO_DATA`.
- **Muốn sửa … thì có tìm đến file này không?:**
  - Có. Muốn đổi mốc tách "quan trắc lịch sử" và "ước tính" (hiện là 2023-12) thì sửa ở đây, và chạy `tests/timeline_months.test.mjs`.
  - Không. Muốn đổi giao diện thanh kéo thì sang `frontend/src/features/timeline-scrubber.js`.

---

### 2.D.3. Tóm tắt: luồng "dự báo đến cống" để trình bày khi bảo vệ

1. `multivariate-forecast.js` gửi `POST /multivariate/history` (hoặc `/predict`), nhận EC dự báo tại một trạm, kiểm bằng `forecast-contract.js`.
2. Người dùng bấm "Dùng dự báo để kiểm tra cống". Sự kiện `workspace:apply-forecast-to-gate` tới `gate-dossiers.js`.
3. `gate-dossiers.js` gọi `loadMultivariateForecastContext()` (tệp `forecast-map-overlay.js`) để dự báo thêm hai trạm còn lại, cùng tháng, cùng đầu vào.
4. `gate-intake-screening.js` nhận ngữ cảnh. `gate-forecast-context.js` chiếu cống lên trục sông. `river-interpolation.js` nội suy EC tại vị trí chiếu.
5. `gate-intake-rules.js` quyết định có "cảnh giác cao" không, và hạn mẫu đo là 6 hay 2 giờ.
6. Người vận hành nhập **số đo thật** ở Phần B. Hệ thống chấm trên trình duyệt và đối chiếu với `backend/domain/gate_intake_rules.py`. Kết luận chỉ là đề nghị xem xét, không phát lệnh cống.

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

## 2.G. Những điểm dễ bị hỏi vặn (phát hiện khi đọc mã ngày 17/11/2026)

Các điểm dưới đây đã được đối chiếu với mã. Chúng không phải lỗi phải sửa ngay, nhưng nên biết để trả lời đúng khi hội đồng hỏi.

1. **Một hàm, nhiều địa chỉ.** Bộ API dự báo được gắn hai lần: `/api/v1/multivariate/...` và `/api/v1/workspace/multivariate/...`. Giao diện dùng đường `/workspace`. Toàn bộ API workspace còn được gắn lại dưới `/api/v1/research/...` (qua `backend/research.py`) để giữ đường cũ.
2. **Tên `_idw()` là tên cũ.** Trong `backend/services/spatial_simulation.py`, `_idw()` không còn là IDW (nghịch đảo khoảng cách) mà chỉ gọi `interpolate_anchors()` = nội suy tuyến tính từng chặng.
3. **Nhãn `OPEN_INTAKE` / `CLOSED_SALINITY_BARRIER` của `gate_state()` chỉ là mức màu EC** (ngưỡng mặc định 120/150 mS/m), không phải trạng thái cống thật, không phải lệnh.
4. **Phía ngoài Mỹ Tho (km 175) là biên giả định chưa hiệu chuẩn:** EC Mỹ Tho × 6,0 vào mùa khô (tháng 12–4) hoặc × 1,5 các tháng khác, cộng 0,4 × max(0, Mỹ Tho − Tân Châu).
5. **Luật rà soát cống có hai bản giống nhau:** `backend/domain/gate_intake_rules.py` và `frontend/src/shared/gate-intake-rules.js`. Ngưỡng: EC ngoài ≤ 156,25; EC trong ≤ 125 mS/m; tuổi mẫu ≤ 6 giờ (≤ 2 giờ khi cảnh giác cao). Sửa một bản phải sửa bản kia; test `tests/gate_intake_parity.test.mjs` và `tests/test_gate_intake_rules.py` cùng đọc `tests/fixtures/gate_intake_cases.json`.
6. **Trạng thái đúng hạn/trễ hạn của sổ phát hành** do trigger PostgreSQL `forecast_issue_guard` tự đóng dấu, không do Python quyết.
7. **`data_freshness.py` ghi cứng EC Mỹ Tho cuối cùng là 12/2023 (STALE).** Khi có EC mới phải sửa tay.
8. **Mã giao diện cũ:** `frontend/src/main.js`, `map.js`, `style.css` không được trang nào nạp; `index.html`, `research.html` chỉ chuyển hướng sang `workspace.html`.
9. **Script/công cụ có thể ghi đè mô hình đang phục vụ:** `scripts/train_mytho_hydrology_primary.py` (ghi mục `MYTHO` trong registry), `scripts/integrate_mythuan.py`, và `tools/model_training.py --apply` (thay toàn bộ registry bằng mô hình chỉ khí tượng). Không chạy khi chỉ muốn khởi động web.
10. **`scripts/forecast_mytho_ec_hydrology.py` không dùng mô hình đang phục vụ;** nó tự huấn luyện một Random Forest khác (100 cây, sâu 7) cho nghiên cứu.
11. **Thư mục `tools/` chưa commit vào Git**, trong khi 33 script trong `scripts/` import từ nó (kể cả script huấn luyện mô hình chính). Một bản clone sạch sẽ thiếu `tools/` cho tới khi nó được commit.
12. **Test nằm lạc chỗ:** `frontend/src/features/gate-simulation-draft.test.js` không được lệnh `node --test tests/*.test.mjs` chạy.
13. **CLAUDE.md mục 11 còn nhắc `scripts/backtest_asof_ec.py`**, tệp này đã bị xóa khỏi đĩa (chưa commit); quy tắc as-of nay nằm ở `tools/backtest_protocols.py`.

## Phụ lục A. Bảng tra nhanh: muốn sửa X thì mở file nào

| Muốn sửa / cần trả lời | Mở file (theo thứ tự) |
| --- | --- |
| Trang web không chạy, đổi cổng, đổi chế độ postgres/snapshot | `start.ps1` → `run_webgis.py` → `backend/main.py` |
| Thêm/sửa một đường dẫn API | `backend/api/<nhóm>.py`; tiền tố gắn ở `backend/main.py` (`include_router`) |
| Đổi chữ, nút, bố cục một tab | `frontend/workspace.html` → file `frontend/src/features/` tương ứng → CSS trong `frontend/src/app/` |
| Chuyển tab, dấu `#` trên URL | `frontend/src/app/navigation.js`, `frontend/src/app/workspace.js` |
| Danh sách trạm, lịch sử EC đo | `backend/repositories/workspace.py`, `backend/services/workspace.py`, `frontend/src/features/observations.js`, `database-history.js` |
| Màu sông, cách nội suy EC dọc sông | `backend/domain/river_interpolation.py` (công thức), `backend/services/spatial_simulation.py` (dựng khung), `backend/services/spatial_inputs.py` (lấy số 3 trạm) |
| Ngưỡng màu cống 120/150 mS/m mặc định | `gate_state()` trong `backend/services/spatial_simulation.py`; bộ ngưỡng chọn sẵn ở `frontend/src/shared/threshold-presets.js` |
| Vẽ chấm cống, nhãn trạm, chú giải bản đồ | `frontend/src/features/observations-map.js`, `gated-waterways.js`, `frontend/src/styles/simulation.css` |
| Thanh kéo tháng | `frontend/src/features/timeline-scrubber.js`; API `/api/v1/workspace/simulation/timeline` và `/simulation/frame` |
| Kết quả dự báo EC, đổi mô hình | `data/models/multivariate_registry.json` → `backend/domain/multivariate_ec.py` → `backend/services/multivariate.py` |
| Đầu vào khí tượng / thủy văn của dự báo | `backend/repositories/multivariate_inputs.py`, `backend/repositories/hydrology_inputs.py` |
| Huấn luyện lại mô hình Mỹ Tho | `scripts/train_mytho_hydrology_primary.py` (ghi artifact mới; không chạy khi chỉ khởi động web) |
| Biểu đồ hồi cứu, so sánh mô hình | `frontend/src/features/forecasts.js`, `backend/services/forecasts.py`, `backend/domain/ec_gap_*.py` |
| Hồ sơ cống, điều kiện lấy nước | `frontend/src/features/gate-*.js`, `frontend/src/shared/gate-intake-rules.js`, `backend/domain/gate_intake_rules.py`, `backend/domain/gates.py` |
| Lưu lịch sử dự báo, bản nháp cống vào DB | `backend/api/dss_storage.py` → `backend/services/dss_storage.py` → `backend/repositories/dss_storage.py`; bảng tạo bởi `sql/30_dss_storage.sql` |
| Quyền tài khoản DB, khóa API | `backend/security.py`, `backend/db_security.py`, `sql/31_database_security.sql`, `tools/security_setup.py` |
| Phiếu EC thực địa | `frontend/src/features/field-measurements.js` → `backend/api/field_measurements.py` → `services/` → `repositories/field_measurements.py`; bảng `sql/35_field_measurement.sql` |
| Sổ phát hành dự báo tháng | `forecast-issue-panel.js` → `backend/api/forecast_issues.py` → `services/forecast_issues.py`; bảng `sql/33_forecast_issue.sql` |
| Tab Chất lượng dữ liệu | `frontend/src/intake.js`, `weather-estimates.js`, `backend/intake.py` |
| Chạy test sau khi sửa | `tests/` (xem mục 2.E) |

## Phụ lục B. Từ điển thuật ngữ bằng lời thường

| Từ | Nghĩa đời thường |
| --- | --- |
| Frontend | Phần chạy trong trình duyệt: những gì người dùng nhìn và bấm. |
| Backend | Phần chạy trên máy chủ: tính toán, đọc kho dữ liệu, trả kết quả. |
| API / endpoint | Một "ô cửa" có địa chỉ riêng (ví dụ `/api/v1/workspace/multivariate/predict`). Frontend gõ cửa, backend trả lời bằng JSON. |
| GET / POST | GET = "cho tôi xem"; POST = "tôi gửi thông tin cho anh xử lý/lưu". |
| JSON | Cách viết dữ liệu dạng `{"tên": giá trị}` mà cả JavaScript và Python đều đọc được. |
| Router | Cuốn sổ ghi "địa chỉ cửa nào thì gọi hàm nào". |
| FastAPI | Thư viện Python giúp dựng các ô cửa API nhanh. |
| Hàm (function) | Một công thức có tên: đưa nguyên liệu vào (tham số), nhận món ra (giá trị trả về). |
| Module / import | Mỗi file là một ngăn tủ; `import` là mượn công cụ từ ngăn tủ khác. |
| Sự kiện (event) | Một tiếng chuông báo: "người dùng vừa bấm", "dự báo vừa xong"; ai đăng ký nghe thì phản ứng. |
| fetch | Lệnh của trình duyệt để gửi thư tới một ô cửa API và chờ thư trả lời. |
| PostgreSQL / PostGIS | Kho dữ liệu dạng bảng; PostGIS là phần thêm để lưu tọa độ, đường, vùng. |
| Bảng / view / role | Bảng = sổ ghi chép; view = trang sổ được lọc sẵn; role = thẻ nhân viên với quyền riêng. |
| Pool kết nối | Một nhóm đường dây điện thoại tới kho mở sẵn, ai cần thì mượn, xong trả lại. |
| Snapshot | Bản chụp dữ liệu lưu trong file `workspace.json`, dùng khi không bật PostgreSQL. |
| Manifest / checksum / hash (sha256) | Manifest = lý lịch; hash = "vân tay" của file. Vân tay khác nghĩa là file đã bị đổi. |
| Cache | Tờ giấy nháp ghi kết quả đã tính, lần sau hỏi lại thì đọc ngay, không tính lại. |
| Registry | Sổ đăng ký: trạm nào dùng mô hình nào, nằm ở đâu. |
| Artifact / `model.joblib` | Mô hình đã học xong, đóng gói thành file để dùng lại mà không học lại. |
| Random Forest | 300 "chuyên gia" (cây quyết định) cùng đoán; lấy trung bình làm dự báo. P10–P90 = khoảng mà 80% chuyên gia đoán nằm trong; **không** phải khoảng tin cậy đã hiệu chuẩn. |
| Đặc trưng (feature) | Thông tin đưa vào mô hình: mưa, nhiệt, gió, lưu lượng Kratie, mực nước Tân Châu... |
| Tháng `t−2` | Dự báo tháng 5 thì dùng dữ liệu tháng 3, vì dữ liệu tháng gần hơn có thể chưa công bố. |
| Nội suy tuyến tính | Hai trạm cách 10 km, một trạm 100, một trạm 200 mS/m; điểm giữa (5 km) ước tính 150. Đây là ước tính, không phải số đo. |
| MAE / RMSE | MAE = trung bình sai bao nhiêu; RMSE giống MAE nhưng phạt nặng lần sai to. Nhỏ hơn là tốt hơn, chỉ so trong cùng giao thức. |
| Hồi cứu / khóa EC / rolling origin | Thử mô hình trên quá khứ như thể đang ở thời điểm đó. "Khóa EC" = học một lần rồi đoán cả đoạn dài; "rolling origin" = cứ mỗi tháng học lại rồi đoán tháng sau. |
| Build (Vite) | Gom và nén các file `src/` thành `frontend/dist/` để máy chủ phục vụ. Sửa `src/` mà không build thì trang ở cổng 8000 vẫn cũ. |
| Middleware | Ông gác cổng đứng trước mọi ô cửa API, kiểm tra từng người trước khi cho vào. |
| Migration | Bản hướng dẫn sửa cấu trúc kho (thêm bảng, thêm cột) có đánh số thứ tự. |
| Test tự động | Bài kiểm tra viết sẵn: chạy một lệnh, máy tự so kết quả với đáp án. |

## Phụ lục C. Năm câu "chỉ tay vào màn hình" mẫu

1. "Khi trang mở, `workspace.js` gọi `/api/v1/workspace/stations`; hàm `stations()` trong `backend/services/workspace.py` lấy danh sách trạm từ `backend/repositories/workspace.py`."
2. "Khi kéo timeline, `timeline-scrubber.js` gọi `/api/v1/workspace/simulation/frame`; `simulation_frame()` trong `spatial_simulation.py` gọi `_segments()`, hàm này dùng `_idw()` (tên cũ, nay là nội suy tuyến tính) để gọi `interpolate_anchors()` trong `river_interpolation.py` tính EC từng đoạn sông. Phía ngoài Mỹ Tho là điều kiện biên cửa sông giả định, chưa hiệu chuẩn."
3. "Chấm cống màu đỏ vì `gate_state()` thấy EC ngoài cống ≥ ngưỡng đóng (mặc định 150 mS/m). Màu này không cho biết cống thật đang đóng hay mở."
4. "Bấm Dự báo, `multivariate-forecast.js` gửi `POST /api/v1/workspace/multivariate/predict` (cùng hàm này cũng mở ở `/api/v1/multivariate/predict`; giao diện dùng đường `/workspace`); `predict_month()` trong `backend/domain/multivariate_ec.py` cho 300 cây Random Forest đoán, rồi trả trung bình và P10–P90."
5. "Rà soát cống chạy `evaluate()` trong `backend/domain/gate_intake_rules.py` (máy chủ) hoặc bản giống hệt trong `frontend/src/shared/gate-intake-rules.js`; kết quả là danh sách điều kiện, không phải lệnh vận hành."
