export function createSpatialGateDraft(detail) {
  const gate = detail?.gate;
  const ec = gate?.simulated_outside_ec_mS_m;
  if (detail?.kind !== "SPATIAL_SIMULATION" || !gate?.gate_code || !Number.isFinite(ec) || ec < 0) return null;
  const thresholds = detail.thresholds || detail.frame?.thresholds || {};
  const context = {
    kind: "SPATIAL_SIMULATION", data_kind: "SIMULATION", simulation_layer: true,
    year_month: detail.year_month || detail.frame?.year_month || null,
    source_reference: gate.source_reference || gate.source_code || gate.source_id || "SPATIAL_SIMULATION",
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
