"""align_report.py — align_all.tsv 요약/품질 리포트"""
import io, os, sys, collections
OUTD = os.path.dirname(os.path.abspath(__file__))
TSV = os.path.join(OUTD, 'align_all.tsv')
pfx = collections.Counter(); agree = collections.Counter()
rows = []
with io.open(TSV, encoding='utf-8') as f:
    hdr = f.readline()
    for line in f:
        p = line.rstrip('\n').split('\t')
        if len(p) < 8: continue
        blk, n, s, e, sc, sec, hits, pre = p[0], int(p[1]), int(p[2]), int(p[3]), float(p[4]), float(p[5]), int(p[6]), p[7]
        tp, ag = pre.split(':')
        rows.append((blk, n, s, e, sc, sec, hits, tp, ag))
print("blocks aligned:", len(rows))
for r in rows: pfx[r[0][0].upper()] += 1
print("per prefix:", dict(sorted(pfx.items())))
ag = collections.Counter(r[8] for r in rows)
print("prefix agreement:", dict(ag), " -> rate Y/(Y+N) = %.1f%%" %
      (100.0*ag['Y']/max(1, ag['Y']+ag['N'])))
agp = collections.defaultdict(collections.Counter)
for r in rows: agp[r[0][0].upper()][r[8]] += 1
print("agreement per prefix:")
for k in sorted(agp): print("   %s: %s" % (k, dict(agp[k])))
marg = [r[4]-r[5] for r in rows]
marg.sort()
def pct(a, q): return a[min(len(a)-1, int(q*len(a)))]
print("score margin (best-2nd): min=%.1f  p25=%.1f  median=%.1f  p75=%.1f  max=%.1f" %
      (marg[0], pct(marg,.25), pct(marg,.5), pct(marg,.75), marg[-1]))
amb = [r for r in rows if r[4]-r[5] < 5.0]
print("ambiguous (margin<5): %d / %d" % (len(amb), len(rows)))
print("no anchor hits (0):", sum(1 for r in rows if r[6] == 0))
print("low anchor hits (<=1):", sum(1 for r in rows if r[6] <= 1))
print()
print("worst 15 (lowest anchor hits):")
for r in sorted(rows, key=lambda a: a[6])[:15]:
    print("   %-10s N=%-3d %6d..%-6d score=%-7.1f hit=%-3d %s:%s" % (r[0], r[1], r[2], r[3], r[4], r[6], r[7], r[8]))
print()
# duplicate/overlap detection: windows re-used across blocks
occ = collections.defaultdict(list)
for r in rows:
    for x in range(r[2], r[3], 20):
        occ[x//20].append(r[0])
dupe = {k: v for k, v in occ.items() if len(set(v)) > 2}
print("heavy window sharing (>=3 blocks): %d cells" % len(dupe))
for k in sorted(dupe)[:10]:
    print("   bin %d: %s" % (k, sorted(set(dupe[k]))))
