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

## Phần I. Các tệp tính năng (`frontend/src/features/`)

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

## Phần II. Thư viện dùng chung (`frontend/src/shared/`)

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

## Tóm tắt: luồng "dự báo đến cống" để trình bày khi bảo vệ

1. `multivariate-forecast.js` gửi `POST /multivariate/history` (hoặc `/predict`), nhận EC dự báo tại một trạm, kiểm bằng `forecast-contract.js`.
2. Người dùng bấm "Dùng dự báo để kiểm tra cống". Sự kiện `workspace:apply-forecast-to-gate` tới `gate-dossiers.js`.
3. `gate-dossiers.js` gọi `loadMultivariateForecastContext()` (tệp `forecast-map-overlay.js`) để dự báo thêm hai trạm còn lại, cùng tháng, cùng đầu vào.
4. `gate-intake-screening.js` nhận ngữ cảnh. `gate-forecast-context.js` chiếu cống lên trục sông. `river-interpolation.js` nội suy EC tại vị trí chiếu.
5. `gate-intake-rules.js` quyết định có "cảnh giác cao" không, và hạn mẫu đo là 6 hay 2 giờ.
6. Người vận hành nhập **số đo thật** ở Phần B. Hệ thống chấm trên trình duyệt và đối chiếu với `backend/domain/gate_intake_rules.py`. Kết luận chỉ là đề nghị xem xét, không phát lệnh cống.
