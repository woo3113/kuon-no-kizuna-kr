"""recode.py — 한글 SJIS 코드를 '사용자영역(0xF0~)'에서 '미사용 표준 코드'로 재배정
- 게임 폰트가 쓰지 않는 표준 2바이트 코드(칸지영역 우선)에 배정
- kr_code_map.json 갱신
"""
import struct, json, io, sys, os
sys.stdout.reconfigure(encoding='utf-8')
PROJ = r'F:\TeraBoxDownload\구원의반'
MAP = PROJ + r'\_work\krfont\kr_code_map.json'
FONT1 = PROJ + r'\_work\psp_work\usrdir\PSP_GAME\USRDIR\FONT1.FNT'

raw = open(FONT1, 'rb').read()
cnt = struct.unpack_from('<I', raw, 8)[0]
used = set()
for i in range(cnt):
    o = 12+i*8
    used.add(raw[o:o+2])

trails = [t for t in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD))]
def range_codes(leads):
    return [bytes([l, t]) for l in leads for t in trails]

# 칸지영역(0x88~0x9F, 0xE0~0xEA) 우선, 그다음 기호영역(0x81~0x87)
KANJI_LEADS = list(range(0x88, 0xA0)) + list(range(0xE0, 0xF0))
SYM_LEADS   = list(range(0x81, 0x88))
primary = [c for c in range_codes(KANJI_LEADS) if c not in used]
secondary = [c for c in range_codes(SYM_LEADS) if c not in used]
gaps = primary + secondary
print("칸지영역 미사용=%d  기호영역 미사용=%d  합계=%d" % (len(primary), len(secondary), len(gaps)))

old = json.load(io.open(MAP, encoding='utf-8'))
syllables = [s for s, _ in sorted(old.items(), key=lambda kv: bytes.fromhex(kv[1]))]
print("한글 음절수:", len(syllables))
assert len(gaps) >= len(syllables), "코드 부족"

new_map = {s: gaps[i].hex() for i, s in enumerate(syllables)}
json.dump(new_map, io.open(MAP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("재배정 완료 ->", MAP)
first = [(s, new_map[s]) for s in syllables[:6]]
last = [(s, new_map[s]) for s in syllables[-4:]]
print("  예:", first, "...", last)
# lead 분포
from collections import Counter
print("  lead 분포:", dict(Counter(int(v[:2], 16) for v in new_map.values())))
