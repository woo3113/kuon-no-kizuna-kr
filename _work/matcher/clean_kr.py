"""clean_kr.py — 기존(dirty) 번역 재사용 + 태그인자 잔여 숫자만 정확히 제거
- JP 전각숫자→반각 정규화 후 '숫자런' 멀티셋 비교
- KR의 숫자런 중 JP(new)에 없는 것만 제거 (정상 숫자 15년/2학년 등은 보존)
추가 API 비용 0. 출력: kr_psp.tsv
"""
import io, os, re, json, collections

OUTD = os.path.dirname(os.path.abspath(__file__))
FW = str.maketrans('０１２３４５６７８９', '0123456789')
def runs(s): return [(m.group(), m.start(), m.end()) for m in re.finditer(r'[0-9]+', s)]

def load_tsv(p):
    d = {}
    for l in io.open(p, encoding='utf-8').read().split('\n')[1:]:
        if not l: continue
        c = l.split('\t')
        if len(c) >= 6: d[(c[0], c[1])] = c[4]
    return d
def load_cache(p):
    d = {}
    for l in io.open(p, encoding='utf-8'):
        try:
            o = json.loads(l); d[(o['b'], str(o['i']))] = o['kr']
        except Exception: pass
    return d

newjp = load_tsv(os.path.join(OUTD, 'psp_lines.tsv'))
kr = load_cache(os.path.join(OUTD, 'kr_psp_cache_dirty.jsonl'))
ref = {}
for l in io.open(os.path.join(OUTD, 'align_lines.tsv'), encoding='utf-8').read().split('\n')[1:]:
    if not l: continue
    c = l.split('\t')
    if len(c) >= 6: ref[(c[0], c[1])] = c[5]

removed = kept = line_fixed = 0
rows = []
for k in newjp:
    jp = newjp[k]
    dirty = kr.get(k, '')
    jpc = collections.Counter(t for t, _, _ in runs(jp.translate(FW)))
    res = dirty
    toks = runs(dirty)
    for tok, s, e in reversed(toks):
        if jpc.get(tok, 0) > 0:
            jpc[tok] -= 1; kept += 1
        else:
            res = res[:s] + res[e:]; removed += 1
    if res != dirty: line_fixed += 1
    rows.append((k[0], k[1], jp, res, ref.get(k, '')))

with io.open(os.path.join(OUTD, 'kr_psp.tsv'), 'w', encoding='utf-8') as o:
    o.write("block\tidx\tjp\tkr\tref\n")
    for b, i, jp, kk, rf in rows:
        o.write("%s\t%s\t%s\t%s\t%s\n" % (b, i, jp.replace('\t',' '), kk.replace('\t',' '), rf.replace('\t',' ')))

still = sum(1 for r in rows if re.search(r'[0-9]', r[3]))
LOG = io.open(os.path.join(OUTD, 'clean.log'), 'w', encoding='utf-8')
LOG.write("lines=%d  digit-runs kept=%d removed=%d  lines-fixed=%d  still-has-digit=%d\n"
          % (len(rows), kept, removed, line_fixed, still))
LOG.close()
print(io.open(os.path.join(OUTD, 'clean.log'), encoding='utf-8').read())
