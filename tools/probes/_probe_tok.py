import struct, re, os, io
from collections import Counter, defaultdict
out = io.open(r'C:\Users\woo31\AppData\Local\Temp\opencode\_probe_tok.txt','w',encoding='utf-8')
w = out.write

# PSP tag args for EV / ENTRY / BG / JUMP
SCP = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\SCRIPT.SCP'
dd = bytes(b ^ 0xFF for b in open(SCP,'rb').read())
cnt = struct.unpack_from('<I', dd, 0)[0]; D0 = 4 + cnt*24
blocks = [(dd[4+i*24:4+i*24+16].split(b'\x00')[0].decode('ascii','replace'), *struct.unpack_from('<II', dd, 4+i*24+16)) for i in range(cnt)]
names = [n for n,_,_ in blocks]
w("block name prefixes: %s\n" % Counter(n.split('_')[0].lower() for n in names))
w("sample names: %s\n" % names[:12])
# collect tag-with-arg sequences
for tagname in ('EV','ENTRY','BG','JUMP','NAME','CHANGE_BG','BG2'):
    vals=[]
    for n,off,size in blocks:
        txt = dd[D0+off:D0+off+size].decode('cp932','replace')
        for m in re.finditer(r'<%s>([^\r<]*)' % tagname, txt):
            vals.append(m.group(1)[:24])
    c = Counter(vals)
    w("\n<%s> %d occurrences, top 15: %s\n" % (tagname, len(vals), c.most_common(15)))

# Android asset-name-like tokens
base = r'F:\TeraBoxDownload\구원의반\_work\apk\assets\bin\Data'
parts_ = sorted([f for f in os.listdir(base) if f.startswith('level4.split')], key=lambda s: int(s.rsplit('split',1)[1]))
d = b''.join(open(os.path.join(base,f),'rb').read() for f in parts_)
n=len(d); recs=[]; i=0
while i+4<=n:
    ln=struct.unpack_from('<I',d,i)[0]
    if 1<=ln<=8192 and i+4+ln<=n:
        recs.append(d[i+4:i+4+ln]); i+=4+ln; i=(i+3)&~3; continue
    i+=4
TOK = re.compile(rb'[A-Za-z_][A-Za-z0-9_]{2,}')
toks=Counter()
for raw in recs:
    for m in TOK.finditer(raw):
        toks[m.group().decode('ascii')]+=1
w("\n=== android tokens matching [GHBENO]_[A-Za-z0-9]+ ===\n")
pat = re.compile(r'^[GHBENO]_[A-Za-z0-9]+$')
sel = [(t,c) for t,c in toks.items() if pat.match(t)]
w("distinct=%d total=%d\n" % (len(sel), sum(c for _,c in sel)))
for t,c in sorted(sel)[:200]:
    w("  %s (%d)\n" % (t,c))
w("\n=== tokens containing 'MS' ===\n")
sel2 = [(t,c) for t,c in toks.items() if 'MS' in t or 'ms' in t]
for t,c in sorted(sel2)[:120]:
    w("  %s (%d)\n" % (t,c))
out.close(); print("ok")
