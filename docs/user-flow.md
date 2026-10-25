# Luồng trình bày đồ án

Cập nhật 23/10/2026. Chạy `.\start.ps1 -Mode postgres` để dùng PostgreSQL hoặc `.\start.ps1` để mở bộ đóng gói có 12 điểm. Trang chính: `http://127.0.0.1:8000/workspace.html`.

1. **Tổng quan:** xem nguồn đang dùng, số điểm/số đo và phiên bản RAW_EC. PostgreSQL hiện có 2 trạm/927 số đo; snapshot có 12 điểm/977 số đo. Thí nghiệm và danh mục cống có nguồn riêng.
2. **Quan trắc:** chọn Mỹ Tho hoặc Tân Châu trên danh sách/bản đồ; lọc ngày; xem EC, nguồn và CSV. Bật/tắt lớp nền, ranh giới, tọa độ RIA2 tham khảo hoặc cống có tọa độ. Điểm RIA2 chỉ có trong bộ đóng gói hiện tại; viền đứt thể hiện CRS giả định.
3. **Ngưỡng:** nhập giá trị EC, mục đích và nguồn/giả định. Màu đỏ nghĩa mẫu mới nhất đạt/vượt ngưỡng tự nhập; xanh nghĩa thấp hơn. Biểu đồ quan trắc và dự báo có đường ngang tương ứng. Bỏ ngưỡng để trở lại chế độ xem nguồn tọa độ. Đây là đối chiếu, chưa phải ngưỡng an toàn cây trồng/cấp nước.
4. **Lịch sử DB:** ngay trong Quan trắc, nhấn kết nối; chọn nguồn → trạm → phiên bản → thời gian/QA/O-E → tải. Xem biểu đồ, chuyển trang và xuất toàn bộ dữ liệu đúng bộ lọc đã tải.
5. **Dự báo EC đa biến:** từ trạm, mở mục dự báo; chọn tháng, nạp mưa/nhiệt/gió ERA5 tháng `t−2` rồi chạy Random Forest. Xem kết quả, nguồn đầu vào, sai số lịch sử và đưa kết quả lên bản đồ. Mô hình đã lưu chạy suy luận trực tiếp. Mô hình EC trễ và ước tính CSV cũ nằm riêng để tham khảo. Xem [mô hình đa biến](multivariate-forecast.md).
6. **Hồ sơ cống:** chọn công trình; nhập thời điểm, mục tiêu, EC và mực nước hai phía, hệ cao độ, cơ sở EC và các giới hạn. Chạy mô phỏng để xem điều kiện đạt/chặn/dải chuyển tiếp và lý do. Lưu nháp theo mã cống rồi khôi phục trên cùng trình duyệt; xuất hoặc nạp input/policy JSON để trao đổi kịch bản. Các ô ngưỡng để trống cho người dùng nhập căn cứ phù hợp.
7. **Chất lượng dữ liệu:** xem hồ sơ tiếp nhận và bằng chứng còn thiếu. Hồ sơ tiếp nhận giữ riêng với quan trắc đã nạp.

Ngưỡng đối chiếu và nháp cống lưu trên trình duyệt, chưa có đồng bộ nhiều người dùng. DB hiện chưa có cống có tọa độ; lớp cống/đường nối ứng viên sẽ hiển thị khi có dữ liệu thật phù hợp. Mô hình khí tượng có thể tính dự báo mới; EC mới cần để đánh giá và cập nhật chất lượng. Vận hành thực tế cần ngưỡng và hồ sơ công trình được thẩm định.
