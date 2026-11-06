# Quy trình nghiên cứu và tích hợp RF_compact

Cập nhật 01/11/2026 theo mã đóng gói hiện tại. Sơ đồ mô tả luồng dữ liệu, không phải bằng chứng đã chạy thành công DB, trình duyệt hoặc một lần kiểm thử mới.

```mermaid
flowchart TD
    EC["MRC: mẫu EC tháng Mỹ Tho, đến 2023"] --> MATRIX["Ma trận tháng và dữ liệu nguồn có provenance"]
    ERA["ERA5 Mỹ Tho: mưa tháng t-2"] --> MATRIX
    HYDRO["Kratie Q và Tân Châu stage: t-2"] --> MATRIX
    SAVED["Dự báo nghiên cứu đã lưu: 36 tháng validation và 24 tháng hồi cứu"] --> CHECK
    MATRIX --> CHECK["Kiểm tra as-of: ngày, nhãn, train_n, cohort và baseline"]
    CHECK --> PRIMARY["Chọn RF_compact trên validation +5 ngày"]
    PRIMARY --> SENS["Run +35 ngày giữ lựa chọn: sensitivity"]
    CHECK --> PACK["Giữ nguyên dự báo hồi cứu RF_compact"]
    SENS --> PACK
    PACK --> METRICS["Tính MAE/RMSE và nhóm EC cao theo P90 train cố định"]
    MATRIX --> FIT["Fit RF_compact 100 cây, 8 biến theo từng độ trễ"]
    FIT --> NEXT["Next forecast lưu trữ: tháng 01/2024, issue 06/12/2023"]
    PACK --> CHART["Vẽ lại biểu đồ từ dự báo đóng gói"]
    METRICS --> ART["Artifact: CSV, JSON, chart, manifest và checksum"]
    NEXT --> ART
    CHART --> ART
    ART --> WS["Kiểm tra checksum và hợp đồng; cập nhật workspace"]
    WS --> API["Repository / service / FastAPI"]
    API --> UI["WebGIS: hồi cứu, baseline, giới hạn và truy nguồn"]
```

Ngày phát hành giả định là ngày 06 tháng trước tháng đích. Nhãn EC được coi là có sau cuối tháng +5 hoặc +35 ngày; khí tượng/thủy văn tháng `t−2` giả định có sau cuối tháng +5 ngày. Không có đầy đủ lịch sử phiên bản và ngày công bố thật để xác nhận tính khả dụng lịch sử ngoài các giả định này. Metadata phân biệt tuổi nguồn mới nhất với tuổi nhãn EC; baseline dùng nguồn EC riêng.

P90 trong artifact được tính từ các nhãn có sẵn tại lần phát hành validation đầu tiên và giữ cố định trong đánh giá. Nó khác nhóm EC ≥ 100 mS/m trong báo cáo nghiên cứu và khác nhóm mùa khô. Giai đoạn 2022–2023 đã từng được xem, không phải kiểm định mù. Next forecast tháng 01/2024 được tính thật từ mô hình, nhưng là dự báo nghiên cứu sau nhãn cuối, không phải dự báo cho hôm nay.

## Luồng suy luận trực tiếp riêng

```mermaid
flowchart LR
    TRAIN["Huấn luyện ngoài web: RF 300 cây, 5 biến"] --> MODEL["Model khí tượng đã lưu"]
    INPUT["Form: tháng đích và mưa/nhiệt/gió t-2"] --> LIVE["API multivariate: suy luận"]
    MODEL --> LIVE
    LIVE --> RESULT["UI và lớp dự báo tại trạm"]
```

Năm biến gồm hai biến mùa và ba biến khí tượng. Cập nhật thí nghiệm RF_compact không thay thế model của form này, không chuyển metric giữa hai model và không đưa huấn luyện vào request web.

## Bản đồ và cống

`riverRibbon()` chia hình học theo tỷ lệ khoảng cách địa lý tích lũy, giữ các đỉnh trung gian và nội suy EC tại trung điểm từng phần. Sửa này tránh lệch phân bố màu khi tọa độ nguồn có mật độ đỉnh không đều; đây vẫn là biểu diễn mô phỏng. Không có bước mặc nhiên biến dự báo trạm thành EC đo tại cống qua IDW, và không phát lệnh thiết bị từ dải màu. Hồ sơ cống và mô phỏng kịch bản tiếp tục cần đầu vào, giả định và bằng chứng riêng.

Nguồn DAHITI, GloFAS hoặc UHSLC có thể thuộc những nghiên cứu khác; chúng không phải đầu vào trực tiếp của RF_compact tám biến được mô tả ở đây.

Tham khảo [kiến trúc](../architecture.md), [luồng người dùng](../user-flow.md), [báo cáo RF_compact](../mo_hinh_rf_compact_chinh_thuc_2026-10-30.md) và [cập nhật logic, tiến trình 01/11/2026](../cap_nhat_logic_va_tien_trinh_2026-11-01.md).
