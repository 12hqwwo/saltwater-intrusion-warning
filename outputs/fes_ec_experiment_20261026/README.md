# Thử biến triều FES2022b cho EC Mỹ Tho (26/10/2026)

## Kết quả

Không đưa biến triều FES này vào mô hình EC đang phục vụ. Trên cùng tập tháng, sai số tuyệt đối trung bình (MAE; càng thấp càng tốt) **tăng** khi thêm triều:

| Giai đoạn | Số tháng | RF khí tượng + tháng | RF khí tượng + tháng + FES | EC gần nhất đến t−2 |
| --- | ---: | ---: | ---: | ---: |
| Kiểm tra 2019–2021 | 36 | 69,61 | 71,01 | 93,39 |
| Kiểm tra hồi cứu 2022–2023 | 24 | 18,32 | 19,22 | 12,62 |

Đơn vị sai số: mS/m. Ở giai đoạn 2022–2023, RF có FES có RMSE thấp hơn RF gốc (47,20 so với 49,31 mS/m), nhưng MAE lại cao hơn và vẫn thua cách dùng EC gần nhất (RMSE 18,91 mS/m). Không chọn mô hình theo một chỉ số thuận lợi riêng lẻ.

## Cách thử

- Từ mặt nạ FES, chọn tâm ô lưới biển gần mốc Cửa Tiểu nhất mà cả bốn nút xung quanh đều có mã **0 = dữ liệu biển gốc**: 106,783333°E; 10,216667°N, cách mốc cửa sông khoảng 6,34 km. Đây không phải tọa độ trạm/cống.
- Dùng PyFES 2026.5.2 và đủ 34 thành phần FES2022b để tính mực triều thiên văn theo từng giờ UTC, sau đó nhóm theo ngày địa phương UTC+7. Biến thử là trung bình của biên độ cao nhất trừ thấp nhất mỗi ngày trong **tháng cần dự báo**, đơn vị cm. Lịch triều thiên văn của tháng đó có thể tính trước; không lấy EC hay thời tiết tương lai làm đầu vào.
- Ghép một-một với 463 mẫu EC tháng Mỹ Tho, từ 06/1985 đến 12/2023. Cả hai mô hình dùng đúng cùng số mẫu, cùng RF/cài đặt, cùng khí tượng tháng t−2 và cùng chu kỳ tháng; chỉ mô hình thử có thêm một biến FES.
- Huấn luyện đến hết 2018 để kiểm tra 2019–2021; huấn luyện đến hết 2021 để kiểm tra 2022–2023. Đối chiếu thêm cách dùng EC gần nhất biết được đến t−2, EC cùng tháng năm trước và trung bình lịch sử của tháng.

## Giới hạn

- EC nhãn là **mẫu trong tháng**, không phải EC trung bình toàn tháng. Biến triều toàn tháng có thể làm mất mối liên hệ với giờ/ngày lấy mẫu EC.
- FES là triều biển thiên văn tính toán, không phải mực nước đo tại Mỹ Tho hay tại cống; chưa đối chiếu với trạm đo triều địa phương. Bốn ô gốc chỉ giải quyết nguồn gốc ô lưới, không chứng minh tính đại diện cho sông.
- Giai đoạn 2022–2023 đã từng được xem trong dự án, nên không gọi đây là kiểm tra mù mới. EC nguồn còn cờ chất lượng chưa xác minh. Không có EC mới sau 2023 trong tập MRC để xác nhận chất lượng dự báo hiện tại.
- Kết quả không áp dụng cho Tân Châu, các cống, bản đồ EC dọc sông hay quy tắc vận hành. Không cập nhật registry hoặc mô hình web.

## Tệp tái lập

- `scripts/experiment_fes_ec.py`: mã thực nghiệm.
- `fes_monthly_feature.csv`: 463 giá trị triều theo tháng, gồm số giờ và cờ PyFES.
- `paired_predictions.csv`: dự báo ghép cặp trên 60 tháng kiểm tra.
- `summary.json`: tọa độ, nguồn, phép đo sai số và giới hạn.

Chạy lại: `.venv-api/Scripts/python.exe scripts/experiment_fes_ec.py` từ thư mục gốc dự án, với bộ FES2022b đã tải tại `data/raw/tide/fes2022b/ocean_tide_extrapolated/`.
