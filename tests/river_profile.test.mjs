import test from 'node:test';
import assert from 'node:assert/strict';
import { riverProfileData, profileSelectionDetail, createRiverProfile } from '../frontend/src/features/river-profile.js';

const frame = {
  river_segments: Array.from({ length: 35 }, (_, index) => ({ properties: {
    chainage_start_km: index * 5, chainage_end_km: (index + 1) * 5,
    chainage_km: index * 5 + 2.5, start_ec_mS_m: index * 10,
    end_ec_mS_m: (index + 1) * 10, ec_mS_m: index * 10 + 5,
  } })),
  thresholds: { open_below_ec_ms_m: 120, close_at_or_above_ec_ms_m: 150 },
  gates: Array.from({ length: 27 }, (_, index) => ({ gate_code: `G${index}`, chainage_km: index < 5 ? 125 : index * 4 })),
  isohaline_boundaries: [{ salinity_g_l: 1, chainage_km: 90 }, { salinity_g_l: 4, chainage_km: null }],
};
test('profile uses segment endpoints and midpoints over the complete 175 km axis', () => {
  const data = riverProfileData(frame);
  assert.deepEqual(data.extent, [0, 175]);
  assert.deepEqual(data.points[0], [0, 0]);
  assert.deepEqual(data.points.at(-1), [175, 350]);
  assert.equal(data.points.length, 71);
  assert.deepEqual(data.thresholds, [120, 150]);
  assert.equal(data.fronts.length, 1);
  assert.ok(data.max > 350);
});
test('salinity conversion changes values and thresholds together without moving gates or fronts', () => {
  const ec = riverProfileData(frame), salinity = riverProfileData(frame, 'salinity');
  assert.equal(salinity.points.at(-1)[1], 350 * 0.0064);
  assert.deepEqual(salinity.thresholds, [120 * 0.0064, 150 * 0.0064]);
  assert.equal(salinity.unit, 'g/L');
  assert.deepEqual(salinity.gates, ec.gates);
  assert.deepEqual(salinity.fronts, ec.fronts);
});
test('all 27 gates remain individually represented, coincident chainages get distinct lanes without x jitter', () => {
  const data = riverProfileData(frame);
  assert.equal(data.gates.length, 27);
  assert.equal(new Set(data.gates.map(row => row.gate.gate_code)).size, 27);
  const coincident = data.gates.filter(row => row.gate.chainage_km === 125);
  assert.equal(new Set(coincident.map(row => row.lane)).size, 5);
  assert.ok(coincident.every(row => row.x === 125 / 175));
  assert.ok(data.gates.every((row, index) => !index || data.gates[index - 1].x <= row.x));
});
test('profile selection requests the shared map drawer and map focus without dossier side effects', () => {
  assert.deepEqual(profileSelectionDetail('G10'), { gate_code: 'G10', focus: true, source: 'profile', interaction: 'activate' });
  assert.deepEqual(profileSelectionDetail('G10', 'hover'), { gate_code: 'G10', focus: true, source: 'profile', interaction: 'hover' });
  assert.deepEqual(riverProfileData(null).gates, []);
});

test('loading preserves selection and hover remains distinct from explicit activation', t => {
  class Element extends EventTarget {
    constructor(tagName) { super(); this.tagName = tagName; }
    children = []; dataset = {}; attributes = {}; style = { setProperty() {} };
    classList = { toggle() {} };
    setAttribute(key, value) { this.attributes[key] = value; }
    append(...children) { this.children.push(...children); }
    replaceChildren() { this.children = []; }
    querySelectorAll() {
      return this.children.flatMap(child => [...(child.dataset.gateCode ? [child] : []), ...child.querySelectorAll()]);
    }
  }
  const win = new EventTarget();
  win.CustomEvent = CustomEvent;
  const doc = { defaultView: win, createElement: name => new Element(name), createElementNS: (_, name) => new Element(name) };
  const host = new Element('div'); host.ownerDocument = doc;
  const profile = createRiverProfile(host);
  const events = [];
  win.addEventListener('workspace:select-simulation-gate', event => events.push(event.detail));
  profile.setFrame(frame);
  win.dispatchEvent(new CustomEvent('workspace:simulation-gate-selected', { detail: { gate_code: 'G10' } }));
  profile.clear();
  assert.equal(host.hidden, true);
  profile.setFrame(frame);
  const selected = host.querySelectorAll().filter(element => element.attributes['aria-pressed'] === 'true');
  assert.equal(selected.length, 2);
  assert.ok(selected.every(element => element.dataset.gateCode === 'G10'));
  const button = selected.find(element => element.tagName === 'button');
  t.mock.timers.enable({ apis: ['setTimeout'] });
  button.dispatchEvent(new Event('pointerenter'));
  t.mock.timers.tick(150);
  assert.equal(events.at(-1).interaction, 'hover');
  assert.equal(events.at(-1).focus, true);
  button.dispatchEvent(new Event('click'));
  assert.equal(events.at(-1).interaction, 'activate');
  win.dispatchEvent(new CustomEvent('workspace:simulation-gate-selected', { detail: { gate_code: null } }));
  assert.ok(host.querySelectorAll().every(element => element.attributes['aria-pressed'] === 'false'));
});
