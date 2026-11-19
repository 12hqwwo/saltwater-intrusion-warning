from docx import Document
from docx.oxml.ns import qn
d=Document(r'D:\Study\TLCN\BaoCao_TLCN_hoan_thien.docx')
for i,p in enumerate(d.paragraphs[:105],1):
 s=p.text.strip().replace('\n',' / ')
 br=len(p._p.findall('.//'+qn('w:br')))
 imgs=len(p._p.findall('.//'+qn('w:drawing')))
 sect=(p._p.pPr is not None and p._p.pPr.sectPr is not None)
 pb=(p._p.pPr is not None and p._p.pPr.pageBreakBefore is not None)
 print(f'{i:03} {p.style.name:16} sect={sect} pb={pb} br={br} img={imgs} {s[:100]}')
