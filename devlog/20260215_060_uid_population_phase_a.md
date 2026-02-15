# UID Population Phase A — 확정적 UID 생성 완료

**날짜:** 2026-02-15
**계획:** `devlog/20260215_P42_uid_population_phase_a.md`

## 목표

SCODA Stable UID Schema v0.2 Section 11.5의 Phase A를 구현.
외부 조회 없이 DB 내 기존 데이터만으로 100% 생성 가능한 확정적 UID를 5개 테이블에 부여.

## 결과 요약

| 테이블 | DB | 레코드 | 커버리지 | 주요 method | 중복 |
|--------|-----|--------|---------|------------|------|
| `ics_chronostrat` | paleocore.db | 178 | 100% | ics_uri (178, all high) | 0 |
| `temporal_ranges` | paleocore.db | 28 | 100% | code (28, all high) | 0 |
| `countries` | paleocore.db | 142 | 100% | iso3166-1=56 (high) + fp_v1=86 (medium/low) | 0 |
| `geographic_regions` | paleocore.db | 562 | 100% | name=497 + iso3166-1=54 + fp_v1=11 | 0 |
| `taxonomic_ranks` | trilobase.db | 5,340 | 100% | name=5,310 (high) + name+disambiguation=30 (medium) | 0 |
| **합계** | | **6,250** | **100%** | | **0** |

## UID 샘플

```
scoda:taxon:class:Trilobita
scoda:taxon:genus:Paradoxides
scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Cambrian
scoda:strat:temporal:code:LCAM
scoda:geo:country:iso3166-1:AU
scoda:geo:region:name:AU:queensland
```

## 변경 상세

### Step 1: countries.code에 ISO 3166-1 alpha-2 코드 채우기

**파일:** `scripts/populate_iso_codes.py` (신규)

- `pycountry`로 자동 매칭 + `MANUAL_MAP` 수동 보정 (190건)
- 서브내셔널 지역(Alaska, Yunnan 등)은 부모 국가 ISO로 매핑
- Unmappable 5건: Antarctica, Central Asia, Kashmir, Tien-Shan, Turkestan → NULL 유지
- 결과: 137건 ISO 코드 채움, 5건 NULL

### Step 2: UID 컬럼 추가 + 값 생성

**파일:** `scripts/populate_uids_phase_a.py` (신규, 통합 스크립트)

각 테이블에 4개 컬럼 추가:
- `uid TEXT` (+ UNIQUE INDEX)
- `uid_method TEXT`
- `uid_confidence TEXT`
- `same_as_uid TEXT`

**countries UID 전략:**
- ISO 코드별 primary 선정: 같은 ISO를 공유하는 entries 중 이름이 가장 짧은 것이 primary
  - 예: `Germany` (primary, iso3166-1) vs `E Germany`, `N Germany` (fp_v1)
- primary: `scoda:geo:country:iso3166-1:<code>` (high)
- 나머지: `scoda:geo:country:fp_v1:sha256:<hash>` (medium/low)
- 결과: iso3166-1=56, fp_v1=86 (서브내셔널+unmappable)

**geographic_regions UID 전략:**
- country-level (60건): `pycountry`로 ISO 해석 → `scoda:geo:country:iso3166-1:<code>` 또는 fp_v1
- region-level (502건): 부모 country ISO + 정규화된 이름 → `scoda:geo:region:name:<iso>:<name>`
- ISO 없는 부모(Turkestan 등) 하위 region: fp_v1 fallback
- collision handling: 동일 UID 발생 시 `-2`, `-3` suffix 부여

**taxonomic_ranks UID 전략:**
- 기본: `scoda:taxon:<rank>:<name>` (high)
- (rank, name) 중복 30쌍: valid인 쪽이 primary, 나머지는 `scoda:taxon:<rank>:<name>:hom2` (medium)
- 중복 선정 규칙: is_valid=1 우선 → 낮은 id 우선

### Step 3: conftest.py 스키마 동기화

- PaleoCore 테이블 4개(countries, geographic_regions, ics_chronostrat, temporal_ranges): uid 4컬럼 + UNIQUE INDEX 추가
- trilobase taxonomic_ranks: uid 4컬럼 + UNIQUE INDEX 추가
- 모든 샘플 INSERT에 uid, uid_method, uid_confidence 값 포함

### Step 4: 테스트 추가

`tests/test_runtime.py`에 `TestUIDSchema` 클래스 (11개):

| 테스트 | 검증 내용 |
|--------|----------|
| `test_uid_unique_constraint_taxonomic_ranks` | UNIQUE INDEX 존재 확인 |
| `test_uid_unique_constraint_paleocore` | PaleoCore 4개 테이블 UNIQUE INDEX 확인 |
| `test_uid_format_scoda_prefix` | 모든 uid가 `scoda:` prefix로 시작 |
| `test_uid_format_taxonomic_ranks` | `scoda:taxon:<rank>:` 포맷 검증 |
| `test_uid_format_ics_chronostrat` | `scoda:strat:ics:uri:` 포맷 검증 |
| `test_uid_format_temporal_ranges` | `scoda:strat:temporal:code:` 포맷 검증 |
| `test_uid_format_countries` | `scoda:geo:country:` 포맷 검증 |
| `test_uid_format_geographic_regions` | `scoda:geo:` 포맷 검증 |
| `test_uid_no_nulls_phase_a` | 5개 테이블 uid NOT NULL 100% 검증 |
| `test_uid_confidence_values` | confidence가 high/medium/low 중 하나 |

### Step 5: create_paleocore.py 갱신

PaleoCore 테이블 CREATE SQL에 uid 4컬럼 포함 → paleocore.db 재생성 시 uid 보존.

### 추가: MCP 테스트 수정

- `test_mcp.py::test_execute_named_query`: 파라미터 필요 없는 쿼리 선택하도록 수정
- 기존: `queries[0]` (alphabetical 첫 번째 = `bibliography_detail`, 파라미터 필요)
- 수정: `params_json`이 NULL인 쿼리만 필터링 후 선택

## Confidence 분포

| confidence | 건수 | 비율 |
|-----------|------|------|
| high | 6,118 | 97.9% |
| medium | 127 | 2.0% |
| low | 5 | 0.1% |

## 테스트

```
208 passed in 157s
```

## 신규/변경 파일

| 파일 | 유형 |
|------|------|
| `scripts/populate_iso_codes.py` | 신규 |
| `scripts/populate_uids_phase_a.py` | 신규 |
| `paleocore.db` | 변경 (uid 컬럼 + 값) |
| `trilobase.db` | 변경 (uid 컬럼 + 값) |
| `scripts/create_paleocore.py` | 변경 (uid 컬럼 포함) |
| `tests/conftest.py` | 변경 (스키마 + 샘플 데이터) |
| `tests/test_runtime.py` | 변경 (TestUIDSchema 11개) |
| `tests/test_mcp.py` | 변경 (파라미터 없는 쿼리 선택) |

## 다음 단계

- **Phase B** (P43): geographic_regions 복합 UID + countries fallback 5건
- **Phase C** (P44): bibliography DOI 조회 + formations lexicon 조회
