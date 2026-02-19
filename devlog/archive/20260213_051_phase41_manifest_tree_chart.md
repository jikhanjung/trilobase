# Phase 41: Manifest-Driven Tree & Chart Rendering

**Date:** 2026-02-13
**Status:** Complete

## 목표

Phase 39에서 detail/table 뷰를 manifest-driven으로 전환했지만 tree 뷰와 ICS chart는 여전히 `app.js`에 하드코딩되어 있었음. manifest의 `tree_options`/`chart_options`를 확장하여 JS 렌더러가 manifest에서 설정을 읽도록 리팩터링.

## 변경 내역

### Phase 41a: Manifest Schema 확장

`scripts/add_scoda_manifest.py`:
- `taxonomy_tree.options` → `taxonomy_tree.tree_options` 이름 변경 + 확장
  - `id_key`, `parent_key`, `label_key`, `rank_key`, `leaf_rank`, `count_key`
  - `on_node_info`: info 버튼 클릭 → detail view
  - `item_query`, `item_param`: Family 선택 시 named query 실행
  - `item_columns`: genera 테이블 컬럼 정의 (key, label, italic, truncate)
  - `on_item_click`: genera 행 클릭 → detail view
  - `item_valid_filter`: Valid only 필터 설정 (key, label, default)
- `chronostratigraphy_table.chart_options` 확장
  - `id_key`, `parent_key`, `label_key`, `color_key`, `order_key`, `rank_key`
  - `skip_ranks`: 건너뛸 rank 목록 (`["Super-Eon"]`)
  - `rank_columns`: 컬럼별 rank + label 배열 (6개)
  - `value_column`: 값 컬럼 설정 (`start_mya`, "Age (Ma)")

### Phase 41b: Tree 렌더러 리팩터링

`static/js/app.js`:
- **`buildTreeFromFlat(rows, opts)`** 신규: flat rows → client-side tree building (parent_key 기반)
- **`loadTree()`**: `fetch('/api/tree')` → manifest `source_query` → `/api/queries/taxonomy_tree/execute` → `buildTreeFromFlat()` (fallback to legacy API)
- **`createTreeNode()`**: 하드코딩 → manifest `tree_options`에서 읽기
  - `leaf_rank`: leaf 판정 (`node.rank === 'Family'` → `node[rankKey] === opts.leaf_rank`)
  - `on_node_info`: info 버튼 타겟 (하드코딩 `rank_detail` → manifest 설정)
  - `count_key`: 카운트 표시 키
- **`selectTreeLeaf()`** 신규 (구 `selectFamily()`):
  - `/api/family/{id}/genera` → manifest `item_query`/`item_param` → named query 실행
  - `selectFamily()` → `selectTreeLeaf()` 위임 (하위 호환)
- **`renderTreeItemTable()`** 신규 (구 `renderGeneraTable()`):
  - 컬럼 5개 하드코딩 → `tree_options.item_columns`에서 읽기
  - Valid 필터: `tree_options.item_valid_filter`에서 읽기
- **Dead code 제거**: 7개 wrapper 함수 삭제 (모두 `renderDetailFromManifest()` 호출만)
  - `showGenusDetail()`, `showCountryDetail()`, `showChronostratDetail()`
  - `showRegionDetail()`, `showFormationDetail()`, `showBibliographyDetail()`
  - `showRankDetail()`
- **초기화 순서 수정**: `loadManifest()` 완료 후 `loadTree()` 호출 (await)

### Phase 41c: Chart 렌더러 리팩터링

`static/js/app.js`:
- **`RANK_COL` 상수 + `COL_COUNT` 상수 제거**
  - `chart_options.rank_columns`에서 `rankColMap` 동적 생성
- **`buildChartTree(rows, opts)`**: `parent.rank === 'Super-Eon'` → `opts.skip_ranks.includes(...)` — manifest에서 읽기
- **`hasSubPeriodChild()` → `hasDirectChildRank()`**: 범용화
  - `c.rank === 'Sub-Period'` → `rankColMap[c[rankKey]] === parentCol + 1`
- **`collectLeafRows()`**: `RANK_COL` → `rankColMap` 참조로 변경
- **`renderChartHTML(leafRows, opts)`**: headers/colors/clicks 모두 manifest에서 읽기

### Phase 41d: 테스트 + 문서

`test_app.py`:
- Test fixture manifest 갱신 (tree_options, chart_options 확장)
- `TestManifestTreeChart` 클래스 신규 (8개 테스트):
  - `test_tree_view_has_tree_options` — tree_options 존재 + 필수 키 확인
  - `test_tree_options_item_query_exists` — item_query가 실제 named query인지
  - `test_tree_options_item_columns` — item_columns 배열 구조
  - `test_tree_options_on_node_info` — on_node_info.detail_view가 manifest views에 존재
  - `test_chart_options_rank_columns` — rank_columns 배열 구조
  - `test_chart_options_value_column` — value_column 존재
  - `test_chart_options_skip_ranks` — skip_ranks 리스트
  - `test_tree_options_no_legacy_options` — legacy 'options' 키 부재 확인

## 테스트 결과

| 파일 | 테스트 수 | 상태 |
|------|---------|------|
| `test_app.py` | 185개 | ✅ 통과 |
| `test_mcp_basic.py` | 1개 | ✅ 통과 |
| `test_mcp.py` | 16개 | ✅ 통과 |
| **합계** | **202개** | **✅ 전부 통과** |

## app.js 줄 수 변화

- 이전: 1,473줄
- 이후: 1,537줄
- Dead code 제거: -50줄 (7개 wrapper 함수)
- 신규 함수: +64줄 (`buildTreeFromFlat`, `selectFamily` alias)
- 하드코딩→manifest 리팩터링: manifest 읽기 코드 추가로 +50줄

## 하위 호환성

- `/api/tree` 엔드포인트 유지 (fallback으로 사용)
- `/api/family/{id}/genera` 엔드포인트 유지 (기존 테스트 통과)
- `selectFamily()` 함수 유지 (`selectTreeLeaf()`로 위임)
- `app.py` 변경 없음
