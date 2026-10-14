"""_probe_font12.py — 원본 FONT1 vs FONT2 코드집합/글리프 비교 (PSP/PS2)"""
import struct, sys, os
sys.stdout.reconfigure(encoding='utf-8')

def load(p):
    raw = open(p, 'rb').read()
    assert raw[:5] == b'FCOMP'
    stride, rows = raw[6], raw[7]
    cnt = struct.unpack_from('<I', raw, 8)[0]
    ents = {}
    for i in range(cnt):
        o = 12+i*8
        ents[raw[o:o+2]] = (struct.unpack_from('<H', raw, o+2)[0], struct.unpack_from('<I', raw, o+4)[0])
    data = raw[12+cnt*8:]
    return stride, rows, ents, data

def cmp(tag, p1, p2):
    s1, r1, e1, d1 = load(p1); s2, r2, e2, d2 = load(p2)
    c1 = set(e1); c2 = set(e2)
    inter = c1 & c2
    print("\n=== %s ===" % tag)
    print("  FONT1 stride=%dx%d glyphs=%d  FONT2 stride=%dx%d glyphs=%d" % (s1, r1, len(c1), s2, r2, len(c2)))
    print("  코드 교집합=%d  FONT1만=%d  FONT2만=%d  합집합=%d" % (len(inter), len(c1-c2), len(c2-c1), len(c1 | c2)))
    # 교집합 코드의 글리프 페이로드 동일 여부
    same = diff = 0
    for c in list(inter)[:4000]:
        off1 = struct.unpack_from('<I', open(p1,'rb').read(), 0)  # noop
    # 페이로드 비교
    raw1 = open(p1,'rb').read()[12+len(c1)*8:]
    raw2 = open(p2,'rb').read()[12+len(c2)*8:]
    for c in list(inter)[:2000]:
        s1_, o1 = e1[c]; s2_, o2 = e2[c]
        if raw1[o1:o1+s1_] == raw2[o2:o2+s2_]: same += 1
        else: diff += 1
    print("  교집합 표본(2000): 동일=%d  다름=%d" % (same, diff))
    # 코드 범위
    def rng(s):
        ls = sorted(x[0] for x in s)
        return "lead %02x..%02x" % (ls[0], ls[-1])
    print("  FONT1 코드범위: %s" % rng(c1))
    print("  FONT2 코드범위: %s" % rng(c2))

cmp("PSP 원본", r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\FONT1.FNT',
             r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\FONT2.FNT')
cmp("PS2 원본", r'F:\TeraBoxDownload\구원의반\_work\ps2\ex\FONT1.FNT',
             r'F:\TeraBoxDownload\구원의반\_work\ps2\ex\FONT2.FNT')
