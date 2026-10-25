import { workspaceAPI as api } from "./workspace-api.js";
import { node, num } from "./ui.js";

let pending;
export function loadThresholdPresets() {
  if (!pending) pending = api("/threshold-presets").then(data => {
    if (!Array.isArray(data.items)) throw new Error("Danh mục ngưỡng đối chiếu không hợp lệ.");
    return data.items;
  }).catch(error => { pending = null; throw error; });
  return pending;
}

export function populateThresholdPresets(select, presets, kind) {
  if (!select) return;
  const empty = node("option", "Tự nhập / chưa chọn mẫu ngưỡng");
  empty.value = "";
  select.replaceChildren(empty);
  for (const preset of presets) {
    const value = kind === "gate" ? preset.allow_intake_below_ms_m : preset.threshold_ms_m;
    const valid = typeof preset.preset_code === "string" && Number.isFinite(value) && value > 0;
    const gateValid = kind !== "gate" || (Number.isFinite(preset.stop_intake_from_ms_m) && preset.stop_intake_from_ms_m > value);
    if (!valid || !gateValid) continue;
    const limits = kind === "gate"
      ? `lấy khi EC < ${num(value)} mS/m; ngừng khi EC ≥ ${num(preset.stop_intake_from_ms_m)} mS/m`
      : `${num(value)} mS/m`;
    const option = node("option", `${preset.usage_purpose || preset.preset_code} · ${limits} · tham khảo`);
    option.value = preset.preset_code;
    select.append(option);
  }
}

export function presetReference(preset) {
  return `${preset.source_note || "Chưa ghi nguồn"} · trạng thái minh chứng: ${preset.evidence_status || "chưa xác minh"}. Mẫu đối chiếu tham khảo, không phải quy tắc vận hành được phê duyệt.`;
}
