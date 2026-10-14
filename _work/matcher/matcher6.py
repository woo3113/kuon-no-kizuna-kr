"""matcher6.py — 전 327 SCP 블록 자동 정렬 (v2: numpy 구조상관 후보 + 앵커 후보 + 가산 DP)

후보 생성:  (a) numpy 교차상관(인용/줄끝/길이버킷) 전역 상위,  (b) 공유 에셋명 앵커
정렬:       가산형 1:N DP (텍스트 + 명령 클래스 + 에셋명 앵커)
출력:       align_all.tsv, matcher6.log
"""
import struct, re, os, io, math, time, sys, bisect
import numpy as np
from collections import defaultdict

PROJ = r'F:\TeraBoxDownload\구원의반'
SCP  = PROJ + r'\_work\psp_work\usrdir\PSP_GAME\USRDIR\SCRIPT.SCP'
BASE = PROJ + r'\_work\apk\assets\bin\Data'
OUTD = os.path.dirname(os.path.abspath(__file__))
LOG  = io.open(os.path.join(OUTD, 'matcher6.log'), 'w', encoding='utf-8')
TSV  = io.open(os.path.join(OUTD, 'align_all.tsv'), 'w', encoding='utf-8')
CAND = io.open(os.path.join(OUTD, 'cand_all.tsv'), 'w', encoding='utf-8')
def log(s=''):
    LOG.write(s + '\n'); LOG.flush()
t0 = time.time()

# ================= SCP =================
dd = bytes(b ^ 0xFF for b in open(SCP, 'rb').read())
cnt = struct.unpack_from('<I', dd, 0)[0]; D0 = 4 + cnt * 24
blocks = [(dd[4+i*24:4+i*24+16].split(b'\x00')[0].decode('ascii', 'replace'),
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
            res.append((''.join(buf), c, nm)); carry = []
        else:
            carry += tags
    return res
scp_blocks = [(n, read_scp_block(off, size)) for n, off, size in blocks]
log("SCP blocks=%d text-lines=%d (%.1fs)" % (len(scp_blocks), sum(len(l) for _, l in scp_blocks), time.time()-t0))

# ================= Android stream =================
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
    def add(n):
        if n: names[n] = names.get(n, 0) + 1
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
    cs, nm = and_extract(b''.join(pend))
    dcls[last] |= cs
    for k, v in nm.items(): dnames[last][k] = dnames[last].get(k, 0) + v
    pend = []
for raw in recs:
    try: t = raw.decode('utf-8')
    except UnicodeDecodeError: t = None
    if t is not None and is_dialogue(t):
        flush(); dlg.append(t); dcls.append(set()); dnames.append({}); last = len(dlg) - 1
    else: pend.append(raw)
flush()
W = len(dlg)
log("Android stream=%d (%.1fs)" % (W, time.time()-t0))

NAME2IDX = defaultdict(list); 
for x in range(W):
    for k in dnames[x]: NAME2IDX[k].append(x)
DF = {k: len(v) for k, v in NAME2IDX.items()}
log("distinct android names=%d" % len(DF))

# ---- numpy feature arrays ----
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
qA = np.array([f[0] for f in FD], dtype=np.int64)
eA = np.array([f[1] for f in FD], dtype=np.int64)
lA = np.array([f[2] for f in FD], dtype=np.int64)
bA = np.clip(lA // 8, 0, 5).astype(np.int64)

def struct_corr(tq, te, tb):
    N = len(tq); M = W - N + 1
    if M <= 0: return np.zeros(0)
    S = np.zeros(M)
    for v, wgt in ((0, 4.0), (1, 4.0)):
        u = (tq == v).astype(np.float64)
        if u.any(): S += wgt * np.correlate((qA == v).astype(np.float64), u, 'valid')
    for v in range(5):
        u = (te == v).astype(np.float64)
        if u.any(): S += 2.0 * np.correlate((eA == v).astype(np.float64), u, 'valid')
    for v in range(6):
        u = (tb == v).astype(np.float64)
        if u.any(): S += 1.0 * np.correlate((bA == v).astype(np.float64), u, 'valid')
    return S

CLASSES = ('SE', 'BGM', 'BG', 'FX', 'SHAKE')
# class next-occurrence arrays: NEXTC[c][j] = first index >= j having class c (else W)
NEXTC = {}
for c in CLASSES:
    arr = [W] * (W + 1)
    for x in range(W - 1, -1, -1):
        arr[x] = x if c in dcls[x] else arr[x + 1]
    NEXTC[c] = arr

def dp_best(FEAT, TCLS, TNAM, w0, maxk=4):
    """1:N DP, matcher5와 동일한 union(묶음) 스코어를 O(1)/O(log)로 계산"""
    N = len(FEAT); best = None
    states = {(0, w0): 0.0}
    _dcls = dcls; _dnames = dnames; _FD = FD; _PL = PL
    _NEXTC = NEXTC; _N2I = NAME2IDX
    for i in range(N):
        tq, te, tl = FEAT[i]; ts = TCLS[i]; tn = TNAM[i]
        tn_items = list(tn.items())
        nxt = {}
        for (ii, j), sc in states.items():
            if ii != i: continue
            for k in range(1, maxk + 1):
                if j + k > W: break
                a = j - 1 if j > 0 else 0
                b = j + k + 1 if j + k < W else W          # neighbour slack(=matcher5)
                cv = 0.0
                for c in CLASSES:
                    it = c in ts
                    ia = _NEXTC[c][a] < b
                    if it and ia: cv += 2.0
                    elif it != ia: cv -= 0.5
                nv = 0.0
                for kk, vv in tn_items:
                    lst = _N2I.get(kk)
                    if lst:
                        cnt = bisect.bisect_left(lst, b) - bisect.bisect_left(lst, a)
                        if cnt: nv += 4.0 * (vv if vv < cnt else cnt)
                lens = _PL[j+k] - _PL[j]
                s = sc + (4 if _FD[j][0] == tq else -3) + (3 if _FD[j][1] == te else -1)
                r = tl / (lens if lens else 1)
                s += 3 if 0.65 <= r <= 1.7 else (1 if 0.5 <= r <= 2.0 else -4)
                s += -0.4 * (k - 1) + cv + nv
                key = (i+1, j+k)
                if nxt.get(key, -1e18) < s: nxt[key] = s
                if i+1 == N and (best is None or s > best[0]): best = (s, w0, j+k)
        states = nxt
    return best

def prefix_of(name):
    m = re.match(r'([A-Za-z])_', name)
    return m.group(1).upper() if m else None

def anchor_candidates(allnames, span, K=30):
    votes = defaultdict(float)
    for nm, c in allnames.items():
        df = DF.get(nm, 0)
        if df == 0 or df > 400: continue
        wgt = 1.0 / df
        for x in NAME2IDX.get(nm, ()): votes[x] += wgt
    if not votes: return []
    arr = sorted(votes.items()); keys = [a for a, _ in arr]
    pref = [0.0]
    for _, v in arr: pref.append(pref[-1] + v)
    scored = []
    for x in keys:
        lo = bisect.bisect_left(keys, x - span); hi = bisect.bisect_right(keys, x)
        scored.append((pref[hi] - pref[lo], x))
    scored.sort(reverse=True)
    chosen = []
    for sc, x in scored:
        if all(abs(x - c) > span // 2 for c in chosen): chosen.append(x)
        if len(chosen) >= K: break
    return chosen

TSV.write("block\tlines\tstart\tend\tscore\tsecond\tanchor_hits\tprefix\n")
CAND.write("block\tlines\tstart\tend\tscore\thits\tprefix\tagree\n")
blocks = [(nm, ls) for nm, ls in scp_blocks if ls]
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else len(blocks)
blocks = blocks[:LIMIT]
log("aligning %d blocks ..." % len(blocks))
for bi, (nm, ls) in enumerate(blocks):
    FEAT = [feat(t) for t, _, _ in ls]
    TCLS = [c for _, c, _ in ls]
    TNAM = [m for _, _, m in ls]
    N = len(FEAT)
    allnames = {}
    for m in TNAM:
        for k, v in m.items(): allnames[k] = allnames.get(k, 0) + v
    span = max(8, int(N * 1.9) + 4)
    Kcap = 45 if N <= 80 else 25                # 대형 블록은 후보 축소(DP 비용 억제)
    cands = set()
    ac = anchor_candidates(allnames, span)
    for c in ac: cands.add(c)
    # structural correlation candidates
    tq = np.array([f[0] for f in FEAT]); te = np.array([f[1] for f in FEAT]); tb = np.array([f[2] // 8 for f in FEAT]).clip(0, 5)
    S = struct_corr(tq, te, tb)
    if len(S):
        order = np.argsort(S)[::-1]
        chosen = []
        for x in order:
            x = int(x)
            if all(abs(x - c) > span // 2 for c in chosen): chosen.append(x)
            if len(chosen) >= Kcap: break
        for c in chosen: cands.add(c)
    starts = set()
    for c in cands:
        for dx in (-1, 0, 1):
            s = c + dx
            if 0 <= s <= W - 4: starts.add(s)
    res = []
    for s in starts:
        b = dp_best(FEAT, TCLS, TNAM, s)
        if b: res.append(b)
    res.sort(reverse=True)
    if not res:
        TSV.write("%s\t%d\t-1\t-1\t0\t0\t0\t-\n" % (nm, N)); continue
    best = res[0]
    second = next((r[0] for r in res if r[1] != best[1]), 0.0)

    def stats(s0, e0):
        win = {}
        for x in range(s0, min(e0, W)):
            for k, v in dnames[x].items(): win[k] = win.get(k, 0) + v
        pf = defaultdict(int)
        for k, v in win.items():
            p = prefix_of(k)
            if p: pf[p] += v
        tp = max(pf.items(), key=lambda a: a[1])[0] if pf else '-'
        ht = sum(min(v, win.get(k, 0)) for k, v in allnames.items())
        return ht, tp

    hits, top_pref = stats(best[1], best[2])
    pfx = prefix_of(nm)
    agree = 'Y' if (top_pref == pfx and pfx) else ('-' if top_pref == '-' else 'N')
    TSV.write("%s\t%d\t%d\t%d\t%.1f\t%.1f\t%d\t%s:%s\n" % (nm, N, best[1], best[2], best[0], second, hits, top_pref, agree))
    TSV.flush()
    # top-K 서로 다른 창 후보 덤프 (전역 배정용)
    picked = []
    for r in res:
        if all(abs(r[1] - p[1]) > 8 for p in picked): picked.append(r)
        if len(picked) >= 12: break
    for r in picked:
        ht, tp = stats(r[1], r[2])
        ag = 'Y' if (tp == pfx and pfx) else ('-' if tp == '-' else 'N')
        CAND.write("%s\t%d\t%d\t%d\t%.1f\t%d\t%s\t%s\n" % (nm, N, r[1], r[2], r[0], ht, tp, ag))
    CAND.flush()
    if bi % 20 == 0 or bi == len(blocks) - 1:
        el = time.time() - t0
        log("  [%d/%d] %s N=%d start=%d score=%.1f hit=%d (%.0fs, eta %.0fs)" %
            (bi, len(blocks), nm, N, best[1], best[0], hits, el, el / max(1, bi + 1) * (len(blocks) - bi - 1)))
TSV.close()
CAND.close()
log("done total %.0fs" % (time.time() - t0))
LOG.close()
print("done")
