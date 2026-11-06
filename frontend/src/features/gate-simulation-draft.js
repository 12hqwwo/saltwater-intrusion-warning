const MONTH = /^(?!0000)\d{4}-(0[1-9]|1[0-2])$/;
const object = value => value && typeof value === "object" && !Array.isArray(value);

export { DEFAULT_GATE_RULE_PROFILE, deriveForecastAdvisoryForGate, evaluateGateIntakeCondition } from '../shared/gate-intake-rules.js';

export function validateGateDraftPart(data, kind, code) {
  if (!object(data) || data.gate_code !== code || data.schema_version !== 1) throw new Error("Hồ sơ không hợp lệ hoặc không khớp cống.");
  if (kind === "input") {
    if (!object(data.observations)) throw new Error("Thiếu các trường quan trắc cống.");
    for (const key of ["outside_level", "inside_level", "outside_quality", "inside_quality"]) {
      const row = data.observations[key], quality = key.endsWith("quality");
      if (!object(row) || row.gate_code !== code || row.unit !== (quality ? "mS/m" : "m")) throw new Error("Mã cống hoặc đơn vị quan trắc không khớp.");
    }
    if (data.forecast_context && (!validForecastReference(data.forecast_context) ||
        (data.forecast_context.attached_gate_code && data.forecast_context.attached_gate_code !== code))) throw new Error("Nguồn dự báo tham khảo không hợp lệ.");
  } else if (kind === "policy" && (!object(data.parameter) || data.parameter.name !== "EC" || data.parameter.unit !== "mS/m")) {
    throw new Error("Quy trình phải dùng EC, đơn vị mS/m.");
  }
  const contexts = [data.simulation_context, ...(kind === "input" ? [data.observations.outside_quality.simulation_context] : [])].filter(Boolean);
  for (const context of contexts) {
    if (!object(context) || context.gate_observation !== false || (context.gate_code && context.gate_code !== code) ||
        !MONTH.test(context.year_month) || !Number.isFinite(context.simulated_outside_ec_mS_m) || context.simulated_outside_ec_mS_m < 0) throw new Error("Nguồn mô phỏng không khớp cống, tháng hoặc EC.");
  }
  if (contexts.some(context => context.year_month !== contexts[0].year_month || context.simulated_outside_ec_mS_m !== contexts[0].simulated_outside_ec_mS_m)) throw new Error("Nguồn mô phỏng trong hồ sơ không đồng nhất.");
  if (kind === "input" && contexts.length) {
    const row = data.observations.outside_quality;
    for (const context of contexts) {
      const expected = Object.hasOwn(context, "current_scenario_ec_mS_m") ? context.current_scenario_ec_mS_m : context.simulated_outside_ec_mS_m;
      if (row.value !== expected) throw new Error("EC kịch bản không khớp nguồn khai báo.");
      if (expected !== context.simulated_outside_ec_mS_m && (context.current_value_origin !== "USER_SCENARIO" || row.source_reference !== `USER_SCENARIO:${code}:${context.year_month}`)) throw new Error("EC do người dùng sửa phải ghi nguồn kịch bản riêng.");
    }
    if (row.data_kind !== "SIMULATION" || row.observed_at !== null) throw new Error("EC mô phỏng phải tách khỏi quan trắc thực đo.");
  }
  return data;
}

export function validateGateDraftPair(input, policy, code) {
  validateGateDraftPart(input, "input", code);
  validateGateDraftPart(policy, "policy", code);
  const source = input.simulation_context || input.observations.outside_quality.simulation_context;
  if (policy.simulation_context && (!source || policy.simulation_context.year_month !== source.year_month ||
      policy.simulation_context.simulated_outside_ec_mS_m !== source.simulated_outside_ec_mS_m ||
      policy.simulation_context.current_scenario_ec_mS_m !== source.current_scenario_ec_mS_m ||
      policy.simulation_context.current_value_origin !== source.current_value_origin)) throw new Error("Nguồn mô phỏng đầu vào và quy trình không khớp.");
  return { input, policy };
}

export function validForecastReference(forecast) {
  const sites = { MYTHO: "MRC_VN_019805", MYTHUAN: "MRC_VN_019804", TANCHAU: "MRC_VN_019803" };
  const station = typeof forecast?.station === "string" ? forecast.station.toUpperCase().replace(/[ _]/g, "") : "";
  return Boolean(forecast && (forecast.gate_observation === undefined || forecast.gate_observation === false) && forecast.unit === "mS/m" && Number.isFinite(forecast.predicted_ec_mS_m) && forecast.predicted_ec_mS_m >= 0 &&
    MONTH.test(forecast.target_month) && sites[station] && (!forecast.site_code || forecast.site_code === sites[station]));
}

export function createSpatialGateDraft(detail) {
  const gate = detail?.gate;
  const ec = gate?.simulated_outside_ec_mS_m;
  if (detail?.kind !== "SPATIAL_SIMULATION" || !gate?.gate_code || !Number.isFinite(ec) || ec < 0 ||
      !MONTH.test(detail.year_month || detail.frame?.year_month) ||
      (detail.year_month && detail.frame?.year_month && detail.year_month !== detail.frame.year_month)) return null;
  if (detail.frame) {
    const current = Array.isArray(detail.frame.gates) ? detail.frame.gates.find(item => item?.gate_code === gate.gate_code) : null;
    if (detail.frame.simulation_layer !== true || !current || current.simulated_outside_ec_mS_m !== ec) return null;
  }
  const thresholds = detail.thresholds || detail.frame?.thresholds || {};
  const context = {
    gate_code: gate.gate_code, kind: "SPATIAL_SIMULATION", data_kind: "SIMULATION", simulation_layer: true,
    year_month: detail.year_month || detail.frame?.year_month || null,
    source_reference: `SPATIAL_SIMULATION:${detail.year_month || detail.frame?.year_month}:${gate.gate_code}`,
    gate_location_source_reference: gate.source_reference || gate.source_code || gate.source_id || null,
    methodology: detail.frame?.methodology || null,
    simulated_outside_ec_mS_m: ec, quality_flag: "UNVERIFIED",
    gate_observation: false, requires_operator_review: true,
  };
  const observations = {};
  for (const key of ["outside_level", "inside_level", "outside_quality", "inside_quality"]) {
    const quality = key.endsWith("quality");
    observations[key] = {
      gate_code: gate.gate_code, value: key === "outside_quality" ? ec : null,
      unit: quality ? "mS/m" : "m", observed_at: null,
      quality_flag: "UNVERIFIED", source_reference: key === "outside_quality" ? context.source_reference : null,
      ...(quality ? { parameter: "EC", ec_basis: "UNKNOWN", method_reference: null } : { vertical_datum: null }),
      ...(key === "outside_quality" ? { data_kind: "SIMULATION", simulation_context: context } : {}),
    };
  }
  return {
    input: { schema_version: 1, is_demo: false, gate_code: gate.gate_code, mode: "INTAKE",
      evaluation_mode: "SIMULATION", data_kind: "SIMULATION", quality_flag: "UNVERIFIED",
      simulation_context: context, observations, recommendation: null, actuator_command: null,
      requires_operator_review: true },
    policy: { schema_version: 1, is_demo: false, gate_code: gate.gate_code,
      approval: { status: "DRAFT", reference: null },
      parameter: { name: "EC", unit: "mS/m", ec_basis: "UNKNOWN" }, vertical_datum: null,
      allowed_modes: ["INTAKE", "DRAIN"], allow_drainage_with_saline_outside: false,
      quality_thresholds: {
        open_below: thresholds.open_below_ec_ms_m ?? thresholds.open_below ?? null,
        close_at_or_above: thresholds.close_at_or_above_ec_ms_m ?? thresholds.close_at_or_above ?? null,
      }, levels: {}, simulation_context: context },
  };
}
