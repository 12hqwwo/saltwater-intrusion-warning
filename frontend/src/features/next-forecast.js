import { $, node, num, save } from "../shared/ui.js";
import { workspaceAPI as api } from "../shared/workspace-api.js";
import { createRequestGate } from "../api.js";
import { dateOnly } from "../research-utils.js";
import { validMonth, validEc } from '../shared/forecast-contract.js';
import { COMPACT_FORECAST_MODEL, COMPACT_FORECAST_SUBTITLE, DEFAULT_P90_MYTHO_MS_M } from '../shared/forecast-map-overlay.js';

/** Archived next-step predictions remain tied to their experiment and origin. */
export function createNextForecast() {
  const requests = createRequestGate();
  let current = null, p90Threshold = DEFAULT_P90_MYTHO_MS_M;
  function reset(message = "Chọn một thí nghiệm để đọc dự báo sau mẫu cuối.") {
    requests.next();
    current = null;
    $("nextForecastValue").textContent = "—";
    $("nextForecastTarget").textContent = "—";
    $("nextForecastStatus").textContent = message;
    $("nextForecastRows").replaceChildren();
    $("nextForecastDownload").disabled = true;
    $('nextForecastApplyMap').disabled = true;
    $('nextForecastModelInfo').hidden = true;
  }
  async function load(id, experiment = {}) {
    reset("Đang đọc kết quả dự báo sau mẫu cuối…");
    const req = requests.next();
    try {
      const data = await api(`/experiments/${encodeURIComponent(id)}/next-forecast`, req);
      if (!req.isCurrent()) return;
      if (data.experiment_id !== id || data.unit !== 'mS/m' || data.data_kind !== 'EXPERIMENTAL_NEXT_AFTER_LAST_OBSERVATION' ||
          data.live_forecast_available !== false || data.deployment_ready !== false || data.gate_decision_eligible !== false ||
          !validMonth(data.target_month?.slice(0, 7)) || !/^\d{4}-\d{2}-01$/.test(data.target_month) ||
          !Array.isArray(data.all_predictions) || !data.selected_prediction || data.selected_prediction.model !== data.selected_model ||
          !Number.isFinite(Date.parse(data.forecast_origin)) || !/(?:Z|[+-]\d{2}:\d{2})$/.test(data.forecast_origin) ||
          Date.parse(data.forecast_origin) >= Date.parse(`${data.target_month}T00:00:00+07:00`) ||
          !data.all_predictions.some(row => row.model === data.selected_prediction.model && row.status === data.selected_prediction.status && row.predicted === data.selected_prediction.predicted) ||
          (data.selected_prediction.status === 'SUCCESS' && !validEc(data.selected_prediction.predicted)) ||
          data.all_predictions.some(row => row.unit !== 'mS/m' || row.station !== data.station || row.target_month !== data.target_month ||
            row.forecast_origin !== data.forecast_origin || (row.status === 'SUCCESS' ? !validEc(row.predicted) : row.predicted != null))) throw new Error('Kết quả lưu không khớp thí nghiệm, tháng hoặc đơn vị hợp lệ.');
      current = data;
      const threshold = experiment.high_ec_metrics?.find(row => row.model === COMPACT_FORECAST_MODEL)?.train_p90_mS_m;
      p90Threshold = validEc(threshold) ? threshold : DEFAULT_P90_MYTHO_MS_M;
      const isCompact = data.selected_model === COMPACT_FORECAST_MODEL && data.station === 'MYTHO';
      $('nextForecastModelInfo').hidden = !isCompact;
      $('nextForecastModelInfo').textContent = COMPACT_FORECAST_SUBTITLE;
      $('nextForecastApplyMap').disabled = !isCompact || data.selected_prediction.status !== 'SUCCESS';
      $("nextForecastValue").textContent = num(data.selected_prediction?.predicted);
      $("nextForecastTarget").textContent = data.target_month.slice(0, 7);
      $("nextForecastStatus").textContent = `${data.station} · ${data.selected_model} · mốc phát hành giả định ${dateOnly(data.forecast_origin)} · độ trễ ${data.availability_lag_days} ngày. ${data.target_is_before_current_month ? "Tháng mục tiêu đã qua; đây là kết quả lưu của thí nghiệm." : "Kết quả thử nghiệm sau mẫu cuối của bộ dữ liệu."} Chưa có thực đo cùng kỳ để đối chiếu kết quả này.`;
      for (const row of data.all_predictions || []) {
        const tr = node("tr");
        tr.append(node("td", row.model), node("td", row.status === "SUCCESS" ? num(row.predicted) : "Chưa tính được"), node("td", row.latest_source_month?.slice(0, 7) || "—"), node("td", Number.isFinite(row.age_latest_months) ? `${num(row.age_latest_months)} tháng` : "—"));
        $("nextForecastRows").append(tr);
      }
      $("nextForecastDownload").disabled = false;
    } catch (error) {
      if (req.isCurrent()) reset(error.message);
    }
  }
  $("nextForecastDownload").addEventListener("click", () => {
    if (current) save(`${current.experiment_id}_next_forecast.json`, current);
  });
  $('nextForecastApplyMap').addEventListener('click', () => {
    if (!current || current.selected_model !== COMPACT_FORECAST_MODEL || current.station !== 'MYTHO' ||
        current.selected_prediction.status !== 'SUCCESS' || !validEc(current.selected_prediction.predicted)) return;
    window.dispatchEvent(new CustomEvent('workspace:apply-forecast-overlay', { detail: {
      sourceModel: COMPACT_FORECAST_MODEL, targetMonth: current.target_month.slice(0, 7),
      mythoEc: current.selected_prediction.predicted, p90Threshold,
      experimentId: current.experiment_id, availabilityLagDays: current.availability_lag_days,
    } }));
  });
  $('nextForecastRestoreTimeline').addEventListener('click', () => {
    window.dispatchEvent(new CustomEvent('workspace:restore-timeline'));
    location.hash = 'observations';
  });
  reset();
  return { reset, load };
}
