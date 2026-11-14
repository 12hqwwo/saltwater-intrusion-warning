import assert from 'node:assert/strict';
import test from 'node:test';
import { freshnessText } from '../frontend/src/features/overview.js';

test('source currency names the measured month and supported target', () => {
  assert.match(freshnessText('ERA5_MYTHO', {
    status: 'DUE', last_source_month: '2026-10', next_target_month_supported: '2026-12',
  }), /Mỹ Tho: Sắp cần cập nhật.*2026-10.*2026-12/);
});

test('frozen EC label has no forecast support month', () => {
  const text = freshnessText('MRC_EC_MYTHO', {
    status: 'STALE', last_source_month: '2023-12', last_observation: '2023-12-15',
    next_target_month_supported: null,
  });
  assert.match(text, /Đã quá hạn.*2023-12-15/);
  assert.doesNotMatch(text, /Dự báo đến/);
});
