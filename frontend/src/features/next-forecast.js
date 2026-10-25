import { $, node, num, save } from "../shared/ui.js";
import { workspaceAPI as api } from "../shared/workspace-api.js";
import { createRequestGate } from "../api.js";
import { dateOnly } from "../research-utils.js";

/** Archived next-step predictions remain tied to their experiment and origin. */
export function createNextForecast() {
  const requests = createRequestGate();
  let current = null;
  function reset(message = "Chọn một thí nghiệm để đọc dự báo sau mẫu cuối.") {
    requests.next();
    current = null;
    $("nextForecastValue").textContent = "—";
    $("nextForecastTarget").textContent = "—";
    $("nextForecastStatus").textContent = message;
    $("nextForecastRows").replaceChildren();
    $("nextForecastDownload").disabled = true;
  }
  async function load(id) {
    reset("Đang đọc kết quả dự báo sau mẫu cuối…");
    const req = requests.next();
    try {
      const data = await api(`/experiments/${encodeURIComponent(id)}/next-forecast`, req);
      if (!req.isCurrent()) return;
      current = data;
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
      if (req.isCurrent()) $("nextForecastStatus").textContent = error.message;
    }
  }
  $("nextForecastDownload").addEventListener("click", () => {
    if (current) save(`${current.experiment_id}_next_forecast.json`, current);
  });
  reset();
  return { reset, load };
}
