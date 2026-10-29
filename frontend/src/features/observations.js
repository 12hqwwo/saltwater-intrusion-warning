import { $, num, node, saveCSV, sourceAnchor } from "../shared/ui.js";
import { workspaceAPI as api } from "../shared/workspace-api.js";
import { createRequestGate } from "../api.js";
import { labels, dateOnly, recentDateWindow, filterObservations } from "../research-utils.js";
import { drawSeries } from "../shared/time-series.js";
import { createResearchMap } from "./observations-map.js";
import { ecComparison, setECComparison, comparisonLines } from "../shared/ec-scenario.js";
import { loadThresholdPresets, populateThresholdPresets, presetReference } from "../shared/threshold-presets.js";
import { createTimelineScrubber } from "./timeline-scrubber.js";
import { formatWater } from "../shared/simulation-display.js";
import { createRiverProfile } from './river-profile.js';

export function createObservations({ onForecast } = {}) {
  const state = { collection: { features: [] }, summary: { sources: [] }, rows: [], shown: [] };
  const stationRequests = createRequestGate();
  let displayUnit = 'ec';
  let hasFitted = false;
  const map = createResearchMap($("researchMap"), { onSelect: selectStation, onTileError: () => {
    $("tileError").hidden = false;
  } });
  const timeline = createTimelineScrubber();
  const profile = createRiverProfile($('simulationRiverProfile'));
  let activeForecast = null, baselineMonth = null;
  // Keep the shared profile's keyboard-accessible SVG dots, without its legacy chip matrix.
  function polishProfile() {
    const host = $('simulationRiverProfile');
    host.querySelector('.river-profile-gates')?.remove();
    host.querySelector('.river-profile-header')?.remove();
    const points = (host.querySelector('.river-profile-line')?.getAttribute('points') || '')
      .trim().split(/\s+/).filter(Boolean).map(point => point.split(',').map(Number));
    for (const dot of host.querySelectorAll('.river-profile-tick')) {
      const x = Number(dot.getAttribute('cx'));
      const right = points.findIndex(point => point[0] >= x);
      if (right < 0) continue;
      const a = points[Math.max(0, right - 1)], b = points[right];
      const fraction = (x - a[0]) / (b[0] - a[0] || 1);
      dot.setAttribute('cy', String(a[1] + (b[1] - a[1]) * fraction));
      dot.setAttribute('r', '3');
    }
  }
  function renderForecastBanner() {
    $('mapForecastBanner').hidden = !activeForecast;
    if (!activeForecast) return;
    $('mapForecastValue').textContent = `${activeForecast.station_name || activeForecast.station || 'Trạm dự báo'} · ${num(activeForecast.predicted_ec_mS_m)} mS/m`;
    $('mapForecastContext').textContent = `Dự báo ${activeForecast.target_month} · Timeline ${baselineMonth || 'đang tải'} · Lớp sông và cống giữ kịch bản tháng nền`;
  }
  window.addEventListener('workspace:show-forecast-map', event => {
    const prediction = event.detail;
    if (!Number.isFinite(prediction?.predicted_ec_mS_m) || prediction.predicted_ec_mS_m < 0 || !/^\d{4}-(0[1-9]|1[0-2])$/.test(prediction.target_month)) return;
    activeForecast = prediction;
    baselineMonth = null;
    renderForecastBanner();
    location.hash = 'observations';
    timeline.selectMonth(prediction.target_month);
    requestAnimationFrame(() => { map.refresh(); map.fit(); });
  });
  function clearForecastBanner() { activeForecast = null; renderForecastBanner(); }
  window.addEventListener('workspace:multivariate-prediction', clearForecastBanner);
  window.addEventListener('workspace:multivariate-clear', clearForecastBanner);
  $('mapForecastDismiss').addEventListener('click', () => {
    clearForecastBanner(); map.setForecast(null); $('mapForecastStatus').hidden = true;
  });
  let profileHasFitted = false;
  window.addEventListener('workspace:simulation-frame', event => {
    profile.setFrame(event.detail);
    polishProfile();
    baselineMonth = event.detail.year_month;
    renderForecastBanner();
    if (!profileHasFitted && !$('observations').hidden) requestAnimationFrame(() => {
      map.refresh();
      map.fit();
      profileHasFitted = true;
    });
  });
  window.addEventListener('workspace:simulation-loading', () => profile.clear());
  window.addEventListener('workspace:simulation-unit', event => { profile.setUnit(event.detail.unit); polishProfile(); });
  const dockSize = new ResizeObserver(() => {
    const scene = $('researchMap').parentElement;
    scene.style.setProperty('--timeline-height', `${Math.ceil($('simulationTimeline').getBoundingClientRect().height)}px`);
  });
  dockSize.observe($('simulationTimeline'));
  window.addEventListener('workspace:simulation-profile-toggle', () => {
    requestAnimationFrame(() => { map.refresh(); map.fit(); });
  });
  $('toggleStationList').addEventListener('click', () => {
    const show = $('stationPanel').hidden;
    $('stationPanel').hidden = !show;
    $('mapLayout').classList.toggle('stations-open', show);
    $('mapLayout').classList.toggle('stations-collapsed', !show);
    $('toggleStationList').setAttribute('aria-expanded', String(show));
    $('toggleStationList').textContent = show ? 'Ẩn danh sách trạm' : 'Hiện danh sách trạm';
    requestAnimationFrame(() => { map.refresh(); map.fit(); });
  });
  function showThresholds(show) {
    $('simulationThresholdPopover').hidden = !show;
    $('simulationThresholdToggle').setAttribute('aria-expanded', String(show));
    if (show) $('simulationOpenBelow').focus();
  }
  function showLegend(show) {
    $('mapLegendPopover').hidden = !show;
    $('mapLegendToggle').setAttribute('aria-expanded', String(show));
  }
  $('mapLegendToggle').addEventListener('click', () => showLegend($('mapLegendPopover').hidden));
  $('simulationThresholdToggle').addEventListener('click', () => showThresholds($('simulationThresholdPopover').hidden));
  $('simulationThresholdPreset').addEventListener('change', event => {
    if (event.target.value === 'custom') showThresholds(true);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !$('simulationThresholdPopover').hidden) {
      showThresholds(false);
      $('simulationThresholdToggle').focus();
    }
    if (event.key === 'Escape' && !$('mapLegendPopover').hidden) {
      showLegend(false); $('mapLegendToggle').focus();
    }
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('.simulation-hud')) showThresholds(false);
    if (!event.target.closest('.map-legend-control')) showLegend(false);
  });
  for (const [id, apply] of [
    ['simulationRiverToggle', value => map.setRiverParticles(value)],
    ['simulationWindToggle', value => map.setWindVisible(value)],
    ['simulationGatesToggle', value => { $('showGates').checked = value; map.setGateVisible(value); }],
  ]) $(id).addEventListener('click', () => {
    const enabled = $(id).getAttribute('aria-pressed') !== 'true';
    $(id).setAttribute('aria-pressed', String(enabled));
    apply(enabled);
  });
  timeline.load();
  $('mapBaseTheme').addEventListener('change', event => {
    map.setBaseTheme(event.target.value);
    document.querySelector('.windy-map-panel').dataset.baseTheme = event.target.value;
  });
  $('stationDetails').addEventListener('toggle', () => {
    if ($('stationDetails').open && state.site) renderObservations();
  });
  window.addEventListener('workspace:simulation-unit', event => {
    displayUnit = event.detail.unit;
    renderStations();
    renderSiteValue();
  });
  function renderSiteValue() {
    const ec = state.site?.latest_ec_mS_m;
    $('siteEC').textContent = Number.isFinite(ec) ? num(displayUnit === 'salinity' ? Math.round(ec * 6.4) / 1000 : ec) : '—';
    $('siteECUnit').textContent = displayUnit === 'salinity' ? `g/L quy đổi · (${num(ec)} mS/m) · mẫu mới nhất` : 'mS/m · mẫu mới nhất của điểm';
  }
  function refreshMap() {
    if ($("observations").hidden) return;
    requestAnimationFrame(() => {
      map.refresh();
      if (!hasFitted && state.collection.features.length) {
        map.fit();
        hasFitted = true;
      }
    });
  }
  window.addEventListener("workspace:viewchange", (event) => {
    if (event.detail.view === "observations") refreshMap();
  });
  function clearObservations() {
    state.rows = [];
    state.shown = [];
    $("observationChart").replaceChildren();
    $("observationRows").replaceChildren();
    $("downloadRows").disabled = true;
  }

  function showError(message) {
    stationRequests.next();
    state.site = null;
    hasFitted = false;
    state.collection = { type: "FeatureCollection", features: [] };
    clearObservations();
    map.setStations(state.collection);
    $("stationList").replaceChildren(node("p", message, "subtle"));
    $("observationStatus").textContent = message;
    $("siteTitle").textContent = "Chưa có điểm đo";
    $("siteEC").textContent = "—";
    $("siteProvider").textContent = "QUAN TRẮC";
    $("siteRole").textContent = "";
    $("siteWarning").textContent = "";
    $("openStationForecast").hidden = true;
    $("stationForecastNote").textContent = "";
    $("mapCount").textContent = "0 điểm hiển thị";
    $("retryObservations").disabled = true;
    $("dateFrom").value = "";
    $("dateTo").value = "";
  }

  function renderStations() {
    const search = $("stationSearch").value.toLocaleLowerCase("vi");
    $("stationList").replaceChildren();
    for (const f of state.collection.features.filter((f2) => (f2.properties.site_name + f2.properties.site_code).toLocaleLowerCase("vi").includes(search))) {
      const p = f.properties, button = node("button", undefined, "station-button" + (state.site?.site_code === p.site_code ? " selected" : ""));
      button.setAttribute("aria-pressed", String(state.site?.site_code === p.site_code));
      button.append(node("strong", p.site_name), node("small", `${p.provider} · ${p.observation_count} mẫu · ${dateOnly(p.last_observed_date)}`), node('span', formatWater(p.latest_ec_mS_m, displayUnit), 'station-water-value'));
      button.addEventListener("click", () => selectStation(p.site_code));
      $("stationList").append(button);
    }
    if (!$("stationList").children.length) {
      $("stationList").append(node("p", "Không có điểm đo phù hợp.", "subtle"));
    }
  }

  async function selectStation(code) {
    const site = state.collection.features.find((f) => f.properties.site_code === code)?.properties;
    if (!site) return;
    const req = stationRequests.next();
    sessionStorage.setItem("workspace.station", code);
    state.site = site;
    clearObservations();
    $("retryObservations").disabled = false;
    renderStations();
    map.select(code);
    $("siteTitle").textContent = site.site_name;
    $("siteProvider").textContent = `${site.provider} / ${site.site_code}`;
    $("siteRole").textContent = site.study_role || "Quan trắc EC có nguồn tại điểm đo";
    renderSiteValue();
    const hasExperiment = state.summary.experiments?.some(ex => ex.site_code === code);
    $("openStationForecast").hidden = !hasExperiment;
    $("stationForecastNote").textContent = hasExperiment
      ? "Chạy mô hình đa biến từ khí tượng có nguồn tại cùng trạm; xem dự báo EC tháng và đầu vào."
      : "Điểm này chưa có thí nghiệm kiểm chứng EC tháng; chỉ hiển thị quan trắc có nguồn.";
    $("siteWarning").textContent = site.site_code.startsWith("RIA2_") ? `Có ${site.observation_count} mẫu, chỉ ghi ngày đo, không có giờ. CRS chưa xác nhận; chưa đủ chuỗi để kiểm chứng dự báo mẫu EC tháng kế tiếp. ${site.site_code === "RIA2_DT_05" ? "Nhãn địa danh Vĩnh Thới trong bản tin cần đối chiếu." : ""}` : `Giữ nguyên cờ chất lượng từng dòng từ nguồn. Dữ liệu gần nhất: ${site.last_observed_date ? dateOnly(site.last_observed_date) : "chưa có"}. Mốc thời gian nguồn chưa xác nhận giờ lấy mẫu thực tế; số liệu lịch sử dùng để tra cứu và kiểm chứng.`;
    renderStationComparison();
    if (site.first_observed_date && site.last_observed_date) {
      [$("dateFrom").value, $("dateTo").value] = recentDateWindow(site);
    } else {
      $("dateFrom").value = "";
      $("dateTo").value = "";
    }
    $("observationStatus").textContent = "Đang tải số đo…";
    $("observationChart").replaceChildren();
    $("observationRows").replaceChildren();
    $("downloadRows").disabled = true;
    try {
      const result = await api(`/stations/${encodeURIComponent(code)}/observations`, req);
      if (!req.isCurrent()) return;
      state.rows = result.items;
      renderObservations();
    } catch (error) {
      if (req.isCurrent()) $("observationStatus").textContent = error.message;
    }
  }

  function renderObservations() {
    try {
      state.shown = filterObservations(state.rows, $("dateFrom").value, $("dateTo").value);
    } catch (error) {
      state.shown = [];
      $("downloadRows").disabled = true;
      $("observationChart").replaceChildren();
      $("observationRows").replaceChildren();
      $("observationStatus").textContent = error.message;
      return;
    }
    const gap = state.site.max_gap_days;
    $("observationStatus").textContent = `${state.shown.length}/${state.rows.length} mẫu · ${state.site.sampling_label || "Mẫu từ nguồn quan trắc"}${Number.isFinite(gap) ? ` · Khoảng trống dài nhất: ${gap} ngày.` : "."}`;
    $("downloadRows").disabled = !state.shown.length;
    drawSeries($("observationChart"), [{ label: "EC quan trắc", color: "#087f78", points: state.shown.map((r) => ({ date: r.observed_date, value: r.ec_mS_m })) }], { title: `EC quan trắc ${state.site.site_name}; từng điểm là một mẫu có nguồn.`, referenceLines: comparisonLines() });
    $("observationRows").replaceChildren();
    for (const r of state.shown) {
      const row = node("tr"), source = state.summary.sources.find((s) => s.source_id === r.source_id), cell = node("td");
      cell.append(sourceAnchor(source, r.source_id), node("small", r.source_locator));
      row.append(node("td", dateOnly(r.observed_date)), node("td", num(r.ec_mS_m)), node("td", labels[r.quality_flag] || r.quality_flag), cell);
      $("observationRows").append(row);
    }
  }

  function exportRows() {
    if (!state.site || !state.shown.length) return;
    const keys = ["site_code", "observed_date", "observed_at", "time_precision", "ec_mS_m", "unit", "quality_flag", "observed_or_estimated", "dataset_code", "source_id", "source_locator", "source_sha256"];
    saveCSV(state.site.site_code + "_observations.csv", state.shown, keys);
  }
  $("stationSearch").addEventListener("input", renderStations);
  $("dateFilter").addEventListener("submit", (e) => {
    e.preventDefault();
    if (state.site) renderObservations();
  });
  $("allDates").addEventListener("click", () => {
    if (!state.site) return;
    $("dateFrom").value = state.site.first_observed_date;
    $("dateTo").value = state.site.last_observed_date;
    renderObservations();
  });
  $("downloadRows").addEventListener("click", exportRows);
  $("openStationForecast").addEventListener("click", () => {
    if (!state.site) return;
    onForecast?.(state.site.site_code);
    location.hash = "forecasts";
  });
  $("showUnconfirmed").addEventListener("change", () => {
    const count = map.setUnconfirmed($("showUnconfirmed").checked);
    $("mapCount").textContent = `${count}/${state.collection.features.length} điểm hiển thị`;
    $("coordinateNotice").textContent = $("showUnconfirmed").checked ? "Điểm viền đứt: giả định WGS84 để xem tham khảo, CRS nguồn chưa xác nhận. Không dùng lớp này xác lập quan hệ thủy lực trạm–cống." : "Ranh giới từ tệp dự án, chưa xác minh phiên bản. Điểm có tọa độ chưa xác nhận đang ẩn.";
  });
  $("showBoundaries").addEventListener("change", () => map.setBoundaryVisible($("showBoundaries").checked));
  $("showGates").addEventListener("change", () => {
    $('simulationGatesToggle').setAttribute('aria-pressed', String($('showGates').checked));
    map.setGateVisible($("showGates").checked);
  });
  function renderStationComparison() {
    const scenario = ecComparison(), value = state.site?.latest_ec_mS_m;
    $("stationComparisonStatus").textContent = scenario && Number.isFinite(value)
      ? `Mẫu ${dateOnly(state.site.last_observed_date)}: ${num(value)} mS/m ${value >= scenario.threshold ? "đạt / vượt" : "thấp hơn"} ngưỡng tự nhập ${num(scenario.threshold)} mS/m. Cơ sở nhiệt độ và mức phù hợp của ngưỡng cần đối chiếu riêng.`
      : "";
  }
  function refreshComparison() {
    const value = ecComparison();
    $("ecComparisonValue").value = value?.threshold ?? "";
    $("ecComparisonPurpose").value = value?.purpose ?? "";
    $("ecComparisonReference").value = value?.reference ?? "";
    $("ecComparisonStatus").textContent = value ? `${value.purpose} · ${num(value.threshold)} mS/m · ${value.reference}. Đây là đối chiếu kịch bản; chưa xác lập mức an toàn cho cây trồng hay cấp nước.` : "Chưa áp dụng ngưỡng. Điền giá trị và nguồn để đối chiếu.";
    $("mapComparisonLegend").textContent = value ? `Đỏ: mẫu mới nhất đạt / vượt ${num(value.threshold)} mS/m · Xanh: thấp hơn ngưỡng · Viền đứt: tọa độ tham khảo.` : "Màu điểm thể hiện nguồn tọa độ. Mở đối chiếu nâng cao để so sánh EC.";
    map.refreshComparison();
    renderStationComparison();
    if (state.site) renderObservations();
  }
  let comparisonPresets = [];
  if ($("ecComparisonPreset")) loadThresholdPresets().then(items => {
    comparisonPresets = items;
    populateThresholdPresets($("ecComparisonPreset"), items, "comparison");
    if ($("ecPresetStatus")) $("ecPresetStatus").textContent = items.length ? "Mẫu đối chiếu tham khảo từ danh mục; chưa xác lập mức an toàn hay quy chuẩn áp dụng." : "Chưa có mẫu ngưỡng trong danh mục. Có thể tự nhập ngưỡng đối chiếu.";
  }).catch(error => {
    ($("ecPresetStatus") || $("ecComparisonStatus")).textContent = `Chưa tải được mẫu ngưỡng: ${error.message} Vẫn có thể tự nhập ngưỡng đối chiếu.`;
  });
  $("ecComparisonPreset")?.addEventListener("change", event => {
    const preset = comparisonPresets.find(item => item.preset_code === event.target.value);
    if (!preset) return;
    $("ecComparisonValue").value = preset.threshold_ms_m;
    $("ecComparisonPurpose").value = preset.usage_purpose || preset.preset_code;
    $("ecComparisonReference").value = presetReference(preset);
    if ($("ecPresetStatus")) $("ecPresetStatus").textContent = presetReference(preset);
    try {
      setECComparison({ threshold: preset.threshold_ms_m, purpose: preset.usage_purpose || preset.preset_code, reference: presetReference(preset) });
    } catch (error) { $("ecComparisonStatus").textContent = error.message; }
  });
  for (const id of ["ecComparisonValue", "ecComparisonPurpose", "ecComparisonReference"]) $(id).addEventListener("input", () => {
    if ($("ecComparisonPreset")) $("ecComparisonPreset").value = "";
  });
  $("ecComparisonForm").addEventListener("submit", (event) => {
    event.preventDefault();
    try { setECComparison({ threshold: Number($("ecComparisonValue").value), purpose: $("ecComparisonPurpose").value.trim(), reference: $("ecComparisonReference").value.trim() }); }
    catch (error) { $("ecComparisonStatus").textContent = error.message; }
  });
  $("clearECComparison").addEventListener("click", () => {
    if ($("ecComparisonPreset")) $("ecComparisonPreset").value = "";
    setECComparison(null);
  });
  window.addEventListener("workspace:ec-comparison", refreshComparison);
  refreshComparison();
  $("showBase").addEventListener("change", () => {
    map.setBase($("showBase").checked);
    $("tileError").hidden = true;
  });
  $("fitMap").addEventListener("click", () => map.fit());
  $("retryObservations").addEventListener("click", () => selectStation(state.site?.site_code));
  async function load(summary, collection) {
    state.summary = summary;
    state.collection = collection;
    if (!collection.features.length) {
      showError("Chưa có điểm quan trắc trong bộ dữ liệu.");
      return;
    }
    map.setUnconfirmed($("showUnconfirmed").checked);
    $("mapCount").textContent = `${map.setStations(collection)}/${collection.features.length} điểm hiển thị`;
    refreshMap();
    const saved = sessionStorage.getItem("workspace.station");
    const preferred = collection.features.find(f => f.properties.site_code === "MRC_VN_019805")
      || collection.features.find(f => f.properties.provider === "MRC")
      || collection.features[0];
    await selectStation(collection.features.some((f) => f.properties.site_code === saved) ? saved : preferred.properties.site_code);
    api("/boundaries").then((data) => {
      map.setBoundaries(data);
      refreshMap();
    }).catch(() => {
      $("coordinateNotice").textContent = "Chưa tải được ranh giới tham khảo.";
    });
  }

  return { map, load, showError, selectStation };
}
