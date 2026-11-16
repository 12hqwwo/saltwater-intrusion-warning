import test from 'node:test';
import assert from 'node:assert/strict';
import { bindNavigation } from '../frontend/src/app/navigation.js';
import { loginWithPassword, logout, getCurrentRole } from '../frontend/src/auth/auth-service.js';
import { roleCanViewSection } from '../frontend/src/auth/auth-roles.js';

test('guest cannot open staff tab and staff navigation shows only the selected section', async () => {
  const previous = { window: globalThis.window, document: globalThis.document, location: globalThis.location,
    sessionStorage: globalThis.sessionStorage, fetch: globalThis.fetch, CustomEvent: globalThis.CustomEvent };
  const events = new EventTarget();
  const elements = ['overview', 'observations', 'forecasts', 'data-quality', 'gates'].map(view => ({
    dataset: { view, ...(['data-quality', 'forecasts'].includes(view) ? { visibleForRoles: 'FIELD_STAFF INSPECTOR' } : {}) },
    hidden: false, scrollIntoView() {},
  }));
  const links = elements.map(element => ({ hash: '#' + element.dataset.view, textContent: element.dataset.view,
    dataset: { ...element.dataset }, hidden: false,
    setAttribute(name, value) { this[name] = value; }, removeAttribute(name) { delete this[name]; } }));
  globalThis.window = events;
  globalThis.location = { hash: '#data-quality' };
  globalThis.document = {
    title: '', querySelectorAll(selector) {
      if (selector === '[data-view]') return elements;
      if (selector === 'nav a') return links;
      if (selector === '[data-visible-for-roles]') return [...elements, ...links].filter(item => item.dataset.visibleForRoles);
      return [];
    },
    querySelector() { return links.find(link => link['aria-current'] === 'page'); },
    getElementById(view) { return elements.find(item => item.dataset.view === view); },
  };
  const store = new Map();
  globalThis.sessionStorage = { setItem: (key, value) => store.set(key, value), getItem: key => store.get(key) || null,
    removeItem: key => store.delete(key) };
  globalThis.CustomEvent = class extends Event { constructor(type, options) { super(type); this.detail = options.detail; } };
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({ access_token: 'test-token',
    user: { username: 'canbo', display_name: 'Cán bộ đo', role: 'FIELD_STAFF' } }) });
  try {
    bindNavigation(view => roleCanViewSection(getCurrentRole(), view));
    assert.equal(location.hash, '#observations');
    assert.equal(elements.find(item => item.dataset.view === 'data-quality').hidden, true);
    location.hash = '#forecasts'; events.dispatchEvent(new Event('hashchange'));
    assert.equal(location.hash, '#observations');
    assert.equal(elements.find(item => item.dataset.view === 'forecasts').hidden, true);
    await loginWithPassword('canbo', 'test-password');
    location.hash = '#data-quality'; events.dispatchEvent(new Event('hashchange'));
    assert.equal(elements.find(item => item.dataset.view === 'data-quality').hidden, false);
    location.hash = '#forecasts'; events.dispatchEvent(new Event('hashchange'));
    assert.equal(elements.find(item => item.dataset.view === 'data-quality').hidden, true);
    assert.equal(elements.find(item => item.dataset.view === 'forecasts').hidden, false);
  } finally {
    logout();
    Object.assign(globalThis, previous);
  }
});
