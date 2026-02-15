# P43: UID Population Phase B — 복합 UID 생성

**날짜:** 2026-02-15
**상태:** 계획
**선행 조건:** Phase A 완료 (P42)

## 목표

SCODA Stable UID Schema v0.2 Section 11.5의 Phase B를 구현한다.
Phase A에서 생성된 UID를 조합하여 만드는 "복합 UID"가 대상이다.

## 배경

### Phase A 완료 후 상태 (전제)

| 테이블 | uid 컬럼 | uid 값 채워짐 | DB |
|--------|---------|-------------|-----|
| `ics_chronostrat` | O | O (178건) | paleocore.db |
| `temporal_ranges` | O | O (28건) | paleocore.db |
| `countries` | O | O (137건 ISO) | paleocore.db |
| `geographic_regions` | O | **X (미채움)** | paleocore.db |
| `taxonomic_ranks` | O | O (5,340건) | trilobase.db |

### Phase B 대상

| 테이블 | 레코드 | UID 패턴 | DB |
|--------|--------|----------|-----|
| `geographic_regions` | 562 | `scoda:geo:region:name:<iso>:<name>` | paleocore.db |
| `countries` (fallback 5건) | 5 | `scoda:geo:country:fp_v1:sha256:<hash>` | paleocore.db |

### 현재 데이터 현황

**geographic_regions (562건):**

| level | 개수 | 설명 |
|-------|------|------|
| `country` | 60 | 상위 국가 노드 (parent_id = NULL) |
| `region` | 502 | 하위 지역 (parent_id → countries.id) |

**ISO 코드 없는 countries 5건:**

| id | name | 하위 region 수 | 성격 |
|----|------|---------------|------|
| 19 | Turkestan | 4 | 역사적 지역명 |
| 61 | Antarctica | 0 | 대륙 |
| 141 | Kashmir | 0 | 분쟁 지역 |
| 144 | Central Asia | 0 | 매크로 지역 |
| 146 | Tien-Shan | 0 | 산맥 |

**Turkestan 하위 4개 region:**
- Eastern Iran, SE Iran, Alborz Mtns, Alborz Mts

## 작업 순서

### Step 1: countries fallback 5건 — fp_v1 UID 생성

**파일:** `scripts/populate_uids_phase_b.py` (신규)

ISO 코드가 없는 5개 "country"에 이름 기반 fingerprint UID를 부여한다.

```python
# Canonical string: name=<normalized_country_name>
# Normalization: lowercase, NFKC, collapse whitespace, remove parenthetical qualifiers
# UID: scoda:geo:country:fp_v1:sha256:<hash>

import hashlib, unicodedata

def uid_country_fp(name):
    normalized = unicodedata.normalize('NFKC', name.strip().lower())
    normalized = ' '.join(normalized.split())  # collapse whitespace
    h = hashlib.sha256(f"name={normalized}".encode('utf-8')).hexdigest()
    return f"scoda:geo:country:fp_v1:sha256:{h}"
```

결과:

| name | uid_method | uid_confidence |
|------|-----------|---------------|
| Turkestan | `fp_v1` | `medium` |
| Antarctica | `fp_v1` | `medium` |
| Kashmir | `fp_v1` | `medium` |
| Central Asia | `fp_v1` | `medium` |
| Tien-Shan | `fp_v1` | `medium` |

### Step 2: geographic_regions — 복합 UID 생성

두 가지 케이스로 분리:

**Case A — level='region' (502건): 부모 country ISO + region name**

```
scoda:geo:region:name:<country_iso>:<normalized_name>
```

- `<country_iso>`: 부모 country의 ISO 코드 (대문자)
- `<normalized_name>`: lowercase, NFKC, space → hyphen, remove punctuation except hyphens

예시:
```
Nevada (parent: United States, US) → scoda:geo:region:name:US:nevada
Yunnan (parent: China, CN) → scoda:geo:region:name:CN:yunnan
```

uid_method = `name`, uid_confidence = `high`

**Case B — level='country' (60건): countries 테이블의 UID 복사**

country-level geographic_regions는 countries 테이블과 1:1 대응한다.
countries 테이블에서 이미 생성된 UID를 `same_as_uid`로 연결한다.

```
geographic_regions[name='Australia'].uid = scoda:geo:region:country:<iso>
geographic_regions[name='Australia'].same_as_uid = scoda:geo:country:iso3166-1:AU
```

**방안 비교:**

| 방안 | 설명 | 장점 | 단점 |
|------|------|------|------|
| A: 독립 UID | country-level region에 별도 `scoda:geo:region:country:<iso>` UID | 모든 row에 UID | UID 중복 의미 (같은 entity, 다른 UID) |
| B: same_as_uid만 | uid=NULL, same_as_uid → countries.uid | 중복 없음 | uid NOT NULL 비율 감소, 쿼리 복잡 |
| C: countries.uid 그대로 복사 | uid = countries.uid 동일 | 단순, 검색 용이 | 두 테이블에 동일 UID (의도적) |

**추천: 방안 A** — entity type이 다르므로 (`country` vs `region`) 독립 namespace가 적절.

```
uid = scoda:geo:region:country:<iso>
same_as_uid = scoda:geo:country:iso3166-1:<iso>
uid_method = name
uid_confidence = high
```

**Case C — Turkestan 하위 4건: 부모에 ISO 없음**

부모 country에 ISO 코드가 없으므로 fingerprint fallback:

```
# Canonical string: country=<normalized_country_name>|name=<normalized_region_name>
# UID: scoda:geo:region:fp_v1:sha256:<hash>
```

예시:
```
Eastern Iran (parent: Turkestan) →
  canonical: "country=turkestan|name=eastern iran"
  uid: scoda:geo:region:fp_v1:sha256:<hash>
  uid_method: fp_v1, uid_confidence: medium
```

### Step 3: Alborz 중복 처리

Turkestan 하위에 `Alborz Mtns` (id=482)와 `Alborz Mts` (id=483)가 존재.
같은 지역의 표기 차이로 보임.

**선택지:**
1. 둘 다 독립 UID 부여 (canonical string이 다르므로 다른 hash)
2. 하나를 primary로, 다른 하나에 same_as_uid 연결
3. 데이터 병합 (레코드 통합)

**추천: 선택지 2** — `Alborz Mtns`를 primary, `Alborz Mts`에 `same_as_uid` 연결.
genus_locations 참조를 확인하여 실제 사용 여부 검증 필요.

### Step 4: conftest.py 스키마 동기화

Phase A에서 이미 uid 컬럼이 추가된 상태라면, Phase B에서 추가 스키마 변경은 불필요.
테스트 데이터에 geographic_regions의 uid 샘플 값만 추가.

### Step 5: 테스트 추가

`tests/test_runtime.py`에 Phase B 테스트:
- geographic_regions uid NOT NULL 비율 검증
- geographic_regions uid 포맷 검증 (region: `scoda:geo:region:name:` 또는 `scoda:geo:region:fp_v1:`)
- countries fallback uid 포맷 검증 (`scoda:geo:country:fp_v1:sha256:`)
- countries uid 100% 커버리지 (Phase A ISO + Phase B fp = 142/142)
- same_as_uid 참조 유효성 (country-level regions → countries.uid)

## 변경 파일

| 파일 | 변경 유형 |
|------|-----------|
| `scripts/populate_uids_phase_b.py` | 신규 |
| `paleocore.db` | countries 5건 uid + geographic_regions 562건 uid |
| `tests/conftest.py` | 테스트 데이터 uid 추가 |
| `tests/test_runtime.py` | Phase B 테스트 추가 |

## 검증

1. `python scripts/populate_uids_phase_b.py --dry-run` → 미리보기
2. `python scripts/populate_uids_phase_b.py` → 실제 적용
3. SQL 검증:
   ```sql
   -- countries 100% 커버리지
   SELECT COUNT(*) FROM countries WHERE uid IS NOT NULL;  -- 142

   -- geographic_regions 커버리지
   SELECT COUNT(*) FROM geographic_regions WHERE uid IS NOT NULL;  -- 562

   -- UNIQUE 위반 없음
   SELECT uid, COUNT(*) FROM geographic_regions GROUP BY uid HAVING COUNT(*) > 1;  -- 0건
   ```
4. `pytest tests/` → 전체 통과

## 예상 결과

| 테이블 | 총 레코드 | uid NOT NULL | 커버리지 |
|--------|----------|-------------|---------|
| `countries` | 142 | 142 | **100%** |
| `geographic_regions` | 562 | 562 | **100%** |

## 참고

- v0.2 스키마 문서: `docs/SCODA_Stable_UID_Schema_v0.2.md`
- Phase A 계획: `devlog/20260215_P42_uid_population_phase_a.md`
