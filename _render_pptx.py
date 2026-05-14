"""Convert PPTX to PNG images using PowerPoint COM."""
import os
import win32com.client
import pythoncom

src = r"C:\Users\32545\Desktop\本周验收汇报.pptx"
out_dir = r"C:\Users\32545\Desktop\软件设计\ruanjiansheji\_qa_render"
os.makedirs(out_dir, exist_ok=True)

pythoncom.CoInitialize()
ppt = win32com.client.DispatchEx("PowerPoint.Application")
# WithWindow=False would be ideal but causes issues; just use it normally
deck = ppt.Presentations.Open(src, WithWindow=False)
try:
    for i, slide in enumerate(deck.Slides, start=1):
        out = os.path.join(out_dir, f"slide-{i:02d}.png")
        slide.Export(out, "PNG", 1600, 900)
        print("exported", out)
finally:
    deck.Close()
    ppt.Quit()
