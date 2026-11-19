import test from 'node:test';
import assert from 'node:assert/strict';

const values = new Map();
globalThis.sessionStorage = {
  getItem: key => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, value),
  removeItem: key => values.delete(key),
};
globalThis.window = new EventTarget();
globalThis.CustomEvent = class extends Event {
  constructor(type, options = {}) { super(type); this.detail = options.detail; }
};

const { requestJSON, APIError } = await import('../api.js');
const auth = await import('./auth-service.js');
const response = (status, body) => ({ ok: status >= 200 && status < 300, status,
  json: async () => body });

test('temporary /auth/me failure retains the token', async () => {
  values.set('webgis.access_token', 'saved-token');
  globalThis.fetch = async () => response(503, { detail: 'Unavailable' });
  let updates = 0;
  const onChange = () => { updates++; };
  window.addEventListener('workspace:auth-changed', onChange);
  assert.equal(await auth.restoreSessionFromStorage(), null);
  window.removeEventListener('workspace:auth-changed', onChange);
  assert.equal(values.get('webgis.access_token'), 'saved-token');
  assert.equal(updates, 1);
});

test('401 from /auth/me clears the matching token', async () => {
  values.set('webgis.access_token', 'expired-token');
  globalThis.fetch = async () => response(401, { detail: 'Expired' });
  assert.equal(await auth.restoreSessionFromStorage(), null);
  assert.equal(values.has('webgis.access_token'), false);
});

test('late 401 cannot log out a newer session', async () => {
  values.set('webgis.access_token', 'old-token');
  let finishOld;
  globalThis.fetch = async (url) => url.endsWith('/auth/me')
    ? new Promise(resolve => { finishOld = resolve; })
    : response(200, { access_token: 'new-token', user: { username: 'staff', role: 'FIELD_STAFF' } });
  const restoring = auth.restoreSessionFromStorage();
  await auth.loginWithPassword('staff', 'correct-password');
  finishOld(response(401, { detail: 'Expired' }));
  await restoring;
  assert.equal(values.get('webgis.access_token'), 'new-token');
  assert.equal(auth.getCurrentUser().username, 'staff');
});

test('401 on a working request clears the matching session and requests re-login', async () => {
  let expired = 0;
  window.addEventListener('workspace:session-expired', () => { expired++; }, { once: true });
  globalThis.fetch = async () => response(401, { detail: 'Expired' });
  await assert.rejects(requestJSON('/workspace/summary'), error =>
    error instanceof APIError && error.status === 401);
  assert.equal(expired, 1);
  assert.equal(values.has('webgis.access_token'), false);
  assert.equal(auth.getCurrentUser(), null);
});
