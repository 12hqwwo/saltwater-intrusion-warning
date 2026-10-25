import assert from 'node:assert/strict';
import test from 'node:test';
import { ADVISORY_PRESETS, validateThresholds, createSimulationFrameLoader, createTimelineScrubber } from '../frontend/src/features/timeline-scrubber.js';

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
