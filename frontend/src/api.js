/** API contract for backend/main.py. No sample data or fallback observations. */
const ROOT = '/api/v1';
const PAGE_SIZE = 500;
const MAX_ROWS = 20_000;
const FLAGS = new Set(['UNVERIFIED', 'VALIDATED', 'SUSPECT', 'INVALID']);
export const TIME_ZONE = 'Asia/Ho_Chi_Minh';

export class APIError extends Error {}

export async function requestJSON(path, { signal, fetcher = globalThis.fetch } = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  let timedOut = false;
  if (signal?.aborted) abort();
  signal?.addEventListener('abort', abort, { once: true });
  const timer = setTimeout(() => { timedOut = true; abort(); }, 15_000);
  try {
    const response = await fetcher(`${ROOT}${path}`, {
      signal: controller.signal, headers: { Accept: 'application/json' },
    });
    let body;
    try { body = await response.json(); }
    catch { throw new APIError('API chưa trả về dữ liệu JSON. Kiểm tra backend đang chạy ở cổng 8000.'); }
    if (!response.ok) {
      const message = typeof body.detail === 'string' ? body.detail : body.detail?.message;
      throw new APIError(message || `Không đọc được dữ liệu (HTTP ${response.status}).`);
    }
    return body;
  } catch (error) {
    if (signal?.aborted) throw new DOMException('Đã hủy yêu cầu cũ.', 'AbortError');
    if (timedOut) throw new APIError('Yêu cầu quá 15 giây. Hãy kiểm tra kết nối rồi thử lại.');
    if (error instanceof APIError) throw error;
    throw new APIError('Không kết nối được API. Kiểm tra backend và thử tải lại.');
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abort);
  }
}

export async function getStations(options) {
  const data = await requestJSON('/stations', options);
  if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) {
    throw new APIError('Danh sách trạm không đúng cấu trúc GeoJSON.');
  }
  const codes = new Set();
  for (const feature of data.features) {
    const code = feature.properties?.site_code;
    if (!code || typeof code !== 'string' || codes.has(code)) {
      throw new APIError('Danh sách trạm có mã thiếu hoặc trùng.');
    }
    codes.add(code);
  }
  return data;
}

export async function getDatasets(siteCode, options) {
  const data = await requestJSON(`/stations/${encodeURIComponent(siteCode)}/datasets`, options);
  if (data.site_code !== siteCode || data.unit !== 'mS/m' || !Array.isArray(data.items)) {
    throw new APIError('Bộ dữ liệu trả về không khớp trạm hoặc đơn vị EC.');
  }
  return data.items;
}

export async function getHistory(siteCode, datasetCode, filters = {}, options = {}) {
  if (!datasetCode) throw new APIError('Hãy chọn một bộ dữ liệu trước khi xem lịch sử.');
  const params = new URLSearchParams({ dataset_code: datasetCode, limit: String(PAGE_SIZE) });
  for (const key of ['date_from', 'date_to', 'quality_flag', 'observed_or_estimated']) {
    if (filters[key]) params.set(key, filters[key]);
  }
  let offset = 0;
  let first = null;
  const items = [];
  const ids = new Set();
  while (true) {
    if (options.signal?.aborted) throw new DOMException('Đã hủy yêu cầu cũ.', 'AbortError');
    params.set('offset', String(offset));
    const page = await requestJSON(
      `/stations/${encodeURIComponent(siteCode)}/observations?${params}`, options,
    );
    if (page.site_code !== siteCode || page.dataset?.dataset_code !== datasetCode ||
        page.unit !== 'mS/m' || page.offset !== offset ||
        !Number.isSafeInteger(page.total) || page.total < 0 ||
        !Array.isArray(page.items) || typeof page.has_more !== 'boolean') {
      throw new APIError('Phản hồi lịch sử không khớp trạm, bộ dữ liệu hoặc trang yêu cầu.');
    }
    for (const key of ['date_from', 'date_to', 'quality_flag', 'observed_or_estimated']) {
      if ((page.filters?.[key] || '') !== (filters[key] || '')) {
        throw new APIError('API trả về bộ lọc khác yêu cầu. Chưa hiển thị biểu đồ.');
      }
    }
    if (page.total > MAX_ROWS) throw new APIError('Khoảng chọn vượt 20.000 số đo. Hãy thu hẹp thời gian.');
    if (first && (first.total !== page.total || first.dataset.sha256 !== page.dataset.sha256)) {
      throw new APIError('Bộ dữ liệu thay đổi trong lúc tải. Hãy thử lại.');
    }
    first ??= page;
    for (const row of page.items) {
      if (!Number.isSafeInteger(row.ec_observation_id) || ids.has(row.ec_observation_id) ||
          row.unit !== 'mS/m' || !Number.isFinite(row.conductivity_ms_per_m) ||
          row.conductivity_ms_per_m < 0 || !FLAGS.has(row.quality_flag) ||
          !['O', 'E'].includes(row.observed_or_estimated) ||
          typeof row.observed_at !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(row.observed_at) ||
          !Number.isFinite(Date.parse(row.observed_at))) {
        throw new APIError('Dữ liệu có dòng trùng hoặc giá trị không hợp lệ. Chưa hiển thị biểu đồ.');
      }
      if (items.length && Date.parse(row.observed_at) < Date.parse(items.at(-1).observed_at)) {
        throw new APIError('Thứ tự thời gian giữa các trang không nhất quán.');
      }
      ids.add(row.ec_observation_id);
      items.push(row);
    }
    offset += page.items.length;
    options.onProgress?.(offset, page.total);
    if (offset > page.total || (!page.has_more && offset !== page.total) ||
        (page.has_more && (!page.items.length || offset >= page.total))) {
      throw new APIError('Phân trang không nhất quán; chưa nhận đủ lịch sử.');
    }
    if (!page.has_more) break;
  }
  return { ...first, items, offset: 0, has_more: false };
}

/** One active request: old station/filter results cannot overwrite the new view. */
export function createRequestGate() {
  let controller;
  let serial = 0;
  return {
    next() {
      controller?.abort();
      controller = new AbortController();
      const ticket = ++serial;
      return { signal: controller.signal, isCurrent: () => ticket === serial };
    },
  };
}

export function localDate(iso) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(iso));
  const get = type => parts.find(part => part.type === type).value;
  return `${get('year')}-${get('month')}-${get('day')}`;
}

export function recentRange(dataset) {
  const end = localDate(dataset.last_observation);
  const [year, month] = end.split('-').map(Number);
  const start = new Date(Date.UTC(year, month - 1 - 23, 1)).toISOString().slice(0, 10);
  return { date_from: [start, localDate(dataset.first_observation)].sort().at(-1), date_to: end };
}
