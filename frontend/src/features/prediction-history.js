import { node, num, save, saveCSV } from "../shared/ui.js";
import { workspaceAPI as api } from "../shared/workspace-api.js";
import { createRequestGate } from "../api.js";

export function createPredictionHistory(host, { onSaved } = {}) {
  const requests = createRequestGate();
  let candidate = null, candidateVersion = 0, saving = false, rows = [], offset = 0, total = 0;
  const session = [];
  const saveButton = node("button", "Chạy và lưu dự báo vào PostgreSQL", "secondary");
  saveButton.type = "button"; saveButton.disabled = true;
  const saveStatus = node("p", "Lưu sẽ chạy lại mô hình trên máy chủ với cùng yêu cầu và lưu kết quả máy chủ tạo ra.", "subtle");
  saveStatus.setAttribute("role", "status");
  host.append(saveButton, saveStatus);

  const comparison = node("details", undefined, "mv-scenario-history"); comparison.hidden = true;
  const summary = node("summary", "So sánh các lượt dự báo trong phiên");
  const comparisonTable = node("div", undefined, "table-wrap");
  const download = node("button", "Tải bảng so sánh CSV", "secondary");
  const clear = node("button", "Xóa bảng so sánh phiên", "text-button");
  download.type = clear.type = "button";
  comparison.append(summary, node("p", "Chênh lệch chỉ so với lượt đầu cùng trạm, tháng và phiên bản mô hình. Bảng phiên mất khi tải lại trang; lịch sử PostgreSQL được lưu riêng.", "subtle"), comparisonTable, download, clear);
  host.append(comparison);
  const history = node("details", undefined, "mv-prediction-history");
  history.append(node("summary", "Lịch sử dự báo đã lưu trong PostgreSQL"));
  const filters = node("form", undefined, "field-grid");
  const station = node("select"), month = node("input"); month.type = "month";
  station.append(new Option("Tất cả trạm", ""));
  const stationLabel = node("label", "Trạm"), monthLabel = node("label", "Tháng dự báo (để trống: tất cả)");
  stationLabel.append(station); monthLabel.append(month);
  const reload = node("button", "Tải lịch sử PostgreSQL", "secondary"); reload.type = "submit";
  filters.append(stationLabel, monthLabel, reload);
  const status = node("p", "Nhấn Tải lịch sử để đọc các dự báo đã lưu.", "subtle"); status.setAttribute("role", "status");
  const tableHost = node("div", undefined, "table-wrap");
  const paging = node("div", undefined, "download-links");
  const previous = node("button", "Trang trước", "secondary"), next = node("button", "Trang sau", "secondary"), count = node("span", "0 lượt");
  previous.type = next.type = "button"; previous.disabled = next.disabled = true;
  paging.append(previous, count, next); history.append(filters, status, tableHost, paging); host.append(history);
  function table(headers) {
    const element = node("table"), head = node("thead"), tr = node("tr"), body = node("tbody");
    for (const text of headers) { const th = node("th", text); th.scope = "col"; tr.append(th); }
    head.append(tr); element.append(head, body); return { element, body };
  }
  function renderComparison() {
    comparison.hidden = !session.length;
    summary.textContent = `So sánh các lượt dự báo trong phiên (${session.length})`;
    comparisonTable.replaceChildren();
    const { element, body } = table(["Lượt", "Trạm", "Tháng", "Nguồn", "Mưa (mm)", "Nhiệt (°C)", "Gió (m/s)", "EC (mS/m)", "Chênh so với mốc cùng nhóm"]);
    for (const item of session) {
      const first = session.find(row => row.station === item.station && row.target_month === item.target_month && row.model_version === item.model_version);
      const diff = item.predicted_ec_mS_m - first.predicted_ec_mS_m;
      const tr = node("tr");
      for (const value of [item.run_index, item.station, item.target_month, item.input_mode, num(item.rainfall_mm), num(item.temperature_degC), num(item.wind_source_units), num(item.predicted_ec_mS_m), first === item ? "Mốc nhóm" : `${diff >= 0 ? "+" : ""}${num(diff)} mS/m`]) tr.append(node("td", String(value)));
      body.append(tr);
    }
    comparisonTable.append(element);
  }
  function record(data) {
    const get = name => data.inputs?.find(item => item.name === name)?.value;
    session.push({ run_index: session.length + 1, prediction_id: data.prediction_id, station: data.station, target_month: data.target_month, input_mode: data.input_mode, input_month: data.input_month, rainfall_mm: get("rainfall_mm"), temperature_degC: get("temperature_degC"), wind_source_units: get("wind_source_units"), predicted_ec_mS_m: data.predicted_ec_mS_m, model_version: data.model_version, issued_at: data.issued_at });
    renderComparison();
  }
  function renderHistory() {
    tableHost.replaceChildren();
    if (!rows.length) { tableHost.append(node("p", "Chưa có dự báo đã lưu trong bộ lọc này.", "subtle")); return; }
    const { element, body } = table(["Trạm", "Tháng", "EC (mS/m)", "Nguồn đầu vào", "Mô hình", "Thời điểm lưu", "Chi tiết"]);
    for (const item of rows) {
      const prediction = item.prediction, tr = node("tr");
      for (const value of [prediction.station, prediction.target_month, num(prediction.predicted_ec_mS_m), prediction.input_mode, prediction.model_version, item.saved_at]) tr.append(node("td", String(value ?? "—")));
      const actions = node("td"), details = node("details"), summary = node("summary", "Xem đầu vào"), list = node("ul");
      for (const input of prediction.inputs || []) list.append(node("li", `${input.label || input.name}: ${num(input.value)} ${input.unit || ""} · ${typeof input.source === "object" ? JSON.stringify(input.source) : input.source || ""}`));
      details.append(summary, node("p", `Mã: ${prediction.prediction_id} · Kỳ đầu vào: ${prediction.input_month} · Phát hành: ${prediction.issued_at}`, "subtle"), list);
      const exportButton = node("button", "JSON", "text-button"), mapButton = node("button", "Bản đồ", "text-button");
      exportButton.type = mapButton.type = "button";
      exportButton.addEventListener("click", () => save(`${prediction.station}_${prediction.target_month}_${prediction.prediction_id}.json`, item));
      mapButton.addEventListener("click", () => window.dispatchEvent(new CustomEvent("workspace:show-forecast-map", { detail: prediction })));
      actions.append(details, exportButton, mapButton); tr.append(actions); body.append(tr);
    }
    tableHost.append(element);
  }
  async function loadHistory(pageOffset = 0) {
    const req = requests.next(); offset = pageOffset;
    reload.disabled = previous.disabled = next.disabled = true;
    rows = []; tableHost.replaceChildren(); count.textContent = "Đang tải…";
    status.textContent = "Đang đọc lịch sử PostgreSQL…";
    const params = new URLSearchParams({ limit: "20", offset: String(offset) });
    if (station.value) params.set("station", station.value);
    if (month.value) params.set("target_month", month.value);
    try {
      const data = await api(`/multivariate/history?${params}`, req);
      if (!req.isCurrent()) return;
      if (!Array.isArray(data.items) || !Number.isSafeInteger(data.total) || data.offset !== offset || data.items.some(item => !item.prediction || !Number.isFinite(item.prediction.predicted_ec_mS_m))) throw new Error("Lịch sử trả về không hợp lệ.");
      rows = data.items; total = data.total; renderHistory();
      count.textContent = rows.length ? `${offset + 1}–${offset + rows.length} / ${total} lượt` : "0 lượt";
      status.textContent = "Lịch sử đã lưu trong PostgreSQL; xem từng lượt để đối chiếu đầu vào và phiên bản mô hình.";
      previous.disabled = offset === 0; next.disabled = offset + rows.length >= total;
    } catch (error) { if (req.isCurrent()) { status.textContent = error.message; count.textContent = "Chưa tải được"; } }
    finally { if (req.isCurrent()) reload.disabled = false; }
  }
  saveButton.addEventListener("click", async () => {
    if (!candidate || saving) return;
    const payload = { ...candidate }, version = candidateVersion;
    saving = true; saveButton.disabled = true;
    saveStatus.textContent = "Máy chủ đang chạy lại mô hình và lưu dự báo vào PostgreSQL…";
    try {
      const saved = await api("/multivariate/history", { method: "POST", body: payload, timeoutMs: 120_000 });
      const prediction = saved.prediction;
      if (!prediction || prediction.station !== payload.station || prediction.target_month !== payload.target_month || prediction.unit !== "mS/m" || !Number.isFinite(prediction.predicted_ec_mS_m)) throw new Error("Phản hồi lưu dự báo không khớp yêu cầu.");
      record(prediction);
      if (version === candidateVersion) onSaved?.(prediction);
      saveStatus.textContent = `Đã lưu lượt máy chủ tạo ${prediction.prediction_id} lúc ${saved.saved_at}.${version !== candidateVersion ? " Bộ chọn hiện tại đã thay đổi; kết quả lưu nằm trong lịch sử." : " Kết quả hiển thị đã cập nhật theo lượt được lưu."}`;
      history.open = true;
      loadHistory(0);
    } catch (error) { saveStatus.textContent = `Chưa lưu được: ${error.message} Dự báo hiện tại vẫn có thể tải JSON/CSV.`; }
    finally { saving = false; saveButton.disabled = !candidate; }
  });
  filters.addEventListener("submit", event => { event.preventDefault(); loadHistory(0); });
  for (const control of [station, month]) control.addEventListener("input", () => {
    requests.next(); rows = []; tableHost.replaceChildren(); previous.disabled = next.disabled = true; reload.disabled = false;
    count.textContent = "Chưa áp dụng"; status.textContent = "Bộ lọc đã đổi. Nhấn Tải lịch sử để cập nhật.";
  });
  previous.addEventListener("click", () => loadHistory(Math.max(0, offset - 20)));
  next.addEventListener("click", () => loadHistory(offset + 20));
  download.addEventListener("click", () => { if (session.length) saveCSV("multivariate_scenarios_comparison.csv", session, Object.keys(session[0])); });
  clear.addEventListener("click", () => { session.length = 0; renderComparison(); });
  return {
    record,
    setCandidate(payload) { candidate = payload ? { ...payload } : null; candidateVersion++; saveButton.disabled = saving || !candidate; },
    setStations(items) {
      const selected = station.value;
      station.replaceChildren(new Option("Tất cả trạm", ""), ...items.map(item => new Option(item.site_name || item.station, item.station)));
      if (!selected || items.some(item => item.station === selected)) {
        station.value = selected;
        return;
      }
      requests.next();
      rows = []; offset = 0; total = 0;
      tableHost.replaceChildren();
      previous.disabled = next.disabled = true;
      reload.disabled = false;
      count.textContent = "Chưa áp dụng";
      status.textContent = "Trạm đã chọn không còn trong danh mục. Nhấn Tải lịch sử để xem tất cả trạm.";
    },
  };
}
