# Trilobase

**Trilobase** is a genus-level taxonomic database for trilobites (Trilobita),
built by cleaning, normalizing, and structuring data from primary literature
into a queryable relational database (SQLite).

The goal is to transform scattered taxonomic information — genus names, synonyms,
higher classification, type localities, and stratigraphic ranges — into a
**machine-queryable format** suitable for research and data exploration.

---

## Primary Sources

- **Jell, P.A. & Adrain, J.M. (2002)** — *Available Generic Names for Trilobites*,
  Memoirs of the Queensland Museum 48(2): 331–553.
- **Adrain, J.M. (2011)** — *Class Trilobita Walch, 1771*,
  in Zhang, Z.-Q. (Ed.), Animal biodiversity (Zootaxa 3148): 104–109.

---

## Database at a Glance

| Taxonomic Rank | Count |
|----------------|-------|
| Class          | 1     |
| Order          | 12    |
| Suborder       | 8     |
| Superfamily    | 13    |
| Family         | 191   |
| Genus          | 5,113 |
| **Total**      | **5,338** |

### Genus Breakdown

- **Valid genera**: 4,258 (83.3%)
- **Invalid genera**: 855 (16.7%)
- **Synonym relationships**: 1,055
- **Bibliographic references**: 2,130
- **Taxonomic opinions**: 84

---

## Key Features

- **Complete genus inventory** — 5,113 genera from Jell & Adrain (2002), covering all trilobite orders
- **Synonym resolution** — 1,055 synonym relationships with 99.9% linkage rate
- **Hierarchical taxonomy** — Class → Order → Suborder → Superfamily → Family → Genus
- **Geographic coverage** — 4,841 genus–country links across 142 countries
- **Stratigraphic data** — 4,853 genus–formation links across 2,004 formations
- **Literature citations** — 2,130 bibliographic references with FK links to taxa
- **MCP integration** — 14 tools for natural-language queries via Claude Desktop
- **SCODA packaging** — Self-Contained Data Artifact format for reproducible distribution

---

## SCODA Framework

Trilobase is a reference implementation of the **SCODA** (Self-Contained Data Artifact) framework.
A single `.scoda` file contains the database, metadata, provenance, schema descriptions,
and UI definitions — making the data self-describing without external documentation.

```sql
-- Check artifact identity
SELECT * FROM artifact_metadata;

-- Check data provenance
SELECT source_type, citation, year FROM provenance;

-- Browse schema descriptions
SELECT * FROM schema_descriptions WHERE table_name = 'taxonomic_ranks';
```

---

## Quick Links

- [Getting Started](getting-started.md) — Installation and usage options
- [Database Schema](database/schema.md) — Table definitions and column descriptions
- [SQL Queries](database/queries.md) — Example queries
- [MCP Tools](api/mcp-tools.md) — LLM integration via Model Context Protocol
- [Changelog](project/changelog.md) — Release history
