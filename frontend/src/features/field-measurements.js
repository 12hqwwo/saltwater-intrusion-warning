import { requestJSON } from '../api.js';
import { node, num } from '../shared/ui.js';

const FACTORS = { 'µS/cm': .1, 'dS/m': 100, 'mS/cm': 100, 'mS/m': 1 };
export function convertedEc(value, unit) {
  const numeric = Number(value);
  return value !== '' && Number.isFinite(numeric) && numeric >= 0 && Object.hasOwn(FACTORS, unit)
    ? numeric * FACTORS[unit] : null;
}
export function approvedMapItems(items) {
  return (items || []).filter(item => item.status === 'APPROVED' &&
    Number.isFinite(item.longitude) && Number.isFinite(item.latitude));
}

export function createFieldMeasurements(host) {
  if (!host) return { loadApproved: async () => {} };
  const panel = node('section', undefined, 'panel field-measurements');
  panel.append(node('h3', 'Phiếu EC thực địa · cán bộ nội bộ'),
    node('p', 'Phiếu mới luôn chờ duyệt, tách khỏi chuỗi MRC. Chỉ phiếu đã duyệt mới hiện trên bản đồ. Dữ liệu đã duyệt cũng chưa mặc nhiên là nhãn EC tháng.', 'subtle'));
  const form = node('form', undefined, 'field-grid');
  const controls = {};
  function field(name, label, type = 'text', options) {
    const input = options ? node('select') : node('input');
    input.name = name;
    if (!options) input.type = type;
    if (options) for (const value of options) { const option = node('option', value); option.value = value; input.append(option); }
    if (type === 'number') input.step = 'any';
    const wrapper = node('label', label); wrapper.append(input); form.append(wrapper);
    controls[name] = input;
    if (['longitude', 'latitude', 'ec', 'observed_at', 'device', 'submitted_by', 'submit_key'].includes(name)) input.required = true;
    return input;
  }
  field('longitude', 'Kinh độ', 'number'); field('latitude', 'Vĩ độ', 'number');
  field('ec', 'Giá trị EC gốc', 'number');
  field('unit', 'Đơn vị gốc', 'text', ['mS/m', 'µS/cm', 'dS/m', 'mS/cm']);
  field('observed_at', 'Thời điểm đo (GMT+7)', 'datetime-local');
  field('position_kind', 'Loại vị trí', 'text', ['RIVER', 'FIELD']);
  field('device', 'Mã thiết bị'); field('submitted_by', 'Người gửi');
  field('ec_basis', 'Cơ sở EC', 'text', ['UNKNOWN', 'EC25', 'RAW']);
  field('calibrated_at', 'Ngày hiệu chuẩn', 'date');
  field('calibration_reference', 'Mã biên bản hiệu chuẩn (nếu có)');
  field('water_temp_degC', 'Nhiệt độ nước (°C, nếu có)', 'number');
  const submitKey = field('submit_key', 'API key gửi phiếu', 'password');
  submitKey.autocomplete = 'off';
  const converted = node('p', 'EC quy đổi: —', 'wide subtle');
  const submitButton = node('button', 'Gửi phiếu chờ duyệt'); submitButton.type = 'submit';
  const submitStatus = node('p', '', 'wide subtle'); submitStatus.setAttribute('role', 'status');
  form.append(converted, submitButton, submitStatus); panel.append(form);
  const reviewPanel = node('details'); reviewPanel.append(node('summary', 'Hàng chờ duyệt · cán bộ kiểm tra'));
  const reviewKey = node('input'); reviewKey.type = 'password'; reviewKey.autocomplete = 'off';
  const reviewKeyLabel = node('label', 'API key duyệt phiếu'); reviewKeyLabel.append(reviewKey);
  const reviewer = node('input'); reviewer.type = 'text';
  const reviewerLabel = node('label', 'Người duyệt'); reviewerLabel.append(reviewer);
  const loadPendingButton = node('button', 'Đọc hàng chờ', 'secondary'); loadPendingButton.type = 'button';
  const reviewStatus = node('p', '', 'subtle');
  const queue = node('div');
  reviewPanel.append(reviewKeyLabel, reviewerLabel, loadPendingButton, reviewStatus, queue);
  panel.append(reviewPanel);
  const approvedStatus = node('p', 'Đang tải phiếu đã duyệt…', 'subtle');
  panel.append(node('h4', 'Phiếu đã duyệt trên bản đồ'), approvedStatus);
  host.replaceChildren(panel);

  function updateConversion() {
    const value = convertedEc(controls.ec.value, controls.unit.value);
    converted.textContent = value === null ? 'EC quy đổi: —' : `EC quy đổi: ${num(value)} mS/m`;
  }
  controls.ec.addEventListener('input', updateConversion);
  controls.unit.addEventListener('change', updateConversion);
  window.addEventListener('workspace:field-point-selected', event => {
    const coordinate = event.detail?.coordinate;
    if (!Array.isArray(coordinate) || coordinate.length < 2) return;
    controls.longitude.value = coordinate[0].toFixed(6);
    controls.latitude.value = coordinate[1].toFixed(6);
  });

  async function loadApproved() {
    try {
      const data = await requestJSON('/field-measurements?status=APPROVED');
      const items = approvedMapItems(data.items);
      approvedStatus.textContent = `${items.length} phiếu đã duyệt; ký hiệu tam giác trên bản đồ, không phải quan trắc MRC.`;
      window.dispatchEvent(new CustomEvent('workspace:approved-field-measurements', { detail: items }));
    } catch (error) {
      approvedStatus.textContent = `Chưa tải được phiếu đã duyệt: ${error.message}`;
    }
  }

  async function loadPending() {
    if (!reviewKey.value) { reviewStatus.textContent = 'Cần API key duyệt phiếu.'; return; }
    reviewStatus.textContent = 'Đang đọc hàng chờ…';
    try {
      const data = await requestJSON('/field-measurements?status=PENDING', { headers: { 'X-API-Key': reviewKey.value } });
      queue.replaceChildren();
      for (const item of data.items || []) {
        const row = node('article', undefined, 'source-card');
        row.append(node('p', `${item.measurement_id} · ${num(item.ec_mS_m)} mS/m · ${item.observed_at} · ${item.submitted_by}`));
        const note = node('input'); note.type = 'text'; note.placeholder = 'Ghi chú duyệt';
        row.append(note);
        for (const decision of ['APPROVED', 'REJECTED']) {
          const button = node('button', decision === 'APPROVED' ? 'Duyệt' : 'Từ chối', 'secondary');
          button.type = 'button';
          button.addEventListener('click', async () => {
            if (!reviewer.value.trim()) { reviewStatus.textContent = 'Cần ghi người duyệt.'; return; }
            button.disabled = true;
            try {
              await requestJSON(`/field-measurements/${encodeURIComponent(item.measurement_id)}/review`, {
                method: 'POST', headers: { 'X-API-Key': reviewKey.value },
                body: { decision, reviewer: reviewer.value.trim(), note: note.value },
              });
              reviewStatus.textContent = `Đã ghi quyết định ${decision} cho ${item.measurement_id}.`;
              await Promise.all([loadPending(), loadApproved()]);
            } catch (error) { reviewStatus.textContent = error.message; button.disabled = false; }
          });
          row.append(button);
        }
        queue.append(row);
      }
      reviewStatus.textContent = `${(data.items || []).length} phiếu đang chờ duyệt.`;
    } catch (error) { reviewStatus.textContent = error.message; }
  }
  loadPendingButton.addEventListener('click', loadPending);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!submitKey.value) { submitStatus.textContent = 'Cần API key gửi phiếu của cán bộ nội bộ.'; return; }
    if (!form.reportValidity()) return;
    const value = convertedEc(controls.ec.value, controls.unit.value);
    if (value === null) { submitStatus.textContent = 'Giá trị EC hoặc đơn vị không hợp lệ.'; return; }
    const observed = controls.observed_at.value;
    const payload = {
      ec: Number(controls.ec.value), unit: controls.unit.value,
      observed_at: observed ? `${observed.length === 16 ? observed + ':00' : observed}+07:00` : '',
      longitude: Number(controls.longitude.value), latitude: Number(controls.latitude.value),
      position_kind: controls.position_kind.value, device: controls.device.value,
      submitted_by: controls.submitted_by.value, ec_basis: controls.ec_basis.value,
      calibrated_at: controls.calibrated_at.value || null,
      calibration_reference: controls.calibration_reference.value || null,
      water_temp_degC: controls.water_temp_degC.value === '' ? null : Number(controls.water_temp_degC.value),
    };
    submitButton.disabled = true;
    try {
      const saved = await requestJSON('/field-measurements', { method: 'POST', body: payload,
        headers: { 'X-API-Key': submitKey.value } });
      submitStatus.textContent = `Đã gửi phiếu ${saved.measurement_id} · ${num(saved.ec_mS_m)} mS/m · đang chờ duyệt.`;
    } catch (error) { submitStatus.textContent = error.message; }
    finally { submitButton.disabled = false; }
  });
  updateConversion(); loadApproved();
  return { loadApproved, loadPending };
}
