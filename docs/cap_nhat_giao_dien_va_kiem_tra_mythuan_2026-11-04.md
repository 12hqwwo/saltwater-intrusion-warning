# Cập nhật giao diện và kiểm tra EC Mỹ Thuận · 04/11/2026

## EC Mỹ Thuận đã có tới đâu?

Đã đối chiếu trực tiếp tệp `data/external/tien_multisite_20261029_verified/019804_Conductivity_Water Quality_4c105414.csv` với manifest cùng thư mục:

- Mã trạm `MRC_VN_019804` (Mỹ Thuận), khác `MRC_VN_019805` (Mỹ Tho).
- 451 mẫu EC, đơn vị mS/m, từ 15/05/1985 đến 15/12/2023.
- SHA-256 `efc3cd6136024f87708b2834a04dbcd3761f2e156625722a4d2ad71b24120482`, khớp manifest.
- Giữ cờ nguồn `UNVERIFIED`, cơ sở bù nhiệt `UNKNOWN`; không có mẫu EC Mỹ Thuận sau 2023 trong tệp này. Các tệp mực nước Mỹ Thuận 2024–2026 thuộc tham số khác.

Snapshot `data/research/workspace.json` sinh ngày 01/11/2026 chưa chứa trạm hoặc mẫu Mỹ Thuận. API đang chạy `/api/v1/workspace/stations`, chế độ `postgres`, cũng chỉ có 12 trạm (Mỹ Tho, Tân Châu và 10 điểm RIA2); chưa có Mỹ Thuận. Như vậy dữ liệu đã được tải để nghiên cứu, chưa tích hợp vào bộ quan trắc đang hiển thị. Đợt cập nhật này chỉ kiểm tra, chưa nạp dữ liệu vào database hoặc đổi mô hình.

## Giao diện

- Bỏ cột “Chất lượng nguồn” lặp lại “Nguồn chưa xác minh” trong bảng EC quan trắc. Các cột ngày, EC và minh chứng vẫn hiển thị; metadata và CSV vẫn giữ cờ chất lượng, O/E, nguồn và vị trí dòng.
- Bỏ cột “Nguồn và vị trí dòng” trong bảng rà soát số đo theo vị trí. Bảng còn ngày, giờ/kỳ đo, chế độ đo và độ mặn g/L. API/tệp nguồn không thay đổi.
- Theo lựa chọn của người dùng, gỡ biểu mẫu mô phỏng cống cũ cùng phần hồ sơ kịch bản liên quan. Giữ phiếu đo, RuleProfile, bảng tiêu chí và xuất JSON của engine giai đoạn 2. Không xóa các bản nháp đã lưu hoặc API backend cũ.
- Chọn cống từ bản đồ chuyển tới đúng phiếu hiện trường, không chép EC mô phỏng vào số đo thực tế. Nút dự báo đổi thành “Dùng dự báo để kiểm tra cống”, lấy ngữ cảnh dự báo hai trạm cho engine thay vì chuyển vào biểu mẫu đã bỏ.

## Kiểm chứng

```powershell
node --test tests/*.test.mjs frontend/src/features/gate-simulation-draft.test.js
npm.cmd --prefix frontend run build
```

138/138 kiểm thử đạt; production build thành công. Các kiểm thử của biểu mẫu cũ được thay bằng kiểm thử tích hợp chọn cống, giữ độc lập số đo và dự báo, tải danh mục PostgreSQL, chuyển cống từ bản đồ và loại phản hồi dự báo/trạm ứng viên đến muộn.

Đã kiểm tra trên trình duyệt: bảng EC còn 3 cột, bảng rà soát độ mặn còn 4 cột; biểu mẫu mô phỏng cũ đã được gỡ. Phiếu giai đoạn 2 trả về “Cần bổ sung hoặc đo lại” khi chưa có số đo. Chuyển dự báo đa biến vào cống cập nhật phần ngữ cảnh dự báo và giữ trống các số đo hiện trường. Không ghi nhận lỗi console.
