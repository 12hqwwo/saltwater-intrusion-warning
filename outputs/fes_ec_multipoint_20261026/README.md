# Thử nhiều điểm triều FES cho dự báo EC Mỹ Tho — 26/10/2026

## Kết luận

Đã kết hợp triều FES vào **một mô hình đa biến thử nghiệm riêng** và tạo dự báo EC tháng 11/2026. Không thay mô hình đang phục vụ: chưa có phương án triều nào giảm sai số MAE so với mô hình không có triều trên cả hai giai đoạn đánh giá. Triều có ảnh hưởng vật lý đến xâm nhập mặn, nhưng các đặc trưng biển–tháng thử ở đây chưa chứng minh được lợi ích dự báo cho mẫu EC Mỹ Tho.

## Điểm và biến

Ba điểm đều ở ngoài biển gần Cửa Tiểu, có bốn nút lưới xung quanh mang mã mặt nạ `0 = dữ liệu biển gốc`; đây **không phải ba trạm triều đo thực tế** và cũng không đại diện ba cửa sông độc lập.

| Điểm | Kinh độ | Vĩ độ | Cách mốc Cửa Tiểu |
| --- | ---: | ---: | ---: |
| Gần cửa | 106,783333 | 10,216667 | 6,34 km |
| Đông–đông nam | 106,850000 | 10,183333 | 14,08 km |
| Phía nam | 106,783333 | 10,050000 | 24,02 km |

Từ mực triều FES tính theo giờ, mỗi ngày lấy mực cao nhất trừ thấp nhất. Thử năm lựa chọn thêm vào mô hình khí tượng + chu kỳ tháng: biên độ trung bình cả tháng tại điểm gần cửa; biên độ trung bình ngày 9–15 tại mỗi điểm; hoặc trung bình ngày 9–15 của cả ba điểm. Cửa sổ ngày 9–15 được định trước vì 428/463 mẫu EC Mỹ Tho trong tệp nguồn được lấy ngày 15. Lịch triều thiên văn có thể tính trước tháng cần dự báo, nên không phải lấy EC tương lai làm đầu vào.

## So sánh cùng tập tháng

MAE là sai số tuyệt đối trung bình; đơn vị mS/m; thấp hơn là tốt hơn.

| Phương án | 2019–2021 (36 tháng) | 2022–2023 (24 tháng) |
| --- | ---: | ---: |
| Khí tượng + chu kỳ tháng, không FES | **69,61** | 18,32 |
| FES điểm gần cửa, cả tháng | 71,01 | 19,22 |
| FES điểm gần cửa, ngày 9–15 | 69,64 | 19,74 |
| FES điểm đông–đông nam, ngày 9–15 | 71,30 | 20,23 |
| FES điểm phía nam, ngày 9–15 | 71,23 | 18,44 |
| FES trung bình ba điểm, ngày 9–15 | 70,59 | 20,33 |
| EC gần nhất biết được đến t−2 | 93,39 | **12,62** |

Phương án **điểm gần cửa, ngày 9–15** được chọn chỉ trong các biến FES theo sai số 2019–2021; nó vẫn không thắng phương án không FES (69,64 so với 69,61). Giai đoạn 2022–2023 cho thấy nó kém rõ hơn (19,74 so với 18,32). Giai đoạn này đã được xem trước trong dự án, không phải kiểm tra mù mới. Không dùng các con số của nó để chọn lại điểm/biến.

## Dự báo thử nghiệm tháng 11/2026

- Mô hình đa biến có FES: **16,87 mS/m** tại **trạm Mỹ Tho**.
- Mô hình web hiện tại, không FES: **17,33 mS/m** tại cùng trạm và tháng.
- Đầu vào: mưa, nhiệt độ, gió tháng 09/2026; chu kỳ tháng 11; biên độ triều FES trung bình ngày 9–15/11 là **298,13 cm** tại điểm biển gần cửa.

Đây là hai **ước tính chưa có EC đo tháng 11/2026 để xác minh**. Chênh lệch 0,46 mS/m giữa hai mô hình không chứng minh FES tốt hơn. Không áp dụng kết quả cho cống hoặc đóng/mở cống.

## Tái lập và giới hạn

- `scripts/experiment_fes_ec_multipoint.py`: chọn điểm, tạo đặc trưng, đánh giá và dự báo.
- `fes_features_1985_2026.csv`: FES theo tháng đến 11/2026, số giờ và cờ nội suy.
- `paired_predictions.csv`: dự báo từng tháng trên hai giai đoạn đánh giá.
- `experimental_model.joblib`: mô hình chỉ dành cho nghiên cứu, không đăng ký trong web.
- `forecast_2026_11.csv` và `summary.json`: dự báo và nguồn/phương pháp chi tiết.

Chạy lại từ thư mục gốc: `.venv-api/Scripts/python.exe scripts/experiment_fes_ec_multipoint.py` với 34 tệp FES2022b và mask đã tải.

FES là triều **biển thiên văn dự tính**, chưa được đối chiếu trạm đo ven bờ/ở sông. EC đích là một mẫu trong tháng, không phải EC trung bình tháng. FES2022b và kho ERA5 hiện dùng là dữ liệu được dựng/cập nhật sau một số thời điểm kiểm tra lịch sử, nên đây là so sánh hồi cứu, không phải bằng chứng vận hành thời gian thực. Hiện chưa có EC MRC sau 2023 để kiểm định dự báo mới. Không suy ra rằng triều không ảnh hưởng xâm nhập mặn; chỉ kết luận các đặc trưng FES đã thử chưa cải thiện mô hình này.

Nghiên cứu liên quan: Eslami và cộng sự, *Dynamics of salt intrusion in the Mekong Delta* (2021), https://esurf.copernicus.org/articles/9/953/2021/; thông tin FES2022b của AVISO, https://www.aviso.altimetry.fr/index.php?id=1279.
