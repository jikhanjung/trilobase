# P44: UID Population Phase C — 외부 조회 기반 UID 생성

**날짜:** 2026-02-15
**상태:** 계획
**선행 조건:** Phase A (P42), Phase B (P43) 완료

## 목표

SCODA Stable UID Schema v0.2 Section 11.5의 Phase C를 구현한다.
외부 API 조회가 필요하거나, 복합 fingerprint로 생성해야 하는 UID가 대상이다.

## 배경

### Phase A/B 완료 후 상태 (전제)

| 테이블 | uid 커버리지 | DB |
|--------|------------|-----|
| `ics_chronostrat` | 178/178 (100%) | paleocore.db |
| `temporal_ranges` | 28/28 (100%) | paleocore.db |
| `countries` | 142/142 (100%) | paleocore.db |
| `geographic_regions` | 562/562 (100%) | paleocore.db |
| `taxonomic_ranks` | 5,340/5,340 (100%) | trilobase.db |
| **`bibliography`** | **0/2,130 (0%)** | **trilobase.db** |
| **`formations`** | **0/2,004 (0%)** | **paleocore.db** |

### Phase C 대상

| 테이블 | 레코드 | 1차 UID 방법 | Fallback | DB |
|--------|--------|-------------|----------|-----|
| `bibliography` | 2,130 | DOI (CrossRef API) | fp_v1 (fingerprint) | trilobase.db |
| `formations` | 2,004 | Lexicon ID (USGS/BGS) | fp_v1 (fingerprint) | paleocore.db |

## Part 1: Bibliography UID

### 1.1 현재 데이터 현황

| 항목 | 값 |
|------|-----|
| 총 레코드 | 2,130 |
| reference_type: article | 1,902 (89.3%) |
| reference_type: book | 161 (7.6%) |
| reference_type: chapter | 52 (2.4%) |
| reference_type: cross_ref | 15 (0.7%) |
| journal 있음 | 1,604 (75.3%) |
| volume 있음 | 1,604 (75.3%) |
| pages 있음 | 1,740 (81.7%) |
| 연도 범위 | 1745–2003 |

uid 컬럼: **미존재** (스키마 마이그레이션 필요)

### 1.2 UID 전략

**우선순위:**
1. DOI — 외부 API (CrossRef)로 조회
2. fp_v1 — 서지 fingerprint (DOI 없는 항목)

### 1.3 Step 1: 스키마 마이그레이션

```sql
ALTER TABLE bibliography ADD COLUMN uid TEXT;
ALTER TABLE bibliography ADD COLUMN uid_method TEXT;
ALTER TABLE bibliography ADD COLUMN uid_confidence TEXT DEFAULT 'medium';
ALTER TABLE bibliography ADD COLUMN same_as_uid TEXT;
CREATE UNIQUE INDEX idx_bibliography_uid ON bibliography(uid);
```

### 1.4 Step 2: DOI 조회 (CrossRef API)

**파일:** `scripts/populate_uids_bib_doi.py` (신규)

CrossRef API (`https://api.crossref.org/works`)를 사용하여 DOI를 조회한다.

**조회 전략:**

```
# 쿼리 조합 (우선순위순)
1. author + title + year (가장 정확)
2. title + year (author 파싱 어려운 경우)
3. title only (fallback)
```

**API 호출:**
```python
import requests, time

def search_crossref(authors, title, year, email="user@example.com"):
    """CrossRef API로 DOI 검색."""
    params = {
        'query.bibliographic': f'{authors} {title}',
        'filter': f'from-pub-date:{year},until-pub-date:{year}',
        'rows': 3,
        'mailto': email  # polite pool (faster rate limit)
    }
    headers = {'User-Agent': f'ScodaTrilobase/1.0 (mailto:{email})'}
    resp = requests.get('https://api.crossref.org/works',
                        params=params, headers=headers, timeout=30)
    if resp.status_code == 200:
        return resp.json()['message']['items']
    return []
```

**매칭 검증:**
- title 유사도 ≥ 0.85 (normalized Levenshtein 또는 token overlap)
- year 정확 일치
- author family name 첫 저자 일치 (보조 확인)

**DOI 발견 시:**
```
uid = scoda:bib:doi:<normalized_doi>
uid_method = doi
uid_confidence = high
```

**예상 DOI 커버리지:**

Jell & Adrain (2002)의 참고문헌은 1745–2003년 고생물학 문헌이다.
- 2000년 이후: DOI 보급률 높음 (~80–90%)
- 1990년대: 중간 (~40–60%, 소급 등록 포함)
- 1980년대 이전: 낮음 (~10–30%)
- **전체 예상: 약 30–50% (600–1,000건)**

**Rate Limiting:**
- CrossRef polite pool: ~50 req/s (mailto 포함 시)
- 안전하게 1 req/s 제한 → 2,130건 ≈ 35분
- `--batch-size`, `--delay` 옵션으로 조절 가능
- 중간 저장: 진행 상황 JSON 파일로 저장, 중단 후 재개 가능

### 1.5 Step 3: Bibliographic Fingerprint (fp_v1)

**파일:** `scripts/populate_uids_bib_fp.py` (신규, 또는 DOI 스크립트에 통합)

DOI를 찾지 못한 항목에 fingerprint UID를 부여한다.

**Canonical string:**
```
fa=<first_author_family>|y=<year>|t=<normalized_title>|c=<normalized_journal>|v=<volume>|p=<first_page>
```

**정규화 규칙:**

| 필드 | 규칙 |
|------|------|
| `fa` (first author) | family name only, lowercase |
| `y` (year) | 4자리 숫자, year_suffix 포함 시 `1998a` |
| `t` (title) | lowercase, remove punctuation `.,:;()'"`, hyphen/slash → space, `&` → `and`, collapse whitespace |
| `c` (container) | journal 또는 book_title, 같은 규칙 |
| `v` (volume) | 그대로 (없으면 생략) |
| `p` (first page) | 시작 페이지만 (`132-138` → `132`, 없으면 생략) |

**First author 추출:**

현재 `authors` 필드 패턴:
```
ACENOLAZA, F.G.                    → acenolaza
ACENOLAZA, F.G. & RABANO, I.       → acenolaza
ABDULLAEV, R.N. & KHALETSKAYA, O.N. → abdullaev
```

추출 로직:
```python
def extract_first_author_family(authors):
    """authors 문자열에서 첫 저자 family name 추출."""
    # '&' 또는 ',' 이전까지가 첫 저자
    # 패턴: FAMILY, INITIALS & ...
    first = authors.split('&')[0].split(',')[0].strip().lower()
    return first
```

**Fingerprint UID:**
```
uid = scoda:bib:fp_v1:sha256:<hash>
uid_method = fp_v1
uid_confidence = medium
```

**cross_ref 타입 (15건):**

`cross_ref`는 "see AUTHOR, YEAR" 형태의 교차 참조이며 독립 문헌이 아님.
- 참조 대상 문헌에 `same_as_uid` 연결
- 자체 uid도 부여 (canonical string에 `t=see <target>` 등)

### 1.6 Step 4: 충돌 처리

동일 canonical string이 여러 레코드에서 발생하면:
```
scoda:bib:fp_v1:sha256:<hash>       ← 첫 번째
scoda:bib:fp_v1:sha256:<hash>-c2    ← 두 번째
scoda:bib:fp_v1:sha256:<hash>-c3    ← 세 번째
```

실제 충돌 가능성은 낮으나 (같은 저자+연도+제목 → 보통 같은 문헌), year_suffix (`a`, `b`)로 인한 edge case 대비.

### 1.7 예상 결과

| uid_method | 예상 건수 | uid_confidence |
|-----------|----------|---------------|
| `doi` | ~600–1,000 | `high` |
| `fp_v1` | ~1,100–1,500 | `medium` |
| **합계** | **2,130** | **100% 커버리지** |

---

## Part 2: Formation UID

### 2.1 현재 데이터 현황

| 항목 | 값 |
|------|-----|
| 총 레코드 | 2,004 |
| `formation_type` 있음 | 1,370 (68.4%) |
| `country` 있음 | **0 (0%)** |
| `region` 있음 | **0 (0%)** |
| `period` 있음 | **0 (0%)** |
| `normalized_name` 있음 | 조사 필요 |

**formation_type 분포:**

| type | 건수 |
|------|------|
| Formation | 902 |
| NULL | 634 |
| Limestone | 179 |
| Zone | 83 |
| Horizon | 78 |
| Shale | 77 |
| Beds | 42 |
| Group | 8 |
| Suite | 1 |

**문제 데이터:**

| 패턴 | 예시 | 건수 (추정) |
|------|------|-----------|
| `?` prefix | `?Amouslek Fm`, `???Taishan Fm` | ~10 |
| 괄호 이름 | `(Gattendorfia-Stufe)` | ~5 |
| 숫자만 | `10` | ~3 |

uid 컬럼: **미존재** (스키마 마이그레이션 필요)

### 2.2 UID 전략

**우선순위:**
1. Lexicon ID — 외부 데이터베이스(USGS, BGS, Macrostrat 등) 조회
2. fp_v1 — Formation fingerprint

### 2.3 Step 1: 스키마 마이그레이션

```sql
ALTER TABLE formations ADD COLUMN uid TEXT;
ALTER TABLE formations ADD COLUMN uid_method TEXT;
ALTER TABLE formations ADD COLUMN uid_confidence TEXT DEFAULT 'medium';
ALTER TABLE formations ADD COLUMN same_as_uid TEXT;
CREATE UNIQUE INDEX idx_formations_uid ON formations(uid);
```

### 2.4 Step 2: 메타데이터 보강 (선행 작업)

현재 `country`, `region`, `period` 컬럼이 모두 NULL이다.
fingerprint 품질을 높이려면 이 메타데이터를 먼저 채워야 한다.

**방법: `genus_formations` + `genus_locations` JOIN으로 역추론**

```sql
-- Formation이 연결된 genera의 country/temporal_code를 집계
SELECT f.id, f.name,
       GROUP_CONCAT(DISTINCT c.name) AS inferred_countries,
       GROUP_CONCAT(DISTINCT tr.name) AS inferred_periods
FROM pc.formations f
JOIN genus_formations gf ON gf.formation_id = f.id
JOIN taxonomic_ranks g ON gf.genus_id = g.id
LEFT JOIN genus_locations gl ON gl.genus_id = g.id
LEFT JOIN pc.countries c ON gl.country_id = c.id
WHERE g.temporal_code IS NOT NULL
GROUP BY f.id;
```

주의: 이는 근사값이며 정확한 메타데이터가 아님. fingerprint에는 사용하되 `uid_confidence`를 `low`로 설정.

**대안: 메타데이터 보강 없이 진행**

`name` + `formation_type`만으로 fingerprint 생성. 동명이형(homonym) formation이 있을 수 있으나, 현재 DB에서 실제 충돌 빈도를 먼저 측정하여 판단.

### 2.5 Step 3: Lexicon ID 조회 (선택적)

**Macrostrat API** (`https://macrostrat.org/api/`)를 우선 활용:

```python
def search_macrostrat(formation_name):
    """Macrostrat API로 formation 조회."""
    resp = requests.get(
        'https://macrostrat.org/api/v2/defs/strat_names',
        params={'strat_name_like': formation_name},
        timeout=30
    )
    if resp.status_code == 200:
        results = resp.json()['success']['data']
        return results
    return []
```

**매칭 기준:**
- 이름 유사도 ≥ 0.90
- rank 일치 (Formation, Group, Member 등)
- 지역 교차 검증 (역추론된 country와 Macrostrat 위치 비교)

**Lexicon UID:**
```
uid = scoda:strat:formation:lexicon:macrostrat:<strat_name_id>
uid_method = lexicon
uid_confidence = high
```

**커버리지 예상:**
- Macrostrat은 북미 중심 → 북미 formation은 높은 매칭률
- 기타 지역(유럽, 아시아, 아프리카) → 대부분 매칭 불가
- **전체 예상: ~15–30% (300–600건)**

**Rate Limiting:**
- Macrostrat: 제한 느슨함, ~5 req/s 안전
- 2,004건 × 0.2s ≈ 7분

### 2.6 Step 4: Formation Fingerprint (fp_v1)

**파일:** `scripts/populate_uids_formation.py` (신규)

Lexicon ID가 없는 항목에 fingerprint UID를 부여한다.

**Canonical string (metadata 있는 경우):**
```
n=<normalized_name>|r=<formation_type>|geo=<country_region>|age=<period>
```

**Canonical string (metadata 없는 경우 — 대다수):**
```
n=<normalized_name>|r=<formation_type>
```

**Name 정규화:**
- Lowercase
- Remove suffixes: "Formation", "Fm.", "Fm", "Limestone", "Ls.", "Shale", "Sh.", "Group", "Gp.", "Beds", "Member", "Mb."
- Remove `?` prefix
- Remove parentheses and their content
- Collapse whitespace
- NFKC normalization

예시:
```
"?Amouslek Fm" → "amouslek"
"???Taishan Fm" → "taishan"
"(Gattendorfia-Stufe)" → "gattendorfia-stufe"
"Abbey Sh" → "abbey"
```

**Fingerprint UID:**
```
uid = scoda:strat:formation:fp_v1:sha256:<hash>
uid_method = fp_v1
uid_confidence = medium  (메타데이터 있으면)
uid_confidence = low     (name + type만으로 생성 시)
```

### 2.7 Step 5: 동명이형(homonym) 처리

Formation 이름은 전세계적으로 고유하지 않다. 같은 이름이 다른 국가/시대에 존재할 수 있음.

**충돌 탐지:**
```sql
SELECT normalized_name, COUNT(*) as cnt
FROM formations
GROUP BY normalized_name
HAVING cnt > 1;
```

**처리:**
- 메타데이터(country, period)가 다르면 canonical string이 달라져 자동 분리
- 메타데이터가 없고 이름만 같으면 collision counter 적용 (`-c2`)
- 수동 검토 목록 생성 후 `--report` 출력

### 2.8 예상 결과

| uid_method | 예상 건수 | uid_confidence |
|-----------|----------|---------------|
| `lexicon` | ~300–600 | `high` |
| `fp_v1` (metadata 있음) | ~200–400 | `medium` |
| `fp_v1` (name+type만) | ~1,000–1,500 | `low` |
| **합계** | **2,004** | **100% 커버리지** |

---

## 전체 작업 순서

### Bibliography (권장 우선)

| Step | 작업 | 파일 |
|------|------|------|
| B-C1 | 스키마 마이그레이션 (uid 컬럼 추가) | `populate_uids_phase_c.py` |
| B-C2 | CrossRef API로 DOI 조회 + 매칭 | `populate_uids_bib_doi.py` |
| B-C3 | DOI 없는 항목에 fp_v1 fingerprint | `populate_uids_bib_fp.py` |
| B-C4 | cross_ref 타입 same_as_uid 연결 | (Step 3에 포함) |
| B-C5 | 충돌 검사 + 리포트 | (Step 3에 포함) |

### Formation (Bibliography 이후)

| Step | 작업 | 파일 |
|------|------|------|
| F-C1 | 스키마 마이그레이션 (uid 컬럼 추가) | `populate_uids_phase_c.py` |
| F-C2 | 메타데이터 역추론 (선택적) | `populate_formation_metadata.py` |
| F-C3 | Macrostrat API로 Lexicon ID 조회 | `populate_uids_formation.py` |
| F-C4 | Lexicon 없는 항목에 fp_v1 fingerprint | (Step 3에 포함) |
| F-C5 | 동명이형 충돌 검사 + 리포트 | (Step 3에 포함) |

## 변경 파일

| 파일 | 변경 유형 |
|------|-----------|
| `scripts/populate_uids_phase_c.py` | 신규 — 스키마 마이그레이션 |
| `scripts/populate_uids_bib_doi.py` | 신규 — CrossRef DOI 조회 |
| `scripts/populate_uids_bib_fp.py` | 신규 — Bibliography fingerprint |
| `scripts/populate_uids_formation.py` | 신규 — Formation lexicon + fingerprint |
| `scripts/populate_formation_metadata.py` | 신규 (선택적) — 메타데이터 역추론 |
| `trilobase.db` | bibliography uid 컬럼 추가 + 값 |
| `paleocore.db` | formations uid 컬럼 추가 + 값 |
| `tests/conftest.py` | 스키마 + 테스트 데이터 uid 추가 |
| `tests/test_runtime.py` | Phase C 테스트 추가 |
| `scripts/create_paleocore.py` | formations uid 컬럼 포함 |
| `requirements.txt` | `requests` 추가 (CrossRef/Macrostrat 호출) |

## 검증

1. `python scripts/populate_uids_bib_doi.py --dry-run --limit 20` → DOI 샘플 확인
2. `python scripts/populate_uids_bib_doi.py` → 실제 적용 (약 35분)
3. `python scripts/populate_uids_bib_fp.py --dry-run` → fingerprint 미리보기
4. `python scripts/populate_uids_formation.py --report` → 매칭 리포트
5. SQL 검증:
   ```sql
   -- Bibliography 커버리지
   SELECT uid_method, COUNT(*), uid_confidence
   FROM bibliography
   GROUP BY uid_method, uid_confidence;

   -- Formation 커버리지
   SELECT uid_method, COUNT(*), uid_confidence
   FROM pc.formations
   GROUP BY uid_method, uid_confidence;

   -- UNIQUE 위반 없음
   SELECT uid, COUNT(*) FROM bibliography GROUP BY uid HAVING COUNT(*) > 1;
   SELECT uid, COUNT(*) FROM pc.formations GROUP BY uid HAVING COUNT(*) > 1;
   ```
6. `pytest tests/` → 전체 통과

## 위험 요소 및 대응

| 위험 | 영향 | 대응 |
|------|------|------|
| CrossRef API 다운/제한 | DOI 조회 불가 | 재시도 로직 + 중간 저장 |
| DOI 매칭 오류 (false positive) | 잘못된 UID | title 유사도 임계값 보수적 설정 (0.85) |
| Macrostrat 커버리지 부족 | lexicon UID 비율 낮음 | fp_v1 fallback으로 100% 보장 |
| Formation 동명이형 | 같은 이름 다른 formation | collision counter + 수동 리포트 |
| 1745년대 문헌 DOI 없음 | fp_v1 비율 높아짐 | 정상 — confidence=medium으로 표기 |

## 예상 최종 UID 커버리지 (Phase A+B+C)

| 테이블 | 레코드 | 커버리지 | 주요 method |
|--------|--------|---------|------------|
| `ics_chronostrat` | 178 | 100% | ics_uri (high) |
| `temporal_ranges` | 28 | 100% | code (high) |
| `countries` | 142 | 100% | iso3166-1 (137, high) + fp_v1 (5, medium) |
| `geographic_regions` | 562 | 100% | name (high) + fp_v1 (4, medium) |
| `taxonomic_ranks` | 5,340 | 100% | name (high) |
| `bibliography` | 2,130 | 100% | doi (~40%, high) + fp_v1 (~60%, medium) |
| `formations` | 2,004 | 100% | lexicon (~20%, high) + fp_v1 (~80%, medium/low) |
| **총계** | **10,384** | **100%** | |

## 참고

- v0.2 스키마 문서: `docs/SCODA_Stable_UID_Schema_v0.2.md`
- Phase A 계획: `devlog/20260215_P42_uid_population_phase_a.md`
- Phase B 계획: `devlog/20260215_P43_uid_population_phase_b.md`
- CrossRef API 문서: https://api.crossref.org/swagger-ui/index.html
- Macrostrat API 문서: https://macrostrat.org/api/
