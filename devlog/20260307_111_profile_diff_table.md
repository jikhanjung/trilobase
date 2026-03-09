# 111: Profile Diff Table — Compare 모드 Phase 0+1

**날짜:** 2026-03-07
**DB:** trilobase-assertion-0.1.5.db
**Related:** R02 (devlog/20260302_R02_tree_diff_visualization.md)

## 개요

R02 로드맵의 Phase 0 (Compare UI 인프라) + Phase 1 (Diff Table)을 합쳐서 구현.
두 classification profile을 선택하고 차이를 테이블로 확인하는 end-to-end 흐름 완성.

## scoda-engine 변경

**`static/js/app.js`:**

- `compareMode` global state 추가
- `renderGlobalControls()`: Compare 토글 버튼 + `compare_control: true`인 셀렉터 조건부 렌더링
- `buildViewTabs()`: `compare_view: true`인 뷰 탭을 Compare 모드에서만 표시
- `updateCompareViewTabs()`: 모드 전환 시 탭 show/hide
- `renderTableViewRows()`: `row_color_key` + `row_color_map` 지원 → 행 배경색 (table-warning/success/danger)

## trilobase 변경

**`scripts/create_assertion_db.py`:**

- `profile_diff` SQL 쿼리: 두 프로필의 edge cache를 LEFT JOIN + UNION ALL로 비교
  - moved: 양쪽에 있지만 parent가 다름
  - added: compare 프로필에만 있음
  - removed: base 프로필에만 있음
- `compare_profile_id` global control: `compare_control: True`, default=2 (treatise1959)
- `profile_diff_table` 뷰: `compare_view: True`로 Compare 모드에서만 탭 표시
  - columns: Taxon, Rank, Base Parent, Compare Parent, Status
  - `row_color_key: "diff_status"` + `row_color_map` (moved=warning, added=success, removed=danger)
  - searchable, sortable, on_row_click → taxon_detail_view

## Diff 결과 예시

| 비교 | moved | added | removed | 합계 |
|------|-------|-------|---------|------|
| default vs treatise1959 | 904 | 250 | 4,009 | 5,163 |
| treatise1959 vs treatise2004 | 68 | 343 | 0 | 411 |

default vs treatise1959에서 removed가 많은 이유: treatise1959가 standalone(1,324 edges)이라
default의 5,083 edges 중 대부분이 1959에 없음.

## 실행 방법

```bash
python -m scoda_engine.serve --db-path db/trilobase-assertion-0.1.5.db --mode admin --port 8090
# Compare 버튼 클릭 → "Compare with" 셀렉터 + "Profile Diff" 탭 등장
```

## 다음 단계 (R02 Phase 2~4)

- Phase 2: Diff Tree — tree chart에서 diff 색상 코딩 + ghost edge
- Phase 3: Overlay + Side-by-side
- Phase 4: Animated Morphing
