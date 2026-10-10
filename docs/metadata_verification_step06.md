# Xác minh metadata — ngày 04/10/2026

**Bổ sung 08/10/2026:** đã tải lại trực tiếp các chuỗi MRC, ghép được 500 cặp EC–nhiệt độ nước trùng timestamp và tải khí tượng ERA5 kèm request/response đầy đủ. EC tải lại khớp các giá trị master, nhưng cơ sở bù nhiệt vẫn `UNKNOWN`; cặp timestamp chưa chứng minh cùng mẫu. Phần dưới lưu kết quả của snapshot ngày 04/10. Bằng chứng từng lần tải nằm trong `data/external/download_runs/`; không cập nhật ngược metadata nguồn cũ bằng suy đoán.

Đã kiểm tra bản dữ liệu hiện có và tài liệu nguồn. Kết luận là **xác nhận được một phần, còn thiếu bằng chứng về phương pháp đo**. Không nâng chất lượng dữ liệu lên VALIDATED và không tự gán EC đã bù nhiệt về 25°C.

## 1. Kết quả đối chiếu trên file

| Nội dung | Mỹ Tho | Tân Châu | Kết luận |
|---|---:|---:|---|
| Số quan trắc EC gốc | 463 | 464 | Khớp snapshot đã kiểm tra |
| Tháng EC đầu tiên | 06/1985 | 05/1985 | Giữ tháng theo thời gian địa phương |
| Quan trắc EC cuối cùng | 15/12/2023 | 15/12/2023 | Không có nhãn EC từ năm 2024 trong snapshot này |
| Đơn vị EC | mS/m | mS/m | Xác nhận từ CSV/README |
| O/E | Tất cả O | Tất cả O | Quan trắc được nguồn đánh dấu O |
| Chất lượng | Unverified data | Unverified data | Chưa được kiểm định; không đồng nghĩa dữ liệu sai |
| Approval Level | Raw - Not Yet Reviewed | Raw - Not Yet Reviewed | Giữ nguyên |
| Múi giờ xuất dữ liệu | UTC+07:00 | UTC+07:00 | Xác nhận từ README và timestamp |
| Cơ sở nhiệt độ của EC | UNKNOWN | UNKNOWN | Không tìm được xác nhận riêng cho chuỗi/trạm/thời kỳ |
| Số dòng khí tượng ngày | 15.218 | 15.218 | Không trùng ngày |
| Khoảng khí tượng | 01/01/1985–31/08/2026 | 01/01/1985–31/08/2026 | Đủ ngày trong cả 500 tháng |
| Cột mực nước có giá trị | 217 tháng | 108 tháng | Nguồn đại diện DAHITI, chưa xác nhận cùng vị trí/cao độ |
| Cột GloFAS có giá trị | 0 tháng | 469 tháng | Chưa xác nhận ô sông và cách trích xuất phù hợp |

Đã tính lại tổng mưa, trung bình nhiệt độ không khí và tổng ET₀ từ CSV ngày. Cả hai trạm khớp `master_timeseries.csv` đến sai số số thực: chênh tuyệt đối lớn nhất lần lượt khoảng `5.68e-14`, `3.55e-15`, `2.84e-14`. Không có giá trị thiếu ở ba cột ngày được chọn. Điều này xác nhận phép tổng hợp, chưa xác nhận mọi giả định khoa học của dữ liệu nguồn.

Đã kiểm tra shared strings và document properties của cả hai XLSX MRC; không thấy tuyên bố bù nhiệt rõ ràng. Việc không tìm thấy trong những phần đã xem không chứng minh rằng MRC không có hồ sơ này ở nơi khác.

Mã SHA-256 của master và hai CSV khí tượng vẫn khớp `forecast_sources.json`. Hai CSV MRC vẫn khớp `ec_conversion_profiles.json`. Không sửa dữ liệu gốc.

Kết quả máy đọc được nằm ở `runs/metadata_verification/step06_20261004/metadata_review.json` trong bản làm việc này.

## 2. Điểm cần phân biệt

**EC theo tháng là giá trị tổng hợp từ những mẫu đã thu trong tháng.** Nó không phải chuỗi đo liên tục và không bảo đảm phản ánh đỉnh mặn hoặc thời điểm mặn nhất trong ngày. Mô hình hiện dự báo đại lượng EC này, chưa dự báo ranh mặn trên toàn bản đồ, diện tích ngập hay mức mở cửa cống.

**Nhiệt độ Open-Meteo là nhiệt độ không khí.** Không dùng cột `temperature_mean` làm nhiệt độ nước trong công thức EC → độ mặn. ET₀ là bốc thoát hơi tham chiếu; không phải phép đo bốc hơi trực tiếp của sông [2].

Tọa độ yêu cầu khí tượng Mỹ Tho là `(106.36, 10.36)`, Tân Châu là `(105.234, 10.804)` theo thứ tự kinh độ, vĩ độ. Tọa độ trạm MRC tương ứng là `(106.3529997, 10.35912163)` và `(105.2480164, 10.80062008)`. Không coi dữ liệu khí tượng dạng lưới là cảm biến đặt đúng tại trạm/cống. Bản phản hồi API có metadata ô lưới, đơn vị, múi giờ và mô hình chưa được lưu cùng CSV cũ.

Trong `pipelines/legacy/data_processing/process_data.py`, GloFAS đang được lấy trung bình theo các chiều không gian rồi tổng hợp tháng. Cách này chưa chứng minh đại diện cho lưu lượng tại trạm. DAHITI cũng cần xác minh vị trí, loại cao độ và mốc chuẩn. Vì vậy hai biến này chỉ được thử khi bật `--include-hydro-proxies`; không tham gia chọn nhánh suy luận chính.

`windspeed_mean` trong bộ xử lý cũ là trung bình của tốc độ gió cực đại từng ngày. Nó chưa được dùng trong mô hình mới, do ý nghĩa thống kê và đơn vị nguồn cần làm rõ.

## 3. Khả dụng theo thời gian và giới hạn của backtest

| Biến | Giả định mặc định trong thí nghiệm | Bằng chứng còn thiếu |
|---|---|---|
| EC của tháng | Cuối tháng + 0 ngày | Ngày công bố thật và lịch sử QA từng mẫu |
| Ba biến khí tượng | Cuối tháng + 5 ngày | Mô hình API gốc, phiên bản phát hành từng thời điểm |
| DAHITI/GloFAS thử nghiệm | Cuối tháng + 30 ngày | Lịch phát hành thực tế; 30 ngày chỉ là giả định |

Tài liệu Open-Meteo nêu ERA5/ERA5-Land có độ trễ 5 ngày [2]. Điều đó **không xác nhận** hai CSV cũ đã chọn đúng các mô hình này hoặc có đúng lịch sử phát hành đó. Bản hiện tại là backtest trên snapshot tái phân tích với độ trễ khai báo; chưa phải tái hiện hoàn toàn dữ liệu người vận hành đã có trong quá khứ.

Script hỗ trợ cột `<tên_biến>__available_at` nếu có thời điểm khả dụng thật. Giá trị tổng hợp tháng không được khai báo khả dụng trước cuối tháng. Timestamp thực tế giúp kiểm soát việc dùng dữ liệu, nhưng vẫn cần lưu từng phiên bản nguồn để kiểm toán dữ liệu đã bị sửa lại sau này.

## 4. EC → độ mặn

Tài liệu MRC nêu đơn vị EC mS/m và phương pháp phân tích đề xuất, nhưng chưa đủ để gán phương pháp đo/bù nhiệt cho từng quan trắc trong chuỗi 1985–2023 [1]. Cụm `Corrected signal` trong README cũng không xác nhận bù nhiệt.

GSW tính Practical Salinity `SP` từ độ dẫn điện, nhiệt độ nước và áp suất. Đầu vào độ dẫn điện là mS/cm; `SP` là đại lượng không thứ nguyên [3]. Đổi đơn vị mS/m sang mS/cm bằng chia 100 không giải quyết được vấn đề cơ sở nhiệt độ. Không đồng nhất `SP` với g/L.

`run_salinity.py` và hai profile vẫn giữ nguyên cơ chế chặn khi thiếu metadata. Việc bổ sung ghi chú nghiên cứu vào profile không mở khóa chuyển đổi chính thức. Kết quả kịch bản giả định nhiệt độ ở bước trước vẫn là kịch bản giả định.

Cần hồ sơ riêng cho từng trạm và thời kỳ: EC tại nhiệt độ nước hay chuẩn hóa; nhiệt độ tham chiếu; công thức bù nhiệt; thiết bị và hiệu chuẩn; nhiệt độ nước cùng mẫu; độ sâu/áp suất; thời điểm thay thiết bị/phương pháp. Sau đó cần cặp mẫu EC–độ mặn độc lập tại vùng nghiên cứu để đánh giá sai số và miền áp dụng. Chia profile theo thời kỳ nếu phương pháp thay đổi.

Nếu quy trình cống đã quy định ngưỡng **EC25** có kiểm chứng tại địa phương, có thể so sánh EC25 trực tiếp với ngưỡng EC25. Không bắt buộc chuyển qua độ mặn chỉ để tạo một con số khác. Script cống hỗ trợ lựa chọn này; dữ liệu EC hiện tại chưa đáp ứng cơ sở EC25.

## 5. Nguồn đối chiếu

Các kết luận về file riêng của dự án dựa trên kiểm tra file. Tài liệu dưới đây cung cấp định nghĩa/phương pháp; không được dùng để thay thế metadata còn thiếu của từng chuỗi.

1. [MRC — Technical Guidelines on the Implementation of the Procedures for Water Quality](https://www.mrcmekong.org/wp-content/uploads/2024/08/TGWQ-1.pdf), Table 1.4.2, trang in số 4, trang PDF 11; phần truy xuất hồ sơ lấy mẫu/phân tích.
2. [Open-Meteo — Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), Data Sources, API Documentation, Daily/Hourly Variable Definition. Truy cập 04/10/2026.
3. [TEOS-10/GSW — gsw_SP_from_C](https://www.teos-10.org/pubs/gsw/html/gsw_SP_from_C.html), định nghĩa đầu vào/đầu ra và phạm vi thuật toán.
4. [MRC Water Quality Portal](https://portal.mrcmekong.org/monitoring/water-quality): trang công khai cần JavaScript trong lần truy xuất; chưa lấy được xác nhận bù nhiệt riêng cho hai chuỗi.

Việc xác minh metadata của bước này đã có kết quả và danh sách thiếu cụ thể. Trạng thái khoa học còn mở sẽ chỉ được cập nhật khi có bằng chứng nguồn phù hợp.
