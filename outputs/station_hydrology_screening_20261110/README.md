# Rà soát đầu vào thủy văn Tân Châu và Mỹ Thuận — 10/11/2026

Đây là thử nghiệm offline để chọn nhóm đầu vào trước khi tích hợp. Không thay registry, model đang phục vụ, DB hoặc giao diện.

## Dữ liệu phù hợp

- EC mục tiêu riêng từng trạm: Tân Châu 464 mẫu; Mỹ Thuận 451 mẫu, 1985–2023. Mỗi nhãn là mẫu EC trong tháng, không phải EC trung bình tháng.
- Khí tượng ERA5 lấy đúng trạm: mưa, nhiệt độ, gió; cộng sin/cos tháng mục tiêu.
- Q Kratie: nguồn MRC, m³/s; đủ 60/60 tháng t−2 cho các mục tiêu 2019–2023, nguồn gần nhất đến 28/10/2026.
- Mực nước Tân Châu: chuỗi Manual MRC, m; đủ 60/60 tháng t−2, nguồn gần nhất đến 28/10/2026.
- Mực nước Mỹ Thuận: đủ 60/60 tháng t−2 để kiểm chứng lịch sử; tệp hiện có kết thúc 2023. Không chọn làm đầu vào bắt buộc cho dự báo 2026 khi chưa cập nhật.
- Vàm Nao: lịch sử ngắn hơn và tệp hiện có kết thúc 2023; Vàm Kênh thiếu 2/60 tháng đầu vào. Chưa ưu tiên trong lượt sàng lọc này.
- Q Tân Châu Mendeley kết thúc 2015, không phủ kỳ đánh giá. Không thay thế Q bằng mực nước.
- Một tháng thủy văn hợp lệ cần ít nhất 20 ngày có giá trị; 28 ngày tháng 10/2026 không có nghĩa đã tải đủ 31 ngày. Cờ QA nguồn vẫn giữ nguyên.

## Giao thức

RF 300 cây, sâu tối đa 8, lá tối thiểu 3, seed 42; fit một lần trước kỳ mất EC. Đầu vào tháng t−2, phát hành ngày 6 tháng t−1, giả định nguồn thủy văn/khí tượng khả dụng sau cuối tháng 5 ngày. Kiểm cả độ trễ công bố EC 5/35 ngày. Các biến trung bình/trung vị 3 tháng kết thúc tại t−2; chuẩn hóa lưu lượng theo cùng tháng chỉ dùng lịch sử trước đó.
Chỉ điền dữ liệu thiếu trong huấn luyện bằng trung vị tập huấn luyện; toàn bộ đầu vào thủy văn trong kỳ chấm phải đủ. Dự báo chỉ khí tượng được kiểm khớp kết quả frozen cũ với atol=1e-8.

## Các phương án khả thi với nguồn gần đây

Đơn vị mS/m; mỗi ô là MAE / RMSE; giả định EC +5 ngày. H = mực nước Tân Châu (tại trạm cho Tân Châu, thượng lưu cho Mỹ Thuận). Q = ba biến lưu lượng Kratie.

| Trạm | Kỳ | Khí tượng | + H | + Q + H |
|---|---|---:|---:|---:|
| TANCHAU | 2019_2021 | 3.737 / 4.793 | 3.037 / 4.004 | 3.193 / 4.038 |
| TANCHAU | 2021_2023 | 4.357 / 5.636 | 3.827 / 5.153 | 3.746 / 4.948 |
| TANCHAU | 2022_2023 | 4.445 / 5.836 | 3.935 / 5.395 | 3.720 / 5.015 |
| MYTHUAN | 2019_2021 | 4.107 / 4.999 | 3.320 / 4.053 | 3.418 / 4.083 |
| MYTHUAN | 2021_2023 | 4.385 / 5.257 | 3.708 / 4.704 | 3.898 / 4.671 |
| MYTHUAN | 2022_2023 | 3.953 / 4.885 | 3.486 / 4.543 | 3.412 / 4.260 |

## Nhận xét và đề xuất

1. Mực nước Tân Châu là đầu vào ưu tiên cho cả hai trạm: có độ phủ huấn luyện dài, đủ kỳ đánh giá và nguồn gần đây. Nhóm thêm H cải thiện cả MAE/RMSE so với model khí tượng ở tất cả cửa sổ đã chấm.
2. Q Kratie là ứng viên bổ sung, không mặc định bắt buộc: thêm Q vào nhóm H không thắng mọi kỳ. Tân Châu: H thắng kỳ 2019–2021, Q+H tốt hơn 2021–2023 và 2022–2023. Mỹ Thuận: H thắng cả hai điểm số 2019–2021 và MAE 2021–2023; Q+H có RMSE tốt hơn 2021–2023 và cả hai tốt hơn 2022–2023.
3. Thêm cả mực nước Mỹ Thuận có thể giảm điểm toàn kỳ lịch sử, nhưng cần cập nhật nguồn sau 2023 trước khi xem xét phục vụ hiện tại. Chỉ thêm mực nước Mỹ Thuận có kỳ kém model khí tượng.
4. Tân Châu: Q+H chưa thắng MonthlyClimatology mọi kỳ (RMSE 2021–2023: 4.948 so với 4.823; 2022–2023: 5.015 so với 4.996). Cần giữ đối chứng này.
5. Phân tích mức EC cao dùng P90 của tập huấn luyện, không dùng ngưỡng 100 mS/m của Mỹ Tho. Các phương án vẫn bỏ sót nhiều tháng cao; giảm MAE/RMSE chưa giải quyết bắt đỉnh.
6. Hướng thử tiếp: giữ hai ứng viên H và Q+H cho từng trạm, kiểm thêm các cửa sổ thời gian ít được xem, lỗi theo mùa/năm và mức cao trước khi chọn model phục vụ. Không cộng/gộp điểm từ ba kỳ chồng lấn.
7. Chưa kiểm chứng mức giảm sai số toàn tuyến: không có tập EC độc lập giữa các trạm trong lượt này.

## Kiểm chứng và giới hạn

- Hoàn tất 12 tổ hợp trạm × độ trễ × cửa sổ; 2.880 giá trị dự báo (bao gồm đối chứng), 270 hàng metrics theo các nhóm.
- Tính lại MAE/RMSE toàn kỳ từ predictions.csv và kiểm SHA-256 đầu ra đều đạt. Registry giữ nguyên checksum.
- Các kỳ lịch sử đã được xem; đây là sàng lọc hồi cứu, không phải kiểm định mù. Chưa tối ưu độ trễ hoặc siêu tham số. Chưa có nhãn EC sau 2023 để kiểm định dự báo hiện tại.
- Tệp protocol.json ghi danh sách biến, nguồn và checksum, phiên bản thư viện, tham số và giới hạn.
