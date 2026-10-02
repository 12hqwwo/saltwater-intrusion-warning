# Bộ tọa độ cống phục vụ TLCN WebGIS xâm nhập mặn – Đồng Tháp mới

## Phạm vi
Bộ dữ liệu gồm 15 cống/công trình ưu tiên ở phần địa bàn Tiền Giang cũ, nay thuộc tỉnh Đồng Tháp mới.
12 điểm có tọa độ để hiển thị GIS; 3 điểm được cố ý để trống vì chưa tìm được tọa độ đủ tin cậy.

## CRS
- EPSG:4326 / WGS84
- CSV: X = longitude, Y = latitude
- GeoJSON: [longitude, latitude]

## Ý nghĩa confidence
- High: tọa độ công bố trực tiếp cho công trình. Hiện gồm Vàm Giồng, Cần Lộc và Vàm Tháp.
- High-derived: tọa độ suy ra từ điểm đầu/cuối thủy văn và quan hệ tuyến-cống được văn bản thủy lợi xác nhận. Đây không phải mốc khảo sát tâm cống.
- Medium: quan hệ không gian hợp lý nhưng còn một bước suy luận; phải rà ảnh vệ tinh.
- Pending: công trình được xác nhận tồn tại/quan trọng nhưng chưa có tọa độ đủ chắc chắn; cố ý để trống.

## Quy tắc sử dụng
1. Có thể đưa toàn bộ 12 điểm có tọa độ vào QGIS để tạo lớp khảo sát ban đầu.
2. Trước khi dùng một điểm trong Decision Logic hoặc viết là “tọa độ chính xác của cống”, mở ảnh vệ tinh trong QGIS và snap điểm vào tâm thân cống.
3. Các điểm Medium chỉ dùng để định vị vùng cần kiểm tra, không coi là tọa độ cuối cùng.
4. Không tự điền 3 điểm Pending nếu chưa có bằng chứng bản đồ/tài liệu.
5. Khi import CSV vào QGIS: Layer > Add Layer > Add Delimited Text Layer; X=longitude, Y=latitude; Geometry CRS=EPSG:4326.

## Nguồn chính
- Quyết định 04/2019/QĐ-UBND tỉnh Tiền Giang: mạng kênh, cống, phạm vi bảo vệ công trình thủy lợi.
- Quyết định 12/2023/QĐ-UBND tỉnh Tiền Giang: cập nhật/phân cấp danh mục công trình thủy lợi.
- Thông tư 18/2017/TT-BTNMT: danh mục địa danh dân cư, sơn văn, thủy văn, kinh tế-xã hội tỉnh Tiền Giang, dùng để đối chiếu tọa độ đầu/cuối sông, rạch, kênh.
- Các bản tin/phương án hạn–mặn địa phương để xác nhận vai trò thực tế của một số cống.

## Lưu ý học thuật
Bộ này là lớp “candidate sluice gates” phục vụ giai đoạn tuần 3. Chỉ điểm có nguồn trực tiếp mới được gọi là tọa độ công bố; các điểm High-derived/Medium phải được mô tả đúng phương pháp suy ra trong luận văn.


## Cập nhật xác minh trực tiếp
- Cống Vàm Giồng: 10°18′7,2″N; 106°32′52,4″E.
- Cống Cần Lộc: 10°24′16,6″N; 106°45′19,6″E.
- Cống Vàm Tháp: 10°24′29,1″N; 106°45′37,4″E.
Ba tọa độ trên xuất hiện trực tiếp trong báo cáo kết quả quan trắc môi trường 2020; các điểm này đồng thời có dữ liệu độ dẫn điện (EC) trong chương trình quan trắc.
