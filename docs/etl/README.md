# Chạy ETL ở ổ D và đưa mã đã kiểm tra vào repo ổ C

Cập nhật ngày 25/09/2026: đã đối chiếu log nạp lần đầu và nhập lặp; người thực hiện xác nhận phép thử rollback cũng đúng kịch bản. Tiếp tục theo [sau_khi_test_dat.md](sau_khi_test_dat.md). Các mục thử lặp/rollback bên dưới được giữ để tái lập khi cần, không yêu cầu chạy lại những ca đã đạt.

Giữ thư mục thực hành ở D làm nơi thử nghiệm và lưu raw/log. Repo ở C lưu mã ETL, SQL, kiểm thử, manifest và hướng dẫn để người khác tái lập. Thư mục chứa Python không quyết định database đích: host, port và --db mới quyết định kết nối PostgreSQL.

## 1. Gói này chứa gì?

| Đường dẫn đưa vào repo | Vai trò |
|---|---|
| etl/etl_csv.py | Đọc/kiểm tra/chuẩn hóa/nạp CSV; giữ nguyên mã từ bộ thực hành trước |
| etl/tests/test_validation.py | 7 kiểm thử offline; bổ sung khả năng đọc dữ liệu test ngoài repo |
| sql/checks/00_kiem_tra_hien_trang.sql | Kiểm tra database bằng các SELECT A01–A12 |
| sql/test/99_bootstrap_database_test.sql | Dựng database test mới theo schema nền; chỉ dùng cho test |
| docs/etl/README.md | Hướng dẫn chạy và tích hợp |
| docs/etl/kiem_tra_20260925.md | Kết quả nạp lần đầu, nhập lặp và xác nhận rollback |
| docs/etl/sau_khi_test_dat.md | Thứ tự đưa mã vào repo, sao lưu, nạp DB chính và tọa độ |
| docs/etl/source_manifest.csv | Nhận diện tệp gốc bằng tên/hash |
| gitignore_webgis.txt | Các dòng tham khảo để bổ sung vào .gitignore đang có |

Gói này không tự sửa repo, không tự commit/push và không chứa raw hoặc toàn bộ log. Ba ca nạp lần đầu/nhập lặp/rollback được ghi nhận theo mức bằng chứng trong tài liệu kiểm tra; các phần GIS, provenance của feature và báo cáo tuần vẫn cần hoàn thành riêng. Thay đổi duy nhất ở mã test là cho phép chọn thư mục dữ liệu bằng WEBGIS_TEST_DATA_DIR; nghiệp vụ ETL không thay đổi.

## 2. Xác định đúng thư mục làm việc ở D

Mở Terminal PowerShell. Dán đường dẫn thực khi được hỏi, chọn thư mục có trực tiếp etl_csv.py và data/raw, không chọn thư mục ZIP chưa giải nén.

```powershell
$etlTestRoot = (Read-Host 'Duong dan thu muc thuc hanh tren o D').Trim('"')
$etlTestRoot = (Resolve-Path -LiteralPath $etlTestRoot).Path
Set-Location -LiteralPath $etlTestRoot
Get-Location
Test-Path .\etl_csv.py
Test-Path .\data\raw\mrc_tanchau.csv
Test-Path .\data\raw\mrc_mytho.csv
Test-Path .\data\raw\master_timeseries.csv
python --version
```

Bốn Test-Path phải True. Nếu False, chọn lại thư mục; không chuyển tệp ngẫu nhiên để sửa lỗi đường dẫn.

Nếu terminal mới chưa có biến psql, khai báo lại. Đường dẫn sau là ví dụ cho vị trí cài PostgreSQL 17 mặc định; dùng vị trí thật trên máy bạn:

```powershell
$etlPsql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe'
Test-Path $etlPsql
& $etlPsql --version
```

## 3. Thử nhập lặp — làm ngay trên database test hiện có

Chạy từng lệnh, giữ nguyên dữ liệu gốc. Chỉ chuyển sang lệnh kế tiếp nếu lệnh trước thành công. Host/port/user phải khớp cấu hình pgAdmin của bạn.

```powershell
python .\etl_csv.py raw .\data\raw\mrc_tanchau.csv --station 019803 --db dongthap_gis_etl_test --out .\runs\repeat_test --load --psql "$etlPsql" --host localhost --port 5432 --user postgres
```

```powershell
python .\etl_csv.py raw .\data\raw\mrc_mytho.csv --station 019805 --db dongthap_gis_etl_test --out .\runs\repeat_test --load --psql "$etlPsql" --host localhost --port 5432 --user postgres
```

```powershell
python .\etl_csv.py master .\data\raw\master_timeseries.csv --db dongthap_gis_etl_test --out .\runs\repeat_test --load --psql "$etlPsql" --host localhost --port 5432 --user postgres
```

Mỗi lệnh in đường dẫn run_directory. Mở database.log của đúng run đó, tìm dòng JSON kết quả etl_result ở cuối, không chỉ nhìn câu SELECT đang được echo.

| Tệp | inserted_rows mong đợi | unchanged_rows | verified_rows |
|---|---:|---:|---:|
| Tân Châu | 0 | 464 | 464 |
| Mỹ Tho | 0 | 463 | 463 |
| Master | 0 | 1000 | 1000 |

Report vẫn phải COMMITTED và psql_exit_code=0. Sau đó chạy A06/A07/A08 trên dongthap_gis_etl_test, lưu kết quả. Với test chỉ chứa ba snapshot này: source_dataset=3, tổng EC raw=927, master=1000. Không tạo lại database hay chạy lại bootstrap cho phép thử này.

## 4. Thử rollback mà không xóa dữ liệu đang có

Chỉ thực hiện trên dongthap_gis_etl_test. Dùng 10 quan trắc thật trích từ raw Mỹ Tho làm tệp thử, tạo snapshot mới theo hash; giữ nguyên tệp raw gốc. Bài thử chủ động gây lỗi nên psql trả mã khác 0 là kết quả mong đợi.

Tạo tệp thử ở D:

```powershell
New-Item -ItemType Directory -Path .\data\test -Force | Out-Null
Import-Csv .\data\raw\mrc_mytho.csv |
    Select-Object -First 10 |
    Export-Csv .\data\test\mytho_rollback_fixture.csv -NoTypeInformation -Encoding utf8

python .\etl_csv.py raw .\data\test\mytho_rollback_fixture.csv --station 019805 --db dongthap_gis_etl_test --out .\runs\rollback_test
```

Lệnh không có --load chỉ tạo SQL. Report phải có 10 hàng hợp lệ, SHA mới và READY_SQL_NOT_LOADED. Ghi lại run_directory và sha256.

1. Mở load.sql trong run_directory đó bằng VS Code.
2. Save As thành load_rollback_test.sql trong cùng thư mục.
3. Ngay trước dòng cuối COMMIT; thêm một dòng `SELECT 1 / 0;`.
4. Lưu file. Chưa chạy file load.sql gốc, vì nó sẽ commit snapshot thử nếu được chạy nguyên văn.

Chạy SQL có lỗi chủ động:

```powershell
$etlRollbackSql = (Read-Host 'Duong dan day du den load_rollback_test.sql').Trim('"')
& $etlPsql -X --set=ON_ERROR_STOP=1 --host=localhost --port=5432 --username=postgres --dbname=dongthap_gis_etl_test --file="$etlRollbackSql"
$LASTEXITCODE
```

Kỳ vọng lỗi division by zero và mã psql khác 0. Nếu psql báo sai password/đường dẫn/kết nối thì đó chưa phải phép thử rollback đạt. psql phải đi qua phần INSERT rồi mới lỗi ở phép chia; khi kết nối kết thúc, transaction chưa commit sẽ bị hoàn tác.

Mở Query Tool của database test. Thay chuỗi trong dấu nháy bằng SHA 64 ký tự lấy từ report của tệp 10 hàng, chạy:

```sql
SELECT count(*) AS test_snapshot_rows
FROM public.source_dataset
WHERE sha256 = '<SHA_CUA_MYTHO_ROLLBACK_FIXTURE>';

SELECT count(*) AS raw_ec_rows FROM public.conductivity_observation;
SELECT count(*) AS monthly_rows FROM public.monthly_feature;
```

Kỳ vọng: 0 snapshot thử, raw EC vẫn 927, monthly vẫn 1000 nếu test chỉ có bộ dữ liệu đang kiểm tra. Không nhập lại SQL gốc của fixture sau phép thử. Giữ file lỗi chủ động ở D, không đưa nó vào thư mục SQL chính thức. Trường report của lần generate vẫn READY_SQL_NOT_LOADED vì lần chạy lỗi được gọi riêng bằng psql; ghi bằng chứng rollback vào tài liệu kiểm thử.

## 5. Chép phần đạt vào repo ổ C

Sau khi thử lặp/rollback đạt, giải nén gói này ra một thư mục riêng ở D. Mở repo C trong VS Code, chạy git status trước khi chép để biết có thay đổi đang làm dở hay không.

Chép etl, sql/checks, sql/test và docs/etl vào đúng các thư mục tương ứng của repo. Giữ các tệp SQL/schema đã có trong repo. Nếu có tên tệp trùng, dùng Compare/Diff để đối chiếu; không chọn Replace All. Không đặt ZIP nguyên khối trong repo thay cho mã nguồn.

Tọa độ/GIS/forecast schema trong bộ thực hành cũ vẫn ở D cho đến khi bạn thực hiện và kiểm tra chúng. Khi đạt, đưa từng script phù hợp vào repo theo lịch sử migration đang dùng. ETL, SQL và kiểm thử đều là thành phần triển khai tiểu luận dù chúng không xuất hiện trực tiếp trên giao diện web.

Mở .gitignore hiện có, bổ sung các dòng thích hợp từ gitignore_webgis.txt. Không ghi đè nội dung ignore của frontend/backend. Không ignore toàn bộ *.sql, *.csv hay tests/ vì có thể che mã nguồn, manifest và test cần quản lý. Raw/log để ngoài repo ở D thì vốn đã không thuộc working tree.

.gitignore chỉ tác động tệp chưa được Git theo dõi. Nếu tệp sinh ra đã được track từ trước, cần xem đúng tên bằng git ls-files rồi xử lý riêng; không dùng lệnh xóa hàng loạt.

## 6. Kiểm tra lại mã ở C nhưng dữ liệu/log vẫn ở D

Mở Terminal tại repo C. Các biến chỉ có hiệu lực trong terminal hiện tại; mở terminal mới cần khai báo lại:

```powershell
$etlRepoRoot = (Get-Location).Path
$etlDataRoot = (Read-Host 'Duong dan data\raw cua bo thuc hanh tren o D').Trim('"')
$etlDataRoot = (Resolve-Path -LiteralPath $etlDataRoot).Path
$etlOutputRoot = (Read-Host 'Duong dan thu muc luu log moi tren o D').Trim('"')
$env:WEBGIS_TEST_DATA_DIR = $etlDataRoot

python -m unittest discover -s .\etl\tests -v
```

Phải có 7 tests OK. Bản test trong gói mới đọc đường dẫn qua WEBGIS_TEST_DATA_DIR; bản test cũ mặc định tìm data/raw cạnh etl_csv.py nên không phù hợp nếu bạn đổi bố cục mà không cấu hình dữ liệu.

Thử generate SQL từ mã ở C, chưa ghi DB:

```powershell
$etlMyThoCsv = Join-Path $etlDataRoot 'mrc_mytho.csv'
python .\etl\etl_csv.py raw "$etlMyThoCsv" --station 019805 --db dongthap_gis_etl_test --out "$etlOutputRoot"
```

Kỳ vọng 463 dòng hợp lệ, 0 reject, READY_SQL_NOT_LOADED và đầu ra ở D. Nếu mã ETL ở C trùng SHA-256 với bản đã chạy đạt ở D, không cần lặp lại phép thử nạp database chỉ vì chuyển thư mục. Chỉ kiểm tra nạp lại khi mã hoặc cấu hình kết nối đã thay đổi. Không dùng đường dẫn .\data\raw nếu bạn đang đứng ở repo C và raw thực nằm trên D.

## 7. Commit những đường dẫn đã chọn

Chạy tại gốc repo C, sau khi đã xem diff và kiểm tra đường dẫn không trùng công việc khác:

```powershell
git status --short
git add -- etl/etl_csv.py etl/tests/test_validation.py
git add -- sql/checks/00_kiem_tra_hien_trang.sql sql/test/99_bootstrap_database_test.sql
git add -- docs/etl/README.md docs/etl/kiem_tra_20260925.md docs/etl/source_manifest.csv
git add -- .gitignore
git diff --cached --stat
git diff --cached
```

Nếu có tệp staged từ công việc khác, xử lý phạm vi staged trước khi commit. Sau khi xác nhận đúng danh sách:

```powershell
git commit -m "Add CSV ETL with validation and documented database checks"
```

Bạn có thể push nhánh đang dùng sau khi kiểm tra remote/upstream. Không cần đổi cách chia nhánh của dự án để hoàn thành bước này. Chỉ ghi “idempotence/rollback đạt” trong báo cáo hoặc commit khi đã có kết quả thực tương ứng.

## 8. Nạp Mỹ Tho lên database chính và cập nhật tọa độ

Log đã gửi hiện chỉ chứng minh nạp vào dongthap_gis_etl_test. Sau khi backup DB chính và các kiểm thử đạt, dùng mã đã giữ trong repo C với raw/log ở D:

```powershell
$etlPsql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe'
$etlMainOutput = Join-Path $etlOutputRoot 'main_load'
python .\etl\etl_csv.py raw "$etlMyThoCsv" --station 019805 --db dongthap_gis --out "$etlMainOutput" --load --psql "$etlPsql" --host localhost --port 5432 --user postgres
```

Kiểm tra report ghi database=dongthap_gis, status=COMMITTED. Chạy A06/A07 trên DB chính, đối chiếu theo SHA: Tân Châu 464, Mỹ Tho 463; master cũ 1000. Nếu Mỹ Tho đã được nhập từ một lần khác, inserted_rows=0 là bình thường khi snapshot khớp.

Tiếp tục file sql/01_toa_do_tram_chay_thu.sql trong bộ thực hành cũ: Query Tool DB chính, chạy ROLLBACK để xem, rồi chuyển dòng cuối thành COMMIT và chạy lại khi đúng trạm/nguồn/tọa độ. A09 phải có hai trạm có SRID 4326, vị trí REPORTED hoặc trạng thái đã có hợp lệ. Khi kiểm chứng xong, đưa bản migration áp dụng cùng bằng chứng vào repo; giữ bản rehearsal để phân biệt nếu cần.

Phần còn lại của tuần 4–5: ranh giới và danh mục cống có nguồn, query GIS/QGIS từ PostGIS, hai bảng forecast_result/gate_recommendation nếu thiếu, ERD thực tế, metadata feature và báo cáo. Ba log ETL không thay thế các đầu ra đó.

## Tài liệu tham chiếu

- PostgreSQL 17 psql: https://www.postgresql.org/docs/17/app-psql.html
- Git ignore: https://git-scm.com/docs/gitignore
