# Bản đồ tài liệu dự án

Đọc từ đây thay vì mở mọi tệp trong `docs/`. Các đường dẫn được giữ ổn định vì mã và tài liệu đã tham chiếu chéo nhiều tệp; không di chuyển dữ liệu hoặc kết quả thí nghiệm chỉ để đổi cách hiển thị thư mục.

## Đọc phần đang dùng trước

1. [Hướng dẫn luồng WebGIS và hồ sơ giảm sai số](HUONG_DAN_LUONG_WEBGIS_VA_THU_NGHIEM_GIAM_SAI_SO.md): cách dùng từng tab, cách đọc bản đồ/biểu đồ và các phép thử sau khi chọn mô hình chính.
2. [Mô hình chính Mỹ Tho: khí tượng + lưu lượng Kratie + mực nước Tân Châu](mytho_hydrology_primary_2026-11-08.md): cấu hình hiện hành, các kỳ khóa EC, kết quả và giới hạn. Mỹ Thuận và Tân Châu dùng mô hình riêng.
3. [Hướng dẫn chạy](run_guide.md), [kiến trúc](architecture.md), [luồng người dùng](user-flow.md): vận hành và cấu trúc dự án.

Các tên `RF_compact`, mô hình EC trễ và chuỗi ước tính khí tượng cũ là **bằng chứng nghiên cứu**, không phải mô hình chính Mỹ Tho hiện đang phục vụ. Giao diện đặt thí nghiệm EC trễ trong phần phụ lục thu gọn. Kết quả không được chọn vẫn được giữ để người hướng dẫn kiểm tra vì sao chọn mô hình hiện tại.

### Hồ sơ kiểm chứng liên quan trực tiếp

- [Thử thêm thủy văn và EC trạm lân cận](frozen_ec_remedies_2026-11-08.md), [thử EC từng trạm và Ridge](frozen_ec_followup_2026-11-08.md): cùng giao thức giả định mất EC liên tục.
- [Thử giảm sai số theo rolling origin](ec_error_reduction_2026-11-08.md), [cửa sổ triều và phân vị cây](ec_tide_window_audit_2026-11-08.md), [chuyển mạch, log, dữ liệu ngày và khoảng trên](ec_math_physics_experiments_2026-11-08.md): các ứng viên chưa thay mô hình chính; báo cáo ghi rõ giao thức và kết quả âm tính.

<details>
<summary>Hồ sơ phát triển và thử nghiệm cũ — mở khi cần truy nguồn</summary>

## Cập nhật 04/11/2026

- [Tích hợp Mỹ Thuận — Bước 3](tich_hop_mythuan_buoc_3_2026-11-04.md): dữ liệu/API ba trạm, nội suy hai chặng, 13 tháng fallback, chuỗi mở rộng và kiểm thử. Đây là trạng thái mới hơn hai báo cáo dưới.
- [Kiểm chứng mô hình Mỹ Thuận và nội suy ba trạm — Bước 1 và 2](kiem_chung_mythuan_ba_tram_2026-11-04.md): bảng MAE/RMSE 2022–2023, quy tắc ngày khả dụng, so sánh hai điểm neo với dự báo tại Mỹ Thuận; chưa đổi giao diện/registry.
- [Dọn giao diện và xác minh dữ liệu EC Mỹ Thuận](cap_nhat_giao_dien_va_kiem_tra_mythuan_2026-11-04.md): bỏ hai cột nguồn được yêu cầu, gỡ biểu mẫu mô phỏng cống cũ, giữ engine giai đoạn 2; xác nhận 451 mẫu Mỹ Thuận đã tải nhưng chưa có trong API quan trắc đang chạy.

## Cập nhật logic và tiến trình 01/11/2026

- [Giai đoạn 2: RuleProfile và engine kiểm tra điều kiện lấy nước tại cống](giai_doan_2_gate_intake_rule_engine.md): số đo hiện trường, bảng từng tiêu chí, dự báo siết thời hạn mẫu 6 → 2 giờ và kiểm thử.
- [Tổng hợp thay đổi theo file, luồng chạy, kiểm tra và việc còn lại](cap_nhat_logic_va_tien_trinh_2026-11-01.md): sửa đóng gói RF_compact, ngày khả dụng, metrics/P90, dự báo lưu 01/2024, biểu đồ/hash/workspace và nội suy màu sông theo khoảng cách.
- [Hiện trạng](current_state.md), [nhật ký tiến độ](weekly_progress.md), [luồng hoạt động](user-flow.md), [kiến trúc](architecture.md), [sơ đồ nghiên cứu](diagrams/02_research_workflow.md).
- [Báo cáo RF_compact đã hiệu đính](mo_hinh_rf_compact_chinh_thuc_2026-10-30.md) và [form dự báo đa biến hiện hữu](multivariate-forecast.md) mô tả hai luồng mô hình riêng. Các báo cáo ghi ngày trước đó giữ bằng chứng thuộc thời điểm lịch sử của chúng.

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

</details>

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
