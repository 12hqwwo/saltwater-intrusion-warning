# Kiểm tra cửa sổ triều và phân vị cây RF cho EC Mỹ Tho

Ngày 08/11/2026. Mẫu EC **692 mS/m ngày 15/03/2020 được giữ là giá trị thực đo đúng** theo xác nhận của chủ dự án. Phép thử dưới đây tìm cách giải thích và dự báo mẫu đó, không sửa nhãn.

## Dữ liệu và cách tính

- Tệp MRC gốc `data/raw/ec/mrc/Conductivity.Water Quality@VN_019805_[My Tho].csv` có 463 mẫu Mỹ Tho. Có 459/463 mẫu ghi ngày 13–17; 428/463 ghi ngày 15. Bốn ngoại lệ là 26/06/1985, 19/09/1985, 09/02/1991 và 01/12/2001. Cả 463 dấu thời gian đều ghi `00:00`, nên không suy ra giờ lấy mẫu hay pha triều thật từ đó. Khung 07:00–16:00 chỉ là **giả định thí nghiệm**, chưa phải lịch lấy mẫu MRC đã chứng minh.
- Dùng FES2022b tại điểm `south` (106,783333°E; 10,05°N), giờ địa phương UTC+7. Tính trước các đặc trưng lịch cố định: cực đại và trung bình giờ 07–16 của ngày 13–17, cực đại ngày 01–15, và trung bình biên độ ngày 05–12. Không dùng ngày lấy mẫu EC thực tế làm đầu vào dự báo. Tính lại 463 tháng 1985–2023 và khớp giá trị biên độ ngày 13–17 đã lưu trước đó đến `1e-7` cm.
- Chấm theo giao thức **khóa EC Mỹ Tho**: huấn luyện RF 300 cây một lần trước từng kỳ mất tín hiệu; dùng khí tượng, lưu lượng Kratie và mực nước Tân Châu tháng `t−2`. Mỗi ứng viên thêm đúng một biến FES. Dự báo đối chứng khớp tệp `outputs/frozen_ec_remedies_20261108/predictions.csv` đến `1e-8` mS/m. Giả định độ trễ EC +5 hoặc +35 ngày. FES2022b là atlas ra đời sau các ngày phát hành lịch sử, nên đây là **hindcast nghiên cứu**, không phải dự báo phát hành thật lúc đó.

## Tháng 03/2020

Mô hình khóa tại lần phát hành đầu của kỳ 2019–2021 dùng **402 mẫu đến 11/2018**, gồm cả mẫu 841 mS/m năm 1998. Đây là bản 300 cây cùng cấu hình với mô hình chính, nhưng được huấn luyện trước 2020 để tránh dùng nhãn tương lai; không lấy artifact đang phục vụ vốn đã học đến 2023 để chấm lại 2020. Tại 03/2020, dự báo trung bình của 300 cây là **213,67 mS/m**; phân vị cây 90% là **360,97**, phân vị 95% là **425,92**, và cây cao nhất là **691,50 mS/m**. **Không cây nào đạt 692 mS/m**; chỉ 2 cây dự báo từ 600 mS/m trở lên. Do đó không thể gọi phân vị 90% của cây là “trần rủi ro” bao phủ đỉnh 692.

FES tại điểm `south` cho trung bình biên độ ngày **299,40 cm** trong 05–12/03 và **264,56 cm** trong 13–17/03; riêng 15/03 là **272,38 cm**. Cửa sổ trước cao hơn khoảng **13,2%** so với cửa sổ sau (tính theo cửa sổ sau). Điều này ủng hộ việc *thử* giả thuyết tác động tích lũy trước ngày lấy mẫu, nhưng không xác định giờ lấy mẫu, EC theo giờ, vận tốc truyền mặn hoặc nguyên nhân của giá trị 692. Mức triều FES ngoài biển cũng không phải mực nước hay độ mặn đo tại Mỹ Tho.

## Sai số trên các kỳ đã kiểm tra

MAE, mS/m; số nhỏ hơn là tốt hơn. Bảng dưới dùng giả định EC +5 ngày. Kết quả +35 ngày và RMSE có trong `outputs/ec_tide_windows_20261108/metrics.csv`.

| Mô hình/đặc trưng thêm | 2019–2021 (36 tháng) | 2021–2023 (36 tháng) | 2022–2023 (24 tháng) | Dự báo 03/2020 |
| --- | ---: | ---: | ---: | ---: |
| RF thủy văn chính, không FES | **57,81** | 16,57 | 12,19 | 213,67 |
| Cực đại ban ngày 13–17 | 57,95 | 16,44 | 12,26 | 213,00 |
| Trung bình ban ngày 13–17 | 57,93 | **15,59** | **11,73** | 229,86 |
| Cực đại nửa đầu tháng | 57,94 | 16,66 | 12,20 | 212,80 |
| Biên độ ngày 05–12 | 58,64 | 16,71 | 12,61 | 211,26 |

Trung bình triều ban ngày giúp hai kỳ gần đây nhưng làm MAE kỳ 2019–2021 tăng nhẹ và vẫn dự báo hụt mẫu 692 khoảng 462 mS/m. Nhóm 6 tháng EC ≥100 mS/m ở kỳ 2019–2021 có MAE **285,92** với RF gốc và **290,05** khi thêm trung bình ban ngày. Các kỳ đã được xem trước, không phải kiểm định mù.

Phân vị 90% của các cây chỉ bao phủ **22/36 tháng (61,1%)** trong 2019–2021, và **1/6 tháng EC ≥100**. Nó không phải phân vị dự báo đã hiệu chuẩn. Việc đưa đường p90/p95 lên WebGIS như một khoảng tin cậy hoặc cảnh báo cực đại sẽ gây hiểu sai.

## Quyết định

**Giữ mô hình thủy văn Kratie + Tân Châu đang phục vụ.** Chưa thêm biến FES ban ngày/nửa đầu tháng hoặc đường phân vị cây vào giao diện. Có tín hiệu nhỏ ở kỳ gần đây để nghiên cứu tiếp, nhưng chưa cải thiện ổn định trên kỳ 2019–2021 và không giải quyết đỉnh 03/2020. Không coi “mẫu lấy đúng đỉnh triều”, “nước mặn tích tụ 5–10 ngày” hay “gió chướng gây đỉnh 692” là kết luận đã được chứng minh từ những tệp này.

Mã tái lập: `scripts/audit_ec_tide_windows_20261108.py`. Đầu ra: `outputs/ec_tide_windows_20261108/` gồm bảng đặc trưng, dự báo từng tháng, chỉ số và `audit.json` ghi mã băm nguồn.
