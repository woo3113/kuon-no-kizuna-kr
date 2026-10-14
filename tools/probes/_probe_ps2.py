"""_probe_ps2.py — PS2판 FONT/SCRIPT 구조 확인 (PSP와 동일 여부)"""
import struct, io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
EX = r'F:\TeraBoxDownload\구원의반\_work\ps2\ex'
PSP = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR'

for nm in ('FONT1.FNT', 'FONT2.FNT', 'DBGFONT.IMY'):
    p = os.path.join(EX, nm)
    b = open(p, 'rb').read()
    hdr = b[:8]
    extra = ''
    if b[:5] == b'FCOMP':
        cnt = struct.unpack_from('<I', b, 8)[0]
        extra = 'byte5=%d stride=%d rows=%d cnt=%d' % (b[5], b[6], b[7], cnt)
    print("%-12s size=%-9d magic=%r  %s" % (nm, len(b), hdr, extra))

# SCRIPT.SCP: XOR 여부 판정
s = open(os.path.join(EX, 'SCRIPT.SCP'), 'rb').read()
print("\nPS2 SCRIPT.SCP size=%d" % len(s))
raw = s
if struct.unpack_from('<I', s, 0)[0] > 100000:
    raw = bytes(x ^ 0xFF for x in s)
    print("  -> XOR 0xFF 적용 판정")
cnt = struct.unpack_from('<I', raw, 0)[0]
print("  block count=%d" % cnt)
names = [raw[4+i*24:4+i*24+16].split(b'\x00')[0].decode('ascii','replace') for i in range(cnt)]
print("  first 6 blocks:", names[:6])
print("  last 4:", names[-4:])
# PSP와 비교
ps = bytes(x ^ 0xFF for x in open(os.path.join(PSP, 'SCRIPT.SCP'), 'rb').read())
pcnt = struct.unpack_from('<I', ps, 0)[0]
pnames = [ps[4+i*24:4+i*24+16].split(b'\x00')[0].decode('ascii','replace') for i in range(pcnt)]
print("  PSP block count=%d  names equal=%s" % (pcnt, pnames == names))
# 블록0 앞부분 비교
for tag, d in (('PS2', raw), ('PSP', ps)):
    D0 = 4 + cnt*24
    o = 4
    name = d[o:o+16].split(b'\x00')[0].decode(); off, size = struct.unpack_from('<II', d, o+16)
    body = d[D0+off:D0+off+size].decode('cp932', 'replace')
    print("  %s block0 %s off=%d size=%d head=%r" % (tag, name, off, size, body[:60]))
# font diff
f1p = open(os.path.join(PSP, 'FONT1.FNT'), 'rb').read()
f1s = open(os.path.join(EX, 'FONT1.FNT'), 'rb').read()
print("\nFONT1 PSP=%d PS2=%d  header PSP=%s PS2=%s" % (len(f1p), len(f1s), f1p[:8].hex(' '), f1s[:8].hex(' ')))
