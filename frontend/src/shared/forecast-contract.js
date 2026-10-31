export const validMonth = value => typeof value === 'string' && /^(?!0000)\d{4}-(0[1-9]|1[0-2])$/.test(value);
export const validEc = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
export function inputMonthFor(target) {
  if (!validMonth(target)) return null;
  const [year, month] = target.split('-').map(Number), index = year * 12 + month - 1 - 2;
  return index >= 12 ? `${String(Math.floor(index / 12)).padStart(4, '0')}-${String(index % 12 + 1).padStart(2, '0')}` : null;
}
export function validPrediction(data, expected = {}) {
  if (!data || typeof data.station !== 'string' || !data.station || typeof data.site_code !== 'string' || !data.site_code ||
      data.unit !== 'mS/m' || !validEc(data.predicted_ec_mS_m) || !validMonth(data.target_month) ||
      data.input_month !== inputMonthFor(data.target_month) || !['ARCHIVE', 'MANUAL'].includes(data.input_mode)) return false;
  for (const key of ['station', 'site_code', 'target_month', 'input_mode']) if (expected[key] !== undefined && data[key] !== expected[key]) return false;
  const units = { rainfall_mm: 'mm', temperature_degC: 'degC', wind_source_units: 'm/s' };
  if (!Array.isArray(data.inputs)) return false;
  return Object.entries(units).every(([name, unit]) => {
    const matches = data.inputs.filter(item => item?.name === name);
    const input = matches[0];
    return matches.length === 1 && input.unit === unit && Number.isFinite(input.value) &&
      (name === 'temperature_degC' || input.value >= 0) &&
      (expected.input_mode !== 'MANUAL' || input.value === expected[name]);
  });
}
