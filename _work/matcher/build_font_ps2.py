"""build_font_ps2.py — PS2판 FONT1/FONT2 에 한글 글리프 확장 (stride/rows는 소스 헤더에서 자동)
기존 kr_code_map.json(PSP와 동일 코드) 재사용.
"""
import struct, os, json
from PIL import Image, ImageDraw, ImageFont

PROJ = r'F:\TeraBoxDownload\구원의반'
SRC = PROJ + r'\_work\ps2\ex'
OUTDIR = PROJ + r'\_work\ps2\krfont'
os.makedirs(OUTDIR, exist_ok=True)
KRFONT = r'C:\Windows\Fonts\malgunbd.ttf'
code_of = {s: bytes.fromhex(v) for s, v in json.load(open(PROJ + r'\_work\krfont\kr_code_map.json', encoding='utf-8')).items()}
syllables = list(code_of.keys())
print("음절:", len(syllables))

def render(ch, w, h):
    fsize = 64
    f = ImageFont.truetype(KRFONT, fsize)
    img = Image.new('L', (fsize*2, fsize*2), 0)
    ImageDraw.Draw(img).text((fsize//2, fsize//2 - fsize//8), ch, font=f, fill=255)
    bb = img.getbbox()
    if bb is None: return [0]*(w*h)
    img = img.crop(bb); W, H = img.size
    sc = min(w/W, h/H)
    nw, nh = max(1, int(round(W*sc))), max(1, int(round(H*sc)))
    img = img.resize((nw, nh), Image.LANCZOS)
    out = Image.new('L', (w, h), 0); out.paste(img, ((w-nw)//2, (h-nh)//2))
    return [min(15, (v*15+127)//255) for v in list(out.getdata())]

def dilate(flat, w, h):
    out = [0]*(w*h)
    for y in range(h):
        for x in range(w):
            v = flat[y*w+x]
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    sy, sx = y+dy, x+dx
                    if 0 <= sy < h and 0 <= sx < w:
                        q = flat[sy*w+sx]
                        if q > v: v = q
            out[y*w+x] = v
    return out

def build(src, dst, bold=False):
    raw = open(src, 'rb').read()
    assert raw[:5] == b'FCOMP'
    b5, stride, rows = raw[5], raw[6], raw[7]
    cnt = struct.unpack_from('<I', raw, 8)[0]
    ents = []
    for i in range(cnt):
        o = 12+i*8
        ents.append((raw[o:o+2], *struct.unpack_from('<HI', raw, o+2)))
    data = raw[12+cnt*8:]
    ne = list(ents); pl = bytearray(); cur = len(data)
    for s in syllables:
        flat = render(s, stride, rows)
        if bold: flat = dilate(flat, stride, rows)
        ne.append((code_of[s], len(flat), cur)); pl += bytes(flat); cur += len(flat)
    out = bytearray(); out += b'FCOMP' + bytes([b5, stride, rows]) + struct.pack('<I', cnt+len(syllables))
    for c, sz, off in ne: out += c + struct.pack('<HI', sz, off)
    out += data + pl
    open(dst, 'wb').write(bytes(out))
    print("  %s: %d -> %d (stride=%d rows=%d cnt %d->%d, bold=%s)" % (os.path.basename(src), len(raw), len(out), stride, rows, cnt, cnt+len(syllables), bold))

build(os.path.join(SRC, 'FONT1.FNT'), os.path.join(OUTDIR, 'FONT1.FNT'), bold=False)
build(os.path.join(SRC, 'FONT2.FNT'), os.path.join(OUTDIR, 'FONT2.FNT'), bold=True)
print("done")
