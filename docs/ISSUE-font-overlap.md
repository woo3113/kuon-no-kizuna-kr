# 미해결 이슈: 인게임 한글 "두 겹 겹침(고스트)"

## 증상

인게임 한국어가 **각 글자마다 밝은 본체 + 오른쪽으로 살짝 오프셋된 흐린 사본**으로 겹쳐 보입니다.
일본어 원문은 **정상(깨끗)** 으로 보입니다.

증거:
- `docs/img/jp_clean.png` — 원본 일본어 `寒い……` (깨끗)
- `docs/img/kr_ghost.png` / `kr_ghost2.png` — 한글 (겹침)
- `docs/img/kr_zoom.png` — 한글 5배 확대 (밝은 본체 + 회색 오프셋 사본이 명확)

## 확정된 사실 (실측)

1. 패치된 `SCRIPT.SCP` 안에 해당 대사는 **한 번만** 들어 있습니다(중복 삽입 아님). `tools/probes/_probe_dup.py`
2. 우리가 만든 글리프 비트맵 자체는 깨끗합니다(겹침 없음). `tools/probes/our_glyphs.py`
3. 이 게임은 폰트 파일이 **2개**: `FONT1.FNT`, `FONT2.FNT` (+`DBGFONT.IMY`는 소형 ASCII용).
   ELF 심볼에 `FONT0_DATA_tmp`, `font_make`, `font_search` 등 존재(`tools/probes/_probe_ps2d.py`).
4. **FONT1과 FONT2는 코드 집합이 완전히 동일(각 7,041글리프)** 하고 내용만 다릅니다. `tools/probes/_probe_font12.py`
5. 원본 일본어에서 FONT2 = FONT1의 변형:
   - 강도합 비 **1.23배**(더 굵음)
   - 서브픽셀 무게중심 **dx ≈ -0.107, dy ≈ +0.185**
   - 이진 IoU(정렬 시) = 0.754
   `tools/probes/_probe_shift.py`, `_probe_dilate.py`, `overlay_fonts.py`
   → **두 폰트를 겹쳐야 최종 글자가 되는 구조**로 추정(사용자 확인: "폰트 두 개가 겹쳐지면서 또렷한 폰트를 출력").

## 시도한 것과 결과

| # | 시도 | 결과 |
|---|---|---|
| 1 | FONT1/FONT2에 한글 글리프를 **동일하게** 삽입 | 고스트 |
| 2 | FONT2만 dilation(굵게) | 고스트 |
| 3 | **FONT1에만** 삽입 (FONT2 원본 유지) | 고스트 (변화 없음) |
| 4 | 한글 코드를 **SJIS 사용자영역(0xF040~)** → **표준 미사용 코드(0x8840~, 0xEB6E~, 0xEFD2~)** 로 변경 | 고스트 (단, 끝의 `▽` 마커는 정상화) |
| 5 | FONT2를 **원본 관계(굵기 1.25x + 시프트 -0.11,+0.19)** 로 생성 | 검증 필요 |

## 다음 단계 (제안)

- 엔진이 두 폰트를 **어떤 순서/오프셋/색**으로 겹쳐 그리는지 규명.
  - 후보: FONT1(본체) + FONT2(그림자, 오프셋) / FONT2(굵은 본체) + FONT1(AA 보정) 등
- 규명 방법 아이디어:
  1. **진단 빌드**: 한 코드에 대해 FONT1 = `가`, FONT2 = `나` 를 넣고, 화면에 무엇이 어떤 순서/색/오프셋으로 그려지는지 스샷으로 확인.
  2. 엔진 폰트 렌더 함수(`font_make`/`font_search` 주변) 디스어셈블 (PS2 `SLPS_251.36`, PSP `EBOOT.BIN`).
  3. 오프셋을 실측: 두 레이어의 화면상 오프셋을 스샷에서 계산(`tools/probes/pitch.py` 참고) 후, 그만큼 글리프를 **미리 반대로 시프트**해 겹침이 정합되게 만든다.
- **참고**: 동일 증상이 Fate 프로젝트에서 Claude에 의해 해결된 전례가 있음(사용자 증언). 그 방법(겹침 순서)을 확보하는 것이 최단 경로.

## 관련 스크립트

- 글리프 재현: `_work/matcher/build_font_ext.py` (PSP), `build_font_ps2.py` (PS2)
  - `render()`의 `bold`, `shift`, `margin` 파라미터로 FONT2 변형 조절 가능
- 코드 재배정: `_work/matcher/recode.py`, 복구: `restore_map.py`
- 스크립트 삽입/ISO: `patch_scp.py` / `patch_iso.py` (PS2는 `_ps2` 버전)
