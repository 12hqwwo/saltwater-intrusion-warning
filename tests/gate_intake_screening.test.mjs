import assert from 'node:assert/strict';
import test from 'node:test';
import { createGateIntakeScreening } from '../frontend/src/features/gate-intake-screening.js';
import { evaluateGateIntakeCondition } from '../frontend/src/shared/gate-intake-rules.js';

// Small DOM harness: exercise public form events and rendered text, with an injected clock.
class Element extends EventTarget {
  children = []; dataset = {}; checked = false; disabled = false; attributes = {}; _text = ''; _value = '';
  constructor(tag) { super(); this.tagName = tag; }
  set value(value) { this._value = String(value); } get value() { return this._value; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(' '); }
  setAttribute(key, value) { this.attributes[key] = value; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this._text = ''; this.children = [...children]; }
}
function harness(t, serverEvaluate = payload => Promise.resolve(evaluateGateIntakeCondition(
  payload.measurement, payload.profile, payload.forecast_context, payload.now_iso)).then(result => ({
    status: result.status, criteriaChecks: result.criteriaChecks,
    effectiveMaxSampleAgeHours: result.forecastAdvisory.effectiveMaxSampleAgeHours,
  }))) {
  const previous = globalThis.document;
  const doc = new EventTarget(); doc.hidden = false; doc.createElement = tag => new Element(tag);
  globalThis.document = doc;
  const events = new EventTarget(), host = new Element('div'), timers = new Map();
  let clock = '2026-11-01T10:00:00Z', timerId = 0;
  const app = createGateIntakeScreening(host, { now: () => clock, eventTarget: events, documentTarget: doc,
    serverEvaluate,
    schedule: (callback, delay) => { timers.set(++timerId, { callback, delay }); return timerId; }, cancel: id => timers.delete(id) });
  t.after(() => { app.destroy(); globalThis.document = previous; });
  const all = (root = host) => [root, ...root.children.flatMap(child => all(child))];
  const find = predicate => all().find(predicate);
  const control = name => find(item => item.name === name);
  const id = value => find(item => item.id === value);
  const fill = (patch = {}) => {
    for (const [name, value] of Object.entries({ exteriorEcMsM: 100, interiorEcMsM: 90, exteriorStageM: 1.2,
      interiorStageM: 1, measuredAtLocal: '2026-11-01T16:00', measuredBy: 'Phiếu đo 01', mechanicalStatus: 'READY', ...patch })) control(name).value = value;
    control('sameElevationDatum').checked = true;
  };
  const edit = (name, value) => { control(name).value = value; id('gateIntakeForm').dispatchEvent(new Event('input')); };
  return { app, host, events, doc, timers, all, control, id, fill, edit,
    setClock: value => { clock = value; }, select: patch => app.setGate({ gate_code: 'A', gate_name: 'Cống A', ...patch }) };
}

test('server agreement permits export and a mismatch blocks it', async t => {
  const h = harness(t); h.select(); h.fill(); h.app.evaluate();
  await new Promise(resolve => setImmediate(resolve));
  assert.match(h.id('gateIntakeServerStatus').textContent, /cùng kết quả/);
  assert.equal(h.all().find(item => item.textContent === 'Tải bảng kiểm tra JSON ↓').disabled, false);
  h.app.destroy();
  const mismatch = harness(t, async () => ({ status: 'NOT_SUITABLE', criteriaChecks: [] }));
  mismatch.select(); mismatch.fill(); mismatch.app.evaluate();
  await new Promise(resolve => setImmediate(resolve));
  assert.match(mismatch.id('gateIntakeServerStatus').textContent, /Kết quả khác nhau/);
  assert.equal(mismatch.all().find(item => item.textContent === 'Tải bảng kiểm tra JSON ↓').disabled, true);
});

test('new screening shows distinct forecast and field sections with independent empty measurements', t => {
  const h = harness(t); h.select();
  assert.match(h.host.textContent, /Phần A/); assert.match(h.host.textContent, /Phần B/);
  h.app.setForecastContext({ mythoEc: 200, mythuanEc: 190, tanchauEc: 180, sourceModel: 'RF_compact', targetMonth: '2026-11' });
  h.app.setSpatialFrame({ gates: [{ gate_code: 'A', chainage_km: 60, simulated_outside_ec_mS_m: 99 }] });
  assert.equal(h.control('exteriorEcMsM').value, '');
  assert.equal(h.control('measuredAtLocal').value, '');
  assert.equal(h.control('sameElevationDatum').checked, false);
  assert.match(h.id('gateIntakeForecastSummary').textContent, /2 giờ/);
  assert.equal(h.app.evaluate().status, 'INSUFFICIENT_OR_EXPIRED_DATA');
});

test('form submission renders all criteria, human-readable units and exact GMT+7 expiry', t => {
  const h = harness(t); h.select(); h.fill();
  h.id('gateIntakeForm').dispatchEvent(new Event('submit', { cancelable: true }));
  const result = h.app.getResult();
  assert.equal(result.status, 'ELIGIBLE_FOR_REVIEW');
  assert.equal(result.measurementInput.measuredAtIso, '2026-11-01T16:00:00+07:00');
  assert.equal(result.validUntilIso, '2026-11-01T15:00:00.000Z');
  assert.equal(h.id('gateIntakeCriteria').children.length, 7);
  assert.match(h.id('gateIntakeCriteria').textContent, /≤ 156,25 mS\/m/);
  assert.match(h.id('gateIntakeCriteria').textContent, /≥ 0,05 m/);
  assert.match(h.id('gateIntakeConclusion').textContent, /Đề nghị xem xét lấy nước/);
  assert.match(h.id('gateIntakeExpiry').textContent, /GMT\+7/);
  assert.equal(h.app.getResult().forecastAdvisory.effectiveMaxSampleAgeHours, 6);
});

test('live forecast context immediately tightens a three-hour sample and restores normal lifetime on clear', t => {
  const h = harness(t); h.select(); h.fill({ measuredAtLocal: '2026-11-01T14:00' });
  assert.equal(h.app.evaluate().status, 'ELIGIBLE_FOR_REVIEW');
  h.events.dispatchEvent(new CustomEvent('workspace:active-forecast-context', { detail: { mythoEc: 60.42, sourceModel: 'MULTIVARIATE_RF_5', targetMonth: '2026-11' } }));
  assert.equal(h.app.getResult().status, 'INSUFFICIENT_OR_EXPIRED_DATA');
  assert.equal(h.app.getResult().validUntilIso, null);
  assert.match(h.id('gateIntakeConclusion').textContent, /Cần bổ sung hoặc đo lại/);
  assert.equal(h.control('exteriorEcMsM').value, '100');
  h.events.dispatchEvent(new CustomEvent('workspace:active-forecast-context', { detail: null }));
  assert.equal(h.app.getResult().status, 'ELIGIBLE_FOR_REVIEW');
  assert.match(h.id('gateIntakeForecastSummary').textContent, /Chưa có ngữ cảnh dự báo/);
});

test('field and profile edits discard stale conclusions and re-evaluation records customized profile', t => {
  const h = harness(t); h.select(); h.fill(); h.app.evaluate();
  h.edit('exteriorEcMsM', 200);
  assert.equal(h.app.getResult(), null);
  assert.equal(h.id('gateIntakeCriteria').children.length, 0);
  assert.equal(h.app.evaluate().status, 'NOT_SUITABLE');
  h.edit('maxExteriorEcMsM', 250);
  assert.equal(h.app.getResult(), null);
  assert.equal(h.app.evaluate().status, 'ELIGIBLE_FOR_REVIEW');
  assert.equal(h.app.getResult().ruleVersion, 'TECH_SCREENING_RULE_V1.0+CUSTOM');
  assert.equal(h.app.getResult().ruleProfile.maxExteriorEcMsM, 250);
  h.edit('maxSampleAgeHoursNormal', '');
  assert.equal(h.app.evaluate(), null);
  assert.match(h.id('gateIntakeConclusion').textContent, /Ngưỡng/);
});

test('same gate updates retain fields; choosing another gate or clearing selection removes old evidence', t => {
  const h = harness(t); h.select(); h.fill(); h.app.evaluate();
  h.select({ chainage_km: 50 });
  assert.equal(h.app.getResult().status, 'ELIGIBLE_FOR_REVIEW');
  h.select({ gate_code: 'B', gate_name: 'Cống B' });
  assert.equal(h.app.getResult(), null);
  for (const name of ['exteriorEcMsM', 'interiorEcMsM', 'exteriorStageM', 'interiorStageM', 'measuredAtLocal', 'mechanicalStatus', 'measuredBy']) assert.equal(h.control(name).value, '');
  assert.equal(h.control('sameElevationDatum').checked, false);
  h.app.setGate(null);
  assert.equal(h.app.evaluate(), null);
  assert.ok(h.all().find(item => item.type === 'submit').disabled);
});

test('expiry timer removes eligibility at expiry plus one millisecond and is cleared on edits/destroy', t => {
  const h = harness(t); h.select(); h.fill(); h.app.evaluate();
  const timer = [...h.timers.values()][0];
  assert.equal(timer.delay, 5 * 3600000 + 1);
  h.setClock('2026-11-01T15:00:00.001Z'); timer.callback();
  assert.equal(h.app.getResult().status, 'INSUFFICIENT_OR_EXPIRED_DATA');
  assert.equal(h.timers.size, 0);
  h.setClock('2026-11-01T10:00:00Z'); h.app.evaluate();
  assert.equal(h.timers.size, 1);
  h.edit('measuredBy', 'Phiếu mới'); assert.equal(h.timers.size, 0);
  h.app.evaluate(); h.app.destroy(); assert.equal(h.timers.size, 0);
  h.events.dispatchEvent(new CustomEvent('workspace:active-forecast-context', { detail: { isHighVigilance: true } }));
  assert.equal(h.app.getResult().forecastAdvisory.effectiveMaxSampleAgeHours, 6);
});

test('focus and visibility refresh catch sample expiry after a suspended browser tab', t => {
  const h = harness(t); h.select(); h.fill(); h.app.evaluate(); h.doc.hidden = true;
  h.setClock('2026-11-01T16:00:00Z'); h.doc.dispatchEvent(new Event('visibilitychange'));
  assert.equal(h.app.getResult().status, 'ELIGIBLE_FOR_REVIEW');
  h.doc.hidden = false; h.events.dispatchEvent(new Event('focus'));
  assert.equal(h.app.getResult().status, 'INSUFFICIENT_OR_EXPIRED_DATA');
});

test('original spatial frame projects gate forecast and can activate vigilance with a normal MyTho forecast', t => {
  const h = harness(t); h.select(); h.fill({ measuredAtLocal: '2026-11-01T14:00' });
  h.app.setForecastContext({ mythoEc: 20, mythuanEc: 80, tanchauEc: 140, sourceModel: 'RF_compact' });
  assert.equal(h.app.evaluate().status, 'ELIGIBLE_FOR_REVIEW');
  h.events.dispatchEvent(new CustomEvent('workspace:simulation-frame', { detail: { gates: [{ gate_code: 'A', chainage_km: 0 }] } }));
  assert.equal(h.app.getResult().forecastAdvisory.projectedGateEc, 140);
  assert.equal(h.app.getResult().status, 'INSUFFICIENT_OR_EXPIRED_DATA');
  assert.match(h.id('gateIntakeForecastSummary').textContent, /vị trí chiếu của cống: 140/);
});
