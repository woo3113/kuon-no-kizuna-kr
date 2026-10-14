"""_probe_font12b.py — 같은 코드의 FONT1/FONT2 글리프 픽셀 비교"""
import struct, sys
sys.stdout.reconfigure(encoding='utf-8')

def load(p):
    raw = open(p, 'rb').read()
    stride, rows = raw[6], raw[7]
    cnt = struct.unpack_from('<I', raw, 8)[0]
    ents = {}
    for i in range(cnt):
        o = 12+i*8
        ents[raw[o:o+2]] = (struct.unpack_from('<H', raw, o+2)[0], struct.unpack_from('<I', raw, o+4)[0])
    data = raw[12+cnt*8:]
    return stride, rows, ents, data

def decode(payload, stride, rows):
    table = [-1, -stride-1, -stride, -stride+1]
    out = bytearray(); i = 0; n = len(payload)
    while i < n and len(out) < stride*rows:
        b = payload[i]
        if (b & 0x80) == 0:
            C = (b & 0x70) >> 4
            out.append(b & 0x0F); i += 1
            while C > 0 and i < n:
                bb = payload[i]
                out.append((bb >> 4) & 0x0F); C -= 1
                if C > 0: out.append(bb & 0x0F); C -= 1
                i += 1
        else:
            idx = (b & 0x60) >> 5; C = b & 0x1F; off = table[idx]
            for _ in range(C):
                pp = len(out)+off
                out.append(out[pp] if 0 <= pp < len(out) else 0)
            i += 1
    while len(out) < stride*rows: out.append(0)
    return out

def show(tag, p1, p2, codes):
    s, r, e1, d1 = load(p1); _, _, e2, d2 = load(p2)
    for c in codes:
        if c not in e1: print("code %s 없음" % c.hex()); continue
        a = decode(d1[e1[c][1]:e1[c][1]+e1[c][0]], s, r)
        b = decode(d2[e2[c][1]:e2[c][1]+e2[c][0]], s, r)
        print("\n=== %s code=%s  FONT1 | FONT2 ===" % (tag, c.hex()))
        ramp = " .:-=+*#%@"
        for y in range(r):
            ra = ''.join(ramp[min(9, a[y*s+x] if y*s+x < len(a) else 0)] for x in range(s))
            rb = ''.join(ramp[min(9, b[y*s+x] if y*s+x < len(b) else 0)] for x in range(s))
            print("  %s | %s" % (ra, rb))

codes = [bytes.fromhex(h) for h in ('82a0', '82a2', '82b1', '8140')]  # あ, い, ア, 전각공백
show("PSP", r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\FONT1.FNT',
           r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\FONT2.FNT', codes)
