# Kịch bản demo WebGIS EC Đồng Tháp — kèm bộ kiểm tra và kiến thức cần nói

**Kiểm tra thực tế:** 13/11/2026, trình duyệt 1440×900, `http://127.0.0.1:8000/workspace.html`, chế độ **PostgreSQL**, commit `0cc62ca`. Mọi số trong tài liệu này là số **đã hiện trên trang** lúc kiểm tra. Ảnh chụp ở `img/`.
**Thời lượng gợi ý:** 12–15 phút. Mỗi bước có: **Thao tác → Kết quả mong đợi (tiêu chí đạt) → Nói gì (kiến thức) → Nếu bị hỏi**.

---

## A. Chuẩn bị trước buổi bảo vệ (checklist)

| # | Việc | Lệnh / cách làm | Đạt khi |
|---|---|---|---|
| A1 | Mở PowerShell ở checkout chính | `Set-Location 'D:\Study\TLCN'` | Đúng thư mục |
| A2 | Kiểm tra Git | `git status --short --branch` | Nhánh `TinBranch`, HEAD là bản muốn demo |
| A3 | Khởi động (build + chạy) | `.\start.ps1` | Terminal báo chạy ở cổng 8000 |
| A4 | Xác định đúng tiến trình giữ cổng | `Get-NetTCPConnection -LocalPort 8000` rồi xem tiến trình | Đường dẫn là `D:\Study\TLCN\run_webgis.py --mode postgres` |
| A5 | Sức khỏe API | mở `http://127.0.0.1:8000/api/v1/health` | `{"status":"ok","database_name":"dongthap_gis","transaction_read_only":true}` |
| A6 | Test frontend | `node --test tests/*.test.mjs` | 156/156 đạt (kết quả 13/11/2026) |
| A7 | Test backend | `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v` | Xem mục F |
| A8 | Tắt ô “Lưu lượt chạy vào PostgreSQL” khi demo nếu không muốn ghi DB | Tab Dự báo | Thông báo “chưa lưu PostgreSQL” |
| A9 | Phương án dự phòng nếu DB lỗi | `.\start.ps1 -Mode snapshot` | Huy hiệu đổi thành “Snapshot có nguồn” — **nói rõ** đây là snapshot |

Mẹo: phóng trình duyệt toàn màn hình, nền “Bản đồ sáng”, để sẵn tab `/docs` ở cửa sổ khác.

---

## B. Kịch bản trình bày

### Bước 1 — Tổng quan: “hệ thống đọc dữ liệu từ đâu” (1,5 phút)

**Thao tác:** Mở `workspace.html`. Chỉ huy hiệu góc phải. Bấm **“Kiểm tra PostgreSQL”**.

**Kết quả mong đợi:**
- Huy hiệu ghi **PostgreSQL**.
- Dòng trạng thái: “Đã kết nối PostgreSQL. Xem lịch sử ngay trong mục Quan trắc.”
- Thẻ số: **50** mẫu EC RIA2; **13** điểm quan trắc, **1428** số đo; quan trắc gần nhất **11/11/2025**; **3** trạm dự báo đa biến.
- Bảng “EC quan trắc gần nhất theo trạm”: 8/13 trạm, kèm câu “Các trạm có thể được đo vào ngày khác nhau; đây không phải EC hiện thời.”

**Nói gì:**
- Hệ thống có hai chế độ nguồn: PostgreSQL/PostGIS và snapshot có kiểm SHA-256. **Lỗi DB không tự chuyển sang snapshot**, để người xem không nhầm dữ liệu tĩnh là dữ liệu sống.
- 1428 = 464 Tân Châu + 463 Mỹ Tho + 451 Mỹ Thuận (MRC) + 50 RIA2. Ngày 11/11/2025 là của **RIA2**, không phải MRC; MRC dừng ở 15/12/2023.
- Nút kiểm tra gọi `GET /api/v1/health`, mở giao dịch **chỉ đọc** bằng tài khoản `webgis_reader` (quyền tối thiểu).

**Nếu bị hỏi “sao EC mới nhất 2025 mà mô hình chỉ học đến 2023?”** → RIA2 là bản tin nuôi trồng, 10 điểm × 5 mẫu, CRS không ghi, khác trạm và khác phương pháp → chỉ tham khảo, không ghép vào chuỗi MRC.

---

### Bước 2 — Quan trắc: bản đồ mùa khô 04/2024 (2 phút)

**Thao tác:** Ở Tổng quan bấm **“Xem mùa khô →”**. (Ảnh `img/demo-01-quantrac-042024.png`.)

**Kết quả mong đợi:**
- URL chuyển `#observations`, tháng **2024-04**.
- Dòng nguồn: “Ước tính hồi cứu · khí tượng ERA5 · Nội suy 3 trạm, 2 chặng”.
- Sông xanh ở thượng lưu, chuyển cam–đỏ dưới Mỹ Tho; chấm cống dưới Mỹ Tho đỏ.
- Chú giải hướng: “Vệt sáng chạy trên sông: hướng lan mặn/nước ngọt theo kịch bản EC; không phải dòng chảy đo thực.” và “Gió vùng 2024-04 đi về Tây Bắc · 2.4 m/s · ERA5 tổng hợp tháng”.
- Trạng thái: “Đang xem 2024-04 · EC nội suy (mS/m)… Màu cảnh báo theo mốc EC đang chọn; cần đo thực tế tại nơi sử dụng.”

**Nói gì:**
- **Từ 2024 không có EC đo** → giá trị ba mốc là ước tính hồi cứu từ mô hình (Mỹ Tho dùng mô hình chính hiện hành khi đủ đầu vào t−2).
- **Nội suy tuyến tính từng chặng** trên trục 175 km: Tân Châu 0 km, Mỹ Thuận 85,2 km, Mỹ Tho 125 km. Đoạn 125–175 km dùng **biên cửa sông giả định chưa hiệu chuẩn**: EC Mỹ Tho × 6 vào tháng 12–4 (×1,5 tháng khác) + 0,4 × chênh Mỹ Tho − Tân Châu. Vì vậy màu ngoài Mỹ Tho là kịch bản, không phải số đo.
- Vệt sáng: ngược dòng khi mùa khô và EC ≥ ngưỡng ngăn mặn. Đây là **minh họa** (`ILLUSTRATIVE_SEASON_AND_EC_PROXY`), không có mô hình thủy lực.
- Gió: một vectơ vùng từ ERA5; **không** là đầu vào mô hình.

**Lưu ý chủ động nói:** nhãn trạm (“Mỹ Tho · Mẫu 2023-12-15: 15,4 mS/m”) luôn là **mẫu nguồn mới nhất** của trạm, **không** phải giá trị tháng đang xem. Giá trị của tháng đang xem nằm trên màu sông và tooltip “Đầu vào mô phỏng”.

---

### Bước 3 — Đổi ngưỡng theo mục đích dùng nước (1 phút)

**Thao tác:** Mở **“Mức cảnh báo EC”** để thấy chú giải. Đổi lựa chọn từ “Cây có múi (100/150)” sang “Sầu riêng (50/80)”, rồi “Lúa & nước ngọt (120/200)”. Có thể bấm **“Mốc cảnh báo”** để tự nhập.

**Kết quả mong đợi:** Chú giải đổi ba lớp (“Dưới X”, “X đến dưới Y”, “Từ Y”); màu sông và chấm cống đổi theo. Ghi chú: “Ngưỡng kịch bản: xem xét lấy <X mS/m; ngăn mặn từ Y mS/m.”

**Nói gì:**
- Cặp ngưỡng là **kịch bản minh họa** theo cây trồng; bảng `dss_reference.ec_threshold_presets` có CHECK `is_operational_rule = false`.
- Tham chiếu chuyên môn: FAO cho lúa ECw 2,0 dS/m = 200 mS/m; MRC dùng 150/620 để trực quan hóa rủi ro tại Mỹ Tho.
- Đổi ngưỡng gọi lại `/simulation/frame?open_below_ec=&close_above_ec=`; máy chủ tính lại trạng thái cống. Cặp ngưỡng rỗng, âm, bằng nhau hoặc đảo ngược bị từ chối.
- Có thể chuyển **“Độ mặn g/L”**: chỉ đổi cách hiển thị (≈ 0,0064 × EC); **màu vẫn tính theo EC**.

---

### Bước 4 — Đỉnh mặn lịch sử 03/2016 và một kênh có cống (2 phút)

**Thao tác:** Đặt lại “Cây có múi (100/150)”. Bấm **“Đỉnh mặn lịch sử 03/2016”**. Chọn “Kênh có cống” → **“Kênh mô phỏng - Xoài Hột”**. (Ảnh `img/demo-02-dinhman-032016.png`, `img/demo-03-kenh-xoaihot.png`.)

**Kết quả mong đợi:**
- Dòng nguồn: “2016-03 · **Mẫu nguồn MRC** · Nội suy 3 trạm, 2 chặng”.
- Gió: “Gió vùng 2016-03 đi về Tây Bắc · 2.8 m/s”.
- Thẻ cống: “Xoài Hột · GATE_TG_020 · Lý trình 120.9 km · Cách trục sông 0.88 km · Từ sông tới cống · tháng 2016-03: **347,09 mS/m**”, khung đỏ “EC mô phỏng đạt hoặc vượt ngưỡng ngừng lấy của kịch bản”.
- Câu “Tuyến màu chỉ kéo từ sông tới cống… Đoạn sau cống không tô màu vì chưa có EC nội kênh.”

**Nói gì:**
- Trước 2024, ba mốc là **mẫu MRC thật**; tháng thiếu được lấp bằng nội suy thời gian và **gắn cờ**.
- EC tại cống = EC sông nội suy tại **lý trình** 120,9 km (gần Mỹ Tho 125 km). Khoảng cách 0,88 km là đường chim bay, **không chứng minh liên thông thủy lực**.
- **Màu cống không phải trạng thái đóng/mở**; frame trả `gate_decision_eligible=false`, `actuator_command=null`.
- Ba loại điểm tách biệt: trạm MRC (nhãn dài), RIA2 (chấm xám xanh viền đứt, CRS giả định WGS84), cống (chấm tròn theo mức EC).

---

### Bước 5 — Cắt dọc sông và phát chu kỳ (1 phút)

**Thao tác:** Bấm **“Hiện cắt dọc sông”**. Sau đó bấm **“Phát chu kỳ”** ở tốc độ 2x vài giây rồi dừng. (Ảnh `img/demo-04-catdoc.png`.)

**Kết quả mong đợi:** Biểu đồ 0–175 km, nhãn Tân Châu 0, Mỹ Thuận 85,2, Mỹ Tho 125, cửa 175; hai đường ngưỡng nét đứt; vạch ranh nơi đường EC cắt ngưỡng; các cống thành vạch; tháng tự chạy.

**Nói gì:**
- Đây là “mặt cắt dọc” của phép nội suy: hai đoạn thẳng nối ba trạm, thêm đoạn biên cửa sông. Đường gấp khúc thể hiện đúng giả định tuyến tính.
- Dòng thời gian chạy 1985-06 → 2027-11. Sau tháng cuối có đầu vào t−2, giá trị là **kịch bản trung vị cùng tháng 2010–2023**, có nhãn riêng.

---

### Bước 6 — Lịch sử PostgreSQL của Mỹ Tho (1,5 phút)

**Thao tác:** Mở “Tra cứu lịch sử quan trắc PostgreSQL” → **“Kết nối và tải danh sách trạm”** → chọn trạm “Mỹ Tho - MRC · MRC_VN_019805” → **“Toàn bộ thời gian”**. (Ảnh `img/demo-05-pg-history.png`.)

**Kết quả mong đợi:**
- “Đã kết nối · 3 trạm.” Nguồn: “MRC Water Quality - user supplied export”, “MRC My Thuan Conductivity”.
- “**463 số đo** · Trung bình: 44,36 mS/m · Cao nhất: **841 mS/m**.”
- Bảng bắt đầu 26/06/1985 12,2 mS/m “Quan trắc (O)”; phân trang “1–20 / 46”.

**Nói gì:**
- Dữ liệu đọc từ `public.conductivity_observation` qua `/api/v1/stations/{site}/observations` (tham số hóa, `limit` ≤ 1000).
- Cờ O/E giữ nguyên; điểm rỗng là ước tính (E); đường nối ngắt ở tháng thiếu.
- 841 mS/m là 04/1998; 692 mS/m là 15/03/2020. Dữ liệu lệch phải: chỉ 26/463 tháng ≥ 150.
- Lược đồ có CHECK đơn vị `mS/m`, giá trị ≥ 0, UNIQUE (dataset, trạm, thời điểm), dataset khóa bằng SHA-256.

**Lưu ý thao tác:** nút “Toàn bộ thời gian” và “Tải lịch sử” **bị khóa cho đến khi chọn trạm** — đúng thiết kế. Đừng bấm trước khi chọn trạm.

---

### Bước 7 — Chạy dự báo Mỹ Tho tháng 12/2026 (2,5 phút)

**Thao tác:** Tab **“Dự báo EC đa biến”** → trạm **Mỹ Tho** → bấm **“Tháng sau · 2026-12”** → (tùy chọn) bỏ ô “Lưu lượt chạy vào PostgreSQL” → **“Chạy dự báo đa biến”**. (Ảnh `img/demo-06-dubao-mytho-122026.png`.)

**Kết quả mong đợi (đã đo 13/11/2026):**
- “Dự báo EC tháng 2026-12 · kỳ khí tượng đầu vào: 2026-10.”
- “Thủy văn: lưu lượng Kratie và mực nước Tân Châu đến 2026-10-31; ngày khả dụng 2026-11-05 là giả định.”
- **24,794 mS/m**; P10–P90 **15,39–40,073**; P50 18,287; IQR 10,75; độ lệch chuẩn 15,736.
- Bảng đầu vào tháng 2026-10: mưa 278,8 mm; nhiệt 28,09 °C; gió 1,526 m/s; sin −0, cos 1; Q Kratie 13.582,067 m³/s; Q 3 tháng 28.983,663; tỷ lệ cùng mùa 0,61; mực nước Tân Châu 2,38 m; trung vị 3 tháng 2,465 m.
- “Phiên bản 20261108T_HYDROLOGY_PRIMARY_V1 · phát hành … · mã …”.
- “Huấn luyện đến 2023-12-01 · 463 mẫu… MAE 16,569 · RMSE 31,21 · n = 36.”
- Bảng đối chiếu cây trồng: cả ba “Dưới ngưỡng thấp của kịch bản · vẫn cần đo kiểm tại nơi lấy nước”.

**Nói gì:**
- **Tháng t−2:** dự báo 12/2026 dùng dữ liệu 10/2026, vì tại ngày phát hành dữ liệu 11/2026 chưa chắc đã công bố. Giả định nguồn có sau cuối tháng + 5 ngày — **chưa xác minh lịch công bố thật**.
- **10 đặc trưng**, quan trọng nhất là mưa (0,341) và nhóm lưu lượng Kratie (tỷ lệ 0,231 + Q 0,160 + Q3 0,092). Tỷ lệ 0,61 nghĩa là lưu lượng tháng 10/2026 chỉ bằng 61% trung vị cùng tháng của tối đa 15 năm trước.
- **Mỗi lần dự báo**, backend kiểm SHA-256 model và manifest theo registry, kiểm thứ tự đặc trưng; **không huấn luyện lại trong request**.
- **P10–P90 là độ phân tán giữa 300 cây**, không phải khoảng tin cậy đã hiệu chuẩn (trang ghi rõ).
- MAE/RMSE hiển thị là của kỳ khóa EC 2021–2023, **không phải sai số của riêng dự báo này**.
- Thiếu thủy văn → API trả 422, **không thay bằng 0**.

**Nếu bị hỏi “24,8 mS/m tháng 12 có hợp lý?”** → Tháng 12 đầu mùa khô, Q cao do lũ tháng 9–10 vẫn còn (Q3 28.984 m³/s); EC Mỹ Tho tháng 12 lịch sử thường thấp. Nhưng tỷ lệ Q 0,61 thấp hơn bình thường → đáng theo dõi các tháng 2–4.

---

### Bước 8 — Đưa dự báo lên bản đồ (1 phút)

**Thao tác:** Bấm **“Áp dụng kịch bản dự báo lên bản đồ”**. (Ảnh `img/demo-07-dubao-banDo.png`.)

**Kết quả mong đợi:** Chuyển sang Quan trắc, khung ghi “Dự báo đa biến theo trạm · Tân Châu 13,691821 → Mỹ Thuận 15,106071 → Mỹ Tho 24,794207 mS/m · Nội suy 3 trạm, 2 chặng · P90 Mỹ Tho 60,42 mS/m”, kèm “cống của Timeline tạm ẩn khi xem kịch bản dự báo”. Nút **“Quay về Timeline”**.

**Nói gì:** Ba trạm dự báo bằng ba mô hình riêng rồi nội suy dọc sông. Đây vẫn là **dự báo tại trạm + nội suy**, không phải dự báo kiểm định tại từng điểm. P90 60,42 là mốc tham chiếu mặc định lấy từ P90 của tập huấn luyện ban đầu thí nghiệm RF_compact (`high_ec_metrics`), dùng làm mốc “cảnh giác cao” cho hồ sơ cống. Đừng gọi là P90 toàn chuỗi: P90 của 463 mẫu Mỹ Tho là 68,52.

---

### Bước 9 — Kiểm chứng khi EC ngừng cập nhật (2 phút)

**Thao tác:** Quay lại tab Dự báo → mở **“Kiểm chứng dự báo khi EC ngừng cập nhật”**. Xem kỳ mặc định 2021–2023, rồi đổi sang **“2019–2021 · giai đoạn đối chiếu 36 tháng”**. Có thể đổi “Kiểm tra độ nhạy: EC chậm 35 ngày”.

**Kết quả mong đợi:**
- 2021–2023: “khóa EC đến 2020-11 tại lần phát hành đầu 2020-12-06”. Bảng: RF chính **16,569/31,21**; RF khí tượng 28,312/64,232; giữ EC cuối 19,133/42,574; trung bình từng tháng 21,532/42,575; RF chỉ chu kỳ 21,863/42,842. Lệch nhiều nhất 2021-03: dự báo 82,797, thực 191,5.
- 2019–2021: RF chính **57,808/133,815**; RF khí tượng 69,545/147,725; giữ EC cuối 80,196/191,229. Lệch nhiều nhất **2020-03: dự báo 213,665, thực 692**.

**Nói gì:**
- **Giao thức khóa EC** mô phỏng đúng tình huống thật: không có EC Mỹ Tho mới sau 2023. Mô hình fit một lần trước đoạn mất EC; đầu vào khí tượng/thủy văn vẫn cập nhật; EC trong đoạn chỉ để chấm.
- RF chính thắng các baseline ở hai kỳ này. Nhưng ở kỳ 2022–2023, **giữ EC cuối (10,76/16,46) tốt hơn RF chính (12,19/25,43)** — nói thẳng.
- RMSE gấp ~2,3 lần MAE ở 2019–2021 → có vài lỗi rất lớn (đỉnh 2020).
- RF **không ngoại suy**, ít mẫu đỉnh → hụt đỉnh 692. Đây là lỗi được giữ lại trong đánh giá, không lọc mẫu.
- Các kỳ chồng lấn và đã xem khi chọn → **hồi cứu, không phải kiểm định mù**.

---

### Bước 10 — Chất lượng dữ liệu (1 phút)

**Thao tác:** Tab **“Chất lượng dữ liệu”**. (Ảnh `img/demo-08-chatluong.png`.)

**Kết quả mong đợi:** “Hồ sơ đang rà soát · Chưa xác minh chất lượng”; **640** dòng tệp nguồn, **47** trạm có dữ liệu, **890** giá trị giữ để rà soát; mục “Cần kiểm tra gì?” ba gạch đầu dòng.

**Nói gì:** Số đo độ mặn tiếp nhận (g/L) **chưa xác minh** — chưa vào chuỗi EC hay dữ liệu huấn luyện; API luôn trả `UNVERIFIED`, `training_eligible=false`. Phải phân biệt điểm “trên sông” và “nội đồng” trước khi so sánh. Mục “Ước tính EC lịch sử từ khí tượng” là kết quả nghiên cứu cũ, không thay dự báo chính.

---

### Bước 11 — Hồ sơ cống: ba kết luận (2 phút)

**Thao tác:** Tab **“Hồ sơ cống”** → chọn **“Xoài Hột · GIS”**. Nhập **bộ số liệu giả lập** (nói rõ là giả lập):

| Trường | Ca 1 — Đạt | Ca 2 — Không đạt | Ca 3 — Quá hạn |
|---|---|---|---|
| EC thực đo ngoài sông sát cống (mS/m) | 80 | **200** | 80 |
| EC thực đo trong đồng (mS/m) | 60 | 60 | 60 |
| Mực nước ngoài sông (m) | 1,20 | 1,20 | 1,20 |
| Mực nước trong đồng (m) | 1,05 | 1,05 | 1,05 |
| Thời điểm bộ số đo | 1 giờ trước | 1 giờ trước | **8 giờ trước** |
| Người đo / nguồn | “Demo hội đồng - số liệu giả lập” | như trên | như trên |
| Trạng thái cơ khí | READY · Sẵn sàng | như trên | như trên |
| Xác nhận cùng hệ cao độ | ✓ | ✓ | ✓ |

Bấm **“Kiểm tra điều kiện xem xét lấy nước”** sau mỗi ca. (Ảnh `img/demo-09-hosocong.png`.)

**Kết quả mong đợi (đã chạy):**
- Phần A (nếu đã chạy dự báo ở Bước 7): “Chưa kích hoạt cảnh giác cao… EC dự báo tại vị trí chiếu của cống: **23,784 mS/m · km 120,852**… thời hạn mẫu đo 6 giờ.”
- Ca 1: **“Đề nghị xem xét lấy nước”**, có hạn hiệu lực đến khi mẫu hết 6 giờ; ΔH = 0,15 m ≥ 0,05 m.
- Ca 2: **“Chưa phù hợp để lấy nước”** — “EC 200 mS/m vượt ngưỡng 156.25 mS/m.”
- Ca 3: **“Cần bổ sung hoặc đo lại”** — “Mẫu đã quá hạn: 8.01 giờ > 6 giờ; cần đo lại.”

**Nói gì:**
- Quy tắc `TECH_SCREENING_RULE_V1.0`: EC ngoài ≤ 156,25 (≈ 1 g/L), EC trong ≤ 125, ΔH ≥ 0,05 m, cùng hệ cao độ, cơ khí READY, có nguồn, mẫu ≤ 6 giờ (≤ 2 giờ khi cảnh giác cao).
- **Cảnh giác cao** bật khi dự báo Mỹ Tho ≥ P90 60,42, hoặc EC chiếu tại cống ≥ 125. Dự báo **chỉ rút ngắn thời hạn mẫu**, **không thay số đo**.
- Ưu tiên kết luận: thiếu/quá hạn > không đạt > đạt.
- Kết quả luôn `requiresOperatorReview: true`, `actuatorCommand: null`: đây là **công cụ rà soát điều kiện**, người vận hành quyết định.

---

### Bước 12 — API docs (1 phút, tùy thời gian)

**Thao tác:** Mở `http://127.0.0.1:8000/docs`. Chỉ nhóm `/api/v1/multivariate/*`, `/api/v1/workspace/simulation/frame`. Thử **GET** `/api/v1/workspace/simulation/frame` với `year_month=2020-03`, `open_below_ec=100`, `close_above_ec=150`.

**Kết quả mong đợi:** HTTP 200; JSON có `interpolation_mode: "PIECEWISE_3_STATION"`, `methodology: "Piecewise 3-Station River-Axis Linear Interpolation & Empirical EC-Salinity Conversion (0.0064 g/L per mS/m)"`, `tier: 2`, `gate_decision_eligible: false`, `actuator_command: null`; các khóa `river_segments`, `gates`, `isohaline_boundaries`, `wind`, `boundary_conditions`, `assumptions`.

**Nói gì:** FastAPI tự sinh OpenAPI. Mọi frame tự khai báo phương pháp và giả định — **ngữ nghĩa khoa học nằm trong dữ liệu trả về**, không chỉ ở giao diện. Endpoint ghi (`POST .../history`, `.../gate-drafts`) yêu cầu cùng nguồn và tùy chọn `X-API-Key`; máy chủ tự chạy lại dự báo trước khi lưu.

**Không bấm “Try it out” cho POST ghi DB khi demo.**

---

## C. Kết thúc demo (30 giây)

> Hệ thống đi từ dữ liệu MRC có truy nguồn, qua CSDL PostGIS có ràng buộc, đến mô hình RF dùng khí tượng và thủy văn thượng nguồn được đánh giá theo giao thức khóa EC, rồi nội suy dọc sông để trực quan hóa và hỗ trợ rà soát cống. Giới hạn lớn nhất là chưa có EC sau 2023 để kiểm định mù và mô hình còn hụt đỉnh mặn cực trị.

---

## D. Bộ test chấp nhận (dùng làm phụ lục)

| ID | Tab | Thao tác | Kết quả mong đợi | Kết quả 13/11/2026 |
|---|---|---|---|---|
| T01 | Tổng quan | Tải trang | Huy hiệu “PostgreSQL”, 13 điểm, 1428 số đo, 0 lỗi console | Đạt (1 cảnh báo hiệu năng Canvas `willReadFrequently`, không ảnh hưởng) |
| T02 | Tổng quan | “Kiểm tra PostgreSQL” | “Đã kết nối PostgreSQL…” | Đạt |
| T03 | Tổng quan → Quan trắc | “Xem mùa khô →” | Tháng 2024-04, nguồn “Ước tính hồi cứu · khí tượng ERA5” | Đạt |
| T04 | Quan trắc | Đổi preset ngưỡng | Chú giải và màu đổi | Đạt |
| T05 | Quan trắc | “Đỉnh mặn lịch sử 03/2016” | “Mẫu nguồn MRC · Nội suy 3 trạm, 2 chặng” | Đạt |
| T06 | Quan trắc | Chọn kênh Xoài Hột | GATE_TG_020, km 120,9, 347,09 mS/m, đoạn sau cống không tô | Đạt |
| T07 | Quan trắc | “Hiện cắt dọc sông” | Biểu đồ 0–175 km có mốc và ngưỡng | Đạt |
| T08 | Quan trắc | Hướng gió/hoạt ảnh | Có chú giải gió theo tháng; nút tạm dừng | Đạt |
| T09 | Quan trắc | Lịch sử PG Mỹ Tho toàn thời gian | 463 số đo, max 841 | Đạt (nút khóa khi chưa chọn trạm — đúng thiết kế) |
| T10 | Dự báo | Mỹ Tho 2026-12, không lưu | 24,794 mS/m, P10–P90 15,39–40,073, phiên bản `20261108T_HYDROLOGY_PRIMARY_V1` | Đạt |
| T11 | Dự báo | Áp lên bản đồ | 13,69 → 15,11 → 24,79; P90 60,42 | Đạt |
| T12 | Dự báo | Kiểm chứng 2021–2023 | 16,569/31,21, n = 36 | Đạt |
| T13 | Dự báo | Kiểm chứng 2019–2021 | 57,808/133,815; 2020-03: 213,665 vs 692 | Đạt |
| T14 | Chất lượng dữ liệu | Mở tab | 640 / 47 / 890, “Chưa xác minh” | Đạt |
| T15 | Hồ sơ cống | Ca 1 | “Đề nghị xem xét lấy nước” | Đạt |
| T16 | Hồ sơ cống | Ca 2 (EC 200) | “Chưa phù hợp để lấy nước” | Đạt |
| T17 | Hồ sơ cống | Ca 3 (8 giờ) | “Cần bổ sung hoặc đo lại” | Đạt |
| T18 | API | `/docs` | HTTP 200 | Đạt |
| T19 | API | `/api/v1/health` | `transaction_read_only: true` | Đạt |
| T20 | API | `/simulation/frame?year_month=2020-03` | `PIECEWISE_3_STATION`, `gate_decision_eligible: false` | Đạt |
| T21 | Test tự động | `node --test tests/*.test.mjs` | 156 pass, 0 fail | Đạt |
| T22 | Test tự động | unittest Python | Toàn bộ đạt | **Chưa đạt**: 110/116; 6 test/bằng chứng lệch — xem mục F |

**Test bổ sung nên thử trước buổi bảo vệ (chưa chạy trong đợt này):**
- Dự báo Tân Châu và Mỹ Thuận cùng tháng.
- Đầu vào “Dữ liệu do người dùng cung cấp” với mưa = 0 và giá trị biên (mưa 20000, nhiệt −90/65, gió 150) → API phải nhận hoặc từ chối đúng giới hạn.
- Chọn tháng trong kỳ huấn luyện (ví dụ 2020-03) → API phải chặn.
- Hồ sơ cống: bỏ ô cùng hệ cao độ; trạng thái “FAULT”; ΔH âm; dự báo Mỹ Tho giả lập > 60,42 để thấy thời hạn 2 giờ.
- Chế độ `snapshot` và trường hợp tắt PostgreSQL: trang phải báo lỗi, không tự đổi nguồn.
- Bàn phím: Tab qua các điều khiển, thanh trượt tháng dùng phím mũi tên.

---

## E. Rủi ro khi demo và cách xử lý

| Rủi ro | Dấu hiệu | Xử lý |
|---|---|---|
| Cổng 8000 do tiến trình cũ/worktree khác giữ | Giao diện thiếu tính năng mới | Kiểm tiến trình (A4), tắt, chạy lại `.\start.ps1` từ checkout chính |
| `frontend/dist` cũ | Không thấy lớp gió/hoạt ảnh | Không dùng `-SkipBuild` |
| PostgreSQL không chạy | “Kiểm tra PostgreSQL” báo lỗi | Bật dịch vụ; hoặc `-Mode snapshot` và nói rõ |
| Hội đồng nhầm nhãn trạm là giá trị tháng | Hỏi “sao 2016 lại ghi mẫu 2023?” | Giải thích như Bước 2 |
| Lưu dự báo ghi DB | Ô lưu đang bật | Bỏ ô trước khi chạy, hoặc nói rõ máy chủ tự chạy lại và ghi nhật ký |
| Hoạt ảnh làm máy chậm | Giật khi kéo bản đồ | Bấm “Tạm dừng hoạt ảnh” |

---

## F. Kết quả chạy test tự động 13/11/2026

- `node --test tests/*.test.mjs`: **156 tests, 156 pass, 0 fail**, 1,33 giây.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`: **116 tests, 110 đạt, 3 FAIL, 3 ERROR** (~12 phút). Log: `tmp/pytest_full_20261113.log`. Không lỗi nào nằm ở đường chạy web; cả 6 là test hoặc bằng chứng tái lập bị lệch so với mã hiện tại:

| Test | Lỗi | Nguyên nhân đã xác định |
|---|---|---|
| `test_spatial_simulation...test_timeline_contains_drought_and_wet_season_frames` | Mỹ Tho 2024-04: 195,727 ≠ 164,713 | Test vẫn kỳ vọng giá trị CSV nghiên cứu cũ `future_ec_forecast_2024_2026.csv`; mã hiện tại cố ý thay Mỹ Tho bằng **mô hình chính** (`spatial_inputs.py`). Test cũ, chưa cập nhật. |
| `test_model_loading...test_postgres_restores_reference_fields_without_promoting_geometry` | `KeyError: 'observations'` | Bundle giả trong test thiếu khóa `observations` mà `_snapshot_reference_points` nay yêu cầu. Fixture cũ. |
| `test_frozen_ec_remedies...test_published_metrics_match_checked_artifact` | SHA-256 lệch | `scripts/evaluate_frozen_ec_gap_remedies.py` đã sửa sau khi tạo `outputs/frozen_ec_remedies_20261108/run_manifest.json`. Bằng chứng không còn khớp script hiện tại. |
| `test_mythuan_three_station...` (3 trường hợp con) | Thiếu `source_snapshots/...`; hash `scripts/train_multivariate_ec.py` lệch | Thư mục chụp nguồn của `outputs/mythuan_three_station_20261104/` thiếu tệp; script huấn luyện đã đổi sau lần chạy. |

**Ý nghĩa khi bị hỏi:** số liệu hiển thị trên trang không bị ảnh hưởng; nhưng chuỗi tái lập của hai bộ bằng chứng (remedies 08/11, Mỹ Thuận 04/11) đang lệch với script hiện tại — cần chạy lại hoặc ghi chú phiên bản script. Lưu ý thêm: Mỹ Tho 04/2024 trên bản đồ là **195,73 mS/m** (mô hình chính), khác bản CSV cũ 164,71.
