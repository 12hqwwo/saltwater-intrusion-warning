export const labels = {
  UNVERIFIED: 'Nguồn chưa xác minh', SOURCE_REPORTED_METHOD_UNVERIFIED: 'Chưa rõ phương pháp đo',
  REPORTED: 'Tọa độ từ KML', NOT_INDEPENDENTLY_VERIFIED: 'CRS chưa xác nhận',
  INSUFFICIENT_DATA: 'Chưa đủ dữ liệu đánh giá', INVALID_INPUT: 'Hồ sơ chưa hợp lệ',
  REVIEW_REQUIRED: 'Cần chuyên môn xem xét', ADVISORY_AVAILABLE: 'Có kết quả xét quy tắc',
};
export function dateOnly(value) {
  const [year, month, day] = value.slice(0, 10).split('-');
  return `${day}/${month}/${year}`;
}
export function recentDateWindow(site) {
  const [year, month] = site.last_observed_date.split('-').map(Number);
  const start = new Date(Date.UTC(year, month - 24, 1)).toISOString().slice(0, 10);
  return [start > site.first_observed_date ? start : site.first_observed_date, site.last_observed_date];
}
export function filterObservations(rows, from, to) {
  if (from && to && from > to) throw new Error('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.');
  return rows.filter(r => (!from || r.observed_date >= from) && (!to || r.observed_date <= to));
}
export function mapFeatures(collection, showUnconfirmed) {
  return { type: 'FeatureCollection', features: collection.features.flatMap(f => {
    if (f.geometry) return [f];
    const c = f.properties.source_coordinates;
    if (!showUnconfirmed || !Array.isArray(c) || c.length !== 2 || !c.every(Number.isFinite)) return [];
    return [{ ...f, geometry: { type: 'Point', coordinates: c }, properties: { ...f.properties, assumed_crs: true } }];
  }) };
}
export function experimentAssessment(ex) {
  const selected = ex.metrics.find(r => r.model === ex.selected_model);
  const baseline = ex.metrics.find(r => r.model === 'Persistence');
  if (!selected || !baseline) throw new Error('Thiếu chỉ số đối chiếu.');
  return { selected, baseline, beatsBaseline: selected.mae_mS_m < baseline.mae_mS_m };
}
export function safeExternalURL(value) {
  try { const url = new URL(value); return url.protocol === 'https:' ? url.href : null; }
  catch { return null; }
}
