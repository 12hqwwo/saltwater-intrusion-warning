# Kế hoạch thu thập dữ liệu — Mô hình dự báo xâm nhập mặn (Mỹ Tho / Tân Châu)

## 0. Dữ liệu đã có

| Biến | Trạm | Tần suất | Khoảng thời gian | Định dạng | Ghi chú |
|---|---|---|---|---|---|
| Conductivity (mS/m) | Mỹ Tho (019805) | ~Tháng (1 điểm/tháng) | 1985-06 → 2023-12 | CSV | Chưa qua kiểm định (Grade: Unverified) |
| Conductivity (mS/m) | Tân Châu (019803) | ~Tháng | 1985-05 → 2023-12 | CSV | Chưa qua kiểm định |
| Vị trí trạm | Mỹ Tho, Tân Châu | — | — | KML | Tọa độ điểm, dùng để đưa vào GIS |

**2 điểm cần lưu ý ngay:**
- Dữ liệu **kết thúc ở 2023-12** — cách hiện tại (2026) gần 3 năm. Cần tính đến việc mua/lấy bổ sung phần 2024–2026 nếu muốn test set sát với kịch bản mùa khô 2026-2027 đang quan tâm.
- Tần suất là **tháng, không phải ngày** — đây là ràng buộc lớn nhất cho toàn bộ kế hoạch bên dưới (xem mục 4).

## 1. Lưu ý về ranh giới hành chính (quan trọng cho việc chọn "1 tỉnh")

Sau đợt sáp nhập tỉnh 2025: **Tiền Giang đã sáp nhập vào Đồng Tháp** (Mỹ Tho hiện là 1 phường thuộc tỉnh Đồng Tháp mới), còn **Mỹ Thuận vẫn thuộc Vĩnh Long** (không sáp nhập). Nghĩa là về ranh giới hành chính hiện hành, Mỹ Tho và Mỹ Thuận không còn cùng 1 tỉnh. Cần quyết định:
- Dùng ranh giới **hành chính cũ (Tiền Giang)** cho mục đích nghiên cứu/so sánh lịch sử, hoặc
- Dùng ranh giới **hành chính mới (Đồng Tháp sáp nhập)** nếu báo cáo/bản đồ cần khớp với dữ liệu hành chính hiện tại.

Việc này ảnh hưởng trực tiếp đến việc bạn tải ranh giới tỉnh (shapefile/GADM) và diễn giải "vùng nghiên cứu" trong luận văn.

## 2. Dữ liệu cốt lõi cần bổ sung (bắt buộc cho model lõi)

| Biến | Trạm | Nguồn | Có API? | Chi phí | Tần suất gốc | Ghi chú khớp thời gian |
|---|---|---|---|---|---|---|
| Lưu lượng (Discharge, m³/s) | Tân Châu | MRC Data Portal (portal.mrcmekong.org/time-series) — cùng giao diện bạn đã mua Conductivity, chỉ đổi filter Parameter → Discharge | Không có REST API công khai, portal cho search/download thủ công | Trả phí (như conductivity) | Ngày | Kiểm tra date range hiện tại trên portal — đừng dựa vào tài liệu archive cũ (chỉ ghi đến 2003-04) |
| Mực nước | Tân Châu | ffw.mrcmekong.org (station code TCH) | Không có API/JSON công khai, chỉ đọc được qua HTML; **robots.txt của trang chặn truy cập tự động** — cần scrape thủ công/kiểm tra ToS trước khi viết script | Miễn phí | Ngày (cập nhật lúc 07:00) | Daily → cần downsample nếu ghép với conductivity tháng |
| Mực nước | Mỹ Tho | Chưa có nguồn số liệu thô đáng tin cậy dạng tải trực tiếp — VNMC (vnmc.gov.vn) công bố bản tin nửa tháng có nhắc đến Mỹ Thuận là chính, ít số liệu Mỹ Tho | Không | — | Bản tin định kỳ, không phải chuỗi số | Cần xác nhận thêm — có thể phải quy đổi từ trạm lân cận hoặc liên hệ Đài KTTV Nam Bộ |
| Mưa | Khu vực Mỹ Tho/Tân Châu | Open-Meteo Archive API | Có, REST/JSON | Miễn phí | Ngày | Daily → downsample nếu cần khớp tháng |

## 3. Dữ liệu nâng cao (mở rộng, không bắt buộc để model chạy được)

| Biến | Nguồn | Có API? | Chi phí | Ghi chú |
|---|---|---|---|---|
| Lịch vận hành cống (Bảo Định, Xuân Hòa, Rạch Chợ, Nguyễn Tấn Thành...) | Công ty TNHH MTV Khai thác CTTL Tiền Giang / Chi cục Thủy lợi | Không | Cần liên hệ trực tiếp, có thể phải xin phép/công văn | Nâng cao độ chính xác đáng kể ở vùng có kiểm soát, nhưng tốn thời gian xin dữ liệu |
| DEM mặt đất | SRTM 30m hoặc ALOS PALSAR 12.5m (qua OpenTopography) | Có API | Miễn phí | Dữ liệu tĩnh (không phải time-series) |
| Bathymetry (mặt cắt đáy sông) | Viện Quy hoạch Thủy lợi Miền Nam / khảo sát thực địa | Không | Thường phải hợp tác nghiên cứu hoặc trả phí | Chỉ cần nếu làm mô phỏng không gian 1D/2D, không cần cho time-series 1 điểm |
| Lịch xả đập thượng nguồn | Mekong Dam Monitor (Stimson Center) | Có dataset tải về | Miễn phí | Dữ liệu tuần (weekly), ước tính vệ tinh — dùng để giải thích dị thường, không phải input chính |

## 4. Vấn đề khớp thời gian (temporal alignment)

Ràng buộc gốc: **conductivity hiện có là tháng** (~ngày 14-15 mỗi tháng), còn discharge/mực nước/mưa các nguồn trên phần lớn là **ngày**.

Hai hướng xử lý:
- **(a) Downsample tất cả về tháng** để khớp với conductivity đang có — đơn giản, triển khai nhanh, nhưng mất hết biến động ngắn hạn (theo triều, theo đợt xả đập) — bất lợi cho bài toán cảnh báo sớm.
- **(b) Tìm/mua thêm nguồn mặn tần suất ngày** làm chuỗi chính, dùng chuỗi tháng hiện có chỉ để mở rộng lịch sử dài hạn (1985-2003) — cần xác nhận MRC portal có option tần suất ngày cho conductivity tại 2 trạm này hay không.

Ngoài ra: **gap 2024–2026** giữa dữ liệu hiện có và thời điểm hiện tại cần được lấp — nếu không, không có test set nào phản ánh đúng bối cảnh mùa khô 2026-2027 đang phân tích.

## 5. Về việc dữ liệu "đặc thù, khó kiếm" — có ổn không?

Đây là tình trạng phổ biến với các đề tài tài nguyên nước ở ĐBSCL ở quy mô luận văn — không phải vấn đề của riêng bạn. Vài cách xử lý được chấp nhận trong nghiên cứu thực tế:

- Chọn tần suất **thấp nhất chung** làm baseline chính thức của model, nêu rõ giới hạn này trong phần "Data Limitations" của báo cáo thay vì cố ép dữ liệu đạt tần suất ngày bằng mọi giá.
- Với khoảng trống (missing), ưu tiên mô hình có khả năng xử lý missing (ví dụ LSTM có masking) hoặc nội suy có căn cứ vật lý, tránh nội suy tuyến tính ngây thơ cho biến phi tuyến như độ mặn.
- Ghi lại **data provenance** (nguồn, ngày tải, phiên bản) cho từng file — hội đồng chấm luận văn thường đánh giá cao việc minh bạch giới hạn dữ liệu hơn là dữ liệu "đẹp" nhưng không rõ nguồn gốc.

## 6. Đề xuất kiến trúc lưu trữ dữ liệu

```
data/
├── raw/                        # bản gốc tải về, KHÔNG chỉnh sửa
│   ├── mrc_conductivity/
│   ├── mrc_discharge/
│   ├── openmeteo_rainfall/
│   ├── waterlevel_scrape/
│   └── spatial/                # KML, OSM, DEM gốc
├── interim/                    # đã làm sạch: chuẩn tên cột, đơn vị, timezone
├── processed/                  # đã resample về tần suất chung + merge theo station-date
│   └── master_timeseries.parquet
├── external/                   # dữ liệu tĩnh: ranh giới hành chính, DEM, vị trí cống
└── metadata/
    └── data_dictionary.md      # nguồn, tần suất gốc, đơn vị, ngày tải, giấy phép sử dụng — mỗi biến 1 dòng
```

Gợi ý công cụ: dùng **Parquet + DuckDB** cho tầng `processed/` thay vì nhiều CSV rời rạc — nhẹ, không cần server, query SQL trực tiếp trên local, dễ merge nhiều nguồn theo station + timestamp. Tầng `raw/` giữ nguyên định dạng gốc (CSV/KML) để truy vết lại khi cần.

---
*Các ô còn trống hoặc chưa xác nhận (mực nước Mỹ Tho, tần suất ngày cho conductivity, dữ liệu vận hành cống) cần bạn tự kiểm tra/liên hệ nguồn trước khi đưa vào pipeline chính thức.*
