# P23. Geographic Regions 계층 구조 도입

**날짜**: 2026-02-12
**상태**: 계획

## 배경

현재 `countries` 테이블(142건)에는 주권국가와 하위 지역이 뒤섞여 있다:

| 유형 | 건수 | 예시 |
|------|------|------|
| 주권국가 (exact COW match) | 50 | China, Russia, USA, France |
| 하위 지역 (manual/prefix COW) | 87 | England→UK, Alaska→USA, Yakutia→Russia, Sichuan→China |
| 매핑불가 (unmappable) | 5 | Antarctica, Turkestan, Kashmir, Central Asia, Tien-Shan |

또한 `genus_locations.region` 텍스트 필드에 440개 고유 지역명이 있지만,
이들은 정규화되지 않은 평문이라 클릭/검색이 불가능하다.

**목표**: 단일 계층형 `geographic_regions` 테이블을 만들어:
1. Country와 Region을 명확히 분리
2. 둘 다 클릭 가능한 링크로 제공
3. 향후 Continent / Paleo-continent 확장 가능

## 새 테이블 설계

### `geographic_regions` (자기 참조 계층)

```sql
CREATE TABLE geographic_regions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    level TEXT NOT NULL,       -- 'continent', 'country', 'region'
    parent_id INTEGER,         -- FK → geographic_regions.id (NULL = 최상위)
    cow_ccode INTEGER,         -- COW 코드 (country level만 해당)
    taxa_count INTEGER DEFAULT 0,
    FOREIGN KEY (parent_id) REFERENCES geographic_regions(id)
);
CREATE INDEX idx_geo_regions_parent ON geographic_regions(parent_id);
CREATE INDEX idx_geo_regions_level ON geographic_regions(level);
CREATE UNIQUE INDEX idx_geo_regions_name_parent ON geographic_regions(name, parent_id);
```

### 계층 예시

```
China (level='country', cow_ccode=710)
├── Guizhou (level='region', parent_id=China)
├── Liaoning (level='region', parent_id=China)
├── Shandong (level='region', parent_id=China)
└── Sichuan (level='region', parent_id=China)    ← 현재 countries 테이블에도 있음

United Kingdom (level='country', cow_ccode=200)
├── England (level='region', parent_id=UK)        ← 현재 countries 테이블의 별도 항목
├── Scotland (level='region', parent_id=UK)
├── Wales (level='region', parent_id=UK)
├── Devon (level='region', parent_id=UK)
└── NW Scotland (level='region', parent_id=UK)

Antarctica (level='country', cow_ccode=NULL)       ← unmappable → 독립 country로 처리
```

### `genus_locations` 변경

```sql
-- 기존 컬럼 보존 (원본 데이터 원칙)
-- 새 컬럼 추가
ALTER TABLE genus_locations ADD COLUMN region_id INTEGER
    REFERENCES geographic_regions(id);
CREATE INDEX idx_genus_locations_region ON genus_locations(region_id);
```

`region_id`는 해당 genus의 **가장 구체적인 지리 단위**를 가리킨다:
- region이 있으면 → region level 엔트리
- region이 없으면 → country level 엔트리

기존 `country_id`, `region` 텍스트 필드는 원본 보존용으로 유지.

## 데이터 마이그레이션

### Step 1: Country level 엔트리 생성

**소스**: COW 매핑의 55개 고유 주권국가 + 5개 unmappable

```
exact match (50건) → 해당 country 이름 그대로 country level
manual/prefix (87건) → 이미 COW 코드로 묶여 있으므로 55개 주권국가로 수렴
unmappable (5건) → 독립 country level로 생성 (Antarctica, Turkestan 등)
```

**예상**: ~60개 country level 엔트리

### Step 2: Region level 엔트리 생성

두 소스에서 region을 수집:

**소스 A — 현 `countries` 테이블의 하위 지역 항목 (87건)**
- `country_cow_mapping`에서 `notes = 'manual'` 또는 `notes = 'prefix'`인 항목
- 예: England → UK 하위 region, Alaska → USA 하위 region, Sichuan → China 하위 region
- 부모: 해당 COW 주권국가의 country level 엔트리

**소스 B — `genus_locations.region` 텍스트 (440개 고유값)**
- 예: Guizhou (parent=China), Queensland (parent=Australia), Vermont (parent=USA)
- 부모: 해당 `country_id`의 sovereign state (COW 매핑 경유)

**중복 제거**: 소스 A와 B에서 (name, parent_country) 기준으로 dedup
- 예: "Sichuan"이 countries에도 있고(소스 A) genus_locations.region에도 있으면(소스 B) → 하나만 생성

**예상**: ~500개 region level 엔트리

### Step 3: `genus_locations.region_id` 채우기

각 `genus_locations` 행에 대해:
1. `region` 텍스트가 있으면 → (region_text, sovereign_country) 로 geographic_regions 검색 → `region_id` 설정
2. `region` 텍스트가 없으면:
   - 현 `country_id`가 실제 주권국가(exact)이면 → 해당 country의 geographic_regions.id
   - 현 `country_id`가 하위 지역(manual/prefix)이면 → 해당 region의 geographic_regions.id
3. 매핑 실패 시 `region_id = NULL` (수동 검토 대상)

### Step 4: `taxa_count` 계산

```sql
-- Region level: 직접 연결된 genus 수
UPDATE geographic_regions SET taxa_count = (
    SELECT COUNT(DISTINCT gl.genus_id) FROM genus_locations gl WHERE gl.region_id = geographic_regions.id
) WHERE level = 'region';

-- Country level: 자신 + 모든 하위 region의 genus 합산
UPDATE geographic_regions SET taxa_count = (
    SELECT COUNT(DISTINCT gl.genus_id) FROM genus_locations gl
    WHERE gl.region_id = geographic_regions.id
       OR gl.region_id IN (SELECT id FROM geographic_regions gr WHERE gr.parent_id = geographic_regions.id)
) WHERE level = 'country';
```

## API 변경

### 기존 엔드포인트 유지 + 수정

**`GET /api/country/<id>`** → 내부적으로 `geographic_regions`에서 level='country' 조회
- 응답에 `regions` 리스트 추가 (하위 region 목록, 각각 taxa_count 포함)

### 새 엔드포인트

**`GET /api/region/<id>`** — Region 상세
```json
{
    "id": 101,
    "name": "Guizhou",
    "level": "region",
    "parent": {"id": 1, "name": "China", "level": "country"},
    "taxa_count": 151,
    "genera": [
        {"id": 1234, "name": "Kaili", "author": "...", "year": 1999, "is_valid": true},
        ...
    ]
}
```

### Named Query 수정

**`countries_list`** → `geographic_regions WHERE level = 'country'`
**신규 `regions_list`** → 전체 region 목록 (country별 그룹핑)

### Genus detail API

`genus_locations` 응답 형식 변경:
```json
// Before
{"locations": [{"id": 3, "country": "China", "region": "Guizhou"}]}

// After
{"locations": [
    {
        "region_id": 101,
        "region_name": "Guizhou",
        "country_id": 1,
        "country_name": "China"
    }
]}
```

## UI 변경

### Genus Detail 모달 — Geographic Information

```
Country:   China > Guizhou        ← 둘 다 클릭 가능
Formation: Kaili Fm (MCAM)        ← 기존과 동일
```

- Country 클릭 → `showCountryDetail(country_id)` (기존)
- Region 클릭 → `showRegionDetail(region_id)` (신규)

### Region Detail 모달 (신규)

```
Region: Guizhou
Country: China (클릭 가능)
Taxa Count: 151
---
Genera: (테이블)
```

### Country Detail 모달 (수정)

기존 genera 목록에 **Regions** 섹션 추가:
```
Regions:
  Guizhou (151)    ← 클릭 가능
  Liaoning (126)
  Shandong (82)
  ...
```

### Countries 테이블 뷰

기존과 동일 (country level만 표시). taxa_count는 하위 region 포함 합산.

## 기존 테이블 처리

| 테이블 | 처리 |
|--------|------|
| `countries` | 유지 (원본 보존). 새 코드는 `geographic_regions` 사용 |
| `country_cow_mapping` | 유지 (마이그레이션 참조용) |
| `genus_locations.country_id` | 유지 (원본 FK 보존) |
| `genus_locations.region` | 유지 (원본 텍스트 보존) |

## 향후 확장

이 계층 구조가 있으면 나중에 추가 가능:
- **Continent**: level='continent', Region/Country의 상위
- **Paleo-continent**: level='paleo_continent' (Gondwana, Laurentia, Baltica 등)
- **Sub-region**: level='sub_region', Region의 하위 (필요 시)

## 작업 단계

| 단계 | 내용 | 예상 파일 |
|------|------|-----------|
| 1 | 마이그레이션 스크립트 작성 | `scripts/create_geographic_regions.py` |
| 2 | 테이블 생성 + 데이터 이관 | `trilobase.db` |
| 3 | API 수정 (country detail, genus detail) | `app.py` |
| 4 | Region detail 엔드포인트 추가 | `app.py` |
| 5 | UI 수정 (genus detail, country detail) | `static/js/app.js` |
| 6 | Region detail 모달 추가 | `static/js/app.js` |
| 7 | Named queries / manifest 갱신 | `scripts/add_scoda_manifest.py` 또는 직접 DB |
| 8 | 테스트 추가 | `test_app.py` |
| 9 | schema_descriptions 갱신 | DB |

## 검증 기준

- 기존 111개 테스트 통과
- 모든 `genus_locations` 행에 `region_id` 설정 (NULL 최소화)
- Country detail에서 하위 region 목록 표시
- Region detail에서 상위 country 링크 + genera 목록 표시
- Genus detail에서 Country > Region 형태로 클릭 가능
