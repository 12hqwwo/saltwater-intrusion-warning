export const ROLE_PUBLIC = 'PUBLIC';
export const ROLE_FIELD_STAFF = 'FIELD_STAFF';
export const ROLE_INSPECTOR = 'INSPECTOR';

export function roleCanViewSection(role, view) {
  return role !== ROLE_PUBLIC || !['data-quality', 'forecasts'].includes(view);
}
