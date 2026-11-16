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
