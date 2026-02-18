# P59: Manifest Schema 정규화 — DB 레벨 (A-3)

**작성일:** 2026-02-18
**유형:** Plan
**선행 문서:** P55 (Hierarchy View 통합), P56 (로드맵)

---

## 배경

Phase 70에서 `type: "tree"` + `tree_options`와 `type: "chart"` + `chart_options`를
`type: "hierarchy"` + `display: "tree"|"nested_table"` + `hierarchy_options`로 통합했으나,
이 변환은 클라이언트(`app.js`)의 `normalizeViewDef()` 런타임 함수에서 수행 중.

DB에 저장된 manifest는 여전히 legacy 형식 사용 중:
- `trilobase.db`: `taxonomy_tree` → `type: "tree"`, `chronostratigraphy_table` → `type: "chart"`
- `paleocore.db`: `chronostratigraphy_chart` → `type: "chart"`

## 목표

DB의 manifest를 새 `hierarchy` 스키마로 직접 업데이트하여 런타임 변환 의존 해소.
`normalizeViewDef()`는 외부 패키지 하위 호환용으로 유지.

## 수정 대상

### 1. `scripts/add_scoda_manifest.py` (trilobase manifest 소스)

| 뷰 | 변경 전 | 변경 후 |
|----|---------|---------|
| `taxonomy_tree` | `type: "tree"`, `tree_options: {...}` | `type: "hierarchy"`, `display: "tree"`, `hierarchy_options: {...}`, `tree_display: {...}` |
| `chronostratigraphy_table` | `type: "chart"`, `chart_options: {...}` | `type: "hierarchy"`, `display: "nested_table"`, `hierarchy_options: {...}`, `nested_table_display: {...}` |

### 2. `scripts/create_paleocore.py` (paleocore manifest 소스)

| 뷰 | 변경 전 | 변경 후 |
|----|---------|---------|
| `chronostratigraphy_chart` | `type: "chart"`, `chart_options: {...}` | `type: "hierarchy"`, `display: "nested_table"`, `hierarchy_options: {...}`, `nested_table_display: {...}` |

### 3. `tests/conftest.py` (test fixture manifest)

동일한 변환 적용. 테스트 fixture도 새 스키마 사용.

### 4. 실제 DB 업데이트

```bash
python scripts/add_scoda_manifest.py        # trilobase.db 갱신
python scripts/create_paleocore.py           # paleocore.db 재생성 (또는 직접 UPDATE)
```

### 5. `scripts/validate_manifest.py` 보강

`_validate_hierarchy_view()`에 `display`, `tree_display`, `nested_table_display` 검증 추가.

## 변환 규칙 (normalizeViewDef 로직 그대로)

### tree → hierarchy
```python
# Before:
{"type": "tree", "tree_options": {"id_key": "id", "parent_key": "parent_id", ...}}

# After:
{
    "type": "hierarchy",
    "display": "tree",
    "hierarchy_options": {
        "id_key": "id", "parent_key": "parent_id", "label_key": "name",
        "rank_key": "rank", "sort_by": "label", "order_key": "id", "skip_ranks": []
    },
    "tree_display": {
        "leaf_rank": "Family", "count_key": "genera_count",
        "on_node_info": {...}, "item_query": "...", "item_param": "...",
        "item_columns": [...], "on_item_click": {...}, "item_valid_filter": {...}
    }
}
```

### chart → hierarchy
```python
# Before:
{"type": "chart", "chart_options": {"id_key": "id", ..., "rank_columns": [...]}}

# After:
{
    "type": "hierarchy",
    "display": "nested_table",
    "hierarchy_options": {
        "id_key": "id", "parent_key": "parent_id", "label_key": "name",
        "rank_key": "rank", "sort_by": "order_key", "order_key": "display_order",
        "skip_ranks": ["Super-Eon"]
    },
    "nested_table_display": {
        "color_key": "color", "rank_columns": [...],
        "value_column": {...}, "cell_click": {...}
    }
}
```

## 검증 방법

```bash
# 1. DB 갱신
python scripts/add_scoda_manifest.py
python scripts/create_paleocore.py

# 2. manifest validator 실행
python scripts/validate_manifest.py trilobase.db
python scripts/validate_manifest.py paleocore.db

# 3. 전체 테스트
pytest tests/ -v

# 4. 웹 UI 수동 확인 (tree 렌더링, chart 렌더링 정상 여부)
```

## 주의사항

- `normalizeViewDef()`는 삭제하지 않음 (외부 .scoda 패키지 하위 호환)
- SPA(`spa/app.js`)에도 동일한 `normalizeViewDef()`가 있을 수 있으므로 유지
- `type: "tree"`, `type: "chart"`를 `validate_manifest.py`의 `KNOWN_VIEW_TYPES`에서 제거하지 않음 (하위 호환)
