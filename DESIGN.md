# Thiết kế WebGIS Đồng Tháp

## Mục đích

Không gian làm việc phục vụ đọc EC theo tháng trên trục Sông Tiền, xem các tuyến kênh có cống, truy nguồn quan trắc và mở các công cụ dự báo. Đường vào `/` chuyển tới trang Tổng quan trong `/workspace.html`; thanh điều hướng giữ năm mục và trạng thái mục đang xem.

## Giao diện

- Nền sáng, chữ xanh đậm, bề mặt nhẹ và đường phân cách rõ. Bản đồ là đối tượng chính của mục Quan trắc.
- Kiểu chữ Funnel Display dùng cho tiêu đề; Funnel Sans dùng cho nội dung và điều khiển. Khi không tải được phông, hệ thống dùng sans-serif của thiết bị.
- Các biến màu, khoảng cách, kích thước chữ và chuyển động nằm trong `frontend/src/app/tokens.css` và `frontend/src/app/refresh.css`.
- Ở màn hình hẹp, điều hướng cuộn ngang; chú giải, phiếu cống và dòng thời gian đi theo luồng trang để không che bản đồ.

## Quy tắc màu EC trên bản đồ

Ngưỡng luôn đọc từ khung mô phỏng đang chọn, đơn vị **mS/m**:

| Mức | Điều kiện | Cách trình bày |
| --- | --- | --- |
| Dưới ngưỡng xem xét lấy | EC nhỏ hơn ngưỡng dưới | Xanh lam lục |
| Chuyển tiếp | EC từ ngưỡng dưới đến dưới ngưỡng ngăn mặn | Hổ phách |
| Đạt ngưỡng ngăn mặn | EC bằng hoặc cao hơn ngưỡng trên | Đỏ gạch |
| Chưa có dữ liệu | Không có EC hoặc ngưỡng hợp lệ | Xám |

Màu trục sông dùng EC nội suy của từng đoạn. Với 10 tuyến kênh có hình học đã kiểm tra, đoạn **từ trục sông đến đúng vị trí cống** dùng EC mô phỏng ngoài cống; đoạn **sau cống** là nét đứt xám vì chưa có EC nội kênh. Vị trí và màu không khẳng định cống đang đóng hay mở. Các cống không có hình học nhánh được giữ dưới dạng điểm; không tự vẽ tuyến nối mới.

Hạt dòng chảy màu trắng chỉ cho biết hướng mô phỏng. Cắt dọc sông đánh dấu vị trí cắt qua hai ngưỡng EC của kịch bản, không dùng mốc quy đổi độ mặn 1/4 g/L.

Sơ đồ trên trang Tổng quan dựng từ `data/biengioi/tien_river_corridor.geojson`; chạy `node frontend/scripts/generate-river-diagram.mjs` khi dữ liệu hình học thay đổi.
