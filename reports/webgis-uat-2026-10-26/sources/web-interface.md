# Giao diện và chức năng WebGIS hiện tại

Ngày ghi nhận: 23/10/2026. Ảnh chụp từ ứng dụng đang chạy tại `http://127.0.0.1:8000/workspace.html`, chế độ PostgreSQL. Các ảnh trích vùng được cắt từ ảnh chụp toàn trang; ảnh gốc được giữ cùng thư mục.

**Cập nhật sau khi tích hợp các tệp người dùng gửi:** web đã bổ sung danh mục ngưỡng minh họa, so sánh lượt dự báo trong phiên, lịch sử dự báo PostgreSQL và lưu/khôi phục bản nháp cống PostgreSQL. Hai ảnh dưới đây ghi nhận lần tích hợp mới; các ảnh đánh số 01–06 giữ lại giao diện trước lần bổ sung này. Xem [hướng dẫn lưu trữ mới](dss-storage.md) và [luồng dự báo hiện tại](multivariate-forecast.md).

## Tính năng vừa tích hợp từ các tệp người dùng gửi

![Dự báo và lịch sử PostgreSQL sau khi tải lại trang](screenshots/current-web/14-lich-su-du-bao-postgresql.jpg)

Lịch sử đã giữ lượt dự báo Mỹ Tho tháng 11/2026, EC 17,331 mS/m, phiên bản `20261023T041813Z`, sau khi tải lại trang. Người dùng có thể lọc theo trạm/tháng, mở đầu vào từng lượt, xuất JSON hoặc đưa kết quả lên bản đồ. Nút lưu chạy lại mô hình phía máy chủ rồi lưu đầy đủ đầu vào và kết quả gốc. Bảng so sánh trong phiên có thể xuất CSV và chỉ so chênh lệch trong cùng trạm, tháng, phiên bản mô hình.

![Nháp cống PostgreSQL có dự báo tháng đính kèm](screenshots/current-web/15-ho-so-cong-postgresql.jpg)

Bản nháp #1 của cống `DT_PLIII_001` đã được khôi phục từ PostgreSQL sau khi tải lại trang. Dự báo tháng nằm trong phần tham khảo riêng; bốn ô quan trắc tại cống vẫn trống. Mẫu ngưỡng có ghi chú nguồn và hai cận lấy/ngừng minh họa; thông tin chưa được xác minh thành quy trình vận hành.

Migration `30_dss_storage` đã được áp dụng vào cơ sở dữ liệu local ngày 23/10/2026, tạo ba bảng chức năng trong schema `dss_reference` cùng bảng theo dõi migration. Chức năng ghi đã được bật trong `.env` local. Tổng số quan trắc trong `public.conductivity_observation` vẫn là 927. Không cần chạy lại tệp SQL trong Downloads.

## Mô tả hệ thống để sử dụng trong tiểu luận

Hệ thống WebGIS hỗ trợ tra cứu quan trắc độ dẫn điện EC theo không gian và thời gian, kết hợp dự báo EC theo tháng bằng mô hình đa biến tại Mỹ Tho và Tân Châu. Người dùng có thể chọn trạm trên bản đồ, xem lịch sử quan trắc và nguồn dữ liệu, lựa chọn tháng dự báo, cung cấp đầu vào khí tượng, chạy mô hình và xuất kết quả. Mỗi dự báo ghi nhận các biến đầu vào, thời điểm phát hành, phiên bản mô hình và kỳ huấn luyện để thuận tiện truy xuất.

Giao diện sử dụng tông xanh đậm, nền sáng, các khối nội dung theo nhiệm vụ và thanh điều hướng chung cho năm mục. Backend tổ chức thành API, service, repository và domain; frontend chia thành các module chức năng. Các entry point `research` giữ tương thích với đường dẫn cũ.

Phần quan trắc đang đọc PostgreSQL/PostGIS. Khí tượng, mô hình đã huấn luyện và kết quả đánh giá được lưu bằng tệp có thông tin nguồn và phiên bản. Vì vậy, chế độ PostgreSQL không có nghĩa mọi thành phần của ứng dụng đều được lưu trong cơ sở dữ liệu.

## 1. Tổng quan

![Giao diện tổng quan](screenshots/current-web/01-tong-quan.jpg)

**Chú thích hình:** Không gian làm việc WebGIS với thống kê độ phủ và nguồn dữ liệu đang phục vụ.

Các chức năng hiện có:

- Hiển thị chế độ nguồn dữ liệu, số điểm quan trắc, số mẫu EC, ngày đo gần nhất và số trạm có mô hình đa biến.
- Cung cấp liên kết đến tra cứu quan trắc, chạy dự báo và xem nguồn dữ liệu.
- Hiển thị phiên bản dữ liệu đang được chọn cho từng trạm và nút kiểm tra PostgreSQL.

Trong ảnh, PostgreSQL phục vụ **2 trạm, 927 quan trắc**, gồm 464 mẫu Tân Châu và 463 mẫu Mỹ Tho. Mẫu gần nhất là 15/12/2023. Chỉ số RIA2 bằng 0 do các mẫu RIA2 chưa nhập vào nguồn PostgreSQL đang chọn; bộ snapshot riêng có 12 điểm và 977 mẫu.

## 2. Quan trắc, bản đồ và lịch sử PostgreSQL

![Bản đồ trạm và lớp dự báo](screenshots/current-web/04-du-bao-tren-ban-do.jpg)

**Chú thích hình:** Tra cứu trạm trên nền bản đồ và hiển thị EC dự báo bằng lớp riêng tại vị trí trạm.

Các chức năng hiện có:

- Tìm kiếm, chọn điểm quan trắc và xem nguồn, số mẫu, ngày đo gần nhất.
- Phóng to, thu nhỏ, quay về vùng nghiên cứu; bật/tắt bản đồ nền, ranh giới, điểm RIA2 tham khảo và cống có tọa độ trong nguồn.
- Nhập ngưỡng EC để đối chiếu màu điểm và đường ngang trên biểu đồ.
- Xem thông tin EC mới nhất, lọc khoảng ngày, xem biểu đồ, bảng số đo và nguồn từng dòng; tải CSV của lựa chọn.
- Chuyển từ trạm đang xem sang dự báo EC đa biến tại đúng trạm.
- Đưa kết quả dự báo lên bản đồ bằng vòng xanh dương và nhãn tháng mục tiêu; giữ riêng giá trị quan trắc và thời điểm đo.

![Biểu đồ quan trắc](screenshots/current-web/02b-bieu-do-quan-trac.jpg)

**Chú thích hình:** Lịch sử mẫu EC tại Mỹ Tho trong giai đoạn 2022–2023, kèm bộ lọc ngày và thao tác xuất dữ liệu.

![Bộ lọc lịch sử PostgreSQL](screenshots/current-web/02c-lich-su-postgresql.jpg)

**Chú thích hình:** Chọn nguồn, trạm, phiên bản dữ liệu và bộ lọc để truy vấn lịch sử EC trong PostgreSQL.

Phần lịch sử PostgreSQL hỗ trợ lọc chất lượng, loại quan trắc/ước tính (O/E), phân trang và xuất CSV. Mỗi trạm sử dụng một phiên bản RAW_EC được chọn rõ ràng; không trộn các lần nhập chồng nhau. Lỗi DB được thông báo, không âm thầm chuyển sang snapshot.

Ngưỡng **6,001 mS/m trong ảnh là giá trị tự nhập đang có trong phiên trình duyệt**, không phải ngưỡng an toàn đã được xác nhận. Mẫu mới nhất của các trạm có thể khác ngày. Điểm tham khảo và lớp ranh giới giữ các ghi chú về nguồn và tọa độ.

## 3. Dự báo EC đa biến

![Form và kết quả dự báo đa biến](screenshots/current-web/03-du-bao-da-bien.jpg)

**Chú thích hình:** Chạy mô hình dự báo EC theo tháng từ lượng mưa, nhiệt độ, tốc độ gió và chu kỳ mùa vụ.

Luồng đã triển khai:

1. Chọn Mỹ Tho hoặc Tân Châu.
2. Chọn tháng cần dự báo EC.
3. Chọn khí tượng lưu trữ hoặc nhập dữ liệu khí tượng thủ công.
4. Chạy suy luận bằng mô hình Random Forest đã lưu của trạm.
5. Xem EC dự báo, nguồn đầu vào, đơn vị, phiên bản mô hình, kỳ huấn luyện và độ quan trọng của biến.
6. Tải JSON/CSV hoặc xem kết quả trên bản đồ.

Dự báo tháng `t` sử dụng tổng mưa, nhiệt độ trung bình và tốc độ gió trung bình tháng `t−2`, cộng hai biến chu kỳ tháng sin/cos. Mô hình này không yêu cầu số đo EC trễ mới để chạy suy luận. Dữ liệu nhập tay được ghi rõ là nguồn do người dùng cung cấp.

Ví dụ được chạy và chụp trong tài liệu:

| Thông tin | Giá trị |
| --- | --- |
| Trạm | Mỹ Tho |
| Tháng dự báo | 11/2026 |
| Tháng khí tượng đầu vào | 09/2026 |
| Tổng lượng mưa | 313 mm |
| Nhiệt độ trung bình | 27,857 °C |
| Tốc độ gió trung bình | 2,261 m/s |
| EC dự báo | **17,331 mS/m** |
| Phiên bản mô hình | `20261023T041813Z` |

![Biểu đồ đánh giá mô hình](screenshots/current-web/03b-danh-gia-mo-hinh.jpg)

**Chú thích hình:** So sánh EC thực đo với Random Forest và Persistence trên 24 tháng đánh giá 2022–2023; bảng hiển thị thêm Seasonal Naive và trung bình theo tháng.

Phần đánh giá cho phép xem MAE/RMSE và biểu đồ thực đo–dự báo. Các thí nghiệm EC trễ cũ vẫn có trong một mục thu gọn riêng. Ảnh toàn trang có đủ bảng đầu vào, độ quan trọng của biến và các nút xuất kết quả: [xem ảnh đầy đủ](screenshots/current-web/03-du-bao-da-bien-day-du.jpg).

Mô hình hiện tại chưa vượt mọi phương pháp đối chiếu. Nhãn EC huấn luyện kết thúc 12/2023; dự báo mới chưa có EC thực đo cùng kỳ để xác nhận độ chính xác. MAE/RMSE là sai số lịch sử, không phải khoảng tin cậy cho từng kết quả dự báo.

## 4. Chất lượng và tiếp nhận dữ liệu

![Rà soát chất lượng dữ liệu](screenshots/current-web/05-chat-luong-du-lieu.jpg)

**Chú thích hình:** Rà soát độ phủ, xuất xứ và số đo theo vị trí trước khi tiếp nhận vào quan trắc hoặc huấn luyện.

Các chức năng hiện có:

- Xem hồ sơ tiếp nhận và thống kê độ phủ theo trạm.
- Xem tên tệp, dấu kiểm tra SHA-256 và các vấn đề cần rà soát.
- Chọn điểm đo sông/nội đồng, xem ngày, giờ/kỳ đo, đơn vị và nguồn từng dòng.
- Giữ riêng số đo độ mặn g/L với EC mS/m; ô thiếu không được thay bằng 0.
- Xem chuỗi ước tính khí tượng hồi cứu 2024–2026 và tải CSV trong phần tham khảo.

Ảnh ghi nhận hồ sơ có 640 dòng tại 47 trạm và các cảnh báo về lag, nhãn ngày kế tiếp, vị trí đo. Đây là dữ liệu tiếp nhận chưa xác minh; chưa tự động trở thành dữ liệu huấn luyện. Chuỗi ước tính dùng khí tượng cùng tháng được phân biệt với luồng dự báo đa biến tháng mới.

## 5. Hồ sơ cống — chức năng bổ trợ

![Hồ sơ cống](screenshots/current-web/06-ho-so-cong.jpg)

**Chú thích hình:** Tra cứu danh mục công trình và biểu mẫu thông tin phục vụ rà soát hồ sơ cống.

Các chức năng hiện có:

- Chọn công trình từ danh mục có tài liệu gốc và đọc danh mục cống trong PostgreSQL.
- Nhập EC trong/ngoài, mực nước, thời điểm đo, hệ cao độ, cơ sở EC và ngưỡng kịch bản.
- Minh họa quy tắc lấy nước/thoát nước theo dữ liệu khai báo.
- Lưu, khôi phục bản nháp trên trình duyệt; tải mẫu, nạp hồ sơ JSON và xuất kết quả.
- Với cống PostgreSQL có tọa độ, truy vấn trạm ứng viên theo khoảng cách.

Đây là phần bổ trợ của WebGIS. Trọng tâm dự báo là mục EC đa biến. Chức năng hồ sơ chưa phát lệnh đóng/mở cống và khoảng cách không chứng minh trạm đại diện về thủy lực cho cống. [Ảnh toàn trang](screenshots/current-web/06-ho-so-cong-day-du.jpg) cho thấy đầy đủ biểu mẫu và danh sách thông tin thiếu.

## Luồng trình bày đồ án

**Tổng quan → Quan trắc → Chọn trạm → Dự báo EC đa biến → Chọn tháng và đầu vào → Chạy mô hình → Xem kết quả/bản đồ → Xuất JSON hoặc CSV.**

Mục chất lượng dữ liệu dùng để giải thích nguồn và giới hạn; hồ sơ cống là phần mở rộng. Hệ thống giữ EC theo mS/m, chưa tự chuyển thành độ mặn hoặc khuyến nghị vận hành cống.

## Trạng thái lưu trữ

| Thành phần | Nguồn hiện tại |
| --- | --- |
| Trạm, nguồn, dataset, quan trắc EC | PostgreSQL: `public.data_source`, `public.measurement_site`, `public.source_dataset`, `public.conductivity_observation` |
| Khí tượng đa biến | Tệp ERA5/Open-Meteo, đã tải 1985–09/2026 |
| Mô hình từng trạm và kết quả đánh giá | Artifact trong `runs/multivariate_ec/` và registry |
| Kết quả dự báo mới | Giao diện và JSON/CSV; nút lưu tạo một lượt dự báo máy chủ và lưu toàn bộ payload vào `dss_reference.multivariate_prediction_log` |
| Hồ sơ tiếp nhận | Tệp riêng; chưa tự nhập vào quan trắc/huấn luyện |
| Bản nháp hồ sơ cống | Bộ nhớ cục bộ của trình duyệt hoặc các phiên bản trong `dss_reference.gate_simulation_drafts` |
| Danh mục ngưỡng minh họa | `dss_reference.ec_threshold_presets`, giữ trạng thái chưa xác minh |

Phần lưu trữ mới sử dụng migration bổ sung riêng, không thay schema quan trắc `public`; xem hướng dẫn DSS. Muốn cải thiện và đánh giá dự báo hiện tại cần tiếp nhận thêm EC thực đo sau năm 2023.

Hướng dẫn mô hình và cập nhật dữ liệu: [multivariate-forecast.md](multivariate-forecast.md).
