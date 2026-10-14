"""dump_psp_lines.py — PSP SCRIPT.SCP 대사를 줄 단위로 추출 (태그 인자 제거판)
태그 인자(<W1>10, <SE_LOAD>18, <BGM>3,1 …)를 본문에서 제거.
출력: psp_lines.tsv  (block, idx, label, chars, jp, tags)
"""
import struct, re, os, io

PROJ = r'F:\TeraBoxDownload\구원의반'
SCP  = PROJ + r'\_work\psp_work\usrdir\PSP_GAME\USRDIR\SCRIPT.SCP'
OUTD = os.path.dirname(os.path.abspath(__file__))

dd = bytes(b ^ 0xFF for b in open(SCP, 'rb').read())
cnt = struct.unpack_from('<I', dd, 0)[0]; D0 = 4 + cnt * 24
blocks = [(dd[4+i*24:4+i*24+16].split(b'\x00')[0].decode('ascii', 'replace'),
           *struct.unpack_from('<II', dd, 4+i*24+16)) for i in range(cnt)]
TAGRE = re.compile(r'<([A-Za-z0-9_]+)>([^\r<]*)')
CJK   = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\u2010-\u2030\u25a0-\u25ff]')

# 인자를 취하는(뒤에 ASCII 인자가 붙는) 태그
ARGTAGS = set("""W1 W2 W3 SE SE1 SE2 SE_LOAD STOP_SE SET_SE BGM BGM_VOLUME STOP_BGM
BG BG2 CHANGE_BG SCROLLBG MOVE_SCROLLBG CLEAR_SCROLLBG BG_BRIGHT CG_BRIGHT CG_RGB
FADE_SPEED EV EV2 JUMP NAME ENTRY BU0 BU1 BU2 BU1_OFS BU2_OFS CLEAR_BU0 CLEAR_BU1 CLEAR_BU2
HC TC IF FLAG INC SELECT SHOCK0 SHOCK1 QUAKE QUAKE2 WHITE_IN WHITE_OUT MASK STOP_MASK FLIP
KOUSHI FULLANM MOVE_LIGHT CG_BRIGHT NONEWAITSPANM STOP_NONEWAITSPANM SAVE SPANM""".split())

def strip_tags(ch):
    # 1) 태그 + (인자태그면 뒤 ASCII 인자까지) 제거
    def r(m):
        return '' if m.group(1).upper() in ARGTAGS else m.group(2)
    ch = re.sub(r'<([A-Za-z0-9_]+)>([0-9A-Za-z_,\.\-]*)', r, ch)
    # 2) 남은 태그 제거
    ch = re.sub(r'<[^>]*>', '', ch)
    return ch

out = io.open(os.path.join(OUTD, 'psp_lines.tsv'), 'w', encoding='utf-8')
out.write("block\tidx\tlabel\tchars\tjp\ttags\n")
nblock = nline = 0
dirty_examples = []
for nm, off, size in blocks:
    txt = dd[D0+off:D0+off+size].decode('cp932', 'replace')
    parts = re.split(r':(\d{4,6})', txt)
    idx = 0
    for k in range(1, len(parts), 2):
        label = parts[k]
        body = parts[k+1] if k+1 < len(parts) else ''
        tags = [m.group(1) for m in TAGRE.finditer(body)]
        buf = []
        for ch in body.split('\r'):
            c = strip_tags(ch).strip()
            if c and CJK.search(c): buf.append(c)
        if not buf:
            continue
        text = ''.join(buf)
        out.write("%s\t%d\t%s\t%d\t%s\t%s\n" % (nm, idx, label, len(text), text.replace('\t',' '), ' '.join(tags)))
        idx += 1; nline += 1
    if idx: nblock += 1
out.close()
print("blocks with text=%d  lines=%d -> psp_lines.tsv (tag args stripped)" % (nblock, nline))
