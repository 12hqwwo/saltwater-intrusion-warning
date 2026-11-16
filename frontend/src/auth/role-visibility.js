import { ROLE_PUBLIC } from './auth-roles.js';

export function applyRoleVisibility(role = ROLE_PUBLIC) {
  for (const element of document.querySelectorAll('[data-visible-for-roles]')) {
    element.hidden = !element.dataset.visibleForRoles.split(/\s+/).includes(role);
  }
}
