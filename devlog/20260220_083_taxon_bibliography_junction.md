# 083: taxon_bibliography Junction Table

**날짜:** 2026-02-20
**계획 문서:** `devlog/20260220_P64_taxon_bibliography.md`

## 목표

Bibliography와 taxonomic_ranks 사이에 정확한 관계 테이블 생성. 기존 LIKE '%author_name%' 텍스트 매칭을 junction table 기반 정확한 링크로 대체.

## 구현 내용

### 1. `scripts/link_bibliography.py` 마이그레이션 스크립트

패턴: `scripts/add_opinions_schema.py` (idempotent, `--dry-run`, `--report`)

**테이블 DDL:**
```sql
CREATE TABLE taxon_bibliography (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    taxon_id INTEGER NOT NULL,
    bibliography_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL DEFAULT 'original_description'
        CHECK(relationship_type IN ('original_description', 'fide')),
    synonym_id INTEGER,
    match_confidence TEXT NOT NULL DEFAULT 'high'
        CHECK(match_confidence IN ('high', 'medium', 'low')),
    match_method TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (taxon_id) REFERENCES taxonomic_ranks(id),
    FOREIGN KEY (bibliography_id) REFERENCES bibliography(id),
    FOREIGN KEY (synonym_id) REFERENCES synonyms(id),
    UNIQUE(taxon_id, bibliography_id, relationship_type, synonym_id)
);
```

**매칭 알고리즘:**
- `extract_surnames(author)`: taxonomic_ranks.author에서 성씨 추출 (mixed case, "in" 패턴, "et al.", initials 제거)
- `extract_bib_surnames(authors)`: bibliography.authors에서 성씨 추출 (ALL CAPS + initials, cross_ref skip)
- 인덱스: `(frozenset(surnames), year)` → `[bib entries]`
- 매칭: surname set + year → candidates → year_suffix 필터
- Confidence: unique match → high, suffix disambiguated → high, ambiguous → skip (low)
- Fide 매칭: synonyms.fide_author+fide_year → same algorithm ("herein", "pers. comm." skip)

**실행 단계:**
- [1/6] Create table (idempotent)
- [2/6] Build bibliography index
- [3/6] Match taxonomic_ranks → bibliography (original_description)
- [4/6] Match synonyms fide → bibliography (fide)
- [5/6] Add named queries + update manifest
- [6/6] Add schema descriptions

### 2. 매칭 결과

| 항목 | 수량 |
|------|------|
| Bibliography entries | 2,131 (cross_ref 15 skip) |
| Index keys | 1,906 |
| **original_description** | **3,607** (high confidence) |
| Taxa with author+year | 5,314 |
| Unmatched taxa | 1,629 (bibliography에 없는 저자) |
| **fide** | **433** (high confidence) |
| Synonyms with fide | 720 |
| Skipped (herein/pers. comm.) | 49 |
| Unmatched fide | 234 |
| **총 링크** | **4,040** |

### 3. Named Queries 추가

- `taxon_bibliography_list`: bibliography detail에서 관련 taxa 표시 (기존 `bibliography_genera` LIKE 쿼리 대체)
- `taxon_bibliography`: genus/rank detail에서 관련 bibliography 표시

### 4. Manifest 업데이트

**bibliography_detail:**
- `sub_queries.genera` (LIKE 쿼리) → `sub_queries.taxa` (junction table)
- Section: "Related Genera" → "Related Taxa" + rank/relationship_type 컬럼 추가

**genus_detail:**
- `source` → `/api/composite/genus_detail?id={id}` (composite endpoint)
- `source_query: "genus_detail"`, `source_param: "genus_id"` 추가
- `sub_queries` 6개: hierarchy, synonyms, formations, locations, temporal_ics_mapping, **bibliography**
- Bibliography linked_table section 추가 (Original Entry 앞)

**rank_detail:**
- `sub_queries.bibliography` 추가
- Bibliography linked_table section 추가 (Opinions 앞)

### 5. Schema Descriptions

`taxon_bibliography` 테이블 + 7개 컬럼 설명 (총 8건)

## 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `scripts/link_bibliography.py` | **신규** — 마이그레이션 스크립트 (~300줄) |
| `db/trilobase.db` | taxon_bibliography 테이블 + 4,040 rows + queries + manifest + schema |
| `tests/conftest.py` | taxon_bibliography DDL, bib entries 3개, junction rows 3개, queries 2개, manifest 3개 뷰 |
| `tests/test_trilobase.py` | TestTaxonBibliography 클래스 16개 테스트 |

## 테스트

```
pytest tests/ -v
======================== 82 passed in 134.19s ========================
```

- 기존 66개 → **82개** (+16)
- TestTaxonBibliography: schema 5 + data 3 + query 2 + composite 3 + manifest 3 = 16
- 기존 TestCompositeBibliographyDetail 수정 (genera → taxa)

## 비고

- Unmatched 1,629 taxa: bibliography에 해당 저자/연도 항목이 없는 경우 (Jell & Adrain 2002 문헌 목록에 미수록)
- Low confidence 매칭은 모두 skip — 4,040건 전부 high confidence
- `--report` 모드로 실행 결과 확인 후 적용 가능
- Idempotent: 재실행 시 모든 단계 [SKIP]
