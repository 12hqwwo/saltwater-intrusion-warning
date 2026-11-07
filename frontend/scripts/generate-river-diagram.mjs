import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const source = new URL('../../data/biengioi/tien_river_corridor.geojson', import.meta.url);
const output = new URL('../public/river-diagram.svg', import.meta.url);
mkdirSync(fileURLToPath(new URL('../public/', import.meta.url)), { recursive: true });
const { features } = JSON.parse(readFileSync(source, 'utf8'));
const x = lon => 46 + (lon - 105.18) / (106.79 - 105.18) * 708;
const y = lat => 35 + (10.86 - lat) / (10.86 - 10.22) * 344;
const point = ([lon, lat]) => `${x(lon).toFixed(1)} ${y(lat).toFixed(1)}`;
const path = coordinates => coordinates.map((coordinate, index) => `${index ? 'L' : 'M'}${point(coordinate)}`).join(' ');
const main = features.find(feature => feature.properties?.type === 'MAIN_RIVER');
const branches = features.filter(feature => feature.properties?.gate_code);
const mainPoints = main.geometry.coordinates.filter((_, index) => index % 3 === 0);
mainPoints.push(main.geometry.coordinates.at(-1));
const branchesSvg = branches.map(feature => {
  const coordinates = feature.geometry.coordinates;
  const gate = coordinates[feature.properties.gate_path_index];
  return `<path class="branch" d="${path(coordinates)}"/><circle class="gate" cx="${x(gate[0]).toFixed(1)}" cy="${y(gate[1]).toFixed(1)}" r="4.5"/>`;
}).join('');
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 420" role="img" aria-labelledby="title description">
<title id="title">Sơ đồ hình học trục Sông Tiền và mười kênh có cống</title>
<desc id="description">Tuyến trục Sông Tiền và các nhánh được dựng từ dữ liệu không gian của dự án; chấm tròn là vị trí cống trên từng nhánh.</desc>
<style>:root{--paper:#e9f5f5;--grid:#c8e2e2;--river:#176b86;--branch:#51a3a0;--gate:#b96b37;--ink:#224d5c}.paper{fill:var(--paper)}.grid{stroke:var(--grid);stroke-width:1}.river{fill:none;stroke:var(--river);stroke-width:8;stroke-linecap:round;stroke-linejoin:round}.branch{fill:none;stroke:var(--branch);stroke-width:3;stroke-linecap:round;stroke-linejoin:round}.gate{fill:var(--gate);stroke:var(--paper);stroke-width:2}.label{fill:var(--ink);font:600 17px system-ui,sans-serif}</style>
<rect class="paper" width="800" height="420" rx="18"/>${[90,170,250,330].map(n => `<path class="grid" d="M28 ${n}H772"/>`).join('')}${[160,320,480,640].map(n => `<path class="grid" d="M${n} 24V396"/>`).join('')}
${branchesSvg}<path class="river" d="${path(mainPoints)}"/></svg>`;
writeFileSync(fileURLToPath(output), svg);
