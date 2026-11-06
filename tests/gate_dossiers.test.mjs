import assert from 'node:assert/strict';
import test from 'node:test';
import { createGateDossiers } from '../frontend/src/features/gate-dossiers.js';
import { createSpatialGateDraft, validateGateDraftPair, validForecastReference } from '../frontend/src/features/gate-simulation-draft.js';

const flush = () => new Promise(setImmediate);
const forecast = (station = 'MyTho', ec = 30, month = '2026-11') => ({ station,
  site_code: { MyTho: 'MRC_VN_019805', MyThuan: 'MRC_VN_019804', TanChau: 'MRC_VN_019803' }[station], target_month: month, input_month: month === '2026-11' ? '2026-09' : '2026-10',
  input_mode: 'ARCHIVE', predicted_ec_mS_m: ec, unit: 'mS/m', inputs: [
    { name: 'rainfall_mm', value: 10, unit: 'mm' }, { name: 'temperature_degC', value: 25, unit: 'degC' }, { name: 'wind_source_units', value: 2, unit: 'm/s' },
  ] });
const draft = () => createSpatialGateDraft({ kind: 'SPATIAL_SIMULATION', year_month: '2026-08',
  gate: { gate_code: 'A', simulated_outside_ec_mS_m: 70 }, thresholds: { open_below_ec_ms_m: 50, close_at_or_above_ec_ms_m: 80 } });
class Element extends EventTarget {
  children = []; dataset = {}; _text = ''; _value; disabled = false;
  constructor(tag) { super(); this.tagName = tag; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(' '); }
  set value(value) { this._value = String(value); }
  get value() { return this._value ?? (this.tagName === 'select' ? this.children[0]?.value || '' : ''); }
  setAttribute(name, value) { this[name] = value; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this._text = ''; this.children = [...children]; this._value = undefined; }
}
const nodes = root => [root, ...root.children.flatMap(nodes)];
function harness(t, handler) {
  const elements = new Map(['gateSelect', 'gateInfo', 'gateContextStatus', 'loadDatabaseGates', 'databaseGateStatus', 'databaseGateList', 'gateIntakeScreeningHost']
    .map(id => [id, new Element(id === 'gateSelect' ? 'select' : 'div')]));
  const previous = Object.fromEntries(['window', 'document', 'location'].map(key => [key, globalThis[key]]));
  const doc = new EventTarget(); doc.getElementById = id => elements.get(id) || null; doc.createElement = tag => new Element(tag);
  globalThis.document = doc; globalThis.window = new EventTarget(); globalThis.location = { hash: '' };
  const calls = [], candidates = [], mappedGates = [];
  t.mock.method(globalThis, 'fetch', async (path, options) => {
    const url = new URL(path, 'https://test.invalid'), body = options.body ? JSON.parse(options.body) : null;
    const call = { url, options, body }; calls.push(call);
    const overridden = await handler?.(call);
    const result = overridden ?? (url.pathname.endsWith('/database-gates') ? { items: [{ gate_code: 'DB_A', gate_name: 'Cống database' }], note: '' }
      : url.pathname.endsWith('/candidate-stations') ? { gate_geometry: null, items: [], note: '' }
        : url.pathname.endsWith('/multivariate/predict') ? forecast(body.station, 20, body.target_month) : null);
    return { ok: true, json: async () => structuredClone(result) };
  });
  const app = createGateDossiers({ setCandidates: (...args) => candidates.push(args), setGates: gates => mappedGates.push(gates) });
  t.after(() => { app.destroy(); for (const [key, value] of Object.entries(previous)) { if (value === undefined) delete globalThis[key]; else globalThis[key] = value; } });
  const get = id => elements.get(id), fieldNodes = () => nodes(get('gateIntakeScreeningHost'));
  const control = name => fieldNodes().find(item => item.name === name);
  const change = code => { get('gateSelect').value = code; get('gateSelect').dispatchEvent(new Event('change')); };
  const load = () => app.load(['A', 'B'].map(gate_code => ({ gate_code, gate_name: `Cống ${gate_code}`, source_id: 'DT_GATE_CATALOG_2025' })));
  return { app, get, calls, candidates, mappedGates, fieldNodes, control, change, load };
}

test('legacy JSON contracts remain usable independently of the removed form', () => {
  assert.equal(validForecastReference(forecast()), true);
  assert.equal(validForecastReference(forecast('MyThuan')), true);
  const value = draft();
  assert.equal(validateGateDraftPair(value.input, value.policy, 'A').input.observations.outside_quality.observed_at, null);
  value.input.observations.outside_quality.unit = 'g/L';
  assert.throws(() => validateGateDraftPair(value.input, value.policy, 'A'));
});

test('catalogue selection uses only the stage 2 form and does not request templates or evaluate empty scenarios', async t => {
  const h = harness(t); await h.load();
  assert.equal(h.get('gateSelect').value, 'A');
  assert.match(h.get('gateInfo').textContent, /Mã A/);
  assert.doesNotMatch(h.get('gateInfo').textContent, /undefined/);
  assert.equal(h.control('exteriorEcMsM').value, '');
  assert.equal(h.control('sameElevationDatum').checked, false);
  assert.equal(h.calls.length, 0);
  assert.equal(h.fieldNodes().filter(item => item.tagName === 'form').length, 1);
});

test('changing or clearing a gate removes previously entered field measurements and candidate lines', async t => {
  const h = harness(t); await h.load();
  h.control('exteriorEcMsM').value = 100; h.control('sameElevationDatum').checked = true;
  h.change('B');
  assert.equal(h.control('exteriorEcMsM').value, ''); assert.equal(h.control('sameElevationDatum').checked, false);
  h.change('missing');
  assert.equal(h.get('gateInfo').textContent, '');
  assert.equal(h.fieldNodes().find(item => item.type === 'submit').disabled, true);
  assert.deepEqual(h.candidates.at(-1), [null, []]);
});

test('GIS gates arrive before or after catalogue load, retain selection and never query database candidates', async t => {
  const h = harness(t);
  const frame = { gates: [{ gate_code: 'GIS_A', gate_name: 'Cống GIS', chainage_km: 125 }] };
  window.dispatchEvent(new CustomEvent('workspace:simulation-frame', { detail: frame }));
  await h.load(); h.change('GIS_A'); h.control('exteriorEcMsM').value = 99;
  window.dispatchEvent(new CustomEvent('workspace:simulation-frame', { detail: frame }));
  assert.equal(h.get('gateSelect').value, 'GIS_A');
  assert.equal(h.get('gateSelect').children.filter(option => option.value === 'GIS_A').length, 1);
  assert.equal(h.control('exteriorEcMsM').value, '99', 'same gate metadata update retains measurements');
  assert.equal(h.calls.length, 0);
});

test('map transfer selects the real gate without copying simulated EC into field measurements', async t => {
  const h = harness(t); await h.load();
  const gate = { gate_code: 'GIS_A', gate_name: 'Cống GIS', simulated_outside_ec_mS_m: 70 };
  const detail = { kind: 'SPATIAL_SIMULATION', year_month: '2026-08', gate,
    frame: { simulation_layer: true, year_month: '2026-08', gates: [gate] } };
  window.dispatchEvent(new CustomEvent('workspace:apply-simulation-gate', { detail }));
  assert.equal(h.get('gateSelect').value, 'GIS_A'); assert.equal(location.hash, 'gates');
  assert.equal(h.control('exteriorEcMsM').value, ''); assert.equal(h.calls.length, 0);
  window.dispatchEvent(new CustomEvent('workspace:apply-forecast-to-gate', { detail }));
  assert.equal(h.calls.length, 0);
  window.dispatchEvent(new CustomEvent('workspace:apply-simulation-gate', { detail: { ...detail, gate: { ...gate, gate_code: 'STALE' } } }));
  assert.equal(h.get('gateSelect').value, 'GIS_A');
});

test('database gates remain selectable and ignore late candidate results after another selection', async t => {
  let release;
  const h = harness(t, call => call.url.pathname.endsWith('/candidate-stations') ? new Promise(resolve => { release = resolve; }) : undefined);
  await h.load(); h.get('loadDatabaseGates').dispatchEvent(new Event('click')); await flush();
  assert.equal(h.mappedGates.length, 1); assert.equal(h.get('loadDatabaseGates').disabled, false);
  h.change('DB_A'); await flush(); assert.equal(typeof release, 'function');
  h.change('B'); release({ gate_geometry: {}, items: [{ site_name: 'Late', distance_m: 1000 }] }); await flush();
  assert.equal(h.get('gateSelect').value, 'B'); assert.deepEqual(h.candidates.at(-1), [null, []]);
});

test('direct forecast obtains a matching counterpart and affects advisory without filling field EC', async t => {
  const h = harness(t); await h.load();
  window.dispatchEvent(new CustomEvent('workspace:apply-forecast-to-gate', { detail: forecast('MyTho', 85) })); await flush();
  assert.equal(h.calls.length, 2); assert.deepEqual(h.calls.map(c => c.body.station), ['TanChau', 'MyThuan']);
  assert.equal(h.calls[0].body.persist, undefined);
  assert.match(h.get('gateContextStatus').textContent, /Đã dùng dự báo/);
  const summary = h.fieldNodes().find(item => item.id === 'gateIntakeForecastSummary').textContent;
  assert.match(summary, /2 giờ/); assert.match(summary, /85/);
  assert.equal(h.control('exteriorEcMsM').value, '');
});

test('a late direct forecast cannot overwrite a newer shared forecast context', async t => {
  const pending = [];
  const h = harness(t, call => call.url.pathname.endsWith('/multivariate/predict') ? new Promise(resolve => { pending.push(() => resolve(forecast(call.body.station, 10))); }) : undefined);
  await h.load();
  window.dispatchEvent(new CustomEvent('workspace:apply-forecast-to-gate', { detail: forecast('MyTho', 85) })); await flush();
  window.dispatchEvent(new CustomEvent('workspace:active-forecast-context', { detail: { sourceModel: 'RF_compact', mythoEc: 20, mythuanEc: 20, tanchauEc: 20, targetMonth: '2026-12' } }));
  assert.equal(pending.length, 2); pending.forEach(release => release()); await flush();
  const summary = h.fieldNodes().find(item => item.id === 'gateIntakeForecastSummary').textContent;
  assert.match(summary, /RF_compact/); assert.match(summary, /2026-12/); assert.match(summary, /6 giờ/);
  assert.equal(h.get('gateContextStatus').textContent, '');
});

test('wrong forecast counterpart is reported without replacing existing advisory', async t => {
  const h = harness(t, call => call.url.pathname.endsWith('/multivariate/predict') ? forecast('MyTho', 20) : undefined);
  await h.load();
  window.dispatchEvent(new CustomEvent('workspace:apply-forecast-to-gate', { detail: forecast('MyTho', 85) })); await flush();
  assert.match(h.get('gateContextStatus').textContent, /Chưa áp dụng được dự báo/);
  assert.match(h.fieldNodes().find(item => item.id === 'gateIntakeForecastSummary').textContent, /Chưa có ngữ cảnh/);
});
