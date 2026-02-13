# Plan: Phase 41 — Manifest-Driven Tree & Chart Rendering

## Context

Phase 39에서 detail/table 뷰를 manifest-driven으로 전환했지만, **tree 뷰**와 **ICS chart**는 여전히 `app.js`에 하드코딩. 현재 manifest에 `taxonomy_tree`/`chronostratigraphy_table`이 선언되어 있지만 렌더러가 그 정보를 사용하지 않음.

목표: manifest의 `tree_options`/`chart_options`를 확장하여 JS 렌더러가 **어떤 데이터든 tree/chart로 그릴 수 있는 범용 엔진**이 되도록 리팩터링.

## 핵심 전략

1. **Tree**: 현재 `/api/tree` (서버 사이드 재귀) 대신 named query `taxonomy_tree` (flat list + parent_id) → **클라이언트 사이드 트리 빌딩**. ICS chart가 이미 이 패턴을 사용 중.
2. **Genera 패널**: 현재 `/api/family/{id}/genera` 하드코딩 → manifest `item_query: "family_genera"` + `item_param: "family_id"` (named query 실행)
3. **ICS Chart**: 현재 `RANK_COL` 상수 + `'Super-Eon'` 하드코딩 → manifest `rank_columns` + `skip_ranks` 설정
4. **Dead code 정리**: 사용되지 않는 wrapper 함수 제거

## 파일 변경 목록

| 파일 | 변경 내용 |
|------|-----------|
| `scripts/add_scoda_manifest.py` | `tree_options` 확장, `chart_options` 확장 |
| `trilobase.db` | ui_manifest 업데이트 (스크립트 재실행) |
| `static/js/app.js` | tree/chart 렌더러 manifest-driven 리팩터링 + dead code 제거 |
| `test_app.py` | manifest 구조 테스트 추가 (tree_options, chart_options 검증) |

**변경하지 않는 파일:** `app.py` (API 엔드포인트 유지, 하위호환), `templates/index.html`, `scoda_package.py`

---

## Phase 41a: Manifest Schema 확장

### `taxonomy_tree` — tree_options 확장

현재:
```json
"options": {
    "root_rank": "Class",
    "leaf_rank": "Family",
    "show_genera_count": true,
    "node_info_detail": "rank_detail",
    "genera_row_click": {"detail_view": "genus_detail", "id_key": "id"}
}
```

변경 → `tree_options`로 이름 변경 + 확장:
```json
"tree_options": {
    "id_key": "id",
    "parent_key": "parent_id",
    "label_key": "name",
    "rank_key": "rank",
    "leaf_rank": "Family",
    "count_key": "genera_count",
    "on_node_info": {"detail_view": "rank_detail", "id_key": "id"},
    "item_query": "family_genera",
    "item_param": "family_id",
    "item_columns": [
        {"key": "name", "label": "Genus", "italic": true},
        {"key": "author", "label": "Author"},
        {"key": "year", "label": "Year"},
        {"key": "type_species", "label": "Type Species", "truncate": 40},
        {"key": "location", "label": "Location", "truncate": 30}
    ],
    "on_item_click": {"detail_view": "genus_detail", "id_key": "id"},
    "item_valid_filter": {"key": "is_valid", "label": "Valid only", "default": true}
}
```

핵심: named query `taxonomy_tree`가 이미 `id, name, rank, parent_id, author, genera_count`를 flat으로 반환함 → 클라이언트에서 트리 빌딩 (ICS chart의 `buildChartTree`와 동일 패턴).

### `chronostratigraphy_table` — chart_options 확장

현재:
```json
"chart_options": {
    "cell_click": {"detail_view": "chronostrat_detail", "id_key": "id"}
}
```

변경:
```json
"chart_options": {
    "id_key": "id",
    "parent_key": "parent_id",
    "label_key": "name",
    "color_key": "color",
    "order_key": "display_order",
    "rank_key": "rank",
    "skip_ranks": ["Super-Eon"],
    "rank_columns": [
        {"rank": "Eon", "label": "Eon"},
        {"rank": "Era", "label": "Era"},
        {"rank": "Period", "label": "System / Period"},
        {"rank": "Sub-Period", "label": "Sub-Period"},
        {"rank": "Epoch", "label": "Series / Epoch"},
        {"rank": "Age", "label": "Stage / Age"}
    ],
    "value_column": {"key": "start_mya", "label": "Age (Ma)"},
    "cell_click": {"detail_view": "chronostrat_detail", "id_key": "id"}
}
```

### 작업

- `scripts/add_scoda_manifest.py` 수정
- `python scripts/add_scoda_manifest.py` 실행하여 DB 업데이트

---

## Phase 41b: Tree 렌더러 리팩터링

### `loadTree()` 변경

현재: `fetch('/api/tree')` → nested JSON → `createTreeNode()`

변경: manifest `source_query` → `fetch('/api/queries/taxonomy_tree/execute')` → flat rows → 클라이언트 트리 빌딩 → `createTreeNode()`

```
[Before] /api/tree → 서버 재귀 빌딩 → nested {id, name, children: [...]}
[After]  /api/queries/taxonomy_tree/execute → flat [{id, name, parent_id, ...}]
         → buildTreeFromFlat(rows, opts) → nested tree → createTreeNode()
```

`buildTreeFromFlat(rows, opts)` 함수: flat rows를 parent_id 기반으로 nested tree로 변환. ICS chart의 `buildChartTree()`와 유사하지만 범용.

### `createTreeNode(node)` 변경

현재 하드코딩:
- `node.rank === 'Family'` → leaf 판정
- info 버튼: `openDetail('rank_detail', node.id)` 직접 호출

변경: manifest `tree_options`에서 읽기
- `opts.leaf_rank` → leaf 판정
- `opts.on_node_info.detail_view` → info 버튼 타겟

### `selectFamily()` → `selectTreeLeaf()` 변경

현재: `/api/family/${familyId}/genera` 하드코딩

변경: named query 실행
```javascript
const opts = manifest.views['taxonomy_tree'].tree_options;
const url = `/api/queries/${opts.item_query}/execute?${opts.item_param}=${leafId}`;
```
→ `response.rows` 를 사용하여 테이블 렌더링

### `renderGeneraTable()` → `renderTreeItemTable()` 변경

현재: 컬럼 5개 하드코딩 (Genus, Author, Year, Type Species, Location)

변경: `tree_options.item_columns`에서 읽기 (table view 렌더러와 동일 패턴)

Valid 필터: `tree_options.item_valid_filter`에서 읽기 (key, label, default)

### Dead code 제거

다음 wrapper 함수 삭제 (모두 `renderDetailFromManifest()` 호출만 함, 외부에서 미사용):
- `showGenusDetail()`, `showCountryDetail()`, `showChronostratDetail()`
- `showRegionDetail()`, `showFormationDetail()`, `showBibliographyDetail()`
- `showRankDetail()`

---

## Phase 41c: Chart 렌더러 리팩터링

### `RANK_COL` 상수 제거

현재:
```javascript
const RANK_COL = {'Eon': 0, 'Era': 1, 'Period': 2, 'Sub-Period': 3, 'Epoch': 4, 'Age': 5};
const COL_COUNT = 7;
```

변경: `chart_options.rank_columns`에서 동적 생성
```javascript
const rankColMap = {};
opts.rank_columns.forEach((rc, i) => { rankColMap[rc.rank] = i; });
```

### `buildChartTree()` 변경

현재: `parent.rank === 'Super-Eon'` 하드코딩

변경: `opts.skip_ranks.includes(parent[opts.rank_key])` — manifest에서 읽기

### `renderChartHTML()` 변경

현재: headers 배열 하드코딩 `['Eon', 'Era', 'System / Period', ...]`

변경: `opts.rank_columns.map(rc => rc.label)` + `opts.value_column.label`

### `collectLeafRows()` 변경

`RANK_COL` → `rankColMap` 참조로 변경. 나머지 rowspan/colspan 알고리즘은 그대로 유지 (이미 범용적임).

### `hasSubPeriodChild()` → `hasDirectChildRank()` 변경

현재: `c.rank === 'Sub-Period'` 하드코딩

변경: rank_columns 인덱스 기반으로 일반화:
```javascript
// parent가 column N이면, child가 column N+1인지 확인
function hasDirectChildRank(node, parentCol, rankColMap, rankKey) {
    return node.children.some(c => rankColMap[c[rankKey]] === parentCol + 1);
}
```

---

## Phase 41d: 테스트 + 문서

### 테스트 추가

`test_app.py`에 `TestManifestTreeChart` 클래스:
- `test_tree_view_has_tree_options` — tree_options 존재 + 필수 키 확인
- `test_tree_options_item_query_exists` — `item_query`가 실제 존재하는 named query인지
- `test_tree_options_item_columns` — item_columns 배열 구조
- `test_chart_view_has_chart_options` — chart_options 확장 키 확인
- `test_chart_options_rank_columns` — rank_columns 배열 구조
- `test_chart_options_value_column` — value_column 존재

기존 테스트: `/api/tree`, `/api/family/{id}/genera` 엔드포인트는 유지하므로 기존 테스트 변경 없음.

### 문서

- devlog: `devlog/20260213_051_phase41_manifest_tree_chart.md`
- `docs/HANDOVER.md` 갱신

---

## 검증 방법

1. `pytest test_app.py test_mcp_basic.py test_mcp.py` — 전체 통과 (194 기존 + ~6 신규 = ~200)
2. `python -c "from app import app; ..."` — manifest API 응답에 tree_options/chart_options 확인
3. **브라우저 수동 테스트**: `python app.py` → http://localhost:8080
   - Taxonomy Tree 탭: 트리 정상 렌더링, Family 클릭 → 오른쪽 genera 목록
   - Chronostratigraphy 탭: ICS 차트 정상 렌더링, 셀 클릭 → 상세 모달
   - 나머지 탭/detail: 기존과 동일 동작

## app.js 줄 수 변화 예상

- 현재: 1,473줄
- Dead code 제거: ~50줄
- 하드코딩 → manifest 읽기 리팩터링: 순 변화 ±0 (로직 동일, 소스만 변경)
- 예상 결과: ~1,420줄
