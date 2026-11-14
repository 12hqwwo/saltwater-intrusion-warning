# Biên bản bàn giao WebGIS Đồng Tháp

**Cập nhật:** 10/11/2026 (giờ Việt Nam). **Dự án chính:** `D:\Study\TLCN`. Tài liệu này dành cho phiên làm việc tiếp theo: đọc trạng thái Git và mã hiện tại trước khi sửa, vì nhánh và dữ liệu có thể thay đổi sau ngày bàn giao.

## 1. Việc đang làm và phiên bản chính thức

- Ứng dụng là WebGIS quan trắc EC, dự báo EC theo tháng tại trạm và rà soát hồ sơ cống. Trang chính là `http://127.0.0.1:8000/workspace.html` khi chạy tại máy chủ cục bộ.
- Người dùng đã xác định **`D:\Study\TLCN` trên nhánh `TinBranch` là checkout chính thức**. Thư mục Codex `C:\Users\QUYNH\.codex\worktrees\tinbranch-map-ui\TLCN` là worktree riêng ở nhánh `codex/tinbranch-map-ui`; không mặc định xem nội dung worktree là bản đang chạy ở cổng 8000.
- Mốc **mã ứng dụng** được đối chiếu là commit `d124473` (`feat: refine gate map display and EC report`), đã được đẩy lên `temp`. Biên bản này được thêm sau mốc đó. `origin/TinBranch` không được cập nhật trong đợt push `temp`. Lần sau phải chạy `git status --short --branch` và kiểm tra remote lại, không coi mốc này là HEAD vĩnh viễn.
- Commit mã `d124473` gồm sửa biểu diễn chấm cống/nhãn trạm trên bản đồ và báo cáo LaTeX. Tệp chưa theo dõi `outputs/ec_error_reduction_20261108/experiment_ec_error_reduction.original.py` được **để ngoài commit**; đừng đưa nó vào Git hoặc xóa khi chưa xác định vai trò. `.claude/`, `.security/`, `.venv/`, `.venv-api/`, `.vscode/`, `.env`, `frontend/node_modules/` và `frontend/dist/` được `.gitignore` loại khỏi Git.

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
