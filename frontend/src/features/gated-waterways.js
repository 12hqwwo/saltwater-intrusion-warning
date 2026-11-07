// A mapped branch carries the river-side EC scenario only as far as its gate.
// The inland reach remains unclassified until it has its own observations.
export function ecWarningLevel(ec, thresholds) {
  if (ec == null || thresholds?.open_below_ec_ms_m == null || thresholds?.close_at_or_above_ec_ms_m == null) return 'unknown';
  const value = Number(ec);
  const open = Number(thresholds?.open_below_ec_ms_m);
  const close = Number(thresholds?.close_at_or_above_ec_ms_m);
  if (!Number.isFinite(value) || !Number.isFinite(open) || !Number.isFinite(close) || open < 0 || close <= open) return 'unknown';
  return value < open ? 'safe' : value < close ? 'caution' : 'risk';
}

export function splitGatedWaterways(features = []) {
  if (!Array.isArray(features)) return [];
  return features.flatMap(feature => {
    const coordinates = feature?.geometry?.coordinates;
    const gateIndex = feature?.properties?.gate_path_index;
    if (feature?.geometry?.type !== 'LineString' || !Array.isArray(coordinates) ||
        !Number.isInteger(gateIndex) || gateIndex < 1 || gateIndex >= coordinates.length - 1 ||
        !feature.properties?.gate_code) return [];
    return [
      { ...feature, id: `${feature.id || feature.properties.id}_river_to_gate`, properties: { ...feature.properties, branch_side: 'river_to_gate' }, geometry: { ...feature.geometry, coordinates: coordinates.slice(0, gateIndex + 1) } },
      { ...feature, id: `${feature.id || feature.properties.id}_beyond_gate`, properties: { ...feature.properties, branch_side: 'beyond_gate' }, geometry: { ...feature.geometry, coordinates: coordinates.slice(gateIndex) } },
    ];
  });
}
