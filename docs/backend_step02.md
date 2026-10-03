# Bước 2 — API trạm và lịch sử EC

Ngày: 03/10/2026. Phạm vi: backend chạy trên máy phát triển, đọc database `dongthap_gis` đã có. Đây là bước nối PostgreSQL/PostGIS với giao diện WebGIS sắp xây dựng.

## 1. Căn cứ triển khai và kết quả cần đạt

Người thực hiện đã xác nhận backend trống. File requirements mới có FastAPI/Uvicorn nhưng chưa có Psycopg. Database hiện có hai trạm với hình học hợp lệ SRID 4326: Tân Châu 464 quan trắc, Mỹ Tho 463 quan trắc; cờ chất lượng hiện đều UNVERIFIED. Kết quả SQL mới nhất xác nhận 0 ranh giới thật và 0 cống thật. Những kết quả này đủ để bắt đầu API lịch sử.

Sau bước này, bạn có thể mở tài liệu API, lấy GeoJSON trạm và đọc EC có lọc ngày. Phần hoàn thành trên máy bạn được xác nhận khi các phép kiểm tra ở mục 5 đạt.

Backend dùng `measurement_site`, `conductivity_observation`, `source_dataset` và `data_source` của schema hiện có. EC là độ dẫn điện, giữ nguyên `mS/m`; không quy đổi thành độ mặn `ppt`.

## 2. Đặt từng file vào repo

Tải từng file và đặt đúng vị trí sau. Giữ tên file, đặc biệt hai dấu gạch dưới trong `__init__.py`.

| Đường dẫn tính từ gốc repo | Vai trò |
|---|---|
| `backend/__init__.py` | Khai báo package Python của backend. |
| `backend/schemas.py` | Quy định cấu trúc JSON, đơn vị, cờ chất lượng và múi giờ. |
| `backend/database.py` | Kết nối PostgreSQL, truy vấn trạm và quan trắc bằng tham số. |
| `backend/main.py` | Khởi tạo FastAPI, khai báo endpoint và xử lý lỗi. |
| `backend/requirements-api.txt` | Các thư viện chạy API với phiên bản đã kiểm thử. |
| `backend/requirements-test.txt` | Thư viện bổ sung cho kiểm thử API. |
| `backend/tests/test_backend_api.py` | Kiểm tra hợp đồng API và cách truyền điều kiện vào SQL. |
| `docs/backend_step02.md` | Tài liệu đang đọc. |

Tất cả là file mới. `requirements.txt` ở gốc repo vẫn là bộ thư viện xử lý dữ liệu/mô hình của bạn. Bộ API dùng môi trường riêng để cài đúng các thư viện cần cho bước này.

## 3. Cài môi trường API

Mở PowerShell tại gốc repo `saltwater-intrusion-warning`, nơi có các thư mục `backend`, `data`, `sql`.

```powershell
py --version
py -m venv .venv-api
.\.venv-api\Scripts\python.exe -m pip install -r backend/requirements-api.txt
```

Cần Python 3.10 trở lên; mã đã kiểm thử bằng Python 3.12. Các phiên bản thư viện chính được ghi trong `requirements-api.txt`. Gói `tzdata` cung cấp dữ liệu múi giờ cho Windows.

Không cần kích hoạt môi trường bằng `Activate.ps1`: các lệnh ở đây gọi trực tiếp Python trong `.venv-api`, tránh vướng ExecutionPolicy của PowerShell.

## 4. Cấu hình và chạy

Trong cùng cửa sổ PowerShell, đặt thông số trùng với kết nối pgAdmin đang hoạt động:

```powershell
$env:PGHOST = "127.0.0.1"
$env:PGPORT = "5432"
$env:PGDATABASE = "dongthap_gis"
$env:PGUSER = "postgres"
$pgSecure = Read-Host "Nhap mat khau PostgreSQL" -AsSecureString
$env:PGPASSWORD = [System.Net.NetworkCredential]::new("", $pgSecure).Password
Remove-Variable pgSecure

.\.venv-api\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Nếu pgAdmin dùng host `::1` hoặc tài khoản khác, thay hai giá trị tương ứng. Mật khẩu được nhập trên máy bạn; không đặt trong file Python hoặc gửi kèm kết quả kiểm tra. API sử dụng biến môi trường PG* tiêu chuẩn; nếu đã có cấu hình passfile hợp lệ thì có thể bỏ ba lệnh nhập mật khẩu.

Terminal sẽ hiện địa chỉ `http://127.0.0.1:8000`. Giữ terminal này chạy và mở trình duyệt tại:

- [Tài liệu API](http://127.0.0.1:8000/docs)
- [Kiểm tra kết nối PostgreSQL](http://127.0.0.1:8000/api/v1/health)

Backend chỉ kết nối database khi gọi endpoint dữ liệu. Mở được `/docs` chứng minh ứng dụng chạy; cần `/api/v1/health` và lịch sử trả thành công mới chứng minh kết nối đọc dữ liệu hoạt động.

Dừng bằng `Ctrl+C`. Khi kết thúc buổi làm việc, có thể xóa mật khẩu khỏi phiên PowerShell:

```powershell
Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
```

## 5. Kiểm tra trên database thật theo đúng thứ tự

### 5.1. Kết nối

Mở `/api/v1/health`. Kết quả mong đợi:

```json
{
  "status": "ok",
  "database_name": "dongthap_gis",
  "transaction_read_only": true
}
```

Mỗi lần đọc dùng một transaction chỉ đọc, có giới hạn thời gian truy vấn và tự đóng kết nối. Chế độ này áp dụng cho các truy vấn của API; quyền của tài khoản PostgreSQL vẫn do cấu hình database quyết định.

### 5.2. Danh sách trạm

Mở [GeoJSON trạm](http://127.0.0.1:8000/api/v1/stations). Theo dữ liệu vừa kiểm tra, `count` phải là 2 và `features` có:

| site_code | Trạm | Kinh độ | Vĩ độ | location_status |
|---|---|---:|---:|---|
| MRC_VN_019803 | Tân Châu | 105.2480164 | 10.80062008 | REPORTED |
| MRC_VN_019805 | Mỹ Tho | 106.3529997 | 10.35912163 | REPORTED |

Trong GeoJSON, `coordinates` có thứ tự `[kinh độ, vĩ độ]`. `REPORTED` thể hiện vị trí có nguồn khai báo, không tự nâng thành VERIFIED. Sau này trạm chưa có tọa độ vẫn được trả về với `geometry: null`, để giao diện thông báo rõ.

### 5.3. Chọn snapshot

Mở lần lượt:

- [Bộ dữ liệu Tân Châu](http://127.0.0.1:8000/api/v1/stations/MRC_VN_019803/datasets)
- [Bộ dữ liệu Mỹ Tho](http://127.0.0.1:8000/api/v1/stations/MRC_VN_019805/datasets)

`items` liệt kê các bộ dữ liệu có quan trắc của đúng trạm, kèm SHA-256, tên file, số dòng, khoảng thời gian và số dòng theo cờ chất lượng. Chọn `dataset_code` từ kết quả này khi gọi lịch sử. API không tự chọn bộ mới nhất và không gộp các snapshot.

Theo W03 đã gửi, hai mã hiện tại là:

| Trạm | dataset_code | observation_count |
|---|---|---:|
| Tân Châu | MRC_EC_TANCHAU_bd4cf100cb4782e3 | 464 |
| Mỹ Tho | MRC_EC_MYTHO_2cee9c9c1cb8e29e | 463 |

Đây là mốc đối chiếu ngày 03/10/2026, không phải số dòng hardcode trong chương trình.

### 5.4. Đọc lịch sử

Mở liên kết này để lấy toàn bộ snapshot Mỹ Tho hiện tại:

[Lịch sử EC Mỹ Tho](http://127.0.0.1:8000/api/v1/stations/MRC_VN_019805/observations?dataset_code=MRC_EC_MYTHO_2cee9c9c1cb8e29e)

Mong đợi `total: 463`, `has_more: false`, `items` có 463 dòng. Dòng cuối có `observed_at` là `2023-12-15T00:00:00+07:00`. `unit` là `mS/m`; `quality_flag` giữ UNVERIFIED, `observed_or_estimated` giữ O.

Trong `/docs`, mở endpoint observations → **Try it out**, điền:

| Tham số | Giá trị mẫu |
|---|---|
| site_code | MRC_VN_019805 |
| dataset_code | MRC_EC_MYTHO_2cee9c9c1cb8e29e |
| date_from | 2022-01-01 |
| date_to | 2023-12-31 |
| limit | 500 |
| offset | 0 |

Nhấn **Execute**. Với snapshot hiện có, khoảng này có 24 quan trắc. Tham số ngày tính theo `Asia/Ho_Chi_Minh`; ngày kết thúc được tính trọn ngày. Bỏ trống hai ngày để xem toàn bộ lịch sử. Dữ liệu chưa có quan trắc mới sau tháng 12/2023; truy vấn năm 2026 trả 0 dòng là hợp lệ.

Ý nghĩa các trường phân trang:

- `dataset.observation_count`: số quan trắc của trạm trong toàn bộ snapshot.
- `total`: số quan trắc sau khi áp dụng các bộ lọc, trước phân trang.
- `items`: trang hiện tại, tối đa `limit` dòng; giới hạn cho phép 1–1000.
- `offset`: số dòng bỏ qua từ đầu danh sách theo thời gian tăng dần.
- `has_more`: còn trang tiếp theo hay không. Nếu true, tăng offset bằng số dòng đã nhận.

Hai bộ lọc tùy chọn: `quality_flag` nhận UNVERIFIED/VALIDATED/SUSPECT/INVALID; `observed_or_estimated` nhận O/E. O là quan trắc, E là ước tính. Mặc định API lịch sử trả mọi cờ và giữ nhãn từng dòng, kể cả INVALID nếu có; khi xây biểu đồ phải biểu thị chất lượng rõ. Lọc VALIDATED hiện sẽ cho 0 dòng vì dữ liệu chưa được xác minh. Đây không phải lỗi kết nối hoặc bằng chứng rằng mọi giá trị EC đều sai.

### 5.5. Kiểm tra một lần phân trang

Với cùng snapshot, đặt `limit=10`, `offset=0`: cần nhận 10 dòng, total vẫn 463 và has_more=true. Đổi offset=10 sẽ nhận trang tiếp theo. Việc này xác nhận API không chỉ trả thành công mà còn đọc đúng phần dữ liệu yêu cầu.

## 6. Kiểm thử tự động và phạm vi bằng chứng

```powershell
.\.venv-api\Scripts\python.exe -m pip install -r backend/requirements-test.txt
.\.venv-api\Scripts\python.exe -m unittest discover -s backend/tests -v
```

Đã chạy đạt 16 kiểm thử trên Python 3.12: GeoJSON và tọa độ thiếu; giữ cờ/đơn vị; thời gian +07:00; snapshot bắt buộc; lọc ngày; phân trang; đầu vào không hợp lệ; 404 khi sai trạm/snapshot; 503 khi lỗi database; không lộ nội dung lỗi chứa thông tin kết nối; CORS; truyền tham số SQL và ràng buộc trạm + snapshot.

Các test dùng đối tượng thay thế repository/kết nối, không tạo hay nhập dữ liệu thử vào PostgreSQL. Chúng không chứng minh SQL đã thực thi thành công trên PostGIS. Môi trường kiểm thử không có PostgreSQL/PostGIS và không kết nối database trên máy bạn; mục 5 là bước kiểm tra tích hợp còn cần thực hiện.

Bộ thư viện đã thử gồm FastAPI 0.142.2, Uvicorn 0.54.0, Psycopg 3.3.6, Pydantic 2.13.5, tzdata 2026.4, HTTPX 0.28.1; Starlette được pip chọn là 1.7.0. Phiên bản Starlette này có thể hiện cảnh báo chuyển thư viện TestClient từ HTTPX sang HTTPX2; các test đã chạy OK với bộ nêu trên.

## 7. Nếu gặp lỗi

| Hiện tượng | Cách xử lý |
|---|---|
| `No module named backend` | Chạy uvicorn từ gốc repo, không chạy bên trong thư mục backend. |
| Thiếu fastapi/psycopg | Cài requirements và chạy bằng đúng `.venv-api\Scripts\python.exe`. |
| Lỗi không tìm thấy múi giờ | Kiểm tra đã cài `tzdata` trong chính môi trường API. |
| `/docs` mở được nhưng health trả 503 | Kiểm tra PostgreSQL đang chạy, đúng host/port/database/user/password; xem mã lỗi và SQLSTATE trong terminal. |
| `DB_PERMISSION_DENIED` | Tài khoản kết nối cần USAGE schema public và SELECT trên bốn bảng API dùng. |
| `DB_SCHEMA_MISMATCH` | Đối chiếu schema v1/v2 và PostGIS; gửi lỗi để kiểm tra, không tạo lại DB đang có dữ liệu. |
| observations trả 422 | Kiểm tra đã truyền dataset_code, ngày hợp lệ, ngày bắt đầu không lớn hơn ngày kết thúc, limit không quá 1000. |
| `DATASET_NOT_FOUND` | Lấy lại mã từ endpoint datasets của đúng trạm, không lấy mã bộ của trạm khác. |
| `total: 0` nhưng HTTP 200 | Khoảng ngày hoặc bộ lọc chất lượng không có dữ liệu phù hợp. |
| Cổng 8000 đã được sử dụng | Dừng tiến trình cũ hoặc đổi `--port 8001`, rồi đổi cổng ở URL kiểm tra. |

CORS mặc định cho giao diện Vite tại `http://localhost:5173` và `http://127.0.0.1:5173`. Nếu frontend chạy cổng khác, đặt `WEBGIS_CORS_ORIGINS` thành danh sách origin cách nhau bằng dấu phẩy trước khi chạy server.

## 8. Mốc bàn giao và bước tiếp theo

Gửi lại kết quả health, `count` của stations, và `total` của lịch sử Mỹ Tho. Nếu các kết quả khớp mục 5, ta xác nhận API đã đọc đúng database của bạn rồi xây giao diện OpenLayers: hai điểm trạm → chọn trạm → chọn bộ dữ liệu → xem biểu đồ EC và cờ chất lượng.

Ranh giới/cống vẫn cần bổ sung bằng nguồn xác định. Phần dự báo đang là thí nghiệm riêng và chưa được đưa vào API này. Mốc hiện tại là chạy API cục bộ; tài khoản DB chỉ có quyền cần thiết, kiểm soát truy cập và cấu hình triển khai sẽ được bổ sung ở bước đưa hệ thống lên máy chủ.

Tài liệu kỹ thuật tham chiếu: [Psycopg — transaction](https://www.psycopg.org/psycopg3/docs/basic/transactions.html), [Psycopg — tham số SQL](https://www.psycopg.org/psycopg3/docs/basic/params.html), [FastAPI — kiểm thử](https://fastapi.tiangolo.com/tutorial/testing/).
