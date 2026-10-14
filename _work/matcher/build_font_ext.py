"""build_font_ext.py — 한글 글리프를 폰트에 확장
FONT1 = 원본 일본어 글리프와 같은 스타일
FONT2 = 원본 일본어 관계 복제 (굵기 ~1.25x + 서브픽셀 시프트)
- 코드는 kr_code_map.json 그대로 사용
"""
import struct, os, json
from PIL import Image, ImageDraw, ImageFont

PROJ = r'F:\TeraBoxDownload\구원의반'
SRC_FONT1 = PROJ + r'\_work\psp_work\usrdir\PSP_GAME\USRDIR\FONT1.FNT'
SRC_FONT2 = PROJ + r'\_work\psp_work\usrdir\PSP_GAME\USRDIR\FONT2.FNT'
KRFONT = r'C:\Windows\Fonts\malgunbd.ttf'
OUTDIR = PROJ + r'\_work\krfont'
MAP = os.path.join(OUTDIR, 'kr_code_map.json')
SS = 4                                   # 슈퍼샘플

code_of = {s: bytes.fromhex(v) for s, v in json.load(open(MAP, encoding='utf-8')).items()}
syllables = list(code_of.keys())
need = set()
for ln in open(PROJ + r'\_work\matcher\kr_psp.tsv', encoding='utf-8').read().split('\n')[1:]:
    c = ln.split('\t')
    if len(c) >= 4:
        for ch in c[3]:
            if '\uac00' <= ch <= '\ud7a3': need.add(ch)
missing = need - set(code_of)
print("코드맵=%d 필요=%d 누락=%d" % (len(code_of), len(need), len(missing)))
assert not missing

def render(ch, W, H, bold=0, shift=(0.0, 0.0), margin=0.86):
    iw, ih = int(round(W*margin*SS)), int(round(H*margin*SS))
    fsize = 64*SS
    f = ImageFont.truetype(KRFONT, fsize)
    img = Image.new('L', (fsize*2, fsize*2), 0)
    ImageDraw.Draw(img).text((fsize//2, fsize//2 - fsize//8), ch, font=f, fill=255)
    bb = img.getbbox()
    out = Image.new('L', (W*SS, H*SS), 0)
    if bb:
        img = img.crop(bb); w, h = img.size
        sc = min(iw/w, ih/h)
        nw, nh = max(1, round(w*sc)), max(1, round(h*sc))
        img = img.resize((nw, nh), Image.LANCZOS)
        out.paste(img, ((W*SS-nw)//2, (H*SS-nh)//2))
    if bold:
        out = out.filter(ImageFilter.MaxFilter(2*bold+1))
    if shift != (0.0, 0.0):
        out = out.transform(out.size, Image.AFFINE, (1, 0, -shift[0]*SS, 0, 1, -shift[1]*SS), resample=Image.BILINEAR)
    out = out.resize((W, H), Image.LANCZOS)
    return [min(15, (v*15 + 127)//255) for v in out.getdata()]

from PIL import ImageFilter

def build(srcpath, dstpath, bold=0, shift=(0.0, 0.0)):
    raw = open(srcpath, 'rb').read()
    assert raw[:5] == b'FCOMP'
    byte5, stride, rows = raw[5], raw[6], raw[7]
    cnt = struct.unpack_from('<I', raw, 8)[0]
    ents = []
    for i in range(cnt):
        o = 12 + i*8
        ents.append((raw[o:o+2], *struct.unpack_from('<HI', raw, o+2)))
    data = raw[12 + cnt*8:]
    ne = list(ents); pl = bytearray(); cur = len(data)
    for s in syllables:
        flat = render(s, stride, rows, bold=bold, shift=shift)
        ne.append((code_of[s], len(flat), cur)); pl += bytes(flat); cur += len(flat)
    out = bytearray(); out += b'FCOMP' + bytes([byte5, stride, rows]) + struct.pack('<I', cnt+len(syllables))
    for c, sz, off in ne: out += c + struct.pack('<HI', sz, off)
    out += data + pl
    open(dstpath, 'wb').write(bytes(out))
    print("  %s: %d -> %d (cnt %d->%d bold=%d shift=%s)" % (os.path.basename(srcpath), len(raw), len(out), cnt, cnt+len(syllables), bold, shift))

# 배포된 한글패치와 동일: FONT1 = FONT2 (동일 글리프, 굵기/시프트 차이 없음)
build(SRC_FONT1, os.path.join(OUTDIR, 'FONT1.FNT'), bold=0, shift=(0.0, 0.0))
build(SRC_FONT2, os.path.join(OUTDIR, 'FONT2.FNT'), bold=0, shift=(0.0, 0.0))
print("done")
