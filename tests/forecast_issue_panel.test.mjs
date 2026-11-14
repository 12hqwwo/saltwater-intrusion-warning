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
  assert.match(scoreSummary({ by_source: {} }), /chưa có EC tháng đủ điều kiện/);
});

test('MRC and approved field EC25 report distinct on-time and late errors', () => {
  const text = scoreSummary({ by_source: {
    MRC: { on_time_n_scored: 2, on_time_mae_mS_m: 10, late_n_scored: 1, late_mae_mS_m: 20 },
    FIELD_APPROVED: { on_time_n_scored: 3, on_time_mae_mS_m: 90, late_n_scored: 1, late_mae_mS_m: 70 },
  } });
  assert.match(text, /MRC · Đúng hạn: MAE 10 mS\/m \(n=2\).*Phát hành trễ: MAE 20/);
  assert.match(text, /EC25 thực địa đã duyệt · Đúng hạn: MAE 90 mS\/m \(n=3\).*Phát hành trễ: MAE 70/);
});

test('field-only scores leave MRC unscored and an old pooled response is not displayed', () => {
  const text = scoreSummary({ by_source: {
    MRC: {}, FIELD_APPROVED: { on_time_n_scored: 1, on_time_mae_mS_m: 90 },
  } });
  assert.match(text, /MRC · Đúng hạn: chưa có EC tháng đủ điều kiện/);
  assert.match(text, /EC25 thực địa đã duyệt · Đúng hạn: MAE 90/);
  const old = scoreSummary({ on_time_n_scored: 2, on_time_mae_mS_m: 50 });
  assert.match(old, /Cần cập nhật máy chủ/);
  assert.doesNotMatch(old, /MAE 50/);
});
