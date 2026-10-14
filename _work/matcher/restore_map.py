"""restore_map.py — 재배정 사고 복구: 0xF0~ 사용자영역 코드맵 재생성
음절 순서는 현재 맵의 코드 정렬 순서를 그대로 사용.
"""
import io, json, sys
sys.stdout.reconfigure(encoding='utf-8')
MAP = r'F:\TeraBoxDownload\구원의반\_work\krfont\kr_code_map.json'
cur = json.load(io.open(MAP, encoding='utf-8'))
syllables = [s for s, _ in sorted(cur.items(), key=lambda kv: bytes.fromhex(kv[1]))]
VALID_TRAIL = [t for t in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD))]
codes = []
for lead in range(0xF0, 0xFA):
    for trail in VALID_TRAIL:
        codes.append(bytes([lead, trail]))
new = {s: codes[i].hex() for i, s in enumerate(syllables)}
json.dump(new, io.open(MAP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("복구:", len(new), "음절")
print("  가=", new.get('가'), " 춥=", new.get('춥'), " 첫=", [new[s] for s in syllables[:3]], " 끝=", [new[s] for s in syllables[-2:]])
