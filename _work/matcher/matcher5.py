"""matcher5.py — 구원의반 PSP↔Android 정렬 매처
matcher4(텍스트 특징) + 명령어(BG/SE/BGM/FADE) 시퀀스 + 공유 에셋명 앵커
"""
import struct, re, os, io

SCP = r'F:\TeraBoxDownload\구원의반\_work\psp_work\usrdir\PSP_GAME\USRDIR\SCRIPT.SCP'
base = r'F:\TeraBoxDownload\구원의반\_work\apk\assets\bin\Data'
OUT = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'matcher5_out.txt'), 'w', encoding='utf-8')
w = OUT.write

# ---------------- SCP ----------------
dd = bytes(b ^ 0xFF for b in open(SCP, 'rb').read())
cnt = struct.unpack_from('<I', dd, 0)[0]; D0 = 4 + cnt * 24
blocks = [(dd[4+i*24:4+i*24+16].split(b'\x00')[0].decode('ascii','replace'),
           *struct.unpack_from('<II', dd, 4+i*24+16)) for i in range(cnt)]

TAGRE = re.compile(r'<([A-Za-z0-9_]+)>([^\r<]*)')
ARG   = re.compile(r'<[^>]*>|[0-9A-Za-z_,\.\-]+')
CJK   = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\u2010-\u2030\u25a0-\u25ff]')

PSP_SE   = {'SE_LOAD', 'SE1', 'SE2', 'STOP_SE', 'SET_SE'}
PSP_BGM  = {'BGM', 'BGM_VOLUME', 'STOP_BGM'}
PSP_BG   = {'BG', 'CHANGE_BG', 'BG2', 'CLEAR_BG', 'SCROLLBG', 'MOVE_SCROLLBG',
            'CLEAR_SCROLLBG', 'BG_BRIGHT', 'CG_BRIGHT', 'CG_RGB',
            'BU0', 'BU1', 'BU2', 'BU1_OFS', 'BU2_OFS', 'CLEAR_BU0', 'CLEAR_BU1', 'CLEAR_BU2'}
PSP_FX   = {'FADE_SPEED', 'FLASH', 'WHITE_IN', 'WHITE_OUT', 'MASK', 'STOP_MASK', 'FLIP'}
PSP_WAIT = {'W1', 'W2'}
PSP_MSG  = {'MSG_IN', 'MSG_OUT', 'PAGE', 'SAVE', 'NAME'}
PSP_SHAKE = {'QUAKE', 'QUAKE2', 'SHOCK0', 'SHOCK1', 'STOP_SHOCK1'}

def psp_extract(tags):
    """tags: list of (name, arg). return (classes frozenset, names Counter-like dict)"""
    cls = set(); names = {}
    def add(n):
        if n and n not in ('-1', '0'): names[n] = names.get(n, 0) + 1
    for name, arg in tags:
        N = name.upper()
        if N in PSP_SE:
            cls.add('SE')
            m = re.match(r'\s*(\d+)', arg)
            if m: add('se%03d' % int(m.group(1)))
        elif N in PSP_BGM:
            cls.add('BGM')
            if N == 'STOP_BGM': add('bgm_stop')
            else:
                m = re.match(r'\s*(\d+)', arg)
                if m: add('bgm%02d' % int(m.group(1)))
        elif N in PSP_BG:
            cls.add('BG')
            if N in ('CLEAR_BG',): add('bg_clear')
            elif N in ('SCROLLBG', 'MOVE_SCROLLBG', 'CLEAR_SCROLLBG'): add('scrollbg')
            else:
                for p in arg.split(','):
                    p = p.strip()
                    if re.match(r'^[A-Za-z]{1,3}_[A-Za-z0-9]+', p): add(p)
        elif N in PSP_FX:
            cls.add('FX'); add('fade')
        elif N in PSP_WAIT:
            cls.add('WAIT')
        elif N in PSP_MSG:
            cls.add('MSG')
        elif N in PSP_SHAKE:
            cls.add('SHAKE')
        elif N == 'EV':
            for p in arg.split(','):
                p = p.strip()
                if re.match(r'^[A-Za-z]{1,3}_[A-Za-z0-9]+', p): add(p)
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
            txt2 = ''.join(buf)
            c, n = psp_extract(carry + tags)
            res.append((txt2, c, n)); carry = []
        else:
            carry += tags
    return res

scp_blocks = [(n, read_scp_block(off, size)) for n, off, size in blocks]

# ---------------- Android event stream ----------------
parts_ = sorted([f for f in os.listdir(base) if f.startswith('level4.split')],
                key=lambda s: int(s.rsplit('split', 1)[1]))
d = b''.join(open(os.path.join(base, f), 'rb').read() for f in parts_)
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
    def add(n):
        if n: names[n] = names.get(n, 0) + 1
    for m in TOK.finditer(raw):
        s = m.group().decode('ascii')
        if AND_SE.match(s):
            cls.add('SE'); add('se%03d' % int(re.search(r'\d+', s).group()))
        elif AND_BGM.match(s):
            cls.add('BGM'); add('bgm%02d' % int(re.search(r'\d+', s).group()))
        elif AND_SCENE.match(s):
            cls.add('SCENE'); add(s)
        elif AND_EV.match(s):
            cls.add('EV'); add(s)
        elif AND_FX.match(s):
            cls.add('FX')
        elif s in AND_SHAKE:
            cls.add('SHAKE')
        elif AND_BG.match(s):
            cls.add('BG'); add(s)
    return frozenset(cls), names

# Android command records physically FOLLOW the dialogue record they belong to,
# so attach a command run to the PREVIOUS dialogue line (trailing convention).
dlg = []; dcls = []; dnames = []
pend_recs = []; last = -1
def flush():
    global pend_recs
    if last < 0 or not pend_recs:
        pend_recs = []; return
    cs, nm = and_extract(b''.join(pend_recs))
    dcls[last] |= cs
    for k, v in nm.items(): dnames[last][k] = dnames[last].get(k, 0) + v
    pend_recs = []
for raw in recs:
    try: t = raw.decode('utf-8')
    except UnicodeDecodeError: t = None
    if t is not None and is_dialogue(t):
        flush()
        dlg.append(t); dcls.append(set()); dnames.append({}); last = len(dlg) - 1
    else:
        pend_recs.append(raw)
flush()

# ---------------- text features (matcher4) ----------------
def endcls(t):
    s = t.rstrip()
    if s.endswith('」') or s.endswith('』') or s.endswith('"'): return 0
    if s.endswith('…') or s.endswith('.'): return 1
    if s.endswith('。'): return 2
    if s.endswith('！') or s.endswith('!') or s.endswith('？') or s.endswith('?'): return 3
    return 4
def feat(t):
    return (1 if t[:1] in '「"『' else 0, endcls(t), len(t))

TCLS = [c for _, c, _ in scp_blocks[0][1]]
TNAM = [nm for _, _, nm in scp_blocks[0][1]]
FEAT = [feat(t) for t, _, _ in scp_blocks[0][1]]
FD = [feat(t) for t in dlg]
N = len(FEAT)

ALLC = ('SE', 'BGM', 'BG', 'FX', 'SHAKE', 'SCENE', 'EV')

def cmd_bonus(tset, tnames, j, k):
    aset = set()
    for x in range(j, j + k):
        aset |= dcls[x]
    # neighbour slack of 1 line on both sides (command offset tolerance)
    if j - 1 >= 0: aset |= dcls[j-1]
    if j + k < len(dcls): aset |= dcls[j+k]
    sc = 0.0
    for c in ('SE', 'BGM', 'BG', 'FX', 'SHAKE'):
        in_t = c in tset; in_a = c in aset
        if in_t and in_a: sc += 2.0
        elif in_t != in_a: sc -= 0.5
    # literal name anchors (shared asset names / seNNN / bgmNN)
    anames = {}
    for x in range(j, j + k):
        for kk, vv in dnames[x].items(): anames[kk] = anames.get(kk, 0) + vv
    hits = []
    for kk, vv in tnames.items():
        if kk in anames:
            sc += 4.0 * min(vv, anames[kk]); hits.append(kk)
    return sc, hits

def align_from(w0, maxk=4):
    INF = -10**9
    states = {(0, w0): 0.0}; best = None
    for i in range(N):
        tq, te, tl = FEAT[i]; tc = TCLS[i]; tn = TNAM[i]
        nxt = {}
        for (ii, j), sc in states.items():
            if ii != i: continue
            for k in range(1, maxk + 1):
                if j + k > len(dlg): break
                lens = sum(FD[x][2] for x in range(j, j + k)); q = FD[j][0]; e = FD[j][1]
                s = sc + (4 if q == tq else -3) + (3 if e == te else -1)
                r = tl / max(1, lens)
                s += 3 if 0.65 <= r <= 1.7 else (1 if 0.5 <= r <= 2.0 else -4)
                s += -0.4 * (k - 1)                      # expansion penalty
                cb, _ = cmd_bonus(tc, tn, j, k)
                s += cb
                key = (i + 1, j + k)
                if nxt.get(key, INF) < s: nxt[key] = s
                if i + 1 == N and (best is None or s > best[0]):
                    best = (s, w0, j + k)
        states = nxt
    return best

res = []
for w0 in range(0, len(dlg) - 3):
    b = align_from(w0)
    if b: res.append(b)
res.sort(reverse=True)
w("block %s lines=%d  android stream=%d  windows=%d\n" % (scp_blocks[0][0], N, len(dlg), len(res)))
w("top 8 (score,start,end):\n")
for sc, s, e in res[:8]:
    w("   %8.1f  %6d..%6d\n" % (sc, s, e))

# rank of true window: prologue start (dialog right after '춥다' == '寒い')
tru = [i for i in range(8000, 12000) if dlg[i].startswith('춥다')]
w("\ntrue-start candidates(8000..12000) idx: %s\n" % tru[:6])
tru_start = tru[0] if tru else 10303
pos = next((k + 1 for k, r in enumerate(res) if abs(r[1] - tru_start) <= 3), None)
w("TARGET window start=%d  ->  RANK = %s / %d\n" % (tru_start, pos, len(res)))

def show(title, sc, s, e):
    w("\n--- %s (score %.1f, %d..%d) ---\n" % (title, sc, s, e))
    for k in range(s, min(e, s + 14)):
        w("   %6d [%-16s] %s\n" % (k, ''.join(sorted(dcls[k])), dlg[k][:56]))
    alln = {}
    for x in range(s, min(e, len(dcls))):
        for kk, vv in dnames[x].items(): alln[kk] = alln.get(kk, 0) + vv
    w("   window names: %s\n" % sorted(alln.items(), key=lambda a: -a[1])[:14])

show("TOP1", *res[0])
truwin = [r for r in res if abs(r[1] - tru_start) <= 3]
if truwin:
    show("TRUE", *max(truwin))
alln = {}
for nm in TNAM:
    for kk, vv in nm.items(): alln[kk] = alln.get(kk, 0) + vv
w("\nPSP G_ms01 names: %s\n" % sorted(alln.items()))
w("PSP G_ms01 classes: %s\n" % sorted(set().union(*TCLS)))
OUT.close()
print("done")
