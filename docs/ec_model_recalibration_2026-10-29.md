# Hiệu chỉnh EC theo ngày phát hành và kiểm tra tín hiệu thượng nguồn

Ngày 29/10/2026. Mục tiêu là **giá trị EC của một mẫu trong tháng**, mS/m, tại Tân Châu và Mỹ Tho. Nguồn EC cuối cùng là 12/2023. Toàn bộ 927 nhãn MRC được giữ nguyên. Phép chấm phát hành ngày 06 tháng trước; EC được xem là có sau cuối tháng +5 ngày (chính) hoặc +35 ngày (độ nhạy); ERA5 tháng t−2 được xem là có sau cuối tháng +5 ngày. Đây là giả định vì không có lịch công bố lịch sử. Tập 2022–2023 đã được xem trước trong dự án, nên chỉ là kiểm tra hồi cứu.

## 1. Công việc đã thực hiện

`scripts/experiment_ec_upstream_asof.py` tạo đặc trưng EC quá khứ (mẫu mới nhất/áp chót, tuổi mẫu, cùng tháng năm trước, trung bình 3/12 tháng đã công bố), mùa vụ, mưa/nhiệt độ/gió ERA5 của tháng t−2, độ ẩm đất và hướng gió ERA5 cùng tháng nguồn. Với Mỹ Tho có nhánh thêm đúng các đặc trưng **EC Tân Châu đã công bố trước ngày phát hành**. Mỗi dự báo huấn luyện lại từ nhãn đã biết lúc đó. So RF 100 cây, Ridge, RF cũ và ba baseline trên cùng tháng. Validation 2019–2021, kiểm tra hồi cứu 2022–2023.

`scripts/select_ec_asof_blends.py` kiểm tra các trọng số cố định 0/0,25/0,5/0,75/1, chọn bằng MAE **chỉ trên 2019–2021**, rồi ghi điểm 2022–2023. Mỹ Tho phối RF cũ với Persistence; Tân Châu phối RF có EC quá khứ với Seasonal Naive. Đây là thử nghiệm phát triển, không phải test mù, do 2022–2023 đã từng được xem.

## 2. Kết quả chính (MAE mS/m)

| Trạm / giả định EC | Phương án | 2019–2021 | 2022–2023 |
| --- | --- | ---: | ---: |
| Mỹ Tho, +5 ngày | RF cũ | 71,56 | 18,63 |
| Mỹ Tho, +5 ngày | 0,75 RF cũ + 0,25 Persistence, chọn trên validation | **70,46** | **15,83** |
| Mỹ Tho, +5 ngày | Persistence riêng | 93,39 | **12,62** |
| Mỹ Tho, +35 ngày | RF cũ / trọng số validation chọn | 71,26 | 18,61 |
| Tân Châu, +5 ngày | RF cũ | 3,70 | 4,34 |
| Tân Châu, +5 ngày | RF có EC quá khứ và đặc trưng đã chọn | 2,17 | 2,42 |
| Tân Châu, +5 ngày | 0,75 RF mới + 0,25 Seasonal Naive, chọn trên validation | **2,03** | **2,18** |
| Tân Châu, +5 ngày | Seasonal Naive riêng | 2,57 | 2,38 |
| Tân Châu, +35 ngày | 0,5 RF mới + 0,5 Seasonal Naive, chọn trên validation | **2,23** | **2,18** |

Tân Châu có cải thiện đáng kể so với RF cũ ở cả hai giả định; lợi ích so với baseline Seasonal Naive chỉ khoảng 0,20 mS/m trên 2022–2023. Mỹ Tho có thể giảm sai số so với **RF cũ** bằng phối Persistence khi giả định nhãn ra sớm, nhưng Persistence riêng còn tốt hơn trên 2022–2023. Trên validation, Monthly Climatology (69,37) vẫn tốt hơn phối RF/Persistence (70,46). Do đó chưa có một phương án Mỹ Tho thắng baseline mạnh nhất ổn định trên cả hai giai đoạn và cả hai giả định công bố.

## 3. Kiểm tra Tân Châu → Mỹ Tho

Thêm EC Tân Châu quá khứ **không cải thiện** Mỹ Tho trong thí nghiệm này. Ở giả định +5 ngày, RF dùng đặc trưng của chính Mỹ Tho đạt MAE 76,69 (validation) và 21,68 (2022–2023); RF thêm Tân Châu đạt 76,30 và **28,06**. Ở giả định +35 ngày, RF riêng Mỹ Tho 75,73 và 18,54; thêm Tân Châu 77,13 và 25,51. Vì vậy **không bật nhánh lan truyền EC thượng nguồn trong mô hình phục vụ**. Tín hiệu EC theo tháng tại Tân Châu không thể thay cho lượng nước ngọt, triều cửa sông và thời gian truyền mặn qua mạng sông phân nhánh. Hai chuỗi lấy **một mẫu/tháng** không xác định được độ trễ di chuyển theo ngày/giờ hoặc nồng độ tại mọi điểm giữa hai trạm.

Không nên dùng khoảng cách thẳng hoặc IDW hai điểm làm mô hình vật lý. Các nghiên cứu mạng sông yêu cầu kết nối theo dòng và khoảng cách dọc sông; nghiên cứu thủy động lực Mekong cho thấy tương tác sông–biển và triều. Đây là lý do khoa học để yêu cầu dữ liệu đồng bộ, không phải bằng chứng cho phép suy diễn đường đi chính xác từ hai nhãn hiện có.

## 4. Bài báo người dùng gửi và cách áp dụng

| Bài | Ý liên quan | Giới hạn khi áp dụng cho bộ EC hiện tại |
| --- | --- | --- |
| Nguyễn Duy Liêm và cộng sự (2024), WebGIS giám sát chất lượng nước | Trình bày/giám sát theo công trình và trạm | Không tự tạo nhãn EC hay hiệu chuẩn truyền mặn. |
| [Eslami và cộng sự (2021)](https://esurf.copernicus.org/articles/9/953/2021/index.html) | Xâm nhập mặn chịu tác động dòng chảy, triều và cấu trúc cửa sông | Mô hình 3D cần biên lưu lượng, triều, hình học và số đo hiệu chuẩn; không thể suy từ hai chuỗi EC tháng. |
| [Ver Hoef và cộng sự (2006)](https://digitalcommons.unl.edu/usdeptcommercepub/185/) | Tương quan không gian theo mạng sông và kết nối dòng | Cần mạng sông có hướng, đường đi và nhiều điểm quan trắc. |
| [Pham và cộng sự (2022)](https://js.vnu.edu.vn/EES/article/download/4852/4112) | So MLR/RF/ANN trên dữ liệu mặn tuần sông Hàm Luông | Khác trạm, mục tiêu, tần suất; không chuyển điểm MAE sang EC tháng. |
| [Nguyen và cộng sự (2025)](https://link.springer.com/article/10.1007/s44163-025-00336-3) | LSTM/XGB với lưu lượng thượng nguồn và mực nước triều theo giờ | Bộ hiện tại không có chuỗi salinity/EC giờ đồng bộ để học mạng như bài báo. |
| [Stachelek & Madden (2015)](https://arxiv.org/abs/1504.01146) | Nội suy theo đường đi tránh cắt qua đất/đê | Cần nhiều điểm đo dày và đường nước; hai trạm không đủ để kiểm định bản đồ. |
| [Apel và cộng sự (2020)](https://nhess.copernicus.org/articles/20/1609/2020/nhess-20-1609-2020.html) | ENSO/lưu lượng cho dự báo xâm nhập mặn theo mùa | Mục tiêu là chỉ báo xâm nhập mặn theo mùa, không phải độ lớn mẫu EC tháng; ENSO thử trước chưa chứng minh thêm lợi ích. |
| [Nguyen và cộng sự (2026)](https://www.mdpi.com/2073-4441/18/19/2379) | Chọn horizon riêng, dùng cross-validation mùa và phối mô hình | Bài dùng salinity trung bình ngày 1–5 ngày trước, còn đây là một mẫu EC mỗi tháng. Ý tưởng phối mô hình được kiểm tra riêng ở trên. |

## 5. Quyết định mô hình và dữ liệu cần để đi tiếp

- **Ứng viên Tân Châu:** giữ RF có EC quá khứ và tổ hợp Seasonal Naive trong artifact nghiên cứu. Có kết quả giảm lỗi trên tập hồi cứu, nhưng chưa thay registry/API vì sau 12/2023 không có EC mới: tại dự báo 11/2026, mẫu EC cuối đã cũ khoảng 35 tháng, nằm ngoài chế độ độ trễ đã kiểm định. Không thể gọi đó là dự báo hoạt động đã được xác nhận.
- **Mỹ Tho:** phối RF cũ/Persistence là hiệu chỉnh tạm cho kiểm tra hồi cứu dưới giả định +5 ngày. Độ nhạy +35 ngày và baseline cho thấy chưa đủ cơ sở triển khai. Giữ cảnh báo sai số cực trị.
- **Truyền mặn thật:** cần tối thiểu EC/độ mặn liên tục cùng đơn vị, thời gian và cơ sở nhiệt độ tại Tân Châu, các nhánh dọc sông Tiền, Mỹ Tho và cửa sông; lưu lượng tại phân lưu, mực nước/triều cửa biển, tiết diện/độ sâu, cống và hướng kết nối sông–kênh, bản ghi đúng ngày công bố. Chuỗi ngày/giờ chồng nhau qua nhiều mùa khô là điều kiện để ước lượng và kiểm định thời gian truyền, không chỉ thêm một tệp bản đồ.
- **Nếu không có dữ liệu mới:** chỉ có thể báo cáo cải thiện hồi cứu như trên; không thể chứng minh độ chính xác 2024–2026 hoặc vận hành cống. Dữ liệu mô phỏng, độ mặn quy đổi và tin báo chí không thay nhãn đo thật.

## 6. Tái lập và kiểm tra

Chạy `python scripts/experiment_ec_upstream_asof.py` rồi `python scripts/select_ec_asof_blends.py` trong `.venv`. Kết quả ở `outputs/ec_upstream_asof_20261029/`: 240 dự báo không trùng khóa, `metrics.csv`, `blend_grid.csv`, `blend_selection.csv`, `protocol.json`. Đã kiểm tra không có tháng EC Tân Châu bằng hoặc sau tháng mục tiêu Mỹ Tho, không có tháng nguồn sau ngày phát hành và mọi dự báo/nhãn đều hữu hạn. MRC gốc không bị sửa.

Kiểm thử `python -m unittest discover -s tests -p test_experiment_ec_upstream_asof.py -v` đạt: dự báo 01/2019 phát hành 06/12/2018 chỉ dùng EC Tân Châu 11/2018 trong giả định +5 ngày và 10/2018 trong giả định +35 ngày; EC 12/2018 không lọt vào đặc trưng.
