# Kiểm toán bộ dữ liệu người dùng cung cấp v3 — 15/10/2026

## Kết luận sử dụng

Tiếp nhận vào vùng kiểm toán riêng `data/external/user_v3_review_20261015`, giữ bản gốc và SHA-256. Chưa nhập vào snapshot/DB hoặc thay kết quả mô hình. UNVERIFIED có nghĩa chưa đủ bằng chứng, không phải kết luận dữ liệu sai. Tuyên bố “kiểm định nguồn 100%” trong workbook chưa được kiểm chứng độc lập.

Hướng triển khai phù hợp: dùng danh mục URL để tìm bảng gốc; chuẩn hóa quan trắc theo **điểm vật lý + đại lượng + chế độ đo + khoảng thời gian** trước khi ghép biến. Giữ nghiên cứu EC MRC riêng. Dữ liệu v3 hữu ích để mở rộng hồ sơ nguồn/công trình và thiết kế luồng dữ liệu; chưa đủ căn cứ công bố mô hình dự báo ngày.

## Số đếm tính lại

- Workbook 14 sheet; 58 dòng danh mục trạm, 190 công trình, 8 quy tắc, 57 nhật ký.
- Độ mặn: 533 dòng sông + 189 dòng nội đồng = 722 dòng; dòng nội đồng có hai vị trí 0m và 200m nên không đồng nghĩa 722 mẫu độc lập.
- CSV có 640 dòng, 47 mã trạm, không trùng khóa trạm-ngày; đối chiếu toàn bộ 29 cột khớp sheet ML sau chuẩn hóa biểu diễn số/trống.
- Chỉ 387 dòng có nhãn ngày kế tiếp; 114 nhãn bằng 0. Chỉ 138 dòng đồng thời đủ nhãn ngày kế tiếp, triều max/min, mực nước kênh và mưa. Đây là số đếm hiện diện ô, chưa phải mẫu được chấp nhận khoa học.
- Chuỗi ngày liên tục dài nhất theo từng trạm không quá 7 ngày. Nhiều điểm nội đồng chỉ có 3 ngày tháng 9 và 5 ngày tháng 10 dù tên split ghi 5/7 ngày.
- GeoJSON có 85 điểm: 58 trạm + 27 cống, không phải 190 cống. 54 EXACT_PLUS_CODE, 2 EXACT_MRC_PORTAL, 16 COMMUNE_REPORTED, 12 LANDMARK_REPORTED và 1 NEARBY_LANDMARK. Các trạng thái là khai báo của tệp, chưa xác minh ngoài nguồn.

## Vấn đề cụ thể

1. **53 lag1 không có giá trị tương ứng đúng ngày trước trong CSV.** Ví dụ ML_0334 (Vàm Môn, 13/05/2024) có lag1 nhưng không có mẫu ngày 12/05. Không được gọi số đo trước đó cách nhiều ngày là lag 1 ngày. Delta hiện khớp phép trừ với lag đã cung cấp nên vẫn bị ảnh hưởng về ý nghĩa thời gian.
2. **Trùng định danh giữa vị trí đo.** Rạch Băng ngày 09–13/10/2026: dòng sông và nội đồng cùng mã ST_SOAIRAP_RACHBANG; ví dụ 09/10 dòng sông 0 g/L, tại cống nội đồng 0,05 và cách cống 200m là 0. ML chọn 0. Không kết luận phải đổi thành 0,05: phải tách các điểm đo trước, không lấy max chung. Năm dòng được đưa vào danh sách cần giải quyết vị trí.
3. **Khác nhau về đại lượng mục tiêu.** DAILY_MAX, FIXED_07H00, cực đại con triều và cực đại mùa đều xuất hiện. Một mẫu 7h không xác định cực đại ngày. Cột target_exceed hiện khớp độ mặn cùng ngày, không phải nhãn vượt ngưỡng ngày mai; không ghép với đầu vào cùng ngày rồi gọi dự báo trước 1 ngày.
4. **141 dòng lịch sử 2016/2020** thuộc HIST_MATCHED_DAY; phần ghi chú có suy ngược bằng chênh lệch với 2026. Phải xác minh cách lấy giá trị và ngày so sánh trên bảng gốc; không mặc định đây là chuỗi quan trắc độc lập đủ để train/test.
5. **Sheet EC có 21 dòng hỗn hợp.** Hai dòng MRC ghi khoảng 1985–2023 với một giá trị EC, không chứa lại 927 mẫu theo ngày. Dòng RIA2 có vùng 10 điểm và khoảng nhiều tháng. WQ_012 là MONITORING_PROGRAM nhưng vẫn có pH/DO/kiềm…; không dùng kế hoạch quan trắc làm số đo.
6. **Biên độ triều bằng 0 tại 50 dòng ML** (25 dòng ngày 21/09 và 25 dòng 13/10). Cần kiểm tra độ đầy đủ đỉnh/chân: max=min của một số đo không chứng minh biên độ triều ngày bằng 0. Chưa xác minh dữ liệu gốc cho trường hợp này.
7. **Split chưa thể dùng như một quy trình đánh giá chung.** TRAIN tháng 9/2026 nằm sau VAL mùa khô 2026. Nếu đây là các thực nghiệm riêng phải khai báo rõ; không huấn luyện gộp rồi đánh giá validation quá khứ. TRAIN_DRY_SEASON_2024 có 49 dòng nhưng không có nhãn ngày kế tiếp nào.
8. **Tọa độ và quy tắc cống:** Plus Code chỉ mã hóa địa điểm, không chứng minh vị trí trạm đo. Cần xác nhận CRS và danh tính; tọa độ xã/địa danh chỉ dùng lớp tham khảo có nhãn. Các quy tắc trích báo chí chưa thay được quy trình vận hành đã phê duyệt, điều kiện áp dụng và quan hệ thủy lực.

## Kiểm tra nguồn và giới hạn

Đã thử mở nguồn PCTT `https://phongchongthientaitiengiang.vn/?p=7360`: 502; PDF RIA2 `https://vienthuysan2.org.vn/wp-content/uploads/2023/07/Xem-tai-day-10.pdf`: 403 qua công cụ web. Đây là lỗi truy cập, không chứng minh nội dung sai. Chưa đối chiếu từng giá trị v3 với bản gốc; không gắn VALIDATED.

## Công việc đã thực hiện và tái lập

`scripts/audit_supplied_v3.py` đọc bằng openpyxl/pandas, không sửa ba tệp gốc. Xuất audit.json, station_coverage.json, row_issues.json và source_urls.json trong thư mục tiếp nhận. Chạy bằng Python có openpyxl/pandas:

```text
python scripts/audit_supplied_v3.py "D:/UNIVERSITY/DOANTOTNGHIEP/TIEULUANCHUYENNGANH/Gemini" --out data/external/user_v3_review_lan_moi
```

Thư mục đầu ra phải mới để tránh ghi đè bằng chứng. Kiểm toán tính nhất quán nội bộ không thay cho xác thực khoa học hoặc kiểm thử DB.

Lượt thu thập ngay trước đó đã tải 22 tài liệu/trang RIA2, gồm 9 tệp gốc đợt 10–18/2025; 5 tệp đợt 10–14 mới so với kho EC cũ. Các bản scan cần đọc bảng và đối chiếu; chưa cộng thành mẫu mới. Luồng tải nằm ở `scripts/collect_observation_archive.py`, kiểm tra nguồn tải bằng `scripts/inspect_observation_archive.py`.

## Thứ tự tiếp theo

1. Tách điểm sông/nội đồng/0m/200m; giữ mã nguồn gốc và thêm định danh đo riêng.
2. Đối chiếu từng giá trị với tệp/bảng gốc, lưu trang/dòng, ngày đo, cửa sổ thống kê, đơn vị và trạng thái.
3. Tạo lại lag/nhãn bằng phép nối ngày lịch và cửa sổ đo đồng nhất; giữ thiếu, không nội suy nhãn.
4. Chỉ thử Persistence trước khi có chuỗi đủ dài và chia thời gian đúng; chưa quảng bá dự báo 1/3/7 ngày từ bộ v3.
