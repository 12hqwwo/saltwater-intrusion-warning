# Tiến độ dự án — cập nhật 01/11/2026

## Đợt cập nhật logic và artifact ngày 01/11/2026

Đã hoàn thành sửa gói kết quả nghiên cứu RF_compact và cách thể hiện gradient sông. Chi tiết ở [bản tổng hợp thay đổi logic và tiến trình](cap_nhat_logic_va_tien_trinh_2026-11-01.md), trạng thái phân biệt từng nhánh ở [current_state.md](current_state.md).

1. Hai packer dùng chung `scripts/rf_compact_artifacts.py`; giữ nguyên dự báo hồi cứu nguồn, kiểm tra nhãn/số mẫu/ngày có dữ liệu trước khi đóng gói. Tính lại metric và nhóm EC cao thay cho hằng số; không huấn luyện lại toàn bộ lịch sử.
2. Tái tạo manifest, workspace và biểu đồ từ đúng bảng dự báo RF_compact. Ghi hash nguồn, hash đầu ra và liên kết hash giữa biểu đồ với bảng dự báo; bỏ việc dùng biểu đồ của một run khác.
3. Tính thực dự báo lưu trữ tháng 01/2024 tại ngày phát hành giả định 06/12/2023: **27,903151 mS/m (+5 ngày)** và **22,022199 mS/m (+35 ngày)**. Đây không phải dự báo hiện tại. Ngày as-of được tuần tự hóa tại đầu ngày **UTC+7**, chỉ có độ phân giải ngày; không khẳng định giờ công bố thật.
4. Giữ RF_compact được chọn từ validation 2019–2021 của kịch bản chính +5 ngày. +35 ngày chỉ đánh giá độ nhạy với cùng ứng viên, không chọn lại theo kết quả của kịch bản phụ. Các giá trị dự báo lịch sử được bảo toàn khi sửa metadata.
5. Nội suy màu dải sông theo khoảng cách tích lũy dọc hình học, tránh gradient lệch do mật độ đỉnh. Phần sửa hiển thị không xác minh kết nối sông–kênh–cống và không tạo dữ liệu cho nhánh chưa mô phỏng.

**Bằng chứng đợt mã nguồn:** bộ Python chạy 73 kiểm thử, bỏ qua 1, kết quả OK. Sau đó riêng bộ kiểm tra packer chạy 6 kiểm thử đạt; chưa chạy lại toàn bộ Python sau khi bổ sung kiểm tra artifact. JavaScript đạt 85 kiểm thử; build frontend thành công với 247 module. Kiểm tra API nhận HTTP 200, kiểm tra hash artifact đạt. Không có lần kiểm tra DB, trình duyệt hoặc triển khai mới. Lần cập nhật Markdown này không chạy lại các kiểm tra đó.

**Phạm vi còn thiếu:** nhãn EC MRC kết thúc 12/2023; timeline mô phỏng không gian đến 08/2026; quan hệ thủy lực tới cống chưa xác minh. RF_compact nghiên cứu (100 cây, 8 biến) vẫn riêng với nhánh suy luận đang phục vụ qua registry (RF 300 cây, 5 biến). Chưa bổ sung EC thực đo 2024–2026 hoặc bằng chứng để dùng dự báo làm lệnh cống. Cần tiếp tục thu thập nhãn mới, xác minh kết nối và kiểm định ngoài mẫu trước khi tăng vai trò vận hành.

---

## Nhật ký lịch sử đến 08/10/2026

> Nội dung bên dưới giữ nguyên mốc lịch sử; các kết quả DB và kiểm thử không phải kiểm chứng lại ngày 01/11/2026. Một số đường dẫn thành phần đã loại bỏ chỉ còn trong bản sao lưu; xem [README hiện tại](../README.md) để chạy ứng dụng. Giữ nội dung đánh giá để truy vết.

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

Bằng chứng được ghi trong nhật ký cũ: `runs/research_step07/`, `runs/sondoc_forecast/`, `runs/label_gap_era5/`, `runs/forecast_era5/`, cùng manifest trong `data/external/`. Nhật ký từng dẫn `research_step07.md` về phương pháp, kết quả và nguồn; tài liệu đó không có trong checkout hiện tại, cần bản lưu để đối chiếu.

## Kiểm thử và phạm vi hoàn thành

Đạt 69 kiểm thử Python và 16 kiểm thử JavaScript; build frontend thành công. Đã kiểm tra HTTP thực tế qua backend và Vite proxy, phản hồi 200 và đúng hành vi ẩn/hiện số đo đối chiếu. Log tại `runs/verification_step07/`.

Chưa xác nhận hiển thị bằng trình duyệt trên máy người thực hiện; chưa kiểm thử kết nối mới với PostgreSQL của người thực hiện. API phát lại phục vụ dự báo lịch sử đã tính sẵn, chưa phải API suy luận hiện tại. Mô hình Sơn Đốc là trường hợp nghiên cứu phương pháp tại địa điểm khác, chưa đại diện cho các cống Đồng Tháp.

Khoảng sai số danh nghĩa 90% của mô hình 6 giờ, kịch bản độ trễ 0, chỉ bao phủ khoảng 66,4% quan trắc test. Dữ liệu EC MRC tải được vẫn kết thúc 15/12/2023. Còn thiếu metadata bù nhiệt, nhãn mới tại địa điểm mục tiêu, hồ sơ cống, quan hệ thủy văn, mực nước hai phía cùng chuẩn và policy có nguồn. Các thiếu sót này chưa được coi là đã khép lại.

## Việc kế tiếp

Kế hoạch ở mốc 08/10 là đưa từng file vào repo và chạy trang phát lại trên máy theo `step07_install_and_evidence.md`, chụp minh chứng thật. Tài liệu hướng dẫn đó không có trong checkout hiện tại. Sau khi mốc này chạy ổn, kế hoạch là hoàn thiện hồ sơ và số đo cho một cống thí điểm để đánh giá tính đại diện và chất lượng khuyến nghị. Việc tiếp theo của đợt hiện tại được ghi ở phần cập nhật 01/11 đầu trang.
