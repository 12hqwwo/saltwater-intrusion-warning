import { validEc } from './forecast-contract.js';

export const MY_THUAN_RATIO = 0.68174084;
export const MY_THUAN_KM = 85.217605;
export const THREE_STATION_MODE = 'PIECEWISE_3_STATION';
export const TWO_STATION_MODE = 'TWO_STATION_FALLBACK_MISSING_MYTHUAN';

export function interpolateStationEc(ratio, context) {
  if (!Number.isFinite(ratio) || !validEc(context.tanchauEc) || !validEc(context.mythoEc)) throw new Error('Điểm neo EC không hợp lệ.');
  const r = Math.max(0, Math.min(1, ratio));
  if (!validEc(context.mythuanEc)) {
    if (context.interpolationMode !== TWO_STATION_MODE || context.mythuanEc !== null ||
        !/^\d{4}-(0[1-9]|1[0-2])$/.test(context.targetMonth || '') || context.targetMonth >= '2024-01') throw new Error('Thiếu điểm neo dự báo Mỹ Thuận.');
    return context.tanchauEc + (context.mythoEc - context.tanchauEc) * r;
  }
  if (r === 0) return context.tanchauEc;
  if (r === 1) return context.mythoEc;
  if (r === MY_THUAN_RATIO) return context.mythuanEc;
  if (r <= MY_THUAN_RATIO) return context.tanchauEc + (context.mythuanEc - context.tanchauEc) * (r / MY_THUAN_RATIO);
  return context.mythuanEc + (context.mythoEc - context.mythuanEc) * ((r - MY_THUAN_RATIO) / (1 - MY_THUAN_RATIO));
}

export function segmentEcAt(properties, fraction) {
  const stops = properties.ec_stops;
  if (Array.isArray(stops) && stops.length >= 2) {
    const right = Math.max(1, stops.findIndex(stop => stop.fraction >= fraction));
    const a = stops[right - 1], b = stops[right];
    const u = Math.max(0, Math.min(1, (fraction - a.fraction) / (b.fraction - a.fraction || 1)));
    return a.ec_mS_m + (b.ec_mS_m - a.ec_mS_m) * u;
  }
  const a = properties.start_ec_mS_m ?? properties.ec_mS_m, b = properties.end_ec_mS_m ?? properties.ec_mS_m;
  return a + (b - a) * fraction;
}
