# 123: taxon 테이블에서 genera_count 컬럼 제거

**날짜**: 2026-03-11

## 배경

`genera_count`는 canonical DB(0.2.6)에서 Family/Order 레코드에 정적으로 저장되던 값.
0.3.0에서는 `classification_edge_cache` 기반 동적 계산(`taxonomy_tree_genera_counts` 쿼리)으로 이미 대체되어 있었으나, 컬럼 자체는 남아 있었음.

- 186개 Family/Order에만 값이 있었고, Treatise 추가 taxa에는 값 없음
- Tree 뷰에서는 동적 계산만 사용 중 (정적 값 무시)
- `taxon_children` 쿼리만 `t.genera_count`를 직접 참조

## 변경 내용

### build_trilobase_db.py
- taxon 테이블 스키마: `genera_count INTEGER DEFAULT 0` 제거
- `copy_taxon()`: SELECT/INSERT에서 genera_count 제거 (18→17 컬럼)
- `taxonomy_tree` 쿼리: `0 as genera_count` 하드코딩 제거
- `taxon_children` 쿼리: `t.genera_count` → edge_cache 서브쿼리로 동적 계산
  ```sql
  (SELECT COUNT(*) FROM classification_edge_cache e2
   JOIN taxon g ON g.id = e2.child_id AND g.rank = 'Genus'
   WHERE e2.parent_id = t.id AND e2.profile_id = COALESCE(:profile_id, 1)
  ) AS genera_count
  ```
- editable_entities taxon: `genera_count` 필드 제거
- taxon_detail children 컬럼: `genera_count`의 `condition` 제거 (동적 계산이므로 항상 값 있음)

### test_trilobase.py
- `genera_count` 직접 참조 모두 제거
- TestGroupAFix: canonical DB 특화 테스트(ID 기반 삭제 확인) → 0.3.0 맞춤 재작성
  - `test_shirakiellidae_duplicate_deleted` → 제거 (0.3.0에 해당 ID 없음)
  - `test_dokimocephalidae_deleted` → `test_dokimocephalidae_is_placeholder` (placeholder + SPELLING_OF 확인)
  - `test_dokimokephalidae_has_genera` → `test_dokimokephalidae_in_edge_cache` (edge_cache 존재 확인)
  - `test_chengkouaspidae_deleted` → `test_chengkouaspidae_is_placeholder`
  - `test_chengkouaspididae_has_genera` → edge_cache 기반 (>= 10)
- TestAgnostidaOrder: `genera_count` 필드 assertion 제거
- TestSpellingOfOpinions: `genera_count` assertion 제거
- 테스트 수: 118 → 117 (TestGroupAFix 5→4개)

## CI 테스트 수정 (같은 커밋에 포함)

0.3.0 통합 후 CI에서 21개 테스트가 `taxonomic_ranks`/`taxonomic_opinions` 테이블 참조로 실패.
모든 테스트를 `taxon`/`assertion`/`classification_edge_cache` 기반으로 전환:

- TestGroupAFix: `taxonomic_ranks` → `taxon`
- TestAgnostidaOrder: `taxonomic_opinions` → `assertion`, `is_accepted` 제거, edge_cache 기반
- TestSpellingOfOpinions: `taxonomic_opinions` → `assertion` (predicate/object_taxon_id)
- TestTemporalCodeFill: `raw_entry IS NOT NULL` 조건 추가 (Treatise 추가 taxa 제외)
- TestCountryIdConsistency: `taxonomic_ranks` → `taxon`

## 검증

- `validate_trilobase_db.py`: 17/17 통과
- `pytest tests/`: 117/117 통과
