# 102b: P75 Radial Tree — Assertion DB 구현 + scoda-engine 고도화

**날짜**: 2026-03-01 (2026-02-28 세션에서 시작, 03-01 마무리)
**Phase**: P75

## 개요

Trilobase assertion DB(`trilobase-assertion`)에 Radial Tree 시각화 기능 추가 및 scoda-engine의 radial display 모드 대폭 고도화.

## Trilobase 측 작업

### 1. 쿼리 추가 (`scripts/create_assertion_db.py`)

**`radial_tree_nodes`**:
```sql
SELECT id, name, rank, genera_count, is_valid,
       temporal_code, author, year
FROM taxon
WHERE is_valid = 1 OR rank <> 'Genus'
ORDER BY rank, name
```
- invalid Genus 856건 제외 → ~4,485 노드
- assertion DB의 `taxon` 테이블에는 `parent_id`가 없으므로 노드만 반환

**`radial_tree_edges`**:
```sql
SELECT child_id, parent_id
FROM classification_edge_cache
WHERE profile_id = :profile_id
```
- 칼럼명 `child_taxon_id`/`parent_taxon_id` → `child_id`/`parent_id`로 변경 (엔진 기본값과 일치)
- profile_id 파라미터로 classification profile 전환 가능

### 2. Manifest 뷰 추가

```python
"radial_tree": {
    "type": "hierarchy",
    "display": "radial",
    "title": "Radial Tree",
    "icon": "bi-bullseye",
    "source_query": "radial_tree_nodes",
    "hierarchy_options": {
        "id_key": "id", "parent_key": "parent_id",
        "label_key": "name", "rank_key": "rank",
    },
    "radial_display": {
        "edge_query": "radial_tree_edges",
        "edge_params": {"profile_id": 1},
        "color_key": "rank",
        "count_key": "genera_count",
        "depth_toggle": True,
        "leaf_rank": "Genus",
        "on_node_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
        "rank_radius": {
            "_root": 0, "Class": 0.10, "Order": 0.25,
            "Suborder": 0.40, "Superfamily": 0.55,
            "Family": 0.70, "Genus": 1.0,
        },
    },
}
```

P76(canonical DB)과의 핵심 차이: assertion DB는 `edge_query`/`edge_params` 필요 (taxon에 parent_id 없음).

### 3. DB 스키마 변경

- `classification_edge_cache` 칼럼: `child_taxon_id` → `child_id`, `parent_taxon_id` → `parent_id`
- 관련 쿼리(`profile_detail`, `profile_edges` 등) 일괄 업데이트

### 4. `scripts/create_scoda.py` 확장

- `--no-assertion` 플래그 추가
- `build_assertion()` 함수: assertion DB 빌드 → assertion .scoda 패키지 생성 자동 체이닝

## scoda-engine 측 작업

**커밋**: `eff18da` (6 files, +554 -121 lines)

### 버그 수정

| 버그 | 수정 |
|------|------|
| `fetchQuery()` 파라미터 미전달 | `params` 객체를 URL 쿼리 파라미터로 변환 |
| Map 키 타입 불일치 | `String()` 변환으로 number/string 통일 |
| 다중 루트 에러 | `__virtual_root__` 가상 루트 삽입 (d3.stratify 호환) |
| 정적 파일 캐싱 | `?v={{ cache_bust }}` 타임스탬프 캐시 버스팅 |

### 레이아웃 개선

- `d3.cluster()` → `d3.tree()` 전환: 동일 rank 노드가 같은 동심원에 배치
- `rank_radius` 오버라이드: manifest에서 rank별 반지름 비율 지정
- LCA 기반 angular separation: 다른 Order/Family 사이 간격 확대
- 정렬: 상위 rank → 하위 rank, 각각 알파벳순

### 신규 기능

| 기능 | 설명 |
|------|------|
| Pruned Tree (depth toggle) | Family ↔ Genus 레벨 전환, 기본값 pruned(Family) |
| 노드 접기/펼치기 | 클릭으로 자식 노드 fold/unfold, 접힌 노드에 "+" 표시 |
| Subtree Root | 우클릭 "View as root" → 하위 트리만 표시, breadcrumb 네비게이션 |
| 컨텍스트 메뉴 | 우클릭 메뉴 (View as root, Expand/Collapse, Zoom to, Detail) |
| 라벨 표시 개선 | rank 기반 폰트 크기 차등, zoom ≥ 2에서 Genus 표시, maxLabels 500 |
| Orphan 필터링 | edge에 없는 노드(invalid genera) JS 측 필터링 |

### 수정 파일

| 파일 | 변경 |
|------|------|
| `static/js/radial.js` | 120행 → 730+행 (대폭 확장) |
| `static/js/app.js` | `fetchQuery()` 파라미터 지원 |
| `static/css/style.css` | 컨텍스트 메뉴 스타일 |
| `templates/index.html` | 캐시 버스팅, 컨텍스트 메뉴 HTML |
| `app.py` | `cache_bust` 템플릿 변수 |

## 빌드 결과

| 항목 | 값 |
|------|---|
| assertion DB ui_queries | 42개 |
| assertion DB assertions | 6,142건 |
| edge cache | 5,083건 |
| trilobase-assertion.scoda | 1.3 MB, checksum OK |
| 테스트 | 112/112 통과 |

## 커밋 이력

### trilobase repo
- `30db180` — feat: P75 radial tree queries + manifest view
- `af350e0` — feat: P75b assertion DB versioning + CI/CD + hub manifest

### scoda-engine repo
- `eff18da` — feat: radial tree 고도화 (subtree view, context menu, collapse/expand)
- `c4422cd` — docs: radial tree 고도화 작업 기록
