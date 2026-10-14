import struct, re, os, io
from collections import Counter
out = io.open(r'C:\Users\woo31\AppData\Local\Temp\opencode\_probe_ms.txt','w',encoding='utf-8')
w = out.write
# PSP block counts per prefix
SCP = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\SCRIPT.SCP'
dd = bytes(b ^ 0xFF for b in open(SCP,'rb').read())
cnt = struct.unpack_from('<I', dd, 0)[0]
names=[dd[4+i*24:4+i*24+16].split(b'\x00')[0].decode('ascii','replace') for i in range(cnt)]
w("PSP blocks per prefix: %s\n" % Counter(n.split('_')[0].upper() for n in names))
low=[n.lower() for n in names]
w("PSP max ms# per prefix: %s\n" % {p: max(int(n.split('_')[1][2:]) for n in low if n.startswith(p.lower()+'_')) for p in 'GHBEN'})
# android tokens per prefix
base = r'F:\TeraBoxDownload\구원의반\_work\apk\assets\bin\Data'
parts_ = sorted([f for f in os.listdir(base) if f.startswith('level4.split')], key=lambda s: int(s.rsplit('split',1)[1]))
d = b''.join(open(os.path.join(base,f),'rb').read() for f in parts_)
TOK = re.compile(rb'([A-Z])_MS(\d+)')
num = {}
for m in TOK.finditer(d):
    p = m.group(1).decode(); v=int(m.group(2))
    num.setdefault(p, set()).add(v)
w("\nandroid MS tokens distinct per prefix: %s\n" % {p: len(s) for p,s in sorted(num.items())})
w("android max ms# per prefix: %s\n" % {p: max(s) for p,s in sorted(num.items())})
for p in sorted(num):
    w("  %s: %s\n" % (p, sorted(num[p])))
out.close(); print("ok")
