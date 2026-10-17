> Tài liệu lịch sử, không phải hướng dẫn chạy hiện tại. Các đường dẫn thành phần đã loại bỏ chỉ còn trong bản sao lưu; xem [README hiện tại](../../README.md). Giữ nội dung đánh giá để truy vết.

# Tiếp tục triển khai — 15/10/2026

## Kết quả thực hiện

- Bỏ replay khỏi điều hướng index/research, đầu vào build Vite và tham số trình chạy sản phẩm. Mã nghiên cứu cũ giữ lại để truy vết.
- Thêm API `/api/v1/research/intake`, `/coverage`, `/measurement-points`, `/observations` và giao diện tiếp nhận. Chế độ `review_files` được ghi rõ, độc lập PostgreSQL/snapshot. Tệp gốc sai checksum trả 503; không có fallback.
- Chuẩn hóa 533 dòng sông + 189 ô tại cống + 168 ô cách cống 200 m thành **890 bản ghi rà soát**, 75 khóa điểm đo. **21 ô thiếu** ở cột 200 m được giữ trong nhật ký loại. Không hợp nhất vị trí sông với nội đồng; không tạo tọa độ, giờ đo hay cửa sổ đo chưa xác minh. Tất cả giữ UNVERIFIED và không đủ điều kiện huấn luyện/vận hành.
- Trích xuất **10 mẫu EC RIA2 đợt 12/2025** từ PDF gốc, đối chiếu ảnh trang 1–4 (đơn vị trang 1, số đo trang 2–4). Ngày lấy mẫu 03–06/08/2025 khác ngày văn bản 08/08/2025. Tên và cặp tọa độ in trong bản tin khớp danh mục RIA2 hiện có; giữ CRS, phương pháp và địa danh chưa xác minh.
- Chuyển đơn vị vật lý µS/cm sang mS/m bằng chia 10; không chuyển EC thành độ mặn. Snapshot mới **977 mẫu: 927 MRC + 50 RIA2**. Nguồn mới, checksum, trang/dòng và metadata nằm trong `data/metadata/ria2_issue12_transcription.json`. Không ghi đè CSV gốc cũ.
- Giữ nguyên kết quả bốn thí nghiệm MRC vì không thêm nhãn MRC. Năm đợt RIA2 vẫn không đủ kiểm chứng dự báo ngày/giờ. Ngày quan trắc mới nhất của bộ vẫn 11/11/2025.

## Cách chạy và tái lập

```text
.venv\Scripts\python.exe scripts/build_research_workspace.py
npm.cmd --prefix frontend run build
.venv\Scripts\python.exe run_webgis.py --mode snapshot --port 8001
```

Mở http://127.0.0.1:8001/research.html . Tệp chuẩn hóa v3 tái tạo bằng `python scripts/normalize_v3_observations.py` trong môi trường có openpyxl. Không chạy tác vụ này bằng cách coi các bản ghi là đã được cơ quan xác thực.

## Hạn chế còn lại

- PostgreSQL thật trả `fe_sendauth: no password supplied`; repo chưa có `.env`. Chưa áp dụng migration/import mới hoặc nghiệm thu PostGIS. Cần cấu hình PG* hoặc PGPASSFILE cục bộ; không gửi mật khẩu qua chat.
- Thủy lợi Tiền Giang còn lỗi chứng chỉ tên miền. Bộ v3 chưa được đối chiếu toàn bộ với bảng gốc; không công bố các số đếm tiếp nhận là nhãn khoa học đã xác minh.
- Bản đồ nền OSM báo lỗi tải trong lần kiểm tra trình duyệt; có thông báo trên giao diện, lớp dữ liệu vẫn độc lập. Chưa có gói nền ngoại tuyến.
- Môi trường `.venv-api` có dependency TestClient thiếu httpx2; kiểm thử hiện dùng `.venv` Python 3.12. Dùng môi trường đã được ghi trong run_guide; không coi hai môi trường tương đương.
- Chưa có quan trắc hiện tại và hồ sơ thủy lực/quy trình đủ để khuyến nghị đóng/mở cống.

Đây là tiến độ chức năng và dữ liệu, chưa phải nghiệm thu toàn bộ đồ án.
