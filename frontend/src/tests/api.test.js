import assert from 'node:assert/strict';
import test from 'node:test';
import { APIError, createRequestGate, getHistory, localDate, recentRange, requestJSON } from '../src/api.js';
import { describeSeries } from '../src/chart.js';

// Only in-memory fixtures; these are never used by the running application.
const SITE = 'TEST_SITE';
const SNAPSHOT = 'TEST_SNAPSHOT';
const dataset = { dataset_code: SNAPSHOT, sha256: 'a'.repeat(64) };
const row = index => ({
  ec_observation_id: index + 1,
  observed_at: new Date(Date.UTC(2000, 0, index + 1)).toISOString(),
  conductivity_ms_per_m: index + 1, unit: 'mS/m',
  quality_flag: 'UNVERIFIED', observed_or_estimated: 'O',
});
const filters = { date_from: null, date_to: null, quality_flag: null, observed_or_estimated: null };
const page = (rows, total = rows.length, offset = 0, hasMore = false) => ({
  site_code: SITE, dataset: { ...dataset }, unit: 'mS/m', offset, total,
  filters: { ...filters }, has_more: hasMore, items: rows,
});
const response = body => ({ ok: true, json: async () => structuredClone(body) });

test('loads every page before returning history; keeps one station and snapshot', async () => {
  const rows = Array.from({ length: 503 }, (_, i) => row(i));
  const offsets = [];
  const fetcher = async url => {
    const parsed = new URL(url, 'http://test.local');
    const offset = Number(parsed.searchParams.get('offset'));
    offsets.push(offset);
    assert.equal(parsed.searchParams.get('dataset_code'), SNAPSHOT);
    assert.equal(parsed.pathname, `/api/v1/stations/${SITE}/observations`);
    return response(page(rows.slice(offset, offset + 500), rows.length, offset, offset + 500 < rows.length));
  };
  const data = await getHistory(SITE, SNAPSHOT, {}, { fetcher });
  assert.equal(data.items.length, 503);
  assert.deepEqual(offsets, [0, 500]);
  assert.equal(data.items.at(-1).ec_observation_id, 503);
});

test('missing snapshot is rejected before any request', async () => {
  let called = false;
  await assert.rejects(getHistory(SITE, '', {}, { fetcher: async () => { called = true; } }), APIError);
  assert.equal(called, false);
});

test('filters are URL encoded and the response must echo them', async () => {
  const selected = { date_from: '2022-01-01', date_to: '2023-12-31', quality_flag: 'SUSPECT', observed_or_estimated: 'E' };
  const fetcher = async url => {
    const params = new URL(url, 'http://test.local').searchParams;
    for (const [key, value] of Object.entries(selected)) assert.equal(params.get(key), value);
    return response({ ...page([]), filters: selected });
  };
  assert.equal((await getHistory(SITE, SNAPSHOT, selected, { fetcher })).total, 0);
});

test('does not display a response for another station or snapshot', async () => {
  for (const changed of [{ site_code: 'OTHER' }, { dataset: { ...dataset, dataset_code: 'OTHER' } }]) {
    await assert.rejects(getHistory(SITE, SNAPSHOT, {}, { fetcher: async () => response({ ...page([row(0)]), ...changed }) }), /không khớp/);
  }
});

test('does not silently accept a server ignoring the requested date filter', async () => {
  await assert.rejects(getHistory(SITE, SNAPSHOT, { date_from: '2023-01-01' }, {
    fetcher: async () => response(page([])),
  }), /bộ lọc khác/);
});

test('duplicate observation across pages is rejected', async () => {
  let requests = 0;
  const fetcher = async () => response(++requests === 1
    ? page(Array.from({ length: 500 }, (_, i) => row(i)), 501, 0, true)
    : page([row(499)], 501, 500, false));
  await assert.rejects(getHistory(SITE, SNAPSHOT, {}, { fetcher }), /dòng trùng/);
});

test('changed snapshot hash between pages is rejected', async () => {
  let requests = 0;
  const fetcher = async () => response(++requests === 1
    ? page(Array.from({ length: 500 }, (_, i) => row(i)), 501, 0, true)
    : { ...page([row(500)], 501, 500), dataset: { ...dataset, sha256: 'b'.repeat(64) } });
  await assert.rejects(getHistory(SITE, SNAPSHOT, {}, { fetcher }), /thay đổi/);
});

test('early final page is rejected instead of showing a partial chart', async () => {
  await assert.rejects(getHistory(SITE, SNAPSHOT, {}, {
    fetcher: async () => response(page([row(0)], 2)),
  }), /Phân trang không nhất quán/);
});

test('empty page marked has_more cannot create an infinite loop', async () => {
  let count = 0;
  await assert.rejects(getHistory(SITE, SNAPSHOT, {}, {
    fetcher: async () => { count++; return response(page([], 2, 0, true)); },
  }), /Phân trang không nhất quán/);
  assert.equal(count, 1);
});

test('an empty date window is a valid empty result', async () => {
  const result = await getHistory(SITE, SNAPSHOT, {}, { fetcher: async () => response(page([])) });
  assert.deepEqual(result.items, []);
  assert.equal(result.total, 0);
});

test('quality labels and O/E are retained including INVALID', async () => {
  const rows = [
    row(0), { ...row(1), quality_flag: 'SUSPECT', observed_or_estimated: 'E' },
    { ...row(2), quality_flag: 'INVALID' },
  ];
  const result = await getHistory(SITE, SNAPSHOT, {}, { fetcher: async () => response(page(rows)) });
  assert.deepEqual(result.items, rows);
});

test('rejects invalid EC, wrong unit, and timestamp without timezone', async () => {
  for (const changed of [{ conductivity_ms_per_m: null }, { conductivity_ms_per_m: -1 }, { unit: 'ppt' }, { observed_at: '2023-12-15T00:00:00' }]) {
    await assert.rejects(getHistory(SITE, SNAPSHOT, {}, {
      fetcher: async () => response(page([{ ...row(0), ...changed }])),
    }), /không hợp lệ/);
  }
});

test('request gate cancels old work and identifies stale results', () => {
  const gate = createRequestGate();
  const old = gate.next();
  const current = gate.next();
  assert.equal(old.signal.aborted, true);
  assert.equal(old.isCurrent(), false);
  assert.equal(current.signal.aborted, false);
  assert.equal(current.isCurrent(), true);
});

test('Vietnam date and 24-month range use observation dates, not computer timezone', () => {
  assert.equal(localDate('2023-12-14T17:00:00Z'), '2023-12-15');
  assert.deepEqual(recentRange({ first_observation: '1985-05-15T00:00:00+07:00', last_observation: '2023-12-15T00:00:00+07:00' }), { date_from: '2022-01-01', date_to: '2023-12-15' });
  assert.deepEqual(recentRange({ first_observation: '2023-08-15T00:00:00+07:00', last_observation: '2023-12-15T00:00:00+07:00' }), { date_from: '2023-08-15', date_to: '2023-12-15' });
});

test('summary excludes INVALID but preserves UNVERIFIED and SUSPECT', () => {
  const summary = describeSeries([
    { ...row(0), conductivity_ms_per_m: 22 },
    { ...row(1), conductivity_ms_per_m: 28, quality_flag: 'SUSPECT' },
    { ...row(2), conductivity_ms_per_m: 900, quality_flag: 'INVALID' },
  ]);
  assert.deepEqual(summary, { count: 3, excluded: 1, mean: 25, max: 28 });
  assert.equal(describeSeries([]).mean, null);
});

test('API error or HTML response does not become an empty successful dataset', async () => {
  await assert.rejects(requestJSON('/health', {
    fetcher: async () => ({ ok: false, status: 503, json: async () => ({ detail: { message: 'Database unavailable' } }) }),
  }), /Database unavailable/);
  await assert.rejects(requestJSON('/health', {
    fetcher: async () => ({ ok: false, status: 502, json: async () => { throw new SyntaxError(); } }),
  }), /JSON/);
});
