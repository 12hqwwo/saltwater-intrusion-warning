export const RIVER_PARTICLE_COUNT = 72;
export const RIVER_STREAK_BANDS = 4;
export const WIND_COLOR = '#0284c7';
export function windAppearance(theme) {
  if (theme === 'dark') return { color: '#67e8f9', opacity: 0.78, thickness: 1.3 };
  if (theme === 'satellite') return { color: '#b6f1ff', opacity: 0.8, thickness: 1.3 };
  return { color: WIND_COLOR, opacity: 0.55, thickness: 1.1 };
}
export const MAX_PARTICLE_DT = 0.05;
export const WIND_TRAIL_POINTS = 34;
export const RIVER_TRAIL_POINTS = 16;

export function appendTrailPoint(trail, point, limit, spacing = 0.8) {
  const last = trail.at(-1);
  if (!last || Math.hypot(point[0] - last[0], point[1] - last[1]) >= spacing) {
    trail.push(point.slice());
    if (trail.length > limit) trail.shift();
  }
  // The head follows every frame; committed tail samples use spatial spacing.
  const committed = trail.at(-1);
  return committed[0] !== point[0] || committed[1] !== point[1] ? [...trail, point] : trail;
}

export function windParticleCount(width, height) {
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return 0;
  const mobile = width < 600;
  return Math.max(mobile ? 90 : 220, Math.min(mobile ? 140 : 360, Math.round(width * height / 3000)));
}

export function riverMotion(properties = {}) {
  const upstream = properties.flow_direction === 'UPSTREAM_SALINE_INTRUSION';
  const factor = Number(properties.flow_velocity_factor);
  return { direction: upstream ? -1 : 1,
    speed: 32 * (Number.isFinite(factor) ? Math.max(0.2, Math.min(1.5, factor)) : 1),
    color: '#ffffff' };
}

export function windVector(wind) {
  if (!wind || wind.available === false) return null;
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const u = wind.u10 ?? wind.eastward_10m_ms, v = wind.v10 ?? wind.northward_10m_ms;
  if (finite(u) && finite(v)) return { x: u, y: -v, speed: Math.hypot(u, v) };
  const speed = wind.speed_ms ?? wind.resultant_speed_ms;
  const direction = wind.direction_from_deg ?? wind.direction_from_degrees ?? wind.direction_degrees;
  if (!finite(speed) || speed < 0 || !finite(direction)) return null;
  const radians = direction * Math.PI / 180;
  // Meteorological bearings specify where wind comes FROM; canvas y is south.
  return { x: -speed * Math.sin(radians), y: speed * Math.cos(radians), speed };
}

export function mapWindVector(wind, targetMonth) {
  const current = (!wind?.source_month || wind.source_month === targetMonth) ? windVector(wind) : null;
  if (current?.speed > 0) return { ...current, kind: 'MONTHLY_ERA5' };
  const visual = wind?.visualization;
  if (visual?.kind !== 'SEASONAL_VECTOR_CLIMATOLOGY' || visual.target_month !== targetMonth) return null;
  const seasonal = windVector(visual);
  return seasonal?.speed > 0 ? { ...seasonal, kind: 'SEASONAL_VECTOR_CLIMATOLOGY', referencePeriod: visual.reference_period } : null;
}

export function boundedDelta(previous, current) {
  return previous == null ? 0 : Math.max(0, Math.min(MAX_PARTICLE_DT, (current - previous) / 1000));
}

function pathMetrics(points) {
  const distances = [0];
  for (let i = 1; i < points.length; i++) distances.push(distances.at(-1) + Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]));
  return { points, distances, length: distances.at(-1) || 0 };
}

function atDistance(path, distance) {
  let low = 0, high = path.distances.length - 1;
  while (low + 1 < high) { const mid = (low + high) >> 1; if (path.distances[mid] <= distance) low = mid; else high = mid; }
  const a = path.points[low], b = path.points[high];
  const fraction = (distance - path.distances[low]) / (path.distances[high] - path.distances[low] || 1);
  return [a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction];
}

export function createMapParticles({ riverCanvas, windCanvas, project, isVisible = () => true, onFrame,
  requestFrame = callback => requestAnimationFrame(callback), cancelFrame = id => cancelAnimationFrame(id),
  random = Math.random, environment = globalThis } = {}) {
  const riverContext = riverCanvas.getContext('2d'), windContext = windCanvas.getContext('2d');
  const documentRef = environment.document;
  const motionQuery = environment.matchMedia?.('(prefers-reduced-motion: reduce)');
  let frame = null, segments = [], canals = [], intakeGate = null, moving = false;
  let width = 0, height = 0, ratio = 1, riverPath = null, spans = [], canalPaths = [];
  let riverParticles = [], windParticles = [], intakeParticles = [];
  let raf = null, previous = null, running = false, destroyed = false, motionOverride = null;
  let windStyle = windAppearance('light');
  const visible = { river: true, wind: true };
  const clear = context => context?.clearRect(0, 0, width, height);
  function clearAll() { clear(riverContext); clear(windContext); }
  function drawRiverArrows(time = 0) {
    if (!visible.river || !riverContext || !riverPath?.length || moving || !isVisible() || documentRef?.hidden) return;
    // Static chevrons only replace the animation when the user prefers reduced motion.
    for (let distance = 45; distance < riverPath.length; distance += 85) {
      if (distance < 20 || distance > riverPath.length - 20) continue;
      const span = spans.find(item => distance <= item.end) || spans.at(-1);
      const direction = riverMotion(span?.properties).direction;
      const a = atDistance(riverPath, Math.max(0, distance - 9));
      const b = atDistance(riverPath, Math.min(riverPath.length, distance + 9));
      const length = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (length < 2) continue;
      const dx = direction * (b[0] - a[0]) / length, dy = direction * (b[1] - a[1]) / length;
      const center = atDistance(riverPath, distance);
      const tip = [center[0] + dx * 8, center[1] + dy * 8];
      const wing = [center[0] - dx * 6, center[1] - dy * 6];
      riverContext.lineCap = riverContext.lineJoin = 'round';
      riverContext.beginPath();
      riverContext.moveTo(wing[0] - dy * 5, wing[1] + dx * 5);
      riverContext.lineTo(...tip);
      riverContext.lineTo(wing[0] + dy * 5, wing[1] - dx * 5);
      riverContext.strokeStyle = '#082130'; riverContext.lineWidth = 5; riverContext.stroke();
      riverContext.strokeStyle = '#ffffff'; riverContext.lineWidth = 2.5; riverContext.stroke();
    }
  }
  function drawWindArrows() {
    const vector = mapWindVector(frame?.wind, frame?.year_month);
    if (!visible.wind || !windContext || !vector?.speed
      || !isVisible() || documentRef?.hidden || moving) return;
    const dx = vector.x / vector.speed, dy = vector.y / vector.speed;
    windContext.lineCap = windContext.lineJoin = 'round';
    for (let y = 110; y < height; y += 220) {
      for (let x = 120 + (Math.floor(y / 220) % 2) * 100; x < width; x += 250) {
        const cx = x, cy = y;
        if (cx < 20 || cx > width - 20 || cy < 20 || cy > height - 20) continue;
        const tip = [cx + dx * 12, cy + dy * 12], tail = [cx - dx * 12, cy - dy * 12];
        windContext.beginPath(); windContext.moveTo(...tail); windContext.lineTo(...tip);
        windContext.moveTo(tip[0] - dx * 8 - dy * 5, tip[1] - dy * 8 + dx * 5);
        windContext.lineTo(...tip);
        windContext.lineTo(tip[0] - dx * 8 + dy * 5, tip[1] - dy * 8 - dx * 5);
        windContext.strokeStyle = '#082130'; windContext.lineWidth = 5; windContext.stroke();
        windContext.strokeStyle = '#7dd3fc'; windContext.lineWidth = 2.5; windContext.stroke();
      }
    }
  }
  function motionEnabled() { return motionOverride ?? !motionQuery?.matches; }
  function drawStill() { clearAll(); if (!motionEnabled()) { drawRiverArrows(); drawWindArrows(); } }
  function projectPoints(points) {
    const result = points.map(project);
    return result.every(p => Array.isArray(p) && p.length >= 2 && p.every(Number.isFinite)) ? result : [];
  }
  function rebuild() {
    const points = []; spans = [];
    for (const feature of segments) {
      const projected = projectPoints(feature.geometry.coordinates);
      if (projected.length < 2) continue;
      points.push(...projected.slice(points.length ? 1 : 0));
      spans.push({ endIndex: points.length - 1, properties: feature.properties });
    }
    riverPath = pathMetrics(points);
    spans.forEach(span => { span.end = riverPath.distances[span.endIndex]; });
    riverParticles = Array.from({ length: RIVER_PARTICLE_COUNT }, (_, index) => ({
      distance: (index + random()) / RIVER_PARTICLE_COUNT * riverPath.length,
      length: 22 + random() * 14,
    }));
    const gate = frame?.gates?.find(item => item.gate_code === intakeGate);
    canalPaths = gate ? canals.filter(feature => feature.properties?.gate_code === intakeGate || gate.canal_ids?.includes(feature.properties?.id ?? feature.id))
      .map(feature => pathMetrics(projectPoints(feature.geometry.coordinates))).filter(path => path.length > 0) : [];
    intakeParticles = canalPaths.flatMap(path => Array.from({ length: 8 }, () => ({ path, distance: random() * path.length, trail: [] })));
    windParticles = Array.from({ length: windParticleCount(width, height) }, () => ({ x: random() * width, y: random() * height, life: random() * 6, trail: [] }));
    previous = null; drawStill();
  }
  function resize() {
    const rect = riverCanvas.getBoundingClientRect();
    width = Math.max(0, rect.width); height = Math.max(0, rect.height);
    ratio = Math.min(3, Math.max(1, environment.devicePixelRatio || 1));
    for (const [canvas, context] of [[riverCanvas, riverContext], [windCanvas, windContext]]) {
      canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
      context?.setTransform(ratio, 0, 0, ratio, 0, 0);
    }
    rebuild();
  }
  function comet(context, trail, color, opacity, thickness = 1.6) {
    if (!context || trail.length < 2) return;
    context.strokeStyle = color; context.lineCap = 'round'; context.lineWidth = thickness;
    // Six alpha bands keep longer fading tails without a stroke per sample.
    const stride = Math.max(1, Math.ceil((trail.length - 1) / 6));
    for (let i = 1; i < trail.length; i += stride) {
      const end = Math.min(trail.length - 1, i + stride - 1);
      context.globalAlpha = opacity * end / trail.length;
      context.beginPath(); context.moveTo(...trail[i - 1]);
      for (let j = i; j <= end; j++) context.lineTo(...trail[j]);
      context.stroke();
    }
    context.globalAlpha = opacity; context.fillStyle = color;
    const glow = thickness >= 1.5;
    context.shadowColor = color; context.shadowBlur = glow ? 5 : 0;
    context.beginPath(); context.arc(...trail.at(-1), glow ? 0.7 : 0.45, 0, Math.PI * 2); context.fill();
    context.shadowBlur = 0; context.globalAlpha = 1;
  }
  function riverStep(dt) {
    if (!visible.river || !riverPath?.length) return;
    for (const particle of riverParticles) {
      const span = spans.find(item => particle.distance <= item.end) || spans.at(-1);
      const motion = riverMotion(span?.properties);
      particle.distance = (particle.distance + motion.direction * motion.speed * dt + riverPath.length) % riverPath.length;
      // A 22–36 px streak along the path, faded from tail to head so travel direction reads without arrows.
      const tail = Math.max(0, Math.min(riverPath.length, particle.distance - motion.direction * particle.length));
      const reach = particle.distance - tail;
      riverContext.strokeStyle = '#ffffff';
      riverContext.lineCap = riverContext.lineJoin = 'round';
      for (let band = 0; band < RIVER_STREAK_BANDS; band++) {
        const from = tail + reach * band / RIVER_STREAK_BANDS, to = tail + reach * (band + 1) / RIVER_STREAK_BANDS;
        const samples = Math.max(1, Math.ceil(Math.abs(to - from) / 2));
        riverContext.globalAlpha = 0.2 + 0.75 * (band + 1) / RIVER_STREAK_BANDS;
        riverContext.lineWidth = 1.4 + band * 0.4;
        riverContext.beginPath();
        riverContext.moveTo(...atDistance(riverPath, from));
        for (let i = 1; i <= samples; i++) riverContext.lineTo(...atDistance(riverPath, from + (to - from) * i / samples));
        riverContext.stroke();
      }
      riverContext.globalAlpha = 1;
    }
    for (const particle of intakeParticles) {
      particle.distance += 20 * dt;
      if (particle.distance > particle.path.length) { particle.distance = 0; particle.trail = []; }
      const trail = appendTrailPoint(particle.trail, atDistance(particle.path, particle.distance), RIVER_TRAIL_POINTS);
      comet(riverContext, trail, '#fef08a', 0.8);
    }
  }
  function windStep(dt) {
    const vector = mapWindVector(frame?.wind, frame?.year_month);
    if (!visible.wind || !vector || vector.speed === 0) return;
    const scale = Math.min(45, 7 + vector.speed * 4) / vector.speed;
    for (const particle of windParticles) {
      particle.x += vector.x * scale * dt; particle.y += vector.y * scale * dt; particle.life += dt;
      if (particle.x < 0 || particle.x > width || particle.y < 0 || particle.y > height || particle.life > 7) {
        particle.x = random() * width; particle.y = random() * height; particle.life = 0; particle.trail = [];
      }
      const trail = appendTrailPoint(particle.trail, [particle.x, particle.y], WIND_TRAIL_POINTS);
      comet(windContext, trail, windStyle.color, windStyle.opacity, windStyle.thickness);
    }
  }
  function permitted() { return !destroyed && running && frame && !moving && !documentRef?.hidden && motionEnabled() && isVisible() && (visible.river || visible.wind); }
  function tick(time) {
    raf = null;
    if (!permitted()) { previous = null; drawStill(); return; }
    if (ratio !== Math.min(3, Math.max(1, environment.devicePixelRatio || 1))) resize();
    const dt = boundedDelta(previous, time); previous = time;
    clearAll(); riverStep(dt); windStep(dt);
    onFrame?.(time);
    raf = requestFrame(tick);
  }
  function start() { if (destroyed) return; running = true; if (raf == null && permitted()) { previous = null; raf = requestFrame(tick); } }
  function stop() { running = false; if (raf != null) cancelFrame(raf); raf = null; previous = null; clearAll(); }
  function resume() { if (!permitted()) { if (raf != null) cancelFrame(raf); raf = null; previous = null; drawStill(); } else start(); }
  documentRef?.addEventListener('visibilitychange', resume);
  motionQuery?.addEventListener?.('change', resume);
  const observer = environment.ResizeObserver ? new environment.ResizeObserver(() => { resize(); resume(); }) : null;
  observer?.observe(riverCanvas);
  resize();
  return {
    setFrame(value, smoothedSegments = value?.river_segments || []) { frame = value; segments = smoothedSegments; intakeGate = null; rebuild(); resume(); },
    setCanals(value) { canals = value; rebuild(); },
    setIntakeGate(code) { intakeGate = code || null; rebuild(); },
    setVisible(value) { Object.assign(visible, value); drawStill(); resume(); },
    setMotionEnabled(value) { motionOverride = Boolean(value); resume(); },
    setTheme(theme) { windStyle = windAppearance(theme); resume(); },
    setMoving(value) { moving = Boolean(value); if (!moving) rebuild(); resume(); },
    invalidate() { rebuild(); resume(); },
    resize, start, stop,
    destroy() { stop(); destroyed = true; observer?.disconnect(); documentRef?.removeEventListener('visibilitychange', resume); motionQuery?.removeEventListener?.('change', resume); },
  };
}
