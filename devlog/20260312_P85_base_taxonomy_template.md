# P85: Base Taxonomy Template for SCODA Packages

**날짜:** 2026-03-12
**목표:** Taxonomy 기반 SCODA 패키지(trilobase, brachiobase 등)가 공통으로 사용하는 SQL 쿼리와 UI manifest 뷰를 `scoda_engine_core.taxonomy_base` 모듈로 추출하여, 각 패키지 빌드 스크립트에서 중복 없이 재사용할 수 있도록 한다.

## 배경

현재 trilobase와 brachiobase는 각각 독립적인 빌드 스크립트(`build_trilobase_db.py`, `build_brachiobase_db.py`)에서 `_build_queries()`와 `_build_manifest()`를 정의한다. 두 스크립트의 쿼리와 뷰를 비교해보면 약 80% 이상이 동일하거나 설정값만 다른 수준이다. 새로운 taxonomy 패키지(예: ammonite, conodont)를 추가할 때마다 이 코드를 복사-붙여넣기하는 것은 유지보수 비용을 기하급수적으로 늘린다.

`scoda_engine_core`는 이미 `scoda_package.py`, `validate_manifest.py`, `hub_client.py`를 포함하는 경량 코어 패키지이므로, 여기에 `taxonomy_base.py`를 추가하는 것이 자연스러운 확장이다.

## 현황 분석

### 공통 쿼리 (동일 또는 거의 동일)

| 쿼리명 | trilobase | brachiobase | 차이점 |
|--------|-----------|-------------|--------|
| `taxonomy_tree_genera_counts` | O | O | 동일 |
| `family_genera` | O | O | 동일 |
| `genera_list` | O | O | 동일 |
| `taxon_detail` | O | O | 동일 |
| `taxon_assertions` | O | O | 동일 |
| `taxon_children` | O | O | 동일 |
| `genus_hierarchy` | O | O | 동일 |
| `assertion_list` | O | O | 동일 |
| `reference_list` | O | O | 동일 |
| `profile_list` | O | O | 동일 |
| `classification_profiles_selector` | O | O | 동일 |
| `radial_tree_nodes` | O | O | 동일 |
| `radial_tree_edges` | O | O | 동일 |
| `profile_diff` | O | O | 동일 |
| `profile_diff_edges` | O | O | 동일 |

**`taxonomy_tree`만 유일하게 SQL이 다르다:**
- trilobase: `WHERE t.rank = 'Class'`로 root를 찾음 (단일 class 가정)
- brachiobase: 동적으로 root 노드를 찾음 (`parent_id에 있지만 child_id에 없는 노드`)

brachiobase의 방식이 더 범용적이므로 이를 base로 채택한다.

### 공통 UI 뷰 (동일 또는 설정만 다른 것)

| 뷰 | trilobase | brachiobase | 차이점 |
|----|-----------|-------------|--------|
| `taxonomy_tree` | O | O | description 텍스트, trilobase에 `skip_ranks: []`와 `location` 컬럼 추가 |
| `genera_table` | O | O | trilobase에 `temporal_code`, `location` 컬럼 추가 |
| `assertion_table` | O | O | 동일 |
| `reference_table` | O | O | trilobase에 `volume`, `pages`, `reference_type` 컬럼 추가 + `on_row_click` |
| `tree_chart` | O | O | `rank_radius` 값 차이 |
| `profile_comparison` | O | O | `default` 비교 대상 다름 (trilobase: 3, brachiobase: 2), `rank_radius` 차이 |
| `taxon_detail_view` | O | O | 구조적으로 크게 다름 (아래 참조) |

### 패키지별 차이점

**trilobase 전용 (brachiobase에 없음):**
- 쿼리 20개+: `valid_genera_list`, `taxon_children_counts`, `genus_synonyms`, `genus_ics_mapping`, `genus_formations`, `genus_locations`, `genus_bibliography`, `taxon_bibliography`, `reference_detail`, `reference_assertions`, `reference_genera`, `formations_list`, `formation_detail`, `formation_genera`, `countries_list`, `country_detail`, `country_regions`, `country_genera`, `regions_list`, `region_detail`, `region_genera`, `ics_chronostrat_list`, `chronostrat_detail`, `chronostrat_children`, `chronostrat_mappings`, `chronostrat_genera`, `genera_by_country`, `genera_by_period`, `profile_detail`, `profile_edges`
- 뷰: `formations_table`, `countries_table`, `chronostratigraphy_table`, `profiles_table`, `genus_detail`, `reference_detail_view`, `formation_detail`, `country_detail`, `region_detail`, `chronostrat_detail`, `profile_detail_view`
- 기능: `editable_entities` 섹션, `redirect` (taxon_detail_view → genus_detail), `sub_queries` 패턴

**brachiobase 전용:**
- 현재 없음 (brachiobase는 trilobase의 부분집합)

**`taxon_detail_view` 구조 차이:**
- trilobase: `sub_queries` + `linked_table` + `redirect`를 활용한 고급 패턴, `genus_detail` 별도 뷰 존재
- brachiobase: 단순 `sections` + inline `source_query` 패턴 (구버전 스타일)

**`rank_radius` 차이:**
- trilobase: `{_root: 0, Class: 0.08, Order: 0.20, Suborder: 0.32, Superfamily: 0.44, Family: 0.56, Subfamily: 0.70, Genus: 1.0}`
- brachiobase: `{_root: 0, Phylum: 0.03, Subphylum: 0.06, Class: 0.10, Order: 0.18, Suborder: 0.28, Superfamily: 0.40, Family: 0.54, Subfamily: 0.70, Genus: 1.0}`

각 분류군의 rank 분포 비율에 따라 시각적으로 최적화한 결과이므로, 패키지별 설정으로 노출해야 한다.

## 설계

### 모듈 구조

```
scoda_engine_core/
├── taxonomy_base.py          # ★ 신규 모듈
├── scoda_package.py
├── validate_manifest.py
└── hub_client.py
```

`taxonomy_base.py` 하나의 파일로 충분하다. 내부적으로 3가지 주요 함수와 설정 dataclass를 제공한다.

### API 설계

```python
# scoda_engine_core/taxonomy_base.py

from dataclasses import dataclass, field

@dataclass
class TaxonomyConfig:
    """패키지별 커스터마이즈 포인트."""
    # 기본 정보
    organism_name: str                    # "trilobite", "brachiopod"
    organism_name_plural: str             # "trilobites", "brachiopods"

    # 프로필
    default_profile_id: int = 1
    default_compare_profile_id: int = 2   # trilobase=3, brachiobase=2

    # rank_radius (tree_chart용)
    rank_radius: dict = field(default_factory=lambda: {
        "_root": 0,
        "Class": 0.08,
        "Order": 0.20,
        "Suborder": 0.32,
        "Superfamily": 0.44,
        "Family": 0.56,
        "Subfamily": 0.70,
        "Genus": 1.0,
    })

    # genera_table 추가 컬럼
    genera_extra_columns: list = field(default_factory=list)

    # taxonomy_tree item_columns 추가 컬럼
    tree_item_extra_columns: list = field(default_factory=list)

    # reference_table 추가 컬럼
    reference_extra_columns: list = field(default_factory=list)

    # taxonomy_tree의 hierarchy_options 추가 키
    tree_hierarchy_extra: dict = field(default_factory=dict)


def base_queries() -> list[tuple]:
    """공통 쿼리 15개 반환. taxonomy_tree는 범용(brachiobase식) SQL 사용."""
    ...

def base_manifest(config: TaxonomyConfig) -> dict:
    """공통 뷰 + config 반영한 manifest dict 반환.

    포함 뷰: taxonomy_tree, genera_table, assertion_table,
             reference_table, tree_chart, profile_comparison,
             taxon_detail_view
    """
    ...

def merge_queries(base: list, extras: list) -> list:
    """base 쿼리 리스트에 extras를 추가/덮어쓰기(같은 이름이면 교체)."""
    ...

def merge_manifest(base: dict, overrides: dict) -> dict:
    """base manifest에 overrides를 deep-merge.

    - views 키는 개별 뷰 단위로 병합
    - 특수 키 "__delete__"로 뷰 제거 가능
    """
    ...
```

### Deep Merge 전략

manifest의 `views` dict에 대해:
1. overrides에 있는 뷰 키가 base에도 있으면 → **뷰 전체를 교체** (부분 패치는 복잡도 대비 이점이 적음)
2. overrides에 있는 뷰 키가 base에 없으면 → **추가**
3. `__delete__` 마커로 base 뷰 제거 가능

개별 컬럼 수준의 패치는 지원하지 않되, `TaxonomyConfig`의 `*_extra_columns`로 가장 흔한 확장 케이스를 처리한다.

### 사용 예시

**brachiobase (최소 설정):**
```python
from scoda_engine_core.taxonomy_base import (
    TaxonomyConfig, base_queries, base_manifest
)

config = TaxonomyConfig(
    organism_name="brachiopod",
    organism_name_plural="brachiopods",
    default_compare_profile_id=2,
    rank_radius={
        "_root": 0, "Class": 0.06, "Order": 0.14,
        "Suborder": 0.24, "Superfamily": 0.36,
        "Family": 0.50, "Subfamily": 0.66, "Genus": 1.0,
    },
)

def _build_queries():
    return base_queries()

def _build_manifest():
    return base_manifest(config)
```

**trilobase (공통 + 대량 확장):**
```python
from scoda_engine_core.taxonomy_base import (
    TaxonomyConfig, base_queries, base_manifest,
    merge_queries, merge_manifest
)

config = TaxonomyConfig(
    organism_name="trilobite",
    organism_name_plural="trilobites",
    default_compare_profile_id=3,
    genera_extra_columns=[
        {"key": "temporal_code", "label": "Period", "sortable": True, "searchable": True},
    ],
    tree_item_extra_columns=[
        {"key": "location", "label": "Location", "truncate": 30},
    ],
    reference_extra_columns=[
        {"key": "volume", "label": "Volume"},
        {"key": "pages", "label": "Pages"},
        {"key": "reference_type", "label": "Type", "sortable": True},
    ],
    tree_hierarchy_extra={"skip_ranks": []},
)

def _build_queries():
    return merge_queries(base_queries(), _trilobase_extra_queries())

def _build_manifest():
    base = base_manifest(config)
    return merge_manifest(base, {
        "views": {
            "formations_table": { ... },
            "countries_table": { ... },
            "genus_detail": { ... },
            # taxon_detail_view를 완전 교체 (redirect 포함 고급 버전)
            "taxon_detail_view": { ... },
        },
        "editable_entities": { ... },
    })
```

## 구현 단계

### Phase 1: 공통 쿼리 추출 (scoda_engine_core)

1. `core/scoda_engine_core/taxonomy_base.py` 생성
2. `TaxonomyConfig` dataclass 정의
3. `base_queries()` 구현 — 15개 공통 쿼리 (taxonomy_tree는 brachiobase식 범용 SQL)
4. `merge_queries()` 헬퍼 구현
5. 단위 테스트: 쿼리 이름 중복 없음, merge 동작 검증

### Phase 2: 공통 manifest 추출 (scoda_engine_core)

1. `base_manifest(config)` 구현 — 7개 공통 뷰
   - `taxonomy_tree`, `genera_table`, `assertion_table`, `reference_table`
   - `tree_chart`, `profile_comparison` (4 sub-views 포함)
   - `taxon_detail_view` (기본 버전)
2. `merge_manifest()` 헬퍼 구현
3. `TaxonomyConfig`의 extra_columns가 올바르게 주입되는지 테스트

### Phase 3: brachiobase 마이그레이션

1. `build_brachiobase_db.py`의 `_build_queries()`를 `base_queries()` 호출로 교체
2. `_build_manifest()`를 `base_manifest(config)` 호출로 교체
3. 기존 DB와 diff 비교하여 동일 결과 확인 (쿼리 SQL, manifest JSON)

### Phase 4: trilobase 마이그레이션

1. `build_trilobase_db.py`에서 공통 쿼리 15개를 `base_queries()`로 교체
2. trilobase 전용 쿼리 20+개는 `_trilobase_extra_queries()`로 분리
3. manifest에서 공통 뷰 7개는 `base_manifest(config)`으로, 전용 뷰는 `merge_manifest()`로 추가
4. 기존 DB와 diff 비교
5. 118개 테스트 전체 통과 확인

### Phase 5: 문서화 + 정리

1. `taxonomy_base.py`에 docstring 완비
2. devlog 작성
3. HANDOFF.md 갱신

## 고려사항

### taxonomy_tree SQL 통합
trilobase의 `WHERE t.rank = 'Class'` 방식은 Brachiopoda처럼 Phylum을 root로 쓰는 경우 동작하지 않는다. brachiobase의 동적 root 탐색 방식이 범용적이므로 이를 base로 채택. trilobase 전환 후 결과 동일 여부 검증 필수.

### taxon_detail_view의 버전 차이
brachiobase는 구버전 스타일(inline source_query), trilobase는 신버전(sub_queries + linked_table + redirect). base에서는 trilobase 스타일(신버전)로 제공하되, brachiobase 마이그레이션 시 함께 업그레이드하는 것이 바람직하다.

### 버전 관리
`taxonomy_base.py`는 `scoda_engine_core` 패키지의 일부이므로 scoda-engine의 버전과 함께 관리된다. trilobase/brachiobase 빌드 스크립트는 scoda-engine을 의존성으로 갖고 있으므로 추가 의존성 설정은 불필요.

### 확장성
향후 새 taxonomy 패키지 추가 시:
1. `TaxonomyConfig` 인스턴스 생성 (organism_name, rank_radius 등)
2. `base_queries()` + 패키지 전용 쿼리 추가
3. `base_manifest(config)` + 패키지 전용 뷰 override

이 패턴으로 새 분류군 패키지를 빠르게 scaffold 할 수 있다.

### 리스크
- manifest deep merge에서 예상치 못한 충돌 가능. 뷰 단위 교체(전체 교체) 전략을 기본으로 하고, 컬럼 수준 패치는 `TaxonomyConfig`의 명시적 extra_columns로 제한하여 방지.
- trilobase의 `editable_entities`는 base에 포함 여부를 Phase 4에서 판단.

## 주요 파일

| 파일 | 역할 |
|------|------|
| `scoda-engine/core/scoda_engine_core/taxonomy_base.py` | ★ 신규 — 공통 쿼리, manifest, config, merge 함수 |
| `trilobase/scripts/build_brachiobase_db.py` | Phase 3 마이그레이션 대상 |
| `trilobase/scripts/build_trilobase_db.py` | Phase 4 마이그레이션 대상 |
