import assert from 'node:assert/strict';
import test from 'node:test';

import { APIError, createRequestGate, requestJSON } from '../frontend/src/api.js';

test('gate dossier POST sends the selected input and policy as JSON', async () => {
  const payload = { policy: { gate_code: 'G1' }, input: { gate_code: 'G1' } };
  let received;
  const result = await requestJSON('/workspace/gate-evaluation', {
    method: 'POST',
    body: payload,
    fetcher: async (url, options) => {
      received = { url, options };
      return { ok: true, json: async () => ({ status: 'INSUFFICIENT_DATA' }) };
    },
  });
  assert.equal(received.url, '/api/v1/workspace/gate-evaluation');
  assert.equal(received.options.method, 'POST');
  assert.equal(received.options.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(received.options.body), payload);
  assert.equal(result.status, 'INSUFFICIENT_DATA');
});

test('station switch cancels the pending request without reporting it as a server error', async () => {
  const requests = createRequestGate();
  const first = requests.next();
  const pending = requestJSON('/workspace/monthly-estimates?station=MyTho', {
    ...first,
    fetcher: async (_url, { signal }) => new Promise((_resolve, reject) => {
      signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
    }),
  });
  const rejected = assert.rejects(pending, { name: 'AbortError' });
  const second = requests.next();
  await rejected;
  assert.equal(first.isCurrent(), false);
  assert.equal(second.isCurrent(), true);
});

test('API error detail reaches the feature instead of being replaced with a network message', async () => {
  await assert.rejects(requestJSON('/workspace/summary', {
    fetcher: async () => ({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'Snapshot checksum mismatch.' }),
    }),
  }), error => error instanceof APIError && error.message === 'Snapshot checksum mismatch.');
});

test('a non-JSON response cannot be displayed as successful application data', async () => {
  await assert.rejects(requestJSON('/workspace/summary', {
    fetcher: async () => ({
      ok: true,
      json: async () => { throw new SyntaxError('HTML received'); },
    }),
  }), APIError);
});
