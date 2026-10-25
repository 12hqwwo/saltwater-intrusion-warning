import assert from 'node:assert/strict';
import test from 'node:test';
import { riverMotion, windVector, boundedDelta, createMapParticles, RIVER_PARTICLE_COUNT, windParticleCount, WIND_TRAIL_POINTS, RIVER_TRAIL_POINTS, appendTrailPoint } from '../frontend/src/features/map-particles.js';

test('distance-sampled tails retain length at high refresh rates while heads move on every frame', () => {
  const trail = [];
  appendTrailPoint(trail, [0, 0], 16);
  const display = appendTrailPoint(trail, [0.1, 0], 16);
  assert.deepEqual(trail, [[0, 0]]);
  assert.deepEqual(display.at(-1), [0.1, 0]);
  for (let i = 2; i <= 300; i++) appendTrailPoint(trail, [i / 10, 0], 16);
  assert.equal(trail.length, 16);
  assert.ok(trail.at(-1)[0] - trail[0][0] >= 12);
  for (let i = 1; i < trail.length; i++) assert.ok(trail[i][0] - trail[i - 1][0] >= 0.8);
  const wind = [];
  for (let i = 0; i <= 600; i++) appendTrailPoint(wind, [0, -i / 10], 34);
  assert.equal(wind.length, 34);
  assert.ok(wind[0][1] - wind.at(-1)[1] >= 26);
});

test('wind density scales with viewport while bounded histories keep rendering work predictable', () => {
  assert.equal(windParticleCount(1200, 820), 328);
  assert.equal(windParticleCount(1920, 1080), 360);
  assert.equal(windParticleCount(800, 600), 220);
  assert.equal(windParticleCount(390, 800), 104);
  assert.equal(windParticleCount(0, 800), 0);
  assert.equal(WIND_TRAIL_POINTS, 34);
  assert.equal(RIVER_TRAIL_POINTS, 16);
});

test('meteorological wind FROM bearings and real u10/v10 fields map to canvas travel direction', () => {
  const north = windVector({ available: true, speed_ms: 5, direction_from_deg: 0 });
  assert.equal(north.y, 5);
  const east = windVector({ speed_ms: 4, direction_from_degrees: 90 });
  assert.equal(east.x, -4); assert.ok(Math.abs(east.y) < 1e-10);
  const south = windVector({ resultant_speed_ms: 3, direction_degrees: 180 });
  assert.equal(south.y, -3);
  const components = windVector({ available: true, u10: -2, v10: 3 });
  assert.equal(components.x, -2); assert.equal(components.y, -3);
  assert.ok(Math.abs(components.speed - Math.sqrt(13)) < 1e-12);
  assert.deepEqual(windVector({ eastward_10m_ms: 3, northward_10m_ms: -4 }), { x: 3, y: 4, speed: 5 });
  assert.equal(windVector({ available: false, u10: 2, v10: 2 }), null);
  assert.equal(windVector({ u10: null, v10: null }), null);
  assert.equal(windVector({ speed_ms: -1, direction_from_deg: 0 }), null);
});

test('river direction, color and bounded speed preserve illustrative seasonal flow', () => {
  const fresh = riverMotion({ flow_direction: 'DOWNSTREAM_FRESHWATER', flow_velocity_factor: 1, salinity_g_l: 0.2 });
  const saline = riverMotion({ flow_direction: 'UPSTREAM_SALINE_INTRUSION', flow_velocity_factor: 0.5, salinity_g_l: 5 });
  assert.equal(fresh.direction, 1); assert.equal(fresh.color, '#00e5ff');
  assert.equal(saline.direction, -1); assert.equal(saline.color, '#f43f5e');
  assert.equal(saline.speed, fresh.speed / 2);
  assert.equal(riverMotion({ flow_velocity_factor: 999 }).speed, 33);
  assert.equal(RIVER_PARTICLE_COUNT, 220);
  assert.equal(boundedDelta(null, 1000), 0);
  assert.equal(boundedDelta(1000, 1016), 0.016);
  assert.equal(boundedDelta(1000, 999), 0);
  assert.equal(boundedDelta(1000, 60000), 0.05);
});

function harness() {
  const callbacks = new Map(), listeners = new Map(); let next = 1;
  const context = () => ({ strokes: 0, clears: 0, transform: null, radii: [],
    setTransform(...args) { this.transform = args; }, clearRect() { this.clears++; },
    beginPath() {}, moveTo() {}, lineTo() {}, stroke() { this.strokes++; }, arc(x, y, radius) { this.radii.push(radius); }, fill() {},
  });
  const riverContext = context(), windContext = context();
  const canvas = ctx => ({ getContext: () => ctx, getBoundingClientRect: () => ({ width: 800, height: 600 }) });
  const riverCanvas = canvas(riverContext), windCanvas = canvas(windContext);
  const document = { hidden: false, addEventListener: (name, fn) => listeners.set(name, fn), removeEventListener: name => listeners.delete(name) };
  const motion = { matches: false, addEventListener: (name, fn) => listeners.set(`motion-${name}`, fn), removeEventListener: name => listeners.delete(`motion-${name}`) };
  const environment = { devicePixelRatio: 2, document, matchMedia: () => motion };
  const engine = createMapParticles({ riverCanvas, windCanvas, project: p => p, random: () => 0.4, environment,
    requestFrame: fn => { const id = next++; callbacks.set(id, fn); return id; }, cancelFrame: id => callbacks.delete(id) });
  const feature = { geometry: { type: 'LineString', coordinates: [[0, 100], [800, 100]] }, properties: { flow_direction: 'DOWNSTREAM_FRESHWATER' } };
  const frame = { river_segments: [feature], gates: [{ gate_code: 'G1', canal_ids: ['CANAL1'] }], wind: { available: true, u10: 2, v10: -1 } };
  function tick(time) { const entry = callbacks.entries().next().value; assert.ok(entry); callbacks.delete(entry[0]); entry[1](time); }
  return { engine, callbacks, riverCanvas, windCanvas, riverContext, windContext, environment, document, motion, listeners, frame, tick };
}

test('separate DPR canvases render both trails, honor toggles and cancel RAF on disposal', () => {
  const h = harness();
  assert.equal(h.riverCanvas.width, 1600); assert.equal(h.windCanvas.height, 1200);
  assert.deepEqual(h.riverContext.transform, [2, 0, 0, 2, 0, 0]);
  const original = structuredClone(h.frame);
  h.engine.setFrame(h.frame); h.engine.start(); h.tick(0); h.tick(16);
  assert.ok(h.riverContext.strokes > 0); assert.ok(h.windContext.strokes > 0);
  assert.equal(h.riverContext.radii.at(-1), 0.7);
  assert.equal(h.windContext.radii.at(-1), 0.45);
  h.engine.setVisible({ wind: false }); const windStrokes = h.windContext.strokes;
  h.tick(32); assert.equal(h.windContext.strokes, windStrokes);
  h.engine.setVisible({ river: false }); assert.equal(h.callbacks.size, 0);
  h.engine.setVisible({ river: true }); assert.equal(h.callbacks.size, 1);
  h.engine.destroy(); assert.equal(h.callbacks.size, 0); assert.equal(h.listeners.size, 0);
  assert.deepEqual(h.frame, original);
});

test('hidden/reduced-motion/moving maps stop trails and resume without a large time step', () => {
  const h = harness(); h.engine.setFrame(h.frame); h.engine.start(); h.tick(0);
  h.document.hidden = true; h.listeners.get('visibilitychange')(); assert.equal(h.callbacks.size, 0);
  h.document.hidden = false; h.listeners.get('visibilitychange')(); assert.equal(h.callbacks.size, 1);
  h.motion.matches = true; h.listeners.get('motion-change')(); assert.equal(h.callbacks.size, 0);
  h.motion.matches = false; h.listeners.get('motion-change')(); assert.equal(h.callbacks.size, 1);
  h.engine.setMoving(true); assert.equal(h.callbacks.size, 0);
  h.engine.setMoving(false); assert.equal(h.callbacks.size, 1);
  h.engine.setFrame(null); assert.equal(h.callbacks.size, 0);
  h.engine.destroy();
});

test('long wind tails use at most six faded stroke bands per particle', () => {
  const h = harness(); h.engine.setFrame(h.frame); h.engine.start();
  for (let i = 0; i < 40; i++) h.tick(i * 16);
  const before = h.windContext.strokes;
  h.tick(640);
  assert.ok(h.windContext.strokes > before);
  assert.ok(h.windContext.strokes - before <= 6 * windParticleCount(800, 600));
  h.engine.destroy();
});

test('canal particles require explicit selection and reset on a new frame', () => {
  const h = harness();
  h.frame.river_segments = [];
  h.engine.setCanals([{ id: 'CANAL1', properties: { gate_code: 'G1' }, geometry: { type: 'LineString', coordinates: [[100, 100], [200, 150]] } }]);
  // A source flag alone cannot opt a gate into a visual intake preview.
  h.frame.gates[0].canal_particle_intake_enabled = true;
  h.engine.setFrame(h.frame); h.engine.start(); h.tick(0); h.tick(16);
  assert.equal(h.riverContext.strokes, 0);
  h.engine.setIntakeGate('G1');
  // Intake preview also needs a visible river path in the current map frame.
  h.frame.river_segments = [{ geometry: { type: 'LineString', coordinates: [[0, 0], [800, 0]] }, properties: {} }];
  h.engine.setFrame(h.frame); h.engine.setIntakeGate('G1'); h.tick(32); h.tick(48);
  assert.equal(h.riverContext.strokes, 228, '220 river and 8 explicitly selected canal trails');
  h.engine.setFrame(h.frame); h.tick(64); h.tick(80);
  assert.equal(h.riverContext.strokes, 448, 'new frame clears preview: only 220 river trails');
  h.engine.setFrame(null); assert.equal(h.callbacks.size, 0); h.engine.destroy();
});
