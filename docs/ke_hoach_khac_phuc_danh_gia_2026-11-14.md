# Kế hoạch khắc phục các điểm nghẽn và lỗ hổng WebGIS EC

Ngày lập: 14/11/2026. Trạng thái: **đã thống nhất phương án và đồng bộ plan triển khai; chưa triển khai mã/CSDL**.

## Nguyên tắc và thứ tự

1. Giữ nguyên dữ liệu gốc, artifact mô hình đang phục vụ và lịch sử dự báo. Mọi thay đổi schema có migration tiến và phương án quay lui.
2. Phân biệt kết quả **nghiên cứu/minh họa** với quyết định vận hành. Không nâng độ tin cậy của dự báo, nội suy hay ngưỡng chỉ bằng đổi nhãn giao diện.
3. Chốt số đo nền trên đúng cấu hình PostgreSQL hiện tại, sau đó kiểm từng giai đoạn bằng thử nghiệm chức năng, hồi quy và đo độ trễ. Không dùng lại số đo 13/11 như cam kết hiệu năng mới.
4. Giữ nguyên mô hình và ngưỡng đang phục vụ đến hết bài bảo vệ, trừ lỗi chức năng bắt buộc phải sửa. Mọi ứng viên phải được chấm trên cùng giao thức khóa dữ liệu, cùng lịch phát hành và có phiên bản mới. Nếu đổi hành vi trước khi bảo vệ, cập nhật bộ ôn tập và demo cùng lúc.

## Giai đoạn 0 — Khóa hiện trạng và sửa cổng kiểm thử (B5, L9)

- Ghi commit, cấu hình không chứa bí mật, phiên bản DB/schema, manifest nguồn và model registry; đo lại p50/p95 cho `frame`, `timeline`, dự báo, và số kết nối dưới 1/5/10 người dùng.
- Dùng lại phân loại sáu lỗi ở mục F của `02_kich_ban_demo.md` (13/11): hai test/fixture cũ, hash script lệch và snapshot nguồn thiếu; không có lỗi nào được xác định là lỗi đường chạy trang. Quyết định cách xử lý từng lỗi: cập nhật kỳ vọng test theo hành vi đã chốt, hoặc tái tạo/ghi chú đúng artifact gốc. **Không sửa hash kỳ vọng cho khớp một cách thủ công**. Nếu không còn nguồn gốc, đánh dấu artifact là không tái lập và loại khỏi bằng chứng chính.
- Tạo `scripts/check.ps1` để chạy smoke test cục bộ nhanh; tách integration PostgreSQL và tái lập khoa học chạy trước phát hành. CI để sau khi môi trường dữ liệu và thời lượng test được chuẩn hóa. Không bỏ qua test lỗi mà không ghi nguyên nhân và phạm vi ảnh hưởng.
- **Đạt khi:** có quyết định và bằng chứng xử lý cho từng lỗi đã phân loại, smoke test xanh, bộ test đầy đủ có kết quả và các giới hạn đã ghi rõ; manifest/hash và lệnh tái lập có thể chạy độc lập; có bảng hiệu năng nền.

## Giai đoạn 1 — Sửa lỗi làm sai hành vi người dùng (L1, L2, L7, L8)

| Mã | Cách sửa đề xuất | Kiểm chứng bắt buộc |
|---|---|---|
| L1 | Migration bổ sung `MyThuan` ↔ `MRC_VN_019804` cho cả hai CHECK của `multivariate_prediction_log`; cập nhật SQL cài mới cùng migration. Giữ nguyên bản ghi cũ. Có script ngược: chỉ chạy được khi chưa có bản Mỹ Thuận; nếu đã có thì giữ schema mới hoặc xuất/di chuyển bản ghi theo một quyết định riêng, không xóa ngầm. | Lưu/đọc lại dự báo 3 trạm trên DB thật; thử sai cặp trạm/site phải bị từ chối; thử migration ngược trên bản sao DB ở cả hai trạng thái. |
| L2 | Ánh xạ SQLSTATE `23505` (UNIQUE) → HTTP **409**, `23514` (CHECK) và `23503` (FK) → HTTP **422**; lỗi schema, quyền, kết nối giữ mã riêng. Log SQLSTATE và tên constraint phía server, không lộ chi tiết DB trong thông báo công khai. | Gây từng lỗi có chủ đích và xác nhận đúng mã HTTP, nội dung, log. |
| L7 | Tạo registry entry/manifest **mới** có `alert_reference.p90_mS_m`, tập nhãn, quy tắc tính, thời điểm hiệu lực và model_version; không sửa artifact cũ. **Trước bảo vệ chỉ tạo bản mới, chưa kích hoạt; kích hoạt sau bảo vệ** sau khi kiểm chứng và cập nhật tài liệu. Khi kích hoạt, bỏ fallback 60,42 khỏi đường đánh giá. Nếu thiếu ngưỡng hợp lệ, báo “chưa có ngưỡng cảnh giác đã hiệu chuẩn” và dùng thời hạn mẫu thận trọng **2 giờ**; không tự thay bằng P90 toàn chuỗi 68,52. | Đổi model không dùng nhầm ngưỡng; thiếu ngưỡng vẫn yêu cầu mẫu ≤ 2 giờ; ngưỡng mới không dùng nhãn tương lai. |
| L8 | Giai đoạn này chọn **endpoint tính không lưu kết quả**: client gửi số đo và RuleProfile, server tính lại và trả kết quả cùng `policy_version`, input hash và hash RuleProfile thực tế. `gate_simulation_drafts` tiếp tục chỉ lưu input/policy; khi mở nháp, server tính lại và gắn nhãn là kết quả tại thời điểm mở. Nếu cần lưu/chia sẻ kết quả bất biến sau này thì thiết kế bảng mới bằng migration riêng. | Một tệp fixture ca biên dùng chung cho test JS/Python; profile tùy biến đổi thì hash đổi; sửa payload kết luận phía client không đổi được kết quả server; không có bảng kết quả mới. |

Giai đoạn này vẫn gắn nhãn tư vấn/minh họa cho quy tắc cống, không tuyên bố an toàn lấy nước.

## Giai đoạn 2 — Hiệu năng và triển khai nhiều người dùng (B1, B2, B3)

| Mã | Cách sửa đề xuất | Kiểm chứng bắt buộc |
|---|---|---|
| B1 | Cache `monthly_inputs()` trong tiến trình theo **dấu phiên bản nguồn/DB/model và ngày hiện tại ở múi giờ Asia/Ho_Chi_Minh**; `_future_boundaries(..., today)` có thể đổi nguồn dự báo khi sang ngày mới. Single-flight để một request dựng, các request khác chờ cùng kết quả. Nếu dựng bản mới lỗi, chỉ trả bản cũ ở đường cho phép với `cache_status: STALE` và `built_at` trong chính phản hồi; nếu đổi ngày làm thay điều kiện khả dụng của dự báo, trả lỗi rõ ràng thay vì lặng lẽ phục vụ kết quả hôm qua. Không thêm scheduler/job nền. | Hai lần gọi cùng tháng cùng ngày/phiên bản cho kết quả tương đương; đổi ngày hoặc cập nhật nguồn/DB làm đổi khóa; giả lập lỗi dựng và kiểm cờ stale hoặc lỗi phù hợp; đo p50/p95 và tải đồng thời. |
| B2 | Giữ **1 worker** trước; đưa host/port ra cấu hình để thử trên LAN có kiểm soát. Chỉ thử nhiều worker/reverse proxy sau khi đo B1 và bộ nhớ thực tế, vì mỗi worker giữ cache riêng. | Truy cập từ máy khác trong mạng thử nghiệm; 1/5/10 người dùng, CPU/RAM và lỗi trong giới hạn đã chốt. |
| B3 | Thêm `psycopg-pool` vào `requirements.txt`, dùng connection pool đọc/ghi riêng, khởi tạo lúc startup và đóng lúc shutdown; pool nhỏ theo worker và tổng số kết nối không vượt `CONNECTION LIMIT 12` (trừ kết nối quản trị). Giữ transaction read-only, timeout, quyền role và reset session/actor khi trả kết nối. | Cài dependency trên môi trường sạch; stress test không rò kết nối, không lẫn actor/transaction giữa request; lỗi DB trả đúng mã. |

**Mục tiêu thử nghiệm:** frame/timeline đã ấm p95 < 300 ms với 5 người dùng trên máy hiện tại; đây là ngưỡng đánh giá, không phải cam kết trước đo. Không có lỗi timeout, 5xx hay vượt giới hạn kết nối.

## Giai đoạn 3 — Quản trị dữ liệu, mô hình và đánh giá thật (B4, L3, L4, L5, L6)

| Mã | Cách sửa đề xuất | Kiểm chứng bắt buộc |
|---|---|---|
| B4 | Bổ sung lệnh cập nhật thủ công có kiểm tra schema/đơn vị/ngày đủ/checksum và báo độ tươi từng nguồn; chỉ thay tệp sau khi kiểm chứng thành công. Lịch chạy tự động và job nền để sau. API 422 nêu rõ nguồn/tháng thiếu. | Nạp dữ liệu hợp lệ, thiếu ngày, trùng ngày, đổi đơn vị và nguồn không truy cập được; bản đã công bố không bị hỏng. |
| L3 | Tách “lần chạy người dùng” khỏi “dự báo phát hành” bất biến. Định nghĩa `MONTHLY_D06_PREV` = lịch phát hành lúc **09:00 ngày 06 của tháng t−1**, múi giờ Asia/Ho_Chi_Minh, cho tháng mục tiêu `t`. **Bảng slot/sự kiện** mang khóa UNIQUE `(trạm, tháng mục tiêu, schedule_code)`; bảng phát hành tham chiếu slot và có ràng buộc tối đa **một bản dự báo mỗi slot**. Model_version, data_version, hash và `issued_at` thật là thuộc tính bất biến. Nếu đến hạn mà đầu vào thiếu, ghi sự kiện `MISSED` cho slot đó (với lý do). Nếu phát hành bù, chỉ gắn một bản `LATE` với `issued_at` thật vào cùng slot; giữ sự kiện `MISSED`, không ghi lùi ngày, không biến nó thành `ON_TIME`. Chấm `LATE` riêng, không gộp vào MAE chính. | Chạy lại/cập nhật model hoặc dữ liệu không sinh bản thứ hai; thiếu nguồn tạo `MISSED`, bản bù giữ `MISSED` và gắn `LATE` cùng slot; MAE chính chỉ dùng `ON_TIME`; nguồn EC đến muộn chỉ thêm điểm và provenance. |
| L4 | Ghi `observed_through`, `retrieved_at` và `availability_basis`; `published_at` chỉ khi nguồn thật sự cung cấp. `retrieved_at` chứng minh hệ thống **đã có bản đó** tại thời điểm tải, không chứng minh ngày công bố đầu tiên. Các phát hành trước khi ghi log này vẫn dựa trên giả định +5/+35 ngày và phải được ghi như vậy; phát hành mới kiểm tra thời điểm tải thực của đúng phiên bản nguồn. | Giả lập nguồn trễ 35 ngày; không dùng tháng chưa tải hoặc chưa đủ; API trả lý do cụ thể. |
| L5 | So RF với **trung vị/trung bình theo tháng từ EC lịch sử đã khóa**, gồm biến thể `SEASONAL_MONTH_MEDIAN`. Khi backtest phải tính climatology từ nhãn khả dụng **trước từng ngày phát hành**, không dùng toàn bộ 2010–2023 để chấm các năm trước 2023. Khi phát hành tương lai mới đóng băng baseline bằng lịch sử đến 12/2023. Không dùng seasonal naive đệ quy. Chỉ đổi mô hình mốc bản đồ sau khi thắng trên cùng giao thức khóa EC. | MAE/RMSE và lỗi theo mùa so cùng mẫu, cùng ngày phát hành; không rò nhãn tương lai; hình sông cũ/mới so được. |
| L6 | Chính sách QA cho huấn luyện tiếp theo: **giữ `SUSPECT` theo mặc định**; cờ IQR/bước nhảy chỉ yêu cầu rà soát. Chỉ loại khi có bằng chứng lỗi kỹ thuật (sai đơn vị, trùng, lỗi thiết bị hoặc nguồn phủ nhận). Rà 117 dòng trong báo cáo QA hai trạm, đặc biệt 26 dòng Mỹ Tho EC ≥ 150 mS/m đều `SUSPECT`; phân tích độ nhạy giữ/loại nhưng không dùng bản loại nếu nó làm mất các tháng cực trị. Ghi policy, quyết định từng dòng và hash vào registry phiên bản mới. **Mô hình hiện tại học trên 463 mẫu EC Mỹ Tho đến 12/2023, gồm cả các dòng `SUSPECT`**; 927 là tổng dòng QA của Mỹ Tho và Tân Châu, không phải số mẫu của mô hình chính. | Kiểm số tháng EC cao trước/sau QA; huấn luyện tái lập đúng tập; thay policy tạo model_version mới. |

Trong bản 1–2 tuần, phát hành bằng lệnh có kiểm soát tại lịch đã định. Nếu lệnh không chạy đúng giờ, ghi `MISSED` với lý do `JOB_NOT_RUN` khi kiểm tra lại và lưu **thời điểm phát hiện thật**; không tạo bản ghi giả như thể đã chạy lúc 09:00. Tự động hóa lịch chạy là bước sau.

**Điều kiện để L3 chấm điểm:** thêm phiếu số đo thực địa có kiểm duyệt ngay trong giai đoạn này, song song sổ phát hành. **Trước khi nhận phiếu đầu tiên**, lập tài liệu tiêu chí tương đương có ngày và phiên bản: bán kính tối đa quanh trạm MRC, cửa sổ ngày trong tháng, khung giờ đo, có hay không quy đổi về EC25 và công thức/nguồn nhiệt độ nếu có, điều kiện hiệu chuẩn thiết bị, số mẫu và cách tổng hợp thành nhãn tháng. Phiếu ghi trạm/vị trí, thời điểm, đơn vị, thiết bị/cách đo và người duyệt; dữ liệu nằm ở bảng riêng. Chỉ dùng phiếu để chấm dự báo EC tháng tại trạm nếu thỏa tiêu chí đã chốt trước đó; một phép đo ở vị trí khác hoặc một ngày bất kỳ không tự thành “EC thực tế của tháng”. Trong 1–2 tuần **nhiều khả năng chưa có nhãn đủ điều kiện để chấm**; L3 khi đó chỉ chứng minh hạ tầng phát hành và chờ nhãn, chưa chứng minh sai số vận hành.

## Giai đoạn 4 — Mở rộng sử dụng có kiểm soát (L10, L11)

- **L10:** Trong phạm vi đồ án, dùng API key riêng cho người duyệt, hàng đợi kiểm duyệt và audit log đã có; chưa mở nhập công khai cho người dân. OIDC, nhiều vai trò và chống spam quy mô công khai là bước triển khai sau.
- **L11:** Sau khi L3 và phiếu thực địa chạy được, cân nhắc thông báo về nguồn cũ và dự báo vượt ngưỡng *tư vấn*. Kênh gửi, người nhận và trách nhiệm trực phải được xác định trước khi bật thông báo. What-if cống là hạng mục tùy chọn sau lõi khoa học.
- **Đạt khi:** biết ai duyệt mỗi phiếu; dữ liệu chưa duyệt không hiển thị như số đo tin cậy; thông báo (nếu có) truy được về bản phát hành và ngưỡng đã dùng.

## Cổng duyệt và cách bàn giao

1. **Khung 1–2 tuần:** ưu tiên giai đoạn 0 (1–2 ngày), giai đoạn 1 phần L1/L2/L8 (2–3 ngày), giai đoạn 2 phần B1/B3 (2–3 ngày), giai đoạn 3 phần khung L3 + phiếu thực địa (2–4 ngày). Ước lượng phụ thuộc 6 lỗi test và migration DB; B2, B4 tự động, đổi P90/model và giai đoạn 4 có thể dời sau bảo vệ.
2. Mỗi giai đoạn giao: migration/code, test, số đo trước/sau, thay đổi tài liệu phương pháp và hướng dẫn quay lui. Migration ngược L1 chỉ hợp lệ nếu chưa có bản Mỹ Thuận; dữ liệu phát hành/phiếu thực địa đã lưu thì quay lui ứng dụng bằng cách giữ schema tương thích, không xóa bản ghi.
3. Điểm quyết định khoa học riêng: chính sách QA, mốc khả dụng nguồn, chọn climatology cho 2 trạm, cách hiệu chuẩn P90 và tính tương đương của phiếu thực địa phải được chốt bằng báo cáo trước khi đổi model/registry đang phục vụ.
4. Đã đồng bộ `docs/superpowers/plans/2026-11-14-stabilize-and-interactive-features.md` về lịch phát hành/slot, P90, L5/L6, phiếu thực địa và phạm vi 1–2 tuần. Cập nhật `docs/on_tap_hoi_dong_2026-11-13/` nếu thay đổi hành vi trước ngày bảo vệ.
