import { node, num } from '../shared/ui.js';

const localTime = value => new Date(value).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false });
const CHECK_LABELS = { PASSED: 'Đạt', FAILED: 'Không đạt', MISSING_OR_EXPIRED: 'Cần bổ sung / đo lại' };

export function createGateIntakeEvaluationDetails() {
  const expiry = node('p', '', 'subtle'); expiry.id = 'gateIntakeExpiry';
  const table = node('table', undefined, 'gate-intake-checks'), head = node('thead'), header = node('tr'), rows = node('tbody');
  rows.id = 'gateIntakeCriteria';
  for (const text of ['Điều kiện', 'Kết quả', 'Số đo / khai báo', 'Ngưỡng kiểm tra', 'Giải thích']) header.append(node('th', text));
  head.append(header); table.append(head, rows);
  const wrap = node('div', undefined, 'table-wrap'); wrap.append(table);
  function clear() { expiry.textContent = ''; rows.replaceChildren(); }
  function render(result) {
    expiry.textContent = `Đánh giá ${localTime(result.evaluatedAtIso)} (GMT+7). ${result.validUntilIso ? `Đề xuất có hiệu lực đến ${localTime(result.validUntilIso)} (GMT+7).`
      : 'Chưa có đề xuất lấy nước còn hiệu lực.'}${result.sampleAgeHours !== null ? ` Tuổi mẫu ${num(result.sampleAgeHours)} giờ; giới hạn ${result.forecastAdvisory.effectiveMaxSampleAgeHours} giờ.` : ''}`;
    rows.replaceChildren();
    const units = { SAMPLE_FRESHNESS: 'giờ', EXTERIOR_EC: 'mS/m', INTERIOR_EC: 'mS/m', HYDRAULIC_HEAD_DIFF: 'm' };
    const display = (value, id) => value === null ? '—' : typeof value === 'boolean' ? value ? 'Đã xác nhận' : 'Chưa xác nhận'
      : typeof value === 'number' ? `${num(value)} ${units[id] || ''}`.trim() : String(value);
    for (const check of result.criteriaChecks) {
      const row = node('tr'); row.dataset.status = check.status;
      const comparison = ['SAMPLE_FRESHNESS', 'EXTERIOR_EC', 'INTERIOR_EC'].includes(check.id) ? '≤ ' : check.id === 'HYDRAULIC_HEAD_DIFF' ? '≥ ' : '';
      for (const value of [check.label, CHECK_LABELS[check.status], display(check.observedValue, check.id), comparison + display(check.thresholdValue, check.id), check.explanation]) row.append(node('td', value));
      rows.append(row);
    }
  }
  return { expiry, wrap, clear, render };
}
