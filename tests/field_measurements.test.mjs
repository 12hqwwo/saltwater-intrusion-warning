import assert from 'node:assert/strict';
import test from 'node:test';
import { convertedEc, approvedMapItems } from '../frontend/src/features/field-measurements.js';
import { fieldMeasurementFeatureCollection } from '../frontend/src/features/observations-map.js';

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
});
