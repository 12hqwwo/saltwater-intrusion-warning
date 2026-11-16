import { requestJSON, registerAuthorizationHeaderProvider } from '../api.js';
import { ROLE_PUBLIC } from './auth-roles.js';
import { saveAccessToken, readAccessToken, clearAccessToken } from './auth-session-storage.js';

let currentUser = null;

function changed() {
  window.dispatchEvent(new CustomEvent('workspace:auth-changed', { detail: { user: currentUser, role: currentUser?.role || ROLE_PUBLIC } }));
}

export function getCurrentUser() { return currentUser; }
export function getCurrentRole() { return currentUser?.role || ROLE_PUBLIC; }
export function getAuthorizationHeader() {
  const token = readAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function logout() { clearAccessToken(); currentUser = null; changed(); }

registerAuthorizationHeaderProvider(getAuthorizationHeader, () => {
  if (readAccessToken()) logout();
});

export async function loginWithPassword(username, password) {
  const result = await requestJSON('/auth/login', { method: 'POST', body: { username, password } });
  saveAccessToken(result.access_token);
  currentUser = result.user;
  changed();
  return currentUser;
}

export async function restoreSessionFromStorage() {
  if (!readAccessToken()) { changed(); return null; }
  try {
    currentUser = await requestJSON('/auth/me');
    changed();
    return currentUser;
  } catch {
    if (readAccessToken()) logout();
    return null;
  }
}
