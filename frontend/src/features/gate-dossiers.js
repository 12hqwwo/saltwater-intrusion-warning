import { $, num, node } from '../shared/ui.js';
import { workspaceAPI as api } from '../shared/workspace-api.js';
import { createRequestGate } from '../api.js';
import { loadMultivariateForecastContext } from '../shared/forecast-map-overlay.js';
import { createSpatialGateDraft } from './gate-simulation-draft.js';
import { createGateIntakeScreening } from './gate-intake-screening.js';

export function createGateDossiers(map) {
  const screening = createGateIntakeScreening($('gateIntakeScreeningHost'));
  const candidateRequests = createRequestGate(), databaseRequests = createRequestGate(), forecastRequests = createRequestGate();
  let gates = [], catalog = [], spatialGates = [], databaseGates = [];

  function rebuildOptions(preferred = $('gateSelect').value) {
    const merged = new Map();
    for (const gate of [...catalog, ...databaseGates, ...spatialGates]) {
      if (!gate?.gate_code) continue;
      merged.set(gate.gate_code, { ...merged.get(gate.gate_code), ...gate });
    }
    gates = [...merged.values()];
    $('gateSelect').replaceChildren();
    for (const gate of gates) {
      const suffix = gate.database_catalog ? ' · PostgreSQL' : gate.spatial_catalog ? ' · GIS' : '';
      const option = node('option', `${gate.gate_name || gate.gate_code}${suffix}`);
      option.value = gate.gate_code;
      $('gateSelect').append(option);
    }
    $('gateSelect').value = gates.some(gate => gate.gate_code === preferred) ? preferred : gates[0]?.gate_code || '';
  }

  async function selectGate() {
    const req = candidateRequests.next();
    const code = $('gateSelect').value, gate = gates.find(item => item.gate_code === code);
    map.setCandidates?.(null, []);
    $('databaseGateStatus').textContent = '';
    $('gateInfo').textContent = '';
    screening.setGate(gate || null);
    if (!gate) return;
    const description = [`Mã ${code}`];
    if (gate.admin_label_source) description.push(gate.admin_label_source);
    if (Number.isFinite(gate.service_area_ha)) description.push(`Diện tích phục vụ ${num(gate.service_area_ha)} ha`);
    if (Number.isFinite(gate.opening_width_m)) description.push(`Khẩu độ ${num(gate.opening_width_m)} m`);
    if (gate.waterway_name) description.push(gate.waterway_name);
    if (Number.isFinite(gate.chainage_km)) description.push(`Lý trình ${num(gate.chainage_km)} km`);
    if (gate.source_locator) description.push(gate.source_locator);
    $('gateInfo').textContent = description.join(' · ');
    if (!gate.database_catalog) return;
    try {
      const candidates = await api(`/database-gates/${encodeURIComponent(code)}/candidate-stations`, req);
      if (!req.isCurrent()) return;
      if (!Array.isArray(candidates.items)) throw new Error('Danh sách trạm ứng viên không hợp lệ.');
      map.setCandidates?.(candidates.gate_geometry, candidates.items);
      $('databaseGateStatus').textContent = candidates.items.length
        ? `Trạm ứng viên theo khoảng cách: ${candidates.items.map(row => `${row.site_name} (${num(row.distance_m / 1000)} km)`).join('; ')}. ${candidates.note || ''}`
        : 'Không có trạm trong bán kính 50 km. Chưa xác lập trạm đại diện cho cống.';
    } catch (error) {
      if (req.isCurrent() && error.name !== 'AbortError') $('databaseGateStatus').textContent = error.message;
    }
  }

  function onSpatialFrame(event) {
    spatialGates = (Array.isArray(event.detail?.gates) ? event.detail.gates : []).map(gate => ({ ...gate, spatial_catalog: true }));
    rebuildOptions();
    screening.setGate(gates.find(gate => gate.gate_code === $('gateSelect').value) || null);
  }
  function onMapGate(event) {
    if (!createSpatialGateDraft(event.detail)) return;
    const gate = { ...event.detail.gate, spatial_catalog: true };
    const index = spatialGates.findIndex(item => item.gate_code === gate.gate_code);
    if (index < 0) spatialGates.push(gate); else spatialGates[index] = gate;
    rebuildOptions(gate.gate_code);
    selectGate();
    location.hash = 'gates';
  }
  async function onForecast(event) {
    if (event.detail?.kind === 'SPATIAL_SIMULATION') return;
    const req = forecastRequests.next();
    const status = $('gateContextStatus');
    status.textContent = 'Đang lấy ngữ cảnh dự báo đa biến tại ba trạm…';
    try {
      const context = await loadMultivariateForecastContext(event.detail, api, req);
      if (!req.isCurrent()) return;
      screening.setForecastContext(context);
      status.textContent = `Đã dùng dự báo đa biến tháng ${context.targetMonth} làm ngữ cảnh kiểm tra cống. Nhập số đo hiện trường ở Phần B để đánh giá.`;
    } catch (error) {
      if (req.isCurrent() && error.name !== 'AbortError') status.textContent = `Chưa áp dụng được dự báo: ${error.message}`;
    }
  }
  function onActiveForecast() {
    forecastRequests.next();
    $('gateContextStatus').textContent = '';
  }
  async function loadDatabaseGates() {
    const req = databaseRequests.next();
    $('loadDatabaseGates').disabled = true;
    $('databaseGateStatus').textContent = 'Đang đọc danh mục trong PostgreSQL…';
    try {
      const response = await api('/database-gates', req);
      if (!req.isCurrent()) return;
      if (!Array.isArray(response.items)) throw new Error('Danh mục cống không hợp lệ.');
      databaseGates = response.items.map(gate => ({ ...gate, database_catalog: true }));
      rebuildOptions();
      map.setGates(response.items);
      $('databaseGateList').replaceChildren();
      for (const gate of databaseGates) $('databaseGateList').append(node('span', `${gate.gate_name || gate.gate_code} · ${gate.gate_code}`, 'database-gate'));
      await selectGate();
      if (req.isCurrent()) $('databaseGateStatus').textContent = `${response.items.length} cống trong database. ${response.note || ''}`;
    } catch (error) {
      if (req.isCurrent() && error.name !== 'AbortError') $('databaseGateStatus').textContent = error.message;
    } finally {
      if (req.isCurrent()) $('loadDatabaseGates').disabled = false;
    }
  }

  const listeners = [['workspace:simulation-frame', onSpatialFrame], ['workspace:apply-simulation-gate', onMapGate],
    ['workspace:apply-forecast-to-gate', onForecast], ['workspace:active-forecast-context', onActiveForecast]];
  listeners.forEach(([name, listener]) => window.addEventListener(name, listener));
  $('gateSelect').addEventListener('change', selectGate);
  $('loadDatabaseGates').addEventListener('click', loadDatabaseGates);
  return {
    async load(items) {
      catalog = Array.isArray(items) ? items.map(gate => ({ ...gate })) : [];
      rebuildOptions();
      await selectGate();
    },
    destroy() {
      candidateRequests.next(); databaseRequests.next(); forecastRequests.next(); screening.destroy();
      listeners.forEach(([name, listener]) => window.removeEventListener(name, listener));
      $('gateSelect').removeEventListener('change', selectGate);
      $('loadDatabaseGates').removeEventListener('click', loadDatabaseGates);
    },
  };
}
