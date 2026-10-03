# Tiến độ tuần hiện tại — cập nhật 02/10/2026

Đồ án được phát triển theo từng chặng. Đây là tiến độ có bằng chứng, chưa phải báo cáo kết thúc đồ án.

## Công việc kế thừa

Schema v1/v2, ETL, tài liệu kiểm tra nhập lặp/rollback, dữ liệu EC/master, backtest, SQL audit, KML trạm và các GeoJSON đã có trước đợt này.

## Đợt 1: kiểm tra dữ liệu và chuẩn bị lớp trạm

1. Đối chiếu 927 EC raw với master: không sai khác giá trị hoặc trạng thái thiếu. Hash ba CSV và hai KML khớp manifest.
2. Sửa đường dẫn fixture theo repo thực tế: 7 test ETL đạt. Giữ hỗ trợ WEBGIS_TEST_DATA_DIR cho bộ fixture cũ.
3. Sửa source_manifest.csv từ mỗi dòng một ô thành bốn cột, giữ nguyên 5 bản ghi và hash.
4. Bỏ 2 dòng minh họa khỏi mẫu cống để tránh dùng nhầm tọa độ/nhãn xác minh.
5. Bổ sung audit cục bộ và 4 test về sai giá trị, thiếu tháng, nhận diện trạm và tọa độ không hữu hạn: đạt.
6. Xuất GeoJSON hai trạm, giữ REPORTED và nguồn/hash.
7. Tính lại sai số từ đầu ra mô hình; xác nhận cùng 24 tháng chấm. Chưa huấn luyện lại.
8. Bổ sung truy vấn chỉ đọc chuẩn bị API; cập nhật tài liệu hiện trạng, từ điển dữ liệu và hướng dẫn.

Bằng chứng: runs/local_audit/review_20261002/. Audit: PASS_WITH_LIMITATIONS, 0 kiểm tra thất bại, 4 lưu ý ngoài phạm vi.

## Phần còn lại

Chưa kết nối PostgreSQL, chưa xác minh topology/nguồn/ngày hiệu lực ranh giới, chưa hoàn thiện phương pháp backtest, chưa tạo API hoặc giao diện bản đồ.

Công việc kế tiếp: đối chiếu trạm/snapshot trong DB, xây API đọc trạm và lịch sử EC; sau đó nối bản đồ chọn trạm với biểu đồ có đơn vị, khoảng thời gian, cờ chất lượng và nguồn.
