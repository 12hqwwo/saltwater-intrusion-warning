import { createRequestGate, localDate } from '../api.js';
import { workspaceAPI } from './workspace-api.js';

const validDate = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  Number.isFinite(Date.parse(`${value}T00:00:00Z`)) && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;

export function validateObservations(data, siteCode) {
  if (data?.site_code !== siteCode || data.unit !== 'mS/m' || !Array.isArray(data.items) ||
      data.total !== data.items.length || typeof data.source !== 'string' || !data.source) throw new Error('Số đo trả về không khớp trạm, nguồn hoặc đơn vị EC.');
  for (const row of data.items) {
    if (row?.site_code !== siteCode || row.unit !== 'mS/m' || !validDate(row.observed_date) ||
        !Number.isFinite(row.ec_mS_m) || row.ec_mS_m < 0 || typeof row.source_id !== 'string' || !row.source_id ||
        typeof row.source_locator !== 'string' || !row.source_locator || !['DATE_ONLY', 'SOURCE_TIMESTAMP'].includes(row.time_precision) ||
        (row.observed_or_estimated != null && !['O', 'E'].includes(row.observed_or_estimated)) ||
        (row.time_precision === 'DATE_ONLY' && row.observed_at != null)) {
      throw new Error('Mẫu EC có trạm, ngày, loại số đo, đơn vị hoặc nguồn không hợp lệ.');
    }
    if (row.time_precision === 'SOURCE_TIMESTAMP' && (typeof row.observed_at !== 'string' ||
        !/(Z|[+-]\d{2}:\d{2})$/.test(row.observed_at) || !Number.isFinite(Date.parse(row.observed_at)) ||
        localDate(row.observed_at) !== row.observed_date)) throw new Error('Thời gian nguồn không khớp ngày của mẫu theo UTC+7.');
  }
  return data;
}

export function createObservationLoader({ api = workspaceAPI, onResult, onError } = {}) {
  const requests = createRequestGate();
  return {
    cancel() { requests.next(); },
    async load(siteCode) {
      const req = requests.next();
      try {
        const data = await api(`/stations/${encodeURIComponent(siteCode)}/observations`, req);
        if (!req.isCurrent()) return null;
        validateObservations(data, siteCode);
        onResult?.(data);
        return data;
      } catch (error) {
        if (req.isCurrent() && error.name !== 'AbortError') onError?.(error);
        return null;
      }
    },
  };
}
