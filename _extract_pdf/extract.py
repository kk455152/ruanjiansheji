import pypdfium2 as pdfium
import os, sys
desktop = r'c:\Users\32545\Desktop'
files = ['本周验收文档.pdf','设计和开发文档.pdf','第三次验收ppt.pdf','pptx example.pdf']
out_dir = r'c:\Users\32545\Desktop\软件设计\ruanjiansheji\_extract_pdf'
for src in files:
    p = os.path.join(desktop, src)
    pdf = pdfium.PdfDocument(p)
    name = src.replace('.pdf','').replace(' ','_')
    out_file = os.path.join(out_dir, name + '.txt')
    with open(out_file, 'w', encoding='utf-8') as f:
        for i in range(len(pdf)):
            page = pdf[i]
            tp = page.get_textpage()
            t = tp.get_text_range()
            f.write(f'=== Page {i+1} ===\n')
            f.write(t)
            f.write('\n\n')
    print('Done:', out_file, 'pages:', len(pdf))
