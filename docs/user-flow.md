# Luồng trình bày đồ án

Cập nhật luồng RF_compact và bản đồ ngày 01/11/2026. Các số lượng nguồn dưới đây là mô tả bộ dữ liệu, không phải xác nhận kết nối DB mới. Chạy `.\start.ps1 -Mode postgres` để dùng PostgreSQL hoặc `.\start.ps1 -Mode snapshot` để mở bộ đóng gói có 12 điểm. `.\start.ps1` mặc định chọn PostgreSQL. Trang chính: `http://127.0.0.1:8000/workspace.html`.

1. **Tổng quan:** xem nguồn đang dùng, số điểm/số đo và phiên bản RAW_EC. Snapshot có 12 điểm/977 số đo (927 MRC và 50 RIA2); chế độ PostgreSQL trả số lượng theo DB và phiên bản được chọn tại thời điểm truy cập. Thí nghiệm và danh mục cống có nguồn riêng.
2. **Quan trắc:** chọn Mỹ Tho hoặc Tân Châu trên danh sách/bản đồ; lọc ngày; xem EC, nguồn và CSV. Bật/tắt lớp nền, ranh giới, tọa độ RIA2 tham khảo hoặc cống có tọa độ. RIA2 có thể được đọc từ DB sau bước đồng bộ riêng; tọa độ tham khảo trên bản đồ vẫn không trở thành hình học DB đã xác minh.
3. **Ngưỡng:** nhập giá trị EC, mục đích và nguồn/giả định. Màu đỏ nghĩa mẫu mới nhất đạt/vượt ngưỡng tự nhập; xanh nghĩa thấp hơn. Biểu đồ quan trắc và dự báo có đường ngang tương ứng. Bỏ ngưỡng để trở lại chế độ xem nguồn tọa độ. Đây là đối chiếu, chưa phải ngưỡng an toàn cây trồng/cấp nước.
4. **Lịch sử DB:** ngay trong Quan trắc, nhấn kết nối; chọn nguồn → trạm → phiên bản → thời gian/QA/O-E → tải. Xem biểu đồ, chuyển trang và xuất toàn bộ dữ liệu đúng bộ lọc đã tải.
5. **Dự báo EC đa biến:** từ trạm, mở mục dự báo; chọn tháng, nạp mưa/nhiệt/gió ERA5 tháng `t−2` rồi chạy Random Forest. Xem kết quả, nguồn đầu vào, sai số lịch sử, đưa kết quả lên bản đồ hoặc tải JSON/CSV. Có thể chạy và lưu vào PostgreSQL khi kho DSS được cấu hình, rồi lọc/xem lịch sử. Mô hình đã lưu chạy suy luận trực tiếp. Thí nghiệm hồi cứu, gồm RF_compact Mỹ Tho, và ước tính CSV cũ nằm riêng để tham khảo. Xem [mô hình đa biến](multivariate-forecast.md).
6. **Hồ sơ cống:** chọn công trình; nhập thời điểm, mục tiêu, EC và mực nước hai phía, hệ cao độ, cơ sở EC và các giới hạn. Chạy mô phỏng để xem điều kiện đạt/chặn/dải chuyển tiếp và lý do. Lưu nháp theo mã cống rồi khôi phục trên cùng trình duyệt; có thể lưu vào PostgreSQL khi kho DSS được cấu hình. Xuất hoặc nạp input/policy JSON để trao đổi kịch bản. Các ô ngưỡng để trống cho người dùng nhập căn cứ phù hợp.
7. **Chất lượng dữ liệu:** xem hồ sơ tiếp nhận và bằng chứng còn thiếu. Hồ sơ tiếp nhận giữ riêng với quan trắc đã nạp.

Ngưỡng đối chiếu và nháp trình duyệt được giữ cục bộ; chức năng lưu dự báo/nháp PostgreSQL dùng kho DSS riêng, xem [cấu hình lưu trữ](dss-storage.md). Bốn hồ sơ cống trong workspace khác phạm vi với 27 công trình có tọa độ của lớp mô phỏng; không suy ra hình học hoặc trạng thái vận hành thật của DB từ lớp mô phỏng. Mô hình khí tượng có thể tính dự báo mới; EC mới cần để đánh giá và cập nhật chất lượng. Vận hành thực tế cần ngưỡng và hồ sơ công trình được thẩm định.

## Đọc đúng hai luồng dự báo

Form dự báo trực tiếp ở bước 5 dùng **Random Forest 300 cây, năm biến**: hai biến mùa và mưa/nhiệt/gió tháng `t−2`. Nó suy luận từ model đã lưu. Cập nhật các thí nghiệm RF_compact trong workspace không thay model của form này.

Khi mở phần kết quả hồi cứu của Mỹ Tho, hai thí nghiệm `MYTHO_MONTHLY_LAG0` và `MYTHO_MONTHLY_LAG30` dùng **RF_compact 100 cây, tám biến** có lưu lượng Kratie và mực nước Tân Châu. Độ trễ nhãn thực sự được giả định là +5 và +35 ngày. Đọc kết quả theo thứ tự:

1. Xem protocol, ngày phát hành giả định và nguồn. Dự báo 2022–2023 giữ nguyên từ kết quả nghiên cứu; đây là giai đoạn đã từng được xem, không phải kiểm định mù.
2. Đối chiếu thực đo, RF_compact và baseline trên cùng tháng; MAE/RMSE và biểu đồ được tạo lại từ chính các dòng dự báo đó. Nhóm EC cao trong artifact dùng P90 cố định của nhãn có sẵn tại lần phát hành validation đầu tiên, không phải nhóm mùa khô hay ngưỡng điều hành cống.
3. Hiểu rằng RF_compact được chọn theo validation 2019–2021 với giả định chính +5 ngày. Run +35 giữ nguyên lựa chọn để đánh giá độ nhạy, không lựa chọn lại mô hình.
4. Nếu xem dự báo sau mẫu cuối, tháng đích hiện là **01/2024**, với phát hành giả định 06/12/2023. Giá trị được fit/tính từ đầu vào đúng giả định thời gian; đây là dự báo nghiên cứu lưu trữ, không phải dự báo cho ngày hiện tại.
5. Khi cần truy nguồn, đối chiếu `predictions.csv`, `metrics.csv`, `high_ec_metrics.csv`, `next_forecast.json`, biểu đồ và `run_manifest.json` trong artifact. MAE tổng thể thấp hơn baseline không đủ để kết luận sẵn sàng vận hành; cần xem sai số mùa khô và các đỉnh EC.

## Dải màu trên sông

Dải màu (ribbon) chia mỗi đoạn đường sông theo tỷ lệ **khoảng cách địa lý tích lũy**, rồi nội suy EC ở trung điểm từng phần. Các đỉnh hình học gốc nằm trong phần được giữ lại, tránh việc mật độ đỉnh không đều làm màu thay đổi sai vị trí. Đây là sửa cách hiển thị mô phỏng; không biến dải màu thành số đo thực tế hoặc bằng chứng truyền mặn đến cống.

Chi tiết thay đổi và tiến trình kiểm tra được ghi riêng tại [cập nhật logic và tiến trình 01/11/2026](cap_nhat_logic_va_tien_trinh_2026-11-01.md). Tài liệu luồng này không xác nhận đã chạy thêm trình duyệt, DB hoặc kiểm thử mới.
