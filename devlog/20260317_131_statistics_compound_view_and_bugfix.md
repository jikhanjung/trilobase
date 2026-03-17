# 20260317_131 — Statistics compound view 통일 + Order "and" 파싱 버그 수정

## 작업 내용

### 1. Order "and" 파싱 버그 수정 (trilobase)

**문제**: `data/sources/treatise_1959.txt`에 `"Order and Family UNCERTAIN"` 같은 compound rank header가
있을 때 `parse_hierarchy_body()`가 `"Order"`만 매칭하고 나머지 `"and Family UNCERTAIN"`에서
`name = "and"`를 추출 → Order `"and"` 생성, Kolpura 등 ~40개 속이 잘못 분류됨.

**수정**: `build_trilobase_db.py`의 `parse_hierarchy_body()`에 compound rank header 패턴 감지 추가.
- `"Order and Family UNCERTAIN"` → rank=Order, name="Order and family uncertain"
- `"Superfamily and Family UNCERTAIN"`, `"Order, Suborder, and Family UNCERTAIN"` 등 다양한 패턴 지원.

### 2. Statistics compound view 적용 (전 패키지)

기존에 다른 패키지들은 `timeline_view` compound view에 single sub_view (geologic+pubyear axis mode 합침)
로 구성되어 있었음. trilobase의 Statistics compound view 구조로 통일:

- **Statistics** compound view
  - `geologic_timeline`: Geologic Timeline (tree_chart_timeline)
  - `pubyear_timeline`: Publication Timeline (tree_chart_timeline)
  - `bar_chart`: Diversity Chart (bar_chart, `diversity_by_age` 쿼리)

### 3. diversity_by_age 쿼리 추가

각 패키지에 `diversity_by_age` 쿼리 추가. Temporal code 목록은 패키지별로 다름:
- trilobase: Paleozoic only (LCAM~UPERM)
- brachiobase/chelicerobase/ostracobase: Paleozoic + Mesozoic + Cenozoic
- graptobase: MCAM~MISS (data-bearing range only)

## 버전 변경

| Package | Before | After |
|---|---|---|
| trilobase | 0.3.2 → 0.3.3 | Order "and" 버그 수정 |
| brachiobase | 0.2.5 → 0.2.6 | Statistics compound view |
| graptobase | 0.1.1 → 0.1.2 | Statistics compound view |
| chelicerobase | 0.1.1 → 0.1.2 | Statistics compound view |
| ostracobase | 0.1.1 → 0.1.2 | Statistics compound view |
| paleocore | 0.1.2 → 0.1.3 | 버전 동기화 |

## 수정된 파일

- `scripts/build_trilobase_db.py` — compound rank header 파싱 수정 + diversity_by_age 쿼리
- `scripts/build_brachiobase_db.py` — Statistics view + diversity_by_age
- `scripts/build_graptobase_db.py` — Statistics view + diversity_by_age
- `scripts/build_chelicerobase_db.py` — Statistics view + diversity_by_age
- `scripts/build_ostracobase_db.py` — Statistics view + diversity_by_age
- `scripts/build_paleocore_db.py` — 버전 0.1.3

## 결과 UI 구조 (전 패키지 공통)

```
Tree / Comparison (Diff Table | Diff Tree | Side-by-Side | Animation) / Statistics (Geologic Timeline | Publication Timeline | Diversity Chart)
```
