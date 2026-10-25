/** Date-only x axis: UTC here is drawing arithmetic, never a fabricated sampling hour. */
function svgNode(tag, attrs = {}, text) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, String(value));
  if (text !== undefined) el.textContent = text;
  return el;
}
const fmt = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 });
export function drawSeries(container, series, { title, connected = false, referenceLines = [] } = {}) {
  container.replaceChildren();
  const points = series.flatMap(s => s.points.filter(p => Number.isFinite(p.value)));
  if (!points.length) { container.textContent = 'Không có số đo trong khoảng đã chọn.'; return; }
  const width = 900, height = 260, left = 58, right = 25, top = 22, bottom = 38;
  const times = points.map(p => Date.parse(p.date.slice(0, 10) + 'T00:00:00Z'));
  let tmin = Math.min(...times), tmax = Math.max(...times);
  if (tmin === tmax) { tmin -= 86400000; tmax += 86400000; }
  const lines = referenceLines.filter(line => Number.isFinite(line.value) && line.value >= 0);
  const max = Math.max(1, ...points.map(p => p.value), ...lines.map(line => line.value)) * 1.12;
  const x = d => left + (Date.parse(d.slice(0, 10) + 'T00:00:00Z') - tmin) / (tmax - tmin) * (width - left - right);
  const y = v => top + (height - top - bottom) * (1 - v / max);
  const svg = svgNode('svg', { viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': title });
  svg.append(svgNode('title', {}, title));
  for (let i = 0; i <= 4; i++) {
    const v = max * i / 4;
    svg.append(svgNode('line', { x1: left, x2: width - right, y1: y(v), y2: y(v), stroke: '#dce6e5', 'stroke-width': 1 }));
    svg.append(svgNode('text', { x: left - 9, y: y(v) + 4, 'text-anchor': 'end', fill: '#596d74', 'font-size': 12 }, fmt.format(v)));
  }
  svg.append(svgNode('text', { x: 5, y: 12, fill: '#596d74', 'font-size': 11 }, 'mS/m'));
  for (const line of lines) {
    const color = line.color || '#bc6430';
    svg.append(svgNode('line', { x1: left, x2: width - right, y1: y(line.value), y2: y(line.value), stroke: color, 'stroke-width': 1.5, 'stroke-dasharray': '7 4' }));
    svg.append(svgNode('text', { x: width - right, y: y(line.value) - 7, 'text-anchor': 'end', fill: color, 'font-size': 12, stroke: '#fff', 'stroke-width': 3, 'paint-order': 'stroke' }, line.label || fmt.format(line.value)));
  }
  for (let i = 0; i <= 4; i++) {
    const stamp = tmin + (tmax - tmin) * i / 4, d = new Date(stamp).toISOString().slice(0, 10);
    svg.append(svgNode('text', { x: left + (width - left - right) * i / 4, y: height - 8, 'text-anchor': i === 0 ? 'start' : i === 4 ? 'end' : 'middle', fill: '#596d74', 'font-size': 12 }, d));
  }
  for (const s of series) {
    const values = s.points.filter(p => Number.isFinite(p.value));
    if (connected) {
      let path = '', previous = null;
      for (const p of values) {
        const [year, month] = p.date.split('-').map(Number), current = year * 12 + month;
        path += `${previous !== null && current - previous === 1 ? 'L' : 'M'}${x(p.date)} ${y(p.value)} `;
        previous = current;
      }
      svg.append(svgNode('path', { d: path, fill: 'none', stroke: s.color, 'stroke-width': 2, 'stroke-dasharray': s.dashed ? '5 4' : 'none' }));
    }
    for (const p of values) {
      const circle = svgNode('circle', { cx: x(p.date), cy: y(p.value), r: values.length > 80 ? 2.2 : 4, fill: s.color, tabindex: 0 });
      circle.append(svgNode('title', {}, `${s.label} · ${p.date.slice(0, 10)} · ${fmt.format(p.value)} mS/m`));
      svg.append(circle);
    }
  }
  container.append(svg);
}
