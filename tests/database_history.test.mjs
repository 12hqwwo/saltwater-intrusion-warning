import assert from 'node:assert/strict';
import test from 'node:test';
import { createDatabaseHistory } from '../frontend/src/features/database-history.js';

class Element {
  constructor(tag = 'div') { this.tagName = tag; this.children = []; this.listeners = {}; this.style = {}; this.dataset = {}; this._text = ''; this._value = undefined; this.disabled = false; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(' '); }
  set value(value) { this._value = String(value); }
  get value() { return this._value ?? (this.tagName === 'select' ? this.children[0]?.value || '' : ''); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this._text = ''; this._value = undefined; this.children = [...children]; }
  setAttribute(name, value) { this[name] = value; }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  async emit(name) { await Promise.all((this.listeners[name] || []).map(callback => callback({ preventDefault() {} }))); }
  click() { return this.emit('click'); }
}
const all = element => [element, ...element.children.flatMap(all)];
const flush = () => new Promise(setImmediate);
function setup(t) {
  const host = new Element(), pending = [], downloads = [];
  const old = Object.fromEntries(['document', 'Option'].map(key => [key, globalThis[key]]));
  const originalCreate = URL.createObjectURL, originalRevoke = URL.revokeObjectURL;
  globalThis.document = { getElementById: () => host, createElement: tag => new Element(tag), createElementNS: (_ns, tag) => new Element(tag) };
  globalThis.Option = class extends Element { constructor(label, value) { super('option'); this.textContent = label; this.value = value; } };
  URL.createObjectURL = blob => { downloads.push(blob); return 'blob:test'; }; URL.revokeObjectURL = () => {};
  t.mock.method(globalThis, 'fetch', (path, options) => new Promise((resolve, reject) => pending.push({
    path, options, reject,
    respond(data, ok = true) { resolve({ ok, status: ok ? 200 : 503, json: async () => data }); },
  })));
  t.after(() => {
    for (const [key, value] of Object.entries(old)) { if (value === undefined) delete globalThis[key]; else globalThis[key] = value; }
    URL.createObjectURL = originalCreate; URL.revokeObjectURL = originalRevoke;
  });
  const feature = createDatabaseHistory();
  const nodes = all(host), selects = nodes.filter(node => node.tagName === 'select'), dates = nodes.filter(node => node.type === 'date');
  const ui = { host, feature, pending, downloads, source: selects[0], station: selects[1], kind: selects[2], from: dates[0], to: dates[1],
    form: nodes.find(node => node.tagName === 'form'), csv: nodes.find(node => node.textContent === 'Xuất CSV đã lọc'),
    chart: nodes.find(node => node.className === 'history-chart'), body: nodes.find(node => node.tagName === 'tbody'), metrics: host.children[5], status: host.children[3] };
  t.after(() => feature.destroy());
  return ui;
}
const stations = { type: 'FeatureCollection', features: ['A', 'B'].map((code, index) => ({
  type: 'Feature', properties: { site_code: code, site_name: code, source_code: `S${index + 1}` }, geometry: null,
})) };
function datasets(site) { return { site_code: site, unit: 'mS/m', items: [{ dataset_code: `D_${site}`, first_observation: '2022-01-01T00:00:00+07:00', last_observation: '2023-12-01T00:00:00+07:00' }] }; }
function history(request, value = 42) {
  const url = new URL(request.path, 'https://test.invalid'), site = url.pathname.split('/')[4];
  return { site_code: site, dataset: { dataset_code: url.searchParams.get('dataset_code'), sha256: 'fixed' }, unit: 'mS/m', total: 1, offset: 0, has_more: false,
    filters: Object.fromEntries(['date_from', 'date_to', 'observed_or_estimated'].map(key => [key, url.searchParams.get(key) || ''])),
    items: [{ ec_observation_id: 1, observed_at: '2023-12-01T00:00:00+07:00', conductivity_ms_per_m: value, unit: 'mS/m', quality_flag: 'UNVERIFIED', observed_or_estimated: 'O' }] };
}
async function connected(t) {
  const ui = setup(t), loading = ui.feature.load(); ui.pending.at(-1).respond(stations); await loading;
  const selecting = ui.feature.selectStation('A'); ui.pending.at(-1).respond(datasets('A')); await selecting;
  return ui;
}
async function loaded(t) {
  const ui = await connected(t);
  await ui.form.emit('submit'); ui.pending.at(-1).respond(history(ui.pending.at(-1))); await flush();
  assert.equal(ui.csv.disabled, false); assert.ok(all(ui.chart).some(node => node.tagName === 'svg'));
  assert.match(ui.metrics.textContent, /42/); return ui;
}
function assertEmpty(ui) {
  assert.equal(ui.metrics.textContent, '');
  assert.equal(all(ui.chart).some(node => node.tagName === 'svg'), false);
  assert.equal(ui.body.children.length, 1);
  assert.match(ui.body.textContent, /Chưa có số đo/);
  assert.equal(ui.csv.disabled, true);
}

test('date and kind edits immediately clear chart, rows, statistics and CSV without another request', async t => {
  for (const field of ['from', 'to', 'kind']) {
    await t.test(field, async sub => {
      const ui = await loaded(sub), count = ui.pending.length;
      ui[field].value = field === 'kind' ? 'E' : '2023-01-01'; await ui[field].emit('input');
      assertEmpty(ui); assert.equal(ui.pending.length, count);
      await ui.csv.emit('click'); assert.equal(ui.downloads.length, 0, 'stale CSV remains unavailable even if its handler is invoked');
    });
  }
});

test('filter edits cancel and ignore late prior history success and failure', async t => {
  for (const failure of [false, true]) {
    await t.test(failure ? 'failure' : 'success', async sub => {
      const ui = await loaded(sub);
      await ui.form.emit('submit'); const previous = ui.pending.at(-1);
      ui.kind.value = 'E'; await ui.kind.emit('input');
      assert.equal(previous.options.signal.aborted, true); assertEmpty(ui);
      const status = ui.status.textContent;
      if (failure) previous.reject(new Error('late failure')); else previous.respond(history(previous, 999));
      await flush();
      assertEmpty(ui); assert.equal(ui.status.textContent, status); assert.doesNotMatch(ui.host.textContent, /999|late failure/);
    });
  }
});

test('source and station changes clear completed values before replacement datasets arrive', async t => {
  const ui = await loaded(t);
  ui.source.value = 'S2'; await ui.source.emit('change'); assertEmpty(ui);
  const selecting = ui.feature.selectStation('B'); assertEmpty(ui);
  ui.pending.at(-1).respond(datasets('B')); await selecting; assertEmpty(ui);
  await ui.form.emit('submit'); const request = ui.pending.at(-1); request.respond(history(request, 27)); await flush();
  assert.match(ui.metrics.textContent, /27/); assert.equal(ui.csv.disabled, false);
});

test('stale dataset success or failure after source change cannot restore a selected dataset', async t => {
  for (const failure of [false, true]) {
    await t.test(failure ? 'failure' : 'success', async sub => {
      const ui = await connected(sub);
      const selecting = ui.feature.selectStation('B'), previous = ui.pending.at(-1);
      ui.source.value = 'S1'; await ui.source.emit('change'); const status = ui.status.textContent;
      assert.equal(previous.options.signal.aborted, true);
      if (failure) previous.reject(new Error('late dataset failure')); else previous.respond(datasets('B'));
      await selecting;
      assertEmpty(ui); assert.equal(ui.status.textContent, status);
      const count = ui.pending.length; await ui.form.emit('submit'); assert.equal(ui.pending.length, count, 'no stale dataset may make history runnable');
    });
  }
});

test('new station selection wins over a delayed previous station dataset', async t => {
  const ui = await connected(t), old = ui.feature.selectStation('A'), previous = ui.pending.at(-1);
  const latest = ui.feature.selectStation('B'); ui.pending.at(-1).respond(datasets('B')); await latest;
  previous.respond(datasets('A')); await old;
  await ui.form.emit('submit'); const request = ui.pending.at(-1), url = new URL(request.path, 'https://test.invalid');
  assert.equal(ui.station.value, 'B'); assert.match(url.pathname, /stations\/B\/observations$/); assert.equal(url.searchParams.get('dataset_code'), 'D_B');
  request.respond(history(request)); await flush(); assert.equal(ui.csv.disabled, false);
});
