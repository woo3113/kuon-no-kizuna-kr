from PIL import Image
import os
DOC = r'C:\Users\woo31\OneDrive\문서\PPSSPP\PSP\SCREENSHOT'
OUT = r'C:\Users\woo31\AppData\Local\Temp\opencode\zoom_cmp.png'
ko = Image.open(os.path.join(DOC, 'ULJM05981_00130.jpg'))   # 한글
jp = Image.open(os.path.join(DOC, 'ULJM05981_00133.jpg'))   # 일본어
print('ko', ko.size, 'jp', jp.size)
# 텍스트 영역 크롭 (좌상단 대사 영역)
def crop(im):
    w, h = im.size
    return im.crop((int(w*0.15), int(h*0.03), int(w*0.60), int(h*0.22)))
ck = crop(ko); cj = crop(jp)
sc = 3
ck = ck.resize((ck.width*sc, ck.height*sc), Image.NEAREST)
cj = cj.resize((cj.width*sc, cj.height*sc), Image.NEAREST)
W = max(ck.width, cj.width); H = ck.height + cj.height + 30
canvas = Image.new('RGB', (W, H), (20, 20, 40))
canvas.paste(cj, (0, 0))
canvas.paste(ck, (0, cj.height + 30))
canvas.save(OUT)
print('saved', OUT, canvas.size)
