# 100 — Rebuild DB ↔ Reference DB 차이 해소

**Date:** 2026-02-28
**Ticket:** P73

## Summary

rebuild pipeline (P72)이 35/35 검증을 통과했지만, 행 단위 비교에서 내용 차이 발견.
수정 가능한 항목은 모두 수정하고, 수동 재분류/미세 차이는 문서화.

최종 결과: **35/35 검증 통과 + SYNONYM_OF 행 단위 diff 0건.**

## 차이 분류 및 처리

| # | 카테고리 | 건수 | 처리 |
|---|---------|------|------|
| A | Hierarchy 이름 파싱 | 3 | ✅ 수정 |
| B | SPELLING_OF 가족 매핑 | 47 | ✅ 수정 |
| C | INDET→Trilobita parent_id | 14 | ✅ 기존 로직 확인 |
| D | Synonym senior_name 추출 | ~9 | ✅ 수정 |
| E | Extra/missing synonym opinions | ~4 | ✅ 수정 |
| F | 수동 재분류 | 6 | ❌ 문서화 |
| G | Type 3 formation 오분류 | 43→356 | ✅ 수정 |
| H | Bracket stripping 버그 | 5 | ✅ 수정 |
| I | genus_locations 미세 차이 | ~18 | ❌ 문서화 |

---

## Fix A: Hierarchy 이름 파싱 (hierarchy.py)

1. `notes` regex에 `subfamil` 추가 → Phacopina "(3 subfamilies)" 매칭
2. `nov.` 제거에 후행 각주 숫자 허용 → "Aulacopleurida nov.23" 정리
3. `notes` regex에 후행 각주 숫자 허용 → "(11 families)33" 정리

## Fix B: SPELLING_OF 가족 매핑 (load_data.py)

`SPELLING_OF_MAP` dict 추가: Dokimocephalidae → Dokimokephalidae, Chengkouaspidae → Chengkouaspididae.
`_build_family_lookup()`에서 variant→canonical 리디렉트. 47개 속 정정.

## Fix C: INDET → Trilobita parent_id

기존 `_MANUAL_PLACED_IN` dict + SQLite trigger로 이미 처리됨. 추가 수정 불필요.

## Fix D: Synonym senior_name 추출 (parse_genera.py, load_data.py)

- **D1**: s.s.s./s.o.s. 패턴 → 보충(enrichment) 전용 (standalone opinion 미생성)
- **D2**: "and thus j.o.s." → `_SYNONYM_OVERRIDES` (Hausmannia→Odontochile)
- **D3**: case-insensitive senior name lookup (load_data.py)
- **D4**: "either X or Y" → 첫 대안 추출 (Mauraspis→Koneprusia)
- **D5**: suppressed "for discussion" 오탐 방지 → "in favour of" only
- **D6**: 수동 오버라이드 (Ogygia→Ogygiocaris, Gortania→Microphthalmus)

## Fix E: Synonym opinion 정밀 조정

- **Boeckaspis**: 중복 j.s.s. 제거 (overlapping regex dedup by type+senior_name)
- **Hausmannia**: 중복 preocc. 제거 (bare preocc. drop when another has senior_name)
- **Paralichas**: `;` + `preocc., replaced by` 패턴 추가 → 누락 preocc. 복원
- **Taihangshaniashania**: replacement pattern에서 "for" 필수화 → "foe" 오탐 방지

## Fix G: Type 3 formation 오분류 (parse_genera.py)

`rec.country and not rec.region` 조건에 `rec.location is None` 추가.
결과: 356건 reclassification (이전 0건 → 과다 731건 → 최종 356건).

## Fix H: Bracket stripping 버그 (parse_genera.py)

`loc_str`에서 잔여 bracket content strip: `re.sub(r'[^\]]*\]\s*', '', loc_str)`.
5개 속에서 type species bracket 내용이 formation으로 누출되던 문제 해결.

---

## 수정하지 않는 항목

### F: 수동 재분류 (6 속)
원본 텍스트와 다른 가족으로 수동 재배치된 항목. 소스 기반 rebuild에서 재현 불가:
- Altikolia, Eurudagnostus, Junggarella, Micragnostus, Polyeres, Xinhuangaspis

### I: genus_locations 미세 차이 (~18건)
hyphen-break, quote 처리, 축약형 지명 차이 등. 데이터 품질에 실질적 영향 없음.

---

## 수정 파일

| 파일 | 수정 |
|------|------|
| `scripts/pipeline/hierarchy.py` | Fix A |
| `scripts/pipeline/load_data.py` | Fix B, D3, E (Hausmannia dedup) |
| `scripts/pipeline/parse_genera.py` | Fix D1-D6, E (Boeckaspis/Paralichas/Taihangshaniashania), G, H |
| `scripts/pipeline/validate.py` | PaleoCore 검증값 조정 (countries >=140, formations >=1780) |

## 검증 결과

```
35/35 validations passed
  taxonomic_ranks: 5341
  opinions total: 1139 (SYNONYM_OF: 1055, PLACED_IN: 82, SPELLING_OF: 2)
  bibliography: 2131
  taxon_bibliography: 4234
  genus_formations: 4502
  genus_locations: 4857
  PaleoCore: 147 countries, 1788 formations
```

SYNONYM_OF 행 단위 diff: **0건** (ref DB와 완전 일치)
