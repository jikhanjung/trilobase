# 115: Profile Comparison Compound View + Morphing + UI 개선

**Date:** 2026-03-09
**Scope:** scoda-engine (runtime) + trilobase (manifest/DB)

## 개요

3개의 개별 compare 뷰(Diff Table, Diff Tree, Side-by-Side)를 하나의 **Profile Comparison** compound view로 통합하고, **Morphing** 애니메이션 뷰를 추가. 동시에 radial/rectangular tree 렌더링을 대폭 단순화하고 다수의 UX 개선을 적용.

## 주요 변경 사항

### 1. Compound View 구현 (`scoda-engine`)

- **`app.js`**: `loadCompoundView()`, `switchCompoundSubView()` — compound view 로딩 및 sub-view 탭 전환
- **`index.html`**: `view-compound` 컨테이너 추가
- **`validate_manifest.py`**: `'compound'` 타입을 `KNOWN_VIEW_TYPES`에 추가
- Sub-view 타입: `table`, `tree_chart`, `side_by_side`, `tree_chart_morph`
- 자체 컨트롤(From/To profile selector) 보유, global `compare_profile_id` 제거

### 2. Morphing 애니메이션 (`tree_chart.js`)

- **`loadMorph()`**: base/compare 두 트리를 빌드, layout, 스냅샷
- **`renderMorphFrame(t)`**: 두 스냅샷 간 위치/색상/투명도 보간
- **`startMorphAnimation()`**: 정방향/역방향 재생 지원, 현재 위치에서 이어 재생
- **`snapshotPositions()`**: `cx`, `cy`, `x`(angle), `y`(radius), `color`, `r` 저장
- **`snapshotLinks()`**: parent-child 연결 스냅샷
- **`_drawMorphLabels()`**: canvas 기반 label 렌더링 with fade in/out
- Morph 중 view-as-root 지원 (`_navigateMorphSubtree`, `_rebuildMorphFromFullTree`)
- **Transport controls**: |< (rewind), ◀ (backward), || (pause), ▶ (forward), >| (fast forward)
- Duration: `3200ms / speed`

### 3. 렌더링 단순화 (`tree_chart.js`)

- **SVG label 제거** → 모든 label을 canvas `drawLabels()`로 렌더링
- **zoom 의존적 크기 조절 제거** → 비트맵처럼 uniform scale
- **depth toggle 제거** (`depthHidden`, `setDepthHidden()` 등)
- **bitmap cache 제거** (`_cacheCanvas`, `_cacheCtx` 등)
- **동적 radius 조절 제거** (MIN_SPACING)
- **node/font 크기 고정**: radius=8, font=20px (textScale로 조절)

### 4. Text Scale 컨트롤

- `radiusScale` → `textScale`로 전환
- **A−/A+** 버튼: font 크기(20px × scale)와 노드 크기(8px × scale)를 직접 조절
- layout 재계산 불필요 — `render()`만 호출하므로 즉각 반응
- radial/rectangular 양쪽 모두 작동
- Side-by-Side에서 양쪽 동기화 (`onTextScaleSync`)

### 5. Radial tree link 통일

- 일반 트리: `quadraticCurveTo` 곡선
- Morph: 이전에는 `lineTo` 직선 → 이제 동일한 `quadraticCurveTo` 사용
- Rectangular: L자형 직각 연결, morph에서도 동일

### 6. Rectangular tree depth spacing 수정

- **문제**: view-as-root 시 `treeW = maxDepth * depthSpacing`이 작아져 rank alignment이 간격 압축
- **수정**: rank 간 간격을 `treeW` 비례가 아닌 **present rank 수 × depthSpacing** 기반으로 계산
- Morph에서 두 트리 bounds를 max로 통합

### 7. genera_count 동적 계산

- **문제**: `taxonomy_tree` 쿼리의 genera_count가 정적 필드(default profile 고정)
- **이전 시도**: per-row recursive CTE subquery → **10초** 소요
- **최종 해결**:
  - `taxonomy_tree` 쿼리: genera_count=0 placeholder
  - `taxonomy_tree_genera_counts` 쿼리 추가: genus의 직접 parent별 count (**9ms**)
  - JS `loadTree()`에서 fetch 후 트리에서 하위→상위로 합산 전파
- **결과**: 10,310ms → 9ms (1000x+ 개선)

### 8. Global Loading Indicator

- `fetchQuery()` 호출 시 자동 표시/숨김
- **Loading bar**: navbar 아래 4px animated gradient bar
- **Wait cursor**: `body.loading-active` class로 전체 cursor:wait
- 여러 fetch 동시 진행 시 모두 끝날 때까지 유지, 캐시 히트 시 미표시

### 9. 기타 UI 개선

- **Show Text / Hide Text** 토글: 상위 탭 바에서 모든 탭 label 표시/숨김
- **Classification Profile** label 명시 (이전: "Classification")
- **Sub-view 탭명 변경**: Table→Diff Table, Tree→Diff Tree, Morph→Morphing
- **Radial tree fit margin**: 10% margin 추가로 바깥쪽 label 표시
- **LEAF_GAP/SUBTREE_GAP 두 배**: rectangular tree leaf 간격 12/16
- **computeFitTransform**: radial에 10% margin, rectangular padding=120

## 파일 변경 목록

### scoda-engine (runtime)
- `scoda_engine/static/js/tree_chart.js` — 핵심 변경 (morph, rendering, text scale, layout)
- `scoda_engine/static/js/app.js` — compound view, loading indicator, Show Text, genera count
- `scoda_engine/static/css/style.css` — compound view, morph controls, loading bar, text scale buttons
- `scoda_engine/templates/index.html` — compound container, loading bar
- `core/scoda_engine_core/validate_manifest.py` — compound view type 추가

### trilobase (domain data)
- `scripts/create_assertion_db.py` — compound view manifest, 쿼리 최적화, 버전 0.1.6
- `db/trilobase-assertion-0.1.6.db` — 재생성

## 버전

- trilobase-assertion: 0.1.5 → **0.1.6**
- scoda-engine: **0.2.1** (변경 없음, 기능 추가만)

## 테스트

- Profile 전환 시 genera_count 정확성 확인 (profile 1 vs 2 vs 3)
- Morph 정방향/역방향/scrubber/view-as-root 작동 확인
- Side-by-Side text scale 동기화 확인
- Rectangular/Radial layout 전환 시 morph re-snapshot 확인
- View-as-root 시 depth spacing 일관성 확인
