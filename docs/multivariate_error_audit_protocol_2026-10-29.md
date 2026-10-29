# Kiểm tra sai số và giao thức chấm EC đa biến

Ngày khóa giao thức: 29/10/2026. Phiên bản dự báo được kiểm tra: `20261023T041813Z`. Hai trạm: Mỹ Tho (`MYTHO`) và Tân Châu (`TANCHAU`). Đơn vị EC và mọi sai số: mS/m.

## Phát hiện từ 120 tháng đã chấm

Mỗi trạm có 36 tháng validation (2019–2021) và 24 tháng holdout (2022–2023). Bảng chi tiết lưu **15 tháng có sai số tuyệt đối RandomForest lớn nhất cho từng trạm và từng tập chấm**, gồm EC đo, dự báo, ba sai số baseline, EC tháng kề, mùa, ngưỡng EC cao, số mẫu và trạng thái rà nguồn.

| Trạm và tập | Mùa khô 12–4: n, MAE RF | Ngoài mùa khô 5–11: n, MAE RF | EC cao: ngưỡng, n, MAE RF | MAE Seasonal Naive trên EC cao |
| --- | ---: | ---: | ---: | ---: |
| Mỹ Tho, validation | 15; 126,76 | 21; 28,79 | ≥60,6; 6; 317,91 | 504,85 |
| Mỹ Tho, holdout | 10; 35,13 | 14; 6,31 | ≥73,8; 1; 49,04 | 39,60 |
| Tân Châu, validation | 15; 4,54 | 21; 3,15 | ≥20,8; 17; 6,00 | 3,36 |
| Tân Châu, holdout | 10; 5,57 | 14; 3,65 | ≥21,3; 10; 7,96 | 3,30 |

- Mỹ Tho validation: tháng 02–05/2020 có EC đo 558, 692, 607, 398; RF đều dự báo thấp. Sai số lớn nhất là 03/2020: 558,93. Các tháng kề cũng cao, nên trước mắt đây là một đợt cực trị liên tiếp trong dữ liệu, chưa có bằng chứng để tự sửa nhãn.
- Mỹ Tho holdout: 04/2022 EC đo 25,7, RF dự báo 253,61, sai số 227,91. Một tháng này chiếm 51,8% tổng sai số tuyệt đối của 24 tháng holdout. EC tháng trước là 38,7; giá trị 25,7 khớp tệp MRC gốc. Bước tiếp theo là phân tích đầu vào thời tiết 02/2022 và phản ứng của mô hình, chưa kết luận nguyên nhân.
- Tân Châu holdout: 03/2023 (26,8 so với 14,21) và 04/2023 (30,3 so với 19,29) đều bị dự báo thấp. Trong 10 tháng EC cao, RF có MAE 7,96; Seasonal Naive 3,30. Đây là dấu hiệu lệch thấp có hệ thống ở nhóm này, không phải chứng cứ cho một nguyên nhân cụ thể.
- Đã đối chiếu hai CSV trong gói xuất MRC `mrc20260831193610.zip` (SHA-256 `66d9960eaea114c27f26b5ca90b669cb217fea7e4695bd0fa21a51bc6fa22ef5`) với dữ liệu đồ án: **927/927 tháng khớp giá trị và số mẫu; không thiếu/thừa tháng**. Bảng chi tiết ghi `MATCHED_MRC_EXPORT`. MRC ghi cả 927 bản ghi là `Raw - Not Yet Reviewed` và `Unverified data`; đây là cấp duyệt của chính nguồn, không phải sai lệch nhập liệu. Không loại điểm nào khỏi phép chấm.

## Giao thức chấm đã khóa

1. **Mục tiêu:** EC của một mẫu tháng tại mỗi trạm, không suy diễn thành EC cực đại tháng hay độ mặn. Tháng là `target_month`; đơn vị mS/m.
2. **Tập thời gian của bản đã lưu:** validation 01/2019–12/2021, huấn luyện nhãn đến 12/2018; holdout 01/2022–12/2023, huấn luyện nhãn đến 12/2021. Giữ nguyên các dự báo đã lưu để chẩn đoán. Ranh giới này chưa đáp ứng mốc phát hành 06/`t−1` ở tháng đầu tập chấm (xem dưới). Không dùng kết quả holdout để sửa siêu tham số rồi gọi lại đó là kiểm định độc lập.
3. **Cohort:** một trạm × tháng có đủ cả RandomForest, Persistence, SeasonalNaive, MonthlyClimatology và EC đo. Chấm bốn mô hình trên cùng 36/24 tháng; không loại cực trị hay tháng QA chưa xác minh khỏi phép tính. Nếu về sau thiếu một đầu vào, báo số tháng bị loại và nguyên nhân thay vì điền số 0.
4. **Thước đo:** MAE là trung bình `|dự báo − EC đo|` (thước đo chính); RMSE là căn trung bình bình phương sai số; bias là trung bình `(dự báo − EC đo)`, âm nghĩa là dự báo thấp. Báo đủ `n`, MAE, RMSE, bias cho toàn bộ tập, mùa và nhóm EC cao. So sánh với cả ba baseline trên cùng cohort. Ưu tiên giảm lỗi mùa khô và EC cao nhưng không đánh đổi bằng việc làm xấu MAE toàn tập.
5. **Mùa:** theo quy ước người dùng cung cấp ngày 29/10/2026, mùa khô = tháng 12–4 năm sau; nhóm đối chiếu = tháng 5–11, gọi là **ngoài mùa khô** để không mặc nhiên khẳng định tất cả là mùa mưa. Phân nhóm theo tháng mục tiêu. Tháng 5/2020 của Mỹ Tho nằm trong nhóm ngoài mùa khô nhưng vẫn được giữ trong nhóm EC cao và toàn tập.
6. **EC cao:** EC đo ≥ phân vị 90 theo quy tắc nearest-rank của **nhãn huấn luyện trước kỳ chấm**, tính riêng theo trạm và split. Ngưỡng lần lượt: Mỹ Tho 60,6/73,8; Tân Châu 20,8/21,3 cho validation/holdout. Ngưỡng không tính từ nhãn đánh giá. Đây là phân tích hậu nghiệm theo EC thực đo, không phải bộ lọc có thể biết khi phát hành dự báo; `n=1` ở Mỹ Tho holdout nên chỉ mô tả mẫu đó, không suy rộng.
7. **Xếp hạng tháng lỗi:** sai số tuyệt đối RandomForest giảm dần, hòa thì tháng tăng dần. Lấy 15 tháng mỗi trạm × split để validation không che khuất holdout. Giữ EC trước/sau một tháng và sai số baseline để hỗ trợ rà nguồn; không dùng EC tháng sau làm đầu vào dự báo.

## Biến tại thời điểm phát hành

Quy ước phát hành cố định cho dự báo tháng `t`: **ngày 06 của tháng `t−1`, giờ Việt Nam**. Ví dụ dự báo 11/2026 phát hành từ 06/10/2026. Đây là mốc thiết kế của phép chấm; hệ thống hiện không lưu dấu thời gian công bố lịch sử cho từng nguồn.

| Biến/đầu vào | Tháng dữ liệu | Có thể biết theo giao thức? | Điều kiện và giới hạn |
| --- | --- | --- | --- |
| Tổng mưa, nhiệt độ trung bình, gió trung bình ERA5 | `t−2` | Có theo **giả định** | Chỉ dùng đủ ngày trong tháng; adapter gắn `assumed_available_at = cuối tháng + 5 ngày`. Đây không phải dấu thời gian công bố thực tế hay bản dữ liệu ERA5 đúng như đã tồn tại lúc đó. |
| `month_sin`, `month_cos` | tháng `t` | Có | Tính từ lịch, không cần quan trắc tương lai. |
| Persistence | EC mới nhất có tháng ≤ `t−2` | Có điều kiện | Chỉ hợp lệ nếu EC tháng đó thực sự đã công bố trước 06/`t−1`. Dữ liệu hiện không có lịch sử ngày công bố; backtest đang giả định có. |
| SeasonalNaive | EC tháng `t−12` | Có điều kiện | Cũng cần xác nhận ngày công bố EC gốc. |
| MonthlyClimatology | nhãn trước đầu split | Có điều kiện | Trung bình cùng tháng chỉ từ tập huấn luyện cố định, không dùng EC của kỳ chấm. |
| Trọng số RandomForest của bản chấm | nhãn đến 12/2018 hoặc 12/2021 | **Không** ở mốc phát hành tháng 01 đầu split | Dự báo 01/2019 phát hành giả định 06/12/2018 nhưng model đã học EC 12/2018; tương tự 01/2022 và EC 12/2021. Các tháng khác còn thiếu ngày công bố nhãn để kết luận. |
| EC đo của tháng `t`, EC tháng `t−1`, EC tháng sau | hiện tại/tương lai | Không | Chỉ dùng để chấm hoặc rà sai số sau khi có nhãn. |
| Ngưỡng EC cao của split | nhãn trước split | Có | Ngưỡng có trước kỳ đánh giá; nhưng việc mẫu đánh giá **thuộc nhóm cao** chỉ xác định sau khi biết EC đo. |

**Giới hạn thời gian:** backtest này kiểm soát độ trễ *theo tháng* của biến thời tiết, nhưng nhãn 12/2018 và 12/2021 trong trọng số model đã đi trước mốc phát hành giả định của dự báo 01/2019 và 01/2022. Chưa chứng minh mọi bản ERA5 và nhãn EC khác thực sự tồn tại vào ngày phát hành lịch sử. Vì vậy đây là đánh giá hồi cứu để chẩn đoán, chưa phải phép chấm tiền cứu đúng thời điểm. Mô hình phục vụ hiện fit lại trên toàn bộ nhãn đến 12/2023; các hàng validation/holdout trong bảng là dự báo lịch sử riêng, không phải dự báo từ model phục vụ hiện tại.

Vì 2022–2023 đã được dùng để phân tích lỗi, các lần chỉnh mô hình sau chỉ được dùng tập này như **mốc lịch sử**; không gọi lại nó là holdout độc lập cho phương án mới. Chọn biến/siêu tham số bằng validation theo thời gian và để dành một giai đoạn EC mới, chưa xem khi chọn mô hình, cho kết luận cuối.

Khi huấn luyện lại để chấm đúng mốc phát hành, mỗi lần fit chỉ được dùng nhãn có **ngày công bố ≤ ngày phát hành**; cần lưu ngày công bố hoặc quy tắc trễ có chứng cứ cho từng nguồn. Nếu thiếu ngày công bố EC, phải ghi kết quả là đánh giá hồi cứu theo giả định. Tập mới phải kiểm tra cả trọng số model, baseline và phiên bản dữ liệu thời tiết theo cùng một mốc.

Đã triển khai bản chấm hồi cứu theo hai giả định ngày công bố EC (+5/+35 ngày từ cuối tháng) trong [backtest theo ngày phát hành](asof_backtest_2026-10-29.md). Bản đó huấn luyện lại từng tháng và để nguyên các dự báo cũ cho mục đích đối chiếu.

## Tái tạo và bước kiểm tra nguồn

Chạy `python scripts/audit_multivariate_errors.py --mrc-zip <đường_dẫn_zip_MRC>` tại gốc dự án. Script xác minh SHA-256 của hai tệp dự báo theo manifest, đối chiếu EC đo với CSV nhãn và gói MRC, kiểm tra 36/24 tháng mỗi trạm, rồi tạo `top_errors.csv`, `season_metrics.csv`, `high_ec_metrics.csv` và `audit_summary.json` trong `outputs/multivariate_error_audit_20261029/`. Workbook Excel cùng thư mục trình bày các bảng đó.

Gói MRC đã cung cấp ngày lấy mẫu, đơn vị mS/m và cấp duyệt cho từng bản ghi. Các tháng 02–05/2020 ở Mỹ Tho, 04/2022 ở Mỹ Tho và 03–07/2023 ở Tân Châu đều khớp nguồn, nên không sửa nhãn để giảm sai số. Tiếp theo cần kiểm tra đầu vào khí tượng, sự khác biệt giai đoạn và giới hạn đặc trưng của mô hình. Gói xuất được tạo năm 2026; nó không chứng minh ngày dữ liệu từng tháng đã sẵn có trong quá khứ để dùng cho backtest theo thời điểm phát hành.

## Thử nghiệm tách mô hình mùa khô/ngoài mùa khô

Ngày 29/10/2026, chạy `python scripts/experiment_seasonal_ec.py` với mùa khô 12–4. Mỗi trạm và mỗi split được fit lại cùng pipeline RandomForest và cùng năm huấn luyện như bản hiện tại. Một nhánh học mọi tháng; nhánh kia học riêng mùa khô/ngoài mùa khô và chỉ dùng mô hình tương ứng để dự báo. Tệp `seasonal_split_comparison.csv` lưu MAE, RMSE, bias cho toàn tập, từng nhóm mùa và EC cao. Runtime thử nghiệm dùng scikit-learn 1.8.0, trong khi artifact gốc ghi 1.9.1; mô hình gộp được fit lại để so hai nhánh trong cùng runtime.

| Trạm, tập | MAE gộp fit lại | MAE tách mùa | Mùa khô: gộp → tách | Baseline tốt nhất toàn tập |
| --- | ---: | ---: | ---: | ---: |
| Mỹ Tho, validation | 69,61 | 73,23 | 126,76 → 141,89 | Climatology 70,22 |
| Mỹ Tho, holdout | 18,34 | 20,15 | 35,17 → 42,59 | Persistence 12,62 |
| Tân Châu, validation | 3,73 | 3,69 | 4,54 → 4,41 | Seasonal Naive 2,57 |
| Tân Châu, holdout | 4,45 | 4,15 | 5,57 → 4,97 | Seasonal Naive 2,38 |

Kết luận cho bản thử này: **không thay model phục vụ bằng hai model theo mùa**. Mỹ Tho xấu hơn ở cả validation/holdout, đặc biệt mùa khô. Tân Châu cải thiện nhẹ nhưng vẫn thua Seasonal Naive rõ rệt ở holdout. Model mùa khô chỉ học 166–181 tháng thay vì 403–440 tháng, nên việc tách làm giảm dữ liệu cho nhánh này. Các mốc huấn luyện của thí nghiệm giữ nguyên để so công bằng với bản cũ, vì vậy giới hạn thời điểm phát hành nêu trên vẫn áp dụng.
