# PaleoCore 패키지 스키마 정의서

**버전:** 0.3.0 (설계 초안)
**날짜:** 2026-02-13
**상태:** 설계 문서 (미구현)

---

## 1. 테이블 분류 매핑표

현재 `trilobase.db`의 20개 테이블을 PaleoCore / Trilobase / Both로 분류:

| # | 현재 테이블 | 레코드 | → 패키지 | 변경사항 |
|---|---|---|---|---|
| 1 | **countries** | 142 | PaleoCore | `taxa_count` 컬럼 제거 |
| 2 | **geographic_regions** | 562 | PaleoCore | `taxa_count` 컬럼 제거 |
| 3 | **cow_states** | 244 | PaleoCore | 그대로 |
| 4 | **country_cow_mapping** | 142 | PaleoCore | 그대로 |
| 5 | **formations** | 2,004 | PaleoCore | `taxa_count` 컬럼 제거, 텍스트 컬럼(country/region/period) 유지 |
| 6 | **temporal_ranges** | 28 | PaleoCore | 그대로 |
| 7 | **ics_chronostrat** | 178 | PaleoCore | 그대로 |
| 8 | **temporal_ics_mapping** | 40 | PaleoCore | 그대로 |
| 9 | **taxonomic_ranks** | 5,340 | Trilobase | `country_id`, `formation_id` 컬럼 삭제 (레거시). `temporal_code` → logical FK to PaleoCore |
| 10 | **synonyms** | 1,055 | Trilobase | 그대로 |
| 11 | **bibliography** | 2,130 | Trilobase | 그대로 |
| 12 | **genus_locations** | 4,841 | Trilobase | `country_id`, `region_id` → logical FK to PaleoCore |
| 13 | **genus_formations** | 4,853 | Trilobase | `formation_id` → logical FK to PaleoCore |
| 14 | **user_annotations** | — | Trilobase (Overlay) | 그대로 |
| 15 | **artifact_metadata** | — | Both | 각 패키지 고유 값 |
| 16 | **provenance** | — | Both | 관련 출처만 각자 보유 |
| 17 | **schema_descriptions** | — | Both | 해당 테이블만 기술 |
| 18 | **ui_display_intent** | — | Both | 해당 엔티티만 |
| 19 | **ui_queries** | — | Both | 해당 쿼리만 |
| 20 | **ui_manifest** | — | Both | 해당 뷰만 |

---

## 2. PaleoCore CREATE TABLE — 데이터 테이블 (8개)

### 2.1 countries

```sql
CREATE TABLE countries (
    id       INTEGER PRIMARY KEY,
    name     TEXT UNIQUE NOT NULL,
    code     TEXT                    -- ISO country code (optional)
);
```

변경: `taxa_count INTEGER DEFAULT 0` 제거. 소비자 패키지가 런타임에 JOIN으로 계산.

### 2.2 geographic_regions

```sql
CREATE TABLE geographic_regions (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    level     TEXT NOT NULL,          -- 'country' or 'region'
    parent_id INTEGER,               -- self-referencing FK
    cow_ccode INTEGER,               -- COW country code (countries만 해당)
    FOREIGN KEY (parent_id) REFERENCES geographic_regions(id)
);
```

변경: `taxa_count INTEGER DEFAULT 0` 제거.

### 2.3 cow_states

```sql
CREATE TABLE cow_states (
    cow_ccode    INTEGER NOT NULL,
    abbrev       TEXT    NOT NULL,
    name         TEXT    NOT NULL,
    start_date   TEXT    NOT NULL,
    end_date     TEXT    NOT NULL,
    version      INTEGER NOT NULL DEFAULT 2024,
    PRIMARY KEY (cow_ccode, start_date)
);
```

변경 없음.

### 2.4 country_cow_mapping

```sql
CREATE TABLE country_cow_mapping (
    country_id   INTEGER NOT NULL,
    cow_ccode    INTEGER,
    parent_name  TEXT,
    notes        TEXT,
    FOREIGN KEY (country_id) REFERENCES countries(id),
    PRIMARY KEY (country_id)
);
```

변경 없음.

### 2.5 formations

```sql
CREATE TABLE formations (
    id              INTEGER PRIMARY KEY,
    name            TEXT UNIQUE NOT NULL,
    normalized_name TEXT,
    formation_type  TEXT,               -- Fm, Lst, Sh, Gp, etc.
    country         TEXT,               -- 텍스트 참고용 (정규화 FK 아님)
    region          TEXT,               -- 텍스트 참고용
    period          TEXT                -- 텍스트 참고용
);
```

변경: `taxa_count INTEGER DEFAULT 0` 제거. `country`/`region`/`period` 텍스트 컬럼은 원본 Jell & Adrain (2002)에서 온 참고 정보로 유지.

### 2.6 temporal_ranges

```sql
CREATE TABLE temporal_ranges (
    id        INTEGER PRIMARY KEY,
    code      TEXT UNIQUE NOT NULL,     -- LCAM, MCAM, UCAM, LORD, ...
    name      TEXT,                     -- Lower Cambrian, ...
    period    TEXT,                     -- Cambrian, Ordovician, ...
    epoch     TEXT,                     -- Lower, Middle, Upper
    start_mya REAL,                     -- 시작 시기 (Ma)
    end_mya   REAL                      -- 종료 시기 (Ma)
);
```

변경 없음.

### 2.7 ics_chronostrat

```sql
CREATE TABLE ics_chronostrat (
    id                INTEGER PRIMARY KEY,
    ics_uri           TEXT UNIQUE NOT NULL,  -- ICS SKOS URI
    name              TEXT NOT NULL,
    rank              TEXT NOT NULL,         -- Super-Eon, Eon, Era, Period, ...
    parent_id         INTEGER,              -- self-referencing FK
    start_mya         REAL,
    start_uncertainty REAL,
    end_mya           REAL,
    end_uncertainty   REAL,
    short_code        TEXT,                 -- e.g., 'C', 'O', 'S', ...
    color             TEXT,                 -- hex color (#RRGGBB)
    display_order     INTEGER,              -- 표시 순서
    ratified_gssp     INTEGER DEFAULT 0,    -- GSSP 비준 여부
    FOREIGN KEY (parent_id) REFERENCES ics_chronostrat(id)
);
```

변경 없음.

### 2.8 temporal_ics_mapping

```sql
CREATE TABLE temporal_ics_mapping (
    id            INTEGER PRIMARY KEY,
    temporal_code TEXT NOT NULL,             -- FK to temporal_ranges.code
    ics_id        INTEGER NOT NULL,         -- FK to ics_chronostrat.id
    mapping_type  TEXT NOT NULL,            -- exact, aggregate, partial, unmappable
    notes         TEXT,
    FOREIGN KEY (ics_id) REFERENCES ics_chronostrat(id)
);
```

변경 없음.

---

## 3. PaleoCore CREATE TABLE — SCODA 메타데이터 테이블 (6개)

### 3.1 artifact_metadata

```sql
CREATE TABLE artifact_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

### 3.2 provenance

```sql
CREATE TABLE provenance (
    id          INTEGER PRIMARY KEY,
    source_type TEXT NOT NULL,       -- reference, build
    citation    TEXT NOT NULL,
    description TEXT,
    year        INTEGER,
    url         TEXT
);
```

### 3.3 schema_descriptions

```sql
CREATE TABLE schema_descriptions (
    table_name  TEXT NOT NULL,
    column_name TEXT,                -- NULL for table-level description
    description TEXT NOT NULL,
    PRIMARY KEY (table_name, column_name)
);
```

### 3.4 ui_display_intent

```sql
CREATE TABLE ui_display_intent (
    id           INTEGER PRIMARY KEY,
    entity       TEXT NOT NULL,
    default_view TEXT NOT NULL,
    description  TEXT,
    source_query TEXT,
    priority     INTEGER DEFAULT 0
);
```

### 3.5 ui_queries

```sql
CREATE TABLE ui_queries (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    sql         TEXT NOT NULL,
    params_json TEXT,
    created_at  TEXT NOT NULL
);
```

### 3.6 ui_manifest

```sql
CREATE TABLE ui_manifest (
    name          TEXT PRIMARY KEY,
    description   TEXT,
    manifest_json TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
```

---

## 4. PaleoCore manifest.json

```json
{
  "format": "scoda",
  "format_version": "1.0",
  "name": "paleocore",
  "version": "0.3.0",
  "title": "PaleoCore - Shared Paleontological Infrastructure",
  "description": "Geography, lithostratigraphy, and chronostratigraphy reference data for paleontological databases",
  "created_at": "2026-02-13T00:00:00+00:00",
  "license": "CC-BY-4.0",
  "authors": [],
  "dependencies": [],
  "provides": ["geography", "lithostratigraphy", "chronostratigraphy"],
  "data_file": "data.db",
  "record_count": 3340,
  "data_checksum_sha256": "<computed at build time>"
}
```

주요 필드:
- `dependencies: []` — 루트 패키지, 외부 의존성 없음
- `provides`: 이 패키지가 제공하는 도메인 목록
- `record_count`: 8개 데이터 테이블 합계 (142 + 562 + 244 + 142 + 2,004 + 28 + 178 + 40 = 3,340)

---

## 5. PaleoCore SCODA 메타데이터 내용

### 5.1 artifact_metadata (7건)

| key | value |
|-----|-------|
| `artifact_id` | `paleocore` |
| `name` | `PaleoCore` |
| `version` | `0.3.0` |
| `schema_version` | `1.0` |
| `created_at` | `2026-02-13` |
| `description` | `Shared paleontological infrastructure: geography, lithostratigraphy, chronostratigraphy` |
| `license` | `CC-BY-4.0` |

### 5.2 provenance (3건)

| id | source_type | citation | description | year |
|----|-------------|----------|-------------|------|
| 1 | `reference` | Correlates of War Project. State System Membership (v2024). | COW 주권국가 마스터 데이터 (cow_states, country_cow_mapping) | 2024 |
| 2 | `reference` | International Commission on Stratigraphy. International Chronostratigraphic Chart (GTS 2020). SKOS/RDF. | ICS 지질연대표 (ics_chronostrat, temporal_ics_mapping) | 2020 |
| 3 | `build` | PaleoCore build pipeline (2026). Scripts: import_cow.py, create_geographic_regions.py, import_ics.py | 자동화된 임포트 및 매핑 파이프라인 | 2026 |

참고: Jell & Adrain (2002)과 Adrain (2011)은 Trilobase 패키지에만 해당하므로 PaleoCore provenance에서 제외.

### 5.3 schema_descriptions (~80건)

8개 데이터 테이블 + 컬럼별 설명:

**countries** (3 컬럼 + 테이블 설명 = 4건):
| table_name | column_name | description |
|------------|-------------|-------------|
| countries | NULL | Countries for geographic reference (142 records) |
| countries | id | Primary key |
| countries | name | Country name |
| countries | code | ISO country code |

**geographic_regions** (5 컬럼 + 테이블 설명 = 6건):
| table_name | column_name | description |
|------------|-------------|-------------|
| geographic_regions | NULL | Hierarchical geographic data: countries and sub-regions (562 records) |
| geographic_regions | id | Primary key |
| geographic_regions | name | Region or country name |
| geographic_regions | level | Hierarchy level: 'country' or 'region' |
| geographic_regions | parent_id | FK to parent geographic_regions.id (self-referencing) |
| geographic_regions | cow_ccode | COW country code (countries only) |

**cow_states** (6 컬럼 + 테이블 설명 = 7건):
| table_name | column_name | description |
|------------|-------------|-------------|
| cow_states | NULL | Correlates of War State System Membership v2024 (244 records) |
| cow_states | cow_ccode | COW numeric country code |
| cow_states | abbrev | COW country abbreviation |
| cow_states | name | Country name in COW dataset |
| cow_states | start_date | State system membership start date |
| cow_states | end_date | State system membership end date |
| cow_states | version | COW dataset version |

**country_cow_mapping** (4 컬럼 + 테이블 설명 = 5건):
| table_name | column_name | description |
|------------|-------------|-------------|
| country_cow_mapping | NULL | Mapping between countries table and COW state codes (142 records) |
| country_cow_mapping | country_id | FK to countries.id |
| country_cow_mapping | cow_ccode | COW country code (NULL if unmappable) |
| country_cow_mapping | parent_name | Parent country name for dependent territories |
| country_cow_mapping | notes | Mapping notes (method: exact, manual, prefix, unmappable) |

**formations** (7 컬럼 + 테이블 설명 = 8건):
| table_name | column_name | description |
|------------|-------------|-------------|
| formations | NULL | Geological formations (2,004 records) |
| formations | id | Primary key |
| formations | name | Formation name as given in source |
| formations | normalized_name | Lowercased, normalized form of name |
| formations | formation_type | Abbreviation: Fm (Formation), Sh (Shale), Lst (Limestone), Gp (Group), etc. |
| formations | country | Country where formation is located (text reference) |
| formations | region | Region within country (text reference) |
| formations | period | Geological period (text reference) |

**temporal_ranges** (7 컬럼 + 테이블 설명 = 8건):
| table_name | column_name | description |
|------------|-------------|-------------|
| temporal_ranges | NULL | Geological time period codes and age ranges (28 records) |
| temporal_ranges | id | Primary key |
| temporal_ranges | code | Short code: LCAM, MCAM, UCAM, LORD, MORD, UORD, etc. |
| temporal_ranges | name | Full name of the time period |
| temporal_ranges | period | Parent period: Cambrian, Ordovician, Silurian, Devonian, Carboniferous, Permian |
| temporal_ranges | epoch | Epoch within period: Lower, Middle, Upper |
| temporal_ranges | start_mya | Start of range in millions of years ago |
| temporal_ranges | end_mya | End of range in millions of years ago |

**ics_chronostrat** (13 컬럼 + 테이블 설명 = 14건):
| table_name | column_name | description |
|------------|-------------|-------------|
| ics_chronostrat | NULL | ICS International Chronostratigraphic Chart, GTS 2020 (178 records) |
| ics_chronostrat | id | Primary key |
| ics_chronostrat | ics_uri | ICS SKOS URI (unique identifier) |
| ics_chronostrat | name | Chronostratigraphic unit name |
| ics_chronostrat | rank | Rank: Super-Eon, Eon, Era, Period, Sub-Period, Epoch, Age |
| ics_chronostrat | parent_id | FK to parent ics_chronostrat.id (self-referencing hierarchy) |
| ics_chronostrat | start_mya | Start age in millions of years ago |
| ics_chronostrat | start_uncertainty | Uncertainty of start age (Ma) |
| ics_chronostrat | end_mya | End age in millions of years ago |
| ics_chronostrat | end_uncertainty | Uncertainty of end age (Ma) |
| ics_chronostrat | short_code | Short code for display (e.g., C, O, S) |
| ics_chronostrat | color | Hex color for chart display (#RRGGBB) |
| ics_chronostrat | display_order | Display ordering for chart rendering |
| ics_chronostrat | ratified_gssp | Whether the GSSP has been ratified (1/0) |

**temporal_ics_mapping** (4 컬럼 + 테이블 설명 = 5건):
| table_name | column_name | description |
|------------|-------------|-------------|
| temporal_ics_mapping | NULL | Mapping between temporal_ranges codes and ICS units (40 records) |
| temporal_ics_mapping | id | Primary key |
| temporal_ics_mapping | temporal_code | temporal_ranges.code reference |
| temporal_ics_mapping | ics_id | FK to ics_chronostrat.id |
| temporal_ics_mapping | mapping_type | Mapping type: exact, aggregate, partial, unmappable |
| temporal_ics_mapping | notes | Mapping notes and rationale |

**SCODA 테이블 자기 참조** (각 6개 테이블 약 ~20건):

동일 구조이므로 생략 — 현재 `add_scoda_tables.py`의 패턴을 따름.

**합계: ~80건** (8개 데이터 테이블 57건 + SCODA 테이블 ~20건)

### 5.4 ui_display_intent (4건)

| id | entity | default_view | description | source_query |
|----|--------|--------------|-------------|--------------|
| 1 | countries | table | Countries for geographic reference | countries_list |
| 2 | formations | table | Geological formations | formations_list |
| 3 | chronostratigraphy | chart | ICS International Chronostratigraphic Chart | ics_chronostrat_list |
| 4 | temporal_ranges | table | Geological time period codes | temporal_ranges_list |

### 5.5 ui_queries (~8건)

| id | name | description | sql |
|----|------|-------------|-----|
| 1 | countries_list | All countries sorted by name | `SELECT id, name, code FROM countries ORDER BY name` |
| 2 | regions_list | All regions with parent country | `SELECT gr.id, gr.name, p.name AS country_name, p.id AS country_id FROM geographic_regions gr LEFT JOIN geographic_regions p ON gr.parent_id = p.id WHERE gr.level = 'region' ORDER BY p.name, gr.name` |
| 3 | formations_list | All formations sorted by name | `SELECT id, name, formation_type, country, period FROM formations ORDER BY name` |
| 4 | temporal_ranges_list | All temporal range codes | `SELECT id, code, name, period, epoch, start_mya, end_mya FROM temporal_ranges ORDER BY start_mya DESC` |
| 5 | ics_chronostrat_list | ICS chart data | `SELECT id, name, rank, parent_id, start_mya, end_mya, color, display_order FROM ics_chronostrat ORDER BY display_order` |
| 6 | country_regions | Regions for a specific country | `SELECT id, name FROM geographic_regions WHERE parent_id = :country_id AND level = 'region' ORDER BY name` |
| 7 | country_cow_info | COW mapping for a country | `SELECT ccm.cow_ccode, cs.abbrev, cs.name AS cow_name, cs.start_date, cs.end_date FROM country_cow_mapping ccm LEFT JOIN cow_states cs ON ccm.cow_ccode = cs.cow_ccode WHERE ccm.country_id = :country_id` |
| 8 | temporal_ics_mapping_list | ICS units for a temporal code | `SELECT tim.mapping_type, ic.name, ic.rank, ic.start_mya, ic.end_mya, ic.color FROM temporal_ics_mapping tim JOIN ics_chronostrat ic ON tim.ics_id = ic.id WHERE tim.temporal_code = :temporal_code` |

참고: 쿼리에서 `taxa_count` 참조 제거.

### 5.6 ui_manifest (1건)

```json
{
  "name": "default",
  "description": "Default UI manifest for PaleoCore viewer",
  "manifest_json": {
    "default_view": "countries_table",
    "views": {
      "countries_table": {
        "type": "table",
        "title": "Countries",
        "description": "Countries for geographic reference",
        "source_query": "countries_list",
        "icon": "bi-globe",
        "columns": [
          {"key": "name", "label": "Country", "sortable": true, "searchable": true},
          {"key": "code", "label": "Code", "sortable": true, "searchable": false}
        ],
        "default_sort": {"key": "name", "direction": "asc"},
        "searchable": true
      },
      "formations_table": {
        "type": "table",
        "title": "Formations",
        "description": "Geological formations",
        "source_query": "formations_list",
        "icon": "bi-layers",
        "columns": [
          {"key": "name", "label": "Formation", "sortable": true, "searchable": true},
          {"key": "formation_type", "label": "Type", "sortable": true, "searchable": false},
          {"key": "country", "label": "Country", "sortable": true, "searchable": true},
          {"key": "period", "label": "Period", "sortable": true, "searchable": true}
        ],
        "default_sort": {"key": "name", "direction": "asc"},
        "searchable": true
      },
      "chronostratigraphy_chart": {
        "type": "chart",
        "title": "Chronostratigraphy",
        "description": "ICS International Chronostratigraphic Chart (GTS 2020)",
        "source_query": "ics_chronostrat_list",
        "icon": "bi-clock-history",
        "columns": [
          {"key": "name", "label": "Name", "sortable": true, "searchable": true},
          {"key": "rank", "label": "Rank", "sortable": true, "searchable": true},
          {"key": "start_mya", "label": "Start (Ma)", "sortable": true, "type": "number"},
          {"key": "end_mya", "label": "End (Ma)", "sortable": true, "type": "number"},
          {"key": "color", "label": "Color", "sortable": false, "type": "color"}
        ],
        "default_sort": {"key": "display_order", "direction": "asc"},
        "searchable": true
      },
      "temporal_ranges_table": {
        "type": "table",
        "title": "Temporal Ranges",
        "description": "Geological time period codes used in genus records",
        "source_query": "temporal_ranges_list",
        "icon": "bi-hourglass",
        "columns": [
          {"key": "code", "label": "Code", "sortable": true, "searchable": true},
          {"key": "name", "label": "Name", "sortable": true, "searchable": true},
          {"key": "period", "label": "Period", "sortable": true, "searchable": true},
          {"key": "epoch", "label": "Epoch", "sortable": true, "searchable": false},
          {"key": "start_mya", "label": "Start (Ma)", "sortable": true, "type": "number"},
          {"key": "end_mya", "label": "End (Ma)", "sortable": true, "type": "number"}
        ],
        "default_sort": {"key": "start_mya", "direction": "desc"},
        "searchable": true
      }
    }
  }
}
```

---

## 6. Trilobase 변경 사항 요약

PaleoCore 분리 후 Trilobase 패키지에 필요한 변경:

### 6.1 테이블 제거 (8개)

PaleoCore로 이동하므로 Trilobase DB에서 삭제:
- `countries`
- `geographic_regions`
- `cow_states`
- `country_cow_mapping`
- `formations`
- `temporal_ranges`
- `ics_chronostrat`
- `temporal_ics_mapping`

### 6.2 manifest.json 변경

```json
{
  "format": "scoda",
  "format_version": "1.0",
  "name": "trilobase",
  "version": "2.0.0",
  "dependencies": [
    {"name": "paleocore", "version": ">=0.3.0,<0.4.0"}
  ],
  "...": "..."
}
```

### 6.3 taxonomic_ranks 스키마 변경

```sql
-- 삭제할 컬럼 (레거시, junction table로 대체됨):
--   country_id  INTEGER  (→ genus_locations로 대체)
--   formation_id INTEGER (→ genus_formations로 대체)

-- 유지하되 논리적 FK로 전환:
--   temporal_code TEXT    (→ logical FK to paleocore.temporal_ranges.code)
```

### 6.4 런타임 ATTACH

```python
# Trilobase 앱에서 PaleoCore 데이터 접근
conn = sqlite3.connect('trilobase.db')
conn.execute("ATTACH 'paleocore.db' AS pc")

# Cross-package JOIN 예시
conn.execute("""
    SELECT g.name, c.name AS country
    FROM genus_locations gl
    JOIN taxonomic_ranks g ON gl.genus_id = g.id
    JOIN pc.countries c ON gl.country_id = c.id
    WHERE c.name = 'China'
""")

# ICS 매핑 예시
conn.execute("""
    SELECT tr.code, tr.name, ic.name AS ics_unit, tim.mapping_type
    FROM taxonomic_ranks t
    JOIN pc.temporal_ranges tr ON t.temporal_code = tr.code
    JOIN pc.temporal_ics_mapping tim ON tim.temporal_code = tr.code
    JOIN pc.ics_chronostrat ic ON tim.ics_id = ic.id
    WHERE t.name = 'Paradoxides'
""")
```

### 6.5 SCODA 메타데이터 갱신

Trilobase의 SCODA 메타데이터에서:

**provenance**: COW 및 ICS 출처(id 4, 5) 제거 → PaleoCore에만 보유
**ui_queries**: 지리/연대 관련 쿼리 제거 또는 cross-DB 쿼리로 수정
- `countries_list` → `SELECT id, name, code FROM pc.countries ORDER BY name`
- `formations_list` → `SELECT id, name, formation_type, country, period FROM pc.formations ORDER BY name`
- `ics_chronostrat_list` → `SELECT ... FROM pc.ics_chronostrat ORDER BY display_order`

**ui_display_intent**: countries, formations 엔티티의 source_query 갱신
**ui_manifest**: countries_table, formations_table, chronostratigraphy_table의 source_query 갱신

---

## 7. Logical Foreign Key 명세

패키지 간 참조 (SQLite FOREIGN KEY 제약 없음, 문서로 명시):

| Source (Trilobase) | Target (PaleoCore) | 참조 의미 |
|---|---|---|
| `taxonomic_ranks.temporal_code` | `temporal_ranges.code` | Genus의 지질시대 |
| `genus_locations.country_id` | `countries.id` | Genus 산출 국가 |
| `genus_locations.region_id` | `geographic_regions.id` | Genus 산출 지역 |
| `genus_formations.formation_id` | `formations.id` | Genus 산출 지층 |

**삭제된 레거시 참조** (PaleoCore 분리 시 함께 제거):
| 레거시 컬럼 | 대체 관계 |
|---|---|
| `taxonomic_ranks.country_id` | → `genus_locations` (junction table) |
| `taxonomic_ranks.formation_id` | → `genus_formations` (junction table) |

### 런타임 무결성 검증

ATTACH 후 orphan 확인 쿼리:

```sql
-- country_id가 PaleoCore에 없는 genus_locations
SELECT gl.id, gl.country_id
FROM genus_locations gl
LEFT JOIN pc.countries c ON gl.country_id = c.id
WHERE c.id IS NULL;

-- formation_id가 PaleoCore에 없는 genus_formations
SELECT gf.id, gf.formation_id
FROM genus_formations gf
LEFT JOIN pc.formations f ON gf.formation_id = f.id
WHERE f.id IS NULL;

-- temporal_code가 PaleoCore에 없는 taxonomic_ranks
SELECT t.id, t.name, t.temporal_code
FROM taxonomic_ranks t
LEFT JOIN pc.temporal_ranges tr ON t.temporal_code = tr.code
WHERE t.temporal_code IS NOT NULL AND tr.code IS NULL;
```

---

## 8. 데이터 흐름 다이어그램

```
┌─────────────────────────────────────┐
│         PaleoCore (paleocore.db)     │
│                                      │
│  countries ◄─────┐                   │
│  geographic_regions ◄─┐              │
│  cow_states            │              │
│  country_cow_mapping   │              │
│  formations ◄────────┐│              │
│  temporal_ranges ◄──┐││              │
│  ics_chronostrat    │││              │
│  temporal_ics_mapping│││              │
└─────────────────────┼┼┼──────────────┘
   ATTACH AS pc       │││
┌─────────────────────┼┼┼──────────────┐
│         Trilobase (trilobase.db)     │
│                     │││              │
│  taxonomic_ranks ───┘││  (temporal_code → pc.temporal_ranges.code)
│  synonyms            ││              │
│  bibliography        ││              │
│  genus_locations ────┘│  (country_id → pc.countries.id)
│                       │  (region_id → pc.geographic_regions.id)
│  genus_formations ────┘  (formation_id → pc.formations.id)
│                                      │
└──────────────────────────────────────┘
```

---

## 9. 구현 로드맵 (후속 Phase)

이 문서는 설계 정의만 다룬다. 실제 구현은 별도 Phase에서 진행:

1. **PaleoCore DB 생성 스크립트** — `scripts/create_paleocore.py`
   - 현재 `trilobase.db`에서 8개 데이터 테이블 추출
   - `taxa_count` 컬럼 제거
   - SCODA 메타데이터 삽입

2. **Trilobase DB 마이그레이션** — `scripts/migrate_to_v2.py`
   - 8개 테이블 DROP
   - `taxonomic_ranks`에서 `country_id`, `formation_id` 제거
   - `manifest.json`에 dependency 추가
   - SCODA 메타데이터 갱신

3. **앱 코드 수정** — `app.py`, `mcp_server.py`, `scoda_package.py`
   - `ATTACH` 로직 추가
   - 쿼리 수정 (cross-DB JOIN)
   - UI에서 PaleoCore 데이터 표시

4. **테스트 갱신** — `test_app.py`, `test_mcp.py`
   - dual-DB fixture 구성
   - cross-DB 쿼리 테스트
