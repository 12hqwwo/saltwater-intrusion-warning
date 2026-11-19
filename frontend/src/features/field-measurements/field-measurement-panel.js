import { node } from '../../shared/ui.js';
import { ROLE_FIELD_STAFF, ROLE_INSPECTOR } from '../../auth/auth-roles.js';
import { loadApprovedFieldMeasurementsForMap } from './approved-field-measurements-layer.js';
import { createFieldMeasurementSubmissionForm } from './field-measurement-submission-form.js';
import { createMyFieldMeasurementsList } from './my-field-measurements-list.js';
import { createFieldMeasurementReviewQueue } from './field-measurement-review-queue.js';

export function mountFieldMeasurementPanelForRole(host, role = 'PUBLIC') {
  if (!host) return { loadApproved: async () => {}, destroy() {} };
  const panel = node('section', undefined, 'panel field-measurements');
  panel.append(node('h3', 'Phiếu EC thực địa'),
    node('p', 'Phiếu mới luôn chờ duyệt, tách khỏi chuỗi MRC. Chỉ phiếu đã duyệt mới hiện trên bản đồ.', 'subtle'));
  let destroyForm = () => {};
  const loadApproved = loadApprovedFieldMeasurementsForMap(panel);
  if (role === ROLE_FIELD_STAFF) {
    const mine = createMyFieldMeasurementsList(panel);
    destroyForm = createFieldMeasurementSubmissionForm(panel, mine);
  }
  if (role === ROLE_INSPECTOR) createFieldMeasurementReviewQueue(panel, loadApproved);
  host.replaceChildren(panel);
  return { loadApproved, destroy() { loadApproved.cancel?.(); destroyForm(); host.replaceChildren(); } };
}
