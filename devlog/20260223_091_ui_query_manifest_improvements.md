# 091 — UI 쿼리 및 매니페스트 개선

**Date:** 2026-02-23
**Status:** WIP (unstaged changes)
**Last commit:** `93603ed` fix(ci): 릴리스 body에 실제 .scoda 파일명 표시

## 변경 사항

### 1. bibliography_genera 쿼리 FK 기반으로 전환 (`add_scoda_ui_tables.py`)

기존: `author LIKE '%' || :author_name || '%'` — 저자명 문자열 매칭 (부정확)
변경: `taxon_bibliography` FK 조인 — `bibliography_id` 파라미터로 정확한 연결

```sql
-- Before
SELECT tr.id, tr.name, tr.author, tr.year, tr.is_valid
FROM taxonomic_ranks tr
WHERE tr.rank = 'Genus'
  AND tr.author LIKE '%' || :author_name || '%'

-- After
SELECT tr.id, tr.name, tr.author, tr.year, tr.is_valid
FROM taxon_bibliography tb
JOIN taxonomic_ranks tr ON tr.id = tb.taxon_id
WHERE tb.bibliography_id = :bibliography_id
  AND tr.rank = 'Genus'
```

### 2. genus_bibliography 쿼리 신규 추가 (`add_scoda_ui_tables.py`)

genus_detail 화면에서 참고문헌 목록을 보여주기 위한 쿼리 추가.

```sql
SELECT b.id, b.authors, b.year, b.title, b.journal, tb.relationship_type
FROM taxon_bibliography tb
JOIN bibliography b ON b.id = tb.bibliography_id
WHERE tb.taxon_id = :genus_id
ORDER BY b.year, b.authors
```

- `ui_queries` 레코드: 36 → **37**

### 3. genus_detail 매니페스트 개선 (`add_scoda_manifest.py`)

- **sub_queries 추가**: `bibliography` → `genus_bibliography` 쿼리 연결
- **genus_geography 제거**: 기존 단일 섹션 → `linked_table` 타입 3개 섹션으로 분리
  - **Locations ({count})**: country_name, region_name (country_detail/region_detail 링크)
  - **Formations ({count})**: name, period (formation_detail 링크)
  - **Bibliography ({count})**: authors, year, title, relationship_type (bibliography_detail 행 클릭)

### 4. bibliography_detail 매니페스트 수정 (`add_scoda_manifest.py`)

- `bibliography_genera` sub_query params: `{"author_name": "result.authors"}` → `{"bibliography_id": "id"}`
- FK 기반 쿼리와 일치하도록 파라미터 변경

### 5. create_scoda.py SPA 기본값 변경

- `--no-spa` 옵션 제거 → `--with-spa` 옵션 추가
- SPA 기본 동작: 포함 → **미포함** (용량 절감)
- **주의**: `if not not args.with_spa` — 이중 부정 버그 있음 (의도와 동일하게 동작하나 가독성 떨어짐)

### 6. trilobase.db 업데이트

위 스크립트 변경사항이 반영된 DB 바이너리 업데이트.

## 파일 목록

| File | Change |
|------|--------|
| `scripts/add_scoda_ui_tables.py` | genus_bibliography 추가, bibliography_genera FK 전환 |
| `scripts/add_scoda_manifest.py` | genus_detail linked_table 3섹션, bibliography sub_query FK 전환 |
| `scripts/create_scoda.py` | --no-spa → --with-spa (기본 SPA 미포함) |
| `db/trilobase.db` | 쿼리/매니페스트 반영 |

## 참고

- `not not args.with_spa`는 `args.with_spa`와 동일하나 코드 정리 권장
