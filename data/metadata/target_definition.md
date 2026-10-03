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

Công thức quy đổi xấp xỉ (chỉ dùng ở dải 1–40‰, nhiệt độ ~25°C):  
`Salinity (‰) ≈ EC (mS/cm) × 0.64`

Vì dữ liệu MRC đơn vị **mS/m**, cần chuyển sang **mS/cm** trước:  
`EC (mS/cm) = EC (mS/m) / 10`  
`Salinity (‰) ≈ (EC_mS_per_m / 10) × 0.64 = EC_mS_per_m × 0.064`

> **Ví dụ:** EC = 25 mS/m → 2.5 mS/cm → ≈ 1.6‰

**Tuy nhiên**, công thức này chỉ là xấp xỉ. Đề xuất:
1. **Dự báo EC (mS/m)** trong toàn bộ pipeline  
2. Khi cần so sánh với ngưỡng quy chuẩn (‰), **quy đổi tại bước Decision Logic**
3. Ghi rõ trong báo cáo rằng hệ thống dự báo EC (mS/m), sau đó quy đổi xấp xỉ sang ‰ để so sánh ngưỡng

---

## 3. Ngưỡng mặn áp dụng trong Decision Logic

> ⚠️ **Không được tự đặt ngưỡng 4‰ cho mọi cống.** Ngưỡng phải dựa trên mục đích sử dụng nước tại khu vực tương ứng.

| Mục đích | Ngưỡng mặn tối đa | Nguồn tham khảo |
|---|---|---|
| Lúa (giống lúa nhạy cảm) | 1.0–2.0‰ | TCVN 8641:2011 – Công trình thủy lợi, kỹ thuật tưới tiêu |
| Lúa (giống chịu mặn vừa) | 2.0–4.0‰ | QCVN 08:2023/BTNMT – Chất lượng nước mặt |
| Hoa màu / rau | 0.5–1.5‰ | Tham chiếu FAO Irrigation Water Quality |
| Nuôi trồng thủy sản nước ngọt | 0.5‰ | Tham chiếu QCVN 02-15:2009/BNNPTNT |
| Cấp nước sinh hoạt | Chloride 250-300 mg/L | QCVN 01-1:2018/BYT |
| Cấp nước nông thôn tối đa | 1.0‰ | QCVN 02:2009/BYT |

**Trong prototype này:** Ngưỡng được gán tại cột `threshold_ppt` trong `sluice_gates.csv` (đơn vị **‰**).  
Khi Decision Logic so sánh, quy đổi giá trị EC dự báo → ‰ rồi so sánh với ngưỡng.

---

## 4. Tuyên bố về giới hạn hệ thống

- Dữ liệu EC có **độ phân giải tháng** → Không thể tuyên bố "gần thời gian thực" hay "theo ngày"
- Kết quả dự báo là **xu hướng tháng**, phù hợp với lịch vụ mùa và kế hoạch vận hành cống theo mùa
- Hệ thống **không điều khiển cống tự động** mà chỉ sinh **Khuyến nghị (Recommendation)**

---

## 5. Tài liệu tham khảo ngưỡng

- TCVN 8641:2011 - Công trình thủy lợi – Kỹ thuật tưới tiêu nước cho cây lương thực và cây thực phẩm
- QCVN 08:2023/BTNMT - Quy chuẩn kỹ thuật quốc gia về chất lượng nước mặt
- QCVN 01-1:2018/BYT - Quy chuẩn kỹ thuật quốc gia về chất lượng nước sạch sử dụng cho mục đích sinh hoạt
- Phạm Văn Giáp và nnk (2016). Nghiên cứu xâm nhập mặn vùng Đồng bằng sông Cửu Long trong điều kiện biến đổi khí hậu.
- FAO (1985). Water quality for agriculture. Irrigation and Drainage Paper 29 Rev.1.
