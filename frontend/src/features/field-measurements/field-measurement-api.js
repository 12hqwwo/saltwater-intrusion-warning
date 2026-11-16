import { requestJSON } from '../../api.js';

export const submitFieldMeasurement = payload => requestJSON('/field-measurements', { method: 'POST', body: payload });
export const listPendingFieldMeasurements = () => requestJSON('/field-measurements?status=PENDING');
export const listMyFieldMeasurements = () => requestJSON('/field-measurements/mine');
export const reviewFieldMeasurement = (id, decision, note) => requestJSON(`/field-measurements/${encodeURIComponent(id)}/review`, { method: 'POST', body: { decision, note } });
export const listApprovedFieldMeasurements = () => requestJSON('/field-measurements?status=APPROVED');
