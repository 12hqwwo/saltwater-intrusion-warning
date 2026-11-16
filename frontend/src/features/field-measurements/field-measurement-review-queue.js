import { node, num } from '../../shared/ui.js';
import { listPendingFieldMeasurements, reviewFieldMeasurement } from './field-measurement-api.js';

export function createFieldMeasurementReviewQueue(host, onReviewed = () => {}) {
  const panel = node('details'); panel.open = true;
  panel.append(node('summary', 'Hàng chờ duyệt · cán bộ kiểm tra'));
  const status = node('p', 'Đang đọc hàng chờ…', 'subtle');
  const queue = node('div'); panel.append(status, queue); host.append(panel);
  async function load() {
    try {
      const data = await listPendingFieldMeasurements();
      queue.replaceChildren();
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
      status.textContent = `${(data.items || []).length} phiếu đang chờ duyệt.`;
    } catch (error) { status.textContent = error.message; }
  }
  load();
  return load;
}
