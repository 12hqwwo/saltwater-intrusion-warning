import { createRequestGate } from '../api.js';
import { workspaceAPI } from '../shared/workspace-api.js';
import { $, node, num } from '../shared/ui.js';
import { formatWater } from '../shared/simulation-display.js';
import { validMonth, validEc } from '../shared/forecast-contract.js';
import { resolveValidTimelineMonth } from '../shared/timeline-months.js';
export { resolveValidTimelineMonth } from '../shared/timeline-months.js';

import { ADVISORY_PRESETS } from '../shared/water-advisory.js';
export { ADVISORY_PRESETS };

export function simulationInputLabel(item) {
  if (item?.data_regime === 'OBSERVED_MRC') return `Mẫu nguồn MRC${item.imputed ? ' + nội suy thời gian' : ''}`;
  return item?.data_regime === 'ML_FORECAST_ERA5' ? 'Ước tính hồi cứu · khí tượng ERA5' : 'Nguồn đầu vào chưa xác định';
}

export function validateThresholds(opening, closing) {
  if (opening === '' || closing === '') throw new Error('Nhập đủ hai ngưỡng EC.');
  const open_below_ec = Number(opening), close_above_ec = Number(closing);
  if (!Number.isFinite(open_below_ec) || !Number.isFinite(close_above_ec) ||
      open_below_ec < 0 || close_above_ec <= open_below_ec) {
    throw new Error('Ngưỡng phải hữu hạn, không âm; ngưỡng lấy nước phải nhỏ hơn ngưỡng ngăn mặn.');
  }
  return { open_below_ec, close_above_ec };
}

export function createSimulationFrameLoader({ api = workspaceAPI, onFrame, onError, onLoading, onClamp, availableMonths } = {}) {
  const requests = createRequestGate();
  return {
    cancel() { requests.next(); },
    setAvailableMonths(months) { availableMonths = [...months]; requests.next(); },
    async load(year_month, thresholds) {
      const req = requests.next();
      if (availableMonths !== undefined) {
        const resolved = resolveValidTimelineMonth(year_month, availableMonths);
        if (!resolved.month) { onError?.(new Error('Chưa có tháng Timeline có frame dữ liệu.')); return null; }
        if (resolved.clamped) onClamp?.({ requestedMonth: year_month, ...resolved });
        year_month = resolved.month;
      }
      onLoading?.({ year_month, thresholds });
      try {
        const query = new URLSearchParams({ year_month, ...thresholds });
        const frame = await api(`/simulation/frame?${query}`, req);
        if (!req.isCurrent()) return null;
        if (frame.year_month !== year_month || frame.simulation_layer !== true ||
            !Array.isArray(frame.river_segments) || !Array.isArray(frame.gates) ||
            (frame.inputs && frame.inputs.year_month !== year_month) ||
            (Array.isArray(frame.gates) && frame.gates.some(gate => !gate?.gate_code || !validEc(gate.simulated_outside_ec_mS_m))) ||
            frame.thresholds?.open_below_ec_ms_m !== thresholds.open_below_ec ||
            frame.thresholds?.close_at_or_above_ec_ms_m !== thresholds.close_above_ec) {
          throw new Error('Khung mô phỏng không khớp tháng hoặc ngưỡng đang chọn.');
        }
        onFrame?.(frame);
        return frame;
      } catch (error) {
        if (req.isCurrent() && error.name !== 'AbortError') onError?.(error);
        return null;
      }
    },
  };
}

export function renderSpatialSummary(frame) {
  const box = $('simulationSpatialSummary');
  if (!box) return;
  box.replaceChildren();
  box.hidden = !frame;
  if (!frame) return;
  const counts = new Map();
  for (const gate of frame.gates || []) counts.set(gate.simulated_gate_state, (counts.get(gate.simulated_gate_state) || 0) + 1);
  const group = node('div', undefined, 'spatial-kpi-group');
  group.append(node('strong', `Mô phỏng · ${(frame.gates || []).length} cống`));
  for (const [code, label, color] of [
    ['OPEN_INTAKE', 'thuận lợi theo ngưỡng', 'safe'],
    ['CAUTION_TRANSITION', 'cần đo kiểm', 'caution'],
    ['CLOSED_SALINITY_BARRIER', 'ngăn mặn', 'risk'],
  ]) {
    group.append(node('span', `${counts.get(code) || 0} ${label}`, `spatial-pill pill-${color}`));
    counts.delete(code);
  }
  const unknown = [...counts.values()].reduce((sum, count) => sum + count, 0);
  if (unknown) group.append(node('span', `${unknown} chưa xác định`, 'spatial-pill'));
  const fronts = node('div', undefined, 'spatial-kpi-group');
  for (const salinity of [1, 4]) {
    const boundary = frame.isohaline_boundaries?.find(item => item.salinity_g_l === salinity);
    const label = `Ranh mô phỏng ${salinity} g/L`;
    const coord = boundary?.coordinate;
    if (boundary?.status === 'WITHIN_CORRIDOR' && Array.isArray(coord) && coord.length === 2 &&
        coord.every(Number.isFinite) && Math.abs(coord[0]) <= 180 && Math.abs(coord[1]) <= 90 &&
        Number.isFinite(boundary.intrusion_distance_km)) {
      const distance = boundary.intrusion_distance_km.toLocaleString('vi-VN', { maximumFractionDigits: 1 });
      const button = node('button', `${label}: ${distance} km từ biển ↗`, `spatial-front-btn front-${salinity === 4 ? 'high' : 'low'}`);
      button.type = 'button';
      button.addEventListener('click', () => window.dispatchEvent(new CustomEvent('workspace:focus-coordinate', {
        detail: { coordinate: [...coord], zoom: 10.8 },
      })));
      fronts.append(button);
    } else {
      const description = boundary?.status === 'NOT_REACHED_AT_ESTUARY' ? 'chưa đạt ngưỡng tại cửa sông'
        : boundary?.status === 'ENTIRE_CORRIDOR_ABOVE_THRESHOLD' ? 'toàn tuyến vượt ngưỡng' : 'chưa có vị trí hợp lệ';
      fronts.append(node('span', `${label}: ${description}`, 'spatial-pill'));
    }
  }
  box.append(group, fronts, node('small', `${frame.inputs ? `Đầu vào ${frame.year_month}: ${simulationInputLabel(frame.inputs)} · ${frame.interpolation_mode === 'PIECEWISE_3_STATION' ? 'Nội suy 3 trạm, 2 chặng qua Mỹ Thuận' : 'Nội suy 2 trạm · khuyết mẫu Mỹ Thuận'}. ` : ''}Ranh mặn quy đổi gần đúng từ EC; bấm bản đồ để tra cứu nguồn nước lân cận.`, 'spatial-click-hint'));
}

export function createTimelineScrubber() {
  const host = $('simulationTimeline');
  const state = { items: [], index: 0, unit: 'ec', thresholds: { ...ADVISORY_PRESETS.citrus }, playing: false, speed: 1 };
  const initialRequests = createRequestGate();
  let playbackTimer, scrubTimer, thresholdTimer, playbackGeneration = 0, pendingMonth = null, clampNotice = '';
  let forecastContext = null, statusMessage = '', statusError = false;
  host.innerHTML = `<div id="simulationSpatialSummary" class="timeline-spatial-kpis" aria-live="polite" hidden></div><div id="simulationProfilePanel" hidden><div id="simulationRiverProfile" hidden></div></div><div class="timeline-banner"><div class="timeline-month"><small>THÁNG ĐANG XEM</small><strong id="simulationMonth">—</strong><span id="simulationRegime" class="timeline-regime">Đang đọc dữ liệu</span></div><div class="timeline-stations"><div><small>THƯỢNG LƯU · TÂN CHÂU</small><strong id="simulationTanChau">—</strong></div><div><small>TRUNG LƯU · MỸ THUẬN</small><strong id="simulationMyThuan">—</strong></div><div><small>HẠ LƯU · MỸ THO</small><strong id="simulationMyTho">—</strong></div></div><p id="simulationWeather" class="timeline-weather"></p></div>
    <div class="timeline-controls"><button id="simulationPlay" type="button" disabled>▶ Phát chu kỳ</button><label class="timeline-speed">Tốc độ<select id="simulationSpeed"><option value="1">1x</option><option value="2">2x</option><option value="4">4x</option></select></label><label class="timeline-month-picker">Chọn tháng<select id="simulationMonthPicker" aria-label="Chọn tháng có frame dữ liệu" disabled></select></label><input id="simulationSlider" type="range" min="0" max="0" value="0" step="1" disabled aria-label="Tháng mô phỏng" aria-valuetext="Đang tải"><button id="simulationRetry" type="button" hidden>Thử lại</button></div>
    <div class="timeline-axis"><span id="simulationStart">1985-06</span><span>QUAN TRẮC MRC <i></i> KHÍ TƯỢNG &amp; ML</span><span id="simulationEnd">2026-08</span></div>
    <div class="timeline-secondary"><div class="profile-dock-heading"><button id="simulationProfileToggle" type="button" aria-expanded="false" aria-controls="simulationProfilePanel">📈 Hiện cắt dọc sông</button><span class="profile-dock-title">Sơ đồ cắt dọc Sông Tiền &amp; Chuỗi 27 cống · km 0 → km 175</span><label class="profile-gate-picker"><span class="visually-hidden">Xem mô phỏng tại cống</span><select id="simulationGatePicker" aria-label="Xem mô phỏng tại cống" disabled><option value="">Đang tải danh mục cống…</option></select></label></div><div id="simulationJumps" class="timeline-jumps" aria-label="Chọn nhanh giai đoạn"></div></div><p id="simulationStatus" class="timeline-status" role="status">Đang tải trục sông và dòng thời gian…</p>`;
  host.dataset.profileExpanded = 'false';
  $('simulationProfileToggle').addEventListener('click', () => {
    const expanded = $('simulationProfilePanel').hidden;
    $('simulationProfilePanel').hidden = !expanded;
    host.dataset.profileExpanded = String(expanded);
    $('simulationProfileToggle').setAttribute('aria-expanded', String(expanded));
    $('simulationProfileToggle').textContent = expanded ? '📈 Ẩn cắt dọc sông' : '📈 Hiện cắt dọc sông';
    emit('workspace:simulation-profile-toggle', { expanded });
  });
  const slider = $('simulationSlider'), play = $('simulationPlay');
  function emit(name, detail) { window.dispatchEvent(new CustomEvent(name, { detail })); }
  function stop() {
    playbackGeneration += 1;
    state.playing = false;
    clearTimeout(playbackTimer);
    play.textContent = '▶ Phát chu kỳ';
    play.setAttribute('aria-pressed', 'false');
  }
  function status(text, error = false) {
    statusMessage = text; statusError = error;
    renderStatus();
  }
  function renderStatus() {
    const text = forecastContext ? `Đang xem lớp sông dự báo ${forecastContext.targetMonth} · Tân Châu ${num(forecastContext.tanchauEc)} → Mỹ Thuận ${num(forecastContext.mythuanEc)} → Mỹ Tho ${num(forecastContext.mythoEc)} mS/m · nội suy 3 trạm; cống và ranh mặn của Timeline nền tạm ẩn.` : statusMessage;
    $('simulationStatus').textContent = clampNotice ? `${clampNotice} ${text}` : text;
    $('simulationStatus').title = $('simulationStatus').textContent;
    $('simulationStatus').classList.toggle('is-error', statusError);
  }
  window.addEventListener('workspace:active-forecast-context', event => {
    forecastContext = event.detail; renderStatus();
  });
  function renderBanner() {
    const item = state.items[state.index];
    if (!item) return;
    slider.value = state.index;
    slider.setAttribute('aria-valuetext', item.year_month);
    slider.style.setProperty('--progress', `${state.index / Math.max(1, state.items.length - 1) * 100}%`);
    $('simulationMonth').textContent = item.year_month;
    $('simulationMonthPicker').value = item.year_month;
    const regime = resolveValidTimelineMonth(item.year_month, [item.year_month]);
    const observed = regime.regimeLabel === 'HISTORICAL_MRC_OBSERVED';
    $('simulationRegime').textContent = `${regime.regimeDescription} · ${item.interpolation_mode === 'PIECEWISE_3_STATION' ? 'Nội suy 3 trạm, 2 chặng' : 'Nội suy 2 trạm: khuyết mẫu Mỹ Thuận'}`;
    $('simulationRegime').dataset.regime = observed ? 'observed' : 'estimate';
    $('simulationRegime').title = observed ? 'Tổng hợp các mẫu nguồn sẵn có, giữ cờ O/E và chất lượng; không đại diện chuỗi đo liên tục cả tháng. Đoạn sông và cống là mô phỏng.' : 'Ước tính hồi cứu lưu trữ; chưa phải dự báo vận hành được kiểm chứng.';
    $('simulationTanChau').textContent = formatWater(item.tan_chau_ec_mS_m, state.unit, item.tan_chau_salinity_g_l);
    $('simulationMyTho').textContent = formatWater(item.my_tho_ec_mS_m, state.unit, item.my_tho_salinity_g_l);
    $('simulationMyThuan').textContent = Number.isFinite(item.my_thuan_ec_mS_m) ? formatWater(item.my_thuan_ec_mS_m, state.unit) : 'Khuyết mẫu · nội suy 2 trạm';
    const direction = item.wind?.direction_from_degrees;
    $('simulationWeather').textContent = `ERA5 · Mưa ${num(item.rainfall_mm)} mm · ${num(item.temperature_degC)} °C · Gió ${num(item.wind_speed_ms)} m/s${Number.isFinite(direction) ? ` · từ ${Math.round(direction)}°` : ' · chưa có hướng'}${item.imputed ? ' · EC có nội suy thời gian' : ''}`;
  }
  const loader = createSimulationFrameLoader({
    availableMonths: [],
    onLoading(detail) {
      renderSpatialSummary(null);
      host.dataset.loading = 'true';
      status(`Đang tải kịch bản tháng ${detail.year_month}…`);
      $('simulationRetry').hidden = true;
      emit('workspace:simulation-loading', detail);
    },
    onFrame(frame) {
      renderSpatialSummary(frame);
      host.dataset.loading = 'false';
      emit('workspace:simulation-frame', frame);
      const colors = frame.gates.reduce((count, gate) => {
        count[gate.advisory_code] = (count[gate.advisory_code] || 0) + 1;
        return count;
      }, {});
      status(`${frame.gates.length} cống mô phỏng · ${colors.ADVISORY_SAFE_INTAKE || 0} dưới ngưỡng lấy · ${colors.ADVISORY_CHECK_ONSITE || 0} chuyển tiếp · ${colors.ADVISORY_HIGH_SALINITY_RISK || 0} đạt ngưỡng ngừng lấy · Cần đo thực tế tại cống`);
    },
    onError(error) {
      renderSpatialSummary(null);
      host.dataset.loading = 'false';
      stop();
      status(error.message, true);
      $('simulationRetry').hidden = false;
    },
  });
  function requestFrame() {
    if (!state.items.length) return Promise.resolve(null);
    clearTimeout(scrubTimer);
    // Every entry point (jump, play, retry or scrub) must use the visible inputs.
    // An invalid edit must never revive a frame with previously valid thresholds.
    try {
      state.thresholds = validateThresholds($('simulationOpenBelow').value, $('simulationCloseAbove').value);
    } catch (error) {
      loader.cancel();
      renderSpatialSummary(null);
      emit('workspace:simulation-loading', { year_month: state.items[state.index].year_month, thresholds: null });
      host.dataset.loading = 'false';
      stop();
      status(error.message, true);
      return Promise.resolve(null);
    }
    return loader.load(state.items[state.index].year_month, { ...state.thresholds });
  }
  function chooseIndex(index, debounce = false, source = 'user') {
    if (!state.items.length) return Promise.resolve(null);
    state.index = Number.isFinite(index) ? Math.max(0, Math.min(state.items.length - 1, Math.trunc(index))) : 0;
    emit('workspace:simulation-selection', { year_month: state.items[state.index].year_month, source });
    renderBanner();
    loader.cancel();
    renderSpatialSummary(null);
    emit('workspace:simulation-loading', { year_month: state.items[state.index]?.year_month, thresholds: state.thresholds });
    if (debounce) {
      clearTimeout(scrubTimer);
      status(`Đang chọn tháng ${state.items[state.index]?.year_month}…`);
      host.dataset.loading = 'true';
      scrubTimer = setTimeout(requestFrame, 120);
      return Promise.resolve(null);
    }
    return requestFrame();
  }
  function resolveMonth(month) {
    const resolved = resolveValidTimelineMonth(month, state.items.map(item => item.year_month));
    clampNotice = resolved.clamped ? `Tháng ${month || 'được yêu cầu'} không có frame dữ liệu; đã chuyển về ${resolved.month}.` : '';
    return state.items.findIndex(item => item.year_month === resolved.month);
  }
  function selectMonth(month, { source = 'user' } = {}) {
    stop(); clearTimeout(scrubTimer); clearTimeout(thresholdTimer);
    if (!state.items.length) { pendingMonth = month; return Promise.resolve(null); }
    pendingMonth = null;
    return chooseIndex(resolveMonth(month), false, source);
  }
  function selectScenario({ month, preset } = {}) {
    const thresholds = ADVISORY_PRESETS[preset];
    if (thresholds) {
      state.thresholds = { ...thresholds };
      $('simulationThresholdPreset').value = preset;
      $('simulationOpenBelow').value = thresholds.open_below_ec;
      $('simulationCloseAbove').value = thresholds.close_above_ec;
    }
    if (month) return selectMonth(month);
    stop(); clearTimeout(scrubTimer); clearTimeout(thresholdTimer);
    return requestFrame();
  }
  window.addEventListener('workspace:simulation-scenario', event => selectScenario(event.detail));
  async function tick(generation) {
    if (!state.playing || generation !== playbackGeneration || document.hidden) return;
    await chooseIndex((state.index + 1) % state.items.length);
    if (state.playing && generation === playbackGeneration) playbackTimer = setTimeout(() => tick(generation), 1500 / state.speed);
  }
  play.addEventListener('click', () => {
    if (state.playing) return stop();
    clampNotice = '';
    state.playing = true;
    play.textContent = '⏸ Tạm dừng';
    play.setAttribute('aria-pressed', 'true');
    tick(++playbackGeneration);
  });
  $('simulationSpeed').addEventListener('change', event => { state.speed = Number(event.target.value); });
  slider.addEventListener('input', () => { stop(); clampNotice = ''; chooseIndex(Number(slider.value), true); });
  slider.addEventListener('change', () => { stop(); clampNotice = ''; chooseIndex(Number(slider.value)); });
  $('simulationMonthPicker').addEventListener('change', event => selectMonth(event.target.value));
  $('simulationRetry').addEventListener('click', () => state.items.length ? requestFrame() : load());
  function applyThresholds() {
    clearTimeout(thresholdTimer);
    stop();
    requestFrame();
  }
  $('simulationThresholdPreset').addEventListener('change', event => {
    const preset = ADVISORY_PRESETS[event.target.value];
    if (!preset) { $('simulationOpenBelow').focus(); return; }
    $('simulationOpenBelow').value = preset.open_below_ec;
    $('simulationCloseAbove').value = preset.close_above_ec;
    applyThresholds();
  });
  $('simulationThresholdForm').addEventListener('submit', event => { event.preventDefault(); clearTimeout(thresholdTimer); applyThresholds(); });
  for (const id of ['simulationOpenBelow', 'simulationCloseAbove']) $(id).addEventListener('input', () => {
    $('simulationThresholdPreset').value = 'custom';
    stop();
    clearTimeout(scrubTimer);
    loader.cancel();
    renderSpatialSummary(null);
    emit('workspace:simulation-loading', { year_month: state.items[state.index]?.year_month, thresholds: null });
    status('Đang nhập ngưỡng kịch bản…');
    clearTimeout(thresholdTimer);
    thresholdTimer = setTimeout(applyThresholds, 500);
  });
  for (const input of document.querySelectorAll('input[name="simulationUnit"]')) input.addEventListener('change', () => {
    if (!input.checked) return;
    state.unit = input.value;
    $('simulationConversionNote').hidden = state.unit !== 'salinity';
    renderBanner();
    emit('workspace:simulation-unit', { unit: state.unit });
  });
  window.addEventListener('workspace:viewchange', event => { if (event.detail.view !== 'observations') stop(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  async function load() {
    stop();
    clearTimeout(scrubTimer); clearTimeout(thresholdTimer); loader.cancel();
    if (!pendingMonth && state.items.length) pendingMonth = state.items[state.index]?.year_month;
    state.items = [];
    loader.setAvailableMonths([]);
    $('simulationMonthPicker').replaceChildren();
    $('simulationMonthPicker').disabled = true;
    renderSpatialSummary(null);
    emit('workspace:simulation-loading', { year_month: pendingMonth, thresholds: null });
    host.dataset.loading = 'true';
    for (const id of ['simulationMonth', 'simulationTanChau', 'simulationMyThuan', 'simulationMyTho']) $(id).textContent = '—';
    $('simulationRegime').textContent = 'Đang tải đầu vào mô phỏng';
    $('simulationWeather').textContent = '';
    $('simulationJumps').replaceChildren();
    const req = initialRequests.next();
    play.disabled = slider.disabled = true;
    $('simulationRetry').hidden = true;
    status('Đang tải trục sông và dòng thời gian…');
    try {
      const [corridor, timeline] = await Promise.all([
        workspaceAPI('/simulation/corridor', req), workspaceAPI('/simulation/timeline', req),
      ]);
      if (!req.isCurrent()) return;
      if (!Array.isArray(timeline.items) || !timeline.items.length || !Array.isArray(corridor.gates) || !corridor.corridor ||
          timeline.items.some((item, index) => !validMonth(item.year_month) || (index && item.year_month <= timeline.items[index - 1].year_month))) throw new Error('Chưa có dữ liệu không gian / thời gian hợp lệ.');
      state.items = timeline.items;
      loader.setAvailableMonths(state.items.map(item => item.year_month));
      state.index = pendingMonth ? resolveMonth(pendingMonth) : state.items.length - 1;
      pendingMonth = null;
      for (const item of state.items) {
        const option = node('option', item.year_month); option.value = item.year_month;
        $('simulationMonthPicker').append(option);
      }
      $('simulationMonthPicker').disabled = false;
      slider.max = state.items.length - 1;
      $('simulationStart').textContent = state.items[0].year_month;
      $('simulationEnd').textContent = state.items.at(-1).year_month;
      emit('workspace:simulation-corridor', corridor);
      $('simulationJumps').replaceChildren();
      const jumps = [['2016-03', 'Đỉnh mặn lịch sử 03/2016'], ['2022-10', 'Mùa lũ 10/2022'], ['2024-04', 'Mùa khô 04/2024'], [state.items.at(-1).year_month, `Mới nhất ${state.items.at(-1).year_month.slice(5)}/${state.items.at(-1).year_month.slice(0, 4)}`]];
      for (const [month, label] of jumps) {
        const index = state.items.findIndex(item => item.year_month === month);
        const button = node('button', label);
        button.type = 'button';
        button.disabled = index < 0;
        button.addEventListener('click', () => { stop(); clampNotice = ''; chooseIndex(index); });
        $('simulationJumps').append(button);
      }
      play.disabled = slider.disabled = false;
      renderBanner();
      await requestFrame();
    } catch (error) {
      if (!req.isCurrent()) return;
      host.dataset.loading = 'false';
      status(error.message, true);
      $('simulationRetry').hidden = false;
    }
  }
  return { load, stop, selectMonth, selectScenario };
}
