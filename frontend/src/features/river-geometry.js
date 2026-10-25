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
