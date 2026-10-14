"""align_lines.py — 블록 창(align_final.tsv)에서 줄 단위 매핑을 복원
출력: align_lines.tsv  (block, idx, label, chars, jp, kr, a_start, a_end, n_consumed)
"""
import struct, re, os, io, bisect
from collections import defaultdict

PROJ = r'F:\TeraBoxDownload\구원의반'
SCP  = PROJ + r'\_work\psp_work\usrdir\PSP_GAME\USRDIR\SCRIPT.SCP'
BASE = PROJ + r'\_work\apk\assets\bin\Data'
OUTD = os.path.dirname(os.path.abspath(__file__))

# ---------- SCP ----------
dd = bytes(b ^ 0xFF for b in open(SCP, 'rb').read())
cnt = struct.unpack_from('<I', dd, 0)[0]; D0 = 4 + cnt * 24
blocks = [(dd[4+i*24:4+i*24+16].split(b'\x00')[0].decode('ascii', 'replace'),
           *struct.unpack_from('<II', dd, 4+i*24+16)) for i in range(cnt)]
TAGRE = re.compile(r'<([A-Za-z0-9_]+)>([^\r<]*)')
ARG   = re.compile(r'<[^>]*>')
CJK   = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\u2010-\u2030\u25a0-\u25ff]')
PSP_SE   = {'SE_LOAD', 'SE1', 'SE2', 'STOP_SE', 'SET_SE'}
PSP_BGM  = {'BGM', 'BGM_VOLUME', 'STOP_BGM'}
PSP_BG   = {'BG', 'CHANGE_BG', 'BG2', 'CLEAR_BG', 'SCROLLBG', 'MOVE_SCROLLBG', 'CLEAR_SCROLLBG',
            'BG_BRIGHT', 'CG_BRIGHT', 'CG_RGB', 'BU0', 'BU1', 'BU2', 'BU1_OFS', 'BU2_OFS',
            'CLEAR_BU0', 'CLEAR_BU1', 'CLEAR_BU2'}
PSP_FX   = {'FADE_SPEED', 'FLASH', 'WHITE_IN', 'WHITE_OUT', 'MASK', 'STOP_MASK', 'FLIP'}
PSP_WAIT = {'W1', 'W2'}
PSP_MSG  = {'MSG_IN', 'MSG_OUT', 'PAGE', 'SAVE', 'NAME'}
PSP_SHAKE = {'QUAKE', 'QUAKE2', 'SHOCK0', 'SHOCK1', 'STOP_SHOCK1'}
NAME_OK = re.compile(r'^[A-Za-z]{1,3}_[A-Za-z0-9]+')

def psp_extract(tags):
    cls = set(); names = {}
    def add(n):
        if n and n not in ('-1', '0'): names[n] = names.get(n, 0) + 1
    for name, arg in tags:
        N = name.upper()
        if N in PSP_SE:
            cls.add('SE'); m = re.match(r'\s*(\d+)', arg)
            if m: add('se%03d' % int(m.group(1)))
        elif N in PSP_BGM:
            cls.add('BGM')
            if N == 'STOP_BGM': add('bgm_stop')
            else:
                m = re.match(r'\s*(\d+)', arg)
                if m: add('bgm%02d' % int(m.group(1)))
        elif N in PSP_BG:
            cls.add('BG')
            if N == 'CLEAR_BG': add('bg_clear')
            elif N in ('SCROLLBG', 'MOVE_SCROLLBG', 'CLEAR_SCROLLBG'): add('scrollbg')
            else:
                for p in arg.split(','):
                    p = p.strip()
                    if NAME_OK.match(p): add(p.upper())
        elif N in PSP_FX: cls.add('FX'); add('fade')
        elif N in PSP_WAIT: cls.add('WAIT')
        elif N in PSP_MSG: cls.add('MSG')
        elif N in PSP_SHAKE: cls.add('SHAKE')
        elif N == 'EV':
            for p in arg.split(','):
                p = p.strip()
                if NAME_OK.match(p): add(p.upper())
    return frozenset(cls), names

def read_scp_block(off, size):
    txt = dd[D0+off:D0+off+size].decode('cp932', 'replace')
    parts = re.split(r':(\d{4,6})', txt)
    res = []; carry = []
    for k in range(1, len(parts), 2):
        body = parts[k+1] if k+1 < len(parts) else ''
        tags = TAGRE.findall(body)
        buf = []
        for ch in body.split('\r'):
            c = ARG.sub('', ch).strip()
            if c and CJK.search(c): buf.append(c)
        if buf:
            c, nm = psp_extract(carry + tags)
            res.append((''.join(buf), c, nm, parts[k])); carry = []
        else:
            carry += tags
    return res
SCPB = {}
for nm, off, size in blocks:
    ls = read_scp_block(off, size)
    if ls: SCPB[nm] = ls

# ---------- Android ----------
parts_ = sorted([f for f in os.listdir(BASE) if f.startswith('level4.split')],
                key=lambda s: int(s.rsplit('split', 1)[1]))
d = b''.join(open(os.path.join(BASE, f), 'rb').read() for f in parts_)
n = len(d); recs = []; i = 0
while i + 4 <= n:
    ln = struct.unpack_from('<I', d, i)[0]
    if 1 <= ln <= 8192 and i + 4 + ln <= n:
        recs.append(d[i+4:i+4+ln]); i += 4 + ln; i = (i+3) & ~3; continue
    i += 4
HAN = re.compile(r'[\uac00-\ud7a3]')
def is_dialogue(t):
    if len(t) < 4 or not HAN.search(t): return False
    if re.fullmatch(r'[0-9A-Za-z_]+', t): return False
    if t[:1] in '「"『': return True
    return bool(re.search(r'[…。！？!?\.]$', t))
TOK = re.compile(rb'[A-Za-z_][A-Za-z0-9_]{2,}')
AND_FX = re.compile(r'^(tr|flash)', re.I)
AND_SHAKE = {'shake', 'vibrate', 'surprise'}
AND_SCENE = re.compile(r'^[A-Za-z]_MS\d+$', re.I)
AND_EV = re.compile(r'^[A-Za-z]_EV\w+$', re.I)
AND_BG = re.compile(r'^(bg_|obtBG|frame|anm|Sprite|[A-Za-z]_[A-Za-z]{2}\d)', re.I)
AND_SE = re.compile(r'^f?se\d+$', re.I)
AND_BGM = re.compile(r'^bgm\d+$', re.I)
def and_extract(raw):
    cls = set(); names = {}
    def add(x):
        if x: names[x] = names.get(x, 0) + 1
    for m in TOK.finditer(raw):
        s = m.group().decode('ascii')
        if AND_SE.match(s):    cls.add('SE');  add('se%03d' % int(re.search(r'\d+', s).group()))
        elif AND_BGM.match(s): cls.add('BGM'); add('bgm%02d' % int(re.search(r'\d+', s).group()))
        elif AND_SCENE.match(s): cls.add('SCENE'); add(s.upper())
        elif AND_EV.match(s):  cls.add('EV'); add(s.upper())
        elif AND_FX.match(s):  cls.add('FX')
        elif s in AND_SHAKE:   cls.add('SHAKE')
        elif AND_BG.match(s):  cls.add('BG'); add(s.upper())
    return frozenset(cls), names
dlg = []; dcls = []; dnames = []; pend = []; last = -1
def flush():
    global pend
    if last < 0 or not pend: pend = []; return
    cs, nm2 = and_extract(b''.join(pend))
    dcls[last] |= cs
    for k, v in nm2.items(): dnames[last][k] = dnames[last].get(k, 0) + v
    pend = []
for raw in recs:
    try: t = raw.decode('utf-8')
    except UnicodeDecodeError: t = None
    if t is not None and is_dialogue(t):
        flush(); dlg.append(t); dcls.append(set()); dnames.append({}); last = len(dlg) - 1
    else: pend.append(raw)
flush()
W = len(dlg)
NAME2IDX = defaultdict(list)
for x in range(W):
    for k in dnames[x]: NAME2IDX[k].append(x)

def endcls(t):
    s = t.rstrip()
    if s.endswith('」') or s.endswith('』') or s.endswith('"'): return 0
    if s.endswith('…') or s.endswith('.'): return 1
    if s.endswith('。'): return 2
    if s.endswith('！') or s.endswith('!') or s.endswith('？') or s.endswith('?'): return 3
    return 4
def feat(t): return (1 if t[:1] in '「"『' else 0, endcls(t), len(t))
FD = [feat(t) for t in dlg]
PL = [0]*(W+1)
for x in range(W): PL[x+1] = PL[x] + FD[x][2]
CLASSES = ('SE', 'BGM', 'BG', 'FX', 'SHAKE')
NEXTC = {}
for c in CLASSES:
    arr = [W]*(W+1)
    for x in range(W-1, -1, -1): arr[x] = x if c in dcls[x] else arr[x+1]
    NEXTC[c] = arr

def dp_path(FEAT, TCLS, TNAM, w0, maxk=4):
    N = len(FEAT)
    states = {(0, w0): 0.0}
    par = {}
    finals = {}
    for i in range(N):
        tq, te, tl = FEAT[i]; ts = TCLS[i]; tn = TNAM[i]
        items = list(tn.items())
        nxt = {}
        for (ii, j), sc in states.items():
            if ii != i: continue
            for k in range(1, maxk+1):
                if j + k > W: break
                a = j; b = j + k            # 명령은 소비한 줄 그룹에 정확히 귀속(trailing)
                cv = 0.0
                for c in CLASSES:
                    it = c in ts; ia = NEXTC[c][a] < b
                    if it and ia: cv += 2.0
                    elif it != ia: cv -= 0.5
                nv = 0.0
                for kk, vv in items:
                    lst = NAME2IDX.get(kk)
                    if lst:
                        c2 = bisect.bisect_left(lst, b) - bisect.bisect_left(lst, a)
                        if c2: nv += 4.0 * (vv if vv < c2 else c2)
                lens = PL[j+k]-PL[j]
                s = sc + (4 if FD[j][0] == tq else -3) + (3 if FD[j][1] == te else -1)
                r = tl/(lens if lens else 1)
                s += 3 if 0.65 <= r <= 1.7 else (1 if 0.5 <= r <= 2.0 else -4)
                s += -0.4*(k-1) + cv + nv
                key = (i+1, j+k)
                if nxt.get(key, -1e18) < s:
                    nxt[key] = s; par[key] = (ii, j, k)
                if i+1 == N and (key not in finals or finals[key] < s): finals[key] = s
        states = nxt
    if not finals: return None
    key = max(finals, key=lambda k: finals[k])
    path = []
    cur = key
    while cur[0] > 0:
        ii, j, k = par[cur]
        path.append((ii, j, k)); cur = (ii, j)
    path.reverse()
    return path, finals[key]

# read align_final
FIN = os.path.join(OUTD, 'align_final.tsv')
wins = {}
with io.open(FIN, encoding='utf-8') as f:
    f.readline()
    for line in f:
        p = line.rstrip('\n').split('\t')
        if len(p) >= 4: wins[p[0]] = int(p[2])

out = io.open(os.path.join(OUTD, 'align_lines.tsv'), 'w', encoding='utf-8')
out.write("block\tidx\tlabel\tchars\tjp\tkr\ta_start\ta_end\tn_consumed\n")
nkr = 0; ntot = 0
for nm, ls in SCPB.items():
    if nm not in wins: continue
    FEAT = [feat(t) for t, _, _, _ in ls]
    TCLS = [c for _, c, _, _ in ls]
    TNAM = [m for _, _, m, _ in ls]
    w0 = wins[nm]
    path = dp_path(FEAT, TCLS, TNAM, w0)
    if not path: continue
    for (i, j, k) in path:
        jp = ls[i][0]; label = ls[i][3]
        kr = ' '.join(dlg[j:j+k])
        out.write("%s\t%d\t%s\t%d\t%s\t%s\t%d\t%d\t%d\n" %
                  (nm, i, label, len(jp), jp.replace('\t', ' '), kr.replace('\t', ' '), j, j+k, k))
        ntot += 1
        if kr.strip(): nkr += 1
out.close()
print("aligned lines=%d  withKR=%d -> align_lines.tsv" % (ntot, nkr))
