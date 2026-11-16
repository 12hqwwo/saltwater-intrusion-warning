# Ngân hàng câu hỏi hội đồng — WebGIS EC Đồng Tháp

**Cách dùng:** mỗi câu có *gợi ý trả lời* ngắn, đúng với mã và số liệu ngày 13/11/2026 (xem `01_he_thong_kien_thuc.md`). Câu đánh dấu **[Khó]** là câu dễ bị “bẫy”. Khi không chắc, trả lời theo cấu trúc: *điều đã làm → bằng chứng (file/số) → giới hạn → hướng tiếp*.

---

## 1. Tổng quan, mục tiêu, phạm vi

1. **Đề tài giải quyết vấn đề gì?** Trực quan hóa và dự báo EC theo tháng tại trạm sông Tiền (trọng tâm Mỹ Tho), nội suy dọc sông, hỗ trợ rà soát điều kiện lấy nước tại cống. Không phát lệnh cống.
2. **Ai là người dùng?** Cán bộ thủy lợi/nông nghiệp cần bối cảnh mặn và công cụ kiểm tra hồ sơ; nhà nghiên cứu cần tra nguồn và đánh giá mô hình.
3. **Tại sao chọn Mỹ Tho làm trọng tâm?** Hạ lưu, EC biến động mạnh, có chuỗi MRC dài 1985–2023; Tân Châu và Mỹ Thuận gần như luôn ngọt.
4. **Đóng góp chính của em là gì?** Chuỗi dữ liệu có truy nguồn → CSDL PostGIS có ràng buộc → mô hình RF khí tượng + thủy văn đánh giá theo giao thức khóa EC → bản đồ nội suy có nhãn ngữ nghĩa rõ → quy tắc rà soát cống tách dự báo khỏi số đo.
5. **Phạm vi không làm?** Mô hình thủy lực, dự báo ngày/giờ, điều khiển cống, độ mặn đo trực tiếp.
6. **Sản phẩm có dùng vận hành được chưa?** Chưa. `deployment_ready=false`, `gate_decision_eligible=false`; chưa kiểm định mù.
7. **[Khó] Nếu không dùng được để vận hành thì giá trị thực tiễn ở đâu?** Bối cảnh xu thế, sàng lọc không gian, chuẩn hóa hồ sơ kiểm tra, hạ tầng sẵn sàng tự chấm điểm khi có EC mới.
8. **Đề tài khác gì các bản tin dự báo mặn hiện có?** Bản tin thường dùng mô hình thủy lực và số đo hiện trường của cơ quan chuyên trách; đề tài này là mô hình dữ liệu theo tháng, minh bạch nguồn và giới hạn, mở mã.
9. **Tại sao dự báo theo tháng mà không theo ngày?** Nhãn MRC là 1 mẫu/tháng; tạo nhãn ngày từ tháng là bịa dữ liệu (quy tắc dự án cấm).
10. **Đồng Tháp “mới” gồm những gì?** Sau sáp nhập (hiệu lực 01/07/2025) gồm Đồng Tháp cũ và Tiền Giang cũ; ranh giới 1 tỉnh + 102 xã/phường.

## 2. Kiến thức chuyên ngành về mặn và EC

11. **EC là gì? Đơn vị?** Độ dẫn điện của nước, mS/m. 1 dS/m = 100 mS/m = 1000 µS/cm.
12. **Quan hệ EC và độ mặn?** Gần tuyến tính ở dải hẹp, phụ thuộc nhiệt độ và thành phần ion; chuẩn là PSS-78. Dự án chỉ dùng `g/L ≈ 0,0064 × EC` để hiển thị.
13. **[Khó] Hệ số 0,0064 lấy từ đâu? Có đúng không?** Là quy đổi kinh nghiệm thường dùng (≈ 0,64 × EC dS/m ra g/L). Không hiệu chuẩn cho sông Tiền; vì vậy màu cảnh báo tính theo EC, và pipeline mô hình không dùng hệ số này.
14. **Có bù nhiệt độ cho EC không?** Nguồn không ghi rõ; cột `ec_temperature_basis = UNKNOWN`. Thừa nhận là giới hạn.
15. **Cơ chế xâm nhập mặn?** Triều đẩy mặn vào; lưu lượng ngọt thượng nguồn đẩy ra; mùa khô Q thấp → ranh mặn vào sâu.
16. **Tại sao Kratie quan trọng?** Kratie đo lưu lượng dòng chính Mekong trước khi phân lưu vào ĐBSCL; Q thấp → mặn vào sâu. Độ quan trọng nhóm Kratie ~0,48.
17. **Tại sao lại là mưa quan trọng nhất (0,341)?** Mưa tại chỗ là tín hiệu mùa rất mạnh (mưa nhiều ↔ mùa lũ ↔ EC thấp); RF dùng nó để tách mùa. Không có nghĩa mưa tại chỗ là nguyên nhân chính.
18. **Tại sao dùng mực nước Tân Châu?** Đại diện năng lượng dòng ngọt vào sông Tiền tại Việt Nam.
19. **Tại sao không dùng triều?** Đã thử FES theo cửa sổ: cải thiện nhẹ 2021–23 (16,57 → 15,59), không giúp 2019–21, đỉnh 03/2020 vẫn chỉ 229,86; FES2022b phát hành sau thời điểm hồi cứu và không biết giờ lấy mẫu.
20. **ENSO ảnh hưởng thế nào?** El Niño thường gây khô hạn → mặn nặng (2015–16, 2019–20). Đã thử ONI t−4; không ổn định qua các kỳ.
21. **Mùa khô ở đây là tháng nào?** Trong bản đồ: 12–4. Trong thử nghiệm conformal: 12–5.
22. **Ngưỡng nào là nguy hiểm cho lúa? Cây ăn trái?** Tham chiếu FAO lúa ECw 2,0 dS/m (200 mS/m); MRC lúa < 200 / 200–480 / > 480. Sầu riêng nhạy hơn nhiều; cặp 50/80 trên trang chỉ là minh họa.
23. **QCVN 39:2011 có dùng không?** Là chuẩn chất lượng nước tưới; được ghi nhận là tham chiếu, không dùng làm luật mở cống.
24. **[Khó] Ngưỡng 156,25 mS/m trong hồ sơ cống từ đâu?** = 1 g/L ÷ 0,0064. Đó là ngưỡng kỹ thuật cấu hình được (RuleProfile), không phải quy chuẩn pháp lý.

## 3. Thu thập dữ liệu

25. **Nguồn EC lấy ở đâu?** MRC; tệp Mỹ Tho/Tân Châu có biên nhận yêu cầu dữ liệu và giấy phép sử dụng trong `data/raw/ec/mrc/`. Mỹ Thuận từ MRC public API.
26. **Có bao nhiêu mẫu?** Mỹ Tho 463 (06/1985–12/2023), Tân Châu 464, Mỹ Thuận 451; RIA2 50.
27. **Tại sao dữ liệu dừng 2023?** Nguồn MRC dừng ở 15/12/2023; đã tìm thêm MRC, SIWRR, sở ngành nhưng chưa có EC Mỹ Tho sau đó.
28. **Khí tượng lấy ở đâu? Tại sao ERA5?** ERA5 qua Open-Meteo archive (CC-BY-4.0): chuỗi dài, đồng nhất, miễn phí từ 1985.
29. **[Khó] ERA5 là tái phân tích, có độ trễ — dùng như vậy có rò rỉ không?** Có rủi ro: dùng ERA5 hoàn chỉnh như thể có sẵn tại ngày phát hành. Đã ghi là giả định; cần dữ liệu “vintage” hoặc dự báo khí tượng thật để đánh giá công bằng.
30. **Lưu lượng Kratie lấy thế nào?** MRC API `timeSeriesList`, trạm 014901, 22.161 bản ghi ngày 1985–10/2026.
31. **RIA2 là gì? Sao không dùng?** Bản tin quan trắc môi trường nuôi trồng 2025; đơn vị µS/cm, CRS không ghi, 5 mẫu/điểm → chỉ tham khảo.
32. **Tọa độ trạm lấy từ đâu?** KML MRC, EPSG:4326 (Tân Châu 105,2480164 E, 10,80062008 N; Mỹ Tho 106,3529997 E, 10,35912163 N).
33. **Tọa độ cống lấy từ đâu?** Danh mục cống của tỉnh (PDF) + số hóa; 15 dòng kiểm kê, 12 có tọa độ; 3 cống chưa có tọa độ tin cậy.
34. **GloFAS, DAHITI có dùng không?** Không trong mô hình chính. GloFAS hiện là trung bình bbox (nợ kỹ thuật); DAHITI là đo cao vệ tinh không đều, không phải triều, không có datum.
35. **Làm sao chứng minh dữ liệu không bị sửa?** SHA-256 của từng tệp trong manifest; builder kiểm hash trước khi dùng.
36. **Bản quyền dữ liệu?** MRC có giấy phép sử dụng kèm; ERA5/Open-Meteo CC-BY-4.0; OSM ODbL (ghi trên bản đồ); một số nguồn Kratie ghi “verify reuse terms before redistribution”.

## 4. Xử lý dữ liệu

37. **Nhãn tháng là trung bình hay mẫu đơn?** Mẫu đơn; builder báo lỗi nếu tháng có > 1 mẫu.
38. **[Khó] Một mẫu trong tháng có đại diện cho tháng không?** Không hoàn toàn: phụ thuộc ngày, giờ, pha triều. Mô hình dự báo “EC của mẫu tháng”, không phải EC trung bình tháng — phải nói rõ khi diễn giải.
39. **Xử lý ngoại lai thế nào?** Không xóa. Gắn cờ `HIGH_VS_CALENDAR_MEDIAN_REVIEW_ONLY` (41/927 dòng EC ≥ 3× trung vị cùng tháng lịch) chỉ để rà soát.
40. **[Khó] Tại sao không loại 692 mS/m? Có thể là lỗi?** Chủ dự án đã xác nhận đúng; 03–04/2020 là đợt hạn mặn lịch sử, mẫu 02/04/2020 cũng cao (558, 607). Loại đỉnh sẽ làm mô hình đẹp giả.
41. **ETL v2 gắn 117 dòng SUSPECT, sao vẫn học trên tất cả?** Cờ dựa IQR/bước nhảy sẽ trúng đúng các đỉnh thật. Hai chính sách đang cùng tồn tại — thừa nhận cần thống nhất.
42. **Tổng hợp thủy văn ngày → tháng thế nào?** Q trung bình ngày; mực nước trung vị của trung vị ngày; tháng hợp lệ khi ≥ 20 ngày.
43. **Tại sao trung vị cho mực nước?** Bền với ngoại lai/ghi sai thủ công.
44. **Tỷ lệ Q cùng mùa tính thế nào? Có rò rỉ không?** Q t−2 chia trung vị Q cùng tháng lịch của tối đa 15 năm **trước**; cắt [0, 5]. Chỉ dùng quá khứ nên không rò rỉ.
45. **Thiếu dữ liệu xử lý thế nào?** Đặc trưng thiếu (57 tháng tỷ lệ Q, 12 tháng mực nước khi học) → imputer trung vị fit trong tập huấn luyện. Khi dự báo trên web, thiếu thủy văn → từ chối (422), không điền 0.
46. **Tháng thiếu trên bản đồ?** Nội suy thời gian giữa hai tháng nguồn hoặc giá trị mép chuỗi; gắn cờ `imputed`.
47. **Múi giờ?** Nguồn UTC+7; DB lưu `timestamptz`, phiên đặt Asia/Ho_Chi_Minh.

## 5. Cơ sở dữ liệu và GIS

48. **Tại sao PostgreSQL/PostGIS?** Quan hệ, ACID, ràng buộc, kiểu không gian, chỉ mục GiST, hàm `ST_*`, miễn phí.
49. **Kể các bảng chính.** `source_dataset`, `measurement_site`, `conductivity_observation`, `monthly_feature`, `irrigation_gate`, `admin_boundary`; schema `dss_reference` (ngưỡng, nhật ký dự báo, nháp cống); `webgis_security.audit_log`.
50. **Ràng buộc nào bảo vệ dữ liệu EC?** CHECK đơn vị `mS/m`, giá trị ≥ 0 hữu hạn, O/E, cờ chất lượng; UNIQUE (dataset, site, observed_at) và (dataset, source_row); dataset khóa bằng SHA-256.
51. **SRID nào? Tại sao?** 4326 (WGS84), thống nhất với KML/GeoJSON. Khoảng cách tính bằng `::geography` để ra mét.
52. **[Khó] Tính khoảng cách trạm–cống bằng gì? Có ý nghĩa thủy lực không?** `ST_DWithin` trên geography (mặc định 50 km). Chỉ là đường chim bay; không chứng minh liên thông thủy lực.
53. **Chỉ mục không gian?** GiST trên mọi cột geometry.
54. **ETL đảm bảo idempotent thế nào?** Dataset khóa SHA-256 UNIQUE; UNIQUE dòng; có lỗi là không ghi gì (`REJECTED_NO_DATABASE_WRITE`).
55. **Migration áp dụng thế nào?** File SQL có kiểm `current_database()`, mặc định ROLLBACK/xem trước; DSS dùng `scripts/apply_dss_storage.py` với advisory lock và bảng checksum.
56. **Phân quyền?** `webgis_reader` chỉ đọc; `webgis_writer` chỉ INSERT vào 2 bảng nhật ký DSS; không superuser; timeout câu lệnh 10 s.
57. **Chống SQL injection?** Truy vấn tham số hóa; tài khoản chỉ đọc; giới hạn `limit`.
58. **Nhật ký kiểm toán?** Trigger `SECURITY DEFINER` sau INSERT ghi `webgis_security.audit_log`.
59. **[Khó] 3 cống chưa tọa độ xử lý ra sao?** Quy tắc dự án: không gán tâm giả; SQL cũ còn placeholder và được ghi là nợ kỹ thuật chưa hoàn tất.
60. **Ranh giới hành chính kiểm tra hình học thế nào?** `ST_MakeValid`, `ST_CollectionExtract`, `ST_Multi`; kiểm `ST_IsValid`, `ST_IsEmpty`, SRID, loại hình học, số lượng.
61. **Có sao lưu DB không?** Chưa cấu hình cho triển khai; là giới hạn ghi trong `docs/database-security.md`.
62. **Tại sao có cả snapshot?** Tái lập và demo ngoại tuyến; có manifest + SHA-256; không tự thay khi DB lỗi.

## 6. Mô hình học máy

63. **Tại sao chọn Random Forest?** Ít mẫu (463), quan hệ phi tuyến, ít giả định phân phối, ổn định, có độ quan trọng biến, phân tán giữa cây để mô tả bất định.
64. **Giải thích RF.** Nhiều cây học trên mẫu bootstrap, mỗi nút xét tập con đặc trưng ngẫu nhiên; dự báo là trung bình → giảm phương sai.
65. **Siêu tham số? Chọn thế nào?** 300 cây, sâu 8, lá ≥ 3, seed 42. Kế thừa từ RF khí tượng và giữ cố định khi so các tập đặc trưng; chọn phương án sau khi xem các kỳ hồi cứu (ghi trong manifest).
66. **[Khó] Có tinh chỉnh siêu tham số trên tập kiểm tra không?** Không có grid search trên kỳ chấm; nhưng việc **chọn phương án** đã xem các kỳ này → đó là lý do gọi là hồi cứu, không phải kiểm định mù.
67. **Tại sao lại t−2?** Để đảm bảo dữ liệu đã công bố tại ngày phát hành (giả định cuối tháng + 5 ngày).
68. **Liệt kê 10 đặc trưng.** Mưa, nhiệt, gió, sin tháng, cos tháng, Q Kratie t−2, Q 3 tháng, tỷ lệ Q cùng mùa, mực nước Tân Châu t−2, trung vị mực nước 3 tháng.
69. **Tại sao mã hóa tháng bằng sin/cos?** Giữ tính tuần hoàn: tháng 12 gần tháng 1.
70. **Feature importance tính thế nào? Có tin được không?** Mức giảm impurity trung bình; thiên vị biến liên tục, không nói nhân quả. Nên bổ sung permutation importance/SHAP.
71. **[Khó] Tại sao RF hụt đỉnh 692?** RF lấy trung bình nhãn trong lá, không ngoại suy; chỉ 26/463 tháng ≥ 150 nên lá chứa đỉnh bị pha mẫu thấp.
72. **Tại sao không dùng LSTM/deep learning?** 463 mẫu tháng quá ít; nguy cơ quá khớp cao; khó giải thích.
73. **Đã thử XGBoost/LightGBM chưa?** Có. XGB log đạt 9,74 ở 2022–23 nhưng dự báo đỉnh chỉ 378–379; không ổn định → loại.
74. **SARIMA/SARIMAX?** Có trong kế hoạch so sánh; `run_forecast.py` import nhưng chưa chạy; `pipelines/models/14_model_baseline.py` có khung so sánh. Nên thừa nhận chưa có kết quả SARIMAX trong bảng chính.
75. **Tại sao không dùng EC tháng trước làm đặc trưng?** Thực tế không có EC mới sau 2023; mô hình cần chạy được khi EC ngừng cập nhật. Có EC quá khứ thì điểm tốt hơn (56,98/12,00) nhưng không dùng được trong tình huống thật.
76. **Mô hình Tân Châu, Mỹ Thuận có tốt không?** Không thắng seasonal naive (2,38 và 1,89 vs RF 4,45 và 3,92). Dùng để có mốc nội suy cho tháng tương lai; cần cải thiện.
77. **[Khó] Vậy sao không dùng seasonal naive cho hai trạm đó?** Hợp lý — là cải tiến nên làm; seasonal naive cần EC năm trước, vốn không có sau 2023 → trong tình huống mất EC dài hạn cũng không áp dụng trực tiếp được.
78. **Mô hình lưu thế nào? Đảm bảo đúng phiên bản?** `model.joblib` + `manifest.json`; registry lưu SHA-256; backend kiểm hash, thứ tự đặc trưng, phiên bản scikit-learn mỗi lần dự báo.
79. **[Khó] Joblib/pickle có rủi ro bảo mật không?** Có (giải tuần tự hóa chạy mã). Giảm rủi ro bằng kiểm SHA-256 trước khi nạp và chỉ nạp từ đường dẫn registry trong repo.
80. **P10–P90 là gì?** Phân vị dự báo của 300 cây; mô tả phân tán, không phải khoảng tin cậy hiệu chuẩn.
81. **Có tính khoảng dự báo hiệu chuẩn chưa?** Đang thử conformal (12/11): phủ 30–31/36 ở 2019–21, 22–23/24 ở 2022–23 với mục tiêu 90%; trượt 02 và 03/2020. Chưa triển khai.
82. **Tại sao không huấn luyện lại khi người dùng bấm dự báo?** Để tái lập, nhanh, kiểm soát phiên bản; không có nhãn mới nên huấn luyện lại không thêm thông tin.
83. **Dự báo xa nhất bao nhiêu tháng?** Với t−2 thật thì một bước 2 tháng; các tháng xa hơn trên bản đồ là kịch bản trung vị cùng tháng 2010–2023.

## 7. Đánh giá mô hình

84. **MAE, RMSE là gì? Khác nhau?** MAE trung bình |sai số|; RMSE căn trung bình bình phương, phạt lỗi lớn. RMSE ≫ MAE → có lỗi lớn lẻ tẻ.
85. **Tại sao không dùng R² hay MAPE?** MAPE vô nghĩa khi EC nhỏ; R² nhạy phân phối lệch. Có thể bổ sung, nhưng MAE/RMSE theo mS/m dễ diễn giải.
86. **Giao thức khóa EC là gì?** Fit một lần trước đoạn mất EC 24/36 tháng; đầu vào t−2 cập nhật; EC trong đoạn chỉ dùng chấm.
87. **Rolling origin là gì?** Mỗi tháng phát hành lại, học trên dữ liệu đã khả dụng tại ngày phát hành.
88. **[Khó] Sao có hai giao thức với hai bảng điểm khác nhau?** Trả lời hai câu hỏi khác nhau: có EC cập nhật hay không. Không trộn bảng.
89. **Kết quả chính?** 57,81/133,82 (2019–21), 16,57/31,21 (2021–23), 12,19/25,43 (2022–23).
90. **[Khó] Kỳ 2022–23 persistence thắng — vậy mô hình có ích gì?** Đúng: 10,76/16,46. Kỳ đó EC ổn định, ít đỉnh; giữ EC cuối tự nhiên mạnh. Ở kỳ khó 2019–21, RF tốt hơn rõ (57,81 vs 80,20 MAE). Mô hình có ích nhất khi điều kiện thay đổi so với lần đo cuối.
91. **Các kỳ chồng lấn có vấn đề gì?** Không độc lập; không cộng gộp như ba bằng chứng riêng.
92. **[Khó] Vậy đây có phải kiểm định độc lập không?** Không. Hồi cứu, đã xem khi chọn. Cần EC sau 2023 chưa dùng để chọn.
93. **Baseline gồm những gì?** Giữ EC cuối, trung bình từng tháng trước khi mất dữ liệu, lặp EC gần nhất của từng tháng, RF chỉ chu kỳ tháng, RF khí tượng.
94. **[Khó] Persistence của em có rò rỉ không?** Đã từng phát hiện một báo cáo ngoài dùng persistence không lọc ngày khả dụng (52,19 sai vs 93,39 đúng). Bản hiện tại lọc theo ngày khả dụng +5/+35.
95. **Kiểm tra rò rỉ dữ liệu thế nào?** Cột issue/available cho từng dòng, kiểm tự động (0/240 vi phạm); tỷ lệ khí hậu chỉ dùng quá khứ; imputer fit trong fold; API chặn tháng trong kỳ huấn luyện; test Python về leakage.
96. **Độ nhạy với độ trễ công bố?** EC: RF_compact 2019–21 50,87 (0–6 ngày) → 56,67 (38–65 ngày). Thủy văn +35 ngày: mô hình chính 2021–23 tăng 16,57 → 24,61 (thử nghiệm 12/11).
97. **Mô hình bắt đỉnh tốt không?** Không. 03/2020 dự báo 213,67 vs 692; 02/2020 thử chuyển mạch chỉ 85,74 vs 558.
98. **Có đếm bỏ sót và báo cao giả không?** Có trong các thử nghiệm: đếm tháng EC ≥ 100 bị dự báo < 100; 04/2022 dự báo 100,04 vs 25,7 là báo cao giả.
99. **Tại sao không chia ngẫu nhiên train/test?** Rò rỉ thời gian và tự tương quan → điểm số lạc quan.
100. **Cross-validation thời gian dùng loại gì?** Expanding window (rolling origin) và khóa EC; chưa dùng blocked k-fold.
101. **Có kiểm định thống kê sự khác biệt giữa mô hình không?** Chưa (ví dụ Diebold–Mariano). Có thể bổ sung; với n = 24–36 sức mạnh kiểm định thấp.
102. **Đánh giá theo năm?** 2019–23 gộp: RF_compact 34,95, RF cũ 50,39, persistence 61,08; thắng 39/60 tháng (rolling origin).

## 8. Phương pháp giảm sai số

103. **Đã thử những gì?** Thêm thủy văn, EC trạm lân cận, Ridge, Ridge+RF phần dư, RF mịn, Huber GB, trọng số EC cao, thiếu hụt Q, FES triều, chuyển mạch Q thấp, RF log + smearing, thủy văn ngày, khoảng trên mùa khô, conformal, phân loại rủi ro đỉnh.
104. **Cái nào hiệu quả?** Thêm thủy văn (đã đưa vào mô hình chính). Các cái khác cải thiện một kỳ và làm xấu kỳ khác hoặc tăng bỏ sót.
105. **Tại sao thêm EC Mỹ Thuận không giúp?** 34 tháng Mỹ Tho ≥ 100 thì Mỹ Thuận chưa lần nào ≥ 100; Pearson 0,353. EC thượng lưu không mang tín hiệu đỉnh hạ lưu.
106. **Tăng trọng số mẫu đỉnh thì sao?** ×8: MAE tháng cao 259 → 234 nhưng 2022–23 xấu đi 11,07 → 14,25.
107. **Log-transform giúp gì?** Giảm lệch phải, nhưng đổi ngược làm chệch (cần smearing); kết quả không ổn định.
108. **Conformal prediction là gì?** Dựng khoảng từ phân phối sai số quá khứ với phủ danh nghĩa 1−α; ACI điều chỉnh trực tuyến cho chuỗi thời gian.
109. **Brier score là gì?** Trung bình (p − o)² cho dự báo xác suất; RF phân loại 0,072 vs khí hậu 0,122 ở 2019–21 nhưng thua 2 kỳ khác.
110. **[Khó] Thử nhiều như vậy có phải p-hacking/quá khớp lịch sử không?** Có nguy cơ — chính vì vậy dừng tinh chỉnh trên dữ liệu đã xem và không đổi mô hình chính chỉ vì một kỳ có MAE thấp hơn.
111. **Nếu có thêm 6 tháng, em làm gì?** Thu EC mới; xây `forecast_issue`/`forecast_score` để tự chấm; lịch công bố thật; leave-one-station-out; hiệu chuẩn khoảng dự báo trên tập thời gian tách biệt.

## 9. Nội suy và bản đồ

112. **Phương pháp nội suy?** Tuyến tính từng chặng theo lý trình trên trục 175 km, mốc 0 / 85,2 / 125 / 175 km.
113. **[Khó] Tại sao tuyến tính? EC thật dọc sông không tuyến tính.** Chỉ có 3 điểm đo; không đủ để hiệu chuẩn dạng phức tạp hơn. Đúng là xâm nhập mặn thường suy giảm dạng hàm mũ từ cửa sông — nói rõ là hình dung bối cảnh, không phải mô phỏng vật lý.
114. **Tại sao không dùng IDW hay Kriging?** Đó là nội suy 2D theo khoảng cách Euclid, bỏ qua cấu trúc mạng sông; 3 điểm không đủ cho variogram.
115. **Biên cửa sông tính thế nào?** EC Mỹ Tho × 6 (mùa khô) hoặc × 1,5 + 0,4 × chênh Mỹ Tho − Tân Châu. Giả định chưa hiệu chuẩn.
116. **[Khó] Hệ số 6 và 1,5 từ đâu?** Lựa chọn kịch bản để phản ánh hướng gia tăng ra cửa sông; không có số đo cửa sông để hiệu chuẩn — phải nói thẳng.
117. **Khi thiếu Mỹ Thuận?** Fallback 2 trạm, chỉ cho tháng trước 2024; từ 2024 bắt buộc đủ 3 mốc.
118. **Tại sao đoạn sau cống không tô màu?** Không có EC nội kênh và không biết trạng thái cống; tô màu là bịa.
119. **Màu chấm cống nghĩa là gì?** Mức EC mô phỏng ngoài cống so với cặp ngưỡng đang chọn; không phải trạng thái đóng/mở.
120. **Vệt sáng trên sông là gì?** Minh họa hướng lan mặn/nước ngọt theo mùa và EC; không phải dòng chảy đo.
121. **Gió trên bản đồ lấy từ đâu? Có dùng cho mô hình không?** ERA5 tổng hợp tháng (vectơ vùng); tháng chưa có thì khí hậu cùng tháng 2010–2023. Không là đầu vào mô hình.
122. **Ranh mặn 1 g/L, 4 g/L tính thế nào?** Từ EC nội suy quy đổi 0,0064; vị trí cắt ngưỡng trên trục.
123. **Click một điểm trên bản đồ cho ra gì?** EC của đoạn sông lân cận, khoảng cách tới trục, cống/trạm gần nhất, cảnh báo nếu > 12 km — không phải số đo tại điểm.
124. **Tại sao nhãn trạm 2016 lại ghi mẫu 2023?** Nhãn là mẫu nguồn mới nhất của trạm; giá trị tháng đang xem nằm trên màu sông/tooltip.
125. **Trục sông lấy từ đâu?** OSM (ODbL), làm mượt, giữ mốc.
126. **Bản đồ dùng thư viện gì? Nền?** OpenLayers; nền sáng/tối/vệ tinh.

## 10. WebGIS, kiến trúc phần mềm, API

127. **Kiến trúc tổng thể?** FastAPI modular monolith (api/services/domain/repositories) + frontend Vite/OpenLayers build tĩnh, phục vụ cùng cổng 8000; PostgreSQL/PostGIS.
128. **Tại sao FastAPI?** Nhanh, kiểu dữ liệu Pydantic, tự sinh OpenAPI `/docs`, hợp hệ sinh thái Python khoa học.
129. **Tại sao không React/TypeScript như thiết kế mục tiêu?** Giữ Vite + JS thuần + OpenLayers để gọn; quy tắc dự án yêu cầu không trộn hai stack ngầm. Là quyết định có ghi nhận.
130. **Luồng một yêu cầu dự báo?** Frontend `/inputs` → `/predict` → service kiểm đầu vào → domain nạp model kiểm hash → trả EC, phân tán, metadata.
131. **Bảo mật API?** Cùng nguồn cho POST, `X-API-Key` tùy chọn (so sánh hằng thời gian), header bảo mật, TrustedHost, CORS hẹp, lỗi DB làm sạch, giới hạn kích thước body 256 KiB.
132. **[Khó] Tại sao máy chủ chạy lại dự báo khi lưu thay vì lưu kết quả trình duyệt gửi?** Không tin dữ liệu phía client; đảm bảo bản lưu đúng mô hình máy chủ.
133. **Có xác thực người dùng không?** Chưa (ứng dụng cục bộ). Triển khai thật cần reverse proxy, TLS, đăng nhập.
134. **Hiệu năng?** Model cache có kiểm hash; frame mô phỏng tính theo yêu cầu; truy vấn có `limit` và chỉ mục.
135. **Xử lý yêu cầu đến trễ (race condition) trên giao diện?** Hủy yêu cầu cũ; “tháng mới nhất thắng”; test `timeline_scrubber`, `observations_contract`.
136. **Truy cập (accessibility)?** Có liên kết “Đến nội dung”, nhãn ARIA, tôn trọng `prefers-reduced-motion`, nút tạm dừng hoạt ảnh.
137. **Responsive?** Có mật độ hạt riêng cho thiết bị di động; chưa kiểm thử đầy đủ.

## 11. Hồ sơ cống và hỗ trợ quyết định

138. **Phần A và Phần B khác nhau?** A: xu thế dự báo chiếu về cống, chỉ điều chỉnh thời hạn mẫu. B: số đo hiện trường hai phía, quyết định kết luận.
139. **Các điều kiện kiểm tra?** Độ mới mẫu, EC ngoài ≤ 156,25, EC trong ≤ 125, cùng hệ cao độ, ΔH ≥ 0,05 m, cơ khí READY, có nguồn, phải là số đo thật.
140. **Tại sao cần cùng hệ cao độ?** Hai mực nước khác datum không trừ được; ΔH sai dẫn tới kết luận sai về chiều chảy.
141. **Tại sao thời hạn mẫu 6 giờ / 2 giờ?** Triều bán nhật ở hạ lưu làm EC đổi trong vài giờ; khi rủi ro cao cần mẫu mới hơn. Là tham số cấu hình được.
142. **P90 = 60,42 là gì?** Mốc tham chiếu mặc định: P90 EC của tập huấn luyện ban đầu thí nghiệm RF_compact (`high_ec_metrics`, bản +35 ngày là 60,6). Không phải P90 toàn chuỗi 463 mẫu (68,52). Cấu hình được trong RuleProfile.
143. **[Khó] Có rủi ro người dùng hiểu “Đề nghị xem xét lấy nước” là lệnh mở cống?** Đã giảm bằng: tên kết luận “xem xét”, `requiresOperatorReview`, `actuatorCommand: null`, câu “Người vận hành xem xét trước khi thao tác”. Vẫn cần quy trình của đơn vị quản lý.
144. **Quy tắc chạy ở client hay server?** Client (`gate-intake-rules.js`); endpoint `/gate-evaluation` cũ còn nhưng giao diện không gọi. Nháp có thể lưu qua `/gate-drafts` với kiểm tra phía máy chủ.
145. **Dự báo có tự điền vào phiếu đo không?** Không bao giờ; kiểm tra `FIELD_MEASUREMENT` thất bại nếu dữ liệu là mô phỏng.

## 12. Kiểm thử, tái lập, quy trình

146. **Kiểm thử những gì?** 156 test Node cho frontend (bản đồ, nội suy, quy tắc cống, timeline, hoạt ảnh) và các test Python (leakage, nạp model, bảo mật, frame mô phỏng, tích hợp 3 trạm).
147. **Làm sao người khác tái lập kết quả?** Manifest có tham số, hash nguồn, phiên bản thư viện; `predictions.csv` từng tháng; script nghiên cứu trong `scripts/`.
148. **Quản lý phiên bản?** Git; mô hình có version trong tên run và registry; không ghi đè artifact chính bằng thí nghiệm.
149. **[Khó] Nếu đổi scikit-learn phiên bản thì sao?** Backend kiểm phiên bản và từ chối nếu không khớp; cần đóng gói lại có version mới.

## 13. Câu hỏi “phản biện” và tình huống

150. **Nếu năm 2027 có hạn mặn như 2020, hệ thống báo trước được không?** Nhiều khả năng báo tăng nhưng thấp hơn thực tế nhiều (như 213,67 vs 692). Cần đọc cùng xu thế Q Kratie thấp và số đo hiện trường.
151. **Em tin mô hình đến mức nào?** Tin cho xu thế mùa và điều kiện bình thường (sai số ~12–17 mS/m ở kỳ ổn định); không tin cho đỉnh cực trị.
152. **Nếu hội đồng đưa EC thật 2024, em kiểm tra thế nào?** Khóa tiêu chí trước, chạy dự báo đã phát hành tương ứng, chấm MAE/RMSE, đếm bỏ sót/báo cao giả theo mùa, không chỉnh mô hình trước khi chấm.
153. **Điểm yếu lớn nhất của đề tài?** Không có kiểm định mù; mẫu đơn trong tháng; hụt đỉnh; giả định lịch công bố.
154. **Nếu làm lại từ đầu, em làm khác gì?** Ghi lịch công bố dữ liệu ngay từ đầu; thiết lập tập kiểm định giữ kín; thống nhất chính sách QA sớm; xây bảng phát hành dự báo bất biến.
155. **Tại sao kết quả đề tài đáng tin dù chưa kiểm định mù?** Không tuyên bố quá mức; mọi số truy được đến tệp, hash, giao thức; lỗi lớn được giữ và hiển thị.
156. **Mô hình có thể áp dụng cho sông Hậu không?** Về phương pháp có; cần EC trạm sông Hậu, huấn luyện lại, đánh giá riêng.
157. **Biến đổi khí hậu, đập thủy điện thượng nguồn ảnh hưởng thế nào đến mô hình?** Thay đổi chế độ dòng chảy → phân phối dữ liệu dịch chuyển (non-stationarity); mô hình học 1985–2023 có thể lệch. Biến tỷ lệ Q so với 15 năm trước giúp một phần thích nghi.
158. **Sụt lún và khai thác cát?** Ảnh hưởng đến địa hình lòng sông và mặn; mô hình không có biến này — giới hạn.
159. **Chi phí triển khai?** Phần mềm mã mở; chi phí chính là dữ liệu đo và vận hành máy chủ.
160. **Em tự làm phần nào, AI hỗ trợ phần nào?** Trả lời trung thực theo thực tế làm việc của bạn; nhấn mạnh phần quyết định khoa học, xác nhận dữ liệu (692), chọn giao thức là của chủ dự án.

## 14. Câu hỏi nhanh kiểm tra trí nhớ (trả lời trong 1 câu)

161. Mấy tab? — 5.
162. Mô hình chính tên gì? — `20261108T_HYDROLOGY_PRIMARY_V1`.
163. Học đến tháng nào? — 12/2023, 463 mẫu.
164. Mốc Mỹ Thuận ở km? — 85,2.
165. Ngưỡng mặc định trên bản đồ? — Cây có múi 100/150.
166. Quy đổi g/L? — 0,0064 × EC.
167. Số đoạn sông? — 35 × 5 km.
168. Đỉnh lịch sử Mỹ Tho? — 841 mS/m, 04/1998.
169. Dự báo 03/2020? — 213,67 vs 692.
170. ΔH tối thiểu? — 0,05 m.
171. Thời hạn mẫu thường/cảnh giác? — 6 giờ / 2 giờ.
172. Tháng thủy văn hợp lệ? — ≥ 20 ngày.
173. Tài khoản đọc DB? — `webgis_reader`.
174. API sức khỏe DB? — `GET /api/v1/health`.
175. Test frontend? — 156/156 đạt (13/11/2026). Python 110/116 — 6 test/bằng chứng cũ lệch mã (đừng nói “tất cả đạt”).
