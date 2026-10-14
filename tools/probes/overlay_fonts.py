"""overlay_fonts.py — FONT1/FONT2 일본어 글리프를 겹쳐 시각화 (역할 파악)"""
import struct, sys, io, os
from PIL import Image, ImageDraw
sys.stdout.reconfigure(encoding='utf-8')

def load(p):
    raw=open(p,'rb').read(); s,r=raw[6],raw[7]; cnt=struct.unpack_from('<I',raw,8)[0]
    e={}
    for i in range(cnt):
        o=12+i*8; e[raw[o:o+2]]=(struct.unpack_from('<H',raw,o+2)[0],struct.unpack_from('<I',raw,o+4)[0])
    return s,r,e,raw[12+cnt*8:]
def dec(pl,s,r):
    t=[-1,-s-1,-s,-s+1];out=bytearray();i=0;n=len(pl)
    while i<n and len(out)<s*r:
        b=pl[i]
        if (b&0x80)==0:
            C=(b&0x70)>>4;out.append(b&0x0F);i+=1
            while C>0 and i<n:
                bb=pl[i];out.append((bb>>4)&0x0F);C-=1
                if C>0:out.append(bb&0x0F);C-=1
                i+=1
        else:
            ix=(b&0x60)>>5;C=b&0x1F;off=t[ix]
            for _ in range(C):
                q=len(out)+off;out.append(out[q] if 0<=q<len(out) else 0)
            i+=1
    while len(out)<s*r: out.append(0)
    return out

PSP = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR'
s,r,e1,d1 = load(PSP + r'\FONT1.FNT')
_,_,e2,d2 = load(PSP + r'\FONT2.FNT')
def g(e,d,c):
    sz,off=e[c]; return dec(d[off:off+sz], s, r)

SC = 12
def cell(f1, f2, shift=(0,0), label=''):
    im = Image.new('RGB', (s, r), (0,0,0))
    px = im.load()
    for y in range(r):
        for x in range(s):
            v1 = f1[y*s+x]
            sx, sy = x+shift[0], y+shift[1]
            v2 = f2[sy*s+sx] if (0<=sy<r and 0<=sx<s) else 0
            px[x,y] = (min(255,v1*18), min(255,v2*18), 60)
    return im.resize((s*SC, r*SC), Image.NEAREST)

# 일본어 대표 글자 (가나/한자)
chars = {'あ':'82a0','い':'82a2','ん':'82f1','日':'93fa','本':'967b','絆':'94bc'}
# 우리가 넣은 한글(빌드된 폰트에서 코드로)
MAP = {v:k for k,v in __import__('json').load(io.open(r'F:\TeraBoxDownload\구원의반\_work\krfont\kr_code_map.json',encoding='utf-8')).items()}
KR = r'F:\TeraBoxDownload\구원의반\_work\krfont'
sb,rb,eb1,db1 = load(KR + r'\FONT1.FNT')
_,_,eb2,db2 = load(KR + r'\FONT2.FNT')
kr_ch = {'춥':'춥','다':'다'}
kr_codes = {}
for ch in '춥다':
    h = MAP.get(ch)
    if h: kr_codes[ch] = bytes.fromhex(h)

rows = []
cols = [('FONT1', (0,0)), ('FONT2', (0,0)), ('겹침(1빨강/2파랑)', (0,0)), ('겹침+shift(1,1)', (1,1)), ('겹침+shift(2,2)', (2,2))]
W = s*SC*len(cols)+8*(len(cols)+1); H = (r*SC+30)* (len(chars)+len(kr_codes)) + 20
canvas = Image.new('RGB', (W, H), (30,30,30)); dr = ImageDraw.Draw(canvas)
y = 10
dr.text((8,y), "원본 일본어 폰트: FONT1 vs FONT2 및 겹침", fill=(255,255,255)); y += 22
for name, code in chars.items():
    c = bytes.fromhex(code)
    if c not in e1: continue
    f1 = g(e1,d1,c); f2 = g(e2,d2,c)
    x = 8
    for cn,(sx,sy) in cols:
        canvas.paste(cell(f1,f2,(sx,sy)), (x,y))
        dr.text((x, y-12), cn, fill=(200,220,255)); x += s*SC+8
    dr.text((8, y-12), name, fill=(255,220,120))
    y += r*SC+30
dr.text((8,y), "우리가 넣은 한글: FONT1 vs FONT2 (둘 다 동일하면 겹칠 때 고스트)", fill=(255,255,255)); y += 22
for ch, c in kr_codes.items():
    f1 = g(eb1,db1,c); f2 = g(eb2,db2,c)
    x = 8
    for cn,(sx,sy) in cols:
        canvas.paste(cell(f1,f2,(sx,sy)), (x,y)); x += s*SC+8
    dr.text((8,y-12), ch, fill=(255,220,120))
    y += r*SC+30
outp = r'C:\Users\woo31\AppData\Local\Temp\opencode\font_overlay.png'
canvas.save(outp)
print("saved", outp, canvas.size)
