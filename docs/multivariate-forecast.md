# Sử dụng dự báo EC đa biến

Luồng chính nằm ở `workspace.html#forecasts`. Chọn Mỹ Tho hoặc Tân Châu, chọn tháng, giữ nguồn khí tượng lưu trữ rồi bấm **Chạy dự báo đa biến**. Nút xem bản đồ đưa kết quả về đúng trạm; JSON/CSV chứa mã dự báo, phiên bản model và các đầu vào thực sự đã dùng.

## So sánh và lưu lịch sử

Mỗi lượt chạy được thêm vào bảng so sánh trong phiên. Chênh lệch EC được tính so với lượt đầu có cùng trạm, tháng và phiên bản mô hình; bảng có thể xuất CSV và sẽ mất khi tải lại trang.

Nút **Chạy và lưu dự báo vào PostgreSQL** gửi lại yêu cầu gốc để máy chủ chạy mô hình và lưu toàn bộ kết quả do máy chủ tạo. Kết quả hiển thị được cập nhật theo lượt đã lưu, với mã và thời điểm phát hành riêng. Đây không phải thao tác nhận một giá trị EC do trình duyệt tự khai báo. Thay đổi đầu vào sẽ vô hiệu hóa thao tác lưu kết quả cũ.

Mục **Lịch sử dự báo đã lưu trong PostgreSQL** cho lọc trạm/tháng, phân trang, xem đầu vào, tải JSON và đưa từng kết quả lên bản đồ. Lịch sử lưu cả số chưa làm tròn, nguồn khí tượng, phiên bản mô hình, kỳ huấn luyện và sai số trong payload. API bổ sung: `GET/POST /api/v1/workspace/multivariate/history` và `GET /api/v1/workspace/multivariate/history/{prediction_id}`. Cấu hình DB: [dss-storage.md](dss-storage.md).

Chức năng đính kèm vào hồ sơ cống giữ dự báo tháng ở phần tham khảo riêng. Nó không tự điền EC ngoài cống hoặc thời điểm quan trắc và không xác lập quan hệ thủy lực giữa trạm và cống.

## Mô hình đang phục vụ

- Mỗi trạm có một Random Forest 300 cây, độ sâu tối đa 8, lá tối thiểu 3 mẫu, seed 42. Pipeline được lưu cùng manifest và checksum; API chỉ chạy suy luận.
- Ba biến môi trường: tổng mưa tháng (mm), nhiệt độ trung bình tháng (°C), trung bình tốc độ gió 10 m trung bình ngày (m/s). Hai biến sin/cos biểu diễn mùa vụ của tháng mục tiêu.
- Dữ liệu khí tượng là ERA5 qua Open-Meteo, có phản hồi gốc, đơn vị, múi giờ Việt Nam, URL và SHA. Đã tải 1985–09/2026 cho cả hai trạm. Giữ nguyên dữ liệu khí tượng cũ riêng vì chưa xác minh đơn vị gió của bộ đó.
- Dự báo tháng `t` dùng khí tượng đầy đủ tháng `t−2`; không dùng thời tiết thực tế trong tháng cần dự báo. Ví dụ tháng 11/2026 dùng đầu vào 09/2026, giả định đã sẵn có từ sau 05/10. Độ trễ công bố năm ngày là giả định nghiên cứu.
- Nhãn EC: 463 tháng Mỹ Tho và 464 tháng Tân Châu, tổng 927 mẫu MRC, kết thúc 12/2023. Cờ chất lượng nguồn được giữ nguyên. Mô hình này dùng khí tượng và mùa vụ nên không yêu cầu EC trễ mới khi dự báo.

Đầu vào thủ công phải cùng cách tổng hợp và đơn vị với mô hình. Kết quả ghi `input_mode=MANUAL`; đây là dự báo có điều kiện theo dữ liệu người dùng cung cấp. API từ chối tháng nằm trong tập đã dùng huấn luyện cuối cùng.

## Tải mô hình và phân tán giữa các cây

Máy chủ thử nạp trước hai mô hình trong vòng đời khởi động. Bộ nhớ đệm giữ phần giải tuần tự artifact, theo đường dẫn và nội dung đã kiểm tra; mỗi lần truy cập vẫn kiểm tra SHA-256 mô hình/manifest và hợp đồng trạm/biến. Không huấn luyện hoặc tải khí tượng khi khởi động. Nếu nạp trước thất bại, máy chủ ghi cảnh báo và request dự báo vẫn kiểm tra lại artifact. Không cam kết thời gian cố định cho lượt dự báo; API hiện chưa trả số đo thời gian chạy.

Kết quả mới có `ensemble_distribution`: P10/P25/P50/P75/P90, IQR, độ lệch chuẩn và số cây, tính từ dự đoán của từng cây trên cùng đầu vào đã biến đổi của pipeline. Đây là **phân tán giữa các cây**, chưa phải khoảng dự báo hay khoảng tin cậy được hiệu chuẩn, không bao gồm toàn bộ sai số khí tượng, sai lệch mô hình hoặc thay đổi theo thời gian. Giá trị EC chính vẫn là dự đoán của toàn bộ Random Forest, không bị thay bằng trung vị cây. JSON và CSV kết quả giữ các trường phân phối; lịch sử cũ có thể chưa có trường này.

Bảng cây trồng chỉ đối chiếu EC với ba cặp ngưỡng minh họa dùng chung với bản đồ: sầu riêng 50/80, cây có múi 100/150 và lúa 120/200 mS/m. Dưới ngưỡng thấp vẫn cần đo kiểm tại nơi lấy nước; các ngưỡng chưa là tiêu chuẩn tưới. Không suy ra chất lượng nước sinh hoạt từ EC hoặc dự báo tháng. Lớp mô phỏng bản đồ có quy đổi độ mặn theo giả định riêng; kết quả dự báo đa biến giữ nguyên EC, không tự quy đổi sang g/L.

## Đánh giá và giới hạn

Đánh giá theo thời gian: huấn luyện đến 2018 để xem 2019–2021; huấn luyện đến 2021 để đánh giá hồi cứu 2022–2023. Mô hình phục vụ sau đó được fit lại trên toàn bộ nhãn đến 2023. Các baseline Persistence, Seasonal Naive và trung bình theo tháng được so trên cùng cohort.

RF chưa vượt mọi baseline tại cả hai trạm. Giao diện công bố sai số từng mô hình; MAE/RMSE không phải khoảng tin cậy của một kết quả cụ thể. Dự báo giai đoạn 2026 chưa có EC thực đo cùng kỳ để đánh giá; EC mới cần cho kiểm chứng và cập nhật mô hình. Giá trị EC giữ mS/m, không tự chuyển thành độ mặn hoặc quyết định tại cống.

## Cập nhật và tái tạo

Trong PowerShell tại gốc dự án, dùng `.venv` hiện có:

```powershell
# Cập nhật tháng khí tượng hoàn chỉnh gần nhất; không sửa tệp nguồn cũ
.venv\Scripts\python.exe scripts/update_multivariate_weather.py

# Chỉ huấn luyện lại khi cần đổi dữ liệu / phiên bản mô hình
.venv\Scripts\python.exe scripts/train_multivariate_ec.py

# Mở ứng dụng
.\start.ps1 -Mode postgres
```

Model được lưu dưới `runs/multivariate_ec/`; registry ở `data/models/multivariate_registry.json`. Runtime phải cùng phiên bản scikit-learn ghi trong manifest (bản hiện tại: 1.9.1). Các API ở `/api/v1/workspace/multivariate/`: `catalog`, `inputs`, `predict`, `evaluation`.

Mã được chia theo chức năng: `backend/domain/multivariate_ec.py`, `backend/repositories/multivariate_inputs.py`, `backend/services/multivariate.py`, `backend/api/multivariate.py`, `frontend/src/features/multivariate-forecast.js`. Các script tải và huấn luyện chạy ngoài request web.
