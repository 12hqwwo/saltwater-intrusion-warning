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
import { fromLonLat, toLonLat } from 'ol/proj.js';
import { defaults as controls, ScaleLine } from 'ol/control.js';
import { mapFeatures } from '../research-utils.js';
import { ecComparison } from '../shared/ec-scenario.js';
import { formatWater, advisoryColor } from '../shared/simulation-display.js';
import { smoothRiverSegments, smoothCoordinates, riverRibbon } from './river-geometry.js';
import { createMapParticles, mapWindVector } from './map-particles.js';
import { inspectWaterPoint, validCoordinate } from './point-inspection.js';
import { cropAdvisories } from '../shared/water-advisory.js';
import { validPrediction } from '../shared/forecast-contract.js';
import { ecWarningLevel, splitGatedWaterways } from './gated-waterways.js';

// Zero tangents keep every sampled point on its supplied vertex-to-vertex span.
// The ribbon, canal display and particles must follow the same constrained path.
const riverInterpolation = { tension: 0, samplesPerSpan: 12 };
const primaryStationLabels = new globalThis.Map([
  ['MRC_VN_019803', 'Tân Châu'],
  ['MRC_VN_019804', 'Mỹ Thuận'],
  ['MRC_VN_019805', 'Mỹ Tho'],
]);

// A single cached SVG label supplies rounded glass, a white keyline and a soft shadow.
function glassLabel(text, zIndex = 25) {
  const escaped = String(text).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[char]));
  const context = document.createElement('canvas').getContext('2d');
  context.font = '600 12px Be Vietnam Pro, sans-serif';
  const width = Math.ceil(context.measureText(String(text)).width) + 24;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width + 24}" height="52"><defs><filter id="shadow" x="-30%" y="-60%" width="160%" height="220%"><feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000" flood-opacity=".25"/></filter></defs><rect x="12" y="7" width="${width}" height="28" rx="14" fill="#0f172a" fill-opacity=".88" stroke="#fff" stroke-opacity=".22" filter="url(#shadow)"/><text x="${12 + width / 2}" y="25" text-anchor="middle" font-family="Be Vietnam Pro, sans-serif" font-size="12" font-weight="600" fill="#f8fafc">${escaped}</text></svg>`;
  return new Style({ image: new Icon({ src: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`, anchor: [.5, 35 / 52], displacement: [0, 18] }), zIndex });
}

export function createResearchMap(target, { onSelect, onTileError }) {
  const token = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const warningColors = { safe: token('--ec-safe'), caution: token('--ec-caution'), risk: token('--ec-risk'), unknown: token('--ec-unknown') };
  const gateWarningColor = gate => warningColors[ecWarningLevel(gate?.simulated_outside_ec_mS_m, frame?.thresholds)];
  const source = new VectorSource(), boundarySource = new VectorSource(), gateSource = new VectorSource(), candidateSource = new VectorSource(), forecastSource = new VectorSource(), inspectSource = new VectorSource(), fieldSource = new VectorSource();
  const tileSource = theme => theme === 'satellite' ? new XYZ({ url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', crossOrigin: 'anonymous', attributions: 'Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community' }) : new OSM();
  const base = new TileLayer({ source: tileSource(), className: 'simulation-base-tiles' });
  let frame = null, corridor = null, displayUnit = 'ec', selectedGate = null, intakeGate = null, disposed = false;
  let riverDirectionVisible = true, windDirectionVisible = true;
  let initialSimulationFit = false, hoveredSegment = null, hoveredGate = null, inspectedCoordinate = null;
  const riverSource = new VectorSource({ attributions: 'River geometry &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · ODbL' }), canalSource = new VectorSource(), simulationGateSource = new VectorSource(), isoSource = new VectorSource();
  const ribbonStyles = new globalThis.Map();
  function ribbonStyle(feature, resolution, band) {
    const ec = feature.get('ec_mS_m'), key = Number(ec).toFixed(3);
    const zoom = Math.log2(156543.03392804097 / resolution);
    const scale = Math.min(1.4, Math.max(.85, 2 ** ((zoom - 10) * .08)));
    const widths = [(10 + 2 * Math.max(0, Math.min(1, zoom - 9))) * scale, 4.5 * scale];
    if (!ribbonStyles.has(key)) ribbonStyles.set(key, widths.map(width => new Style({ stroke: new Stroke({ color: warningColors[ecWarningLevel(ec, frame?.thresholds)], width, lineCap: 'round', lineJoin: 'round' }) })));
    const style = ribbonStyles.get(key)[band];
    style.getStroke().setWidth(widths[band]);
    return style;
  }
  // Opacity is applied once per complete canvas, avoiding darker round segment joints.
  // No black casing, and the main river never goes into the dashed canal layer.
  const riverDiffusion = new VectorLayer({ source: riverSource, className: 'river-water-diffusion', opacity: .25, updateWhileAnimating: true, updateWhileInteracting: true, style: (f, resolution) => ribbonStyle(f, resolution, 0) });
  const riverLayer = new VectorLayer({ source: riverSource, className: 'river-water-core', opacity: .78, updateWhileAnimating: true, updateWhileInteracting: true, style: (f, resolution) => ribbonStyle(f, resolution, 1) });
  const canalLayer = new VectorLayer({ source: canalSource, style: feature => {
    const inland = feature.get('branch_side') === 'beyond_gate';
    if (inland) return null;
    const gate = frame?.gates?.find(item => item.gate_code === feature.get('gate_code'));
    const active = selectedGate === feature.get('gate_code');
    const color = gateWarningColor(gate);
    return new Style({ stroke: new Stroke({ color, width: active ? 5 : 2.5, lineCap: 'round', lineJoin: 'round' }) });
  } });
  const simulationGates = new VectorLayer({ source: simulationGateSource, style: f => {
    const gate = f.get('gate');
    const active = [selectedGate, hoveredGate].includes(gate.gate_code);
    const radius = active ? 7 : 4.5;
    return new Style({ image: new Circle({ radius, fill: new Fill({ color: gateWarningColor(gate) }), stroke: new Stroke({ color: '#ffffff', width: active ? 2 : 1.5 }) }), zIndex: active ? 24 : 20 });
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
    const stationLabel = primaryStationLabels.get(f.get('site_code')) || f.get('site_name');
    const compactWater = displayUnit === 'salinity' && Number.isFinite(ec)
      ? `${(ec * 0.0064).toLocaleString('vi-VN', { maximumFractionDigits: 3 })} g/L ước tính`
      : formatWater(ec);
    const sampleDate = f.get('last_observed_date') || 'chưa có ngày';
    const key = `${f.get('site_code')}:${f.get('site_code') === selected}:${f.get('assumed_crs')}:${exceeds}:${ec}:${sampleDate}:${displayUnit}`;
    if (!cache.has(key)) {
      const active = f.get('site_code') === selected;
      const color = exceeds === true ? '#c44d39' : exceeds === false ? '#087f78' : f.get('assumed_crs') ? '#647985' : '#097c78';
      cache.set(key, [new Style({
        image: new Circle({ radius: active ? 9 : primaryStationLabels.has(f.get('site_code')) ? 6 : 5, fill: new Fill({ color }), stroke: new Stroke({ color: '#fff', width: active ? 2 : 1.5, lineDash: f.get('assumed_crs') ? [3, 2] : undefined }) }), zIndex: active ? 24 : 21,
      }), ...(primaryStationLabels.has(f.get('site_code')) ? [glassLabel(`${stationLabel} · Mẫu ${sampleDate}: ${compactWater}`, active ? 28 : 26)] : [])]);
    }
    return cache.get(key);
  } });
  const fieldLayer = new VectorLayer({ source: fieldSource, style: new Style({
    image: new RegularShape({ points: 3, radius: 8, rotation: Math.PI,
      fill: new Fill({ color: '#9a4bb5' }), stroke: new Stroke({ color: '#fff', width: 2 }) }), zIndex: 27,
  }) });
  const gates = new VectorLayer({ source: gateSource, visible: false, style: new Style({ image: new Circle({ radius: 4.5, fill: new Fill({ color: warningColors.unknown }), stroke: new Stroke({ color: '#fff', width: 1.5 }) }) }) });
  const candidates = new VectorLayer({ source: candidateSource, style: new Style({ stroke: new Stroke({ color: '#7560a7', width: 2, lineDash: [6, 5] }) }) });
  const inspection = new VectorLayer({ source: inspectSource, style: new Style({
    image: new Circle({ radius: 7, fill: new Fill({ color: '#0e7490' }), stroke: new Stroke({ color: '#fff', width: 2 }) }),
    stroke: new Stroke({ color: '#e0f2fe', width: 2, lineDash: [6, 5] }), zIndex: 30,
  }) });
  const forecastLayer = new VectorLayer({ source: forecastSource, style(f) {
    return new Style({ image: new Circle({ radius: 13, fill: new Fill({ color: 'rgba(54,105,191,.16)' }), stroke: new Stroke({ color: '#3669bf', width: 3 }) }), text: new Text({ text: `Dự báo ${f.get('target_month')}: ${formatWater(f.get('predicted_ec_mS_m'), displayUnit)}`, offsetY: 27, font: '600 13px Be Vietnam Pro', fill: new Fill({ color: '#234d90' }), backgroundFill: new Fill({ color: '#fff' }), padding: [4, 6, 4, 6], stroke: new Stroke({ color: '#fff', width: 3 }) }), zIndex: 15 });
  } });
  function hasRenderableSize() { return !disposed && target.clientWidth > 0 && target.clientHeight > 0 && !target.closest('[hidden]'); }
  const map = new Map({ layers: [base, boundaries, canalLayer, riverDiffusion, riverLayer, candidates, gates, simulationGates, stations, fieldLayer, forecastLayer, isoLayer, inspection], controls: controls({ rotate: false, attributionOptions: { collapsible: false } }).extend([new ScaleLine()]),
    view: new View({ center: fromLonLat([105.8, 10.45]), zoom: 8.7, minZoom: 5, maxZoom: 18, enableRotation: false }) });
  function ensureMapMounted() {
    if (!hasRenderableSize()) {
      if (map.getTarget()) map.setTarget(undefined);
      return false;
    }
    if (map.getTarget() !== target) map.setTarget(target);
    map.updateSize();
    return true;
  }
  ensureMapMounted();
  if (onTileError) base.getSource().on('tileloaderror', onTileError);
  const canvases = ['river', 'wind'].map(kind => {
    const canvas = document.createElement('canvas'); canvas.className = `map-particle-canvas map-particles-${kind}`; canvas.setAttribute('aria-hidden','true');
    Object.assign(canvas.style,{ position:'absolute', inset:'0', width:'100%', height:'100%', pointerEvents:'none', zIndex: kind === 'river' ? '3' : '2' }); target.append(canvas); return canvas;
  });
  let lastHaloRender = 0;
  const particles = createMapParticles({ riverCanvas: canvases[0], windCanvas: canvases[1], project: coordinate => map.getPixelFromCoordinate(fromLonLat(coordinate)), isVisible: () => !disposed && !document.hidden && !document.getElementById('observations')?.hidden,
    onFrame: time => { if (hasRenderableSize() && time-lastHaloRender > 65) { lastHaloRender=time; map.render(); } } });
  particles.start();
  function updateDirectionStatus() {
    const status = document.getElementById('mapDirectionStatus');
    const riverRow = document.getElementById('mapRiverDirectionStatus');
    const windRow = document.getElementById('mapWindDirectionStatus');
    const windArrow = document.getElementById('mapWindDirectionArrow');
    const windText = document.getElementById('mapWindDirectionText');
    if (!status || !riverRow || !windRow || !windArrow || !windText) return;
    riverRow.hidden = !riverDirectionVisible || !frame?.river_segments?.length;
    windRow.hidden = !windDirectionVisible || !frame;
    status.hidden = riverRow.hidden && windRow.hidden;
    if (!frame || !windDirectionVisible) return;
    const vector = mapWindVector(frame.wind, frame.year_month);
    windArrow.hidden = !vector;
    if (!vector) {
      windText.textContent = `${frame.year_month}: chưa có dữ liệu hướng gió; tốc độ đơn lẻ không cho biết hướng.`;
      return;
    }
    const heading = (Math.atan2(vector.x, -vector.y) * 180 / Math.PI + 360) % 360;
    windArrow.style.transform = `rotate(${heading}deg)`;
    const directions = ['Bắc', 'Đông Bắc', 'Đông', 'Đông Nam', 'Nam', 'Tây Nam', 'Tây', 'Tây Bắc'];
    const toward = directions[Math.round(heading / 45) % 8];
    windText.textContent = vector.kind === 'SEASONAL_VECTOR_CLIMATOLOGY'
      ? `Gió ước tính theo mùa ${frame.year_month} đi về ${toward} · hướng điển hình từ ERA5 ${vector.referencePeriod}; không phải dự báo gió tháng này.`
      : `Gió vùng ${frame.year_month} đi về ${toward} · ${vector.speed.toFixed(1)} m/s · ERA5 tổng hợp tháng`;
  }
  map.on('movestart', () => particles.setMoving(true)); map.on('moveend', () => particles.setMoving(false));
  map.on('singleclick', event => {
    const waterwayPicker = document.getElementById('simulationWaterwayPicker'); if (waterwayPicker) waterwayPicker.value = '';
    const found = map.forEachFeatureAtPixel(event.pixel, f => f, { layerFilter: l => l === simulationGates, hitTolerance: 10 });
    if (found) { selectSimulationGate(found.get('gate').gate_code, false); return; }
    const branch = map.forEachFeatureAtPixel(event.pixel, f => f, { layerFilter: l => l === canalLayer, hitTolerance: 8 });
    if (branch?.get('gate_code')) { selectSimulationGate(branch.get('gate_code'), false); return; }
    const station = map.forEachFeatureAtPixel(event.pixel, f => f, { layerFilter: l => l === stations, hitTolerance: 7 });
    if (station) { selectSimulationGate(null, false); onSelect(station.get('site_code')); return; }
    selectSimulationGate(null, false);
    inspectedCoordinate = toLonLat(event.coordinate);
    window.dispatchEvent(new CustomEvent('workspace:field-point-selected', { detail: { coordinate: inspectedCoordinate } }));
    renderPointCard();
    document.getElementById('simulationGateCard')?.focus({ preventScroll: true });
  });
  const toolbar = target.parentElement.querySelector('.map-toolbar');
  const observer = new ResizeObserver(() => {
    if (toolbar) target.parentElement.style.setProperty('--map-header-height', `${toolbar.getBoundingClientRect().height}px`);
    if (ensureMapMounted()) particles.resize();
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
    const branch = map.forEachFeatureAtPixel(event.pixel, feature => feature, { layerFilter: layer => layer === canalLayer, hitTolerance: 8 });
    if (branch) {
      const gate = frame?.gates?.find(item => item.gate_code === branch.get('gate_code'));
      const inland = branch.get('branch_side') === 'beyond_gate';
      riverTooltip.hidden = false;
      riverTooltip.textContent = `${branch.get('name') || 'Kênh có cống'} · ${inland ? 'Sau cống: chưa có EC trong kênh' : gate ? `Từ sông tới cống: ${formatWater(gate.simulated_outside_ec_mS_m, displayUnit)} · ${gate.advisory_label_vi || gate.advisory_label || 'Mức cảnh báo theo ngưỡng EC'}` : 'Chưa có EC mô phỏng cho tháng này'}`;
    }
    if (gate) {
      const item = gate.get('gate');
      riverTooltip.hidden = false;
      riverTooltip.textContent = `${item.gate_name || item.gate_code} · EC mô phỏng ngoài cống ${frame?.year_month || ''}: ${formatWater(item.simulated_outside_ec_mS_m, displayUnit)} · ${item.advisory_label_vi || item.advisory_label || 'Mức cảnh báo EC chưa xác định'}`;
    }
    const station = map.forEachFeatureAtPixel(event.pixel, feature => feature, { layerFilter: layer => layer === stations, hitTolerance: 14 });
    if (station) {
      const name = `${station.get('site_code')} ${station.get('site_name')}`.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z]/gi,'').toLowerCase();
      const value = name.includes('tanchau') ? frame?.inputs?.tan_chau_ec_mS_m : name.includes('mythuan') ? frame?.inputs?.my_thuan_ec_mS_m : name.includes('mytho') ? frame?.inputs?.my_tho_ec_mS_m : null;
      riverTooltip.hidden = false; riverTooltip.textContent = `${station.get('site_name')} · Mẫu nguồn ${station.get('last_observed_date') || 'chưa rõ ngày'}: ${formatWater(station.get('latest_ec_mS_m'), displayUnit)}${value == null ? '' : ` · Đầu vào mô phỏng ${frame.year_month}: ${formatWater(value,displayUnit)}`}`;
    }
    const field = map.forEachFeatureAtPixel(event.pixel, feature => feature, { layerFilter: layer => layer === fieldLayer, hitTolerance: 9 });
    if (field) {
      riverTooltip.hidden = false;
      riverTooltip.textContent = `Số đo thực địa đã duyệt · ${field.get('observed_at')} · ${field.get('submitted_by')} · ${formatWater(field.get('ec_mS_m'), displayUnit)} · không phải dữ liệu MRC`;
    }
  }
  map.on('pointermove', inspectRiver); map.on('singleclick', inspectRiver);
  const clearGateHover = () => { if (hoveredGate) { hoveredGate = null; simulationGates.changed(); } };
  target.addEventListener('pointerleave', clearGateHover);
  map.getView().on('change:resolution', () => simulationGates.changed());
  function fitMap() {
    if (!ensureMapMounted()) return;
    const extent = riverSource.getFeatures().length ? riverSource.getExtent() : boundarySource.getFeatures().length ? boundarySource.getExtent() : source.getExtent();
    const size = map.getSize() || [1000, 900], mobile = size[0] < 700;
    const dockHeight = document.getElementById('simulationTimeline')?.getBoundingClientRect().height || 255;
    const desired = [50, mobile ? 35 : 60, dockHeight + 35, mobile ? 35 : 60];
    // Keep a usable viewport even when an embedding panel is shorter than its overlays.
    const scale = Math.min(1, Math.max(0, size[1] - 150) / (desired[0] + desired[2]));
    const padding = [desired[0] * scale, desired[1], desired[2] * scale, desired[3]];
    if (extent.every(Number.isFinite)) map.getView().fit(extent, { padding, maxZoom: 10, duration: 200 });
  }
  function renderPointCard() {
    const card = document.getElementById('simulationGateCard');
    if (!card || !inspectedCoordinate) return;
    card.setAttribute('aria-label', 'Tra cứu nguồn nước sông lân cận điểm chọn');
    inspectSource.clear(); card.replaceChildren(); card.hidden = false;
    const add = (tag, text, className) => { const element = document.createElement(tag); element.textContent = text; if (className) element.className = className; card.append(element); return element; };
    const close = add('button', '✕', 'simulation-gate-close');
    close.type = 'button'; close.setAttribute('aria-label', 'Đóng phiếu tra cứu nguồn nước');
    close.addEventListener('click', () => { inspectedCoordinate = null; inspectSource.clear(); card.hidden = true; target.focus({ preventScroll: true }); });
    add('span', 'TRA CỨU NGUỒN NƯỚC LÂN CẬN', 'tag');
    add('h3', `Điểm chọn ${inspectedCoordinate[1].toFixed(4)}°B, ${inspectedCoordinate[0].toFixed(4)}°Đ`, 'simulation-gate-heading');
    const context = inspectWaterPoint(inspectedCoordinate, frame, mapFeatures(collection, showUnconfirmed).features);
    if (!context) {
      add('p', 'Chưa có khung mô phỏng phù hợp. Hãy chọn tháng hoặc thử tải lại trên dòng thời gian.', 'inspect-context-note');
      return;
    }
    const { river, gate, station } = context, properties = river.segment.properties || {};
    const connectors = [river.coordinate, gate?.coordinate].filter(Boolean).map(coordinate => ({ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: [inspectedCoordinate, coordinate] } }));
    connectors.push({ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: inspectedCoordinate } });
    inspectSource.addFeatures(formatter.readFeatures({ type: 'FeatureCollection', features: connectors }, options));
    const water = add('div', '', 'inspect-water-highlight');
    const label = document.createElement('small'); label.textContent = `MÔ PHỎNG ĐOẠN SÔNG LÂN CẬN · ${context.yearMonth}`;
    const value = document.createElement('strong'); value.textContent = `EC ${formatWater(properties.ec_mS_m)}`;
    water.append(label, value);
    add('p', `Cách trục Sông Tiền ${river.distanceKm.toFixed(2)} km · Đoạn km ${properties.chainage_start_km ?? '—'}–${properties.chainage_end_km ?? '—'}`);
    if (gate) add('p', `Cống gần nhất: ${gate.item.gate_name || gate.item.name || gate.item.gate_code} · ${gate.distanceKm.toFixed(2)} km`);
    else add('p', 'Chưa có tọa độ cống để đối chiếu.');
    if (station) {
      const site = station.item.properties || {};
      add('p', `Trạm gần nhất: ${site.site_name || site.site_code} · ${station.distanceKm.toFixed(2)} km${site.assumed_crs ? ' · tọa độ tham khảo, CRS chưa xác nhận' : ''}`);
      add('p', `Quan trắc trạm ${site.last_observed_date || 'chưa rõ ngày'}: ${formatWater(site.latest_ec_mS_m)}. Đây là kỳ đo riêng của trạm.`, 'inspect-context-note');
    } else add('p', 'Chưa có trạm có tọa độ trong lớp đang hiển thị.');
    add('p', 'Giá trị thuộc đoạn sông lân cận, chưa phải số đo tại điểm chọn. Khoảng cách là đường chim bay; chưa xác lập kết nối thủy lực trạm–cống–ruộng.', 'inspect-context-note');
    add('p', 'EC ở đây được nội suy trên trục sông; kênh sau cống cần số đo riêng.', 'inspect-context-note');
    if (river.distanceKm > 12) add('p', 'Điểm chọn cách trục sông trên 12 km. Nước nội đồng còn phụ thuộc kênh nhánh và vận hành cống; cần đo trực tiếp tại vị trí sử dụng.', 'inspect-distance-warning');
    add('h4', 'Đối chiếu ngưỡng EC theo cây trồng');
    const crops = add('div', '', 'inspect-crop-list');
    for (const item of cropAdvisories(properties.ec_mS_m)) {
      const row = document.createElement('div'); row.className = `inspect-crop-item crop-${item.status}`;
      const heading = document.createElement('strong'); heading.textContent = item.label;
      const limit = document.createElement('small'); limit.textContent = `Ngưỡng kịch bản ${item.openBelowEc}/${item.closeAboveEc} mS/m`;
      const result = document.createElement('span'); result.textContent = item.text;
      row.append(heading, limit, result); crops.append(row);
    }
    add('p', 'Các ngưỡng là ví dụ để so sánh; cần đo kiểm tại chỗ và hướng dẫn chuyên môn trước khi tưới.', 'inspect-context-note');
    if (gate) {
      const actions = add('div', '', 'simulation-card-actions');
      const button = document.createElement('button'); button.type = 'button'; button.textContent = `Xem cống gần nhất: ${gate.item.gate_name || gate.item.name || gate.item.gate_code} →`;
      button.addEventListener('click', () => selectSimulationGate(gate.item.gate_code, true)); actions.append(button);
    }
  }
  function renderGateCard() {
    if (inspectedCoordinate) { renderPointCard(); return; }
    const card = document.getElementById('simulationGateCard');
    if (!card) return;
    card.setAttribute('aria-label', 'Thông tin nhánh có cống');
    card.replaceChildren();
    const gate = frame?.gates?.find(item => item.gate_code === selectedGate);
    card.hidden = !gate;
    if (card.hidden) return;
    const add = (tag, text, className) => { const node = document.createElement(tag); node.textContent = text; if (className) node.className = className; card.append(node); return node; };
    if (!gate) return;
    const close = add('button', '✕', 'simulation-gate-close'); close.type = 'button'; close.setAttribute('aria-label', 'Đóng thông tin nhánh'); close.addEventListener('click', () => {
      const code = selectedGate; selectSimulationGate(null, false);
      const picker = document.getElementById('simulationGatePicker');
      const profileButton = [...document.querySelectorAll('button[data-gate-code]')].find(item => item.dataset.gateCode === code && item.getClientRects().length);
      const returnTarget = picker?.getClientRects().length ? picker : profileButton || document.getElementById('simulationWaterwayPicker') || target;
      returnTarget?.focus();
    });
    add('h3', gate.gate_name || gate.name || gate.gate_code, 'simulation-gate-heading');
    const linkedWaterways = (corridor?.corridor?.features || []).filter(feature => gate.canal_ids?.includes(feature.properties?.id)).map(feature => feature.properties.name).filter(Boolean);
    add('p', `${gate.gate_code} · ${gate.waterway_name || gate.waterway || gate.river_name || linkedWaterways.join(', ') || 'Chưa xác minh tên thủy vực'}`);
    add('p', `Lý trình ${Number(gate.chainage_km).toFixed(1)} km · Cách trục sông ${Number(gate.distance_to_axis_km).toFixed(2)} km`);
    add('p', `Từ sông tới cống · tháng ${frame.year_month}: ${formatWater(gate.simulated_outside_ec_mS_m, displayUnit)}`);
    if (gate.canal_ids?.length) add('p', 'Tuyến màu chỉ kéo từ sông tới cống và dùng EC mô phỏng ngoài cống. Đoạn sau cống không tô màu vì chưa có EC nội kênh.');
    const advisory = add('p', gate.advisory_label_vi || gate.advisory_label || gate.advisory_code || gate.simulated_gate_state, 'simulation-advisory'); advisory.style.color = advisoryColor(gate);
    add('p', 'Giá trị EC được nội suy theo kịch bản ngoài cống; chưa có số đo trong kênh sau cống. Mức cảnh báo dựa trên EC, không suy ra trạng thái đóng hoặc mở thực tế.');
  }
  function selectSimulationGate(code, focus = true, interaction) {
    const waterwayPicker = document.getElementById('simulationWaterwayPicker'); if (waterwayPicker) waterwayPicker.value = '';
    inspectedCoordinate = null; inspectSource.clear();
    const gate = frame?.gates?.find(item => item.gate_code === code);
    if (selectedGate !== code) { intakeGate = null; particles.setIntakeGate(null); }
    selectedGate = gate?.gate_code || null; simulationGates.changed(); canalLayer.changed(); renderGateCard();
    const picker = document.getElementById('simulationGatePicker'); if (picker) picker.value = selectedGate || '';
    window.dispatchEvent(new CustomEvent('workspace:simulation-gate-selected',{detail:{gate_code:selectedGate}}));
    if (gate && focus && ensureMapMounted()) { map.getView().animate({center:fromLonLat(gate.coordinates || gate.geometry.coordinates), zoom:Math.max(10,map.getView().getZoom()), duration:450}); if (interaction !== 'hover') document.getElementById('simulationGateCard')?.focus(); }
  }
  function setSimulationCorridor(value) {
    corridor = value; canalSource.clear();
    const branches = (value?.corridor?.features || value?.features || []).filter(feature => feature.properties?.type !== 'MAIN_RIVER');
    const smooth = feature => ({ ...feature, geometry: { ...feature.geometry, coordinates: smoothCoordinates(feature.geometry.coordinates, riverInterpolation) } });
    const features = branches.filter(feature => feature.geometry?.type === 'LineString').map(smooth);
    const displayed = splitGatedWaterways(branches).map(smooth);
    canalSource.addFeatures(formatter.readFeatures({ type: 'FeatureCollection', features: displayed }, options));
    particles.setCanals(features);
    const picker = document.getElementById('simulationWaterwayPicker');
    if (picker) {
      picker.replaceChildren();
      const prompt = document.createElement('option'); prompt.value = ''; prompt.textContent = 'Chọn kênh / nhánh'; picker.append(prompt);
      const selectable = features.filter(feature => feature.properties?.gate_code &&
        Number.isInteger(feature.properties.gate_path_index) &&
        feature.properties.gate_path_index > 0 &&
        feature.properties.gate_path_index < feature.geometry.coordinates.length - 1);
      selectable.forEach((feature, index) => {
        const option = document.createElement('option'); option.value = String(index); option.textContent = feature.properties?.name || feature.properties?.id || `Kênh ${index + 1}`; picker.append(option);
      });
      picker.disabled = picker.options.length < 2;
      picker.onchange = () => {
        const selectedIndex = picker.value, selected = selectable[Number(selectedIndex)];
        if (!picker.value || !selected?.geometry?.coordinates?.length) return;
        selectSimulationGate(selected.properties?.gate_code, false);
        picker.value = selectedIndex;
        const coordinate = selected.geometry.coordinates[Math.floor(selected.geometry.coordinates.length / 2)].slice(0, 2);
        if (ensureMapMounted()) map.getView().animate({ center: fromLonLat(coordinate), zoom: Math.max(10, map.getView().getZoom()), duration: 450 });
        document.getElementById('simulationGateCard')?.focus({ preventScroll: true });
      };
    }
  }
  function setSimulationFrame(value) {
    frame = value; intakeGate = null; hoveredSegment = null; hoveredGate = null; updateRiverTooltip(); riverSource.clear(); simulationGateSource.clear(); isoSource.clear(); isoStyles.clear(); canalLayer.changed();
    updateDirectionStatus();
    const smoothed = smoothRiverSegments(frame?.river_segments || [], riverInterpolation);
    // Subdivide only display geometry: particles retain the original 35 continuous paths.
    const ribbon = riverRibbon(smoothed.segments, 8, [frame?.thresholds?.open_below_ec_ms_m, frame?.thresholds?.close_at_or_above_ec_ms_m]);
    ribbonStyles.clear();
    riverSource.addFeatures(formatter.readFeatures({ type: 'FeatureCollection', features: ribbon }, options));
    particles.setFrame(frame,smoothed.segments);
    for (const gate of frame?.gates || []) {
      if (!gate.canal_ids?.length) continue;
      const coordinates = gate.coordinates || gate.geometry?.coordinates;
      if (coordinates) simulationGateSource.addFeature(new Feature({ geometry: new Point(fromLonLat(coordinates)), gate }));
    }
    // The EC warning palette is driven by the selected thresholds. The former
    // 1/4 g/L isohaline markers are intentionally absent from this EC map.
    const picker = document.getElementById('simulationGatePicker');
    if (picker) {
      picker.disabled = !frame;
      picker.replaceChildren(); const prompt = document.createElement('option'); prompt.value = ''; prompt.textContent = 'Chọn cống để xem mô phỏng'; picker.append(prompt);
      for (const gate of frame?.gates || []) { const option = document.createElement('option'); option.value = gate.gate_code; option.textContent = `${gate.gate_name || gate.name || gate.gate_code} · ${gate.gate_code}`; picker.append(option); }
      picker.value = selectedGate || '';
      picker.onchange = () => selectSimulationGate(picker.value,true);
    }
    renderGateCard(); stations.changed();
    const waterwayPicker = document.getElementById('simulationWaterwayPicker');
    if (waterwayPicker) waterwayPicker.disabled = !frame?.gates?.length;
    if (frame && !initialSimulationFit && ensureMapMounted()) { fitMap(); initialSimulationFit = true; }
  }
  function setDisplayUnit(value) { displayUnit = value === 'salinity' ? 'salinity' : 'ec'; cache.clear(); stations.changed(); isoLayer.changed(); forecastLayer.changed(); renderGateCard(); updateRiverTooltip(); }
  function resumeVisibleMap() { if (!document.hidden && ensureMapMounted()) { map.render(); particles.resize(); particles.start(); } }
  document.addEventListener('visibilitychange', resumeVisibleMap);
  const listeners = [
    ['workspace:simulation-corridor', event => setSimulationCorridor(event.detail)],
    ['workspace:display-simulation-frame', event => setSimulationFrame(event.detail)],
    ['workspace:simulation-unit', event => setDisplayUnit(event.detail?.unit)],
    ['workspace:select-simulation-gate', event => selectSimulationGate(event.detail?.gate_code,event.detail?.focus !== false,event.detail?.interaction)],
    ['workspace:focus-coordinate', event => {
      const coordinate = event.detail?.coordinate;
      if (!validCoordinate(coordinate) || !ensureMapMounted()) return;
      const zoom = Number.isFinite(event.detail.zoom) ? Math.min(18, Math.max(5, event.detail.zoom)) : 10.8;
      map.getView().animate({ center: fromLonLat(coordinate), zoom, duration: 450 });
    }],
    ['workspace:approved-field-measurements', event => {
      fieldSource.clear();
      fieldSource.addFeatures(formatter.readFeatures(fieldMeasurementFeatureCollection(event.detail), options));
    }],
    ['workspace:viewchange', event => { if (event.detail?.view === 'observations') resumeVisibleMap(); else { particles.stop(); map.setTarget(undefined); } }],
  ];
  listeners.forEach(([name, handler]) => window.addEventListener(name, handler));
  // Particle engine schedules lightweight halo redraws; all streamlines use dedicated canvases.
  riverLayer.on('postrender', event => {
    if (!frame || disposed || document.hidden || document.getElementById('observations')?.hidden || globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
    const context = getVectorContext(event), time = event.frameState.time / 1000;
    const activeGates = simulationGates.getVisible() ? simulationGateSource.getFeatures().filter(feature => [selectedGate, hoveredGate].includes(feature.get('gate').gate_code)) : [];
    for (const feature of [...activeGates, ...isoSource.getFeatures()]) {
      const color = feature.get('gate') ? gateWarningColor(feature.get('gate')) : '#fbbf24';
      context.setStyle(new Style({ image: new Circle({ radius: 10 + (time % 1.8) * 4, stroke: new Stroke({ color: `${color}${Math.round((1 - (time % 1.8) / 1.8) * 160).toString(16).padStart(2, '0')}`, width: 1.5 }) }) })); context.drawGeometry(feature.getGeometry());
    }
  });
  function updateForecast() {
    forecastSource.clear();
    if (!validPrediction(forecastResult)) return false;
    const feature = collection.features.find(item => item.properties.site_code === forecastResult.site_code);
    if (!feature?.geometry) return false;
    forecastSource.addFeatures(formatter.readFeatures({ type: 'FeatureCollection', features: [{ type: 'Feature', geometry: feature.geometry, properties: { target_month: forecastResult.target_month, predicted_ec_mS_m: forecastResult.predicted_ec_mS_m } }] }, options));
    return true;
  }
  const update = () => { source.clear(); cache.clear(); source.addFeatures(formatter.readFeatures(mapFeatures(collection, showUnconfirmed), options)); updateForecast(); if (inspectedCoordinate) renderPointCard(); return source.getFeatures().length; };
  return {
    setSimulationCorridor,
    setSimulationFrame,
    setDisplayUnit,
    setRiverParticles(value) { riverDirectionVisible = Boolean(value); particles.setVisible({river:riverDirectionVisible}); updateDirectionStatus(); },
    setWindVisible(value) { windDirectionVisible = Boolean(value); particles.setVisible({wind:windDirectionVisible}); updateDirectionStatus(); },
    setMotionEnabled(value) { particles.setMotionEnabled(value); },
    setBaseTheme(theme) { const next = tileSource(theme); if (onTileError) next.on('tileloaderror', onTileError); base.setSource(next); particles.setTheme(theme); },
    refresh() { if (!ensureMapMounted()) return; particles.resize(); particles.start(); if (frame && !initialSimulationFit) { fitMap(); initialSimulationFit = true; } map.render(); },
    setStations(value) { collection = value; return update(); },
    setUnconfirmed(value) { showUnconfirmed = value; return update(); },
    setBoundaries(value) { boundarySource.clear(); boundarySource.addFeatures(formatter.readFeatures(value, options)); },
    setBoundaryVisible(value) { boundaries.setVisible(value); },
    setGateVisible(value) { gates.setVisible(value); candidates.setVisible(value); simulationGates.setVisible(value); if (!value) { clearGateHover(); selectSimulationGate(null,false); } },
    setMappedGateVisible(value) { simulationGates.setVisible(value); if (!value) { clearGateHover(); selectSimulationGate(null, false); } },
    refreshComparison() { cache.clear(); stations.changed(); },
    setForecast(value) { forecastResult = validPrediction(value) ? value : null; return updateForecast(); },
    setCandidates(gate, items = []) {
      candidateSource.clear();
      const geometry = gate?.geometry || gate;
      if (geometry?.type !== 'Point') return;
      const features = items.filter(item => item.geometry?.type === 'Point').map(item => ({ type: 'Feature', properties: { site_code: item.site_code }, geometry: { type: 'LineString', coordinates: [geometry.coordinates, item.geometry.coordinates] } }));
      candidateSource.addFeatures(formatter.readFeatures({ type: 'FeatureCollection', features }, options));
    },
    setGates(items) { gateSource.clear(); gateSource.addFeatures(formatter.readFeatures(databaseGateFeatureCollection(items), options)); },
    select(code) { selected = code; stations.changed(); },
    fit: fitMap,
    setBase(value) { base.setVisible(value); },
    destroy() { disposed = true; particles.destroy(); canvases.forEach(canvas => canvas.remove()); target.removeEventListener('pointerleave', clearGateHover); document.removeEventListener('visibilitychange', resumeVisibleMap); riverTooltip.remove(); for (const id of ['simulationGatePicker', 'simulationWaterwayPicker']) { const picker = document.getElementById(id); if (picker) picker.onchange = null; } listeners.forEach(([name, handler]) => window.removeEventListener(name, handler)); observer.disconnect(); map.setTarget(undefined); },
  };
}

export function databaseGateFeatureCollection(items) {
  return {
    type: 'FeatureCollection',
    features: items.filter(item => item.geometry).map(({ geometry, ...properties }) => ({
      type: 'Feature', geometry, properties,
    })),
  };
}

export function fieldMeasurementFeatureCollection(items) {
  return { type: 'FeatureCollection', features: (items || []).filter(item =>
    item.status === 'APPROVED' && Number.isFinite(item.longitude) && Number.isFinite(item.latitude))
    .map(item => ({ type: 'Feature', geometry: { type: 'Point', coordinates: [item.longitude, item.latitude] },
      properties: { measurement_id: item.measurement_id, ec_mS_m: item.ec_mS_m,
        observed_at: item.observed_at, submitted_by: item.submitted_by } })) };
}
