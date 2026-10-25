# Tiến trình hiện tại — WebGIS cảnh báo xâm nhập mặn

Cập nhật ngày **25/10/2026 (UTC+7)**.

Repository: `saltwater-intrusion-warning`.

Tài liệu tổng hợp công việc đã thực hiện trong phiên phát triển, kết quả kiểm thử đã chạy và kiểm tra chỉ đọc trên server local. Không chạy lại huấn luyện, không thêm dữ liệu thử và không triển khai lên server bên ngoài khi xuất báo cáo này.

## 1. Trạng thái tổng quát

Web đã có giao diện bản đồ quan trắc, dự báo EC tháng tại Mỹ Tho/Tân Châu, mô phỏng dọc Sông Tiền và 27 cống, lưu lịch sử dự báo/nháp cống vào PostgreSQL, cùng phân quyền tài khoản kết nối DB.

Server local đang chạy tại `http://127.0.0.1:8000/workspace.html`. Kiểm tra tại thời điểm xuất tài liệu:

| Hạng mục | Trạng thái xác nhận |
| --- | --- |
| Trang workspace | HTTP 200 |
| Chế độ dữ liệu runtime | `postgres` |
| Kết nối PostgreSQL | HTTP 200; DB `dongthap_gis`; transaction đọc là read-only |
| Quan trắc đang được chọn để phục vụ | 12 điểm, 977 mẫu EC; trong đó RIA2 có 50 mẫu |
| Tổng dòng trong bảng quan trắc | 1.017 dòng tại lần kiểm tra quyền DB gần nhất; khác số mẫu được chọn để phục vụ |
| Tuyến `TIEN_MAIN` | 45 đỉnh WGS84 |
| Nhánh kênh trong corridor | 10 nhánh |
| Cống có tọa độ trong mô phỏng | 27 cống |
| Lịch sử dự báo PostgreSQL | API đọc thành công; hiện trả tổng 1 lượt đã lưu |
| Header phục vụ ảnh nền | `Referrer-Policy: strict-origin-when-cross-origin` |

Số liệu có thể thay đổi khi nhập dữ liệu hoặc lưu thêm dự báo. Không dùng số tổng bảng DB thay cho số mẫu của các phiên bản được chọn. Danh mục 4 hồ sơ công trình trong workspace và tập 27 cống mô phỏng có phạm vi khác nhau.

## 2. Giao diện bản đồ và timeline

Các phần đã hoàn thành:

- Bản đồ nền tối, ảnh vệ tinh Esri và nền sáng; bộ chọn nền nằm trên thanh công cụ bản đồ.
- Dải màu EC/độ mặn mô phỏng trên sông; hạt chuyển động dòng chảy và gió; các mốc ranh mô phỏng.
- Timeline theo tháng, có phát chu kỳ và các nút chọn nhanh giai đoạn hạn/mùa lũ.
- Sơ đồ cắt dọc sông có thể đóng/mở; giữ đường biểu diễn, điểm tương tác và một dropdown chọn cống.
- Đã bỏ hàng 27 nút tên cống bị cắt chữ khỏi dải cắt dọc.
- Marker cống thông thường là chấm tròn nhỏ; marker đang chọn/hover dùng hình thoi nổi bật và vòng halo.
- Các ghi chú kỹ thuật được gom vào nút **Chú giải & Nguồn**.
- Các panel so sánh ngưỡng, biểu đồ chi tiết và lịch sử DB nằm trong ngăn thu gọn bên dưới bản đồ.
- Nút **Xem dự báo trên bản đồ** chuyển về Quan trắc, chọn tháng phù hợp/gần nhất trong timeline và hiển thị thông tin dự báo.

Timeline mô phỏng hiện được kiểm thử với 495 tháng từ 06/1985 đến 08/2026. Timeline này là nguồn riêng với tháng mục tiêu của mô hình dự báo mới; không tự có dữ liệu quan trắc cho tháng tương lai.

## 3. Phase 5 — Chỉnh tuyến Sông Tiền

Đã sửa hai tệp:

- `data/biengioi/tien_river_corridor.geojson`
- `frontend/src/features/observations-map.js`

Nội dung cập nhật:

1. Thay trục chính bằng 45 đỉnh theo danh sách tọa độ người dùng cung cấp, bao gồm đoạn uốn về phía nam trước khi rẽ sang đông ở khu vực Thanh Bình–Cao Lãnh.
2. Giữ mốc Tân Châu chính xác `[105.233, 10.8]` theo hợp đồng backend/kiểm thử, thay cho mốc gần đúng `[105.2335, 10.8015]` trong đề xuất.
3. Giữ Mỹ Tho `[106.36, 10.35]` tại lý trình mô phỏng 125 km và cửa biển `[106.75, 10.22]` tại 175 km.
4. Nối lại cả 10 nhánh kênh vào đỉnh phù hợp của tuyến mới; cập nhật chỉ số đỉnh nối và điểm tiếp cận. Tọa độ cống tại `gate_path_index: 2` được giữ nguyên.
5. Đặt nội suy hiển thị `tension: 0`; các điểm lấy mẫu nằm trên từng đoạn nối đỉnh, tránh spline văng ra ngoài đoạn nguồn. Tuyến nền, dải màu và đường hạt dùng cùng thiết lập nội suy.
6. Bề rộng thay đổi liên tục theo zoom; tại zoom 9, lõi khoảng 4,5 px, viền 7,5 px và glow 13 px.

**Giới hạn còn lại:** mới xác nhận cấu trúc, mốc neo và nội suy bằng mã nguồn/kiểm thử. Chưa kiểm chứng độc lập toàn bộ 45 đỉnh và mọi đoạn nối trên ảnh vệ tinh. Vì vậy chưa thể kết luận toàn bộ dải màu nằm trong lòng nước ở mọi vị trí/zoom. Lý trình 0/125/175 km vẫn là thang mô phỏng được chuẩn hóa, không phải chiều dài khảo sát thực địa.

## 4. PostgreSQL có vai trò thực tế

Ứng dụng đọc quan trắc qua PostgreSQL và có thể lưu kết quả mới vào schema DSS:

| Bảng/schema | Vai trò |
| --- | --- |
| `public.measurement_site` | Danh mục điểm quan trắc |
| `public.source_dataset` | Phiên bản và nguồn dữ liệu |
| `public.conductivity_observation` | Quan trắc EC gốc |
| `dss_reference.ec_threshold_presets` | Ngưỡng kịch bản tham khảo |
| `dss_reference.multivariate_prediction_log` | Lịch sử lượt dự báo, đầu vào và phiên bản mô hình |
| `dss_reference.gate_simulation_drafts` | Các phiên bản nháp mô phỏng cống |
| `webgis_security.audit_log` | Nhật ký INSERT dự báo và nháp |

Trong Dự báo EC đa biến, tùy chọn **Lưu lượt chạy vào PostgreSQL** bật sẵn. Khi chọn, server chạy mô hình và lưu chính kết quả lượt đó; không lấy giá trị EC do client tự khai báo để ghi thành dự báo. Bỏ chọn để chạy xem thử. Lượt dự báo được phép chờ tối đa 120 giây ở frontend để xử lý thời gian nạp mô hình ban đầu.

Hồ sơ cống có thao tác lưu nháp PostgreSQL và khôi phục nháp mới nhất; lưu cục bộ trên trình duyệt vẫn là cơ chế riêng. Lỗi DB được báo rõ, không báo thành công giả hoặc tự chuyển sang snapshot.

Artifact mô hình, khí tượng và một số danh mục tiếp tục đọc từ tệp dự án. Chọn PostgreSQL không có nghĩa toàn bộ nội dung web đều được chuyển vào DB.

## 5. Bảo mật đã áp dụng

Đã tạo và kiểm tra trên PostgreSQL local:

| Role | Phạm vi |
| --- | --- |
| `webgis_reader` | SELECT dữ liệu được cấp; transaction API chỉ đọc |
| `webgis_writer` | INSERT vào hai bảng lịch sử/nháp; SELECT phục vụ trả kết quả và USAGE sequence nháp |
| Tài khoản quản trị PG* | Dùng riêng cho script thiết lập/nhập dữ liệu/bảo trì |

- API không dùng superuser `postgres` để đọc/ghi dữ liệu ứng dụng.
- Hai role ứng dụng không được sửa/xóa/truncate quan trắc gốc, sửa/xóa lịch sử hoặc thay đổi audit.
- Kết nối ứng dụng kiểm tra và từ chối role quản trị, role sở hữu dữ liệu hoặc có membership đặc quyền.
- Mật khẩu runtime được tạo riêng, lưu trong `.env`; `.env` và `.security/` bị loại khỏi Git và được giới hạn quyền truy cập cục bộ.
- Không có màn hình đăng nhập hoặc tài khoản người dùng web. Hai role trên là role DB.
- API key ghi là tùy chọn qua `WEBGIS_WRITE_API_KEY` và header `X-API-Key`. Giao diện mặc định không gửi key; nếu bật key, cần API client/proxy phù hợp.
- Có kiểm tra Host/Origin, header bảo mật, tham số SQL được bind và timeout truy vấn.
- Audit ghi role DB và nguồn ứng dụng; không xác định danh tính cá nhân của người dùng web local.

Đã thử quyền bằng kết nối thật: reader đọc được, writer thêm được nháp, các thao tác bị cấm bị PostgreSQL từ chối và trigger audit ghi đúng role. Các bản ghi kiểm tra được rollback; 1.017 dòng quan trắc gốc không đổi trong kiểm tra tích hợp.

Bảo mật này phục vụ chạy local. Chưa triển khai xác thực nhiều người dùng, reverse proxy HTTPS, firewall, mã hóa bản sao lưu hay cấu hình PostgreSQL từ xa.

## 6. Lỗi ảnh nền 403 và bản sửa mới nhất

Ảnh người dùng gửi cho thấy OpenStreetMap trả ô **403 Access blocked**, trong khi API dữ liệu vẫn trả HTTP 200.

Phát hiện header `Referrer-Policy: same-origin` đã chặn thông tin nguồn trang khi trình duyệt gọi ảnh nền khác origin. Đã đổi sang `strict-origin-when-cross-origin` để gửi origin theo yêu cầu ảnh nền, không gửi đường dẫn/query sang dịch vụ ngoài. Có kiểm thử hồi quy cho header trên response trang.

Server local tại thời điểm xuất tài liệu đã trả header mới. Chưa kiểm tra lại bằng ảnh chụp trình duyệt để xác nhận mọi ô bị cache/block đã hết. Nếu trang đang mở vẫn hiện ô cũ, tải lại bằng Ctrl+F5; nếu còn lỗi thì kiểm tra request ảnh nền và phản hồi thực tế của nhà cung cấp.

## 7. Kết quả kiểm thử đã chạy

| Đợt | Kết quả |
| --- | --- |
| Sau Phase 5: toàn bộ Python `test_*.py` | 38/38 qua |
| Sau sửa header: nhóm `test_security.py` | 7/7 qua, gồm kiểm thử header mới |
| Sau sửa header: Node tests | 33/33 qua |
| Build frontend gần nhất | Thành công |
| Kiểm tra quyền PostgreSQL thật | Qua; kết quả trong `docs/database-security-verification.json` |
| Kiểm tra API lưu dự báo/nháp bằng DB thật | Qua; INSERT kiểm tra được rollback |
| Kiểm tra runtime khi xuất báo cáo | Trang, health, summary, corridor và API đọc lịch sử đều HTTP 200 |

Không cộng 38 và 7 thành tổng test của một lần chạy: kiểm thử header mới được thêm sau lần chạy toàn bộ Python. Không chạy browser screenshot hoặc triển khai bên ngoài trong các đợt sửa gần nhất.

Các lệnh kiểm tra:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
node --test tests/*.test.mjs frontend/src/features/gate-simulation-draft.test.js
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe scripts/verify_database_security.py
```

## 8. Chạy trong Antigravity

Mở terminal PowerShell tại thư mục gốc repository:

```powershell
.\start.ps1
```

Mặc định build frontend và dùng PostgreSQL. Mở `http://127.0.0.1:8000/workspace.html`. Dừng server cũ bằng Ctrl+C trước khi chạy lại sau thay đổi backend; dùng Ctrl+F5 để nạp lại trang và asset.

Các lựa chọn:

```powershell
.\start.ps1 -SkipBuild             # Chỉ khi build đã cập nhật
.\start.ps1 -Mode snapshot         # Xem bộ tệp; DSS vẫn cần PostgreSQL để lưu
.\start.ps1 -Port 8016             # Đổi cổng local
```

Máy hiện tại đã áp dụng phân quyền. Máy khác cần PostgreSQL/dữ liệu dự án, cấu hình quản trị cục bộ và chạy setup; role/quyền/mật khẩu không tự được chuyển qua Git:

```powershell
.\.venv\Scripts\python.exe scripts/apply_dss_storage.py --apply
.\.venv\Scripts\python.exe scripts/setup_security.py --apply
```

## 9. Công việc tiếp theo

1. Đối chiếu tuyến chính với ảnh vệ tinh theo từng đoạn, ưu tiên khúc uốn Thanh Bình–Cao Lãnh và các cù lao; xác nhận tuyến/dải màu thực sự nằm trong lòng nước.
2. Rà lại điểm nối 10 nhánh kênh và quan hệ với 27 cống bằng nguồn địa lý đáng tin cậy. Điểm nối gần nhất chỉ là hình học, không chứng minh kết nối thủy lực.
3. Kiểm tra lại trực quan ảnh nền sau bản sửa header và thử một lượt dự báo/nháp thực tế từ UI để xác nhận trải nghiệm người dùng.
4. Giữ riêng quan trắc, dự báo tháng, ước tính hồi cứu và mô phỏng; cần EC thực đo mới để đánh giá dự báo sau 2023. Quy đổi độ mặn đang dùng hệ số thực nghiệm, chưa có hiệu chuẩn địa phương.
5. Cập nhật đồng bộ tài liệu cũ khi bàn giao. `docs/current_state.md` và một số tài liệu ngày 23–24/10 còn mô tả snapshot mặc định hoặc số liệu DB trước các thay đổi mới; dùng báo cáo này cho mốc 25/10 và kiểm tra API runtime khi cần số liệu mới nhất.

Chưa có lịch vận hành cống được thẩm định, kiểm chứng thủy lực đầy đủ hoặc kết nối điều khiển thiết bị. Không coi màu mô phỏng/marker hoặc bản nháp lưu DB là quyết định vận hành đã phê duyệt.

## 10. Tài liệu tham chiếu

- [Hướng dẫn chạy](run_guide.md)
- [Bảo mật cơ sở dữ liệu](database-security.md)
- [Kết quả kiểm tra quyền DB](database-security-verification.json)
- [Kho lưu trữ DSS](dss-storage.md)
- [Mô hình dự báo đa biến](multivariate-forecast.md)
- [Mô phỏng không gian](spatial-simulation.md)

Khi push hoặc đóng gói, không đưa `.env`, `.security/`, mật khẩu hoặc bản sao lưu chứa bí mật lên Git. Chỉ push mã nguồn, migration, tài liệu và dữ liệu được phép chia sẻ sau khi rà soát danh sách thay đổi.
