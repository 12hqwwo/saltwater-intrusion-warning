# Target Definition – Biến mục tiêu của hệ thống

## 1. Quyết định chính thức

**Biến mục tiêu dự báo:** Độ dẫn điện (Electrical Conductivity – EC), đơn vị **mS/m**  
**Nguồn dữ liệu gốc:** Mekong River Commission (MRC), 2 trạm quan trắc  
**Độ phân giải thời gian:** **Tháng** (không phải ngày hoặc giờ)

---

## 2. Lý do KHÔNG gọi là "độ mặn ‰" (salinity in PSU/‰)

Dữ liệu từ MRC được đo và lưu trữ dưới dạng **Conductivity (mS/m)** – độ dẫn điện của nước.  
Độ mặn (‰ hay PSU) và độ dẫn điện (EC) là hai đại lượng khác nhau, mặc dù có tương quan chặt:

| Đại lượng | Ký hiệu | Đơn vị phổ biến |
|---|---|---|
| Electrical Conductivity | EC | mS/m hoặc mS/cm hoặc µS/cm |
| Salinity | S | ‰ (g/L) hoặc PSU |

**Đính chính 29/10/2026:** phép đổi đơn vị trong phiên bản cũ sai hệ số 10. Theo định nghĩa đơn vị,
`1 mS/m = 0,01 mS/cm = 10 µS/cm`, nên `25 mS/m = 0,25 mS/cm`. Đây chỉ là đổi **đơn vị EC**, không phải đổi EC sang độ mặn.
[Bảng đổi đơn vị của USGS](https://pubs.usgs.gov/of/2012/1176/OF12-1176.pdf) là nguồn kiểm tra phép đổi này.

Không có một hệ số EC → ‰ hợp lệ cho mọi mẫu nước. Quan hệ còn phụ thuộc nhiệt độ đo/bù nhiệt và thành phần ion; [USGS](https://water.usgs.gov/water-resources/memos/documents/WQ.2011.03.pdf) cũng nêu giới hạn này. Gói EC MRC hiện chưa xác định cơ sở bù nhiệt, và bộ dữ liệu chưa có cặp EC–độ mặn đủ tin cậy để hiệu chuẩn tại hai trạm. Vì vậy:

1. Huấn luyện, chấm và báo cáo **EC mS/m**; nhãn là **một phép đo trong tháng**, không phải trung bình hay cực đại tháng.
2. Không dùng phép đổi tuyến tính cũ `EC × 0,064` để so với ngưỡng độ mặn.
3. Nếu cần quyết định theo ngưỡng ‰, phải có cặp EC–độ mặn đồng thời tại cùng vị trí, nhiệt độ/cơ sở bù nhiệt và kiểm định hiệu chuẩn ngoài mẫu.

---

## 3. Ngưỡng trong Decision Logic

Chưa có ngưỡng EC vận hành đã được xác nhận cho từng cống và mục đích dùng nước. Không gán một ngưỡng độ mặn chung cho mọi cống, không chuyển ngưỡng độ mặn sang EC bằng hệ số cố định, và không diễn giải dự báo tại hai trạm MRC là dự báo tại từng cống.

Một số màn hình mô phỏng cũ hiển thị hệ số thực nghiệm `0,0064 g/L trên 1 mS/m`; hệ số đó chưa được xác nhận là quan hệ của hai trạm và không phải kết quả của mô hình EC. Muốn xây dựng luật vận hành cần hồ sơ ngưỡng có nguồn, điểm đo tại cống, hiệu chuẩn cùng vị trí và kiểm định riêng.

---

## 4. Tuyên bố về giới hạn hệ thống

- Dữ liệu EC có **độ phân giải tháng** → Không thể tuyên bố "gần thời gian thực" hay "theo ngày"
- Kết quả dự báo là **xu hướng tháng**, phù hợp với lịch vụ mùa và kế hoạch vận hành cống theo mùa
- Hệ thống **không điều khiển cống tự động** mà chỉ sinh **Khuyến nghị (Recommendation)**

---

## 5. Tài liệu tham khảo

- [USGS: hệ đơn vị EC và specific conductance](https://pubs.usgs.gov/of/2012/1176/OF12-1176.pdf).
- [USGS: giới hạn của phép suy độ mặn từ độ dẫn điện](https://water.usgs.gov/water-resources/memos/documents/WQ.2011.03.pdf).
