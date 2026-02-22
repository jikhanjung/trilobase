# 086: Group A 데이터 품질 수정 + Agnostida Order 생성

**날짜:** 2026-02-22

## 요약

Order Uncertain(id=144) 아래 81개 Family 중:
- **Group A (3건)**: 철자 변형 중복 해소 → 81→78 families
- **Agnostida (10건)**: 신규 Order 생성 + opinion 기반 이동 → 78→68 families

## Group A — 철자 변형 중복 해소

### Case 1: Shirakiellidae (id=196) 삭제
- id=67: 정상 엔트리 (4 genera, Corynexochida/Leiostegiina)
- id=196: 빈 중복 (0 genera, Order Uncertain) → **삭제**

### Case 2: Dokimocephalidae(id=210) → Dokimokephalidae(id=134)
- id=210: Jell & Adrain 2002 철자, 46 genera, Order Uncertain
- id=134: Adrain 2011 철자, 0 genera, Olenida (정위치)
- 46 genera 이동 → id=134, id=210 **삭제**

### Case 3: Chengkouaspidae(id=205) → Chengkouaspididae(id=36)
- id=205: Jell & Adrain 2002 철자, 11 genera, Order Uncertain
- id=36: Adrain 2011 철자, 0 genera, Redlichioidea/Redlichiina (정위치)
- 11 genera 이동 → id=36, id=205 **삭제**

**결과**: 3 엔트리 삭제, 57 genera 이동

## Agnostida Order 생성

### Order 신설
- name: Agnostida, rank: Order, parent_id: 1 (Trilobita)
- author: SALTER, year: 1864
- genera_count: 162
- id: 5341

### 10 Family PLACED_IN Opinion
| Family | ID | Genera |
|--------|-----|--------|
| Agnostidae | 201 | 32 |
| Ammagnostidae | 202 | 13 |
| Clavagnostidae | 206 | 11 |
| Condylopygidae | 207 | 3 |
| Diplagnostidae | 209 | 33 |
| Doryagnostidae | 211 | 3 |
| Glyptagnostidae | 212 | 3 |
| Metagnostidae | 213 | 23 |
| Peronopsidae | 216 | 21 |
| Ptychagnostidae | 218 | 20 |

- `assertion_status='asserted'`, `curation_confidence='medium'`, `is_accepted=1`
- `bibliography_id=NULL` (개별 문헌 특정 불가)
- 트리거가 자동으로 parent_id를 Agnostida로 변경

### Order Uncertain 갱신
- genera_count: 1185 (재계산)
- families: 68

## 스크립트

| 파일 | 설명 |
|------|------|
| `scripts/fix_spelling_variants.py` | Group A 철자 변형 수정 (`--dry-run`) |
| `scripts/create_agnostida_order.py` | Agnostida Order + opinions (`--dry-run`) |

## DB 변경 요약

| 항목 | Before | After |
|------|--------|-------|
| Order Uncertain families | 81 | 68 |
| Orders (Uncertain 포함) | 13 | 14 |
| taxonomic_opinions | 2 | 12 |
| taxonomic_ranks 총 행 | 5,340 | 5,338 (-3 삭제, +1 Agnostida) |

## 테스트

- `TestGroupAFix`: 5개 (중복 삭제 확인, genera 이동 확인)
- `TestAgnostidaOrder`: 5개 (Order 존재, 10 families, opinions 10건)
- **총 92개 통과** (기존 82 + 신규 10)
