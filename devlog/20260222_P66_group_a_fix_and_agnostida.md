# P66: Group A 데이터 품질 수정 + Agnostida Order 생성

**작성일:** 2026-02-22
**유형:** Plan (구현 계획)
**선행 문서:** P60 (Taxonomic Opinions PoC), P63 (향후 로드맵), devlog 084 (null parent families)

---

## 1. 배경

Order Uncertain(id=144) 아래 81개 Family를 정리하는 T-1 작업의 첫 단계.
현재 taxonomic_opinions 인프라는 B-1 PoC에서 구축 완료 (테이블, 트리거 4개, partial unique index, named query, manifest).
런타임 코드 변경 없이 DB 데이터만 추가하면 됨.

### 대상

- **Group A (3건)**: Adrain 2011과 Jell & Adrain 2002 간 철자 변형으로 인한 중복 엔트리 — 데이터 품질 수정
- **Agnostida (10건)**: Agnostida Order 신설 + opinion 기반 이동

---

## 2. Step 1: Group A — 철자 변형 중복 해소

스크립트: `scripts/fix_spelling_variants.py` (신규, `--dry-run` 지원, idempotent)

### Case 1: Shirakiellidae 중복 삭제

- id=67 (4 genera, Corynexochida/Leiostegiina) — **정상 엔트리**
- id=196 (0 genera, Order Uncertain) — **빈 중복, 삭제**

```sql
DELETE FROM taxonomic_ranks WHERE id = 196;
```

FK 영향: 없음 (genera 0, taxon_bibliography 0, synonyms 0, opinions 0)

### Case 2: Dokimocephalidae(id=210) → Dokimokephalidae(id=134)

- id=210: Jell & Adrain 2002 철자, 46 genera, Order Uncertain
- id=134: Adrain 2011 철자, 0 genera, Olenida (이미 정위치)

```sql
-- 46 genera를 정위치 family로 이동
UPDATE taxonomic_ranks SET parent_id = 134 WHERE parent_id = 210;
-- genera_count 갱신
UPDATE taxonomic_ranks SET genera_count = 46 WHERE id = 134;
-- 빈 엔트리 삭제
DELETE FROM taxonomic_ranks WHERE id = 210;
```

FK 영향: 없음 (taxon_bibliography 0, synonyms 0, opinions 0)

### Case 3: Chengkouaspidae(id=205) → Chengkouaspididae(id=36)

- id=205: Jell & Adrain 2002 철자, 11 genera, Order Uncertain
- id=36: Adrain 2011 철자, 0 genera, Redlichioidea/Redlichiina (이미 정위치)

```sql
UPDATE taxonomic_ranks SET parent_id = 36 WHERE parent_id = 205;
UPDATE taxonomic_ranks SET genera_count = 11 WHERE id = 36;
DELETE FROM taxonomic_ranks WHERE id = 205;
```

FK 영향: 없음

### Group A 결과

- Order Uncertain: 81 → **78** families (-3)
- 삭제된 엔트리 3개 (196, 210, 205)
- genera 이동 57개 (46+11)

---

## 3. Step 2: Agnostida Order 생성 + 10 Family 이동

스크립트: `scripts/create_agnostida_order.py` (신규, `--dry-run` 지원, idempotent)

### 3-1. Agnostida Order 신설

```sql
INSERT INTO taxonomic_ranks (name, rank, parent_id, author, year, genera_count, notes)
VALUES ('Agnostida', 'Order', 1, 'SALTER', '1864', 162,
        'Order created based on traditional classification. Excluded from Adrain (2011) Trilobita sensu stricto.');
```

- parent_id=1 (Class Trilobita)
- Order 수: 12 → **13** (Uncertain 포함 14)

### 3-2. 10 Family에 PLACED_IN Opinion 생성

대상 10개 family (총 162 genera):

| ID | Family | Genera |
|----|--------|--------|
| 201 | Agnostidae | 32 |
| 202 | Ammagnostidae | 13 |
| 206 | Clavagnostidae | 11 |
| 207 | Condylopygidae | 3 |
| 209 | Diplagnostidae | 33 |
| 211 | Doryagnostidae | 3 |
| 212 | Glyptagnostidae | 3 |
| 213 | Metagnostidae | 23 |
| 216 | Peronopsidae | 21 |
| 218 | Ptychagnostidae | 20 |

각 family에 대해:

```sql
INSERT INTO taxonomic_opinions
    (taxon_id, opinion_type, related_taxon_id, bibliography_id,
     assertion_status, curation_confidence, is_accepted, notes)
VALUES
    (<family_id>, 'PLACED_IN', <agnostida_id>, NULL,
     'asserted', 'medium', 1,
     'Traditional classification. Family name contains agnostid root. Adrain (2011) excluded Agnostida from Trilobita sensu stricto classification.');
```

- `bibliography_id=NULL`: Adrain 2011은 Agnostida를 제외했으므로 부적합. 특정 단일 문헌을 지목하기 어려움.
- `assertion_status='asserted'`: Agnostida 배정은 학계 통상 분류
- `curation_confidence='medium'`: 개별 문헌 확인 없이 명칭 기반 배정
- `is_accepted=1`: **트리거가 자동으로 parent_id를 Agnostida로 변경**

### 3-3. Order Uncertain genera_count 갱신

```sql
UPDATE taxonomic_ranks SET genera_count = (
    SELECT SUM(tr.genera_count) FROM taxonomic_ranks tr WHERE tr.parent_id = 144
) WHERE id = 144;
```

### Agnostida 결과

- Order Uncertain: 78 → **68** families (-10)
- 신규 Order: Agnostida (10 families, 162 genera)
- taxonomic_opinions: 2 → **12** (+10)

---

## 4. Step 3: 테스트

`tests/test_trilobase.py`에 추가:

- **TestGroupAFix**: 중복 삭제 확인, genera 이동 확인 (3~5개)
- **TestAgnostidaOrder**: Order 존재, 10 family parent_id, opinions 10건 (3~5개)

---

## 5. Step 4: Devlog + HANDOFF

- `devlog/20260222_086_group_a_fix_and_agnostida.md`
- `docs/HANDOFF.md` 갱신

---

## 6. 수정 파일 목록

| 파일 | 작업 |
|------|------|
| `scripts/fix_spelling_variants.py` | **신규** — Group A 데이터 수정 |
| `scripts/create_agnostida_order.py` | **신규** — Agnostida Order + opinions |
| `db/trilobase.db` | 수정 — 스크립트 적용 |
| `tests/test_trilobase.py` | 수정 — 테스트 추가 |
| `devlog/20260222_086_group_a_fix_and_agnostida.md` | **신규** |
| `docs/HANDOFF.md` | 수정 |

**수정하지 않는 파일**: app.py, mcp_server.py, SPA, conftest.py

---

## 7. 검증 방법

```bash
# 1. Group A dry-run
python scripts/fix_spelling_variants.py --dry-run

# 2. Group A 적용
python scripts/fix_spelling_variants.py

# 3. Agnostida dry-run
python scripts/create_agnostida_order.py --dry-run

# 4. Agnostida 적용
python scripts/create_agnostida_order.py

# 5. DB 검증
sqlite3 db/trilobase.db "SELECT COUNT(*) FROM taxonomic_ranks WHERE parent_id = 144 AND rank = 'Family';"
# 예상: 68

sqlite3 db/trilobase.db "SELECT name FROM taxonomic_ranks WHERE rank = 'Order' ORDER BY name;"
# Agnostida가 목록에 포함

sqlite3 db/trilobase.db "SELECT COUNT(*) FROM taxonomic_opinions;"
# 예상: 12

# 6. 전체 테스트
pytest tests/test_trilobase.py -v
```
