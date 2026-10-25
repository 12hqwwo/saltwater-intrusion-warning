export function formatWater(ec, unit = 'ec', salinity) {
  if (ec == null || !Number.isFinite(Number(ec))) return '—';
  const value = unit === 'salinity' ? (salinity == null ? Number(ec) * 0.0064 : Number(salinity)) : Number(ec);
  if (!Number.isFinite(value)) return '—';
  const formatted = value.toLocaleString('vi-VN', { maximumFractionDigits: unit === 'salinity' ? 3 : 2 });
  return unit === 'salinity' ? `${formatted} g/L (ước tính; ${Number(ec).toLocaleString('vi-VN', { maximumFractionDigits: 2 })} mS/m)` : `${formatted} mS/m`;
}

export function salinityColor(ec) {
  const salinity = Number(ec) * 0.0064;
  if (!Number.isFinite(salinity)) return '#64748b';
  const stops = [[0, [6, 182, 212]], [1, [16, 185, 129]], [4, [245, 158, 11]], [6, [239, 68, 68]], [8, [190, 18, 60]]];
  const index = stops.findIndex(([value]) => salinity <= value);
  if (index <= 0) return index < 0 ? '#be123c' : '#06b6d4';
  const [low, a] = stops[index - 1], [high, b] = stops[index];
  const t = (salinity - low) / (high - low);
  return `rgb(${a.map((value, i) => Math.round(value + (b[i] - value) * t)).join(',')})`;
}

export function advisoryColor(gate) {
  if (['#10b981', '#f59e0b', '#ef4444'].includes(gate.advisory_color)) return gate.advisory_color;
  return gate.advisory_color === 'green' || gate.simulated_gate_state === 'OPEN_INTAKE' ? '#10b981'
    : gate.advisory_color === 'amber' || gate.simulated_gate_state === 'CAUTION_TRANSITION' ? '#f59e0b' : '#ef4444';
}
