# P79: Profile-Based Taxonomy Tree + Profile Selector UI

## Context

P78에서 Treatise(2004) 데이터 추가 후, 새 taxon들(Subfamily, Superfamily 등)이 `is_accepted=0`이라 `parent_id=NULL`이 되어 taxonomy tree root level에 orphan으로 노출되는 버그 발생. 근본적 해결: `is_accepted` 대신 `classification_profile` + `classification_edge_cache` 기반으로 tree를 표시하고, 사용자가 profile을 선택하는 UI 추가.

**Cross-repo 변경**: trilobase + scoda-engine 양쪽 수정 필요.

## A. trilobase — 쿼리 & 매니페스트 (`scripts/create_assertion_db.py`)

### A1. `taxonomy_tree` 쿼리 → profile 기반 (line 487-491)

```sql
-- 변경: edge_cache 기반
SELECT t.id, t.name, t.rank, NULL as parent_id, t.author, t.genera_count
FROM taxon t WHERE t.rank = 'Class'
UNION ALL
SELECT t.id, t.name, t.rank, e.parent_id, t.author, t.genera_count
FROM taxon t
JOIN classification_edge_cache e ON e.child_id = t.id
WHERE e.profile_id = COALESCE(:profile_id, 1) AND t.rank != 'Genus'
ORDER BY rank, name
```
params: `{"profile_id": "integer"}`

### A2. `family_genera` 쿼리 → recursive CTE (line 493-500)

Subfamily 지원: Family→Subfamily→Genus 전체 하위 트리 탐색.

```sql
WITH RECURSIVE subtree AS (
    SELECT child_id FROM classification_edge_cache
    WHERE parent_id = :family_id AND profile_id = COALESCE(:profile_id, 1)
    UNION ALL
    SELECT e.child_id FROM classification_edge_cache e
    JOIN subtree s ON e.parent_id = s.child_id
    WHERE e.profile_id = COALESCE(:profile_id, 1)
)
SELECT t.id, t.name, t.author, t.year, t.type_species, t.location, t.is_valid
FROM taxon t JOIN subtree ON subtree.child_id = t.id
WHERE t.rank = 'Genus'
ORDER BY t.name
```
params: `{"family_id": "integer", "profile_id": "integer"}`

### A3. `taxon_children` / `taxon_children_counts` → edge_cache 기반 (line 539-555)

```sql
-- taxon_children: JOIN classification_edge_cache e ... WHERE e.profile_id = COALESCE(:profile_id, 1) AND e.parent_id = :taxon_id
-- taxon_children_counts: 동일 패턴
```

### A4. 새 쿼리: `classification_profiles_selector`

```sql
SELECT id, name, description FROM classification_profile ORDER BY id
```

### A5. 매니페스트 변경 (`_build_manifest()`, line 862)

최상위에 `global_controls` 추가:
```python
"global_controls": [{
    "type": "select",
    "param": "profile_id",
    "label": "Classification",
    "source_query": "classification_profiles_selector",
    "value_key": "id",
    "label_key": "name",
    "default": 1,
}],
```

radial_tree `edge_params` (line 1540):
```python
"edge_params": {"profile_id": "$profile_id"},  # 기존: {"profile_id": 1}
```

### A6. DB 버전: `ASSERTION_VERSION` → `"0.1.2"`

## B. scoda-engine — 프론트엔드

### B1. `app.js` — Global Controls 파싱 & 렌더링

```javascript
let globalControls = {};  // { param_name: current_value }

// loadManifest() 에서:
if (manifest.global_controls) {
    for (const ctrl of manifest.global_controls) {
        const stored = localStorage.getItem(`scoda_ctrl_${ctrl.param}`);
        globalControls[ctrl.param] = stored ? JSON.parse(stored) : ctrl.default;
    }
    renderGlobalControls();
}
```

드롭다운을 `#global-controls` 컨테이너에 렌더. 변경 시:
1. `globalControls[param]` 업데이트 + localStorage 저장
2. `queryCache = {}` 캐시 무효화
3. `switchToView(currentView)` 재로드

### B2. `app.js` — fetchQuery에 global params 병합

```javascript
async function fetchQuery(queryName, params) {
    const mergedParams = { ...globalControls, ...params };
    const cacheKey = `${queryName}?${new URLSearchParams(mergedParams)}`;
    // ...
}
```

`selectTreeLeaf()` item_query URL에도 global params 추가.

### B3. `app.js` — isLeaf 로직 확장 (line 682)

```javascript
// 현재: const isLeaf = node[rankKey] === leafRank;
// 변경:
const isLeaf = node[rankKey] === leafRank || !hasChildren;
```

효과:
- Default: Family에 children 없음 → isLeaf=true (동일)
- Treatise: Family에 Subfamily children → isLeaf via leafRank, Subfamily에 children 없음 → isLeaf=true

### B4. `radial.js` — `$variable` 참조 해석 (line 129)

```javascript
const resolvedParams = {};
for (const [k, v] of Object.entries(rOpts.edge_params || {})) {
    resolvedParams[k] = (typeof v === 'string' && v.startsWith('$'))
        ? (globalControls[v.slice(1)] || v) : v;
}
```

### B5. `index.html` — global controls 컨테이너

```html
<div class="view-tabs-bar">
    <div class="view-tabs" id="view-tabs"></div>
    <div class="global-controls-container" id="global-controls"></div>
    <div class="global-search-container">...</div>
</div>
```

### B6. `style.css` — 드롭다운 스타일

탭바에 맞는 compact select 스타일.

## C. 범용성

`global_controls`는 generic manifest 스키마:
- `type: "select"` + `source_query` → 쿼리 결과를 드롭다운으로
- 어떤 SCODA 패키지든 사용 가능 (분류 프로필, 데이터 버전, 시대별 필터 등)
- 사용자 선택: **localStorage** (`scoda_ctrl_{param_name}`) — 브라우저별 세션 간 유지

## D. V1 범위 제한

| 항목 | 상태 | 비고 |
|------|------|------|
| taxonomy_tree / family_genera / radial_tree / taxon_children | Profile-aware | |
| genus_hierarchy / taxon_detail parent / genera_count | **V2** | is_accepted 기반 유지 |

## 파일 변경 목록

| 파일 | 레포 | 작업 |
|------|------|------|
| `scripts/create_assertion_db.py` | trilobase | 쿼리 4개 수정 + 1개 추가 + 매니페스트 |
| `static/js/app.js` | scoda-engine | global controls + fetchQuery + isLeaf |
| `static/js/radial.js` | scoda-engine | $variable 해석 |
| `templates/index.html` | scoda-engine | controls 컨테이너 |
| `static/css/style.css` | scoda-engine | controls 스타일 |

## 검증

```bash
# DB 재빌드
python scripts/create_assertion_db.py && python scripts/import_treatise.py
python scripts/validate_treatise_import.py && python scripts/validate_assertion_db.py
# SCODA 빌드 & 실행
python scripts/create_scoda.py --type assertion
scoda run dist/trilobase-assertion.scoda
# 확인: profile 전환, tree 구조, genera 로드, radial tree, localStorage 유지
```

## 실행 순서

1. scoda-engine 수정 (app.js, radial.js, index.html, style.css)
2. trilobase 수정 (create_assertion_db.py)
3. DB 재빌드 + 검증
4. SCODA 패키지 빌드 & 테스트
5. 커밋 (scoda-engine 먼저, trilobase 이후)
