import { node, num } from '../../shared/ui.js';
import { listPendingFieldMeasurements, reviewFieldMeasurement } from './field-measurement-api.js';

export function createFieldMeasurementReviewQueue(host, onReviewed = () => {}) {
  const panel = node('details'); panel.open = true;
  panel.append(node('summary', 'Hàng chờ duyệt · cán bộ kiểm tra'));
  const status = node('p', 'Đang đọc hàng chờ…', 'subtle');
  const queue = node('div');
  const more = node('button', 'Tải thêm phiếu', 'secondary'); more.type = 'button'; more.hidden = true;
  panel.append(status, queue, more); host.append(panel);
  let cursor = null, loaded = 0, serial = 0;
  async function load(append = false) {
    const ticket = ++serial;
    if (!append) { cursor = null; loaded = 0; queue.replaceChildren(); }
    more.disabled = true;
    try {
      const data = await listPendingFieldMeasurements(cursor);
      if (ticket !== serial) return;
      if (!Array.isArray(data.items) || !Number.isSafeInteger(data.total)) throw new Error('Trang hàng chờ không hợp lệ.');
      for (const item of data.items || []) {
        const row = node('article', undefined, 'source-card');
        row.append(node('p', `${item.measurement_id} · ${num(item.ec_mS_m)} mS/m · ${item.observed_at} · ${item.submitted_by}`));
        const note = node('input'); note.type = 'text'; note.placeholder = 'Ghi chú duyệt'; row.append(note);
        for (const decision of ['APPROVED', 'REJECTED']) {
          const button = node('button', decision === 'APPROVED' ? 'Duyệt' : 'Từ chối', 'secondary'); button.type = 'button';
          button.addEventListener('click', async () => {
            button.disabled = true;
            try {
              await reviewFieldMeasurement(item.measurement_id, decision, note.value);
              await load(); onReviewed();
            } catch (error) { status.textContent = error.message; button.disabled = false; }
          });
          row.append(button);
        }
        queue.append(row);
      }
      loaded += data.items.length;
      cursor = data.next_cursor;
      more.hidden = !data.has_more;
      status.textContent = `Đang hiển thị ${loaded}/${data.total} phiếu chờ duyệt.`;
    } catch (error) { if (ticket === serial) status.textContent = error.message; }
    finally { if (ticket === serial) more.disabled = false; }
  }
  more.addEventListener('click', () => load(true));
  load();
  return load;
}
