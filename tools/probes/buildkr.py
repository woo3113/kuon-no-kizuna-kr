import struct, os, shutil, json, collections
from PIL import Image, ImageDraw, ImageFont

SRC_FONT1 = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\FONT1.FNT'
SRC_FONT2 = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\FONT2.FNT'
KRFONT = r'C:\Windows\Fonts\malgunbd.ttf'
OUTDIR = r'F:\TeraBoxDownload\구원의반\_work\krfont'
os.makedirs(OUTDIR, exist_ok=True)

# ---- syllable set from the extracted android korean script ----
syl = collections.Counter()
for ln in open(r'F:\TeraBoxDownload\구원의반\_work\android_kr_lines.tsv', encoding='utf-8'):
    for c in ln:
        if '\uac00' <= c <= '\ud7a3':
            syl[c] += 1
syllables = sorted(syl.keys())          # 1408
print("syllables:", len(syllables))

# ---- SJIS user-defined code assignment ----
VALID_TRAIL = [t for t in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD))]
codes = []
for lead in range(0xF0, 0xFA):
    for trail in VALID_TRAIL:
        codes.append(bytes([lead, trail]))
print("available user-area codes:", len(codes))
assert len(codes) >= len(syllables), "not enough codes"
code_of = {s: codes[i] for i, s in enumerate(syllables)}
json.dump({s: c.hex() for s, c in code_of.items()}, open(os.path.join(OUTDIR, 'kr_code_map.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def render_kr(ch, box_w, box_h):
    fsize = 64
    f = ImageFont.truetype(KRFONT, fsize)
    img = Image.new('L', (fsize*2, fsize*2), 0)
    ImageDraw.Draw(img).text((fsize//2, fsize//2 - fsize//8), ch, font=f, fill=255)
    bb = img.getbbox()
    if bb is None: return [0]*(box_w*box_h)
    img = img.crop(bb)
    w, h = img.size
    sc = min(box_w/w, box_h/h)
    nw, nh = max(1, int(round(w*sc))), max(1, int(round(h*sc)))
    img = img.resize((nw, nh), Image.LANCZOS)
    out = Image.new('L', (box_w, box_h), 0)
    out.paste(img, ((box_w-nw)//2, (box_h-nh)//2))
    px = list(out.getdata())
    return [min(15, (v*15 + 127)//255) for v in px]

def build(srcpath, dstpath):
    raw = open(srcpath, 'rb').read()
    assert raw[:5] == b'FCOMP'
    byte5, stride, rows = raw[5], raw[6], raw[7]
    cnt = struct.unpack_from('<I', raw, 8)[0]
    ents = []
    for i in range(cnt):
        o = 12 + i*8
        code = raw[o:o+2]
        s, off = struct.unpack_from('<HI', raw, o+2)
        ents.append((code, s, off))
    data = raw[12 + cnt*8:]
    n_new = len(syllables)
    # NOTE: offsets are relative to the data area. The data area moves right by 8*n_new bytes
    # because the table grows, but that shift is implicit -> keep original offsets as-is.
    new_ents = list(ents)
    payloads = bytearray()
    cur = len(data)
    for s in syllables:
        flat = render_kr(s, stride, rows)
        pay = bytes(flat)                 # 1 byte per pixel
        assert len(pay) == stride*rows
        new_ents.append((code_of[s], len(pay), cur))
        payloads += pay
        cur += len(pay)
    newcnt = cnt + n_new
    out = bytearray()
    out += b'FCOMP' + bytes([byte5, stride, rows])
    out += struct.pack('<I', newcnt)
    for c, s, off in new_ents:
        out += c + struct.pack('<HI', s, off)
    out += data
    out += payloads
    open(dstpath, 'wb').write(bytes(out))
    print(f"  {os.path.basename(srcpath)}: {len(raw)} -> {len(out)} bytes (cnt {cnt}->{newcnt}, +{len(payloads)} data)")
    return bytes(out)

F1 = build(SRC_FONT1, os.path.join(OUTDIR, 'FONT1.FNT'))
F2 = build(SRC_FONT2, os.path.join(OUTDIR, 'FONT2.FNT'))
print("built KR fonts.")

# ---- verify: decode a few new glyphs ----
def decode(payload, stride, rows):
    table = [-1, -stride-1, -stride, -stride+1]
    out = bytearray(); i = 0; n = len(payload)
    while i < n and len(out) < stride*rows+32:
        b = payload[i]
        if (b & 0x80) == 0:
            C = (b & 0x70) >> 4
            out.append(b & 0x0F); i += 1
            while C > 0:
                if i >= n: break
                bb = payload[i]
                out.append((bb >> 4) & 0x0F); C -= 1
                if C > 0:
                    out.append(bb & 0x0F); C -= 1
                i += 1
        else:
            idx = (b & 0x60) >> 5; C = b & 0x1F; off = table[idx]
            for _ in range(C):
                p = len(out)+off
                out.append(out[p] if 0 <= p < len(out) else 0)
            i += 1
    return bytes(out)
stride, rows = F1[6], F1[7]
cnt = struct.unpack_from('<I', F1, 8)[0]
DATA = 12 + cnt*8
ents = {}
for i in range(cnt):
    o = 12 + i*8
    ents[F1[o:o+2]] = struct.unpack_from('<HI', F1, o+2)
for s in ('안','녕','하','세','요','가','한'):
    c = code_of[s]
    sz, off = ents[c]
    px = decode(F1[DATA+off:DATA+off+sz], stride, rows)
    print(f"  verify {s} code={c.hex()} decoded={len(px)}px")
print("OK")
