import { node } from '../../shared/ui.js';
import { listApprovedFieldMeasurements } from './field-measurement-api.js';

export function filterMappableApprovedItems(items) {
  return (items || []).filter(item => item.status === 'APPROVED' && Number.isFinite(item.longitude) && Number.isFinite(item.latitude));
}

export function loadApprovedFieldMeasurementsForMap(host) {
  const status = node('p', 'Đang tải phiếu đã duyệt…', 'subtle');
  host.append(node('h4', 'Phiếu đã duyệt trên bản đồ'), status);
  let serial = 0;
  async function load() {
    const ticket = ++serial;
    try {
      const all = [], seen = new Set();
      let cursor = null, total = 0;
      do {
        const data = await listApprovedFieldMeasurements(cursor);
        if (ticket !== serial) return;
        if (!Array.isArray(data.items) || !Number.isSafeInteger(data.total)) throw new Error('Trang phiếu đã duyệt không hợp lệ.');
        total = data.total;
        all.push(...data.items);
        if (!data.has_more) break;
        cursor = data.next_cursor;
        const key = JSON.stringify(cursor);
        if (!cursor || seen.has(key) || !data.items.length) throw new Error('Phân trang phiếu đã duyệt không nhất quán.');
        seen.add(key);
        status.textContent = `Đang tải ${all.length}/${total} phiếu đã duyệt…`;
      } while (true);
      const items = filterMappableApprovedItems(all);
      status.textContent = `${items.length}/${total} phiếu đã duyệt có tọa độ hợp lệ; ký hiệu tam giác trên bản đồ, không phải quan trắc MRC.`;
      window.dispatchEvent(new CustomEvent('workspace:approved-field-measurements', { detail: items }));
    } catch (error) { if (ticket === serial) status.textContent = `Chưa tải được phiếu đã duyệt: ${error.message}`; }
  }
  load.cancel = () => { serial++; };
  load();
  return load;
}
