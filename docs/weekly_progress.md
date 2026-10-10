# Tiến độ dự án — cập nhật 08/10/2026

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

## Phần còn lại tại thời điểm 02/10/2026

Chưa kết nối PostgreSQL, chưa xác minh topology/nguồn/ngày hiệu lực ranh giới, chưa hoàn thiện phương pháp backtest, chưa tạo API hoặc giao diện bản đồ.

Công việc kế tiếp: đối chiếu trạm/snapshot trong DB, xây API đọc trạm và lịch sử EC; sau đó nối bản đồ chọn trạm với biểu đồ có đơn vị, khoảng thời gian, cờ chất lượng và nguồn.

## Bằng chứng bổ sung từ máy người thực hiện

Người thực hiện đã cung cấp phản hồi thành công của API health trên database `dongthap_gis`, GeoJSON hai trạm có tọa độ, danh sách snapshot và API phân trang quan trắc. Các snapshot có 464 dòng Tân Châu, 463 dòng Mỹ Tho, đều giữ `UNVERIFIED`. Đây là bằng chứng người thực hiện gửi; lần rà soát 08/10 không truy cập trực tiếp database trên máy Windows.

## Đợt bổ sung mô hình, nguồn dữ liệu và phát lại lịch sử

Đã bổ sung mô hình EC đa biến và mô-đun hỗ trợ đánh giá điều kiện cống ở bước trước; đợt này kiểm tra hồi quy và mở rộng bằng các nội dung sau:

1. Tải lại khí tượng ERA5 có request/response, tọa độ ô lưới, đơn vị, múi giờ và hash; giữ master gốc. Huấn luyện lại mô hình tháng ở hai trạm. Chưa có kết quả cho phép kết luận thêm biến luôn tốt hơn baseline.
2. Tạo và chạy thí nghiệm không nhận thêm nhãn EC trong 36 tháng sau ba mốc lịch sử. Ghi nhận giới hạn dự báo khi thiếu nhãn; không gọi đầu ra năm 2026 là đã được kiểm chứng bằng nhãn thật.
3. Tải dữ liệu GFZ Sơn Đốc: 18.336 dòng gốc, 18.300 dòng đạt kiểm tra cấu trúc, 36 dòng cách ly. Huấn luyện/đánh giá dự báo độ mặn trước 2/6/12 giờ, có baseline và kịch bản độ trễ công bố 0/2/6 giờ.
4. Truy xuất API công khai MRC. Đối chiếu EC với master: 0 sai khác. Bổ sung 500 cặp EC–nhiệt độ nước trùng timestamp; vẫn chưa xác nhận được cơ sở bù nhiệt EC.
5. Tải 3.630 số đo mực nước tự động Tân Châu đến 05:00 ngày 08/10/2026, giờ Việt Nam, và 246 số đo thủ công đến 07:00 ngày 06/10. Giữ riêng chuỗi, timestamp và cờ nguồn; chưa triển khai thu thập liên tục.
6. Tạo contract và chương trình kiểm tra quan hệ trạm–cống. Khoảng cách gần không tự đủ để chấp nhận quan hệ đại diện; chưa có cống thực địa được xác minh qua mô-đun này.
7. Bổ sung API chỉ đọc kết quả hồi cứu và trang `frontend/replay.html`, có chọn chân trời, thanh thời gian, biểu đồ, nguồn và chế độ đối chiếu với quan trắc.

Bằng chứng: `runs/research_step07/`, `runs/sondoc_forecast/`, `runs/label_gap_era5/`, `runs/forecast_era5/`, cùng manifest trong `data/external/`. Chi tiết phương pháp, kết quả và nguồn tại [research_step07.md](research_step07.md).

## Kiểm thử và phạm vi hoàn thành

Đạt 69 kiểm thử Python và 16 kiểm thử JavaScript; build frontend thành công. Đã kiểm tra HTTP thực tế qua backend và Vite proxy, phản hồi 200 và đúng hành vi ẩn/hiện số đo đối chiếu. Log tại `runs/verification_step07/`.

Chưa xác nhận hiển thị bằng trình duyệt trên máy người thực hiện; chưa kiểm thử kết nối mới với PostgreSQL của người thực hiện. API phát lại phục vụ dự báo lịch sử đã tính sẵn, chưa phải API suy luận hiện tại. Mô hình Sơn Đốc là trường hợp nghiên cứu phương pháp tại địa điểm khác, chưa đại diện cho các cống Đồng Tháp.

Khoảng sai số danh nghĩa 90% của mô hình 6 giờ, kịch bản độ trễ 0, chỉ bao phủ khoảng 66,4% quan trắc test. Dữ liệu EC MRC tải được vẫn kết thúc 15/12/2023. Còn thiếu metadata bù nhiệt, nhãn mới tại địa điểm mục tiêu, hồ sơ cống, quan hệ thủy văn, mực nước hai phía cùng chuẩn và policy có nguồn. Các thiếu sót này chưa được coi là đã khép lại.

## Việc kế tiếp

Đưa từng file vào repo và chạy trang phát lại trên máy theo [step07_install_and_evidence.md](step07_install_and_evidence.md), chụp minh chứng thật. Sau khi mốc này chạy ổn, hoàn thiện hồ sơ và số đo cho một cống thí điểm để đánh giá tính đại diện và chất lượng khuyến nghị.
