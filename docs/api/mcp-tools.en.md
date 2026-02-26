# MCP Tools

Trilobase exposes **7 tools** via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) for natural-language database access through Claude Desktop or other MCP-compatible LLM clients.

---

## Tool Reference

### get_taxonomy_tree

Retrieve the full taxonomic hierarchy tree from Class down to Family.

| Property | Value |
|----------|-------|
| Query type | named_query (`taxonomy_tree`) |
| Parameters | *none* |

---

### search_genera

Search for trilobite genera by name pattern (SQL LIKE).

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| name_pattern | string | yes | — | SQL LIKE pattern (e.g., `Paradoxides%`) |
| valid_only | boolean | no | false | If true, only return valid genera |
| limit | integer | no | 50 | Maximum results |

---

### get_genus_detail

Get full detail for a trilobite genus including synonyms, formations, locations, and hierarchy. Returns a composite evidence pack.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| genus_id | integer | yes | The ID of the genus |

**Returns:** Composite view with genus info, synonyms, formations, locations, bibliography, and provenance.

---

### get_rank_detail

Get detailed information for a specific taxonomic rank (Class, Order, Family, etc.) by its ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| rank_id | integer | yes | The ID of the taxonomic rank |

**Returns:** Rank info with children counts and children list.

---

### get_family_genera

Get all genera belonging to a specific family.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| family_id | integer | yes | The ID of the family |

---

### get_genera_by_country

Get genera found in a specific country.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| country_name | string | yes | Country name (e.g., `China`, `Germany`) |

---

### get_genera_by_formation

Get genera found in a specific geological formation.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| formation_name | string | yes | Formation name |
| limit | integer | no | Maximum results (default: 50) |

---

### get_taxon_opinions

Get taxonomic opinions for a taxon, showing classification viewpoints from different literature sources.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| taxon_id | integer | yes | The ID of the taxon |

**Returns:** Accepted and alternative PLACED_IN, VALID_AS, or SYNONYM_OF opinions with bibliography references.

---

## Evidence Pack Pattern

All MCP responses follow the SCODA evidence pack pattern — every response includes source data and provenance:

```json
{
  "genus": {
    "name": "Paradoxides",
    "author": "BRONGNIART",
    "year": 1822,
    "raw_entry": "original source text..."
  },
  "synonyms": ["..."],
  "provenance": {
    "source": "Jell & Adrain, 2002",
    "canonical_version": "0.2.3"
  }
}
```

**Core principles:**

- **DB is truth** — the database is the single source of truth
- **MCP is access** — MCP is only an access layer
- **LLM is narration** — the LLM provides evidence-based narration only

---

## Setup

See [Getting Started](../getting-started.md#option-3-mcp-server-llm-integration) for MCP server configuration instructions.
