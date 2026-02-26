# PaleoCore Schema

PaleoCore is the shared geographic and stratigraphic reference package that Trilobase depends on. It provides foundational data for countries, formations, temporal ranges, and ICS chronostratigraphy.

**Version:** 0.1.1
**Status:** Production

---

## Table Overview

| # | Table | Records | Description |
|---|-------|---------|-------------|
| 1 | countries | 142 | Country registry (ISO 3166-1 mapped) |
| 2 | geographic_regions | 562 | Hierarchical regions (60 countries + 502 regions) |
| 3 | cow_states | 244 | COW state system records |
| 4 | country_cow_mapping | 142 | Country ↔ COW mappings (96.5%) |
| 5 | formations | 2,004 | Geological formations |
| 6 | temporal_ranges | 28 | Time period codes |
| 7 | ics_chronostrat | 178 | ICS chronostratigraphic units (GTS 2020) |
| 8 | temporal_ics_mapping | 40 | Temporal code ↔ ICS mappings |

---

## Key Tables

### countries

```sql
CREATE TABLE countries (
    id    INTEGER PRIMARY KEY,
    name  TEXT UNIQUE NOT NULL,
    code  TEXT  -- ISO country code (optional)
);
```

### geographic_regions

```sql
CREATE TABLE geographic_regions (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    country_id  INTEGER REFERENCES countries(id),
    uid         TEXT UNIQUE
);
```

### formations

```sql
CREATE TABLE formations (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    country  TEXT,
    period   TEXT
);
```

### temporal_ranges

```sql
CREATE TABLE temporal_ranges (
    id    INTEGER PRIMARY KEY,
    code  TEXT UNIQUE NOT NULL,
    name  TEXT NOT NULL,
    rank  TEXT  -- Period, Epoch, etc.
);
```

### ics_chronostrat

```sql
CREATE TABLE ics_chronostrat (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    rank        TEXT,
    parent_id   INTEGER,
    age_bottom  REAL,
    age_top     REAL
);
```

---

## Cross-Database Usage

PaleoCore is attached at runtime with the `pc` alias:

```sql
ATTACH DATABASE 'db/paleocore.db' AS pc;

-- Country lookup
SELECT * FROM pc.countries WHERE name = 'China';

-- Formation lookup
SELECT * FROM pc.formations WHERE name LIKE '%Wheeler%';

-- Temporal range → ICS mapping
SELECT tr.code, tr.name, ic.name AS ics_name
FROM pc.temporal_ranges tr
JOIN pc.temporal_ics_mapping tim ON tr.id = tim.temporal_range_id
JOIN pc.ics_chronostrat ic ON tim.ics_id = ic.id;
```
