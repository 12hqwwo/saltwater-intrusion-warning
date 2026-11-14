# Phụ lục triển khai sau bộ ôn tập 13/11/2026

**Ngày lập:** 14/11/2026. Tài liệu này cập nhật trạng thái phần mềm; không thay các số liệu mô hình và ảnh chụp của ba tài liệu gốc. Trước buổi bảo vệ, mở bản build mới và chạy lại kịch bản demo trên đúng PostgreSQL.

## Những phần đã triển khai

- `monthly_inputs()` có cache theo dấu nguồn, phiên bản và ngày `Asia/Ho_Chi_Minh`; phản hồi nêu `cache_status` và `built_at` khi dùng bản cũ. Có pool kết nối đọc/ghi và cấu hình host LAN có kiểm soát.
- Lưu dự báo Mỹ Thuận đã được mở bằng migration 32. Lỗi ràng buộc UNIQUE trả 409; CHECK/FK trả 422.
- API độ tươi nguồn cho biết tháng cuối của khí tượng/thủy văn và tháng dự báo có thể hỗ trợ. Mốc nguồn khả dụng sau cuối tháng 5 ngày vẫn là giả định cần xác minh, không phải lịch công bố đã biết.
- Rà soát cống có phép tính trên server và fixture đối chiếu với client. Kết quả là thông tin rà soát, không là lệnh vận hành. Registry P90 mới chỉ được chuẩn bị, chưa kích hoạt; mô hình và ngưỡng đang phục vụ không đổi.
- Sổ phát hành có lịch `MONTHLY_D06_PREV` (09:00 ngày 06 của tháng trước), slot riêng, sự kiện `MISSED`, bản `LATE` và điểm theo `UNIQUE(issue_id,label_protocol_version)`. Bản trễ được chấm riêng; không đưa vào MAE đúng hạn. Lịch đầu tiên sau khi mở sổ là 06/12/2026 cho tháng 01/2027.
- Phiếu EC thực địa nằm trong bảng riêng, cần key cán bộ để gửi và key khác để duyệt. Chỉ phiếu đã duyệt hiện trên lớp tam giác của bản đồ. Phiếu không nhập vào chuỗi EC MRC hay tập huấn luyện. Phiếu bất thường so với trung vị lịch sử cùng tháng của trạm MRC gần nhất được gắn `REVIEW_HIGH` để kiểm tra.

## Giới hạn phải nói rõ khi demo

- Chưa có phiếu thực địa thật hoặc nhãn EC tháng mới đủ điều kiện; **chưa có MAE vận hành thật**. Hệ thống mới chứng minh hạ tầng phát hành và chấm điểm.
- Phiếu đã duyệt vẫn chưa tự thành nhãn chấm. Chỉ khi thỏa [giao thức nhãn EC tháng](../field_ec_label_protocol_2026-11-14.md) đã chốt trước phiếu đầu tiên mới được xét; MRC và phiếu EC25 phải báo cáo riêng.
- Ba tài liệu gốc và ảnh trong `img/` được đối chiếu ở commit `0cc62ca`. Các điều khiển mới cần kiểm trên trang bản build hiện tại: sổ phát hành, độ tươi nguồn, màn hình phiếu và lớp bản đồ đã duyệt. Không dùng ảnh cũ để chứng minh các tính năng mới.

## Kiểm tra mã ngày 14/11/2026

- Python: `unittest discover` 165 test qua, 1 skip.
- Frontend: `node --test tests/*.test.mjs` 172 test qua.
- Vite: build thành công.
- Migration 35 đã kiểm bằng dữ liệu tổng hợp trong transaction rollback; không để lại phiếu thử. Chi tiết ở [biên bản migration 35](../migration_35_execution_2026-11-14.md).
