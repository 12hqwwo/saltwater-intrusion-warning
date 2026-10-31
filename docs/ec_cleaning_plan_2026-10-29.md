# Phương án làm sạch EC MRC

## Kết quả kiểm tra tệp gốc

Gói `mrc20260831193610.zip` được đọc trực tiếp, không sửa tệp gốc. Hai CSV của MRC có 927 phép đo EC, mỗi trạm đúng một phép đo mỗi tháng: Mỹ Tho 463 tháng (06/1985–12/2023), Tân Châu 464 tháng (05/1985–12/2023). Đối chiếu với `data/research/mrc_ec_monthly_samples.csv`: **927/927 tháng trùng giá trị và số mẫu**. Không có tháng trống, tháng trùng, giá trị âm hoặc không hữu hạn. Tất cả dùng mS/m và là phép đo quan trắc (`O`).

MRC tự ghi `Raw - Not Yet Reviewed` và `Unverified data` cho 927 bản ghi. Đây là tình trạng duyệt của nguồn, không phải lỗi nhập liệu. Vì vậy **không thay, cắt ngọn, nội suy hay xóa EC cao**. `ec_for_model_mS_m` trong bảng QC bằng đúng `ec_original_mS_m` cho mọi dòng.

Script `scripts/prepare_ec_qc.py` tạo `ec_qc_review.csv` và `ec_qc_summary.json` trong `outputs/multivariate_error_audit_20261029/`. Cờ `HIGH_VS_CALENDAR_MEDIAN_REVIEW_ONLY` được đặt khi EC ≥ 3 lần trung vị cùng tháng lịch của chính trạm. Có **41/927** dòng được gắn cờ, chủ yếu ở Mỹ Tho. Ngưỡng này chỉ dùng để chọn hồ sơ cần giải thích trong báo cáo; nó được tính hồi cứu từ toàn chuỗi, không dùng làm đặc trưng dự báo hay quy tắc loại nhãn. Tháng 02–05/2020 ở Mỹ Tho đều được gắn cờ và giữ nguyên.

## Tư liệu về những năm EC cao

Tin tức và báo cáo về hạn mặn cho biết **bối cảnh vùng/năm**, không xác nhận trực tiếp số EC lấy mẫu tại trạm. EC là độ dẫn điện mS/m; tư liệu thường báo độ mặn g/L hoặc ranh mặn theo km, nên không so số trực tiếp.

| Năm/đợt trong EC | Dữ liệu cần lưu ý | Bằng chứng bối cảnh | Kết luận QC |
| --- | --- | --- | --- |
| 1997–1998 | Mỹ Tho 04/1998: 841 mS/m; Tân Châu có hai tháng vượt 3 lần trung vị | [Bộ NN&PTNT](https://phongchongthientai.mard.gov.vn/en/Pages/assessment-causes-and-forecasts-of-drought-saltwater-intrusion-in-the-mekong-delta-from-expert-perspective.aspx) nêu mùa khô 1997–1998 là đợt hạn mặn nghiêm trọng; [tài liệu kế hoạch Việt Nam tại MRC](https://www.mrcmekong.org/?document_id=01YJPZCU4FXT2DUIA54VAJ7P4TSO7EA7CT&download_document=1&name=National-Indicative-Plan-for-Implementation-of-the-MRC-IWRM-Based-Basin-Development-Strategy-2011-2015-%28Viet-Nam%29.pdf) cũng nhắc năm 1998 xâm nhập mặn sâu. | Có bối cảnh phù hợp; không xác nhận riêng số 841. Giữ nguyên. |
| 2015–2016 | Mỹ Tho 01–03/2016 đều cao so với trung vị tháng lịch | [MRC, State of the Basin 2023](https://www.mrcmekong.org/publications/mekong-river-basin-2023-state-of-the-basin-report-2/) tổng hợp xâm nhập mặn sâu ở các năm 2016, 2020 và 2021. | Có bối cảnh vùng; giữ nguyên. |
| 2019–2020 | Mỹ Tho 02–05/2020: 558, 692, 607, 398 mS/m | [Báo Chính phủ đầu 2020](https://baochinhphu.vn/cac-dia-phuong-khan-cap-ung-pho-han-man-102268354.htm) ghi nhận Tiền Giang ứng phó mặn từ hệ thống sông Tiền; [MRC, State of the Basin 2023](https://www.mrcmekong.org/publications/mekong-river-basin-2023-state-of-the-basin-report-2/) xác định 2020 là năm xâm nhập mặn sâu trong những năm có dữ liệu. | Chuỗi cao liên tiếp và có bối cảnh phù hợp; giữ nguyên. |
| 2023 | Tân Châu 03–07/2023 cao hơn nhiều dự báo RF | [MRC ngày 04/04/2023](https://www.mrcmekong.org/media-releases/mrc-secretariat-chief-cites-progress-amid-troubling-trends-in-annual-address/2024/) cảnh báo xu thế xâm nhập mặn trong vùng, nhưng không xác nhận EC các tháng tại Tân Châu. | Không dùng tin vùng để kết luận nguyên nhân. Giữ nguyên. |

Chưa tìm thấy tư liệu có thể xác nhận **đúng trạm và ngày lấy mẫu** cho các giá trị cao năm 1988 hoặc 1994. Việc thiếu bài báo lịch sử không biến phép đo thành lỗi. Nếu muốn xác thực ở mức cao hơn, cần một chuỗi quan trắc độc lập gần trạm hoặc biên bản QA phòng thí nghiệm tương ứng.

## Quy tắc cho dữ liệu dùng huấn luyện

1. Giữ bản MRC và `mrc_ec_monthly_samples.csv` bất biến; kiểm tra SHA-256 trước mỗi lần tạo tập huấn luyện.
2. Tách rõ ba loại cờ: **lỗi kỹ thuật** (thiếu/trùng tháng, sai đơn vị, số âm, không hữu hạn), **trạng thái duyệt nguồn**, và **cực trị thống kê cần giải thích**. Chỉ lỗi kỹ thuật có bằng chứng mới chặn huấn luyện. Cờ cực trị không tự loại điểm.
3. Dữ liệu có một phép đo/ngày mẫu trong tháng, nên nhãn là **EC của mẫu tháng**, không phải trung bình hay cực đại toàn tháng. Giữ `sample_timestamp_local` để báo cáo và để tránh diễn giải sai.
4. Khi so mô hình mới, huấn luyện trên tất cả 927 nhãn hiện có theo các mốc thời gian phù hợp. Báo MAE/RMSE/bias toàn tập, mùa khô và EC cao; dùng cùng cohort và luôn so baseline. Thử biến đổi mục tiêu hoặc hàm mất mát bền vững với cực trị như một thí nghiệm riêng, rồi đánh giá trên **EC gốc**, không tính điểm trên thang biến đổi.
5. Tin tức chỉ đưa vào phần thảo luận kết quả. Không dùng tin được đăng **sau ngày phát hành** làm biến đầu vào cho dự báo hồi cứu. Cần sửa riêng phép chấm theo ngày phát hành vì gói MRC xuất năm 2026 không có ngày công bố lịch sử cho từng phép đo.

Kết luận: dữ liệu EC không còn lỗi nhập liệu cần “làm sạch” bằng thay giá trị. Vấn đề chính là **cực trị thật khó dự báo, nhãn chỉ lấy một ngày trong tháng và thiếu thông tin công bố lịch sử**. Bảng QC giúp minh bạch ba điểm đó mà không làm sai nguồn.
