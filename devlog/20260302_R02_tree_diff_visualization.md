# R02: 두 Classification Profile의 시각적 비교 방법

**Date:** 2026-03-02
**Type:** Review (설계 탐색)
**Related:** R01 (taxonomy management), P79 (profile selector UI), scoda-engine P23/032 (tree chart layout mode)

## 배경

### 현재 상황

assertion DB에는 복수의 `classification_profile`이 있고, 각각 다른 edge cache를 통해 서로 다른 taxonomy tree를 구성한다.

| Profile | Edge 수 | 설명 |
|---------|---------|------|
| default (id=1) | 5,083 | JA2002 + A2011 accepted |
| ja2002_strict (id=2) | (미구축) | JA2002만 |
| treatise2004 (id=3) | 5,138 | default + Treatise override |

현재 UI에서는 global dropdown으로 프로필을 **전환**할 수만 있다. 프로필 A에서 B로 바꾸면 전체 트리가 처음부터 다시 그려지며, 이전 상태와의 관계가 사라진다.

### 핵심 특성

두 프로필 간 차이의 특성:
- **대부분 동일**: default와 treatise2004는 ~95%+ edge가 같음
- **차이 집중**: Agnostida/Redlichiida subtree에 변화 집중
- **변화 유형**: 이동(moved), 추가(added), 삭제(removed), 계층 심화(Subfamily 추가)
- **노드 공유**: 같은 `taxon.id` 집합을 공유. edge(parent-child 관계)만 다름

### 아키텍처 현황 (scoda-engine P23/032 반영)

scoda-engine P23/032에서 `radial.js` → `tree_chart.js`로 리네이밍되고,
radial + rectangular 두 가지 레이아웃 모드를 toolbar 토글로 전환 가능하게 됨.

| 항목 | Before (P23 이전) | After (P23/032) |
|------|-------------------|-----------------|
| 파일 | `radial.js` | `tree_chart.js` |
| manifest display | `"radial"` | `"tree_chart"` (backward compat: `"radial"` 자동 변환) |
| manifest 옵션 키 | `radial_display` | `tree_chart_options` (backward compat 지원) |
| HTML ID/CSS class | `radial-*` | `tc-*` |
| 레이아웃 | radial만 | radial + rectangular (toolbar 토글) |
| 레이아웃 디스패처 | `computeRadialLayout()` 직접 호출 | `computeLayout()` → 모드별 분기 |
| 렌더링 분기 | radial 전용 | `treeLayoutMode` 체크: drawGuideLines, drawLinks, updateLabels 모두 분기 |

> **내부 JS 변수명은 유지됨**: `radialRoot`, `radialCanvas`, `buildRadialHierarchy()` 등은
> 리팩토링 범위 최소화를 위해 그대로 유지 (P23 기술 결정).

| 항목 | 현재 상태 |
|------|----------|
| 렌더링 | Canvas(즉시 모드) + SVG(라벨). 장면 그래프 없음 |
| 트리 빌드 | profile 전환 시 full teardown → rebuild |
| 노드 애니메이션 | 없음 (zoom 전환만 D3 transition 사용) |
| 레이아웃 모드 | radial (방사형) + rectangular (직각 분지도), toolbar 토글 |
| 색상 | rank별 palette (d3.schemeTableau10) |
| 데이터 분리 | nodes(profile 무관) / edges(profile 의존) — diff에 유리 |
| 쿼리 | `fetchQuery()` 가 항상 `globalControls` 병합 |

---

## 프로필 선택 인터페이스

비교를 하려면 두 프로필을 선택해야 한다. 선택 UI 패턴 3가지를 검토.

### 패턴 A: Compare 모드 토글 (추천)

```
[Normal mode]
  Classification: [default ▾]                ← 기존 global_controls 그대로

[Compare 버튼 클릭 → Compare mode]
  Base:    [default ▾]    Compare: [treatise2004 ▾]    ← 두 번째 셀렉터 등장
```

- 평소에는 단일 셀렉터 (현재와 동일)
- Toolbar에 "Compare" 토글 버튼 → 활성화 시 두 번째 셀렉터 나타남
- 현재 보고 있던 프로필이 자동으로 Base(A)가 됨
- 사용자는 Compare(B)만 고르면 비교 시작

**장점**: 기존 UX 변경 최소. 비교 안 할 때 UI 깔끔. 구현 범위 최소.
**구현**: toolbar에 토글 버튼 1개 + 조건부 셀렉터 1개 (scoda-engine `app.js`)

### 패턴 B: Dual selector (항상 노출)

```
  Tree A: [default ▾]    Tree B: [treatise2004 ▾]    [Compare]
```

- B가 미선택이면 단일 뷰, 둘 다 선택되면 비교 뷰
- **장점**: 단순 명확
- **단점**: 비교 안 할 때도 공간 차지, "왜 두 개?" 혼란 가능

### 패턴 C: 체크박스 목록 (프로필 다수일 때)

```
  Available trees:
  ☑ default (JA2002 + A2011)
  ☑ treatise2004 (Treatise override)
  ☐ ja2002_strict
  [Compare selected]
```

- 프로필이 10개 이상일 때 유용. 메타데이터(연도/저자) 표시 가능.
- **단점**: 클릭 수 많음, 2개 제한 로직 필요

### 선택: 패턴 A

현재 SCODA 구조에서 **패턴 A**가 가장 자연스러움:
- `global_controls`의 profile selector가 이미 존재 → 이것이 Base(A) 역할
- Compare 모드 진입 시 두 번째 셀렉터만 추가
- 비교 안 할 때는 기존 UX 100% 유지
- 프로필 수가 적으므로 (2~5개) dropdown이면 충분

#### scoda-engine 구현 위치

`app.js`의 `renderGlobalControls()` 확장:
- Compare 토글 시 `compareMode = true` → `compare_profile_id` 셀렉터 생성
- 기존 `profile_id` 셀렉터와 동일한 `source_query` 사용
- Compare 해제 시 셀렉터 제거 + 단일 프로필 모드로 복원

#### manifest 계약 (trilobase)

```python
"global_controls": [
    {
        "type": "select",
        "param": "profile_id",
        "label": "Classification",
        "source_query": "classification_profiles_selector",
        ...
    },
    {
        "type": "select",
        "param": "compare_profile_id",
        "label": "Compare with",
        "source_query": "classification_profiles_selector",
        "value_key": "id",
        "label_key": "name",
        "default": 3,
        "compare_control": True,   # ← Compare 모드에서만 표시
    },
],
```

`compare_control: True`인 컨트롤은 Compare 모드 활성 시에만 렌더링.

---

## 비교 표시 모드 (Compare Display Modes)

비교 결과를 보여주는 형태를 사용자가 선택할 수 있게 한다.
모두 구현하되, 나중에 불필요한 것은 제거하는 방향.

### 지원 모드 4가지

| 모드 | 설명 | 적합한 상황 |
|------|------|------------|
| **Diff** | 단일 트리 + diff 색상 코딩 | 차이가 적을 때 (95%+ 동일). 가장 정보 밀도 높음 |
| **Side-by-side** | 좌/우 분할, 동기화 탐색 | 구조가 크게 다를 때. A/B 명확 구분 |
| **Overlay** | 같은 캔버스에 두 트리 겹침 | 위치 변화 시각적 파악. ghost 느낌 |
| **Table** | 차이 목록 테이블 | 정확한 데이터 확인. export/필터 |

### UI: 모드 선택 toolbar

Compare 모드 활성 시 추가 toolbar 영역:

```
[Compare mode toolbar]
  Base: [default ▾]  Compare: [treatise2004 ▾]
  Display: [Diff] [Side-by-side] [Overlay] [Table]
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^
                    toggle button group (하나만 active)
```

### 모드별 tree_chart_options.diff_mode 확장

```python
"diff_mode": {
    # 공통
    "edge_query": "profile_diff_edges",
    "edge_params": { "profile_a": "$profile_id", "profile_b": "$compare_profile_id" },
    "colors": { "same": "#adb5bd", "moved": "#fd7e14", "added": "#198754", "removed": "#dc3545" },

    # Diff 모드 전용
    "show_ghost_edges": True,

    # Side-by-side 전용 (scoda-engine이 해석)
    "side_by_side": {
        "sync_zoom": True,       # 좌우 zoom/pan 동기화
        "sync_collapse": True,   # 좌우 collapse/expand 동기화
        "highlight_hover": True, # 한쪽 hover → 다른 쪽 같은 노드 하이라이트
    },

    # Table 전용
    "diff_table_query": "profile_diff",
},
```

### 모드별 구현 위치

| 모드 | scoda-engine | trilobase |
|------|-------------|-----------|
| Diff (색상 코딩) | tree_chart.js: diff 색상, ghost edge, 범례 | diff_edges 쿼리, diff_mode 선언 |
| Side-by-side | tree_chart.js: 캔버스 2개 + 이벤트 동기화 | (추가 선언 없음) |
| Overlay | tree_chart.js: 두 edge set 겹쳐 그리기 (opacity 조절) | (추가 선언 없음) |
| Table | app.js: 기존 table 렌더링 재사용 | diff 쿼리 |

### Side-by-side 구현 개요 (scoda-engine)

```
┌─────────────── view-tree-chart ────────────────┐
│ ┌──── tc-canvas-a ────┐ ┌──── tc-canvas-b ────┐│
│ │                     │ │                     ││
│ │   Profile A tree    │ │   Profile B tree    ││
│ │                     │ │                     ││
│ └─────────────────────┘ └─────────────────────┘│
│        zoom/pan 동기화 ←→ zoom/pan 동기화       │
└─────────────────────────────────────────────────┘
```

- Canvas 2개를 `display: flex`로 배치
- 각각 독립적으로 `buildRadialHierarchy()` + `computeLayout()` 호출 (다른 profile_id)
- Zoom/Pan은 하나의 `d3.zoom`으로 공유하거나, 한쪽 이벤트를 다른 쪽에 mirror

### Overlay 구현 개요 (scoda-engine)

```
단일 캔버스에서:
1. Profile A edges: 실선, A color palette
2. Profile B edges: 점선, B color palette (또는 opacity 50%)
3. 노드: diff_status별 색상 (Diff 모드와 동일)
4. 동일한 edge는 한 번만 그리기 (중복 제거)
```

- Diff 모드의 확장 — 같은 캔버스에 두 edge set을 다른 스타일로 렌더
- Ghost edge 개념을 일반화: A only = 실선, B only = 점선, both = 실선

### 선택 UI와 표시 모드의 관계

```
                Compare 모드 토글 (패턴 A)
                         │
                         ▼
              ┌── 비교 표시 모드 선택 ──┐
              │                       │
    ┌─────────┼──────┬────────┬───────┤
    ▼         ▼      ▼        ▼       │
  Diff    Side-by  Overlay  Table     │
  (색상)   -side   (겹침)   (목록)     │
    │         │      │        │       │
    └─────────┼──────┴────────┘       │
              ▼                       │
     tree_chart_options.diff_mode     │
     에서 모드별 옵션 참조             │
              │                       │
              ▼                       ▼
         scoda-engine            trilobase
         (렌더링)               (쿼리/선언)
```

---

## 접근법 1: Diff Table (차이 목록 테이블)

### 개념

두 프로필의 edge를 비교하여 차이를 테이블로 보여준다. 가장 기본적인 비교 뷰.

```
┌──────────────────┬──────────────┬────────────────┬────────┐
│ Taxon            │ Profile A    │ Profile B      │ Status │
├──────────────────┼──────────────┼────────────────┼────────┤
│ Condylopygidae   │ → Agnostida  │ → Eodiscina    │ moved  │
│ Clavagnostus     │ (없음)       │ → Agnostidae   │ added  │
│ Weymouthia       │ → Eodiscidae │ (없음)         │ removed│
└──────────────────┴──────────────┴────────────────┴────────┘
```

### 구현 범위

#### trilobase (이 repo)

**`scripts/create_assertion_db.py`** — ui_queries에 diff 쿼리 추가:

```sql
-- profile_diff: 두 프로필 간 edge 차이
SELECT
    COALESCE(a.child_id, b.child_id) AS taxon_id,
    t.name AS taxon_name,
    t.rank AS taxon_rank,
    pa.name AS parent_a,
    pb.name AS parent_b,
    CASE
        WHEN a.child_id IS NULL THEN 'added'
        WHEN b.child_id IS NULL THEN 'removed'
        WHEN a.parent_id != b.parent_id THEN 'moved'
    END AS diff_status
FROM classification_edge_cache a
LEFT JOIN classification_edge_cache b
    ON a.child_id = b.child_id AND b.profile_id = :profile_b
LEFT JOIN taxon t ON t.id = COALESCE(a.child_id, b.child_id)
LEFT JOIN taxon pa ON pa.id = a.parent_id
LEFT JOIN taxon pb ON pb.id = b.parent_id
WHERE a.profile_id = :profile_a
    AND (b.child_id IS NULL OR a.parent_id != b.parent_id)

UNION ALL

SELECT
    b.child_id AS taxon_id,
    t.name AS taxon_name,
    t.rank AS taxon_rank,
    NULL AS parent_a,
    pb.name AS parent_b,
    'added' AS diff_status
FROM classification_edge_cache b
LEFT JOIN classification_edge_cache a
    ON b.child_id = a.child_id AND a.profile_id = :profile_a
LEFT JOIN taxon t ON t.id = b.child_id
LEFT JOIN taxon pb ON pb.id = b.parent_id
WHERE b.profile_id = :profile_b
    AND a.child_id IS NULL

ORDER BY diff_status, taxon_rank, taxon_name
```

**`scripts/create_assertion_db.py`** — manifest에 diff 뷰 추가:

```python
"profile_diff_table": {
    "type": "table",
    "title": "Profile Diff",
    "description": "Compare two classification profiles",
    "icon": "bi-arrows-expand",
    "source_query": "profile_diff",
    "params": {"profile_a": "$profile_id", "profile_b": "$compare_profile_id"},
    "columns": [
        {"key": "taxon_name", "label": "Taxon"},
        {"key": "taxon_rank", "label": "Rank"},
        {"key": "parent_a",   "label": "Profile A Parent"},
        {"key": "parent_b",   "label": "Profile B Parent"},
        {"key": "diff_status","label": "Status"},
    ],
}
```

manifest의 `global_controls`에 비교 대상 프로필 선택 컨트롤 추가:

```python
{
    "type": "select",
    "param": "compare_profile_id",
    "label": "Compare with",
    "source_query": "classification_profiles_selector",
    "value_key": "id",
    "label_key": "name",
    "default": 3,  # treatise2004
}
```

#### scoda-engine

**변경 없음** — 기존 table 뷰 + `fetchQuery()` + global_controls 인프라로 동작.
단, diff_status별 행 색상 하이라이트가 필요하면 아래 소규모 변경:

**`static/js/app.js`** — table 렌더링에서 `row_color_key` 지원 (선택적):

```js
// manifest에 row_color_key: "diff_status" 가 있으면
// 각 행의 diff_status 값에 따라 CSS class 적용
// moved → bg-warning-subtle, added → bg-success-subtle, removed → bg-danger-subtle
```

### 난이도: 낮음

- SQL 쿼리 + manifest 선언만으로 기본 동작
- scoda-engine 변경 최소 (행 색상만 선택적)

---

## 접근법 2: Diff Tree (단일 병합 트리 + 색상 코딩)

### 개념

기존 tree chart (radial/rectangular 양쪽 레이아웃)에 "diff mode"를 추가. 두 프로필의 edge를 합친(union) 트리를 그리되, 각 노드/edge의 diff 상태에 따라 색상을 부여한다. 두 레이아웃 모두에서 동작해야 한다.

```
시각적 결과:

         Trilobita (회색: 동일)
        ╱         ╲
  Agnostida       Redlichiida
  (회색)           (회색)
   ╱    ╲
Agnostina  Eodiscina
(회색)     (주황: 이동됨 — 다른 위치에서 옴)
  │          ╱     ╲
  │   Weymouthiidae  Eodiscidae
  │   (초록: B에만)   (회색)
  ...

색상 범례:
  ● 회색  — 양쪽 동일 (same)
  ● 주황  — parent 변경됨 (moved)
  ● 초록  — Profile B에만 존재 (added)
  ● 빨강  — Profile A에만 존재 (removed)
  ● 점선  — 원래 위치 (moved 노드의 A 위치 표시)
```

### 구현 범위

#### trilobase (이 repo)

**`scripts/create_assertion_db.py`** — diff 전용 edge 쿼리 추가:

```sql
-- profile_diff_edges: 두 프로필의 edge union + diff 상태
SELECT
    COALESCE(a.child_id, b.child_id) AS child_id,
    -- diff tree에서는 B(비교 대상)의 parent를 기본으로 사용
    COALESCE(b.parent_id, a.parent_id) AS parent_id,
    -- A의 parent (moved 표시용)
    a.parent_id AS parent_id_a,
    CASE
        WHEN a.child_id IS NULL THEN 'added'
        WHEN b.child_id IS NULL THEN 'removed'
        WHEN a.parent_id != b.parent_id THEN 'moved'
        ELSE 'same'
    END AS diff_status
FROM classification_edge_cache a
FULL OUTER JOIN classification_edge_cache b
    ON a.child_id = b.child_id AND b.profile_id = :profile_b
WHERE (a.profile_id = :profile_a OR a.profile_id IS NULL)
ORDER BY child_id
```

> **참고**: SQLite는 FULL OUTER JOIN을 3.39.0+ (2022-09-05)에서 지원. 이전 버전이면 LEFT JOIN + UNION + RIGHT JOIN 으로 에뮬레이션 필요.

manifest의 tree chart 뷰에 diff 모드 옵션 추가:

```python
"tree_chart_options": {
    # ... 기존 설정 (edge_query, rank_radius, default_layout 등) ...
    "diff_mode": {
        "edge_query": "profile_diff_edges",
        "edge_params": {
            "profile_a": "$profile_id",
            "profile_b": "$compare_profile_id",
        },
        "colors": {
            "same": "#adb5bd",
            "moved": "#fd7e14",
            "added": "#198754",
            "removed": "#dc3545",
        },
        "show_ghost_edges": True,
    },
},
```

#### scoda-engine (주요 변경)

Diff Tree는 scoda-engine의 `tree_chart.js`에 상당한 변경이 필요하다.
Diff 기능은 radial/rectangular **양쪽 레이아웃 모두**에서 동작해야 한다.

##### 1. Diff 모드 토글 UI

**`static/js/tree_chart.js`** — 툴바에 diff 토글 버튼 추가:

```
현재 툴바: [Radial] [Rectangular] [Depth Toggle] [Search] [Fit] [Reset]
변경 후:   [Radial] [Rectangular] [Depth Toggle] [🔀 Diff] [Search] [Fit] [Reset]
```

Diff 버튼 클릭 시:
- `diffMode = true` 상태 전환
- `compare_profile_id` global control이 표시됨 (또는 이미 표시된 것을 활성화)
- `buildRadialHierarchy()` 를 diff 모드로 재호출
- 현재 활성 레이아웃 모드(radial/rectangular)에서 diff 색상 적용

##### 2. `buildRadialHierarchy()` diff 분기

**`static/js/tree_chart.js`** — `buildRadialHierarchy()` 수정 (내부 함수명은 기존 유지):

```js
async function buildRadialHierarchy(view) {
    const rOpts = view.tree_chart_options;
    // ...기존 nodes fetch...

    if (diffMode && rOpts.diff_mode) {
        // ── Diff mode: 두 프로필의 edge를 diff 쿼리로 fetch ──
        const diffEdgeQuery = rOpts.diff_mode.edge_query;
        const diffParams = resolveDollarParams(rOpts.diff_mode.edge_params);
        const diffEdges = await fetchQuery(diffEdgeQuery, diffParams);

        // 각 노드에 diff_status 부여
        const diffMap = new Map();  // child_id → {diff_status, parent_id, parent_id_a}
        for (const e of diffEdges) {
            diffMap.set(String(e.child_id), e);
        }

        // node의 parent_id를 diff edge 기준으로 설정
        for (const row of rows) {
            const info = diffMap.get(String(row[idKey]));
            if (info) {
                row[parentKey] = info.parent_id;
                row._diff_status = info.diff_status;
                row._parent_id_a = info.parent_id_a;  // ghost edge용
            } else {
                row._diff_status = 'same';
            }
        }
    } else {
        // ── 기존 단일 프로필 모드 ──
        // ... 기존 edge fetch 로직 유지 ...
    }
    // ...이하 기존 로직 (orphan filter, stratify, etc.)
}
```

##### 3. Diff 색상 적용

**`static/js/tree_chart.js`** — `assignRadialColors()` 에 diff 모드 분기 추가 (레이아웃 무관하게 적용):

```js
function assignRadialColors(root, rOpts) {
    if (diffMode && rOpts.diff_mode) {
        const colors = rOpts.diff_mode.colors;
        root.each(node => {
            const status = node.data._diff_status || 'same';
            node._color = colors[status] || colors.same;
        });
        return;
    }
    // ... 기존 rank 기반 색상 로직 ...
}
```

##### 4. Ghost Edge 렌더링 (이동된 노드의 원래 위치 표시)

**`static/js/tree_chart.js`** — `drawLinks()` 에 ghost edge 추가.
`drawLinks()`는 이미 `treeLayoutMode`에 따라 radial(quadratic curve) vs rectangular(elbow connector)로 분기하므로, ghost edge도 같은 분기를 따른다:

```js
function drawLinks(ctx) {
    // ... 기존 실선 edge 렌더링 (radial: curve, rectangular: elbow) ...

    if (diffMode && rOpts.diff_mode?.show_ghost_edges) {
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = 'rgba(220, 53, 69, 0.3)';  // 반투명 빨강
        ctx.lineWidth = 1.0;

        radialRoot.each(node => {
            if (node.data._diff_status === 'moved' && node.data._parent_id_a) {
                const oldParent = nodeMap.get(String(node.data._parent_id_a));
                if (oldParent) {
                    if (treeLayoutMode === 'rectangular') {
                        drawElbowLink(ctx, oldParent, node);  // rectangular: elbow
                    } else {
                        drawCurvedLink(ctx, oldParent, node);  // radial: curve
                    }
                }
            }
        });
        ctx.setLineDash([]);
    }
}
```

##### 5. Diff 범례 (Legend)

**`static/js/tree_chart.js`** — Canvas 위에 범례 overlay 추가:

```
┌─ Profile Diff ──────────────────┐
│ ● Same (4,950)  ● Moved (45)   │
│ ● Added (55)    ● Removed (12) │
│ ── Ghost edge (original pos.)  │
└─────────────────────────────────┘
```

##### 6. Diff 노드 상호작용

호버 시 tooltip에 diff 정보 추가:

```
기존:   "Condylopygidae (Family)"
Diff:   "Condylopygidae (Family) — moved: Agnostida → Eodiscina"
```

### 파일별 변경 요약

| 파일 | Repo | 변경 내용 |
|------|------|----------|
| `scripts/create_assertion_db.py` | trilobase | diff 쿼리, manifest `tree_chart_options.diff_mode` 설정 |
| `static/js/tree_chart.js` | scoda-engine | diff 모드 토글, 색상, ghost edge(radial curve + rectangular elbow), 범례, tooltip |
| `static/css/style.css` | scoda-engine | 범례 스타일 (`.tc-diff-legend`), diff 버튼 스타일 |
| `static/js/app.js` | scoda-engine | compare_profile_id global control 렌더링 (이미 인프라 있음) |

### 난이도: 중간

- `tree_chart.js` 변경이 핵심이지만, 기존 구조(nodes/edges 분리, 레이아웃 분기)가 diff에 유리
- ghost edge: radial(curve)과 rectangular(elbow) 양쪽 렌더링 경로 모두 처리 필요
- `fetchQuery()`에 profile override 전달이 필요할 수 있음
- P23에서 `drawLinks()`, `drawGuideLines()` 등이 이미 `treeLayoutMode`로 분기하므로, diff 로직도 같은 패턴으로 분기하면 됨

---

## 접근법 3: Animated Morphing (프로필 전환 애니메이션)

### 개념

프로필을 전환할 때, 트리가 즉시 다시 그려지는 대신 노드가 부드럽게 새 위치로 이동한다.

```
시간 흐름:

t=0 (Profile A)              t=0.5 (전환 중)           t=1 (Profile B)
     Agnostida                    Agnostida                 Agnostida
    ╱    ╲                       ╱    ╲                    ╱    ╲
 Fam1    Fam2               Fam1    Fam2              Fam1   Eodiscina
  │       │                  │       │                 │     ╱    ╲
GenA    GenB              GenA    GenB→→→           GenA   GenB   Fam2
                                  (이동 중)
```

GenB가 Fam2에서 Eodiscina 하위로 이동하는 과정이 애니메이션으로 보인다.

### 핵심 과제

현재 `tree_chart.js`는 Canvas 즉시 모드 렌더링이므로 D3 transition을 직접 사용할 수 없다.
또한 radial/rectangular 두 레이아웃 모드가 있으므로, 같은 모드 내 전환과 모드 간 전환을 구분해야 한다.
두 가지 접근이 가능:

**방법 A: 프레임 보간 (Canvas 유지)**
```
1. 현재 레이아웃의 노드 좌표를 oldPositions로 저장
2. 새 edge로 레이아웃 재계산 → newPositions
3. requestAnimationFrame 루프로 oldPositions → newPositions 보간
4. 각 프레임에서 canvas clear → 보간된 좌표로 렌더
```

**방법 B: SVG 전환 (렌더링 방식 변경)**
```
- 노드를 SVG <circle>로 전환하면 D3 transition 직접 사용 가능
- 하지만 5,000+ SVG 요소는 성능 문제
- 현실적이지 않음
```

→ **방법 A (프레임 보간)** 이 유일하게 실용적.

### 구현 범위

#### trilobase (이 repo)

**변경 없음** — 모든 구현이 scoda-engine 쪽.

#### scoda-engine (전체 구현)

##### 1. 노드 좌표 저장 구조

**`static/js/tree_chart.js`** — 모듈 레벨 상태 추가:

```js
let previousNodePositions = null;  // Map<nodeId, {cx, cy, color, radius}>
let morphAnimation = null;         // requestAnimationFrame ID
```

##### 2. 프로필 전환 시 morph 트리거

**`static/js/app.js`** — global control onChange 수정:

```js
// 현재: queryCache = {}; switchToView(currentView);
// 변경:
sel.addEventListener('change', () => {
    // ... 기존 값 저장 로직 ...
    queryCache = {};

    if (currentView && views[currentView]?.display === 'tree_chart') {
        // Tree chart 뷰가 활성 상태면 morph 모드로 전환
        morphTreeChartToNewProfile(currentView);
    } else {
        switchToView(currentView);
    }
});
```

##### 3. Morph 핵심 로직

**`static/js/tree_chart.js`** — 새 함수 `morphTreeChartToNewProfile()`:

```js
async function morphTreeChartToNewProfile(viewKey) {
    const view = views[viewKey];

    // Step 1: 현재 노드 좌표 스냅샷 (radial/rectangular 무관 — cx/cy는 공통)
    const oldPositions = new Map();
    if (radialRoot) {
        radialRoot.each(node => {
            oldPositions.set(String(node.data.id), {
                cx: node.cx,
                cy: node.cy,
                color: node._color,
                radius: node._radius || 2,
                depth: node.depth,
            });
        });
    }

    // Step 2: 새 프로필로 트리 재빌드 (현재 레이아웃 모드 유지)
    await buildRadialHierarchy(view);
    computeLayout(radialRoot, view);  // treeLayoutMode에 따라 radial 또는 rectangular
    assignRadialColors(radialRoot, view.tree_chart_options);

    // Step 3: 새 좌표 수집 + 매핑
    const newPositions = new Map();
    radialRoot.each(node => {
        newPositions.set(String(node.data.id), {
            cx: node.cx,
            cy: node.cy,
            color: node._color,
            radius: node._radius || 2,
            depth: node.depth,
        });
    });

    // Step 4: 보간 대상 결정
    const allIds = new Set([...oldPositions.keys(), ...newPositions.keys()]);
    const interpolators = [];
    for (const id of allIds) {
        const old = oldPositions.get(id);
        const nw = newPositions.get(id);
        interpolators.push({
            id,
            // 새로 추가된 노드: 부모 위치에서 시작 → fade in
            startCx: old ? old.cx : (nw.cx * 0.8),
            startCy: old ? old.cy : (nw.cy * 0.8),
            endCx:   nw ? nw.cx : old.cx,
            endCy:   nw ? nw.cy : old.cy,
            startColor: old ? old.color : 'rgba(0,0,0,0)',
            endColor:   nw ? nw.color : 'rgba(0,0,0,0)',
            startRadius: old ? old.radius : 0,
            endRadius:   nw ? nw.radius : 0,
            status: !old ? 'added' : !nw ? 'removed' : 'existing',
        });
    }

    // Step 5: 애니메이션 루프
    const duration = 800;  // ms
    const startTime = performance.now();

    function animateFrame(now) {
        const elapsed = now - startTime;
        const t = Math.min(elapsed / duration, 1);
        const ease = easeInOutCubic(t);

        const canvas = radialCanvas;  // 내부 변수명 유지 (P23)
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.save();
        // zoom transform 적용
        const tr = d3.zoomTransform(canvas);
        ctx.translate(tr.x + canvas.width/2, tr.y + canvas.height/2);
        ctx.scale(tr.k, tr.k);

        // 보간된 위치에서 edge + node 렌더
        for (const interp of interpolators) {
            const cx = interp.startCx + (interp.endCx - interp.startCx) * ease;
            const cy = interp.startCy + (interp.endCy - interp.startCy) * ease;
            const r  = interp.startRadius + (interp.endRadius - interp.startRadius) * ease;
            // node 그리기
            ctx.beginPath();
            ctx.arc(cx, cy, Math.max(r, 0.5), 0, 2 * Math.PI);
            ctx.fillStyle = lerpColor(interp.startColor, interp.endColor, ease);
            ctx.fill();
        }
        // (edge 보간은 더 복잡 — 아래 고려사항 참조)

        ctx.restore();

        if (t < 1) {
            morphAnimation = requestAnimationFrame(animateFrame);
        } else {
            // 애니메이션 완료 → 정상 렌더로 전환
            renderRadial();
            updateRadialLabels(tr);
        }
    }

    if (morphAnimation) cancelAnimationFrame(morphAnimation);
    morphAnimation = requestAnimationFrame(animateFrame);
}

function easeInOutCubic(t) {
    return t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t + 2, 3) / 2;
}
```

##### 4. Edge 애니메이션

Edge 보간이 가장 까다로운 부분이다. `drawLinks()`는 이미 `treeLayoutMode`에 따라
radial(quadratic curve) vs rectangular(elbow connector)로 분기하므로,
edge 애니메이션도 레이아웃별로 다르게 처리해야 한다:

```
옵션 A: Edge는 애니메이션하지 않음
  - 노드만 이동, edge는 t=0에서 사라지고 t=1에서 나타남
  - 가장 간단하지만 시각적으로 불완전

옵션 B: Edge도 함께 보간
  - 양 끝점(parent.cx/cy, child.cx/cy)이 모두 보간되므로 곡선/elbow도 자연스럽게 변함
  - parent가 바뀐 경우: old_parent → child 곡선이 new_parent → child로 전환
  - radial: curve 보간, rectangular: elbow 보간 — 각각 구현 필요
  - 구현이 복잡하지만 가장 완성도 높음

옵션 C: Edge fade 전환
  - old edges를 fade out (opacity 1→0) + new edges를 fade in (0→1)
  - 노드 이동과 결합하면 자연스러움
  - 옵션 B보다 단순하면서 시각적으로 충분함
  - 레이아웃 모드 구분 없이 동일한 로직으로 처리 가능
```

**권장: 옵션 C (Edge fade)** — 노드 보간 + edge fade의 조합이 복잡도/효과 비율이 최적.
특히 radial/rectangular 양쪽에서 동일한 fade 로직을 재사용할 수 있어 구현 부담이 적음.

### 고려사항

**레이아웃 재배치 문제**: 양쪽 레이아웃 모두에서 한 노드의 parent가 바뀌면, 형제 노드들의 위치도 전부 재계산된다.

```
Radial: GenB가 Fam2 → Eodiscina로 이동
  - Fam2의 나머지 자식들: 각도 간격이 넓어짐 (형제 하나 줄었으므로)
  - Eodiscina의 기존 자식들: 각도 간격이 좁아짐 (형제 하나 늘었으므로)

Rectangular: 동일한 문제가 수직 방향으로 발생
  - Fam2 subtree의 y 간격이 넓어짐
  - Eodiscina subtree의 y 간격이 좁아짐
  - leafCount 기반 동적 크기(MIN_LEAF_SPACING=24px)로 전체 높이도 변할 수 있음

  → 두 모드 모두 "잡음" 미세 이동이 발생
```

**완화 방안:**
- 이동량이 임계값(예: 5px) 미만인 노드는 보간하지 않고 즉시 최종 위치로
- 실제 parent가 변한 노드만 강조 색상 + 이동 경로(arc trail) 표시
- "moved" 노드의 이동 경로를 잔상(trail)으로 표시하여 주목도 향상

### 파일별 변경 요약

| 파일 | Repo | 변경 내용 |
|------|------|----------|
| (없음) | trilobase | 변경 없음 |
| `static/js/tree_chart.js` | scoda-engine | `morphTreeChartToNewProfile()`, 좌표 보간, edge fade. 두 레이아웃 모두 지원 |
| `static/js/app.js` | scoda-engine | profile 전환 시 morph 트리거 분기 (`display === 'tree_chart'`) |

### 난이도: 중간~높음

- Canvas 프레임 보간 로직이 핵심 복잡도
- Edge 처리 방식에 따라 복잡도 크게 변동
- radial/rectangular 양쪽에서 동작 검증 필요
- 레이아웃 재배치 잡음 문제 해결 필요
- `computeLayout()` 디스패처를 통해 재레이아웃하므로, morph 시점의 `treeLayoutMode` 유지가 중요

---

## 구현 순서 제안

5개 Phase로 확장. 비교 표시 모드 4가지를 모두 구현하는 것이 목표.

```
Phase 0: Compare UI 인프라       Phase 1: Diff Table
┌──────────────────────────┐    ┌─────────────────────────┐
│ scoda-engine             │    │ trilobase               │
│  • Compare 모드 토글     │    │  • profile_diff 쿼리    │
│  • compare_control 렌더  │    │  • manifest diff 뷰     │
│  • compareMode 상태 관리 │    │  • compare global ctrl  │
│  • 표시 모드 selector    │    ├─────────────────────────┤
└──────────────────────────┘    │ scoda-engine            │
                                │  • (행 색상 row_color)  │
                                └─────────────────────────┘

Phase 2: Diff Tree                   Phase 3: Overlay + Side-by-side
┌────────────────────────────────┐   ┌──────────────────────────────────┐
│ trilobase                      │   │ scoda-engine                     │
│  • profile_diff_edges 쿼리     │   │  • Overlay: 두 edge set 겹쳐     │
│  • manifest diff_mode 설정     │   │    렌더 (실선/점선, opacity 조절) │
├────────────────────────────────┤   │  • Side-by-side: 캔버스 2개,     │
│ scoda-engine                   │   │    zoom/pan/collapse 동기화       │
│  • tree_chart.js diff 전체     │   │  • 표시 모드 전환 로직            │
│  • 색상, ghost edge, 범례      │   └──────────────────────────────────┘
└────────────────────────────────┘

Phase 4: Animated Morphing
┌──────────────────────────────────┐
│ scoda-engine                     │
│  • tree_chart.js morph 로직     │
│  • 좌표 보간 + edge fade        │
│  • app.js 전환 분기              │
│  • radial/rectangular 양쪽 지원  │
└──────────────────────────────────┘
```

### Phase 0: Compare UI 인프라 (난이도: 낮음)

**목표**: Compare 모드 토글 + 두 번째 프로필 셀렉터 + 비교 표시 모드 선택 UI

| 단계 | Repo | 작업 |
|------|------|------|
| 0-1 | scoda-engine | app.js: `compareMode` 상태 + Compare 토글 버튼 (global controls 영역) |
| 0-2 | scoda-engine | app.js: `compare_control: true`인 global_controls를 compare 모드에서만 렌더 |
| 0-3 | scoda-engine | app.js/tree_chart.js: 비교 표시 모드 selector ([Diff] [Side-by-side] [Overlay] [Table]) |
| 0-4 | scoda-engine | style.css: compare toolbar 스타일 |

**산출물**: Compare 버튼 클릭 → 두 번째 프로필 셀렉터 + 표시 모드 선택 UI 등장

```
[Normal mode]
  Classification: [default ▾]

[Compare 버튼 클릭]
  Base: [default ▾]   Compare: [treatise2004 ▾]
  Display: [Diff] [Side-by-side] [Overlay] [Table]
```

### Phase 1: Diff Table (난이도: 낮음)

**목표**: 두 프로필 간 차이를 데이터로 확인할 수 있는 기반 마련

| 단계 | Repo | 작업 |
|------|------|------|
| 1-1 | trilobase | `compare_profile_id` global control 추가 (`compare_control: True`) |
| 1-2 | trilobase | `profile_diff` SQL 쿼리 작성 + ui_queries 등록 |
| 1-3 | trilobase | manifest에 `profile_diff_table` 뷰 선언 |
| 1-4 | trilobase | assertion DB 재빌드 + 검증 |
| 1-5 | scoda-engine | table 뷰에 `row_color_key` 지원 (diff_status별 행 배경색) |

**산출물**: Compare 모드 → Table 선택 시 diff 목록 표시

### Phase 2: Diff Tree (난이도: 중간)

**목표**: tree chart에서 diff 색상 코딩 비교

| 단계 | Repo | 작업 |
|------|------|------|
| 2-1 | trilobase | `profile_diff_edges` SQL 쿼리 작성 |
| 2-2 | trilobase | manifest `tree_chart_options`에 `diff_mode` 설정 추가 |
| 2-3 | scoda-engine | tree_chart.js: compare 모드 "Diff" 선택 시 diff 렌더링 활성화 |
| 2-4 | scoda-engine | tree_chart.js: `buildRadialHierarchy()` diff 분기 |
| 2-5 | scoda-engine | tree_chart.js: diff 색상 적용 (`assignRadialColors` 수정) |
| 2-6 | scoda-engine | tree_chart.js: ghost edge 렌더링 (radial curve + rectangular elbow) |
| 2-7 | scoda-engine | tree_chart.js: diff 범례 + tooltip 확장 |
| 2-8 | 양쪽 | 테스트 + 검증 |

**산출물**: Compare 모드 → Diff 선택 시 색상 코딩된 단일 트리

### Phase 3: Overlay + Side-by-side (난이도: 중간~높음)

**목표**: 나머지 두 비교 표시 모드 구현

| 단계 | Repo | 작업 |
|------|------|------|
| 3-1 | scoda-engine | tree_chart.js: Overlay 모드 — 두 edge set을 다른 스타일로 같은 캔버스에 렌더 |
| 3-2 | scoda-engine | tree_chart.js: Overlay — A edges 실선 + B edges 점선/반투명, 공통 edge는 실선 1회 |
| 3-3 | scoda-engine | tree_chart.js: Side-by-side — 캔버스 2개 생성 (flex 배치) |
| 3-4 | scoda-engine | tree_chart.js: Side-by-side — 각각 다른 profile로 독립 빌드 |
| 3-5 | scoda-engine | tree_chart.js: Side-by-side — zoom/pan 동기화 (한쪽 이벤트 → 다른 쪽 mirror) |
| 3-6 | scoda-engine | tree_chart.js: Side-by-side — hover 하이라이트 동기화 |
| 3-7 | scoda-engine | tree_chart.js: Side-by-side — collapse/expand 동기화 |
| 3-8 | 양쪽 | 테스트 + 검증 |

**산출물**: Compare 모드에서 4가지 표시 모드 (Table/Diff/Overlay/Side-by-side) 전환 가능

### Phase 4: Animated Morphing (난이도: 중간~높음)

**목표**: 프로필 전환 시 부드러운 시각적 전이 (Compare 모드와 독립적으로도 동작)

| 단계 | Repo | 작업 |
|------|------|------|
| 4-1 | scoda-engine | tree_chart.js: `previousNodePositions` 저장 구조 |
| 4-2 | scoda-engine | tree_chart.js: `morphTreeChartToNewProfile()` 핵심 로직 |
| 4-3 | scoda-engine | tree_chart.js: 노드 좌표 보간 + easing (cx/cy 공통) |
| 4-4 | scoda-engine | tree_chart.js: edge fade 전환 (레이아웃 무관 opacity 보간) |
| 4-5 | scoda-engine | app.js: profile 전환 시 morph 트리거 (`display === 'tree_chart'`) |
| 4-6 | scoda-engine | 미세 이동 필터링 + moved 강조 |
| 4-7 | scoda-engine | 테스트 (다양한 프로필 × 레이아웃 조합) |

**산출물**: 프로필 전환 시 노드가 새 위치로 부드럽게 이동하는 애니메이션

> **참고**: Morphing은 Compare 모드와 별개로 동작한다. Compare 모드가 아니어도
> 단일 프로필 전환(dropdown 변경) 시 애니메이션 효과를 줄 수 있다.

---

## scoda-engine vs trilobase 책임 분리

```
                    ┌───────────────────────────────────────┐
                    │            scoda-engine                │
                    │     (범용 시각화 프레임워크)              │
                    │                                       │
                    │  • app.js: Compare 모드 토글 UI        │
                    │  • app.js: compare_control 조건부 렌더  │
                    │  • app.js: 비교 표시 모드 selector      │
                    │  • tree_chart.js: Diff 렌더링 엔진     │
                    │    (radial + rectangular)              │
                    │  • tree_chart.js: Overlay 렌더링       │
                    │  • tree_chart.js: Side-by-side 분할    │
                    │  • tree_chart.js: Morph 애니메이션      │
                    │  • table: row_color_key 지원           │
                    │  • diff_mode manifest 해석             │
                    │                                       │
                    │  모든 .scoda 패키지에서 재사용 가능       │
                    └───────────────────┬───────────────────┘
                                        │ manifest 계약
                    ┌───────────────────┴───────────────────┐
                    │             trilobase                   │
                    │     (도메인 데이터 + 선언)                │
                    │                                       │
                    │  • profile_diff SQL 쿼리               │
                    │  • profile_diff_edges SQL 쿼리         │
                    │  • manifest diff_mode 설정 선언         │
                    │  • compare_profile_id control 선언     │
                    │    (compare_control: True)             │
                    │  • classification_edge_cache 데이터     │
                    │                                       │
                    │  trilobase 도메인에 특화된 설정           │
                    └───────────────────────────────────────┘
```

**원칙**: scoda-engine은 "어떻게 비교하고 그릴지"를 알고(4가지 표시 모드 × 2가지 레이아웃), trilobase는 "무엇을 비교할지"를 선언한다. manifest의 `tree_chart_options.diff_mode` + `compare_control`이 계약(contract) 역할.

---

## 향후 확장 가능성

위 5개 Phase 완료 후 추가할 수 있는 시각화:

| 방법 | 활용 시점 | scoda-engine 추가 필요 |
|------|----------|----------------------|
| Tanglegram | subtree 단위 상세 비교 | 새 표시 모드 또는 뷰 타입 |
| Sankey | Family 수준 집계 흐름 비교 | 새 표시 모드 (`display: "sankey"`) |

이들은 Phase 0~4의 기반 (Compare UI, diff 쿼리, 표시 모드 selector) 위에 구축된다.
Side-by-side가 이미 구현되므로 "Dual Tree Chart"는 별도 구현 불필요.
