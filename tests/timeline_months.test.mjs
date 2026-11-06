import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveValidTimelineMonth } from '../frontend/src/shared/timeline-months.js';
import { createSimulationFrameLoader } from '../frontend/src/features/timeline-scrubber.js';

const months = Array.from({ length: 495 }, (_, i) => {
  const ordinal = 1985 * 12 + 5 + i;
  return `${Math.floor(ordinal / 12)}-${String(ordinal % 12 + 1).padStart(2, '0')}`;
});
test('available timeline bounds clamp October 2026 to August and retain every advertised month', () => {
  assert.equal(months.at(-1), '2026-08');
  assert.equal(resolveValidTimelineMonth('2026-10', months).month, '2026-08');
  assert.equal(resolveValidTimelineMonth('1980-01', months).month, '1985-06');
  for (const month of months) {
    assert.equal(resolveValidTimelineMonth(month, months).month, month);
    assert.equal(resolveValidTimelineMonth(month, months).clamped, false);
  }
});
test('resolver handles sparse/unsorted input without creating missing frames or mutating it', () => {
  const available = ['2024-03', '2023-12', 'invalid', '2024-01', '2024-01'];
  const before = [...available];
  assert.equal(resolveValidTimelineMonth('2024-02', available).month, '2024-01');
  assert.equal(resolveValidTimelineMonth(null, available).month, '2023-12');
  assert.equal(resolveValidTimelineMonth('2024-13', available).month, '2023-12');
  assert.deepEqual(available, before);
  for (const empty of [[], null, undefined, ['invalid']]) {
    assert.deepEqual(resolveValidTimelineMonth('2026-10', empty), { month: null, clamped: false, regimeLabel: 'NO_DATA' });
  }
});
test('December 2023 and January 2024 use distinct academic source labels', () => {
  const observed = resolveValidTimelineMonth('2023-12', months);
  const extended = resolveValidTimelineMonth('2024-01', months);
  assert.equal(observed.regimeLabel, 'HISTORICAL_MRC_OBSERVED');
  assert.equal(observed.regimeDescription, 'Quan trắc lịch sử MRC');
  assert.equal(extended.regimeLabel, 'EXTENDED_METEOROLOGICAL_ESTIMATE');
  assert.equal(extended.regimeDescription, 'Chuỗi ước tính khí tượng mở rộng (chưa phải quan trắc MRC)');
});
test('frame loader never calls an out-of-range or missing month and announces clamping', async () => {
  const calls = [], notices = [], errors = [];
  const thresholds = { open_below_ec: 100, close_above_ec: 150 };
  const loader = createSimulationFrameLoader({ availableMonths: months, onClamp: detail => notices.push(detail),
    onError: error => errors.push(error), api: async path => {
      const month = new URL(path, 'https://test.invalid').searchParams.get('year_month');
      calls.push(month);
      return { year_month: month, simulation_layer: true, gates: [], river_segments: [],
        thresholds: { open_below_ec_ms_m: 100, close_at_or_above_ec_ms_m: 150 } };
    },
  });
  assert.equal((await loader.load('2026-10', thresholds)).year_month, '2026-08');
  assert.equal(notices[0].requestedMonth, '2026-10');
  loader.setAvailableMonths(['2024-01', '2024-03']);
  await loader.load('2024-02', thresholds);
  assert.deepEqual(calls, ['2026-08', '2024-01']);
  loader.setAvailableMonths([]);
  assert.equal(await loader.load('2026-10', thresholds), null);
  assert.equal(calls.length, 2);
  assert.match(errors[0].message, /Chưa có tháng/);
});
