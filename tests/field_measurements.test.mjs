import assert from 'node:assert/strict';
import test from 'node:test';
import { convertedEc, approvedMapItems } from '../frontend/src/features/field-measurements.js';
import { fieldMeasurementFeatureCollection } from '../frontend/src/features/observations-map.js';
import { loadApprovedFieldMeasurementsForMap } from '../frontend/src/features/field-measurements/approved-field-measurements-layer.js';

test('field EC units show exact converted value before submission', () => {
  assert.equal(convertedEc('1500', 'µS/cm'), 150);
  assert.equal(convertedEc('1.5', 'dS/m'), 150);
  assert.equal(convertedEc('1.5', 'mS/cm'), 150);
  assert.equal(convertedEc('150', 'mS/m'), 150);
  assert.equal(convertedEc('', 'mS/m'), null);
});

test('pending and rejected measurements never reach the map layer', () => {
  const items = [
    { measurement_id: 'a', status: 'PENDING', longitude: 105.8, latitude: 10.5 },
    { measurement_id: 'b', status: 'REJECTED', longitude: 105.8, latitude: 10.5 },
    { measurement_id: 'c', status: 'APPROVED', longitude: 105.8, latitude: 10.5, ec_mS_m: 150 },
  ];
  assert.deepEqual(approvedMapItems(items).map(item => item.measurement_id), ['c']);
  assert.deepEqual(fieldMeasurementFeatureCollection(items).features.map(item => item.properties.measurement_id), ['c']);
  assert.equal('submitted_by' in fieldMeasurementFeatureCollection(items).features[0].properties, false);
});

test('approved map loader follows every page before publishing', async t => {
  const previous = { document: globalThis.document, window: globalThis.window,
    fetch: globalThis.fetch, CustomEvent: globalThis.CustomEvent };
  t.after(() => Object.assign(globalThis, previous));
  globalThis.document = { createElement: tag => ({ tag, children: [], append(...items) { this.children.push(...items); } }) };
  globalThis.window = new EventTarget();
  globalThis.CustomEvent = class extends Event { constructor(type, options) { super(type); this.detail = options.detail; } };
  const urls = [];
  globalThis.fetch = async url => {
    urls.push(url);
    const second = url.includes('before_measurement_id');
    return { ok: true, status: 200, json: async () => ({
      items: [second ? { measurement_id: 'b', status: 'APPROVED', longitude: 105.9, latitude: 10.6 }
        : { measurement_id: 'a', status: 'APPROVED', longitude: 105.8, latitude: 10.5 }],
      total: 2, has_more: !second,
      next_cursor: second ? null : { before_submitted_at: '2026-11-01T10:00:00+07:00',
        before_measurement_id: '00000000-0000-0000-0000-000000000001' },
    }) };
  };
  const host = { children: [], append(...items) { this.children.push(...items); } };
  const published = new Promise(resolve => window.addEventListener('workspace:approved-field-measurements',
    event => resolve(event.detail), { once: true }));
  const load = loadApprovedFieldMeasurementsForMap(host);
  const items = await published;
  load.cancel();
  assert.deepEqual(items.map(item => item.measurement_id), ['a', 'b']);
  assert.equal(urls.length, 2);
  assert.match(urls[1], /before_measurement_id=/);
});
