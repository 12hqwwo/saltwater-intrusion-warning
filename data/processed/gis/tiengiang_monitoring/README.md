# Điểm quan trắc EC Tiền Giang — pilot Gò Công

Nguồn: `C:\Users\QUYNH\Downloads\06b1183fcd396396.pdf`, SHA-256
`40539339afc35690e7d75f933f415a5eb2f7f2d9f9aa4f022d76aef733aedfbe`.
Bảng tọa độ nằm ở trang PDF 1–5; các bảng EC ở trang PDF 8, 12, 16, 19, 23.
Từng bản ghi có trường trang nguồn. Đây là bản chép và chuẩn hóa từ PDF, chưa
được xác minh bằng dữ liệu đo đạc gốc.

## Tệp

- `locations_34.csv`: 34 điểm NM1–NM34; DMS gốc, tọa độ thập phân WGS84,
  cờ QA, EC I–IV đơn vị mS/m.
- `ec_campaigns_136.csv`: 34 × 4 bản ghi EC; giữ chuỗi in gốc µS/cm, số
  µS/cm, số mS/m, đợt và trang PDF.
- `pilot_go_cong_8.csv`: NM26, NM28–NM34.
- `coordinate_hypotheses_5.csv`: năm phương án suy luận để đối chiếu;
  `INFERRED_NOT_VERIFIED`, không thay tọa độ Bảng 1.
- `tiengiang_ec_34.xlsx`: cùng dữ liệu, các trang pilot, 34 điểm, EC I–IV,
  phương án tọa độ và thông tin nguồn.
- `tiengiang_ec_34_qa4.gpkg`: ba lớp `sites_34`, `pilot_go_cong_8` và
  `coordinate_hypotheses_5`, CRS EPSG:4326.
- `go_cong_ec_pilot_qa4.qgs`: dự án QGIS đã nạp ba lớp, hiển thị lớp pilot
  tọa độ gốc và lớp giả thuyết màu cam (nhãn dấu `?`).
  Mở tệp này trong QGIS; giữ GeoPackage cùng thư mục để đường dẫn tương đối
  hoạt động. Tệp `_attachments.zip` đi kèm là thành phần do QGIS tạo. Các bản
  trước `_qa4` được giữ lại vì có thể đang mở trong QGIS; chúng thiếu lớp giả thuyết.
- `monitoring_records.json`: dữ liệu trung gian và thông tin nguồn để tạo
  lại các tệp trên.

## Quy tắc xử lý

`EC (mS/m) = EC (µS/cm) / 10`. Dấu chấm hàng nghìn và dấu phẩy thập phân
trong PDF được phân tích theo cách viết Việt Nam. Ví dụ NM26, đợt I:
`19.330 µS/cm = 1.933 mS/m` (các dấu chấm ở ví dụ này là phân tách hàng
nghìn; trong CSV giá trị số là `1933`). Các đợt chỉ được gọi là I–IV vì
trích đoạn PDF chưa cung cấp ngày lấy mẫu đủ rõ để gán ngày.

## QA tọa độ

- NM13: vĩ độ in `10°289'44,0"` có phút DMS không hợp lệ. Giữ chuỗi gốc,
  để trống tọa độ số; trong GeoPackage đối tượng không có vị trí hiển thị.
- NM26: kinh độ in `106°04'7,7"`, khác xa cụm Gò Công. Giữ tọa độ in và
  tô đỏ trên QGIS. **Không dùng NM26 để tính khoảng cách** trước khi xác minh.
- NM27–NM28: bảng trang 4 đặt NM27 phía đông NM28, còn bản đồ Phụ lục 1
  trang 26 vẽ NM27 phía tây NM28. NM28 cách NM25 (Cầu Chợ Gạo) khoảng
  1,46 km theo tọa độ in. Hoán đổi hai dòng là **giả thuyết**, chưa thay
  tọa độ ở bảng hay lớp GIS.
- NM22: tọa độ in đặt NM22 phía đông NM4, còn Phụ lục 1 vẽ phía tây NM4.
- NM33: tọa độ in cách NM32 khoảng 0,66 km, còn Phụ lục 1 vẽ NM33 xa hơn
  về phía bắc. Đây là cờ kiểm tra, không phải tọa độ thay thế.
- NM8, NM17, NM21: kinh độ đáng ngờ khi đối chiếu với địa danh in trên
  báo cáo. NM20 ghi phút `8,0′`, là dạng không thông thường nhưng vẫn
  phân tích được thành 8,0 phút; điểm này có cờ `REVIEW_FORMAT`.

Hiện có 24 điểm không mang cờ, 8 điểm `REVIEW_POSITION`, 1 điểm
`REVIEW_FORMAT` và 1 điểm `INVALID_DMS`. “Không mang cờ” chỉ có nghĩa là
chưa thấy mâu thuẫn trong lần kiểm tra này, **không** xác nhận đã đo đạc độc
lập tại hiện trường. Trong pilot, NM26, NM28 và NM33 mang cờ vị trí.

Một nhận định trong bản kiểm kê dán thêm không đúng với PDF: trang 2 **không
đảo cột** kinh độ–vĩ độ. Ảnh trang 2 cho thấy cột trái ghi `Kinh độ` với
giá trị `106°`, cột phải ghi `Vĩ độ` với giá trị `10°`. Bản chép hiện tại
giữ đúng thứ tự này. Ví dụ NM6 in `106°22′21,6″` và `10°20′30,6″`.

## Phương án tọa độ để kiểm tra

PDF chỉ có Bảng 1 (trang 1–5) ghi tọa độ số. Phụ lục 1 (trang 26) là bản đồ
chấm điểm, không có tọa độ số hoặc đủ tỷ lệ để xác nhận vị trí chính xác.
Các bảng vị trí ở trang 7, 11, 15, 18 và 22 không cung cấp tọa độ thay thế.
Vì vậy các phương án sau là **suy luận từ PDF**, không phải khôi phục chắc
chắn số liệu đo đạc gốc:

- NM8: thử đổi riêng độ kinh `106°` thành `105°`.
- NM17 và NM21: thử đổi riêng độ kinh `105°` thành `106°`.
- NM27 và NM28: thử hoán đổi nguyên cặp tọa độ in ở hai dòng.

Năm phương án nằm trong CSV, Excel và lớp GeoPackage riêng. Không dùng chúng
để snap, tính khoảng cách hoặc huấn luyện như tọa độ đã được xác minh. NM13,
NM22, NM26 và NM33 vẫn không có tọa độ thay thế đáng tin cậy từ PDF.

Lớp pilot là dữ liệu điểm. Dự án này chưa có mạng sông/kênh, snap, khoảng
cách theo sông hay kết quả nội suy và kiểm định.

## Tái tạo

Chạy `scripts/extract_tiengiang_monitoring.py --pdf <đường dẫn PDF>` bằng
Python 3 để xuất JSON và CSV. Chạy `scripts/build_tiengiang_monitoring_qgis.py`
bằng `python-qgis-ltr.bat` của QGIS 3.44.14. Trên máy này cần đặt `TEMP` và
`TMP` vào `D:\Study\TLCN\tmp` có quyền ghi trước khi gọi QGIS Python; nếu
không, QGIS báo lỗi lưu tệp đính kèm của dự án. Workbook được tạo bởi
`scripts/build_tiengiang_monitoring_workbook.mjs` với biến môi trường
`CODEX_ARTIFACT_TOOL_MJS` trỏ tới `@oai/artifact-tool/dist/artifact_tool.mjs`
trong Codex runtime.
