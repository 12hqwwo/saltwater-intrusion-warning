import { requestJSON } from '../api.js';
import { node, num } from '../shared/ui.js';

export function issueRow(item) {
  const { slot, events = [], issue, score } = item;
  return {
    month: String(slot.target_month).slice(0, 7), station: slot.station_key,
    status: issue?.issue_status || (events.some(event => event.event_type === 'MISSED') ? 'MISSED' : 'SCHEDULED'),
    forecast: issue ? `${num(issue.predicted_ec_mS_m)} mS/m` : '—',
    label: score ? `${num(score.observed_ec_mS_m)} mS/m (${score.obs_source})` : 'Chưa có nhãn',
    error: score ? `${num(score.abs_error_mS_m)} mS/m` : '—',
  };
}

export function scoreSummary(summary) {
  const primary = summary.on_time_n_scored
    ? `Đúng hạn: MAE ${num(summary.on_time_mae_mS_m)} mS/m (n=${summary.on_time_n_scored}).`
    : 'Đúng hạn: chưa có EC tháng đủ điều kiện để chấm — mới kiểm chứng hạ tầng phát hành.';
  const late = summary.late_n_scored
    ? `Phát hành trễ: MAE ${num(summary.late_mae_mS_m)} mS/m (n=${summary.late_n_scored}), báo cáo riêng.`
    : 'Phát hành trễ: chưa có điểm đủ điều kiện.';
  return `${primary} ${late}`;
}

export function createForecastIssuePanel(host, { load = () => requestJSON('/forecast-issues') } = {}) {
  const panel = node('details', undefined, 'mv-issue-ledger');
  panel.append(node('summary', 'Sổ phát hành và sai số vận hành thật'));
  const note = node('p', 'Lịch MONTHLY_D06_PREV: 09:00 ngày 06 tháng trước. Bản MISSED và LATE được giữ riêng; dự báo đã lưu thủ công không phải bản phát hành mù.', 'subtle');
  const refresh = node('button', 'Làm mới sổ phát hành', 'secondary'); refresh.type = 'button';
  const status = node('p', 'Chưa tải sổ phát hành.', 'subtle');
  const metrics = node('p', '', 'subtle');
  const table = node('table'), head = node('thead'), header = node('tr'), body = node('tbody');
  for (const title of ['Tháng', 'Trạm', 'Trạng thái', 'Dự báo', 'Nhãn EC', 'Sai số tuyệt đối']) header.append(node('th', title));
  head.append(header); table.append(head, body);
  panel.append(note, refresh, status, metrics, table);
  host.append(panel);

  async function reload() {
    status.textContent = 'Đang đọc sổ phát hành…';
    refresh.disabled = true;
    try {
      const report = await load();
      if (!Array.isArray(report.items) || !report.summary) throw new Error('Sổ phát hành không đúng cấu trúc.');
      body.replaceChildren();
      for (const item of report.items) {
        const values = issueRow(item), row = node('tr');
        row.dataset.status = values.status;
        for (const key of ['month', 'station', 'status', 'forecast', 'label', 'error']) row.append(node('td', values[key]));
        body.append(row);
      }
      metrics.textContent = scoreSummary(report.summary);
      status.textContent = report.items.length ? `${report.items.length} slot trong sổ.` : 'Chưa có slot nào. Chưa có dữ liệu chấm vận hành.';
    } catch (error) {
      status.textContent = `Không đọc được sổ phát hành: ${error.message}`;
    } finally {
      refresh.disabled = false;
    }
  }
  refresh.addEventListener('click', reload);
  reload();
  return { reload };
}
