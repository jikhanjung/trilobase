# Hierarchy View 일반화 (tree + nested_table 통합)

**날짜:** 2026-02-16
**파일:** `scoda_desktop/static/js/app.js`

## 변경 내용

### 문제
Generic viewer에 hierarchical data 렌더러가 2개 존재:
- `type: "tree"` — 펼치기/접기 트리 + leaf 아이템 테이블 (`buildTreeFromFlat()`)
- `type: "chart"` — colspan/rowspan nested table (`buildChartTree()`)

둘 다 같은 입력(id, parent_id, name, rank flat rows)을 사용하지만 트리 빌드 함수가 별도 구현.
차이는 sort 방식(label vs order_key)과 skip_ranks 처리뿐.

### 해결

`type: "hierarchy"` + `display` 속성으로 통합, 공유 트리 빌더 추출.

#### 1. `buildHierarchy(rows, opts)` — 통합 트리 빌더
- `buildTreeFromFlat()` (알파벳 정렬) + `buildChartTree()` (order_key 정렬) 통합
- `sort_by: "label" | "order_key"` 옵션으로 정렬 방식 선택
- `skip_ranks` 지원 (기존 chart의 Super-Eon 건너뛰기 등)

#### 2. `normalizeViewDef(viewDef)` — 하위 호환 정규화
- `loadManifest()` 직후 모든 view에 적용
- `type: "tree"` + `tree_options` → `type: "hierarchy"`, `display: "tree"`, `hierarchy_options` + `tree_display`
- `type: "chart"` + `chart_options` → `type: "hierarchy"`, `display: "nested_table"`, `hierarchy_options` + `nested_table_display`

#### 3. `switchToView()` dispatch 변경
- `type === 'tree'` / `type === 'chart'` → `type === 'hierarchy'` + `display` 분기

#### 4. 옵션 경로 변경
- Tree 함수들: `viewDef.tree_options` → `viewDef.hierarchy_options` + `viewDef.tree_display`
- Chart 함수들: `viewDef.chart_options` → `viewDef.hierarchy_options` + `viewDef.nested_table_display`

#### 5. 함수 리네이밍
- `renderChronostratChart()` → `renderNestedTableView()`
- `buildChartTree()` → `buildHierarchy()` (통합)
- `buildTreeFromFlat()` → 삭제 (`buildHierarchy`로 대체)

### 새 Manifest 스키마

```json
{
  "type": "hierarchy",
  "display": "tree | nested_table",
  "hierarchy_options": {
    "id_key": "id",
    "parent_key": "parent_id",
    "label_key": "name",
    "rank_key": "rank",
    "sort_by": "label | order_key",
    "order_key": "display_order",
    "skip_ranks": []
  },
  "tree_display": { "leaf_rank", "count_key", ... },
  "nested_table_display": { "color_key", "rank_columns", ... }
}
```

### 변경하지 않은 것
- HTML 컨테이너: `#view-tree`, `#view-chart` 그대로
- CSS: 변경 없음
- Python 백엔드: 변경 없음 (정규화는 클라이언트)
- 기존 manifest (DB의 `tree_options`/`chart_options`): `normalizeViewDef`로 자동 변환

## 테스트
- `pytest tests/ -x -q` → 231 passed
- 계획 문서: `devlog/20260216_P55_hierarchy_view_unification.md`
