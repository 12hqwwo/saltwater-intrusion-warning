import "./workspace.css";
import "../styles/simulation.css";
import "./refresh.css";
import { $ } from "../shared/ui.js";
import { workspaceAPI as api } from "../shared/workspace-api.js";
import { createRequestGate } from "../api.js";
import { createObservations } from "../features/observations.js";
import { createForecasts } from "../features/forecasts.js";
import { createWeatherEstimates } from "../features/weather-estimates.js";
import { createGateDossiers } from "../features/gate-dossiers.js";
import { renderOverview, renderOverviewStations, bindDatabaseCheck, loadDataFreshness } from "../features/overview.js";
import { showIntake } from "../intake.js";
import { bindNavigation } from "./navigation.js";
import { createDatabaseHistory } from "../features/database-history.js";
import { createMultivariateForecast } from "../features/multivariate-forecast.js";
import { createFieldMeasurements } from "../features/field-measurements.js";
import { createLoginPanel } from '../auth/login-panel.js';
import { getCurrentRole, restoreSessionFromStorage } from '../auth/auth-service.js';
import { roleCanViewSection, ROLE_PUBLIC } from '../auth/auth-roles.js';
import { applyRoleVisibility } from '../auth/role-visibility.js';

createLoginPanel($("authHost"));
applyRoleVisibility(ROLE_PUBLIC);
bindDatabaseCheck();
const forecasts = createForecasts();
const multivariate = createMultivariateForecast();
let fieldMeasurements = createFieldMeasurements($("fieldMeasurementsHost"), ROLE_PUBLIC);
const observations = createObservations({ onForecast: async (code) => {
  if (getCurrentRole() === ROLE_PUBLIC) return;
  forecasts.selectStation(code);
  await multivariate.selectStation(code);
} });
window.addEventListener("workspace:select-station", event => {
  if (event.detail?.site_code) observations.selectStation(event.detail.site_code);
});
window.addEventListener("workspace:multivariate-catalog", event => {
  $("statExperiments").textContent = event.detail.stations.length;
});
function showMapForecast(prediction) {
  if (!observations.map.setForecast(prediction)) {
    $("mapForecastStatus").hidden = true;
    return;
  }
  $("mapForecastStatus").hidden = false;
  $("mapForecastStatus").textContent = `Vòng xanh dương: EC dự báo đa biến ${prediction.target_month} tại ${prediction.station}; các điểm quan trắc vẫn giữ giá trị và thời điểm đo riêng.`;
}
window.addEventListener("workspace:multivariate-prediction", event => {
  showMapForecast(event.detail);
});
window.addEventListener("workspace:multivariate-clear", () => {
  observations.map.setForecast(null);
  $("mapForecastStatus").hidden = true;
});
let databaseHistory = null;
let weather = null;
let gates = createGateDossiers(observations.map, ROLE_PUBLIC);
bindNavigation(view => roleCanViewSection(getCurrentRole(), view));
let lastRole = null;
window.addEventListener('workspace:auth-changed', () => {
  const role = getCurrentRole();
  applyRoleVisibility(role);
  if (role === lastRole) return;
  lastRole = role;
  fieldMeasurements.destroy?.();
  fieldMeasurements = createFieldMeasurements($("fieldMeasurementsHost"), role);
  gates.destroy();
  gates = createGateDossiers(observations.map, role);
  if (role !== ROLE_PUBLIC && !databaseHistory) databaseHistory = createDatabaseHistory();
  if (role !== ROLE_PUBLIC) { weather?.destroy(); weather = createWeatherEstimates(); weather.load(); }
  else {
    weather?.destroy(); weather = null;
    databaseHistory?.destroy(); databaseHistory = null;
    multivariate.clearPrivate();
    window.dispatchEvent(new CustomEvent('workspace:multivariate-clear'));
  }
  if (role !== ROLE_PUBLIC) multivariate.load();
  loadWorkspace();
  if (role !== ROLE_PUBLIC) loadIntake();
});
const requests = createRequestGate();
async function loadWorkspace() {
  const req = requests.next();
  forecasts.showError('Đang tải danh sách thí nghiệm…');
  observations.showError('Đang tải nguồn quan trắc…');
  gates.load([]);
  $("loadError").hidden = true;
  $("retryWorkspace").hidden = true;
  $("modeBadge").textContent = "Đang tải…";
  const results = await Promise.allSettled([api("/summary", req), api("/stations", req), api("/gates", req)]);
  if (!req.isCurrent()) return;
  const [summary, stations, catalogue] = results;
  const errors = results.filter((result) => result.status === "rejected").map((result) => result.reason.message);
  if (errors.length) {
    $("loadError").textContent = [...new Set(errors)].join(" ");
    $("loadError").hidden = false;
    $("retryWorkspace").hidden = false;
    $("modeBadge").textContent = "Một phần dữ liệu chưa tải được";
  }
  const jobs = [];
  if (summary.status === "fulfilled") {
    renderOverview(summary.value);
    if (getCurrentRole() !== ROLE_PUBLIC) jobs.push(loadDataFreshness(req));
    if (getCurrentRole() !== ROLE_PUBLIC) jobs.push(forecasts.load(summary.value.experiments || []));
  } else {
    forecasts.showError(summary.reason.message);
  }
  if (stations.status === "fulfilled") {
    const sources = summary.status === "fulfilled" ? summary.value : { sources: [] };
    jobs.push(observations.load(sources, stations.value).then(() => renderOverviewStations(stations.value)));
  } else {
    observations.showError(stations.reason.message);
  }
  if (catalogue.status === "fulfilled") {
    jobs.push(gates.load(catalogue.value.items));
  }
  await Promise.allSettled(jobs);
}
async function loadIntake() {
  if (getCurrentRole() === ROLE_PUBLIC) return;
  $("retryIntake").disabled = true;
  try {
    await showIntake();
  } finally {
    $("retryIntake").disabled = false;
  }
}
$("retryWorkspace").addEventListener("click", loadWorkspace);
$("retryIntake").addEventListener("click", loadIntake);
restoreSessionFromStorage();
