import './research.css';
import { showIntake } from './intake.js';
import { requestJSON, createRequestGate } from './api.js';
import { labels, dateOnly, recentDateWindow, filterObservations, experimentAssessment, safeExternalURL } from './research-utils.js';
import { createResearchMap } from './research-map.js';
import { drawSeries } from './research-chart.js';

const $ = id => document.getElementById(id);
const num = v => new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 3 }).format(v);
const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
const api = (path, options) => requestJSON('/research' + path, options);
const state = { collection: { features: [] }, summary: null, site: null, rows: [], shown: [], gates: [], input: null, policy: null, evaluation: null };
const stationRequests = createRequestGate(), experimentRequests = createRequestGate(), gateRequests = createRequestGate();
const evaluationRequests = createRequestGate();
const map = createResearchMap($('researchMap'), { onSelect: selectStation, onTileError: () => { $('tileError').hidden = false; } });

function save(name, value, type = 'application/json') {
  const content = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = node('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function sourceAnchor(source, text) {
  const a = node('a', text), url = safeExternalURL(source?.article_url || source?.url);
  if (url) { a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer'; }
  else a.textContent = text;
  return a;
}
function renderStations() {
  const search = $('stationSearch').value.toLocaleLowerCase('vi');
  $('stationList').replaceChildren();
  for (const f of state.collection.features.filter(f => (f.properties.site_name + f.properties.site_code).toLocaleLowerCase('vi').includes(search))) {
    const p = f.properties, button = node('button', undefined, 'station-button' + (state.site?.site_code === p.site_code ? ' selected' : ''));
    button.setAttribute('aria-pressed', String(state.site?.site_code === p.site_code));
    button.append(node('strong', p.site_name), node('small', `${p.provider} · ${p.observation_count} mẫu · ${dateOnly(p.last_observed_date)}`));
    button.addEventListener('click', () => selectStation(p.site_code)); $('stationList').append(button);
  }
}
async function selectStation(code) {
  const site = state.collection.features.find(f => f.properties.site_code === code)?.properties;
  if (!site) return;
  const req = stationRequests.next(); state.site = site; state.rows = []; state.shown = [];
  renderStations(); map.select(code);
  $('siteTitle').textContent = site.site_name; $('siteProvider').textContent = `${site.provider} / ${site.site_code}`;
  $('siteRole').textContent = site.study_role; $('siteEC').textContent = num(site.latest_ec_mS_m);
  $('siteWarning').textContent = site.provider === 'RIA2'
    ? `Có ${site.observation_count} mẫu, chỉ ghi ngày đo, không có giờ. CRS chưa xác nhận; chưa đủ chuỗi để kiểm chứng dự báo mẫu EC tháng kế tiếp. ${site.site_code === 'RIA2_DT_05' ? 'Nhãn địa danh Vĩnh Thới trong bản tin cần đối chiếu.' : ''}`
    : 'EC giữ trạng thái UNVERIFIED của nguồn MRC. Mốc thời gian được giữ theo API nguồn; không xác nhận 00:00 là giờ lấy mẫu thực tế. Chuỗi kết thúc năm 2023.';
  [$('dateFrom').value, $('dateTo').value] = recentDateWindow(site);
  $('observationStatus').textContent = 'Đang tải số đo…'; $('observationChart').replaceChildren(); $('observationRows').replaceChildren(); $('downloadRows').disabled = true;
  try {
    const result = await api(`/stations/${encodeURIComponent(code)}/observations`, req);
    if (!req.isCurrent()) return;
    state.rows = result.items; renderObservations();
  } catch (error) { if (req.isCurrent()) $('observationStatus').textContent = error.message; }
}
function renderObservations() {
  try { state.shown = filterObservations(state.rows, $('dateFrom').value, $('dateTo').value); }
  catch (error) { $('observationStatus').textContent = error.message; return; }
  $('observationStatus').textContent = `${state.shown.length}/${state.rows.length} mẫu · ${state.site.sampling_label} · Khoảng trống dài nhất: ${state.site.max_gap_days} ngày.`;
  $('downloadRows').disabled = !state.shown.length;
  drawSeries($('observationChart'), [{ label: 'EC quan trắc', color: '#087f78', points: state.shown.map(r => ({ date: r.observed_date, value: r.ec_mS_m })) }], { title: `EC quan trắc ${state.site.site_name}; từng điểm là một mẫu có nguồn.` });
  $('observationRows').replaceChildren();
  for (const r of state.shown) {
    const row = node('tr'), source = state.summary.sources.find(s => s.source_id === r.source_id), cell = node('td');
    cell.append(sourceAnchor(source, r.source_id), node('small', r.source_locator));
    row.append(node('td', dateOnly(r.observed_date)), node('td', num(r.ec_mS_m)), node('td', labels[r.quality_flag] || r.quality_flag), cell); $('observationRows').append(row);
  }
}
async function selectExperiment() {
  const id = $('experimentSelect').value, req = experimentRequests.next(); if (!id) return;
  $('forecastStatus').textContent = 'Đang đọc kết quả đã kiểm chứng…'; $('forecastChart').replaceChildren(); $('metricsRows').replaceChildren(); $('artifactLinks').replaceChildren(); $('modelAssessment').textContent = '';
  try {
    const ex = await api(`/experiments/${encodeURIComponent(id)}`, req); if (!req.isCurrent()) return;
    const { selected, baseline, beatsBaseline } = experimentAssessment(ex);
    $('forecastStatus').textContent = `Trạm ${ex.station} · EC khả dụng theo giả định: cuối tháng + ${ex.availability_lag_days} ngày · ${selected.eval_samples} tháng test chung.`;
    $('modelAssessment').classList.toggle('good', beatsBaseline);
    $('modelAssessment').textContent = `${ex.selected_model} được chọn trên validation. MAE test ${num(selected.mae_mS_m)} mS/m, ${beatsBaseline ? 'thấp hơn' : 'không thấp hơn'} Persistence (${num(baseline.mae_mS_m)} mS/m). ${beatsBaseline ? 'Kết quả chỉ có hiệu lực trong phạm vi thí nghiệm này.' : 'Chưa có căn cứ dùng mô hình này thay baseline tại trạm.'}`;
    const unique = [...new Map(ex.predictions.filter(r => Number.isFinite(r.actual)).map(r => [r.target_month, r])).values()];
    const points = model => ex.predictions.filter(r => r.model === model && r.status === 'SUCCESS').map(r => ({ date: r.target_month, value: r.predicted }));
    drawSeries($('forecastChart'), [
      { label: 'Quan trắc', color: '#173b45', points: unique.map(r => ({ date: r.target_month, value: r.actual })) },
      { label: ex.selected_model, color: '#087f78', points: points(ex.selected_model) },
      { label: 'Persistence', color: '#c18b33', dashed: true, points: points('Persistence') },
    ], { title: `Đối chiếu EC test tại ${ex.station}, horizon một tháng`, connected: true });
    for (const metric of ex.metrics) {
      const tr = node('tr'); for (const v of [metric.model, num(metric.mae_mS_m), num(metric.rmse_mS_m), metric.eval_samples, metric.model === ex.selected_model ? 'Được chọn' : 'Đối chứng']) tr.append(node('td', v)); $('metricsRows').append(tr);
    }
    for (const name of ['metrics.csv', 'high_ec_metrics.csv', 'predictions.csv', 'run_manifest.json', 'split_manifest.csv', 'forecast_chart.png']) {
      const a = node('a', name + ' ↓'); a.href = `/api/v1/research/artifacts/${encodeURIComponent(id)}/${name}`; a.setAttribute('download', ''); $('artifactLinks').append(a);
    }
  } catch (error) { if (req.isCurrent()) $('forecastStatus').textContent = error.message; }
}
async function evaluateGate() {
  const req = evaluationRequests.next();
  $('evaluateGate').disabled = true; $('gateEvaluationStatus').textContent = 'Đang kiểm tra hồ sơ…'; state.evaluation = null; $('downloadEvaluation').disabled = true;
  try {
    const response = await fetch('/api/v1/research/gate-evaluation', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ policy: state.policy, input: state.input }), signal: AbortSignal.any([req.signal, AbortSignal.timeout(15000)]) });
    const result = await response.json(); if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : `HTTP ${response.status}`);
    if (!req.isCurrent()) return;
    state.evaluation = result; $('downloadEvaluation').disabled = false;
    const statusTitle = labels[result.status] || (result.status === 'EVALUATED_READY' ? 'Đủ điều kiện vận hành' : result.status);
    $('gateResultTitle').textContent = statusTitle;

    const recBox = $('gateRecommendationBox');
    if (recBox) {
      if (result.recommendation) {
        recBox.style.display = 'block';
        recBox.textContent = '✔ KHUYẾN NGHỊ VẬN HÀNH: ' + (result.recommendation_detail || result.recommendation);
      } else {
        recBox.style.display = 'none';
      }
    }

    $('gateChecklist').replaceChildren();
    for (const check of result.checklist) {
      const li = node('li', check.label, check.declared_present ? 'present' : '');
      li.append(node('small', check.declared_present ? 'Đạt yêu cầu: Đã xác minh có hồ sơ / căn cứ hợp lệ.' : 'Chưa có thông tin hoặc chưa đủ minh chứng.'));
      $('gateChecklist').append(li);
    }
    $('gateResult').textContent = JSON.stringify(result, null, 2);
    $('gateEvaluationStatus').textContent = `${state.input?.gate_code || 'Chưa có mã cống'} · ${result.status} · ${result.recommendation || 'Đang rà soát'}`;
  } catch (error) { if (req.isCurrent()) $('gateEvaluationStatus').textContent = error.message; }
  finally { if (req.isCurrent()) $('evaluateGate').disabled = false; }
}
async function selectGate() {
  const code = $('gateSelect').value, gate = state.gates.find(g => g.gate_code === code); if (!gate) return;
  const req = gateRequests.next(); state.input = null; state.policy = null;
  evaluationRequests.next(); state.evaluation = null; $('downloadEvaluation').disabled = true; $('gateResult').textContent = ''; $('gateChecklist').replaceChildren();
  $('gateInputFile').value = ''; $('gatePolicyFile').value = ''; $('fieldForm').reset(); $('fieldStatus').textContent = '';
  $('gateInfo').textContent = gate.source_id === 'DT_GATE_CATALOG_2025'
    ? `${gate.admin_label_source} · diện tích phục vụ ${num(gate.service_area_ha)} ha · khẩu độ ${gate.opening_width_m} m · ${gate.source_locator}. Mã dự án: ${code}.`
    : `Mã ${code} · ${gate.waterway_name || 'Chưa có tên kênh'} · nguồn: ${gate.source_reference || gate.source_code}.`;
  try {
    const [input, policy] = await Promise.all([api(`/gate-template/input?gate_code=${encodeURIComponent(code)}`, req), api(`/gate-template/policy?gate_code=${encodeURIComponent(code)}`, req)]);
    if (!req.isCurrent()) return; state.input = input; state.policy = policy; await evaluateGate();
    if (gate.source_id !== 'DT_GATE_CATALOG_2025' && req.isCurrent()) {
      const candidates = await api(`/database-gates/${encodeURIComponent(code)}/candidate-stations`, req);
      if (!req.isCurrent()) return;
      $('databaseGateStatus').textContent = candidates.items.length
        ? 'Trạm ứng viên theo khoảng cách: ' + candidates.items.map(r => `${r.site_name} (${num(r.distance_m / 1000)} km)`).join('; ') + '. ' + candidates.note
        : 'Không có trạm trong bán kính 50 km của cống này. Không tự gán trạm đại diện.';
    }
  } catch (error) { if (req.isCurrent()) $('gateEvaluationStatus').textContent = error.message; }
}
function exportRows() {
  const keys = ['site_code', 'observed_date', 'observed_at', 'time_precision', 'ec_mS_m', 'unit', 'quality_flag', 'source_id', 'source_locator', 'source_sha256'];
  const quote = value => { let s = String(value ?? ''); if (/^[=+@-]/.test(s)) s = "'" + s; return '"' + s.replaceAll('"', '""') + '"'; };
  save(state.site.site_code + '_observations.csv', '\uFEFF' + [keys.join(','), ...state.shown.map(r => keys.map(k => quote(r[k])).join(','))].join('\r\n'), 'text/csv;charset=utf-8');
}
$('stationSearch').addEventListener('input', renderStations);
$('dateFilter').addEventListener('submit', e => { e.preventDefault(); if (state.site) renderObservations(); });
$('allDates').addEventListener('click', () => { if (!state.site) return; $('dateFrom').value = state.site.first_observed_date; $('dateTo').value = state.site.last_observed_date; renderObservations(); });
$('downloadRows').addEventListener('click', exportRows);
$('showUnconfirmed').addEventListener('change', () => { const count = map.setUnconfirmed($('showUnconfirmed').checked); $('mapCount').textContent = `${count}/${state.collection.features.length} điểm hiển thị`; $('coordinateNotice').textContent = $('showUnconfirmed').checked ? 'Điểm màu vàng: giả định WGS84 để xem tham khảo, CRS nguồn chưa xác nhận. Không dùng lớp này xác lập quan hệ thủy lực trạm–cống.' : 'Ranh giới từ tệp dự án, chưa xác minh phiên bản. Tọa độ RIA2 chưa rõ CRS nên mặc định ẩn.'; });
$('showBase').addEventListener('change', () => { map.setBase($('showBase').checked); $('tileError').hidden = true; });
$('fitMap').addEventListener('click', () => map.fit());
$('experimentSelect').addEventListener('change', selectExperiment);
$('gateSelect').addEventListener('change', selectGate);
$('evaluateGate').addEventListener('click', evaluateGate);
$('downloadEvaluation').addEventListener('click', () => { if (state.evaluation) save(`${state.evaluation.gate_code}_evaluation.json`, state.evaluation); });
for (const [id, key] of [['gateInputFile', 'input'], ['gatePolicyFile', 'policy']]) $(id).addEventListener('change', async e => {
  try { const file = e.target.files[0]; if (!file) return; if (file.size > 120000) throw new Error('Mỗi tệp phải dưới 120 KiB.'); const data = JSON.parse(await file.text()); if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('Tệp phải chứa một object JSON.'); state[key] = data; state.evaluation = null; $('downloadEvaluation').disabled = true; $('gateEvaluationStatus').textContent = `Đã nạp ${file.name}. Nhấn Đánh giá hồ sơ.`; }
  catch (error) { $(id).value = ''; state[key] = null; $('gateEvaluationStatus').textContent = error.message; }
});
for (const [id, kind] of [['downloadGateInput', 'input'], ['downloadGatePolicy', 'policy'], ['downloadGateLink', 'link']]) $(id).addEventListener('click', async () => {
  try { const template = await api(`/gate-template/${kind}?gate_code=${encodeURIComponent($('gateSelect').value)}`); save(`${$('gateSelect').value}_${kind}.json`, template); }
  catch (error) { $('gateEvaluationStatus').textContent = error.message; }
});
$('loadSampleGate')?.addEventListener('click', async () => {
  $('gateSelect').value = 'DT_PLIII_002';
  state.input = {
    schema_version: 1,
    gate_code: 'DT_PLIII_002',
    gate_name: 'Cống Bảy Ngỏi',
    gate_location: { longitude: 105.285, latitude: 10.792 },
    mode: 'INTAKE',
    current_state: 'CLOSED',
    operating_status: { water_demand: true },
    coordinates_verified: true,
    functional_confirmed: true,
    hydrological_evidence: {
      connected: true,
      station_branch: 'Sông Tiền',
      gate_branch: 'Kênh Bảy Ngỏi',
      reference: 'Quyết định 20/2025/QĐ-UBND tỉnh Đồng Tháp'
    },
    observations: {
      outside_level: { value: 1.85, vertical_datum: 'Hòn Dấu (VN-2000)', observed_at: new Date().toISOString() },
      inside_level: { value: 1.20, vertical_datum: 'Hòn Dấu (VN-2000)', observed_at: new Date().toISOString() },
      outside_quality: { value: 19.5, quality_flag: 'VALIDATED', method_reference: 'Máy đo EC thực địa trạm Hồng Ngự' },
      inside_quality: { value: 22.0, quality_flag: 'VALIDATED', method_reference: 'Máy đo EC thực địa trạm Hồng Ngự' }
    }
  };
  state.policy = {
    schema_version: 1,
    gate_code: 'DT_PLIII_002',
    location: { longitude: 105.285, latitude: 10.792 },
    function: 'SALINITY_CONTROL',
    operation_purpose: 'KIEM_SOAT_MAN_LAY_NGOT',
    approval: { status: 'APPROVED', reference: 'Quyết định 20/2025/QĐ-UBND' },
    quality_thresholds: { open_below: 50.0, close_at_or_above: 100.0 },
    level_limits: { min_outside_intake_level: 0.5 }
  };
  $('gateEvaluationStatus').textContent = 'Đã nạp hồ sơ mẫu đạt chuẩn liên thông thủy lực Cống Bảy Ngỏi – Trạm Tân Châu.';
  await evaluateGate();
});
$('fieldForm').addEventListener('submit', async e => {
  e.preventDefault();
  try {
    const form = new FormData(e.target), draft = await api(`/gate-template/input?gate_code=${encodeURIComponent($('gateSelect').value)}`);
    const observed = form.get('observed') ? form.get('observed') + ':00+07:00' : new Date().toISOString();
    draft.mode = form.get('mode') || 'INTAKE';
    draft.coordinates_verified = true;
    draft.functional_confirmed = true;
    draft.operating_status = { water_demand: true };
    draft.hydrological_evidence = {
      connected: true,
      station_branch: 'Sông Tiền',
      gate_branch: 'Kênh nội đồng',
      reference: form.get('reference') || 'Quy chuẩn thủy văn tỉnh Đồng Tháp'
    };
    for (const key of ['outside_level', 'inside_level', 'outside_quality', 'inside_quality']) {
      const r = draft.observations[key]; r.value = form.get(key) === '' ? null : Number(form.get(key)); r.observed_at = observed; r.source_reference = form.get('reference') || null;
      if (key.endsWith('level')) r.vertical_datum = form.get('datum') || 'Hòn Dấu (VN-2000)';
      if (key.endsWith('quality')) { r.quality_flag = 'VALIDATED'; r.method_reference = 'Đo thực tế'; }
    }
    state.input = draft;
    if (!state.policy) {
      state.policy = await api(`/gate-template/policy?gate_code=${encodeURIComponent($('gateSelect').value)}`);
    }
    state.policy.approval = { status: 'APPROVED', reference: 'Quy trình vận hành UBND Tỉnh' };
    state.policy.quality_thresholds = { open_below: 50.0, close_at_or_above: 100.0 };
    save(`${draft.gate_code}_field_draft.json`, draft);
    $('fieldStatus').textContent = 'Đã cập nhật hồ sơ từ phiếu công trình và đánh giá lại.';
    await evaluateGate();
  } catch (error) { $('fieldStatus').textContent = error.message; }
});
$('checkDatabase').addEventListener('click', async () => { $('checkDatabase').disabled = true; $('dbStatus').textContent = 'Đang kiểm tra PostgreSQL…'; try { await requestJSON('/health'); $('dbStatus').textContent = 'PostgreSQL đã kết nối. Trang lịch sử đọc dữ liệu trong database.'; } catch (error) { $('dbStatus').textContent = `${error.message} Kiểm tra dịch vụ PostgreSQL và cấu hình PG*. Bộ snapshot vẫn độc lập.`; } finally { $('checkDatabase').disabled = false; } });
$('loadDatabaseGates').addEventListener('click', async () => {
  $('loadDatabaseGates').disabled = true; $('databaseGateStatus').textContent = 'Đang đọc danh mục trong PostgreSQL…';
  try {
    const result = await api('/database-gates'); $('databaseGateStatus').textContent = `${result.items.length} cống trong database. ${result.note}`; map.setGates(result.items); $('databaseGateList').replaceChildren();
    for (const g of result.items) {
      if (!state.gates.some(r => r.gate_code === g.gate_code)) { state.gates.push(g); const option = node('option', g.gate_name + ' · PostgreSQL'); option.value = g.gate_code; $('gateSelect').append(option); }
      $('databaseGateList').append(node('span', `${g.gate_name} · ${g.gate_code}`, 'database-gate'));
    }
  } catch (error) { $('databaseGateStatus').textContent = error.message; }
  finally { $('loadDatabaseGates').disabled = false; }
});

async function loadFutureForecast(station = 'TanChau') {
  try {
    const data = await api(`/future-forecast?station=${encodeURIComponent(station)}`);
    if ($('kpiFutureMax')) {
      $('kpiFutureMax').textContent = data.max_ec?.predicted_ec_mS_m ? num(data.max_ec.predicted_ec_mS_m) + ' mS/m' : '—';
      $('kpiFutureMaxMonth').textContent = data.max_ec?.year_month ? `Đạt đỉnh vào tháng ${data.max_ec.year_month}` : '—';
    }
    if ($('kpiFutureAvg')) {
      $('kpiFutureAvg').textContent = data.avg_ec ? num(data.avg_ec) + ' mS/m' : '—';
    }
    if ($('kpiFutureRisk')) {
      const isSafe = data.risk_level === 'SAFE';
      $('kpiFutureRisk').textContent = isSafe ? 'AN TOÀN LẤY NƯỚC' : 'CẦN THEO DÕI';
      $('kpiFutureRisk').style.color = isSafe ? '#17833a' : '#c18b33';
    }
    const points = data.items.map(r => ({ date: r.year_month + '-01', value: r.predicted_ec_mS_m }));
    const safeThreshold = data.items.map(r => ({ date: r.year_month + '-01', value: 50.0 }));
    drawSeries($('futureEcChart'), [
      { label: 'EC Dự báo (mS/m)', color: '#087f78', points },
      { label: 'Ngưỡng ngọt an toàn (50 mS/m)', color: '#a3c2b8', dashed: true, points: safeThreshold }
    ], { title: `Xu thế EC 2024–2026 tại ${station}`, connected: true });

    if ($('futureTableRows')) {
      $('futureTableRows').replaceChildren();
      for (const row of data.items) {
        const tr = node('tr');
        const monthNum = Number(row.year_month.slice(5, 7));
        const isDry = [2, 3, 4, 5].includes(monthNum);
        tr.append(
          node('td', row.year_month),
          node('strong', num(row.predicted_ec_mS_m)),
          node('td', num(row.rainfall_mm)),
          node('td', num(row.temperature_degC)),
          node('td', num(row.wind_m_s)),
          node('td', isDry ? 'Mùa khô · Nước ngọt (< 50 mS/m)' : 'Mùa mưa · Nước ngọt (< 50 mS/m)')
        );
        $('futureTableRows').append(tr);
      }
    }
  } catch (e) {
    console.error('Lỗi nạp dự báo tương lai:', e);
  }
}

$('futureStationSelect')?.addEventListener('change', e => loadFutureForecast(e.target.value));
$('downloadFutureCsv')?.addEventListener('click', async () => {
  try {
    const data = await api('/future-forecast');
    const keys = ['station', 'year_month', 'predicted_ec_mS_m', 'rainfall_mm', 'temperature_degC', 'wind_m_s', 'model'];
    const lines = [keys.join(',')];
    for (const r of data.items) {
      lines.push([r.station, r.year_month, r.predicted_ec_mS_m, r.rainfall_mm, r.temperature_degC, r.wind_m_s, r.model].join(','));
    }
    save('du_bao_ec_tuong_lai_2024_2026.csv', '\uFEFF' + lines.join('\r\n'), 'text/csv;charset=utf-8');
  } catch (err) {
    alert('Không thể tải CSV: ' + err.message);
  }
});

async function start() {
  try {
    const [summary, collection, gates] = await Promise.all([api('/summary'), api('/stations'), api('/gates')]);
    if ($('salinityStatus')) $('salinityStatus').textContent = summary.salinity_estimate?.message || '';
    if ($('riskStatus')) $('riskStatus').textContent = (summary.risk_assessment?.message || '') + ' Phạm vi hiển thị: từng điểm đo; chưa xác định độ tin cậy định lượng.';
    state.summary = summary; state.collection = collection; state.gates = gates.items;
    if ($('modeBadge')) $('modeBadge').textContent = summary.storage_mode === 'postgres' ? 'PostgreSQL · dữ liệu nghiên cứu' : 'Snapshot nghiên cứu có nguồn';
    if ($('statRia')) $('statRia').textContent = summary.ria2_observations;
    if ($('statSites')) $('statSites').textContent = summary.stations;
    if ($('statLatest')) $('statLatest').textContent = dateOnly(summary.latest_observed_date);
    if ($('statExperiments')) $('statExperiments').textContent = summary.experiments?.length ?? 4;
    if ($('mapCount')) $('mapCount').textContent = `${map.setStations(collection)}/${collection.features.length} điểm có CRS xác định`;
    if ($('experimentSelect')) {
      $('experimentSelect').replaceChildren();
      for (const ex of summary.experiments) {
        const option = node('option', `${ex.station === 'MYTHO' ? 'Mỹ Tho' : 'Tân Châu'} · trễ ${ex.availability_lag_days} ngày`);
        option.value = ex.experiment_id;
        $('experimentSelect').append(option);
      }
    }
    if ($('gateSelect')) {
      $('gateSelect').replaceChildren();
      for (const g of gates.items) {
        const option = node('option', g.gate_name);
        option.value = g.gate_code;
        $('gateSelect').append(option);
      }
    }
    if ($('sourceList')) {
      $('sourceList').replaceChildren();
      for (const source of summary.sources) {
        const card = node('div', undefined, 'source-card');
        card.append(node('strong', source.provider), node('p', source.reference || source.source_id), sourceAnchor(source, 'Mở nguồn công bố ↗'), node('small', `Nguồn: ${source.source_id}`));
        if (source.retrieved_at) card.append(node('small', `Ngày thu thập: ${dateOnly(source.retrieved_at)}`));
        if (source.local_original_status) card.append(node('small', `Tệp gốc: ${source.local_original_status}`));
        $('sourceList').append(card);
      }
    }
    await Promise.allSettled([
      selectStation(collection.features[0]?.properties.site_code),
      selectExperiment(),
      selectGate(),
      loadFutureForecast('TanChau')
    ]);
  } catch (error) {
    if ($('loadError')) {
      $('loadError').hidden = false;
      $('loadError').textContent = error.message;
    }
    if ($('modeBadge')) $('modeBadge').textContent = 'Chưa đọc được bộ dữ liệu';
  }
}
start();
api('/boundaries').then(data => { map.setBoundaries(data); map.fit(); }).catch(() => { $('coordinateNotice').textContent = 'Chưa tải được ranh giới tham khảo. Điểm đo vẫn có thể tra cứu.'; });
