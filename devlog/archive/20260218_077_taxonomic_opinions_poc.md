# B-1: Taxonomic Opinions PoC

**날짜:** 2026-02-18
**브랜치:** `feature/taxonomic-opinions`
**계획 문서:** `devlog/20260218_P60_taxonomic_opinions_poc.md`

## 개요

분류학적 의견(taxonomic opinions) 시스템 PoC 구현. 하나의 taxon에 대해 여러 문헌이 서로 다른 분류 위치를 제안할 수 있는 구조를 DB에 도입. 기존 `parent_id`는 accepted opinion의 캐시로 유지하고, 별도 `taxonomic_opinions` 테이블에 전체 의견 이력을 저장.

## 구현 내용

### 1. DB 마이그레이션 (`scripts/add_opinions_schema.py`, ~230줄)

**새 테이블: `taxonomic_opinions`**
```sql
CREATE TABLE taxonomic_opinions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    taxon_id INTEGER NOT NULL REFERENCES taxonomic_ranks(id),
    opinion_type TEXT NOT NULL CHECK(opinion_type IN ('PLACED_IN', 'VALID_AS', 'SYNONYM_OF')),
    related_taxon_id INTEGER REFERENCES taxonomic_ranks(id),
    proposed_valid INTEGER,
    bibliography_id INTEGER REFERENCES bibliography(id),
    assertion_status TEXT DEFAULT 'asserted' CHECK(...),
    curation_confidence TEXT DEFAULT 'high' CHECK(...),
    is_accepted INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**트리거 4개 (BEFORE/AFTER 분리 패턴):**
- `trg_deactivate_before_insert`: BEFORE INSERT — 기존 accepted PLACED_IN 비활성화
- `trg_sync_parent_insert`: AFTER INSERT — `taxonomic_ranks.parent_id` 동기화
- `trg_deactivate_before_update`: BEFORE UPDATE — 기존 accepted PLACED_IN 비활성화
- `trg_sync_parent_update`: AFTER UPDATE — `taxonomic_ranks.parent_id` 동기화

**Partial unique index:**
```sql
CREATE UNIQUE INDEX idx_unique_accepted_opinion
ON taxonomic_opinions(taxon_id, opinion_type) WHERE is_accepted = 1;
```

**새 컬럼:** `taxonomic_ranks.is_placeholder INTEGER DEFAULT 0` — "Uncertain" 같은 인공 노드 표시

**PoC 데이터:** Eurekiidae 2건
- PLACED_IN Ptychopariida (incertae sedis, accepted) — Jell & Adrain 2002
- PLACED_IN Asaphida (asserted, alternative) — Adrain 2011

**마이그레이션 7단계:** 테이블 생성 → 트리거 → is_placeholder → bibliography → opinions → named query → manifest. 모두 idempotent, `--dry-run` 지원.

### 2. Manifest 업데이트 (`scripts/add_scoda_manifest.py`)

`rank_detail` composite view에 opinions sub_query 및 linked_table 섹션 추가:
- Sub-query: `taxon_opinions` (param: `result.id`)
- Section: "Taxonomic Opinions ({count})" linked_table — related_taxon_name, rank, authors, year, assertion_status, is_accepted

### 3. MCP 도구 (`data/mcp_tools_trilobase.json`)

`get_taxon_opinions` 추가 (query_type: named_query, named_query: taxon_opinions).

### 4. 테스트 추가 (15개)

`tests/test_trilobase.py` — `TestTaxonomicOpinions` 클래스:

| 카테고리 | 테스트 | 설명 |
|----------|--------|------|
| Schema | test_opinions_table_exists | 테이블 존재 확인 |
| Schema | test_opinions_columns | 11개 컬럼 확인 |
| Schema | test_is_placeholder_column | taxonomic_ranks 컬럼 확인 |
| Constraint | test_opinion_type_check | CHECK 제약 검증 |
| Constraint | test_assertion_status_check | CHECK 제약 검증 |
| Constraint | test_curation_confidence_check | CHECK 제약 검증 |
| Constraint | test_partial_unique_accepted_non_placed | VALID_AS partial unique 검증 |
| Trigger | test_trigger_insert_sync_parent | INSERT 시 parent_id 동기화 |
| Trigger | test_trigger_update_sync_parent | UPDATE 시 parent_id 동기화 |
| Trigger | test_trigger_deactivates_previous | BEFORE 트리거 자동 비활성화 |
| API | test_opinions_named_query | named query 실행 검증 |
| API | test_composite_rank_detail_includes_opinions | composite에 opinions 포함 |
| API | test_composite_rank_detail_no_opinions | opinions 없는 경우 빈 배열 |
| Manifest | test_rank_detail_manifest_has_opinions_sub_query | sub_queries 확인 |
| Manifest | test_rank_detail_manifest_has_opinions_section | sections 확인 |

### 5. 기타 변경

- `tests/conftest.py`: opinions 테이블/트리거/테스트 데이터/쿼리/매니페스트 추가
- `tests/test_runtime.py`: query count 29 → 30
- `trilobase.db`: 마이그레이션 적용 완료 (테이블, 트리거, 데이터, 쿼리, 매니페스트, schema_descriptions 10건)

## 핵심 설계 결정

### BEFORE/AFTER 트리거 분리

원래 설계: AFTER 트리거에서 deactivate + sync 모두 수행.
문제: SQLite partial unique index 체크가 AFTER 트리거 전에 발생 → 새 accepted INSERT 시 IntegrityError.
해결: Deactivation은 BEFORE 트리거 (index 체크 전), parent_id sync는 AFTER 트리거 (INSERT 후).

### 런타임 코드 변경 없음

SCODA Desktop 아키텍처가 완전히 범용적이므로 `app.py`, `mcp_server.py`, `app.js` 변경 없이:
- Composite endpoint가 manifest sub_queries 실행
- SPA가 linked_table 섹션 자동 렌더링
- MCP 서버가 mcp_tools.json에서 동적 로드

DB + manifest + named query + mcp_tools.json 변경만으로 구현 완료.

## 테스트 결과

```
262 passed in 283.47s
```

| 파일 | 수 |
|------|-----|
| test_runtime.py | 122 |
| test_trilobase.py | 123 |
| test_mcp.py | 16 |
| test_mcp_basic.py | 1 |
| **합계** | **262** |

## 수정 파일 목록

| 파일 | 작업 |
|------|------|
| `scripts/add_opinions_schema.py` | **신규** — DB 마이그레이션 (~230줄) |
| `scripts/add_scoda_manifest.py` | 수정 — rank_detail에 opinions 추가 |
| `data/mcp_tools_trilobase.json` | 수정 — get_taxon_opinions 도구 추가 |
| `tests/conftest.py` | 수정 — opinions 테이블/트리거/데이터/쿼리/매니페스트 |
| `tests/test_trilobase.py` | 수정 — TestTaxonomicOpinions 15개 테스트 |
| `tests/test_runtime.py` | 수정 — query count 29→30 |
| `trilobase.db` | 수정 — 마이그레이션 적용 |
