# P55: Hierarchy View 일반화 (tree + nested_table 통합)

## Context

Generic viewer에 hierarchical data 렌더러가 2개:
- `type: "tree"` — 펼치기/접기 트리 + leaf 아이템 테이블 (`buildTreeFromFlat()` line 533)
- `type: "chart"` — colspan/rowspan nested table (`buildChartTree()` line 338)

둘 다 같은 입력(`id`, `parent_id`, `name`, `rank` flat rows) → 트리 빌드 함수가 별도 구현.
차이는 sort 방식(label vs order_key)과 skip_ranks 처리뿐.

**목표**: `type: "hierarchy"` + `display` 속성으로 통합, 공유 트리 빌더 추출.

## 새 Manifest 스키마

```json
{
  "type": "hierarchy",
  "display": "tree | nested_table",
  "source_query": "...",
  "hierarchy_options": {
    "id_key": "id",
    "parent_key": "parent_id",
    "label_key": "name",
    "rank_key": "rank",
    "sort_by": "label | order_key",
    "order_key": "display_order",
    "skip_ranks": []
  },
  "tree_display": { ... },
  "nested_table_display": { ... }
}
```

### `hierarchy_options` (공통)

| 필드 | 기본값 | 설명 |
|------|--------|------|
| `id_key` | `"id"` | PK |
| `parent_key` | `"parent_id"` | 부모 참조 |
| `label_key` | `"name"` | 표시 텍스트 |
| `rank_key` | `"rank"` | 계층 레벨 |
| `sort_by` | `"label"` | 정렬: `"label"` (알파벳) or `"order_key"` (숫자) |
| `order_key` | `"id"` | sort_by=order_key일 때 기준 |
| `skip_ranks` | `[]` | 건너뛸 rank (자식을 루트로 승격) |

### `tree_display` (tree 전용, 기존 tree_options에서 분리)

`leaf_rank`, `count_key`, `on_node_info`, `item_query`, `item_param`,
`item_columns`, `on_item_click`, `item_valid_filter`

### `nested_table_display` (nested_table 전용, 기존 chart_options에서 분리)

`color_key`, `rank_columns`, `value_column`, `cell_click`

## 변경 사항 — `scoda_desktop/static/js/app.js` only

### 1. `buildHierarchy(rows, opts)` 추가

`buildTreeFromFlat()` (line 533)과 `buildChartTree()` (line 338) 통합:

```javascript
function buildHierarchy(rows, opts) {
    const idKey = opts.id_key || 'id';
    const parentKey = opts.parent_key || 'parent_id';
    const labelKey = opts.label_key || 'name';
    const rankKey = opts.rank_key || 'rank';
    const sortBy = opts.sort_by || 'label';
    const orderKey = opts.order_key || 'id';
    const skipRanks = opts.skip_ranks || [];
    // byId 맵 → parent-child 연결 (skip_ranks 처리) → sort
}
```

→ `buildTreeFromFlat()`, `buildChartTree()` 삭제

### 2. `normalizeViewDef(viewDef)` 추가

`loadManifest()` 직후 모든 view에 적용:

| 입력 | 출력 |
|------|------|
| `type: "tree"` + `tree_options` | `type: "hierarchy"`, `display: "tree"`, `hierarchy_options` + `tree_display` |
| `type: "chart"` + `chart_options` | `type: "hierarchy"`, `display: "nested_table"`, `hierarchy_options` + `nested_table_display` |
| 그 외 | 그대로 통과 |

### 3. `switchToView()` dispatch 변경

```javascript
// Before:
if (view.type === 'tree') { ... }
else if (view.type === 'chart') { ... }

// After:
if (view.type === 'hierarchy') {
    if (view.display === 'tree') { treeContainer; loadTree(); }
    else if (view.display === 'nested_table') { chartContainer; renderNestedTableView(); }
}
```

### 4. Tree 함수 옵션 경로 변경

`loadTree()`, `createTreeNode()`, `selectTreeLeaf()`, `renderTreeItemTable()`:
- `viewDef.tree_options` → `viewDef.hierarchy_options` + `viewDef.tree_display`

### 5. Chart 함수 이름 + 옵션 경로 변경

- `renderChronostratChart()` → `renderNestedTableView()`
- `viewDef.chart_options` → `viewDef.hierarchy_options` + `viewDef.nested_table_display`
- `buildChartTree()` → `buildHierarchy()` 호출

## 변경하지 않는 것

- HTML 컨테이너: `#view-tree`, `#view-chart` 그대로
- CSS: 변경 없음
- Python 백엔드: 변경 없음 (정규화는 클라이언트)
- manifest 스크립트: 선택사항 (기존 형식도 normalizeViewDef로 동작)

## Verification

1. `pytest tests/ -x -q` — 231 tests pass
2. 브라우저: taxonomy tree 동작 (펼치기/접기, leaf 클릭, detail 모달)
3. 브라우저: chronostratigraphy nested table 동작 (색상, rowspan, cell 클릭)
