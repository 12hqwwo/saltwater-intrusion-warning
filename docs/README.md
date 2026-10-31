# Bản đồ tài liệu dự án

Đọc từ đây thay vì mở mọi tệp trong `docs/`. Các đường dẫn được giữ ổn định vì mã và tài liệu đã tham chiếu chéo nhiều tệp; không di chuyển dữ liệu hoặc kết quả thí nghiệm chỉ để đổi cách hiển thị thư mục.

## Đang dùng cho sản phẩm và báo cáo

- [README gốc](../README.md): chạy ứng dụng và cấu trúc mã.
- [Hướng dẫn chạy](run_guide.md), [kiến trúc](architecture.md), [luồng người dùng](user-flow.md).
- [Bản thảo báo cáo](bao_cao_ban_thao_2026-10-28.md), [kế hoạch bốn tuần](ke_hoach_4_tuan_2026-10-28.md).
- [Đối chiếu sequence với website](sequence_coverage_2026-10-29.md).
- [Quyết định EC, thủy lực và cống](integrated_ec_salinity_gate_2026-10-29.md).

## Bằng chứng nghiên cứu cần giữ để tái lập

- [Hiệu chỉnh EC gọn](ec_compact_recalibration_2026-10-29.md), [thử mô hình bổ sung](ec_advanced_search_2026-10-29.md), [đặc trưng và triều](ec_feature_physics_hybrid_2026-10-29.md).
- [Kiểm toán mô hình thích ứng và tương quan đặc trưng](ec_adaptive_asof_audit_2026-10-30.md): đọc trước khi trích bảng Adaptive Dual-Head cũ.
- [Quét độ trễ công bố EC 0–70 ngày](ec_publication_lag_sensitivity_2026-10-30.md): kiểm tra +5/+35 chỉ là giả định và các ngày cho cùng tập nhãn.
- [Nguồn dữ liệu bổ sung](new_data_search_2026-10-29.md), [biên FES](fes_tide_boundary_validation_2026-10-29.md), [GRIT và cống](grit_gate_feasibility_2026-10-29.md).
- Các báo cáo `ec_*`, `tien_*` và `model_data_audit_*` còn lại là nhật ký giả thuyết, nguồn và kết quả âm tính. Chúng không phải bản mô hình đang chạy; giữ để tránh lặp thử nghiệm hoặc mất bằng chứng khi viết báo cáo.

## Thư mục dữ liệu và kết quả

| Nơi | Vai trò | Có thể dọn? |
|---|---|---|
| `data/raw/` | Dữ liệu nguồn, gồm atlas FES dung lượng lớn | Không tự xóa hoặc chuyển. |
| `data/external/` | Nguồn tải bổ sung cùng manifest/hash | Không tự xóa; nhiều script dùng đường dẫn cố định. |
| `data/processed/`, `data/research/`, `data/models/` | Dữ liệu chuẩn hóa, snapshot và model artifact | Giữ cho ứng dụng/tái lập. |
| `outputs/` | Bảng từng tháng, metric, kiểm toán triều/GRIT | Giữ; là bằng chứng cho báo cáo. |
| `runs/` | Thí nghiệm và manifest được website tham chiếu | Giữ. |
| `tmp/`, `frontend/dist/`, `__pycache__/` | Kết quả tạm hoặc sinh lại được | Có thể dọn sau khi kiểm nội dung; `tmp` còn vài bản thử GIS/ảnh xem trước nên không xóa cả thư mục. |
| `.venv/`, `.venv-api/`, `frontend/node_modules/` | Môi trường chạy/cài đặt phụ thuộc | Giữ khi còn chạy dự án; đều được Git bỏ qua. |

Ngày 30/10/2026 đã dọn **48 thư mục tạm rỗng, 35 tệp 0 byte, 35 cache DB tạm, 88 ảnh/binary sinh trong `tmp/pdfs` (87,6 MB), 8 ảnh trích từ Word và 1 log PDF**. Không xóa nguồn MRC, FES, GFZ, các model, metric hay tệp có thay đổi trong Git. `output/pdf` rỗng cũ đã bỏ; thư mục kết quả chính là `outputs/`.

Khi định xóa thêm: kiểm `rg` trong mã và tài liệu, kiểm `git status`, xác minh manifest/checksum và khả năng tái tạo. Các script nghiên cứu không được import bởi website vẫn có thể là lệnh tái lập số liệu báo cáo, nên không coi là “không dùng” chỉ vì không nằm trong API.
