import { $, num, node, saveCSV } from "../shared/ui.js";
import { workspaceAPI as api, artifactURL } from "../shared/workspace-api.js";
import { createRequestGate } from "../api.js";
import { experimentAssessment } from "../research-utils.js";
import { drawSeries } from "../shared/time-series.js";
import { comparisonLines } from "../shared/ec-scenario.js";
import { createNextForecast } from "./next-forecast.js";

export function createForecasts() {
  const nextForecast = createNextForecast();
  const experimentRequests = createRequestGate();
  let availableExperiments = [];
  let activeExperiment = null, displayedRows = [];
  function clearForecast(message) {
    nextForecast.reset();
    activeExperiment = null;
    displayedRows = [];
    $("forecastStatus").textContent = message;
    $("forecastChart").replaceChildren();
    $("metricsRows").replaceChildren();
    $("artifactLinks").replaceChildren();
    $("modelAssessment").textContent = "";
    $("modelAssessment").classList.remove("good");
    $("predictionRows").replaceChildren();
    $("predictionStatus").textContent = "";
    $("downloadPredictions").disabled = true;
    $("predictionYear").replaceChildren(node("option", "Toàn bộ"));
    $("predictionYear").firstChild.value = "";
  }

  function renderPredictions() {
    const ex = activeExperiment;
    if (!ex) return;
    const year = $("predictionYear").value;
    const predictions = ex.predictions.filter(row => !year || row.target_month.startsWith(year));
    const months = [...new Set(predictions.map(row => row.target_month))].sort();
    displayedRows = months.map(month => {
      const rows = predictions.filter(row => row.target_month === month);
      const selected = rows.find(row => row.model === ex.selected_model && row.status === "SUCCESS");
      const baseline = rows.find(row => row.model === "Persistence" && row.status === "SUCCESS");
      const actual = rows.find(row => Number.isFinite(row.actual))?.actual ?? null;
      const predicted = Number.isFinite(selected?.predicted) ? selected.predicted : null;
      return { experiment_id: ex.experiment_id, site_code: ex.site_code, target_month: month, actual, selected_model: ex.selected_model, predicted, persistence: baseline?.predicted ?? null, absolute_error: actual !== null && predicted !== null ? Math.abs(predicted - actual) : null, unit: "mS/m", data_kind: "HISTORICAL_BACKTEST" };
    });
    const value = v => Number.isFinite(v) ? num(v) : "—";
    $("predictionRows").replaceChildren();
    $("predictionModelHeading").textContent = ex.selected_model;
    for (const row of displayedRows) {
      const tr = node("tr");
      for (const cell of [row.target_month.slice(0, 7), value(row.actual), value(row.predicted), value(row.persistence), value(row.absolute_error)]) tr.append(node("td", cell));
      $("predictionRows").append(tr);
    }
    $("predictionStatus").textContent = `${displayedRows.length} tháng đang xem · EC và sai số: mS/m. Bảng MAE/RMSE bên dưới luôn dùng toàn bộ tập đánh giá chung của thí nghiệm.`;
    $("downloadPredictions").disabled = !displayedRows.length;
    const series = (key) => displayedRows.filter(row => Number.isFinite(row[key])).map(row => ({ date: row.target_month, value: row[key] }));
    drawSeries($("forecastChart"), [
      { label: "Quan trắc", color: "#173b45", points: series("actual") },
      { label: ex.selected_model, color: "#087f78", points: series("predicted") },
      { label: "Persistence", color: "#c18b33", dashed: true, points: series("persistence") }
    ], { title: `Đối chiếu EC tại ${ex.station}, horizon một tháng`, connected: true, referenceLines: comparisonLines() });
  }

  function showError(message) {
    availableExperiments = [];
    experimentRequests.next();
    clearForecast(message);
    $("experimentSelect").replaceChildren();
    $("experimentSelect").disabled = true;
    $("retryForecast").disabled = true;
  }

  async function selectExperiment() {
    const id = $("experimentSelect").value;
    const req = experimentRequests.next();
    clearForecast(id ? "Đang đọc kết quả kiểm chứng…" : "Chưa có thí nghiệm EC tháng để hiển thị.");
    if (!id) return;
    sessionStorage.setItem("workspace.experiment", id);
    try {
      const ex = await api(`/experiments/${encodeURIComponent(id)}`, req);
      if (!req.isCurrent()) return;
      const { selected, baseline, beatsBaseline } = experimentAssessment(ex);
      $("forecastStatus").textContent = `Trạm ${ex.station} · EC khả dụng theo giả định: cuối tháng + ${ex.availability_lag_days} ngày · ${selected.eval_samples} tháng test chung.`;
      $("modelAssessment").classList.toggle("good", beatsBaseline);
      $("modelAssessment").textContent = `${ex.selected_model} được chọn trên validation. MAE test ${num(selected.mae_mS_m)} mS/m, ${beatsBaseline ? "thấp hơn" : "không thấp hơn"} Persistence (${num(baseline.mae_mS_m)} mS/m). ${beatsBaseline ? "Kết quả chỉ có hiệu lực trong phạm vi thí nghiệm này." : "Chưa có căn cứ dùng mô hình này thay baseline tại trạm."}`;
      activeExperiment = ex;
      nextForecast.load(id);
      for (const year of [...new Set(ex.predictions.map(row => row.target_month.slice(0, 4)))].sort()) {
        const option = node("option", year); option.value = year; $("predictionYear").append(option);
      }
      renderPredictions();
      for (const metric of ex.metrics) {
        const tr = node("tr");
        const values = [
          metric.model,
          num(metric.mae_mS_m),
          num(metric.rmse_mS_m),
          metric.eval_samples,
          metric.model === ex.selected_model ? "Được chọn" : "Đối chứng",
        ];
        for (const value of values) {
          tr.append(node("td", value));
        }
        $("metricsRows").append(tr);
      }
      for (const name of ["metrics.csv", "high_ec_metrics.csv", "predictions.csv", "run_manifest.json", "split_manifest.csv", "forecast_chart.png"]) {
        const a = node("a", name + " ↓");
        a.href = artifactURL(id, name);
        a.setAttribute("download", "");
        $("artifactLinks").append(a);
      }
    } catch (error) {
      if (req.isCurrent()) $("forecastStatus").textContent = error.message;
    }
  }
  $("experimentSelect").addEventListener("change", selectExperiment);
  $("retryForecast").addEventListener("click", selectExperiment);
  $("predictionYear").addEventListener("change", renderPredictions);
  window.addEventListener("workspace:ec-comparison", renderPredictions);
  $("downloadPredictions").addEventListener("click", () => {
    if (displayedRows.length) saveCSV(`${activeExperiment.experiment_id}_monthly.csv`, displayedRows, ["experiment_id", "site_code", "target_month", "actual", "selected_model", "predicted", "persistence", "absolute_error", "unit", "data_kind"]);
  });
  async function selectStation(siteCode) {
    const current = availableExperiments.find(ex => ex.experiment_id === $("experimentSelect").value);
    const candidates = availableExperiments.filter(ex => ex.site_code === siteCode);
    const selected = candidates.find(ex => ex.availability_lag_days === current?.availability_lag_days) || candidates[0];
    if (!selected) {
      experimentRequests.next();
      clearForecast("Chưa có thí nghiệm kiểm chứng EC tháng cho điểm đo này.");
      return;
    }
    $("experimentSelect").value = selected.experiment_id;
    await selectExperiment();
  }

  async function load(experiments) {
    availableExperiments = experiments;
    $("experimentSelect").replaceChildren();
    $("experimentSelect").disabled = !experiments.length;
    $("retryForecast").disabled = !experiments.length;
    for (const ex of experiments) {
      const option = node("option", `${ex.station} · độ trễ ${ex.availability_lag_days} ngày`);
      option.value = ex.experiment_id;
      $("experimentSelect").append(option);
    }
    const saved = sessionStorage.getItem("workspace.experiment");
    if (experiments.some((ex) => ex.experiment_id === saved)) $("experimentSelect").value = saved;
    await selectExperiment();
  }

  return { load, showError, selectStation };
}
