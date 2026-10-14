import struct, re, os, json
SCP = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\SCRIPT.SCP'
dd = bytes(b ^ 0xFF for b in open(SCP,'rb').read())
cnt = struct.unpack_from('<I', dd, 0)[0]
D0 = 4 + cnt*24
blocks = []
for i in range(cnt):
    o = 4 + i*24
    blocks.append((dd[o:o+16].split(b'\x00')[0].decode('ascii','replace'), *struct.unpack_from('<II', dd, o+16)))
ARG = re.compile(r'<[^>]*>|[0-9A-Za-z_,\.\-]+')
CJK = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\u2010-\u2030\u25a0-\u25ff]')
def scp_lines_of(off, size):
    txt = dd[D0+off:D0+off+size].decode('cp932','replace')
    parts = re.split(r':(\d{4,6})', txt)
    out = []
    for k in range(1, len(parts), 2):
        body = parts[k+1] if k+1 < len(parts) else ''
        buf = []
        for ch in body.split('\r'):
            c = ARG.sub('', ch).strip()
            if c and CJK.search(c): buf.append(c)
        if buf: out.append(''.join(buf))
    return out
scp_blocks = [(n, scp_lines_of(off, size)) for n, off, size in blocks]

base = r'F:\TeraBoxDownload\구원의반\_work\apk\assets\bin\Data'
parts_ = sorted([f for f in os.listdir(base) if f.startswith('level4.split')], key=lambda s: int(s.rsplit('split',1)[1]))
d = b''.join(open(os.path.join(base,f),'rb').read() for f in parts_)
recs=[]; i=0; n=len(d)
while i+4<=n:
    ln=struct.unpack_from('<I',d,i)[0]
    if 1<=ln<=1024 and i+4+ln<=n:
        raw=d[i+4:i+4+ln]
        try: t=raw.decode('utf-8'); ok=all(c=='\n' or c>=' ' for c in t)
        except UnicodeDecodeError: ok=False; t=None
        if ok and t:
            recs.append(t); i+=4+ln; i=(i+3)&~3; continue
    i+=4
HAN = re.compile(r'[\uac00-\ud7a3]')
def is_dialogue(t):
    if len(t) < 4 or not HAN.search(t): return False
    if re.fullmatch(r'[0-9A-Za-z_]+', t): return False
    if t[:1] in '「"『': return True
    return bool(re.search(r'[…。！？!?\.]$', t))
dlg = [t for t in recs if is_dialogue(t)]

ELL = ('…', '...', '……', '…….')
def endcls(t):
    s = t.rstrip()
    if s.endswith('」') or s.endswith('』') or s.endswith('"'): return 0
    if s.endswith('…') or s.endswith('.'): return 1
    if s.endswith('。'): return 2
    if s.endswith('！') or s.endswith('!') or s.endswith('？') or s.endswith('?'): return 3
    return 4
def feat(t):
    return (1 if t[:1] in '「"『' else 0, endcls(t), len(t))
FSCP = [[feat(t) for t in ls] for _, ls in scp_blocks]
FD = [feat(t) for t in dlg]

def align_from(target, w, maxk=3, minr=0.55, maxr=1.9):
    nt = len(target); INF = -10**9
    states = {(0, w): 0}; best = None
    for i in range(nt):
        tq, te, tl = target[i]
        nxt = {}
        for (ii, j), sc in states.items():
            if ii != i: continue
            for k in range(1, maxk+1):
                if j+k > len(dlg): break
                lens = sum(FD[x][2] for x in range(j, j+k)); q = FD[j][0]; e = FD[j][1]
                s = sc + (4 if q == tq else -3) + (3 if e == te else -1)
                r = tl / max(1, lens)
                s += 3 if 0.65 <= r <= 1.7 else (1 if minr <= r <= maxr else -4)
                key = (i+1, j+k)
                if nxt.get(key, INF) < s: nxt[key] = s
                if i+1 == nt and (best is None or s > best[0]):
                    best = (s, w, j+k)
        states = nxt
    return best

target = FSCP[0]
print("pilot block", scp_blocks[0][0], "lines", len(target))
res = []
for w in range(0, len(dlg)-3):
    b = align_from(target, w)
    if b: res.append(b)
res.sort(reverse=True)
print("top:", res[:6])
for sc, s, e in res[:2]:
    print(f"  start {s} end {e} score {sc}")
    for k in range(s, min(e, s+6)):
        print(f"     {k:6d} {dlg[k][:64]}")
