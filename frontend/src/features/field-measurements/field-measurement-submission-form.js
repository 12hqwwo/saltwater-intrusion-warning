import { node, num } from '../../shared/ui.js';
import { convertEcToMsPerM } from './ec-unit-conversion.js';
import { submitFieldMeasurement } from './field-measurement-api.js';

export function createFieldMeasurementSubmissionForm(host, onSubmitted = () => {}) {
  const form = node('form', undefined, 'field-grid');
  const controls = {};
  function field(name, label, type = 'text', options) {
    const input = options ? node('select') : node('input');
    input.name = name;
    if (!options) input.type = type;
    if (options) for (const value of options) { const option = node('option', value); option.value = value; input.append(option); }
    if (type === 'number') input.step = 'any';
    if (['longitude', 'latitude', 'ec', 'observed_at', 'device'].includes(name)) input.required = true;
    const wrapper = node('label', label); wrapper.append(input); form.append(wrapper);
    controls[name] = input;
    return input;
  }
  field('longitude', 'Kinh độ', 'number'); field('latitude', 'Vĩ độ', 'number');
  field('ec', 'Giá trị EC gốc', 'number');
  field('unit', 'Đơn vị gốc', 'text', ['mS/m', 'µS/cm', 'dS/m', 'mS/cm']);
  field('observed_at', 'Thời điểm đo (GMT+7)', 'datetime-local');
  field('position_kind', 'Loại vị trí', 'text', ['RIVER', 'FIELD']);
  field('device', 'Mã thiết bị');
  field('ec_basis', 'Cơ sở EC', 'text', ['UNKNOWN', 'EC25', 'RAW']);
  field('calibrated_at', 'Ngày hiệu chuẩn', 'date');
  field('calibration_reference', 'Mã biên bản hiệu chuẩn (nếu có)');
  field('water_temp_degC', 'Nhiệt độ nước (°C, nếu có)', 'number');
  const converted = node('p', 'EC quy đổi: —', 'wide subtle');
  const button = node('button', 'Gửi phiếu chờ duyệt'); button.type = 'submit';
  const status = node('p', '', 'wide subtle'); status.setAttribute('role', 'status');
  form.append(converted, button, status); host.append(form);
  const update = () => {
    const value = convertEcToMsPerM(controls.ec.value, controls.unit.value);
    converted.textContent = value === null ? 'EC quy đổi: —' : `EC quy đổi: ${num(value)} mS/m`;
  };
  controls.ec.addEventListener('input', update);
  controls.unit.addEventListener('change', update);
  const selected = event => {
    const coordinate = event.detail?.coordinate;
    if (!Array.isArray(coordinate) || coordinate.length < 2) return;
    controls.longitude.value = coordinate[0].toFixed(6);
    controls.latitude.value = coordinate[1].toFixed(6);
  };
  window.addEventListener('workspace:field-point-selected', selected);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    if (convertEcToMsPerM(controls.ec.value, controls.unit.value) === null) { status.textContent = 'Giá trị EC hoặc đơn vị không hợp lệ.'; return; }
    const observed = controls.observed_at.value;
    const payload = {
      ec: Number(controls.ec.value), unit: controls.unit.value,
      observed_at: observed ? `${observed.length === 16 ? observed + ':00' : observed}+07:00` : '',
      longitude: Number(controls.longitude.value), latitude: Number(controls.latitude.value),
      position_kind: controls.position_kind.value, device: controls.device.value,
      ec_basis: controls.ec_basis.value, calibrated_at: controls.calibrated_at.value || null,
      calibration_reference: controls.calibration_reference.value || null,
      water_temp_degC: controls.water_temp_degC.value === '' ? null : Number(controls.water_temp_degC.value),
    };
    button.disabled = true;
    try {
      const saved = await submitFieldMeasurement(payload);
      status.textContent = `Đã gửi phiếu ${saved.measurement_id} · ${num(saved.ec_mS_m)} mS/m · đang chờ duyệt.`;
      onSubmitted();
    } catch (error) { status.textContent = error.message; }
    finally { button.disabled = false; }
  });
  update();
  return () => window.removeEventListener('workspace:field-point-selected', selected);
}
