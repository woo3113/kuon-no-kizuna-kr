"""analyze_their.py — 배포된 한글패치 ISO 분석
- 그들의 한글 코드 범위(SCP 리드바이트 분포, 폰트 사용자영역)
- FONT1/FONT2 헤더 및 관계
사용: py -3.14 analyze_their.py <iso>
"""
import struct, sys, collections
sys.stdout.reconfigure(encoding='utf-8')

ISO = sys.argv[1] if len(sys.argv) > 1 else r'F:\psptest\_knk\krvoice.iso'
f = open(ISO, 'rb')
def rd(off, n):
    f.seek(off); return f.read(n)
pvd = 16*2048
pvd_b = rd(pvd, 2048)
root_lba = struct.unpack_from('<I', pvd_b, 158)[0]
root_size = struct.unpack_from('<I', pvd_b, 166)[0]

def walk(lba, size, path=""):
    off = lba*2048; end = off+size; res = {}
    while off < end:
        head = rd(off, 256)
        if not head: break
        ln = head[0]
        if ln == 0:
            off = ((off//2048)+1)*2048
            if off >= end: break
            continue
        nl = head[32]; name = bytes(head[33:33+nl]); fl = head[25]
        l2 = struct.unpack_from('<I', head, 2)[0]; dl = struct.unpack_from('<I', head, 10)[0]
        if name not in (b'\x00', b'\x01'):
            p = path + "/" + name.decode('latin1').split(';')[0]
            if fl & 2: res.update(walk(l2, dl, p))
            else: res[p] = (l2, dl)
        off += ln
    return res
files = walk(root_lba, root_size)
print("파일 수:", len(files))
for k in sorted(files):
    if k.upper().endswith(('.FNT', '.SCP', '.IMY')): print("   %-40s lba=%-8d size=%d" % (k, files[k][0], files[k][1]))

def read(key):
    lba, size = files[key]
    f.seek(lba*2048); return f.read(size)

def font_info(key):
    b = read(key)
    cnt = struct.unpack_from('<I', b, 8)[0]
    ents = {}
    for i in range(cnt):
        o = 12+i*8
        ents[b[o:o+2]] = (struct.unpack_from('<H', b, o+2)[0], struct.unpack_from('<I', b, o+4)[0])
    data = b[12+cnt*8:]
    user = [c for c in ents if 0xF0 <= c[0] <= 0xF9]
    print("\n%s magic=%s byte5=%d stride=%d rows=%d glyphs=%d 사용자영역=%d" %
          (key, b[:5], b[5], b[6], b[7], cnt, len(user)))
    return b[6], b[7], ents, data

# 폰트
F = {}
for k in sorted(files):
    if k.upper().endswith('FONT1.FNT') or k.upper().endswith('FONT2.FNT'):
        F[k] = font_info(k)

# FONT1 vs FONT2 관계 (사용자영역 코드)
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

if len(F) >= 2:
    ks = sorted(F)
    s1, r1, e1, d1 = F[ks[0]]; s2, r2, e2, d2 = F[ks[1]]
    common = [c for c in e1 if c in e2 and 0xF0 <= c[0] <= 0xF9]
    if common:
        import statistics
        ddx, ddy, rat = [], [], []
        for c in common[:400]:
            a = dec(d1[e1[c][1]:e1[c][1]+e1[c][0]], s1, r1)
            b = dec(d2[e2[c][1]:e2[c][1]+e2[c][0]], s2, r2)
            sa = sum(a); sb = sum(b); rat.append(sb/max(1, sa))
            if sa and sb:
                ax = sum((i % s1)*v for i, v in enumerate(a))/sa; ay = sum((i//s1)*v for i, v in enumerate(a))/sa
                bx = sum((i % s2)*v for i, v in enumerate(b))/sb; by = sum((i//s2)*v for i, v in enumerate(b))/sb
                ddx.append(bx-ax); ddy.append(by-ay)
        print("\n[FONT1 vs FONT2, 사용자영역 코드 %d개]" % len(common))
        print("  강도비 FONT2/FONT1 = %.3f" % statistics.mean(rat))
        print("  무게중심 시프트 dx=%.3f dy=%.3f" % (statistics.mean(ddx), statistics.mean(ddy)))
    else:
        print("\n[FONT1/FONT2 공통 사용자영역 코드 없음]")

# SCP
if '/SCRIPT.SCP' in files:
    raw = read('/SCRIPT.SCP')
    dec2 = raw if struct.unpack_from('<I', raw, 0)[0] < 100000 else bytes(x ^ 0xFF for x in raw)
    cnt = struct.unpack_from('<I', dec2, 0)[0]; D0 = 4+cnt*24
    print("\nSCRIPT.SCP size=%d blocks=%d" % (len(raw), cnt))
    of, sz = struct.unpack_from('<II', dec2, 4+16)
    blk = dec2[D0+of:D0+of+sz]
    i = blk.find(b'\r:00002\r')
    print("  :00002:", blk[i:i+90].hex(' '))
    hist = collections.Counter(); j = 0; body = dec2[D0:]
    while j+1 < len(body):
        b0, b1 = body[j], body[j+1]
        if ((0x81 <= b0 <= 0x9F) or (0xE0 <= b0 <= 0xFC)) and ((0x40 <= b1 <= 0x7E) or (0x80 <= b1 <= 0xFC)):
            hist[b0] += 1; j += 2; continue
        j += 1
    print("  리드바이트 상위:", hist.most_common(12))
    print("  사용자영역(0xF0~0xF9) 사용수:", sum(v for k2, v in hist.items() if 0xF0 <= k2 <= 0xF9))
f.close()
