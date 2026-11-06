# Kiến trúc WebGIS và dự báo EC theo tháng

Ngày cập nhật: 01/11/2026. Phạm vi được chọn: **WebGIS kết hợp dự báo giá trị mẫu EC tháng kế tiếp tại từng trạm**. Tài liệu mô tả trách nhiệm các thành phần và nguyên tắc tích hợp; kết quả nghiệm thu cần đối chiếu với lần kiểm tra thực tế, không suy ra từ sơ đồ.

## 1. Sản phẩm và giới hạn dữ liệu

Ứng dụng giúp chọn trạm, xem EC theo thời gian, đối chiếu thực đo với dự báo hồi cứu, đọc sai số so với baseline và truy nguồn. EC giữ đơn vị mS/m. Một mẫu trong tháng không đại diện mặc nhiên cho trung bình hoặc cực đại cả tháng.

Bộ nghiên cứu hiện có 977 quan trắc: 927 MRC tại Mỹ Tho/Tân Châu và 50 RIA2 tại 10 điểm. Chuỗi MRC kết thúc năm 2023 và còn cờ nguồn chưa xác minh. Dữ liệu khí tượng đến 2026 không bổ sung nhãn EC thực đo sau 2023. Không quy đổi EC sang độ mặn khi chưa có phương pháp, cơ sở nhiệt độ, hiệu chuẩn và sai số phù hợp.

Phần công trình phục vụ xem hồ sơ và phần bằng chứng còn thiếu. Kết quả mô phỏng phải được nhận diện rõ. Khoảng cách từ trạm tới cống không chứng minh quan hệ thủy lực; dự báo tại trạm không tự trở thành dự báo tại cống. Ứng dụng không phát lệnh đóng/mở thiết bị.

## 2. Luồng dữ liệu

```mermaid
flowchart TD
    A[Nguồn EC, khí tượng, thủy văn và GIS] --> B[Thu thập và lưu nguồn, manifest]
    B --> C[Chuẩn hóa, QA và ghi lý do loại]
    C --> D[Snapshot nghiên cứu có phiên bản]
    C --> E[PostgreSQL và PostGIS]
    C --> F[Đặc trưng đúng thời điểm phát hành]
    F --> G[Đánh giá mô hình ngoài request web]
    G --> H[Artifact: protocol, dự báo, metrics, manifest]
    H --> D
    D --> I[Repository đọc dữ liệu]
    E --> I
    I --> J[Service và quy tắc nghiệp vụ]
    J --> K[FastAPI]
    K --> L[WebGIS: quan trắc, dự báo, chất lượng, hồ sơ]
```

Mũi tên QA tới PostgreSQL thể hiện luồng nhập có kiểm soát, không phải cơ chế tự đồng bộ đang chạy. Tương tự, một thư mục kết quả mới chưa tự trở thành phiên bản đang phục vụ. Cần bước tiếp nhận và kiểm tra hợp đồng dữ liệu trước khi đưa artifact vào ứng dụng.

## 3. Trách nhiệm các lớp

| Thành phần | Trách nhiệm | Ranh giới |
| --- | --- | --- |
| `backend/main.py` | Tạo ứng dụng, middleware và đăng ký router | Không huấn luyện mô hình |
| `backend/api/` | Route HTTP, kiểm tra đầu vào và mã lỗi | Không chứa trực tiếp toàn bộ SQL hoặc quy tắc đánh giá |
| `backend/services/` | Điều phối ca sử dụng, chuẩn bị kết quả cho API | Không coi khai báo người dùng là chứng từ đã thẩm định |
| `backend/repositories/` | Đọc snapshot, kết quả tệp hoặc dữ liệu DB theo chế độ | Không chuyển nguồn âm thầm khi DB lỗi |
| `backend/domain/` | Quy tắc nghiệp vụ và trạng thái hồ sơ | Không phụ thuộc giao diện trình duyệt |
| `backend/research.py` | Lớp tương thích cho import/router nghiên cứu cũ trong quá trình chuyển đổi | Mã nghiệp vụ mới thuộc các lớp chuyên trách |
| `frontend/` | Trang ứng dụng, bản đồ, bộ lọc, bảng, biểu đồ và điều hướng | Không tự tạo bằng chứng xác minh hoặc quan trắc |
| `scripts/`, `pipelines/`, `etl/`, các runner khoa học | Thu thập, chuẩn hóa, QA và đánh giá ngoài web | Không chạy huấn luyện theo mỗi thao tác chọn trạm |
| `data/raw/`, `data/external/` | Nguồn gốc, hồ sơ tải và tiếp nhận | Bảo toàn nội dung và provenance |
| `data/research/`, `runs/`, `outputs/` | Snapshot và kết quả có phiên bản | Phân biệt artifact đang phục vụ với nghiên cứu chưa tích hợp |
| `sql/` | Schema, migration và kiểm toán dữ liệu | Thay đổi schema/nhập DB là bước riêng có kiểm soát |

Các module đã được tách trong đợt chuyển đổi:

- `backend/api/workspace.py`: adapter HTTP cho workspace.
- `backend/services/workspace.py`, `forecasts.py`, `gates.py`: ca sử dụng đọc dữ liệu, metadata/kiểm tra kết quả tháng và rà soát hồ sơ.
- `backend/repositories/workspace.py`: đọc tệp và PostgreSQL theo nguồn được chọn.
- `backend/domain/workspace.py`, `gates.py`: hợp đồng snapshot và bộ đánh giá cống độc lập HTTP.
- `backend/research.py`: facade tương thích xuất router, `validate_bundle` và `load_bundle`; `run_gate_advisor.py` là wrapper CLI của bộ đánh giá domain.

Đây là mô tả cấu trúc mã; kết quả chạy cần được kiểm tra riêng. Các thành phần lịch sử chưa thuộc phạm vi tách vẫn giữ adapter hiện có.

## 4. Điều hướng theo công việc

Trang chính của đợt chuyển đổi là `frontend/workspace.html`. Điều hướng hash tổ chức theo công việc:

| Mục | Luồng chính |
| --- | --- |
| `#overview` | Hiểu phạm vi, dữ liệu đang có và chọn việc cần làm |
| `#observations` | Chọn trạm, thời gian, xem bản đồ/bảng/biểu đồ và xuất dữ liệu |
| `#forecasts` | Chạy form dự báo đa biến; phần tham khảo riêng cho thí nghiệm hồi cứu, baseline và sai số |
| `#data-quality` | Đọc nguồn, cờ chất lượng, độ phủ và giới hạn dữ liệu |
| `#gates` | Xem hồ sơ công trình và bằng chứng cần bổ sung |

`frontend/src/app/workspace.js` khởi tạo ứng dụng; `app/navigation.js` quản lý điều hướng. Các feature nằm trong `frontend/src/features/`: `observations.js`, `forecasts.js`, `weather-estimates.js`, `gate-dossiers.js` và `overview.js`. Lớp gọi API dùng `frontend/src/shared/workspace-api.js`; tiện ích giao diện dùng `shared/ui.js`. Phần tiếp nhận `intake.js` được hiển thị trong mục chất lượng dữ liệu, vẫn tách khỏi quan trắc đã tiếp nhận.

Từ mục Quan trắc, nút xem kiểm chứng chuyển sang đúng thí nghiệm của trạm MRC đang chọn. Trạm RIA2 chưa có thí nghiệm tháng được thông báo rõ. Lựa chọn trạm và thí nghiệm được nhớ trong phiên trình duyệt; mỗi module hủy yêu cầu cũ khi thay đầu vào để tránh hiển thị kết quả trạm trước.

`frontend/index.html` tiếp tục phục vụ lịch sử PostgreSQL với lựa chọn dataset rõ ràng. `frontend/research.html` chuyển tới trang workspace và hỗ trợ hash cũ qua `frontend/src/app/legacy.js`. Tên hiển thị theo nghiệp vụ; các tên API/adapter cũ không buộc giao diện phải lấy “research” làm trung tâm điều hướng.

Lịch sử PostgreSQL cũng đã tích hợp vào mục Quan trắc qua `features/database-history.js`. Bản đồ nằm ở `features/observations-map.js`; biểu đồ ở `shared/time-series.js`; ngưỡng tự nhập ở `shared/ec-scenario.js`; kiểu giao diện ở `app/workspace.css`. `features/next-forecast.js` đọc dự báo sau mẫu cuối đã lưu. `backend/domain/gate_simulation.py` tính kịch bản cống độc lập với trạng thái phê duyệt. Các entry point `research` chỉ giữ tương thích cho phần đã chuyển.

Nhánh dự báo đa biến chính dùng `backend/api/multivariate.py` → `services/multivariate.py` → `domain/multivariate_ec.py`; khí tượng do `repositories/multivariate_inputs.py` cung cấp. `scripts/update_multivariate_weather.py` cập nhật nguồn ERA5 có đơn vị; `scripts/train_multivariate_ec.py` đánh giá và lưu model ngoài request. `features/multivariate-forecast.js` gọi suy luận và gửi kết quả sang lớp dự báo riêng trên bản đồ. Phần đánh giá mô hình EC trễ cũ được thu gọn để tham khảo; CSV dùng khí tượng cùng tháng nằm trong mục chất lượng dữ liệu.

## 5. Phân biệt các sản phẩm mô hình

| Sản phẩm | Đầu vào và ý nghĩa | Cách trình bày |
| --- | --- | --- |
| Dự báo mẫu EC tháng kế tiếp | Chỉ dùng thông tin được coi là đã có trước tháng mục tiêu; giả định độ trễ phải công bố | Kèm thời điểm phát hành, horizon, protocol, baseline, metrics và tập tháng đánh giá |
| Ước tính EC từ khí tượng cùng tháng | Dùng khí tượng thực tế của tháng cần ước tính, hiện có chuỗi 2024–2026 | Ước tính lịch sử tại giai đoạn thiếu EC; không gọi là dự báo trước một tháng hoặc số đo thực tế |
| Nghiên cứu feature 19/10 | Thử thêm nhóm biến, so sánh trên cùng tập tháng theo protocol riêng | Kết quả nghiên cứu chưa tự thay thế bộ đang phục vụ; không dùng chéo MAE giữa các tập nhãn |

Nghiên cứu mới giữ các nhãn nguồn hữu hạn, không âm; bản feature v2 cũ đã loại 117 mẫu MRC qua QA. Vì tập nhãn và protocol khác nhau, chỉ so sánh mô hình sau khi xác định cùng cohort. Cấu hình chọn bằng validation không đồng nghĩa sẵn sàng triển khai. Mô hình phức tạp không thắng baseline vẫn là kết quả cần hiển thị trung thực.

## 6. Nguồn dữ liệu và trạng thái lỗi

### Đóng gói RF_compact và ranh giới với suy luận trực tiếp

`scripts/rf_compact_artifacts.py` là bộ đóng gói dùng chung cho wrapper `pack_rf_compact_run.py` (+5 ngày) và `pack_rf_compact_lag30.py` (+35 ngày). Luồng cụ thể:

1. Đọc các dự báo nguồn trong `outputs/ec_extreme_robust_20261029/`, dựng ma trận đầu vào và kiểm tra cohort, số mẫu huấn luyện, nhãn thực tế, ngày phát hành và hai baseline. Các dự báo hồi cứu RF_compact được bảo toàn, không huấn luyện lại chỉ để đóng gói.
2. Tái dựng metadata as-of theo ngày phát hành 06 của tháng trước tháng đích; lọc nhãn theo độ trễ +5/+35 và dùng khí tượng/thủy văn `t−2`. Dấu thời gian nửa đêm +07:00 chỉ là quy ước tuần tự hóa ngày. Tuổi nguồn mới nhất và tuổi nhãn EC được lưu riêng; baseline chỉ nhận nguồn EC mà nó sử dụng.
3. Tính MAE/RMSE từ `predictions.csv` cho cùng cohort. Nhóm EC cao dùng P90 cố định của nhãn có sẵn tại lần phát hành validation đầu tiên, không dùng metric mùa khô thay thế. RF_compact được chọn trên validation 2019–2021 của giả định chính +5; +35 là đánh giá độ nhạy giữ nguyên lựa chọn.
4. Fit thuật toán RF_compact thật (100 cây, tám biến, `max_features=0.8`) để tính dự báo sau nhãn cuối. Với dữ liệu hiện tại, tháng đích là 01/2024, phát hành giả định 06/12/2023; đầu vào khí tượng/thủy văn là 11/2023 và nhãn huấn luyện được lọc riêng theo từng độ trễ. Không gán giá trị dự báo bằng hằng số.
5. Vẽ biểu đồ từ dự báo vừa đóng gói; ghi cấu hình, nguồn, giới hạn và checksum trong manifest. Hoàn tất tệp trong thư mục tạm rồi thay các tệp artifact đích. Việc thay từng tệp không phải giao dịch nguyên tử cho toàn thư mục.
6. `scripts/update_workspace_with_rf_compact.py` đọc registry, nạp artifact qua `experiments()` để kiểm tra checksum, kiểm tra hợp đồng bằng `validate_bundle`, rồi cập nhật workspace và manifest. Bước này không sửa quan trắc gốc hay chuyển các model khác thành RF_compact. Repository/service/API cung cấp kết quả cho UI.

Luồng trên khác form live tại `backend/api/multivariate.py`: form dùng RF **300 cây, năm biến** (hai biến mùa, mưa, nhiệt, gió), suy luận từ artifact đã lưu qua `domain/multivariate_ec.py`. Các metric RF_compact không phải metric của form live. Việc tính next forecast trong script đóng gói là tác vụ ngoài request web, không thay đổi ranh giới API không huấn luyện model.

Các giả định công bố không thay thế lịch sử phiên bản nguồn hoặc thời điểm công bố thật. Workspace tiếp tục đánh dấu chưa sẵn sàng triển khai; kết quả hồi cứu đã xem không thành kiểm định mù vì được đóng gói lại. Xem [quy trình nghiên cứu](diagrams/02_research_workflow.md) và [nhật ký thay đổi, tiến trình](cap_nhat_logic_va_tien_trinh_2026-11-01.md).

### Hình học dải màu trên bản đồ

`frontend/src/features/river-geometry.js` cung cấp `riverRibbon()` cho `observations-map.js`. Hàm tích lũy khoảng cách địa lý giữa các tọa độ, chia mỗi đoạn theo tỷ lệ chiều dài thay vì chỉ số đỉnh và nội suy EC tại trung điểm mỗi phần. Các đỉnh gốc nằm giữa hai điểm cắt được giữ lại để dải màu bám đường sông; đoạn có tổng chiều dài bằng 0 không sinh ribbon. Đây là thay đổi lớp hiển thị, không sửa nhãn quan trắc, thuật toán ML hoặc xác nhận liên kết thủy lực.

- Chế độ snapshot đọc dữ liệu nghiên cứu có manifest/checksum. Tệp thiếu hoặc checksum không khớp phải báo lỗi có hướng xử lý.
- Chế độ postgres đọc trạm và EC từ schema public, chọn một phiên bản RAW_EC mỗi trạm; thí nghiệm và danh mục tài liệu giữ nguồn tệp riêng. Lỗi DB phải được báo rõ, không tự chuyển sang snapshot.
- Trang lịch sử DB luôn đọc PostgreSQL; trạng thái ứng dụng chạy không đồng nghĩa DB kết nối được.
- Kết quả ước tính 2024–2026 hiện có nguồn tệp riêng; huy hiệu chế độ DB không được diễn giải thành mọi khối đều đọc DB.
- Hồ sơ tiếp nhận chưa xác minh giữ riêng, không nhập ngầm vào quan trắc hoặc nhãn huấn luyện.
- Không dữ liệu, dữ liệu cũ và dữ liệu chưa xác minh là các trạng thái riêng; không thay bằng giá trị 0 hay mẫu giả.

## 7. Chuyển đổi tương thích và bảo toàn bằng chứng

API workspace dùng tiền tố `/api/v1/workspace`; `/api/v1/research` là alias tương thích. Nhánh ước tính khí tượng dùng `/monthly-estimates`; `/future-forecast` còn là alias cho client cũ. CSV có đường dẫn `/monthly-estimates/export?station=...` dưới tiền tố workspace. API lịch sử `/api/v1/stations` vẫn riêng cho PostgreSQL.

Giữ đường dẫn/API cũ cần thiết trong giai đoạn chuyển đổi, chuyển nghiệp vụ sang module chuyên trách và cập nhật runner/build để trang chính mới được phục vụ. Chỉ đổi bố cục hoặc tên module không được làm đổi giá trị nguồn, tập thí nghiệm, đơn vị hoặc ý nghĩa cờ chất lượng.

Các thư mục chưa được Git theo dõi và script nghiên cứu mới không được coi là tệp rác chỉ vì chưa commit. Khi chủ động di chuyển artifact, cần giữ ánh xạ đường dẫn, checksum và cập nhật các tham chiếu liên quan. Các thao tác xóa do người dùng xác nhận trong đợt này được giữ nguyên. Thư mục kết quả feature 19/10 hiện không còn trong checkout; tài liệu về nghiên cứu đó là hồ sơ lịch sử, không phải artifact đã được ứng dụng nạp.

Tham khảo: [kế hoạch triển khai](implementation-plan.md), [bàn giao 16/10](handover.md), [cập nhật logic và tiến trình 01/11](cap_nhat_logic_va_tien_trinh_2026-11-01.md). Hai tài liệu từng được dẫn là `reports/20261018_kien_truc_du_lieu_va_dinh_huong_webgis.md` và `reports/20261021_huong_dan_file_va_cau_hoi_giang_vien.md` không có trong checkout hiện tại; tên được giữ để truy tìm bản lưu, không dùng làm hướng dẫn hiện hành.
