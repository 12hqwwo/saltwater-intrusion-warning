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
