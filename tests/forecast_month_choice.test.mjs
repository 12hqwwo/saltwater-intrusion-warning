import test from 'node:test';
import assert from 'node:assert/strict';
import { forecastMonthFromToday } from '../frontend/src/features/multivariate-forecast.js';

test('quick forecast choices follow the current month across year boundaries', () => {
  const november = new Date(2026, 10, 7);
  assert.equal(forecastMonthFromToday(0, november), '2026-11');
  assert.equal(forecastMonthFromToday(1, november), '2026-12');
  const december = new Date(2026, 11, 31);
  assert.equal(forecastMonthFromToday(1, december), '2027-01');
});
