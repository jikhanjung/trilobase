# P64: taxon_bibliography Junction Table

**날짜:** 2026-02-20
**상태:** 계획

## 배경

현재 bibliography(2,130건)와 taxonomic_ranks(5,340건) 사이에 직접적인 FK 관계가 없다.
Bibliography detail에서 관련 genera를 `LIKE '%author_name%'` 텍스트 매칭으로 표시 중 — 부정확하고 느리다.

**기존 간접 연결:**
- `taxonomic_ranks.author` + `year` ↔ `bibliography.authors` + `year` (텍스트 매칭)
- `synonyms.fide_author` + `fide_year` ↔ `bibliography.authors` + `year` (텍스트 매칭)
- `taxonomic_opinions.bibliography_id` → FK (PoC 2건뿐)

**핵심 문제:**
- taxonomic_ranks.author: mixed case, initials 없음 ("Kobayashi", "Hawle & Corda")
- bibliography.authors: ALL CAPS, initials 있음 ("KOBAYASHI, T.", "HAWLE, I. & CORDA, A.J.C.")
- 직접 비교 불가 → surname 추출 + case-insensitive 매칭 필요

## 범위

- 테이블명: `taxon_bibliography` (모든 rank 포함, Genus뿐 아니라 Family/Order 등도)
- `relationship_type`: `original_description` + `fide`
- 예상 링크 수: ~4,000+ original_description + ~500 fide

## 매칭 통계 (탐색 결과)

| 항목 | 수량 |
|------|------|
| author+year 있는 taxa | 5,314 (genera 5,096 + higher 218) |
| 1개 bib 매칭 (high) | ~2,191 (43%) |
| 2+ bib 매칭 (요 disambiguation) | ~830 (16%), 이 중 690은 year_suffix로 해소 |
| 매칭 불가 | ~2,075 (41%) — bib에 해당 저자 없음 |
| fide 매칭 가능 | ~500 / 720 |

## 설계

### 테이블 DDL

```sql
CREATE TABLE taxon_bibliography (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    taxon_id INTEGER NOT NULL,
    bibliography_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL DEFAULT 'original_description'
        CHECK(relationship_type IN ('original_description', 'fide')),
    synonym_id INTEGER,           -- fide 링크의 출처 synonym
    match_confidence TEXT NOT NULL DEFAULT 'high'
        CHECK(match_confidence IN ('high', 'medium', 'low')),
    match_method TEXT,            -- 매칭 알고리즘 분기 기록
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (taxon_id) REFERENCES taxonomic_ranks(id),
    FOREIGN KEY (bibliography_id) REFERENCES bibliography(id),
    FOREIGN KEY (synonym_id) REFERENCES synonyms(id),
    UNIQUE(taxon_id, bibliography_id, relationship_type, synonym_id)
);
CREATE INDEX idx_taxon_bibliography_taxon ON taxon_bibliography(taxon_id);
CREATE INDEX idx_taxon_bibliography_bib ON taxon_bibliography(bibliography_id);
CREATE INDEX idx_taxon_bibliography_type ON taxon_bibliography(relationship_type);
```

**설계 근거:**
- `genus_formations`/`genus_locations` 패턴 준수 (autoincrement id, 2 FK, UNIQUE, notes, created_at)
- `relationship_type`: 같은 taxon-bib 쌍이 다른 역할로 나타날 수 있음
- `synonym_id`: fide 링크의 출처 추적 (NULL for original_description)
- `match_confidence`: 자동 매칭 품질 기록 (UID 스키마와 일관)
- `match_method`: 감사/디버깅용 알고리즘 분기 기록

### 매칭 알고리즘

**Surname 추출 (taxonomic_ranks.author):**
1. "in" 앞부분만 취함: "SIVOV in EGOROVA et al." → "SIVOV"
2. "et al." 제거
3. "&", "," 로 분할: "Hawle & Corda" → ["HAWLE", "CORDA"]
4. 이니셜 접두사 제거: "W. Zhang" → "ZHANG"

**Surname 추출 (bibliography.authors):**
1. cross_ref 제외 ("CHIEN see QIAN.")
2. "&" 로 분할, "SURNAME, INITIALS" 패턴에서 surname 추출

**매칭 로직:**
1. Index 빌드: `(frozenset(surnames_upper), year_int)` → `[bib entries]`
2. Unique match → `high` confidence
3. Multiple candidates + year_suffix disambiguation → `high`
4. Multiple candidates, suffix 없음 → `low`
5. First-surname fallback (et al. 케이스) → `medium`

**Edge Cases:**
- "in" 패턴 저자, "et al.", 이니셜 접두사, year TEXT→INT 변환
- fide_author "herein"/"pers. comm." → skip
- cross_ref bib entries → skip
- 중국/한국 이름 이니셜 패턴

### Named Queries

**`taxon_bibliography_list`** (bibliography detail → 관련 taxa):
```sql
SELECT tr.id, tr.name, tr.rank, tr.author, tr.year, tr.is_valid,
       tb.relationship_type, tb.match_confidence
FROM taxon_bibliography tb
JOIN taxonomic_ranks tr ON tb.taxon_id = tr.id
WHERE tb.bibliography_id = :bibliography_id
ORDER BY tb.relationship_type, tr.rank, tr.name
```

**`taxon_bibliography`** (genus/rank detail → 관련 bibliography):
```sql
SELECT b.id, b.authors, b.year, b.year_suffix, b.title, b.reference_type,
       tb.relationship_type, tb.match_confidence
FROM taxon_bibliography tb
JOIN bibliography b ON tb.bibliography_id = b.id
WHERE tb.taxon_id = :taxon_id
ORDER BY tb.relationship_type, b.year, b.authors
```

### Manifest 업데이트

**bibliography_detail:**
- sub_queries.genera: `bibliography_genera` (LIKE) → `taxon_bibliography_list` (FK)
- Section: "Related Genera" → "Related Taxa", rank/relationship_type 컬럼 추가

**genus_detail:**
- source_query + sub_queries composite 형식으로 전환
- bibliography sub_query 추가
- Sections에 Bibliography linked_table 추가

**rank_detail:**
- bibliography sub_query 추가
- Sections에 Bibliography linked_table 추가

## 구현 파일

| 파일 | 변경 |
|------|------|
| `scripts/link_bibliography.py` | **신규** — 마이그레이션 스크립트 |
| `db/trilobase.db` | 테이블 + 데이터 + queries + manifest |
| `tests/conftest.py` | fixture 업데이트 |
| `tests/test_trilobase.py` | TestTaxonBibliography ~12개 |

## 검증

```bash
python scripts/link_bibliography.py --report   # 매칭 통계
python scripts/link_bibliography.py            # 실행
pytest tests/ -v                               # 테스트 통과
```
