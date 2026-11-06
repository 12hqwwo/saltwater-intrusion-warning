import assert from 'node:assert/strict';
import test from 'node:test';
import { DEFAULT_GATE_RULE_PROFILE as RULE, deriveForecastAdvisoryForGate as advisory,
  evaluateGateIntakeCondition as evaluate, validateGateRuleProfile, gateTimestampMs } from '../frontend/src/shared/gate-intake-rules.js';
import { evaluateGateIntakeCondition as publicEvaluate } from '../frontend/src/features/gate-simulation-draft.js';

const NOW = '2026-11-01T10:00:00Z';
const MEASURED = '2026-11-01T09:00:00Z';
const field = (patch = {}) => ({ gateId: 'G1', gateName: 'Cống thí điểm', measuredAtIso: MEASURED,
  exteriorEcMsM: 100, interiorEcMsM: 90, exteriorStageM: 1.2, interiorStageM: 1,
  sameElevationDatum: true, mechanicalStatus: 'READY', measuredBy: 'Phiếu đo 01', ...patch });
const run = (patch, context = {}, profile = RULE, now = NOW) => evaluate(field(patch), profile, context, now);
const check = (result, id) => result.criteriaChecks.find(item => item.id === id);

test('default RuleProfile is frozen and exposes technical origin, name and version through public module', () => {
  assert.ok(Object.isFrozen(RULE));
  assert.equal(RULE.ruleVersion, 'TECH_SCREENING_RULE_V1.0');
  assert.match(RULE.ruleNatureNotice, /không thay thế quy trình vận hành pháp lý/);
  assert.ok(RULE.ruleName);
  assert.equal(publicEvaluate, evaluate);
});

test('eligible output includes all auditable criteria and an expiry derived from measurement time', () => {
  const result = run();
  assert.equal(result.status, 'ELIGIBLE_FOR_REVIEW');
  assert.equal(result.statusTitle, 'Đề nghị xem xét lấy nước');
  assert.equal(result.validUntilIso, '2026-11-01T15:00:00.000Z');
  assert.equal(result.sampleAgeHours, 1);
  assert.equal(result.criteriaChecks.length, 7);
  for (const item of result.criteriaChecks) {
    assert.equal(item.status, 'PASSED');
    for (const key of ['id', 'label', 'status', 'observedValue', 'thresholdValue', 'explanation']) assert.ok(key in item);
  }
  assert.equal(result.ruleVersion, RULE.ruleVersion);
  assert.deepEqual(result.ruleProfile, RULE);
  assert.equal(result.requiresOperatorReview, true);
  assert.equal(result.actuatorCommand, null);
});

test('thresholds are inclusive, including decimal subtraction and negative elevations', () => {
  assert.equal(run({ exteriorEcMsM: 156.25, interiorEcMsM: 125, exteriorStageM: 1.05 }).status, 'ELIGIBLE_FOR_REVIEW');
  assert.equal(run({ exteriorEcMsM: 0, interiorEcMsM: '0', exteriorStageM: '-0.95', interiorStageM: '-1' }).status, 'ELIGIBLE_FOR_REVIEW');
  assert.equal(run({ exteriorStageM: 1.04999999 }).status, 'NOT_SUITABLE');
  assert.equal(run({ exteriorStageM: 1e16, interiorStageM: 1e16 }).status, 'NOT_SUITABLE', 'large values must not inflate roundoff tolerance');
});

for (const [patch, id] of [
  [{ exteriorEcMsM: 156.2501 }, 'EXTERIOR_EC'], [{ interiorEcMsM: 125.0001 }, 'INTERIOR_EC'],
  [{ exteriorStageM: 1.04 }, 'HYDRAULIC_HEAD_DIFF'], [{ exteriorStageM: 1 }, 'HYDRAULIC_HEAD_DIFF'],
  [{ exteriorStageM: 0.9 }, 'HYDRAULIC_HEAD_DIFF'], ...['NOT_READY', 'MAINTENANCE', 'FAULT', 'BLOCKED', 'OUT_OF_SERVICE'].map(mechanicalStatus => [{ mechanicalStatus }, 'MECHANICAL_READINESS']),
]) test(`valid fresh data fails technical criterion ${id}: ${JSON.stringify(patch)}`, () => {
  const result = run(patch);
  assert.equal(result.status, 'NOT_SUITABLE');
  assert.equal(result.statusTitle, 'Chưa phù hợp để lấy nước');
  assert.equal(check(result, id).status, 'FAILED');
  assert.equal(result.validUntilIso, null);
});

for (const name of ['exteriorEcMsM', 'interiorEcMsM', 'exteriorStageM', 'interiorStageM']) {
  test(`missing or malformed ${name} requires field data`, () => {
    for (const value of [undefined, null, '', '  ', true, false, [], {}, 'abc', 'Infinity', Infinity, NaN, '0x10']) {
      assert.equal(run({ [name]: value }).status, 'INSUFFICIENT_OR_EXPIRED_DATA', String(value));
    }
    if (name.includes('Ec')) assert.equal(run({ [name]: -0.01 }).status, 'INSUFFICIENT_OR_EXPIRED_DATA');
    assert.equal(run({ [name]: name.includes('Ec') ? ' 1e2 ' : name === 'interiorStageM' ? '1.0' : '1.2' }).status, 'ELIGIBLE_FOR_REVIEW');
  });
}

test('datum must be exactly true; no head is computed without confirmation', () => {
  for (const value of [undefined, false, 'true', 1, null]) {
    const result = run({ sameElevationDatum: value, exteriorEcMsM: 200 });
    assert.equal(result.status, 'INSUFFICIENT_OR_EXPIRED_DATA');
    assert.equal(check(result, 'ELEVATION_DATUM').status, 'MISSING_OR_EXPIRED');
    assert.equal(result.headDiffM, null);
    assert.equal(check(result, 'HYDRAULIC_HEAD_DIFF').observedValue, null);
    assert.equal(check(result, 'EXTERIOR_EC').status, 'FAILED', 'retain violations in audit table');
  }
});

test('unknown mechanics and missing provenance require supplementation, never a ready assumption', () => {
  for (const mechanicalStatus of [undefined, null, '', 'UNKNOWN', 'ready', 1]) assert.equal(run({ mechanicalStatus }).status, 'INSUFFICIENT_OR_EXPIRED_DATA');
  for (const measuredBy of [undefined, null, '', '  ', 5, {}]) assert.equal(run({ measuredBy }).status, 'INSUFFICIENT_OR_EXPIRED_DATA');
  assert.equal(run({ measuredBy: ' Phiếu 02 ', mechanicalStatus: ' READY ' }).status, 'ELIGIBLE_FOR_REVIEW');
  assert.equal(run({ mechanicalStatus: 'NOT_READY' }, {}, { ...RULE, requireMechanicalReady: false }).status, 'ELIGIBLE_FOR_REVIEW');
});

test('missing, invalid calendar, timezone-less and any future sample is insufficient', () => {
  for (const measuredAtIso of [undefined, null, '', 'yesterday', '2026-11-01', '2026-11-01T09:00:00',
    '2026-02-30T09:00:00Z', '2025-02-29T09:00:00Z', '2026-13-01T00:00:00Z', '2026-11-01T24:00:00Z',
    '2026-11-01T09:60:00Z', '2026-11-01T09:00:60Z', '2026-11-01T09:00:00+14:01',
    '2026-11-01T09:00:00+07:60', '2026-11-01T09:00:00+15:00', '2026-11-01T10:00:00.001Z']) {
    const result = run({ measuredAtIso });
    assert.equal(result.status, 'INSUFFICIENT_OR_EXPIRED_DATA', String(measuredAtIso));
    assert.equal(result.sampleAgeHours, null);
    assert.equal(result.validUntilIso, null);
  }
});

test('timestamps honor explicit offset, leap days, minute precision and strict evaluation time', () => {
  assert.equal(run({ measuredAtIso: '2026-11-01T16:00+07:00' }).sampleAgeHours, 1);
  assert.equal(run({ measuredAtIso: NOW }).sampleAgeHours, 0);
  assert.equal(gateTimestampMs('2024-02-29T09:00:00.123Z'), Date.parse('2024-02-29T09:00:00.123Z'));
  for (const time of [undefined, null, '', '2026-02-30T09:00:00Z', '2026-11-01T10:00:00']) assert.throws(() => evaluate(field(), RULE, {}, time), /Thời điểm đánh giá/);
});

test('normal and high-vigilance sample expiry boundaries are inclusive to the millisecond', () => {
  for (const [hours, context] of [[6, {}], [2, { isHighVigilance: true }]]) {
    const measuredAtIso = new Date(Date.parse(NOW) - hours * 3600000).toISOString();
    const result = run({ measuredAtIso }, context);
    assert.equal(result.status, 'ELIGIBLE_FOR_REVIEW');
    assert.equal(result.validUntilIso, new Date(NOW).toISOString());
    const expired = run({ measuredAtIso }, context, RULE, '2026-11-01T10:00:00.001Z');
    assert.equal(expired.status, 'INSUFFICIENT_OR_EXPIRED_DATA');
    assert.equal(expired.validUntilIso, null);
    assert.equal(expired.sampleExpiresAtIso, new Date(NOW).toISOString());
  }
});

test('expired or absent evidence takes precedence over technical failures', () => {
  for (const patch of [{ measuredAtIso: '2026-11-01T03:00:00Z' }, { interiorEcMsM: null }]) {
    const result = run({ exteriorEcMsM: 999, mechanicalStatus: 'FAULT', ...patch });
    assert.equal(result.status, 'INSUFFICIENT_OR_EXPIRED_DATA');
    assert.equal(result.statusTitle, 'Cần bổ sung hoặc đo lại');
    assert.equal(check(result, 'EXTERIOR_EC').status, 'FAILED');
    assert.match(result.summaryReason, /vượt ngưỡng/);
  }
});

test('forecast flag, P90 equality and 80% gate equality each tighten six hours to two', () => {
  for (const context of [{ isHighVigilance: true }, { mythoEc: 60.42 }, { mythoEc: 30, projectedGateEc: 125 },
    { mythoEc: 40, p90Threshold: 40 }]) {
    const result = run({ measuredAtIso: '2026-11-01T07:00:00Z' }, { sourceModel: 'RF_compact', ...context });
    assert.equal(result.status, 'INSUFFICIENT_OR_EXPIRED_DATA');
    assert.equal(result.forecastAdvisory.effectiveMaxSampleAgeHours, 2);
    assert.equal(result.forecastAdvisory.vigilanceLevel, 'HIGH_VIGILANCE');
    assert.ok(result.forecastAdvisory.reasons.length);
    assert.equal(result.forecastAdvisory.sourceModel, 'RF_compact');
  }
  const normal = run({ measuredAtIso: '2026-11-01T07:00:00Z' }, { mythoEc: 60.419, projectedGateEc: 124.999, isHighVigilance: 'true' });
  assert.equal(normal.status, 'ELIGIBLE_FOR_REVIEW');
  assert.equal(normal.forecastAdvisory.effectiveMaxSampleAgeHours, 6);
});

test('forecast absence, zero, malformed values and station fallback are described truthfully', () => {
  for (const context of [undefined, null, {}, { mythoEc: null }, { mythoEc: '' }, { mythoEc: -1 }, { mythoEc: false }]) {
    const result = advisory(context);
    assert.equal(result.hasForecastContext, false);
    assert.equal(result.stationForecastEc, null);
    assert.match(result.advisoryMessage, /Chưa có ngữ cảnh/);
  }
  assert.equal(advisory({ mythoEc: 0 }).hasForecastContext, true);
  const fallback = advisory({ mythoEc: 50, projectedGateEc: null, p90Threshold: 'bad', targetMonth: '2026-13' });
  assert.equal(fallback.projectedGateEc, 50);
  assert.equal(fallback.projectionBasis, 'STATION_FALLBACK_NO_PROJECTION');
  assert.equal(fallback.p90Threshold, 60.42);
  assert.equal(fallback.targetMonth, null);
  assert.equal(advisory({ projectedGateEc: 125 }).highByGateRatio, true);
  assert.equal(advisory({ mythoEc: 200, p90Threshold: 999 }).highByGateRatio, true);
});

test('custom profile controls EC, head, lifetime and forecast ratio thresholds', () => {
  const profile = { ...RULE, ruleVersion: 'CUSTOM_V2', maxExteriorEcMsM: 100, maxInteriorEcMsM: 80,
    minPositiveHeadDiffM: 0.1, maxSampleAgeHoursNormal: 4, maxSampleAgeHoursHighVigilance: 1 };
  const result = run({ exteriorEcMsM: 100, interiorEcMsM: 80 }, { projectedGateEc: 80 }, profile);
  assert.equal(result.status, 'ELIGIBLE_FOR_REVIEW');
  assert.equal(result.ruleVersion, 'CUSTOM_V2');
  assert.equal(result.forecastAdvisory.effectiveMaxSampleAgeHours, 1);
  assert.equal(result.validUntilIso, new Date(NOW).toISOString());
  assert.equal(run({ interiorEcMsM: 81 }, {}, profile).status, 'NOT_SUITABLE');
});

test('malformed RuleProfiles fail explicitly instead of silently relaxing criteria', () => {
  for (const profile of [null, [], 'rule', ...['ruleId', 'ruleVersion', 'ruleName', 'ruleNatureNotice'].map(key => ({ ...RULE, [key]: '' })),
    ...['maxExteriorEcMsM', 'maxInteriorEcMsM', 'minPositiveHeadDiffM', 'maxSampleAgeHoursNormal', 'maxSampleAgeHoursHighVigilance', 'p90ReferenceEcMsM'].flatMap(key => [NaN, -1, '6', null].map(value => ({ ...RULE, [key]: value }))),
    { ...RULE, requireSameDatum: false }, { ...RULE, requireMechanicalReady: 'true' },
    { ...RULE, minPositiveHeadDiffM: 0 }, { ...RULE, maxSampleAgeHoursNormal: 0 },
    { ...RULE, maxSampleAgeHoursHighVigilance: 0 }, { ...RULE, maxSampleAgeHoursHighVigilance: 7 }]) {
    assert.throws(() => validateGateRuleProfile(profile));
  }
});

test('evaluation is deterministic, preserves input/profile/context and never replaces missing EC with forecast EC', () => {
  const input = Object.freeze(field()), context = Object.freeze({ mythoEc: 30, projectedGateEc: 40 });
  const first = evaluate(input, RULE, context, NOW);
  assert.deepEqual(evaluate(input, RULE, context, NOW), first);
  first.ruleProfile.maxExteriorEcMsM = 999;
  assert.equal(RULE.maxExteriorEcMsM, 156.25);
  assert.equal(run({ exteriorEcMsM: null }, context).status, 'INSUFFICIENT_OR_EXPIRED_DATA');
  for (const patch of [{ dataKind: 'SIMULATION' }, { gateObservation: false }]) {
    assert.equal(run(patch).status, 'INSUFFICIENT_OR_EXPIRED_DATA');
  }
  assert.equal(evaluate(null, RULE, {}, NOW).status, 'INSUFFICIENT_OR_EXPIRED_DATA');
});
