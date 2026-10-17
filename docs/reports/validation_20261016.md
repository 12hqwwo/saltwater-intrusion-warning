> Tài liệu lịch sử, không phải hướng dẫn chạy hiện tại. Các đường dẫn thành phần đã loại bỏ chỉ còn trong bản sao lưu; xem [README hiện tại](../../README.md). Giữ nội dung đánh giá để truy vết.

# Kiểm tra và sửa lỗi tiếp — 16/10/2026

## Thay đổi

- Sửa dependency TestClient: thêm httpx2==2.13.1 vào requirements-test; đã cài và chạy được kiểm thử trong `.venv-api` Python 3.14. Môi trường `.venv` Python 3.12 cũng đã cài httpx2 và openpyxl 3.1.5; requirements-prototype ghi dependency đọc workbook.
- Thêm `scripts/check_webgis_setup.py`: kiểm tra dependency, bản build, checksum snapshot và PostgreSQL; không in secret, không sửa DB. Kết quả cuối chỉ còn PostgreSQL `PASSWORD_NOT_CONFIGURED` (repo chưa có .env).
- API rà soát kiểm tra thêm hash workbook nguồn, không chấp nhận tệp chuẩn hóa của workbook khác.
- Công cụ thu minh chứng giữ lỗi kết nối vào hồ sơ thay vì thoát bằng traceback; trả exit code 1 khi có lỗi. Lỗi HTTP không thành bộ dữ liệu rỗng thành công.
- Bản build mới hiển thị cả URL HTTP dưới dạng văn bản nguồn, giữ nguyên URL được khai báo. Không tự đổi nguồn hoặc vô hiệu TLS.

## Kết quả đã chạy

- `python -m unittest discover -s backend/test -v`: **36/36 đạt** trong `.venv-api`. Các bài dùng mock DB chỉ kiểm tra hợp đồng phần mềm, không phải nghiệm thu PostGIS.
- `python -m unittest discover -s scripts/tests -v`: **7/7 đạt** trong `.venv`. Lần chạy sandbox lỗi quyền thư mục tạm; chạy lại được phê duyệt đã đạt.
- `npm.cmd --prefix frontend run build`: đạt; `frontend/dist/replay.html` không tồn tại.
- Chạy chuẩn hóa bằng `.venv` trực tiếp: **890 bản ghi, 21 ô loại, 75 điểm đo**, 0 bản ghi được cấp quyền huấn luyện/vận hành.
- Thu HTTP ở `runs/webgis_evidence/20261016T023020257183Z`: **28 phản hồi 200**, **3 phản hồi 503** tại health/stations/database-gates của PostgreSQL. Tổng 31 yêu cầu; không báo tất cả đạt.
- `git diff --check`: đạt, chỉ cảnh báo chuyển đổi LF/CRLF.
- Trình duyệt đã kiểm tra ngày 15/10; ảnh tại `docs/reports/intake_review_20261015.png`. Lượt 16/10 này kiểm tra build và HTTP, không gọi đó là một lượt nghiệm thu trình duyệt mới.

## Cần người dùng cung cấp cục bộ

Tạo `.env` theo `.env.example`, cấu hình PGHOST/PGPORT/PGDATABASE/PGUSER và PGPASSWORD hoặc PGPASSFILE. Không gửi mật khẩu qua chat. Chạy lại `scripts/check_webgis_setup.py`; sau khi có quyền DB mới chạy importer transactional và kiểm tra idempotence/PostGIS thật. Chưa áp dụng migration khi thiếu xác thực.

Nguồn Tiền Giang và phần lớn v3 còn cần đối chiếu bảng gốc; không có dự báo hiện tại hoặc lệnh vận hành cống được chứng nhận. Thêm mẫu RIA2 không làm các kết quả tháng MRC thành kết quả tại cống. Các giới hạn khoa học trong báo cáo 15/10 vẫn còn hiệu lực.
