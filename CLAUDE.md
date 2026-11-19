# Biên bản bàn giao WebGIS Đồng Tháp

**Cập nhật trạng thái Git:** 19/11/2026 (giờ Việt Nam). **Dự án chính:** `D:\Study\TLCN`. Các phần nghiên cứu bên dưới ghi lại mốc cũ; đọc trạng thái Git và mã hiện tại trước khi sửa.

## 1. Việc đang làm và phiên bản chính thức

- Ứng dụng là WebGIS quan trắc EC, dự báo EC theo tháng tại trạm và rà soát hồ sơ cống. Trang chính là `http://127.0.0.1:8000/workspace.html` khi chạy tại máy chủ cục bộ.
- Tại lần tích hợp ngày 19/11, checkout `D:\Study\TLCN` ở `TinBranch` (`990f6e5`). Nhánh `refactor` local là đích nhận TinBranch; `origin/refactor` ở `feaf5dc` trước lần tích hợp. Luôn kiểm tra trạng thái Git trước khi chạy vì checkout chính có thể đổi nhánh. Worktree `C:\Users\QUYNH\.codex\worktrees\tinbranch-map-ui\TLCN` ở nhánh riêng `codex/tinbranch-map-ui`.
- Tệp chưa theo dõi `outputs/ec_error_reduction_20261108/experiment_ec_error_reduction.original.py` và các file untracked khác thuộc công việc riêng; đừng tự đưa vào Git hoặc xóa. `.claude/`, `.security/`, `.venv/`, `.venv-api/`, `.vscode/`, `.env`, `frontend/node_modules/` và `frontend/dist/` được `.gitignore` loại khỏi Git.

## 2. Chạy bản đúng và kiểm tra nhanh

Mở PowerShell ở `D:\Study\TLCN`. `start.ps1` build frontend rồi chạy FastAPI và frontend cùng cổng; mặc định dùng PostgreSQL. `.env` chứa thiết lập máy cục bộ, **không in nội dung hoặc commit**.

```powershell
Set-Location 'D:\Study\TLCN'
.\start.ps1
```

Mở `http://127.0.0.1:8000/workspace.html`; API docs ở `/docs`. `Ctrl+C` trong terminal đang chạy để dừng. Nếu muốn xem snapshot có nguồn mà không dùng PostgreSQL: `.\start.ps1 -Mode snapshot`. Chỉ dùng `-SkipBuild` khi chắc `frontend/dist/` đã build từ mã mới nhất. Nếu cổng 8000 đã bị chiếm, xác định tiến trình đang giữ cổng và đường dẫn nó chạy trước khi kết luận giao diện nào đang phục vụ; có thể chọn `-Port 8016`.

Lần đầu trên máy mới: xem [README.md](README.md), [docs/run_guide.md](docs/run_guide.md), `.env.example`; cài dependency theo hướng dẫn ở đó. `start-tinbranch.ps1` dành cho chạy **một worktree khác** bằng cấu hình trong checkout chính, không cần dùng khi đang ở chính `D:\Study\TLCN`.

Kiểm tra sau khi sửa giao diện hoặc API:

```powershell
node --test tests/*.test.mjs
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
npm.cmd --prefix frontend run build
```

Kiểm tra đúng phần sửa trước, rồi chạy rộng hơn nếu rủi ro còn lại đòi hỏi. Ngày 10/11/2026, ba tệp test `observations_map_gates`, `observations_contract`, `forecast_flows` đạt **22/22** trước khi push `d124473`; đây **không** phải tuyên bố toàn bộ suite đã chạy. Nếu Node test báo `spawn EPERM` trong sandbox, đó là hạn chế tạo tiến trình con; chạy lại với quyền phù hợp trước khi kết luận test hỏng.

## 3. Luồng dữ liệu hiện tại

1. `start.ps1` gọi `run_webgis.py`, nạp `.env`, chọn `postgres` hoặc `snapshot`, kiểm tra điều kiện bảo mật và phục vụ bản build `frontend/dist/`. `backend/main.py` đăng ký các API.
2. `frontend/workspace.html` chứa năm tab: **Tổng quan, Quan trắc, Dự báo EC đa biến, Chất lượng dữ liệu, Hồ sơ cống**. `frontend/src/app/workspace.js` khởi tạo các tính năng và nối các sự kiện giữa tab; `navigation.js` xử lý hash và tab.
3. Quan trắc đọc từ PostgreSQL `public` ở chế độ `postgres` hoặc `data/research/workspace.json` có manifest/checksum ở chế độ `snapshot`. Lỗi PostgreSQL không tự đổi sang snapshot. RIA2 là nguồn tham khảo riêng, không ghép vào chuỗi MRC.
4. Bản đồ tháng lấy các mốc EC Tân Châu, Mỹ Thuận, Mỹ Tho. `backend/domain/river_interpolation.py` nội suy **tuyến tính từng chặng dọc sông**; khi lịch sử thiếu Mỹ Thuận thì có fallback hai trạm và giao diện ghi rõ. `backend/services/spatial_inputs.py` có thể lấp tháng thiếu bằng nội suy thời gian giữa hai tháng nguồn, hoặc dùng tháng gần nhất ở mép chuỗi; giá trị lấp được gắn cờ, không sửa mẫu gốc. Phía ngoài Mỹ Tho có điều kiện biên cửa sông giả định chưa hiệu chuẩn; không gọi toàn bộ màu sông là số đo.
5. Với Mỹ Tho, form dự báo dùng artifact Random Forest đã lưu, không huấn luyện trong request. Đầu vào khí tượng và thủy văn lấy tháng `t−2`; thiếu thủy văn thì không chạy. Dự báo tại ba trạm có thể được đưa lên bản đồ và nội suy dọc sông; đó vẫn là dự báo theo trạm và nội suy, không phải phép đo hoặc dự báo được kiểm định tại từng cống.
6. Hồ sơ cống nhận dự báo làm **bối cảnh xu thế** ở phần A; phần B cần EC/mực nước đo thực tế hai phía cống, thời điểm, nguồn và tình trạng cơ khí. Công cụ rà soát điều kiện, không phát lệnh đóng/mở cống.

## 4. Muốn sửa việc gì thì mở file nào

| Việc cần tìm hoặc sửa | File chính và trách nhiệm |
| --- | --- |
| Khởi động, chế độ nguồn, API gốc | `start.ps1`, `run_webgis.py`, `backend/main.py`; cấu hình mẫu ở `.env.example`, hướng dẫn ở `docs/run_guide.md`. |
| Bố cục năm tab, nhãn và điều khiển chung | `frontend/workspace.html`, `frontend/src/app/workspace.js`, `frontend/src/app/navigation.js`, `frontend/src/app/workspace.css`, `frontend/src/app/refresh.css`. |
| Quan trắc, lọc trạm/ngày, biểu đồ, PostgreSQL history | `frontend/src/features/observations.js`, `database-history.js`, `frontend/src/shared/observation-contract.js`; API ở `backend/api/workspace.py` và endpoint PostgreSQL trong `backend/main.py`; đọc nguồn ở `backend/repositories/workspace.py`. |
| Bản đồ sông, điểm trạm và chấm cống | `frontend/src/features/observations-map.js`, `gated-waterways.js`, `river-geometry.js`, `timeline-scrubber.js`, `river-profile.js`, `point-inspection.js`; CSS ở `frontend/src/styles/simulation.css`. |
| Số EC và nội suy phục vụ bản đồ | `backend/services/spatial_inputs.py`, `backend/services/spatial_simulation.py`, `backend/domain/river_interpolation.py`; quy tắc hiển thị phía frontend ở `frontend/src/shared/river-interpolation.js` và `simulation-display.js`. |
| Dự báo EC trực tiếp theo trạm | `frontend/src/features/multivariate-forecast.js`, `prediction-history.js`, `frontend/src/shared/forecast-map-overlay.js`; `backend/api/multivariate.py`, `backend/services/multivariate.py`, `backend/domain/multivariate_ec.py`. |
| Khí tượng, Kratie, Tân Châu và model đang chọn | `backend/repositories/multivariate_inputs.py`, `hydrology_inputs.py`; registry `data/models/multivariate_registry.json`; artifact và manifest ở `runs/multivariate_ec/mytho/20261108T_HYDROLOGY_PRIMARY_V1/`. |
| Biểu đồ hồi cứu và mô hình cũ để đối chứng | `frontend/src/features/forecasts.js`, `next-forecast.js`; `backend/services/forecasts.py`, `backend/domain/ec_gap_evaluation.py`, `ec_gap_remedies.py`, `ec_gap_followup.py`; registry thí nghiệm ở `data/research/experiment_registry.json`. |
| Chất lượng/tiếp nhận dữ liệu và ước tính lịch sử | `frontend/src/intake.js`, `frontend/src/features/weather-estimates.js`, `backend/intake.py`, `data/models/future_ec_forecast_2024_2026.csv`. CSV này là **bản lưu nghiên cứu cũ**, không phải đầu ra Mỹ Tho của mô hình chính hiện hành. |
| Hồ sơ cống và điều kiện xem xét lấy nước | `frontend/src/features/gate-dossiers.js`, `gate-forecast-context.js`, `gate-intake-screening.js`, `frontend/src/shared/gate-intake-rules.js`; `backend/services/gates.py`, `backend/domain/gates.py`, `gate_simulation.py`, `backend/api/dss_storage.py`. |
| SQL, quyền và lưu lịch sử | `backend/database.py`, `backend/security.py`, `backend/repositories/dss_storage.py`, `sql/`, `scripts/apply_dss_storage.py`, `scripts/setup_security.py`, `docs/database-security.md`. Các lệnh `--apply` có thể ghi DB/cấu hình; chỉ chạy khi đúng yêu cầu. |
| Test | `tests/*.test.mjs` cho frontend và `tests/test_*.py` cho backend, nội suy, nguồn, mô hình, bảo mật và cống. Chọn test sát phần sửa trước. |

### Trạng thái bản đồ ở commit `d124473`

- **Ba trạm MRC chính** Tân Châu, Mỹ Thuận, Mỹ Tho có nhãn dài như trước; **điểm RIA2 tham khảo** là chấm xám xanh nhỏ, không có nhãn dài trên bản đồ.
- **Cống trên nhánh kênh** là các chấm tròn; chấm đổi theo ba mức cảnh báo EC của tháng và cặp ngưỡng đang chọn. Màu không phản ánh cống đang đóng/mở. `observations.js` cho lớp chấm cống hiện, còn lớp cống cũ không hiện trùng.
- Màu trên nhánh chỉ kéo từ sông tới cống; **đoạn sau cống không tô màu** vì chưa có EC nội kênh. Khi chọn nhánh/cống, phiếu giải thích giá trị ngoài cống là nội suy. Kiểm tra các thay đổi này trong `observations-map.js`, `simulation.css`, `workspace.html` trước khi đổi lại cách vẽ.

## 5. Model, dữ liệu và cách đọc đúng

**Mô hình chính Mỹ Tho** là `20261108T_HYDROLOGY_PRIMARY_V1`: Random Forest 300 cây, độ sâu tối đa 8, tối thiểu 3 mẫu/lá, seed 42. Artifact hiện đăng ký tại `data/models/multivariate_registry.json`; `manifest.json` cùng `model.joblib` nằm ở `runs/multivariate_ec/mytho/20261108T_HYDROLOGY_PRIMARY_V1/`. Mô hình phục vụ được học trên **463 mẫu EC Mỹ Tho đến 12/2023**, không có EC Mỹ Tho mới sau 2023 trong tập học.

Mười đặc trưng: mưa, nhiệt độ, gió, hai biến chu kỳ tháng; lưu lượng Kratie tháng `t−2`, trung bình ba tháng, tỷ lệ với trung vị cùng mùa của tối đa 15 năm trước; mực nước Tân Châu tháng `t−2` và trung vị ba tháng. Nguồn thủy văn là các CSV MRC trong `data/external/mrc_kratie_discharge_20261029/`, `data/external/tien_manual_long_20261029/`, `data/external/tien_manual_2024_2026_20261029/`. `hydrology_inputs.py` yêu cầu mỗi tháng nguồn có ít nhất 20 ngày. Mốc ``cuối tháng +5 ngày'' là **giả định sẵn có**, chưa xác minh lịch công bố lịch sử thực tế. Nguồn khí tượng nằm trong `data/external/multivariate_weather/`.

Nguồn EC MRC gốc Mỹ Tho: `data/raw/ec/mrc/Conductivity.Water Quality@VN_019805_[My Tho].csv`. **Mẫu 692 mS/m ngày 15/03/2020 đã được người dùng xác nhận là đúng; không hỏi xác nhận lại, không tự loại hoặc sửa nhãn.** Tệp nguồn chỉ ghi ngày; dấu giờ `00:00` không chứng minh giờ lấy mẫu thật. Mẫu trong tháng không phải EC trung bình tháng. Ở phép khóa EC trước kỳ 2019–2021, dự báo 03/2020 là 213,67 mS/m; 04/2022 dự báo 100,04 khi mẫu là 25,7 mS/m. Đây là hai lỗi cần giữ trong đánh giá.

Ba kỳ khóa EC: 2019–2021 (36 tháng), 2021–2023 (36 tháng), 2022–2023 (24 tháng). RF khí tượng + thủy văn đạt MAE/RMSE lần lượt **57,81/133,82**, **16,57/31,21**, **12,19/25,43 mS/m**; tốt hơn RF chỉ khí tượng ở cả ba kỳ, nhưng cách giữ EC cuối tốt hơn ở kỳ 2022–2023 (**10,76/16,46**). Các kỳ chồng lấn và đã được xem khi chọn phương án: đây là **đánh giá hồi cứu, chưa phải kiểm định mù** trên EC mới. Không so trực tiếp điểm của giao thức khóa EC với rolling origin hoặc gọi P10–P90 giữa cây là khoảng tin cậy đã hiệu chuẩn.

Giá trị g/L trên bản đồ dùng quy đổi tham khảo `g/L ≈ 0,0064 × EC (mS/m)`; mức màu cảnh báo vẫn dựa trên **EC**. Không dùng g/L quy đổi làm nhãn EC thực đo hoặc dùng ngưỡng minh họa làm lệnh cống. Số liệu độ mặn tiếp nhận chưa xác minh nằm riêng trong tab Chất lượng dữ liệu. Tọa độ RIA2 là tham khảo; khoảng cách trạm–cống không chứng minh liên thông thủy lực.

## 6. Tài liệu và bằng chứng: đọc theo thứ tự

1. [README.md](README.md) và [docs/README.md](docs/README.md) để định hướng; [docs/HUONG_DAN_LUONG_WEBGIS_VA_THU_NGHIEM_GIAM_SAI_SO.md](docs/HUONG_DAN_LUONG_WEBGIS_VA_THU_NGHIEM_GIAM_SAI_SO.md) cho cách dùng từng tab và cách đọc bản đồ/biểu đồ.
2. [docs/bao_cao_webgis_ec_mytho_2026_11_08/main.tex](docs/bao_cao_webgis_ec_mytho_2026_11_08/main.tex) là báo cáo LaTeX đã biên dịch ở trình biên tập Codex; bìa, bố cục và bảng được chỉnh theo yêu cầu người dùng.
3. [docs/mytho_hydrology_primary_2026-11-08.md](docs/mytho_hydrology_primary_2026-11-08.md) và manifest mô hình là nguồn chính cho cấu hình Mỹ Tho, điểm hồi cứu và giới hạn.
4. [docs/frozen_ec_remedies_2026-11-08.md](docs/frozen_ec_remedies_2026-11-08.md), [docs/frozen_ec_followup_2026-11-08.md](docs/frozen_ec_followup_2026-11-08.md): các phép so sánh cùng giao thức khóa EC; bảng từng tháng/metrics/manifest trong `outputs/frozen_ec_remedies_20261108/` và `outputs/frozen_ec_followup_20261108/`.
5. [docs/ec_error_reduction_2026-11-08.md](docs/ec_error_reduction_2026-11-08.md), [docs/ec_tide_window_audit_2026-11-08.md](docs/ec_tide_window_audit_2026-11-08.md), [docs/ec_math_physics_experiments_2026-11-08.md](docs/ec_math_physics_experiments_2026-11-08.md): RF mịn/Huber, FES, chuyển mạch theo Kratie, log, Ridge+RF, dữ liệu ngày và khoảng trên. Các cách này **chưa thay mô hình chính**. `outputs/` và `runs/` là bằng chứng tái lập, không coi là rác chỉ vì chưa được ứng dụng import.

Một số tài liệu như `docs/architecture.md`, `docs/run_guide.md` và `docs/handover.md` được viết trước đợt thêm Mỹ Thuận, chuyển mô hình chính hoặc đổi hiển thị cống; chúng hữu ích về kiến trúc/lịch sử nhưng có câu mô tả giao diện hoặc số trạm đã cũ. Khi xung đột, đối chiếu mã hiện tại, registry/manifest và tài liệu 08/11/2026; không âm thầm sửa tài liệu lịch sử để che sự khác biệt.

## 7. Việc còn cần kiểm chứng, không tự suy diễn

- Cần EC Mỹ Tho **mới sau 2023**, chưa từng dùng để chọn phương án, để kiểm định độc lập; chấm riêng mùa khô, đỉnh EC cao, báo cao giả và bỏ sót. Không tuyên bố mô hình đã đạt sai số dự báo vận hành từ các kỳ hồi cứu.
- Cần lịch công bố thật của khí tượng, Kratie, Tân Châu và EC trạm lân cận. Không dùng ERA5 hoàn chỉnh sau sự kiện như thể đã có tại ngày phát hành lịch sử.
- Dữ liệu triều FES, EC Mỹ Thuận/Tân Châu, Ridge+RF, RF log, chuyển mạch lưu lượng và đặc trưng ngày có kết quả chưa ổn định hoặc giới hạn giao thức. Giữ bằng chứng, không tự thay registry/model đang phục vụ chỉ vì một kỳ có MAE thấp hơn.
- Chưa có EC trực tiếp đủ dài và cùng lịch công bố ở điểm gần cửa sông để kiểm chứng khả năng bắt đỉnh Mỹ Tho. Đường sau cống không có EC đo, và ứng dụng không chứng minh trạng thái cống thực tế.

## 8. Quy trình cho phiên làm việc tiếp theo

1. Xác nhận đang ở `D:\Study\TLCN` nếu sửa bản chính; chạy `git status --short --branch`, `git log -3 --oneline --decorate`. Kiểm tra thay đổi chưa commit của người dùng trước khi sửa; không `reset`, xóa dữ liệu hoặc di chuyển nguồn/artifact theo suy đoán.
2. Tìm file bằng `rg --files` và nội dung bằng `rg -n`, bắt đầu từ bảng ở mục 4. Đối chiếu mã, nguồn và manifest trước khi kết luận một số là quan trắc, nội suy hay dự báo.
3. Sửa phạm vi nhỏ nhất cần thiết. Nếu đổi model/đầu vào, giữ version và đánh giá cùng giao thức; nếu đổi bản đồ, giữ tách biệt trạm chính, RIA2, chấm cống và đoạn sau cống.
4. Chạy test sát phần sửa, build frontend khi có thay đổi UI, kiểm tra `git diff --check` và trạng thái Git. Với báo cáo LaTeX, dùng compiler của Codex để xác nhận biên dịch; mở preview để kiểm bố cục khi sửa bảng/bìa.
5. Khi được yêu cầu push lên `temp`, xác minh remote tip trước, stage **đúng tệp** và push fast-forward từ nhánh nguồn đã xác nhận; không force-push hoặc kéo theo `.env`, môi trường, tệp dự phòng chưa được chọn. Sau push xác nhận commit trên `origin/temp`.

## 9. Sơ đồ xử lý từ yêu cầu của người dùng đến dữ liệu hiển thị

### 9.1 Khởi động và nguồn dữ liệu

`start.ps1` là lối chạy thông thường ở Windows: build frontend rồi gọi `run_webgis.py`. `run_webgis.py` nạp cấu hình cục bộ, chọn `postgres` hoặc `snapshot`, kiểm tra các điều kiện chạy và mở FastAPI. `backend/main.py` gắn router, phục vụ `frontend/dist/` và các đường dẫn trang. `frontend/package.json` chỉ có Vite/OpenLayers; sửa `frontend/src/` xong phải build lại để cổng 8000 hiển thị mã mới. Trước khi sửa vì thấy “trạm biến mất” hoặc “giao diện cũ”, kiểm tra process giữ cổng 8000, thư mục process chạy, chế độ nguồn và thời điểm build; không kết luận từ riêng URL.

Nguồn quan trắc của chế độ `snapshot` là `data/research/workspace.json` cùng manifest/checksum. `backend/repositories/workspace.py` đọc và kiểm tra bộ này; khi `postgres`, nó nạp trạm/EC từ PostgreSQL `public` và giữ RIA2 tham khảo riêng. `backend/services/workspace.py` tạo summary, danh sách trạm, quan trắc, thí nghiệm và cống cho API. `backend/research.py` giữ router/tương thích cũ; `backend/api/workspace.py` thêm frame bản đồ, timeline, mẫu hồ sơ cống và xuất dữ liệu. Không để lỗi DB âm thầm trả về snapshot và bị hiểu thành dữ liệu sống.

### 9.2 Người dùng mở từng tab

| Bước người dùng | Mã chịu trách nhiệm | Dữ liệu/điểm cần kiểm |
| --- | --- | --- |
| Mở `workspace.html`, đổi tab | `frontend/workspace.html`, `frontend/src/app/workspace.js`, `navigation.js`; CSS `workspace.css`, `refresh.css` | `workspace.js` tải `/summary`, `/stations`, `/gates` độc lập, rồi khởi tạo Quan trắc, Dự báo, Chất lượng dữ liệu, Hồ sơ cống. Hash điều hướng nằm ở `navigation.js`. |
| Xem trạm và lịch sử EC | `frontend/src/features/observations.js`, `database-history.js`, `frontend/src/shared/observation-contract.js`; `backend/repositories/workspace.py` | Phân biệt MRC 3 trạm chính và RIA2 tham khảo; ngày lấy mẫu là ngày mẫu, không phải chuỗi EC liên tục hoặc trung bình tháng. Bảng PostgreSQL cần chọn đúng nguồn/phiên bản/QA. |
| Kéo timeline và xem màu sông | `timeline-scrubber.js`, `observations-map.js`, `river-profile.js`, `gated-waterways.js`, `point-inspection.js`; `backend/api/workspace.py`, `backend/services/spatial_inputs.py`, `spatial_simulation.py`, `backend/domain/river_interpolation.py` | `spatial_inputs.py` ghép EC tại 3 mốc, gắn cờ tháng được lấp; `river_interpolation.py` nội suy dọc từng chặng; `spatial_simulation.py` dựng frame/cống. Click bản đồ đọc ước tính trên sông, không phải phép đo tại chỗ. |
| Chọn trạm/tháng rồi bấm dự báo | `frontend/src/features/multivariate-forecast.js`, `prediction-history.js`, `frontend/src/shared/forecast-map-overlay.js`; `backend/api/multivariate.py` → `backend/services/multivariate.py` → `backend/domain/multivariate_ec.py` | API `/catalog`, `/inputs`, `/predict`, `/evaluation`. `multivariate_inputs.py` nạp ERA5; `hydrology_inputs.py` nạp Kratie/Tân Châu cho Mỹ Tho. `multivariate_ec.py` đọc registry, kiểm hash model/manifest và dự báo; request không fit lại model. |
| Xem đánh giá và biểu đồ hồi cứu | `frontend/src/features/forecasts.js`, `next-forecast.js`, `backend/services/forecasts.py`, `backend/domain/ec_gap_evaluation.py`, `ec_gap_remedies.py`, `ec_gap_followup.py` | Đây là kết quả nghiên cứu/đối chứng, không phải chuỗi EC mới. So sánh phải cùng kỳ và cùng giao thức. |
| Mở Chất lượng dữ liệu | `frontend/src/intake.js`, `weather-estimates.js`, `backend/intake.py` | Hồ sơ tiếp nhận và ước tính có nhãn riêng. `data/models/future_ec_forecast_2024_2026.csv` là bản nghiên cứu cũ; không dùng thay dự báo Mỹ Tho hiện hành. |
| Mở Hồ sơ cống | `gate-dossiers.js`, `gate-forecast-context.js`, `gate-intake-screening.js`, `frontend/src/shared/gate-intake-rules.js`; `backend/services/gates.py`, `backend/domain/gates.py`, `backend/api/dss_storage.py` | Phần A nêu xu thế dự báo. Phần B cần EC và mực nước đo hai phía, thời điểm, nguồn, tình trạng cơ khí; kết quả là rà soát điều kiện, không phát lệnh cống. |

### 9.3 Giải thích bản đồ đúng với dữ liệu

- `data/research/mrc_ec_monthly_samples.csv` và MRC gốc cung cấp mẫu EC tại trạm. Chỉ ba mốc Tân Châu–Mỹ Thuận–Mỹ Tho neo nội suy sông. Khi thiếu Mỹ Thuận lịch sử, `spatial_inputs.py` có fallback và trả dấu nguồn; tháng thiếu có thể được lấp bằng nội suy thời gian hoặc giá trị mép chuỗi. Giá trị lấp không trở thành mẫu MRC.
- `backend/domain/river_interpolation.py` tính tuyến tính theo vị trí trên tuyến giữa hai mốc có sẵn. Đường màu là hình dung không gian một chiều, chưa có mô hình lan truyền mặn theo triều/dòng chảy. Sau cống không có EC nội kênh nên không tô như đã biết. `frontend/src/features/gated-waterways.js` tách phần trước/sau cống; `observations-map.js` vẽ điểm cống tròn theo mức EC ngoài cống và ngưỡng đang chọn. Điểm cống không chứng minh cống đang mở/đóng; RIA2 không phải mốc neo MRC.
- `backend/services/spatial_simulation.py` có quy đổi tham khảo `g/L ≈ 0,0064 × EC (mS/m)`. Mức cảnh báo màu trên bản đồ vẫn dùng EC. Khi sửa chú giải, đừng thay mốc EC bằng ngưỡng độ mặn g/L hoặc gọi quy đổi là độ mặn đo trực tiếp. `frontend/src/shared/simulation-display.js` và `river-interpolation.js` có quy tắc hiển thị liên quan.

## 10. Mô hình Mỹ Tho đang phục vụ: chính xác ở đâu và chạy thế nào

1. `data/models/multivariate_registry.json` chọn artifact và manifest riêng cho `MYTHO`, `MYTHUAN`, `TANCHAU`. Chỉ mục Mỹ Tho trỏ tới `runs/multivariate_ec/mytho/20261108T_HYDROLOGY_PRIMARY_V1/model.joblib` và `manifest.json`; không tự suy phiên bản từ tên trang, CSV dự báo cũ hoặc kết quả thí nghiệm.
2. `scripts/train_mytho_hydrology_primary.py` là mã huấn luyện/đóng gói bản Mỹ Tho 300 cây, sâu tối đa 8, tối thiểu 3 mẫu/lá, seed 42. Mẫu đích là EC Mỹ Tho có trong `data/research/mrc_ec_monthly_samples.csv`, 463 mẫu qua 12/2023. `runs/.../manifest.json` giữ thứ tự 10 đặc trưng, đơn vị, tham số, nguồn/hash và điểm đánh giá. `predictions.csv` trong cùng run là kết quả đã lưu. Không chạy lại script này như bước khởi động web: nó có thể tạo/ghi artifact.
3. Đầu vào khí tượng: `backend/repositories/multivariate_inputs.py` đọc `data/external/multivariate_weather/`, tổng hợp mưa/nhiệt/gió theo tháng và lấy tháng `t−2`. Đầu vào thủy văn: `backend/repositories/hydrology_inputs.py` đọc CSV MRC lưu lượng Kratie và mực nước Tân Châu; yêu cầu ít nhất 20 ngày/tháng; tạo Q tháng `t−2`, Q ba tháng, tỷ lệ Q theo trung vị cùng mùa, mực nước tháng `t−2` và trung vị ba tháng. `backend/services/multivariate.py` ghép đầu vào, kiểm tra và đưa đến model; thiếu thủy văn thì báo không đủ dữ liệu, không tự thay bằng 0.
4. `backend/domain/multivariate_ec.py` tải model theo registry, xác minh hash và `feature_order`, thực hiện dự báo. `backend/api/multivariate.py` mở các endpoint, còn `frontend/src/features/multivariate-forecast.js` hiển thị kết quả, metadata và xuất dữ liệu. `frontend/src/app/workspace.js` nhận sự kiện dự báo để đánh dấu trạm trên bản đồ; đánh dấu đó vẫn là dự báo tại trạm, không chuyển các điểm khác thành quan trắc.
5. `scripts/forecast_mytho_ec_hydrology.py` dùng đầu vào hiện có để chạy dự báo Mỹ Tho ở lối nghiên cứu/CLI. Nó không phải đường chạy request của trang. `tests/test_mytho_hydrology_primary.py`, `tests/test_model_loading.py`, `tests/forecast_flows.test.mjs`, `tests/forecast_map_overlay.test.mjs` là các điểm kiểm gần khi đổi registry, nguồn hay cách hiển thị.

**Vấn đề khoa học đang mở:** `t−2` và quy tắc coi thủy văn có sẵn sau cuối tháng +5 ngày là giả định cho hồi cứu; lịch xuất bản lịch sử chưa xác minh. Dữ liệu ERA5 hoàn chỉnh sau sự kiện cũng không được tự coi là đã có ở ngày phát hành. Mẫu MRC chỉ có ngày, dấu `00:00` không xác nhận giờ lấy mẫu. Nhãn 692 mS/m ngày 15/03/2020 **đúng theo xác nhận của chủ dự án**, dù cờ QA nguồn chưa được nâng; giữ nguyên trong dữ liệu và điểm chấm. Mô hình khóa trước 2019 dự báo 213,67 so với 692; 04/2022 báo 100,04 so với 25,7. Đây là lỗi bỏ hụt đỉnh và báo cao giả cần thể hiện, không được xóa bằng cách lọc mẫu.

## 11. Hồ sơ thử giảm sai số: mã chạy, bằng chứng và quyết định

**Đọc giao thức trước khi đọc số.** “Khóa EC liên tục” fit một lần trước mỗi đoạn mất EC dài 24/36 tháng, chỉ dùng EC của đoạn đó để chấm. “Rolling origin/as-of” phát hành lại theo từng tháng và có quy tắc nhãn khả dụng +5/+35 ngày. Hai giao thức không tạo cùng một bảng xếp hạng; cũng không trộn số của các phiên bản scikit-learn/nguồn có hash khác nhau. MAE là sai lệch tuyệt đối trung bình; RMSE phạt mạnh lỗi lớn. Cả hai đơn vị mS/m, nhỏ hơn chỉ có nghĩa trên cùng cohort/giao thức. Đếm riêng tháng EC ≥100 bị dự báo <100 và báo cao giả; 100 là mốc phân tích, không là chuẩn nước tưới.

| Câu hỏi/phương pháp đã thử | File thực hiện và bằng chứng | Kết quả, giới hạn và quyết định |
| --- | --- | --- |
| Nếu EC Mỹ Tho ngừng cập nhật lâu, khí tượng riêng, thêm Kratie/Tân Châu, thêm EC trạm lân cận hay giữ EC cuối tốt hơn? | `scripts/evaluate_frozen_ec_gap.py`, `scripts/evaluate_frozen_ec_gap_remedies.py`; `backend/domain/ec_gap_evaluation.py`, `ec_gap_remedies.py`; `outputs/frozen_ec_gap_20261104/{predictions.csv,metrics.csv,run_manifest.json}`, `outputs/frozen_ec_remedies_20261108/{predictions.csv,metrics.csv,run_manifest.json}`; `docs/frozen_ec_remedies_2026-11-08.md`. | RF thêm thủy văn giảm MAE/RMSE so với chỉ khí tượng cả ba kỳ: 2019–2021 57,81/133,82; 2021–2023 16,57/31,21; 2022–2023 12,19/25,43. Nhưng persistence đạt 10,76/16,46 ở 2022–2023; thủy văn vẫn hụt 692. Đây là lý do chọn trong phạm vi hiện có, không chứng minh thắng mọi kỳ. |
| EC Mỹ Thuận/Tân Châu từng trạm, cả hai, Ridge tuyến tính hay Ridge + RF phần dư có giúp thêm? | `scripts/evaluate_frozen_ec_followup.py`; `backend/domain/ec_gap_followup.py`; `outputs/frozen_ec_followup_20261108/{predictions.csv,metrics.csv,run_manifest.json}`; `docs/frozen_ec_followup_2026-11-08.md`. | Thêm cả hai EC giảm RMSE 2021–2023 từ 31,21 xuống 29,59 nhưng tăng 2019–2021 lên 136,58 và 2022–2023 lên 28,09. Ridge thuần kém; Ridge+RF giảm RMSE 2022–2023 tới 21,92 nhưng MAE tăng và bỏ sót thêm đỉnh ở kỳ khó. Chưa đủ để thay RF chính; không kết luận EC trạm khác vô ích. |
| Cây RF mịn hơn, thiếu hụt lưu lượng, tăng trọng số EC cao, GB Huber và blend có giảm lỗi không? | `scripts/experiment_ec_error_reduction.py`, dùng nền `scripts/experiment_ec_long_hydrology.py` và mốc as-of từ `scripts/backtest_asof_ec.py`; `outputs/ec_error_reduction_20261108/{predictions_5d.csv,predictions_35d.csv,metrics_5d.csv,metrics_35d.csv,protocol_5d.json,protocol_35d.json}`; `docs/ec_error_reduction_2026-11-08.md`. | Đây là rolling origin trên RF_compact, **khác** frozen RF chính. +5 ngày: RF_fine_compact giảm MAE 2019–2021 51,71→49,40 nhưng làm MAE 2022–2023 12,01→13,88; mẫu 692 vẫn dự báo thấp. GB/weight/deficit không ổn định. Không đưa lên trang. Tệp untracked `experiment_ec_error_reduction.original.py` là bản dự phòng chưa chọn, không tự commit/xóa. |
| Thêm đặc trưng triều FES theo cửa sổ lịch cố định có giúp bắt mẫu 03/2020? | `scripts/audit_ec_tide_windows_20261108.py`; `outputs/ec_tide_windows_20261108/{fes_fixed_windows.csv,frozen_predictions.csv,metrics.csv,audit.json}`; `docs/ec_tide_window_audit_2026-11-08.md`. | Trung bình triều ban ngày 13–17 giảm MAE 2021–2023 16,57→15,59, nhưng 2019–2021 57,81→57,93 và dự báo 03/2020 vẫn chỉ 229,86. FES2022b là atlas phát hành sau ngày hồi cứu; giờ lấy mẫu thật không có. Chưa thêm FES hay p90/p95 cây vào WebGIS. |
| Chuyển mạch khi Q thấp, RF log/smearing, Ridge nghịch đảo Q + RF phần dư, dữ liệu thủy văn ngày gần phát hành và khoảng trên? | `scripts/experiment_ec_math_physics_20261108.py`; `outputs/ec_math_physics_20261108/{predictions.csv,metrics.csv,recent_daily_features.csv,calibration.csv,interval_audit.csv,protocol.json}`; `docs/ec_math_physics_experiments_2026-11-08.md`. | Ngưỡng Q<0,85 giảm MAE 2019–2021 57,81→56,19 nhưng bỏ sót EC ≥100 tăng 2→3; 02/2020 thực 558, dự báo chỉ 85,74. Ridge+RF cải thiện vài kỳ nhưng 2021–2023 xấu hơn. Dữ liệu ngày làm MAE kỳ khó tăng 57,81→64,82. Khoảng trên mùa khô chỉ bao phủ 10/15 tháng (66,7%); không gọi là trần an toàn. Không triển khai các ứng viên. |

Tất cả `outputs/` nêu trên là bằng chứng tái lập, không phải rác. Mỗi bộ có dự báo từng tháng, metrics và manifest/protocol/hash nguồn; đọc `predictions.csv` để hiểu tháng nào lỗi, không chỉ đọc MAE tổng. `scripts/train_mytho_hydrology_primary.py` đóng gói mô hình **đang phục vụ** sau quyết định chọn; `scripts/evaluate_*`/`experiment_*` ở bảng là **nghiên cứu**, không tự thay registry. Các script nghiên cứu có thể ghi lại `outputs/`; trước khi chạy nên xem tham số `--help`, nguồn và nơi ghi, giữ bản gốc nếu cần đối chiếu. Không trình bày một thử nghiệm có cải thiện ở một kỳ như nâng cấp đã đưa lên WebGIS.

## 12. Quy trình làm việc cho phiên Claude/Codex sau

1. Bắt đầu tại `D:\Study\TLCN`, đọc tài liệu này, `README.md`, `docs/README.md`; chạy `git status --short --branch` và `git log -3 --oneline --decorate`. Ngày 19/11/2026 checkout chính ở `TinBranch`; nhánh `refactor` local nhận tích hợp riêng. [CI run 44324276115](https://github.com/12hqwwo/saltwater-intrusion-warning/actions/runs/44324276115) chỉ xác nhận commit cũ `feaf5dc`, không xác nhận merge mới. Luôn kiểm tra lại các file untracked của công việc khác trước khi sửa.
2. Nếu cần sửa giao diện, mở `frontend/workspace.html` và `frontend/src/app/workspace.js` trước, rồi file feature trong mục 9. Đọc test liên quan trước khi đổi. Sau khi sửa, build `npm.cmd --prefix frontend run build`; chạy test Node sát chức năng. Để xem bản mới ở cổng 8000, khởi động lại bằng `.\start.ps1` từ **checkout chính** và xem tab/nguồn/tháng thực tế.
3. Nếu cần sửa model hoặc dữ liệu, kiểm `data/models/multivariate_registry.json`, manifest run, `backend/repositories/{multivariate_inputs,hydrology_inputs}.py`, `backend/domain/multivariate_ec.py`, các script/test ở mục 10–11. Ghi rõ giả định ngày phát hành và thời gian công bố của từng nguồn. Chỉ so các mô hình cùng cohort và giao thức; không ghi đè artifact chính bằng thí nghiệm. Nếu muốn đổi model phục vụ, tạo version/artifact/manifest mới và kiểm hash, test, hồi cứu cùng giao thức rồi mới đổi registry có chủ đích.
4. Nếu cần sửa bản đồ/cống, giữ ba loại điểm (MRC, RIA2, cống), màu trước cống và đoạn sau cống chưa có EC. Chạy `tests/observations_map_gates.test.mjs`, `tests/gated_waterways.test.mjs`, `tests/river_interpolation.test.mjs`, `tests/test_spatial_simulation.py`, `tests/gate_dossiers.test.mjs` tùy phạm vi. Nếu thay màn hình, kiểm cả thao tác bàn phím, chú giải và không che bản đồ.
5. Nếu cần sửa hồ sơ cống hoặc lưu DB, đọc `backend/domain/gates.py`, `backend/services/gates.py`, `backend/api/dss_storage.py`, `backend/repositories/dss_storage.py`, `sql/`, `docs/database-security.md`. Phân biệt tính toán hồ sơ với lệnh vận hành. Migration 38 (`38_app_user_username_case_insensitive`, checksum `93cbb62439f8ce7636787971555ef82f179e139e50d1654b8b0526ef7a1d5c92`) đã được áp dụng bằng `--apply` lên DB cục bộ `dongthap_gis` ngày 18/11/2026; DB khác phải kiểm tra riêng trước khi áp dụng. Các script DB có `--apply` ghi thật; không chạy để “kiểm tra thử”. Không mở/in `.env` hoặc tệp khóa.
6. `.claude/skills/` trong checkout chính đã có `code-review`, `data-pipeline-audit`, `postgis-migration`, `security-audit`, `test-writer` và ba skill thêm 12/11: `ec-forecast-evaluation`, `webgis-map-review`, `research-evidence-report`. Chúng là cấu hình cục bộ, bị `.gitignore` bỏ qua; một checkout/máy khác không tự nhận được. `CLAUDE.md` này là tài liệu bàn giao được Git theo dõi.

## 13. Hướng phát triển và điều kiện để hiệu chỉnh có cơ sở

1. **Dữ liệu kiểm định độc lập:** thu EC Mỹ Tho sau 12/2023 chưa từng dùng chọn/điều tham số, kèm ngày giờ thật, QA, đơn vị và ngày công bố. Chấm riêng mùa khô, đỉnh cao, bỏ sót, báo cao giả; khóa tiêu chí trước khi nhìn kết quả. Giữ nguyên mẫu đúng 692 mS/m và kiểm độ bền với lỗi cực trị thay vì xóa nó.
2. **Tính “biết được vào ngày phát hành”:** bổ sung lịch công bố/vintage của ERA5, Q Kratie, mực nước Tân Châu, EC trạm khác. Khi chưa có, gắn cờ rõ kết quả dùng dữ liệu hoàn chỉnh/hindcast và chạy phân tích độ nhạy +5/+35 ngày. Chỉ dùng cửa sổ ngày nếu mốc giờ phát hành và độ trễ nguồn cho phép; hiện thử nghiệm 4 biến ngày chưa giúp kỳ 2019–2021.
3. **Cải thiện mô hình theo rủi ro thực tế:** tiếp tục thử Q thấp/chuyển mạch và Ridge+RF trên tập **mới** với tiêu chí đồng thời MAE/RMSE và không tăng bỏ sót EC cao. Kiểm phần dư Ridge bằng dự báo ngoài mẫu trước khi cho RF học; hiệu chỉnh khoảng dự báo trên tập thời gian tách biệt. Không gọi p90 giữa cây RF là khoảng tin cậy.
4. **Không gian và cống:** nếu cần màu EC trong kênh hoặc sau cống, phải có số đo nội kênh, trạng thái cống và liên thông thủy lực theo thời gian; khi đó hiệu chuẩn/kiểm chứng mô hình mới. Hiện bản đồ một chiều chỉ cho bối cảnh. Nghiên cứu ngưỡng EC phù hợp địa phương và cây trồng từ nguồn chuyên môn trước khi đổi nhãn cảnh báo hoặc dùng vào quyết định lấy nước.
5. **Vận hành và trình bày:** đồng bộ `CLAUDE.md`, `docs/README.md`, hướng dẫn người dùng và biểu đồ với đúng registry khi có version mới; đánh dấu tài liệu lịch sử. Bổ sung test hồi quy cho nguồn/đơn vị/thời gian và khả năng dùng bàn phím; kiểm trang chạy thực tế sau build. Giữ manifest, hash, dự báo từng tháng và bản báo cáo để giáo viên hướng dẫn có thể truy ngược mọi số liệu.
