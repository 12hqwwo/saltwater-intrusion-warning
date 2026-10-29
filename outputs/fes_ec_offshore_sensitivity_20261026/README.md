# Thử FES nhiều điểm biển cho EC Mỹ Tho — 26/10/2026

Đã tạo mô hình đa biến **thử nghiệm riêng** gồm mưa, nhiệt độ, gió tháng t−2, chu kỳ tháng và một đặc trưng triều FES. Mô hình chính của web không bị thay đổi.

Ba điểm FES đều là điểm **biển** gần mốc Cửa Tiểu; bốn nút nội suy tại mỗi điểm có mã mask `0 = dữ liệu biển gốc`. Đây là khảo sát độ nhạy theo vị trí, không phải ba trạm triều đo hay ba cửa sông độc lập:

| Điểm | Kinh độ, vĩ độ | Cách mốc Cửa Tiểu |
| --- | --- | ---: |
| Gần cửa | 106,783333; 10,216667 | 6,34 km |
| Đông–đông nam | 106,850000; 10,183333 | 14,08 km |
| Phía nam | 106,783333; 10,050000 | 24,02 km |

Mỗi giờ FES tạo mực triều thiên văn. Mỗi ngày lấy mực cao nhất trừ thấp nhất; thử trung bình cả tháng hoặc trung bình ngày 9–15 của tháng cần dự báo. Cửa sổ giữa tháng được chọn vì 428/463 mẫu EC Mỹ Tho trong tệp nguồn được lấy ngày 15. Lịch triều này có thể tính trước tháng dự báo; không dùng EC tương lai.

## Sai số kiểm tra

MAE (sai số tuyệt đối trung bình), đơn vị mS/m; thấp hơn là tốt hơn. Mọi mô hình dùng cùng tập tháng.

| Phương án | 2019–2021, 36 tháng | 2022–2023, 24 tháng |
| --- | ---: | ---: |
| Khí tượng + tháng, không FES | **69,61** | 18,32 |
| FES gần cửa, cả tháng | 71,01 | 19,22 |
| FES gần cửa, ngày 9–15 | 69,64 | 19,74 |
| FES đông–đông nam, ngày 9–15 | 71,30 | 20,23 |
| FES phía nam, ngày 9–15 | 71,23 | 18,44 |
| FES trung bình ba điểm, ngày 9–15 | 70,59 | 20,33 |
| EC gần nhất có thể biết đến t−2 | 93,39 | **12,62** |

Biến FES gần cửa, ngày 9–15 là phương án FES tốt nhất khi chọn theo **2019–2021**. Nó vẫn không tốt hơn mô hình không FES, và giai đoạn 2022–2023 còn kém hơn. Không chọn lại phương án theo giai đoạn 2022–2023 vì giai đoạn đó đã được xem trước trong dự án, không phải kiểm tra mù mới.

## Dự báo tháng 11/2026 tại trạm Mỹ Tho

- Mô hình đa biến thử nghiệm **có FES: 16,87 mS/m**.
- Mô hình web hiện tại **không FES: 17,33 mS/m**.
- Đầu vào: mưa/nhiệt độ/gió tháng 09/2026 và biên độ FES trung bình ngày 9–15/11 là 298,13 cm tại điểm biển gần cửa.

Không có EC thực đo tháng 11/2026 để xác nhận con số nào đúng. Không dùng dự báo thử nghiệm này cho cống hoặc vận hành. EC nhãn là một mẫu trong tháng, không phải trung bình tháng; FES chưa được đối chiếu với trạm triều địa phương. Bộ FES2022b và khí tượng ERA5 hiện dùng cũng không tồn tại ở đúng dạng này tại các thời điểm dự báo lịch sử, nên đây là **so sánh hồi cứu**. Chưa có EC MRC sau 2023 để đánh giá dự báo mới.

Tệp chính: [mã thử nghiệm](../../scripts/experiment_fes_ec_multipoint.py), `fes_features_1985_2026.csv`, `paired_predictions.csv`, `experimental_model.joblib`, `forecast_2026_11.csv`, `summary.json`. Chạy lại từ thư mục gốc bằng `.venv-api/Scripts/python.exe scripts/experiment_fes_ec_multipoint.py`.

Về cơ sở vật lý, triều có thể thay đổi xâm nhập mặn qua dòng chảy, trộn nước và chu kỳ triều mạnh–yếu; kết quả phụ thuộc cửa sông và lưu lượng, không suy ra EC tại cống bằng một hệ số. Xem [Eslami và cộng sự (2021)](https://esurf.copernicus.org/articles/9/953/2021/) và [mô tả FES2022b của AVISO](https://www.aviso.altimetry.fr/index.php?id=1279).
