# Giao thức nhãn EC tháng cho sổ phát hành — v1.0

**Lập ngày 14/11/2026, trước khi hệ thống nhận phiếu thực địa đầu tiên.** Mã bất biến: `MONTHLY_EC_LABEL_V1_20261114`. Thay đổi tiêu chí chỉ có hiệu lực cho các bản phát hành/chấm điểm sau khi tạo phiên bản giao thức mới; không chọn lại nhãn cũ theo sai số đã thấy.

Sổ phát hành mở ngày 14/11/2026; lịch đầu tiên đủ điều kiện là 06/12/2026 cho tháng mục tiêu 01/2027. Không tạo bản phát hành hồi tố cho lịch 06/11/2026 hoặc trước đó.

## Định nghĩa nhãn

- Trạm: MYTHO (`MRC_VN_019805`), MYTHUAN (`MRC_VN_019804`), TANCHAU (`MRC_VN_019803`). Mỗi `(trạm, tháng mục tiêu)` có tối đa một nhãn theo giao thức này.
- Ưu tiên MRC: dùng EC tháng do MRC công bố đúng trạm, có ngày quan trắc trong tháng đích, đơn vị mS/m, giá trị hữu hạn không âm, cờ QA không phải `INVALID` và loại quan trắc `O`. Nếu có nhiều bản nguồn MRC hợp lệ, chọn dataset có `imported_at` sớm nhất (hòa thì `dataset_code` tăng dần); trong dataset đó chọn ngày gần 15 nhất, sau đó thời điểm đo và ID quan trắc tăng dần. Quy tắc này cố định trước khi xem dự báo, không chọn bản có sai số thấp nhất. EC của snapshot cũ không được dùng làm kết quả vận hành mới nếu đã có trong dữ liệu huấn luyện.
- Phiếu thực địa chỉ xét nếu không có nhãn MRC mới đủ điều kiện. Phiếu phải `APPROVED`, cùng tháng đích, vị trí cách tọa độ trạm MRC tối đa **2 km**, đo từ **ngày 13 đến hết ngày 17**, từ **09:00 đến trước 16:00** giờ `Asia/Ho_Chi_Minh`. Chỉ nhận vị trí `RIVER`, không nhận mẫu trong đồng/cống.
- Thiết bị phải có mã định danh và bằng chứng hiệu chuẩn trong **30 ngày trước phép đo**. Giá trị phải quy về **EC25** bằng chức năng bù nhiệt có chứng từ của thiết bị; nếu thiết bị chỉ cho EC tại nhiệt độ tại chỗ hoặc không rõ chế độ bù nhiệt, phiếu có thể lưu/hiển thị nhưng không là nhãn chấm điểm. Cần ít nhất **2 mẫu độc lập** từ cùng trạm trong cửa sổ trên, cách nhau tối thiểu 30 phút; nhãn là trung vị EC25 của tất cả mẫu hợp lệ. Nếu hai mẫu chênh nhau quá 20% so với trung vị, không tạo nhãn và chuyển kiểm tra thủ công theo giao thức mới.
- `observation_ref` của nhãn field là hash danh sách `measurement_id` đã sắp xếp và phiên bản giao thức. Nhãn MRC tham chiếu `dataset_code` và ID quan trắc. Một issue chỉ có **một** điểm cho mỗi `label_protocol_version` bằng `UNIQUE(issue_id,label_protocol_version)`; `observation_ref` lưu nguồn đã chọn, không nằm trong khóa UNIQUE.

## Giới hạn và công bố

Nhiệt độ quy chiếu của chuỗi EC MRC lịch sử chưa được xác nhận. Điểm từ MRC và điểm từ phiếu EC25 phải báo cáo riêng theo `obs_source`; không gộp để khẳng định sai số tương đương cho đến khi có nghiên cứu đối chiếu. Điểm `ON_TIME` là MAE vận hành chính; `LATE` báo cáo riêng. Nếu chưa có nhãn đủ điều kiện, hiện “chưa có dữ liệu chấm”; việc sổ phát hành hoạt động không phải kết quả kiểm định độ chính xác.
