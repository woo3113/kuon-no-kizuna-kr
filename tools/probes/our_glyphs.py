from PIL import Image, ImageDraw, ImageFont
import struct, json, io, os
PROJ = r'F:\TeraBoxDownload\구원의반'
MAP = json.load(io.open(PROJ + r'\_work\krfont\kr_code_map.json', encoding='utf-8'))
cmap = {k: bytes.fromhex(v) for k, v in MAP.items()}

def load(p):
    raw = open(p, 'rb').read(); s, r = raw[6], raw[7]
    cnt = struct.unpack_from('<I', raw, 8)[0]
    e = {}
    for i in range(cnt):
        o = 12+i*8
        e[raw[o:o+2]] = (struct.unpack_from('<H', raw, o+2)[0], struct.unpack_from('<I', raw, o+4)[0])
    return s, r, e, raw[12+cnt*8:]
def dec(pl, s, r):
    t = [-1, -s-1, -s, -s+1]; out = bytearray(); i = 0; n = len(pl)
    while i < n and len(out) < s*r:
        b = pl[i]
        if (b & 0x80) == 0:
            C = (b & 0x70) >> 4; out.append(b & 0x0F); i += 1
            while C > 0 and i < n:
                bb = pl[i]; out.append((bb >> 4) & 0x0F); C -= 1
                if C > 0: out.append(bb & 0x0F); C -= 1
                i += 1
        else:
            ix = (b & 0x60) >> 5; C = b & 0x1F; off = t[ix]
            for _ in range(C):
                q = len(out)+off; out.append(out[q] if 0 <= q < len(out) else 0)
            i += 1
    while len(out) < s*r: out.append(0)
    return out

B = PROJ + r'\_work\krfont'
s, r, e, d = load(B + r'\FONT1.FNT')
words = list('춥다질주하는순찰차')
SC = 16
W = len(words)*(s*SC+6)+10; H = r*SC+30
cv = Image.new('RGB', (W, H), (10,10,20)); dr = ImageDraw.Draw(cv)
x = 10
for ch in words:
    c = cmap.get(ch)
    if not c or c not in e:
        x += s*SC+6; continue
    px = dec(d[e[c][1]:e[c][1]+e[c][0]], s, r)
    im = Image.new('L', (s, r))
    im.putdata([v*17 for v in px])
    im = im.resize((s*SC, r*SC), Image.NEAREST)
    cv.paste(im.convert('RGB'), (x, 22))
    dr.text((x, 4), ch, fill=(255,220,120))
    # 폭 정보
    ink = [(i % s) for i in range(len(px)) if px[i] > 0]
    dr.text((x, 22+r*SC), "w%d-%d" % (min(ink), max(ink)) if ink else "-", fill=(120,220,255))
    x += s*SC+6
outp = r'C:\Users\woo31\AppData\Local\Temp\opencode\our_glyphs.png'
cv.save(outp)
print('saved', outp, cv.size)
