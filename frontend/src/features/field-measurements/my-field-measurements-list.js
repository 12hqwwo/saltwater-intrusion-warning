import { node, num } from '../../shared/ui.js';
import { listMyFieldMeasurements } from './field-measurement-api.js';

export function createMyFieldMeasurementsList(host) {
  const details = node('details');
  details.append(node('summary', 'Phiếu của tôi'));
  const status = node('p', 'Đang tải phiếu của tôi…', 'subtle');
  const rows = node('div');
  details.append(status, rows); host.append(details);
  async function load() {
    try {
      const data = await listMyFieldMeasurements();
      rows.replaceChildren();
      for (const item of data.items || []) rows.append(node('p', `${item.measurement_id} · ${num(item.ec_mS_m)} mS/m · ${item.status} · ${item.observed_at}`));
      status.textContent = `${(data.items || []).length} phiếu đã gửi.`;
    } catch (error) { status.textContent = error.message; }
  }
  details.addEventListener('toggle', () => { if (details.open) load(); });
  return load;
}
