import { node } from '../shared/ui.js';

export function createGateIntakeMeasurementForm(form, controls, addControl) {
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
}
