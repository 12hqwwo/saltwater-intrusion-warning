import { mountQuickScenarios } from '../frontend/src/features/overview.js';
import assert from 'node:assert/strict';
import test from 'node:test';
import { ADVISORY_PRESETS, validateThresholds, createSimulationFrameLoader, createTimelineScrubber, renderSpatialSummary, simulationInputLabel } from '../frontend/src/features/timeline-scrubber.js';

const thresholds = { open_below_ec: 100, close_above_ec: 150 };
function frame(month, values = thresholds) {
  return { year_month: month, simulation_layer: true, river_segments: [], gates: [],
    thresholds: { open_below_ec_ms_m: values.open_below_ec, close_at_or_above_ec_ms_m: values.close_above_ec } };
}
function harness() {
  const pending = [], frames = [], errors = [], loading = [];
  const loader = createSimulationFrameLoader({
    // Deliberately ignore abort: a late server response must still be discarded.
    api: (path, request) => new Promise((resolve, reject) => pending.push({ path, request, resolve, reject })),
    onFrame: value => frames.push(value), onError: error => errors.push(error),
    onLoading: value => loading.push(value),
  });
  return { loader, pending, frames, errors, loading };
}

test('crop presets retain EC units and ordered threshold pairs', () => {
  assert.deepEqual(ADVISORY_PRESETS, {
    durian: { open_below_ec: 50, close_above_ec: 80 },
    citrus: { open_below_ec: 100, close_above_ec: 150 },
    rice: { open_below_ec: 120, close_above_ec: 200 },
  });
  for (const value of Object.values(ADVISORY_PRESETS)) {
    assert.deepEqual(validateThresholds(String(value.open_below_ec), String(value.close_above_ec)), value);
  }
  assert.deepEqual(validateThresholds('0', '0.1'), { open_below_ec: 0, close_above_ec: 0.1 });
});

test('threshold validation rejects blanks, nonfinite, negative, equal and reversed pairs', () => {
  for (const pair of [['', 150], [100, ''], [NaN, 150], [100, Infinity], [-1, 150], [100, 100], [150, 100]]) {
    assert.throws(() => validateThresholds(...pair));
  }
});

test('newer month wins even when the older server response ignores cancellation', async () => {
  const h = harness();
  const old = h.loader.load('2016-03', thresholds);
  const current = h.loader.load('2024-04', thresholds);
  assert.equal(h.pending[0].request.signal.aborted, true);
  h.pending[1].resolve(frame('2024-04'));
  assert.equal((await current).year_month, '2024-04');
  h.pending[0].resolve(frame('2016-03'));
  assert.equal(await old, null);
  assert.deepEqual(h.frames.map(value => value.year_month), ['2024-04']);
  assert.deepEqual(h.errors, []);
});

test('cancel without a replacement silences both late success and late failure', async () => {
  for (const fail of [false, true]) {
    const h = harness();
    const result = h.loader.load('2016-03', thresholds);
    h.loader.cancel();
    assert.equal(h.pending[0].request.signal.aborted, true);
    if (fail) h.pending[0].reject(new Error('late backend failure'));
    else h.pending[0].resolve(frame('2016-03'));
    assert.equal(await result, null);
    assert.deepEqual(h.frames, []);
    assert.deepEqual(h.errors, []);
  }
});

test('threshold changes supersede pending requests for the same month', async () => {
  const h = harness();
  const old = h.loader.load('2024-04', thresholds);
  const current = h.loader.load('2024-04', ADVISORY_PRESETS.durian);
  const query = new URL(h.pending[1].path, 'https://test.invalid').searchParams;
  assert.equal(query.get('open_below_ec'), '50');
  assert.equal(query.get('close_above_ec'), '80');
  h.pending[0].reject(new Error('stale thresholds'));
  h.pending[1].resolve(frame('2024-04', ADVISORY_PRESETS.durian));
  assert.equal(await old, null);
  assert.equal((await current).thresholds.open_below_ec_ms_m, 50);
  assert.equal(h.frames.length, 1);
  assert.deepEqual(h.errors, []);
});

test('current frame must match selected month, thresholds and simulation contract', async () => {
  for (const mutation of [
    { year_month: '2016-03' }, { simulation_layer: false }, { river_segments: null },
    { gates: {} }, { thresholds: { open_below_ec_ms_m: 99, close_at_or_above_ec_ms_m: 150 } },
    { inputs: { year_month: '2024-03' } }, { gates: [{ gate_code: 'G1', simulated_outside_ec_mS_m: -1 }] },
  ]) {
    const h = harness();
    const result = h.loader.load('2024-04', thresholds);
    h.pending[0].resolve({ ...frame('2024-04'), ...mutation });
    assert.equal(await result, null);
    assert.equal(h.errors.length, 1);
    assert.deepEqual(h.frames, []);
  }
});

test('current network errors are reported while AbortError remains silent', async () => {
  for (const aborted of [false, true]) {
    const h = harness();
    const result = h.loader.load('2024-04', thresholds);
    const error = aborted ? new DOMException('cancelled', 'AbortError') : new Error('backend unavailable');
    h.pending[0].reject(error);
    assert.equal(await result, null);
    assert.deepEqual(h.errors, aborted ? [] : [error]);
    assert.deepEqual(h.frames, []);
  }
});

test('invalid threshold edits after scrubbing cannot reload old advisories through timers or quick jumps', async t => {
  class Element extends EventTarget {
    value = '';
    textContent = '';
    dataset = {};
    children = [];
    classList = { toggle() {} };
    style = { setProperty() {} };
    setAttribute() {}
    replaceChildren() { this.children = []; }
    append(child) { this.children.push(child); }
  }
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  };
  const previous = { document: globalThis.document, window: globalThis.window };
  globalThis.document = Object.assign(new EventTarget(), {
    getElementById: get, querySelectorAll: () => [], createElement: () => new Element(), hidden: false,
  });
  globalThis.window = new EventTarget();
  t.after(() => {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete globalThis[key];
      else globalThis[key] = value;
    }
  });
  t.mock.timers.enable({ apis: ['setTimeout'] });
  get('simulationOpenBelow').value = '100';
  get('simulationCloseAbove').value = '150';
  const queries = [], frames = [];
  window.addEventListener('workspace:simulation-frame', event => frames.push(event.detail));
  t.mock.method(globalThis, 'fetch', async path => {
    const url = new URL(path, 'https://test.invalid');
    let body;
    if (url.pathname.endsWith('/timeline')) body = { items: [{ year_month: '2016-03' }, { year_month: '2026-08' }] };
    else if (url.pathname.endsWith('/corridor')) body = { gates: [], corridor: {} };
    else {
      queries.push(url.searchParams);
      body = frame(url.searchParams.get('year_month'), {
        open_below_ec: Number(url.searchParams.get('open_below_ec')),
        close_above_ec: Number(url.searchParams.get('close_above_ec')),
      });
    }
    return { ok: true, json: async () => body };
  });
  const scrubber = createTimelineScrubber();
  await scrubber.load();
  assert.equal(frames.length, 1);
  get('simulationSlider').value = '0';
  get('simulationSlider').dispatchEvent(new Event('input'));
  get('simulationOpenBelow').value = '';
  get('simulationOpenBelow').dispatchEvent(new Event('input'));
  t.mock.timers.tick(120);
  await new Promise(setImmediate);
  assert.equal(queries.length, 1, 'the pending scrub must not request the previous thresholds');
  t.mock.timers.tick(500);
  await new Promise(setImmediate);
  assert.match(get('simulationStatus').textContent, /Nhập đủ/);
  get('simulationJumps').children[0].dispatchEvent(new Event('click'));
  await new Promise(setImmediate);
  assert.equal(queries.length, 1, 'a quick jump must not bypass invalid visible thresholds');
  assert.equal(frames.length, 1);

  get('simulationOpenBelow').value = '50';
  get('simulationOpenBelow').dispatchEvent(new Event('input'));
  get('simulationCloseAbove').value = '80';
  get('simulationCloseAbove').dispatchEvent(new Event('input'));
  t.mock.timers.tick(500);
  await new Promise(setImmediate);
  assert.equal(queries.length, 2);
  assert.equal(queries[1].get('year_month'), '2016-03');
  assert.equal(queries[1].get('open_below_ec'), '50');
  assert.equal(queries[1].get('close_above_ec'), '80');
  assert.equal(frames.length, 2, 'valid replacement thresholds restore advisories');
  scrubber.stop();
});

function installDOM(t) {
  class Element extends EventTarget {
    value = ''; textContent = ''; dataset = {}; children = []; hidden = false;
    classList = { toggle() {} }; style = { setProperty() {} };
    setAttribute() {} replaceChildren() { this.children = []; }
    append(...children) { this.children.push(...children); }
  }
  const elements = new Map();
  const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const previous = { document: globalThis.document, window: globalThis.window };
  globalThis.document = Object.assign(new EventTarget(), {
    getElementById: get, querySelectorAll: () => [], createElement: () => new Element(), hidden: false,
  });
  globalThis.window = new EventTarget();
  t.after(() => { for (const [key, value] of Object.entries(previous)) {
    if (value === undefined) delete globalThis[key]; else globalThis[key] = value;
  } });
  return get;
}

test('simulation source labels distinguish archived estimates and filled source samples', t => {
  const get = installDOM(t);
  assert.equal(simulationInputLabel({ data_regime: 'OBSERVED_MRC', imputed: false }), 'Mẫu nguồn MRC');
  assert.match(simulationInputLabel({ data_regime: 'OBSERVED_MRC', imputed: true }), /nội suy thời gian/);
  assert.match(simulationInputLabel({ data_regime: 'ML_FORECAST_ERA5' }), /Ước tính hồi cứu/);
  renderSpatialSummary({ year_month: '2024-04', inputs: { data_regime: 'ML_FORECAST_ERA5' }, gates: [] });
  assert.match(get('simulationSpatialSummary').children.at(-1).textContent, /Đầu vào 2024-04: Ước tính hồi cứu/);
});

test('timeline reload clears the displayed month and cancels a prior frame even if replacement load fails', async t => {
  const get = installDOM(t), frames = [], loading = [];
  get('simulationOpenBelow').value = '100'; get('simulationCloseAbove').value = '150';
  window.addEventListener('workspace:simulation-frame', event => frames.push(event.detail));
  window.addEventListener('workspace:simulation-loading', event => loading.push(event.detail));
  let failTimeline = false, delayedFrame;
  t.mock.method(globalThis, 'fetch', async path => {
    const url = new URL(path, 'https://test.invalid');
    const result = body => ({ ok: true, json: async () => body });
    if (url.pathname.endsWith('/timeline')) {
      if (failTimeline) throw new Error('replacement unavailable');
      return result({ items: [{ year_month: '2016-03' }, { year_month: '2026-08' }] });
    }
    if (url.pathname.endsWith('/corridor')) return result({ gates: [], corridor: {} });
    if (url.searchParams.get('year_month') === '2016-03') return new Promise(resolve => { delayedFrame = () => resolve(result(frame('2016-03'))); });
    return result(frame(url.searchParams.get('year_month')));
  });
  const scrubber = createTimelineScrubber(); await scrubber.load();
  assert.equal(frames.length, 1);
  const older = scrubber.selectMonth('2016-03');
  failTimeline = true; const reload = scrubber.load();
  assert.equal(get('simulationMonth').textContent, '—');
  assert.equal(get('simulationSpatialSummary').hidden, true);
  delayedFrame(); await older; await reload;
  assert.equal(frames.length, 1, 'previous month must not reappear after reload');
  assert.equal(get('simulationPlay').disabled, true); assert.equal(get('simulationRetry').hidden, false);
  assert.equal(get('simulationTimeline').dataset.loading, 'false');
  assert.ok(loading.length >= 3); scrubber.stop();
});

test('scenario event before timeline load preserves preset and selects nearest available month', async t => {
  const get = installDOM(t), queries = [], selections = [];
  window.addEventListener('workspace:simulation-selection', event => selections.push(event.detail));
  get('simulationOpenBelow').value = '100'; get('simulationCloseAbove').value = '150';
  t.mock.method(globalThis, 'fetch', async path => {
    const url = new URL(path, 'https://test.invalid');
    let body;
    if (url.pathname.endsWith('/timeline')) body = { items: [{ year_month: '2022-10', data_regime: 'OBSERVED_MRC' }, { year_month: '2024-03', data_regime: 'ML_FORECAST_ERA5' }] };
    else if (url.pathname.endsWith('/corridor')) body = { gates: [], corridor: {} };
    else { queries.push(url.searchParams); body = { ...frame(url.searchParams.get('year_month'), ADVISORY_PRESETS.durian), inputs: { year_month: url.searchParams.get('year_month'), data_regime: 'ML_FORECAST_ERA5' } }; }
    return { ok: true, json: async () => body };
  });
  const scrubber = createTimelineScrubber();
  window.dispatchEvent(new CustomEvent('workspace:simulation-scenario', { detail: { month: '2024-04', preset: 'durian' } }));
  await scrubber.load();
  assert.equal(get('simulationMonth').textContent, '2024-03');
  assert.equal(get('simulationThresholdPreset').value, 'durian');
  assert.equal(queries.length, 1);
  assert.equal(queries[0].get('year_month'), '2024-03');
  assert.equal(queries[0].get('open_below_ec'), '50');
  assert.equal(queries[0].get('close_above_ec'), '80');
  await scrubber.selectMonth('2024-04', { source: 'forecast' });
  assert.deepEqual(selections.at(-1), { year_month: '2024-03', source: 'forecast' });
  assert.match(get('simulationStatus').textContent, /2024-04 không có frame dữ liệu; đã chuyển về 2024-03/);
  assert.equal(get('simulationMonthPicker').children.length, 2);
  assert.equal(get('simulationMonthPicker').value, '2024-03');
  assert.match(get('simulationRegime').textContent, /^Ước tính hồi cứu · khí tượng ERA5/);
  window.dispatchEvent(new CustomEvent('workspace:active-forecast-context', { detail: { targetMonth: '2024-04' } }));
  assert.match(get('simulationStatus').textContent, /Đang xem lớp sông dự báo 2024-04/);
  assert.doesNotMatch(get('simulationStatus').textContent, /0 cống mô phỏng/);
  window.dispatchEvent(new CustomEvent('workspace:active-forecast-context', { detail: null }));
  assert.match(get('simulationStatus').textContent, /các nhánh có cống/);
  await scrubber.selectMonth('2024-04');
  assert.equal(selections.at(-1).source, 'user', 'user month changes must let the map invalidate a prior forecast overlay');
  scrubber.stop();
});

test('spatial summary counts simulated states and uses selected EC warning thresholds', t => {
  const get = installDOM(t);
  renderSpatialSummary({ gates: [
    { simulated_gate_state: 'OPEN_INTAKE' }, { simulated_gate_state: 'CAUTION_TRANSITION' },
    { simulated_gate_state: 'CLOSED_SALINITY_BARRIER' }, { simulated_gate_state: 'UNKNOWN' },
  ], thresholds: { open_below_ec_ms_m: 100, close_at_or_above_ec_ms_m: 150 }, isohaline_boundaries: [
    { salinity_g_l: 1, status: 'WITHIN_CORRIDOR', intrusion_distance_km: 12, coordinate: [106, 10] },
    { salinity_g_l: 4, status: 'NOT_REACHED_AT_ESTUARY' },
    { salinity_g_l: 2, status: 'WITHIN_CORRIDOR', intrusion_distance_km: 10, coordinate: [106, 10] },
  ] });
  const box = get('simulationSpatialSummary'), [counts, levels] = box.children;
  assert.equal(box.hidden, false);
  assert.deepEqual(counts.children.map(item => item.textContent), [
    'Mô phỏng · 4 cống', '1 thuận lợi theo ngưỡng', '1 cần đo kiểm', '1 ngăn mặn', '1 chưa xác định',
  ]);
  assert.deepEqual(levels.children.map(item => item.textContent), [
    'EC dưới 100 mS/m: dưới ngưỡng lấy',
    'EC 100–<150 mS/m: chuyển tiếp',
    'EC từ 150 mS/m: đạt ngưỡng ngừng lấy',
  ]);
  renderSpatialSummary(null);
  assert.equal(box.hidden, true);
  assert.deepEqual(box.children, []);
});

test('overview actions dispatch scenario contracts directly and navigate to forecast tool', t => {
  const get = installDOM(t), actions = [], panels = [];
  const workflow = { after(panel) { panels.push(panel); } };
  document.querySelector = selector => selector === '.workflow-cards' ? workflow : null;
  // This DOM stub ordinarily auto-creates IDs; mimic missing dynamically mounted panel.
  const originalGet = document.getElementById;
  document.getElementById = id => id === 'quickSpatialScenarios' ? panels[0] || null : originalGet(id);
  const previousLocation = globalThis.location;
  globalThis.location = { hash: '#overview' };
  t.after(() => { if (previousLocation === undefined) delete globalThis.location; else globalThis.location = previousLocation; });
  window.addEventListener('workspace:simulation-scenario', event => actions.push(event.detail));
  mountQuickScenarios(); mountQuickScenarios();
  assert.equal(panels.length, 1, 'summary reload must not duplicate quick actions');
  const grid = panels[0].children.at(-1);
  assert.equal(grid.children.length, 4);
  for (const card of grid.children) card.children.at(-1).dispatchEvent(new Event('click'));
  assert.deepEqual(actions, [{ month: '2024-04' }, { month: '2022-10' }, { preset: 'durian' }]);
  assert.equal(location.hash, 'forecasts');
});
