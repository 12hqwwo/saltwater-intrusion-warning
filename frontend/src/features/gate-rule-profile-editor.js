import { node } from '../shared/ui.js';
import { DEFAULT_GATE_RULE_PROFILE, gateMeasurementNumber, validateGateRuleProfile } from '../shared/gate-intake-rules.js';

export function createGateRuleProfileEditor(addControl) {
  const ruleControls = new Map();
  const details = node('details', undefined, 'wide gate-rule-profile');
  details.append(node('summary', 'RuleProfile · Xem / cấu hình ngưỡng kỹ thuật'));
  const grid = node('div', undefined, 'field-grid');
  for (const [name, label] of [
    ['maxExteriorEcMsM', 'EC ngoài tối đa (mS/m) · 156.25 ≈ 1 g/L'], ['maxInteriorEcMsM', 'EC trong tối đa (mS/m)'],
    ['minPositiveHeadDiffM', 'ΔH dương tối thiểu (m)'], ['maxSampleAgeHoursNormal', 'Thời hạn mẫu bình thường (giờ)'],
    ['maxSampleAgeHoursHighVigilance', 'Thời hạn mẫu cảnh giác cao (giờ)'], ['p90ReferenceEcMsM', 'P90 Mỹ Tho mặc định khi thiếu ngưỡng mô hình (mS/m)'],
  ]) addControl(name, label, 'number', ruleControls, grid).value = DEFAULT_GATE_RULE_PROFILE[name];
  details.append(grid, node('p', 'Bắt buộc xác nhận cùng hệ cao độ và cơ khí READY. Quy đổi 0.0064 × EC chỉ là tham khảo; cấu hình này không phải quy trình công trình được phê duyệt.', 'subtle'));
  function readGateRuleProfile() {
    const profile = { ...DEFAULT_GATE_RULE_PROFILE };
    for (const [name, control] of ruleControls) profile[name] = gateMeasurementNumber(control.value);
    if ([...ruleControls.keys()].some(name => profile[name] !== DEFAULT_GATE_RULE_PROFILE[name])) {
      profile.ruleVersion += '+CUSTOM';
      profile.ruleName += ' (ngưỡng tùy chỉnh)';
    }
    return validateGateRuleProfile(profile);
  }
  return { details, readGateRuleProfile };
}
