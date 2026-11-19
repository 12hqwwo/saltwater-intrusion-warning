import { requestJSON } from '../../api.js';

export const submitFieldMeasurement = payload => requestJSON('/field-measurements', { method: 'POST', body: payload });
const pagePath = (path, cursor) => {
  const params = new URLSearchParams({ limit: '200' });
  if (cursor) {
    params.set('before_submitted_at', cursor.before_submitted_at);
    params.set('before_measurement_id', cursor.before_measurement_id);
  }
  return `${path}${path.includes('?') ? '&' : '?'}${params}`;
};
export const listPendingFieldMeasurements = cursor => requestJSON(pagePath('/field-measurements?status=PENDING', cursor));
export const listMyFieldMeasurements = cursor => requestJSON(pagePath('/field-measurements/mine', cursor));
export const reviewFieldMeasurement = (id, decision, note) => requestJSON(`/field-measurements/${encodeURIComponent(id)}/review`, { method: 'POST', body: { decision, note } });
export const listApprovedFieldMeasurements = cursor => requestJSON(pagePath('/field-measurements?status=APPROVED', cursor));
