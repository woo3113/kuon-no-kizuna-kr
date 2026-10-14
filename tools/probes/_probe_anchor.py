import struct, re, os, io
from collections import defaultdict
out = io.open(r'C:\Users\woo31\AppData\Local\Temp\opencode\_probe_anchor.txt','w',encoding='utf-8')
w = out.write

base = r'F:\TeraBoxDownload\구원의반\_work\apk\assets\bin\Data'
parts_ = sorted([f for f in os.listdir(base) if f.startswith('level4.split')], key=lambda s: int(s.rsplit('split',1)[1]))
d = b''.join(open(os.path.join(base,f),'rb').read() for f in parts_)
n=len(d); recs=[]; i=0
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
TOK=re.compile(rb'([GHBEN])_MS(\d+)', re.I)
dlg=[]; pend=[]
msmap=defaultdict(list)   # token -> list of dialogue idx that follow
for raw in recs:
    try: t=raw.decode('utf-8')
    except UnicodeDecodeError: t=None
    if t is not None and is_dialogue(t):
        dlg.append(t)
        for m in TOK.finditer(raw if False else b''):
            pass
        pend=[]
    else:
        for m in TOK.finditer(raw):
            tok = m.group(1).decode().upper() + '_MS' + m.group(2).decode()
            msmap[tok].append(len(dlg))   # next dialogue index after this token
w("distinct MS tokens: %d\n" % len(msmap))
# show next-dialogue text for a few key tokens
for tok in ['G_MS01','G_MS02','G_MS03','G_MS04','G_MS05','B_MS01','B_MS02','E_MS01','E_MS02','H_MS01','N_MS01','G_MS299','G_MS100','G_MS102','G_MS168','G_MS169']:
    v = msmap.get(tok)
    w("\n--- token %s : %d hits ---\n" % (tok, len(v) if v else 0))
    if v:
        for idx in v[:4]:
            w("   next dlg idx=%6d : %s\n" % (idx, (dlg[idx][:70] if idx < len(dlg) else '<end>')))
out.close(); print("ok")
