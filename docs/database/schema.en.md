# Database Schema

Trilobase uses a **3-database architecture**:

1. **Canonical DB** (`trilobase.db`) — read-only, immutable taxonomic data
2. **Overlay DB** (`trilobase_overlay.db`) — read/write user annotations
3. **PaleoCore DB** (`paleocore.db`) — shared geographic/stratigraphic reference data

```python
conn = sqlite3.connect('db/trilobase.db')
conn.execute("ATTACH DATABASE 'dist/trilobase_overlay.db' AS overlay")
conn.execute("ATTACH DATABASE 'db/paleocore.db' AS pc")
```

---

## Canonical DB (trilobase.db)

### taxonomic_ranks

Unified taxonomic hierarchy — 5,341 records (Class through Genus + 2 placeholders + 1 Suborder).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | Taxon name |
| rank | TEXT | Taxonomic rank (Class, Order, Suborder, Superfamily, Family, Genus) |
| parent_id | INTEGER | FK to parent taxon |
| author | TEXT | Authority author |
| year | INTEGER | Year of description |
| year_suffix | TEXT | Suffix for same-author-year disambiguation |
| genera_count | INTEGER | Number of genera (for higher ranks) |
| notes | TEXT | Additional notes |
| created_at | TEXT | Record creation timestamp |
| type_species | TEXT | Type species (Genus only) |
| type_species_author | TEXT | Type species authority (Genus only) |
| formation | TEXT | Type formation text (Genus only) |
| location | TEXT | Type locality text (Genus only) |
| family | TEXT | Family name text (Genus only) |
| temporal_code | TEXT | Time period code (Genus only) |
| is_valid | INTEGER | 1 = valid, 0 = invalid (Genus only) |
| raw_entry | TEXT | Original source text (Genus only) |

### synonyms

Synonym relationships — 1,055 records.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| junior_taxon_id | INTEGER | FK to junior synonym in taxonomic_ranks |
| senior_taxon_name | TEXT | Name of senior synonym |
| senior_taxon_id | INTEGER | FK to senior synonym in taxonomic_ranks |
| synonym_type | TEXT | Type: j.s.s., j.o.s., preocc. |
| fide_author | TEXT | "According to" author |
| fide_year | INTEGER | "According to" year |
| notes | TEXT | Additional notes |

### genus_formations

Genus–Formation many-to-many — 4,853 records.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| genus_id | INTEGER | FK to taxonomic_ranks |
| formation_id | INTEGER | FK to pc.formations |
| is_type_locality | INTEGER | Whether this is the type locality |
| notes | TEXT | Additional notes |

### genus_locations

Genus–Country many-to-many — 4,841 records.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| genus_id | INTEGER | FK to taxonomic_ranks |
| country_id | INTEGER | FK to pc.countries |
| region | TEXT | Sub-country region |
| is_type_locality | INTEGER | Whether this is the type locality |
| notes | TEXT | Additional notes |

### bibliography

Literature references — 2,130 records.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| authors | TEXT | Author(s) |
| year | INTEGER | Publication year |
| year_suffix | TEXT | Same-year disambiguation suffix |
| title | TEXT | Article/chapter title |
| journal | TEXT | Journal name |
| volume | TEXT | Volume number |
| pages | TEXT | Page range |
| publisher | TEXT | Publisher |
| city | TEXT | Publication city |
| editors | TEXT | Editor(s) |
| book_title | TEXT | Book title (for chapters) |
| reference_type | TEXT | article, book, chapter |
| raw_entry | TEXT | Original citation text |

### taxon_bibliography

Taxon–Bibliography FK links — 4,040 records.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| taxon_id | INTEGER | FK to taxonomic_ranks |
| bibliography_id | INTEGER | FK to bibliography |
| relationship_type | TEXT | original_description, fide |
| synonym_id | INTEGER | FK to synonyms (if via synonym) |
| match_confidence | REAL | Matching confidence score |
| match_method | TEXT | How the match was determined |
| notes | TEXT | Additional notes |
| created_at | TEXT | Timestamp |

### taxonomic_opinions

Taxonomic opinions — 84 records (PLACED_IN 82 + SPELLING_OF 2).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| taxon_id | INTEGER | FK to taxonomic_ranks |
| opinion_type | TEXT | PLACED_IN, SPELLING_OF |
| related_taxon_id | INTEGER | FK to related taxon |
| proposed_valid | INTEGER | Whether this opinion proposes the taxon as valid |
| bibliography_id | INTEGER | FK to bibliography |
| assertion_status | TEXT | asserted, incertae_sedis, indet, questionable |
| curation_confidence | TEXT | Confidence level |
| is_accepted | INTEGER | Whether this is the currently accepted opinion |
| notes | TEXT | Additional notes |
| created_at | TEXT | Timestamp |

### taxa (view)

Backward-compatibility view exposing only Genus-rank records.

```sql
CREATE VIEW taxa AS SELECT ... FROM taxonomic_ranks WHERE rank = 'Genus';
```

---

## SCODA Metadata Tables

| Table | Description |
|-------|-------------|
| artifact_metadata | Key-value artifact identity (name, version, etc.) |
| provenance | Data sources with citations and descriptions |
| schema_descriptions | Human-readable descriptions for tables and columns |
| ui_display_intent | View type hints for UI rendering |
| ui_queries | Named SQL queries with parameter definitions |
| ui_manifest | Declarative UI view definitions (JSON) |

---

## Overlay DB (trilobase_overlay.db)

### overlay_metadata

Tracks which canonical DB version this overlay is associated with.

| Column | Type | Description |
|--------|------|-------------|
| key | TEXT | Metadata key (canonical_version, created_at) |
| value | TEXT | Metadata value |

### user_annotations

User-created annotations that persist across database updates.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| entity_type | TEXT | Type of annotated entity |
| entity_id | INTEGER | ID of annotated entity |
| entity_name | TEXT | Name for cross-release matching |
| annotation_type | TEXT | Type of annotation |
| content | TEXT | Annotation content |
| author | TEXT | Annotation author |
| created_at | TEXT | Timestamp |
