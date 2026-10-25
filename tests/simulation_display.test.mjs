import test from 'node:test';
import assert from 'node:assert/strict';
import { formatWater, salinityColor, advisoryColor } from '../frontend/src/shared/simulation-display.js';

test('water labels distinguish estimates, zero, and unavailable data', () => {
  assert.equal(formatWater(0), '0 mS/m');
  assert.equal(formatWater(null), '—');
  assert.equal(formatWater(Number.NaN), '—');
  assert.equal(formatWater(156.25, 'salinity'), '1 g/L (ước tính; 156,25 mS/m)');
  assert.equal(formatWater(156.25, 'salinity', 2), '2 g/L (ước tính; 156,25 mS/m)');
  assert.equal(formatWater(156.25, 'salinity', 1.2345), '1,235 g/L (ước tính; 156,25 mS/m)');
  assert.match(formatWater(156.25), /mS\/m$/);
});

test('river gradient is continuous at salinity thresholds and saturates', () => {
  assert.equal(salinityColor(0), '#06b6d4');
  assert.equal(salinityColor(156.25), 'rgb(16,185,129)');
  assert.equal(salinityColor(625), 'rgb(245,158,11)');
  assert.equal(salinityColor(937.5), 'rgb(239,68,68)');
  assert.equal(salinityColor(1250), 'rgb(190,18,60)');
  assert.equal(salinityColor(2000), '#be123c');
  assert.equal(salinityColor(Number.NaN), '#64748b');
});

test('gate transition is amber rather than eligible intake green', () => {
  assert.equal(advisoryColor({ simulated_gate_state: 'CAUTION_TRANSITION' }), '#f59e0b');
  assert.equal(advisoryColor({ simulated_gate_state: 'OPEN_INTAKE' }), '#10b981');
  assert.equal(advisoryColor({ simulated_gate_state: 'CLOSED_SALINITY_BARRIER' }), '#ef4444');
  for (const color of ['#10b981', '#f59e0b', '#ef4444']) assert.equal(advisoryColor({ advisory_color: color }), color);
});
