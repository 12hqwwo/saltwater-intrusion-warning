import assert from 'node:assert/strict';
import test from 'node:test';
import { issueRow, scoreSummary } from '../frontend/src/features/forecast-issue-panel.js';

test('missed slot remains visible without a prediction', () => {
  const row = issueRow({ slot: { target_month: '2026-12-01', station_key: 'MYTHO' },
    events: [{ event_type: 'MISSED' }], issue: null, score: null });
  assert.equal(row.status, 'MISSED');
  assert.equal(row.label, 'Chưa có nhãn');
});

test('late issue shows separately from on-time score', () => {
  const row = issueRow({ slot: { target_month: '2026-12-01', station_key: 'MYTHUAN' },
    events: [{ event_type: 'MISSED' }],
    issue: { issue_status: 'LATE', predicted_ec_mS_m: 25 }, score: null });
  assert.equal(row.status, 'LATE');
  assert.match(row.forecast, /25/);
  assert.match(scoreSummary({ on_time_n_scored: 0, on_time_mae_mS_m: null,
    late_n_scored: 0, late_mae_mS_m: null }), /chưa có EC tháng đủ điều kiện/);
});
