import { validMonth } from './forecast-contract.js';

export const HISTORICAL_CUTOFF_MONTH = '2023-12';

/** Resolve against months advertised by the frame API, including gaps in a series. */
export function resolveValidTimelineMonth(requestedMonth, availableMonths) {
  const sorted = [...new Set((Array.isArray(availableMonths) ? availableMonths : []).filter(validMonth))].sort();
  if (!sorted.length) return { month: null, clamped: false, regimeLabel: 'NO_DATA' };
  let month = requestedMonth;
  const clamped = !sorted.includes(month);
  if (clamped) {
    month = validMonth(month)
      ? sorted.findLast(value => value <= month) || sorted[0]
      : sorted[0];
  }
  const observed = month <= HISTORICAL_CUTOFF_MONTH;
  return {
    month, clamped,
    regimeLabel: observed ? 'HISTORICAL_MRC_OBSERVED' : 'EXTENDED_METEOROLOGICAL_ESTIMATE',
    regimeDescription: observed ? 'Quan trắc lịch sử MRC'
      : 'Chuỗi ước tính khí tượng mở rộng (chưa phải quan trắc MRC)',
  };
}
