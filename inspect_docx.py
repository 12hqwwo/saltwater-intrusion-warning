from docx import Document
from docx.oxml.ns import qn
from pathlib import Path

sources = {
    'mau5': Path(r'C:\Users\QUYNH\Downloads\Mau-5-TrinhBay-KLTN.docx'),
    'mau3': Path(r'C:\Users\QUYNH\Downloads\Mau-3-HuongDanLam-LuanVan.docx'),
    'mau2': Path(r'C:\Users\QUYNH\Downloads\Mau-2-Rubric-KLTN-Edit.docx'),
    'draft': Path(r'D:\Study\BAOCAOTLCN\BaoCao_TLCN.docx'),
}

def celltext(cell):
    return ' / '.join(p.text.strip().replace('\n', ' ') for p in cell.paragraphs if p.text.strip())

for name, path in sources.items():
    doc = Document(path)
    lines=[]
    lines.append(f'SOURCE {path}')
    lines.append(f'PARAGRAPHS {len(doc.paragraphs)} TABLES {len(doc.tables)} SECTIONS {len(doc.sections)}')
    for i, section in enumerate(doc.sections):
        lines.append(f'SECTION {i} width={section.page_width.cm:.2f}cm height={section.page_height.cm:.2f}cm margins={section.left_margin.cm:.2f},{section.right_margin.cm:.2f},{section.top_margin.cm:.2f},{section.bottom_margin.cm:.2f}')
    body = doc.element.body
    pi=ti=0
    for child in body.iterchildren():
        if child.tag == qn('w:p'):
            p = doc.paragraphs[pi]; pi += 1
            t = p.text.strip().replace('\t',' [TAB] ').replace('\n',' [BR] ')
            if t:
                lines.append(f'P{pi:04} [{p.style.name}] {t}')
        elif child.tag == qn('w:tbl'):
            table = doc.tables[ti]; ti += 1
            lines.append(f'TABLE {ti} {len(table.rows)}x{len(table.columns)}')
            for j,row in enumerate(table.rows):
                lines.append(f'  R{j+1:02} ' + ' || '.join(celltext(c) for c in row.cells))
    out=Path(f'{name}_extract.txt')
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(name, out, len(lines))
