> Tài liệu lịch sử, không phải hướng dẫn chạy hiện tại. Các đường dẫn thành phần đã loại bỏ chỉ còn trong bản sao lưu; xem [README hiện tại](../../README.md). Giữ nội dung đánh giá để truy vết.

# Bàn giao đợt kiểm tra 14–15/10/2026

Nguyên mẫu đã chạy ở chế độ đọc tệp có nguồn, với FastAPI và frontend của repository chính. Chưa nghiệm thu luồng PostgreSQL/PostGIS thật: server cục bộ phản hồi nhưng yêu cầu mật khẩu, `.env` chưa tồn tại tại lần kiểm tra cuối. Không tự chuyển lỗi PostgreSQL thành dữ liệu mẫu.

## Bảo toàn và hợp nhất

Không thay tên đề tài hoặc đề cương, không push, không thay đổi hai tệp minh chứng đã bị xóa trước phiên làm việc. Không chép đè Step08 lên repository. Danh sách các tệp hợp nhất chọn lọc cùng hash bản tham khảo nằm trong `selective_merge_20261014.json`. Mô hình cũ `run_forecast.py` và kết quả cũ được giữ; thí nghiệm hiện dùng `run_monthly_ec.py`.

Phát hiện ở pipeline cũ `pipelines/models/14_model_baseline.py`: lựa chọn accepted dựa trên test, RF dùng biến khí tượng cùng tháng đích mà chưa chứng minh khả dụng. Không sử dụng bảng accepted cũ làm bằng chứng cải tiến dự báo. Audit cũ có đường dẫn không còn đúng; đã sửa đường dẫn MRC/KML. Master trong archive vẫn khác header và SHA-256 của manifest cũ, nên giữ trạng thái FAILED, không sửa gốc để khớp manifest.

## Dữ liệu tính lại

| Nguồn / trạm | Số mẫu | Đầu–cuối | Khoảng cách trung vị / lớn nhất | Phạm vi |
|---|---:|---|---|---|
| MRC Tân Châu 019803 | 464 | 15/05/1985–15/12/2023 | 31 / 42 ngày | EC mS/m, UNVERIFIED |
| MRC Mỹ Tho 019805 | 463 | 26/06/1985–15/12/2023 | 31 / 45 ngày | EC mS/m, UNVERIFIED |
| RIA2, 10 điểm riêng | 40 | 28/09–11/11/2025 | 14 / 14 ngày ở mỗi điểm | 4 mẫu/điểm; chỉ có ngày |

Mỗi tháng MRC trong khoảng trên có một mẫu. Builder từ chối tự tổng hợp nhiều mẫu trong một tháng nếu nguồn thay đổi. Mốc 00:00 của MRC là timestamp nguồn, chưa được xác nhận là giờ lấy mẫu. RIA2 giữ `observed_at=null`. Đổi µS/cm sang mS/m bằng phép đổi đơn vị chính xác 0,1; không đổi EC sang độ mặn. MRC dùng KML EPSG:4326 với trạng thái REPORTED. RIA2 giữ tọa độ nguồn và CRS chưa rõ, geometry mặc định NULL.

Audit tái lập: `python scripts/audit_research_data.py`. Kết quả tại `data/research/audit/`: 73 chuỗi/biến, thống kê thiếu, trùng, khoảng cách lấy mẫu, histogram khoảng trống, cực trị và cờ nguồn; checksum của 148 tệp raw. Cờ 3×IQR chỉ để rà soát, không loại cực trị thật. Audit chưa kiểm toán số học tất cả NetCDF hoặc xác minh địa hình/thủy lực GIS; inventory ghi rõ NOT_RUN cho phần đó. `input_label_overlap.csv` đếm giao nhau theo tháng, không coi đó là bằng chứng khả dụng tại thời điểm dự báo, không tạo thêm nhãn EC từ khí tượng.

DAHITI là mực nước suy ra từ vệ tinh; GloFAS là lưu lượng mô hình/tái phân tích; Open-Meteo là sản phẩm archive khí tượng, chỉ gọi ERA5 khi metadata chọn rõ; GFZ Tân Châu là chuỗi lưu lượng có lấp khoảng trống. Không dùng các đại lượng này thay EC. Sơn Đốc là độ mặn g/L, nghiên cứu riêng tại địa điểm khác. Bộ mô phỏng/synthetic không đi vào snapshot nghiên cứu.

## Bổ sung và truy vết nguồn

- Đã tải lại API MRC ngày 14/10, lưu JSON gốc, CSV, inventory, URL, thời điểm, SHA-256, cờ nguồn trong `data/external/mrc_20261014_network`. Không có EC sau 2023 trong hai chuỗi đã truy vấn. Đối chiếu bản trích dùng huấn luyện: 927 timestamp/giá trị khớp, không có dòng khác. Mực nước manual/telemetry năm 2026 không tạo nhãn EC năm 2026.
- Đã tải lại bốn tài liệu RIA2 15–18/2025 và xác minh khớp hash của hồ sơ Step08. Giữ phương pháp trích xuất, vị trí bảng, ngày đo, ngày bài viết tách biệt. Đối chiếu hash xác nhận đúng tệp nguồn; chưa thực hiện lại toàn bộ chép bảng 40 dòng trong phiên này, không nâng cờ VALIDATED.
- Tìm được báo cáo thủy lợi Tiền Giang ngày 13/10/2026: https://thuyloitiengiang.vn/en/web/thuyloitiengiang/chi-tiet-tin-tuc?id=522066 . Tải gốc bị lỗi xác minh chứng chỉ HTTPS. Không tắt SSL, không lấy snippet tìm kiếm làm quan trắc. Đây là đầu mối cần tiếp tục, chưa nhập số liệu.
- Đã tải bản tin SIWRR mùa khô 2025–2026: https://www.siwrr.org.vn/docs/2023/files/20251124-Ban-tin-mua-kho-2025-2026-DB-HTVH-CL-CB-24-11-2025.pdf . Phân loại dự báo cơ quan khác, không nhập làm nhãn quan trắc.
- Truy vấn nguồn địa phương chưa thu được chuỗi số có đủ định danh/thời gian/đơn vị để nhập. Không suy luận rằng các cơ quan không có dữ liệu mới. Nhật ký tải thành công/thất bại tại `data/external/source_review_*`; chạy lại bằng `python scripts/refresh_review_sources.py`.

## Bài toán dự báo và kết quả

Mục tiêu: giá trị mẫu EC của tháng kế tiếp, không phải trung bình liên tục cả tháng. Origin cuối tháng trước; ngày lấy mẫu tháng đích có thể thay đổi, nên thời gian từ origin tới mẫu không cố định 30 ngày. Không suy ra ngày bắt đầu mặn, không chuyển kết quả tháng thành 1/3/7 ngày hoặc 2/6/12 giờ. Bốn mẫu RIA2 không đủ kiểm chứng trước 14 ngày.

Train trước 2021, validation năm 2021, test 2022–2023. Expanding-window walk-forward, RF refit ở từng origin; chỉ EC đã khả dụng theo kịch bản và đặc trưng lịch. Chọn cấu hình và mô hình bằng validation trên tập tháng chung, lưu selection trước khi chạy test. Hai giả định công bố cuối tháng +0/+30 ngày; chưa có nhật ký công bố/vintage thực. Các nhãn validation chưa công bố tại origin test đầu tiên không tham gia lựa chọn. Test đã từng được xem trong dự án, không phải kiểm thử mù mới.

| Trạm | Trễ (ngày) | MAE Persistence | MAE Seasonal Naive | MAE RF | RMSE RF | n chung |
|---|---:|---:|---:|---:|---:|---:|
| Mỹ Tho | 0 | 9,155 | 20,150 | 22,253 | 41,356 | 24 |
| Mỹ Tho | 30 | 12,675 | 20,150 | 29,491 | 49,362 | 24 |
| Tân Châu | 0 | 2,666 | 2,382 | 1,440 | 1,936 | 24 |
| Tân Châu | 30 | 5,147 | 2,382 | 2,167 | 2,965 | 24 |

Đơn vị sai số mS/m. Độ phủ test 24/24 tháng có nhãn ở cả bốn thí nghiệm. RF được chọn trên validation cả bốn lần; RF Mỹ Tho kém Persistence, không đổi người thắng theo test. Đánh giá EC cao dùng P90 chỉ tính trên train: Mỹ Tho 71,1 mS/m nhưng chỉ có **1 mẫu test cao**, không đủ kết luận độ tin cậy trong đợt mặn. Tân Châu P90 21,265, có 10 mẫu cao; MAE RF 1,855 và 3,179 tương ứng độ trễ 0/30 ngày. Đây là phân nhóm EC tương đối, không phải ngưỡng mặn hay ngưỡng vận hành.

Mỗi run có predictions, metrics, high_ec_metrics, validation, split, selection, biểu đồ và manifest hash/config/version. Registry tại `data/research/experiment_registry.json`. Các run nằm trong `runs/local_ec_backtest` (Git hiện bỏ qua runs), cần chạy `--fit` khi tái lập ở checkout khác. Không nạp pickle từ nguồn ngoài. Dự báo kế tiếp của chuỗi là tháng 01/2024, được gắn lịch sử; không công bố như dự báo hôm nay.

## WebGIS và cống

Trang `research.html` tích hợp nguồn, quan trắc, bản đồ, thực tế–dự báo, bảng chỉ số, tải minh chứng và bốn cống trong phạm vi trang 2 phụ lục nguồn. Không tuyên bố đây là toàn bộ cống của tỉnh. Tọa độ cống chưa có, không dựng điểm giả. Lớp RIA2 tham khảo chỉ bật chủ động với cảnh báo giả định CRS.

API phân biệt snapshot/postgres. Migration `sql/04_research_workspace.sql` bổ sung schema riêng, không xóa bảng public. Import transaction, khóa nạp, snapshot SHA-256 và ràng buộc khóa ngoại tránh nạp lặp cùng snapshot. Chỉ dry-run đã chạy; chưa chứng minh migration trên DB thật.

Hồ sơ cống trả thông tin thiếu về vị trí, chức năng, liên kết thủy lực, quy trình, EC, mực nước hai phía cùng hệ cao độ, trạng thái và nhu cầu nước. Khoảng cách chỉ lọc ứng viên. JSON do người dùng khai báo không chứng minh APPROVED/VALIDATED: endpoint giữ recommendation=null khi máy chủ chưa có hồ sơ thực địa được xác minh; kết quả tính quy tắc nếu có chỉ lưu riêng để rà soát. Chưa có dự báo vài ngày đã kiểm chứng để phát hành cảnh báo chuẩn bị kế hoạch; hệ thống hiện hỗ trợ rà soát dữ liệu và hồ sơ, không đưa lịch đóng liên tục hay mặc định mở cống.

## Kiểm tra và việc còn lại

26 kiểm thử Python mô hình/pipeline và 31 kiểm thử API đã đạt. 22 kiểm thử JavaScript đã đạt, frontend build thành công. API test dùng mock DB là kiểm thử hợp đồng, không phải DB thật. HTTP API nghiên cứu đã được gọi thật; ba endpoint DB trả 503 đúng tình trạng thiếu xác thực. Trình duyệt đã mở trang, chọn trạm Mỹ Tho và đổi kịch bản Tân Châu trễ 30 ngày; biểu đồ và đánh giá cập nhật đúng. Chưa nghiệm thu tất cả kích thước màn hình hoặc thiết bị.

Lượt cuối: thêm 4 kiểm thử audit đạt; thu minh chứng API nghiên cứu không có lỗi HTTP. Replay đã mở trong trình duyệt và bật số đo đối chiếu; API trả 990/930/840 bản ghi ở 2/6/12 giờ. Chỉ kiểm tra đọc bộ kết quả Sơn Đốc hiện có, không huấn luyện lại hoặc chứng nhận khoa học cho bộ này. Log và bảng chỉ số gọn được giữ trong `docs/reports/validation_20261015`; ảnh minh chứng `webgis_forecast_review.jpg`, `webgis_replay_review.jpg` cùng thư mục báo cáo.

Tiếp theo: cấu hình `.env` cục bộ; nạp schema/snapshot và kiểm tra đọc thật như `docs/run_guide.md`; xác minh CRS/định danh công trình; thu chuỗi EC/độ mặn hằng ngày hoặc dày hơn cùng mực nước, lịch công bố và vận hành; đánh giá trên giai đoạn tương lai chưa dùng điều chỉnh mô hình. Đề xuất trao đổi giảng viên: giữ tên đề tài, nghiệm thu phần WebGIS truy vết + kiểm chứng mẫu EC tháng + hồ sơ điều kiện cống; trình bày dự báo ngắn hạn/vận hành như phần cần dữ liệu thực địa, không tự sửa đề cương.
