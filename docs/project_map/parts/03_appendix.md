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
