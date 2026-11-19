import { node, num } from '../../shared/ui.js';
import { listMyFieldMeasurements } from './field-measurement-api.js';

export function createMyFieldMeasurementsList(host) {
  const details = node('details');
  details.append(node('summary', 'Phiếu của tôi'));
  const status = node('p', 'Đang tải phiếu của tôi…', 'subtle');
  const rows = node('div');
  const more = node('button', 'Tải thêm phiếu', 'secondary'); more.type = 'button'; more.hidden = true;
  details.append(status, rows, more); host.append(details);
  let cursor = null, loaded = 0, serial = 0;
  async function load(append = false) {
    const ticket = ++serial;
    if (!append) { cursor = null; loaded = 0; rows.replaceChildren(); }
    more.disabled = true;
    try {
      const data = await listMyFieldMeasurements(cursor);
      if (ticket !== serial) return;
      if (!Array.isArray(data.items) || !Number.isSafeInteger(data.total)) throw new Error('Trang phiếu của tôi không hợp lệ.');
      for (const item of data.items || []) rows.append(node('p', `${item.measurement_id} · ${num(item.ec_mS_m)} mS/m · ${item.status} · ${item.observed_at}`));
      loaded += data.items.length;
      cursor = data.next_cursor;
      more.hidden = !data.has_more;
      status.textContent = `Đang hiển thị ${loaded}/${data.total} phiếu đã gửi.`;
    } catch (error) { if (ticket === serial) status.textContent = error.message; }
    finally { if (ticket === serial) more.disabled = false; }
  }
  more.addEventListener('click', () => load(true));
  details.addEventListener('toggle', () => { if (details.open) load(); });
  return load;
}
