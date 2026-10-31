import { node, num, save, saveCSV } from "../shared/ui.js";
import { workspaceAPI as api } from "../shared/workspace-api.js";
import { createRequestGate } from "../api.js";
import { drawSeries } from "../shared/time-series.js";
import { createPredictionHistory } from "./prediction-history.js";
import { cropAdvisories } from "../shared/water-advisory.js";
import { validMonth, inputMonthFor, validPrediction } from '../shared/forecast-contract.js';

export function createMultivariateForecast({ onStation, onPrediction } = {}) {
  const host = document.getElementById("multivariateForecastHost");
  if (!host) return { load: async () => {}, selectStation: async () => false };
  const catalogRequests = createRequestGate();
  const inputRequests = createRequestGate();
  const predictionRequests = createRequestGate();
  const evaluationRequests = createRequestGate();
  let evaluationStation = null;
  let stations = [], archive = null, result = null, busy = false;
  const fields = [
    { name: "rainfall_mm", label: "Lượng mưa", unit: "mm", min: "0" },
    { name: "temperature_degC", label: "Nhiệt độ", unit: "°C" },
    { name: "wind_source_units", label: "Gió", unit: "đơn vị nguồn", min: "0" },
  ];
  host.replaceChildren();
  const form = node("form", undefined, "field-grid mv-form");
  const station = node("select"), month = node("input"), mode = node("select");
  station.name = "station";
  month.name = "target_month";
  month.type = "month";
  month.required = true;
  mode.name = "input_mode";
  for (const [value, label] of [["ARCHIVE", "Dữ liệu khí tượng lưu trữ"], ["MANUAL", "Dữ liệu do người dùng cung cấp"]]) {
    const option = node("option", label);
    option.value = value;
    mode.append(option);
  }
  function labelFor(text, control) {
    const label = node("label", text);
    label.append(control);
    return label;
  }
  form.append(labelFor("Trạm dự báo", station), labelFor("Tháng cần dự báo EC", month), labelFor("Nguồn đầu vào", mode));
  const inputMonth = node("p", "Chọn trạm và tháng để đọc kỳ dữ liệu đầu vào.", "subtle wide");
  form.append(inputMonth);
  const controls = new Map(), fieldLabels = new Map();
  for (const field of fields) {
    const control = node("input");
    control.type = "number";
    control.step = "any";
    control.name = field.name;
    control.required = true;
    if (field.min !== undefined) control.min = field.min;
    const title = node("span", `${field.label} (${field.unit})`);
    const label = node("label");
    label.append(title, control);
    form.append(label);
    controls.set(field.name, control);
    fieldLabels.set(field.name, title);
  }
  const source = node("p", "", "subtle wide");
  const submit = node("button", "Chạy dự báo đa biến");
  submit.type = "submit";
  submit.disabled = true;
  const action = node("div", undefined, "wide mv-actions");
  action.append(submit);
  const persistRun = node('input');
  persistRun.type = 'checkbox';
  persistRun.checked = true;
  const persistLabel = node('label', 'Lưu lượt chạy vào PostgreSQL');
  persistLabel.prepend(persistRun);
  action.append(persistLabel);
  form.append(source, action);
  const status = node("p", "Đang tải danh mục mô hình…", "subtle mv-status");
  status.setAttribute("role", "status");
  const modelInfo = node("p", "", "subtle mv-model-info");
  const output = node("section", undefined, "mv-result");
  output.setAttribute("aria-live", "polite");
  const exports = node("div", undefined, "download-links mv-exports");
  const jsonButton = node("button", "Tải dự báo JSON ↓", "secondary");
  const csvButton = node("button", "Tải dự báo CSV ↓", "secondary");
  const mapButton = node("button", "Xem dự báo trên bản đồ", "secondary");
  const gateButton = node("button", "Tham khảo trong mô phỏng cống", "secondary");
  gateButton.type = "button";
  gateButton.disabled = true;
  jsonButton.type = csvButton.type = mapButton.type = "button";
  jsonButton.disabled = csvButton.disabled = mapButton.disabled = true;
  exports.append(mapButton, jsonButton, csvButton, gateButton);
  host.append(form, status, modelInfo, output, exports);
  const evaluation = node("details", undefined, "mv-evaluation");
  const evaluationSummary = node("summary", "Đánh giá mô hình đa biến và các mô hình tham chiếu");
  const evaluationStatus = node("p", "", "subtle");
  evaluationStatus.setAttribute("role", "status");
  const evaluationChart = node("div", undefined, "mv-evaluation-chart");
  const evaluationLegend = node("p", "Thực đo: xanh đậm · Random Forest: cam · Persistence: xanh lam nét đứt.", "subtle");
  const evaluationMetrics = node("div", undefined, "mv-evaluation-metrics");
  evaluation.append(evaluationSummary, evaluationStatus, evaluationChart, evaluationLegend, evaluationMetrics);
  host.append(evaluation);
  const predictionHistory = createPredictionHistory(host, {
    onSaved(data) {
      result = data;
      renderResult(data);
      jsonButton.disabled = csvButton.disabled = mapButton.disabled = gateButton.disabled = false;
      window.dispatchEvent(new CustomEvent("workspace:multivariate-prediction", { detail: data }));
      onPrediction?.(data);
      status.textContent = "Đã cập nhật kết quả theo lượt mô hình được máy chủ chạy lại và lưu trong PostgreSQL.";
    },
  });

  async function loadEvaluation() {
    const req = evaluationRequests.next(), selected = station.value;
    evaluationStation = selected;
    evaluationChart.replaceChildren();
    evaluationMetrics.replaceChildren();
    evaluationLegend.hidden = true;
    evaluationStatus.textContent = "Đang tải đánh giá của mô hình đa biến…";
    if (!selected) { evaluationStatus.textContent = "Chọn trạm để xem đánh giá."; return; }
    try {
      const data = await api(`/multivariate/evaluation?${new URLSearchParams({ station: selected })}`, req);
      if (!req.isCurrent() || station.value !== selected) return;
      if (data.station !== selected || data.unit !== "mS/m" || !Array.isArray(data.items)) throw new Error("Đánh giá trả về không khớp trạm hoặc đơn vị EC.");
      evaluationStatus.textContent = `Đánh giá hồi cứu ${data.period} · phiên bản ${data.model_version}. So sánh trên cùng các tháng có đủ dữ liệu; đây là đánh giá mô hình khí tượng đa biến.`;
      const series = [
        { key: "actual", label: "EC thực đo", color: "#12675a" },
        { key: "RandomForest", label: "Random Forest đa biến", color: "#c26728" },
        { key: "Persistence", label: "Persistence", color: "#2676aa", dashed: true },
      ];
      const rows = data.items.filter(item => /^\d{4}-(0[1-9]|1[0-2])(?:-01)?$/.test(item.target_month || "")).sort((a, b) => a.target_month.localeCompare(b.target_month));
      drawSeries(evaluationChart, series.map(item => ({ ...item, points: rows.map(row => ({ date: `${row.target_month.slice(0, 7)}-01`, value: row[item.key] })) })), { title: "EC thực đo và dự báo đa biến trên tập kiểm định", connected: true });
      evaluationLegend.hidden = false;
      const table = node("table"), head = node("thead"), header = node("tr"), body = node("tbody");
      for (const label of ["Mô hình", "MAE (mS/m)", "RMSE (mS/m)", "Số tháng (n)"]) header.append(node("th", label));
      head.append(header);
      for (const [key, label] of [["RandomForest", "Random Forest đa biến"], ["Persistence", "Persistence · EC mới nhất khả dụng (t−2)"], ["SeasonalNaive", "Seasonal Naive · cùng tháng năm trước"], ["MonthlyClimatology", "Trung bình EC theo tháng trong tập huấn luyện"]]) {
        const metric = data.metrics?.[key] || {}, row = node("tr");
        for (const value of [label, num(metric.mae_mS_m), num(metric.rmse_mS_m), metric.n ?? "—"]) row.append(node("td", String(value)));
        body.append(row);
      }
      table.append(head, body);
      evaluationMetrics.append(table, node("p", "Sai số nhỏ hơn là tốt hơn. Đối chiếu Random Forest với các mô hình tham chiếu trước khi diễn giải mức cải thiện; sai số kiểm định không đảm bảo độ chính xác của từng tháng tương lai.", "subtle"));
    } catch (error) {
      if (req.isCurrent() && station.value === selected) evaluationStatus.textContent = error.message;
    }
  }

  const currentStation = () => stations.find(item => item.station === station.value);
  const textValue = value => value == null ? "Chưa có" : typeof value === "object" ? JSON.stringify(value) : String(value);
  function refreshButton() {
    submit.disabled = busy || !currentStation() || !validMonth(month.value) || !inputMonthFor(month.value) || (mode.value === "ARCHIVE" && archive?.complete !== true);
  }
  function clearResult(message = "Đầu vào đã thay đổi. Chạy lại mô hình để xem dự báo mới.") {
    predictionRequests.next();
    busy = false;
    result = null;
    predictionHistory.setCandidate(null);
    window.dispatchEvent(new CustomEvent("workspace:multivariate-clear"));
    output.replaceChildren();
    jsonButton.disabled = csvButton.disabled = mapButton.disabled = gateButton.disabled = true;
    status.textContent = message;
    refreshButton();
  }
  function describeModel() {
    const selected = currentStation();
    if (!selected) return;
    const cutoff = String(selected.trained_through || "").slice(0, 7);
    if (/^\d{4}-(0[1-9]|1[0-2])$/.test(cutoff)) {
      const [year, number] = cutoff.split("-").map(Number);
      const index = year * 12 + number;
      month.min = `${String(Math.floor(index / 12)).padStart(4, '0')}-${String(index % 12 + 1).padStart(2, '0')}`;
    } else month.removeAttribute("min");
    modelInfo.textContent = `Mô hình: ${textValue(selected.model)} · huấn luyện đến ${textValue(selected.trained_through)} · trạm ${selected.site_name || selected.station}.`;
    for (const field of fields) {
      const feature = selected.features?.find(item => item.name === field.name);
      fieldLabels.get(field.name).textContent = `${feature?.label || field.label} (${feature?.unit || field.unit})`;
    }
  }
  function applyMode() {
    const manual = mode.value === "MANUAL";
    for (const control of controls.values()) control.readOnly = !manual;
    if (manual) {
      source.textContent = "Đầu vào do người dùng cung cấp. Nếu chỉnh sửa dữ liệu đã nạp, kết quả sẽ ghi nguồn MANUAL; đây là dự báo của mô hình từ các điều kiện bạn nhập.";
    } else if (archive) {
      source.textContent = `Nguồn: ${textValue(archive.source)} · quan trắc đến ${textValue(archive.observed_through)} · thời điểm sẵn có giả định: ${textValue(archive.assumed_available_at)}.`;
      for (const field of fields) controls.get(field.name).value = Number.isFinite(archive[field.name]) ? archive[field.name] : "";
    } else source.textContent = "Chưa có đầu vào lưu trữ cho kỳ đã chọn. Có thể chọn dữ liệu do người dùng cung cấp.";
    refreshButton();
  }
  async function loadInputs() {
    const req = inputRequests.next();
    archive = null;
    clearResult("Đang đọc dữ liệu đầu vào…");
    for (const control of controls.values()) control.value = "";
    describeModel();
    if (evaluationStation !== station.value) loadEvaluation();
    applyMode();
    if (!station.value || !validMonth(month.value) || !inputMonthFor(month.value)) {
      inputMonth.textContent = 'Chưa xác định kỳ khí tượng đầu vào.';
      status.textContent = "Chọn trạm và tháng dự báo hợp lệ.";
      return;
    }
    const target = month.value;
    const previous = inputMonthFor(target);
    inputMonth.textContent = `Dự báo EC tháng ${target} từ dữ liệu khí tượng tháng ${previous}.`;
    try {
      const data = await api(`/multivariate/inputs?${new URLSearchParams({ station: station.value, target_month: target })}`, req);
      if (!req.isCurrent()) return;
      if (data.station !== station.value || data.target_month !== target || data.input_month !== previous || data.wind_unit !== 'm/s' ||
          (data.complete === true && fields.some(field => !Number.isFinite(data[field.name]) || (field.min === '0' && data[field.name] < 0)))) throw new Error("Đầu vào trả về không khớp trạm, kỳ khí tượng hoặc đơn vị hợp lệ.");
      archive = data;
      inputMonth.textContent = `Dự báo EC tháng ${target} · kỳ khí tượng đầu vào: ${data.input_month || previous}.`;
      if (data.wind_unit) fieldLabels.get("wind_source_units").textContent = `Gió (${data.wind_unit})`;
      // An explicit manual choice can start from the visible archived values.
      for (const field of fields) controls.get(field.name).value = Number.isFinite(data[field.name]) ? data[field.name] : "";
      applyMode();
      status.textContent = data.complete ? "Đã nạp đầu vào. Có thể chạy dự báo đa biến." : "Kỳ lưu trữ thiếu dữ liệu. Chọn dữ liệu do người dùng cung cấp và điền đủ ba biến để dự báo.";
    } catch (error) {
      if (!req.isCurrent()) return;
      status.textContent = error.message;
      applyMode();
    }
  }
  function renderResult(data) {
    output.replaceChildren();
    output.append(node("span", "DỰ BÁO EC THÁNG · MÔ HÌNH ĐA BIẾN", "tag"));
    output.append(node("h3", `${num(data.predicted_ec_mS_m)} mS/m`, "mv-predicted-ec"));
    output.append(node("p", `${currentStation()?.site_name || data.station} · tháng ${data.target_month} · nguồn đầu vào ${data.input_mode === "MANUAL" ? "người dùng cung cấp" : "lưu trữ"}`));
    const distribution = data.ensemble_distribution;
    if (distribution?.unit === 'mS/m' && [distribution.p10, distribution.p90].every(Number.isFinite) && distribution.p10 <= distribution.p90) {
      const spread = node('section', undefined, 'mv-tree-spread');
      spread.append(node('h4', 'Mức phân tán giữa các cây Random Forest'));
      spread.append(node('p', `P10–P90: ${num(distribution.p10)}–${num(distribution.p90)} mS/m`, 'mv-spread-range'));
      const details = [
        ['P25', distribution.p25], ['P50', distribution.p50], ['P75', distribution.p75],
        ['IQR', distribution.iqr], ['Độ lệch chuẩn', distribution.std],
      ].filter(([, value]) => Number.isFinite(value)).map(([label, value]) => `${label}: ${num(value)} mS/m`);
      if (details.length) spread.append(node('p', details.join(' · '), 'subtle'));
      spread.append(node('p', `${Number.isInteger(distribution.n_estimators) ? `${distribution.n_estimators} cây. ` : ''}P10–P90 mô tả phân tán dự đoán giữa các cây; chưa phải khoảng dự báo hoặc khoảng tin cậy được hiệu chuẩn và không bao quát toàn bộ sai số thực tế.`, 'subtle'));
      output.append(spread);
    } else {
      output.append(node('p', 'Lượt chạy này chưa có phân phối dự đoán giữa các cây. Có thể chạy lại mô hình để cập nhật.', 'subtle'));
    }
    const cropSection = node('section', undefined, 'mv-crop-advisory');
    cropSection.append(node('h4', 'Đối chiếu EC dự báo với kịch bản cây trồng'));
    const cropTable = node('table'), cropHead = node('thead'), cropHeader = node('tr'), cropBody = node('tbody');
    for (const label of ['Cây trồng', 'Ngưỡng thấp / cao (mS/m)', 'Đối chiếu kịch bản']) cropHeader.append(node('th', label));
    cropHead.append(cropHeader);
    for (const item of cropAdvisories(data.predicted_ec_mS_m)) {
      const row = node('tr', undefined, `crop-advisory-${item.status}`);
      for (const text of [item.label, `${item.openBelowEc} / ${item.closeAboveEc}`, item.text]) row.append(node('td', text));
      cropBody.append(row);
    }
    cropTable.append(cropHead, cropBody);
    const cropTableWrap = node('div', undefined, 'table-wrap');
    cropTableWrap.append(cropTable);
    cropSection.append(cropTableWrap, node('p', 'Các ngưỡng minh họa dùng chung với mô phỏng bản đồ, chưa được xác nhận là tiêu chuẩn tưới. EC trung bình tháng không thay số đo tại vườn/cống và không xác nhận nước dùng cho sinh hoạt. Chưa quy đổi EC dự báo sang độ mặn vì thiếu hiệu chuẩn phù hợp.', 'subtle'));
    output.append(cropSection);
    if (data.target_is_before_current_month) output.append(node("p", "Dự báo hồi cứu: tháng mục tiêu nằm trong quá khứ. Đối chiếu mốc huấn luyện và thời điểm sẵn có của đầu vào khi diễn giải kết quả.", "mv-retrospective"));
    output.append(node("p", `Phiên bản ${textValue(data.model_version)} · phát hành ${textValue(data.issued_at)} · mã ${textValue(data.prediction_id)}`, "subtle"));
    const table = node("table", undefined, "mv-input-table");
    const head = node("thead"), header = node("tr");
    for (const title of ["Biến đầu vào", "Giá trị", "Đơn vị", "Nguồn"]) header.append(node("th", title));
    head.append(header);
    const body = node("tbody");
    for (const item of data.inputs || []) {
      const row = node("tr");
      for (const value of [item.label || item.name, num(item.value), item.unit, textValue(item.source)]) row.append(node("td", value));
      body.append(row);
    }
    table.append(head, body);
    output.append(node("h4", `Đầu vào tháng ${data.input_month || "—"}`), table);
    const training = data.training || {}, metrics = data.metrics || {};
    output.append(node("p", `Huấn luyện đến ${textValue(training.through)} · ${textValue(training.samples)} mẫu. Sai số kiểm định: MAE ${num(metrics.mae_mS_m)} mS/m · RMSE ${num(metrics.rmse_mS_m)} mS/m · n = ${textValue(metrics.n)}.`, "mv-validation"));
    output.append(node("p", "MAE và RMSE mô tả sai số trên tập kiểm định; không phải khoảng tin cậy của dự báo riêng này. Kết quả EC theo tháng phục vụ đánh giá và lập kế hoạch.", "subtle"));
    if (data.feature_importance?.length) {
      output.append(node("h4", "Độ quan trọng của biến trong mô hình"));
      const list = node("ul", undefined, "mv-importance");
      for (const item of data.feature_importance) list.append(node("li", `${item.label || item.name}: ${num(item.importance)}`));
      output.append(list, node("p", "Độ quan trọng của biến mô tả mô hình, không chứng minh quan hệ nhân quả.", "subtle"));
    }
  }
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (!form.reportValidity() || submit.disabled) return;
    clearResult("Đang chạy mô hình dự báo đa biến…");
    const req = predictionRequests.next();
    const payload = { station: station.value, target_month: month.value, input_mode: mode.value };
    if (mode.value === "MANUAL") {
      for (const field of fields) {
        const value = controls.get(field.name).value.trim();
        if (!value || !Number.isFinite(Number(value))) {
          status.textContent = "Cần đủ ba biến khí tượng với giá trị số hữu hạn.";
          return;
        }
        payload[field.name] = Number(value);
      }
    }
    busy = true;
    refreshButton();
    try {
      const persist = persistRun.checked;
      const response = await api(persist ? '/multivariate/history' : '/multivariate/predict', { ...req, method: 'POST', body: payload, timeoutMs: 120_000 });
      const data = persist ? response.prediction : response;
      if (!req.isCurrent()) return;
      if (!validPrediction(data, { ...payload, site_code: currentStation()?.site_code })) throw new Error("Kết quả dự báo không khớp yêu cầu, đầu vào hoặc đơn vị hợp lệ.");
      result = data;
      renderResult(data);
      predictionHistory.setCandidate(persist ? null : payload);
      predictionHistory.record(data);
      jsonButton.disabled = csvButton.disabled = mapButton.disabled = gateButton.disabled = false;
      window.dispatchEvent(new CustomEvent("workspace:multivariate-prediction", { detail: data }));
      onPrediction?.(data);
      status.textContent = persist
        ? `Đã lưu dự báo PostgreSQL · ${data.prediction_id} · ${response.saved_at}. Có thể xem lại trong lịch sử.`
        : 'Đã chạy mô hình dự báo EC đa biến; chưa lưu PostgreSQL. Có thể tải JSON/CSV hoặc lưu riêng.';
    } catch (error) {
      if (req.isCurrent()) status.textContent = error.message;
    } finally {
      if (req.isCurrent()) { busy = false; refreshButton(); }
    }
  });
  station.addEventListener("change", () => { onStation?.(currentStation()?.site_code); loadInputs(); });
  month.addEventListener("input", loadInputs);
  mode.addEventListener("change", () => {
    inputRequests.next();
    clearResult();
    applyMode();
    if (mode.value === "ARCHIVE" && !archive) loadInputs();
  });
  for (const control of controls.values()) control.addEventListener("input", () => {
    inputRequests.next();
    clearResult();
  });
  jsonButton.addEventListener("click", () => { if (result) save(`${result.station}_${result.target_month}_multivariate.json`, result); });
  mapButton.addEventListener("click", () => {
    if (result) window.dispatchEvent(new CustomEvent("workspace:show-forecast-map", { detail: result }));
  });
  gateButton.addEventListener("click", () => {
    if (!result) return;
    window.dispatchEvent(new CustomEvent("workspace:apply-forecast-to-gate", { detail: result }));
    location.hash = "gates";
  });
  csvButton.addEventListener("click", () => {
    if (!result) return;
    const common = { prediction_id: result.prediction_id, model_version: result.model_version, station: result.station, site_code: result.site_code, target_month: result.target_month, predicted_ec_mS_m: result.predicted_ec_mS_m, unit: result.unit, data_kind: result.data_kind, input_mode: result.input_mode, input_month: result.input_month, issued_at: result.issued_at };
    for (const key of ['p10', 'p25', 'p50', 'p75', 'p90', 'iqr', 'std', 'n_estimators', 'unit', 'method', 'interpretation']) common[`ensemble_${key}`] = result.ensemble_distribution?.[key] ?? '';
    const rows = (result.inputs?.length ? result.inputs : [{}]).map(item => ({ ...common, input_name: item.name, input_value: item.value, input_unit: item.unit, input_source: textValue(item.source) }));
    saveCSV(`${result.station}_${result.target_month}_multivariate.csv`, rows, Object.keys(rows[0]));
  });
  async function load() {
    const req = catalogRequests.next();
    inputRequests.next();
    archive = null; stations = [];
    station.replaceChildren();
    for (const control of controls.values()) control.value = '';
    modelInfo.textContent = ''; source.textContent = ''; inputMonth.textContent = 'Chưa xác định kỳ khí tượng đầu vào.';
    evaluationRequests.next();
    evaluationStation = null;
    evaluationChart.replaceChildren();
    evaluationMetrics.replaceChildren();
    evaluationLegend.hidden = true;
    evaluationStatus.textContent = "Đang tải danh mục mô hình…";
    clearResult("Đang tải danh mục mô hình…");
    try {
      const data = await api("/multivariate/catalog", req);
      if (!req.isCurrent()) return;
      if (!Array.isArray(data.stations)) throw new Error("Danh mục mô hình không hợp lệ.");
      stations = data.stations;
      predictionHistory.setStations(stations);
      window.dispatchEvent(new CustomEvent("workspace:multivariate-catalog", { detail: data }));
      station.replaceChildren();
      for (const item of stations) {
        const option = node("option", item.site_name || item.station);
        option.value = item.station;
        station.append(option);
      }
      month.value = validMonth(data.default_target_month) ? data.default_target_month : '';
      if (!stations.length) { status.textContent = "Chưa có mô hình đa biến sẵn sàng."; refreshButton(); return; }
      await loadInputs();
    } catch (error) {
      if (req.isCurrent()) { status.textContent = error.message; refreshButton(); }
    }
  }
  async function selectStation(code) {
    const match = stations.find(item => item.site_code === code || item.station === code);
    if (!match) {
      inputRequests.next();
      archive = null;
      station.value = '';
      for (const control of controls.values()) control.value = '';
      modelInfo.textContent = ''; source.textContent = '';
      inputMonth.textContent = 'Chưa xác định kỳ khí tượng đầu vào.';
      evaluationRequests.next(); evaluationStation = null;
      evaluationChart.replaceChildren(); evaluationMetrics.replaceChildren(); evaluationLegend.hidden = true;
      evaluationStatus.textContent = 'Điểm này chưa có mô hình đa biến đã đăng ký.';
      clearResult('Điểm này chưa có mô hình đa biến đã đăng ký. Chọn một trạm trong danh mục để chạy dự báo.');
      return false;
    }
    if (station.value !== match.station) { station.value = match.station; await loadInputs(); }
    return true;
  }
  applyMode();
  return { load, selectStation };
}
