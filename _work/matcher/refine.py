"""refine.py — 후보창 재채점(엄격 그룹 스코어) -> 전역 배정 -> 줄 단위 매핑
입력: cand_all.tsv (matcher6 후보)   출력: align_final.tsv, align_lines.tsv, refine.log
파싱/DP는 align_lines.py 앞부분을 재사용(엄격 그룹 스코어).
"""
import io, os, collections

OUTD = os.path.dirname(os.path.abspath(__file__))
AL = os.path.join(OUTD, 'align_lines.py')
src = open(AL, encoding='utf-8').read().split("# read align_final")[0]
g = {'__name__': 'al', '__file__': AL}
exec(compile(src, AL, 'exec'), g)
dp_path = g['dp_path']; SCPB = g['SCPB']; feat = g['feat']; dlg = g['dlg']; W = g['W']

PREF_BONUS = {'Y': 12.0, '-': 0.0, 'N': -3.0}
HIT_W = 1.5
OVERLAP_FRAC = 0.30

rows = collections.defaultdict(list)
with io.open(os.path.join(OUTD, 'cand_all.tsv'), encoding='utf-8') as f:
    f.readline()
    for line in f:
        p = line.rstrip('\n').split('\t')
        if len(p) < 8: continue
        blk, N, s, e, sc, hits, pre, ag = p[0], int(p[1]), int(p[2]), int(p[3]), float(p[4]), int(p[5]), p[6], p[7]
        rows[blk].append((s, e, sc, hits, pre, ag))

best_path = {}
allc = []
for blk, cands in rows.items():
    ls = SCPB.get(blk)
    if not ls: continue
    FEAT = [feat(t) for t, _, _, _ in ls]
    TCLS = [c for _, c, _, _ in ls]
    TNAM = [m for _, _, m, _ in ls]
    for i, (s, e, sc, hits, pre, ag) in enumerate(cands):
        r = dp_path(FEAT, TCLS, TNAM, s)
        if not r: continue
        path, score = r
        eff = score + PREF_BONUS.get(ag, 0.0) + HIT_W*hits
        allc.append((eff, i, blk, s, e, score, hits, pre, ag, path))

allc.sort(key=lambda a: (-a[0], a[1]))
assigned = {}
placed = []
def overlaps(s, e, s2, e2):
    ov = min(e, e2) - max(s, s2)
    return ov / max(1, min(e-s, e2-s2)) if ov > 0 else 0.0
for eff, i, blk, s, e, score, hits, pre, ag, path in allc:
    if blk in assigned: continue
    if any(overlaps(s, e, s2, e2) > OVERLAP_FRAC for (s2, e2, _) in placed): continue
    assigned[blk] = (eff, i, s, e, score, hits, pre, ag, path)
    placed.append((s, e, blk))
forced = 0
for blk, cands in rows.items():
    if blk not in assigned and blk in SCPB:
        for (eff, i, b2, s, e, score, hits, pre, ag, path) in allc:
            if b2 == blk:
                assigned[blk] = (eff, i, s, e, score, hits, pre, ag, path); forced += 1; break

LOG = io.open(os.path.join(OUTD, 'refine.log'), 'w', encoding='utf-8')
def log(x=''): LOG.write(x+'\n')
log("blocks=%d assigned=%d forced=%d" % (len(rows), len(assigned)-forced, forced))
ag = collections.Counter(v[7] for v in assigned.values())
log("prefix agreement: %s  Y/(Y+N)=%.1f%%" % (dict(ag), 100.0*ag['Y']/max(1, ag['Y']+ag['N'])))
pp = collections.defaultdict(collections.Counter)
for blk, v in assigned.items(): pp[blk[0]][v[7]] += 1
for k in sorted(pp): log("   %s: %s" % (k, dict(pp[k])))

FIN = io.open(os.path.join(OUTD, 'align_final.tsv'), 'w', encoding='utf-8')
FIN.write("block\tlines\tstart\tend\tscore\teff\thits\tprefix\tagree\trank\n")
for blk in sorted(assigned, key=lambda b: (b[0], int(b.split('_ms')[1]))):
    v = assigned[blk]; ls = SCPB[blk]
    FIN.write("%s\t%d\t%d\t%d\t%.1f\t%.1f\t%d\t%s\t%s\t%s\n" %
              (blk, len(ls), v[2], v[3], v[4], v[0], v[5], v[6], v[7], v[1]))
FIN.close()

lines = io.open(os.path.join(OUTD, 'align_lines.tsv'), 'w', encoding='utf-8')
lines.write("block\tidx\tlabel\tchars\tjp\tkr\ta_start\ta_end\tn_consumed\n")
ntot = 0
for blk, v in assigned.items():
    ls = SCPB[blk]; path = v[8]
    for (i, j, k) in path:
        jp = ls[i][0]
        lines.write("%s\t%d\t%s\t%d\t%s\t%s\t%d\t%d\t%d\n" %
                    (blk, i, ls[i][3], len(jp), jp.replace('\t', ' '),
                     ' '.join(dlg[j:j+k]).replace('\t', ' '), j, j+k, k))
        ntot += 1
lines.close()
log("line mappings=%d" % ntot)
LOG.close()
print(io.open(os.path.join(OUTD, 'refine.log'), encoding='utf-8').read())
