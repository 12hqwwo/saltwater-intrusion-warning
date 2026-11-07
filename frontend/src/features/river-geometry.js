import { segmentEcAt } from '../shared/river-interpolation.js';
// Display geometry only: preserve source vertices and never alter API evidence.
const same = (a, b) => a[0] === b[0] && a[1] === b[1];

export function smoothCoordinates(coordinates, { samplesPerSpan = 12, tension = 0.5 } = {}) {
  if (!Number.isInteger(samplesPerSpan) || samplesPerSpan < 1 || samplesPerSpan > 100 ||
      !Number.isFinite(tension) || tension < 0 || tension > 1) throw new Error('Invalid spline options.');
  if (!Array.isArray(coordinates) || coordinates.some(p => !Array.isArray(p) || p.length < 2 || !p.slice(0, 2).every(Number.isFinite))) {
    throw new Error('Invalid river coordinates.');
  }
  if (coordinates.length < 2) return coordinates.map(p => p.slice());
  const result = [];
  for (let i = 0; i < coordinates.length - 1; i++) {
    const p0 = coordinates[Math.max(0, i - 1)], p1 = coordinates[i];
    const p2 = coordinates[i + 1], p3 = coordinates[Math.min(coordinates.length - 1, i + 2)];
    for (let j = 0; j < samplesPerSpan; j++) {
      if (j === 0) { result.push(p1.slice()); continue; }
      const t = j / samplesPerSpan, t2 = t * t, t3 = t2 * t;
      result.push([0, 1].map(k => (2 * t3 - 3 * t2 + 1) * p1[k] +
        (t3 - 2 * t2 + t) * tension * (p2[k] - p0[k]) +
        (-2 * t3 + 3 * t2) * p2[k] + (t3 - t2) * tension * (p3[k] - p1[k])));
    }
  }
  result.push(coordinates.at(-1).slice());
  return result;
}

export function smoothRiverSegments(features, options = {}) {
  const samples = options.samplesPerSpan ?? 12;
  const original = [], ranges = [];
  for (const feature of features) {
    const points = feature.geometry?.coordinates;
    if (feature.geometry?.type !== 'LineString' || !Array.isArray(points) || points.length < 2) throw new Error('Expected river LineString.');
    if (original.length && !same(original.at(-1), points[0])) throw new Error('River segments must form one connected path.');
    const start = original.length ? original.length - 1 : 0;
    original.push(...points.slice(original.length ? 1 : 0));
    ranges.push([start, original.length - 1]);
  }
  // All segments share tangents from the complete river, including both sides
  // of a five-kilometre seam; smoothing each segment alone would leave kinks.
  const coordinates = smoothCoordinates(original, options);
  const segments = features.map((feature, i) => ({ ...feature,
    properties: { ...feature.properties },
    geometry: { ...feature.geometry, coordinates: coordinates.slice(ranges[i][0] * samples, ranges[i][1] * samples + 1).map(p => p.slice()) },
  }));
  return { coordinates, segments };
}

function geographicDistance(a, b) {
  const radians = Math.PI / 180;
  const h = Math.sin((b[1] - a[1]) * radians / 2) ** 2 +
    Math.cos(a[1] * radians) * Math.cos(b[1] * radians) * Math.sin((b[0] - a[0]) * radians / 2) ** 2;
  return 2 * Math.asin(Math.sqrt(Math.min(1, h)));
}

export function riverRibbon(features, count = 8, thresholds = []) {
  if (!Number.isInteger(count) || count < 1) throw new Error('Invalid ribbon count.');
  return features.flatMap(feature => {
    const coordinates = feature.geometry.coordinates, props = feature.properties;
    const distances = [0];
    for (let i = 1; i < coordinates.length; i++) {
      distances.push(distances[i - 1] + geographicDistance(coordinates[i - 1], coordinates[i]));
    }
    const total = distances.at(-1);
    if (!(total > 0)) return [];
    const pointAt = distance => {
      if (distance === 0) return coordinates[0].slice();
      if (distance === total) return coordinates.at(-1).slice();
      const end = distances.findIndex(value => value >= distance), start = end - 1;
      const fraction = (distance - distances[start]) / (distances[end] - distances[start]);
      return coordinates[start].map((value, axis) => value + (coordinates[end][axis] - value) * fraction);
    };
    const stops = props.ec_stops || [];
    const warningCrossings = [];
    for (const [left, right] of stops.slice(0, -1).map((stop, index) => [stop, stops[index + 1]])) {
      for (const threshold of thresholds) {
        if (!Number.isFinite(threshold) || left.ec_mS_m === right.ec_mS_m) continue;
        const ratio = (threshold - left.ec_mS_m) / (right.ec_mS_m - left.ec_mS_m);
        if (ratio > 0 && ratio < 1) warningCrossings.push(left.fraction + (right.fraction - left.fraction) * ratio);
      }
    }
    const cuts = [...new Set([...Array.from({ length: count + 1 }, (_, i) => i / count),
      ...stops.map(stop => stop.fraction).filter(f => f > 0 && f < 1), ...warningCrossings])].sort((a, b) => a - b);
    // Source vertices are unevenly spaced; both cuts and EC follow traveled distance.
    return cuts.slice(0, -1).map((fraction, index) => {
      const start = total * fraction, end = total * cuts[index + 1];
      const points = [pointAt(start), ...coordinates.filter((_, i) => distances[i] > start && distances[i] < end).map(point => point.slice()), pointAt(end)];
      const ec = segmentEcAt(props, (fraction + cuts[index + 1]) / 2);
      return { ...feature, id: `${feature.id || props.segment_id}_R${index}`,
        properties: { ...props, ec_stops: undefined, start_ec_mS_m: segmentEcAt(props, fraction),
          end_ec_mS_m: segmentEcAt(props, cuts[index + 1]), ec_mS_m: ec, salinity_g_l: ec * .0064 },
        geometry: { ...feature.geometry, coordinates: points } };
    });
  });
}
