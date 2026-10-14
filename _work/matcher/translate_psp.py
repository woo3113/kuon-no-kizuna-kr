"""translate_psp.py — PSP 대사 JP->KR 번역 (DeepSeek)
입력: psp_lines.tsv (block,idx,label,chars,jp,tags)
      align_lines.tsv (참고: 안드로이드 정식 번역, 있으면 '참고 번역'으로 제공)
출력: kr_psp.tsv (block,idx,jp,kr,ref) / kr_psp_cache.jsonl
고유명사: 안드로이드 정식 표기 우선(참고 번역 + 용어집)
"""
import os, re, json, time, urllib.request, urllib.error, argparse, io, struct
from collections import Counter

PROJ = r'F:\TeraBoxDownload\구원의반'
OUTD = os.path.dirname(os.path.abspath(__file__))
PSPLINES = os.path.join(OUTD, 'psp_lines.tsv')
ALIGN = os.path.join(OUTD, 'align_lines.tsv')
CACHE = os.path.join(OUTD, 'kr_psp_cache.jsonl')
OUT_TSV = os.path.join(OUTD, 'kr_psp.tsv')
KEYFILE = r'C:\Users\woo31\rezero-kr\work\deepseek_key.txt'
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

def get_key():
    k = os.environ.get("DEEPSEEK_API_KEY")
    if k: return k.strip()
    if os.path.exists(KEYFILE): return open(KEYFILE, encoding='utf-8').read().strip()
    raise SystemExit("DeepSeek 키 없음")

# ---- glossary: 안드로이드에서 화자명(짧은 순수 한글 레코드) 채굴 ----
def mine_names():
    base = PROJ + r'\_work\apk\assets\bin\Data'
    parts = sorted([f for f in os.listdir(base) if f.startswith('level4.split')],
                   key=lambda s: int(s.rsplit('split',1)[1]))
    d = b''.join(open(os.path.join(base,f),'rb').read() for f in parts)
    n=len(d); recs=[]; i=0
    while i+4<=n:
        ln=struct.unpack_from('<I',d,i)[0]
        if 1<=ln<=8192 and i+4+ln<=n:
            recs.append(d[i+4:i+4+ln]); i+=4+ln; i=(i+3)&~3; continue
        i+=4
    c = Counter()
    for raw in recs:
        try: t = raw.decode('utf-8')
        except UnicodeDecodeError: continue
        s = t.strip()
        if 2 <= len(s) <= 14 and re.fullmatch(r'[가-힣 ]+', s) and ' ' not in s[:0]:
            # 순수 한글, 조사/문장부호 없음 -> 화자명 후보
            if not re.search(r'(다|요|까|죠|네|서|며|고|면)$', s):
                c[s] += 1
    return [k for k,v in c.most_common(200) if v >= 2]

NAMES = mine_names()

SYSTEM = """당신은 PS1/PSP 게임 '구원의 반(久遠の絆) 재림조'의 한국어 전문 로컬라이징 번역가입니다.
일본어 원문을 한국 정식 발매판(안드로이드판) 스타일의 자연스러운 한국어로 옮깁니다.

[규칙]
1. 실제 한국 게임 문체로 자연스럽게. 번역투 금지.
2. 입력 각 줄은 "###n [JA] <일본어> [REF] <참고 한국어>" 형식입니다.
   [REF]는 같은 대사의 공식 한국어 번역일 수 있습니다.
   - REF가 원문(JA)과 의미가 일치하면 그 표현·고유명사 표기를 그대로 따르세요.
   - REF가 원문과 명백히 어긋나면(정렬 오류) 원문을 우선 번역하되, **고유명사 표기만** REF/용어집에서 가져오세요.
   - REF가 비어 있으면 JA를 직접 번역합니다.
3. 고유명사(인명·지명·용어)는 반드시 아래 [안드로이드 정식 표기] 목록/참고 번역의 표기를 따릅니다.
4. 서식/태그 토큰(예: <W1> <SE_LOAD> <PAGE> 등)은 절대 만들거나 바꾸지 말고, 원문에 있는 것만 위치 그대로 둡니다.
5. 출력은 입력과 같은 개수·순서로 "###n 번역문"만. 설명·주석 금지.

[안드로이드 정식 표기(인명/지명 후보)]
""" + ", ".join(NAMES)

def call(key, messages):
    body = json.dumps({"model": MODEL, "messages": messages, "temperature": 1.1, "stream": False}).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + key})
    for attempt in range(4):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=120).read().decode("utf-8"))
            return r["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            print("  HTTP", e.code, e.read().decode('utf-8','replace')[:160], flush=True)
            time.sleep(2 + attempt*2)
        except Exception as e:
            print("  err", e, flush=True); time.sleep(2 + attempt*2)
    return None

def parse(out, n):
    res = {}
    for line in out.split("\n"):
        m = re.match(r'^###\s*(\d+)\s*(.*)$', line.strip())
        if m: res[int(m.group(1))] = m.group(2).strip()
    return [res.get(i+1, "") for i in range(n)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)      # 배치 수 제한(테스트)
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    key = get_key()

    refs = {}
    if os.path.exists(ALIGN):
        with io.open(ALIGN, encoding='utf-8') as f:
            f.readline()
            for line in f:
                p = line.rstrip('\n').split('\t')
                if len(p) >= 6: refs[(p[0], int(p[1]))] = p[5]
    rows = []
    with io.open(PSPLINES, encoding='utf-8') as f:
        f.readline()
        for line in f:
            p = line.rstrip('\n').split('\t')
            if len(p) >= 6:
                rows.append([p[0], int(p[1]), p[4], refs.get((p[0], int(p[1])), "")])
    print("rows:", len(rows), " with ref:", sum(1 for r in rows if r[3]), flush=True)

    cache = {}
    if os.path.exists(CACHE):
        for ln in io.open(CACHE, encoding='utf-8'):
            try:
                o = json.loads(ln); cache[(o['b'], o['i'])] = o['kr']
            except Exception: pass
    todo = [r for r in rows if (r[0], r[1]) not in cache]
    if a.limit: todo = todo[:a.limit*a.batch]
    print("todo:", len(todo), flush=True)

    batches = [todo[i:i+a.batch] for i in range(0, len(todo), a.batch)]
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    lock = threading.Lock(); cf = open(CACHE, "a", encoding='utf-8'); done = 0
    def work(b):
        lines = []
        for j, (blk, idx, jp, ref) in enumerate(b):
            lines.append("###%d [JA] %s [REF] %s" % (j+1, jp, ref if ref else ""))
        user = "다음 대사들을 한국어로 번역하세요.\n\n" + "\n".join(lines)
        out = call(key, [{"role":"system","content":SYSTEM},{"role":"user","content":user}])
        return b, (parse(out, len(b)) if out else [""]*len(b))
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(work, b) for b in batches]
        for f in as_completed(futs):
            b, res = f.result()
            with lock:
                for (blk, idx, jp, ref), t in zip(b, res):
                    cache[(blk, idx)] = t
                    cf.write(json.dumps({"b": blk, "i": idx, "kr": t}, ensure_ascii=False) + "\n")
                cf.flush(); done += len(b)
                if (done // a.batch) % 10 == 0: print("  %d/%d" % (done, len(todo)), flush=True)
    cf.close()
    with io.open(OUT_TSV, 'w', encoding='utf-8') as o:
        o.write("block\tidx\tjp\tkr\tref\n")
        nn = 0
        for blk, idx, jp, ref in rows:
            kr = cache.get((blk, idx), "")
            if kr: nn += 1
            o.write("%s\t%d\t%s\t%s\t%s\n" % (blk, idx, jp.replace('\t',' '), kr.replace('\t',' '), ref.replace('\t',' ')))
    print("translated:", nn, "/", len(rows), "->", OUT_TSV, flush=True)

if __name__ == "__main__":
    main()
