# P75: Radial Taxonomy Tree Visualization Plan

**날짜**: 2026-02-28 (P74/P74b 반영 + 엔진 분리 업데이트)
**상태**: 계획 — P74/P74b 구조 변경 + scoda-engine P20 완료 후 착수
**의존성**: P74 (assertion-centric DB), P74b (UI 기능 동등화), **scoda-engine P20 (radial display 지원)**

## 목적

Trilobase의 taxonomy hierarchy (Class → Order → Suborder → Superfamily → Family → Genus, 총 5,341 레코드)를 방사형(radial) 트리로 시각화한다. 루트(Trilobita)를 원 중앙에, 각 rank를 동심원에, leaf 노드를 최외곽에 배치하여 전체 분류 체계를 한눈에 조망하고 zoom in/out으로 세부 탐색이 가능하게 한다.

## 아키텍처 결정

Radial tree는 **scoda-engine의 새 display mode**로 구현한다.

- 기존 hierarchy 뷰: `display: "tree"` (DOM 트리), `display: "nested_table"` (ICS 차트)
- 신규: `display: "radial"` — 동일 hierarchy 데이터를 Canvas+SVG로 방사형 렌더링
- 엔진 수정사항은 별도 계획: **scoda-engine P20**
- Trilobase에서는 manifest에 뷰 정의만 추가

## 사용자 결정 사항

- **배치**: scoda-engine의 `display: "radial"` 뷰 모드 (탭으로 전환)
- **깊이**: UI에서 Family ↔ Genus 토글 가능
- **데이터**: SCODA API (`fetchQuery()`) 호출

---

## P74/P74b 반영 사항

### 스키마 변경 대응

| 항목 | P74 이전 (P52) | P74 이후 (assertion-centric) |
|------|----------------|------------------------------|
| 분류 테이블 | `taxonomic_ranks` (parent_id 직접 저장) | `taxon` (parent_id 없음) |
| 트리 파생 | parent_id 직접 조회 | `classification_edge_cache` 또는 호환 뷰 `v_taxonomic_ranks` |
| 의견/관계 | `taxonomic_opinions` (1,139건) | `assertion` (6,142건) |
| 참고문헌 | `bibliography` | `reference` |

### Classification Profile 전환

P74의 classification profile 전환은 trilobase 고유 기능이므로 엔진의 radial display에는 포함하지 않음. 추후 manifest extension 또는 trilobase 전용 JS 오버라이드로 구현.

### Agnostida 처리

Agnostida (189 taxa)는 CTE 트리 미도달. 쿼리 수준에서 처리:
- `radial_tree_edges` 쿼리가 Agnostida 포함/제외 옵션 제공
- 엔진의 radial display는 받은 데이터를 그대로 렌더링

---

## Trilobase 쪽 구현 (이 계획의 범위)

### Step 1: 쿼리 추가

**파일**: `scripts/create_assertion_db.py` (metadata 섹션)

**`radial_tree_nodes`**:
```sql
SELECT id, name, rank, genera_count, is_valid,
       temporal_code, author, year
FROM taxon
ORDER BY rank, name
```

**`radial_tree_edges`**:
```sql
SELECT child_id, parent_id
FROM classification_edge_cache
WHERE profile_id = :profile_id
```

### Step 2: Manifest 뷰 정의 추가

```json
"radial_tree": {
  "type": "hierarchy",
  "display": "radial",
  "title": "Radial Tree",
  "icon": "bi-bullseye",
  "source_query": "radial_tree_nodes",
  "hierarchy_options": {
    "id_key": "id",
    "parent_key": "parent_id",
    "label_key": "name",
    "rank_key": "rank"
  },
  "radial_display": {
    "edge_query": "radial_tree_edges",
    "edge_params": { "profile_id": 1 },
    "color_key": "order",
    "count_key": "genera_count",
    "depth_toggle": true,
    "leaf_rank": "Genus",
    "on_node_click": { "type": "detail", "view": "taxon_detail_view" }
  }
}
```

> 노드(source_query)와 엣지(edge_query)를 분리하여 프로필 전환 시 엣지만 재로드 가능.

### Step 3: 검증

1. DB 리빌드 → 쿼리 동작 확인
2. 엔진에서 Radial Tree 탭 표시 → 방사형 트리 렌더링
3. 노드 클릭 → detail 모달 연동

---

## 수정 파일 목록 (trilobase repo)

| 파일 | 작업 |
|------|------|
| `scripts/create_assertion_db.py` | `radial_tree_nodes`, `radial_tree_edges` 쿼리 + manifest 뷰 추가 |

엔진 수정사항은 **scoda-engine repo P20** 참조.

---

## 검증 방법

1. `python scripts/create_assertion_db.py` → DB 생성 성공
2. `/api/queries/radial_tree_nodes/execute` → 5,341행 반환
3. `/api/queries/radial_tree_edges/execute?profile_id=1` → 5,083 edges 반환
4. Radial Tree 탭 클릭 → 방사형 트리 렌더링
5. 줌 인/아웃 → LOD 변화 (Order → Family → Genus 순차 표시)
6. Family ↔ Genus 토글 → 레이아웃 전환
7. 노드 클릭/hover → 툴팁 및 detail 모달
8. 검색 → 노드 하이라이트 + 자동 줌
