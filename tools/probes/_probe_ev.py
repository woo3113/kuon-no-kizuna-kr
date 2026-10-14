import struct, re, os, io, json
from collections import Counter
out = io.open(r'C:\Users\woo31\AppData\Local\Temp\opencode\_probe_ev.txt','w',encoding='utf-8')
w = out.write

# ---------- SCP ----------
SCP = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\SCRIPT.SCP'
dd = bytes(b ^ 0xFF for b in open(SCP,'rb').read())
cnt = struct.unpack_from('<I', dd, 0)[0]; D0 = 4 + cnt*24
blocks = [(dd[4+i*24:4+i*24+16].split(b'\x00')[0].decode('ascii','replace'), *struct.unpack_from('<II', dd, 4+i*24+16)) for i in range(cnt)]
ARG = re.compile(r'<[^>]*>|[0-9A-Za-z_,\.\-]+')
CJK = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\u2010-\u2030\u25a0-\u25ff]')
tagre = re.compile(r'<([A-Za-z0-9_]+)>')
def scp_lines(off,size):
    txt = dd[D0+off:D0+off+size].decode('cp932','replace')
    parts = re.split(r':(\d{4,6})', txt)
    out2=[]
    for k in range(1,len(parts),2):
        body = parts[k+1] if k+1<len(parts) else ''
        tags = [m.upper() for m in tagre.findall(body)]
        buf=[]
        for ch in body.split('\r'):
            c = ARG.sub('', ch).strip()
            if c and CJK.search(c): buf.append(c)
        if buf: out2.append((''.join(buf), tags))
    return out2
scp_blocks = [(n, scp_lines(off,size)) for n,off,size in blocks]
tag2 = Counter()
for n,ls in scp_blocks:
    for t,tags in ls: tag2.update(tags)
w("=== SCP tag counter (all blocks) top 60 ===\n")
for t,c in tag2.most_common(60): w("%7d %s\n" % (c,t))

# ---------- Android event stream ----------
base = r'F:\TeraBoxDownload\구원의반\_work\apk\assets\bin\Data'
parts_ = sorted([f for f in os.listdir(base) if f.startswith('level4.split')], key=lambda s: int(s.rsplit('split',1)[1]))
d = b''.join(open(os.path.join(base,f),'rb').read() for f in parts_)
n=len(d)
recs=[]; i=0
while i+4<=n:
    ln=struct.unpack_from('<I',d,i)[0]
    if 1<=ln<=8192 and i+4+ln<=n:
        recs.append(d[i+4:i+4+ln]); i+=4+ln; i=(i+3)&~3; continue
    i+=4
HAN=re.compile(r'[\uac00-\ud7a3]')
def is_dialogue(t):
    if len(t)<4 or not HAN.search(t): return False
    if re.fullmatch(r'[0-9A-Za-z_]+',t): return False
    if t[:1] in '「"『': return True
    return bool(re.search(r'[…。！？!?\.]$',t))
# ascii command tokens inside a record payload
TOK = re.compile(rb'[A-Za-z_][A-Za-z0-9_]{2,}')
def cmd_tokens(raw):
    res=[]
    for m in TOK.finditer(raw):
        s=m.group().decode('ascii')
        res.append(s)
    return res
# walk records, track dialogue index and collect command tokens since previous dialogue
dlg=[]; cmds_of=[]; pend=[]
ascii_tokens=Counter()
for raw in recs:
    try:
        t=raw.decode('utf-8')
    except UnicodeDecodeError:
        t=None
    if t is not None and is_dialogue(t):
        dlg.append(t); cmds_of.append(pend); pend=[]
    else:
        # try ascii tokens
        toks = cmd_tokens(raw)
        if toks:
            pend.extend(toks); ascii_tokens.update(toks)
w("\n=== android dialogue stream len=%d ===\n" % len(dlg))
w("=== android ascii token counter top 80 ===\n")
for t,c in ascii_tokens.most_common(80): w("%7d %s\n" % (c,t))

# confirm anchor
hit=[k for k,t in enumerate(dlg) if '순찰차' in t]
w("\n'순찰차' dialogue idx=%s\n" % hit[:8])
hit2=[k for k,t in enumerate(dlg) if '자갈' in t]
w("'자갈' idx=%s\n" % hit2[:8])
i0=hit[0] if hit else (hit2[0] if hit2 else 15452)
w("\n=== dlg around %d (+-6) ===\n" % i0)
for k in range(i0-8, i0+10):
    if 0<=k<len(dlg):
        w("%6d %-55s | cmds=%s\n" % (k, dlg[k][:55], cmds_of[k][:8]))
out.close(); print("ok")
