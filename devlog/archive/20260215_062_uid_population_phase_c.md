# UID Population Phase C — Bibliography + Formations

**날짜:** 2026-02-15
**상태:** 완료

## 작업 내용

Phase A/B에서 5개 테이블에 6,250건 UID를 부여 완료한 후, 남은 2개 테이블에 UID를 부여하여 전체 7개 테이블 10,384건 100% 커버리지를 달성.

### 대상 테이블

| 테이블 | DB | 레코드 | UID 방법 |
|--------|-----|--------|----------|
| `bibliography` | trilobase.db | 2,130 | fp_v1 fingerprint |
| `formations` | paleocore.db | 2,004 | fp_v1 fingerprint |

### Bibliography fp_v1 Fingerprint

- Canonical string: `fa=<first_author_family>|y=<year[suffix]>|t=<normalized_title>|c=<journal_or_book>|v=<volume>|p=<first_page>`
- UID: `scoda:bib:fp_v1:sha256:<hash>`
- 정규화: NFKC, lowercase, 구두점 제거, soft-hyphen 제거, `&`→`and`
- cross_ref 15건: `low` confidence (음역 참조, same_as_uid 미설정)
- 나머지 2,115건: `medium` confidence
- 충돌: 0건

### Formations fp_v1 Fingerprint

- Canonical string: `n=<normalized_name>|r=<formation_type or 'unknown'>`
- UID: `scoda:strat:formation:fp_v1:sha256:<hash>`
- formation_type 있는 경우: `medium` confidence (1,370건)
- formation_type NULL인 경우: `low` confidence (634건)
- 충돌: 0건

### 선택적 API 업그레이드 (opt-in)

스크립트는 --crossref, --macrostrat 옵션으로 외부 API 조회를 통한 UID 업그레이드를 지원하나, 이번에는 fp_v1만 적용:
- `--crossref --email <email>`: CrossRef DOI 조회 → fp_v1 → doi 업그레이드
- `--macrostrat`: Macrostrat lexicon ID 조회 → fp_v1 → lexicon 업그레이드

## 변경 파일

| 파일 | 유형 | 설명 |
|------|------|------|
| `scripts/populate_uids_phase_c.py` | 신규 | 통합 스크립트 (fp_v1 + CrossRef + Macrostrat) |
| `tests/conftest.py` | 수정 | bibliography/formations uid 4컬럼 + UNIQUE INDEX + 테스트 데이터 |
| `tests/test_runtime.py` | 수정 | TestUIDPhaseC 10개 테스트 + bibliography count 수정 |
| `scripts/create_paleocore.py` | 수정 | formations CREATE TABLE에 uid 4컬럼 추가 |
| `trilobase.db` | 데이터 | bibliography uid 컬럼 + 2,130건 값 |
| `paleocore.db` | 데이터 | formations uid 컬럼 + 2,004건 값 |

## 테스트 결과

| 파일 | 테스트 수 | 상태 |
|------|---------|------|
| `tests/test_runtime.py` | 160개 | 통과 |
| `tests/test_trilobase.py` | 51개 | 통과 |
| `tests/test_mcp.py` | 7개 | 통과 |
| `tests/test_mcp_basic.py` | 1개 | 통과 |
| MCP 기본 | 3개 | 통과 |
| **합계** | **222개** | **전부 통과** |

### 신규 테스트 (TestUIDPhaseC, 10개)

1. `test_bibliography_uid_columns_exist` — uid 4컬럼 존재
2. `test_bibliography_uid_unique_index` — UNIQUE 제약
3. `test_formations_uid_columns_exist` — uid 4컬럼 존재
4. `test_formations_uid_unique_index` — UNIQUE 제약
5. `test_bibliography_uid_format` — `scoda:bib:` prefix
6. `test_formations_uid_format` — `scoda:strat:formation:` prefix
7. `test_bibliography_no_null_uids` — 100% 커버리지
8. `test_formations_no_null_uids` — 100% 커버리지
9. `test_bibliography_confidence_values` — high/medium/low만
10. `test_cross_ref_low_confidence` — cross_ref는 low

## UID Coverage (전체)

| 테이블 | 레코드 | 커버리지 | 주요 method |
|--------|--------|---------|------------|
| `ics_chronostrat` | 178 | 100% | ics_uri (high) |
| `temporal_ranges` | 28 | 100% | code (high) |
| `countries` | 142 | 100% | iso3166-1 + fp_v1 |
| `geographic_regions` | 562 | 100% | name + iso3166-1 + fp_v1 |
| `taxonomic_ranks` | 5,340 | 100% | name (high) |
| `bibliography` | 2,130 | 100% | fp_v1 (medium/low) |
| `formations` | 2,004 | 100% | fp_v1 (medium/low) |
| **총계** | **10,384** | **100%** | |

## 참조

- 계획 문서: `devlog/20260215_P44_uid_population_phase_c.md`
- Phase A: `devlog/20260215_060_uid_population_phase_a.md`
- Phase B: `devlog/20260215_061_uid_population_phase_b.md`
