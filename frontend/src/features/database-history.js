import { createRequestGate, getStations, getDatasets, getHistory, localDate, recentRange } from '../api.js';
import { dateLabel, number, renderChart, describeSeries } from '../chart.js';

const PAGE_SIZE = 20;
function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}

/** Mount is offline; the user explicitly opens the PostgreSQL connection. */
export function createDatabaseHistory({ onSelectStation } = {}) {
  const host = document.getElementById('databaseHistoryHost');
  if (!host) throw new Error('Missing #databaseHistoryHost');
  const gate = createRequestGate();
  const state = { stations: [], datasets: [], dataset: null, rows: [], page: 0, busy: false, applied: null };
  const title = node('h3', 'Lịch sử quan trắc PostgreSQL');
  const intro = node('p', 'Tra cứu EC theo nguồn, trạm, khoảng thời gian và loại số đo.', 'muted');
  const connect = node('button', 'Kết nối và tải danh sách trạm');
  connect.type = 'button';
  const status = node('p', 'Chưa kết nối. Chế độ snapshot không tự kiểm tra PostgreSQL.', 'muted');
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  const form = node('form');
  const fields = node('fieldset');
  fields.append(node('legend', 'Nguồn dữ liệu và bộ lọc lịch sử'));
  const controls = node('div', undefined, 'filter-grid');
  function control(label, tag = 'select', type) {
    const wrapper = node('label', label);
    const input = node(tag);
    if (type) input.type = type;
    wrapper.append(input); controls.append(wrapper);
    return input;
  }
  const source = control('Nguồn');
  const station = control('Trạm');
  const kind = control('Loại số đo');
  kind.append(new Option('Quan trắc và ước tính', ''), new Option('Quan trắc (O)', 'O'), new Option('Ước tính (E)', 'E'));
  const from = control('Từ ngày (UTC+7)', 'input', 'date');
  const to = control('Đến ngày (UTC+7)', 'input', 'date');
  const actions = node('div', undefined, 'actions');
  const apply = node('button', 'Tải lịch sử'); apply.type = 'submit';
  const full = node('button', 'Toàn bộ thời gian'); full.type = 'button';
  const csv = node('button', 'Xuất CSV đã lọc'); csv.type = 'button';
  actions.append(apply, full, csv); fields.append(controls, actions); form.append(fields);
  const metrics = node('p');
  const chart = node('div', undefined, 'history-chart');
  const legend = node('p', 'EC: mS/m. Điểm rỗng là ước tính (E); đường nối ngắt tại tháng thiếu hoặc số đo không hợp lệ.', 'muted');
  const scroll = node('div', undefined, 'table-wrap'); scroll.style.overflowX = 'auto';
  const table = node('table');
  table.append(node('caption', 'Lịch sử EC theo giờ Việt Nam (UTC+7)'));
  const head = node('thead'); const header = node('tr');
  for (const label of ['Ngày', 'EC (mS/m)', 'Loại']) {
    const cell = node('th', label); cell.scope = 'col'; header.append(cell);
  }
  head.append(header); const body = node('tbody'); table.append(head, body); scroll.append(table);
  const pager = node('div', undefined, 'actions');
  const prev = node('button', 'Trang trước'); prev.type = 'button';
  const next = node('button', 'Trang sau'); next.type = 'button';
  const page = node('span'); pager.append(prev, page, next);
  host.replaceChildren(title, intro, connect, status, form, metrics, chart, legend, scroll, pager);

  function sync() {
    host.setAttribute('aria-busy', String(state.busy));
    connect.disabled = state.busy;
    fields.disabled = state.busy || !state.stations.length;
    apply.disabled = full.disabled = !state.dataset;
    csv.disabled = state.busy || !state.rows.length || !state.applied;
    prev.disabled = state.busy || state.page === 0;
    next.disabled = state.busy || (state.page + 1) * PAGE_SIZE >= state.rows.length;
  }
  function renderTable() {
    body.replaceChildren();
    const start = state.page * PAGE_SIZE;
    for (const row of state.rows.slice(start, start + PAGE_SIZE)) {
      const tr = node('tr'); const date = node('td', dateLabel(row.observed_at)); date.title = row.observed_at;
      tr.append(date, node('td', number(row.conductivity_ms_per_m)), node('td', row.observed_or_estimated === 'O' ? 'Quan trắc (O)' : 'Ước tính (E)'));
      body.append(tr);
    }
    if (!state.rows.length) {
      const tr = node('tr'); const td = node('td', 'Chưa có số đo trong lựa chọn này.'); td.colSpan = 3; tr.append(td); body.append(tr);
    }
    page.textContent = state.rows.length ? `${start + 1}–${Math.min(start + PAGE_SIZE, state.rows.length)} / ${number(state.rows.length)} dòng` : '0 dòng';
    sync();
  }
  function clear(message) {
    state.rows = []; state.page = 0; state.applied = null;
    chart.replaceChildren(node('p', message)); metrics.textContent = ''; renderTable();
  }
  function fail(error) { status.textContent = error.message || 'Không tải được dữ liệu. Hãy thử kết nối lại.'; status.dataset.state = 'error'; }
  function chooseDataset() {
    // The API orders imports newest first; keep one dataset per station.
    state.dataset = state.datasets[0] || null;
    from.value = to.value = ''; kind.value = '';
    if (state.dataset) {
      const d = state.dataset;
      if (d.first_observation && d.last_observation) {
        const range = recentRange(d); from.value = range.date_from; to.value = range.date_to;
      }
    }
    clear('Chọn bộ lọc rồi tải lịch sử EC.');
    status.textContent = state.dataset ? 'Đã chọn trạm. Nhấn Tải lịch sử để đọc số đo.' : 'Trạm chưa có dữ liệu EC trong PostgreSQL.';
  }
  async function selectStation(code) {
    const feature = state.stations.find(item => item.properties.site_code === code);
    if (!feature) return;
    const req = gate.next(); state.busy = true;
    station.value = code; state.datasets = []; state.dataset = null;
    from.value = to.value = ''; kind.value = '';
    clear('Đang tải dữ liệu của trạm…');
    status.textContent = 'Đang tải dữ liệu của trạm…';
    try {
      const datasets = await getDatasets(code, req);
      if (!req.isCurrent()) return;
      state.datasets = datasets;
      chooseDataset();
      if (!state.datasets.length) status.textContent = 'Trạm chưa có bộ dữ liệu EC trong PostgreSQL.';
      onSelectStation?.(code, feature);
    } catch (error) { if (req.isCurrent() && error.name !== 'AbortError') fail(error); }
    finally { if (req.isCurrent()) { state.busy = false; sync(); } }
  }
  function chooseSource() {
    gate.next(); state.busy = false; state.dataset = null; state.datasets = [];
    const choices = state.stations.filter(f => !source.value || f.properties.source_code === source.value);
    station.replaceChildren(new Option('Chọn trạm', ''), ...choices.map(f => new Option(`${f.properties.site_name} · ${f.properties.site_code}`, f.properties.site_code)));
    from.value = to.value = ''; kind.value = '';
    clear('Chọn trạm để tra cứu lịch sử EC.');
    status.textContent = `${choices.length} trạm trong nguồn đã chọn.`;
  }
  async function load() {
    const req = gate.next(); state.busy = true;
    state.stations = []; state.datasets = []; state.dataset = null;
    source.replaceChildren(); station.replaceChildren();
    clear('Đang kết nối PostgreSQL…'); status.textContent = 'Đang tải danh sách trạm từ PostgreSQL…'; status.dataset.state = 'loading';
    try {
      const collection = await getStations(req);
      if (!req.isCurrent()) return;
      state.stations = collection.features;
      const sources = new Map(state.stations.map(f => [f.properties.source_code, f.properties.source_name || f.properties.source_code]));
      source.replaceChildren(new Option('Tất cả nguồn', ''), ...Array.from(sources, ([code, label]) => new Option(label, code)));
      chooseSource();
      status.textContent = state.stations.length ? `Đã kết nối · ${state.stations.length} trạm. Chọn nguồn và trạm để tiếp tục.` : 'PostgreSQL chưa có trạm. Nhập dữ liệu rồi kết nối lại.';
      status.dataset.state = 'ready';
    } catch (error) { if (req.isCurrent() && error.name !== 'AbortError') fail(error); }
    finally { if (req.isCurrent()) { state.busy = false; sync(); } }
  }
  async function loadHistory() {
    if (!state.dataset) return;
    if (from.value && to.value && from.value > to.value) { fail(new Error('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.')); return; }
    const req = gate.next(); state.busy = true;
    const selection = { site: station.value, dataset: state.dataset.dataset_code, date_from: from.value, date_to: to.value, observed_or_estimated: kind.value };
    clear('Đang tải lịch sử…'); status.textContent = 'Đang tải số đo…';
    try {
      const history = await getHistory(selection.site, selection.dataset, selection, { ...req, onProgress: (count, total) => { if (req.isCurrent()) status.textContent = `Đã tải ${number(count)} / ${number(total)} số đo…`; } });
      if (!req.isCurrent()) return;
      state.rows = history.items; state.applied = selection;
      renderChart(chart, state.rows, { showQuality: false }); renderTable();
      const summary = describeSeries(state.rows);
      metrics.textContent = `${number(summary.count)} số đo · Trung bình: ${summary.mean === null ? '—' : number(summary.mean)} mS/m · Cao nhất: ${summary.max === null ? '—' : number(summary.max)} mS/m${summary.excluded ? ` · ${number(summary.excluded)} số đo không hợp lệ được bỏ qua khi tính thống kê.` : '.'}`;
      status.textContent = `Đã áp dụng: ${selection.site} · ${selection.date_from || 'đầu chuỗi'} đến ${selection.date_to || 'cuối chuỗi'} · ${selection.observed_or_estimated === 'O' ? 'Quan trắc (O)' : selection.observed_or_estimated === 'E' ? 'Ước tính (E)' : 'Quan trắc và ước tính'}.`;
      status.dataset.state = 'ready';
    } catch (error) { if (req.isCurrent() && error.name !== 'AbortError') fail(error); }
    finally { if (req.isCurrent()) { state.busy = false; sync(); } }
  }
  connect.addEventListener('click', load);
  source.addEventListener('change', chooseSource);
  station.addEventListener('change', () => { if (station.value) selectStation(station.value); else chooseSource(); });
  form.addEventListener('submit', event => { event.preventDefault(); loadHistory(); });
  for (const input of [from, to, kind]) input.addEventListener('input', () => {
    state.applied = null; sync(); status.textContent = 'Bộ lọc đã đổi. Biểu đồ và bảng vẫn là lần tải trước; nhấn Tải lịch sử để cập nhật và xuất CSV.';
  });
  full.addEventListener('click', () => {
    if (!state.dataset) return;
    from.value = state.dataset.first_observation ? localDate(state.dataset.first_observation) : '';
    to.value = state.dataset.last_observation ? localDate(state.dataset.last_observation) : '';
    loadHistory();
  });
  prev.addEventListener('click', () => { state.page--; renderTable(); });
  next.addEventListener('click', () => { state.page++; renderTable(); });
  csv.addEventListener('click', () => {
    if (!state.applied || !state.rows.length) return;
    // Quote every field and neutralize spreadsheet formulas in source metadata.
    const cell = value => `"${String(value ?? '').replace(/^[=+@\-\t\r]/, "'$&").replaceAll('"', '""')}"`;
    const columns = ['site_code', 'dataset_code', 'observed_at', 'conductivity_ms_per_m', 'unit', 'observed_or_estimated', 'quality_flag', 'ec_observation_id'];
    const lines = [columns, ...state.rows.map(row => [state.applied.site, state.applied.dataset, row.observed_at, row.conductivity_ms_per_m, row.unit, row.observed_or_estimated, row.quality_flag, row.ec_observation_id])];
    const url = URL.createObjectURL(new Blob(['\uFEFF', lines.map(row => row.map(cell).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' }));
    const anchor = node('a'); anchor.href = url;
    anchor.download = `ec-history-${state.applied.site.replace(/[^a-zA-Z0-9_-]/g, '_')}.csv`;
    anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  clear('Kết nối PostgreSQL để tra cứu lịch sử quan trắc.');
  return { load, selectStation, destroy() { gate.next(); host.replaceChildren(); } };
}
