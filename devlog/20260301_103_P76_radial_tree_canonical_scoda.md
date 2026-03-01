# 103: P76 Radial Tree → Canonical trilobase.scoda 구현

**날짜**: 2026-03-01
**Phase**: P76

## 작업 내용

P75에서 assertion DB 전용으로 구현된 Radial Tree 기능을 canonical `trilobase.scoda` 패키지에 추가.

### 핵심 차이: assertion DB vs canonical DB

| 항목 | assertion DB (P75) | canonical DB (P76) |
|------|--------------------|--------------------|
| 트리 소스 | `taxon` + `classification_edge_cache` | `taxonomic_ranks` (parent_id 내장) |
| 쿼리 수 | 2개 (nodes + edges) | 1개 (nodes만) |
| manifest | `edge_query` + `edge_params` 필요 | 불필요 |

## 수정 파일

### 1. `scripts/add_scoda_ui_tables.py`

`insert_queries()`에 `radial_tree_nodes` 쿼리 추가:

```sql
SELECT id, name, rank, parent_id, genera_count, is_valid,
       temporal_code, author, year
FROM taxonomic_ranks
WHERE is_valid = 1 OR rank <> 'Genus'
ORDER BY rank, name
```

- 기존 `taxonomy_tree`: Genus 전체 제외
- `radial_tree_nodes`: valid Genus 포함, invalid Genus(856건)만 제외
- `parent_id` 칼럼 직접 반환 → edge 쿼리 불필요

### 2. `scripts/add_scoda_manifest.py`

`views` dict에 `radial_tree` 뷰 추가:

- `type: "hierarchy"`, `display: "radial"`
- `rank_radius`: 동심원 배치 (Class 0.10 → Genus 1.0)
- `depth_toggle: True`: Family ↔ Genus 레벨 토글
- `on_node_click`: `rank_detail` 연동

## 빌드 결과

| 항목 | Before | After |
|------|--------|-------|
| ui_queries | 37 | 38 (+radial_tree_nodes) |
| manifest views | 13 (6 tab + 7 detail) | 14 (7 tab + 7 detail) |
| trilobase.scoda | 0.2.5 | 0.2.5 (1.4 MB) |

## 검증

- `ui_queries`에 `radial_tree_nodes` 존재 확인
- `ui_manifest`의 `views.radial_tree` 항목 확인 (type=hierarchy, display=radial)
- `.scoda` 패키지 빌드 성공, checksum OK
- assertion DB 리빌드 정상 (6,142 assertions, 5,083 edges)
- 테스트: **112/112 통과**

## HANDOFF.md 갱신

- P76 섹션 추가
- ui_queries 카운트 37 → 38
- Last updated 날짜 갱신
