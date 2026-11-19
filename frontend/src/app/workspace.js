import "./workspace.css";
import "../styles/simulation.css";
import "./refresh.css";
import { $ } from "../shared/ui.js";
import { workspaceAPI as api } from "../shared/workspace-api.js";
import { createRequestGate } from "../api.js";
import { createForecasts } from "../features/forecasts.js";
import { createWeatherEstimates } from "../features/weather-estimates.js";
import { createGateDossiers } from "../features/gate-dossiers.js";
import { renderOverview, renderOverviewStations, bindDatabaseCheck, loadDataFreshness } from "../features/overview.js";
import { showIntake } from "../intake.js";
import { bindNavigation } from "./navigation.js";
import { createDatabaseHistory } from "../features/database-history.js";
import { createFieldMeasurements } from "../features/field-measurements.js";
import { createLoginPanel } from '../auth/login-panel.js';
import { getCurrentRole, restoreSessionFromStorage } from '../auth/auth-service.js';
import { roleCanViewSection, ROLE_PUBLIC } from '../auth/auth-roles.js';
import { applyRoleVisibility } from '../auth/role-visibility.js';

createLoginPanel($("authHost"));
applyRoleVisibility(ROLE_PUBLIC);
bindDatabaseCheck();
const forecasts = createForecasts();
let multivariate = null;
let multivariatePromise = null;
function ensureMultivariate() {
  if (!multivariatePromise) multivariatePromise = import("../features/multivariate-forecast.js").then(({ createMultivariateForecast }) => {
    multivariate = createMultivariateForecast();
    if (getCurrentRole() !== ROLE_PUBLIC) return Promise.resolve(multivariate.load()).then(() => multivariate);
    return multivariate;
  }).catch(error => { multivariatePromise = null; throw error; });
  return multivariatePromise;
}
let fieldMeasurements = createFieldMeasurements($("fieldMeasurementsHost"), ROLE_PUBLIC);
let observations = null;
let observationsPromise = null;
let stationPayload = null;
let currentPrediction = null;
let pendingGates = null;
let pendingCandidates = null;
function ensureObservations() {
  if (!observationsPromise) observationsPromise = import("../features/observations.js").then(async ({ createObservations }) => {
    observations = createObservations({ onForecast: async (code) => {
      if (getCurrentRole() === ROLE_PUBLIC) return;
      forecasts.selectStation(code);
      try {
        await (await ensureMultivariate()).selectStation(code);
      } catch (error) {
        forecasts.showError(error.message);
      }
    } });
    if (pendingGates) observations.map.setGates(...pendingGates);
    if (pendingCandidates) observations.map.setCandidates(...pendingCandidates);
    if (stationPayload) await observations.load(...stationPayload);
    if (currentPrediction) showMapForecast(currentPrediction);
    return observations;
  }).catch(error => { observationsPromise = null; throw error; });
  return observationsPromise;
}
window.addEventListener("workspace:select-station", event => {
  if (event.detail?.site_code) ensureObservations()
    .then(feature => feature.selectStation(event.detail.site_code))
    .catch(error => { $('loadError').textContent = error.message; $('loadError').hidden = false; });
});
window.addEventListener("workspace:multivariate-catalog", event => {
  $("statExperiments").textContent = event.detail.stations.length;
});
function showMapForecast(prediction) {
  currentPrediction = prediction;
  if (!observations?.map.setForecast(prediction)) {
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
  currentPrediction = null;
  observations?.map.setForecast(null);
  $("mapForecastStatus").hidden = true;
});
let databaseHistory = null;
let weather = null;
const mapBridge = {
  setCandidates(...args) { pendingCandidates = args; observations?.map.setCandidates(...args); },
  setGates(...args) { pendingGates = args; observations?.map.setGates(...args); },
};
let gates = createGateDossiers(mapBridge, ROLE_PUBLIC);
window.addEventListener('workspace:viewchange', event => {
  if (['observations', 'gates'].includes(event.detail?.view)) ensureObservations().catch(error => {
    $('loadError').textContent = error.message; $('loadError').hidden = false;
  });
  if (event.detail?.view === 'forecasts' && getCurrentRole() !== ROLE_PUBLIC) ensureMultivariate().catch(error => {
    $('loadError').textContent = error.message; $('loadError').hidden = false;
  });
});
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
  gates = createGateDossiers(mapBridge, role);
  if (role !== ROLE_PUBLIC && !databaseHistory) databaseHistory = createDatabaseHistory();
  if (role !== ROLE_PUBLIC) { weather?.destroy(); weather = createWeatherEstimates(); weather.load(); }
  else {
    weather?.destroy(); weather = null;
    databaseHistory?.destroy(); databaseHistory = null;
    multivariate?.clearPrivate();
    window.dispatchEvent(new CustomEvent('workspace:multivariate-clear'));
  }
  if (role !== ROLE_PUBLIC && multivariate) multivariate.load();
  loadWorkspace();
  if (role !== ROLE_PUBLIC) loadIntake();
});
const requests = createRequestGate();
async function loadWorkspace() {
  const req = requests.next();
  forecasts.showError('Đang tải danh sách thí nghiệm…');
  observations?.showError('Đang tải nguồn quan trắc…');
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
    stationPayload = [sources, stations.value];
    renderOverviewStations(stations.value);
    if (observations) jobs.push(observations.load(...stationPayload));
  } else {
    stationPayload = null;
    observations?.showError(stations.reason.message);
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
