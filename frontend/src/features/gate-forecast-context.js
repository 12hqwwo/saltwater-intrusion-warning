import { gateMeasurementNumber } from '../shared/gate-intake-rules.js';
import { nearestRiverPoint, haversineKm, validCoordinate } from './point-inspection.js';
import { interpolateStationEc } from '../shared/river-interpolation.js';

/** Project onto the same 0/125 km station anchors as the phase 1 overlay. */
export function projectForecastContextForGate(context, gate, baseFrame) {
  if (!context || typeof context !== 'object') return null;
  const { projectedGateEc: _oldEc, projectionBasis: _oldBasis, projectedGateId: _oldId,
    projectedChainageKm: _oldChainage, projectionDistanceKm: _oldDistance, ...result } = context;
  let chainage = gateMeasurementNumber(gate?.chainage_km), distanceKm = null;
  const frameGate = (Array.isArray(baseFrame?.gates) ? baseFrame.gates : []).find(item => item.gate_code === gate?.gate_code);
  if (chainage === null) chainage = gateMeasurementNumber(frameGate?.chainage_km);
  const coordinate = gate?.coordinates || gate?.geometry?.coordinates;
  if (chainage === null && validCoordinate(coordinate)) {
    const nearest = nearestRiverPoint(coordinate, baseFrame?.river_segments || []);
    const props = nearest?.segment?.properties;
    if (nearest && Number.isFinite(props?.chainage_start_km) && Number.isFinite(props?.chainage_end_km)) {
      const coords = nearest.segment.geometry.coordinates;
      const lengths = coords.slice(1).map((point, i) => haversineKm(coords[i], point));
      const total = lengths.reduce((sum, value) => sum + value, 0);
      const traveled = lengths.slice(0, nearest.spanIndex).reduce((sum, value) => sum + value, 0) + lengths[nearest.spanIndex] * nearest.spanFraction;
      if (total > 0) chainage = props.chainage_start_km + (props.chainage_end_km - props.chainage_start_km) * traveled / total;
      distanceKm = nearest.distanceKm;
    }
  }
  const mytho = gateMeasurementNumber(context.mythoEc), tanchau = gateMeasurementNumber(context.tanchauEc);
  const downstreamKm = baseFrame?.assumptions?.chainage_anchors_km?.[1] ?? 125;
  if (chainage !== null && chainage >= 0 && chainage <= 175 && Number.isFinite(downstreamKm) && downstreamKm > 0 &&
      mytho !== null && mytho >= 0 && tanchau !== null && tanchau >= 0) {
    const ratio = Math.max(0, Math.min(1, chainage / downstreamKm));
    let projectedGateEc;
    try { projectedGateEc = interpolateStationEc(ratio, context); }
    catch { return { ...result, projectedGateEc: null, projectionBasis: 'STATION_FALLBACK_NO_PROJECTION' }; }
    return { ...result, projectedGateEc,
      projectionBasis: 'GEOMETRIC_AXIS_INTERPOLATION', projectedGateId: gate?.gate_code || null,
      projectedChainageKm: chainage, projectionDistanceKm: distanceKm };
  }
  return { ...result, projectedGateEc: null, projectionBasis: 'STATION_FALLBACK_NO_PROJECTION' };
}
