# P76: Radial Tree View → Canonical trilobase.scoda

**날짜**: 2026-03-01
**상태**: 구현
**의존성**: P75 (assertion DB radial tree), scoda-engine radial display 완료

## 목적

P75에서 `trilobase-assertion` 패키지 전용으로 구현된 Radial Tree 기능을 **canonical `trilobase.scoda` 패키지**에도 추가한다.

## 핵심 차이점 (P75 vs P76)

| 항목 | P75 (assertion DB) | P76 (canonical DB) |
|------|--------------------|--------------------|
| 트리 테이블 | `taxon` (parent_id 없음) | `taxonomic_ranks` (parent_id 직접 보유) |
| 엣지 소스 | `classification_edge_cache` 별도 쿼리 | `parent_id` 칼럼 직접 사용 |
| 쿼리 수 | 2개 (nodes + edges) | **1개** (nodes만, parent_id 포함) |
| manifest | `edge_query` + `edge_params` 필요 | **불필요** |

`taxonomic_ranks`에 이미 `parent_id`가 있으므로, 별도 edge 쿼리 없이 **쿼리 1개 + manifest 뷰 1개**만 추가하면 된다.

## 구현

### Step 1: 쿼리 추가 (`scripts/add_scoda_ui_tables.py`)

`radial_tree_nodes` 쿼리를 `insert_queries()`에 추가:

```sql
SELECT id, name, rank, parent_id, genera_count, is_valid,
       temporal_code, author, year
FROM taxonomic_ranks
WHERE is_valid = 1 OR rank <> 'Genus'
ORDER BY rank, name
```

**기존 `taxonomy_tree` 쿼리와의 차이:**
- `taxonomy_tree`: Genus rank 전체 제외
- `radial_tree_nodes`: **valid Genus (is_valid=1)** 포함, invalid Genus만 제외
- `parent_id` 칼럼을 반환하여 별도 edge 쿼리 불필요

### Step 2: Manifest 뷰 추가 (`scripts/add_scoda_manifest.py`)

`radial_tree` 뷰를 views dict에 추가:

```python
"radial_tree": {
    "type": "hierarchy",
    "display": "radial",
    "title": "Radial Tree",
    "description": "Radial taxonomy — Class at center, genera at periphery",
    "icon": "bi-bullseye",
    "source_query": "radial_tree_nodes",
    "hierarchy_options": {
        "id_key": "id",
        "parent_key": "parent_id",
        "label_key": "name",
        "rank_key": "rank",
    },
    "radial_display": {
        "color_key": "rank",
        "count_key": "genera_count",
        "depth_toggle": True,
        "leaf_rank": "Genus",
        "on_node_click": {"detail_view": "rank_detail", "id_key": "id"},
        "rank_radius": {
            "_root": 0, "Class": 0.10, "Order": 0.25,
            "Suborder": 0.40, "Superfamily": 0.55,
            "Family": 0.70, "Genus": 1.0,
        },
    },
}
```

**P75 대비 차이점:** `edge_query`, `edge_params` 속성 없음 — `parent_id`가 `source_query` 결과에 포함.

### Step 3: DB 재빌드 + .scoda 패키지 생성

```bash
python scripts/add_scoda_ui_tables.py    # 쿼리 추가
python scripts/add_scoda_manifest.py     # manifest 갱신
python scripts/create_scoda.py           # .scoda 패키지 생성
```

## 수정 파일

| 파일 | 작업 |
|------|------|
| `scripts/add_scoda_ui_tables.py` | `radial_tree_nodes` 쿼리 추가 |
| `scripts/add_scoda_manifest.py` | `radial_tree` manifest 뷰 추가 |

## 검증

1. `sqlite3 db/trilobase.db "SELECT name FROM ui_queries WHERE name='radial_tree_nodes'"` → 쿼리 존재 확인
2. `sqlite3 db/trilobase.db "SELECT manifest_json FROM ui_manifest" | python3 -m json.tool | grep radial` → manifest 항목 확인
3. `trilobase.scoda` 로드 → Radial Tree 탭 표시 확인
