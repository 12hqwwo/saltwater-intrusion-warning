# Tìm nguồn bổ sung — 15/10/2026

## Kết quả

1. Thủy lợi Tiền Giang: tìm được thông báo mặn ngày 12, 13, 14, 15/05/2026, có bảng g/L và khoảng thống kê 12h hôm trước–12h ngày báo cáo. Các điểm gồm Vàm Giồng, Hòa Định, Xuân Hòa, Tân Mỹ Chánh; một số bản tin có thêm Thủ Khoa Huân, cầu Trường Chính Trị và điểm trên kênh Chợ Gạo. Đây là độ mặn cực đại trong cửa sổ, không phải EC hoặc trung bình ngày. Các URL chính thức lần lượt có id=455332, 455336, 455412, 455416 tại https://thuyloitiengiang.vn/web/thuyloitiengiang/chi-tiet-tin-tuc . Nội dung được công cụ tìm kiếm trả về; tải HTML gốc vẫn lỗi chứng chỉ HTTPS. Chưa nhập giá trị từ kết quả tìm kiếm vào bộ quan trắc.

2. Báo cáo ngày 13/10/2026 tại https://thuyloitiengiang.vn/en/web/thuyloitiengiang/chi-tiet-tin-tuc?id=522066: có mực nước Xuân Hòa, ghi hệ cao độ quốc gia; độ mặn cực đại từng con nước có giờ và giá trị lúc 7h. Cần tách từng loại thống kê, tránh trùng các ngày lặp lại giữa bản tin. Tải gốc bị lỗi TLS; chưa có chuỗi đã kiểm toán.

3. Đại học Cần Thơ: https://knowledgehub.ctu.edu.vn/quantrac_man.aspx . Đã tải HTML gốc, có tiêu đề bản đồ cực đại ngày 14/10/2026 và kết nối GeoServer/WMS. Đây mới là đầu mối bản đồ; chưa tải được bộ giá trị có metadata/nguồn đo đầy đủ, chưa xác nhận lớp bao phủ các trạm thuộc phạm vi đề tài. Không đọc màu bản đồ để tạo số đo.

4. RIA2: đã tải trang chủ và chuyên mục https://vienthuysan2.org.vn/category/tin-hoat-dong/ban-tin-quan-trac-chat-luong-nuoc/ . Trang chuyên mục được tải trong lần này có bản tin cá tra đợt 18/2025 ở đầu danh sách; chưa tìm thấy bản tin cá tra 2026 tại trang đã kiểm tra. Đây không phải bằng chứng cơ quan không có dữ liệu 2026. Kho có liên kết phân trang tới trang 36, là đầu mối mở rộng chuỗi lịch sử.

5. SIWRR: trang chủ https://www.siwrr.org.vn/ có bản tin tuần 01–15/10/2026 và bản tin mùa Đông Xuân 2026–2027. Phân loại sản phẩm dự báo cơ quan khác; không dùng làm nhãn quan trắc.

## Trạng thái thu thập

`data/external/search_20261015/manifest.json`: 3 HTML tải thành công (CTU, trang chủ RIA2, chuyên mục RIA2), 5 lần tải bản tin Tiền Giang bị chặn do xác minh chứng chỉ. Tệp thành công có URL, thời điểm và SHA-256; không tắt kiểm tra SSL. Chưa bổ sung nhãn quan trắc mới vào snapshot hoặc DB.

## Ý nghĩa với nghiên cứu

Nguồn thủy lợi phù hợp để nghiên cứu độ mặn cực đại theo ngày/con nước và tra cứu diễn biến vận hành được báo cáo. Chưa được kết luận đủ train/test chỉ từ vài bản tin. Cần tải gốc hợp lệ, khảo sát độ dài chuỗi, lập định danh điểm, tọa độ/CRS, phương pháp đo, cờ chất lượng và kiểm tra thiếu/trùng. Không ghép với MRC chỉ vì cùng vùng Mỹ Tho.

Một số trang tháng 5 ghi giờ đăng buổi sáng nhưng cửa sổ báo cáo kết thúc 12h cùng ngày; phải đánh dấu thời điểm khả dụng chưa rõ, không mặc định số liệu đã có tại giờ đăng. Nhật ký vận hành dạng mô tả không thay thế quy trình vận hành được phê duyệt hoặc quan hệ thủy lực đã kiểm chứng.
