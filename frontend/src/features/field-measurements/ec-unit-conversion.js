export const EC_UNIT_FACTORS_TO_MS_PER_M = Object.freeze({ 'µS/cm': .1, 'dS/m': 100, 'mS/cm': 100, 'mS/m': 1 });

export function convertEcToMsPerM(value, unit) {
  const number = Number(value);
  return value !== '' && Number.isFinite(number) && number >= 0 && Object.hasOwn(EC_UNIT_FACTORS_TO_MS_PER_M, unit)
    ? number * EC_UNIT_FACTORS_TO_MS_PER_M[unit] : null;
}
