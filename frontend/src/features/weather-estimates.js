import { $, num, node, saveCSV } from "../shared/ui.js";
import { workspaceAPI as api } from "../shared/workspace-api.js";
import { createRequestGate } from "../api.js";
import { drawSeries } from "../research-chart.js";

export function createWeatherEstimates() {
  const requests = createRequestGate();
  let displayed = null;
  async function load() {
    const station = $("futureStationSelect").value;
    const req = requests.next();
    displayed = null;
    $("downloadFutureCsv").disabled = true;
    $("futureStatus").textContent = "Đang đọc ước tính hồi cứu…";
    $("futureTableRows").replaceChildren();
    $("futureEcChart").replaceChildren();
    for (const id of ["kpiFutureMax", "kpiFutureAvg", "kpiFutureMaxMonth"]) $(id).textContent = "—";
    try {
      const data = await api(`/monthly-estimates?station=${encodeURIComponent(station)}`, req);
      if (!req.isCurrent()) return;
      displayed = {
        station,
        items: data.items.map((row) => ({
          ...row,
          data_kind: data.data_kind,
          unit: data.unit,
          live_forecast_available: data.live_forecast_available,
          gate_decision_eligible: data.gate_decision_eligible
        }))
      };
      $("futureStatus").textContent = `${data.items.length} tháng · ước tính hồi cứu từ khí tượng Open-Meteo; chưa có đánh giá với EC thực đo cùng kỳ. Không suy ra độ mặn hoặc an toàn lấy nước.`;
      $("downloadFutureCsv").disabled = !data.items.length;
      $("kpiFutureMax").textContent = Number.isFinite(data.max_ec?.predicted_ec_mS_m) ? num(data.max_ec.predicted_ec_mS_m) : "—";
      $("kpiFutureMaxMonth").textContent = data.max_ec?.year_month || "—";
      $("kpiFutureAvg").textContent = Number.isFinite(data.avg_ec) && data.items.length ? num(data.avg_ec) : "—";
      const series = [{
        label: "EC ước tính hồi cứu",
        color: "#087f78",
        points: data.items.map(row => ({
          date: row.year_month + "-01",
          value: row.predicted_ec_mS_m,
        })),
      }];
      drawSeries($("futureEcChart"), series, {
        title: `EC ước tính hồi cứu tại ${station}`,
        connected: true,
      });
      for (const row of data.items) {
        const tr = node("tr");
        const values = [
          row.year_month,
          num(row.predicted_ec_mS_m),
          num(row.rainfall_mm),
          num(row.temperature_degC),
          num(row.wind_m_s),
        ];
        for (const value of values) {
          tr.append(node("td", value));
        }
        $("futureTableRows").append(tr);
      }
    } catch (error) {
      if (req.isCurrent()) $("futureStatus").textContent = error.message;
    }
  }
  $("futureStationSelect").addEventListener("change", load);
  $("retryFuture").addEventListener("click", load);
  $("downloadFutureCsv").addEventListener("click", () => {
    if (displayed) {
      saveCSV(`${displayed.station}_ec_weather_estimate.csv`, displayed.items, [
        "station",
        "year_month",
        "predicted_ec_mS_m",
        "rainfall_mm",
        "temperature_degC",
        "wind_m_s",
        "model",
        "data_kind",
        "unit",
        "live_forecast_available",
        "gate_decision_eligible"
      ]);
    }
  });
  return { load };
}
