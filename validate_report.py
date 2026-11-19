from docx import Document
from pypdf import PdfReader
from pathlib import Path
docx=Path(r'D:\Study\TLCN\BaoCao_TLCN_hoan_thien.docx')
pdf=Path(r'D:\Study\TLCN\report_preview.pdf')
d=Document(docx); p=PdfReader(pdf)
texts=[x.extract_text() for x in p.pages]
def last_page(term):
    return max(i+1 for i,t in enumerate(texts) if term in t)
start=last_page('PHẦN MỞ ĐẦU')
end=last_page('PHẦN KẾT LUẬN')
para='\n'.join(x.text for x in d.paragraphs)
blank=[i+1 for i,t in enumerate(texts) if len(t.strip())<45]
print('DOCX_BYTES',docx.stat().st_size)
print('PDF_PAGES',len(texts))
print('CONTENT_PAGES',end-start+1,'START',start,'END',end)
print('BLANK_PAGES',blank)
print('EM_DASH_COUNT',para.count('—'))
print('IMAGE_PLACEHOLDERS',para.count('[CHÈN ẢNH TẠI ĐÂY:'))
print('CAPTION_PLACEHOLDERS',para.count('[TÊN HÌNH:'))
print('TABLE_CAPTIONS',sum(1 for x in d.paragraphs if x.text.startswith('Bảng 5.')))
print('LAST_PAGE',last_page('TÀI LIỆU THAM KHẢO'))
for i,s in enumerate(d.sections):
    print('MARGINS',i,*(round(v.cm,2) for v in (s.left_margin,s.right_margin,s.top_margin,s.bottom_margin)))
