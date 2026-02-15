# P42: UID Population Phase A — 확정적 UID 생성

**날짜:** 2026-02-15
**상태:** 계획

## 목표

SCODA Stable UID Schema v0.2 문서의 Section 11.5에 정의된 Phase A를 구현한다.
외부 조회 없이 DB 내 기존 데이터만으로 100% 생성 가능한 "확정적 UID"를 대상으로 한다.

## 배경

### 현재 상태
- 모든 테이블에 uid 관련 컬럼 없음
- `countries.code` (ISO 3166-1 alpha-2) 컬럼이 100% NULL
- COW 약어는 3글자(USA, CHN, GMY)이고 ISO alpha-2와 형식 다름
- `taxonomic_ranks`에 30개 (rank, name) 중복 쌍 존재
- 테스트 스키마가 `conftest.py`에 하드코딩

### Phase A 대상 테이블

| 테이블 | 레코드 | UID 패턴 | 소스 | DB |
|--------|--------|----------|------|----|
| `ics_chronostrat` | 178 | `scoda:strat:ics:uri:<ics_uri>` | `ics_uri` | paleocore.db |
| `temporal_ranges` | 28 | `scoda:strat:temporal:code:<code>` | `code` | paleocore.db |
| `countries` | 142 | `scoda:geo:country:iso3166-1:<code>` / fp | ISO code | paleocore.db |
| `geographic_regions` | 562 | `scoda:geo:region:name:<iso>:<name>` | country ISO + name | paleocore.db |
| `taxonomic_ranks` | 5,340 | `scoda:taxon:<rank>:<name>` | rank + name | trilobase.db |

## 작업 순서

### Step 1: countries.code에 ISO 3166-1 alpha-2 코드 채우기

**파일:** `scripts/populate_iso_codes.py` (신규)

- `pycountry` 라이브러리로 국가명 → ISO alpha-2 자동 매칭
- 자동 매칭 실패분은 수동 매핑 딕셔너리로 보정
- 5개 unmappable (Antarctica, Central Asia, Kashmir, Tien-Shan, Turkestan)은 NULL 유지
- `paleocore.db`의 `countries.code` UPDATE
- `--dry-run`, `--report` 옵션

### Step 2: UID 컬럼 추가 + 값 생성

**파일:** `scripts/populate_uids_phase_a.py` (신규, 통합 스크립트)

**2a. 컬럼 추가 (ALTER TABLE):**
```sql
-- 각 테이블에 4개 컬럼 추가
ALTER TABLE <table> ADD COLUMN uid TEXT;
ALTER TABLE <table> ADD COLUMN uid_method TEXT;
ALTER TABLE <table> ADD COLUMN uid_confidence TEXT DEFAULT 'medium';
ALTER TABLE <table> ADD COLUMN same_as_uid TEXT;
CREATE UNIQUE INDEX idx_<table>_uid ON <table>(uid);
```

대상:
- paleocore.db: countries, geographic_regions, ics_chronostrat, temporal_ranges
- trilobase.db: taxonomic_ranks

**2b. UID 값 생성 (순서대로):**

1. `ics_chronostrat` → `scoda:strat:ics:uri:{ics_uri}`, method=ics_uri, confidence=high
2. `temporal_ranges` → `scoda:strat:temporal:code:{code}`, method=code, confidence=high
3. `countries` → ISO면 `scoda:geo:country:iso3166-1:{code}`, 아니면 fp_v1, confidence=high/medium
4. `geographic_regions` → `scoda:geo:region:name:{iso}:{name}`, confidence=high
5. `taxonomic_ranks` → `scoda:taxon:{rank}:{name}`, confidence=high

### Step 3: 중복 taxonomic_ranks 조사 및 처리

30개 (rank, name) 중복 쌍 조사:
- 대부분 preoccupied name + replacement name (둘 다 valid genus 아님)
- 스크립트에서 첫 번째(id 작은 쪽)에 UID 부여, 두 번째는 same_as_uid로 연결
- 또는 조사 결과에 따라 데이터 정리

### Step 4: conftest.py 스키마 동기화

- PaleoCore 테스트 테이블 스키마에 uid 4개 컬럼 추가
- trilobase taxonomic_ranks 스키마에 uid 4개 컬럼 추가
- 샘플 테스트 데이터에 uid 값 삽입

### Step 5: 테스트 추가

`tests/test_runtime.py`에 UID 테스트 클래스:
- uid 컬럼 존재 확인
- uid UNIQUE 제약 검증
- uid 포맷 검증 (`scoda:` prefix)
- Phase A 커버리지 (uid NOT NULL 비율)

### Step 6: create_paleocore.py 갱신

uid 컬럼이 포함되도록 PaleoCore 추출 스크립트 업데이트.

## 변경 파일

| 파일 | 변경 유형 |
|------|-----------|
| `scripts/populate_iso_codes.py` | 신규 |
| `scripts/populate_uids_phase_a.py` | 신규 |
| `paleocore.db` | countries.code + 4테이블 uid 컬럼 |
| `trilobase.db` | taxonomic_ranks uid 컬럼 |
| `tests/conftest.py` | 스키마 + 테스트 데이터 uid 추가 |
| `tests/test_runtime.py` | UID 테스트 추가 |
| `scripts/create_paleocore.py` | uid 컬럼 포함 |

## 검증

1. `python scripts/populate_iso_codes.py --report` → ISO 매핑률
2. `python scripts/populate_uids_phase_a.py --dry-run` → 미리보기
3. `python scripts/populate_uids_phase_a.py` → 실제 적용
4. SQL: `SELECT COUNT(*) FROM <table> WHERE uid IS NOT NULL` → 각 테이블 전수
5. `pytest tests/` → 전체 통과

## 참고

- v0.2 스키마 문서: `docs/SCODA_Stable_UID_Schema_v0.2.md`
- PaleoCore 스키마: `docs/paleocore_schema.md`
