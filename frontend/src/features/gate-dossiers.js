import { $, num, node, save } from "../shared/ui.js";
import { workspaceAPI as api } from "../shared/workspace-api.js";
import { createRequestGate } from "../api.js";
import { labels } from "../research-utils.js";
import { loadThresholdPresets, populateThresholdPresets, presetReference } from "../shared/threshold-presets.js";
import { createSpatialGateDraft } from "./gate-simulation-draft.js";

export function createGateDossiers(map) {
  const state = { gates: [], input: null, policy: null, evaluation: null };
  const gateRequests = createRequestGate();
  const evaluationRequests = createRequestGate();
  const fieldRequests = createRequestGate();
  const databaseDraftRequests = createRequestGate();
  let presets = [], selectedPreset = null, forecastContext = null, simulationContext = null;
  const fileRequests = { input: createRequestGate(), policy: createRequestGate() };
  const draftKey = () => `gate-scenario-v1:${$("gateSelect").value}`;
  function populateForm() {
    const form = $("fieldForm");
    const set = (name, value) => { if (form.elements[name]) form.elements[name].value = value ?? ""; };
    set("mode", state.input?.mode || "INTAKE");
    for (const key of ["outside_level", "inside_level", "outside_quality", "inside_quality"]) set(key, state.input?.observations?.[key]?.value);
    const row = state.input?.observations?.outside_level;
    if (row?.observed_at && Number.isFinite(Date.parse(row.observed_at))) set("observed", new Date(Date.parse(row.observed_at) + 7 * 3600000).toISOString().slice(0, 16));
    else set("observed", "");
    set("datum", state.policy?.vertical_datum || row?.vertical_datum);
    set("reference", row?.source_reference);
    set("method", state.input?.observations?.outside_quality?.method_reference);
    set("ec_basis", state.policy?.parameter?.ec_basis || "UNKNOWN");
    for (const key of ["open_below", "close_at_or_above"]) set(key, state.policy?.quality_thresholds?.[key]);
    for (const key of ["min_head_m", "max_abs_head_m", "inside_min_m", "inside_max_m"]) set(key, state.policy?.levels?.[key]);
    if (form.elements.allow_saline_drain) form.elements.allow_saline_drain.checked = state.policy?.allow_drainage_with_saline_outside === true;
    selectedPreset = state.policy?.scenario_preset || null;
    if ($("gateScenarioPreset")) $("gateScenarioPreset").value = selectedPreset?.preset_code || "";
    forecastContext = state.input?.forecast_context || null;
    simulationContext = state.input?.simulation_context || null;
    renderForecastContext();
  }
  function renderForecastContext() {
    const host = $("gateForecastContext");
    if (!host) return;
    host.replaceChildren();
    host.hidden = !forecastContext && !simulationContext;
    if (simulationContext) {
      host.append(node("strong", "SIMULATION · UNVERIFIED · Cần kỹ sư rà soát"));
      host.append(node("p", `Tháng ${simulationContext.year_month || "chưa rõ"} · nguồn ${simulationContext.source_reference} · EC ngoài mô phỏng ${num(simulationContext.simulated_outside_ec_mS_m)} mS/m. Đây là nội suy kịch bản, chưa xác minh tại cống. Nhập mực nước thực đo ngoài, trong và hệ cao độ chung trước khi rà soát. Không phải lệnh vận hành.`));
    }
    if (!forecastContext) return;
    host.append(node("strong", "Dự báo tháng đính kèm để tham khảo"));
    host.append(node("p", `${forecastContext.station || forecastContext.site_code || "Chưa rõ trạm"} · tháng ${forecastContext.target_month || "chưa rõ"} · ${num(forecastContext.predicted_ec_mS_m)} mS/m · mã ${forecastContext.prediction_id || "chưa có"}. Dự báo này không thay số đo EC hai phía cống, không xác lập liên kết thủy lực và không được dùng làm đầu vào quan trắc tức thời.`));
  }
  function invalidateEditedDraft() {
    gateRequests.next();
    fileRequests.input.next();
    fileRequests.policy.next();
    databaseDraftRequests.next();
    fieldRequests.next();
    evaluationRequests.next();
    clearResult();
    state.input = null;
  }
  function databaseStatus(message) {
    const target = $("gateDraftDatabaseStatus") || $("fieldStatus");
    target.textContent = message;
  }
  function persistDraft() {
    localStorage.setItem(draftKey(), JSON.stringify({ input: state.input, policy: state.policy }));
  }
  function clearResult() {
    $("evaluateGate").disabled = false;
    state.evaluation = null;
    $("downloadEvaluation").disabled = true;
    $("gateResultTitle").textContent = "Chưa có kết quả cho hồ sơ hiện tại";
    $("gateChecklist").replaceChildren();
    $("gateResult").textContent = "";
  }

  async function evaluateGate() {
    if (!state.input || !state.policy) {
      clearResult();
      $("gateEvaluationStatus").textContent = "Cần có bản nháp đầu vào và hồ sơ quy trình trước khi rà soát.";
      return;
    }
    const req = evaluationRequests.next();
    clearResult();
    $("evaluateGate").disabled = true;
    $("gateEvaluationStatus").textContent = "Đang kiểm tra hồ sơ…";
    state.evaluation = null;
    $("downloadEvaluation").disabled = true;
    try {
      const result = await api("/gate-evaluation", { ...req, method: "POST", body: { policy: state.policy, input: { ...state.input, evaluation_mode: "SIMULATION" } } });
      if (!req.isCurrent()) return;
      state.evaluation = result;
      $("downloadEvaluation").disabled = false;
      const outcomes = { CONDITIONS_MET: "Mô phỏng: đáp ứng điều kiện đã nhập", BLOCKED: "Mô phỏng: không đáp ứng điều kiện", REVIEW_REQUIRED: "Mô phỏng: cần rà soát dải chuyển tiếp" };
      $("gateResultTitle").textContent = outcomes[result.simulation_outcome] || labels[result.status] || "Cần bổ sung hoặc sửa dữ liệu kịch bản";
      $("gateChecklist").replaceChildren();
      for (const check of result.checklist) {
        const li = node("li", check.label, check.declared_present ? "present" : "");
        li.append(node("small", check.declared_present ? "Đã khai báo thông tin; chưa xác minh độc lập." : "Chưa có thông tin hoặc chưa đủ minh chứng."));
        $("gateChecklist").append(li);
      }
      for (const reason of result.reasons || []) $("gateChecklist").append(node("li", reason));
      for (const missing of result.missing_evidence || []) $("gateChecklist").append(node("li", `Còn thiếu: ${missing}`));
      if (result.evaluation_mode === "SIMULATION") {
        const head = result.evidence?.head_outside_minus_inside_m;
        if (Number.isFinite(head)) $("gateChecklist").append(node("li", `Mực ngoài − mực trong: ${num(head)} m · mục tiêu ${result.evidence.mode}`));
        $("gateChecklist").append(node("li", "Chỉ mô phỏng theo dữ liệu khai báo; không phải lệnh vận hành hay quy trình được phê duyệt."));
      }
      $("gateResult").textContent = JSON.stringify(result, null, 2);
      $("gateEvaluationStatus").textContent = `${state.input?.gate_code || "Chưa có mã cống"} · ${result.simulation_outcome || result.status}`;
    } catch (error) {
      if (req.isCurrent()) $("gateEvaluationStatus").textContent = error.message;
    } finally {
      if (req.isCurrent()) $("evaluateGate").disabled = false;
    }
  }

  async function selectGate() {
    databaseDraftRequests.next();
    selectedPreset = null;
    forecastContext = null;
    simulationContext = null;
    renderForecastContext();
    databaseStatus("");
    fileRequests.input.next();
    fileRequests.policy.next();
    fieldRequests.next();
    const code = $("gateSelect").value, gate = state.gates.find((g) => g.gate_code === code);
    if (!gate) return;
    const req = gateRequests.next();
    state.input = null;
    state.policy = null;
    evaluationRequests.next();
    clearResult();
    state.evaluation = null;
    $("downloadEvaluation").disabled = true;
    $("gateResult").textContent = "";
    $("gateChecklist").replaceChildren();
    $("gateInputFile").value = "";
    $("gatePolicyFile").value = "";
    $("fieldForm").reset();
    $("fieldStatus").textContent = "";
    $("gateInfo").textContent = gate.source_id === "DT_GATE_CATALOG_2025" ? `${gate.admin_label_source} · diện tích phục vụ ${num(gate.service_area_ha)} ha · khẩu độ ${gate.opening_width_m} m · ${gate.source_locator}. Mã dự án: ${code}.` : `Mã ${code} · ${gate.waterway_name || "Chưa có tên kênh"} · nguồn: ${gate.source_reference || gate.source_code}.`;
    try {
      const [input, policy] = await Promise.all([api(`/gate-template/input?gate_code=${encodeURIComponent(code)}`, req), api(`/gate-template/policy?gate_code=${encodeURIComponent(code)}`, req)]);
      if (!req.isCurrent()) return;
      state.input = input;
      state.policy = policy;
      populateForm();
      await evaluateGate();
      if (gate.source_id !== "DT_GATE_CATALOG_2025" && req.isCurrent()) {
        const candidates = await api(`/database-gates/${encodeURIComponent(code)}/candidate-stations`, req);
        if (!req.isCurrent()) return;
        map.setCandidates?.(candidates.gate_geometry, candidates.items);
        $("databaseGateStatus").textContent = candidates.items.length ? "Trạm ứng viên theo khoảng cách: " + candidates.items.map((r) => `${r.site_name} (${num(r.distance_m / 1000)} km)`).join("; ") + ". " + candidates.note : "Không có trạm trong bán kính 50 km của cống này. Không tự gán trạm đại diện.";
      }
    } catch (error) {
      if (req.isCurrent()) $("gateEvaluationStatus").textContent = error.message;
    }
  }
  $("gateSelect").addEventListener("change", selectGate);
  $("evaluateGate").addEventListener("click", evaluateGate);
  $("downloadEvaluation").addEventListener("click", () => {
    if (state.evaluation) save(`${state.evaluation.gate_code}_evaluation.json`, state.evaluation);
  });
  for (const [id, key] of [["gateInputFile", "input"], ["gatePolicyFile", "policy"]]) {
    $(id).addEventListener("change", async (event) => {
      const req = fileRequests[key].next(), code = $("gateSelect").value;
      gateRequests.next();
      databaseDraftRequests.next();
      evaluationRequests.next();
      fieldRequests.next();
      clearResult();
      try {
        const file = event.target.files[0];
        if (!file) return;
        if (file.size > 120000) throw new Error("Mỗi tệp phải dưới 120 KiB.");
        const data = JSON.parse(await file.text());
        if (!req.isCurrent() || code !== $("gateSelect").value) return;
        if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("Tệp phải chứa một object JSON.");
        if (data.gate_code !== code) throw new Error("Mã cống trong tệp không khớp cống đang chọn.");
        state[key] = data;
        populateForm();
        $("gateEvaluationStatus").textContent = `Đã nạp ${file.name}. Nhấn Mô phỏng kịch bản.`;
      } catch (error) {
        if (!req.isCurrent() || code !== $("gateSelect").value) return;
        $(id).value = "";
        state[key] = null;
        $("gateEvaluationStatus").textContent = error.message;
      }
    });
  }
  for (const [id, kind] of [["downloadGateInput", "input"], ["downloadGatePolicy", "policy"], ["downloadGateLink", "link"]]) $(id).addEventListener("click", async () => {
    const code = $("gateSelect").value;
    if (simulationContext) {
      if (kind === "link") {
        $("gateEvaluationStatus").textContent = "Mô phỏng không xác lập liên kết trạm–cống. Cần kỹ sư xác minh liên kết thủy lực thực tế.";
      } else if (state[kind]?.gate_code === code) {
        save(`${code}_simulation_${kind}.json`, state[kind]);
      } else {
        $("gateEvaluationStatus").textContent = "Phiếu đã thay đổi. Dùng xuất bản nháp để giữ các giá trị mới và nguồn mô phỏng.";
      }
      return;
    }
    try {
      const template = await api(`/gate-template/${kind}?gate_code=${encodeURIComponent(code)}`);
      save(`${code}_${kind}.json`, template);
    } catch (error) {
      $("gateEvaluationStatus").textContent = error.message;
    }
  });
  $("gateSelect").addEventListener("change", () => fieldRequests.next());
  $("fieldForm").addEventListener("input", event => {
    invalidateEditedDraft();
    if (["ec_basis", "open_below", "close_at_or_above"].includes(event.target.name)) {
      selectedPreset = null;
      if ($("gateScenarioPreset")) $("gateScenarioPreset").value = "";
    }
    $("gateEvaluationStatus").textContent = "Phiếu đã thay đổi. Nhấn lưu hoặc xuất bản nháp để chạy kịch bản mới.";
  });
  $("fieldForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    gateRequests.next();
    databaseDraftRequests.next();
    const req = fieldRequests.next(), code = $("gateSelect").value;
    evaluationRequests.next();
    clearResult();
    $("fieldStatus").textContent = "Đang tạo bản nháp…";
    try {
      const form = new FormData(event.target);
      const draft = await api(`/gate-template/input?gate_code=${encodeURIComponent(code)}`, req);
      if (!req.isCurrent()) return;
      const observed = form.get("observed") ? form.get("observed") + ":00+07:00" : null;
      draft.mode = form.get("mode");
      draft.evaluation_mode = "SIMULATION";
      if (forecastContext) draft.forecast_context = forecastContext;
      if (simulationContext) {
        draft.simulation_context = simulationContext;
        draft.data_kind = "SIMULATION";
        draft.quality_flag = "UNVERIFIED";
        draft.requires_operator_review = true;
        draft.recommendation = null;
        draft.actuator_command = null;
      }
      for (const key of ["outside_level", "inside_level", "outside_quality", "inside_quality"]) {
        const row = draft.observations[key];
        row.value = form.get(key) === "" ? null : Number(form.get(key));
        row.observed_at = observed;
        row.source_reference = form.get("reference") || null;
        row.quality_flag = "UNVERIFIED";
        if (key.endsWith("level")) row.vertical_datum = form.get("datum") || null;
        else {
          row.quality_flag = "UNVERIFIED";
          row.method_reference = form.get("method") || null;
          row.ec_basis = form.get("ec_basis") || "UNKNOWN";
        }
      }
      if (simulationContext) {
        draft.observations.outside_quality.data_kind = "SIMULATION";
        draft.observations.outside_quality.simulation_context = simulationContext;
        draft.observations.outside_quality.observed_at = null;
        draft.observations.outside_quality.source_reference = simulationContext.source_reference;
      }
      state.input = draft;
      state.policy = {
        schema_version: 1, is_demo: false, gate_code: code,
        approval: { status: "DRAFT", reference: null },
        parameter: { name: "EC", unit: "mS/m", ec_basis: form.get("ec_basis") || "UNKNOWN" },
        vertical_datum: form.get("datum") || null,
        allowed_modes: ["INTAKE", "DRAIN"],
        allow_drainage_with_saline_outside: form.get("allow_saline_drain") !== null,
        quality_thresholds: {}, levels: {},
      };
      for (const [section, keys] of [["quality_thresholds", ["open_below", "close_at_or_above"]], ["levels", ["min_head_m", "max_abs_head_m", "inside_min_m", "inside_max_m"]]]) {
        for (const key of keys) state.policy[section][key] = form.get(key) === null || form.get(key) === "" ? null : Number(form.get(key));
      }
      if (selectedPreset) state.policy.scenario_preset = selectedPreset;
      if (simulationContext) state.policy.simulation_context = simulationContext;
      let stored = true;
      try { persistDraft(); } catch { stored = false; }
      if (!["saveGateDraft", "saveGateDatabaseDraft"].includes(event.submitter?.id)) {
        save(`${code}_field_draft.json`, draft);
        save(`${code}_scenario_policy.json`, state.policy);
      }
      $("fieldStatus").textContent = stored ? "Đã lưu kịch bản trên trình duyệt này. Ngưỡng do người dùng nhập, chưa được phê duyệt; chưa lưu vào cơ sở dữ liệu." : "Trình duyệt không cho lưu cục bộ. Có thể xuất JSON; kịch bản vẫn được mô phỏng.";
      if (event.submitter?.id === "saveGateDatabaseDraft") {
        databaseStatus("Đang lưu phiên bản nháp vào PostgreSQL…");
        try {
          const record = await api("/gate-drafts", { ...req, method: "POST", body: { gate_code: code, input: state.input, policy: state.policy } });
          if (!req.isCurrent() || code !== $("gateSelect").value) return;
          if (record.gate_code !== code || !record.draft_id) throw new Error("Phản hồi lưu nháp không khớp cống hoặc thiếu mã bản nháp.");
          databaseStatus(`Đã lưu bản nháp PostgreSQL #${record.draft_id} · ${record.created_at || ""}. Thông tin chưa xác minh; không phải lệnh vận hành.`);
          $("fieldStatus").textContent = stored ? "Bản nháp hiện tại đã lưu trên trình duyệt và PostgreSQL." : "Bản nháp hiện tại đã lưu trên PostgreSQL; trình duyệt không cho lưu cục bộ.";
        } catch (error) {
          if (!req.isCurrent()) return;
          databaseStatus(`Chưa lưu được PostgreSQL: ${error.message} ${stored ? "Bản nháp trình duyệt vẫn được giữ." : "Có thể xuất JSON để giữ bản nháp."}`);
        }
      }
      await evaluateGate();
    } catch (error) {
      if (req.isCurrent()) $("fieldStatus").textContent = error.message;
    }
  });
  if ($("saveGateDraft")) $("saveGateDraft").type = "submit";
  if ($("saveGateDatabaseDraft")) $("saveGateDatabaseDraft").type = "submit";
  $("restoreGateDraft")?.addEventListener("click", async () => {
    try {
      const stored = localStorage.getItem(draftKey());
      if (!stored) throw new Error("Chưa có bản nháp cục bộ cho cống này.");
      const draft = JSON.parse(stored), code = $("gateSelect").value;
      if (!draft.input || !draft.policy || draft.input.gate_code !== code || draft.policy.gate_code !== code) throw new Error("Bản nháp không hợp lệ hoặc không khớp cống.");
      fieldRequests.next();
      gateRequests.next();
      databaseDraftRequests.next();
      fileRequests.input.next();
      fileRequests.policy.next();
      state.input = draft.input;
      state.policy = draft.policy;
      populateForm();
      $("fieldStatus").textContent = "Đã khôi phục bản nháp cục bộ; thông tin chưa được xác minh.";
      await evaluateGate();
    } catch (error) { $("fieldStatus").textContent = error.message; }
  });
  $("restoreGateDatabaseDraft")?.addEventListener("click", async () => {
    const code = $("gateSelect").value;
    gateRequests.next();
    fieldRequests.next();
    fileRequests.input.next();
    fileRequests.policy.next();
    evaluationRequests.next();
    clearResult();
    const req = databaseDraftRequests.next();
    databaseStatus("Đang đọc bản nháp PostgreSQL mới nhất…");
    try {
      const response = await api(`/gate-drafts?${new URLSearchParams({ gate_code: code, limit: "1", offset: "0" })}`, req);
      if (!req.isCurrent() || code !== $("gateSelect").value) return;
      if (!Array.isArray(response.items)) throw new Error("Danh sách bản nháp không hợp lệ.");
      const draft = response.items[0];
      if (!draft) { databaseStatus("Chưa có bản nháp PostgreSQL cho cống này."); return; }
      if (!draft.input || !draft.policy || Array.isArray(draft.input) || Array.isArray(draft.policy) || draft.gate_code !== code || draft.input.gate_code !== code || draft.policy.gate_code !== code) throw new Error("Bản nháp không hợp lệ hoặc không khớp cống.");
      state.input = draft.input;
      state.policy = draft.policy;
      populateForm();
      databaseStatus(`Đã khôi phục bản nháp PostgreSQL #${draft.draft_id} · ${draft.created_at || ""}. Khai báo chưa được xác minh.`);
      await evaluateGate();
    } catch (error) {
      if (req.isCurrent()) databaseStatus(`Chưa khôi phục được PostgreSQL: ${error.message}`);
    }
  });
  $("loadDatabaseGates").addEventListener("click", async () => {
    $("loadDatabaseGates").disabled = true;
    $("databaseGateStatus").textContent = "Đang đọc danh mục trong PostgreSQL…";
    try {
      const result = await api("/database-gates");
      $("databaseGateStatus").textContent = `${result.items.length} cống trong database. ${result.note}`;
      map.setGates(result.items);
      $("databaseGateList").replaceChildren();
      for (const g of result.items) {
        if (!state.gates.some((r) => r.gate_code === g.gate_code)) {
          state.gates.push(g);
          const option = node("option", g.gate_name + " · PostgreSQL");
          option.value = g.gate_code;
          $("gateSelect").append(option);
        }
        $("databaseGateList").append(node("span", `${g.gate_name} · ${g.gate_code}`, "database-gate"));
      }
    } catch (error) {
      $("databaseGateStatus").textContent = error.message;
    } finally {
      $("loadDatabaseGates").disabled = false;
    }
  });
  if ($("gateScenarioPreset")) loadThresholdPresets().then(items => {
    presets = items;
    populateThresholdPresets($("gateScenarioPreset"), items, "gate");
    if (selectedPreset) $("gateScenarioPreset").value = selectedPreset.preset_code;
    if ($("thresholdPresetStatus")) $("thresholdPresetStatus").textContent = $("gateScenarioPreset").options.length > 1 ? "Mẫu ngưỡng chỉ phục vụ kịch bản; không thay quy trình công trình được phê duyệt." : "Chưa có mẫu đủ hai ngưỡng EC cho mô phỏng cống. Có thể tự nhập ngưỡng và ghi nguồn.";
  }).catch(error => {
    if ($("thresholdPresetStatus")) $("thresholdPresetStatus").textContent = `Chưa tải được mẫu ngưỡng: ${error.message} Vẫn có thể tự nhập.`;
  });
  $("gateScenarioPreset")?.addEventListener("change", event => {
    const preset = presets.find(item => item.preset_code === event.target.value);
    selectedPreset = preset || null;
    if (!preset) return;
    const form = $("fieldForm");
    if (!Number.isFinite(preset.allow_intake_below_ms_m) || !Number.isFinite(preset.stop_intake_from_ms_m) || preset.allow_intake_below_ms_m <= 0 || preset.stop_intake_from_ms_m <= preset.allow_intake_below_ms_m) return;
    invalidateEditedDraft();
    form.elements.open_below.value = preset.allow_intake_below_ms_m;
    form.elements.close_at_or_above.value = preset.stop_intake_from_ms_m;
    form.elements.ec_basis.value = ["EC25", "RAW"].includes(preset.ec_basis) ? preset.ec_basis : "UNKNOWN";
    if ($("thresholdPresetStatus")) $("thresholdPresetStatus").textContent = presetReference(preset);
    $("gateEvaluationStatus").textContent = "Đã điền ngưỡng tham khảo. Lưu hoặc xuất bản nháp để mô phỏng lại; chưa xác lập quy trình được phê duyệt.";
  });
  window.addEventListener("workspace:apply-simulation-gate", event => {
    const draft = createSpatialGateDraft(event.detail);
    if (!draft) return;
    invalidateEditedDraft();
    const gate = event.detail.gate;
    if (!state.gates.some(item => item.gate_code === gate.gate_code)) {
      state.gates.push(gate);
      const option = node("option", `${gate.gate_name || gate.gate_code} · SIMULATION`);
      option.value = gate.gate_code;
      $("gateSelect").append(option);
    }
    $("gateSelect").value = gate.gate_code;
    state.input = draft.input;
    state.policy = draft.policy;
    $("fieldForm").reset();
    $("gateInputFile").value = "";
    $("gatePolicyFile").value = "";
    populateForm();
    $("gateInfo").textContent = `${gate.gate_name || gate.gate_code} · mã ${gate.gate_code} · SIMULATION / UNVERIFIED`;
    const message = `SIMULATION · tháng ${simulationContext.year_month || "chưa rõ"} · nguồn ${simulationContext.source_reference}. Đã điền EC và ngưỡng mô phỏng; chưa lưu hoặc đánh giá. Kỹ sư cần nhập mực ngoài, mực trong thực đo và hệ cao độ chung, kiểm tra nguồn trước khi rà soát. Không phải lệnh đóng/mở cống.`;
    $("fieldStatus").textContent = message;
    $("gateEvaluationStatus").textContent = message;
    databaseStatus("");
    location.hash = "gates";
  });
  window.addEventListener("workspace:apply-forecast-to-gate", event => {
    const forecast = event.detail;
    if (forecast?.kind === "SPATIAL_SIMULATION") return;
    if (!forecast || !Number.isFinite(forecast.predicted_ec_mS_m) || forecast.unit !== "mS/m") return;
    invalidateEditedDraft();
    forecastContext = {
      prediction_id: forecast.prediction_id || null,
      model_version: forecast.model_version || null,
      station: forecast.station || null,
      site_code: forecast.site_code || null,
      target_month: forecast.target_month || null,
      predicted_ec_mS_m: forecast.predicted_ec_mS_m,
      unit: "mS/m",
      data_kind: "MONTHLY_FORECAST_REFERENCE_ONLY",
      issued_at: forecast.issued_at || null,
      gate_observation: false,
    };
    renderForecastContext();
    $("fieldStatus").textContent = "Đã đính kèm dự báo EC tháng để tham khảo, tách riêng khỏi số đo cống. Các ô quan trắc vẫn giữ nguyên; cần số đo hai phía cùng thời điểm để mô phỏng điều kiện tại cống.";
  });
  async function load(gates) {
    state.gates = gates;
    $("gateSelect").replaceChildren();
    for (const gate of gates) {
      const option = node("option", gate.gate_name);
      option.value = gate.gate_code;
      $("gateSelect").append(option);
    }
    await selectGate();
  }

  return { load };
}
