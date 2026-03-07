# 112: Side-by-Side Tree Chart — R02 Phase B~D 구현

**날짜:** 2026-03-07
**DB:** trilobase-assertion-0.1.5.db
**Related:** P03 (devlog/20260307_P03_side_by_side_tree_refactoring.md), R02 (devlog/20260302_R02_tree_diff_visualization.md)

## 개요

두 classification profile의 tree chart를 좌우로 나란히 보여주는 Side-by-Side 뷰를 구현했다.
이를 위해 `tree_chart.js`의 전역 상태를 `TreeChartInstance` 클래스로 리팩토링하고,
듀얼 인스턴스 렌더링 + zoom/layout 동기화를 완성했다.

## scoda-engine 변경

### Phase A: TreeChartInstance 클래스 추출 (tree_chart.js)

기존 1,385줄의 전역 상태/함수를 클래스 기반으로 전환.

**전역 변수 → 인스턴스 멤버:**
- `radialRoot`, `radialCanvas`, `radialCtx`, `radialZoom` 등 20+개 → `this.root`, `this.canvas`, `this.ctx`, `this.zoom` 등
- `treeLayoutMode`, `cladoBoundsW/H` → `this.layoutMode`, `this.cladoBoundsW/H`

**전역 함수 → 클래스 메서드:**
- `buildRadialHierarchy()` → `buildHierarchy()`
- `computeLayout()`, `computeRadialLayout()`, `computeCladogramLayout()` → 인스턴스 메서드
- `renderRadial()` → `render()`
- `setupRadialZoom()` → `setupZoom()`
- `onRadialMouseMove/Click/ContextMenu` → `onMouseMove/onClick/onContextMenu`
- `radialSearch()` → `search()`
- 기타 30+ 함수 모두 메서드화

**DOM 요소 핸들링:**
- 하드코딩된 `document.getElementById('tc-canvas')` 등 → 생성자 옵션 (`wrapEl`, `toolbarEl`, `tooltipEl` 등)
- canvas/svg를 `load()` 시 동적 생성 (HTML에서 초기 요소 제거)
- context menu/breadcrumb: inline `onclick` → `addEventListener` (인스턴스 바인딩)

**CSS:**
- `#tc-canvas`, `#tc-labels` ID 셀렉터 → `.tc-canvas-wrap canvas`, `.tc-canvas-wrap svg` 클래스 기반

**overrideParams:**
- 인스턴스별 `fetchQuery()` 호출 시 `globalControls`를 override 가능
- Side-by-side에서 right 패널이 `{ profile_id: compare_profile_id }`로 다른 프로필 로드

**기존 진입점 유지:**
```js
async function loadRadialView(viewKey) {
    // 내부에서 singleton TreeChartInstance 생성
    _singletonTC = new TreeChartInstance({ wrapEl, toolbarEl, ... });
    await _singletonTC.load(viewKey);
}
```

### Phase B: Side-by-Side 컨테이너

**index.html:**
```html
<div id="view-side-by-side">
  <div class="sbs-view-content">
    <div class="tc-toolbar" id="sbs-toolbar"></div>
    <div class="sbs-panels">
      <div class="sbs-panel" id="sbs-left">
        <div class="sbs-panel-header" id="sbs-left-header"></div>
        <div class="tc-canvas-wrap" id="sbs-left-wrap"></div>
        <div class="tc-breadcrumb" id="sbs-left-breadcrumb"></div>
      </div>
      <div class="sbs-panel" id="sbs-right">...</div>
    </div>
    <div class="tc-tooltip" id="sbs-tooltip"></div>
    <div class="tc-context-menu" id="sbs-context-menu"></div>
  </div>
</div>
```

**app.js:**
- `display: "side_by_side"` 뷰 타입 인식
- `switchToView()`에서 `view-side-by-side` 컨테이너 show/hide

**style.css:**
- `.sbs-panels`: flex 레이아웃 (50:50 분할)
- `.sbs-panel`: 좌우 패널 (border-right 구분선)
- `.sbs-panel-header`: 프로필 이름 표시 (absolute positioning)

### Phase C: 듀얼 렌더링 (loadSideBySideView)

```js
async function loadSideBySideView(viewKey) {
    // Left: base profile (globalControls.profile_id)
    _sbsLeft = new TreeChartInstance({
        wrapEl: sbs-left-wrap, toolbarEl: sbs-toolbar, ...
    });
    // Right: compare profile (override profile_id)
    _sbsRight = new TreeChartInstance({
        wrapEl: sbs-right-wrap, toolbarEl: null,
        overrideParams: { profile_id: compare_profile_id },
    });
    await Promise.all([_sbsLeft.load(...), _sbsRight.load(...)]);
}
```

- 프로필 이름을 `classification_profiles_selector` 쿼리로 조회하여 패널 헤더에 표시
- Toolbar는 left 패널만 빌드 (공유)
- Tooltip/context menu도 공유

### Phase D: 동기화

**Zoom/Pan 동기화:**
- 한쪽 zoom 이벤트 → 다른 쪽 `d3.select(canvas).call(zoom.transform, ...)` 호출
- `syncing` flag로 무한 루프 방지

**Layout mode 동기화:**
- `switchLayout()` override: 한쪽 radial↔rectangular 전환 시 다른 쪽도 함께

## trilobase 변경

**`scripts/create_assertion_db.py`:**
- `side_by_side_tree` 뷰 선언 추가
  - `type: "hierarchy"`, `display: "side_by_side"`, `compare_view: True`
  - `tree_chart_options.source_view: "tree_chart"` — 기존 tree_chart 뷰 설정 재사용

## UX 변경

**Compare 버튼 제거:**
- 이전: 전역 Compare 토글 버튼으로 compare 모드 진입
- 이후: Profile Diff / Side-by-Side 탭 클릭 시 자동으로 compare 모드 활성화
- 다른 탭으로 이동하면 자동 비활성화 (compare_profile_id 셀렉터 숨김)

## 파일별 변경 요약

| 파일 | Repo | 변경 |
|------|------|------|
| `static/js/tree_chart.js` | scoda-engine | 전역→클래스 리팩토링, loadSideBySideView(), zoom sync |
| `static/js/app.js` | scoda-engine | side_by_side display 라우팅, Compare 버튼 제거 |
| `static/css/style.css` | scoda-engine | sbs-* 스타일, CSS ID→class 셀렉터 |
| `templates/index.html` | scoda-engine | view-side-by-side 컨테이너, canvas/svg 초기 요소 제거 |
| `scripts/create_assertion_db.py` | trilobase | side_by_side_tree 뷰 선언 |

## 실행 방법

```bash
python scripts/create_scoda.py  # treatise 프로필 포함 전체 빌드
python -m scoda_engine.serve --db-path db/trilobase-assertion-0.1.5.db --mode admin --port 8090
# Profile Diff 탭 → compare 셀렉터 나타남
# Side-by-Side 탭 → 좌우 tree chart 나란히 표시
```

## 다음 단계

- R02 Phase 2: Diff Tree — 단일 tree chart에서 diff 색상 코딩 (moved/added/removed)
- Side-by-side에서 depth toggle 동기화
- Side-by-side에서 hover 하이라이트 동기화 (한쪽 hover → 다른 쪽 같은 taxon 표시)
