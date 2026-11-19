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

registerAuthorizationHeaderProvider(getAuthorizationHeader, authorization => {
  const token = readAccessToken();
  if (token && authorization === `Bearer ${token}`) {
    logout();
    window.dispatchEvent(new CustomEvent('workspace:session-expired'));
  }
});

export async function loginWithPassword(username, password) {
  const result = await requestJSON('/auth/login', { method: 'POST', body: { username, password } });
  saveAccessToken(result.access_token);
  currentUser = result.user;
  changed();
  return currentUser;
}

export function registerAccount(username, displayName, password) {
  return requestJSON('/auth/register', { method: 'POST', body: { username, display_name: displayName, password } });
}

export function listPendingAccounts() {
  return requestJSON('/auth/pending');
}

export function approveAccount(userId) {
  return requestJSON(`/auth/pending/${encodeURIComponent(userId)}/approve`, { method: 'POST' });
}

export async function restoreSessionFromStorage() {
  const token = readAccessToken();
  if (!token) { changed(); return null; }
  try {
    const user = await requestJSON('/auth/me');
    if (readAccessToken() !== token) return null;
    currentUser = user;
    changed();
    return currentUser;
  } catch (error) {
    if (error.status === 401 && readAccessToken() === token) logout();
    else if (currentUser === null && readAccessToken() === token) changed();
    return null;
  }
}
