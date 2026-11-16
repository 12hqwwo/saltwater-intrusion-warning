# Hướng phát triển WebGIS EC Đồng Tháp

Ngày 12/11/2026. Trả lời năm câu hỏi: cần triển khai gì, sai số cao xử lý thế nào, nội suy đã hoàn chỉnh chưa, Conformal Prediction có hiệu quả không, nguồn dữ liệu bổ sung và cách tự suy công thức quy đổi EC–độ mặn. Mọi số dưới đây có tệp kết quả đi kèm (bản sửa sau rà soát 12/11/2026); không có thay đổi nào với registry, model phục vụ hay giao diện.

## 1. Vì sao sai số ở một số mốc còn quá cao

Sai số lớn tập trung ở vài tháng mùa khô cực đoan (02–05/2020, 03–04/2021). Các nguyên nhân là **giới hạn của dữ liệu**, không phải thiếu một đặc trưng:
- Nhãn là **một mẫu EC/tháng**, không ghi giờ. Ở vùng triều, EC trong một ngày có thể đổi nhiều lần theo pha triều; mẫu lấy lúc triều lên hay xuống cho số rất khác nhau. Mô hình tháng không biết pha triều lúc lấy mẫu.
- Mỹ Tho nằm ở vùng mà **mặn chỉ tới trong năm hạn**. EC gần như nằm yên ~20 mS/m rồi nhảy lên hàng trăm khi ranh mặn tới. Hành vi kiểu ngưỡng này rất khó học từ 26 tháng ≥150 mS/m trong 463 mẫu.
- Đáy sông hạ thấp làm cùng một lưu lượng nay cho mặn sâu hơn trước (Eslami và cộng sự 2019); mô hình học từ 1985 có thể hụt mặn hiện nay.
- Điểm số phụ thuộc giả định độ trễ công bố: khi giả định thủy văn có sau +35 thay vì +5 ngày, MAE 2021–2023 của cấu hình mô hình chính tăng từ 16,57 lên 24,61 mS/m ([giai_phap_van_de_mo_2026-11-12.md](giai_phap_van_de_mo_2026-11-12.md), mục 3). Kịch bản +35 buộc dùng **tháng thủy văn cũ hơn** (t−3 thay vì t−2); nó đo ảnh hưởng của việc mất một tháng thông tin, **không** đo sai khác giữa hai phiên bản số liệu MRC công bố ở hai thời điểm (dự án không có bản phát hành cũ để so).

Dự án đã thử hơn mười hướng (RF mịn, trọng số, GB Huber, FES, chuyển mạch Q, log, Ridge+RF, dữ liệu ngày, EC trạm lân cận, đặc trưng thiếu hụt mùa, ENSO, phân loại vượt ngưỡng); không hướng nào ổn định ở cả ba kỳ. **Kết luận: không nên tiếp tục tối ưu điểm số trên cùng dữ liệu đã xem.** Hướng đúng là (a) hiển thị bất định trung thực, (b) đổi câu hỏi sang xác suất/mức cảnh báo, (c) chờ dữ liệu mới để kiểm định.

## 2. Nội suy dọc sông đã hoàn chỉnh chưa

**Chưa, và chưa có kiểm định cho đoạn sông nào.** Hiện trạng:
- Kết quả MAE 11,25 → 3,92 mS/m ([kiem_chung_mythuan_ba_tram_2026-11-04.md](kiem_chung_mythuan_ba_tram_2026-11-04.md)) là sai số **tại đúng vị trí Mỹ Thuận** khi thêm dự báo của chính trạm Mỹ Thuận làm điểm neo, 24 tháng 2022–2023 (EC thấp, không có đỉnh mặn). Nó cho biết có thêm điểm neo thì giá trị tại điểm neo tốt hơn; **không** cho biết sai số nội suy ở các vị trí giữa Tân Châu–Mỹ Thuận, giữa Mỹ Thuận–Mỹ Tho hay ngoài Mỹ Tho.
- Phía ngoài Mỹ Tho tới cửa dùng điều kiện biên giả định chưa hiệu chuẩn.
- Lý thuyết cửa sông (Savenije) cho thấy độ mặn dọc tuyến thường giảm dạng đường cong từ cửa vào. Đây mới là **giả thuyết** về dạng hàm; chưa đủ lý do để thay nội suy tuyến tính khi chưa có số đo kiểm.

**Có thể phát triển thêm, theo thứ tự:**
1. Kiểm định **bỏ một trạm**: với ba trạm MRC cùng ngày mẫu, bỏ Mỹ Thuận, nội suy từ Tân Châu và Mỹ Tho bằng **giá trị thực đo** hai đầu, chấm tại Mỹ Thuận; báo riêng mùa khô. Đây là phép kiểm duy nhất làm được ngay với dữ liệu hiện có, và chỉ cho một vị trí giữa.
2. Thu **số đo đồng thời** (cùng ngày, cùng loại giá trị: cùng đỉnh triều hoặc cùng giờ) tại ít nhất 4 điểm dọc đoạn Mỹ Thuận–cửa, trong đó **giữ lại ít nhất một điểm** không dùng để fit.
3. Chỉ khi đó mới so tuyến tính với đường cong dạng mũ S(x) = S₀·exp(−x/L) trên điểm giữ lại; đổi phương pháp nếu dạng mũ thắng ở nhiều đợt đo, kể cả mùa khô.
4. Trước đó, nhãn bản đồ ghi: "nội suy tuyến tính giữa các trạm; chưa kiểm định sai số tại các vị trí giữa trạm".

## 3. Conformal Prediction có hiệu quả không: thử nghiệm 12/11/2026 (bản sửa)

**Đối tượng chấm.** Cấu hình của mô hình Mỹ Tho đang phục vụ `20261108T_HYDROLOGY_PRIMARY_V1` (RF 300 cây, sâu 8, lá ≥3, seed 42; 10 đặc trưng khí tượng t−2, chu kỳ tháng, Kratie và Tân Châu). Artifact đang phục vụ được fit trên toàn bộ nhãn đến 12/2023 nên không có sai số ngoài mẫu; vì vậy script **fit lại đúng cấu hình đó tại mỗi tháng phát hành** (rolling origin, cửa sổ mở rộng, chỉ dùng nhãn EC đã công bố tại ngày phát hành) và lấy sai số từ chuỗi dự báo này. Script đối chiếu thứ tự đặc trưng và tham số với manifest đang đăng ký; không tải hay đổi artifact. Bản trước dùng dự báo RF_compact (mô hình khác) và đã bị thay.

**Phương pháp** (thang log1p, mục tiêu 90 %; nhãn EC khả dụng +5 hoặc +35 ngày, giả định; khí tượng/thủy văn t−2):
- `online_quantile`: tại mỗi lần phát hành, lấy thống kê thứ tự bậc k = ⌈(n+1)·0,9⌉ của n sai số đã có; nếu k > n thì khoảng không giới hạn. Đây là **conformal trực tuyến trên chuỗi mô hình fit lại**, không phải split conformal với một mô hình cố định và tập hiệu chỉnh tách riêng, nên không mang bảo đảm độ phủ hữu hạn của split conformal.
- `online_quantile_season`: như trên, chỉ dùng sai số cùng mùa (XII–V khô, VI–XI mưa).
- `aci`: Adaptive Conformal Inference (Gibbs & Candès 2021), γ = 0,02, cập nhật khi nhãn được công bố.
- `tree_p05_p95`: phân vị 5–95 % dự báo của từng cây **trong cùng mô hình fit lại đó**, để so cùng dự báo, cùng tháng.

2010–2018 làm khởi động; chấm 2019–2021 và 2022–2023. Mã: [scripts/experiment_ec_conformal_20261112.py](../scripts/experiment_ec_conformal_20261112.py) (protocol `ROLLING_ONLINE_CONFORMAL_HYDROLOGY_PRIMARY_CONFIG_V1`); kết quả, danh sách tháng trượt và hash ở `outputs/ec_conformal_20261112/`. MAE/RMSE điểm của chuỗi rolling này là 51,44/128,63 (2019–2021) và 11,89/24,94 (2022–2023); không so trực tiếp với giao thức khóa EC.

**Độ phủ thực tế, +5 ngày (số tháng nằm trong khoảng / tổng):**

| Nhóm | online_quantile | online_quantile_season | aci | tree_p05_p95 |
|---|---|---|---|---|
| 2019–2021, cả kỳ | 31/36 | 30/36 | 31/36 | 28/36 |
| 2019–2021, mùa khô XII–V | 14/18 | **16/18** | 14/18 | 14/18 |
| 2019–2021, EC ≥100 | 4/6 | 4/6 | 4/6 | 3/6 |
| 2022–2023, cả kỳ | 22/24 | 23/24 | 22/24 | 22/24 |
| 2022–2023, mùa khô XII–V | 10/12 | 11/12 | 10/12 | 11/12 |

Kịch bản EC +35 ngày cho cùng mức ở biến thể theo mùa; `online_quantile` và `aci` hụt thêm 04/2020.

**Tháng EC cao 2019–2021, cận trên (mS/m):**

| Tháng | Thực đo | Dự báo | online_quantile | theo mùa | aci | cây p95 |
|---|---|---|---|---|---|---|
| 02/2020 | 558 | 107,9 | 257 | 368 | 219 | 316 |
| 03/2020 | 692 | 201,0 | 499 | 683 | 499 | 419 |
| 04/2020 | 607 | 259,3 | **652** | **889** | **733** | 559 |
| 03/2021 | 191,5 | 83,5 | **211** | **289** | **237** | **300** |

**Đánh giá:**
- Biến thể theo mùa phủ 16/18 tháng mùa khô 2019–2021 nhưng **trượt đúng 02/2020 và 03/2020**, hai tháng đầu đợt hạn. Mọi biến thể đều trượt hai tháng này. Conformal chỉ dựa trên sai số quá khứ nên phản ứng chậm khi chế độ mặn đổi đột ngột; **không sửa được đỉnh mặn**.
- So **trên cùng dự báo và cùng tháng**, khoảng giữa các cây hẹp hơn nhiều ở năm bình thường (trung vị độ rộng 14 mS/m so với 46 mS/m kỳ 2022–2023) và phủ kém hơn ở 2019–2021 (28/36 so với 30–31/36). Chênh lệch có thật nhưng nhỏ về số tháng; với 6 tháng EC ≥100 không đủ để xếp hạng ở nhóm này. Câu "tốt hơn rõ so với p90 cây 66,7 %" trong bản trước đã bị **bỏ**: con số 66,7 % thuộc phép cộng bù sai số mùa khô của một thí nghiệm khác, không phải độ phủ p90 cây trên cùng dự báo.
- Khoảng mùa khô rộng (trung vị độ rộng ~165 mS/m với biến thể theo mùa ở 2019–2021), phản ánh đúng mức bất định của mô hình tháng.
- Các kỳ chấm đã được xem nhiều lần, nên độ phủ ở đây là **hồi cứu**, chưa phải độ phủ kiểm định.

**Khuyến nghị:** nếu đưa lên WebGIS, dùng biến thể theo mùa cho **đúng phiên bản mô hình đang hiển thị**, tạo artifact sai số rolling riêng có manifest và hash, nhãn "khoảng thống kê từ sai số dự báo hồi cứu của cùng cấu hình mô hình; phủ 16/18 tháng mùa khô 2019–2021, trượt 02–03/2020; không phải cận an toàn". Khi đổi model phục vụ, phải tạo lại artifact sai số. Không dùng cận trên làm ngưỡng mở cống.

## 4. Cần triển khai gì trên WebGIS (theo thứ tự ưu tiên)

| Ưu tiên | Việc | Lý do | Điều kiện |
|---|---|---|---|
| 1 | Dải bất định conformal theo mùa trên biểu đồ và phiếu dự báo | Dự báo một con số che giấu sai số hàng trăm mS/m ở mùa khô | Cần artifact sai số rolling của **đúng phiên bản mô hình** đang phục vụ, có manifest/hash; tạo lại khi đổi model |
| 2 | Hiển thị **xác suất vượt mức WATCH/SEVERE** bên cạnh độ lớn | Câu hỏi vận hành là "có nguy cơ không", không phải con số chính xác | Hiện chỉ tốt hơn khí hậu tháng ở năm cực đoan; ghi rõ là nghiên cứu |
| 3 | Bảng điểm theo **kịch bản độ trễ** (+5/+35/+90) trong tab đánh giá | Điểm số phụ thuộc mạnh giả định chưa chứng minh | Có sẵn từ `outputs/ec_peak_risk_20261112/` |
| 4 | Nhãn phạm vi kiểm định của nội suy trên bản đồ (chưa kiểm định tại vị trí giữa trạm) | Người xem dễ hiểu màu sông là đo thực | Có ngay |
| 5 | Lớp điểm "bản tin chính thức" (g/L, nguồn, ngày phát hành) | Bối cảnh mùa hiện tại khi không có EC MRC mới | Nhập tay; không tô kênh, không dùng làm nhãn |
| 6 | Quy trình nạp EC mới + chấm tự động khi có dữ liệu | Để kiểm định độc lập ngay khi có nguồn | Cần nguồn EC |
| 7 | Kiểm định bỏ một trạm; sau đó mới cân nhắc nội suy dạng mũ đoạn cửa sông | Chưa có sai số nội suy tại vị trí giữa trạm | Dạng mũ cần đo đồng thời nhiều điểm và một điểm giữ lại |

## 5. Nguồn dữ liệu có thể bổ sung sau này

| Nguồn | Cung cấp | Trạng thái |
|---|---|---|
| MRC Data Portal (EC VN_019805/019803/019804) | EC mẫu tháng sau 2023 | Hiện không có; theo dõi định kỳ |
| Trạm đo mặn tự động trên sông Tiền (theo chuẩn trạm quan trắc mặn tự động của Bộ, truyền dữ liệu thời gian thực) | EC và độ mặn theo giờ | Không có API công khai; cần đề nghị chính thức |
| Nền tảng chia sẻ dữ liệu mặn DHI – Văn phòng Ủy ban sông Mê Công Việt Nam (01/2026–01/2027) | Dữ liệu mặn và dự báo MIKE+ | Đang xây dựng; theo dõi khi công bố |
| Bản tin xâm nhập mặn Nam Bộ của NCHMF (kttv.gov.vn) | Đỉnh mặn 10 ngày, có giờ phát hành | Công khai PDF; chỉ làm bối cảnh |
| Báo cáo tuần mùa khô của MRC | Q Kratie, mực nước Tân Châu đã công bố tại thời điểm | Công khai PDF; dùng xác định giá trị "biết được lúc phát hành" |
| GloFAS (Copernicus) | Dự báo lưu lượng có lưu trữ từ 11/2019 | Công khai; thay thế Q khi MRC chậm |
| SEAS5 (ECMWF) | Dự báo mùa mưa/nhiệt cho tháng tương lai | Công khai; thay khí tượng t−2 bằng dự báo |
| Copernicus GTSM / CMEMS | Mực nước tổng, nước dâng, độ mặn biển ngoài khơi | Công khai; biên biển cho mô hình thủy lực |
| Sentinel-2/Landsat | Chỉ số độ đục/màu nước, diện tích lúa bị ảnh hưởng | Công khai; liên hệ với EC chưa được chứng minh, chỉ nghiên cứu |
| Tự đo (cảm biến EC giá rẻ đã hiệu chuẩn) tại 1–2 cống | EC theo giờ trong và ngoài cống | Khả thi nếu có kinh phí; là nguồn kiểm định trực tiếp nhất |

## 6. Tự suy công thức quy đổi EC ↔ độ mặn khi có dữ liệu cặp

**Có thể, nhưng phải định nghĩa đại lượng đích trước khi fit.** "Độ mặn" không phải một đại lượng duy nhất:
- **Độ mặn thực dụng PSS-78** (gần như không thứ nguyên, ký hiệu PSU) được định nghĩa từ **tỷ số độ dẫn** của mẫu so với dung dịch KCl chuẩn ở 15 °C, 1 atm, theo công thức có hiệu chỉnh nhiệt độ; phạm vi định nghĩa 2–42. Không đưa EC25 thẳng vào công thức như thể đó là phép đo ở điều kiện tham chiếu của PSS-78, và không đồng nhất PSU với g/L.
- **g/L tổng chất rắn hòa tan (TDS)** đo bằng sấy khô cặn; phụ thuộc thành phần ion.
- **Clorua (mg/L)** đo bằng chuẩn độ; là chỉ tiêu dùng trong QCVN 39:2011/BTNMT.
- **Độ mặn ‰ hay g/L đọc từ khúc xạ kế hoặc máy cầm tay** mà cơ quan địa phương báo: thường là giá trị do thiết bị tự quy đổi từ độ dẫn theo thuật toán của hãng.

Quan hệ EC với mỗi đại lượng khác nhau; công thức suy cho đại lượng này không dùng cho đại lượng kia.

**Quy trình:**
1. **Chọn đại lượng đích** khớp quyết định cần hỗ trợ (ví dụ: con số g/L mà bản tin địa phương dùng, hay clorua theo QCVN 39). Ghi rõ đơn vị.
2. **Chọn phương pháp chuẩn** cho đại lượng đó (ví dụ phòng thí nghiệm có quy trình được công nhận cho TDS hoặc clorua), ghi model thiết bị, cách hiệu chuẩn, sai số phương pháp.
3. **EC đo cùng mẫu nước**: ghi cả EC thô, nhiệt độ nước, hệ số bù nhiệt của máy (thường 2 %/°C, tuyến tính) để biết EC25 được tính ra sao; với nước lợ, bù nhiệt tuyến tính có sai số riêng.
4. **Thiết kế mẫu**: phủ đủ dải từ nước ngọt tới mặn, đặc biệt dày ở vùng quyết định (dưới 1 g/L), nhiều trạm, nhiều đợt đo trong các mùa. Khoảng 30–50 cặp chỉ là **mốc thu thập ban đầu** để xem dạng quan hệ; không bảo đảm đủ cho toàn dải. Đủ hay chưa được xác định bằng độ rộng khoảng dự báo ở từng dải sau kiểm định.
5. **Tách kiểm định theo đợt đo hoặc theo trạm** (giữ nguyên một đợt/trạm làm tập kiểm), không chia ngẫu nhiên từng mẫu, vì các mẫu cùng đợt có cùng sai lệch thiết bị và cùng thành phần nước.
6. **So các dạng hàm** trên tập kiểm: tuyến tính qua gốc, tuyến tính có hệ số tự do, lũy thừa (log–log), và hai đoạn (nước ngọt ion sông / nước lợ ion biển). Nếu đại lượng đích là PSU, dùng đúng định nghĩa PSS-78 từ tỷ số độ dẫn và nhiệt độ thô, rồi chỉ hiệu chỉnh phần lệch địa phương.
7. **Báo sai số và khoảng dự báo theo từng dải** (ví dụ < 0,5; 0,5–2; 2–4; > 4 g/L), không chỉ hệ số và R² toàn dải.

**Cảnh báo về tệp `data/8file/01_ec_salinity_calibration_and_lookup.csv`:** không dùng 18 "cặp quan trắc" trong tệp này để hiệu chuẩn.
- Độ mặn "quan trắc" khớp công thức PSS-78 với tương quan 0,99993; tỷ số EC/S giảm đều từ 200 xuống 159 theo đúng hình dạng PSS-78. Đây là dấu hiệu các giá trị được **tính từ công thức**, không phải đo độc lập.
- Hai cặp gắn nhãn MRC không khớp dữ liệu MRC gốc: Mỹ Tho 15/01/2023 ghi 52,0 mS/m trong tệp, MRC gốc là 19,36; Tân Châu 15/04/2023 ghi 26,4, MRC gốc là 30,3. Giờ 07:00 cũng không có trong MRC gốc.
- Fit lại công thức trên các cặp này chỉ tái tạo PSS-78, tạo cảm giác "đã hiệu chuẩn địa phương" mà không có bằng chứng.

## 7. Lộ trình đề xuất

1. **Ngắn hạn:** tạo artifact sai số rolling cho đúng mô hình đang phục vụ, rồi đưa dải conformal theo mùa và bảng điểm theo kịch bản độ trễ lên WebGIS; thêm nhãn phạm vi kiểm định của nội suy; ghi rõ mô hình chưa có kiểm định độc lập.
2. **Trung hạn:** đổi trọng tâm sang **xác suất vượt mức cảnh báo theo mùa** (một dự báo cho II–IV, phát hành tháng 12–01) và quy trình nạp/chấm EC mới tự động.
3. **Dài hạn (cần dữ liệu):** EC mới sau 2023 để kiểm định; chuỗi đo cùng thời điểm nhiều điểm, có điểm giữ lại, để kiểm định và so dạng nội suy; cặp EC–đại lượng độ mặn đã định nghĩa, đo bằng phương pháp chuẩn, để suy công thức quy đổi; cảm biến và nhật ký cống để tô màu kênh.
