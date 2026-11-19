from pathlib import Path
import re
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.shared import Pt, Cm, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

SOURCE = Path(r'D:\Study\BAOCAOTLCN\BaoCao_TLCN.docx')
CONTENT = Path(r'D:\Study\TLCN\report_content.md')
OUTPUT = Path(r'D:\Study\TLCN\BaoCao_TLCN_hoan_thien.docx')

doc = Document(SOURCE)

# Thu gọn các khoảng trắng của hai trang bìa và phiếu GVHD trong bản thảo.
original_paragraphs=list(doc.paragraphs)
for number in [19,20,21,39,40,42,43,55,58,61,63,66]:
    p=original_paragraphs[number-1]
    p._p.getparent().remove(p._p)

def set_run(run, size=13, bold=None, italic=None):
    run.font.name = 'Times New Roman'
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0,0,0)
    if bold is not None: run.bold = bold
    if italic is not None: run.italic = italic

def set_style(name, size, bold=False, italic=False, align=None, spacing=1.5, before=0, after=6):
    s = doc.styles[name]
    s.font.name = 'Times New Roman'
    s.font.size = Pt(size)
    s.font.bold = bold
    s.font.italic = italic
    s.font.color.rgb = RGBColor(0,0,0)
    s.paragraph_format.line_spacing = spacing
    s.paragraph_format.space_before = Pt(before)
    s.paragraph_format.space_after = Pt(after)
    s.paragraph_format.left_indent = Cm(0)
    s.paragraph_format.right_indent = Cm(0)
    s.paragraph_format.first_line_indent = Cm(0)
    if align is not None: s.paragraph_format.alignment = align
    if s._element.pPr is not None and s._element.pPr.numPr is not None:
        s._element.pPr.remove(s._element.pPr.numPr)

set_style('Normal',13,align=WD_ALIGN_PARAGRAPH.JUSTIFY,after=4)
set_style('Heading 1',14,True,align=WD_ALIGN_PARAGRAPH.CENTER,before=14,after=12)
set_style('Heading 2',14,True,align=WD_ALIGN_PARAGRAPH.CENTER,before=12,after=10)
set_style('Heading 3',13,True,align=WD_ALIGN_PARAGRAPH.LEFT,before=10,after=6)
set_style('Heading 4',13,True,align=WD_ALIGN_PARAGRAPH.LEFT,before=8,after=5)
set_style('Caption',11,True,align=WD_ALIGN_PARAGRAPH.CENTER,before=3,after=8)
set_style('KHONG CO CHUONG',13,True,align=WD_ALIGN_PARAGRAPH.LEFT,before=10,after=6)

for sec in doc.sections:
    sec.page_width=Cm(21); sec.page_height=Cm(29.7)
    sec.left_margin=Cm(3); sec.right_margin=Cm(2)
    sec.top_margin=Cm(2); sec.bottom_margin=Cm(2)
    sec.footer_distance=Cm(1.2)
    sec.header.is_linked_to_previous=False
    for hp in sec.header.paragraphs:
        hp.clear()

def clear_num(p):
    if p._p.pPr is not None and p._p.pPr.numPr is not None:
        p._p.pPr.remove(p._p.pPr.numPr)

def insert_after(p, text, style='Normal'):
    q=doc.add_paragraph(style=style)
    p._p.addnext(q._p)
    q.text=text
    return q

def field(p, instruction):
    run=p.add_run()
    begin=OxmlElement('w:fldChar'); begin.set(qn('w:fldCharType'),'begin')
    instr=OxmlElement('w:instrText'); instr.set(qn('xml:space'),'preserve'); instr.text=' '+instruction+' '
    separate=OxmlElement('w:fldChar'); separate.set(qn('w:fldCharType'),'separate')
    value=OxmlElement('w:t'); value.text='1'
    end=OxmlElement('w:fldChar'); end.set(qn('w:fldCharType'),'end')
    for el in (begin,instr,separate,value,end): run._r.append(el)
    set_run(run,11)

def bookmark(p, name, n):
    start=OxmlElement('w:bookmarkStart'); start.set(qn('w:id'),str(n)); start.set(qn('w:name'),name)
    end=OxmlElement('w:bookmarkEnd'); end.set(qn('w:id'),str(n))
    p._p.insert(0,start); p._p.append(end)

def add_page_ref(p, name):
    p.add_run('\t')
    field(p, f'PAGEREF {name} \\h')

def format_body(p):
    p.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing=1.5
    p.paragraph_format.space_after=Pt(4)
    for r in p.runs: set_run(r,13)

# Sửa các nhãn trong phần mở đầu để đúng mạch nội dung đã viết.
for p in doc.paragraphs:
    t=p.text.strip()
    if t=='TP. Hồ Chí Minh, tháng 09 năm 2026': p.text='TP. Hồ Chí Minh, tháng 11 năm 2026'
    if t=='3. Đối tượng nghiên cứu': p.text='3. Mục tiêu cụ thể'
    elif t=='4. Phạm vi nghiên cứu': p.text='4. Đối tượng và phạm vi nghiên cứu'
    elif t.startswith('Từ các lý do trên, đề tài “Xây dựng nền tảng WebGIS dự báo'):
        p.text=t.replace('Xây dựng nền tảng WebGIS dự báo xâm nhập mặn và hỗ trợ điều phối vận hành cống thủy lợi tại Đồng Tháp','Xây dựng nền tảng WebGIS cảnh báo xâm nhập mặn và hỗ trợ vận hành cống thủy lợi tại Đồng Tháp')
    elif t.startswith('Hình 1: Cơ chế'):
        p.text=t.replace('Hình 1:', 'Hình 1.1.')

front = {
  'LỜI CẢM ƠN': [
    'Nhóm thực hiện xin cảm ơn ThS. Trần Trọng Bình đã hướng dẫn việc xác định phạm vi nghiên cứu, kiểm tra cách diễn giải dữ liệu và góp ý cho quá trình xây dựng nguyên mẫu. Những trao đổi với giảng viên giúp nhóm phân biệt rõ kết quả dự báo tại trạm với điều kiện vận hành tại công trình.',
    'Nhóm cảm ơn Khoa Công nghệ Thông tin và Bộ môn Hệ thống Thông tin đã cung cấp điều kiện học tập và cơ hội thực hiện tiểu luận chuyên ngành. Các nguồn dữ liệu công khai của MRC và các đơn vị cung cấp dữ liệu khí tượng, bản đồ được sử dụng theo phạm vi nêu trong báo cáo. Mọi sai sót còn lại trong cách xử lý và trình bày thuộc trách nhiệm của nhóm thực hiện.'
  ],
  'TÓM TẮT': [
    'Tiểu luận xây dựng nguyên mẫu WebGIS để tra cứu độ dẫn điện của nước (EC) theo trạm và thời gian, nghiên cứu dự báo giá trị mẫu EC theo tháng trên sông Tiền, đồng thời hỗ trợ rà soát điều kiện lấy nước tại cống. Dữ liệu EC MRC dùng cho nghiên cứu gồm 1.378 mẫu tại ba trạm Tân Châu, Mỹ Thuận và Mỹ Tho, kết thúc ở tháng 12/2023. Hệ thống tách quan trắc, dự báo, lớp nội suy và phiếu đo hiện trường để người dùng không hiểu các giá trị dẫn xuất là số đo thực.',
    'Dữ liệu được kiểm tra nguồn, đơn vị, thời gian và chất lượng trước khi lưu vào snapshot hoặc PostgreSQL/PostGIS. Các mô hình dự báo được huấn luyện ngoài luồng web; API FastAPI đọc artifact có phiên bản và cung cấp kết quả cho giao diện OpenLayers. Thử nghiệm Mỹ Tho cho thấy Random Forest bổ sung biến thủy văn đạt MAE 12,19 mS/m trên 24 tháng 2022-2023, trong khi baseline giữ EC cuối có MAE 10,76 mS/m. Mô hình Mỹ Thuận đạt MAE 3,917 mS/m trên cùng kỳ, thấp hơn Persistence 4,806 mS/m nhưng RMSE không thấp hơn trung bình theo tháng lịch. Các kết quả này là hồi cứu trên thời kỳ đã được xem trong quá trình phát triển.',
    'Phần cống kiểm tra EC và mực nước hai phía, thời điểm mẫu, hệ cao độ và trạng thái cơ khí theo RuleProfile kỹ thuật. Kết quả chỉ là đề nghị xem xét hoặc yêu cầu bổ sung dữ liệu, không là lệnh vận hành. Chưa có nhãn EC MRC sau 2023 và chưa có bộ đo tại cống đủ điều kiện kiểm định khả năng hỗ trợ quyết định thực tế. Từ khóa: WebGIS; độ dẫn điện; dự báo chuỗi thời gian; sông Tiền; cống thủy lợi.'
  ]
}
for heading, paragraphs in front.items():
    p=next(p for p in doc.paragraphs if p.text.strip()==heading)
    current=p
    for t in paragraphs:
        current=insert_after(current,t)
        format_body(current)

# Trang đề cương theo cấu trúc Mẫu 5. Phần ký xác nhận để trống vì tệp nguồn
# không chứa chữ ký của giảng viên hướng dẫn.
thanks=next(p for p in doc.paragraphs if p.text.startswith('Nhóm cảm ơn Khoa Công nghệ Thông tin'))
outline=[
    ('ĐỀ CƯƠNG CHI TIẾT CỦA TIỂU LUẬN','Heading 1'),
    ('Tên đề tài: Xây dựng nền tảng WebGIS cảnh báo xâm nhập mặn và hỗ trợ vận hành cống thủy lợi tại Đồng Tháp.','Normal'),
    ('Sinh viên thực hiện: Hà Như Quỳnh (23110298), Võ Hữu Tín (23110343). Giảng viên hướng dẫn: ThS. Trần Trọng Bình.','Normal'),
    ('Mục tiêu: Xây dựng nguyên mẫu WebGIS tra cứu EC, nghiên cứu dự báo mẫu EC theo tháng tại các trạm phù hợp và hỗ trợ rà soát điều kiện lấy nước tại cống bằng dữ liệu hiện trường cùng bộ quy tắc có thể truy xuất.','Normal'),
    ('Nội dung thực hiện: (1) thu thập và chuẩn hóa dữ liệu EC, khí tượng, thủy văn và không gian; (2) thiết kế cơ sở dữ liệu và quy trình xử lý; (3) huấn luyện, đánh giá mô hình dự báo theo thời gian; (4) xây dựng API và giao diện WebGIS; (5) kiểm thử nội suy và bộ kiểm tra điều kiện cống.','Normal'),
    ('Sản phẩm: mã nguồn, dữ liệu và manifest nghiên cứu, artifact mô hình, nguyên mẫu WebGIS, bộ kiểm thử và báo cáo tiểu luận. Giới hạn: kết quả dự báo và kiểm tra cống phục vụ nghiên cứu, không thay thế quyết định vận hành của đơn vị quản lý.','Normal'),
    ('Xác nhận của giảng viên hướng dẫn: ........................................................','Normal'),
]
cur=thanks
for t,sty in outline:
    cur=insert_after(cur,t,sty)
    if sty=='Heading 1': cur.paragraph_format.page_break_before=True
    else: format_body(cur)

# Mẫu 5 yêu cầu phiếu GVPB; bổ sung trang mẫu nhưng không giả chữ ký/nhận xét.
gvhd_end=next(p for p in doc.paragraphs if p.text.strip()=='LỜI CẢM ƠN')
previous=gvhd_end._p.getprevious()
if previous is not None:
    p=doc.add_paragraph('PHIẾU NHẬN XÉT CỦA GIẢNG VIÊN PHẢN BIỆN',style='Heading 1')
    previous.addnext(p._p)
    p.paragraph_format.page_break_before=True
    cur=p
    for t in [
        'Sinh viên: Hà Như Quỳnh (23110298), Võ Hữu Tín (23110343).',
        'Tên đề tài: Xây dựng nền tảng WebGIS cảnh báo xâm nhập mặn và hỗ trợ vận hành cống thủy lợi tại Đồng Tháp.',
        'Giảng viên phản biện: ........................................................................',
        'Nhận xét về nội dung và khối lượng thực hiện: ........................................',
        'Ưu điểm: ...............................................................................................',
        'Khuyết điểm: .........................................................................................',
        'Đề nghị cho bảo vệ: ....................  Điểm: .............................................',
        'TP. Hồ Chí Minh, ngày ..... tháng ..... năm .....',
        'Giảng viên phản biện (ký và ghi rõ họ tên): ............................................',
    ]:
        cur=insert_after(cur,t)
        format_body(cur)
gvhd_end.style='Heading 1'
gvhd_end.paragraph_format.page_break_before=True

# Bảng phân công trong bản thảo không có dữ liệu xác nhận và không thuộc
# cấu trúc bắt buộc ở Mẫu 5, nên bỏ trang trống này.
body=doc.element.body
children=list(body.iterchildren())
start_blank=end_blank=None
for idx,el in enumerate(children):
    if el.tag==qn('w:p'):
        txt=''.join(n.text or '' for n in el.iter(qn('w:t'))).strip()
        if txt=='BẢNG PHÂN CÔNG NHIỆM VỤ VÀ TIẾN ĐỘ THỰC HIỆN': start_blank=idx
        if txt=='MỤC LỤC': end_blank=idx; break
if start_blank is not None and end_blank is not None:
    for el in children[start_blank:end_blank]: body.remove(el)
    toc_head=next(p for p in doc.paragraphs if p.text.strip()=='MỤC LỤC')
    toc_head.paragraph_format.page_break_before=True

# Bỏ các đề mục trống của bản thảo từ mục 1.4 để thay bằng nội dung hoàn chỉnh.
body=doc.element.body
start=None
for i,el in enumerate(body.iterchildren()):
    if el.tag==qn('w:p'):
        txt=''.join(n.text or '' for n in el.iter(qn('w:t')))
        if txt.strip()=='Các hệ thống/nghiên cứu liên quan':
            start=i; break
assert start is not None
elements=list(body.iterchildren())
for el in elements[start:]:
    if el.tag != qn('w:sectPr'): body.remove(el)

# Định dạng các đoạn nội dung đã có trong phần mở đầu và chương 1.
seen_body=False
for p in doc.paragraphs:
    if p.text.strip()=='PHẦN MỞ ĐẦU': seen_body=True
    if seen_body:
        clear_num(p)
        if p.style.name=='Normal': format_body(p)
        elif p.style.name=='Heading 3':
            if p.text.strip()=='Tổng quan về xâm nhập mặn': p.text='1.1. TỔNG QUAN VỀ XÂM NHẬP MẶN'
            elif p.text.strip()=='Đặc điểm khu vực nghiên cứu': p.text='1.2. ĐẶC ĐIỂM KHU VỰC NGHIÊN CỨU'
            elif p.text.strip()=='Bài toán giám sát và hỗ trợ vận hành cống': p.text='1.3. BÀI TOÁN GIÁM SÁT VÀ HỖ TRỢ VẬN HÀNH CỐNG'
        elif p.style.name=='Heading 4':
            if p.text.strip()=='Khái quát tỉnh Đồng Tháp mới': p.text='1.2.1. Khái quát tỉnh Đồng Tháp mới'
            elif p.text.strip()=='Khu vực phía Đông và hệ thống thủy lợi Gò Công': p.text='1.2.2. Khu vực phía Đông và hệ thống thủy lợi Gò Công'
        elif p.style.name=='Heading 2' and p.text.strip()=='TỔNG QUAN ĐỀ TÀI': p.text='CHƯƠNG 1: TỔNG QUAN ĐỀ TÀI'

figures=[]; tables=[]; bookmark_id=1
table_source_notes={
    'Bảng 5.1.':'Nguồn: Nhóm thực hiện kiểm đếm từ các chuỗi EC MRC và RIA2 đã lưu trong bộ dữ liệu nghiên cứu.',
    'Bảng 5.2.':'Nguồn: Hồ sơ thí nghiệm mô hình Mỹ Tho với khí tượng và thủy văn, ngày 08/11/2026.',
    'Bảng 5.3.':'Nguồn: Hồ sơ kiểm chứng mô hình Mỹ Thuận, ngày 04/11/2026.',
    'Bảng 5.4.':'Nguồn: Hồ sơ kiểm chứng nội suy ba trạm tại Mỹ Thuận, ngày 04/11/2026.',
    'Bảng 5.5.':'Nguồn: Hồ sơ kiểm tra biến triều FES cho Mỹ Tho, ngày 08/11/2026.',
    'Bảng 5.6.':'Nguồn: Nhóm thực hiện đối chiếu mục tiêu với sản phẩm và bằng chứng thực nghiệm.'
}
current_table_caption=''
old_fig=next((p for p in doc.paragraphs if p.text.startswith('Hình 1.1.')),None)
if old_fig:
    bookmark(old_fig,'fig_1_1',bookmark_id); bookmark_id+=1
    figures.append(('Hình 1.1. Cơ chế khái quát của quá trình xâm nhập mặn từ cửa sông vào nội đồng','fig_1_1'))

chapter=1; section=3; subsection=0
lines=CONTENT.read_text(encoding='utf-8').splitlines()
i=0
while i<len(lines):
    s=lines[i].strip(); i+=1
    if not s: continue
    if s.startswith('# '):
        title=s[2:]
        p=doc.add_paragraph(title,style='Heading 1')
        p.paragraph_format.page_break_before=True
        continue
    if s.startswith('## '):
        chapter+=1; section=0; subsection=0
        p=doc.add_paragraph(f'CHƯƠNG {chapter}: {s[3:].upper()}',style='Heading 2')
        p.paragraph_format.page_break_before=True
        continue
    if s.startswith('### '):
        section+=1; subsection=0
        p=doc.add_paragraph(f'{chapter}.{section}. {s[4:].upper()}',style='Heading 3')
        continue
    if s.startswith('#### '):
        subsection+=1
        p=doc.add_paragraph(f'{chapter}.{section}.{subsection}. {s[5:]}',style='Heading 4')
        continue
    if s.startswith('[CHÈN ẢNH TẠI ĐÂY:'):
        p=doc.add_paragraph(s,style='Normal')
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next=True
        for r in p.runs: set_run(r,11,italic=True)
        continue
    if s.startswith('[TÊN HÌNH:'):
        m=re.match(r'\[TÊN HÌNH: (Hình (\d+)\.(\d+)\..+)\]',s)
        assert m,s
        caption=m.group(1)
        p=doc.add_paragraph(s,style='Caption')
        name=f'fig_{m.group(2)}_{m.group(3)}'
        bookmark(p,name,bookmark_id); bookmark_id+=1
        figures.append((caption,name))
        continue
    if s.startswith('Bảng ') and re.match(r'Bảng \d+\.\d+\.',s):
        current_table_caption=s
        p=doc.add_paragraph(s,style='Caption')
        p.paragraph_format.keep_with_next=True
        m=re.match(r'Bảng (\d+)\.(\d+)\.',s)
        name=f'tab_{m.group(1)}_{m.group(2)}'
        bookmark(p,name,bookmark_id); bookmark_id+=1
        tables.append((s,name))
        continue
    if s.startswith('|'):
        rows=[s]
        while i<len(lines) and lines[i].strip().startswith('|'):
            rows.append(lines[i].strip()); i+=1
        data=[[c.strip() for c in row.strip('|').split('|')] for row in rows]
        assert len({len(r) for r in data})==1,data
        table=doc.add_table(rows=0, cols=len(data[0]))
        table.style='Table Grid'; table.alignment=WD_TABLE_ALIGNMENT.CENTER
        for ri,row in enumerate(data):
            cells=table.add_row().cells
            for j,val in enumerate(row):
                cells[j].text=val
                cells[j].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                for p in cells[j].paragraphs:
                    p.paragraph_format.line_spacing=1.0
                    p.paragraph_format.space_after=Pt(2)
                    p.alignment=WD_ALIGN_PARAGRAPH.CENTER if j>0 else WD_ALIGN_PARAGRAPH.LEFT
                    for run in p.runs: set_run(run,12,bold=(ri==0))
            if ri==0:
                trPr=table.rows[-1]._tr.get_or_add_trPr()
                repeat=OxmlElement('w:tblHeader'); repeat.set(qn('w:val'),'true'); trPr.append(repeat)
        note_text=next((v for k,v in table_source_notes.items() if current_table_caption.startswith(k)),None)
        if note_text:
            note=doc.add_paragraph(note_text)
            note.alignment=WD_ALIGN_PARAGRAPH.CENTER
            note.paragraph_format.line_spacing=1.0
            note.paragraph_format.space_after=Pt(8)
            for run in note.runs: set_run(run,10,italic=True)
        continue
    if s.startswith('[') and re.match(r'\[\d+\] ',s):
        p=doc.add_paragraph(s,style='Normal')
        p.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing=1.0
        p.paragraph_format.space_after=Pt(4)
        for r in p.runs: set_run(r,11)
        continue
    p=doc.add_paragraph(s,style='Normal')
    format_body(p)

# Tạo danh mục hình, bảng và mục lục với trường tham chiếu trang.
for title, items in [('DANH MỤC BẢNG',tables),('DANH MỤC HÌNH',figures)]:
    marker=next(p for p in doc.paragraphs if p.text.strip()==title)
    cur=marker
    for label,name in items:
        cur=insert_after(cur,label)
        cur.paragraph_format.tab_stops.add_tab_stop(Cm(15.5))
        cur.paragraph_format.line_spacing=1.0
        for r in cur.runs: set_run(r,11)
        add_page_ref(cur,name)
toc_marker=next(p for p in doc.paragraphs if p.text.strip()=='MỤC LỤC')
toc=insert_after(toc_marker,'')
field(toc,'TOC \\o "1-4" \\h \\z \\u')

# Số trang giữa chân trang trong mọi section.
for sec_i,sec in enumerate(doc.sections):
    sec.footer.is_linked_to_previous=False
    footer=sec.footer
    for p in list(footer.paragraphs):
        p.clear()
    p=footer.paragraphs[0]
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    if sec_i>=3: field(p,'PAGE')

doc.core_properties.title='Xây dựng nền tảng WebGIS cảnh báo xâm nhập mặn và hỗ trợ vận hành cống thủy lợi tại Đồng Tháp'
doc.core_properties.subject='Tiểu luận chuyên ngành Hệ thống Thông tin'
doc.save(OUTPUT)
print(OUTPUT)
print('figures',len(figures),'tables',len(tables),'paragraphs',len(doc.paragraphs))
