import { node, num, save } from '../shared/ui.js';
import { activeForecastContext, forecastModelLabel } from '../shared/forecast-map-overlay.js';
import { DEFAULT_GATE_RULE_PROFILE, evaluateGateIntakeCondition, deriveForecastAdvisoryForGate,
  gateMeasurementNumber, validateGateRuleProfile } from '../shared/gate-intake-rules.js';
import { projectForecastContextForGate } from './gate-forecast-context.js';
import { requestJSON } from '../api.js';

const localTime = value => new Date(value).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false });
const CHECK_LABELS = { PASSED: 'Đạt', FAILED: 'Không đạt', MISSING_OR_EXPIRED: 'Cần bổ sung / đo lại' };

export function createGateIntakeScreening(host, { now = () => new Date().toISOString(), schedule = setTimeout, cancel = clearTimeout,
  serverEvaluate = payload => requestJSON('/gate-screening/evaluate', { method: 'POST', body: payload }),
  eventTarget = globalThis.window, documentTarget = globalThis.document } = {}) {
  if (!host) return { setGate() {}, setSpatialFrame() {}, destroy() {} };
  let gate = null, baseFrame = null, forecast = activeForecastContext, result = null, expiryTimer = null, disposed = false, evaluationSerial = 0;
  const controls = new Map(), ruleControls = new Map();
  const panel = node('section', undefined, 'panel gate-intake-screening');
  panel.append(node('span', 'KIỂM TRA KỸ THUẬT · NGƯỜI VẬN HÀNH XEM XÉT', 'tag'), node('h3', DEFAULT_GATE_RULE_PROFILE.ruleName));
  const gateTitle = node('p', 'Chọn cống để kiểm tra điều kiện lấy nước.', 'gate-screening-gate');
  const version = node('p', `${DEFAULT_GATE_RULE_PROFILE.ruleId} · ${DEFAULT_GATE_RULE_PROFILE.ruleVersion}`, 'subtle');
  panel.append(gateTitle, version, node('p', DEFAULT_GATE_RULE_PROFILE.ruleNatureNotice, 'notice'));
  const contextSection = node('section', undefined, 'gate-screening-forecast');
  contextSection.append(node('h3', 'Phần A · Ngữ cảnh xu thế từ mô hình dự báo đa biến'));
  const forecastSummary = node('div'); forecastSummary.id = 'gateIntakeForecastSummary';
  forecastSummary.setAttribute('aria-live', 'polite');
  contextSection.append(forecastSummary);
  const fieldSection = node('section');
  fieldSection.append(node('h3', 'Phần B · Điều kiện hiện trường và kết luận đề xuất'),
    node('p', 'Nhập một bộ số đo thực tế cùng thời điểm tại cống. Dự báo và EC mô phỏng được giữ ở Phần A; không tự điền vào phiếu đo.', 'subtle'));
  const form = node('form', undefined, 'field-grid gate-intake-form');
  form.id = 'gateIntakeForm'; form.noValidate = true;
  const addControl = (name, label, type = 'number', target = controls, parent = form) => {
    const control = node('input'); control.type = type; control.name = name;
    if (type === 'number') control.step = 'any';
    const wrapper = node('label', label); wrapper.append(control); parent.append(wrapper); target.set(name, control);
    return control;
  };
  for (const [name, label] of [
    ['exteriorEcMsM', 'EC thực đo ngoài sông sát cống (mS/m)'], ['interiorEcMsM', 'EC thực đo trong đồng (mS/m)'],
    ['exteriorStageM', 'Mực nước thực đo ngoài sông (m)'], ['interiorStageM', 'Mực nước thực đo trong đồng (m)'],
  ]) addControl(name, label);
  addControl('measuredAtLocal', 'Thời điểm bộ số đo (GMT+7)', 'datetime-local');
  addControl('measuredBy', 'Người đo / nguồn bộ số đo', 'text');
  const mechanical = node('select'); mechanical.name = 'mechanicalStatus';
  for (const [value, label] of [['', 'Chưa xác định'], ['READY', 'READY · Sẵn sàng'], ['NOT_READY', 'NOT_READY · Chưa sẵn sàng'], ['MAINTENANCE', 'MAINTENANCE · Đang bảo trì'], ['FAULT', 'FAULT · Sự cố']]) {
    const option = node('option', label); option.value = value; mechanical.append(option);
  }
  const mechanicalLabel = node('label', 'Trạng thái cơ khí / công trình'); mechanicalLabel.append(mechanical); form.append(mechanicalLabel);
  controls.set('mechanicalStatus', mechanical);
  addControl('sameElevationDatum', 'Tôi xác nhận hai mực nước cùng hệ quy chiếu cao độ', 'checkbox').checked = false;
  const profileDetails = node('details', undefined, 'wide gate-rule-profile');
  profileDetails.append(node('summary', 'RuleProfile · Xem / cấu hình ngưỡng kỹ thuật'));
  const ruleGrid = node('div', undefined, 'field-grid');
  for (const [name, label] of [
    ['maxExteriorEcMsM', 'EC ngoài tối đa (mS/m) · 156.25 ≈ 1 g/L'], ['maxInteriorEcMsM', 'EC trong tối đa (mS/m)'],
    ['minPositiveHeadDiffM', 'ΔH dương tối thiểu (m)'], ['maxSampleAgeHoursNormal', 'Thời hạn mẫu bình thường (giờ)'],
    ['maxSampleAgeHoursHighVigilance', 'Thời hạn mẫu cảnh giác cao (giờ)'], ['p90ReferenceEcMsM', 'P90 Mỹ Tho mặc định khi thiếu ngưỡng mô hình (mS/m)'],
  ]) addControl(name, label, 'number', ruleControls, ruleGrid).value = DEFAULT_GATE_RULE_PROFILE[name];
  profileDetails.append(ruleGrid, node('p', 'Bắt buộc xác nhận cùng hệ cao độ và cơ khí READY. Quy đổi 0.0064 × EC chỉ là tham khảo; cấu hình này không phải quy trình công trình được phê duyệt.', 'subtle'));
  const actions = node('div', undefined, 'wide draft-actions');
  const submit = node('button', 'Kiểm tra điều kiện xem xét lấy nước'); submit.type = 'submit'; submit.disabled = true;
  const download = node('button', 'Tải bảng kiểm tra JSON ↓', 'secondary'); download.type = 'button'; download.disabled = true;
  actions.append(submit, download); form.append(profileDetails, actions);
  const conclusion = node('div', undefined, 'gate-intake-conclusion'); conclusion.id = 'gateIntakeConclusion'; conclusion.setAttribute('role', 'status');
  const expiry = node('p', '', 'subtle'); expiry.id = 'gateIntakeExpiry';
  const serverStatus = node('p', '', 'subtle'); serverStatus.id = 'gateIntakeServerStatus';
  const table = node('table', undefined, 'gate-intake-checks'), head = node('thead'), header = node('tr'), rows = node('tbody');
  rows.id = 'gateIntakeCriteria';
  for (const text of ['Điều kiện', 'Kết quả', 'Số đo / khai báo', 'Ngưỡng kiểm tra', 'Giải thích']) header.append(node('th', text));
  head.append(header); table.append(head, rows);
  const wrap = node('div', undefined, 'table-wrap'); wrap.append(table);
  fieldSection.append(form, conclusion, expiry, serverStatus, wrap); panel.append(contextSection, fieldSection); host.replaceChildren(panel);

  function readProfile() {
    const profile = { ...DEFAULT_GATE_RULE_PROFILE };
    for (const [name, control] of ruleControls) profile[name] = gateMeasurementNumber(control.value);
    if ([...ruleControls.keys()].some(name => profile[name] !== DEFAULT_GATE_RULE_PROFILE[name])) {
      profile.ruleVersion += '+CUSTOM';
      profile.ruleName += ' (ngưỡng tùy chỉnh)';
    }
    return validateGateRuleProfile(profile);
  }
  function gateContext() { return projectForecastContextForGate(forecast, gate, baseFrame); }
  function renderForecast() {
    forecastSummary.replaceChildren();
    try {
      const profile = readProfile();
      version.textContent = `${profile.ruleId} · ${profile.ruleVersion}`;
      const advisory = deriveForecastAdvisoryForGate(gateContext(), profile);
      const heading = node('strong', advisory.isHighVigilance ? 'Cảnh giác cao' : advisory.hasForecastContext ? 'Chưa kích hoạt cảnh giác cao' : 'Chưa có ngữ cảnh dự báo');
      heading.className = advisory.isHighVigilance ? 'gate-vigilance-high' : '';
      forecastSummary.append(heading);
      if (advisory.hasForecastContext) {
        const source = ['MULTIVARIATE_RF_5', 'RF_compact'].includes(advisory.sourceModel) ? forecastModelLabel(advisory.sourceModel) : advisory.sourceModel;
        forecastSummary.append(node('p', `${source} · tháng mục tiêu ${advisory.targetMonth || 'chưa khai báo'} · Tân Châu ${num(advisory.tanchauEc)} → Mỹ Thuận ${num(advisory.mythuanEc)} → Mỹ Tho ${num(advisory.stationForecastEc)} mS/m.`));
        const upstreamBasis = advisory.tanchauBasis === 'TIMELINE_BASELINE' ? 'EC Tân Châu lấy từ Timeline nền.'
          : advisory.tanchauBasis === 'ASSUMED_DEFAULT_25' ? 'EC Tân Châu là giá trị giả định 25 mS/m.'
            : advisory.tanchauBasis === 'MODEL_PREDICTION' ? 'EC ba trạm từ mô hình dự báo; nội suy hai chặng qua Mỹ Thuận.' : 'Chưa khai báo nguồn riêng của EC Tân Châu.';
        forecastSummary.append(node('p', upstreamBasis, 'subtle'));
        const projected = gateContext();
        forecastSummary.append(node('p', advisory.projectionBasis === 'GEOMETRIC_AXIS_INTERPOLATION'
          ? `EC dự báo tại vị trí chiếu của cống: ${num(advisory.projectedGateEc)} mS/m · km ${num(projected.projectedChainageKm)}${Number.isFinite(projected.projectionDistanceKm) ? ` · cách trục ${num(projected.projectionDistanceKm)} km` : ''}. Nội suy hình học phục vụ sàng lọc không gian, chưa xác lập kết nối thủy lực.`
          : 'Chưa có vị trí chiếu hợp lệ của cống; dùng EC dự báo Mỹ Tho làm ngữ cảnh thay thế, không coi là EC tại cống.'));
        forecastSummary.append(node('p', `Cảnh giác cao nếu Mỹ Tho ≥ P90 ${num(advisory.p90Threshold)} mS/m, hoặc EC tại vị trí chiếu ≥ 80% ngưỡng EC ngoài (${num(advisory.gateRatioThresholdEcMsM)} mS/m), hoặc ngữ cảnh mô hình đã bật cảnh giác cao.`, 'subtle'));
      }
      forecastSummary.append(node('p', advisory.advisoryMessage), node('p', 'Xu thế dự báo chỉ điều chỉnh thời hạn mẫu đo. Kết luận ở Phần B cần số đo hiện trường của cả hai phía cống.', 'subtle'));
    } catch (error) { forecastSummary.append(node('p', error.message, 'error')); }
  }
  function invalidate(message = 'Phiếu đã thay đổi. Cần kiểm tra lại điều kiện hiện tại.') {
    evaluationSerial++; cancel(expiryTimer); expiryTimer = null; result = null; download.disabled = true;
    serverStatus.textContent = '';
    conclusion.dataset.status = 'PENDING'; conclusion.textContent = message; expiry.textContent = ''; rows.replaceChildren();
  }
  function measurementInput() {
    const local = controls.get('measuredAtLocal').value;
    return { gateId: gate.gate_code, gateName: gate.gate_name || gate.gate_code,
      ...Object.fromEntries(['exteriorEcMsM', 'interiorEcMsM', 'exteriorStageM', 'interiorStageM', 'measuredBy', 'mechanicalStatus'].map(name => [name, controls.get(name).value])),
      measuredAtIso: local ? `${local.length === 16 ? local + ':00' : local}+07:00` : null,
      sameElevationDatum: controls.get('sameElevationDatum').checked === true,
      dataKind: 'DECLARED_FIELD_MEASUREMENT',
    };
  }
  function runEvaluation() {
    if (disposed || !gate) return null;
    cancel(expiryTimer); expiryTimer = null;
    try {
      const measured = measurementInput(), profile = readProfile(), context = gateContext(), evaluatedAt = now();
      result = { ...evaluateGateIntakeCondition(measured, profile, context, evaluatedAt), measurementInput: measured };
      const serial = ++evaluationSerial, localResult = result;
      serverStatus.textContent = 'Đang đối chiếu quy tắc trên máy chủ…';
      download.disabled = true;
      Promise.resolve().then(() => serverEvaluate({ measurement: measured, profile, forecast_context: context, now_iso: evaluatedAt }))
        .then(remote => {
          if (disposed || serial !== evaluationSerial || result !== localResult) return;
          const localChecks = localResult.criteriaChecks.map(item => [item.id, item.status]);
          const remoteChecks = (remote.criteriaChecks || []).map(item => [item.id, item.status]);
          const matches = remote.status === localResult.status && JSON.stringify(remoteChecks) === JSON.stringify(localChecks) &&
            remote.effectiveMaxSampleAgeHours === localResult.forecastAdvisory.effectiveMaxSampleAgeHours;
          serverStatus.textContent = matches ? 'Máy chủ đã đối chiếu cùng kết quả và từng tiêu chí.' :
            `Kết quả khác nhau: giao diện ${localResult.status}, máy chủ ${remote.status || 'không rõ'}. Cần kiểm tra trước khi dùng.`;
          serverStatus.dataset.status = matches ? 'MATCH' : 'MISMATCH';
          download.disabled = !matches;
        }).catch(error => {
          if (disposed || serial !== evaluationSerial) return;
          serverStatus.textContent = `Chưa đối chiếu được với máy chủ: ${error.message}`;
          serverStatus.dataset.status = 'UNVERIFIED';
          download.disabled = true;
        });
      conclusion.dataset.status = result.status;
      conclusion.replaceChildren(node('h4', result.statusTitle), node('p', result.summaryReason));
      expiry.textContent = `Đánh giá ${localTime(result.evaluatedAtIso)} (GMT+7). ${result.validUntilIso ? `Đề xuất có hiệu lực đến ${localTime(result.validUntilIso)} (GMT+7).`
        : 'Chưa có đề xuất lấy nước còn hiệu lực.'}${result.sampleAgeHours !== null ? ` Tuổi mẫu ${num(result.sampleAgeHours)} giờ; giới hạn ${result.forecastAdvisory.effectiveMaxSampleAgeHours} giờ.` : ''}`;
      rows.replaceChildren();
      const units = { SAMPLE_FRESHNESS: 'giờ', EXTERIOR_EC: 'mS/m', INTERIOR_EC: 'mS/m', HYDRAULIC_HEAD_DIFF: 'm' };
      const display = (value, id) => value === null ? '—' : typeof value === 'boolean' ? value ? 'Đã xác nhận' : 'Chưa xác nhận'
        : typeof value === 'number' ? `${num(value)} ${units[id] || ''}`.trim() : String(value);
      for (const check of result.criteriaChecks) {
        const row = node('tr'); row.dataset.status = check.status;
        const comparison = ['SAMPLE_FRESHNESS', 'EXTERIOR_EC', 'INTERIOR_EC'].includes(check.id) ? '≤ ' : check.id === 'HYDRAULIC_HEAD_DIFF' ? '≥ ' : '';
        for (const value of [check.label, CHECK_LABELS[check.status], display(check.observedValue, check.id), comparison + display(check.thresholdValue, check.id), check.explanation]) row.append(node('td', value));
        rows.append(row);
      }
      renderForecast();
      const delay = result.sampleExpiresAtIso ? Date.parse(result.sampleExpiresAtIso) - Date.parse(result.evaluatedAtIso) + 1 : 0;
      if (delay > 0) expiryTimer = schedule(runEvaluation, Math.min(delay, 2_147_483_647));
      return result;
    } catch (error) { invalidate(error.message); return null; }
  }
  function setGate(value) {
    const changed = value?.gate_code !== gate?.gate_code;
    gate = value?.gate_code ? value : null;
    submit.disabled = !gate;
    gateTitle.textContent = gate ? `${gate.gate_name || gate.gate_code} · ${gate.gate_code}` : 'Chọn cống để kiểm tra điều kiện lấy nước.';
    if (changed || !gate) {
      for (const [name, control] of controls) { control.value = ''; if (name === 'sameElevationDatum') control.checked = false; }
      invalidate(gate ? 'Chưa đánh giá. Nhập bộ số đo tại cống và nhấn kiểm tra.' : 'Chọn cống để kiểm tra điều kiện lấy nước.');
    } else if (result) runEvaluation();
    renderForecast();
  }
  function updateContext(value) { forecast = value; if (result) runEvaluation(); else renderForecast(); }
  function setSpatialFrame(value) { baseFrame = value; if (result) runEvaluation(); else renderForecast(); }
  form.addEventListener('submit', event => { event.preventDefault(); runEvaluation(); });
  const edited = () => { invalidate(); renderForecast(); };
  form.addEventListener('input', edited); form.addEventListener('change', edited);
  download.addEventListener('click', () => {
    if (!result || download.disabled) return;
    if (result.sampleExpiresAtIso && Date.parse(now()) > Date.parse(result.sampleExpiresAtIso)) { runEvaluation(); return; }
    save(`${gate.gate_code}_intake_screening.json`, result);
  });
  const listeners = [['workspace:active-forecast-context', event => updateContext(event.detail)],
    ['workspace:simulation-frame', event => setSpatialFrame(event.detail)]];
  listeners.forEach(([name, listener]) => eventTarget?.addEventListener(name, listener));
  const refresh = () => { if (!documentTarget?.hidden && result) runEvaluation(); };
  documentTarget?.addEventListener?.('visibilitychange', refresh);
  eventTarget?.addEventListener?.('focus', refresh);
  invalidate('Chọn cống để kiểm tra điều kiện lấy nước.'); renderForecast();
  return { setGate, setSpatialFrame, setForecastContext: updateContext, evaluate: runEvaluation, getResult: () => result,
    destroy() { disposed = true; cancel(expiryTimer); listeners.forEach(([name, listener]) => eventTarget?.removeEventListener(name, listener));
      documentTarget?.removeEventListener?.('visibilitychange', refresh); eventTarget?.removeEventListener?.('focus', refresh); },
  };
}
