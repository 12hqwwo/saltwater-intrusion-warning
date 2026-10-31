const radians = degrees => degrees * Math.PI / 180;

export function validCoordinate(value) {
  return Array.isArray(value) && value.length === 2 && value.every(Number.isFinite) &&
    Math.abs(value[0]) <= 180 && Math.abs(value[1]) <= 90;
}

export function haversineKm(a, b) {
  if (!validCoordinate(a) || !validCoordinate(b)) return Infinity;
  const dLat = radians(b[1] - a[1]), dLon = radians(b[0] - a[0]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(radians(a[1])) * Math.cos(radians(b[1])) * Math.sin(dLon / 2) ** 2;
  return 6371.0088 * 2 * Math.asin(Math.sqrt(Math.min(1, h)));
}

// Project onto every span, not just the vertices: long spans must remain selectable.
// A local metric projection is adequate for this regional corridor; final distances
// use the great-circle distance and describe proximity, not hydraulic connectivity.
export function nearestRiverPoint(point, segments = []) {
  if (!validCoordinate(point) || !Array.isArray(segments)) return null;
  const xScale = Math.cos(radians(point[1]));
  let nearest = null;
  for (const segment of segments) {
    if (segment?.geometry?.type !== 'LineString') continue;
    const coordinates = segment.geometry.coordinates || [];
    if (!Array.isArray(coordinates)) continue;
    for (let i = 1; i < coordinates.length; i += 1) {
      const a = coordinates[i - 1], b = coordinates[i];
      if (!validCoordinate(a) || !validCoordinate(b)) continue;
      const ax = (a[0] - point[0]) * xScale, ay = a[1] - point[1];
      const dx = (b[0] - a[0]) * xScale, dy = b[1] - a[1];
      const lengthSquared = dx * dx + dy * dy;
      const fraction = lengthSquared ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / lengthSquared)) : 0;
      const coordinate = [a[0] + fraction * (b[0] - a[0]), a[1] + fraction * (b[1] - a[1])];
      const distanceKm = haversineKm(point, coordinate);
      if (!nearest || distanceKm < nearest.distanceKm) nearest = { segment, coordinate, distanceKm };
    }
  }
  return nearest;
}

function nearestPoint(point, items, getCoordinate) {
  let nearest = null;
  for (const item of Array.isArray(items) ? items : []) {
    if (!item) continue;
    const coordinate = getCoordinate(item);
    if (!validCoordinate(coordinate)) continue;
    const distanceKm = haversineKm(point, coordinate);
    if (!nearest || distanceKm < nearest.distanceKm) nearest = { item, coordinate, distanceKm };
  }
  return nearest;
}

export function inspectWaterPoint(coordinate, frame, stationFeatures = []) {
  if (!validCoordinate(coordinate) || frame?.simulation_layer !== true) return null;
  const river = nearestRiverPoint(coordinate, frame.river_segments);
  if (!river) return null;
  return {
    coordinate: [...coordinate], yearMonth: frame.year_month, river,
    gate: nearestPoint(coordinate, frame.gates || [], item => item.coordinates || item.geometry?.coordinates),
    station: nearestPoint(coordinate, Array.isArray(stationFeatures) ? stationFeatures.filter(item => item?.geometry?.type === 'Point') : [], item => item.geometry.coordinates),
  };
}
