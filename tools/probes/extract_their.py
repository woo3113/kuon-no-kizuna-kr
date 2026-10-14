"""extract_their.py — 배포 패치 ISO에서 FONT1/FONT2/SCRIPT 추출 + 글리프 메트릭 비교"""
import struct, sys, os, io
sys.stdout.reconfigure(encoding='utf-8')
ISO = r'F:\psptest\Kuon no Kizuna - Sairinshou (K, FullVoice).iso'
OUT = r'F:\TeraBoxDownload\구원의반\_work\their'
os.makedirs(OUT, exist_ok=True)
f = open(ISO, 'rb')
def rd(off, n): f.seek(off); return f.read(n)
pvd = 16*2048; pb = rd(pvd, 2048)
rl = struct.unpack_from('<I', pb, 158)[0]; rs = struct.unpack_from('<I', pb, 166)[0]
def walk(lba, size, path=""):
    off = lba*2048; end = off+size; res = {}
    while off < end:
        h = rd(off, 256)
        if not h: break
        ln = h[0]
        if ln == 0:
            off = ((off//2048)+1)*2048
            if off >= end: break
            continue
        nl = h[32]; name = bytes(h[33:33+nl]); fl = h[25]
        l2 = struct.unpack_from('<I', h, 2)[0]; dl = struct.unpack_from('<I', h, 10)[0]
        if name not in (b'\x00', b'\x01'):
            p = path+"/"+name.decode('latin1').split(';')[0]
            if fl & 2: res.update(walk(l2, dl, p))
            else: res[p] = (l2, dl)
        off += ln
    return res
files = walk(rl, rs)
for k in ('/FONT1.FNT', '/FONT2.FNT', '/SCRIPT.SCP'):
    lba, size = files[k]
    blob = rd(lba*2048, size)
    open(os.path.join(OUT, os.path.basename(k)), 'wb').write(blob)
    print("saved %s (%d bytes)" % (os.path.basename(k), size))
f.close()

# 글리프 메트릭
def load(p):
    raw = open(p, 'rb').read()
    s, r = raw[6], raw[7]; cnt = struct.unpack_from('<I', raw, 8)[0]
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

s, r, e, d = load(os.path.join(OUT, 'FONT1.FNT'))
kr_codes = [c for c in e if 0xF0 <= c[0] <= 0xF9]
print("\n그들 FONT1: stride=%d rows=%d  한글코드=%d" % (s, r, len(kr_codes)))
# 메트릭 통계
xs0, xs1, ys0, ys1, npix = [], [], [], [], []
for c in kr_codes[:400]:
    px = dec(d[e[c][1]:e[c][1]+e[c][0]], s, r)
    ink = [(i % s, i // s) for i, v in enumerate(px) if v > 0]
    if not ink: continue
    xs0.append(min(a for a, _ in ink)); xs1.append(max(a for a, _ in ink))
    ys0.append(min(b for _, b in ink)); ys1.append(max(b for _, b in ink))
    npix.append(sum(1 for v in px if v > 0))
import statistics as st
print("  잉크 x: %d~%d (폭 %d)  y: %d~%d (높이 %d) of cell %dx%d  평균픽셀=%.0f" %
      (min(xs0), max(xs1), st.mean([b-a+1 for a, b in zip(xs0, xs1)]),
       min(ys0), max(ys1), st.mean([b-a+1 for a, b in zip(ys0, ys1)]), s, r, st.mean(npix)))

# 대응 샘플: :00002 의 f4b7, f156
for code in (bytes.fromhex('f4b7'), bytes.fromhex('f156')):
    if code in e:
        px = dec(d[e[code][1]:e[code][1]+e[code][0]], s, r)
        print("\n  글리프 %s:" % code.hex())
        for y in range(r):
            print("   " + ''.join(" .:-=+*#%@"[min(9, px[y*s+x])] for x in range(s)))
        break
