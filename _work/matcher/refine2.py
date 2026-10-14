"""refine2.py — 후보 재생성(오프셋 투표, 1:N 인식) -> 엄격 DP 재채점 -> 전역 배정 -> 줄 매핑
파싱/DP는 align_lines.py 앞부분 재사용.
출력: align_final.tsv, align_lines.tsv, refine2.log
"""
import io, os, collections

OUTD = os.path.dirname(os.path.abspath(__file__))
AL = os.path.join(OUTD, 'align_lines.py')
src = open(AL, encoding='utf-8').read().split("# read align_final")[0]
g = {'__name__': 'al', '__file__': AL}
exec(compile(src, AL, 'exec'), g)
dp_path = g['dp_path']; SCPB = g['SCPB']; feat = g['feat']; dlg = g['dlg']; W = g['W']
NAME2IDX = g['NAME2IDX']; dnames = g['dnames']
DF = {k: len(v) for k, v in NAME2IDX.items()}

PREF_BONUS = {'Y': 12.0, '-': 0.0, 'N': -3.0}
HIT_W = 1.5
OVERLAP_FRAC = 0.30
PREF_OF = g['prefix_of'] if 'prefix_of' in g else None
import re as _re
def prefix_of(name):
    m = _re.match(r'([A-Za-z])_', name)
    return m.group(1).upper() if m else None

def make_candidates(TNAM, N, K=60):
    """앵커 위치 a, 타깃 줄 i -> start = a - i 오프셋 투표"""
    votes = collections.defaultdict(float)
    for i, names in enumerate(TNAM):
        for nm, c in names.items():
            df = DF.get(nm, 0)
            if df == 0 or df > 200: continue
            wv = 1.0/df
            for a in NAME2IDX.get(nm, ()): votes[a - i] += wv
    if not votes:
        return list(range(0, max(1, W - 4), 64))
    order = sorted(votes.items(), key=lambda a: -a[1])
    chosen = []
    for s, v in order:
        s = max(0, min(W - 4, s))
        if all(abs(s - c) > 3 for c in chosen): chosen.append(s)
        if len(chosen) >= K: break
    return chosen

def stats_of(path):
    a0 = path[0][1]; a1 = path[-1][1] + path[-1][2]
    win = {}
    for x in range(a0, min(a1, W)):
        for kk, vv in dnames[x].items(): win[kk] = win.get(kk, 0) + vv
    return a0, a1, win

LOG = io.open(os.path.join(OUTD, 'refine2.log'), 'w', encoding='utf-8')
def log(x=''): LOG.write(x+'\n')

allc = []
for blk, ls in SCPB.items():
    FEAT = [feat(t) for t, _, _, _ in ls]
    TCLS = [c for _, c, _, _ in ls]
    TNAM = [m for _, _, m, _ in ls]
    N = len(FEAT)
    allnames = {}
    for m in TNAM:
        for kk, vv in m.items(): allnames[kk] = allnames.get(kk, 0) + vv
    pfx = prefix_of(blk)
    cands = set()
    for s in make_candidates(TNAM, N):
        for d in (-2, -1, 0, 1, 2):
            s2 = s + d
            if 0 <= s2 <= W - 4: cands.add(s2)
    seen = set()
    got = []
    for s in sorted(cands):
        r = dp_path(FEAT, TCLS, TNAM, s)
        if not r: continue
        path, score = r
        a0, a1, win = stats_of(path)
        pf = collections.defaultdict(int)
        for kk, vv in win.items():
            p = prefix_of(kk)
            if p: pf[p] += vv
        tp = max(pf.items(), key=lambda a: a[1])[0] if pf else '-'
        ag = 'Y' if (tp == pfx and pfx) else ('-' if tp == '-' else 'N')
        hits = sum(min(vv, win.get(kk, 0)) for kk, vv in allnames.items())
        eff = score + PREF_BONUS[ag] + HIT_W*hits
        got.append((eff, s, a0, a1, score, hits, tp, ag, path))
    got.sort(reverse=True)
    allc.extend([(x[0], i, blk, x) for i, x in enumerate(got)])

allc.sort(key=lambda a: (-a[0], a[1]))
assigned = {}
placed = []
def overlaps(s, e, s2, e2):
    ov = min(e, e2) - max(s, s2)
    return ov/max(1, min(e-s, e2-s2)) if ov > 0 else 0.0
for eff, i, blk, x in allc:
    if blk in assigned: continue
    if any(overlaps(x[2], x[3], s2, e2) > OVERLAP_FRAC for (s2, e2, _) in placed): continue
    assigned[blk] = x
    placed.append((x[2], x[3], blk))
forced = 0
for eff, i, blk, x in allc:
    if blk not in assigned:
        assigned[blk] = x; forced += 1
log("blocks=%d assigned=%d forced=%d" % (len(SCPB), len(assigned)-forced, forced))
ag = collections.Counter(v[7] for v in assigned.values())
log("prefix agreement: %s  Y/(Y+N)=%.1f%%" % (dict(ag), 100.0*ag['Y']/max(1, ag['Y']+ag['N'])))
pp = collections.defaultdict(collections.Counter)
for blk, v in assigned.items(): pp[blk[0]][v[7]] += 1
for k in sorted(pp): log("   %s: %s" % (k, dict(pp[k])))

FIN = io.open(os.path.join(OUTD, 'align_final.tsv'), 'w', encoding='utf-8')
FIN.write("block\tlines\tstart\tend\tscore\teff\thits\tprefix\tagree\trank\n")
for blk in sorted(assigned, key=lambda b: (b[0], int(b.split('_ms')[1]))):
    x = assigned[blk]; ls = SCPB[blk]
    FIN.write("%s\t%d\t%d\t%d\t%.1f\t%.1f\t%d\t%s\t%s\t%s\n" %
              (blk, len(ls), x[2], x[3], x[4], x[0], x[5], x[6], x[7], x[1]))
FIN.close()

lines = io.open(os.path.join(OUTD, 'align_lines.tsv'), 'w', encoding='utf-8')
lines.write("block\tidx\tlabel\tchars\tjp\tkr\ta_start\ta_end\tn_consumed\n")
ntot = 0
for blk, x in assigned.items():
    ls = SCPB[blk]
    for (i, j, k) in x[8]:
        jp = ls[i][0]
        lines.write("%s\t%d\t%s\t%d\t%s\t%s\t%d\t%d\t%d\n" %
                    (blk, i, ls[i][3], len(jp), jp.replace('\t',' '),
                     ' '.join(dlg[j:j+k]).replace('\t',' '), j, j+k, k))
        ntot += 1
lines.close()
log("line mappings=%d" % ntot)
LOG.close()
print(io.open(os.path.join(OUTD, 'refine2.log'), encoding='utf-8').read())
