# Kiểm thử WebGIS Đồng Tháp – Tiền Giang

Ngày kiểm thử: **26/10/2026**, giờ Việt Nam. Bản web thực tế: [Mở WebGIS đang chạy](http://127.0.0.1:8000/workspace.html).

Đã khởi động bản build của dự án với **PostgreSQL/PostGIS thật**, thao tác trên cả 5 mục chính, chạy dự báo bằng mô hình thật, tải tệp từ giao diện và chụp màn hình đang được phục vụ. Không sửa mã ứng dụng trong đợt này.

## Kết quả kiểm thử

| Nhóm kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- |
| Bộ kiểm thử Python sẵn có | 41/41 đạt, 57,541 giây | [Nhật ký Python](python-tests.log) |
| Bộ kiểm thử JavaScript sẵn có | 34/34 đạt | [Nhật ký JavaScript](javascript-tests.log) |
| Kiểm tra HTTP bổ sung trên server và DB thật | 37/37 đạt | [Kết quả API](live-api-results.json), [mã kiểm tra](live_api_checks.py) |
| Kịch bản thao tác giao diện | 23 mục ghi nhận đạt | [Kết quả UI](ui-results.json) |
| Quyền PostgreSQL và audit trigger | Cả reader/writer đạt; các phép ghi thử được rollback | [Kết quả bảo mật](database-security-verification.json) |

Tổng cộng **112 kiểm tra tự động đạt**. Các kịch bản UI và kiểm tra phân quyền DB được ghi riêng, không cộng trùng vào 112. Những phép thử đầu vào sai trả về 403/404/422 theo kỳ vọng, không được tính là lỗi hệ thống.

## Các luồng nghiệp vụ đã thực hiện

| Màn hình / luồng | Thao tác và kết quả quan sát | Ý nghĩa nghiệp vụ | Ảnh |
| --- | --- | --- | --- |
| Tổng quan | Kiểm tra kết nối DB; hiển thị 12 điểm, 977 số đo, 50 mẫu RIA2, 2 trạm dự báo; ngày mẫu gần nhất 11/11/2025 | Biết phạm vi dữ liệu đang thực sự được phục vụ | [01](screenshots/01-tong-quan.png) |
| Quan trắc trên bản đồ | Xem danh sách 12 trạm, chi tiết Mỹ Tho, đơn vị EC và g/L quy đổi; bản đồ chỉ hiện 2/12 điểm có tọa độ | Phân biệt dữ liệu có trong danh mục với dữ liệu có thể định vị | [02](screenshots/02-ban-do-2016-03.png), [12](screenshots/12-quan-trac-mytho-2023.png) |
| Timeline và cắt dọc | Với ngưỡng 100/150 mS/m: 03/2016 có 27 cống rủi ro; 10/2022 có 27 thuận lợi; 04/2024 có 14 thuận lợi, 2 cần đo kiểm, 11 rủi ro | So sánh không gian và mùa vụ trong cùng một kịch bản | [03](screenshots/03-mua-lu-cat-doc-do-man.png), [18](screenshots/18-mua-kho-2024-ve-tinh.png) |
| Điều khiển bản đồ | Đổi nền tối/vệ tinh/OSM; bật tắt hạt dòng chảy, gió và cống; phát 4x thấy tháng tiến; chuyển mục làm dừng phát; khôi phục 1x | Kiểm tra tương tác bản đồ và quản lý thời gian | [20](screenshots/20-ban-do-cuoi-kiem-thu.png) |
| Kiểm tra ngưỡng | Nhập 150/150 bị chặn với thông báo ngưỡng lấy nước phải nhỏ hơn ngưỡng ngăn mặn; khôi phục 100/150 | Tránh phân loại theo một cặp ngưỡng mâu thuẫn | [19](screenshots/19-nguong-khong-hop-le.png) |
| Bản đồ → hồ sơ cống | Chọn Bảo Định, thử kịch bản lấy nước rồi chuyển hồ sơ; giữ mã GATE_TG_002 và tháng 2022-10, ghi SIMULATION/UNVERIFIED; thiếu mực nước và cơ sở EC vẫn được thể hiện | Chuyển tham khảo không gian sang bước kiểm tra điều kiện cụ thể | [04](screenshots/04-cong-bao-dinh-mo-phong.png), [05](screenshots/05-ho-so-tu-ban-do-thieu-du-lieu.png) |
| Hồ sơ cống: lấy nước | Dữ liệu giả định tại DT_PLIII_001: mực ngoài 1,2 m, trong 0,5 m, EC ngoài 80 và trong 70 mS/m; điều kiện nhập cho kết quả CONDITIONS_MET. Đổi EC ngoài thành 150 → BLOCKED | Kiểm tra đồng thời chiều chênh mực nước và ngưỡng chất lượng nước | [06](screenshots/06-cong-intake-dat-dieu-kien.png), [07](screenshots/07-cong-ec-150-bi-chan.png) |
| Hồ sơ cống: thoát nước và nháp | DRAIN với ngoài 0,2 m, trong 0,8 m, EC ngoài 200 và cho phép thoát khi EC ngoài cao → CONDITIONS_MET. Lưu/khôi phục nháp trình duyệt; lưu PostgreSQL #7 rồi sửa và khôi phục đúng EC=150 | Kiểm tra sự khác nhau giữa lấy nước/thoát nước và khả năng lưu tiếp công việc | [08](screenshots/08-cong-drain-va-nhap-postgres.png) |
| Xuất và nhập JSON cống | Xuất input DRAIN, tải policy mẫu, nạp cả hai qua bộ chọn tệp; policy mẫu chưa có ngưỡng/cơ sở EC/hệ cao độ → INVALID_INPUT, liệt kê đúng phần thiếu; tải JSON kết quả thành công, khôi phục nháp cục bộ | Không chấp nhận quy trình chưa khai báo đủ; tệp input xuất riêng không bao gồm toàn bộ policy | [21](screenshots/21-nap-json-quy-trinh-thieu.png) |
| Dự báo Mỹ Tho | Chọn 11/2026, khí tượng 09/2026: mưa 313 mm, nhiệt 27,857°C, gió 2,261 m/s → EC 17,331 mS/m; lưu DB, mở đánh giá 24 tháng | Kết quả có đầu vào và phiên bản để truy vết | [09](screenshots/09-du-bao-mytho-va-danh-gia.png), [10](screenshots/10-lich-su-du-bao-postgres.png) |
| Dự báo Tân Châu và thủ công | Lưu trữ 11/2026 → 13,709 mS/m; đầu vào thủ công 200 mm, 28°C, 2 m/s → 12,433 mS/m. Bảng so sánh có 3 lượt; thay đầu vào xóa kết quả cũ và khóa đưa lên bản đồ | So sánh kịch bản, tránh dùng nhầm kết quả cũ | [16](screenshots/16-du-bao-thu-cong-va-so-sanh.png) |
| Dự báo thiếu khí tượng | Chọn 01/2027 khi thiếu khí tượng 11/2026 → thông báo thiếu dữ liệu, nút chạy và xem bản đồ bị khóa | Không tự tạo đầu vào chưa có | [17](screenshots/17-du-bao-thieu-khi-tuong.png) |
| Dự báo → lịch sử → bản đồ | Mở lại kết quả đã lưu, tải JSON/CSV và đưa lên bản đồ; banner ghi tháng dự báo 11/2026 khác timeline nền 08/2026 | Không nhầm dự báo điểm với kịch bản toàn sông | [11](screenshots/11-du-bao-tren-ban-do.png) |
| Lọc quan trắc và xuất | Mỹ Tho năm 2023 có 12/463 mẫu; CSV đúng 12 dòng. Năm 2026 có 0 mẫu và khóa xuất | Giữ đúng số đo gốc, không biến thiếu dữ liệu thành quan trắc | [12](screenshots/12-quan-trac-mytho-2023.png) |
| Lịch sử PostgreSQL | Chọn nguồn MRC, trạm Tân Châu, toàn thời gian; 464 mẫu. Trang 1 là 1–20, trang 2 là 21–40; xuất khi ở trang 2 vẫn đủ 464 dòng | Phân biệt phân trang hiển thị với toàn bộ kết quả lọc | [13](screenshots/13-lich-su-postgresql-phan-trang.png) |
| Ước tính hồi cứu | Tân Châu có 32 tháng 01/2024–08/2026, trung bình 16,96; cao nhất 25,299 mS/m ở 05/2024; mở bảng chi tiết | Xem chuỗi ước tính có nhãn hồi cứu và giới hạn kiểm chứng | [14](screenshots/14-uoc-tinh-hoi-cuu.png) |
| Chất lượng và nguồn dữ liệu | 640 dòng/47 trạm, 387 nhãn ngày kế tiếp, 138 dòng đủ nhóm biến; 53 lag1 lệch, 5 dòng cần tách sông/nội đồng; 890 giá trị rà soát, 21 ô bị loại. Đổi điểm sang Xuân Hòa, mở SHA-256 | Đánh giá khả năng dùng dữ liệu và truy về nguồn từng dòng | [15](screenshots/15-chat-luong-va-truy-nguon.png) |

Các điều kiện đạt trong hồ sơ cống là **kết quả mô phỏng với dữ liệu giả định**, không xác nhận số đo thực tế, không phê duyệt vận hành. API mô phỏng giữ `actuator_command=null` và `gate_decision_eligible=false`.

## Những gì kiểm tra backend bổ sung đã xác nhận

- Danh mục 12 trạm khớp tổng 977 số đo của phiên bản đang phục vụ; từng dòng có mã trạm, đơn vị mS/m và giá trị hữu hạn.
- Timeline có 495 tháng từ 06/1985 đến 08/2026; mỗi frame đã thử có 35 đoạn sông và 27 cống.
- Chặn khoảng ngày đảo ngược, tháng sai định dạng, tháng thiếu, ngưỡng bằng nhau, trạm không có, mưa âm, đầu vào thủ công thiếu và dự báo trong kỳ đã dùng huấn luyện.
- Ngoài các trường hợp UI, đã thử EC vùng chuyển tiếp → REVIEW_REQUIRED; chênh mực nước sai chiều → BLOCKED; thoát nước EC cao nhưng không bật ngoại lệ → BLOCKED.
- Yêu cầu ghi khác origin bị từ chối 403; đường tải tệp nhị phân bị cấm trả 404.
- Kiểm tra PostgreSQL thực tế: reader/writer đều không phải admin; bị từ chối sửa/xóa/TRUNCATE bảng quan trắc, sửa/xóa nhật ký và tạo bảng. Writer không đọc được quan trắc; reader không lưu được nháp. Trigger ghi đúng database_actor và application_actor. Các bản ghi thử riêng của script bảo mật đều rollback.
- Console ghi hai cảnh báo kích thước bản đồ bằng 0 khi vùng bản đồ bị ẩn. Không có lỗi mức error trong nhật ký console đã lấy; bản đồ hiển thị được khi mở mục Quan trắc. [Nhật ký console](browser-console.json).

## Hạn chế thực tế so với WebGIS vận hành chuyên nghiệp

Không có một danh sách tính năng duy nhất cho mọi WebGIS “hoàn chỉnh”. Với bài toán cảnh báo xâm nhập mặn và hỗ trợ cống, các khoảng cách quan trọng của bản hiện tại là:

| Khoảng cách | Bằng chứng từ bản đang chạy | Hệ quả và hướng ưu tiên |
| --- | --- | --- |
| Độ mới và độ phủ dữ liệu | MRC kết thúc 12/2023; RIA2 gần nhất 11/11/2025. Chỉ 2/12 trạm có hình học, 10 trạm RIA2 chưa có tọa độ | Ưu tiên xác minh tọa độ, cập nhật EC/mực nước ngoài và trong cống, ghi thời gian lấy mẫu và chất lượng. Chưa thể coi đây là mạng quan trắc thời gian thực |
| Mô hình không gian chưa phải thủy động lực | Tài liệu mô tả IDW theo trục 1D, quy đổi 0,0064 g/L trên 1 mS/m; biên cửa sông dùng hệ số mùa 6 hoặc 1,5 chưa hiệu chỉnh; hình học sơ đồ, liên kết cống chưa xác minh | Màu, hạt chuyển động, ranh mặn và đèn cống chỉ dùng khám phá kịch bản. Muốn dự báo vận hành cần mô hình có triều, lưu lượng, mực nước và kiểm định độc lập |
| Dự báo chưa vượt baseline ở Mỹ Tho | 24 tháng kiểm định 2022–2023: RF MAE 18,318 và RMSE 49,311 mS/m; Persistence MAE 12,621 và RMSE 18,911 mS/m | Chưa nên gọi RF là phương án dự báo tốt nhất. Cần kiểm định thời gian thêm, dữ liệu mới, xem nguyên nhân sai số lớn và công bố so sánh baseline |
| Chưa có kiểm chứng cùng kỳ mới | Chuỗi ước tính 2024–2026 được gắn nhãn hồi cứu; chưa có EC thực đo cùng kỳ để đối chiếu. MAE/RMSE lịch sử không phải khoảng tin cậy của dự báo mới | Cần thu thập nhãn mới và theo dõi sai số sau phát hành trước khi dùng cho quyết định thực địa |
| Tốc độ lần suy luận đầu | Lượt Mỹ Tho đầu tiên mất khoảng 54,55 giây ở môi trường này; lượt Tân Châu sau đó khoảng 0,368 giây | Cần đo thêm sau khởi động lại, cân nhắc nạp sẵn model và thông báo tiến trình. Chưa có phép thử tải đồng thời |
| Quản trị GIS tổng quát | Giao diện đã thử tập trung vào trạm, tuyến sông, cống và nguồn nghiên cứu; chưa chứng minh luồng biên tập hình học/topology, truy vấn không gian buffer/intersection hoặc kết nối WMS/WFS/WMTS | Nếu cần làm nền tảng GIS nhiều ngành, cần khảo sát và bổ sung theo nghiệp vụ; không chỉ thêm các nút bản đồ |
| Vận hành tổ chức và cảnh báo | Đã chứng minh phân quyền DB và ranh giới request; chưa kiểm thử đăng nhập từng người, phân vai/phê duyệt nghiệp vụ, phát cảnh báo và xác nhận xử lý, SSO, sao lưu/phục hồi hoặc HA | Đây là các mục cần thiết kế và nghiệm thu riêng trước triển khai nhiều người dùng. Không suy ra “bảo mật hoàn chỉnh” từ kiểm tra ACL |

Kết luận về mức độ hiện tại: hệ thống đã có **luồng nghiên cứu và tra cứu khá đầy đủ** từ nguồn → quan trắc → mô phỏng → dự báo → lưu/xuất → hồ sơ cống. Nó chưa có đủ bằng chứng để được xem là hệ thống cảnh báo và vận hành cống thời gian thực đã kiểm định.

## Tệp tải thực và thay đổi do kiểm thử

| Tệp | Đã đối chiếu |
| --- | --- |
| [Dự báo Mỹ Tho JSON](downloads/du-bao-mytho-2026-11.json) | Đúng mã dự báo, MyTho, tháng 2026-11, đầu vào 2026-09 và EC 17,3312446527 mS/m |
| [Dự báo Mỹ Tho CSV](downloads/du-bao-mytho-2026-11.csv) | Cùng kết quả JSON; CSV có các dòng đầu vào, không được coi là các lượt dự báo riêng |
| [Quan trắc Mỹ Tho 2023 CSV](downloads/quan-trac-mytho-2023.csv) | 12 dòng dữ liệu |
| [Lịch sử Tân Châu toàn bộ CSV](downloads/lich-su-tanchau-toan-bo.csv) | 464 dòng dữ liệu, dù tải ở trang 2 |
| [Hồ sơ cống giả định](downloads/ho-so-cong-gia-dinh.json) | Input DRAIN với dữ liệu giả định; policy được tải riêng |
| [Quy trình mẫu](downloads/quy-trinh-cong-mau.json) | Template còn trống, được dùng để thử trường hợp thiếu thông tin |
| [Kết quả kiểm tra quy trình thiếu](downloads/ket-qua-quy-trinh-thieu.json) | INVALID_INPUT, không có lệnh vận hành |

Đã lưu **1 lượt dự báo thật** để kiểm tra khả năng đọc lại: `4be2b3e4-7d88-4216-a713-60db1436039b`, Mỹ Tho 11/2026. Lịch sử dự báo sau đó có 2 lượt, gồm lượt có sẵn và lượt kiểm thử này.

Đã lưu **1 nháp cống PostgreSQL #7**, mã DT_PLIII_001, với nguồn ghi rõ `UAT 26/10/2026 - SO LIEU GIA DINH KIEM THU, KHONG PHAI QUAN TRAC`. Nháp này chứa kịch bản EC ngoài 150 mS/m bị chặn. Có lưu nháp cục bộ trong trình duyệt và tải tệp kiểm thử. Không xóa các bản ghi kiểm thử; không sửa số đo quan trắc hay huấn luyện lại mô hình.

Bảng quan trắc trong DB có 1.017 dòng, trong khi bộ nguồn được chọn đang phục vụ 977 dòng. Đây là hai phạm vi khác nhau do DB giữ cả phiên bản nguồn; không phải lỗi cộng tổng của giao diện.

## Phạm vi kết luận

Đợt này bao phủ 5 màn hình chính ở môi trường local PostgreSQL và một trình duyệt, khung hiển thị khoảng 827×715. Bộ test có phần dùng fixture/mock; 37 kiểm tra HTTP bổ sung và thao tác UI dùng server/DB/model thật.

Chưa thực hiện tải đồng thời, mất mạng/khôi phục DB chủ động, kiểm thử thiết bị di động/trình duyệt khác, kiểm thử xâm nhập toàn diện, diễn tập sao lưu hoặc xác nhận khoa học tại thực địa. Nhập JSON đã thử một cặp tệp với policy thiếu; chưa thử mọi schema/tệp hỏng và mọi tổ hợp bộ lọc. Vì vậy, kết quả đạt áp dụng cho các kịch bản được liệt kê, không phải chứng nhận mọi tính năng không có lỗi.

Toàn bộ ảnh trong [thư viện ảnh](index.html) là ảnh chụp web đang phục vụ, không phải mockup. Ảnh dài cho phép xem cả nội dung; ảnh tổng hợp chỉ thu nhỏ/cắt vùng từ ảnh gốc và ghi rõ tính chất này.

## Tài liệu đối chiếu trong dự án

- [Phương pháp và giới hạn mô phỏng không gian](sources/spatial-simulation.md)
- [Mô hình dự báo và kiểm định](sources/multivariate-forecast.md)
- [Luồng giao diện](sources/web-interface.md)
- [Lưu nháp và dự báo PostgreSQL](sources/dss-storage.md)
