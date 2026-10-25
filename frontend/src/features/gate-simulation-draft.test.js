import test from "node:test";
import assert from "node:assert/strict";
import { createSpatialGateDraft } from "./gate-simulation-draft.js";

test("spatial gate draft retains real code and simulated provenance without operational measurements", () => {
  const detail = { kind: "SPATIAL_SIMULATION", year_month: "2030-04",
    gate: { gate_code: "NEW-CATALOG-01", simulated_outside_ec_mS_m: 180, source_reference: "catalog",
      outside_level: 5, inside_level: 4, vertical_datum: "OLD", quality_flag: "VERIFIED" },
    thresholds: { open_below_ec_ms_m: 120, close_at_or_above_ec_ms_m: 150 } };
  const { input, policy } = createSpatialGateDraft(detail);
  assert.equal(input.gate_code, "NEW-CATALOG-01");
  assert.equal(policy.gate_code, input.gate_code);
  assert.equal(input.evaluation_mode, "SIMULATION");
  assert.equal(input.observations.outside_quality.value, 180);
  assert.equal(input.observations.outside_quality.quality_flag, "UNVERIFIED");
  assert.equal(input.simulation_context.year_month, "2030-04");
  assert.equal(input.simulation_context.gate_observation, false);
  for (const side of ["outside_level", "inside_level"]) {
    assert.equal(input.observations[side].value, null);
    assert.equal(input.observations[side].vertical_datum, null);
    assert.equal(input.observations[side].observed_at, null);
  }
  assert.equal(policy.vertical_datum, null);
  assert.equal(policy.approval.status, "DRAFT");
  assert.equal(policy.quality_thresholds.open_below, 120);
  assert.equal(policy.quality_thresholds.close_at_or_above, 150);
  assert.equal(input.actuator_command, null);
  assert.equal(input.recommendation, null);
  assert.equal(input.station_gate_link, undefined);
});

test("malformed and legacy events cannot create spatial drafts", () => {
  assert.equal(createSpatialGateDraft({ predicted_ec_mS_m: 10 }), null);
  assert.equal(createSpatialGateDraft({ kind: "SPATIAL_SIMULATION", gate: { gate_code: "x", simulated_outside_ec_mS_m: NaN } }), null);
});
