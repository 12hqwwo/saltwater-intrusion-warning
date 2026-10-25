import Map from 'ol/Map.js';
import View from 'ol/View.js';
import GeoJSON from 'ol/format/GeoJSON.js';
import TileLayer from 'ol/layer/Tile.js';
import VectorLayer from 'ol/layer/Vector.js';
import OSM from 'ol/source/OSM.js';
import XYZ from 'ol/source/XYZ.js';
import Feature from 'ol/Feature.js';
import Point from 'ol/geom/Point.js';
import { getVectorContext } from 'ol/render.js';
import VectorSource from 'ol/source/Vector.js';
import { Circle, Fill, Stroke, Style, Text, RegularShape, Icon } from 'ol/style.js';
import { fromLonLat } from 'ol/proj.js';
import { defaults as controls, ScaleLine } from 'ol/control.js';
import { mapFeatures } from '../research-utils.js';
import { ecComparison } from '../shared/ec-scenario.js';
import { formatWater, advisoryColor } from '../shared/simulation-display.js';
import { smoothRiverSegments, smoothCoordinates } from './river-geometry.js';
import { createMapParticles } from './map-particles.js';

// Zero tangents keep every sampled point on its supplied vertex-to-vertex span.
// The ribbon, canal display and particles must follow the same constrained path.
const riverInterpolation = { tension: 0, samplesPerSpan: 12 };

function riverColor(ec, alpha = 1) {
  const stops = [[0,[0,229,255]],[1,[16,185,129]],[2,[250,204,21]],[4,[249,115,22]],[6,[244,63,94]],[8,[168,85,247]]];
  const value = Math.max(0, Number(ec) * .0064), index = stops.findIndex(([limit]) => value <= limit);
  const high = index < 0 ? stops.length - 1 : Math.max(1,index), [lowValue,low] = stops[high-1], [highValue,upper] = stops[high];
  const t = Math.min(1, Math.max(0,(value-lowValue)/(highValue-lowValue)));
  return `rgba(${low.map((channel,i)=>Math.round(channel+(upper[i]-channel)*t)).join(',')},${alpha})`;
}

// A single cached SVG label supplies rounded glass, a white keyline and a soft shadow.
function glassLabel(text, zIndex = 25) {
  const escaped = String(text).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[char]));
  const context = document.createElement('canvas').getContext('2d');
  context.font = '600 12px Segoe UI, sans-serif';
  const width = Math.ceil(context.measureText(String(text)).width) + 24;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width + 24}" height="52"><defs><filter id="shadow" x="-30%" y="-60%" width="160%" height="220%"><feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000" flood-opacity=".25"/></filter></defs><rect x="12" y="7" width="${width}" height="28" rx="14" fill="#0f172a" fill-opacity=".88" stroke="#fff" stroke-opacity=".22" filter="url(#shadow)"/><text x="${12 + width / 2}" y="25" text-anchor="middle" font-family="Segoe UI, sans-serif" font-size="12" font-weight="600" fill="#f8fafc">${escaped}</text></svg>`;
  return new Style({ image: new Icon({ src: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`, anchor: [.5, 35 / 52], displacement: [0, 18] }), zIndex });
}

export function createResearchMap(target, { onSelect, onTileError }) {
  const source = new VectorSource(), boundarySource = new VectorSource(), gateSource = new VectorSource(), candidateSource = new VectorSource(), forecastSource = new VectorSource();
  const tileSource = theme => theme === 'satellite' ? new XYZ({ url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', crossOrigin: 'anonymous', attributions: 'Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community' }) : new OSM();
  const base = new TileLayer({ source: tileSource(), className: 'simulation-base-tiles' });
  let frame = null, corridor = null, displayUnit = 'ec', selectedGate = null, intakeGate = null, disposed = false;
  let initialSimulationFit = false, hoveredSegment = null, hoveredGate = null;
  const riverSource = new VectorSource({ attributions: 'River geometry &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · ODbL' }), canalSource = new VectorSource(), simulationGateSource = new VectorSource(), isoSource = new VectorSource();
  const ribbonStyles = new globalThis.Map();
  function ribbonStyle(feature, resolution, band) {
    const ec = feature.get('ec_mS_m'), key = Number(ec).toFixed(3);
    const zoom = Math.log2(156543.03392804097 / resolution);
    const scale = Math.min(1.4, Math.max(.85, 2 ** ((zoom - 10) * .08)));
    const widths = [(10 + 2 * Math.max(0, Math.min(1, zoom - 9))) * scale, 4.5 * scale];
    if (!ribbonStyles.has(key)) ribbonStyles.set(key, widths.map(width => new Style({ stroke: new Stroke({ color: riverColor(ec), width, lineCap: 'round', lineJoin: 'round' }) })));
    const style = ribbonStyles.get(key)[band];
    style.getStroke().setWidth(widths[band]);
    return style;
  }
  // Opacity is applied once per complete canvas, avoiding darker round segment joints.
  // No black casing, and the main river never goes into the dashed canal layer.
  const riverDiffusion = new VectorLayer({ source: riverSource, className: 'river-water-diffusion', opacity: .25, updateWhileAnimating: true, updateWhileInteracting: true, style: (f, resolution) => ribbonStyle(f, resolution, 0) });
  const riverLayer = new VectorLayer({ source: riverSource, className: 'river-water-core', opacity: .78, updateWhileAnimating: true, updateWhileInteracting: true, style: (f, resolution) => ribbonStyle(f, resolution, 1) });
  const canalLayer = new VectorLayer({ source: canalSource, style: new Style({ stroke: new Stroke({ color: 'rgba(148,163,184,.55)', width: 2, lineDash: [5, 7] }) }) });
  const simulationGates = new VectorLayer({ source: simulationGateSource, style: f => {
    const color = advisoryColor(f.get('gate'));
    const active = [selectedGate, hoveredGate].includes(f.get('gate').gate_code);
    const radius = active ? 9 : 5.5;
    return [new Style({ image: new Circle({ radius: radius + 4, fill: new Fill({ color: 'rgba(15,23,42,.08)' }) }), zIndex: active ? 22 : 18 }),
      new Style({ image: new Circle({ radius: radius + 2, fill: new Fill({ color: 'rgba(15,23,42,.17)' }) }), zIndex: active ? 23 : 19 }),
      new Style({ image: new Circle({ radius, fill: new Fill({ color }), stroke: new Stroke({ color: '#ffffff', width: 2 }) }), zIndex: active ? 24 : 20 })];
  } });
  const isoStyles = new globalThis.Map();
  const isoLayer = new VectorLayer({ source: isoSource, declutter: true, style: feature => {
    const text = `Ranh ${feature.get('salinity_g_l')} g/L · km ${Number(feature.get('chainage_km')).toFixed(1)}`;
    if (!isoStyles.has(text)) isoStyles.set(text, [new Style({ image: new RegularShape({ points: 3, radius: 7, rotation: Math.PI / 2, fill: new Fill({ color: '#facc15' }), stroke: new Stroke({ color: '#fff', width: 2 }) }), zIndex: 22 }), glassLabel(text)]);
    return isoStyles.get(text);
  } });
  let selected = null, collection = { type: 'FeatureCollection', features: [] }, showUnconfirmed = false, forecastResult = null;
  const formatter = new GeoJSON(), cache = new globalThis.Map();
  const options = { dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857' };
  const boundaries = new VectorLayer({ source: boundarySource, style: new Style({ stroke: new Stroke({ color: 'rgba(56,189,248,.35)', width: 1.2, lineDash: [4,4] }), fill: new Fill({ color: 'rgba(14,116,144,.04)' }) }) });
  const stations = new VectorLayer({ source, declutter: true, style(f) {
    const comparison = ecComparison(), ec = f.get('latest_ec_mS_m');
    const exceeds = comparison && Number.isFinite(ec) ? ec >= comparison.threshold : null;
    const stationName = `${f.get('site_code')} ${f.get('site_name')}`.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z]/gi, '').toLowerCase();
    const monthlyEC = stationName.includes('tanchau') ? frame?.inputs?.tan_chau_ec_mS_m : stationName.includes('mytho') ? frame?.inputs?.my_tho_ec_mS_m : null;
    const simulationLabel = monthlyEC == null ? '' : `\nĐầu vào mô phỏng ${frame.year_month}: ${formatWater(monthlyEC, displayUnit)}`;
    const stationLabel = stationName.includes('tanchau') ? 'Tân Châu' : stationName.includes('mytho') ? 'Mỹ Tho' : f.get('site_name');
    const compactValue = monthlyEC ?? ec;
    const compactWater = compactValue == null ? '—' : displayUnit === 'salinity' ? `${(Number(compactValue)*.0064).toLocaleString('vi-VN',{maximumFractionDigits:2})} g/L` : `${Number(compactValue).toLocaleString('vi-VN',{maximumFractionDigits:1})} mS/m`;
    const key = `${f.get('site_code')}:${f.get('site_code') === selected}:${f.get('assumed_crs')}:${exceeds}:${displayUnit}:${simulationLabel}`;
    if (!cache.has(key)) {
      const active = f.get('site_code') === selected;
      const color = exceeds === true ? '#c44d39' : exceeds === false ? '#087f78' : f.get('assumed_crs') ? '#b77a23' : '#097c78';
      cache.set(key, [new Style({
        image: new Circle({ radius: active ? 9 : 6, fill: new Fill({ color }), stroke: new Stroke({ color: '#fff', width: 2, lineDash: f.get('assumed_crs') ? [3, 2] : undefined }) }), zIndex: active ? 24 : 21,
      }), glassLabel(`${stationLabel} · ${compactWater}${monthlyEC == null ? '' : ' ◇'}`, active ? 28 : 26)]);
    }
    return cache.get(key);
  } });
  const gates = new VectorLayer({ source: gateSource, style: new Style({ image: new Circle({ radius: 5.5, fill: new Fill({ color: '#7560a7' }), stroke: new Stroke({ color: '#fff', width: 2 }) }) }) });
  const candidates = new VectorLayer({ source: candidateSource, style: new Style({ stroke: new Stroke({ color: '#7560a7', width: 2, lineDash: [6, 5] }) }) });
  const forecastLayer = new VectorLayer({ source: forecastSource, style(f) {
    return new Style({ image: new Circle({ radius: 13, fill: new Fill({ color: 'rgba(54,105,191,.16)' }), stroke: new Stroke({ color: '#3669bf', width: 3 }) }), text: new Text({ text: `Dự báo ${f.get('target_month')}: ${formatWater(f.get('predicted_ec_mS_m'), displayUnit)}`, offsetY: 27, font: '600 13px Segoe UI', fill: new Fill({ color: '#234d90' }), backgroundFill: new Fill({ color: '#fff' }), padding: [4, 6, 4, 6], stroke: new Stroke({ color: '#fff', width: 3 }) }), zIndex: 15 });
  } });
  const map = new Map({ target, layers: [base, boundaries, canalLayer, riverDiffusion, riverLayer, candidates, gates, simulationGates, stations, forecastLayer, isoLayer], controls: controls({ rotate: false, attributionOptions: { collapsible: false } }).extend([new ScaleLine()]),
    view: new View({ center: fromLonLat([105.8, 10.45]), zoom: 8.7, minZoom: 5, maxZoom: 18, enableRotation: false }) });
  if (onTileError) base.getSource().on('tileloaderror', onTileError);
  const canvases = ['river', 'wind'].map(kind => {
    const canvas = document.createElement('canvas'); canvas.className = `map-particle-canvas map-particles-${kind}`; canvas.setAttribute('aria-hidden','true');
    Object.assign(canvas.style,{ position:'absolute', inset:'0', width:'100%', height:'100%', pointerEvents:'none', zIndex: kind === 'river' ? '3' : '2' }); target.append(canvas); return canvas;
  });
  let lastHaloRender = 0;
  const particles = createMapParticles({ riverCanvas: canvases[0], windCanvas: canvases[1], project: coordinate => map.getPixelFromCoordinate(fromLonLat(coordinate)), isVisible: () => !disposed && !document.hidden && !document.getElementById('observations')?.hidden,
    onFrame: time => { if (time-lastHaloRender > 65) { lastHaloRender=time; map.render(); } } });
  particles.start();
  map.on('movestart', () => particles.setMoving(true)); map.on('moveend', () => particles.setMoving(false));
  map.on('singleclick', event => {
    const found = map.forEachFeatureAtPixel(event.pixel, f => f, { layerFilter: l => l === simulationGates, hitTolerance: 10 });
    if (found) selectSimulationGate(found.get('gate').gate_code, false);
  });
  map.on('singleclick', event => { const f = map.forEachFeatureAtPixel(event.pixel, f => f, { layerFilter: l => l === stations, hitTolerance: 7 }); if (f) onSelect(f.get('site_code')); });
  const toolbar = target.parentElement.querySelector('.map-toolbar');
  const observer = new ResizeObserver(() => {
    if (toolbar) target.parentElement.style.setProperty('--map-header-height', `${toolbar.getBoundingClientRect().height}px`);
    map.updateSize(); particles.resize();
  });
  observer.observe(target);
  if (toolbar) observer.observe(toolbar);
  const riverTooltip = document.createElement('div'); riverTooltip.id = 'simulationRiverTooltip'; riverTooltip.className = 'simulation-river-tooltip'; riverTooltip.hidden = true; riverTooltip.setAttribute('role', 'status'); target.parentElement.append(riverTooltip);
  function updateRiverTooltip() {
    riverTooltip.hidden = !hoveredSegment;
    if (hoveredSegment) riverTooltip.textContent = `Sông Tiền · mô phỏng ${frame?.year_month || ''} · km ${hoveredSegment.get('chainage_start_km')}–${hoveredSegment.get('chainage_end_km')} · ${formatWater(hoveredSegment.get('ec_mS_m'), displayUnit, hoveredSegment.get('salinity_g_l'))}`;
  }
  function inspectRiver(event) {
    const gate = event.dragging ? null : map.forEachFeatureAtPixel(event.pixel, feature => feature, { layerFilter: layer => layer === simulationGates, hitTolerance: 5 });
    const nextHoveredGate = gate?.get('gate').gate_code || null;
    if (hoveredGate !== nextHoveredGate) { hoveredGate = nextHoveredGate; simulationGates.changed(); }
    hoveredSegment = map.forEachFeatureAtPixel(event.pixel, feature => feature, { layerFilter: layer => layer === riverLayer, hitTolerance: 8 }) || null; updateRiverTooltip();
    const station = map.forEachFeatureAtPixel(event.pixel, feature => feature, { layerFilter: layer => layer === stations, hitTolerance: 14 });
    if (station) {
      const name = `${station.get('site_code')} ${station.get('site_name')}`.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z]/gi,'').toLowerCase();
      const value = name.includes('tanchau') ? frame?.inputs?.tan_chau_ec_mS_m : name.includes('mytho') ? frame?.inputs?.my_tho_ec_mS_m : null;
      riverTooltip.hidden = false; riverTooltip.textContent = `${station.get('site_name')} · Quan trắc ${station.get('last_observed_date') || 'chưa rõ ngày'}: ${formatWater(station.get('latest_ec_mS_m'),displayUnit)}${value == null ? '' : ` · ◇ Đầu vào mô phỏng ${frame.year_month}: ${formatWater(value,displayUnit)}`}`;
    }
  }
  map.on('pointermove', inspectRiver); map.on('singleclick', inspectRiver);
  const clearGateHover = () => { if (hoveredGate) { hoveredGate = null; simulationGates.changed(); } };
  target.addEventListener('pointerleave', clearGateHover);
  map.getView().on('change:resolution', () => simulationGates.changed());
  function fitMap() {
    const extent = riverSource.getFeatures().length ? riverSource.getExtent() : boundarySource.getFeatures().length ? boundarySource.getExtent() : source.getExtent();
    const size = map.getSize() || [1000, 900], mobile = size[0] < 700;
    const dockHeight = document.getElementById('simulationTimeline')?.getBoundingClientRect().height || 255;
    const forecastVisible = !document.getElementById('mapForecastBanner')?.hidden;
    const desired = [forecastVisible ? (mobile ? 285 : 210) : (mobile ? 220 : 145), mobile ? 70 : 90, dockHeight + 35, mobile ? 70 : 90];
    // Keep a usable viewport even when an embedding panel is shorter than its overlays.
    const scale = Math.min(1, Math.max(0, size[1] - 150) / (desired[0] + desired[2]));
    const padding = [desired[0] * scale, desired[1], desired[2] * scale, desired[3]];
    if (extent.every(Number.isFinite)) map.getView().fit(extent, { padding, maxZoom: 10, duration: 200 });
  }
  function renderGateCard() {
    const card = document.getElementById('simulationGateCard');
    if (!card) return;
    card.replaceChildren();
    const gate = frame?.gates?.find(item => item.gate_code === selectedGate);
    card.hidden = !gate;
    if (card.hidden) return;
    const add = (tag, text, className) => { const node = document.createElement(tag); node.textContent = text; if (className) node.className = className; card.append(node); return node; };
    const label = add('label', 'Chọn cống mô phỏng');
    const chooser = document.createElement('select'); chooser.setAttribute('aria-label', 'Chọn một trong các cống mô phỏng');
    const placeholder = document.createElement('option'); placeholder.value = ''; placeholder.textContent = 'Chọn cống để xem điều kiện ngoài sông'; chooser.append(placeholder);
    for (const item of frame.gates) { const option = document.createElement('option'); option.value = item.gate_code; option.textContent = `${item.gate_name || item.name || item.gate_code} · ${item.gate_code}`; chooser.append(option); }
    chooser.value = gate?.gate_code || ''; chooser.addEventListener('change', () => selectSimulationGate(chooser.value, true)); label.append(chooser);
    if (!gate) return;
    const close = add('button', '✕', 'simulation-gate-close'); close.type = 'button'; close.setAttribute('aria-label', 'Đóng thông tin cống mô phỏng'); close.addEventListener('click', () => {
      const code = selectedGate; selectSimulationGate(null, false);
      const picker = document.getElementById('simulationGatePicker');
      const profileButton = [...document.querySelectorAll('button[data-gate-code]')].find(item => item.dataset.gateCode === code && item.getClientRects().length);
      const returnTarget = picker?.getClientRects().length ? picker : profileButton || document.getElementById('simulationGatesToggle');
      returnTarget?.focus();
    });
    add('h3', gate.gate_name || gate.name || gate.gate_code, 'simulation-gate-heading');
    const linkedWaterways = (corridor?.corridor?.features || []).filter(feature => gate.canal_ids?.includes(feature.properties?.id)).map(feature => feature.properties.name).filter(Boolean);
    add('p', `${gate.gate_code} · ${gate.waterway_name || gate.waterway || gate.river_name || linkedWaterways.join(', ') || 'Chưa xác minh tên thủy vực'}`);
    add('p', `Lý trình ${Number(gate.chainage_km).toFixed(1)} km · Cách trục sông ${Number(gate.distance_to_axis_km).toFixed(2)} km`);
    add('p', `Ngoài sông (mô phỏng ${frame.year_month}): ${formatWater(gate.simulated_outside_ec_mS_m, displayUnit, gate.simulated_outside_salinity_g_l)}`);
    if (displayUnit === 'ec') add('p', `Độ mặn ${formatWater(gate.simulated_outside_ec_mS_m, 'salinity', gate.simulated_outside_salinity_g_l)}`);
    const advisory = add('p', gate.advisory_label_vi || gate.advisory_label || gate.advisory_code || gate.simulated_gate_state, 'simulation-advisory'); advisory.style.color = advisoryColor(gate);
    add('p', 'Bắt buộc con người kiểm tra & quyết định vận hành. Đây là mô phỏng, không phải lệnh vận hành.');
    const actions = add('div', '', 'simulation-card-actions');
    const apply = document.createElement('button'); apply.type = 'button'; apply.textContent = 'Đưa vào Hồ sơ cống để kiểm tra & quyết định vận hành →';
    apply.addEventListener('click', () => {
      const detail = { kind: 'SPATIAL_SIMULATION', gate, frame, year_month: frame.year_month, thresholds: frame.thresholds, simulation_layer: true };
      window.dispatchEvent(new CustomEvent('workspace:apply-simulation-gate', { detail }));
      window.dispatchEvent(new CustomEvent('workspace:apply-forecast-to-gate', { detail }));
    }); actions.append(apply);
    const test = document.createElement('button'); test.type = 'button'; test.textContent = intakeGate === gate.gate_code ? 'Dừng kịch bản thử lấy nước (mô phỏng)' : 'Thử kịch bản lấy nước (chỉ mô phỏng)'; test.setAttribute('aria-pressed', String(intakeGate === gate.gate_code));
    test.disabled = !(gate.canal_ids?.length); test.addEventListener('click', () => { intakeGate = intakeGate === gate.gate_code ? null : gate.gate_code; particles.setIntakeGate(intakeGate); renderGateCard(); }); actions.append(test);
    if (intakeGate) add('p', 'Hạt chuyển động trong kênh là kịch bản thử do người dùng chọn; không xác nhận cống đang mở.');
  }
  function selectSimulationGate(code, focus = true, interaction) {
    const gate = frame?.gates?.find(item => item.gate_code === code);
    if (selectedGate !== code) { intakeGate = null; particles.setIntakeGate(null); }
    selectedGate = gate?.gate_code || null; simulationGates.changed(); renderGateCard();
    const picker = document.getElementById('simulationGatePicker'); if (picker) picker.value = selectedGate || '';
    window.dispatchEvent(new CustomEvent('workspace:simulation-gate-selected',{detail:{gate_code:selectedGate}}));
    if (gate && focus) { map.getView().animate({center:fromLonLat(gate.coordinates || gate.geometry.coordinates), zoom:Math.max(10,map.getView().getZoom()), duration:450}); if (interaction !== 'hover') document.getElementById('simulationGateCard')?.focus(); }
  }
  function setSimulationCorridor(value) {
    corridor = value; canalSource.clear();
    const features = (value?.corridor?.features || value?.features || []).filter(feature => feature.properties?.type !== 'MAIN_RIVER').map(feature => feature.geometry?.type === 'LineString' ? {...feature,geometry:{...feature.geometry,coordinates:smoothCoordinates(feature.geometry.coordinates, riverInterpolation)}} : feature);
    canalSource.addFeatures(formatter.readFeatures({ type: 'FeatureCollection', features }, options));
    particles.setCanals(features.filter(feature => feature.properties?.type !== 'MAIN_RIVER'));
  }
  function setSimulationFrame(value) {
    frame = value; intakeGate = null; hoveredSegment = null; hoveredGate = null; updateRiverTooltip(); riverSource.clear(); simulationGateSource.clear(); isoSource.clear(); isoStyles.clear();
    const smoothed = smoothRiverSegments(frame?.river_segments || [], riverInterpolation);
    // Subdivide only display geometry: particles retain the original 35 continuous paths.
    const ribbon = smoothed.segments.flatMap(feature => {
      const coordinates = feature.geometry.coordinates, count = Math.min(8, coordinates.length - 1), props = feature.properties;
      const startEC = props.start_ec_mS_m ?? props.ec_mS_m, endEC = props.end_ec_mS_m ?? props.ec_mS_m;
      return Array.from({length:count}, (_, index) => {
        const start = Math.floor(index * (coordinates.length - 1) / count), end = Math.floor((index + 1) * (coordinates.length - 1) / count);
        const fraction = (start + end) / (2 * (coordinates.length - 1)), ec = startEC + (endEC - startEC) * fraction;
        return {...feature, id:`${feature.id || props.segment_id}_R${index}`, properties:{...props,ec_mS_m:ec,salinity_g_l:ec*.0064}, geometry:{...feature.geometry,coordinates:coordinates.slice(start,end+1)}};
      });
    });
    ribbonStyles.clear();
    riverSource.addFeatures(formatter.readFeatures({ type: 'FeatureCollection', features: ribbon }, options));
    particles.setFrame(frame,smoothed.segments);
    for (const gate of frame?.gates || []) {
      const coordinates = gate.coordinates || gate.geometry?.coordinates;
      if (coordinates) simulationGateSource.addFeature(new Feature({ geometry: new Point(fromLonLat(coordinates)), gate }));
    }
    for (const boundary of frame?.isohaline_boundaries || []) {
      if (boundary.status === 'WITHIN_CORRIDOR' && boundary.coordinate) isoSource.addFeature(new Feature({ ...boundary, geometry: new Point(fromLonLat(boundary.coordinate)) }));
    }
    const picker = document.getElementById('simulationGatePicker');
    if (picker) {
      picker.disabled = !frame;
      picker.replaceChildren(); const prompt = document.createElement('option'); prompt.value = ''; prompt.textContent = 'Chọn cống để xem mô phỏng'; picker.append(prompt);
      for (const gate of frame?.gates || []) { const option = document.createElement('option'); option.value = gate.gate_code; option.textContent = `${gate.gate_name || gate.name || gate.gate_code} · ${gate.gate_code}`; picker.append(option); }
      picker.value = selectedGate || '';
      picker.onchange = () => selectSimulationGate(picker.value,true);
    }
    renderGateCard(); stations.changed();
    if (frame && !initialSimulationFit && !document.getElementById('observations')?.hidden) { fitMap(); initialSimulationFit = true; }
  }
  function setDisplayUnit(value) { displayUnit = value === 'salinity' ? 'salinity' : 'ec'; cache.clear(); stations.changed(); isoLayer.changed(); forecastLayer.changed(); renderGateCard(); updateRiverTooltip(); }
  function resumeVisibleMap() { if (!disposed && !document.hidden && !document.getElementById('observations')?.hidden) { map.render(); particles.start(); } }
  document.addEventListener('visibilitychange', resumeVisibleMap);
  const listeners = [
    ['workspace:simulation-corridor', event => setSimulationCorridor(event.detail)],
    ['workspace:simulation-frame', event => setSimulationFrame(event.detail)],
    ['workspace:simulation-loading', () => setSimulationFrame(null)],
    ['workspace:simulation-unit', event => setDisplayUnit(event.detail?.unit)],
    ['workspace:select-simulation-gate', event => selectSimulationGate(event.detail?.gate_code,event.detail?.focus !== false,event.detail?.interaction)],
    ['workspace:viewchange', event => { if (event.detail?.view === 'observations') particles.start(); else particles.stop(); }],
  ];
  listeners.forEach(([name, handler]) => window.addEventListener(name, handler));
  // Particle engine schedules lightweight halo redraws; all streamlines use dedicated canvases.
  riverLayer.on('postrender', event => {
    if (!frame || disposed || document.hidden || document.getElementById('observations')?.hidden || globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
    const context = getVectorContext(event), time = event.frameState.time / 1000;
    const activeGates = simulationGates.getVisible() ? simulationGateSource.getFeatures().filter(feature => [selectedGate, hoveredGate].includes(feature.get('gate').gate_code)) : [];
    for (const feature of [...activeGates, ...isoSource.getFeatures()]) {
      const color = feature.get('gate') ? advisoryColor(feature.get('gate')) : '#fbbf24';
      context.setStyle(new Style({ image: new Circle({ radius: 10 + (time % 1.8) * 4, stroke: new Stroke({ color: `${color}${Math.round((1 - (time % 1.8) / 1.8) * 160).toString(16).padStart(2, '0')}`, width: 1.5 }) }) })); context.drawGeometry(feature.getGeometry());
    }
  });
  function updateForecast() {
    forecastSource.clear();
    if (!forecastResult || !Number.isFinite(forecastResult.predicted_ec_mS_m)) return;
    const feature = collection.features.find(item => item.properties.site_code === forecastResult.site_code);
    if (!feature?.geometry) return;
    forecastSource.addFeatures(formatter.readFeatures({ type: 'FeatureCollection', features: [{ type: 'Feature', geometry: feature.geometry, properties: { target_month: forecastResult.target_month, predicted_ec_mS_m: forecastResult.predicted_ec_mS_m } }] }, options));
  }
  const update = () => { source.clear(); cache.clear(); source.addFeatures(formatter.readFeatures(mapFeatures(collection, showUnconfirmed), options)); updateForecast(); return source.getFeatures().length; };
  return {
    setSimulationCorridor,
    setSimulationFrame,
    setDisplayUnit,
    setRiverParticles(value) { particles.setVisible({river:Boolean(value)}); },
    setWindVisible(value) { particles.setVisible({wind:Boolean(value)}); },
    setBaseTheme(theme) { const next = tileSource(theme); if (onTileError) next.on('tileloaderror', onTileError); base.setSource(next); },
    refresh() { map.updateSize(); particles.resize(); particles.start(); if (frame && !initialSimulationFit && !document.getElementById('observations')?.hidden) { fitMap(); initialSimulationFit = true; } map.render(); },
    setStations(value) { collection = value; return update(); },
    setUnconfirmed(value) { showUnconfirmed = value; return update(); },
    setBoundaries(value) { boundarySource.clear(); boundarySource.addFeatures(formatter.readFeatures(value, options)); },
    setBoundaryVisible(value) { boundaries.setVisible(value); },
    setGateVisible(value) { gates.setVisible(value); candidates.setVisible(value); simulationGates.setVisible(value); if (!value) { clearGateHover(); selectSimulationGate(null,false); } },
    refreshComparison() { cache.clear(); stations.changed(); },
    setForecast(value) { forecastResult = value; updateForecast(); },
    setCandidates(gate, items = []) {
      candidateSource.clear();
      const geometry = gate?.geometry || gate;
      if (geometry?.type !== 'Point') return;
      const features = items.filter(item => item.geometry?.type === 'Point').map(item => ({ type: 'Feature', properties: { site_code: item.site_code }, geometry: { type: 'LineString', coordinates: [geometry.coordinates, item.geometry.coordinates] } }));
      candidateSource.addFeatures(formatter.readFeatures({ type: 'FeatureCollection', features }, options));
    },
    setGates(items) { gateSource.clear(); gateSource.addFeatures(formatter.readFeatures({ type: 'FeatureCollection', features: items.filter(r => r.geometry).map(r => ({ type: 'Feature', geometry: r.geometry, properties: r })) }, options)); },
    select(code) { selected = code; stations.changed(); },
    fit: fitMap,
    setBase(value) { base.setVisible(value); },
    destroy() { disposed = true; particles.destroy(); canvases.forEach(canvas => canvas.remove()); target.removeEventListener('pointerleave', clearGateHover); document.removeEventListener('visibilitychange', resumeVisibleMap); riverTooltip.remove(); const picker = document.getElementById('simulationGatePicker'); if (picker) picker.onchange = null; listeners.forEach(([name, handler]) => window.removeEventListener(name, handler)); observer.disconnect(); map.setTarget(undefined); },
  };
}
