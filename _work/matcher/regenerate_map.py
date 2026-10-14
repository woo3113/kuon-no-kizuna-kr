"""regenerate_map.py — 사용자영역(0xF0~0xF9) 코드맵 재생성
buildkr.py 와 동일한 순서: sorted(안드로이드 한글 음절) + sorted(추가 필요 음절)
"""
import io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
PROJ = r'F:\TeraBoxDownload\구원의반'
MAP = PROJ + r'\_work\krfont\kr_code_map.json'

base = set()
for ln in io.open(PROJ + r'\_work\android_kr_lines.tsv', encoding='utf-8'):
    for ch in ln:
        if '\uac00' <= ch <= '\ud7a3': base.add(ch)
base_order = sorted(base)

need = set()
for ln in io.open(PROJ + r'\_work\matcher\kr_psp.tsv', encoding='utf-8').read().split('\n')[1:]:
    c = ln.split('\t')
    if len(c) >= 4:
        for ch in c[3]:
            if '\uac00' <= ch <= '\ud7a3': need.add(ch)
new_only = sorted(need - base)
syllables = base_order + new_only
print("안드로이드 음절=%d  추가=%d  합계=%d" % (len(base_order), len(new_only), len(syllables)))

VALID_TRAIL = [t for t in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD))]
codes = []
for lead in range(0xF0, 0xFA):
    for t in VALID_TRAIL:
        codes.append(bytes([lead, t]))
assert len(codes) >= len(syllables), len(codes)
new = {s: codes[i].hex() for i, s in enumerate(syllables)}
json.dump(new, io.open(MAP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("저장:", MAP, len(new))
print("  가=", new['가'], " 춥=", new['춥'], " 다=", new['다'])
