import { createRequestGate } from '../api.js';
import { workspaceAPI } from '../shared/workspace-api.js';
import { $, node, num } from '../shared/ui.js';
import { formatWater } from '../shared/simulation-display.js';

export const ADVISORY_PRESETS = {
  durian: { open_below_ec: 50, close_above_ec: 80 },
  citrus: { open_below_ec: 100, close_above_ec: 150 },
  rice: { open_below_ec: 120, close_above_ec: 200 },
};

export function validateThresholds(opening, closing) {
  if (opening === '' || closing === '') throw new Error('Nhập đủ hai ngưỡng EC.');
  const open_below_ec = Number(opening), close_above_ec = Number(closing);
  if (!Number.isFinite(open_below_ec) || !Number.isFinite(close_above_ec) ||
      open_below_ec < 0 || close_above_ec <= open_below_ec) {
    throw new Error('Ngưỡng phải hữu hạn, không âm; ngưỡng lấy nước phải nhỏ hơn ngưỡng ngăn mặn.');
  }
  return { open_below_ec, close_above_ec };
}

export function createSimulationFrameLoader({ api = workspaceAPI, onFrame, onError, onLoading } = {}) {
  const requests = createRequestGate();
  return {
    cancel() { requests.next(); },
    async load(year_month, thresholds) {
      const req = requests.next();
      onLoading?.({ year_month, thresholds });
      try {
        const query = new URLSearchParams({ year_month, ...thresholds });
        const frame = await api(`/simulation/frame?${query}`, req);
        if (!req.isCurrent()) return null;
        if (frame.year_month !== year_month || frame.simulation_layer !== true ||
            !Array.isArray(frame.river_segments) || !Array.isArray(frame.gates) ||
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

export function createTimelineScrubber() {
  const host = $('simulationTimeline');
  const state = { items: [], index: 0, unit: 'ec', thresholds: { ...ADVISORY_PRESETS.citrus }, playing: false, speed: 1 };
  const initialRequests = createRequestGate();
  let playbackTimer, scrubTimer, thresholdTimer, playbackGeneration = 0, pendingMonth = null;
  host.innerHTML = `<div id="simulationProfilePanel" hidden><div id="simulationRiverProfile" hidden></div></div><div class="timeline-banner"><div class="timeline-month"><small>THÁNG ĐANG XEM</small><strong id="simulationMonth">—</strong><span id="simulationRegime" class="timeline-regime">Đang đọc dữ liệu</span></div><div class="timeline-stations"><div><small>THƯỢNG LƯU · TÂN CHÂU</small><strong id="simulationTanChau">—</strong></div><div><small>HẠ LƯU · MỸ THO</small><strong id="simulationMyTho">—</strong></div></div><p id="simulationWeather" class="timeline-weather"></p></div>
    <div class="timeline-controls"><button id="simulationPlay" type="button" disabled>▶ Phát chu kỳ</button><label class="timeline-speed">Tốc độ<select id="simulationSpeed"><option value="1">1x</option><option value="2">2x</option><option value="4">4x</option></select></label><input id="simulationSlider" type="range" min="0" max="494" value="494" step="1" disabled aria-label="Tháng mô phỏng" aria-valuetext="Đang tải"><button id="simulationRetry" type="button" hidden>Thử lại</button></div>
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
    $('simulationStatus').textContent = text;
    $('simulationStatus').title = text;
    $('simulationStatus').classList.toggle('is-error', error);
  }
  function renderBanner() {
    const item = state.items[state.index];
    if (!item) return;
    slider.value = state.index;
    slider.setAttribute('aria-valuetext', item.year_month);
    slider.style.setProperty('--progress', `${state.index / Math.max(1, state.items.length - 1) * 100}%`);
    $('simulationMonth').textContent = item.year_month;
    const observed = item.data_regime === 'OBSERVED_MRC';
    $('simulationRegime').textContent = observed ? 'Quan trắc thực đo MRC' : 'Dự báo ML + Khí tượng ERA5';
    $('simulationRegime').dataset.regime = observed ? 'observed' : 'forecast';
    $('simulationRegime').title = observed ? 'Đầu vào quan trắc có nguồn; đoạn sông và cống vẫn là mô phỏng.' : 'Ước tính hồi cứu lưu trữ; chưa phải dự báo vận hành được kiểm chứng.';
    $('simulationTanChau').textContent = formatWater(item.tan_chau_ec_mS_m, state.unit, item.tan_chau_salinity_g_l);
    $('simulationMyTho').textContent = formatWater(item.my_tho_ec_mS_m, state.unit, item.my_tho_salinity_g_l);
    const direction = item.wind?.direction_from_degrees;
    $('simulationWeather').textContent = `ERA5 · Mưa ${num(item.rainfall_mm)} mm · ${num(item.temperature_degC)} °C · Gió ${num(item.wind_speed_ms)} m/s${Number.isFinite(direction) ? ` · từ ${Math.round(direction)}°` : ' · chưa có hướng'}${item.imputed ? ' · EC có nội suy thời gian' : ''}`;
  }
  const loader = createSimulationFrameLoader({
    onLoading(detail) {
      host.dataset.loading = 'true';
      status(`Đang tải kịch bản tháng ${detail.year_month}…`);
      $('simulationRetry').hidden = true;
      emit('workspace:simulation-loading', detail);
    },
    onFrame(frame) {
      host.dataset.loading = 'false';
      emit('workspace:simulation-frame', frame);
      const colors = frame.gates.reduce((count, gate) => {
        count[gate.advisory_code] = (count[gate.advisory_code] || 0) + 1;
        return count;
      }, {});
      status(`${frame.gates.length} cống mô phỏng · ${colors.ADVISORY_SAFE_INTAKE || 0} dưới ngưỡng lấy · ${colors.ADVISORY_CHECK_ONSITE || 0} chuyển tiếp · ${colors.ADVISORY_HIGH_SALINITY_RISK || 0} đạt ngưỡng ngừng lấy · Cần đo thực tế tại cống`);
    },
    onError(error) {
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
      emit('workspace:simulation-loading', { year_month: state.items[state.index].year_month, thresholds: null });
      host.dataset.loading = 'false';
      stop();
      status(error.message, true);
      return Promise.resolve(null);
    }
    return loader.load(state.items[state.index].year_month, { ...state.thresholds });
  }
  function chooseIndex(index, debounce = false) {
    state.index = Math.max(0, Math.min(state.items.length - 1, index));
    renderBanner();
    loader.cancel();
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
  function closestMonthIndex(month) {
    const ordinal = value => Number(value.slice(0, 4)) * 12 + Number(value.slice(5, 7)) - 1;
    const target = ordinal(month);
    return state.items.reduce((best, item, index) =>
      Math.abs(ordinal(item.year_month) - target) < Math.abs(ordinal(state.items[best].year_month) - target) ? index : best, 0);
  }
  function selectMonth(month) {
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(month)) return Promise.resolve(null);
    stop(); clearTimeout(scrubTimer); clearTimeout(thresholdTimer);
    if (!state.items.length) { pendingMonth = month; return Promise.resolve(null); }
    pendingMonth = null;
    return chooseIndex(closestMonthIndex(month));
  }
  async function tick(generation) {
    if (!state.playing || generation !== playbackGeneration || document.hidden) return;
    await chooseIndex((state.index + 1) % state.items.length);
    if (state.playing && generation === playbackGeneration) playbackTimer = setTimeout(() => tick(generation), 1500 / state.speed);
  }
  play.addEventListener('click', () => {
    if (state.playing) return stop();
    state.playing = true;
    play.textContent = '⏸ Tạm dừng';
    play.setAttribute('aria-pressed', 'true');
    tick(++playbackGeneration);
  });
  $('simulationSpeed').addEventListener('change', event => { state.speed = Number(event.target.value); });
  slider.addEventListener('input', () => { stop(); chooseIndex(Number(slider.value), true); });
  slider.addEventListener('change', () => { stop(); chooseIndex(Number(slider.value)); });
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
    const req = initialRequests.next();
    play.disabled = slider.disabled = true;
    $('simulationRetry').hidden = true;
    status('Đang tải trục sông và dòng thời gian…');
    try {
      const [corridor, timeline] = await Promise.all([
        workspaceAPI('/simulation/corridor', req), workspaceAPI('/simulation/timeline', req),
      ]);
      if (!req.isCurrent()) return;
      if (!Array.isArray(timeline.items) || !timeline.items.length || !Array.isArray(corridor.gates) || !corridor.corridor) throw new Error('Chưa có dữ liệu không gian / thời gian hợp lệ.');
      state.items = timeline.items;
      state.index = pendingMonth ? closestMonthIndex(pendingMonth) : state.items.length - 1;
      pendingMonth = null;
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
        button.addEventListener('click', () => { stop(); chooseIndex(index); });
        $('simulationJumps').append(button);
      }
      play.disabled = slider.disabled = false;
      renderBanner();
      await requestFrame();
    } catch (error) {
      if (!req.isCurrent()) return;
      status(error.message, true);
      $('simulationRetry').hidden = false;
    }
  }
  return { load, stop, selectMonth };
}
