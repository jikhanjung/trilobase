# P87 — Timeline 기능을 위한 .scoda 패키지 작업

**날짜**: 2026-03-14
**관련**: scoda-engine P28, `20260314_030_timeline_subview_implementation.md`

## 배경

scoda-engine 측에 범용 `tree_chart_timeline` 서브뷰 메커니즘이 구현됨.
이 문서는 trilobase `.scoda` 패키지에서 해당 기능을 활성화하기 위해 필요한 작업을 정리한다.

---

## 1. 축(Axis) 쿼리 추가 — `ui_queries`

### 1-1. 지질시대 축: `timeline_geologic_periods`

`pc.temporal_ranges` (28개 코드)를 시간순으로 반환.

```sql
SELECT code AS id, name, start_mya AS sort_order
FROM pc.temporal_ranges
ORDER BY start_mya DESC
```

- `value_key`: `id` (temporal code, e.g. `LCAM`)
- `label_key`: `name` (e.g. `Lower Cambrian`)
- `order_key`: `sort_order` (start_mya 역순 → 시간 순)

### 1-2. 출판 연도 축: `timeline_publication_years`

`reference` 테이블에서 고유 연도 목록 반환.

```sql
SELECT DISTINCT r.year AS year, r.year AS label
FROM reference r
JOIN assertion a ON a.reference_id = r.id
WHERE r.year IS NOT NULL
ORDER BY r.year
```

- `value_key`: `year`
- `label_key`: `label`
- `order_key`: `year`

---

## 2. 필터 쿼리 추가 — `ui_queries`

### 2-1. 지질시대 필터: `taxonomy_tree_by_geologic`

특정 temporal_code에 해당하는 분류군만 포함하는 트리.
temporal_ranges는 시간 범위(start_mya~end_mya)이므로, 슬라이더 값 이전(더 오래된) 시대까지 누적 표시.

```sql
SELECT t.id, t.name, t.rank, t.author, t.year, t.temporal_code, t.is_valid
FROM taxon t
WHERE t.id IN (
    SELECT DISTINCT e.child_id
    FROM classification_edge_cache e
    WHERE e.profile_id = COALESCE(:profile_id, 1)
)
AND (
    :timeline_value IS NULL
    OR t.temporal_code IN (
        SELECT tr.code FROM pc.temporal_ranges tr
        WHERE tr.start_mya >= (
            SELECT tr2.start_mya FROM pc.temporal_ranges tr2
            WHERE tr2.code = :timeline_value
        )
    )
    OR t.rank != 'Genus'  -- 상위 분류군은 항상 표시 (빈 노드 pruning은 별도 처리)
)
ORDER BY t.id
```

### 2-2. 출판 연도 필터: `taxonomy_tree_by_pubyear`

특정 연도까지 출판된 assertion에 포함된 분류군만 표시 (누적 모드).

```sql
SELECT t.id, t.name, t.rank, t.author, t.year, t.temporal_code, t.is_valid
FROM taxon t
WHERE t.id IN (
    SELECT DISTINCT e.child_id
    FROM classification_edge_cache e
    JOIN assertion a ON (
        a.subject_taxon_id = e.child_id
        AND a.predicate = 'PLACED_IN'
    )
    JOIN reference r ON a.reference_id = r.id
    WHERE e.profile_id = COALESCE(:profile_id, 1)
    AND r.year <= :timeline_value
)
OR (
    t.rank != 'Genus'  -- 상위 분류군은 항상 표시 (빈 노드 pruning은 별도 처리)
    AND t.id IN (
        SELECT DISTINCT e.child_id
        FROM classification_edge_cache e
        WHERE e.profile_id = COALESCE(:profile_id, 1)
    )
)
ORDER BY t.id
```

### 2-3. 타임라인용 edge 쿼리: `tree_edges_by_timeline`

edge_cache에서 프로파일별 부모-자식 관계 (기존 `classification_tree_edges`와 유사).

```sql
SELECT child_id, parent_id
FROM classification_edge_cache
WHERE profile_id = COALESCE(:profile_id, 1)
```

---

## 3. Manifest 수정 — `ui_manifest`

기존 compound view의 `sub_views`에 `timeline` 서브뷰 추가.

### 3-1. 두 가지 접근법

**A안: 단일 서브뷰 + 축 모드 드롭다운 (권장)**

```json
"timeline": {
    "display": "tree_chart_timeline",
    "title": "Timeline",
    "source_query": "taxonomy_tree_by_geologic",
    "hierarchy_options": {
        "id_key": "id",
        "parent_key": "parent_id",
        "label_key": "name",
        "rank_key": "rank"
    },
    "tree_chart_options": {
        "default_layout": "radial",
        "rank_radius": { /* 기존과 동일 */ },
        "edge_query": "tree_edges_by_timeline",
        "edge_id_key": "child_id",
        "edge_parent_key": "parent_id"
    },
    "timeline_options": {
        "param_name": "timeline_value",
        "default_step_size": 1,
        "axis_modes": [
            {
                "key": "geologic",
                "label": "Geologic Time",
                "axis_query": "timeline_geologic_periods",
                "value_key": "id",
                "label_key": "name",
                "order_key": "sort_order",
                "source_query_override": "taxonomy_tree_by_geologic"
            },
            {
                "key": "pubyear",
                "label": "Publication Year",
                "axis_query": "timeline_publication_years",
                "value_key": "year",
                "label_key": "label",
                "order_key": "year",
                "source_query_override": "taxonomy_tree_by_pubyear"
            }
        ]
    }
}
```

**B안: 축 모드별 별도 서브뷰** — 단순하지만 서브탭이 늘어남. 비권장.

### 3-2. `source_query_override` 지원

축 모드마다 다른 source_query를 사용해야 할 수 있음.
- 지질시대: `taxonomy_tree_by_geologic` (temporal_code 기반 필터)
- 출판 연도: `taxonomy_tree_by_pubyear` (reference.year 기반 필터)

**scoda-engine 측 대응**: `loadAxis()`에서 `mode.source_query_override`가 있으면
서브뷰의 `source_query`를 런타임에 교체. (엔진 측 소규모 수정 필요)

---

## 4. 작업 목록

### 4-1. `build_trilobase_db.py` 수정

| # | 작업 | 위치 |
|---|------|------|
| 1 | `timeline_geologic_periods` 쿼리 추가 | `_build_queries()` |
| 2 | `timeline_publication_years` 쿼리 추가 | `_build_queries()` |
| 3 | `taxonomy_tree_by_geologic` 쿼리 추가 | `_build_queries()` |
| 4 | `taxonomy_tree_by_pubyear` 쿼리 추가 | `_build_queries()` |
| 5 | `tree_edges_by_timeline` 쿼리 추가 (또는 기존 재활용) | `_build_queries()` |
| 6 | compound view `sub_views`에 `timeline` 추가 | `_build_manifest()` |

### 4-2. scoda-engine 소규모 수정

| # | 작업 | 파일 |
|---|------|------|
| 7 | `source_query_override` 지원 — 축 모드 전환 시 source_query 교체 | `app.js` `loadAxis()` |

### 4-3. 검증

| # | 작업 |
|---|------|
| 8 | DB 빌드 후 쿼리 단독 실행 검증 (sqlite3 CLI) |
| 9 | `.scoda` 패키지 리빌드 + 엔진에서 Timeline 탭 동작 확인 |
| 10 | morph 애니메이션 동작 확인 (지질시대 / 출판 연도 양쪽) |

---

## 5. 열린 질문

### 5-1. 상위 분류군 필터링 전략 — ✅ 결정됨

**결정: 하위에 해당 시대 Genus가 없는 상위 노드는 숨긴다.** 트리 골격이 고정된 채 말단만 깜빡이는 것보다, 가지 자체가 자라나고 사라지는 효과가 타임라인으로서 훨씬 유의미함.

**구현 방법(SQL vs JS 후처리)은 실제 트리 출력을 보고 결정한다.** 두 접근 모두 가능:
- SQL: 재귀 CTE로 leaf가 있는 ancestor만 반환 (쿼리 복잡)
- JS: 전체 트리 받은 뒤 렌더링 전 빈 가지 pruning (쿼리 단순)

### 5-2. 출판 연도 기준의 의미 — ✅ 결정됨

`taxonomy_tree_by_pubyear`에서 assertion의 reference.year를 기준으로 하면:
- 해당 연도까지 "주장된" 분류 관계만 표시
- 같은 분류군이 여러 assertion에 걸쳐 있으면 가장 이른 것 기준으로 포함 (누적 모드이므로 문제없음)
- **결정: profile은 항상 연동되어야 한다.** 모든 타임라인 쿼리에 `profile_id` 조건 필수. edge_cache의 profile_id 조건과 assertion의 연도 조건을 동시에 적용.

### 5-3. edge_query도 타임라인 필터 필요 여부 — ✅ 결정됨

**결정: edge도 쿼리에서 직접 필터한다.** JS 후처리가 아닌 SQL 레벨에서 orphan edge를 제거.
출판 연도 모드에서는 node가 연도 필터로 줄어들므로, edge_query에도 `:timeline_value` 파라미터를 전달하여 존재하는 노드 간의 edge만 반환해야 한다.
