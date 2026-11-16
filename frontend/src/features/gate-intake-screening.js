import { node, num, save } from '../shared/ui.js';
import { activeForecastContext, forecastModelLabel } from '../shared/forecast-map-overlay.js';
import { DEFAULT_GATE_RULE_PROFILE, evaluateGateIntakeCondition, deriveForecastAdvisoryForGate } from '../shared/gate-intake-rules.js';
import { projectForecastContextForGate } from './gate-forecast-context.js';
import { requestJSON } from '../api.js';
import { createGateIntakeMeasurementForm } from './gate-intake-measurement-form.js';
import { createGateRuleProfileEditor } from './gate-rule-profile-editor.js';
import { renderGateIntakeConclusion } from './gate-intake-conclusion-summary.js';
import { createGateIntakeEvaluationDetails } from './gate-intake-evaluation-details.js';

export function createGateIntakeScreening(host, { now = () => new Date().toISOString(), schedule = setTimeout, cancel = clearTimeout,
  serverEvaluate = payload => requestJSON('/gate-screening/evaluate', { method: 'POST', body: payload }),
  eventTarget = globalThis.window, documentTarget = globalThis.document, role = 'INSPECTOR' } = {}) {
  if (!host) return { setGate() {}, setSpatialFrame() {}, destroy() {} };
  let gate = null, baseFrame = null, forecast = activeForecastContext, result = null, expiryTimer = null, disposed = false, evaluationSerial = 0;
  const staff = role !== 'PUBLIC';
  const controls = new Map();
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
  createGateIntakeMeasurementForm(form, controls, addControl);
  const profileEditor = staff ? createGateRuleProfileEditor(addControl) : null;
  const evaluationDetails = staff ? createGateIntakeEvaluationDetails() : null;
  const actions = node('div', undefined, 'wide draft-actions');
  const submit = node('button', 'Kiểm tra điều kiện xem xét lấy nước'); submit.type = 'submit'; submit.disabled = true;
  const download = staff ? node('button', 'Tải bảng kiểm tra JSON ↓', 'secondary') : null;
  if (download) { download.type = 'button'; download.disabled = true; }
  actions.append(submit);
  if (staff) { form.append(profileEditor.details); actions.append(download); }
  form.append(actions);
  const conclusion = node('div', undefined, 'gate-intake-conclusion'); conclusion.id = 'gateIntakeConclusion'; conclusion.setAttribute('role', 'status');
  const serverStatus = node('p', '', 'subtle'); serverStatus.id = 'gateIntakeServerStatus';
  fieldSection.append(form, conclusion);
  if (staff) fieldSection.append(evaluationDetails.expiry);
  fieldSection.append(serverStatus);
  if (staff) fieldSection.append(evaluationDetails.wrap);
  panel.append(contextSection, fieldSection); host.replaceChildren(panel);

  function readProfile() {
    return profileEditor ? profileEditor.readGateRuleProfile() : DEFAULT_GATE_RULE_PROFILE;
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
    evaluationSerial++; cancel(expiryTimer); expiryTimer = null; result = null;
    if (download) download.disabled = true;
    serverStatus.textContent = '';
    conclusion.dataset.status = 'PENDING'; conclusion.textContent = message; evaluationDetails?.clear();
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
      if (download) download.disabled = true;
      Promise.resolve().then(() => serverEvaluate({ measurement: measured, profile, forecast_context: context, now_iso: evaluatedAt }))
        .then(remote => {
          if (disposed || serial !== evaluationSerial || result !== localResult) return;
          const localChecks = localResult.criteriaChecks.map(item => [item.id, item.status]);
          const remoteChecks = (remote.criteriaChecks || []).map(item => [item.id, item.status]);
          const matches = staff ? remote.status === localResult.status && JSON.stringify(remoteChecks) === JSON.stringify(localChecks) &&
            remote.effectiveMaxSampleAgeHours === localResult.forecastAdvisory.effectiveMaxSampleAgeHours : remote.status === localResult.status;
          serverStatus.textContent = matches ? staff ? 'Máy chủ đã đối chiếu cùng kết quả và từng tiêu chí.' : 'Máy chủ đã đối chiếu kết luận.' :
            `Kết quả khác nhau: giao diện ${localResult.status}, máy chủ ${remote.status || 'không rõ'}. Cần kiểm tra trước khi dùng.`;
          serverStatus.dataset.status = matches ? 'MATCH' : 'MISMATCH';
          if (download) download.disabled = !matches;
        }).catch(error => {
          if (disposed || serial !== evaluationSerial) return;
          serverStatus.textContent = `Chưa đối chiếu được với máy chủ: ${error.message}`;
          serverStatus.dataset.status = 'UNVERIFIED';
          if (download) download.disabled = true;
        });
      renderGateIntakeConclusion(conclusion, result);
      evaluationDetails?.render(result);
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
  download?.addEventListener('click', () => {
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
