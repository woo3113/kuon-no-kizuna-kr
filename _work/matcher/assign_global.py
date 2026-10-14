"""assign_global.py — 후보 창 전역 배정
cand_all.tsv(블록별 상위 창 후보) → 블록마다 서로 겹치지 않는 창 하나 배정
점수 = raw + prefix보너스 + 앵커적중 보너스  (탐욕 배정, 겹침 금지)
출력: align_final.tsv, assign.log
"""
import io, os, collections

OUTD = os.path.dirname(os.path.abspath(__file__))
PREF_BONUS = {'Y': 12.0, '-': 0.0, 'N': -3.0}
HIT_W = 1.5
OVERLAP_FRAC = 0.30

rows = []   # (block, N, start, end, score, hits, prefix, agree)
with io.open(os.path.join(OUTD, 'cand_all.tsv'), encoding='utf-8') as f:
    f.readline()
    for line in f:
        p = line.rstrip('\n').split('\t')
        if len(p) < 8: continue
        rows.append((p[0], int(p[1]), int(p[2]), int(p[3]), float(p[4]),
                     int(p[5]), p[6], p[7]))

byblock = collections.defaultdict(list)
for r in rows:
    eff = r[4] + PREF_BONUS.get(r[7], 0.0) + HIT_W * r[5]
    byblock[r[0]].append((eff, r))

allc = []
for blk, lst in byblock.items():
    for i, (eff, r) in enumerate(sorted(lst, key=lambda a: -a[0])):
        allc.append((eff, i, blk, r))
allc.sort(key=lambda a: (-a[0], a[1]))

assigned = {}
placed = []   # (start, end, block)

def overlaps(s, e, s2, e2):
    ov = min(e, e2) - max(s, s2)
    if ov <= 0: return 0.0
    return ov / max(1, min(e - s, e2 - s2))

for eff, rank, blk, r in allc:
    if blk in assigned: continue
    bad = False
    for (s2, e2, b2) in placed:
        if overlaps(r[2], r[3], s2, e2) > OVERLAP_FRAC:
            bad = True; break
    if bad: continue
    assigned[blk] = (r, eff, rank)
    placed.append((r[2], r[3], blk))

forced = 0
for blk, lst in byblock.items():
    if blk not in assigned:
        eff, r = max(lst, key=lambda a: a[0])
        assigned[blk] = (r, eff, 99); forced += 1

LOG = io.open(os.path.join(OUTD, 'assign.log'), 'w', encoding='utf-8')
def log(s=''): LOG.write(s + '\n')

FIN = io.open(os.path.join(OUTD, 'align_final.tsv'), 'w', encoding='utf-8')
FIN.write("block\tlines\tstart\tend\tscore\teff\thits\tprefix\tagree\trank\n")
ag = collections.Counter(); ranks = collections.Counter()
for blk in sorted(assigned, key=lambda b: (b[0], int(b.split('_ms')[1]))):
    r, eff, rank = assigned[blk]
    FIN.write("%s\t%d\t%d\t%d\t%.1f\t%.1f\t%d\t%s\t%s\t%s\n" %
              (blk, r[1], r[2], r[3], r[4], eff, r[5], r[6], r[7], rank))
    ag[r[7]] += 1; ranks[rank] += 1
FIN.close()
log("blocks=%d  assigned(no-overlap)=%d  forced=%d" % (len(byblock), len(assigned) - forced, forced))
log("prefix agreement: %s  Y/(Y+N)=%.1f%%" % (dict(ag), 100.0 * ag['Y'] / max(1, ag['Y'] + ag['N'])))
log("candidate rank used: %s" % dict(sorted(ranks.items())))
# per-prefix
pp = collections.defaultdict(collections.Counter)
for blk, (r, eff, rank) in assigned.items(): pp[blk[0]][r[7]] += 1
for k in sorted(pp): log("   %s: %s" % (k, dict(pp[k])))
LOG.close()
print(io.open(os.path.join(OUTD, 'assign.log'), encoding='utf-8').read())
