# Phase 46 Step 1: Generic Composite Detail Endpoint

**날짜:** 2026-02-14
**상태:** 완료

## 작업 내용

Legacy detail 엔드포인트 7개(`/api/genus/<id>`, `/api/rank/<id>` 등)를 대체할 manifest-driven
generic composite endpoint 구현.

### 새 엔드포인트

```
GET /api/composite/<view_name>?id=<entity_id>
```

동작:
1. `ui_manifest`에서 `views.<view_name>` 정의를 읽음
2. `source_query` 실행 (메인 쿼리, 단일 행) → 결과를 기본 dict로
3. `sub_queries` 각각 실행 → 결과 배열을 키별로 병합
4. 조합된 복합 JSON 반환

### Named Query 추가 (21개)

**기존 production → conftest 추가 (4개):**
- `rank_detail`, `genus_synonyms`, `genus_formations`, `genus_locations`

**신규 (17개):**
- Genus: `genus_hierarchy` (재귀 CTE), `genus_ics_mapping`
- Rank: `rank_children`, `rank_children_counts`
- Country: `country_detail`, `country_regions`, `country_genera`
- Region: `region_detail`, `region_genera`
- Formation: `formation_detail`, `formation_genera`
- Bibliography: `bibliography_detail`, `bibliography_genera`
- Chronostrat: `chronostrat_detail`, `chronostrat_children`, `chronostrat_mappings`, `chronostrat_genera`

### Manifest Detail View 업데이트 (7개)

모든 detail view에 `source_query`, `source_param`, `sub_queries` 추가:
- `genus_detail`: hierarchy, synonyms, formations, locations, temporal_ics_mapping
- `rank_detail`: children_counts, children
- `country_detail`: regions, genera
- `region_detail`: genera
- `formation_detail`: genera
- `bibliography_detail`: genera
- `chronostrat_detail`: children, mappings, genera

`source` URL을 `/api/composite/<view>?id={id}` 형식으로 변경.

### Sub-query 파라미터 매핑

- `"id"` → URL의 id 파라미터
- `"result.field"` → 메인 쿼리 결과의 필드 값 (예: `result.temporal_code`)

## 파일 변경

| 파일 | 변경 |
|------|------|
| `scoda_desktop/app.py` | `/api/composite/<view_name>` 엔드포인트 추가 (~35줄) |
| `tests/conftest.py` | 21개 named query + 7개 detail view 업데이트 |
| `scripts/add_scoda_ui_tables.py` | 17개 신규 named query 추가 |
| `tests/test_runtime.py` | `TestCompositeDetail` 15개 테스트 |
| `tests/test_trilobase.py` | 5개 composite domain 테스트 클래스 (9개 테스트) |

## 테스트

- **254개 전부 통과** (230 기존 + 24 신규)
- Legacy 엔드포인트 미삭제 — 기존 테스트 모두 유지

## 주의 사항

- Legacy 엔드포인트는 이 단계에서 삭제하지 않음 (Step 3에서 제거 예정)
- `bibliography_genera` 쿼리는 author 이름 LIKE 매칭 — legacy의 first-author + year 매칭과 정확도 차이 있음
- `genus_hierarchy` 재귀 CTE는 SQLite 3.8.3+ 필요
- 프론트엔드 코드 변경 없음 — manifest `source` URL 변경만으로 동작
