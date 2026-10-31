import test from 'node:test';
import assert from 'node:assert/strict';
import { cropAdvisories } from '../frontend/src/shared/water-advisory.js';

test('crop scenario comparisons handle boundaries without claiming suitability', () => {
  for (const row of cropAdvisories(0)) {
    assert.equal(row.status, 'below');
    assert.match(row.text, /đo kiểm/);
    assert.equal(cropAdvisories(row.openBelowEc).find(item => item.id === row.id).status, 'transition');
    assert.equal(cropAdvisories(row.closeAboveEc).find(item => item.id === row.id).status, 'above');
  }
});

test('missing, non-numeric and physically invalid EC stay unknown', () => {
  for (const value of [null, undefined, '', '50', NaN, Infinity, -1]) {
    assert.ok(cropAdvisories(value).every(row => row.status === 'missing'));
  }
});
