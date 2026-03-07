# 113: Side-by-Side Tree — Sync 보강 + 성능 최적화

**날짜:** 2026-03-07
**Related:** 112 (Side-by-Side Tree 기본 구현), scoda-engine devlog 040

## 개요

Side-by-Side Tree Chart의 동기화 기능 5종 추가 및 zoom 성능 최적화.
모든 변경은 scoda-engine 쪽 (`tree_chart.js`, `style.css`, `index.html`).

## 동기화 기능 (5종)

| 기능 | 동작 |
|------|------|
| Hover highlight | 한쪽 hover → 반대쪽 같은 taxon에 cyan 링 + tooltip |
| Depth toggle | genus show/hide 토글 시 양쪽 동기화 |
| Collapse/expand | 내부 노드 클릭 시 같은 taxon collapse/expand |
| View-as-root | 우클릭 "View as Root" + breadcrumb 양쪽 동기화 |
| Tooltip (양쪽) | 패널별 독립 tooltip, hover sync 시 양쪽 동시 표시 |

## 성능 최적화

| 기법 | 효과 |
|------|------|
| Bitmap cache | zoom 중 offscreen canvas blit (pan은 full render 유지) |
| SVG 라벨 숨김 | zoom 중 visibility:hidden, zoom 끝에만 update |
| Guide depth 캐싱 | 매 프레임 트리 순회 → 캐시 lookup |
| Zoom sync 최적화 | canvas.__zoom 직접 세팅으로 이벤트 사이클 제거 |

## scoda-engine 수정 파일

| 파일 | 변경 |
|------|------|
| `static/js/tree_chart.js` | sync 콜백 5종, bitmap cache, 라벨/가이드 최적화 |
| `static/css/style.css` | `.sbs-panel` overflow: hidden |
| `templates/index.html` | 패널별 tooltip 요소 분리 |

## trilobase 변경

없음 (scoda-engine 변경만).
assertion DB 파일은 이전 세션의 side_by_side_tree 뷰 선언 반영.
