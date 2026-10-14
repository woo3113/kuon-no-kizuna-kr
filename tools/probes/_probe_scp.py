import struct, re, os, io, json

SCP = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\SCRIPT.SCP'
dd = bytes(b ^ 0xFF for b in open(SCP,'rb').read())
cnt = struct.unpack_from('<I', dd, 0)[0]
D0 = 4 + cnt*24
blocks = []
for i in range(cnt):
    o = 4 + i*24
    blocks.append((dd[o:o+16].split(b'\x00')[0].decode('ascii','replace'), *struct.unpack_from('<II', dd, o+16)))

out = io.open(r'C:\Users\woo31\AppData\Local\Temp\opencode\_probe_scp.txt','w',encoding='utf-8')
w = out.write
w("blocks=%d D0=%d\n" % (cnt, D0))
name, off, size = blocks[0]
raw = dd[D0+off:D0+off+size].decode('cp932','replace')
w("=== block %s off=%d size=%d len=%d ===\n" % (name, off, size, len(raw)))
w(raw[:3000])
w("\n\n=== raw repr first 2000 ===\n")
w(repr(raw[:2000]))
# count tags
tags = re.findall(r'<[^>]*>', raw)
from collections import Counter
w("\n\ntag counter top 40:\n")
for t,c in Counter(tags).most_common(40):
    w("%6d %s\n" % (c,t))
out.close()
print("ok")
