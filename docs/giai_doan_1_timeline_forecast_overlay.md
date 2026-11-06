# Giai đoạn 1 — Timeline hợp lệ và lớp sông dự báo

**Cập nhật 04/11/2026:** lớp phủ hiện dùng ba điểm neo và hai chặng qua Mỹ Thuận. Form gọi thêm hai trạm; RF_compact cũng lấy hai model bổ sung cho cùng tháng. Các mô tả hai trạm/280 lát dưới đây ghi lại giai đoạn 1 trước tích hợp. Hợp đồng mới và kết quả kiểm tra ở [Bước 3](tich_hop_mythuan_buoc_3_2026-11-04.md).

Triển khai ngày 01/11/2026. Đọc trực tiếp `simulation_timeline()` và API đang chạy xác nhận **495 tháng, 1985-06 → 2026-08**, mỗi frame có **35 đoạn sông** và 27 cống nền.

## Chọn tháng

Thanh trượt dùng chỉ số của `timeline.items`; bộ chọn tháng chỉ có các tháng trong danh sách này. `resolveValidTimelineMonth()` và bộ nạp frame cùng kiểm tra danh sách tháng do API công bố. Tháng ngoài biên được kẹp về đầu/cuối chuỗi; tháng nằm trong khoảng trống dùng tháng hợp lệ gần nhất trước đó, theo logic tham chiếu. Danh sách rỗng không gọi API frame.

Ví dụ dự báo 2026-10 vẫn giữ tháng mục tiêu 2026-10, nhưng hình học nền lấy frame 2026-08. Timeline hiện thông báo chuyển tháng trước khi gọi API. Nhãn nguồn hiện rõ ở ranh 2023-12/2024-01, kể cả trong bố cục Timeline thu gọn. Các cờ nguồn MRC, ước tính và nội suy trong frame gốc được giữ nguyên.

## Áp dụng và khôi phục

- Form 5 biến: nút áp dụng lấy kết quả đang xem và gọi thêm `/workspace/multivariate/predict` cho trạm còn lại, cùng tháng và chế độ đầu vào. Với `MANUAL`, dùng cùng ba điều kiện khí tượng của kịch bản; với `ARCHIVE`, API đọc khí tượng của từng trạm. Lượt bổ sung không ghi PostgreSQL.
- RF_compact 8 biến: dùng đúng `selected_prediction.predicted` của thí nghiệm Mỹ Tho, giữ nguồn thí nghiệm và độ trễ. EC Tân Châu lấy từ frame Timeline nền và được ghi rõ trên banner. P90 lấy từ `high_ec_metrics` của thí nghiệm; mặc định 60.42 mS/m khi không có ngưỡng. Thí nghiệm +35 ngày hiện dùng 60.6 mS/m.
- Nút khôi phục tại Form, thí nghiệm hoặc banner trả lại frame gốc, bao gồm các cống và ranh mặn. Đổi tháng bằng Timeline cũng thoát lớp dự báo. Kết quả API đến muộn sau khi đổi đầu vào hoặc khôi phục không được áp dụng lại.

`buildForecastOverlayFrame()` sao chép sâu dữ liệu. Các trường EC thực tế mà `smoothRiverSegments()` và `riverRibbon()` sử dụng là `start_ec_mS_m`, `end_ec_mS_m`, `ec_mS_m`; đồng thời có các tên trường trong logic tham chiếu. Dải màu gồm 280 lát hiển thị từ 35 đoạn gốc.

Tuyến thật đặt Tân Châu ở km 0, Mỹ Tho ở km 125 và cửa sông ở km 175. Vì vậy frame thực dùng tỷ lệ `clamp(chainage / 125, 0, 1)` để EC dự báo Mỹ Tho xuất hiện đúng vị trí trạm; 50 km sau Mỹ Tho giữ EC Mỹ Tho, không tự khuếch đại độ mặn cửa sông. GeoJSON không có mốc trạm dùng `axial_ratio_start/end`, hoặc chỉ số đoạn theo logic tham chiếu.

Lớp dự báo chỉ phục vụ sàng lọc không gian. Banner nêu rõ mô hình, tháng mục tiêu/nền, EC và nguồn tại trạm, P90, cảnh giác cao và hệ số quy đổi tham khảo 0.0064. Trạng thái cống và ranh mặn nền tạm ẩn để tránh gán kết quả cũ cho EC mới; phần đánh giá cống thuộc giai đoạn 2.

## Hợp đồng ngữ cảnh cho giai đoạn 2

Module `frontend/src/shared/forecast-map-overlay.js` xuất live binding `activeForecastContext`. Lắng nghe `workspace:active-forecast-context` trên `window`; `event.detail` là ngữ cảnh đang hiển thị hoặc `null` khi đã khôi phục/chưa có frame hợp lệ.

```js
{
  sourceModel: 'MULTIVARIATE_RF_5', // hoặc 'RF_compact'
  targetMonth: '2026-10',
  mythoEc: 17.372893,
  tanchauEc: 11.783164,
  p90Threshold: 60.42,
  isHighVigilance: false,
  // metadata bổ sung: tanchauBasis, experimentId, availabilityLagDays...
}
```

`isHighVigilance` luôn được tính lại bằng `mythoEc >= p90Threshold`. Sự kiện `workspace:simulation-frame` tiếp tục mang frame Timeline gốc; `workspace:display-simulation-frame` mang frame đang được vẽ. Module giai đoạn 2 có thể đọc ngữ cảnh dự báo mà không sửa bằng chứng quan trắc.

## Kiểm tra

```powershell
node --test tests/*.test.mjs frontend/src/features/gate-simulation-draft.test.js
npm.cmd --prefix frontend run build
```

Đã kiểm tra trên trình duyệt: Form dự báo 2026-10 kẹp nền về 2026-08; RF_compact +5 ngày 27.903151 mS/m và +35 ngày 22.022199 mS/m; khôi phục trả lại 27 cống; đổi tháng về 2023-12 hiển thị nhãn MRC và bỏ lớp dự báo.
