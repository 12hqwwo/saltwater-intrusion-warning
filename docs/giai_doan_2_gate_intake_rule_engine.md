# Giai đoạn 2 · Engine kiểm tra điều kiện xem xét lấy nước tại cống

## Hợp đồng và phạm vi

`frontend/src/shared/gate-intake-rules.js` định nghĩa `DEFAULT_GATE_RULE_PROFILE`, `deriveForecastAdvisoryForGate` và hàm thuần:

```js
evaluateGateIntakeCondition(measurementInput, ruleProfile, forecastContext, evaluationTimeIso)
```

Module `gate-simulation-draft.js` tái xuất các API này. Thời điểm đánh giá được truyền rõ bằng ISO có múi giờ để cùng đầu vào luôn cho cùng kết quả. Không đọc đồng hồ hệ thống, không ghi dữ liệu và không phát lệnh vận hành trong engine.

RuleProfile mặc định `MYTHO_TIEN_RIVER_INTAKE_SCREENING / TECH_SCREENING_RULE_V1.0` có tên, ghi chú nguồn gốc và các ngưỡng:

| Thuộc tính | Mặc định | Điều kiện |
| --- | --- | --- |
| maxExteriorEcMsM | 156.25 mS/m | EC ngoài ≤ ngưỡng |
| maxInteriorEcMsM | 125 mS/m | EC trong ≤ ngưỡng |
| minPositiveHeadDiffM | 0.05 m | H ngoài − H trong ≥ ngưỡng |
| requireSameDatum | true | Chỉ tính ΔH khi sameElevationDatum === true |
| requireMechanicalReady | true | mechanicalStatus === READY |
| maxSampleAgeHoursNormal | 6 giờ | Tuổi mẫu ≤ thời hạn |
| maxSampleAgeHoursHighVigilance | 2 giờ | Tuổi mẫu khi cảnh giác cao ≤ thời hạn |
| p90ReferenceEcMsM | 60.42 mS/m | Ngưỡng Mỹ Tho dự phòng nếu ngữ cảnh không cung cấp P90 |

Quy đổi tham khảo 156.25 × 0.0064 ≈ 1.0 g/L không thay đổi đơn vị EC dùng để đánh giá. Ngưỡng và thời hạn có thể chỉnh trong giao diện; cấu hình chỉnh mang hậu tố `+CUSTOM` và toàn bộ RuleProfile được ghi trong JSON kết quả.

Thông báo cố định: “Quy tắc kỹ thuật cấu hình để kiểm tra nhất quán trên WebGIS (không thay thế quy trình vận hành pháp lý của đơn vị quản lý công trình)”.

## Dữ liệu và thứ tự kết luận

Bộ đo bắt buộc gồm EC hai phía, mực nước hai phía, xác nhận cùng hệ cao độ, thời điểm đo, trạng thái cơ khí và người/nguồn đo. Giao diện giả định các giá trị thuộc cùng một bộ đo tại một thời điểm. Múi giờ biểu mẫu là GMT+7. Số âm của mực nước được chấp nhận; EC phải không âm. Dữ liệu trống, boolean, đối tượng, số không hữu hạn hoặc thời điểm không tồn tại trên lịch bị từ chối. Mẫu ở tương lai dù chỉ 1 ms cũng không hợp lệ.

Kết luận ưu tiên theo yêu cầu mô tả (khác thứ tự FAILED trước trong đoạn mã tham chiếu):

1. Có tiêu chí `MISSING_OR_EXPIRED` → `INSUFFICIENT_OR_EXPIRED_DATA` / “Cần bổ sung hoặc đo lại”.
2. Dữ liệu đầy đủ, còn hạn nhưng có `FAILED` → `NOT_SUITABLE` / “Chưa phù hợp để lấy nước”.
3. Tất cả đạt → `ELIGIBLE_FOR_REVIEW` / “Đề nghị xem xét lấy nước”.

Mọi vi phạm vẫn được giữ trong bảng kể cả khi dữ liệu thiếu/quá hạn. `criteriaChecks` ghi `id`, `label`, `status`, `observedValue`, `thresholdValue`, `explanation`. Các giá trị số giữ dạng số theo đơn vị trong tên trường/nhãn. `validUntilIso` chỉ có khi đủ điều kiện xem xét; `sampleExpiresAtIso` cho biết hạn mẫu ngay cả khi có tiêu chí không đạt. Mốc hết hạn được tính từ lúc đo, không tính từ lúc nhấn đánh giá. Đúng mốc hết hạn vẫn được chấp nhận; sau mốc đó phải đo lại.

## Liên kết dự báo đa biến

Nhận ngữ cảnh Phase 1 qua `activeForecastContext` và sự kiện `workspace:active-forecast-context`, tương thích Form Đa biến 5 biến và RF_compact 8 biến. Cảnh giác cao được kích hoạt nếu ngữ cảnh bật cờ, Mỹ Tho ≥ P90, hoặc EC dự báo tại vị trí chiếu của cống ≥ 80% ngưỡng EC ngoài. Thời hạn mẫu tự chuyển 6 → 2 giờ (hoặc hai thời hạn trong cấu hình).

`gate-forecast-context.js` dùng chainage cống GIS hoặc chiếu tọa độ lên khung sông gốc. EC nội suy giữa Tân Châu km 0 và Mỹ Tho km 125; từ Mỹ Tho đến cửa sông km 175 giữ EC Mỹ Tho, nhất quán với lớp phủ Phase 1. Đây là chiếu hình học, chưa xác lập kết nối thủy lực. Khi thiếu vị trí, dùng Mỹ Tho làm ngữ cảnh thay thế có nhãn rõ; không khẳng định đó là EC tại cống. Khi chưa có dự báo, áp dụng thời hạn mặc định và hiển thị thiếu ngữ cảnh.

EC dự báo không tự điền vào EC thực đo. Các cống GIS được thêm vào danh sách chọn. Cập nhật 04/11/2026 theo yêu cầu người dùng: đã gỡ biểu mẫu mô phỏng và phần hồ sơ kịch bản cũ khỏi giao diện; giữ phiếu hiện trường giai đoạn 2. Dữ liệu bản nháp đã lưu và các API backend cũ không bị xóa. Xem [ghi nhận cập nhật](cap_nhat_giao_dien_va_kiem_tra_mythuan_2026-11-04.md).

## Giao diện và kiểm chứng

`gate-intake-screening.js` hiển thị Phần A (nguồn/tháng/EC dự báo, mức cảnh giác, hạn mẫu), Phần B (phiếu hiện trường, bảng từng tiêu chí, kết luận, hạn đề xuất) và xuất JSON. Thay đổi số đo/quy tắc xóa kết luận cũ. Thay ngữ cảnh dự báo hoặc vị trí chiếu tự đánh giá lại phiếu đã kiểm tra. Hẹn giờ lúc hết hạn và kiểm tra lại khi tab được kích hoạt tránh giữ đề xuất cũ sau thời gian treo trình duyệt.

Chạy kiểm thử và build từ thư mục gốc:

```powershell
node --test tests/*.test.mjs frontend/src/features/gate-simulation-draft.test.js
npm.cmd --prefix frontend run build
```

Các test mới bao phủ ba kết luận, ưu tiên thiếu/quá hạn, biên EC/ΔH/thời hạn, lịch và múi giờ, dự báo P90/80%/cờ cảnh giác, cấu hình tùy chỉnh, tính thuần, chiếu vị trí cống, cập nhật dự báo trực tiếp và tự hết hạn trên giao diện. Số đo khai báo chưa được máy chủ xác minh; kết quả yêu cầu người vận hành xem xét.

Kết quả ngày 01/11/2026: **140/140 kiểm thử frontend đạt**, gồm 42 kiểm thử bổ sung; Vite production build thành công. Kiểm tra trình duyệt xác nhận ba kết luận, chọn cống GIS, kết nối Form Đa biến 5 biến và mẫu hơn 3 giờ chuyển thành quá hạn khi quy tắc cảnh giác cao áp dụng thời hạn 2 giờ. Bản build cuối được tải lại và kiểm tra không có lỗi JavaScript trong console.
