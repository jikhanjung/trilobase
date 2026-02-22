# 088: 유효 속 parent_id NULL 전수 해소 + Agnostina Suborder 추가

**날짜:** 2026-02-22

---

## 배경

유효 속(valid genus) 68건의 parent_id가 NULL인 상태였음.
원문(Jell & Adrain 2002)에서 Family가 확정되지 않은 속들로, 3가지 유형으로 분류됨:

| 유형 | 건수 | 의미 |
|------|------|------|
| `SUBORDER FAMILY UNCERTAIN` | 22 | 아목까지만 확인, 과는 불확실 |
| `INDET` | 14 | 분류 미정 |
| `?FAMILY` / `??FAMILY` | 32 | 잠정적 과 배정 |

## 작업 내용

### 1. Agnostina Suborder 추가 (id=5344)

- Agnostida (Order, id=5341) 산하에 Agnostina (Suborder) 신규 생성
- 원문에 명시되지 않으나 일반적 분류 관례에 따른 배치
- Agnostida 산하 10개 Family를 Agnostina 아래로 재배치 (parent_id 5341 → 5344)

### 2. parent_id 연결 (68건 → 0건)

| 유형 | 건수 | 연결 대상 |
|------|------|-----------|
| AGNOSTINA FAMILY UNCERTAIN | 16 | Agnostina (Suborder, 5344) |
| REDLICHIINA FAMILY UNCERTAIN | 5 | Redlichiina (Suborder, 20) |
| OLENELLINA FAMILY UNCERTAIN | 1 | Olenellina (Suborder, 10) |
| INDET | 14 | Trilobita (Class, 1) |
| ?FAMILY / ??FAMILY | 31 | 해당 Family |
| UNCERTAIN (pyg.) — Costapyge | 1 | Trilobita (Class, 1) |

결과: 유효 속 parent_id NULL **68 → 0건**

### 3. taxonomic_opinions 기록 (6 → 84건)

새로운 assertion_status `questionable` 도입:

| assertion_status | 의미 | 건수 |
|-----------------|------|------|
| `asserted` + high | 기존 확정 배정 | 2 |
| `asserted` + medium | 관례적 배정 (Agnostina Family 10건 + 기존 1건) | 11 |
| `incertae_sedis` + high | FAMILY UNCERTAIN (아목까지만 확인) | 23 |
| `indet` + high | INDET (분류 미정) | 14 |
| `questionable` + low | ?FAMILY / ??FAMILY (잠정적 배정) | 32 |
| SPELLING_OF + high | 철자 변형 (기존) | 2 |

`questionable`과 `incertae_sedis`의 구분:
- `incertae_sedis`: 어디에 속하는지 모름 (과 배정 없음)
- `questionable`: 저자가 특정 과를 지목했으나 불확실 (`?`/`??` 표기)

`??` 여부는 curation_confidence가 아닌 notes에서 "double question mark, very uncertain"으로 구분.

### 4. P10: validate_manifest.py 중복 제거

- `scripts/validate_manifest.py` 삭제 (332줄)
- `scripts/create_scoda.py`, `scripts/create_paleocore_scoda.py`의 import를 `scoda_engine_core`로 변경
- `sys.path.insert` hack 제거

## 테스트

- 100/100 통과
- 수정된 테스트:
  - `test_total_opinions_count`: 6 → 84
  - `test_agnostida_has_10_families`: Agnostida → Agnostina 쿼리로 변경

## 변경 파일

| 파일 | 변경 |
|------|------|
| `db/trilobase.db` | Agnostina 추가, parent_id 연결, opinions 78건 추가 |
| `tests/test_trilobase.py` | 테스트 2건 업데이트 |
| `scripts/validate_manifest.py` | 삭제 |
| `scripts/create_scoda.py` | import 변경 |
| `scripts/create_paleocore_scoda.py` | import 변경 |
| `dist/trilobase.scoda` | 재생성 |
| `dist/paleocore.scoda` | 재생성 |
