import assert from 'node:assert/strict';
import test from 'node:test';
import { createGateDossiers } from '../frontend/src/features/gate-dossiers.js';
import { createSpatialGateDraft, validateGateDraftPair, validForecastReference } from '../frontend/src/features/gate-simulation-draft.js';

const copy = value => structuredClone(value);
function draft(code = 'A', month = '2026-08') {
  return createSpatialGateDraft({ kind: 'SPATIAL_SIMULATION', year_month: month,
    gate: { gate_code: code, simulated_outside_ec_mS_m: 70 },
    thresholds: { open_below_ec_ms_m: 50, close_at_or_above_ec_ms_m: 80 } });
}
const forecast = { station: 'MyTho', site_code: 'MRC_VN_019805', target_month: '2026-11', predicted_ec_mS_m: 70, unit: 'mS/m' };
const flush = () => new Promise(setImmediate);

test('gate references validate station, month, units and keep simulated EC separate from observations', () => {
  assert.equal(validForecastReference(forecast), true);
  for (const change of [{ predicted_ec_mS_m: -1 }, { unit: 'g/L' }, { target_month: '2026-13' }, { site_code: 'MRC_VN_019803' }, { station: 'Unknown' }]) {
    assert.equal(validForecastReference({ ...forecast, ...change }), false);
  }
  const value = draft();
  assert.equal(validateGateDraftPair(value.input, value.policy, 'A').input.observations.outside_quality.observed_at, null);
  for (const mutate of [
    d => d.input.observations.inside_level.gate_code = 'B',
    d => d.input.observations.outside_quality.unit = 'g/L',
    d => d.input.observations.outside_quality.observed_at = '2026-08-01T00:00:00+07:00',
    d => d.policy.simulation_context = { ...d.policy.simulation_context, year_month: '2025-07' },
    d => d.input.forecast_context = { ...forecast, attached_gate_code: 'B' },
  ]) {
    const changed = copy(value); mutate(changed);
    assert.throws(() => validateGateDraftPair(changed.input, changed.policy, 'A'));
  }
  assert.equal(createSpatialGateDraft({ kind: 'SPATIAL_SIMULATION', gate: { gate_code: 'A', simulated_outside_ec_mS_m: 70 } }), null);
  assert.equal(createSpatialGateDraft({ kind: 'SPATIAL_SIMULATION', year_month: '2026-08', frame: { year_month: '2026-07' }, gate: { gate_code: 'A', simulated_outside_ec_mS_m: 70 } }), null);
});

function harness(t, handler) {
  class Element extends EventTarget {
    value = ''; textContent = ''; disabled = false; hidden = false; checked = false; files = [];
    children = []; dataset = {}; options = [];
    append(...children) { this.children.push(...children); this.options = this.children; }
    replaceChildren(...children) { this.children = [...children]; this.options = this.children; }
    reset() { for (const field of Object.values(this.elements || {})) { field.value = ''; field.checked = false; } }
  }
  const elements = new Map(), calls = [], candidates = [];
  const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const previous = Object.fromEntries(['document', 'window', 'localStorage', 'location', 'FormData'].map(key => [key, globalThis[key]]));
  globalThis.document = { getElementById: get, createElement: () => new Element() };
  globalThis.window = new EventTarget(); globalThis.location = { hash: '' };
  const stored = new Map(); globalThis.localStorage = { setItem: (k, v) => stored.set(k, v), getItem: k => stored.get(k) };
  globalThis.FormData = class {
    constructor(form) { this.form = form; }
    get(name) { const field = this.form.elements[name]; return name === 'allow_saline_drain' ? (field.checked ? 'on' : null) : field?.value ?? null; }
  };
  const form = get('fieldForm'); form.elements = {};
  for (const name of ['mode', 'outside_level', 'inside_level', 'outside_quality', 'inside_quality', 'observed', 'datum', 'reference', 'method', 'ec_basis', 'open_below', 'close_at_or_above', 'min_head_m', 'max_abs_head_m', 'inside_min_m', 'inside_max_m', 'allow_saline_drain']) form.elements[name] = new Element();
  get('gateSelect').value = 'A';
  t.mock.method(globalThis, 'fetch', async (path, options) => {
    const url = new URL(path, 'https://test.invalid');
    const call = { url, options, body: options.body ? JSON.parse(options.body) : null }; calls.push(call);
    const response = await handler?.(call);
    let data = response;
    const code = url.searchParams.get('gate_code') || 'A';
    if (data === undefined) {
      if (url.pathname.endsWith('/threshold-presets')) data = { items: [] };
      else if (url.pathname.includes('/gate-template/')) data = draft(code)[url.pathname.endsWith('/input') ? 'input' : 'policy'];
      else if (url.pathname.endsWith('/gate-evaluation')) data = { gate_code: call.body.input.gate_code, evaluation_mode: 'SIMULATION', checklist: [], simulation_outcome: 'BLOCKED' };
      else if (url.pathname.endsWith('/candidate-stations')) data = { gate_geometry: null, items: [], note: '' };
      else if (url.pathname.endsWith('/gate-drafts')) data = { items: [] };
    }
    return { ok: true, json: async () => copy(data) };
  });
  t.after(() => { for (const [key, value] of Object.entries(previous)) { if (value === undefined) delete globalThis[key]; else globalThis[key] = value; } });
  const app = createGateDossiers({ setCandidates: (...args) => candidates.push(args), setGates() {} });
  const gates = ['A', 'B'].map(gate_code => ({ gate_code, gate_name: gate_code, source_id: 'DT_GATE_CATALOG_2025' }));
  const change = (id, value) => { get(id).value = value; get(id).dispatchEvent(new Event('change')); };
  return { get, app, calls, candidates, stored, gates, change };
}

test('changing to invalid gate cancels previous evaluation and clears candidate lines', async t => {
  let release;
  const h = harness(t, call => call.url.pathname.endsWith('/gate-evaluation') ? new Promise(resolve => { release = resolve; }) : undefined);
  const loading = h.app.load(h.gates);
  await flush();
  assert.equal(typeof release, 'function');
  h.change('gateSelect', 'missing');
  release({ gate_code: 'A', evaluation_mode: 'SIMULATION', checklist: [], simulation_outcome: 'CONDITIONS_MET' });
  await loading;
  assert.equal(h.get('downloadEvaluation').disabled, true);
  assert.match(h.get('gateResultTitle').textContent, /Chưa có/);
  assert.deepEqual(h.candidates.at(-1), [null, []]);
});

test('failed local restore clears old evaluation and mismatched units are not posted', async t => {
  const h = harness(t); await h.app.load(h.gates);
  assert.equal(h.get('downloadEvaluation').disabled, false);
  h.get('restoreGateDraft').dispatchEvent(new Event('click')); await flush();
  assert.equal(h.get('downloadEvaluation').disabled, true);
  const invalid = draft(); invalid.input.observations.outside_quality.unit = 'g/L';
  h.stored.set('gate-scenario-v1:A', JSON.stringify(invalid));
  const evaluations = h.calls.filter(call => call.url.pathname.endsWith('/gate-evaluation')).length;
  h.get('restoreGateDraft').dispatchEvent(new Event('click')); await flush();
  assert.match(h.get('fieldStatus').textContent, /đơn vị/);
  assert.equal(h.calls.filter(call => call.url.pathname.endsWith('/gate-evaluation')).length, evaluations);
});

test('late file read cannot replace a newer submitted draft; attached forecast remains reference only', async t => {
  const h = harness(t); await h.app.load(h.gates);
  let releaseFile;
  h.get('gateInputFile').files = [{ size: 100, name: 'old.json', text: () => new Promise(resolve => { releaseFile = resolve; }) }];
  h.get('gateInputFile').dispatchEvent(new Event('change'));
  window.dispatchEvent(new CustomEvent('workspace:apply-forecast-to-gate', { detail: forecast }));
  const submit = new Event('submit', { cancelable: true }); submit.submitter = { id: 'saveGateDraft' };
  h.get('fieldForm').dispatchEvent(submit); await flush();
  const stored = JSON.parse(h.stored.get('gate-scenario-v1:A'));
  assert.equal(stored.input.forecast_context.attached_gate_code, 'A');
  assert.equal(stored.input.observations.outside_quality.value, 70);
  assert.equal(stored.input.observations.outside_quality.observed_at, null);
  assert.equal(stored.input.observations.outside_quality.data_kind, 'SIMULATION');
  const old = draft(); old.input.observations.outside_quality.value = 999;
  releaseFile(JSON.stringify(old.input)); await flush();
  assert.notEqual(h.get('fieldForm').elements.outside_quality.value, 999);
  const body = h.calls.filter(call => call.url.pathname.endsWith('/gate-evaluation')).at(-1).body;
  assert.equal(body.input.forecast_context.target_month, '2026-11');
  assert.equal(body.input.observations.outside_quality.value, 70, 'station forecast did not become a gate measurement');
});

test('PostgreSQL restore ignores a late response after selecting another gate', async t => {
  let release;
  const h = harness(t, call => call.url.pathname.endsWith('/gate-drafts') ? new Promise(resolve => { release = resolve; }) : undefined);
  await h.app.load(h.gates);
  h.get('restoreGateDatabaseDraft').dispatchEvent(new Event('click')); await flush();
  h.change('gateSelect', 'B'); await flush();
  release({ items: [{ gate_code: 'A', draft_id: 1, ...draft('A') }] }); await flush();
  assert.equal(h.get('gateSelect').value, 'B');
  assert.equal(h.calls.filter(call => call.url.pathname.endsWith('/gate-evaluation')).at(-1).body.input.gate_code, 'B');
  assert.doesNotMatch(h.get('gateDraftDatabaseStatus').textContent, /#1/);
});

test('simulation transfer rejects gates from a stale or unrelated displayed frame', () => {
  const gate = { gate_code: 'A', simulated_outside_ec_mS_m: 70 };
  const detail = { kind: 'SPATIAL_SIMULATION', year_month: '2026-08', gate,
    frame: { simulation_layer: true, year_month: '2026-08', gates: [{ ...gate }] } };
  assert.ok(createSpatialGateDraft(detail));
  for (const gates of [[], [{ ...gate, gate_code: 'B' }], [{ ...gate, simulated_outside_ec_mS_m: 71 }]]) {
    assert.equal(createSpatialGateDraft({ ...detail, frame: { ...detail.frame, gates } }), null);
  }
});

test('evaluation response for another gate cannot enable result export', async t => {
  const h = harness(t, call => call.url.pathname.endsWith('/gate-evaluation')
    ? { gate_code: 'B', evaluation_mode: 'SIMULATION', checklist: [], simulation_outcome: 'CONDITIONS_MET' } : undefined);
  await h.app.load(h.gates);
  assert.equal(h.get('downloadEvaluation').disabled, true);
  assert.match(h.get('gateEvaluationStatus').textContent, /không khớp/);
});

test('PostgreSQL save and simulation use the same current draft, and edits discard its late status', async t => {
  let release;
  const h = harness(t, call => call.url.pathname.endsWith('/gate-drafts') && call.options.method === 'POST'
    ? new Promise(resolve => { release = resolve; }) : undefined);
  await h.app.load(h.gates);
  h.get('fieldForm').elements.inside_quality.value = '25';
  const submit = new Event('submit', { cancelable: true }); submit.submitter = { id: 'saveGateDatabaseDraft' };
  h.get('fieldForm').dispatchEvent(submit); await flush();
  const post = h.calls.find(call => call.url.pathname.endsWith('/gate-drafts') && call.options.method === 'POST');
  const saved = JSON.parse(h.stored.get('gate-scenario-v1:A'));
  assert.deepEqual(post.body.input, saved.input);
  assert.deepEqual(post.body.policy, saved.policy);
  h.get('fieldForm').dispatchEvent(new Event('input'));
  release({ gate_code: 'A', draft_id: 99, created_at: '2026-10-28' }); await flush();
  assert.doesNotMatch(h.get('gateDraftDatabaseStatus').textContent, /#99/);
  assert.equal(h.get('downloadEvaluation').disabled, true);
  assert.equal(h.calls.filter(call => call.url.pathname.endsWith('/gate-evaluation')).length, 1, 'cancelled save must not evaluate an old payload');
});

test('empty or invalid gate clears old form fields, context and dossier descriptions', async t => {
  const h = harness(t); await h.app.load(h.gates);
  assert.equal(h.get('fieldForm').elements.outside_quality.value, 70);
  h.get('fieldStatus').textContent = 'Saved A'; h.get('gateInfo').textContent = 'Gate A';
  h.change('gateSelect', '');
  for (const field of Object.values(h.get('fieldForm').elements)) assert.equal(field.value, '');
  assert.equal(h.get('fieldStatus').textContent, ''); assert.equal(h.get('gateInfo').textContent, '');
  assert.equal(h.get('gateForecastContext').hidden, true);
  assert.equal(h.get('downloadEvaluation').disabled, true);
  h.get('fieldForm').elements.outside_quality.value = '999'; h.get('gateInfo').textContent = 'stale';
  h.change('gateSelect', 'invalid');
  assert.equal(h.get('fieldForm').elements.outside_quality.value, ''); assert.equal(h.get('gateInfo').textContent, '');
});

test('editing spatial EC preserves original frame as reference and saves current EC as user scenario', async t => {
  const h = harness(t); await h.app.load(h.gates);
  h.get('fieldForm').elements.outside_quality.value = '92';
  h.get('fieldForm').dispatchEvent(new Event('input'));
  assert.ok(h.get('gateForecastContext').children.some(node => /92.*người dùng chỉnh/.test(node.textContent)));
  const submit = new Event('submit', { cancelable: true }); submit.submitter = { id: 'saveGateDraft' };
  h.get('fieldForm').dispatchEvent(submit); await flush();
  const saved = JSON.parse(h.stored.get('gate-scenario-v1:A')), row = saved.input.observations.outside_quality;
  assert.equal(saved.input.simulation_context.simulated_outside_ec_mS_m, 70);
  assert.equal(saved.input.simulation_context.current_scenario_ec_mS_m, 92);
  assert.equal(saved.input.simulation_context.current_value_origin, 'USER_SCENARIO');
  assert.equal(row.value, 92); assert.equal(row.observed_at, null); assert.equal(row.data_kind, 'SIMULATION');
  assert.equal(row.source_reference, 'USER_SCENARIO:A:2026-08');
  assert.doesNotThrow(() => validateGateDraftPair(saved.input, saved.policy, 'A'));
  h.get('restoreGateDraft').dispatchEvent(new Event('click')); await flush();
  assert.equal(h.get('fieldForm').elements.outside_quality.value, 92);
  assert.ok(h.get('gateForecastContext').children.some(node => /92.*người dùng chỉnh/.test(node.textContent)));
  const bad = copy(saved); delete bad.input.simulation_context.current_scenario_ec_mS_m;
  assert.throws(() => validateGateDraftPair(bad.input, bad.policy, 'A'));
});
