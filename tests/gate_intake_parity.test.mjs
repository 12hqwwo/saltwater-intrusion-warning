import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { evaluateGateIntakeCondition, DEFAULT_GATE_RULE_PROFILE } from '../frontend/src/shared/gate-intake-rules.js';

const fixture = JSON.parse(readFileSync(new URL('./fixtures/gate_intake_cases.json', import.meta.url), 'utf8'));
for (const item of fixture.cases) {
  test(`gate fixture ${item.id}`, () => {
    const result = evaluateGateIntakeCondition({ ...fixture.base_measurement, ...item.measurement },
      DEFAULT_GATE_RULE_PROFILE, item.context, fixture.now_iso);
    assert.equal(result.status, item.expected);
    assert.equal(result.requiresOperatorReview, true);
    assert.equal(result.actuatorCommand, null);
    assert.ok(result.criteriaChecks.some(check => check.id === 'SAMPLE_FRESHNESS'));
  });
}
