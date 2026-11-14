# Hợp nhất temp vào TinBranch — 14/11/2026

## Mã được hợp nhất

- Nhánh đích giữ commit `915ec42`: cache hash nguồn thủy văn, truyền đầu vào thủy văn đã đọc vào dự báo, tăng timeout Timeline và giữ toàn bộ audit station hydrology.
- Nhánh nguồn `temp` tại `084736a`, cộng bản sửa `23f4c8d` trên `codex/fix-temp-integration`.
- Giữ cả cache mô phỏng theo nguồn/ngày, hướng gió theo mùa và tối ưu thủy văn. Không sửa registry, trọng số mô hình hay các giá trị dự báo/đánh giá đã lưu.

## Lỗi đã sửa

1. Alias SQL có ngoặc kép giữ đúng các tên API `predicted_ec_mS_m`, `observed_ec_mS_m`, `abs_error_mS_m` ở cả SELECT và INSERT RETURNING; không còn lỗi KeyError khi lưu/đọc sổ dự báo.
2. Truy vấn phiếu thực địa giữ đúng `ec_mS_m`, `water_temp_degC` và truy vấn tạo nhãn giữ đúng EC. Giao diện và bộ chấm nhãn nhận được cùng hợp đồng dữ liệu.
3. Summary có `by_source.MRC` và `by_source.FIELD_APPROVED`, mỗi nguồn tách ON_TIME/LATE. Các trường summary cũ chỉ còn đại diện MRC, kèm `primary_obs_source=MRC`. Giao diện hiển thị riêng từng nguồn, từ chối hiển thị MAE gộp của máy chủ phiên bản cũ.
4. `.gitattributes` cố định CRLF cho sáu tệp nguồn mà bằng chứng frozen EC gap đã hash theo CRLF. Nội dung mã và manifest nghiên cứu không bị thay đổi; checksum tại checkout chính khớp lại bản gốc.

## Kiểm chứng sau hợp nhất

- JavaScript: **174/174 qua**; frontend production build thành công.
- Python: **168 test, 166 qua, 2 bỏ qua**. Hai test hợp đồng PostgreSQL mới được chạy thật với bảng/view tạm tạo từ định nghĩa migration, rollback và đóng kết nối sau mỗi test.
- Hai test bỏ qua: kiểm tra lỗi kết nối FES do chưa cài `paramiko`, và kiểm tra hash nguồn nghiên cứu Mỹ Thuận do thiếu snapshot nguồn gốc. Các test PostgreSQL mới đều đã chạy. Xem thông báo cụ thể trong `merge-python-tests.log`.
- PostgreSQL tạm kiểm tra lưu issue, đọc issue/score qua API, đọc EC/nhiệt độ phiếu đã duyệt và tạo nhãn tháng từ hai mẫu hợp lệ.
- Kiểm tra cấu hình máy thật: app-health, workspace summary, danh mục mô hình, độ tươi dữ liệu và frame tháng 08/2026 đều HTTP 200. Dự báo ARCHIVE cho tháng 10/2026 tại Mỹ Tho, Mỹ Thuận, Tân Châu đều HTTP 200 với tháng đầu vào 08/2026.
- `git diff --check` và kiểm tra diff đã stage đều qua. Đã cài `psycopg-pool==3.3.3` vào `.venv` chính để khởi động được backend mới.
- Log cục bộ: `merge-python-tests.log`, `merge-js-tests.log`, `merge-runtime-smoke.log` tại gốc dự án; log không được commit.

## Tiếp tục làm việc

Checkout chính là `C:\Users\TOAN TIEN COMPUTER\Documents\CodeWebBaoMatCoSoDuLieu\saltwater-intrusion-warning`, nhánh `TinBranch`. Chạy `./start.ps1` như trước. Merge được lưu cục bộ; chưa push lên origin.

Việc merge mã không tự thay đổi schema hay cấu hình khóa của PostgreSQL đang dùng. Tại lần kiểm tra này, máy có migration `30_dss_storage`, chưa có bảng ledger/field và chưa cấu hình hai khóa cán bộ. Các API dự báo và mô phỏng lõi đã hoạt động; để sử dụng sổ phát hành và phiếu thực địa cần triển khai thêm theo thứ tự:

```powershell
.\.venv\Scripts\python.exe scripts/apply_dss_migration.py --file sql/32_dss_prediction_stations.sql --version 32_dss_prediction_stations --apply
.\.venv\Scripts\python.exe scripts/apply_dss_migration.py --file sql/33_forecast_issue.sql --version 33_forecast_issue --apply
.\.venv\Scripts\python.exe scripts/apply_dss_migration.py --file sql/33b_forecast_issue_guard.sql --version 33b_forecast_issue_guard --apply
.\.venv\Scripts\python.exe scripts/apply_dss_migration.py --file sql/35_field_measurement.sql --version 35_field_measurement --apply
```

Xem giao thức nhãn và tài liệu migration 32/33/35 trước khi bật chức năng cán bộ. Khi cấu hình `WEBGIS_WRITE_API_KEY`, mọi endpoint lưu bản nháp/lịch sử được bảo vệ bởi middleware cũng yêu cầu `X-API-Key`; không đưa khóa vào frontend build hay commit vào Git.
