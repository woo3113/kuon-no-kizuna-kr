"""_probe_shift.py — FONT2 가 FONT1 의 시프트본인지 판정 (dx,dy 최적 + 잔차)"""
import struct, sys
sys.stdout.reconfigure(encoding='utf-8')
def load(p):
    raw = open(p,'rb').read(); stride, rows = raw[6], raw[7]
    cnt = struct.unpack_from('<I', raw, 8)[0]
    ents = {}
    for i in range(cnt):
        o = 12+i*8
        ents[raw[o:o+2]] = (struct.unpack_from('<H',raw,o+2)[0], struct.unpack_from('<I',raw,o+4)[0])
    return stride, rows, ents, raw[12+cnt*8:]
def dec(payload, s, r):
    tab=[-1,-s-1,-s,-s+1]; out=bytearray(); i=0; n=len(payload)
    while i<n and len(out)<s*r:
        b=payload[i]
        if (b&0x80)==0:
            C=(b&0x70)>>4; out.append(b&0x0F); i+=1
            while C>0 and i<n:
                bb=payload[i]; out.append((bb>>4)&0x0F); C-=1
                if C>0: out.append(bb&0x0F); C-=1
                i+=1
        else:
            idx=(b&0x60)>>5; C=b&0x1F; off=tab[idx]
            for _ in range(C):
                q=len(out)+off; out.append(out[q] if 0<=q<len(out) else 0)
            i+=1
    while len(out)<s*r: out.append(0)
    return out

BASE = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR'
s, r, e1, d1 = load(BASE + r'\FONT1.FNT')
_, _, e2, d2 = load(BASE + r'\FONT2.FNT')
codes = [c for c in e1 if c in e2]
def get(e, d, c):
    sz, off = e[c]; return dec(d[off:off+sz], s, r)
# 최적 시프트 분포
from collections import Counter
bestc = Counter(); resid = []
import random
random.seed(1)
sample = random.sample(codes, min(400, len(codes)))
for c in sample:
    a = get(e1,d1,c); b = get(e2,d2,c)
    bestv = -1; bestsh = (0,0)
    for dy in range(-2,3):
        for dx in range(-2,3):
            m = 0
            for y in range(r):
                for x in range(s):
                    sy, sx = y+dy, x+dx
                    if 0 <= sy < r and 0 <= sx < s:
                        if a[y*s+x] > 3 and b[sy*s+sx] > 3: m += 1
            if m > bestv: bestv = m; bestsh = (dx,dy)
    bestc[bestsh] += 1
    # 잔차: 시프트 후 겹침 대비 총 픽셀
    aN = sum(1 for v in a if v > 3); bN = sum(1 for v in b if v > 3)
    resid.append((aN, bN, bestv))
print("stride=%d rows=%d 표본=%d" % (s, r, len(sample)))
print("최적 시프트 분포(dx,dy):", bestc.most_common(8))
import statistics
rec = [bv/max(1,min(aN,bN)) for aN,bN,bv in resid]
print("겹침비(recall) 평균=%.3f  중앙=%.3f  최소=%.3f" % (statistics.mean(rec), statistics.median(rec), min(rec)))
ax = statistics.mean([aN for aN,_,_ in resid]); bx = statistics.mean([bN for _,bN,_ in resid])
print("평균 픽셀수 FONT1=%.1f FONT2=%.1f (비 %.2f)" % (ax, bx, bx/ax))
