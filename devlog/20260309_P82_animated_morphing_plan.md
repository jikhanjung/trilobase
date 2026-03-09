# P04: Profile Comparison 탭 통합 + Animated Morphing

**Date:** 2026-03-09
**Status:** Plan
**R02 Phase:** 4 (Animated Morphing) + UI 리팩토링

## 목표

Compare 기능을 하나의 **Profile Comparison 탭**으로 통합하고, Animated Morphing을 서브뷰로 추가한다.

## 현재 구조 (Before)

```
[Taxonomy Tree] [Genera] [Assertions] [References] ...
[Diff Table*] [Diff Tree*] [Side-by-Side*]
                                          * compare_view: true
                                          * 클릭 시 compareMode 자동 토글
                                          * global "Compare with" 드롭다운 표시
```

- Compare 뷰 3개가 최상위 탭으로 분산
- `compareMode` 글로벌 상태 → global control 표시/숨김
- 일반 탭 클릭 시 compare 컨트롤 자동 숨김

## 목표 구조 (After)

```
[Taxonomy Tree] [Genera] [Assertions] ... [Profile Comparison]
                                               ↓
                                    ┌─────────────────────────┐
                                    │ From: [default ▾]       │
                                    │ To:   [treatise2004 ▾]  │
                                    ├─────────────────────────┤
                                    │ [Table] [Tree] [Morph]  │  ← 서브탭
                                    │                         │
                                    │  (서브뷰 컨텐츠)         │
                                    └─────────────────────────┘
```

- 일반 탭들: 선택된 프로필 데이터만 표시 (compare 무관)
- **Profile Comparison** 탭 1개: 내부에 from/to 셀렉터 + 3가지 서브뷰
- 글로벌 `compareMode` 토글 제거 → Comparison 탭 내부에서만 from/to 선택
- Side-by-Side는 Diff Tree에 토글로 통합하거나 별도 서브탭으로 유지 (TBD)

## 리팩토링 범위

### 1. Manifest 구조 변경 (trilobase)

**파일:** `scripts/create_assertion_db.py`

#### 1-1. Compound View 타입 도입

```python
"profile_comparison": {
    "type": "compound",           # 새 타입
    "title": "Profile Comparison",
    "controls": [                 # 탭 로컬 컨트롤 (글로벌이 아님)
        {
            "type": "select",
            "param": "base_profile_id",
            "label": "From",
            "source_query": "classification_profiles_selector",
            "value_key": "id",
            "label_key": "name",
            "default": 1,
        },
        {
            "type": "select",
            "param": "compare_profile_id",
            "label": "To",
            "source_query": "classification_profiles_selector",
            "value_key": "id",
            "label_key": "name",
            "default": 3,
        },
    ],
    "sub_views": {
        "diff_table": { ... },     # 기존 profile_diff_table 내용
        "diff_tree": { ... },      # 기존 diff_tree 내용
        "morph": {                 # 신규
            "title": "Morph",
            "type": "hierarchy",
            "display": "tree_chart_morph",
            ...
        },
    },
    "default_sub_view": "diff_table",
}
```

#### 1-2. 기존 compare 뷰 제거

- `profile_diff_table` (최상위 탭) → `profile_comparison.sub_views.diff_table`로 이동
- `diff_tree` (최상위 탭) → `profile_comparison.sub_views.diff_tree`로 이동
- `side_by_side_tree` (최상위 탭) → `profile_comparison.sub_views.side_by_side`로 이동 또는 diff_tree 내 토글로 통합

#### 1-3. Global controls 정리

- `compare_profile_id` global control 제거 (compound view 내부로 이동)
- `profile_id`만 global control로 유지 (일반 탭에서 프로필 선택)
- `compare_control: true` 플래그 제거

### 2. scoda-engine app.js 변경

**파일:** `scoda_engine/static/js/app.js`

#### 2-1. Compound view 렌더러

`switchToView()`에 `type: "compound"` 분기 추가:

```js
case 'compound':
    loadCompoundView(viewKey, view);
    break;
```

`loadCompoundView(viewKey, view)`:
- Compound view 컨테이너 표시
- **로컬 컨트롤** 렌더링 (from/to 프로필 셀렉터)
- **서브탭** 렌더링 (Table / Tree / Morph)
- 서브탭 클릭 시 해당 서브뷰 로드
- 로컬 컨트롤 변경 시 현재 서브뷰만 리프레시

#### 2-2. compareMode 글로벌 상태 제거

- `compareMode` 변수 제거
- `renderGlobalControls()`에서 `compare_control` 관련 로직 제거
- `switchToView()`에서 `compare_view` 자동 토글 로직 제거
- 기존 `compare_view: true` 뷰들은 더 이상 최상위 탭으로 노출되지 않음

#### 2-3. 서브뷰 파라미터 해석

Compound view의 로컬 컨트롤 값을 서브뷰 쿼리에 전달:
- `$base_profile_id` → 로컬 from 셀렉터 값
- `$compare_profile_id` → 로컬 to 셀렉터 값
- 기존 `$profile_id` 참조를 `$base_profile_id`로 매핑 (서브뷰 쿼리 내)

### 3. scoda-engine index.html 변경

**파일:** `scoda_engine/templates/index.html`

#### 3-1. Compound view 컨테이너 추가

```html
<div class="view-container" id="view-compound" style="display: none;">
    <div class="compound-controls" id="compound-controls">
        <!-- From/To selectors rendered by JS -->
    </div>
    <ul class="nav nav-tabs" id="compound-sub-tabs">
        <!-- Sub-tab buttons rendered by JS -->
    </ul>
    <div class="compound-sub-content" id="compound-sub-content">
        <!-- Sub-view content rendered by JS -->
    </div>
</div>
```

### 4. Animated Morphing 구현 (scoda-engine tree_chart.js)

**파일:** `scoda_engine/static/js/tree_chart.js`

#### 4-1. `tree_chart_morph` display 타입

Morph 뷰는 tree_chart와 거의 동일하지만, 두 프로필 데이터를 동시에 로드하여 애니메이션한다.

#### 4-2. MorphTreeChartInstance (또는 TreeChartInstance 확장)

```js
// TreeChartInstance에 morph 메서드 추가
class TreeChartInstance {
    // 기존 메서드들...

    async loadMorph(view, baseParams, compareParams) {
        // 1. Base 프로필 트리 빌드 → basePositions 스냅샷
        // 2. Compare 프로필 트리 빌드 → comparePositions 스냅샷
        // 3. Play/Pause 컨트롤 표시
        // 4. 애니메이션 대기 (사용자가 Play 클릭 시 시작)
    }

    snapshotPositions() { ... }

    animateMorph(fromPositions, toPositions, duration = 800) {
        // requestAnimationFrame 루프
        // 노드: lerp(from.cx, to.cx, ease), lerp(from.cy, to.cy, ease)
        // Added: fade-in + grow (부모 위치에서)
        // Removed: fade-out + shrink
        // Edge crossfade: old links fade out, new links fade in
    }

    lerpColor(a, b, t) { ... }
}
```

#### 4-3. Morph UI 컨트롤

- **Play/Pause** 버튼
- **Scrubber** (0~100% 슬라이더) — 사용자가 수동으로 시점 조절
- **Speed** 조절 (0.5x, 1x, 2x)
- **방향 전환** (From→To / To→From)

#### 4-4. 애니메이션 상세

| 요소 | 처리 |
|------|------|
| Same 노드 | cx/cy 보간 (형제 재배치로 인한 미세 이동) |
| Moved 노드 | cx/cy 보간 (큰 이동), 색상 강조 |
| Added 노드 | 부모 위치에서 fade-in + grow, opacity 0→1 |
| Removed 노드 | fade-out + shrink, opacity 1→0 |
| Edges (shared) | full opacity, 끝점 보간 |
| Edges (old-only) | opacity 1→0 페이드아웃 |
| Edges (new-only) | opacity 0→1 페이드인 |
| SVG 라벨 | 애니메이션 중 숨김, 완료 시 표시 |
| Micro-movement (<3px) | 즉시 snap (노이즈 감소) |

**Easing:** cubic ease-in-out `t < 0.5 ? 4t³ : 1 - (-2t+2)³/2`
**Duration:** 800ms (기본), 사용자 조절 가능

### 5. 구현 순서

| Phase | 내용 | Repo |
|-------|------|------|
| **A** | Manifest에 `compound` 뷰 타입 정의 + 기존 compare 뷰 → sub_views 이동 | trilobase |
| **B** | app.js에 `loadCompoundView()` + 서브탭 + 로컬 컨트롤 렌더러 | scoda-engine |
| **C** | index.html에 compound 컨테이너 추가 | scoda-engine |
| **D** | `compareMode` 글로벌 상태 제거 + `compare_control` 로직 정리 | scoda-engine |
| **E** | 기존 Diff Table/Diff Tree/Side-by-Side가 compound 내에서 동작하는지 검증 | both |
| **F** | `tree_chart_morph` display 타입 + morph 메서드 구현 | scoda-engine |
| **G** | Morph UI (play/pause, scrubber) 구현 | scoda-engine |
| **H** | Edge crossfade + edge cases (collapsed, interruption 등) | scoda-engine |
| **I** | Manifest에 morph 서브뷰 추가 | trilobase |

### 6. 수정 파일 요약

| File | Repo | 변경 |
|------|------|------|
| `scripts/create_assertion_db.py` | trilobase | manifest 구조 변경: compound 뷰, sub_views, 로컬 컨트롤 |
| `static/js/app.js` | scoda-engine | `loadCompoundView()`, compareMode 제거, 서브탭 렌더링 |
| `templates/index.html` | scoda-engine | compound 컨테이너 HTML |
| `static/js/tree_chart.js` | scoda-engine | `loadMorph()`, `snapshotPositions()`, `animateMorph()`, morph UI |
| `static/css/style.css` | scoda-engine | compound 뷰 + morph 컨트롤 스타일 |

### 7. 리스크

| 리스크 | 대응 |
|--------|------|
| compound 뷰가 scoda-engine의 범용 기능이므로 다른 패키지에서도 쓸 수 있어야 함 | manifest 스펙을 일반적으로 설계 |
| 기존 compare 동작과의 하위 호환성 | Phase D에서 compare_view 플래그를 compound로 자동 변환하는 마이그레이션 고려 |
| 5,000+ 노드 morph 성능 | Canvas는 빠름. 필요 시 guide lines/edges 생략 |
| Side-by-Side를 compound 안으로 넣으면 레이아웃 복잡 | Side-by-Side는 diff_tree의 토글로 통합 검토 |

## 참고 문서

- `devlog/20260302_R02_tree_diff_visualization.md` — R02 설계
- `devlog/20260307_111_profile_diff_table.md` — Diff Table
- `devlog/20260307_114_diff_tree.md` — Diff Tree
- `devlog/20260307_112_side_by_side_tree.md` — Side-by-Side
