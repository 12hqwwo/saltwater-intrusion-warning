# Tiếp tục sau khi kiểm thử ETL đạt — 25/09/2026

Mốc hiện tại: đã đối chiếu log nạp lần đầu và nhập lặp; người thực hiện xác nhận rollback cũng đúng kịch bản. Tiếp theo: đưa mã đã kiểm chứng vào repo C, sao lưu database chính, bổ sung raw Mỹ Tho và tọa độ hai trạm, rồi hoàn thiện GIS và hồ sơ tuần. Các ca test đã đạt được giữ làm bằng chứng; không dựng lại database test.

Ổ C/D quyết định vị trí mã và tệp. Database nhận dữ liệu được xác định bởi host, port và `--db`. Chạy Python trong repo C vẫn có thể đọc raw và ghi log trên D.

**1. Chép mã đã kiểm chứng vào repo C**

Giải nén bản cập nhật `WebGIS_ETL_Goi_cho_repo.zip` ra một thư mục riêng ở D. Mở repo C bằng VS Code, mở Terminal PowerShell và chạy:

```powershell
git rev-parse --show-toplevel
git status --short
git diff --cached --name-only
```

Lệnh đầu phải trả về đúng gốc repo C. Nếu đang có tệp thay đổi/staged của công việc khác, giữ nguyên chúng và ghi nhận trước khi chép. Chép các đường dẫn sau từ gói mới vào cùng đường dẫn tương đối của repo; nếu trùng tên, dùng Compare/Diff trước khi quyết định thay thế.

| Đường dẫn | Cần dùng cho việc gì? |
|---|---|
| `etl/etl_csv.py` | Chương trình kiểm tra, chuẩn hóa và nạp CSV đã chạy đạt |
| `etl/tests/test_validation.py` | Kiểm thử validation, đọc raw từ D qua biến môi trường |
| `sql/checks/00_kiem_tra_hien_trang.sql` | SELECT A01–A12 để kiểm tra cấu trúc, dữ liệu và GIS |
| `sql/test/99_bootstrap_database_test.sql` | Tái lập schema của một DB test mới khi cần |
| `docs/etl/README.md` | Hướng dẫn chạy và tái lập các phép thử |
| `docs/etl/kiem_tra_20260925.md` | Kết quả và phạm vi bằng chứng |
| `docs/etl/source_manifest.csv` | Tên, kích thước và SHA của tệp nguồn |
| `docs/etl/sau_khi_test_dat.md` | Hướng dẫn đang đọc |

Mã ETL, test, SQL và tài liệu tái lập đều là thành phần sử dụng được trong tiểu luận. Raw, các thư mục runs, bản backup và SQL cố ý gây lỗi rollback tiếp tục để ở D. Script bootstrap nằm trong `sql/test` để phân biệt mục đích; không chạy nó trên `dongthap_gis`.

Bổ sung các dòng phù hợp trong `gitignore_webgis.txt` vào `.gitignore` hiện có, giữ các quy tắc frontend/backend. Không ignore toàn bộ CSV/SQL/tests. `.gitignore` không tự bỏ theo dõi những tệp đã được Git track.

**2. Khai báo đường dẫn một lần trong PowerShell**

Đường dẫn D bên dưới lấy theo ảnh thư mục đã gửi. Nó có thư mục con cuối `WebGIS_Tuan04_05`, là nơi chứa trực tiếp `etl_csv.py` và `data\raw`. Nếu bạn đã chuyển thư mục, sửa dòng này thành vị trí hiện tại.

```powershell
$etlTestRoot = 'D:\UNIVERSITY\DOANTOTNGHIEP\TIEULUANCHUYENNGANH\WebGIS_Tuan04_05_Bo_thuc_hanh\WebGIS_Tuan04_05'
$etlRepoRoot = (Read-Host 'Dan duong dan goc repo tren o C').Trim('"')
$etlRepoRoot = (Resolve-Path -LiteralPath $etlRepoRoot).Path
$etlDataRoot = Join-Path $etlTestRoot 'data\raw'
$etlOutputRoot = Join-Path $etlTestRoot 'runs\main_load'
$etlScript = Join-Path $etlRepoRoot 'etl\etl_csv.py'
$etlMyThoCsv = Join-Path $etlDataRoot 'mrc_mytho.csv'
$etlPsql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe'

Test-Path -LiteralPath $etlScript
Test-Path -LiteralPath $etlMyThoCsv
Test-Path -LiteralPath (Join-Path $etlTestRoot 'etl_csv.py')
Test-Path -LiteralPath $etlPsql
```

Bốn kết quả phải là True. Nếu False, sửa đúng đường dẫn đó trước khi chạy tiếp. Các biến chỉ tồn tại trong cửa sổ PowerShell hiện tại; mở terminal mới cần khai báo lại.

Kiểm tra mã C trùng bản D đã kiểm thử:

```powershell
$etlRepoHash = (Get-FileHash -LiteralPath $etlScript -Algorithm SHA256).Hash
$etlTestHash = (Get-FileHash -LiteralPath (Join-Path $etlTestRoot 'etl_csv.py') -Algorithm SHA256).Hash
$etlRepoHash -eq $etlTestHash
```

Kết quả phải True. Mã đã bàn giao có SHA-256 `cf3e85cf3518fbf58f840262d64cb366d6f030cfa9b4ec090f4368537264a35e`. Nếu khác, đối chiếu diff trước; không thay file đang có bằng một bản chưa rõ nguồn.

Kiểm tra ngắn việc bố trí mã C và dữ liệu D:

```powershell
Set-Location -LiteralPath $etlRepoRoot
$env:WEBGIS_TEST_DATA_DIR = $etlDataRoot
python -m unittest discover -s .\etl\tests -v
```

Kỳ vọng 7 tests, OK. Đây là kiểm tra đường dẫn sau khi chuyển vào repo, không ghi database và không yêu cầu chạy lại nạp lần đầu/nhập lặp/rollback.

**3. Ghi nhận bộ mã trong Git**

Sau khi kiểm tra các tệp vừa chép và phần bổ sung ignore, stage theo tên cụ thể:

```powershell
git add -- etl/etl_csv.py etl/tests/test_validation.py
git add -- sql/checks/00_kiem_tra_hien_trang.sql sql/test/99_bootstrap_database_test.sql
git add -- docs/etl/README.md docs/etl/kiem_tra_20260925.md docs/etl/source_manifest.csv docs/etl/sau_khi_test_dat.md
git add -- .gitignore
git diff --cached --stat
git diff --cached
```

Nếu diff chỉ gồm phần bạn muốn ghi nhận, thực hiện:

```powershell
git commit -m "Add validated CSV ETL and documented test results"
```

Nếu có staged của việc khác từ trước, tách phạm vi trước khi commit; không dùng `git add .` cho bước này. Việc push theo nhánh/remote đang dùng của dự án. Bạn thực hiện các lệnh trên máy của mình; gói ZIP không tự sửa repo hay tạo commit.

**4. Kiểm tra và sao lưu database chính**

Trong pgAdmin, mở Query Tool của `dongthap_gis`, chạy câu sau và giữ kết quả làm mốc trước khi nhập:

```sql
SELECT current_database() AS database_name,
       (SELECT count(*) FROM public.source_dataset) AS snapshot_count,
       (SELECT count(*) FROM public.conductivity_observation) AS raw_ec_count,
       (SELECT count(*) FROM public.monthly_feature) AS monthly_count;
```

Tên phải là `dongthap_gis`. Theo lần kiểm tra DB chính trước đây, mới có Tân Châu 464 hàng và master 1000 hàng; nếu chưa thay đổi thì số tổng là 2/464/1000. Đây là mốc cũ để đối chiếu, không phải kết quả trực tiếp ở thời điểm hiện tại.

Mở `sql/checks/00_kiem_tra_hien_trang.sql`, chạy riêng A06 để thấy từng snapshot và SHA. Nếu raw Mỹ Tho đã có đúng SHA và 463 hàng thì có thể bỏ qua lần nạp Mỹ Tho. Nếu số tổng khác vì có thêm snapshot, đối chiếu A06 theo SHA; không xóa dữ liệu để ép tổng về con số mẫu.

Backup trong pgAdmin:

1. Tạo thư mục lưu backup trên D, ngoài repo, ví dụ `D:\WebGIS_backups`.
2. Nhấp phải đúng database `dongthap_gis` → Backup.
3. Filename: chọn tệp mới, ví dụ `D:\WebGIS_backups\dongthap_gis_before_mytho_20260925.backup`. Nếu tên đã tồn tại, thêm giờ/phút để giữ bản cũ.
4. Format: Custom. Sao lưu toàn bộ DB, bao gồm cấu trúc và dữ liệu; không bật Only data/Only schemas, không giới hạn vài bảng.
5. Nhấn Backup; mở Processes và đợi trạng thái thành công. Nếu có lỗi, xử lý lỗi trước bước nạp.
6. Kiểm tra tệp backup đã có dung lượng lớn hơn 0. Giữ đường dẫn và log hoàn tất bên D. Đây là xác nhận tạo backup; khả năng khôi phục đầy đủ chỉ được chứng minh khi restore thành công sang DB khác.

**5. Nạp raw Mỹ Tho còn thiếu vào database chính**

Quay lại PowerShell đã khai báo các biến ở bước 2. Dùng cùng host/port/user đã kết nối thành công khi test; lệnh dưới giả định localhost:5432 và user postgres:

```powershell
python "$etlScript" raw "$etlMyThoCsv" --station 019805 --db dongthap_gis --out "$etlOutputRoot" --load --psql "$etlPsql" --host localhost --port 5432 --user postgres
```

Chỉ chạy sau khi backup thành công. Nhập mật khẩu PostgreSQL khi được hỏi. Đầu ra mới ở D, trong `runs\main_load`; chương trình in `run_directory` để tìm đúng lần chạy.

Trong report của lần đó, kiểm tra database=`dongthap_gis`, status=`COMMITTED`, source_rows=463, valid_rows=463, rejected_rows=0, psql_exit_code=0. Số hàng thực sự được chèn hoặc giữ nguyên lấy từ dòng JSON `etl_result` ở cuối database.log.

Trong database.log: nếu snapshot Mỹ Tho mới, inserted_rows=463, unchanged_rows=0, verified_rows=463. Nếu đã có snapshot khớp, inserted_rows=0, unchanged_rows=463, verified_rows=463. `inserted_rows: null` trong report của phiên bản này là giới hạn báo cáo; số thực lấy từ `etl_result`, không kết luận thất bại chỉ vì NULL.

Chạy lại A06/A07 và câu tổng hợp ở bước 4 trên DB chính. Với đúng ba snapshot đang dùng:

| Bộ dữ liệu | Số hàng phải đối chiếu | SHA-256 |
|---|---:|---|
| Raw Tân Châu | 464 | bd4cf100cb4782e37b355d94f15911c1bab2c4a9d4ad69d2fa2c3b4c5d590ba7 |
| Raw Mỹ Tho | 463 | 2cee9c9c1cb8e29e67ea5379391fca507419385cd4fac990edf5119634b65997 |
| Master tháng | 1000 | f9b2de085a265a13e21779aa7c95b8d0caaed9335ae61d820475f54e519eac71 |

Tổng tương ứng 3 snapshot, 927 hàng EC raw và 1000 hàng monthly. Các số tổng phụ thuộc tập snapshot; bằng chứng chính là đúng SHA, mã trạm và số hàng cho từng snapshot. Giữ EC dưới đơn vị mS/m và cờ chất lượng gốc.

**6. Bổ sung tọa độ hai trạm**

File cần dùng nằm trong bộ thực hành cũ ở D: `WebGIS_Tuan04_05\sql\01_toa_do_tram_chay_thu.sql`. Script kiểm tra đúng DB chính, hai mã trạm MRC, nguồn dữ liệu và tọa độ hiện có trước khi cập nhật.

1. Mở Query Tool mới, kết nối `dongthap_gis`.
2. Mở toàn bộ file trên. Xác nhận dòng cuối còn `ROLLBACK;`.
3. Chọn toàn bộ nội dung và Execute script (F5). Xem kết quả SELECT và Messages; nếu có ERROR, dừng để kiểm tra thông báo, không bỏ các khối guard.
4. Kết quả trước rollback phải có đúng hai trạm và các giá trị bên dưới. Lần này chưa lưu thay đổi.
5. Nếu đúng, Save As một bản mới `01_toa_do_tram_ap_dung.sql` ở D. Chỉ đổi dòng cuối thành `COMMIT;`.
6. Chạy lại TOÀN BỘ bản áp dụng từ BEGIN tới COMMIT. Chạy riêng COMMIT sau lần ROLLBACK không áp dụng lại cập nhật.
7. Mở một Query Tool khác trên DB chính và chạy truy vấn đọc bên dưới để xác nhận tọa độ đã được lưu.

| site_code | longitude (X) | latitude (Y) | SRID | Trạng thái khi bổ sung mới |
|---|---:|---:|---:|---|
| MRC_VN_019803 | 105.2480164 | 10.80062008 | 4326 | REPORTED |
| MRC_VN_019805 | 106.3529997 | 10.35912163 | 4326 | REPORTED |

```sql
SELECT current_database() AS database_name,
       site_code, external_site_code, location_status,
       ST_X(geom) AS longitude,
       ST_Y(geom) AS latitude,
       ST_SRID(geom) AS srid,
       location_reference
FROM public.measurement_site
WHERE site_code IN ('MRC_VN_019803', 'MRC_VN_019805')
ORDER BY site_code;
```

Phải có hai hàng đúng tọa độ, SRID 4326 và nguồn KML kèm SHA trong location_reference khi vừa được bổ sung. Tọa độ KML được ghi REPORTED; chỉ nâng VERIFIED khi có bằng chứng xác minh. Nếu tọa độ đúng đã tồn tại với trạng thái và nguồn hợp lệ, script giữ nguyên chúng. Tọa độ EC nằm trong measurement_site; không nhân bản sang salinity_station chỉ để đạt số lượng điểm trên giao diện.

Sau khi xác nhận lưu thành công, chép bản áp dụng vào vị trí migration của repo theo quy ước dự án. Có thể dùng `sql/migrations/20260925_measurement_site_locations.sql` nếu chưa có quy ước khác. Ghi điều kiện trước chạy: schema đã có, raw hai trạm đã nạp. Đây là script áp dụng dữ liệu sau ETL, không phải bootstrap cho DB rỗng. Đối chiếu tên file trùng trước khi chép. Cập nhật báo cáo với ngày chạy, DB đích, kết quả rồi commit các file cụ thể đó.

**7. Những việc làm sau mốc này**

| Việc | Đầu vào cần có trước | Cách thực hiện và kết quả cần giữ |
|---|---|---|
| Nạp ranh giới | Tệp có nguồn, CRS, phạm vi và thời điểm hiệu lực rõ ràng | Chuẩn hóa qua staging; dùng mẫu SQL 04 sau khi điền đúng cột/nguồn; xác nhận MultiPolygon 4326, hình học hợp lệ và valid_from/valid_to |
| Nạp danh mục cống thật | Mã/tên cống, tọa độ riêng của cống và tài liệu nguồn | Thu thập theo CSV mẫu, đối chiếu vị trí, nhập irrigation_gate; mục chưa có tọa độ tiếp tục nằm trong tệp thu thập |
| Minh chứng GIS | Có trạm, ranh giới, cống trong PostGIS | Kết nối QGIS với dongthap_gis, đọc lớp từ DB; chạy các truy vấn SQL 02 với boundary_id phù hợp, giữ CSV/ảnh kết quả |
| Cấu trúc đầu ra dự báo | Chốt mục tiêu EC theo tháng, thời hạn dự báo và khóa nguồn dữ liệu | Đối chiếu hợp đồng API/UI trước khi áp dụng mẫu SQL 03 cho forecast_result/gate_recommendation; kiểm tra FK và ERD |
| Nguồn và chất lượng feature | Metadata thật của các biến trong master | Bổ sung đơn vị, thời gian khả dụng, datum mực nước, nguồn và quy trình tổng hợp; phân biệt tháng trên lịch với tháng có EC |
| Hoàn thiện ERD và hồ sơ | Schema/dữ liệu thực tế sau các bước trên | Xuất ERD, lưu truy vấn minh chứng, kết quả test, manifest, hướng dẫn tái lập; đánh dấu từng đầu ra đạt theo bằng chứng |
| Tích hợp backend/giao diện | Hợp đồng dữ liệu khớp schema thật | API đọc đúng measurement_site/conductivity_observation; giao diện ghi EC mS/m, khoảng thời gian thực, trạng thái thiếu dữ liệu và nguồn; phần khuyến nghị cống là mô phỏng học thuật theo phạm vi dữ liệu |

Trạm đo và cống là hai loại đối tượng khác nhau; không dùng tọa độ trạm thay tọa độ cống. Khoảng cách gần chưa chứng minh trạm đại diện cho cống về thủy văn. EC theo tháng không đủ làm chỉ dẫn vận hành cống thực tế. Hai bảng dự báo/khuyến nghị và giao diện phải thể hiện rõ phạm vi mô phỏng.

Mốc tiếp theo để đối chiếu: A06/A07 trên dongthap_gis sau nạp, truy vấn tọa độ sau COMMIT, và danh sách tên tệp đã đưa vào repo. Không cần gửi lại toàn bộ log test đã đạt.

Tài liệu chính thức: [pgAdmin Backup](https://www.pgadmin.org/docs/pgadmin4/latest/backup_dialog.html), [pgAdmin Query Tool](https://www.pgadmin.org/docs/pgadmin4/latest/query_tool_toolbar.html), [Git ignore](https://git-scm.com/docs/gitignore), [PostGIS ST_MakePoint](https://postgis.net/docs/ST_MakePoint.html).
