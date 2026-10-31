"""Build a local report/gallery from actual UAT screenshots and evidence."""
import csv
import html
import json
import math
import re
import shutil
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:8000'
(ROOT / 'sources').mkdir(exist_ok=True)
for source_name in ('spatial-simulation.md', 'multivariate-forecast.md', 'web-interface.md', 'dss-storage.md'):
    shutil.copyfile(ROOT.parents[1] / 'docs' / source_name, ROOT / 'sources' / source_name)


def get(route):
    with urllib.request.urlopen(BASE + route, timeout=15) as response:
        return json.load(response)


def csv_rows(name):
    with (ROOT / 'downloads' / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


prediction = json.loads((ROOT / 'downloads/du-bao-mytho-2026-11.json').read_text(encoding='utf-8-sig'))
prediction_csv = csv_rows('du-bao-mytho-2026-11.csv')
assert prediction['prediction_id'] == '4be2b3e4-7d88-4216-a713-60db1436039b'
assert prediction['station'] == 'MyTho' and prediction['target_month'] == '2026-11' and prediction['input_month'] == '2026-09'
assert math.isclose(prediction['predicted_ec_mS_m'], 17.33124465272705)
assert len(csv_rows('quan-trac-mytho-2023.csv')) == 12
assert len(csv_rows('lich-su-tanchau-toan-bo.csv')) == 464
assert all(row['prediction_id'] == '4be2b3e4-7d88-4216-a713-60db1436039b' for row in prediction_csv)
assert all(row['station'] == 'MyTho' and row['target_month'] == '2026-11' for row in prediction_csv)
assert all(math.isclose(float(row['predicted_ec_mS_m']), 17.33124465272705) for row in prediction_csv)
summary = get('/api/v1/workspace/summary')
assert summary['stations'] == 12 and summary['observations'] == 977
history = get('/api/v1/workspace/multivariate/history?limit=20&offset=0')
drafts = get('/api/v1/workspace/gate-drafts?gate_code=DT_PLIII_001&limit=1')
final = {
    'checked_at': datetime.now().astimezone().isoformat(),
    'selected_stations': summary['stations'],
    'selected_observations': summary['observations'],
    'export_rows': {'mytho_2023': 12, 'tanchau_all': 464},
    'prediction_csv_matches_expected': True,
    'forecast_history': history,
    'latest_test_gate_draft': drafts,
    'app_health': get('/api/v1/app-health'),
    'database_health': get('/api/v1/health'),
}
(ROOT / 'final-verification.json').write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding='utf-8')

CAPTIONS = {
    '01': 'Tổng quan: nguồn dữ liệu và độ phủ',
    '02': 'Bản đồ: đỉnh mặn lịch sử 03/2016',
    '03': 'Mùa lũ: cắt dọc sông và độ mặn quy đổi',
    '04': 'Bảo Định: kịch bản lấy nước minh họa',
    '05': 'Từ bản đồ sang hồ sơ còn thiếu bằng chứng',
    '06': 'INTAKE: đáp ứng điều kiện giả định',
    '07': 'INTAKE: EC ngoài 150 mS/m bị chặn',
    '08': 'DRAIN và lưu/khôi phục nháp PostgreSQL',
    '09': 'Dự báo Mỹ Tho và bảng đánh giá mô hình',
    '10': 'Lịch sử dự báo lưu PostgreSQL',
    '11': 'Dự báo trên bản đồ, tách tháng timeline nền',
    '12': 'Lọc 12 mẫu Mỹ Tho năm 2023',
    '12b': 'Chi tiết quan trắc: ảnh vùng hiển thị',
    '13': 'Lịch sử PostgreSQL và phân trang',
    '13b': 'Lịch sử PostgreSQL: ảnh vùng hiển thị',
    '14': 'Ước tính hồi cứu theo khí tượng',
    '15': 'Chất lượng dữ liệu và truy nguồn',
    '16': 'Dự báo thủ công và so sánh 3 lượt',
    '17': 'Thiếu khí tượng: khóa chạy dự báo',
    '18': 'Mùa khô 04/2024 trên nền ảnh vệ tinh',
    '19': 'Thông báo cặp ngưỡng không hợp lệ',
    '20': 'Bản đồ sau kiểm thử: 14/2/11 cống',
    '21': 'Nhập JSON: policy thiếu bị từ chối',
}
shots = sorted((ROOT / 'screenshots').glob('*.png'))
font_path = Path('C:/Windows/Fonts/arial.ttf')
font = ImageFont.truetype(str(font_path), 24)
small = ImageFont.truetype(str(font_path), 18)
contact = Image.new('RGB', (1320, 1710), '#eef5f4')
draw = ImageDraw.Draw(contact)
draw.rectangle((0, 0, 1320, 112), fill='#143f43')
draw.text((28, 20), 'WEBGIS · KIỂM THỬ THỰC TẾ 26/10/2026', font=font, fill='white')
draw.text((28, 65), 'Ảnh chụp thật, thu nhỏ/cắt vùng để tổng hợp · mở ảnh gốc trong thư viện', font=small, fill='#cbe9e6')
tiles = [
    ('01-tong-quan.png', (0, 0, 827, 1030), 'Tổng quan · 12 trạm / 977 số đo'),
    ('20-ban-do-cuoi-kiem-thu.png', (0, 0, 827, 1418), 'Bản đồ · mô phỏng tháng 04/2024'),
    ('09-du-bao-mytho-va-danh-gia.png', (0, 550, 827, 1650), 'Mỹ Tho · dự báo EC 17,331 mS/m'),
    ('07-cong-ec-150-bi-chan.png', (0, 1540, 827, 2350), 'Hồ sơ cống · EC đạt ngưỡng chặn'),
    ('13-lich-su-postgresql-phan-trang.png', (0, 2740, 827, 3992), 'Lịch sử quan trắc PostgreSQL'),
    ('15-chat-luong-va-truy-nguon.png', (0, 1430, 827, 2530), 'Chất lượng dữ liệu và dấu kiểm tra'),
]
for i, (name, box, title) in enumerate(tiles):
    x = 20 + (i % 3) * 440
    y = 134 + (i // 3) * 780
    draw.rounded_rectangle((x, y, x+420, y+750), radius=12, fill='white', outline='#d2e4e0', width=2)
    draw.text((x+12, y+12), title, font=small, fill='#143f43')
    source = Image.open(ROOT / 'screenshots' / name).convert('RGB').crop(box)
    source.thumbnail((396, 690), Image.Resampling.LANCZOS)
    contact.paste(source, (x+(420-source.width)//2, y+52))
contact.save(ROOT / 'contact-sheet.jpg', quality=92)


def inline(value):
    value = html.escape(value)
    value = re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
    value = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
    value = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', value)
    return value


def render_md(source):
    lines = source.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            blocks.append(f'<h{level}>{inline(line[level:].strip())}</h{level}>')
            i += 1
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [c.strip() for c in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+', c) for c in cells):
                    rows.append(cells)
                i += 1
            blocks.append('<div class="table-wrap"><table><thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in rows[0]) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in row) + '</tr>' for row in rows[1:]) + '</tbody></table></div>')
        elif line.startswith('- '):
            items = []
            while i < len(lines) and lines[i].startswith('- '):
                items.append(f'<li>{inline(lines[i][2:])}</li>')
                i += 1
            blocks.append('<ul>' + ''.join(items) + '</ul>')
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '|', '- ')):
                para.append(lines[i])
                i += 1
            blocks.append('<p>' + inline(' '.join(para)) + '</p>')
    return '\n'.join(blocks)


cards = []
for shot in shots:
    prefix = shot.stem.split('-')[0]
    title = CAPTIONS[prefix]
    cards.append(f'<a class="shot" href="screenshots/{shot.name}"><img src="screenshots/{shot.name}" loading="lazy" alt="{html.escape(title)}"><span>{prefix} · {html.escape(title)}</span><small>Mở ảnh gốc đầy đủ</small></a>')
body = render_md((ROOT / 'report.md').read_text(encoding='utf-8'))
template = '''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Kiểm thử WebGIS · 26/10/2026</title><style>
*{box-sizing:border-box}body{margin:0;color:#193b40;background:#eff5f4;font:16px/1.65 'Segoe UI',Arial,sans-serif}header{background:#143f43;color:white;padding:38px max(24px,calc((100vw - 1240px)/2))}header p{max-width:900px;margin-bottom:22px;color:#d0e9e4}header h1{font-size:clamp(28px,4vw,45px);line-height:1.15;margin:8px 0 18px}nav{display:flex;gap:12px;flex-wrap:wrap}nav a{padding:9px 16px;border:1px solid #6c9d9a;border-radius:8px;color:white;text-decoration:none}.tag{font-size:13px;letter-spacing:.12em;color:#b8dfd9}.wrap{max-width:1290px;margin:auto;padding:28px 24px 60px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.stat{padding:22px;background:white;border:1px solid #d7e6e3;border-radius:12px}.stat strong{display:block;font-size:32px;color:#087b76}.stat span{font-size:14px}.note{padding:16px 20px;background:#fff8e8;border-left:4px solid #b18a2a;margin:24px 0;border-radius:6px}h2{font-size:27px;margin:40px 0 16px}a{color:#007d78}code{background:#e8f0ef;padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}p,li{max-width:1120px}li{margin:9px 0}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.shot{display:flex;flex-direction:column;background:white;overflow:hidden;border:1px solid #d6e4e1;border-radius:12px;text-decoration:none;transition:transform .15s}.shot:hover{transform:translateY(-3px)}.shot img{width:100%;height:360px;object-fit:cover;object-position:top;border-bottom:1px solid #e2eeeb}.shot span{font-weight:600;color:#193b40;padding:16px 18px 3px}.shot small{padding:0 18px 16px;color:#637b7b}article{background:white;border:1px solid #d6e4e1;border-radius:14px;padding:30px;margin-top:32px}article h1{font-size:30px}.table-wrap{overflow:auto;margin:20px 0}table{border-collapse:collapse;width:100%;min-width:650px;font-size:14px}th{background:#eaf4f1;text-align:left}td,th{padding:14px 12px;border:1px solid #dbe8e4;vertical-align:top}tr:nth-child(even) td{background:#fafcfb}footer{font-size:13px;color:#637b7b;margin-top:30px}@media(max-width:850px){.grid{grid-template-columns:repeat(2,1fr)}.stats{grid-template-columns:repeat(2,1fr)}article{padding:18px}}@media(max-width:540px){.grid{grid-template-columns:1fr}.shot img{height:400px}.wrap{padding:20px 14px}header{padding:28px 20px}}@media print{header nav,.grid{display:none}body{background:white}article{border:0;padding:0}.table-wrap{overflow:visible}table{min-width:0}}
</style></head><body><header><div class="tag">LOCAL POSTGRESQL · KIỂM THỬ THỰC TẾ</div><h1>WebGIS Đồng Tháp – Tiền Giang</h1><p>Đã chạy 5 mục chính, kiểm tra API/model/DB thật và chụp các màn hình đang phục vụ. Ngày 26/10/2026 · Ảnh gốc giữ nguyên trong thư mục screenshots.</p><nav><a href="http://127.0.0.1:8000/workspace.html">Mở web đang chạy</a><a href="#gallery">Xem ảnh</a><a href="#report">Đọc báo cáo</a><a href="report.md">Bản Markdown</a><a href="contact-sheet.jpg">Ảnh tổng hợp</a></nav></header><main class="wrap"><div class="stats"><div class="stat"><strong>112 / 112</strong><span>kiểm tra tự động đạt</span></div><div class="stat"><strong>23</strong><span>mục UI ghi nhận đạt</span></div><div class="stat"><strong>5</strong><span>mục chính đã thao tác</span></div><div class="stat"><strong>__COUNT__</strong><span>ảnh chụp màn hình gốc</span></div></div><div class="note">Giá trị và điều kiện cống trong bài thử là kịch bản giả định. Dữ liệu lịch sử, ước tính hồi cứu và dự báo mới có phạm vi khác nhau; không dùng kết quả thử làm lệnh vận hành.</div><h2 id="gallery">Thư viện ảnh màn hình thật</h2><p>Bấm một ảnh để xem toàn bộ. Hình thu nhỏ bên dưới chỉ hiển thị phần đầu của ảnh dài.</p><div class="grid">__CARDS__</div><article id="report">__BODY__</article><footer>Được tạo từ các bằng chứng trong thư mục báo cáo. Không thay đổi mã ứng dụng.</footer></main></body></html>'''
(ROOT / 'index.html').write_text(template.replace('__COUNT__', str(len(shots))).replace('__CARDS__', '\n'.join(cards)).replace('__BODY__', body), encoding='utf-8')

api = json.loads((ROOT / 'live-api-results.json').read_text(encoding='utf-8'))
ui = json.loads((ROOT / 'ui-results.json').read_text(encoding='utf-8'))
assert len(api['checks']) == 37 and all(x['status'] == 'PASS' for x in api['checks'])
assert len(ui) == 23 and all(x['status'] == 'PASS' for x in ui)
assert history['total'] == 2 and any(x['prediction']['prediction_id'] == prediction['prediction_id'] for x in history['items'])
assert drafts['items'][0]['draft_id'] == 7
for target in re.findall(r'href="([^"#]+)"', (ROOT / 'index.html').read_text(encoding='utf-8')):
    if not target.startswith(('http:', 'https:')):
        assert (ROOT / target).exists(), target

archive = ROOT.parent / 'webgis-uat-2026-10-26.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for file in sorted(ROOT.rglob('*')):
        if file.is_file() and '__pycache__' not in file.parts:
            z.write(file, Path(ROOT.name) / file.relative_to(ROOT))
print(json.dumps({'screenshots': len(shots), 'ui_checks': len(ui), 'automated_checks': 112, 'selected_observations_after': summary['observations'], 'report': str(ROOT / 'index.html'), 'zip': str(archive)}, ensure_ascii=False))
