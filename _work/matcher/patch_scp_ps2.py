"""patch_scp.py — SCRIPT.SCP 에 한국어 삽입 + 재빌드
- 태그(<...>)와 인자, \r 청크 구조 보존
- 각 라벨그룹의 일본어 텍스트를 해당 한국어로 교체(첫 텍스트 청크에 배치)
- 블록 크기 변동 -> 인덱스 재계산
출력: _work/matcher/SCRIPT_kr.SCP, patch_scp.log
"""
import struct, re, os, io, json

PROJ = r'F:\TeraBoxDownload\구원의반'
SCP = PROJ + r'\_work\ps2\ex\SCRIPT.SCP'
MAP = PROJ + r'\_work\krfont\kr_code_map.json'
KRTSV = PROJ + r'\_work\matcher\kr_psp.tsv'
OUTD = os.path.dirname(os.path.abspath(__file__))

code_of = {s: bytes.fromhex(v) for s, v in json.load(open(MAP, encoding='utf-8')).items()}
kr = {}
for l in io.open(KRTSV, encoding='utf-8').read().split('\n')[1:]:
    c = l.split('\t')
    if len(c) >= 4: kr[(c[0], c[1])] = c[3]

ARGTAGS = set("""W1 W2 W3 SE SE1 SE2 SE_LOAD STOP_SE SET_SE BGM BGM_VOLUME STOP_BGM
BG BG2 CHANGE_BG SCROLLBG MOVE_SCROLLBG CLEAR_SCROLLBG BG_BRIGHT CG_BRIGHT CG_RGB
FADE_SPEED EV EV2 JUMP NAME ENTRY BU0 BU1 BU2 BU1_OFS BU2_OFS CLEAR_BU0 CLEAR_BU1 CLEAR_BU2
HC TC IF FLAG INC SELECT SHOCK0 SHOCK1 QUAKE QUAKE2 WHITE_IN WHITE_OUT MASK STOP_MASK FLIP
KOUSHI FULLANM MOVE_LIGHT NONEWAITSPANM STOP_NONEWAITSPANM SPANM""".split())
TAGTAG = re.compile(r'<([A-Za-z0-9_]+)>')
CJK = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\u2010-\u2030\u25a0-\u25ff]')

def enc_kr(s):
    b = bytearray()
    for ch in s:
        if ch in code_of:
            b += code_of[ch]
        elif ord(ch) < 0x80:
            b += bytes([ord(ch)])
        elif ch == '\u3000':
            b += b'\x81\x40'
        else:
            try: b += ch.encode('shift_jis')
            except Exception: b += b'?'
    return bytes(b)

# tag+arg 토큰 스캐너(ARGTAGS만 인자 소비)
def tokens(ch):
    out = []; last = 0; i = 0
    while True:
        m = TAGTAG.search(ch, i)
        if not m: break
        if m.start() > last: out.append((False, ch[last:m.start()]))
        name = m.group(1)
        j = m.end()
        if name.upper() in ARGTAGS:
            k = j
            while k < len(ch) and (ch[k].isascii() and (ch[k].isalnum() or ch[k] in '_,.-')):
                k += 1
            out.append((True, ch[m.start():k])); last = k; i = k
        else:
            out.append((True, ch[m.start():j])); last = j; i = j
    if last < len(ch): out.append((False, ch[last:]))
    return out

dd = bytes(b ^ 0xFF for b in open(SCP, 'rb').read())
cnt = struct.unpack_from('<I', dd, 0)[0]
ents = []
for i in range(cnt):
    o = 4 + i*24
    name = dd[o:o+16]
    off, size = struct.unpack_from('<II', dd, o+16)
    ents.append([name, off, size])
D0 = 4 + cnt*24

LOG = io.open(os.path.join(OUTD, 'patch_scp_ps2.log'), 'w', encoding='utf-8')
def log(x=''): LOG.write(x+'\n')

newdata = bytearray()
newents = []
nrepl = nmiss = 0
for name, off, size in ents:
    nm = name.split(b'\x00')[0].decode('ascii', 'replace')
    block = dd[D0+off:D0+off+size].decode('cp932', 'replace')
    parts = re.split(r'(:\d{4,6})', block)
    out = bytearray()
    idx = -1
    # parts[0] = 라벨 이전(보통 없음), 이후 [label, body] 반복
    out += parts[0].encode('cp932', 'replace')
    for k in range(1, len(parts), 2):
        label = parts[k]
        body = parts[k+1] if k+1 < len(parts) else ''
        out += label.encode('ascii')
        chunks = body.split('\r')
        # 그룹 텍스트 존재 판정
        has = any(any((not isg) and CJK.search(v) for isg, v in tokens(ch)) for ch in chunks)
        if not has:
            out += body.encode('cp932', 'replace'); continue
        idx += 1
        kr_s = kr.get((nm, str(idx)), '')
        if not kr_s:
            nmiss += 1
            out += body.encode('cp932', 'replace')      # 번역 없으면 원문 유지
            continue
        krb = enc_kr(kr_s); placed = False
        for ci, ch in enumerate(chunks):
            for isg, v in tokens(ch):
                if isg:
                    out += v.encode('ascii', 'replace')
                else:
                    if (not placed) and CJK.search(v):
                        out += krb; placed = True
            if ci < len(chunks) - 1: out += b'\r'
        if placed: nrepl += 1
    nb = bytes(out)
    newents.append([name, len(newdata), len(nb)])
    newdata += nb

hdr = bytearray()
hdr += struct.pack('<I', cnt)
for name, off, size in newents:
    hdr += name + struct.pack('<II', off, size)
full = bytes(hdr) + bytes(newdata)
enc = bytes(x ^ 0xFF for x in full)
open(os.path.join(OUTD, 'SCRIPT_kr_ps2.SCP'), 'wb').write(enc)
log("blocks=%d  replaced groups=%d  missing_kr=%d" % (cnt, nrepl, nmiss))
log("size %d -> %d" % (len(dd), len(full)))
LOG.close()
print(io.open(os.path.join(OUTD, 'patch_scp.log'), encoding='utf-8').read())
