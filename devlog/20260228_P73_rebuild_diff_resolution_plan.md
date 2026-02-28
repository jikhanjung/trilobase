# P73 — Rebuild DB ↔ Reference DB 차이 해소 계획

**Date:** 2026-02-28

## Context

rebuild pipeline 35/35 검증 통과했지만 행 단위 비교에서 차이 발견. 건수는 일치하나 내용이 다른 항목들을 수정 가능한 것은 수정하고, 수정 불가능한 것은 devlog에 문서화.

## 차이 분류

| # | 카테고리 | 건수 | 수정? |
|---|---------|------|------|
| A | Hierarchy 이름 파싱 (3 노드) | 3 | ✅ |
| B | SPELLING_OF 가족 매핑 (47 속) | 47 | ✅ |
| C | INDET→Trilobita parent_id (14 속) | 14 | ✅ |
| D | Synonym senior_name 추출 (~9건) | 9 | ✅ |
| E | Extra/missing synonym opinions | ~8 | ✅ (일부) |
| F | 수동 재분류 (6 속) | 6 | ❌ 문서화 |
| G | Type 3 formation 오분류 (43건) | 43 | ✅ |
| H | Bracket stripping 버그 (5 속) | 5 | ✅ |
| I | genus_locations 미세 차이 | ~18 | ❌ 문서화 |

---

## Fix A: Hierarchy 이름 파싱

**파일**: `scripts/pipeline/hierarchy.py:108,114`

1. notes regex에 `subfamil` 추가 → Phacopina "(3 subfamilies)" 매칭
2. nov. 제거에 후행 각주 숫자 허용 → "Aulacopleurida nov.23" 정리
3. notes regex에 후행 각주 숫자 허용 → "Olenida nov. (11 families)33" 정리

## Fix B: SPELLING_OF 가족 매핑

**파일**: `scripts/pipeline/load_data.py:324` — `_build_family_lookup()`

SPELLING_OF_MAP으로 variant→canonical 리디렉트 추가.
46개 속(Dokimocephalidae) + 1개 속(Chengkouaspidae) → 정정 스펠링으로 매핑.

## Fix C: INDET→Trilobita parent_id

**파일**: `scripts/pipeline/load_data.py`

14개 INDET 속을 Trilobita로 직접 이동 (reference처럼 opinion 없이 parent_id만 UPDATE).

## Fix D: Synonym senior_name 추출

**파일**: `scripts/pipeline/parse_genera.py`, `load_data.py`

- D1: s.s.s./s.o.s. 패턴 추가 (Conocephalus, Herse, Kirkella, Rhinaspis 등)
- D2: "and thus j.o.s." 패턴 (Hausmannia→Odontochile)
- D3: case-insensitive senior name lookup (Korolevium→Sphaerexochus)
- D4: "either X or Y" 처리 (Mauraspis→Koneprusia)
- D5: suppressed "for discussion" 오탐 방지 (Acanthaloma)
- D6: 수동 오버라이드 (Ogygia→Ogygiocaris, Gortania→Microphthalmus)

## Fix G: Type 3 formation 오분류 개선

**파일**: `scripts/pipeline/parse_genera.py` — `parse_all()` Type 3 조건

현재 `not rec.region` 조건이 "central Kazakhstan" 등 다중 단어 location에서 실패.
→ region 유무 무관하게 formation suffix/whitelist 체크로 변경.

## Fix H: Bracket stripping 버그

**파일**: `scripts/pipeline/parse_genera.py` — `parse_entry()` loc_match 후

5개 속에서 type species bracket 내용이 formation으로 누출. loc_str에서 잔여 bracket content strip.

---

## 수정하지 않는 항목 (devlog에 문서화)

- **F**: 수동 재분류 6 속 (Altikolia, Eurudagnostus, Junggarella, Micragnostus, Polyeres, Xinhuangaspis) — 소스 텍스트와 다른 가족으로 수동 재배치됨
- **I**: genus_locations 미세 차이 — hyphen-break, quote 처리 차이 등

## 수정 파일

| 파일 | 수정 |
|------|------|
| `scripts/pipeline/hierarchy.py` | Fix A |
| `scripts/pipeline/load_data.py` | Fix B, C, D3 |
| `scripts/pipeline/parse_genera.py` | Fix D1-D6, G, H |
| `devlog/20260228_100_rebuild_diff_resolution.md` | 전체 차이 내역 + 처리 결과 |

## 검증

```bash
python scripts/rebuild_database.py --output-dir dist/rebuild/ --validate
# 35/35 유지 + 행 단위 diff 감소 확인
```
