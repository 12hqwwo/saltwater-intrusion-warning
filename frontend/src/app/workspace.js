import "./workspace.css";
import "../styles/simulation.css";
import { $ } from "../shared/ui.js";
import { workspaceAPI as api } from "../shared/workspace-api.js";
import { createRequestGate } from "../api.js";
import { createObservations } from "../features/observations.js";
import { createForecasts } from "../features/forecasts.js";
import { createWeatherEstimates } from "../features/weather-estimates.js";
import { createGateDossiers } from "../features/gate-dossiers.js";
import { renderOverview, renderOverviewStations, bindDatabaseCheck } from "../features/overview.js";
import { showIntake } from "../intake.js";
import { bindNavigation } from "./navigation.js";
import { createDatabaseHistory } from "../features/database-history.js";
import { createMultivariateForecast } from "../features/multivariate-forecast.js";

bindDatabaseCheck();
const forecasts = createForecasts();
const multivariate = createMultivariateForecast();
const observations = createObservations({ onForecast: async (code) => {
  await multivariate.selectStation(code);
  forecasts.selectStation(code);
} });
window.addEventListener("workspace:select-station", event => {
  if (event.detail?.site_code) observations.selectStation(event.detail.site_code);
});
window.addEventListener("workspace:multivariate-catalog", event => {
  $("statExperiments").textContent = event.detail.stations.length;
});
function showMapForecast(prediction) {
  observations.map.setForecast(prediction);
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
window.addEventListener("workspace:show-forecast-map", event => {
  showMapForecast(event.detail);
  location.hash = "observations";
});
createDatabaseHistory();
const weather = createWeatherEstimates();
const gates = createGateDossiers(observations.map);
bindNavigation();
const requests = createRequestGate();
async function loadWorkspace() {
  const req = requests.next();
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
    jobs.push(forecasts.load(summary.value.experiments || []));
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
  $("retryIntake").disabled = true;
  try {
    await showIntake();
  } finally {
    $("retryIntake").disabled = false;
  }
}
$("retryWorkspace").addEventListener("click", loadWorkspace);
$("retryIntake").addEventListener("click", loadIntake);
loadWorkspace();
loadIntake();
weather.load();
multivariate.load();
