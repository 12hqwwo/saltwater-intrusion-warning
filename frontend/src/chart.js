import { localDate, TIME_ZONE } from './api.js';

export const QUALITY_LABELS = {
  UNVERIFIED: 'Chưa xác minh', VALIDATED: 'Đã xác minh',
  SUSPECT: 'Cần kiểm tra', INVALID: 'Không hợp lệ',
};
const COLORS = { UNVERIFIED: '#a47725', VALIDATED: '#087f78', SUSPECT: '#ce6b21', INVALID: '#bf4658' };
export const number = value => new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 }).format(value);
export const dateLabel = iso => new Intl.DateTimeFormat('vi-VN', {
  timeZone: TIME_ZONE, day: '2-digit', month: '2-digit', year: 'numeric',
}).format(new Date(iso));

function svgNode(tag, attributes = {}, text) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
  if (text !== undefined) node.textContent = text;
  return node;
}

export function describeSeries(items) {
  const included = items.filter(row => row.quality_flag !== 'INVALID');
  const values = included.map(row => row.conductivity_ms_per_m);
  return {
    count: items.length, excluded: items.length - values.length,
    mean: values.length ? values.reduce((a, b) => a + b, 0) / values.length : null,
    max: values.length ? Math.max(...values) : null,
  };
}

export function renderChart(container, items) {
  container.replaceChildren();
  if (!items.length) {
    const note = document.createElement('p');
    note.className = 'empty-chart';
    note.textContent = 'Không có quan trắc trong bộ lọc này. Hãy thử khoảng thời gian hoặc cờ chất lượng khác.';
    container.append(note);
    return;
  }
  const width = 960, height = 300;
  const margin = { left: 64, right: 25, top: 22, bottom: 45 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const times = items.map(row => Date.parse(row.observed_at));
  let minTime = times[0], maxTime = times.at(-1);
  if (minTime === maxTime) { minTime -= 15 * 86400000; maxTime += 15 * 86400000; }
  const maxValue = Math.max(1, ...items.map(row => row.conductivity_ms_per_m)) * 1.12;
  const x = time => margin.left + (time - minTime) / (maxTime - minTime) * plotWidth;
  const y = value => margin.top + plotHeight * (1 - value / maxValue);
  const svg = svgNode('svg', { viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-labelledby': 'ec-chart-title ec-chart-description' });
  svg.append(svgNode('title', { id: 'ec-chart-title' }, 'Độ dẫn điện EC theo thời gian, đơn vị mS/m'));
  svg.append(svgNode('desc', { id: 'ec-chart-description' }, `${items.length} số đo, từ ${dateLabel(items[0].observed_at)} đến ${dateLabel(items.at(-1).observed_at)}. Giá trị và chất lượng từng số đo có trong bảng phía dưới. Đường nối dừng tại tháng thiếu hoặc giá trị INVALID.`));
  for (let i = 0; i <= 4; i++) {
    const value = maxValue * i / 4;
    svg.append(svgNode('line', { x1: margin.left, x2: width - margin.right, y1: y(value), y2: y(value), stroke: '#e7ecec', 'stroke-dasharray': i ? '3 5' : '0' }));
    svg.append(svgNode('text', { x: margin.left - 12, y: y(value) + 4, 'text-anchor': 'end', class: 'axis-label' }, number(value)));
  }
  const wide = maxTime - minTime > 850 * 86400000;
  const axisFormatter = new Intl.DateTimeFormat('vi-VN', { timeZone: TIME_ZONE, ...(wide ? { year: 'numeric' } : { month: '2-digit', year: '2-digit' }) });
  for (let i = 0; i <= 5; i++) {
    const time = minTime + (maxTime - minTime) * i / 5;
    svg.append(svgNode('text', { x: x(time), y: height - 14, 'text-anchor': i === 0 ? 'start' : i === 5 ? 'end' : 'middle', class: 'axis-label' }, axisFormatter.format(new Date(time))));
  }
  let path = '';
  let previousMonth = null;
  for (const row of items) {
    const [year, month] = localDate(row.observed_at).split('-').map(Number);
    const monthIndex = year * 12 + month;
    if (row.quality_flag === 'INVALID') { previousMonth = null; continue; }
    const connected = previousMonth !== null && monthIndex - previousMonth <= 1;
    path += `${connected ? 'L' : 'M'}${x(Date.parse(row.observed_at)).toFixed(2)},${y(row.conductivity_ms_per_m).toFixed(2)} `;
    previousMonth = monthIndex;
  }
  svg.append(svgNode('path', { d: path, fill: 'none', stroke: '#238e86', 'stroke-width': 2, 'stroke-linejoin': 'round' }));
  for (const row of items) {
    const px = x(Date.parse(row.observed_at)), py = y(row.conductivity_ms_per_m);
    const color = COLORS[row.quality_flag];
    const invalid = row.quality_flag === 'INVALID';
    const point = invalid
      ? svgNode('path', { d: `M${px-4},${py-4}l8,8m-8,0l8,-8`, stroke: color, 'stroke-width': 2, 'data-quality': row.quality_flag })
      : svgNode('circle', { cx: px, cy: py, r: items.length > 120 ? 2.4 : 4, fill: row.observed_or_estimated === 'E' ? '#ffffff' : color, stroke: color, 'stroke-width': 1.3, 'data-quality': row.quality_flag });
    point.append(svgNode('title', {}, `${dateLabel(row.observed_at)} · ${number(row.conductivity_ms_per_m)} mS/m · ${QUALITY_LABELS[row.quality_flag]} · ${row.observed_or_estimated === 'O' ? 'Quan trắc (O)' : 'Ước tính (E)'}`));
    svg.append(point);
  }
  container.append(svg);
}
