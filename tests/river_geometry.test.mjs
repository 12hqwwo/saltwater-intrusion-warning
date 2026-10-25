import assert from 'node:assert/strict';
import test from 'node:test';
import { smoothCoordinates, smoothRiverSegments } from '../frontend/src/features/river-geometry.js';

const feature = (coordinates, id) => ({ type: 'Feature', id, geometry: { type: 'LineString', coordinates }, properties: { segment_id: id, simulation_layer: true } });

test('complete 35-segment spline retains all original anchors and exact shared endpoints without mutation', () => {
  const anchors = Array.from({ length: 36 }, (_, i) => [105 + i / 20, 10 + Math.sin(i / 4) / 5]);
  anchors[25] = [106.36, 10.35];
  const source = anchors.slice(1).map((point, i) => feature([anchors[i], point], `segment-${i}`));
  const before = structuredClone(source);
  const result = smoothRiverSegments(source);
  assert.equal(result.segments.length, 35);
  assert.equal(result.coordinates.length, 35 * 12 + 1);
  assert.deepEqual(result.coordinates[0], anchors[0]);
  assert.deepEqual(result.coordinates.at(-1), anchors.at(-1));
  for (let i = 0; i < 35; i++) {
    const points = result.segments[i].geometry.coordinates;
    assert.deepEqual(points[0], anchors[i]);
    assert.deepEqual(points.at(-1), anchors[i + 1]);
    assert.deepEqual(result.segments[i].properties, source[i].properties);
    if (i) assert.deepEqual(result.segments[i - 1].geometry.coordinates.at(-1), points[0]);
  }
  assert.deepEqual(result.coordinates[25 * 12], [106.36, 10.35]);
  result.segments[0].geometry.coordinates[0][0] = 999;
  assert.deepEqual(source, before);
});

test('shared seam tangents use neighbors across segments rather than two-point interpolation', () => {
  const source = [feature([[0, 0], [1, 1]], 'a'), feature([[1, 1], [2, 0]], 'b')];
  const { segments } = smoothRiverSegments(source, { samplesPerSpan: 100 });
  const left = segments[0].geometry.coordinates, right = segments[1].geometry.coordinates;
  assert.ok(left[50][1] > 0.5, 'neighbor bends the first span');
  const incoming = [left.at(-1)[0] - left.at(-2)[0], left.at(-1)[1] - left.at(-2)[1]];
  const outgoing = [right[1][0] - right[0][0], right[1][1] - right[0][1]];
  assert.ok(Math.abs(incoming[1] / incoming[0]) < 0.03);
  assert.ok(Math.abs(outgoing[1] / outgoing[0]) < 0.03);
});

test('intermediate geographic anchors survive smoothing and canal output is separate', () => {
  const points = [[105, 10], [105.1, 10.3], [105.3, 10.2], [105.6, 10.4]];
  const { coordinates, segments } = smoothRiverSegments([feature(points, 'river')]);
  for (const point of points) assert.ok(coordinates.some(candidate => candidate[0] === point[0] && candidate[1] === point[1]));
  assert.deepEqual(segments[0].geometry.coordinates, smoothCoordinates(points));
  assert.deepEqual(smoothCoordinates([]), []);
  assert.deepEqual(smoothCoordinates([[1, 2]]), [[1, 2]]);
  assert.throws(() => smoothRiverSegments([feature([[0, 0], [1, 1]]), feature([[2, 2], [3, 3]])]), /connected/);
  assert.throws(() => smoothCoordinates([[NaN, 1], [2, 3]]), /Invalid/);
});
