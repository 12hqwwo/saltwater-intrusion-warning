import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { ecWarningLevel, splitGatedWaterways } from '../frontend/src/features/gated-waterways.js';

const thresholds = { open_below_ec_ms_m: 100, close_at_or_above_ec_ms_m: 150 };

test('EC warning levels use only the selected EC thresholds', () => {
  assert.equal(ecWarningLevel(0, thresholds), 'safe');
  assert.equal(ecWarningLevel(99.999, thresholds), 'safe');
  assert.equal(ecWarningLevel(100, thresholds), 'caution');
  assert.equal(ecWarningLevel(149.999, thresholds), 'caution');
  assert.equal(ecWarningLevel(150, thresholds), 'risk');
  assert.equal(ecWarningLevel(null, thresholds), 'unknown');
  assert.equal(ecWarningLevel(40, null), 'unknown');
});

test('every mapped branch is split exactly at its catalogued gate', () => {
  const corridor = JSON.parse(readFileSync(new URL('../data/biengioi/tien_river_corridor.geojson', import.meta.url), 'utf8'));
  const branches = corridor.features.filter(feature => feature.properties?.gate_code);
  const displayed = splitGatedWaterways(branches);
  assert.equal(branches.length, 10);
  assert.equal(displayed.length, 20);
  assert.equal(new Set(displayed.map(feature => feature.id)).size, displayed.length);
  for (let index = 0; index < branches.length; index += 1) {
    const original = branches[index], riverSide = displayed[index * 2], inlandSide = displayed[index * 2 + 1];
    const gate = original.geometry.coordinates[original.properties.gate_path_index];
    assert.equal(riverSide.properties.branch_side, 'river_to_gate');
    assert.equal(inlandSide.properties.branch_side, 'beyond_gate');
    assert.deepEqual(riverSide.geometry.coordinates.at(-1), gate);
    assert.deepEqual(inlandSide.geometry.coordinates[0], gate);
    assert.deepEqual([...riverSide.geometry.coordinates, ...inlandSide.geometry.coordinates.slice(1)], original.geometry.coordinates);
  }
});
