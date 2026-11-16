const KEY = 'webgis.access_token';

export function saveAccessToken(token) { globalThis.sessionStorage?.setItem(KEY, token); }
export function readAccessToken() { return globalThis.sessionStorage?.getItem(KEY) || null; }
export function clearAccessToken() { globalThis.sessionStorage?.removeItem(KEY); }
