# Bước 3 — Bản đồ trạm và biểu đồ lịch sử EC

Ngày 03/10/2026. Bản này xây frontend trên Vite 5.4.21 và OpenLayers 6.15.1 trong repo hiện có, kết nối backend đã chạy ở bước 2.

## 1. Hiện trạng đã xác nhận

Backend đã kết nối `dongthap_gis` trên máy bạn ở chế độ transaction chỉ đọc. GeoJSON có hai trạm Tân Châu và Mỹ Tho với tọa độ REPORTED, SRID 4326. API liệt kê đúng hai snapshot EC: 464 quan trắc Tân Châu và 463 quan trắc Mỹ Tho; giữ đơn vị mS/m, cờ UNVERIFIED và múi giờ Việt Nam.

Hai phản hồi phân trang mới nhất có total=463, limit=10, offset lần lượt 0 và 10, has_more=true. Đoạn items bạn gửi chưa đầy đủ nên chưa thể đối chiếu trực tiếp từng dòng giữa hai trang. Việc lọc ngày sẽ được kiểm tra tiếp ngay trên giao diện này.

## 2. Đặt từng file vào đúng vị trí

Tất cả đường dẫn dưới đây tính từ gốc repo `saltwater-intrusion-warning`.

| File mới | Chức năng |
|---|---|
| `frontend/index.html` | Khung trang, các vùng bản đồ/bộ lọc/biểu đồ/bảng số liệu. |
| `frontend/vite.config.js` | Cấu hình cổng 5173 và chuyển tiếp `/api` đến backend cổng 8000. |
| `frontend/src/api.js` | Gọi API, tải đủ các trang, kiểm tra trạm/snapshot/bộ lọc, hủy yêu cầu cũ. |
| `frontend/src/map.js` | Bản đồ OpenLayers, điểm trạm, chọn trạm và bật/tắt nền OpenStreetMap. |
| `frontend/src/chart.js` | Vẽ biểu đồ SVG, định dạng ngày/số và tính thống kê. |
| `frontend/src/main.js` | Kết nối thao tác người dùng với dữ liệu, quản lý trạng thái giao diện. |
| `frontend/src/style.css` | Bố cục và giao diện cho máy tính/điện thoại. |
| `frontend/tests/api.test.js` | Kiểm thử logic tải dữ liệu, phân trang, chất lượng và múi giờ. |
| `docs/frontend_step03.md` | Hướng dẫn đang đọc. |

Tạo thư mục `frontend/src` và `frontend/tests` nếu chưa có. Giữ `package.json` và `package-lock.json` hiện tại: đợt này không thêm thư viện npm. Các module dùng JavaScript thuần; OpenLayers đảm nhiệm bản đồ, SVG đảm nhiệm biểu đồ.

## 3. Chạy bằng hai terminal

### Terminal 1: backend

Nếu terminal chạy Uvicorn hiện vẫn mở và `/api/v1/health` trả thành công, tiếp tục giữ terminal đó chạy.

Nếu đã tắt, mở PowerShell ở gốc repo, cấu hình PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD theo mục 4 trong `docs/backend_step02.md`, rồi chạy:

```powershell
.\.venv-api\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: frontend

Mở một terminal PowerShell mới ở gốc repo:

```powershell
cd frontend
npm run dev
```

Mở [http://127.0.0.1:5173](http://127.0.0.1:5173) trong trình duyệt.

Nếu báo thiếu thư viện hoặc không tìm thấy vite, chạy `npm ci` trong thư mục frontend khi có `package-lock.json`, rồi chạy lại `npm run dev`. Nếu repo chưa có lockfile, dùng `npm install` để tạo lockfile và cài thư viện. Không cần cài lại khi frontend đã khởi động bình thường.

Frontend chạy bằng Node.js và npm; bước này không cần tạo thêm môi trường Python. `.venv` tiếp tục phục vụ mô hình, `.venv-api` phục vụ backend.

Trình duyệt gọi `/api/v1/...` trên cổng 5173. Vite chuyển tiếp các yêu cầu này đến FastAPI ở cổng 8000; FastAPI đọc PostgreSQL. Mật khẩu database chỉ đặt cho backend và không xuất hiện trong mã frontend.

## 4. Cách sử dụng và kết quả cần thấy

### 4.1. Trang khởi động

Khi kết nối thành công, phần đầu trang hiện “Đã kết nối dữ liệu”. Danh sách có hai trạm. Bản đồ có hai điểm và tên trạm, với tọa độ đọc từ API.

Giao diện chọn trạm đầu tiên trong danh sách API. Nếu trạm chỉ có một snapshot, bộ đó được chọn tự động và được ghi rõ trong phần thông tin nguồn. Nếu có nhiều snapshot, người dùng phải chọn một bộ; ứng dụng không gộp các phiên bản.

Mặc định mở **24 tháng lịch cuối kết thúc tại ngày quan trắc cuối của snapshot**. Với dữ liệu hiện tại, đó là từ 01/01/2022 đến 15/12/2023; dự kiến 24 số đo ở mỗi trạm. Giao diện không dùng ngày hiện tại năm 2026 làm mặc định vì chuỗi EC hiện kết thúc năm 2023.

### 4.2. Chọn trạm và xem lịch sử

Bấm **Mỹ Tho - MRC** trong danh sách hoặc bấm điểm Mỹ Tho trên bản đồ. Tiêu đề biểu đồ, mã bộ dữ liệu và số liệu phải cùng chuyển sang Mỹ Tho.

Nhấn **Toàn bộ** khi hai bộ lọc chất lượng/loại số liệu đang để “Tất cả”. Kết quả cần thấy:

| Trạm | Số đo theo bộ lọc | Ngày đầu | Ngày cuối |
|---|---:|---|---|
| Mỹ Tho | 463 | 26/06/1985 | 15/12/2023 |
| Tân Châu | 464 | 15/05/1985 | 15/12/2023 |

Nút **24 tháng cuối** quay về khoảng gần nhất của snapshot. Hai nút thời gian chỉ đổi khoảng ngày; bộ lọc chất lượng và O/E được giữ theo lựa chọn hiện tại.

### 4.3. Lọc ngày và chất lượng

Chọn Mỹ Tho, điền Từ ngày 01/01/2022, Đến ngày 31/12/2023, giữ hai bộ lọc còn lại ở “Tất cả”, rồi nhấn **Áp dụng bộ lọc**. Cần thấy 24 số đo.

Chọn chất lượng **Đã xác minh · VALIDATED** và áp dụng. Với dữ liệu hiện tại, kết quả là 0 số đo, thống kê trung bình/cực đại hiển thị “—”, và biểu đồ giải thích không có dữ liệu phù hợp. Không có dữ liệu không được thay bằng EC=0.

Chọn lại “Tất cả trạng thái” để tiếp tục. Khi chỉnh bộ lọc nhưng chưa nhấn Áp dụng, dòng trạng thái sẽ nhắc rằng biểu đồ chưa cập nhật; khoảng ngày dưới tiêu đề vẫn là khoảng đang được hiển thị.

### 4.4. Bảng số liệu

Bấm **Xem bảng số liệu** hoặc mở mục **Bảng số liệu quan trắc**. Bảng có ngày đo, EC, loại O/E và nhãn chất lượng. Di chuột vào ngày để xem timestamp gốc, hoặc vào nhãn chất lượng để xem cờ và mô tả nguồn.

Bảng hiển thị 20 dòng mỗi trang. Nhấn Sau để chuyển từ dòng 1–20 sang 21–40. Đây là phân trang hiển thị sau khi frontend đã tải đủ dữ liệu theo bộ lọc; API vẫn được gọi theo các trang tối đa 500 dòng.

Frontend chỉ vẽ biểu đồ khi tải đủ số dòng API thông báo. Nếu có dòng trùng, tổng số thay đổi hoặc snapshot khác giữa các trang, ứng dụng báo lỗi thay vì trình bày lịch sử bị thiếu/trộn.

### 4.5. Bản đồ và điện thoại

Nút **Xem tất cả trạm** đưa khung nhìn về các trạm có tọa độ. Dấu cộng/trừ hoặc bánh xe chuột dùng để thu/phóng. Bỏ chọn **Nền OpenStreetMap** để chỉ xem điểm trạm trên nền lưới.

Trạm chưa có tọa độ vẫn có trong danh sách và vẫn xem được EC; ứng dụng không tạo vị trí thay thế. Màu điểm trên bản đồ biểu thị trạm đang chọn, không biểu thị mức độ mặn hay mức nguy hiểm.

Trên màn hình nhỏ, mở **Bộ lọc quan trắc** để chỉnh điều kiện. Có thể vuốt ngang bên trong vùng biểu đồ/bảng để xem hết nội dung; trang không cần cuộn ngang toàn bộ.

## 5. Cách diễn giải biểu đồ

EC được giữ đúng đơn vị **mS/m**. Chưa có phép quy đổi sang ppt, ngưỡng an toàn tưới tiêu, dự báo tương lai hoặc khuyến nghị vận hành cống trong giao diện này.

| Nhãn | Hiển thị |
|---|---|
| UNVERIFIED | Chưa xác minh; màu nâu vàng. Vẫn hiển thị số liệu và tính thống kê. |
| VALIDATED | Đã xác minh; màu xanh. |
| SUSPECT | Cần kiểm tra; màu cam. Vẫn có trong thống kê, có thông báo đi kèm. |
| INVALID | Không hợp lệ; dấu chéo. Giữ trong bảng nhưng loại khỏi trung bình/cực đại và đường nối. |
| O | Số liệu quan trắc; điểm đặc. |
| E | Số liệu ước tính; điểm rỗng. |

Trung bình là trung bình cộng của các số đo trong bộ lọc sau khi loại INVALID, không phải trung bình theo thời lượng hay dự báo. Đường nối chỉ hỗ trợ đọc xu hướng; bị ngắt khi thiếu tháng hoặc gặp INVALID, không nội suy để lấp dữ liệu thiếu.

## 6. Kiểm thử và giới hạn bằng chứng

Trong terminal ở thư mục frontend:

```powershell
node --test tests/api.test.js
npm run build
```

Đã chạy đạt **16 kiểm thử logic** và build thành công trên Node 24.19.0, Vite 5.4.21, OpenLayers 6.15.1. Lệnh `npm test` trong package.json gốc còn là placeholder; dùng lệnh Node ở trên để chạy bộ test đợt này.

Đã kiểm tra **11 tình huống trong Chromium**: mở trang; bấm đúng điểm Mỹ Tho trên bản đồ; tải 463 số đo và phân trang bảng; bộ lọc VALIDATED rỗng; khoảng tương lai rỗng; ngày đảo ngược; lỗi 503 và thử lại; đổi trạm nhanh; nhiều snapshot phải chọn rõ; bố cục điện thoại 390 px; trạm thiếu tọa độ. Không ghi nhận lỗi JavaScript ở các tình huống này.

Kiểm tra trình duyệt sử dụng phản hồi API mô phỏng từ hai CSV gốc đã gửi. Đây không phải kết quả kết nối frontend với PostgreSQL của bạn. Bản đồ nền OSM được chặn trong kiểm thử tự động; chức năng điểm trạm được kiểm tra riêng. Chạy mục 4 trên máy bạn là bước kiểm tra tích hợp cuối của đợt này.

## 7. Xử lý lỗi thường gặp

| Hiện tượng | Kiểm tra |
|---|---|
| Trang báo không kết nối được API | Terminal backend còn chạy không; mở `http://127.0.0.1:8000/api/v1/health`. |
| API mở riêng được nhưng frontend lỗi | Kiểm tra đã đặt `vite.config.js` ở frontend; dừng/chạy lại Vite sau khi thêm hoặc sửa config. |
| Cổng 5173 bận | Dừng frontend cũ rồi chạy lại; cấu hình strictPort sẽ báo lỗi thay vì tự đổi sang cổng khác. |
| Có hai điểm nhưng không có bản đồ nền | Kiểm tra Internet và truy cập đến OpenStreetMap. Dữ liệu trạm/EC vẫn lấy qua API độc lập. |
| Nhấn Toàn bộ nhưng vẫn 0 số đo | Kiểm tra bộ lọc chất lượng có đang VALIDATED hoặc loại E không. |
| Hiện trang Vite mặc định/trắng | Kiểm tra đã đặt index.html tại frontend và đủ năm file trong frontend/src; xem Console của trình duyệt nếu còn lỗi. |
| Thấy thông báo dataset không khớp | Tải lại danh sách và chọn snapshot đúng trạm; không thay mã bằng tay trong code. |

OpenStreetMap được dùng làm bản đồ nền tham chiếu, không thay lớp ranh giới nghiên cứu có nguồn/phiên bản. Ứng dụng giữ ghi công OpenStreetMap trên bản đồ và không cung cấp tải hàng loạt hoặc lưu bản đồ nền offline.

`npm run build` tạo `frontend/dist`. Việc chạy Vite/preview hiện phục vụ kiểm tra cục bộ; khi triển khai máy chủ cần cấu hình chuyển tiếp `/api` tương ứng. Không đưa mật khẩu PostgreSQL vào các biến hoặc file frontend.

## 8. Kết quả gửi lại để chốt đợt giao diện đầu tiên

Gửi một ảnh trang có hai điểm trạm và biểu đồ EC, cùng ba kết quả: Mỹ Tho Toàn bộ = 463; Tân Châu Toàn bộ = 464; Mỹ Tho 2022–2023 = 24. Khi các mục này đạt, ta có luồng hoàn chỉnh từ database qua API đến bản đồ và biểu đồ trên trình duyệt.

Các bước phát triển tiếp theo vẫn còn: xác định nguồn/phiên bản ranh giới, tích hợp lớp ranh giới và cống có tọa độ thật, sau đó đưa kết quả dự báo đã kiểm định lên WebGIS.

Tham chiếu kỹ thuật: [OpenLayers GeoJSON](https://openlayers.org/en/latest/apidoc/module-ol_format_GeoJSON-GeoJSON.html), [Vite server options](https://vite.dev/config/server-options), [Chính sách bản đồ nền OpenStreetMap](https://operations.osmfoundation.org/policies/tiles/). Việc triển khai được đối chiếu thêm với mã OpenLayers 6.15.1 trong node_modules để giữ tương thích phiên bản của repo.
