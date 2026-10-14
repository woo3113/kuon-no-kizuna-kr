"""patch_scp.py — SCRIPT.SCP 에 한국어 삽입 (원본 청크 구조 보존 방식)
- 각 라벨그룹의 '원본 텍스트 런' 위치/개수를 그대로 두고, 한국어를 런 길이 비례로 분배
- 태그(<...>)와 인자는 원위치 보존
- 선두 전각공백(0x8140) 유지
출력: _work/matcher/SCRIPT_kr.SCP (PSP) / SCRIPT_kr_ps2.SCP (PS2)
"""
import struct, re, os, io, json

PROJ = r'F:\TeraBoxDownload\구원의반'
SCP = PROJ + r'\_work\psp_work\usrdir\PSP_GAME\USRDIR\SCRIPT.SCP'
MAP = PROJ + r'\_work\krfont\kr_code_map.json'
KRTSV = PROJ + r'\_work\matcher\kr_psp.tsv'
OUTD = os.path.dirname(os.path.abspath(__file__))
OUTNAME = 'SCRIPT_kr.SCP'

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
FWSP = '\u3000'

def enc_kr(s):
    b = bytearray()
    for ch in s:
        if ch in code_of: b += code_of[ch]
        elif ord(ch) < 0x80: b += bytes([ord(ch)])
        elif ch == FWSP: b += b'\x81\x40'
        else:
            try: b += ch.encode('shift_jis')
            except Exception: b += b'?'
    return bytes(b)

def tokens(ch):
    """(is_tag, text) 목록. ARGTAG 는 인자까지 태그로 취급."""
    out = []; last = 0; i = 0
    while True:
        m = TAGTAG.search(ch, i)
        if not m: break
        if m.start() > last: out.append((False, ch[last:m.start()]))
        name = m.group(1); j = m.end()
        if name.upper() in ARGTAGS:
            k = j
            while k < len(ch) and (ch[k].isascii() and (ch[k].isalnum() or ch[k] in '_,.-')): k += 1
            out.append((True, ch[m.start():k])); last = k; i = k
        else:
            out.append((True, ch[m.start():j])); last = j; i = j
    if last < len(ch): out.append((False, ch[last:]))
    return out

def rebuild_group(chunks, slices_by_run, only_idx):
    """chunks: 원본 \r 분할. slices_by_run: {(ci,ti): kr_slice}. 태그/구조 보존."""
    out = bytearray()
    for ci, ch in enumerate(chunks):
        for ti, (isg, val) in enumerate(tokens(ch)):
            if isg:
                out += val.encode('ascii', 'replace')
            else:
                if CJK.search(val):
                    out += enc_kr(slices_by_run.get((ci, ti), ''))
                else:
                    out += val.encode('cp932', 'replace')   # 숫자/공백 등 원본 유지
        if ci < len(chunks)-1: out += b'\r'
    return bytes(out)

dd = bytes(b ^ 0xFF for b in open(SCP, 'rb').read())
cnt = struct.unpack_from('<I', dd, 0)[0]
ents = []
for i in range(cnt):
    o = 4 + i*24
    ents.append([dd[o:o+16], *struct.unpack_from('<II', dd, o+16)])
D0 = 4 + cnt*24

LOG = io.open(os.path.join(OUTD, 'patch_scp.log'), 'w', encoding='utf-8')
def log(x=''): LOG.write(x + '\n')

newdata = bytearray(); newents = []
nrepl = nmiss = 0
for name, off, size in ents:
    nm = name.split(b'\x00')[0].decode('ascii', 'replace')
    block = dd[D0+off:D0+off+size].decode('cp932', 'replace')
    parts = re.split(r'(:\d{4,6})', block)
    out = bytearray(); out += parts[0].encode('cp932', 'replace')
    idx = -1
    for k in range(1, len(parts), 2):
        label = parts[k]; body = parts[k+1] if k+1 < len(parts) else ''
        out += label.encode('ascii')
        chunks = body.split('\r')
        tokchunks = [tokens(ch) for ch in chunks]
        runs = [(ci, ti, v) for ci, tc in enumerate(tokchunks) for ti, (isg, v) in enumerate(tc)
                if not isg and CJK.search(v)]
        if not runs:
            out += body.encode('cp932', 'replace'); continue
        idx += 1
        kr_s = kr.get((nm, str(idx)), '')
        if not kr_s:
            nmiss += 1; out += body.encode('cp932', 'replace'); continue
        jp_all = ''.join(v for _, _, v in runs)
        if jp_all.startswith(FWSP) and not kr_s.startswith(FWSP):
            kr_s = FWSP + kr_s
        L = len(kr_s); total = sum(len(v) for _, _, v in runs)
        bounds = [0]; cum = 0
        for _, _, v in runs:
            cum += len(v); bounds.append(round(L*cum/total))
        bounds[-1] = L
        slices = {}
        for r, (ci, ti, v) in enumerate(runs):
            slices[(ci, ti)] = kr_s[bounds[r]:bounds[r+1]]
        out += rebuild_group(chunks, slices, idx)
        nrepl += 1
    nb = bytes(out)
    newents.append([name, len(newdata), len(nb)])
    newdata += nb

hdr = bytearray(); hdr += struct.pack('<I', cnt)
for name, off, size in newents: hdr += name + struct.pack('<II', off, size)
full = bytes(hdr) + bytes(newdata)
open(os.path.join(OUTD, OUTNAME), 'wb').write(bytes(x ^ 0xFF for x in full))
log("blocks=%d  replaced groups=%d  missing_kr=%d" % (cnt, nrepl, nmiss))
log("size %d -> %d" % (len(dd), len(full)))
LOG.close()
print(io.open(os.path.join(OUTD, 'patch_scp.log'), encoding='utf-8').read())
