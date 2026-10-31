import test from 'node:test';
import assert from 'node:assert/strict';
import { createObservationLoader, validateObservations } from '../frontend/src/shared/observation-contract.js';
import { dateOnly } from '../frontend/src/research-utils.js';

function response(site = 'A', changes = {}) {
  return { site_code: site, unit: 'mS/m', source: 'RESEARCH_SNAPSHOT', total: 1, items: [
    { site_code: site, unit: 'mS/m', observed_date: '2026-09-01', observed_at: null, time_precision: 'DATE_ONLY', ec_mS_m: 0,
      source_id: 'MRC', source_locator: 'source.csv:row 2' },
  ], ...changes };
}
function harness() {
  const pending = [], results = [], errors = [];
  const loader = createObservationLoader({
    api: (path, request) => new Promise((resolve, reject) => pending.push({ path, request, resolve, reject })),
    onResult: data => results.push(data), onError: error => errors.push(error),
  });
  return { pending, results, errors, loader };
}

test('observation selection ignores both late success and late failure from the previous station', async () => {
  for (const fail of [false, true]) {
    const h = harness(), a = h.loader.load('A'), b = h.loader.load('B');
    assert.equal(h.pending[0].request.signal.aborted, true);
    h.pending[1].resolve(response('B')); await b;
    if (fail) h.pending[0].reject(new Error('old A failure')); else h.pending[0].resolve(response('A'));
    assert.equal(await a, null);
    assert.deepEqual(h.results.map(data => data.site_code), ['B']); assert.deepEqual(h.errors, []);
  }
});

test('cleared workspace cannot be revived by an in-flight observation request', async () => {
  const h = harness(), loading = h.loader.load('A'); h.loader.cancel();
  h.pending[0].resolve(response());
  assert.equal(await loading, null); assert.deepEqual(h.results, []); assert.deepEqual(h.errors, []);
});

test('observation contract preserves zero EC, date-only precision, O/E flags and source timestamps', () => {
  assert.equal(validateObservations(response(), 'A').items[0].ec_mS_m, 0);
  for (const flag of ['O', 'E']) {
    const data = response(); Object.assign(data.items[0], { observed_or_estimated: flag, time_precision: 'SOURCE_TIMESTAMP', observed_at: '2026-08-31T18:00:00Z' });
    assert.equal(validateObservations(data, 'A').items[0].observed_or_estimated, flag);
  }
  assert.equal(dateOnly(null), 'chưa có ngày'); assert.equal(dateOnly('2026-09-01'), '01/09/2026');
});

test('wrong station, unit, invalid dates, missing sources and invented sampling hours cannot be displayed', async () => {
  const mutations = [
    data => { data.site_code = 'B'; }, data => { data.unit = 'g/L'; }, data => { data.total = 2; },
    data => { data.items[0].site_code = 'B'; }, data => { data.items[0].unit = 'g/L'; },
    data => { data.items[0].ec_mS_m = -1; }, data => { data.items[0].ec_mS_m = '10'; },
    data => { data.items[0].observed_date = '2026-02-30'; }, data => { data.items[0].source_locator = ''; },
    data => { data.items[0].observed_or_estimated = 'SIMULATION'; },
    data => { data.items[0].observed_at = '2026-09-01T00:00:00Z'; },
    data => { Object.assign(data.items[0], { time_precision: 'SOURCE_TIMESTAMP', observed_at: '2026-08-31T00:00:00Z' }); },
  ];
  for (const mutate of mutations) {
    const h = harness(), data = response(), loading = h.loader.load('A'); mutate(data); h.pending[0].resolve(data);
    assert.equal(await loading, null); assert.deepEqual(h.results, []); assert.equal(h.errors.length, 1);
  }
});
