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
