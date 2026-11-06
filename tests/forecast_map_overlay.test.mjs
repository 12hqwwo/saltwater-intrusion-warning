import test from 'node:test';
import assert from 'node:assert/strict';
import { buildForecastOverlayFrame, normalizeForecastContext, createForecastMapBridge,
  activeForecastContext, loadMultivariateForecastContext, DIRECT_FORECAST_MODEL,
} from '../frontend/src/shared/forecast-map-overlay.js';
import { riverRibbon, smoothRiverSegments } from '../frontend/src/features/river-geometry.js';
import { MY_THUAN_RATIO, TWO_STATION_MODE } from '../frontend/src/shared/river-interpolation.js';

const context = { sourceModel: 'RF_compact', targetMonth: '2024-01', mythoEc: 60.42, tanchauEc: 20, mythuanEc: 100 };
function baseFrame(count = 35) {
  return { year_month: '2026-08', simulation_layer: true,
    inputs: { tan_chau_ec_mS_m: 25, my_tho_ec_mS_m: 30 },
    assumptions: { chainage_anchors_km: [0, 125, 175] },
    gates: [{ gate_code: 'G1', simulated_outside_ec_mS_m: 999 }],
    isohaline_boundaries: [{ salinity_g_l: 4 }],
    river_segments: Array.from({ length: count }, (_, index) => ({ type: 'Feature', id: `SEG_${index}`,
      geometry: { type: 'LineString', coordinates: [[105 + index / 100, 10], [105 + (index + 1) / 100, 10]] },
      properties: { chainage_start_km: index * 5, chainage_end_km: (index + 1) * 5,
        chainage_km: index * 5 + 2.5, ec_mS_m: 999, start_ec_mS_m: 999, end_ec_mS_m: 999 },
    })),
  };
}
function freeze(value) {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}

test('35 river segments retain all three anchors including the My Thuan knot in the ribbon', () => {
  const base = freeze(baseFrame()), before = structuredClone(base);
  const overlay = buildForecastOverlayFrame(base, context);
  assert.deepEqual(base, before);
  assert.equal(overlay.river_segments.length, 35);
  assert.equal(overlay.river_segments[0].properties.start_ec_mS_m, 20);
  assert.equal(overlay.river_segments[24].properties.end_ec_mS_m, 60.42);
  assert.equal(overlay.river_segments[34].properties.end_ec_mS_m, 60.42);
  assert.equal(overlay.year_month, '2024-01');
  assert.equal(overlay.overlayMetadata.baseMonth, '2026-08');
  assert.equal(overlay.overlayMetadata.isHighVigilance, true);
  assert.equal(overlay.inputs.my_tho_ec_mS_m, 60.42);
  assert.deepEqual(overlay.gates, []);
  assert.deepEqual(overlay.isohaline_boundaries, []);
  const ribbon = riverRibbon(smoothRiverSegments(overlay.river_segments, { tension: 0 }).segments);
  assert.equal(ribbon.length, 281);
  const knot = overlay.river_segments[17].properties.ec_stops[1];
  assert.ok(Math.abs(knot.ec_mS_m - 100) < 1e-10);
  const touchKnot = ribbon.filter(item => Math.abs(item.properties.start_ec_mS_m - 100) < 1e-10 || Math.abs(item.properties.end_ec_mS_m - 100) < 1e-10);
  assert.equal(touchKnot.length, 2, 'both ribbon pieces meet at the third station exactly');
  assert.equal(overlay.interpolation_mode, 'PIECEWISE_3_STATION');
  assert.ok(ribbon.every(item => Number.isFinite(item.properties.ec_mS_m) && item.properties.ec_mS_m !== 999));
  overlay.river_segments[0].geometry.coordinates[0][0] = 0;
  assert.deepEqual(base, before, 'returned geometry must be independent');
});

test('GeoJSON frames honor explicit axial positions and fall back to ordered segment fractions', () => {
  const base = { type: 'FeatureCollection', features: baseFrame(2).river_segments };
  base.features[0].properties.axial_ratio_start = 0;
  base.features[0].properties.axial_ratio_end = 0.25;
  const result = buildForecastOverlayFrame(base, { ...context, mythoEc: 100, tanchauEc: 0, mythuanEc: 100 * MY_THUAN_RATIO });
  assert.ok(Math.abs(result.features[0].properties.ec_mS_m - 12.5) < 1e-10);
  assert.equal(result.features[1].properties.ec_mS_m, 75);
  assert.equal(result.features[1].properties.ec_end_ms_m, 100);
  assert.equal(result.features[1].properties.salinity_gl_est, 0.48);
});

test('forecast validation rejects malformed months, EC, thresholds, and models while preserving zero', () => {
  assert.equal(buildForecastOverlayFrame(baseFrame(), { ...context, mythoEc: 0, tanchauEc: 0, mythuanEc: 0 }).river_segments[0].properties.ec_mS_m, 0);
  for (const invalid of [-1, NaN, Infinity, null, '', '25', true]) {
    assert.throws(() => buildForecastOverlayFrame(baseFrame(), { ...context, mythoEc: invalid }));
    assert.throws(() => normalizeForecastContext({ ...context, tanchauEc: invalid }));
    assert.throws(() => normalizeForecastContext({ ...context, mythuanEc: invalid }));
    if (invalid !== null) assert.throws(() => normalizeForecastContext({ ...context, p90Threshold: invalid }));
  }
  for (const invalid of [null, {}, { features: [] }, { river_segments: null }]) {
    assert.throws(() => buildForecastOverlayFrame(invalid, context));
  }
  assert.throws(() => normalizeForecastContext({ ...context, targetMonth: '2026-13' }));
  assert.throws(() => normalizeForecastContext({ ...context, sourceModel: 'Persistence' }));
  assert.equal(normalizeForecastContext({ ...context, p90Threshold: 60.6 }).isHighVigilance, false);
});

test('bridge applies complete forecast anchors, publishes context and restores the exact original', () => {
  const base = freeze(baseFrame()), frames = [], events = [], target = new EventTarget();
  target.addEventListener('workspace:active-forecast-context', event => events.push(event.detail));
  const bridge = createForecastMapBridge({ onFrame: frame => frames.push(frame), eventTarget: target });
  bridge.setBaseFrame(base);
  for (const mythoEc of [27.903151156478184, 22.022199245004803]) {
    bridge.apply({ ...context, mythoEc });
    assert.equal(activeForecastContext.mythoEc, mythoEc);
    assert.equal(activeForecastContext.tanchauEc, 20);
    assert.equal(activeForecastContext.mythuanEc, 100);
    assert.equal(activeForecastContext.isHighVigilance, false);
    assert.equal(frames.at(-1).river_segments[24].properties.end_ec_mS_m, mythoEc);
  }
  bridge.setBaseFrame(null);
  assert.equal(activeForecastContext, null);
  assert.equal(frames.at(-1), null);
  bridge.setBaseFrame(base);
  assert.equal(activeForecastContext.mythoEc, 22.022199245004803);
  bridge.clear();
  assert.equal(activeForecastContext, null);
  assert.equal(frames.at(-1), base);
  assert.equal(events.at(-1), null);
});

test('pending overlay uses the arriving baseline and a bad replacement restores the baseline', () => {
  const errors = [], bridge = createForecastMapBridge({ eventTarget: new EventTarget(), onError: e => errors.push(e) });
  bridge.apply({ ...context, mythoEc: 65 });
  const base = baseFrame(); base.inputs.tan_chau_ec_mS_m = 12;
  bridge.setBaseFrame(base);
  assert.equal(activeForecastContext.tanchauEc, 20, 'never borrow timeline station EC');
  assert.equal(activeForecastContext.isHighVigilance, true);
  bridge.apply({ ...context, mythoEc: -1 });
  assert.equal(activeForecastContext, null);
  assert.equal(errors.length, 1);
  assert.equal(bridge.getBaseFrame(), base);
});

function prediction(station, ec, input_mode = 'ARCHIVE') {
  return { station, site_code: { MyTho: 'MRC_VN_019805', MyThuan: 'MRC_VN_019804', TanChau: 'MRC_VN_019803' }[station],
    target_month: '2026-10', input_month: '2026-08', input_mode, unit: 'mS/m', predicted_ec_mS_m: ec,
    inputs: [{ name: 'rainfall_mm', unit: 'mm', value: 10 }, { name: 'temperature_degC', unit: 'degC', value: 25 }, { name: 'wind_source_units', unit: 'm/s', value: 2 }],
  };
}
test('direct form obtains the other two stations for all three stations and either input mode', async () => {
  const values = { MyTho: 80, MyThuan: 45, TanChau: 12 };
  for (const station of Object.keys(values)) for (const mode of ['ARCHIVE', 'MANUAL']) {
    const original = prediction(station, values[station], mode), requests = [];
    const result = await loadMultivariateForecastContext(original, async (path, options) => {
      requests.push({ path, ...options });
      return prediction(options.body.station, values[options.body.station], mode);
    });
    assert.equal(result.sourceModel, DIRECT_FORECAST_MODEL);
    assert.equal(result.mythoEc, 80);
    assert.equal(result.tanchauEc, 12);
    assert.equal(result.mythuanEc, 45);
    assert.equal(requests.length, 2);
    assert.deepEqual(new Set(requests.map(r => r.body.station)), new Set(Object.keys(values).filter(s => s !== station)));
    assert.equal(result.isHighVigilance, true);
    assert.equal(requests[0].path, '/multivariate/predict');
    assert.equal(requests[0].method, 'POST');
    assert.equal(requests[0].body.rainfall_mm, mode === 'MANUAL' ? 10 : undefined);
  }
});

test('only explicit historical missing My Thuan samples allow two-station overlays', () => {
  const missing = { ...context, targetMonth: '2023-01', mythuanEc: null, interpolationMode: TWO_STATION_MODE };
  const frame = buildForecastOverlayFrame(baseFrame(), missing);
  assert.equal(frame.interpolation_mode, TWO_STATION_MODE);
  assert.equal(frame.interpolation_fallback_reason, 'MISSING_HISTORICAL_MYTHUAN_OBSERVATION');
  assert.ok(Math.abs(frame.river_segments[12].properties.ec_mS_m - 40.21) < 1e-10);
  assert.throws(() => normalizeForecastContext({ ...missing, targetMonth: '2024-01' }));
  assert.throws(() => normalizeForecastContext({ ...missing, interpolationMode: undefined }));
});
test('direct form rejects a counterpart for another month or changed manual input', async () => {
  await assert.rejects(loadMultivariateForecastContext(prediction('MyTho', 80), async () => ({ ...prediction('TanChau', 12), target_month: '2026-11' })));
  const changed = prediction('TanChau', 12, 'MANUAL'); changed.inputs[0].value = 11;
  await assert.rejects(loadMultivariateForecastContext(prediction('MyTho', 80, 'MANUAL'), async () => changed));
});
