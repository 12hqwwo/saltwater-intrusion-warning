import test from 'node:test';
import assert from 'node:assert/strict';
import { createMultivariateForecast } from '../frontend/src/features/multivariate-forecast.js';
import { createPredictionHistory } from '../frontend/src/features/prediction-history.js';
import { createWeatherEstimates } from '../frontend/src/features/weather-estimates.js';
import { createNextForecast } from '../frontend/src/features/next-forecast.js';
import { createForecasts } from '../frontend/src/features/forecasts.js';
import { validMonth, inputMonthFor } from '../frontend/src/shared/forecast-contract.js';

class Element {
  constructor(tag = 'div') { this.tagName = tag; this.children = []; this.listeners = {}; this._text = ''; this._value = undefined; this.disabled = false; this.classList = { remove() {}, toggle() {} }; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(' '); }
  set value(value) { this._value = String(value); }
  get value() { return this._value ?? (this.tagName === 'select' ? this.children[0]?.value || '' : ''); }
  append(...children) { this.children.push(...children); }
  prepend(...children) { this.children.unshift(...children); }
  replaceChildren(...children) { this._text = ''; this.children = []; this._value = undefined; this.append(...children); }
  get firstChild() { return this.children[0]; }
  setAttribute(name, value) { this[name] = value; }
  removeAttribute(name) { delete this[name]; }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  async emit(name) { await Promise.all((this.listeners[name] || []).map(callback => callback({ preventDefault() {} }))); }
  reportValidity() { return true; }
  click() { if (!this.disabled) return this.emit('click'); }
}
function environment() {
  const elements = new Map(), events = [], downloads = [];
  URL.createObjectURL = blob => { downloads.push(blob); return 'blob:test'; };
  URL.revokeObjectURL = () => {};
  globalThis.document = { getElementById: id => { if (!elements.has(id)) elements.set(id, new Element(['experimentSelect', 'predictionYear', 'futureStationSelect'].includes(id) ? 'select' : 'div')); return elements.get(id); }, createElement: tag => new Element(tag), createElementNS: (_ns, tag) => new Element(tag) };
  globalThis.Option = class extends Element { constructor(label, value) { super('option'); this.textContent = label; this.value = value; } };
  globalThis.CustomEvent = class { constructor(type, options = {}) { this.type = type; this.detail = options.detail; } };
  globalThis.window = { addEventListener() {}, dispatchEvent: event => { events.push(event); } };
  globalThis.location = { hash: '' };
  globalThis.sessionStorage = { getItem() { return null; }, setItem() {} };
  const pending = [];
  globalThis.fetch = (url, options) => new Promise(resolve => pending.push({ url, options, respond(data, ok = true) { resolve({ ok, status: ok ? 200 : 503, json: async () => data }); } }));
  return { get: id => document.getElementById(id), pending, events, downloads };
}
const flush = () => new Promise(resolve => setImmediate(resolve));
function descendants(element) { return [element, ...element.children.flatMap(descendants)]; }
function prediction(overrides = {}) {
  return { station: 'MyTho', site_code: 'MRC_VN_019805', target_month: '2026-11', input_month: '2026-09', unit: 'mS/m', data_kind: 'MULTIVARIATE_MONTHLY_FORECAST', predicted_ec_mS_m: 0, input_mode: 'ARCHIVE', model_version: 'v1', inputs: [
    { name: 'rainfall_mm', value: 10, unit: 'mm' }, { name: 'temperature_degC', value: 25, unit: 'degC' }, { name: 'wind_source_units', value: 2, unit: 'm/s' },
  ], ...overrides };
}
const catalog = { default_target_month: '2026-11', stations: [{ station: 'MyTho', site_code: 'MRC_VN_019805', trained_through: '2021-12-01' }, { station: 'TanChau', site_code: 'MRC_VN_019803', trained_through: '2021-12-01' }] };
const input = (station = 'MyTho', target = '2026-11', inputMonth = '2026-09') => ({ station, target_month: target, input_month: inputMonth, wind_unit: 'm/s', complete: true, rainfall_mm: 10, temperature_degC: 25, wind_source_units: 2 });
function frozenEvaluation(overrides = {}) {
  return { station: 'MyTho', unit: 'mS/m', protocol_id: 'FROZEN_EC_WEATHER_ONLY_V1',
    experiment: 'gap_2021_2023', ec_delay_days: 5,
    period: '2021-01..2023-12', frozen_ec_through: '2020-11-01', first_issue_date_local: '2020-12-06',
    items: [{ target_month: '2021-01-01', actual: 10, RandomForest: 12, FrozenPersistence: 9 }],
    methods: [{ key: 'RandomForest', label: 'RF khí tượng' }, { key: 'FrozenPersistence', label: 'EC khóa trước mất dữ liệu' }],
    metrics: { RandomForest: { n: 36, mae_mS_m: 2, rmse_mS_m: 3 }, FrozenPersistence: { n: 36, mae_mS_m: 4, rmse_mS_m: 5 } },
    seasonal_naive: { available_months: 11, total_months: 36 }, ...overrides };
}
async function loadMultivariate(env) {
  const feature = createMultivariateForecast();
  const loading = feature.load(); env.pending[0].respond(catalog); await flush();
  env.pending.find(row => row.url.includes('/evaluation')).respond(frozenEvaluation());
  env.pending.find(row => row.url.includes('/inputs')).respond(input()); await loading;
  const all = descendants(env.get('multivariateForecastHost'));
  return { feature, all, form: all.find(row => row.tagName === 'form'), month: all.find(row => row.name === 'target_month'), mode: all.find(row => row.name === 'input_mode'), station: all.find(row => row.name === 'station'), submit: all.find(row => row.type === 'submit'), output: all.find(row => row.className === 'mv-result'), status: all.find(row => row.className === 'subtle mv-status') };
}

test('multivariate requests frozen-label evidence and renders baseline availability instead of full-period direct seasonal scores', async () => {
  const env = environment(), ui = await loadMultivariate(env);
  const request = new URL(env.pending.find(row => row.url.includes('/evaluation')).url, 'http://localhost');
  assert.equal(request.searchParams.get('protocol'), 'FROZEN_EC_WEATHER_ONLY_V1');
  assert.equal(request.searchParams.get('experiment'), 'gap_2021_2023');
  assert.equal(request.searchParams.get('ec_delay_days'), '5');
  const text = env.get('multivariateForecastHost').textContent;
  assert.match(text, /khóa EC đến 2020-11/);
  assert.match(text, /mô hình giữ cố định/);
  assert.match(text, /11\/36 tháng/);
  assert.match(text, /không xếp hạng toàn kỳ/);
  assert.match(text, /RF khí tượng/);
  assert.doesNotMatch(text, /Persistence · EC mới nhất khả dụng/);
  assert.equal(ui.all.filter(row => row.tagName === 'circle').length, 3);
});

test('outage evidence separates hydrology remedies from the served weather model', async () => {
  const env = environment();
  const feature = createMultivariateForecast();
  const loading = feature.load(); env.pending[0].respond(catalog); await flush();
  const remedy_research = {
    protocol_id: 'FROZEN_EC_REMEDY_RESEARCH_V1', station: 'MyTho', experiment: 'gap_2021_2023', ec_delay_days: 5,
    deployment_ready: false,
    methods: [{ key: 'WeatherOnly', label: 'Chỉ khí tượng' }, { key: 'WeatherHydrology', label: 'Thêm thủy văn' }],
    metrics: { WeatherOnly: { mae_mS_m: 28, rmse_mS_m: 64, false_alerts_100: 2, missed_high_100: 2 },
      WeatherHydrology: { mae_mS_m: 16, rmse_mS_m: 31, false_alerts_100: 1, missed_high_100: 1 } },
  };
  const followup_research = {
    protocol_id: 'FROZEN_EC_FOLLOWUP_RESEARCH_V1', station: 'MyTho', experiment: 'gap_2021_2023', ec_delay_days: 5,
    deployment_ready: false,
    methods: [{ key: 'WeatherHydrology', label: 'Thủy văn đối chứng' }, { key: 'HydroMyThuanEC', label: 'Thủy văn + EC Mỹ Thuận' }],
    metrics: { WeatherHydrology: { mae_mS_m: 16, rmse_mS_m: 31, false_alerts_100: 1, missed_high_100: 1 },
      HydroMyThuanEC: { mae_mS_m: 15, rmse_mS_m: 29, false_alerts_100: 1, missed_high_100: 1 } },
  };
  env.pending.find(row => row.url.includes('/evaluation')).respond(frozenEvaluation({
    metrics: { RandomForest: { n: 36, mae_mS_m: 28, rmse_mS_m: 64 }, FrozenPersistence: { n: 36, mae_mS_m: 19, rmse_mS_m: 42 } },
    remedy_research, followup_research,
  }));
  env.pending.find(row => row.url.includes('/inputs')).respond(input()); await loading;
  const text = env.get('multivariateForecastHost').textContent;
  assert.match(text, /Không dùng riêng kết quả này để cảnh báo/);
  assert.match(text, /Thêm thủy văn/);
  assert.match(text, /chưa thay mô hình đang phục vụ/);
  assert.match(text, /thiếu bản dự báo thời tiết lưu đúng ngày phát hành/);
  assert.match(text, /Thử riêng EC từng trạm và mô hình tuyến tính/);
  assert.match(text, /Thủy văn \+ EC Mỹ Thuận/);
  assert.match(text, /chưa đủ để loại vĩnh viễn EC trạm lân cận/);
});

test('changing outage experiment discards stale evaluation responses and rejects historical protocol', async () => {
  const env = environment(), ui = await loadMultivariate(env);
  const select = ui.all.find(row => row.name === 'gap_experiment');
  select.value = 'gap_2022_2023'; const old = select.emit('change'), oldRequest = env.pending.at(-1);
  select.value = 'gap_2019_2021'; const latest = select.emit('change');
  env.pending.at(-1).respond(frozenEvaluation({ frozen_ec_through: '2018-11-01' })); await latest;
  oldRequest.respond(frozenEvaluation({ frozen_ec_through: '2021-11-01' })); await old;
  assert.match(env.get('multivariateForecastHost').textContent, /khóa EC đến 2018-11/);
  assert.doesNotMatch(env.get('multivariateForecastHost').textContent, /khóa EC đến 2021-11/);
  const delay = ui.all.find(row => row.name === 'gap_ec_delay'); delay.value = '35';
  const reload = delay.emit('change');
  assert.match(env.pending.at(-1).url, /ec_delay_days=35/);
  env.pending.at(-1).respond(frozenEvaluation({ protocol_id: 'HISTORICAL' })); await reload;
  assert.match(env.get('multivariateForecastHost').textContent, /không khớp.*giao thức khóa EC/);
});

test('prediction presents multi-year frozen validation separately from deployment training and legacy historical metrics', async () => {
  const env = environment(), ui = await loadMultivariate(env);
  const submission = ui.form.emit('submit');
  env.pending.at(-1).respond({ prediction: prediction({ training: { through: '2023-12-01', samples: 464 },
    metrics: { mae_mS_m: 999, rmse_mS_m: 999, n: 24 },
    gap_validation: { period: '2021-01..2023-12', metrics: { RandomForest: { mae_mS_m: 2, rmse_mS_m: 3, n: 36 } } } }) });
  await submission;
  assert.match(ui.output.textContent, /Huấn luyện đến 2023-12-01/);
  assert.match(ui.output.textContent, /Kiểm chứng thiếu EC liên tục 2021-01\.\.2023-12/);
  assert.match(ui.output.textContent, /MAE 2 mS\/m/);
  assert.doesNotMatch(ui.output.textContent, /999/);
});

test('multivariate input month/station changes discard late responses and failed catalog reload clears runnable inputs', async () => {
  const env = environment(), ui = await loadMultivariate(env);
  ui.month.value = '2026-12'; const old = ui.month.emit('input'); const oldRequest = env.pending.at(-1);
  ui.month.value = '2027-01'; const latest = ui.month.emit('input'); env.pending.at(-1).respond(input('MyTho', '2027-01', '2026-11')); await latest;
  oldRequest.respond(input('MyTho', '2026-12', '2026-10')); await old;
  assert.equal(ui.submit.disabled, false);
  assert.ok(env.get('multivariateForecastHost').textContent.includes('2026-11'));
  ui.mode.value = 'MANUAL'; await ui.mode.emit('change');
  const reload = ui.feature.load(); env.pending.at(-1).respond({ detail: 'catalog unavailable' }, false); await reload;
  assert.equal(ui.submit.disabled, true);
  assert.equal(ui.all.find(row => row.name === 'rainfall_mm').value, '');
  assert.equal(ui.output.children.length, 0);
});

test('multivariate rejects mismatched mode, wrong wind unit, and changed manual values without enabling exports', async () => {
  const env = environment(), ui = await loadMultivariate(env);
  ui.mode.value = 'MANUAL'; await ui.mode.emit('change');
  const responses = [prediction(), prediction({ input_mode: 'MANUAL', inputs: prediction().inputs.map(row => row.name === 'wind_source_units' ? { ...row, unit: 'km/h' } : row) }), prediction({ input_mode: 'MANUAL', inputs: prediction().inputs.map(row => row.name === 'rainfall_mm' ? { ...row, value: 11 } : row) })];
  for (const response of responses) {
    const submission = ui.form.emit('submit'); env.pending.at(-1).respond({ prediction: response }); await submission;
    assert.equal(ui.output.children.length, 0);
    assert.equal(ui.all.find(row => row.textContent === 'Tải dự báo JSON ↓').disabled, true);
    assert.match(ui.status.textContent, /không khớp/);
  }
});

test('completed zero-EC prediction enables exports until an input edit and superseded prediction cannot restore them', async () => {
  const env = environment(), ui = await loadMultivariate(env);
  let submission = ui.form.emit('submit'); env.pending.at(-1).respond({ prediction: prediction() }); await submission;
  const json = ui.all.find(row => row.textContent === 'Tải dự báo JSON ↓');
  assert.equal(json.disabled, false);
  assert.ok(ui.output.textContent.includes('0 mS/m'));
  await json.emit('click');
  assert.equal(JSON.parse(await env.downloads.at(-1).text()).target_month, '2026-11');
  await ui.all.find(row => row.textContent === 'Tải dự báo CSV ↓').emit('click');
  const exported = await env.downloads.at(-1).text(), [header, firstRow] = exported.replace(/^\uFEFF/, '').split('\r\n');
  const columns = header.split(','), values = firstRow.split(',').map(value => value.replace(/^"|"$/g, ''));
  assert.equal(values[columns.indexOf('unit')], 'mS/m');
  assert.equal(values[columns.indexOf('data_kind')], 'MULTIVARIATE_MONTHLY_FORECAST');
  submission = ui.form.emit('submit'); const pendingPrediction = env.pending.at(-1);
  ui.month.value = '2026-12'; const inputLoad = ui.month.emit('input');
  env.pending.at(-1).respond(input('MyTho', '2026-12', '2026-10')); await inputLoad;
  pendingPrediction.respond({ prediction: prediction() }); await submission;
  assert.equal(json.disabled, true);
  assert.equal(ui.output.children.length, 0);
  assert.equal(env.events.filter(event => event.type === 'workspace:multivariate-prediction').length, 1);
});

test('selecting a station without a model clears the prior prediction, candidate and pending inputs', async () => {
  const env = environment(), ui = await loadMultivariate(env);
  const submission = ui.form.emit('submit'); env.pending.at(-1).respond({ prediction: prediction() }); await submission;
  assert.ok(ui.output.children.length);
  assert.equal(await ui.feature.selectStation('RIA2_DT_01'), false);
  assert.equal(ui.station.value, '');
  assert.equal(ui.output.children.length, 0);
  assert.equal(ui.submit.disabled, true);
  assert.equal(ui.all.find(row => row.textContent === 'Tải dự báo JSON ↓').disabled, true);
  assert.equal(ui.all.find(row => row.name === 'rainfall_mm').value, '');
  assert.equal(env.events.at(-1).type, 'workspace:multivariate-clear');
  const restoring = ui.feature.selectStation('MRC_VN_019805');
  env.pending.at(-1).respond(input());
  env.pending.at(-2).respond({ station: 'MyTho', unit: 'mS/m', items: [] });
  assert.equal(await restoring, true);
});

test('saved prediction cannot replace a newer form candidate and history rejects rows outside requested filters', async () => {
  const env = environment(), host = new Element(), saved = [];
  const feature = createPredictionHistory(host, { onSaved: value => saved.push(value) });
  const all = descendants(host), save = all.find(row => row.textContent === 'Chạy và lưu dự báo vào PostgreSQL');
  feature.setCandidate({ station: 'MyTho', target_month: '2026-11', input_mode: 'ARCHIVE' });
  const saving = save.emit('click'); feature.setCandidate(null);
  env.pending.at(-1).respond({ prediction: prediction(), saved_at: '2026-10-28' }); await saving;
  assert.equal(saved.length, 0);
  env.pending.at(-1).respond({ items: [], total: 0, offset: 0 }); await flush();
  const station = all.find(row => row.tagName === 'select'); station.value = 'TanChau'; await station.emit('input');
  const form = all.find(row => row.tagName === 'form'), loading = form.emit('submit');
  env.pending.at(-1).respond({ items: [{ prediction: prediction() }], total: 1, offset: 0 }); await loading; await flush();
  assert.match(host.textContent, /không khớp bộ lọc/);
  assert.equal(descendants(host).some(row => row.textContent === 'Bản đồ'), false);
});

test('weather estimates reject wrong station/unit and ignore a late response after switching stations', async () => {
  const env = environment(); env.get('futureStationSelect').value = 'MyTho'; const feature = createWeatherEstimates();
  const a = feature.load(), first = env.pending.at(-1);
  env.get('futureStationSelect').value = 'TanChau'; const b = feature.load();
  const data = { unit: 'mS/m', data_kind: 'RETROSPECTIVE_WEATHER_ESTIMATE', live_forecast_available: false, gate_decision_eligible: false, items: [{ station: 'TanChau', year_month: '2026-01', predicted_ec_mS_m: 0, rainfall_mm: 0, temperature_degC: 25, wind_m_s: 0 }] };
  env.pending.at(-1).respond(data); await b; first.respond({ ...data, unit: 'g/L' }); await a;
  assert.equal(env.get('downloadFutureCsv').disabled, false);
  assert.match(env.get('futureStatus').textContent, /1 tháng/);
  await env.get('downloadFutureCsv').emit('click');
  const csv = await env.downloads.at(-1).text();
  assert.match(csv, /TanChau/); assert.doesNotMatch(csv, /MyTho/);
  assert.match(csv, /RETROSPECTIVE_WEATHER_ESTIMATE/); assert.match(csv, /mS\/m/);
  const bad = feature.load(); env.pending.at(-1).respond({ ...data, items: [{ ...data.items[0], station: 'MyTho' }] }); await bad;
  assert.equal(env.get('downloadFutureCsv').disabled, true);
  assert.equal(env.get('futureTableRows').children.length, 0);
});

test('archived next forecast rejects another experiment without retaining downloadable results', async () => {
  const env = environment(), feature = createNextForecast(), loading = feature.load('EX_A');
  env.pending.at(-1).respond({ experiment_id: 'EX_B' }); await loading;
  assert.equal(env.get('nextForecastDownload').disabled, true);
  assert.match(env.get('nextForecastStatus').textContent, /không khớp/);
});

test('archived next forecast valid zero result is cleared before failed replacement load', async () => {
  const env = environment(), feature = createNextForecast();
  const row = { station: 'MYTHO', model: 'Persistence', unit: 'mS/m', status: 'SUCCESS', predicted: 0, target_month: '2024-01-01', forecast_origin: '2023-12-31T23:59:59+07:00' };
  const loading = feature.load('EX_A');
  env.pending.at(-1).respond({ experiment_id: 'EX_A', station: 'MYTHO', unit: 'mS/m', data_kind: 'EXPERIMENTAL_NEXT_AFTER_LAST_OBSERVATION', live_forecast_available: false, deployment_ready: false, gate_decision_eligible: false, selected_model: 'Persistence', selected_prediction: row, all_predictions: [row], target_month: row.target_month, forecast_origin: row.forecast_origin });
  await loading;
  assert.equal(env.get('nextForecastDownload').disabled, false);
  assert.equal(env.get('nextForecastValue').textContent, '0');
  const replacement = feature.load('EX_B');
  assert.equal(env.get('nextForecastDownload').disabled, true);
  env.pending.at(-1).respond({ detail: 'artifact unavailable' }, false); await replacement;
  assert.equal(env.get('nextForecastValue').textContent, '—');
  assert.equal(env.get('nextForecastRows').children.length, 0);
});

test('calendar input lag crosses year boundaries without Date.UTC years 0–99 coercion', () => {
  assert.equal(inputMonthFor('2027-01'), '2026-11');
  assert.equal(inputMonthFor('0099-01'), '0098-11');
  for (const value of ['2026-00', '2026-13', '0000-01', '2026-1', '2026-11-01', null]) assert.equal(validMonth(value), false);
  assert.equal(inputMonthFor('0001-01'), null);
});

test('direct forecast exposes model subtitle, explicit map application, and Timeline restore actions', async () => {
  const env = environment(), ui = await loadMultivariate(env);
  const apply = ui.all.find(row => row.textContent === 'Áp dụng kịch bản dự báo lên bản đồ');
  const restore = ui.all.find(row => row.textContent === 'Quay về dữ liệu Timeline gốc');
  assert.match(env.get('multivariateForecastHost').textContent, /Dự báo khi thiếu EC · RF 300 cây, 5 biến khí tượng\/mùa/);
  assert.doesNotMatch(env.get('multivariateForecastHost').textContent, /MAE holdout Mỹ Tho 18.32/);
  assert.equal(apply.disabled, true);
  const submission = ui.form.emit('submit'); env.pending.at(-1).respond({ prediction: prediction() }); await submission;
  await apply.click();
  assert.equal(env.events.at(-1).type, 'workspace:show-forecast-map');
  assert.equal(env.events.at(-1).detail.predicted_ec_mS_m, 0);
  await restore.click();
  assert.equal(env.events.at(-1).type, 'workspace:restore-timeline');
  assert.equal(location.hash, 'observations');
  ui.month.value = '2026-12'; const changing = ui.month.emit('input');
  assert.equal(apply.disabled, true);
  env.pending.at(-1).respond(input('MyTho', '2026-12', '2026-10')); await changing;
});

test('RF_compact actions pass the selected archive value and experiment-specific P90 for both lags', async () => {
  const env = environment(), feature = createNextForecast();
  for (const [lag, predicted, p90] of [[5, 27.903151156478184, 60.42], [35, 22.022199245004803, 60.6]]) {
    const row = { station: 'MYTHO', model: 'RF_compact', unit: 'mS/m', status: 'SUCCESS', predicted,
      target_month: '2024-01-01', forecast_origin: '2023-12-06T00:00:00+07:00' };
    const loading = feature.load(`EX_${lag}`, { high_ec_metrics: [{ model: 'RF_compact', train_p90_mS_m: p90 }] });
    assert.equal(env.get('nextForecastApplyMap').disabled, true);
    env.pending.at(-1).respond({ experiment_id: `EX_${lag}`, station: 'MYTHO', unit: 'mS/m',
      data_kind: 'EXPERIMENTAL_NEXT_AFTER_LAST_OBSERVATION', live_forecast_available: false,
      deployment_ready: false, gate_decision_eligible: false, selected_model: 'RF_compact',
      selected_prediction: row, all_predictions: [row], target_month: row.target_month,
      forecast_origin: row.forecast_origin, availability_lag_days: lag });
    await loading;
    assert.equal(env.get('nextForecastApplyMap').disabled, false);
    assert.match(env.get('nextForecastModelInfo').textContent, /RF_compact 100 cây, 8 biến - MAE hồi cứu Mỹ Tho 11.07/);
    await env.get('nextForecastApplyMap').click();
    assert.equal(env.events.at(-1).type, 'workspace:apply-forecast-overlay');
    assert.deepEqual(env.events.at(-1).detail, { sourceModel: 'RF_compact', targetMonth: '2024-01', mythoEc: predicted,
      p90Threshold: p90, experimentId: `EX_${lag}`, availabilityLagDays: lag });
  }
  feature.reset();
  assert.equal(env.get('nextForecastApplyMap').disabled, true);
  await env.get('nextForecastRestoreTimeline').click();
  assert.equal(env.events.at(-1).type, 'workspace:restore-timeline');
});

test('backtest experiment switch discards stale responses and rejects another site', async () => {
  const env = environment(), feature = createForecasts();
  const loading = feature.load([{ experiment_id: 'EX_A', site_code: 'A' }, { experiment_id: 'EX_B', site_code: 'B' }]);
  const a = env.pending.at(-1), switching = feature.selectStation('B');
  env.pending.at(-1).respond({ experiment_id: 'EX_B', site_code: 'A', unit: 'mS/m', predictions: [] }); await switching;
  a.respond({ experiment_id: 'EX_A', site_code: 'A', unit: 'mS/m', predictions: [] }); await loading;
  assert.equal(env.get('downloadPredictions').disabled, true);
  assert.match(env.get('forecastStatus').textContent, /không khớp/);
  await feature.selectStation('C');
  assert.equal(env.get('experimentSelect').value, '');
});
