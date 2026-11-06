import assert from 'node:assert/strict';
import test from 'node:test';
import { projectForecastContextForGate as project } from '../frontend/src/features/gate-forecast-context.js';
import { deriveForecastAdvisoryForGate } from '../frontend/src/shared/gate-intake-rules.js';
import { MY_THUAN_KM, MY_THUAN_RATIO } from '../frontend/src/shared/river-interpolation.js';

const forecast = Object.freeze({ sourceModel: 'RF_compact', mythoEc: 20, tanchauEc: 140, mythuanEc: 140 - 120 * MY_THUAN_RATIO, targetMonth: '2026-11' });
test('gate projection uses forecast station anchors and holds MyTho EC downstream', () => {
  for (const [chainage_km, expected] of [[0, 140], [62.5, 80], [125, 20], [175, 20]]) {
    const result = project(forecast, { gate_code: 'A', chainage_km });
    assert.ok(Math.abs(result.projectedGateEc - expected) < 1e-10);
    assert.equal(result.projectedGateId, 'A');
    assert.equal(result.projectionBasis, 'GEOMETRIC_AXIS_INTERPOLATION');
  }
  const upstream = deriveForecastAdvisoryForGate(project(forecast, { gate_code: 'A', chainage_km: 0 }));
  assert.equal(upstream.highByStationP90, false);
  assert.equal(upstream.highByGateRatio, true);
  assert.equal(upstream.effectiveMaxSampleAgeHours, 2);
});

test('projection finds matching GIS gate chainage from original spatial frame', () => {
  const frame = { assumptions: { chainage_anchors_km: [0, 125, 175] }, gates: [{ gate_code: 'A', chainage_km: 62.5 }, { gate_code: 'B', chainage_km: 0 }] };
  assert.ok(Math.abs(project(forecast, { gate_code: 'A' }, frame).projectedGateEc - 80) < 1e-10);
  assert.equal(project(forecast, { gate_code: 'C' }, frame).projectedGateEc, null);
});

test('coordinate projection uses traveled span length, including an intermediate vertex', () => {
  const frame = { river_segments: [{ type: 'Feature', geometry: { type: 'LineString', coordinates: [[105, 10], [105.01, 10], [105.03, 10]] },
    properties: { chainage_start_km: 0, chainage_end_km: 125 } }] };
  const result = project(forecast, { gate_code: 'A', coordinates: [105.015, 10.001] }, frame);
  assert.ok(Math.abs(result.projectedChainageKm - 62.5) < 1e-6);
  assert.ok(Math.abs(result.projectedGateEc - 80) < 1e-6);
  assert.ok(result.projectionDistanceKm > 0.1 && result.projectionDistanceKm < 0.12);
  assert.equal(project(forecast, { geometry: { type: 'Point', coordinates: [105.015, 10] } }, frame).projectionBasis, 'GEOMETRIC_AXIS_INTERPOLATION');
});

test('missing position, malformed axis and invalid EC fall back without reusing a previous gate projection', () => {
  const oldContext = { ...forecast, projectedGateEc: 999, projectionBasis: 'OLD', projectedGateId: 'OLD', projectedChainageKm: 10 };
  for (const gate of [null, {}, { chainage_km: -1 }, { chainage_km: 176 }, { coordinates: [181, 10] }]) {
    const result = project(oldContext, gate);
    assert.equal(result.projectedGateEc, null);
    assert.equal(result.projectionBasis, 'STATION_FALLBACK_NO_PROJECTION');
    assert.equal(result.projectedGateId, undefined);
    assert.equal(result.projectedChainageKm, undefined);
    assert.equal(deriveForecastAdvisoryForGate(result).projectedGateEc, 20);
  }
  for (const tanchauEc of [null, '', false, -1]) assert.equal(project({ ...forecast, tanchauEc }, { chainage_km: 0 }).projectedGateEc, null);
  assert.equal(project(forecast, { coordinates: [105, 10] }, { river_segments: [{ geometry: { type: 'LineString', coordinates: [[105, 10], [105, 10]] }, properties: { chainage_start_km: 0, chainage_end_km: 5 } }] }).projectedGateEc, null);
  assert.equal(project(null, {}), null);
});

test('projection preserves input objects', () => {
  const gate = Object.freeze({ gate_code: 'A', chainage_km: 50 });
  const copy = structuredClone(forecast);
  project(forecast, gate);
  assert.deepEqual(forecast, copy);
});

test('a midstream gate receives the third anchor and activates the tightened sample lifetime', () => {
  const context = { ...forecast, tanchauEc: 10, mythuanEc: 150, mythoEc: 20 };
  const gateContext = project(context, { gate_code: 'MT', chainage_km: MY_THUAN_KM });
  assert.equal(gateContext.projectedGateEc, 150);
  const advisory = deriveForecastAdvisoryForGate(gateContext);
  assert.equal(advisory.highByGateRatio, true);
  assert.equal(advisory.effectiveMaxSampleAgeHours, 2);
  for (const chainage_km of [0, MY_THUAN_KM, 125]) {
    assert.equal(project({ ...context, mythuanEc: null }, { chainage_km }).projectedGateEc, null);
  }
});
