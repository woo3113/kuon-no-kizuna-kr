# 久遠の絆 再臨詔 한글패치 (PS2 / PSP)

「久遠の絆 再臨詔」(구원의 반 재림조) 한글패치 프로젝트.

- **PS2**: `SLPS_251.36` (일본판)
- **PSP**: `ULJM05981` — 久遠の絆 再臨詔 Portable (일본판)
- 방식: 일본어 스크립트(`SCRIPT.SCP`)를 한국어로 교체 + 폰트에 한글 글리프 삽입 → ISO 재빌드

> ⚠️ **미해결 이슈가 하나 있습니다. [`docs/ISSUE-font-overlap.md`](docs/ISSUE-font-overlap.md) 를 먼저 보세요.**
> 인게임 한국어가 **두 겹으로 겹쳐(고스트)** 보입니다. 원인은 이 게임이 **두 폰트(FONT1/FONT2)를 겹쳐서** 글자를 그리는 구조 때문으로 보이며, 겹침 순서/역할 규명이 필요합니다. (동일 증상이 Fate 프로젝트에서 Claude에 의해 해결된 바 있음)

---

## 1. 현재 상태

| 항목 | 상태 |
|---|---|
| FCOMP 폰트 포맷 해독 | ✅ |
| 한국어 대사 번역 (11,677줄) | ✅ |
| PSP 블록 ↔ 안드로이드 대사 정렬 | ✅ (블록단위) |
| `SCRIPT.SCP` 재빌드 (태그 보존) | ✅ |
| 폰트 한글 확장 (1,487음절) | ✅ |
| ISO 재배치 (PSP / PS2) | ✅ |
| **인게임 한글 렌더 (겹침)** | ❌ **미해결** |
| UI/이미지 텍스트 | ⬜ 미착수 |

증거 스샷:
- `docs/img/kr_ghost.png`, `docs/img/kr_ghost2.png`, `docs/img/kr_zoom.png` — 한글(겹침)
- `docs/img/jp_clean.png` — 일본어(정상)
- `docs/img/font_overlay.png` — FONT1 vs FONT2 겹침 비교

---

## 2. 미해결 이슈 요약

- 게임은 **FONT1.FNT / FONT2.FNT** 두 폰트를 **겹쳐서** 그립니다. 코드 집합은 양쪽 동일(7,041글리프).
- 원본 일본어에서 **FONT2 = FONT1의 굵기 1.23배 + 서브픽셀 시프트 (dx≈-0.11, dy≈+0.19)** 관계입니다.
  즉 두 폰트가 **역할이 다른 레이어**이며, 겹쳐야 "또렷한" 글자가 됩니다.
- 우리가 넣은 한글은 두 폰트에 **동일(또는 굵기만 다르게)** 들어가서, 겹칠 때 **고스트(이중상)** 로 보입니다.
- 시도한 것과 결과, 그리고 계측 스크립트는 `docs/ISSUE-font-overlap.md` 참고.

**다음 사람이 할 일**: 두 폰트의 겹침 순서/역할(그리고 엔진이 각 레이어에 적용하는 오프셋·색)을 규명하여, 한글 글리프를 원본과 **동일한 관계**로 생성.

---

## 3. 파이프라인 (전체 재현 순서)

모든 스크립트는 `_work/matcher/` 에 있습니다. `PROJ = F:\TeraBoxDownload\구원의반` 절대경로 기준.

```
1) 대사 추출        dump_psp_lines.py         -> psp_lines.tsv (326블록, 11,677줄, 태그 인자 제거)
2) 정렬(매처)       matcher6.py -> refine2.py  -> align_final.tsv, align_lines.tsv
   (명령 시퀀스)    (matcher5.py = 파일럿, matcher4.py = 텍스트 전용)
3) 번역            translate_psp.py          -> kr_psp_cache.jsonl (DeepSeek, 안드로이드 REF)
                  clean_kr.py                -> kr_psp.tsv (11,677줄 최종)
4) 폰트 확장        build_font_ext.py(PSP) / build_font_ps2.py(PS2) -> _work/krfont, _work/ps2/krfont
5) 스크립트 삽입     patch_scp.py(PSP) / patch_scp_ps2.py(PS2) -> SCRIPT_kr.SCP / SCRIPT_kr_ps2.SCP
6) ISO 빌드        patch_iso.py(PSP) / patch_iso_ps2.py(PS2) -> F:\psptest\* (K).iso
7) 검증            verify_iso.py
```

부가: `recode.py`(코드 재배정), `restore_map.py`(코드맵 복구), `assign_global.py`/`align_report.py`(정렬 QA).

---

## 4. 포맷 메모

### SCRIPT.SCP
- 전체 **XOR 0xFF**.
- 헤더: `u32 블록수(327)` + 327×24 인덱스 `[name16][offset u32][size u32]` (offset은 데이터 시작 이후 상대값).
- 블록 = `\r:NNNNN\r<태그>인자\r...텍스트...\r` 구조. 태그: `<SAVE> <MSG_IN> <PAGE> <W1> <BGM> <SE_LOAD> <BG> <CHANGE_BG> <EV> <NAME> <ENTRY> <JUMP>` 등.
- PSP 데이터 시작 = `4 + 327*24`; PS2도 동일 구조(블록 이름/개수 동일, 텍스트 줄수 11,677 완전 일치).

### 폰트 (FCOMP)
- 헤더 8B: `"FCOMP" | byte5(42) | stride | rows`  (PSP 14×17, **PS2 26×28**)
- `u32 글리프수` → 글리프당 8B: `[SJIS 2B][payload크기 u16][offset u32]`
- payload = RLE: `b&0x80==0` → 리터럴(픽셀수=(b&0x70)>>4, 픽셀값=b&0x0F, 이후 니블), `b&0x80` → 백참조.
  (픽셀값 0~15 = 1바이트에 1픽셀을 그대로 써도 디코드됨)
- **FONT1/FONT2 코드집합 동일**, 내용만 다름(FONT2 = 굵음+시프트).

### ISO
- PSP: ISO9660 디렉터리 엔트리 갱신(파일을 ISO 끝에 append). `FONT1.FNT`,`FONT2.FNT`,`SCRIPT.SCP` 재배치.
- PS2: 파일이 루트(`/FONT1.FNT` 등). ELF에 **파일명 풀만 있고 LBA/크기 테이블 없음** → ISO9660만 갱신하면 됨.

---

## 5. 번역 정책

- PSP 일본어 대사를 DeepSeek(`deepseek-chat`)로 JP→KR.
- **안드로이드 한국어 정식 발매판** 텍스트를 정렬해 **참고(REF)로 주입** → 고유명사/용어를 안드로이드 표기로 고정.
- 정렬이 ±1줄 밀린 REF는 원문 우선으로 무시하도록 프롬프트에 명시.
- 태그 인자(`<W1>10`)가 본문에 섞이던 문제 → 추출기에서 제거, 기존 번역은 `clean_kr.py`로 잔여 숫자만 제거(추가 API 비용 0).
- 누락 30줄은 원문 유지.

---

## 6. 주요 데이터/산출물

| 파일 | 설명 |
|---|---|
| `_work/matcher/psp_lines.tsv` | PSP 원문 대사 11,677줄 (block, idx, label, chars, jp, tags) |
| `_work/matcher/kr_psp.tsv` | 최종 한국어 번역 (block, idx, jp, kr, ref) |
| `_work/matcher/align_lines.tsv` | PSP줄 ↔ 안드로이드줄 매핑 |
| `_work/krfont/kr_code_map.json` | 음절 → SJIS 코드 (현재 표준 미사용 코드) |
| `_work/matcher/SCRIPT_kr.SCP` | 한글 삽입된 PSP 스크립트 (XOR 상태) |
| `_work/matcher/SCRIPT_kr_ps2.SCP` | 한글 삽입된 PS2 스크립트 |

> 대용량 게임 바이너리(ISO/APK/추출본)는 저장소에 포함하지 않았습니다.

---

## 7. 환경

- Windows x64, Python 3.14 (`py -3.14`), Pillow
- 원본 ISO/APK는 각자 준비 (`_work/psp_work/`, `_work/ps2/`, `_work/apk/`)
- 에뮬: PPSSPP / PCSX2
