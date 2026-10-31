# Rà soát bốn luồng WebGIS — 28/10/2026

Phạm vi: kiểm tra và sửa tính nhất quán của tháng, nguồn, đơn vị, loại kết quả và trạng thái sau khi thay đổi lựa chọn. Giữ nguyên dữ liệu nguồn và mô hình đã huấn luyện.

| Luồng | Lỗi cụ thể đã sửa | Hành vi sau sửa |
| --- | --- | --- |
| Quan trắc | Phản hồi chưa được đối chiếu trạm/đơn vị/ngày/nguồn; mẫu E có thể mang nhãn quan trắc; bộ lọc mới vẫn giữ bảng và CSV cũ | Kiểm tra hợp đồng phản hồi; tách mẫu ước tính E; xóa kết quả và khóa CSV ngay khi sửa ngày; phản hồi trạm cũ không được ghi vào lựa chọn mới |
| Bản đồ quan trắc | Nhãn điểm có thể lấy EC đầu vào mô phỏng trong khi màu đối chiếu dùng mẫu mới nhất; đổi đơn vị mô phỏng cũng đổi mẫu nguồn sang g/L | Giá trị điểm, danh sách và thẻ trạm giữ EC mS/m và ngày riêng của mẫu nguồn; lớp sông/cống có đơn vị mô phỏng riêng |
| Mô phỏng | Nhãn “dự báo ML” được dùng cho đầu vào hồi cứu; nhãn quan trắc không nói rõ nội suy; tải lại timeline có thể để khung cũ hoàn tất muộn | Hiện rõ tháng và nguồn đầu vào: mẫu nguồn MRC / nội suy / ước tính hồi cứu ERA5; hủy khung cũ ngay khi đổi tháng/ngưỡng/tải lại; kiểm tra tháng và ngưỡng phản hồi |
| Nguồn mô phỏng | Tổng hợp tháng có thể gộp mẫu O/E và INVALID dưới nhãn thực đo; nội suy không giữ đầy đủ danh tính nguồn | Giữ số lượng O/E/UNKNOWN, cờ chất lượng, nguồn/tệp/dataset; loại INVALID khỏi phép tính; mô tả là trung bình các mẫu sẵn có, không khẳng định chuỗi đo liên tục cả tháng |
| Dự báo | Phản hồi sai trạm, tháng t−2, chế độ hoặc đơn vị có thể được nhận; tải danh mục lỗi còn đầu vào cũ; chuỗi đổi trạm có thể phục hồi lựa chọn trước | Đối chiếu trạm/mã trạm/tháng/chế độ/ba biến khí tượng; xóa đầu vào và kết quả không còn hợp lệ; chặn phản hồi cũ; giữ EC bằng 0 là giá trị hợp lệ |
| Dự báo trên bản đồ | Banner và nhãn dự báo tự đổi EC sang độ mặn; tháng dự báo dễ bị lẫn với khung sông nền | Dự báo giữ mS/m; ghi rõ tháng mục tiêu và tháng mô phỏng nền riêng; đổi trạm hoặc tự chọn tháng mô phỏng sẽ bỏ lớp dự báo trước đó |
| Lịch sử và xuất dữ liệu | Bộ lọc mới có thể còn bảng cũ; phản hồi lưu có thể ghi đè ứng viên mới; CSV thiếu đơn vị đầu ra riêng | Xóa bảng khi đổi bộ lọc; kiểm tra danh tính và đơn vị của kết quả đã lưu; lưu là chạy lại trên máy chủ và hiển thị lượt máy chủ trả về; CSV có đơn vị kết quả và đơn vị đầu vào riêng |
| Hồ sơ cống | Đổi cống/nhập tệp/khôi phục nháp có thể nhận đánh giá cũ; mã cống, đơn vị và tháng lồng trong JSON chưa được đối chiếu đủ | Hủy các yêu cầu cũ và xóa kết quả/đường ứng viên; kiểm tra hồ sơ nhập, cặp đầu vào–quy trình, khung chuyển từ bản đồ và phản hồi đánh giá |
| Nguồn EC trong hồ sơ | Nguồn tọa độ danh mục có thể bị dùng làm nguồn EC mô phỏng; người dùng sửa EC nhưng vẫn mang nguồn giá trị từ khung cũ | Tách nguồn vị trí khỏi nguồn mô phỏng; giá trị sửa được ghi USER_SCENARIO, giữ khung tháng gốc riêng để đối chiếu; không tự tạo thời điểm đo cho EC mô phỏng |
| Backend hồ sơ | Có thể nhận đơn vị mực nước sai, schema Boolean hoặc thời điểm không hợp lý | Kiểm tra đơn vị m/mS/m, schema số nguyên, thời điểm đo/sẵn có/lập hồ sơ; giữ khả năng lưu nháp còn thiếu dữ liệu |
| Nguồn mô hình | Danh mục và artifact có thể khác phiên bản trong lúc xử lý | Đối chiếu phiên bản/cutoff; kết quả giữ checksum mô hình và các nguồn huấn luyện liên quan |

Kiểm chứng đã hoàn thành:

- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -q`: **54/54 đạt**. Dòng log lỗi kết nối trong bộ kiểm thử là tình huống kiểm tra lỗi được dựng có chủ đích; kết quả toàn bộ suite là OK.
- `node --test tests/*.test.mjs frontend/src/features/*.test.js`: **82/82 đạt**. Có tình huống phản hồi thành công/thất bại về muộn sau đổi trạm, tháng, bộ lọc, ngưỡng, cống và phiếu; kiểm tra CSV/JSON không dùng kết quả đã bị vô hiệu hóa.
- `npm.cmd --prefix frontend run build`: thành công.
- Trình duyệt trên PostgreSQL tại `http://127.0.0.1:8016`: quan trắc tải đúng nguồn; sửa ngày xóa kết quả/khóa CSV; dự báo Mỹ Tho 11/2026 dùng khí tượng 09/2026; đổi sang g/L chỉ tác động lớp mô phỏng; chuyển tháng mô phỏng bỏ overlay dự báo trước; chuyển khung 03/2016 sang hồ sơ và sửa EC thành 92 mS/m hiển thị rõ giá trị người dùng và giá trị khung gốc; đổi cống xóa phiếu/kết quả trước. Không có cảnh báo/lỗi console trong các thao tác này.
- Không tạo bản ghi kiểm thử trong PostgreSQL; lượt dự báo UI dùng chế độ không lưu. Các trường hợp lưu/khôi phục được kiểm tra bằng mock, không thay dữ liệu người dùng.

Các giới hạn dữ liệu vẫn cần trình bày khi bảo vệ đồ án: mô phỏng không gian chưa được hiệu chuẩn thủy lực; hệ số EC–độ mặn chỉ để minh họa; dữ liệu lịch sử không phải mạng cảm biến thời gian thực; tọa độ tham khảo chưa xác nhận CRS không chứng minh kết nối thủy lực; P10–P90 là độ phân tán giữa các cây, chưa phải khoảng dự báo hiệu chuẩn; hồ sơ cống không phát lệnh vận hành. Các kiểm thử trên xác nhận hành vi phần mềm, không thay thế kiểm định khoa học mô hình.
