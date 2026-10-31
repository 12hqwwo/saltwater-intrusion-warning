// Illustrative scenario thresholds; these are not validated irrigation standards.
export const ADVISORY_PRESETS = {
  durian: { open_below_ec: 50, close_above_ec: 80 },
  citrus: { open_below_ec: 100, close_above_ec: 150 },
  rice: { open_below_ec: 120, close_above_ec: 200 },
};

export function cropAdvisories(ec) {
  const valid = typeof ec === 'number' && Number.isFinite(ec) && ec >= 0;
  return [['durian', 'Sầu riêng'], ['citrus', 'Cây có múi'], ['rice', 'Lúa']].map(([id, label]) => {
    const { open_below_ec: openBelowEc, close_above_ec: closeAboveEc } = ADVISORY_PRESETS[id];
    const status = !valid ? 'missing' : ec < openBelowEc ? 'below' : ec < closeAboveEc ? 'transition' : 'above';
    const text = {
      missing: 'Thiếu EC hợp lệ để đối chiếu',
      below: 'Dưới ngưỡng thấp của kịch bản · vẫn cần đo kiểm tại nơi lấy nước',
      transition: 'Trong vùng chuyển tiếp của kịch bản · cần đo kiểm trước khi cân nhắc lấy nước',
      above: 'Đạt hoặc vượt ngưỡng cao của kịch bản · cần đánh giá nguồn nước thay thế',
    }[status];
    return { id, label, openBelowEc, closeAboveEc, status, text };
  });
}
