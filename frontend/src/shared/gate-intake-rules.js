/**
 * @typedef {Object} RuleProfile
 * @property {string} ruleId
 * @property {string} ruleVersion
 * @property {string} ruleName
 * @property {string} ruleNatureNotice
 * @property {number} maxExteriorEcMsM
 * @property {number} maxInteriorEcMsM
 * @property {number} minPositiveHeadDiffM
 * @property {true} requireSameDatum
 * @property {boolean} requireMechanicalReady
 * @property {number} maxSampleAgeHoursNormal
 * @property {number} maxSampleAgeHoursHighVigilance
 * @property {number} p90ReferenceEcMsM
 */
/** @type {Readonly<RuleProfile>} */
export const DEFAULT_GATE_RULE_PROFILE = Object.freeze({
  ruleId: 'MYTHO_TIEN_RIVER_INTAKE_SCREENING',
  ruleVersion: 'TECH_SCREENING_RULE_V1.0',
  ruleName: 'Kiểm tra kỹ thuật điều kiện xem xét lấy nước sông Tiền',
  ruleNatureNotice: 'Quy tắc kỹ thuật cấu hình để kiểm tra nhất quán trên WebGIS (không thay thế quy trình vận hành pháp lý của đơn vị quản lý công trình)',
  maxExteriorEcMsM: 156.25,
  maxInteriorEcMsM: 125,
  minPositiveHeadDiffM: 0.05,
  requireSameDatum: true,
  requireMechanicalReady: true,
  maxSampleAgeHoursNormal: 6,
  maxSampleAgeHoursHighVigilance: 2,
  p90ReferenceEcMsM: 60.42,
});

export const GATE_INTAKE_STATUS_TITLES = Object.freeze({
  ELIGIBLE_FOR_REVIEW: 'Đề nghị xem xét lấy nước',
  NOT_SUITABLE: 'Chưa phù hợp để lấy nước',
  INSUFFICIENT_OR_EXPIRED_DATA: 'Cần bổ sung hoặc đo lại',
});

// Accept decimal form input, but never coerce null, booleans, arrays or whitespace to zero.
export function gateMeasurementNumber(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value !== 'string' || !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value.trim())) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
const nonnegative = value => { const number = gateMeasurementNumber(value); return number !== null && number >= 0 ? number : null; };
const text = value => typeof value === 'string' ? value.trim() : '';

/** Validate actual ISO calendar dates with an explicit zone, independent of the host timezone. */
export function gateTimestampMs(value) {
  if (typeof value !== 'string') return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!match) return null;
  const [year, month, day, hour, minute, second] = match.slice(1, 7).map(value => Number(value ?? 0));
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > days[month - 1] || hour > 23 || minute > 59 || second > 59) return null;
  if (match[8] !== 'Z') {
    const [zoneHour, zoneMinute] = match[8].slice(1).split(':').map(Number);
    if (zoneHour > 14 || zoneMinute > 59 || (zoneHour === 14 && zoneMinute !== 0)) return null;
  }
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function validateGateRuleProfile(profile = DEFAULT_GATE_RULE_PROFILE) {
  if (!profile || typeof profile !== 'object' || Array.isArray(profile)) throw new Error('RuleProfile phải là cấu hình quy tắc hợp lệ.');
  for (const key of ['ruleId', 'ruleVersion', 'ruleName', 'ruleNatureNotice']) {
    if (!text(profile[key])) throw new Error(`RuleProfile thiếu ${key}.`);
  }
  for (const key of ['maxExteriorEcMsM', 'maxInteriorEcMsM', 'minPositiveHeadDiffM', 'maxSampleAgeHoursNormal', 'maxSampleAgeHoursHighVigilance', 'p90ReferenceEcMsM']) {
    if (typeof profile[key] !== 'number' || !Number.isFinite(profile[key]) || profile[key] < 0) throw new Error(`Ngưỡng ${key} phải là số hữu hạn không âm.`);
  }
  if (profile.minPositiveHeadDiffM <= 0 || profile.maxSampleAgeHoursNormal <= 0 || profile.maxSampleAgeHoursHighVigilance <= 0 ||
      profile.maxSampleAgeHoursHighVigilance > profile.maxSampleAgeHoursNormal) throw new Error('Chênh mực nước và thời hạn mẫu phải dương; thời hạn cảnh giác cao không được dài hơn bình thường.');
  if (profile.requireSameDatum !== true) throw new Error('RuleProfile bắt buộc xác nhận cùng hệ cao độ.');
  if (typeof profile.requireMechanicalReady !== 'boolean') throw new Error('requireMechanicalReady phải là giá trị boolean.');
  return profile;
}

export function deriveForecastAdvisoryForGate(forecastContext = {}, ruleProfile = DEFAULT_GATE_RULE_PROFILE) {
  validateGateRuleProfile(ruleProfile);
  const stationForecastEc = nonnegative(forecastContext?.mythoEc);
  const explicitProjection = nonnegative(forecastContext?.projectedGateEc);
  const projectedGateEc = explicitProjection ?? stationForecastEc;
  const p90 = nonnegative(forecastContext?.p90Threshold) ?? ruleProfile.p90ReferenceEcMsM;
  const highByStationP90 = stationForecastEc !== null && stationForecastEc >= p90;
  const gateRatioThresholdEcMsM = 0.8 * ruleProfile.maxExteriorEcMsM;
  const highByGateRatio = projectedGateEc !== null && projectedGateEc >= gateRatioThresholdEcMsM;
  const highByContext = forecastContext?.isHighVigilance === true;
  const isHighVigilance = highByContext || highByStationP90 || highByGateRatio;
  const hasForecastContext = stationForecastEc !== null || explicitProjection !== null || highByContext;
  const effectiveMaxSampleAgeHours = isHighVigilance ? ruleProfile.maxSampleAgeHoursHighVigilance : ruleProfile.maxSampleAgeHoursNormal;
  const reasons = [highByContext && 'CONTEXT_HIGH_VIGILANCE', highByStationP90 && 'STATION_AT_OR_ABOVE_P90', highByGateRatio && 'GATE_AT_OR_ABOVE_80_PERCENT'].filter(Boolean);
  return {
    hasForecastContext, sourceModel: text(forecastContext?.sourceModel) || 'CHƯA_CHỌN_MÔ_HÌNH',
    targetMonth: typeof forecastContext?.targetMonth === 'string' && /^(?!0000)\d{4}-(0[1-9]|1[0-2])$/.test(forecastContext.targetMonth) ? forecastContext.targetMonth : null,
    stationForecastEc, tanchauEc: nonnegative(forecastContext?.tanchauEc), mythuanEc: nonnegative(forecastContext?.mythuanEc), projectedGateEc,
    interpolationMode: forecastContext?.interpolationMode || null,
    tanchauBasis: text(forecastContext?.tanchauBasis) || null,
    projectionBasis: explicitProjection !== null ? text(forecastContext?.projectionBasis) || 'PROVIDED_GATE_PROJECTION'
      : stationForecastEc !== null ? 'STATION_FALLBACK_NO_PROJECTION' : 'UNAVAILABLE',
    p90Threshold: p90, gateRatioThresholdEcMsM, highByStationP90, highByGateRatio, highByContext,
    vigilanceLevel: isHighVigilance ? 'HIGH_VIGILANCE' : 'NORMAL', isHighVigilance, reasons,
    effectiveMaxSampleAgeHours,
    advisoryMessage: isHighVigilance
      ? `Ngữ cảnh dự báo cảnh báo mặn cao: thời hạn mẫu đo tại cống rút xuống ${effectiveMaxSampleAgeHours} giờ.`
      : hasForecastContext ? `Ngữ cảnh dự báo chưa kích hoạt cảnh giác cao: thời hạn mẫu đo ${effectiveMaxSampleAgeHours} giờ.`
        : `Chưa có ngữ cảnh dự báo đa biến; áp dụng thời hạn mẫu đo mặc định ${effectiveMaxSampleAgeHours} giờ.`,
  };
}

/** Pure evaluation: time is supplied by the caller; forecast EC never replaces a gate measurement. */
export function evaluateGateIntakeCondition(input = {}, ruleProfile = DEFAULT_GATE_RULE_PROFILE, forecastContext = {}, evaluationTimeIso) {
  const evalTimeMs = gateTimestampMs(evaluationTimeIso);
  if (evalTimeMs === null) throw new Error('Thời điểm đánh giá (evaluationTimeIso) phải là ISO hợp lệ có múi giờ.');
  const advisory = deriveForecastAdvisoryForGate(forecastContext, ruleProfile);
  const checks = [];
  const add = (id, label, status, observedValue, thresholdValue, explanation) => checks.push({ id, label, status, observedValue, thresholdValue, explanation });
  const measuredAtMs = gateTimestampMs(input?.measuredAtIso);
  let sampleAgeHours = null, sampleExpiresAtIso = null;
  const sampleThreshold = `≤ ${advisory.effectiveMaxSampleAgeHours} giờ`;
  if (measuredAtMs === null || measuredAtMs > evalTimeMs) {
    add('SAMPLE_FRESHNESS', 'Thời điểm và độ mới của mẫu đo', 'MISSING_OR_EXPIRED', input?.measuredAtIso ?? null, sampleThreshold,
      measuredAtMs === null ? 'Thiếu thời điểm đo hợp lệ có múi giờ tại cống.' : 'Thời điểm đo ở tương lai so với thời điểm đánh giá.');
  } else {
    sampleAgeHours = (evalTimeMs - measuredAtMs) / 3_600_000;
    const expiry = measuredAtMs + advisory.effectiveMaxSampleAgeHours * 3_600_000;
    const fresh = sampleAgeHours <= advisory.effectiveMaxSampleAgeHours;
    if (!Number.isFinite(expiry) || Math.abs(expiry) > 8.64e15) throw new Error('Thời hạn mẫu đo vượt phạm vi thời gian hợp lệ.');
    sampleExpiresAtIso = new Date(expiry).toISOString();
    add('SAMPLE_FRESHNESS', 'Thời điểm và độ mới của mẫu đo', fresh ? 'PASSED' : 'MISSING_OR_EXPIRED', sampleAgeHours, advisory.effectiveMaxSampleAgeHours,
      fresh ? `Mẫu còn hiệu lực, tuổi mẫu ${sampleAgeHours.toFixed(2)} giờ.` : `Mẫu đã quá hạn: ${sampleAgeHours.toFixed(2)} giờ > ${advisory.effectiveMaxSampleAgeHours} giờ; cần đo lại.`);
  }
  for (const [id, field, label, threshold] of [
    ['EXTERIOR_EC', 'exteriorEcMsM', 'EC phía ngoài sông sát cống', ruleProfile.maxExteriorEcMsM],
    ['INTERIOR_EC', 'interiorEcMsM', 'EC phía trong đồng', ruleProfile.maxInteriorEcMsM],
  ]) {
    const value = nonnegative(input?.[field]);
    const passed = value !== null && value <= threshold;
    add(id, label, value === null ? 'MISSING_OR_EXPIRED' : passed ? 'PASSED' : 'FAILED', value, threshold,
      value === null ? 'Thiếu số đo EC hữu hạn, không âm tại cống.' : passed ? `EC ${value} mS/m đạt ngưỡng ≤ ${threshold} mS/m.` : `EC ${value} mS/m vượt ngưỡng ${threshold} mS/m.`);
  }
  const exteriorStage = gateMeasurementNumber(input?.exteriorStageM), interiorStage = gateMeasurementNumber(input?.interiorStageM);
  const sameDatum = input?.sameElevationDatum === true;
  add('ELEVATION_DATUM', 'Xác nhận cùng hệ quy chiếu cao độ', sameDatum ? 'PASSED' : 'MISSING_OR_EXPIRED', sameDatum, true,
    sameDatum ? 'Người cung cấp đã xác nhận hai mực nước cùng hệ cao độ.' : 'Chưa xác nhận cùng hệ cao độ; không tính chênh lệch cột nước.');
  const headDiffM = sameDatum && exteriorStage !== null && interiorStage !== null ? exteriorStage - interiorStage : null;
  const headAvailable = headDiffM !== null && Number.isFinite(headDiffM);
  // Tolerance only absorbs subtraction roundoff (e.g. 1.05 - 1); never round readings before comparing.
  const headTolerance = Math.min(1e-10, ruleProfile.minPositiveHeadDiffM * 1e-10,
    4 * Number.EPSILON * Math.max(1, Math.abs(exteriorStage ?? 0), Math.abs(interiorStage ?? 0)));
  const headPassed = headAvailable && headDiffM > 0 && headDiffM + headTolerance >= ruleProfile.minPositiveHeadDiffM;
  add('HYDRAULIC_HEAD_DIFF', 'Chênh mực nước ngoài − trong', !headAvailable ? 'MISSING_OR_EXPIRED' : headPassed ? 'PASSED' : 'FAILED', headAvailable ? headDiffM : null, ruleProfile.minPositiveHeadDiffM,
    !sameDatum ? 'Không tính ΔH khi chưa xác nhận cùng hệ cao độ.' : !headAvailable ? 'Thiếu mực nước hữu hạn của một hoặc cả hai phía.'
      : headPassed ? `ΔH = ${headDiffM.toFixed(4)} m đạt mức tối thiểu ${ruleProfile.minPositiveHeadDiffM} m để xem xét tự chảy vào đồng.`
        : `ΔH = ${headDiffM.toFixed(4)} m chưa đạt ${ruleProfile.minPositiveHeadDiffM} m để tự chảy vào đồng.`);
  const mechanical = text(input?.mechanicalStatus);
  const knownMechanical = ['READY', 'NOT_READY', 'MAINTENANCE', 'FAULT', 'BLOCKED', 'OUT_OF_SERVICE'].includes(mechanical);
  const mechanicalPassed = knownMechanical && (!ruleProfile.requireMechanicalReady || mechanical === 'READY');
  add('MECHANICAL_READINESS', 'Tình trạng cơ khí / công trình', !knownMechanical ? 'MISSING_OR_EXPIRED' : mechanicalPassed ? 'PASSED' : 'FAILED', mechanical || null, ruleProfile.requireMechanicalReady ? 'READY' : 'Đã khai báo tình trạng',
    !knownMechanical ? 'Thiếu hoặc chưa xác định trạng thái cơ khí công trình.' : mechanicalPassed ? `Trạng thái ${mechanical} đạt quy tắc đã cấu hình.` : `Công trình ${mechanical}, chưa sẵn sàng để xem xét lấy nước.`);
  const measuredBy = text(input?.measuredBy);
  add('MEASUREMENT_PROVENANCE', 'Người đo / nguồn số đo', measuredBy ? 'PASSED' : 'MISSING_OR_EXPIRED', measuredBy || null, 'Có người đo / nguồn số đo',
    measuredBy ? `Nguồn khai báo: ${measuredBy}.` : 'Cần ghi người đo hoặc nguồn cung cấp số đo tại cống.');
  if (input?.dataKind === 'SIMULATION' || input?.gateObservation === false) {
    add('FIELD_MEASUREMENT', 'Số đo hiện trường tại cống', 'MISSING_OR_EXPIRED', 'SIMULATION', 'FIELD_MEASUREMENT', 'EC mô phỏng / dự báo không thay số đo thực tế tại cống.');
  }
  const missing = checks.filter(check => check.status === 'MISSING_OR_EXPIRED');
  const failed = checks.filter(check => check.status === 'FAILED');
  // NOT_SUITABLE requires valid, current input. Missing/expired evidence takes precedence.
  const status = missing.length ? 'INSUFFICIENT_OR_EXPIRED_DATA' : failed.length ? 'NOT_SUITABLE' : 'ELIGIBLE_FOR_REVIEW';
  return {
    gateId: text(input?.gateId) || 'PILOT_GATE', gateName: text(input?.gateName) || 'Cống thí điểm',
    status, statusTitle: GATE_INTAKE_STATUS_TITLES[status],
    summaryReason: status === 'ELIGIBLE_FOR_REVIEW' ? 'Tất cả tiêu chí kỹ thuật đạt quy tắc kiểm tra và số đo còn hiệu lực. Người vận hành xem xét trước khi thao tác.'
      : [...missing, ...failed].map(check => check.explanation).join(' '),
    evaluatedAtIso: new Date(evalTimeMs).toISOString(),
    validUntilIso: status === 'ELIGIBLE_FOR_REVIEW' ? sampleExpiresAtIso : null,
    sampleExpiresAtIso, sampleAgeHours, headDiffM: headAvailable ? headDiffM : null,
    ruleVersion: ruleProfile.ruleVersion, ruleName: ruleProfile.ruleName, ruleNatureNotice: ruleProfile.ruleNatureNotice,
    ruleProfile: { ...ruleProfile }, forecastAdvisory: advisory, criteriaChecks: checks,
    requiresOperatorReview: true, actuatorCommand: null,
  };
}
