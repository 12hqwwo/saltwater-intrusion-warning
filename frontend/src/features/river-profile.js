import { advisoryColor, formatWater } from '../shared/simulation-display.js';

const LENGTH_KM = 175;
const validChainage = value => Number.isFinite(value) && value >= 0 && value <= LENGTH_KM;
export function riverProfileData(frame, unit = 'ec') {
  const convert = value => unit === 'salinity' ? value * 0.0064 : value;
  const samples = new Map();
  for (const feature of frame?.river_segments || []) {
    const p = feature.properties || {};
    for (const [km, ec] of [[p.chainage_start_km, p.start_ec_mS_m], [p.chainage_km, p.ec_mS_m], [p.chainage_end_km, p.end_ec_mS_m]]) {
      if (validChainage(km) && Number.isFinite(ec) && ec >= 0) samples.set(km, convert(ec));
    }
  }
  const points = [...samples].sort((a, b) => a[0] - b[0]);
  const thresholds = [frame?.thresholds?.open_below_ec_ms_m, frame?.thresholds?.close_at_or_above_ec_ms_m]
    .filter(value => Number.isFinite(value) && value >= 0).map(convert);
  const laneEnds = [];
  const gates = [...(frame?.gates || [])].filter(gate => validChainage(gate.chainage_km))
    .sort((a, b) => a.chainage_km - b.chainage_km || String(a.gate_code).localeCompare(String(b.gate_code)))
    .map(gate => {
      let lane = laneEnds.findIndex(end => gate.chainage_km - end >= 3);
      if (lane < 0) lane = laneEnds.length;
      laneEnds[lane] = gate.chainage_km;
      return { gate, x: gate.chainage_km / LENGTH_KM, lane };
    });
  const fronts = (frame?.isohaline_boundaries || []).filter(front => validChainage(front.chainage_km));
  return { points, thresholds, gates, fronts, lanes: laneEnds.length,
    max: Math.max(1e-6, ...points.map(point => point[1]), ...thresholds) * 1.08,
    unit: unit === 'salinity' ? 'g/L' : 'mS/m', extent: [0, LENGTH_KM] };
}

export function profileSelectionDetail(gate_code, interaction = 'activate') {
  return { gate_code, focus: true, source: 'profile', interaction };
}

export function createRiverProfile(host) {
  let frame = null, unit = 'ec', selected = null, hoverTimer = null;
  const doc = host.ownerDocument;
  const win = doc.defaultView;
  const svgNode = (name, attributes = {}) => {
    const element = doc.createElementNS('http://www.w3.org/2000/svg', name);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
    return element;
  };
  function highlight() {
    for (const element of host.querySelectorAll('[data-gate-code]')) {
      const active = element.dataset.gateCode === selected;
      element.classList.toggle('is-selected', active);
      element.setAttribute('aria-pressed', String(active));
      if (element.tagName.toLowerCase() === 'circle') {
        element.setAttribute('stroke', active ? '#0f172a' : '#fff');
        element.setAttribute('stroke-width', active ? '2' : '0.6');
      }
    }
  }
  function select(code, interaction = 'activate') {
    clearTimeout(hoverTimer);
    selected = code;
    highlight();
    win.dispatchEvent(new win.CustomEvent('workspace:select-simulation-gate', { detail: profileSelectionDetail(code, interaction) }));
  }
  function bind(element, gate) {
    element.dataset.gateCode = gate.gate_code;
    element.addEventListener('click', () => select(gate.gate_code));
    element.addEventListener('pointerenter', () => {
      clearTimeout(hoverTimer);
      hoverTimer = setTimeout(() => select(gate.gate_code, 'hover'), 150);
    });
    element.addEventListener('pointerleave', () => clearTimeout(hoverTimer));
  }
  function render() {
    clearTimeout(hoverTimer);
    host.replaceChildren();
    host.hidden = !frame;
    if (!frame) return;
    const data = riverProfileData(frame, unit);
    const header = doc.createElement('div');
    header.className = 'river-profile-header';
    header.textContent = `Dọc sông Tiền · ${data.unit}${unit === 'salinity' ? ' ước tính' : ''} · SIMULATION · ${frame.year_month} · ${data.gates.length} cống`;
    const svg = svgNode('svg', { viewBox: '0 0 1000 56', height: 56, width: '100%', preserveAspectRatio: 'none', class: 'river-profile-chart', role: 'group', 'aria-label': 'Hồ sơ mô phỏng EC dọc 175 km sông Tiền; chọn cống để xem trên bản đồ' });
    const x = km => 8 + km / LENGTH_KM * 984;
    const y = value => 40 - value / data.max * 36;
    data.thresholds.forEach((value, index) => {
      const line = svgNode('line', { x1: 8, x2: 992, y1: y(value), y2: y(value), stroke: index ? '#ef4444' : '#10b981', 'stroke-dasharray': '5 4', class: 'river-profile-threshold' });
      const title = svgNode('title');
      title.textContent = `${index ? 'Ngưỡng ngăn mặn' : 'Ngưỡng lấy nước'}: ${value.toFixed(2)} ${data.unit}`;
      line.append(title); svg.append(line);
    });
    svg.append(svgNode('polyline', { points: data.points.map(([km, value]) => `${x(km)},${y(value)}`).join(' '), fill: 'none', stroke: '#0891b2', 'stroke-width': 2, class: 'river-profile-line' }));
    for (const front of data.fronts) {
      svg.append(svgNode('line', { x1: x(front.chainage_km), x2: x(front.chainage_km), y1: 1, y2: 42, stroke: front.salinity_g_l === 4 ? '#ef4444' : '#f59e0b', 'stroke-dasharray': '2 2', class: 'river-profile-front' }));
      const label = svgNode('text', { x: x(front.chainage_km), y: front.salinity_g_l === 4 ? 18 : 8, 'text-anchor': front.chainage_km > 160 ? 'end' : 'start', 'font-size': 8, fill: '#475569' });
      label.textContent = `${front.salinity_g_l} g/L`; svg.append(label);
    }
    const matrix = doc.createElement('div');
    matrix.className = 'river-profile-gates';
    matrix.setAttribute('aria-label', 'Danh sách cống theo lý trình');
    for (const { gate, lane } of data.gates) {
      const name = `${gate.gate_name || gate.gate_code} · km ${gate.chainage_km.toFixed(2)} · ${formatWater(gate.simulated_outside_ec_mS_m, unit)} · ${gate.advisory_label || 'Cần kỹ sư rà soát'}`;
      const tick = svgNode('circle', { cx: x(gate.chainage_km), cy: 6 + lane / Math.max(1, data.lanes - 1) * 44, r: Math.min(2.7, 20 / Math.max(1, data.lanes)), fill: advisoryColor(gate), stroke: '#fff', 'stroke-width': 0.6, tabindex: 0, role: 'button', 'aria-label': name, class: 'river-profile-tick' });
      const title = svgNode('title'); title.textContent = name; tick.append(title);
      bind(tick, gate);
      tick.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(gate.gate_code); }
      });
      svg.append(tick);
      const button = doc.createElement('button');
      button.type = 'button'; button.className = 'river-profile-gate';
      button.style.setProperty('--gate-color', advisoryColor(gate));
      button.textContent = gate.gate_name || gate.gate_code;
      button.title = name; button.setAttribute('aria-label', name);
      bind(button, gate); matrix.append(button);
    }
    const anchors = doc.createElement('div'); anchors.className = 'river-profile-anchors';
    for (const [name, km] of [['Tân Châu', 0], ['Mỹ Tho', 125], ['Cửa Tiểu', 175]]) {
      const label = doc.createElement('span'); label.textContent = `${name} · ${km} km`;
      label.style.left = `${km / LENGTH_KM * 100}%`;
      label.style.transform = km === 0 ? 'none' : km === 175 ? 'translateX(-100%)' : 'translateX(-50%)';
      anchors.append(label);
    }
    host.append(header, svg, anchors, matrix);
    highlight();
  }
  win.addEventListener('workspace:simulation-gate-selected', event => {
    selected = event.detail?.gate_code || null; highlight();
  });
  return {
    setFrame(value) { frame = value; render(); },
    setUnit(value) { unit = value === 'salinity' ? 'salinity' : 'ec'; render(); },
    clear() { frame = null; render(); },
  };
}
