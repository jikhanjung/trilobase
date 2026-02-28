# P74b — Assertion DB UI 기능 동등화 + Classification Profile 표시

**Date:** 2026-02-28

## Context

P74에서 assertion-centric 테스트 DB를 생성했으나, 현재는 핵심 테이블(taxon, reference, assertion)만 있고 junction table·PaleoCore 연결·geography/formation/bibliography UI가 빠져 있다.
기존 trilobase UI와 동등한 기능을 갖추고, assertion-centric의 고유 기능인 **classification profile 전환**을 사용자에게 노출해야 한다.

## 현재 Gap 분석

| 기능 | trilobase.db | assertion DB | 상태 |
|------|-------------|-------------|------|
| genus_formations (4,503) | ✅ | ❌ | 복사 필요 |
| genus_locations (4,849) | ✅ | ❌ | 복사 필요 |
| taxon_bibliography (4,173) | ✅ | ❌ | 복사 필요 |
| PaleoCore 의존성 (pc.*) | ✅ | ❌ | 추가 필요 |
| formations_table 뷰 | ✅ | ❌ | 추가 필요 |
| countries_table 뷰 | ✅ | ❌ | 추가 필요 |
| chronostratigraphy_table 뷰 | ✅ | ❌ | 추가 필요 |
| formation/country/region detail | ✅ | ❌ | 추가 필요 |
| chronostrat detail | ✅ | ❌ | 추가 필요 |
| genus_detail 지리/지층/문헌 섹션 | ✅ | ❌ | 추가 필요 |
| bibliography_detail genera 링크 | ✅ 부분 | ❌ | 추가 필요 |
| classification profile 표시/전환 | ❌ | 구조만 | **신규 구현** |

## 구현 계획

### Step 1: Junction 테이블 복사 (create_assertion_db.py 수정)

`db/trilobase.db`에서 3개 junction table을 그대로 복사:

```python
def copy_junction_tables(src, dst):
    # genus_formations: id, genus_id, formation_id, is_type_locality, notes, created_at
    # genus_locations: id, genus_id, country_id, region, is_type_locality, notes, created_at, region_id
    # taxon_bibliography: id, taxon_id, bibliography_id, relationship_type, opinion_id,
    #                     match_confidence, match_method, notes, created_at
```

스키마도 `create_schema()`에 추가. FK 이름은 기존과 동일 유지 (genus_id = taxon.id).

### Step 2: UI Queries 확장 (create_scoda_metadata() 수정)

기존 trilobase의 33개 쿼리를 assertion-centric 버전으로 변환. 주요 변경:
- `taxonomic_ranks` → `taxon` (또는 `v_taxonomic_ranks`)
- `bibliography` → `reference`
- `parent_id` 직접 참조 → assertion JOIN 또는 `v_taxonomic_ranks.parent_id`
- `pc.*` 테이블 참조는 동일 유지

**추가해야 할 쿼리 (~20개):**
- `genus_detail` — genus용 상세 (hierarchy 포함, assertion 기반 parent 조회)
- `genus_hierarchy` — 조상 체인 (recursive CTE, assertion 기반)
- `genus_ics_mapping` — temporal_code → ICS 매핑
- `genus_formations` — genus의 지층 목록
- `genus_locations` — genus의 국가/지역 목록
- `genus_bibliography` — genus의 참고문헌 목록 (taxon_bibliography 경유)
- `formations_list`, `formation_detail`, `formation_genera`
- `countries_list`, `country_detail`, `country_regions`, `country_genera`
- `regions_list`, `region_detail`, `region_genera`
- `ics_chronostrat_list`, `chronostrat_detail`, `chronostrat_children`, `chronostrat_mappings`, `chronostrat_genera`
- `bibliography_genera` — 참고문헌의 관련 속 목록
- `genera_by_country`, `genera_by_period`
- `profile_detail` — classification profile 상세

### Step 3: UI Manifest 확장

기존 6개 뷰 → **14개 뷰**로 확장:

**기존 유지 (수정):**
1. `taxonomy_tree` — edge_cache 기반으로 전환 + profile 표시
2. `genera_table` — 동일
3. `assertion_table` — 동일
4. `reference_table` — 동일
5. `taxon_detail_view` — 지리/지층/문헌/ICS 섹션 추가
6. `reference_detail_view` — genera 링크 추가

**신규 추가:**
7. `formations_table` — 지층 목록 (pc.formations)
8. `countries_table` — 국가 목록 (pc.geographic_regions)
9. `chronostratigraphy_table` — ICS 차트 (nested hierarchy)
10. `formation_detail` — 지층 상세 + genera 목록
11. `country_detail` — 국가 상세 + regions + genera
12. `region_detail` — 지역 상세 + genera
13. `chronostrat_detail` — ICS 단위 상세
14. `profiles_table` — **신규**: classification profiles 목록 + 현재 활성 프로필 표시

### Step 4: Classification Profile 표시

**`profiles_table` 뷰:**
- 프로필 목록: name, description, edge count, reference basis
- 현재 활성 프로필 표시 (is_active 컬럼)

**`profile_detail` 뷰:**
- 프로필 기본 정보 (name, description, rule_json)
- 이 프로필의 edge 통계 (Order/Family/Genus 수)
- 이 프로필의 트리와 default 프로필 차이 요약

**`taxonomy_tree` 헤더:**
- taxonomy_tree 뷰의 description에 현재 프로필 표시

**`profile_edges` 쿼리:**
- 특정 프로필의 edge 목록 — profile switching 시뮬레이션용

### Step 5: PaleoCore 의존성 복원 (create_assertion_scoda.py 수정)

```python
metadata = {
    "dependencies": [{
        "name": "paleocore",
        "alias": "pc",
        "version": ">=0.1.1,<0.2.0",
        "file": "paleocore.scoda",
        "required": True,
        "description": "Shared paleontological infrastructure"
    }]
}
```

### Step 6: validate_assertion_db.py 검증 항목 추가

- junction table 건수 확인 (genus_formations 4,503, genus_locations 4,849, taxon_bibliography 4,173)
- pc.* 참조 쿼리 정합성

## 수정 대상 파일

| 파일 | 변경 |
|------|------|
| `scripts/create_assertion_db.py` | junction table 복사 + SCODA metadata 확장 |
| `scripts/create_assertion_scoda.py` | paleocore 의존성 추가 |
| `scripts/validate_assertion_db.py` | junction table 검증 추가 |

## 검증

```bash
python scripts/create_assertion_db.py
python scripts/validate_assertion_db.py
python scripts/create_assertion_scoda.py
```
