from PIL import Image, ImageOps, ImageDraw
from pathlib import Path
from pypdf import PdfReader
files=sorted(Path(r'D:\Study\TLCN\render_final').glob('page-*.png'))
files=files[:len(PdfReader(r'D:\Study\TLCN\report_preview.pdf').pages)]
thumb_w=280; thumb_h=400; cols=4
rows=(len(files)+cols-1)//cols
sheet=Image.new('RGB',(cols*thumb_w,rows*(thumb_h+28)),'white')
draw=ImageDraw.Draw(sheet)
for i,f in enumerate(files):
    im=Image.open(f).convert('RGB')
    im.thumbnail((thumb_w-12,thumb_h-12))
    x=(i%cols)*thumb_w+(thumb_w-im.width)//2
    y=(i//cols)*(thumb_h+28)+8
    sheet.paste(im,(x,y))
    draw.text(((i%cols)*thumb_w+8,(i//cols)*(thumb_h+28)+thumb_h+5),f.stem,fill='black')
sheet.save(r'D:\Study\TLCN\render_final\contact.png')
print(len(files),sheet.size)
