# Kế hoạch 4 tuần để chốt đồ án và báo cáo

Ngày lập: 28/10/2026 (UTC+7). Mốc dự kiến: 25/11/2026; điều chỉnh nếu lịch nộp thực tế khác. Kế hoạch này dùng trạng thái mã và artifact tại checkout ngày lập, không coi tài liệu tiến độ cũ là kết quả kiểm tra mới.

## Đích nghiệm thu

Một bản WebGIS chạy lại được, một báo cáo có bảng/biểu đồ truy được đến dữ liệu và mã, một kịch bản demo 5–7 phút. Phạm vi định lượng chính: EC mS/m tại Mỹ Tho và Tân Châu, dự báo mẫu EC theo tháng, đánh giá hồi cứu cùng baseline. **Hỗ trợ rà soát kịch bản đóng/mở cống** là chức năng ứng dụng riêng: hiển thị cống và ngưỡng, kiểm tra hồ sơ EC/mực nước hai phía, trả trạng thái sàng lọc và phần bằng chứng còn thiếu. Chưa có dữ liệu tại cống để xác nhận quyết định vận hành; mô phỏng không phát lệnh đóng/mở. Dữ liệu sau 2023 chưa có nhãn EC MRC để kiểm định dự báo hiện tại.

Mỗi kết luận định lượng trong báo cáo cần nêu trạm, khoảng thời gian, đơn vị, số mẫu, baseline, phiên bản artifact và giới hạn. Các con số ở giao diện, báo cáo và artifact phải khớp. Không dùng kết quả nghiên cứu FES ngày 26/10 làm mô hình phục vụ: trên Mỹ Tho, thêm FES không giảm MAE so với cấu hình khí tượng + tháng trên validation 2019–2021 hoặc holdout hồi cứu 2022–2023.

## Tuần 1 — 28/10–03/11: khóa phạm vi và chứng cứ

1. Lập bản kiểm kê một phiên bản: Git commit, trạng thái thay đổi chưa commit, nguồn dữ liệu, checksum, registry mô hình, cấu hình runtime. Phân loại thay đổi đang làm dở trước khi đóng gói; không ghi đè hoặc xóa artifact.
2. Chạy bộ kiểm thử Python và JavaScript, build; xử lý ca treo/thất bại có nguyên nhân cụ thể. Thử UI thật ở desktop và màn hình hẹp: quan trắc → dự báo → bản đồ → hồ sơ cống → xuất tệp. Với hồ sơ cống, thử mục tiêu lấy nước và thoát nước, trường hợp thiếu số đo, ngưỡng chuyển tiếp và trạng thái bị chặn; xác nhận không có lệnh vận hành. Ghi ảnh hoặc video màn hình cùng ngày, chế độ dữ liệu và phiên bản.
3. Kiểm tra một luồng PostgreSQL đọc và một luồng lưu dự báo/nháp qua UI; ghi rõ nếu môi trường không sẵn. Đối chiếu số mẫu DB với số mẫu phiên bản được phục vụ, không gộp hai khái niệm.
4. Chốt ma trận tuyên bố: phần đã kiểm chứng, phần chỉ mô phỏng, phần thiếu dữ liệu. Kiểm tra 27 cống có tọa độ trong lớp mô phỏng thuộc danh mục Tiền Giang; bốn cống Đồng Tháp chưa có tọa độ. Chỉ dùng cống trong demo như ví dụ minh họa khi chưa xác minh quan hệ thủy lực.
5. Viết ngay bản thảo mục tiêu, phạm vi, nguồn dữ liệu và phương pháp; tạo danh sách hình/bảng sẽ dùng trong báo cáo.

**Cửa nghiệm thu 03/11:** demo một vòng không lỗi chặn; có log test/build và bằng chứng UI; có danh sách chính xác các tuyên bố được phép viết; bản thảo 30–40% báo cáo. Nếu UI có lỗi nhỏ về thẩm mỹ, ghi lại và ưu tiên sửa sau lỗi dữ liệu/nguồn/sai nghĩa.

## Tuần 2 — 04/11–10/11: chốt đánh giá khoa học

1. Từ `predictions.csv` và manifest của cùng cohort, tạo bảng MAE/RMSE theo từng trạm và baseline, số mẫu, train/validation/holdout. Kiểm lại phép tính độc lập; chọn 2–3 đồ thị giải thích mùa vụ và các tháng sai số lớn.
2. Viết phân tích lỗi của Mỹ Tho và Tân Châu, đặc biệt các mẫu EC cao. Phân biệt RF đang phục vụ với ứng viên nghiên cứu `RF_compact`: ở Mỹ Tho, backtest theo ngày phát hành +5 ngày cho 2022–2023 có MAE RF cũ 18,63, `RF_compact` 11,07 và Persistence 12,62 mS/m; sáu tháng EC cao 2019–2021 vẫn có MAE 259,37 mS/m ở ứng viên. Tân Châu cần báo riêng RF cũ và ứng viên theo đúng giao thức.
3. Chốt thí nghiệm FES là kết quả âm có giá trị: bảng cùng tập tháng, quy tắc chọn trên validation, giới hạn dữ liệu triều biển thiên văn. Không tiếp tục thử nhiều biến chỉ để tối ưu trên holdout đã xem.
4. Viết phần phương pháp, kết quả và thảo luận; mỗi hình/bảng có nguồn, đơn vị, thời đoạn và cách tái lập. Soát câu chữ ở UI nếu còn gợi ý dự báo tại cống hoặc quyết định vận hành đã kiểm chứng.

**Cửa nghiệm thu 10/11:** 100% bảng/đồ thị chính tái tạo được; báo cáo đủ bản thảo phần phương pháp và kết quả; không còn kết luận vượt bằng chứng. Nếu không có EC mới đạt QA, đóng băng phạm vi đánh giá tại dữ liệu hiện có.

## Tuần 3 — 11/11–17/11: hoàn chỉnh báo cáo và demo

1. Hoàn tất các chương giới thiệu, dữ liệu, thiết kế hệ thống, phương pháp, kết quả, thảo luận, giới hạn và kết luận. Vẽ sơ đồ kiến trúc, luồng dữ liệu và màn hình chính từ phiên bản đang chạy.
2. Đối chiếu từng câu định lượng với bảng nguồn; thống nhất EC mS/m, các mốc thời gian và tên trạm. Chú thích mô phỏng 1D, hệ số EC–độ mặn, tọa độ cống và trạng thái dự báo sau 2023.
3. Thử cài/chạy theo hướng dẫn trên môi trường sạch khả thi hoặc ít nhất từ phiên terminal mới; chuẩn bị phương án demo snapshot khi DB local không sẵn, với nhãn nguồn rõ. Soát bảo mật tệp đóng gói để không kèm `.env` và mật khẩu.
4. Gửi bản thảo cho giảng viên/người phản biện nếu có kênh và lịch phù hợp; ghi nhận góp ý thành danh sách sửa có mức ưu tiên. Chuẩn bị slide ngắn và luyện demo 5–7 phút.

**Cửa nghiệm thu 17/11:** bản báo cáo đầy đủ vòng 1, hình/bảng và trích dẫn khớp, demo lặp lại được, có danh sách góp ý và lỗi còn lại.

## Tuần 4 — 18/11–24/11: rà soát và đóng gói

1. Sửa góp ý theo thứ tự: sai kết luận khoa học → sai dữ liệu/nguồn → lỗi chạy → trình bày. Đóng băng tính năng mới, trừ lỗi chặn nghiệm thu.
2. Người khác đọc thử báo cáo hoặc tự kiểm tra theo checklist: câu hỏi nghiên cứu, phương pháp đánh giá theo thời gian, so sánh baseline, giới hạn, đóng góp, tài liệu tham khảo, khả năng tái lập.
3. Chạy lại kiểm thử, build và demo trên bản cuối; lưu log, ảnh màn hình, commit/manifest, phiên bản báo cáo và slide. Kiểm tra các liên kết hình và bảng, mục lục, số trang, chính tả.
4. Dự phòng ít nhất 1 ngày trước mốc 25/11 để xuất PDF, xem toàn bộ trang và nộp theo yêu cầu thực tế.

**Cửa nghiệm thu 24/11:** bản nộp mở được, không thiếu hình/bảng, mã chạy được theo hướng dẫn, có log xác nhận trên đúng phiên bản, slide và demo khớp báo cáo.

## Quy tắc ưu tiên khi thiếu thời gian

Giữ thứ tự: (1) tính đúng và truy nguồn của dữ liệu/kết luận; (2) luồng demo không lỗi; (3) báo cáo hoàn chỉnh và dễ hiểu; (4) thẩm mỹ. Dừng mở rộng sang dự báo cho cống khác, vận hành cống thật, bề mặt mặn liên tục hoặc mô hình FES phục vụ nếu chưa có dữ liệu kiểm định tương ứng. Một kết quả âm được giải thích trung thực tốt hơn một tính năng mới thiếu kiểm chứng.

## Trạng thái kiểm tra lúc lập kế hoạch

- JavaScript: 35/35 ca qua, gồm kiểm thử mới cho geometry cống; build Vite thành công (28/10).
- Python: 48/48 ca qua sau khi cố định line ending của nguồn OSM theo checksum provenance (28/10). TestClient cần socket nội bộ nên lượt xác nhận chạy ngoài sandbox; thông báo `Database error` là đầu ra của ca thử nhánh lỗi DB, không phải ca thất bại.
- Checkout có thay đổi chưa commit ở dữ liệu v3, bản đồ, runner, mã và kết quả thí nghiệm FES. Chúng thuộc công việc đang dở; cần rà soát trước khi chốt phiên bản.
- Đã khởi tạo [bản thảo nội dung báo cáo](bao_cao_ban_thao_2026-10-28.md) để viết song song với kiểm chứng giao diện.
- UI snapshot đã được mở trên trình duyệt local: Tổng quan và Quan trắc tải dữ liệu; chạy dự báo Mỹ Tho tháng 11/2026 với đầu vào 09/2026 trả 17,331 mS/m, đưa lên bản đồ đúng trạm và giữ timeline ở 08/2026. Lượt thử không lưu PostgreSQL. Nhãn mô phỏng cống đã sửa để không trình bày thành khuyến nghị vận hành. Chưa kiểm tra giao diện màn hình hẹp và luồng ghi PostgreSQL thật.

Tham chiếu hiện trạng: [tiến trình 25/10](tien_trinh_web_2026-10-25.md), [trạng thái 24/10](current_state.md), [kế hoạch ứng dụng](implementation-plan.md), [thí nghiệm FES 26/10](../outputs/fes_ec_multipoint_20261026/README.md).
