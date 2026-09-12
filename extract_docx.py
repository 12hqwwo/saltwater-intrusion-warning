import zipfile
import xml.etree.ElementTree as ET

def extract():
    docx_file = 'Đề Cương - TLCN.docx'
    txt_file = 'decuong.txt'
    
    with zipfile.ZipFile(docx_file) as z:
        xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        text = '\n'.join([node.text for node in tree.findall('.//w:t', ns) if node.text])
        
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(text)

if __name__ == '__main__':
    extract()
