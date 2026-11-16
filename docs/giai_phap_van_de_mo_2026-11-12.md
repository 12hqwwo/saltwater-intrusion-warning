# Giải pháp cho các vấn đề mở trong CLAUDE.md mục 7 và 13

Ngày 12/11/2026. Tài liệu này tổng hợp kết quả tra cứu nguồn công khai (ECMWF/Copernicus, MRC, NCHMF, báo chí tỉnh, bài báo khoa học) và **một thử nghiệm mới** chạy trên dữ liệu dự án. Không đổi registry, model phục vụ hay giao diện. Các URL ở cuối mỗi mục; phần "chưa xác minh" được ghi riêng.

## Tóm tắt quyết định

| Vấn đề | Giải quyết được ngay? | Hành động đề xuất |
|---|---|---|
| 1. EC Mỹ Tho sau 2023 để kiểm định độc lập | Không | Đã thử MRC (cổng dữ liệu, báo cáo 2024), SIWRR, Văn phòng Ủy ban sông Mê Công Việt Nam và công ty thủy lợi tỉnh: không có hoặc không cấp dữ liệu. Bản tin độ mặn g/L **không** kiểm định được cảnh báo EC (mục 1). Mô hình vẫn chưa có kiểm định độc lập. |
| 2. Lịch công bố đầu vào | Không | Không nguồn nào có dấu thời gian công bố từng giá trị. Mọi độ trễ là **giả định**; báo cáo các kịch bản +5, +35, +90 ngày theo từng nguồn, không chọn một kịch bản làm "đúng". Điểm số của mô hình chính xấu đi rõ khi thủy văn trễ hơn +5 (mục 3). |
| 3. Bắt đỉnh mặn / báo cao giả | Chưa | Thử nghiệm mới (mục 3) **không ổn định** ở mọi kịch bản độ trễ, không triển khai. Hướng còn lại: bài toán xác suất vượt ngưỡng theo mùa và khoảng conformal thích ứng, chấm trên dữ liệu mới. |
| 4. Màu EC trong kênh/sau cống | Không, nếu chỉ dùng dữ liệu mở | Giữ đoạn sau cống trống. Có thể thêm lớp "bản tin chính thức" dạng điểm. Muốn tô kênh cần nhật ký cống, cảm biến trong kênh và mô hình HEC-RAS 1D đã hiệu chuẩn. |
| 5. Ngưỡng EC theo cây trồng | Có nguồn tham khảo | Ghi ngưỡng tham khảo có nguồn vào hồ sơ cống dưới dạng văn bản, tách khỏi mức màu bản đồ. |

## 1. Dữ liệu EC Mỹ Tho sau 12/2023

**Kết quả tìm kiếm (người dùng đã thử trực tiếp, 12/11/2026):**
- MRC: không tìm thấy EC VN_019805 sau 12/2023 trên cổng dữ liệu, và không xác nhận được [báo cáo chất lượng nước 2024](https://www.mrcmekong.org/publications/2024-lower-mekong-water-quality-monitoring-report) có EC Mỹ Tho theo tháng.
- SIWRR, Văn phòng Ủy ban sông Mê Công Việt Nam, công ty thủy lợi tỉnh: không cấp dữ liệu.
- Tệp hiện có kết thúc ở 15/12/2023 với cờ "Raw – Not Yet Reviewed". **Mô hình chưa có tập kiểm định độc lập**; mọi điểm số trong dự án là hồi cứu trên dữ liệu đã xem.

Ngày xuất bản báo cáo năm của MRC (báo cáo 2020 ra 05/2022, 2021 ra 08/2022, 2022 ra năm 2024) **không** cho biết ngày một mẫu EC xuất hiện trên cổng dữ liệu, nên không dùng làm độ trễ của nhãn EC.

**Vì sao bản tin độ mặn không kiểm định được cảnh báo EC:**
- Bản tin và báo chí đưa độ mặn g/L, thường là đỉnh triều trong ngày hoặc trong 10 ngày, tại điểm khác (công viên Lạc Hồng, Vàm Kênh, Hòa Bình, An Định). Mẫu MRC là một mẫu EC/tháng tại trạm Mỹ Tho, không ghi giờ.
- Muốn hỏi "dự báo có vào mức WATCH/SEVERE không" cần một quy tắc đối chiếu g/L đỉnh với EC mẫu tháng, **hiệu chuẩn bằng số đo cùng vị trí, cùng thời gian**. Dự án không có cặp số đo như vậy, nên câu hỏi có/không này cũng không chấm được.
- Một giá trị ngày 11/03/2024 (6,8 g/L) và một giá trị đến 29/02/2020 (5,7 g/L, SIWRR) khác thời điểm trong mùa, nên **không** suy ra được mùa khô 2024 nặng hơn 2020.
- Bản tin NCHMF phát hành 15:00 ngày 20/04/2026 chỉ là thông tin đã biết **từ thời điểm đó**, không phải đầu vào sẵn có cho dự báo các tháng trước.
- Quy đổi g/L và EC: hệ số 0,0064 của ứng dụng chỉ là tham khảo. Câu viện dẫn văn bản pháp lý về quy đổi PSS-78 trong bản trước đã bị **bỏ** vì chưa có văn bản kiểm chứng được.

**Các số đã ghi nhận** (chỉ là bối cảnh mô tả, không làm nhãn hay phép kiểm):

| Ngày | Điểm | Độ mặn (loại giá trị) | Nguồn |
|---|---|---|---|
| 11/03/2024 | Công viên Lạc Hồng, Mỹ Tho | 6,8 g/L (giá trị báo chí trong ngày) | [Nhân Dân](https://nhandan.vn/tien-giang-quyet-liet-trien-khai-cac-giai-phap-phong-chong-han-man-post799553.html) |
| 12/02/2024 | Công viên Lạc Hồng | gần 2 g/L | [Tuổi Trẻ](https://tuoitre.vn/tien-giang-man-da-xam-nhap-sau-vao-dat-lien-hon-50km-20240212110133913.htm) |
| 11/02/2025 | Công viên Lạc Hồng | 0,10 g/L | [TTXVN](https://vietnammedia.vnanet.vn/news/nuoc-man-nguoc-dong-vao-sau-thuong-luu-tinh-tien-giang-150628.htm) |
| 11–20/04/2026 | Vàm Kênh / Hòa Bình / An Định | 17,5 / 8,7 / 2,0 g/L (đỉnh 10 ngày) | [NCHMF, phát hành 15:00 20/04/2026](https://kttv.gov.vn//upload/thuyvan1/2026/4/20/dbqg_xman_20260420_1500.pdf) |

**Điều cần có để kiểm định thật:** EC (hoặc độ mặn kèm EC gốc) tại hoặc sát trạm Mỹ Tho sau 12/2023, có ngày giờ lấy mẫu, đơn vị, QA và ngày công bố; hoặc một chuỗi đo **đồng thời** g/L đỉnh và EC mẫu tại cùng điểm đủ dài để hiệu chuẩn quy tắc đối chiếu. Cho đến khi có, báo cáo phải ghi mô hình chưa được kiểm định độc lập.

## 2. Lịch công bố đầu vào

Không nguồn nào trong dự án có **dấu thời gian công bố từng giá trị** hay lưu bản phát hành cũ. Vì vậy mọi độ trễ dưới đây là **kịch bản giả định**, không kịch bản nào "đã chứng minh". Tài liệu nguồn chỉ giúp chọn khoảng hợp lý để thử độ nhạy.

| Nguồn | Tài liệu nói | Tài liệu **không** chứng minh | Kịch bản thử |
|---|---|---|---|
| ERA5 trung bình tháng | ERA5T trễ khoảng 5 ngày; trung bình tháng có khoảng ngày 6 tháng sau; bản cuối thay sau 2–3 tháng ([CDS](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-monthly-means)). | Dữ liệu đã có **trước giờ** phát hành dự báo ngày 6; giá trị ERA5T lúc đó trùng bản tải năm 2026 (có sự cố đã ghi nhận 09–12/2021, 10/2024, 1–6/01/2025, [ECMWF forum](https://forum.ecmwf.int/t/era5-data-from-1st-january-2025-was-degraded-and-is-being-corrected/10689)). | +5, +35 |
| Lưu lượng Kratie | Tính từ đường quan hệ mực nước–lưu lượng, đường quan hệ được cập nhật định kỳ ([MRC](https://www.mrcmekong.org/hydrometeorological-monitoring)). | Lịch công bố, chính sách hiệu chỉnh, giá trị đã công bố trong quá khứ. | +5, +35, +90 |
| Mực nước Tân Châu | Có trong báo cáo tuần mùa khô của MRC. | Ngày chuỗi ngày xuất hiện trên cổng dữ liệu; hiệu chỉnh sau đó. | +5, +35, +90 |
| EC Mỹ Tho (MRC) | Không có tài liệu về lịch cổng dữ liệu. | Bất kỳ độ trễ nào; ngày báo cáo năm không phải ngày lên cổng. | +5, +35; giao thức khóa EC là trường hợp xấu nhất |
| ONI (NOAA PSL) | Giá trị gán theo tháng giữa của trung bình 3 tháng. | Bản phát hành theo thời điểm; mức hiệu chỉnh khi cập nhật. | ONI tâm tháng mục tiêu −4, luôn so với phiên bản bỏ ONI |

**Cách dựng tập dữ liệu "biết được vào ngày phát hành":**
1. Với mỗi nguồn, xác định **tháng mới nhất đã có** tại ngày phát hành theo kịch bản trễ riêng của nguồn đó, rồi tính mọi trung bình trượt, trung vị cùng mùa và cửa sổ mùa chỉ đến tháng đó. Chỉ đổi độ trễ nhãn EC mà giữ đặc trưng tính từ t−2 thì **không** kiểm thử được độ trễ của nguồn đầu vào.
2. Ghi kịch bản trễ của từng nguồn trong manifest; báo cáo theo bảng kịch bản, không gộp.
3. Nếu sau này lấy được báo cáo tuần MRC lưu trữ, đối chiếu Q/mực nước đã công bố với bản tải năm 2026 để ước lượng mức hiệu chỉnh.
4. GloFAS có lưu trữ dự báo từ 05/11/2019 nhưng đổi phiên bản (v4.0 năm 2023, v5.0 ngày 15/07/2026); không trộn phiên bản trong một phép chấm.

## 3. Bắt đỉnh mặn: thử nghiệm mới ngày 12/11/2026

**Giả thuyết** từ [Apel và cộng sự 2020](https://nhess.copernicus.org/articles/20/1609/2020/) (dự báo đúng hạn mặn 2020 trước 9 tháng bằng hồi quy logistic trên Niño3.4 hoặc chỉ số dòng chảy chuẩn hóa 3 tháng) và [Nguyen & Savenije 2006](https://hess.copernicus.org/articles/10/743/2006/) (chiều dài xâm nhập phụ thuộc phi tuyến vào Q, nên EC tại một trạm cố định tăng theo kiểu ngưỡng):
- Mô hình hiện tại chỉ có Q tháng t−2 và trung bình 3 tháng; thiếu **trí nhớ theo mùa** về thiếu hụt dòng chảy.
- Có thể dự báo **xác suất vượt ngưỡng** tốt hơn là dự báo độ lớn.

**Đặc trưng mới** (tính từ *tháng neo* là tháng thủy văn mới nhất đã có theo kịch bản trễ: +5 → t−2, +35 → t−3, +90 → t−5):
- `kratie_dry_deficit_t2`: trung bình log(Q / trung vị cùng tháng của tối đa 15 năm trước) từ tháng 11 đến tháng neo. Để trống (điền trung vị) khi tháng neo ngoài XI–VI.
- `kratie_wet_ratio_last`: Q trung bình VII–X của mùa lũ có tháng 10 không muộn hơn tháng neo, so với trung vị 15 năm trước.
- `oni_t4`: ONI NOAA PSL gán theo tháng giữa của trung bình 3 tháng, nên dùng ONI tâm tháng mục tiêu −4 (cần SST đến tháng −3). Không có bản phát hành theo thời điểm, nên luôn chạy kèm phiên bản **bỏ ONI** (`NoONI`).

**Giao thức:** khóa EC như `evaluate_frozen_ec_gap_remedies.py` (3 kỳ). Mỗi nguồn có kịch bản trễ riêng: EC {+5, +35}, khí tượng {+5, +35}, Kratie/Tân Châu {+5, +35, +90}, tổng 12 tổ hợp. Mã kiểm mọi đầu vào của tháng dự báo đã có tại ngày phát hành, và ở tổ hợp +5/+5/+5 các cột khí tượng/thủy văn khớp đúng ma trận đã công bố. Đối chứng `WeatherHydrology` ở +5/+5/+5 tái tạo đúng 57,81/133,82; 16,57/31,21; 12,19/25,43. Manifest băm 48 tệp: nhãn EC, ONI, mọi tệp ERA5 và manifest khí tượng, Kratie, các chuỗi mực nước trong ma trận, và 9 tệp mã phụ thuộc. Mã: `scripts/experiment_ec_peak_risk_20261112.py` (protocol `FROZEN_EC_PEAK_RISK_RESEARCH_V2`). Kết quả: `outputs/ec_peak_risk_20261112/`.

**Hồi quy độ lớn, MAE/RMSE mS/m (số tháng EC≥100 bị dự báo <100).** Khí tượng trễ bằng EC; các tổ hợp khác trong `metrics.csv`:

| EC / thủy văn | Mô hình | 2019–2021 | 2021–2023 | 2022–2023 |
|---|---|---|---|---|
| +5 / +5 | WeatherHydrology | 57,81/133,82 (2) | 16,57/31,21 (1) | 12,19/25,43 (0) |
| | + mùa | 59,62/142,36 (2) | 15,68/30,78 (2) | 9,72/19,75 (0) |
| | + mùa, bỏ ONI | 57,32/134,00 (2) | 15,81/30,89 (2) | 9,90/20,82 (0) |
| +5 / +35 | WeatherHydrology | 65,67/140,83 (2) | 24,61/56,30 (2) | 13,58/29,33 (0) |
| | + mùa | 63,99/142,95 (2) | 20,95/41,44 (2) | 12,54/21,83 (0) |
| +5 / +90 | WeatherHydrology | 69,67/148,83 (2) | 23,88/46,91 (2) | 19,89/42,60 (0) |
| | + mùa | 71,82/158,95 (**3**) | 21,37/40,41 (2) | 15,99/29,31 (0) |
| +35 / +35 | WeatherHydrology | 70,13/162,28 (3) | 20,86/44,11 (2) | 9,06/15,57 (0) |
| | + mùa | 71,43/167,69 (**5**) | 19,95/44,21 (2) | 8,92/15,21 (0) |
| | + mùa, bỏ ONI | 69,02/156,75 (3) | 20,64/42,95 (2) | 9,14/15,40 (0) |

**Đọc kết quả:**
- Câu "+35 tương tự" trong bản trước **chỉ đổi độ trễ nhãn EC**, đặc trưng thủy văn vẫn lấy t−2, nên không phải kiểm thử Kratie +35. Bản này đã sửa.
- Khi thủy văn trễ hơn +5, **cả cấu hình mô hình chính** xấu đi rõ (ví dụ 2021–2023 MAE 16,57 → 24,61 ở +35). Kịch bản +35 buộc dùng tháng thủy văn cũ hơn (t−3 thay vì t−2), nên con số này đo ảnh hưởng của việc mất một tháng thông tin; nó **không** đo sai khác giữa hai phiên bản số liệu MRC công bố ở hai thời điểm, vì dự án không có bản phát hành cũ. Điểm số đã công bố của mô hình chính phụ thuộc mạnh vào giả định +5 chưa được chứng minh. Phát hiện này quan trọng hơn bản thân đặc trưng mùa.
- Đặc trưng mùa giúp kỳ 2022–2023 và một phần 2021–2023 ở nhiều kịch bản, nhưng ở kỳ khó 2019–2021 thường xấu hơn và **tăng bỏ sót** (5 tháng ở +35/+35). Bỏ ONI không đổi kết luận. **Không đạt tiêu chí**; không triển khai.

**Xác suất EC ≥ 150 mS/m** (mốc WATCH tham khảo trong `data-contracts.md`, không phải ngưỡng vận hành cống). Kịch bản +5/+5/+5; Brier thấp hơn tốt hơn; trúng/báo sai ở xác suất 0,5:

| Kỳ (số tháng vượt 150) | Khí hậu tháng | Logit theo mùa | RF phân loại |
|---|---|---|---|
| 2019–2021 (6) | 0,122; trúng 0 | 0,121; trúng 6, báo sai 6 | **0,072**; trúng 3, báo sai 1 |
| 2021–2023 (2) | **0,043**; trúng 0 | 0,089; trúng 2, báo sai 6 | 0,051; trúng 1, báo sai 1 |
| 2022–2023 (0) | **0,014** | 0,136; báo sai 6 | 0,058; báo sai 3 |

Qua 12 tổ hợp trễ, RF phân loại có Brier thấp hơn khí hậu tháng ở **12/12** tổ hợp của kỳ 2019–2021 nhưng **0/12** ở hai kỳ còn lại: chỉ có ích ở năm cực đoan, báo sai ở năm bình thường.

**Nhận xét:**
- Có tín hiệu vật lý: thiếu hụt Kratie đầu mùa khô 2020 thấp nhất cohort; RF phân loại đưa 03–05/2020 lên khoảng 0,5–0,7.
- 02/2020 (558 mS/m) chỉ có xác suất 0,08–0,35 và dự báo độ lớn 26–140 tùy kịch bản. Chưa cách nào bắt được tháng này.
- Với 26 tháng ≥150 trong 463 mẫu (17 năm có sự kiện), bài toán phân loại thiếu dữ liệu sự kiện.

**Hướng còn lại, chỉ chấm khi có EC mới chưa dùng để chọn:**
1. Dự báo theo mùa (một xác suất cho II–IV) như Apel 2020.
2. Khoảng dự báo bằng conformal thích ứng (ACI/AgACI, [Zaffran và cộng sự 2022](https://proceedings.mlr.press/v162/zaffran22a/zaffran22a.pdf)), báo độ phủ riêng mùa khô và EC≥100.
3. Xu hướng năm do đáy sông hạ thấp ([Eslami và cộng sự 2019](https://doi.org/10.1038/s41598-019-55018-9)).
4. Khóa trước tiêu chí: không xấu đi ở cả ba kỳ **và mọi kịch bản trễ**, bỏ sót EC≥100 không tăng, Brier thấp hơn khí hậu tháng.

## 4. Màu EC trong kênh và sau cống

**Không có nguồn mở nào** công bố trạng thái cống hay EC trong kênh dưới dạng chuỗi thời gian có dấu giờ:
- Trạng thái cống chỉ có trong tin tức (ví dụ [Ban PCTT Tiền Giang](https://phongchongthientaitiengiang.vn/?p=6793): Xuân Hòa lấy nước gạn, Bảo Định và Xoài Hột lấy nước, Gò Cát đóng).
- Điểm đo trong hệ thống Bảo Định (cầu Xoài Hột, cầu Kênh Xáng) chỉ có giá trị đỉnh ngày trên báo.
- Ứng dụng SIWRR (Mekong SCADA, "Thủy Lợi ĐBSCL V2") không có API công khai. DHI và Văn phòng Ủy ban sông Mê Công Việt Nam đang xây nền tảng chia sẻ dữ liệu mặn 01/2026–01/2027 ([UNEP-DHI](https://unepdhi.org/strengthening-salinity-intrusion-data-sharing-and-forecasting-for-adaptation-to-climate-change-impacts-in-the-mekong-delta-of-viet-nam/)); đáng theo dõi.

**Hiển thị trung thực hiện nay (đã có, giữ nguyên):** nội suy dọc sông có nhãn, chấm cống theo EC ngoài cống, đoạn sau cống trống.

**Có thể thêm mà không bịa số:** lớp điểm "bản tin chính thức" nhập tay, mỗi điểm có ngày, URL, trạng thái cống được công bố và độ mặn đỉnh g/L; hiển thị như điểm đo, không tô kênh.

**Mức tối thiểu để tô một hệ thống (đề xuất Bảo Định):**
1. Nhật ký trạng thái cống có dấu thời gian, ít nhất theo ngày.
2. Hai cảm biến EC trong kênh và một ngoài cống, theo giờ, qua một mùa khô.
3. Mặt cắt kênh chính và kích thước cống (từ SIWRP/SIWRR).
4. Mô hình HEC-RAS 1D có mô-đun chất lượng nước (miễn phí), như nghiên cứu [Cổ Chiên–Hậu 2023](https://doi.org/10.3390/cli11030066): hiệu chuẩn một mùa, kiểm định mùa khác; chỉ tô đoạn đã hiệu chuẩn, nhãn "mô phỏng", kèm dải bất định.

Thiếu mục 1 và 2 thì mọi màu trong kênh đều là bịa.

## 5. Ngưỡng tham khảo theo cây trồng (chỉ để giải thích, không đổi mức màu)

- Lúa: MRC dùng < 200 mS/m không giảm năng suất, 200–480 giảm 10–50%, > 480 hạn chế ([MRC Tech Note](https://archive.iwlearn.org/mrcmekong.org/download/programmes/bdp/Tech-Note4-Environment-Assessment-Feb10-Part3.pdf)).
- FAO (Ayers & Westcot, *Water quality for agriculture*, Bảng 4, [mục lục](https://www.fao.org/4/t0234e/t0234e00.htm); bảng tái bản trong [FAO Irrigation Manual Module 4, Bảng 28](https://openknowledge.fao.org/server/api/core/bitstreams/e7d053e8-9c16-4ceb-80d5-990865b794c6/content)): lúa nước (*rice, paddy*) ECe 3,0 dS/m của **dịch chiết đất bão hòa vùng rễ** ứng với 100% năng suất tiềm năng; ECw tương đương của **nước tưới** là 2,0 dS/m (200 mS/m). Mức 90%: ECe 3,8 / ECw 2,6; 50%: ECe 7,2 / ECw 4,8 dS/m. ECw được suy từ ECe theo ECe ≈ 1,5 ECw, giả định tỷ lệ rửa mặn 15–20% và tưới mặt thông thường. Bảng không phân giống lúa; FAO ghi độ chịu mặn thay đổi theo giai đoạn sinh trưởng, giống và khí hậu. Ruộng lúa ngập liên tục không khớp giả định rửa mặn này, nên ECw 2,0 dS/m chỉ là tham khảo, không phải ngưỡng cho giống lúa địa phương.
- Tưới chung theo MRC: < 70 / 70–300 / > 300 mS/m.
- Sầu riêng khoảng 0,64 g/L; Viện Cây ăn quả miền Nam khuyến cáo < 1‰.
- QCVN 39:2011/BTNMT là quy chuẩn chất lượng nước tưới (chất rắn hòa tan 2000 mg/L, clorua 350 mg/L), **không** phải quy tắc mở cống. Không tìm thấy quyết định quốc gia cố định độ mặn mở cống; Đồng Tháp dùng 0,25 g/L tại công viên Lạc Hồng làm mốc kích hoạt giếng dự phòng ([Báo Đồng Tháp](https://baodongthap.vn/dong-thap-xay-dung-kich-ban-ung-pho-han-man-mua-kho-voi-muc-do-cao-nhat-a247055.html)).

## Việc chưa xác minh hoặc đã thử không được

- EC Mỹ Tho sau 2023 từ MRC (cổng dữ liệu, báo cáo 2024): **đã thử, không tìm thấy**.
- Dữ liệu cống/kênh từ SIWRR, Văn phòng Ủy ban sông Mê Công Việt Nam, công ty thủy lợi tỉnh: **đã thử, không được cấp**.
- Lịch công bố và chính sách hiệu chỉnh số liệu Kratie/Tân Châu của MRC; ngày EC MRC lên cổng dữ liệu: chưa có.
- Quy tắc đối chiếu g/L đỉnh triều với EC mẫu tháng: chưa có số đo cùng vị trí, cùng thời gian để hiệu chuẩn.
- Văn bản pháp lý Việt Nam quy định phương pháp quy đổi EC và độ mặn: chưa kiểm chứng, không viện dẫn.
- Ngưỡng EC nước tưới theo giống lúa, cây trồng và giai đoạn sinh trưởng ở địa phương: chưa có nguồn chuyên môn trong nước.
