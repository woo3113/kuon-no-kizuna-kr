import json, io, re
P = r'C:\Users\woo31\AppData\Local\Temp\opencode'
out = io.open(P + r'\_probe_fo.txt','w',encoding='utf-8')
w = out.write
d = json.load(open(P+r'\android_lines_fileorder.json', encoding='utf-8'))
w("fileorder type=%s len=%d\n" % (type(d).__name__, len(d)))
for i in range(0, 60):
    w("%5d %r\n" % (i, d[i] if i < len(d) else None))
# classify tokens
HAN = re.compile(r'[\uac00-\ud7a3]')
def has_han(s): return bool(HAN.search(s))
cmdtok = re.compile(r'^[0-9A-Za-z_]+$')
kinds = {}
for t in d:
    if not isinstance(t, str):
        k = 'nonstr'; kinds[k]=kinds.get(k,0)+1; continue
    if re.fullmatch(r'[0-9]{7}', t): k='id7'
    elif has_han(t): k='korean'
    elif cmdtok.match(t): k='ascii_token'
    else: k='other'
    kinds[k] = kinds.get(k,0)+1
w("\nkinds: %s\n" % kinds)
# ascii tokens counter
from collections import Counter
c = Counter(t for t in d if isinstance(t,str) and cmdtok.match(t) and not re.fullmatch(r'[0-9]{7}',t))
w("\ntop ascii tokens: %d distinct\n" % len(c))
for t,n in c.most_common(120):
    w("%6d %s\n" % (n,t))
out.close()
print("ok")
