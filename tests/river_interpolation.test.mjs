import test from 'node:test';
import assert from 'node:assert/strict';
import { interpolateStationEc, segmentEcAt, MY_THUAN_RATIO as r, MY_THUAN_KM,
  TWO_STATION_MODE } from '../frontend/src/shared/river-interpolation.js';
import { riverProfileData } from '../frontend/src/features/river-profile.js';

const context = Object.freeze({ tanchauEc: 10, mythuanEc: 100, mythoEc: 20 });
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-8, `${a} != ${b}`);

test('piecewise linear interpolation uses local fractions and keeps the nonmonotonic middle anchor', () => {
  for (const [ratio, ec] of [[0, 10], [r / 2, 55], [r, 100], [(r + 1) / 2, 60], [1, 20]]) {
    near(interpolateStationEc(ratio, context), ec);
  }
  near(interpolateStationEc(r - 1e-12, context), 100);
  near(interpolateStationEc(r + 1e-12, context), 100);
  assert.equal(interpolateStationEc(-1, context), 10);
  assert.equal(interpolateStationEc(2, context), 20);
  assert.equal(interpolateStationEc(r, { tanchauEc: 0, mythuanEc: 0, mythoEc: 0 }), 0);
});

test('missing My Thuan falls back only for explicit historical missing samples', () => {
  const missing = { ...context, mythuanEc: null, targetMonth: '2023-12', interpolationMode: TWO_STATION_MODE };
  assert.equal(interpolateStationEc(0.5, missing), 15);
  near(interpolateStationEc(r, missing), 10 + 10 * r);
  for (const patch of [{ targetMonth: '2024-01' }, { targetMonth: undefined }, { interpolationMode: undefined }, { mythuanEc: '' }]) {
    for (const ratio of [0, r, 1]) assert.throws(() => interpolateStationEc(ratio, { ...missing, ...patch }));
  }
});

test('invalid anchors and positions cannot produce an apparent EC result', () => {
  for (const value of [null, '', true, '12', NaN, Infinity, -1]) {
    for (const key of ['tanchauEc', 'mythuanEc', 'mythoEc']) assert.throws(() => interpolateStationEc(0.5, { ...context, [key]: value }));
  }
  for (const ratio of [null, '', NaN, Infinity]) assert.throws(() => interpolateStationEc(ratio, context));
});

test('segment color and longitudinal profile preserve the exact third-station knot', () => {
  const props = { chainage_start_km: 85, chainage_end_km: 90, chainage_km: 87.5,
    start_ec_mS_m: 10, ec_mS_m: 60, end_ec_mS_m: 20,
    ec_stops: [{ fraction: 0, ec_mS_m: 10 }, { fraction: (MY_THUAN_KM - 85) / 5, ec_mS_m: 100 }, { fraction: 1, ec_mS_m: 20 }] };
  const knot = props.ec_stops[1].fraction;
  assert.equal(segmentEcAt(props, knot), 100);
  near(segmentEcAt(props, knot / 2), 55);
  near(segmentEcAt(props, (1 + knot) / 2), 60);
  const frame = { river_segments: [{ properties: props }] };
  assert.deepEqual(riverProfileData(frame).points.find(([km]) => km === MY_THUAN_KM), [MY_THUAN_KM, 100]);
  near(riverProfileData(frame, 'salinity').points.find(([km]) => km === MY_THUAN_KM)[1], 0.64);
});
