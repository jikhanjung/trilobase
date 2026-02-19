# P60: B-1 Taxonomic Opinions PoC — 상세 구현 계획

**작성일:** 2026-02-18
**유형:** Plan (구현 계획)
**브랜치:** `feature/taxonomic-opinions`
**선행 문서:** P50 (설계 방안), P51 (리뷰), P52 (최종 설계), P53 (장기 비전)

---

## 1. 목표

P52에서 확정된 **방안 A'** (별도 테이블 + 무결성 보강)의 Phase 1 PoC 구현.

- `taxonomic_opinions` 테이블 생성
- `is_placeholder` 컬럼 추가
- bibliography에 Adrain 2011 추가
- Eurekiidae에 2-3건 opinion 입력
- API/UI에 opinions 표시
- MCP 도구 추가

**범위:** Eurekiidae 1개 Family의 PLACED_IN opinion 2-3건만. 대규모 입력은 B-2에서.

---

## 2. 구현 단계

### Step 1: DB 스키마 변경 — `scripts/add_opinions_schema.py` 신규 (~120줄)

실제 DB(trilobase.db)에 적용하는 마이그레이션 스크립트.

#### 2.1 `taxonomic_opinions` 테이블

```sql
CREATE TABLE taxonomic_opinions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    taxon_id            INTEGER NOT NULL REFERENCES taxonomic_ranks(id),
    opinion_type        TEXT NOT NULL
                        CHECK(opinion_type IN ('PLACED_IN', 'VALID_AS', 'SYNONYM_OF')),
    related_taxon_id    INTEGER REFERENCES taxonomic_ranks(id),
    proposed_valid      INTEGER,
    bibliography_id     INTEGER REFERENCES bibliography(id),
    assertion_status    TEXT DEFAULT 'asserted'
                        CHECK(assertion_status IN (
                            'asserted', 'incertae_sedis', 'questionable', 'indet'
                        )),
    curation_confidence TEXT DEFAULT 'high'
                        CHECK(curation_confidence IN ('high', 'medium', 'low')),
    is_accepted         INTEGER DEFAULT 0,
    notes               TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.2 인덱스

```sql
CREATE INDEX idx_opinions_taxon ON taxonomic_opinions(taxon_id);
CREATE INDEX idx_opinions_type ON taxonomic_opinions(opinion_type);

-- 핵심: taxon당 opinion_type당 accepted는 최대 1건
CREATE UNIQUE INDEX idx_unique_accepted_opinion
ON taxonomic_opinions(taxon_id, opinion_type)
WHERE is_accepted = 1;
```

#### 2.3 Trigger — parent_id 자동 동기화

```sql
CREATE TRIGGER trg_sync_parent_insert
AFTER INSERT ON taxonomic_opinions
WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1
BEGIN
    UPDATE taxonomic_opinions
    SET is_accepted = 0
    WHERE taxon_id = NEW.taxon_id
      AND opinion_type = 'PLACED_IN'
      AND is_accepted = 1
      AND id != NEW.id;
    UPDATE taxonomic_ranks
    SET parent_id = NEW.related_taxon_id
    WHERE id = NEW.taxon_id;
END;

CREATE TRIGGER trg_sync_parent_update
AFTER UPDATE OF is_accepted ON taxonomic_opinions
WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1 AND OLD.is_accepted = 0
BEGIN
    UPDATE taxonomic_opinions
    SET is_accepted = 0
    WHERE taxon_id = NEW.taxon_id
      AND opinion_type = 'PLACED_IN'
      AND is_accepted = 1
      AND id != NEW.id;
    UPDATE taxonomic_ranks
    SET parent_id = NEW.related_taxon_id
    WHERE id = NEW.taxon_id;
END;
```

#### 2.4 `is_placeholder` 컬럼

```sql
ALTER TABLE taxonomic_ranks ADD COLUMN is_placeholder INTEGER DEFAULT 0;

UPDATE taxonomic_ranks SET is_placeholder = 1
WHERE name = 'Uncertain' AND rank IN ('Order', 'Superfamily');
```

현재 DB의 Uncertain 노드: id=83 (Superfamily), id=144 (Order). 둘 다 플레이스홀더.

#### 2.5 bibliography에 Adrain 2011 추가

현재 bibliography에 Adrain 2011은 없음 (Adrain 논문은 1990~2002 범위만 존재).

```sql
INSERT INTO bibliography (authors, year, title, journal, volume, pages, reference_type, raw_entry,
    uid, uid_method, uid_confidence)
VALUES ('ADRAIN, J.M.', 2011,
    'Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) Animal biodiversity: An outline of higher-level classification and survey of taxonomic richness',
    'Zootaxa', '3148', '104-109', 'article',
    'ADRAIN, J.M. (2011) Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) Animal biodiversity: An outline of higher-level classification and survey of taxonomic richness. Zootaxa, 3148, 104-109.',
    'scoda:bib:fp_v1:sha256:adrain_2011_zootaxa3148', 'fp_v1', 'medium');
```

이 id를 opinions에서 FK로 사용.

#### 2.6 Eurekiidae 시범 데이터

Eurekiidae (id=164) → 현재 parent_id=144 (Uncertain Order)

```sql
-- Opinion 1: incertae sedis (현재 수용)
INSERT INTO taxonomic_opinions
    (taxon_id, opinion_type, related_taxon_id, bibliography_id,
     assertion_status, curation_confidence, is_accepted)
VALUES
    (164, 'PLACED_IN', 144, <adrain_2011_id>,
     'incertae_sedis', 'high', 1);

-- Opinion 2: Asaphida 소속 (대안)
INSERT INTO taxonomic_opinions
    (taxon_id, opinion_type, related_taxon_id, bibliography_id,
     assertion_status, curation_confidence, is_accepted, notes)
VALUES
    (164, 'PLACED_IN', 115, NULL,
     'asserted', 'medium', 0, 'Hypothetical example for PoC');
```

Fortey 1990 논문은 bibliography에 있지만 이 정확한 주장을 매칭하는 것은 실제 문헌 확인이 필요하므로, PoC에서는 bibliography_id=NULL로 넣거나, Fortey 논문 중 하나를 연결.

#### 2.7 schema_descriptions 갱신

```sql
INSERT INTO schema_descriptions (table_name, column_name, description)
VALUES
    ('taxonomic_opinions', NULL, 'Taxonomic opinions — multiple classification viewpoints per taxon'),
    ('taxonomic_opinions', 'taxon_id', 'Subject taxon of this opinion'),
    ('taxonomic_opinions', 'opinion_type', 'PLACED_IN, VALID_AS, or SYNONYM_OF'),
    ('taxonomic_opinions', 'related_taxon_id', 'Target taxon (parent for PLACED_IN, senior for SYNONYM_OF)'),
    ('taxonomic_opinions', 'proposed_valid', 'Proposed validity for VALID_AS (1=valid, 0=invalid)'),
    ('taxonomic_opinions', 'bibliography_id', 'Source reference for this opinion'),
    ('taxonomic_opinions', 'assertion_status', 'Author certainty: asserted, incertae_sedis, questionable, indet'),
    ('taxonomic_opinions', 'curation_confidence', 'Curator confidence: high, medium, low'),
    ('taxonomic_opinions', 'is_accepted', 'Whether this is the currently accepted opinion (max 1 per taxon+type)'),
    ('taxonomic_ranks', 'is_placeholder', 'Whether this node is a placeholder (e.g., Uncertain Order)');
```

**스크립트 기능:**
- `--dry-run`: 변경 없이 실행 계획만 출력
- idempotent: 이미 적용된 경우 skip (테이블/컬럼 존재 체크)
- Adrain 2011 bibliography_id 자동 조회 후 opinions에 사용

---

### Step 2: Named Query 추가 — `trilobase.db` ui_queries

```sql
-- 특정 taxon의 opinions 조회
INSERT INTO ui_queries (name, description, sql, params_json, created_at)
VALUES ('taxon_opinions',
    'Taxonomic opinions for a specific taxon',
    'SELECT o.id, o.opinion_type, o.related_taxon_id, t.name as related_taxon_name, t.rank as related_taxon_rank, o.bibliography_id, b.authors as bib_authors, b.year as bib_year, b.title as bib_title, o.assertion_status, o.curation_confidence, o.is_accepted, o.notes, o.created_at FROM taxonomic_opinions o LEFT JOIN taxonomic_ranks t ON o.related_taxon_id = t.id LEFT JOIN bibliography b ON o.bibliography_id = b.id WHERE o.taxon_id = :taxon_id ORDER BY o.is_accepted DESC, o.created_at',
    '{"taxon_id": "integer"}',
    '2026-02-18T00:00:00');
```

이 쿼리를 `rank_detail`의 sub_query로 연결.

---

### Step 3: Manifest 수정 — `rank_detail` view에 opinions 섹션 추가

**수정 대상:** `trilobase.db`의 `ui_manifest` (default)

`rank_detail` view의 `sub_queries`에 opinions 추가:

```json
"sub_queries": {
    "children_counts": {"query": "rank_children_counts", "params": {"rank_id": "id"}},
    "children": {"query": "rank_children", "params": {"rank_id": "id"}},
    "opinions": {"query": "taxon_opinions", "params": {"taxon_id": "id"}}
}
```

`rank_detail` view의 `sections`에 opinions linked_table 추가 (Children 뒤, My Notes 앞):

```json
{
    "title": "Taxonomic Opinions ({count})",
    "type": "linked_table",
    "data_key": "opinions",
    "condition": "opinions",
    "columns": [
        {"key": "related_taxon_name", "label": "Proposed Parent"},
        {"key": "related_taxon_rank", "label": "Rank"},
        {"key": "bib_authors", "label": "Author"},
        {"key": "bib_year", "label": "Year"},
        {"key": "assertion_status", "label": "Status"},
        {"key": "is_accepted", "label": "Accepted", "type": "boolean"}
    ],
    "on_row_click": {"detail_view": "rank_detail", "id_key": "related_taxon_id"}
}
```

opinions가 있는 taxon의 rank detail에만 표시됨 (`condition: "opinions"`).

**수정 적용:** `scripts/add_opinions_schema.py`에서 manifest JSON UPDATE로 적용.

---

### Step 4: `scripts/add_scoda_manifest.py` 수정

Trilobase manifest 생성 스크립트에 동일한 변경 반영:
- `rank_detail.sub_queries`에 `opinions` 추가
- `rank_detail.sections`에 opinions linked_table 추가
- `taxon_opinions` named query INSERT 추가

---

### Step 5: Test Fixture 수정 — `tests/conftest.py`

1. `test_db` fixture에 `taxonomic_opinions` 테이블 CREATE
2. `is_placeholder` 컬럼 추가 (ALTER TABLE or CREATE 시 포함)
3. 인덱스 + trigger 생성
4. 테스트용 opinion 데이터 2건 삽입:
   - Phacopida(id=2)에 대한 PLACED_IN accepted opinion → parent Trilobita(id=1)
   - Phacopida(id=2)에 대한 PLACED_IN alternative opinion → (가상 taxon)
5. `taxon_opinions` named query 추가
6. `rank_detail` manifest의 sub_queries/sections에 opinions 추가

---

### Step 6: 테스트 추가 — `tests/test_trilobase.py`

`TestTaxonomicOpinions` 클래스 (~15개 테스트):

**스키마 테스트:**
1. `test_opinions_table_exists` — taxonomic_opinions 테이블 존재
2. `test_opinions_columns` — 필수 컬럼 확인
3. `test_is_placeholder_column` — taxonomic_ranks.is_placeholder 존재

**Constraint 테스트:**
4. `test_opinion_type_check` — 잘못된 opinion_type INSERT → 실패
5. `test_assertion_status_check` — 잘못된 assertion_status → 실패
6. `test_partial_unique_accepted` — 같은 taxon+type에 accepted 2건 → 실패

**Trigger 테스트:**
7. `test_trigger_insert_sync_parent` — accepted PLACED_IN INSERT → parent_id 변경
8. `test_trigger_update_sync_parent` — is_accepted=1 UPDATE → parent_id 변경
9. `test_trigger_deactivates_previous` — 새 accepted → 기존 accepted 해제

**API/Composite 테스트:**
10. `test_opinions_named_query` — `taxon_opinions` 쿼리 실행
11. `test_composite_rank_detail_includes_opinions` — `/api/composite/rank_detail` 응답에 opinions 포함
12. `test_composite_rank_detail_no_opinions` — opinions 없는 taxon → opinions 키 빈 배열

**Manifest 테스트:**
13. `test_rank_detail_manifest_has_opinions_section` — manifest에 opinions section 존재
14. `test_rank_detail_manifest_has_opinions_sub_query` — sub_queries에 opinions 존재

**PoC 데이터 테스트 (실제 DB):**
15. `test_eurekiidae_has_opinions` — 실제 trilobase.db에서 Eurekiidae opinions 조회

---

### Step 7: MCP 도구 — `data/mcp_tools_trilobase.json`

기존 dynamic MCP tools에 `get_taxon_opinions` 추가:

```json
{
    "name": "get_taxon_opinions",
    "description": "Get taxonomic opinions for a taxon, showing alternative classification viewpoints from different literature sources",
    "input_schema": {
        "type": "object",
        "properties": {
            "taxon_id": {"type": "integer", "description": "ID of the taxon to get opinions for"}
        },
        "required": ["taxon_id"]
    },
    "query_type": "named_query",
    "named_query": "taxon_opinions"
}
```

---

### Step 8: .scoda 패키지 갱신

마이그레이션 스크립트 실행 후 `.scoda` 패키지 재생성:

```bash
python scripts/create_scoda.py --mcp-tools data/mcp_tools_trilobase.json
```

`validate_manifest.py`가 자동으로 새 sub_query/section 검증.

---

### Step 9: devlog + HANDOFF.md 갱신

- `devlog/20260218_077_taxonomic_opinions_poc.md` — 작업 기록
- `docs/HANDOFF.md` — 완료 항목 추가, test count 갱신

---

## 3. 수정 파일 목록

| 파일 | 작업 | 규모 |
|------|------|------|
| `scripts/add_opinions_schema.py` | **신규** — DB 마이그레이션 스크립트 | ~120줄 |
| `scripts/add_scoda_manifest.py` | 수정 — rank_detail opinions, taxon_opinions query | ~30줄 |
| `tests/conftest.py` | 수정 — opinions 테이블/데이터/쿼리/manifest | ~60줄 |
| `tests/test_trilobase.py` | 수정 — TestTaxonomicOpinions 클래스 추가 | ~200줄 |
| `data/mcp_tools_trilobase.json` | 수정 — get_taxon_opinions 도구 추가 | ~15줄 |
| `trilobase.db` | 수정 — 스키마 변경 + 데이터 입력 | 스크립트 |
| `docs/HANDOFF.md` | 수정 — 완료 항목 추가 | ~20줄 |

**수정하지 않는 파일:**
- `scoda_desktop/app.py` — composite endpoint이 이미 범용이므로 코드 변경 불필요
- `scoda_desktop/mcp_server.py` — dynamic tool loading이므로 코드 변경 불필요
- `scoda_desktop/static/js/app.js` — linked_table section이 이미 범용이므로 변경 불필요
- `spa/app.js` — 동일 이유

---

## 4. 검증 방법

```bash
# 1. 마이그레이션 스크립트 dry-run
python scripts/add_opinions_schema.py --dry-run

# 2. 실제 적용
python scripts/add_opinions_schema.py

# 3. 단위 테스트
pytest tests/test_trilobase.py::TestTaxonomicOpinions -v

# 4. 전체 테스트
pytest tests/ -v

# 5. 실제 DB 확인
sqlite3 trilobase.db "SELECT * FROM taxonomic_opinions;"
sqlite3 trilobase.db "SELECT is_placeholder FROM taxonomic_ranks WHERE name='Uncertain';"

# 6. Composite API 확인 (서버 실행 시)
curl 'http://localhost:8080/api/composite/rank_detail?id=164' | jq '.opinions'

# 7. .scoda 패키지 재생성 (manifest validator 자동 실행)
python scripts/create_scoda.py --mcp-tools data/mcp_tools_trilobase.json
```

---

## 5. 아키텍처 노트

### 왜 app.py를 수정하지 않는가

SCODA Desktop은 Phase 46에서 도메인 코드가 완전히 제거되었다. 모든 데이터 접근은:
- **REST API**: `/api/composite/<view_name>` — manifest의 source_query + sub_queries로 자동 실행
- **MCP**: `mcp_tools.json`의 dynamic tool definitions로 자동 로드

따라서 `taxonomic_opinions` 추가는 **DB 스키마 + 쿼리 + manifest** 변경만으로 API/MCP 모두에 자동 노출된다.

### Trigger의 역할

> tree structure는 선택된 assertion의 materialized result다. (P52 §4.2)

`parent_id`는 accepted opinion의 캐시다. Trigger가 이 동기화를 자동 보장하므로:
- 기존 트리 쿼리 100% 호환
- SPA의 tree view 변경 불필요
- opinion 변경 → parent_id 자동 반영

### PoC 범위 제한

이 단계에서는:
- **PLACED_IN**만 구현 (VALID_AS, SYNONYM_OF는 B-2 이후)
- **Eurekiidae 1개**만 데이터 입력 (56개 전부는 B-2)
- **읽기 전용** — opinion 추가/변경 UI는 백오피스(C-2)에서
- **SPA 커스텀 렌더링 없음** — 기존 `linked_table` section type으로 충분
