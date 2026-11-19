from docx import Document
from pathlib import Path
from docx.oxml.ns import qn
d=Document(r'D:\Study\BAOCAOTLCN\BaoCao_TLCN.docx')
for n in ['Normal','Heading 1','Heading 2','Heading 3','Heading 4','Caption','KHONG CO CHUONG']:
 try:
  s=d.styles[n]
  print(n,'font',s.font.name,'size',s.font.size.pt if s.font.size else None,'bold',s.font.bold,'italic',s.font.italic,'align',s.paragraph_format.alignment,'spacing',s.paragraph_format.line_spacing,'numPr',s._element.pPr.numPr.xml if s._element.pPr is not None and s._element.pPr.numPr is not None else None)
 except Exception as e: print(n,'missing',e)
for i in [149,150,151,157,158,172,173,174,175,179,180,194,214,227]:
 p=d.paragraphs[i-1]
 print('P',i,p.style.name,repr(p.text),'numPr',p._p.pPr.numPr.xml if p._p.pPr is not None and p._p.pPr.numPr is not None else None)
print('inline shapes',len(d.inline_shapes))
