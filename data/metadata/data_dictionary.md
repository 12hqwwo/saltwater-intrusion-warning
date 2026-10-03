# Từ điển dữ liệu hiện có

Cập nhật theo gói dự án ngày 02/10/2026. File, database và xác minh chuyên môn là các phạm vi khác nhau.

## Trạm và tọa độ EC

| Mã trạm | Tên | Kinh độ | Vĩ độ | Nguồn | Trạng thái |
|---|---|---:|---:|---|---|
| MRC_VN_019803 | Tân Châu | 105.2480164 | 10.80062008 | KML VN_019803 trong data/raw/spatial/ | REPORTED |
| MRC_VN_019805 | Mỹ Tho | 106.3529997 | 10.35912163 | KML VN_019805 trong data/raw/spatial/ | REPORTED |

Không giả định điểm khí tượng, ô lưới GloFAS hoặc điểm DAHITI trùng trạm EC. Tọa độ làm tròn ở tài liệu cũ không được dùng thay KML cho lớp trạm.

## Các cột master_timeseries.csv

| Cột | Ý nghĩa theo mã xử lý hiện có | Đơn vị và giới hạn |
|---|---|---|
| station | Khóa MyTho/TanChau để gộp dữ liệu | Không chứng minh các nguồn đo cùng vị trí |
| month_start | Ngày đầu tháng làm khóa | Không phải thời điểm dữ liệu sẵn có/phát hành dự báo |
| conductivity_mS_per_m | Trung bình EC trong tháng | mS/m; DB dùng conductivity_ms_per_m; không tự đổi thành ppt |
| precipitation_sum | Tổng trường lượng mưa ngày trong tháng | Đối chiếu đơn vị với metadata nguồn tải |
| temperature_mean | Trung bình nhiệt độ trung bình ngày | Đối chiếu metadata nguồn tải |
| temperature_max | Lớn nhất của nhiệt độ cao nhất ngày | Đối chiếu metadata nguồn tải |
| temperature_min | Nhỏ nhất của nhiệt độ thấp nhất ngày | Đối chiếu metadata nguồn tải |
| evapotranspiration_sum | Tổng ET0 ngày | Đối chiếu metadata nguồn tải |
| windspeed_mean | Trung bình windspeed_10m_max hàng ngày | Trung bình cực đại ngày; không mặc nhiên là trung bình giờ; đơn vị chưa xác minh |
| humidity_mean | Trung bình độ ẩm tương đối ngày | Bộ kiểm tra giới hạn 0–100; giữ metadata nguồn |
| shortwave_rad_sum | Tổng trường bức xạ sóng ngắn ngày | Đối chiếu metadata nguồn tải |
| water_level_m | Trung bình tháng DAHITI | m theo tên trường; mốc cao độ chưa xác minh |
| glofas_discharge_m3s | GloFAS qua pipeline hiện có | m³/s theo tên trường; cách chọn ô lưới, thời gian và gộp file cần rà soát |

Các phép tổng hợp đọc từ data_processing/process_data.py. Đợt này chỉ đối chiếu lại EC với raw; chưa chứng nhận toàn bộ biến ngoại sinh.

## Độ phủ

| Khu vực | Tháng lịch | Có EC | Có DAHITI | Có GloFAS |
|---|---:|---:|---:|---:|
| Mỹ Tho | 500 | 463 | 217 | 0 |
| Tân Châu | 500 | 464 | 108 | 469 |

Lịch 1985-01–2026-08. EC Mỹ Tho bắt đầu 1985-06; Tân Châu bắt đầu 1985-05; cả hai kết thúc tháng 12/2023, với ngày raw cuối 15/12/2023. Các tháng sau có nguồn khác hoặc dữ liệu thiếu, không phải EC mới.

## Cờ dữ liệu

- O: nguồn ghi quan trắc; E: nguồn ghi ước tính. Hai raw hiện tại đều toàn bộ O.
- Grade = Unverified data và Approval Level = Raw - Not Yet Reviewed giữ từ nguồn. O không đồng nghĩa đã kiểm định.
- quality_flag là cờ nội bộ DB, tách biệt O/E và cờ nguồn. ETL không tự nâng VALIDATED.
- REPORTED: có tọa độ kèm nguồn, không đồng nghĩa xác minh thực địa.
- EC lớn không tự động là lỗi cảm biến. Không lọc/sửa chỉ dựa vào ngưỡng 80 mS/m ở tài liệu cũ khi chưa có căn cứ kiểm định.

## Mẫu cống

data/irrigation_gates_template.csv hiện chỉ có header. longitude/latitude là kinh độ/vĩ độ; srid là hệ tọa độ; source_reference phải chỉ rõ tài liệu và vị trí trích dẫn. source_url có thể trống nếu tài liệu cục bộ được lưu kèm. VERIFIED cần căn cứ xác minh được ghi nhận.

Đây là mẫu thu thập, chưa phải file COPY trực tiếp: DB lưu geom và source_id; irrigation_gate chưa có cột location_status. Bước nạp phải bổ sung ánh xạ/kiểm tra nguồn theo schema. Không điền tọa độ ước chừng hoặc dòng minh họa vào danh mục thật.
