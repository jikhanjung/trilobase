# P79: Profile-Based Taxonomy Tree + Profile Selector UI

**Date:** 2026-03-01

## Summary

P78에서 Treatise(2004) 데이터 추가 후, 새 taxon들(Subfamily, Superfamily 등)이 `is_accepted=0`이라 taxonomy tree root level에 orphan으로 노출되는 문제 해결. `classification_edge_cache` 기반으로 tree를 표시하고, 사용자가 profile을 선택하는 UI 추가.

## Changes

### scoda-engine (4 files)

| File | Changes |
|------|---------|
| `static/js/app.js` | `globalControls` state, `renderGlobalControls()`, `fetchQuery()` param merge, `isLeaf` logic fix, `selectTreeLeaf()` global params |
| `static/js/radial.js` | `$variable` reference resolution in `edge_params` |
| `templates/index.html` | `#global-controls` container in tab bar |
| `static/css/style.css` | `.global-control-*` compact select styles |

### trilobase (1 file + DB)

| File | Changes |
|------|---------|
| `scripts/create_assertion_db.py` | 4 queries → edge_cache based, 1 new query, manifest `global_controls`, `$profile_id` variable, version 0.1.2 |
| `db/trilobase-assertion-0.1.2.db` | Rebuilt DB with Treatise import |

## Query Changes

| Query | Before | After |
|-------|--------|-------|
| `taxonomy_tree` | `v_taxonomic_ranks` view | `classification_edge_cache` JOIN with `profile_id` param |
| `family_genera` | `assertion` JOIN (single level) | Recursive CTE through edge_cache (Family→Subfamily→Genus) |
| `taxon_children` | `assertion` JOIN | `classification_edge_cache` JOIN |
| `taxon_children_counts` | `assertion` JOIN | `classification_edge_cache` JOIN |
| `classification_profiles_selector` | (new) | `SELECT id, name, description FROM classification_profile` |

## Manifest Changes

- `global_controls`: Profile selector dropdown (`classification_profiles_selector` source)
- `radial_tree.edge_params.profile_id`: `1` → `"$profile_id"` (resolved at runtime)

## Generic Framework

`global_controls`는 SCODA manifest의 범용 스키마:
- `type: "select"` + `source_query` → 쿼리 결과를 드롭다운으로 렌더
- 사용자 선택은 `localStorage`에 저장 (`scoda_ctrl_{param_name}`)
- 변경 시 `queryCache` 무효화 → 현재 뷰 재로드
- `fetchQuery()`에 자동 병합 → 모든 쿼리에 param 전달

## Validation

- Treatise import: 17/17 checks passed
- Assertion DB: 15/15 checks passed
- Trilobase tests: 112/112 passed
- scoda-engine tests: 223/223 passed
- Profile 1 (default): 224 tree nodes
- Profile 3 (treatise2004): 272 tree nodes (+48 Subfamily/Superfamily)

## V1 Scope

| Item | Status |
|------|--------|
| taxonomy_tree / family_genera / taxon_children / taxon_children_counts | Profile-aware |
| radial_tree | Profile-aware ($variable) |
| genus_hierarchy / taxon_detail parent / genera_count | V2 (is_accepted 기반 유지) |
