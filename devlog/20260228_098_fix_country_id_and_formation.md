# T-5: genus_locations country_id 수정 + Formation 오정렬 해결

**Date:** 2026-02-28

## Summary

`genus_locations` 테이블의 두 가지 대규모 데이터 품질 문제를 수정:

1. **country_id 매핑 오류 수정** (Phase A): 4,841건 중 3,769건 (77.8%) 재매핑
2. **Formation 필드 오정렬 수정** (Phase B): 350건 수정 (Type 1: 8, Type 2: 36, Type 3: 306)

## Root Cause

**country_id 오류**: `normalize_database.py`의 `LIKE '%country_name'` 반복 UPDATE에서 후속 매칭이 이전 결과를 덮어씀 (예: China 1,023건이 England로 잘못 배정).

**Formation 오정렬**: `create_database.py`가 `]` ~ `; FAMILY;` 사이 텍스트를 첫 `,` 기준으로만 분할하여 `Region, Country` 패턴에서 region이 formation 필드로 잘못 저장됨.

## Phase A: country_id Fix

**Script**: `scripts/fix_country_id.py`

- Location 텍스트의 마지막 comma 뒤 부분에서 올바른 국가명 추출
- COUNTRY_NORMALIZE 맵으로 국가명 정규화 (13개 변형)
- LOCATION_OVERRIDES로 특수 케이스 처리 (Metagnostus, Iberocoryphe)
- Unicode curly quote (U+201D) 처리

**Results**:
| Metric | Value |
|--------|-------|
| Already correct | 1,072 (22.1%) |
| Updated | 3,769 (77.8%) |
| Parse errors | 0 |
| Unmatched countries | 0 |

**Top 5 country 수정 (before → after)**:
| Country | Before | After |
|---------|--------|-------|
| China | 111 → | 1,066 |
| USA | 315 → | 669 |
| Russia | 256 → | 581 |
| England | 1,027 → | 121 |
| Mexico | 678 → | 46 |

## Phase B: Formation Misalignment Fix

**Script**: `scripts/fix_formation_misalignment.py`

세 가지 유형으로 분류하여 처리:

| Type | Description | Count | Action |
|------|-------------|-------|--------|
| Type 1 | formation=country, location=NULL | 8 | formation→NULL, genus_formations 삭제, genus_locations 생성 |
| Type 2 | formation=location (동일값) | 36 | formation→NULL, genus_formations 삭제 |
| Type 3 | formation=region, location=country | 306 | formation→NULL, genus_formations 삭제, genus_locations.region 설정 |

- Formation whitelist (56개)로 유효한 지층명 보호
- 182개 orphan formation 레코드 정리 (pc.formations)

**Post-fix counts**:
| Table | Before | After | Change |
|-------|--------|-------|--------|
| genus_formations | 4,853 | 4,503 | -350 |
| genus_locations | 4,841 | 4,849 | +8 |
| Genera with formation | 4,853 | 4,503 | -350 |

## Phase C: region_id 수정 + location 복원

### region_id 수정 (272건)

`genus_locations.region_id`가 `geographic_regions`의 country-level 엔트리를 직접 가리키는 경우
→ 올바른 region-level 엔트리로 재연결:

| 구분 | 건수 |
|------|------|
| 기존 region 매칭 | 160 |
| 신규 region 생성 후 매칭 | 104 (93개 region 생성) |
| Type 1 신규분 country-level 연결 | 7 |
| Baltic Russia 신규 생성 + 연결 | 1 |
| Scotland, N Wales 직접 연결 | 2 |
| **NULL region_id 잔여** | **0** |

### taxonomic_ranks.location 복원 (314건)

Phase B에서 formation→NULL로 바꾸면서 location이 country만 남은 케이스 수정:

- Type 3 (306건): `China` → `Zhejiang, China` (region + country 복원)
- Type 1 (8건): NULL → `Argentina`, `Baltic Russia, Russia` 등

### genus_locations 쿼리 수정

`ui_queries.genus_locations`: country/region level 분기 처리
- `r.level = 'country'` → country_name으로 직접 표시
- `r.level = 'region'` → parent를 country로, 자신을 region으로 표시

## New Tests (4)

`TestCountryIdConsistency` class in `tests/test_trilobase.py`:

1. `test_country_id_match_rate` — country_id 매칭률 95%+ 검증
2. `test_china_not_mapped_to_england` — 최대 오류 패턴 재발 방지
3. `test_formation_not_country_name` — location=NULL 시 formation이 국가명이 아닌지 검증
4. `test_type1_genera_have_locations` — Type 1 수정 대상 8개 genus의 genus_locations 존재 검증

**Test results**: 112 passed (108 + 4 new)

## Files Changed

| File | Action |
|------|--------|
| `scripts/fix_country_id.py` | **NEW** — Phase A: country_id 일괄 수정 |
| `scripts/fix_formation_misalignment.py` | **NEW** — Phase B: formation 오정렬 수정 |
| `db/trilobase.db` | UPDATE genus_locations + taxonomic_ranks + genus_formations + ui_queries |
| `db/paleocore.db` | DELETE orphan formations, INSERT 93 regions in geographic_regions |
| `tests/test_trilobase.py` | ADD TestCountryIdConsistency (4 tests) |

## Version

**0.2.4 → 0.2.5** (Patch: data quality fix)
