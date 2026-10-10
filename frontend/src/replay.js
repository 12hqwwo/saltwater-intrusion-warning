import 'ol/ol.css';
import { createStationMap } from './map.js';

const $ = id => document.getElementById(id);
let rows = [], meta = null, controller = null, serial = 0;
const fmt = n => Number.isFinite(n) ? n.toLocaleString('vi-VN', { maximumFractionDigits: 2 }) : '—';
const date = value => new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));
const map = createStationMap($('replayMap'), { onSelect: () => {}, onTileError: () => { $('tileNotice').hidden = false; } });
function text(tag, value) { const node = document.createElement(tag); node.textContent = value; return node; }
function svg(tag, attrs, content) { const node = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [k,v] of Object.entries(attrs)) node.setAttribute(k,String(v)); if (content !== undefined) node.textContent = content; return node; }
function draw(items) {
  const box = svg('svg', { viewBox: '0 0 1000 250', role: 'img', 'aria-label': 'Dự báo theo các thời điểm phát hành trong ngày; đơn vị g/L.' });
  const max = Math.max(1, ...items.flatMap(r => [r.upper, r.actual_for_evaluation ?? 0]));
  const x = i => 60 + i * 870 / Math.max(1, items.length - 1), y = n => 210 - n / max * 175;
  for (let k = 0; k <= 4; k++) { const value = max * k / 4; box.append(svg('line', {x1:55,x2:945,y1:y(value),y2:y(value),stroke:'#dce7e4'}), svg('text',{x:48,y:y(value)+4,'text-anchor':'end','font-size':12,fill:'#476468'},fmt(value))); }
  const band = items.map((r,i) => `${x(i)},${y(r.upper)}`).concat(items.map((r,i) => `${x(i)},${y(r.lower)}`).reverse()).join(' ');
  box.append(svg('polygon', {points:band, fill:'#d8efea'}));
  for (const [key,color] of [['predicted','#13766b'],['actual_for_evaluation','#b36a1a']]) {
    if (!items.every(r => Number.isFinite(r[key]))) continue;
    box.append(svg('polyline', {points:items.map((r,i)=>`${x(i)},${y(r[key])}`).join(' '), fill:'none',stroke:color,'stroke-width':2.5}));
    items.forEach((r,i)=>box.append(svg('circle',{cx:x(i),cy:y(r[key]),r:3,fill:color})));
  }
  items.forEach((r,i)=>{ if (i%2===0 || i===items.length-1) box.append(svg('text',{x:x(i),y:236,'text-anchor':'middle','font-size':12,fill:'#476468'},r.forecast_origin.slice(11,16))); });
  $('chart').replaceChildren(box);
}
function render() {
  if (!rows.length) return;
  const i = Math.min(Number($('position').value), rows.length-1), r = rows[i];
  $('origin').textContent = `Phát hành: ${date(r.forecast_origin)} → thời điểm đích: ${date(r.target_time)} (giờ Việt Nam)`;
  $('count').textContent = `${i+1} / ${rows.length} thời điểm có đủ đầu vào và số đo kiểm tra`;
  $('previous').disabled = i===0; $('next').disabled = i===rows.length-1;
  $('lastValue').textContent = `${fmt(r.salinity_at_issue)} g/L`;
  $('prediction').textContent = `${fmt(r.predicted)} g/L`;
  $('actual').textContent = r.actual_for_evaluation === undefined ? 'Chưa bật' : `${fmt(r.actual_for_evaluation)} g/L`;
  $('availability').textContent = `Giả định công bố số đo sau ${meta.observation_delay_hours ?? 0} giờ. Số đo gần nhất: ${date(r.last_available_observation_at ?? r.forecast_origin)}.`;
  $('interval').textContent = `Khoảng sai số thực nghiệm: ${fmt(r.lower)}–${fmt(r.upper)} g/L. Không phải xác suất an toàn mở cống.`;
  $('model').textContent = `Mô hình: ${r.model_id}. Ngày nhãn huấn luyện cuối: ${date(r.train_last_target)}.`;
  const report = meta.forecasts.find(f=>f.horizon_hours===r.horizon_hours && f.model_id===r.model_id);
  const s = report?.test_scores.find(s=>s.period==='2015-2016');
  $('scores').textContent = s ? `Tập kiểm tra 2015–2016: ${s.n} mẫu; MAE ${fmt(s.mae)} g/L; độ bao phủ khoảng sai số ${fmt(s.interval_coverage*100)}%.` : '';
  const day = rows.filter(v=>v.forecast_origin.slice(0,10)===r.forecast_origin.slice(0,10));
  draw(day); $('rows').replaceChildren();
  day.forEach(v=>{const tr=text('tr',''); [date(v.forecast_origin),date(v.target_time),fmt(v.predicted),fmt(v.actual_for_evaluation)].forEach(value=>tr.append(text('td',value))); $('rows').append(tr);});
}
async function json(url, signal) { const response = await fetch(url, {signal}); const data = await response.json(); if (!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'Không tải được kết quả hồi cứu.'); return data; }
async function load() {
  const id=++serial; controller?.abort(); controller=new AbortController();
  $('error').hidden=true; $('status').textContent='Đang tải kết quả…'; $('position').disabled=true;
  $('previous').disabled=true; $('next').disabled=true;
  // Clear stale forecasts while changing horizon; never label an old result with a new horizon.
  rows=[]; $('chart').replaceChildren(); $('rows').replaceChildren();
  for(const key of ['origin','count','lastValue','prediction','availability','interval','model','scores']) $(key).textContent='—';
  $('actual').textContent='—';
  try {
    const [m, data]=await Promise.all([json('/api/v1/replay',controller.signal),json(`/api/v1/replay/forecasts?horizon_hours=${$('horizon').value}&include_actual=${$('comparison').checked}`,controller.signal)]);
    if(id!==serial)return;
    if(data.has_more)throw new Error('Bộ kết quả vượt giới hạn trang; cần mở rộng phân trang trước khi hiển thị.');
    meta=m.metadata; rows=data.items;
    if(!rows.length)throw new Error('Chưa có kết quả cho chân trời đã chọn.');
    map.setStations({type:'FeatureCollection',features:[m.station_feature]}); map.select('GFZ_SONDOC');
    $('position').max=rows.length-1; $('position').value=0; $('position').disabled=false;
    $('status').textContent='Đã tải kết quả hồi cứu · chưa đủ dữ liệu để khuyến nghị vận hành cống.'; render();
  } catch(error) { if(error.name==='AbortError' || id!==serial)return; $('error').textContent=error.message; $('error').hidden=false; $('status').textContent='Chưa tải được kết quả.'; }
}
$('position').addEventListener('input',render);
$('previous').addEventListener('click',()=>{$('position').value=Number($('position').value)-1;render();});
$('next').addEventListener('click',()=>{$('position').value=Number($('position').value)+1;render();});
for(const key of ['horizon','comparison'])$(key).addEventListener('change',load);
$('reload').addEventListener('click',load); load();
