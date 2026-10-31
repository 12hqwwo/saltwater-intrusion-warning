import test from 'node:test';
import assert from 'node:assert/strict';
import { inspectWaterPoint, nearestRiverPoint, validCoordinate, haversineKm } from '../frontend/src/features/point-inspection.js';

const segment = (coordinates, ec = 0) => ({ type: 'Feature', properties: { ec_mS_m: ec }, geometry: { type: 'LineString', coordinates } });
const frame = () => ({ simulation_layer: true, year_month: '2024-04', river_segments: [segment([[105, 10], [107, 10]])] });

test('nearest river projects to span interior rather than closest vertex', () => {
  const result = nearestRiverPoint([106, 10.1], frame().river_segments);
  assert.deepEqual(result.coordinate, [106, 10]);
  assert.ok(result.distanceKm > 11 && result.distanceKm < 12);
  assert.ok(result.distanceKm < haversineKm([106, 10.1], [105, 10]) / 5);
});

test('invalid coordinates and broken spans cannot become a nearest river', () => {
  for (const value of [null, [105], ['105', 10], [181, 10], [105, 91], [NaN, 10]]) {
    assert.equal(validCoordinate(value), false);
    assert.equal(nearestRiverPoint(value, frame().river_segments), null);
  }
  const broken = [segment([[105, 10], null, [106, 10]]), segment([[Infinity, 10], [106, 10]])];
  assert.equal(nearestRiverPoint([106, 10], broken), null);
  assert.equal(haversineKm(null, [106, 10]), Infinity);
});

test('inspection preserves zero EC and handles absent nearby gates and stations', () => {
  const result = inspectWaterPoint([106, 10.1], frame());
  assert.equal(result.river.segment.properties.ec_mS_m, 0);
  assert.equal(result.gate, null);
  assert.equal(result.station, null);
  assert.equal(result.yearMonth, '2024-04');
});

test('inspection requires explicit simulation flag and usable river geometry', () => {
  for (const value of [null, {}, { ...frame(), simulation_layer: false }, { ...frame(), simulation_layer: 'true' }, { ...frame(), river_segments: [] }, { ...frame(), river_segments: null }, { ...frame(), river_segments: [null] }]) {
    assert.equal(inspectWaterPoint([106, 10.1], value), null);
  }
  assert.equal(inspectWaterPoint([106, 10.1], { ...frame(), gates: [null] }, [null]).gate, null);
});

test('nearest station retains unconfirmed source metadata and inputs are not mutated', () => {
  const inputFrame = frame();
  inputFrame.gates = [{ gate_code: 'bad', coordinates: [NaN, 10] }, { gate_code: 'G1', coordinates: [106, 10.2] }];
  const stations = [{ type: 'Feature', properties: { site_code: 'RIA2', assumed_crs: true, source_coordinates: [106, 10.15], latest_ec_mS_m: 0 }, geometry: { type: 'Point', coordinates: [106, 10.15] } }];
  const coordinate = [106, 10.1], beforeFrame = structuredClone(inputFrame), beforeStations = structuredClone(stations);
  const result = inspectWaterPoint(coordinate, inputFrame, stations);
  assert.equal(result.station.item.properties.assumed_crs, true);
  assert.deepEqual(result.station.item.properties.source_coordinates, [106, 10.15]);
  assert.equal(result.gate.item.gate_code, 'G1');
  assert.deepEqual(inputFrame, beforeFrame);
  assert.deepEqual(stations, beforeStations);
  result.coordinate[0] = 0;
  assert.deepEqual(coordinate, [106, 10.1]);
});
