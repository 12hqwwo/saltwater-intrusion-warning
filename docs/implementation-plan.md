# Kế hoạch hoàn thiện WebGIS và dự báo EC tháng

Ngày cập nhật: 22/10/2026. Phạm vi được chọn là WebGIS kết hợp dự báo giá trị mẫu EC tháng kế tiếp. Mục tiêu là một ứng dụng có luồng sử dụng nhất quán và kết quả có thể truy nguồn, phù hợp bằng chứng hiện có.

## 1. Trạng thái và quy tắc nghiệm thu

Đợt hiện tại chuyển ứng dụng từ trang nghiên cứu tập trung sang các mục công việc, tách lớp backend và module frontend, sửa diễn giải kết quả và cập nhật hướng dẫn chạy. Các tiêu chí trong tài liệu này là điều kiện nghiệm thu, không phải tuyên bố đã chạy đạt. Báo cáo kiểm tra của từng đợt cần ghi lệnh, chế độ dữ liệu, kết quả và giới hạn kiểm tra.

Kết quả kiểm tra trong biên bản 16/10 là bằng chứng của phiên bản khi đó. Cần kiểm tra lại phần bị thay đổi trước khi sử dụng cho phiên bản mới. Không cần huấn luyện lại chỉ để chứng minh một thay đổi bố cục hoặc cấu trúc mã.

## 2. Các giai đoạn

| Giai đoạn | Công việc | Tiêu chí hoàn thành |
| --- | --- | --- |
| A. Phạm vi và trạng thái | Giữ EC mS/m; tách quan trắc, dự báo hồi cứu, ước tính khí tượng và mô phỏng | Người dùng phân biệt được từng loại kết quả, kỳ dữ liệu và giới hạn |
| B. Cấu trúc ứng dụng | Tách API/service/repository/domain; module hóa frontend; trang chính và điều hướng theo công việc | Import và build hợp lệ; các route cần tương thích còn dùng được; không nhân bản nghiệp vụ |
| C. Luồng tra cứu | Chọn trạm/thời gian, bản đồ, bảng, biểu đồ, nguồn và xuất CSV | Bộ lọc nhất quán; dữ liệu rỗng/lỗi được thể hiện; bảng và CSV khớp |
| D. Luồng dự báo tháng | Chọn thí nghiệm, xem thực đo–dự báo, baseline, sai số, độ trễ và protocol | Không huấn luyện trong request; không dùng MAE khác cohort làm sai số cho kết quả đang xem |
| E. Hồ sơ và chất lượng | Hiển thị nguồn, cờ QA và bằng chứng thiếu; tách hồ sơ thực khỏi mô phỏng | Khai báo không trở thành xác minh; không mặc định ngưỡng an toàn hoặc khuyến nghị vận hành |
| F. Bàn giao | Kiểm tra ứng dụng, cập nhật lệnh chạy và danh sách phần còn thiếu | Có bằng chứng kiểm tra phiên bản hiện tại; nguồn/artifact được giữ nguyên; tài liệu khớp giao diện |

Các bước A–F tập trung hoàn thiện ứng dụng hiện có. Tích hợp toàn bộ nghiên cứu feature mới và cập nhật dữ liệu tự động là các bước tiếp theo cần điều kiện riêng.

## 3. Kịch bản kiểm tra ứng dụng

1. Chạy build frontend và kiểm tra import/route backend. Mở trang chính, chọn từng mục và thử liên kết hash trực tiếp.
2. Ở snapshot: chọn Mỹ Tho và Tân Châu, đổi khoảng thời gian, xem dữ liệu rỗng, bảng/biểu đồ và CSV; đối chiếu một số giá trị với snapshot.
3. Chọn từng thí nghiệm tháng và đổi kịch bản độ trễ. Kiểm tra trạm, thời gian, giá trị thực đo/dự báo, đơn vị, baseline và metrics khớp artifact tương ứng.
4. Kiểm tra nhánh khí tượng cùng tháng: nhãn là ước tính lịch sử, không phải thực đo, dự báo hiện tại hoặc bằng chứng nước an toàn.
5. Chọn công trình thiếu bằng chứng và gửi hồ sơ không đầy đủ. Kết quả phải giữ trạng thái thiếu dữ liệu; không tự thêm phê duyệt, chất lượng VALIDATED, ngưỡng hoặc lệnh điều khiển.
6. Kiểm tra PostgreSQL nếu môi trường có DB: chọn dataset, lọc và phân trang; đối chiếu nguồn. Nếu chưa kiểm tra được, ghi rõ chưa xác nhận luồng DB thay vì dùng snapshot làm bằng chứng thay thế.
7. Kiểm tra lỗi API/DB, nguồn tệp thiếu và dữ liệu cũ. Người dùng nhận thông báo rõ; ứng dụng không âm thầm đổi nguồn hoặc tạo số liệu.
8. Kiểm tra trên màn hình máy tính và kích thước di động: điều hướng, bộ lọc, biểu đồ và bảng còn sử dụng được.

Các kiểm tra logic hồ sơ, nguồn dữ liệu và route tương thích cần có hồi quy phù hợp. Không cần thêm kiểm thử chỉ lặp lại chi tiết CSS hoặc thay thế kiểm chứng khoa học bằng kiểm thử giao diện.

## 4. Tích hợp nghiên cứu feature mới

Nghiên cứu 19/10 có protocol và bộ kết quả riêng theo tài liệu đã rà soát. Thư mục `outputs/ec_feature_research_20261019/` không còn trong checkout lúc nghiệm thu ngày 22/10, nên chưa thể tích hợp bộ kết quả này vào ứng dụng. Cần có lại đủ artifact và đối chiếu manifest trước khi thực hiện lộ trình:

1. Đăng ký một phiên bản kết quả mới: nguồn, checksum, protocol, đơn vị, cohort, giả định khả dụng và thuật toán được chọn.
2. Giữ nguyên bộ cũ để truy vết; không ghi đè metrics cũ hoặc đổi nhãn giữa hai bộ. Giải thích 927 mẫu nguồn và 810 nhãn v2 trong mục chất lượng dữ liệu.
3. Tạo adapter đọc kết quả cho ứng dụng; kiểm tra khóa trạm–tháng–kịch bản, trường bắt buộc và các metric khớp dự báo từng tháng.
4. Hiển thị baseline cạnh mô hình được chọn theo từng trạm. Mức cải thiện âm hoặc không ổn định phải được giữ nguyên.
5. Ghi rõ validation 2014–2019, holdout hồi cứu 2020–2023 và giả định EC trễ 0/30 ngày. Không gọi holdout này là kiểm định mù mới.

Nghiệm thu tích hợp khi người dùng phân biệt được hai phiên bản, xem được bằng chứng tương ứng và không so sai tập tháng. Chỉ tái huấn luyện khi có thay đổi dữ liệu/protocol hoặc nhu cầu nghiên cứu cụ thể; đóng băng protocol cũ trước khi bắt đầu vòng mới.

## 5. Điều kiện để có dự báo mới

| Nhu cầu | Dữ liệu hoặc bằng chứng cần bổ sung |
| --- | --- |
| Dự báo EC tháng sắp tới dùng EC trễ | EC đủ mới, thời điểm đo và thời điểm khả dụng, QA và điều kiện về tuổi dữ liệu |
| Mô hình chỉ dùng khí tượng | Giao thức đánh giá riêng; dùng dự báo khí tượng đã phát hành nếu muốn dự báo trước thời gian |
| Cải thiện Mỹ Tho và các mẫu EC cao | Xác minh nhãn/thiết bị, phân tích độ nhạy, đánh giá công bằng với baseline |
| Thêm lưu lượng hoặc mực nước | Độ phủ đồng thời, vị trí/ô lưới đại diện, đơn vị và thời điểm khả dụng; xử lý cờ SUSPECT |
| Cập nhật theo lịch | Cơ chế tiếp nhận có phiên bản, phát hiện lỗi/thiếu nguồn và công bố trạng thái; lịch tải khí tượng không thay cho cảm biến EC |

Không cam kết chất lượng dự báo hiện tại khi chuỗi EC MRC đang kết thúc năm 2023. Có thể hoàn thiện WebGIS và đánh giá hồi cứu trong khi chờ dữ liệu mới.

## 6. Các phần mở rộng phụ thuộc dữ liệu thực địa

Chưa đưa vào tiêu chí bắt buộc của ứng dụng tiểu luận hiện tại: cảnh báo tại cống theo giờ, lịch đóng/mở tự động, điều khiển thiết bị, bề mặt mặn liên tục, quy đổi EC sang g/L hoặc xác suất tin cậy chưa hiệu chuẩn.

Muốn tiến tới hỗ trợ vận hành cần tọa độ/CRS xác minh, quan hệ thủy lực trạm–cống, EC và mực nước hai phía cùng cơ sở đo, ngưỡng có nguồn phù hợp mục đích sử dụng, quy trình công trình và người có thẩm quyền duyệt. Hệ thống nhiều người dùng còn cần lưu hồ sơ, phân quyền và nhật ký thay đổi. Các hạng mục này không được thay bằng cờ boolean do giao diện tự đặt.

## 7. Bảo toàn và bàn giao

- Giữ nguồn gốc, manifest, dữ liệu chưa xác minh và artifact khoa học; không dọn dựa riêng vào trạng thái untracked.
- Không nhập hồ sơ v3 hoặc độ mặn g/L vào nhãn EC mS/m khi chưa hoàn tất tiếp nhận và xác định tương thích.
- Giữ khả năng truy lại bộ kết quả đang phục vụ, phiên bản nghiên cứu mới và lý do khác nhau.
- Hướng dẫn chạy phải chỉ rõ trang chính, chế độ snapshot/postgres, cách build và trạng thái cần xử lý khi lỗi.
- Báo cáo bàn giao ghi phần đã kiểm tra, phần chưa kiểm tra và bước phụ thuộc dữ liệu mới; không suy diễn phần chưa kiểm tra thành đã đạt.

Tham khảo: [kiến trúc](architecture.md), [hướng dẫn chạy](run_guide.md), [hướng dẫn kết quả 21/10](reports/20261021_huong_dan_file_va_cau_hoi_giang_vien.md).

## 8. Kết quả kiểm tra ngày 22/10/2026

| Kiểm tra | Kết quả |
| --- | --- |
| `python -m unittest discover -s tests -p "test_*.py" -v` | 17 kiểm thử đạt: route tương thích, intake/phân trang, lọc ngày, dữ liệu thiếu, nguồn và xuất kết quả, hồ sơ không tự xác minh, không fallback khi DB lỗi |
| `node --test tests/frontend_api.test.mjs` | 4 kiểm thử đạt: JSON POST, hủy request cũ, giữ thông báo lỗi API, từ chối phản hồi không phải JSON |
| `npm.cmd --prefix frontend run build` | Bản build cuối đạt, 228 module; tạo `workspace.html`, `index.html` và trang chuyển hướng `research.html` |
| Đối chiếu kết quả khoa học đang phục vụ | MAE/RMSE tính lại từ dự đoán trên common cohort khớp API và CSV của cả bốn thí nghiệm; không huấn luyện lại |
| Chẩn đoán môi trường | Python, thư viện API, snapshot/checksum, PostGIS và schema nghiên cứu đều sẵn sàng |
| API với PostgreSQL thật, qua TestClient trong tiến trình | Health trả transaction chỉ đọc; workspace có 12 điểm và 977 quan trắc; API trạm DB có 2 trạm; chọn dataset và đọc lịch sử trả 200; danh mục cống DB có 0 bản ghi |
| Runner | `run_webgis.py --help` và kiểm tra cú pháp PowerShell đạt; tiến trình Uvicorn phục vụ build đã khởi động thành công trong lần kiểm tra |

Các phép thử PostgreSQL chỉ đọc dữ liệu; không nhập dữ liệu, thay đổi schema hay ghi phiếu. Các lần xóa tài liệu do người dùng xác nhận được giữ nguyên, không khôi phục tự động.

Kiểm tra trực quan desktop/mobile chưa thực hiện: công cụ trình duyệt từ chối quyền truy cập địa chỉ cục bộ. Kiểm thử API và build không thay thế việc nghiệm thu bố cục hoặc tương tác trên trình duyệt thật.

## 9. Phần ứng dụng đã triển khai tiếp ngày 23/10/2026

- Quan trắc PostgreSQL đọc trực tiếp các bảng public: 2 trạm/927 mẫu hiện có, chọn một RAW_EC mỗi trạm; công bố dataset và checksum. Snapshot vẫn có 12 điểm/977 mẫu, chọn chế độ rõ ràng.
- Lịch sử PostgreSQL nằm ngay trong Dashboard: nguồn, trạm, phiên bản, thời gian, QA, O/E, biểu đồ, phân trang và CSV.
- RIA2 tham khảo bật sẵn khi có trong nguồn; bổ sung bật/tắt ranh giới/cống. Ngưỡng EC tự nhập đổi màu điểm và thêm đường ngang vào biểu đồ quan trắc/dự báo.
- Dự báo có bảng từng tháng, lọc năm, sai số từng tháng và xuất CSV; đọc thêm `next_forecast.json` để hiển thị dự báo sau mẫu cuối kèm mốc đầu vào, phân biệt rõ tháng lịch sử.
- Cống có luồng mô phỏng INTAKE/DRAIN với ngưỡng EC, chênh mực nước, giới hạn mực nước trong, lý do kết quả; lưu/khôi phục nháp và nhập/xuất JSON. Mô phỏng không chuyển khai báo thành bằng chứng được phê duyệt.
- Bản đồ, biểu đồ, CSS và logic kịch bản được đặt trong module nghiệp vụ/shared/domain; tên research giữ cho tương thích.

Hướng dẫn thao tác: [user-flow.md](user-flow.md). Hoàn thiện ở phạm vi ứng dụng tiểu luận và kịch bản mô phỏng. Các phần tiếp theo phụ thuộc dữ liệu: EC mới cho dự báo hiện tại, tọa độ và hồ sơ cống, ngưỡng được xác minh và lưu hồ sơ nhiều người dùng.

## 10. Ưu tiên dự báo đa biến theo yêu cầu người dùng

Luồng chính đã chuyển sang chạy mô hình EC đa biến trực tiếp. Đã tải ERA5 có đơn vị xác định 1985–09/2026, huấn luyện và lưu Random Forest riêng cho hai trạm với 927 nhãn EC MRC. Đặc trưng gồm mưa, nhiệt độ, gió tháng `t−2` và chu kỳ tháng mục tiêu. Người dùng chọn trạm/tháng, chạy suy luận, xem đầu vào/kết quả/sai số, đưa kết quả lên bản đồ và xuất JSON/CSV.

Mô hình khí tượng có thể tính tháng mới mà không cần EC trễ hiện tại; EC mới cần cho kiểm chứng và cập nhật chất lượng, không phải điều kiện chặn suy luận. Cách diễn đạt yêu cầu EC mới ở các phần trước áp dụng cho mô hình có EC trễ hoặc việc đánh giá dự báo hiện tại. Sai số hồi cứu của RF chưa vượt mọi baseline; các kết quả đối chứng được giữ trên giao diện. Chi tiết ở [multivariate-forecast.md](multivariate-forecast.md).
