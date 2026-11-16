import { node } from '../../shared/ui.js';
import { listApprovedFieldMeasurements } from './field-measurement-api.js';

export function filterMappableApprovedItems(items) {
  return (items || []).filter(item => item.status === 'APPROVED' && Number.isFinite(item.longitude) && Number.isFinite(item.latitude));
}

export function loadApprovedFieldMeasurementsForMap(host) {
  const status = node('p', 'Đang tải phiếu đã duyệt…', 'subtle');
  host.append(node('h4', 'Phiếu đã duyệt trên bản đồ'), status);
  async function load() {
    try {
      const data = await listApprovedFieldMeasurements();
      const items = filterMappableApprovedItems(data.items);
      status.textContent = `${items.length} phiếu đã duyệt; ký hiệu tam giác trên bản đồ, không phải quan trắc MRC.`;
      window.dispatchEvent(new CustomEvent('workspace:approved-field-measurements', { detail: items }));
    } catch (error) { status.textContent = `Chưa tải được phiếu đã duyệt: ${error.message}`; }
  }
  load();
  return load;
}
