# P72: 소스 텍스트 → DB 완전 재구성 파이프라인 설계

**Date:** 2026-02-28
**Status:** 계획 (Plan)

## 배경

현재 DB는 46개 Phase에 걸쳐 점진적으로 구성됨:
- `create_database.py` → `normalize_database.py` → 수십 개 fix/migration 스크립트
- 각 Phase에서 발견한 버그를 별도 스크립트로 패치
- 일부는 직접 SQL로 수정

이 과정에서 축적된 교훈을 반영하여, **두 개의 소스 텍스트에서 현재 DB를 한 번에 정확하게 재구성**할 수 있는 단일 파이프라인을 설계한다.

### 목표

1. `data/trilobite_genus_list.txt` + `data/adrain2011.txt` → `db/trilobase.db` + `db/paleocore.db` 완전 재현
2. 과거 fix 스크립트의 교훈을 파싱 단계에 통합 (후속 패치 불필요)
3. 다른 분류군 데이터(e.g. brachiopod, conodont) 추가 시 재활용 가능한 구조

---

## 현재 파이프라인의 문제점

### 1. 파싱 단계 결함

| 문제 | 원인 | 후속 fix |
|------|------|----------|
| formation/location 오분리 (350건) | 첫 `,` 기준 split → `Region, Country`가 `fm=Region, loc=Country`로 | `fix_formation_misalignment.py` |
| country_id 덮어쓰기 (3,769건) | `LIKE '%name'` 순차 UPDATE → 후속이 이전 결과 덮어씀 | `fix_country_id.py` |
| 국가명 변형 미처리 (13개) | "Czech Repubic", "Brasil", U+201D curly quote 등 | `fix_countries_quality.py` |
| temporal_code 누락 (84건) | regex가 `; CODE.` 직전 위치만 탐색 | `fill_temporal_codes.py` |
| synonym fide 파싱 불완전 | `et al.`, year suffix, `in` 구문 미처리 | `link_bibliography.py` 재매칭 |

### 2. 구조적 문제

- **단일 테이블 설계 후 분리**: `taxa` 테이블에 모든 것을 넣고 나중에 junction table 생성
- **참조 데이터 혼재**: countries, formations가 trilobase.db에 있다가 paleocore.db로 이관
- **synonyms → opinions 마이그레이션**: 별도 테이블로 만들었다가 VIEW로 전환

### 3. 교훈

| 교훈 | 적용 |
|------|------|
| Location 파싱은 **오른쪽(country)**부터 해야 한다 | 마지막 comma 뒤 = country, 나머지 = region |
| Formation/location 분리는 **suffix 기반** 판단 필요 | Fm/Lst/Sh/Gp 등 suffix 있으면 formation, 없으면 region |
| Country 매칭은 **LIKE가 아닌 exact match** | location 텍스트에서 추출 후 정규화 → exact match |
| Synonym은 처음부터 opinion model로 | synonyms 테이블 불필요, taxonomic_opinions로 직행 |
| Junction table은 파싱과 동시에 | genus_formations, genus_locations를 나중에 만들면 formation/country 데이터가 이미 변질 |

---

## 재구성 파이프라인 설계

```
┌─────────────────────────────────────────────────────┐
│ Source Texts                                        │
│  data/trilobite_genus_list.txt  (5,115 genera)      │
│  data/adrain2011.txt            (hierarchy)          │
│  data/trilobite_family_list.txt (family→genus map)   │
└──────────────┬──────────────────────────┬───────────┘
               │                          │
       ┌───────▼────────┐        ┌───────▼────────┐
       │ Step 1          │        │ Step 2          │
       │ Text Cleaning   │        │ Hierarchy Parse │
       └───────┬────────┘        └───────┬────────┘
               │                          │
       ┌───────▼────────┐                │
       │ Step 3          │                │
       │ Entry Parsing   │                │
       │ (improved)      │                │
       └───────┬────────┘                │
               │                          │
       ┌───────▼──────────────────────────▼───┐
       │ Step 4: Schema + Data Load            │
       │  taxonomic_ranks (hierarchy + genera) │
       │  taxonomic_opinions (synonyms)        │
       │  bibliography                         │
       │  taxon_bibliography                   │
       └───────┬──────────────────────────────┘
               │
       ┌───────▼────────┐
       │ Step 5          │
       │ PaleoCore 생성  │◄── vendor/cow/, vendor/ics/
       │ (reference DB)  │
       └───────┬────────┘
               │
       ┌───────▼─────────────────────┐
       │ Step 6: Junction Tables     │
       │  genus_formations           │
       │  genus_locations            │
       │  (country/region 분리 포함)  │
       └───────┬─────────────────────┘
               │
       ┌───────▼────────┐
       │ Step 7          │
       │ SCODA Metadata  │
       │ + UI Manifest   │
       └───────┬────────┘
               │
       ┌───────▼────────┐
       │ Step 8          │
       │ Validation      │
       └───────┬────────┘
               │
               ▼
        trilobase.db + paleocore.db
```

---

### Step 1: Text Cleaning

**입력**: `data/trilobite_genus_list_original.txt`
**출력**: `data/trilobite_genus_list.txt` (정제 완료)

현재 이미 완료된 정제 작업을 코드화:

```python
CLEANING_RULES = [
    # PDF line-break hyphen removal (165 patterns)
    (r'(\w)-\n(\w)', r'\1\2'),
    # Whitespace fixes (44 cases)
    (r'(?<=[a-z])in(?=[A-Z])', r' in '),     # missing space around 'in'
    (r'(?<=[a-z])et(?=[A-Z])', r' et '),      # missing space around 'et'
    # Encoding fixes
    ('BRAÃ'A', 'BRAÑA'),                       # BRAÑA encoding (13 cases)
    # Control character removal
    (r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ''),
    # Colon → semicolon (4 cases)
    (r'(?<=IDAE): (?=[LMU])', '; '),
    # Spelling corrections
    ('Grinellaspis', 'Grinnellaspis'),
    # CHU-GAEVA → CHUGAEVA
    ('CHU-GAEVA', 'CHUGAEVA'),
]
```

**재활용 포인트**: 다른 PDF 추출 텍스트에도 동일한 정제 프레임워크 적용 가능

---

### Step 2: Hierarchy Parse

**입력**: `data/adrain2011.txt` + `data/trilobite_family_list.txt`
**출력**: 계층 구조 딕셔너리

```python
hierarchy = {
    'Trilobita': {
        'rank': 'Class', 'author': 'Walch', 'year': 1771,
        'children': {
            'Eodiscida': {
                'rank': 'Order', 'author': 'Kobayashi', 'year': 1939,
                'children': {
                    'Calodiscidae': {
                        'rank': 'Family', 'author': 'Kobayashi', 'year': 1943,
                        'genera': ['Calodiscus', 'Dawsonia', ...]
                    },
                    ...
                }
            },
            ...
        }
    }
}
```

**family_list.txt 활용**: Family → genus 소속 관계 교차 검증

---

### Step 3: Entry Parsing (개선판)

**입력**: 정제된 genus_list.txt
**출력**: 구조화된 genus 레코드 리스트

현재 `create_database.py`의 `parse_entry()` 개선:

#### 3a. Formation/Location 분리 (핵심 개선)

**현재 로직 (버그)**:
```python
# 첫 comma로 분리 → "Region, Country"가 fm=Region, loc=Country
parts = loc_str.split(',', 1)
formation = parts[0]
location = parts[1]
```

**개선 로직**:
```python
def parse_formation_location(text):
    """
    Formation/Location 분리.
    규칙:
      1. Formation suffix (Fm/Lst/Sh/Gp 등) 있으면 → 첫 comma 앞 = formation
      2. Suffix 없고 comma 있으면 → 전체가 location (region, country)
      3. Suffix 없고 comma 없으면 → 국가명이면 location, 아니면 보류
    """
    FORMATION_SUFFIXES = ['Fm', 'Lst', 'Sh', 'Gp', 'Beds', 'Zone', ...]

    if ',' in text:
        first_part = text.split(',', 1)[0].strip()
        has_suffix = any(s in first_part for s in FORMATION_SUFFIXES)

        if has_suffix:
            # "Blue Fjiord Fm, Nunavut, Canada"
            # → formation="Blue Fjiord Fm", location="Nunavut, Canada"
            return first_part, text.split(',', 1)[1].strip()
        else:
            # "Zhejiang, China" → formation=None, location="Zhejiang, China"
            # "Mendoza, Argentina" → formation=None, location="Mendoza, Argentina"
            return None, text
    else:
        # "Argentina" or "Andrarum"
        if text in KNOWN_COUNTRIES:
            return None, text      # location only
        elif text in FORMATION_WHITELIST:
            return text, None      # formation only
        else:
            return text, None      # 기본: formation으로 취급 (보수적)
```

**FORMATION_WHITELIST**: suffix 없는 유효 지층명 56개 (T-5에서 확인한 목록)

#### 3b. Country 추출 (개선)

```python
def extract_country(location):
    """Location 텍스트에서 country 추출. 오른쪽부터."""
    if not location:
        return None, None

    # 정규화
    location = location.strip().strip('""\u201c\u201d').strip()
    location = COUNTRY_NORMALIZE.get(location, location)

    parts = [p.strip() for p in location.split(',')]
    country = COUNTRY_NORMALIZE.get(parts[-1], parts[-1])
    region = ', '.join(parts[:-1]) if len(parts) > 1 else None

    return country, region
```

#### 3c. Synonym 파싱 (개선)

```python
# 현재: fide author와 year를 따로 추출 → 불완전
# 개선: fide 전체를 하나의 문자열로 캡처 후 후처리
SYNONYM_PATTERNS = [
    # j.s.s. — fide를 그룹으로 캡처
    (r'\[j\.s\.s\.?\s*of\s+([^,\]]+)(?:,\s*fide\s+(.+?))?\]', 'j.s.s.'),
    # j.o.s.
    (r'\[j\.o\.s\.?\s*of\s+([^\]]+)\]', 'j.o.s.'),
    # preocc., replaced by
    (r'\[preocc\.\s*(?:\(.*?\))?,?\s*replaced\s+by\s+([^\]]+)\]', 'preocc.'),
    # replacement name for
    (r'\[replacement\s+name\s+(?:for\s+)?([^\]]+)\]', 'replacement'),
    # suppressed
    (r'\[suppressed[^\]]*\]', 'suppressed'),
]

def parse_fide(fide_text):
    """'SHERGOLD et al., 1990' → (author='SHERGOLD et al.', year='1990')"""
    match = re.match(r'(.+?),\s*(\d{4}[a-z]?)\s*$', fide_text.strip())
    if match:
        return match.group(1).strip(), match.group(2)
    return fide_text.strip(), None
```

---

### Step 4: Schema + Data Load

**DB 스키마를 처음부터 최종 형태로 생성** (마이그레이션 불필요):

```sql
-- 최종 스키마 (현재 trilobase.db 구조 그대로)
CREATE TABLE taxonomic_ranks (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    rank TEXT NOT NULL,       -- Class/Order/Suborder/Family/Genus
    parent_id INTEGER REFERENCES taxonomic_ranks(id),
    author TEXT, year INTEGER, year_suffix TEXT,
    genera_count INTEGER,
    notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Genus-specific
    type_species TEXT, type_species_author TEXT,
    formation TEXT, location TEXT, family TEXT,
    temporal_code TEXT, is_valid INTEGER DEFAULT 1,
    raw_entry TEXT
);

CREATE TABLE taxonomic_opinions (
    id INTEGER PRIMARY KEY,
    taxon_id INTEGER NOT NULL REFERENCES taxonomic_ranks(id),
    opinion_type TEXT NOT NULL,        -- SYNONYM_OF, PLACED_IN, SPELLING_OF
    related_taxon_id INTEGER REFERENCES taxonomic_ranks(id),
    proposed_valid INTEGER,
    bibliography_id INTEGER,
    assertion_status TEXT,             -- asserted/incertae_sedis/indet/questionable
    curation_confidence TEXT,
    is_accepted INTEGER DEFAULT 1,
    synonym_type TEXT,                 -- j.s.s./j.o.s./preocc./replacement/suppressed
    notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- backward-compat VIEW
CREATE VIEW synonyms AS ...;

CREATE TABLE bibliography (...);
CREATE TABLE taxon_bibliography (...);
CREATE TABLE genus_formations (...);
CREATE TABLE genus_locations (...);
```

**로드 순서**:

1. **계층 노드 삽입** (Step 2 결과): Class → Order → Suborder → Family
   - Agnostina Suborder 포함
   - genera_count 계산
2. **Genus 삽입** (Step 3 결과): parent_id = 해당 Family
   - `?FAMILY`/`??FAMILY` → 잠정 배정 + questionable opinion
   - `FAMILY UNCERTAIN` → incertae_sedis opinion
   - `INDET` → indet opinion
3. **Synonym → taxonomic_opinions 직접 생성** (synonyms 테이블 생략)
   - 중복 synonym 처리 (43 taxa): priority 기반 is_accepted
4. **Bibliography 삽입** + taxon_bibliography 연결
   - author/year 매칭 시 `et al.`, initial, diacritics 모두 처리

---

### Step 5: PaleoCore 생성

**입력**: `vendor/cow/`, `vendor/ics/`, Step 3의 formation/country 목록
**출력**: `db/paleocore.db`

**순서**:

1. **countries 테이블**: Step 3에서 추출한 고유 국가명 (COUNTRY_NORMALIZE 적용 후)
2. **CoW 매핑**: `statelist2024.csv` 파싱 → cow_states + country_cow_mapping
3. **geographic_regions**: country → region 계층 (CoW 기반 + genus_locations.region 기반)
4. **formations 테이블**: Step 3에서 추출한 고유 formation명 + formation_type 분류
5. **temporal_ranges**: 26개 코드 (하드코딩)
6. **ICS import**: `chart.ttl` 파싱 → ics_chronostrat + temporal_ics_mapping

**핵심**: PaleoCore를 trilobase 이전에 독립적으로 만들 수 있음 (분류군 데이터 무관)
→ 다른 분류군 DB에서도 동일한 paleocore.db 공유 가능

---

### Step 6: Junction Tables

**genus_formations, genus_locations를 정확하게 한 번에 생성.**

#### genus_formations

```python
for genus in genera:
    if genus.formation:
        fm_id = formations_map[genus.formation]
        INSERT genus_formations (genus_id, fm_id)
```

#### genus_locations

```python
for genus in genera:
    country, region = extract_country(genus.location)
    if country:
        country_id = countries_map[country]
        region_id = resolve_region_id(region, country_id, geographic_regions)
        INSERT genus_locations (genus_id, country_id, region, region_id)
```

**`resolve_region_id()` 로직**:
1. `geographic_regions`에서 `(name=region, parent_id=country_geo_id)` 검색
2. 있으면 → 해당 id
3. 없으면 → 신규 region 생성 후 id 반환
4. region이 NULL이면 → country-level id

**이 단계에서 country_id 오류가 발생하지 않음** (exact match, LIKE 미사용)

---

### Step 7: SCODA Metadata + UI

```python
# artifact_metadata (하드코딩)
INSERT artifact_metadata (key, value) VALUES
  ('name', 'trilobase'),
  ('version', '0.2.5'),
  ('description', 'Trilobite genus database...'),
  ...;

# provenance
INSERT provenance (...) VALUES
  ('primary_source', 'Jell & Adrain, 2002', ...),
  ('secondary_source', 'Adrain, 2011', ...),
  ...;

# schema_descriptions (112건)
# ui_display_intent (6건)
# ui_queries (37건) — 검증된 최종 SQL
# ui_manifest (1건) — 검증된 JSON
```

---

### Step 8: Validation

파이프라인 마지막에 자동 실행되는 검증 쿼리:

```python
VALIDATIONS = [
    # 구조
    ("taxonomic_ranks count", "SELECT COUNT(*) FROM taxonomic_ranks", 5341),
    ("valid genera", "SELECT COUNT(*) FROM taxonomic_ranks WHERE rank='Genus' AND is_valid=1", 4259),
    ("invalid genera", "SELECT COUNT(*) FROM taxonomic_ranks WHERE rank='Genus' AND is_valid=0", 856),
    ("parent_id NULL (valid)", "SELECT COUNT(*) FROM taxonomic_ranks WHERE rank='Genus' AND is_valid=1 AND parent_id IS NULL", 0),

    # 관계
    ("synonym linkage", "SELECT COUNT(*) FROM taxonomic_opinions WHERE opinion_type='SYNONYM_OF' AND related_taxon_id IS NOT NULL", ">=1054"),
    ("genus_formations", "SELECT COUNT(*) FROM genus_formations", ">=4500"),
    ("genus_locations", "SELECT COUNT(*) FROM genus_locations", ">=4840"),

    # 데이터 품질
    ("country_id match rate ≥95%", """
        SELECT CAST(SUM(CASE WHEN tr.location LIKE '%' || c.name THEN 1 ELSE 0 END) AS REAL) / COUNT(*)
        FROM genus_locations gl JOIN taxonomic_ranks tr ON gl.genus_id = tr.id
        JOIN pc.countries c ON gl.country_id = c.id WHERE tr.location IS NOT NULL
    """, ">=0.95"),
    ("no China→England", """
        SELECT COUNT(*) FROM genus_locations gl
        JOIN taxonomic_ranks tr ON gl.genus_id = tr.id
        JOIN pc.countries c ON gl.country_id = c.id
        WHERE tr.location LIKE '%China' AND c.name = 'England'
    """, 0),
    ("no formation=country", """
        SELECT COUNT(*) FROM taxonomic_ranks tr
        JOIN pc.countries c ON tr.formation = c.name
        WHERE tr.rank = 'Genus' AND tr.location IS NULL
    """, 0),
]
```

---

## 재활용 가능한 컴포넌트

다른 분류군 데이터 추가 시 재활용:

| 컴포넌트 | 설명 | 재활용 범위 |
|----------|------|------------|
| Text Cleaning framework | PDF 추출 텍스트 정제 규칙 | 모든 PDF 추출 데이터 |
| COUNTRY_NORMALIZE | 국가명 변형 → 정규화 맵 | 모든 고생물 데이터 |
| FORMATION_WHITELIST | suffix 없는 유효 지층명 | 삼엽충 + 유사 데이터 |
| Formation/Location 분리 | suffix 기반 판단 로직 | Jell&Adrain 형식 데이터 |
| PaleoCore DB | 지리/시간 참조 데이터 | 모든 SCODA 패키지 |
| SCODA metadata 템플릿 | artifact_metadata, provenance 등 | 모든 SCODA 패키지 |
| Validation framework | 빌드 후 자동 검증 | 모든 SCODA 패키지 |
| Bibliography matching | author/year → bibliography FK | 모든 고생물 데이터 |
| Synonym → Opinion model | 동의어를 opinion으로 처리 | 모든 분류학 데이터 |

---

## 구현 제안

### 옵션 A: 단일 스크립트 (`scripts/rebuild_database.py`)

```bash
python scripts/rebuild_database.py \
    --genus-list data/trilobite_genus_list.txt \
    --hierarchy data/adrain2011.txt \
    --family-list data/trilobite_family_list.txt \
    --cow-data vendor/cow/v2024/States2024/statelist2024.csv \
    --ics-data vendor/ics/gts2020/chart.ttl \
    --output-dir db/ \
    --validate
```

장점: 실행이 단순, 의존성 명확
단점: 파일이 커짐

### 옵션 B: 모듈화된 파이프라인

```
scripts/
  pipeline/
    __init__.py
    clean.py          # Step 1: text cleaning
    hierarchy.py      # Step 2: hierarchy parse
    parse_genera.py   # Step 3: genus entry parsing
    load_data.py      # Step 4: schema + data load
    paleocore.py      # Step 5: PaleoCore creation
    junctions.py      # Step 6: genus_formations/locations
    metadata.py       # Step 7: SCODA metadata
    validate.py       # Step 8: validation
  rebuild_database.py # 오케스트레이터
```

장점: 단계별 테스트 가능, 모듈 재활용 용이
단점: 파일 수 증가

### 추천: 옵션 B

각 단계를 독립적으로 테스트하고, 다른 분류군 추가 시 `parse_genera.py`만 교체하면 됨.
`paleocore.py`는 완전히 독립적이므로 별도 패키지로도 분리 가능.

---

## 현재 DB와의 차이

재구성 파이프라인으로 만든 DB는 현재 DB와 **동일한 최종 상태**를 가져야 한다.
차이가 발생하면 그것 자체가 버그 발견:

```bash
# 검증 방법
python scripts/rebuild_database.py --output-dir db_new/
# 비교
python scripts/compare_databases.py db/trilobase.db db_new/trilobase.db
```

비교 대상:
- taxonomic_ranks: name, rank, parent_id, author, year, formation, location, is_valid
- taxonomic_opinions: taxon_id, opinion_type, related_taxon_id, synonym_type
- genus_formations: genus_id, formation_id (건수)
- genus_locations: genus_id, country_id, region (건수)
- bibliography: 전수 비교

---

## 참고

- 현재 파이프라인 상세: `design/HISTORY.md`
- T-5 fix 내용: `devlog/20260228_098_fix_country_id_and_formation.md`
- 관련 스크립트: `create_database.py`, `normalize_database.py`, `fix_country_id.py`, `fix_formation_misalignment.py`
