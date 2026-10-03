import 'ol/ol.css';
import { APIError, createRequestGate, getDatasets, getHistory, getStations, localDate, recentRange, requestJSON } from './api.js';
import { createStationMap, hasCoordinates } from './map.js';
import { dateLabel, describeSeries, number, QUALITY_LABELS, renderChart } from './chart.js';
import './style.css';

const $ = id => document.getElementById(id);
const state = { stations: [], site: null, datasets: [], dataset: null, rows: [], tablePage: 0, busy: false };
const requests = createRequestGate();
const TABLE_SIZE = 20;
const map = createStationMap($('map'), {
  onSelect: code => selectStation(code),
  onTileError: () => { if ($('basemapToggle').checked) $('tileNotice').hidden = false; },
});

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function connection(status, label) {
  $('connectionStatus').dataset.state = status;
  $('connectionStatus').querySelector('span').textContent = label;
}

function setBusy(value) {
  state.busy = value;
  $('filterFields').disabled = value || !state.dataset;
  $('datasetSelect').disabled = value || !state.datasets.length;
  $('historySection').setAttribute('aria-busy', String(value));
}

function showError(error) {
  $('alertText').textContent = error.message || 'Không thể tải dữ liệu. Vui lòng thử lại.';
  $('appAlert').hidden = false;
  connection('error', 'Chưa tải được dữ liệu');
}

function clearError() { $('appAlert').hidden = true; }

function resetHistory(message) {
  state.rows = [];
  state.tablePage = 0;
  for (const id of ['metricCount', 'metricMean', 'metricMax']) $(id).textContent = '—';
  $('chart').replaceChildren(element('p', message, 'empty-chart'));
  $('qualityNotice').hidden = true;
  $('appliedRange').textContent = 'Thời gian hiển thị theo giờ Việt Nam (UTC+7).';
  $('loadStatus').textContent = message;
  renderTable();
}

function stationSymbol() {
  const span = element('span', undefined, 'station-symbol');
  span.setAttribute('aria-hidden', 'true');
  // Fixed decorative markup only. API text is always inserted with textContent.
  span.innerHTML = '<svg viewBox="0 0 24 30"><path d="M12 28S3 17 3 11a9 9 0 1 1 18 0c0 6-9 17-9 17Z"/><circle cx="12" cy="11" r="3"/></svg>';
  return span;
}

function renderStations() {
  $('stationList').replaceChildren();
  $('stationCount').textContent = state.stations.length;
  if (!state.stations.length) {
    $('stationList').append(element('p', 'Chưa có trạm trong dữ liệu nguồn.', 'muted small'));
    return;
  }
  for (const feature of state.stations) {
    const props = feature.properties;
    const button = element('button', undefined, 'station-button');
    button.type = 'button';
    button.dataset.site = props.site_code;
    button.setAttribute('aria-pressed', String(state.site?.properties.site_code === props.site_code));
    const label = element('span');
    label.append(element('strong', props.site_name), element('small', hasCoordinates(feature) ? props.site_code : `${props.site_code} · Thiếu vị trí`));
    button.append(stationSymbol(), label, element('span', undefined, 'chosen-dot'));
    button.addEventListener('click', () => selectStation(props.site_code));
    $('stationList').append(button);
  }
}

function renderSiteMetadata() {
  const props = state.site.properties;
  $('siteCode').textContent = props.site_code;
  $('coordinates').textContent = hasCoordinates(state.site) ? state.site.geometry.coordinates.slice(0, 2).map(v => v.toFixed(8)).join(', ') : 'Chưa có tọa độ';
  const names = { REPORTED: 'Có nguồn khai báo · REPORTED', VERIFIED: 'Đã xác minh vị trí · VERIFIED', UNKNOWN: 'Chưa rõ vị trí · UNKNOWN' };
  $('locationStatus').textContent = names[props.location_status] || props.location_status;
  $('locationReference').textContent = props.location_reference || 'Chưa có';
  $('sourceName').textContent = props.source_name || props.source_code;
  $('sourceReference').textContent = props.source_reference || 'Chưa có';
  $('historyTitle').textContent = `${props.site_name} · EC`;
}

function resetDatasetMetadata() {
  for (const id of ['datasetCode', 'sourceFilename', 'datasetHash']) $(id).textContent = '—';
}

async function selectStation(code) {
  const selected = state.stations.find(feature => feature.properties.site_code === code);
  if (!selected) return;
  const request = requests.next();
  state.site = selected;
  state.datasets = [];
  state.dataset = null;
  map.select(code);
  // Keep existing station buttons to preserve keyboard focus during selection.
  for (const button of $('stationList').querySelectorAll('button[data-site]')) {
    button.setAttribute('aria-pressed', String(button.dataset.site === code));
  }
  renderSiteMetadata();
  resetDatasetMetadata();
  $('datasetSelect').replaceChildren(new Option('Đang tải bộ dữ liệu…', ''));
  $('datasetHint').textContent = 'Đang đối chiếu các bộ dữ liệu của trạm.';
  $('dateFrom').value = '';
  $('dateTo').value = '';
  $('qualityFilter').value = '';
  $('kindFilter').value = '';
  clearError();
  resetHistory('Đang tải bộ dữ liệu của trạm…');
  setBusy(true);
  try {
    const datasets = await getDatasets(code, request);
    if (!request.isCurrent()) return;
    state.datasets = datasets;
    $('datasetSelect').replaceChildren(new Option(datasets.length ? 'Chọn một bộ dữ liệu' : 'Chưa có quan trắc EC', ''));
    for (const dataset of datasets) {
      $('datasetSelect').append(new Option(
        `${dateLabel(dataset.imported_at)} · ${number(dataset.observation_count)} số đo · ${dataset.sha256.slice(0, 8)}`,
        dataset.dataset_code,
      ));
    }
    setBusy(false);
    connection('ready', 'Đã kết nối dữ liệu');
    if (datasets.length === 1) {
      $('datasetSelect').value = datasets[0].dataset_code;
      await selectDataset(datasets[0].dataset_code);
    } else {
      $('datasetHint').textContent = datasets.length ? 'Có nhiều phiên bản. Chọn một bộ để xem; dữ liệu không được gộp giữa các phiên bản.' : 'Trạm này chưa có bộ dữ liệu EC.';
      resetHistory(datasets.length ? 'Chọn một bộ dữ liệu để xem lịch sử EC.' : 'Trạm chưa có quan trắc EC.');
    }
  } catch (error) {
    if (!request.isCurrent() || error.name === 'AbortError') return;
    $('datasetSelect').replaceChildren(new Option('Chưa tải được bộ dữ liệu', ''));
    $('datasetHint').textContent = 'Có thể thử tải lại bằng nút thông báo phía trên.';
    resetHistory('Chưa tải được dữ liệu của trạm.');
    showError(error);
  } finally {
    if (request.isCurrent()) setBusy(false);
  }
}

async function selectDataset(code) {
  state.dataset = state.datasets.find(dataset => dataset.dataset_code === code) || null;
  resetDatasetMetadata();
  if (!state.dataset) {
    requests.next();
    resetHistory('Chọn một bộ dữ liệu để xem lịch sử EC.');
    setBusy(false);
    return;
  }
  const d = state.dataset;
  $('datasetCode').textContent = d.dataset_code;
  $('sourceFilename').textContent = d.source_filename;
  $('datasetHash').textContent = d.sha256;
  $('datasetHint').textContent = `${number(d.observation_count)} số đo trong bộ nguồn. Quan trắc cuối: ${dateLabel(d.last_observation)}.`;
  const range = recentRange(d);
  $('dateFrom').value = range.date_from;
  $('dateTo').value = range.date_to;
  $('qualityFilter').value = '';
  $('kindFilter').value = '';
  await refreshHistory();
}

function readFilters() {
  const filters = {
    date_from: $('dateFrom').value, date_to: $('dateTo').value,
    quality_flag: $('qualityFilter').value, observed_or_estimated: $('kindFilter').value,
  };
  if (filters.date_from && filters.date_to && filters.date_from > filters.date_to) {
    throw new APIError('Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc.');
  }
  return filters;
}

function renderHistory(data) {
  state.rows = data.items;
  state.tablePage = 0;
  const stats = describeSeries(data.items);
  $('metricCount').textContent = number(stats.count);
  $('metricMean').textContent = stats.mean === null ? '—' : number(stats.mean);
  $('metricMax').textContent = stats.max === null ? '—' : number(stats.max);
  const start = data.filters.date_from || localDate(data.dataset.first_observation);
  const end = data.filters.date_to || localDate(data.dataset.last_observation);
  $('appliedRange').textContent = `${dateLabel(`${start}T00:00:00+07:00`)} – ${dateLabel(`${end}T00:00:00+07:00`)} · Giờ Việt Nam (UTC+7)`;
  $('loadStatus').textContent = `Đã tải đủ ${number(data.items.length)}/${number(data.total)} số đo theo bộ lọc.`;
  renderChart($('chart'), data.items);
  const counts = Object.fromEntries(Object.keys(QUALITY_LABELS).map(flag => [flag, data.items.filter(row => row.quality_flag === flag).length]));
  const notices = [];
  if (counts.UNVERIFIED) notices.push(`${number(counts.UNVERIFIED)} số đo chưa được xác minh chất lượng. UNVERIFIED không tự có nghĩa là số đo sai.`);
  if (counts.SUSPECT) notices.push(`${number(counts.SUSPECT)} số đo SUSPECT cần kiểm tra và vẫn có trong thống kê.`);
  if (stats.excluded) notices.push(`${number(stats.excluded)} số đo INVALID vẫn có trong bảng nhưng không được tính vào trung bình, cực đại hoặc đường nối.`);
  $('qualityNotice').textContent = notices.join(' ');
  $('qualityNotice').hidden = !notices.length;
  renderTable();
}

async function refreshHistory() {
  if (!state.site || !state.dataset) return;
  let filters;
  try { filters = readFilters(); } catch (error) { showError(error); return; }
  const request = requests.next();
  const code = state.site.properties.site_code;
  const datasetCode = state.dataset.dataset_code;
  clearError();
  resetHistory('Đang tải quan trắc theo bộ lọc…');
  setBusy(true);
  try {
    const data = await getHistory(code, datasetCode, filters, {
      ...request,
      onProgress(loaded, total) {
        if (request.isCurrent()) $('loadStatus').textContent = `Đang tải ${number(loaded)}/${number(total)} số đo…`;
      },
    });
    if (!request.isCurrent()) return;
    renderHistory(data);
    connection('ready', 'Đã kết nối dữ liệu');
  } catch (error) {
    if (!request.isCurrent() || error.name === 'AbortError') return;
    resetHistory('Chưa tải được lịch sử. Hãy thử lại để xem dữ liệu đầy đủ.');
    showError(error);
  } finally {
    if (request.isCurrent()) setBusy(false);
  }
}

function renderTable() {
  const first = state.tablePage * TABLE_SIZE;
  const rows = state.rows.slice(first, first + TABLE_SIZE);
  $('dataRows').replaceChildren();
  for (const row of rows) {
    const tr = element('tr');
    const date = element('td', dateLabel(row.observed_at));
    date.title = row.observed_at;
    const kind = element('td', row.observed_or_estimated === 'O' ? 'Quan trắc (O)' : 'Ước tính (E)');
    const quality = element('td');
    const badge = element('span', QUALITY_LABELS[row.quality_flag], 'quality-badge');
    badge.dataset.quality = row.quality_flag;
    badge.title = `${row.quality_flag} · ${row.approval_level || ''} · ${row.grade || ''}`;
    quality.append(badge);
    tr.append(date, element('td', number(row.conductivity_ms_per_m)), kind, quality);
    $('dataRows').append(tr);
  }
  if (!rows.length) {
    const tr = element('tr');
    const td = element('td', 'Chưa có số đo để hiển thị.');
    td.colSpan = 4;
    tr.append(td); $('dataRows').append(tr);
  }
  $('tableCount').textContent = `${number(state.rows.length)} dòng`;
  $('pageSummary').textContent = rows.length ? `${first + 1}–${first + rows.length} / ${number(state.rows.length)} số đo` : 'Chưa có dữ liệu';
  $('previousPage').disabled = state.tablePage === 0;
  $('nextPage').disabled = first + TABLE_SIZE >= state.rows.length;
}

async function bootstrap() {
  const request = requests.next();
  state.stations = []; state.datasets = []; state.dataset = null; state.site = null;
  clearError(); setBusy(true);
  connection('loading', 'Đang kết nối');
  $('stationList').replaceChildren(element('p', 'Đang tải danh sách trạm…', 'muted small'));
  resetHistory('Đang kết nối dữ liệu quan trắc…');
  try {
    const [health, collection] = await Promise.all([requestJSON('/health', request), getStations(request)]);
    if (!request.isCurrent()) return;
    if (health.status !== 'ok') throw new APIError('API chưa sẵn sàng. Hãy kiểm tra backend.');
    state.stations = collection.features;
    const located = map.setStations(collection);
    $('fitStations').disabled = !located;
    $('mapCount').textContent = `${located}/${collection.features.length} trạm có tọa độ`;
    renderStations();
    connection('ready', 'Đã kết nối dữ liệu');
    if (state.stations.length) await selectStation(state.stations[0].properties.site_code);
    else resetHistory('Chưa có trạm quan trắc trong database.');
  } catch (error) {
    if (!request.isCurrent() || error.name === 'AbortError') return;
    $('stationList').replaceChildren(element('p', 'Chưa tải được trạm. Hãy thử tải lại.', 'muted small'));
    resetHistory('Cần kết nối API để xem dữ liệu quan trắc.');
    showError(error);
  } finally {
    if (request.isCurrent()) setBusy(false);
  }
}

$('datasetSelect').addEventListener('change', () => selectDataset($('datasetSelect').value));
$('filterForm').addEventListener('submit', event => { event.preventDefault(); refreshHistory(); });
$('filterForm').addEventListener('input', () => {
  if (state.dataset && !state.busy) $('loadStatus').textContent = 'Bộ lọc đã thay đổi. Nhấn Áp dụng để cập nhật biểu đồ và bảng số liệu.';
});
$('fullRange').addEventListener('click', () => {
  $('dateFrom').value = localDate(state.dataset.first_observation);
  $('dateTo').value = localDate(state.dataset.last_observation);
  refreshHistory();
});
$('recentRange').addEventListener('click', () => {
  const range = recentRange(state.dataset);
  $('dateFrom').value = range.date_from; $('dateTo').value = range.date_to;
  refreshHistory();
});
$('fitStations').addEventListener('click', () => map.fit());
$('basemapToggle').addEventListener('change', () => {
  map.setBasemapVisible($('basemapToggle').checked);
  $('tileNotice').hidden = true;
});
$('previousPage').addEventListener('click', () => { state.tablePage--; renderTable(); });
$('nextPage').addEventListener('click', () => { state.tablePage++; renderTable(); });
$('retryButton').addEventListener('click', () => {
  if (state.dataset) refreshHistory();
  else if (state.site) selectStation(state.site.properties.site_code);
  else bootstrap();
});
document.querySelector('a[href="#tableDetails"]').addEventListener('click', () => { $('tableDetails').open = true; });
if (matchMedia('(max-width: 780px)').matches) $('filterDetails').open = false;
bootstrap();
