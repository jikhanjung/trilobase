# P53: Assertion-Centric Canonical Taxonomic Data Model

**작성일:** 2026-02-16
**유형:** Plan (장기 아키텍처 비전)

### 문서 관계

```
P50 (설계 방안)     방안 A/B/C 초기 분석, Eurekiidae 중심 사례
  ↓
P51 (리뷰)          A' 권고 (무결성 보강: trigger, partial index, CHECK)
  ↓
P52 (최종 계획)     A' 확정, 구현 로드맵, Phase 1-3
  ↓                    ├─ Phase 1: PoC (taxonomic_opinions 테이블 추가)
  ↓                    ├─ Phase 2: 확장 (56개 Uncertain Family)
  ↓                    └─ Phase 3: 심화 → P53 전환 검토
  ↓
P53 (이 문서)       장기 비전 — 완전한 assertion-centric 모델
                    P52의 Phase 3 이후 도달점
```

- **P52는 P53의 Migration Phase 1에 해당한다.**
  P52의 `taxonomic_opinions` 테이블은 이 문서의 `assertion` 테이블의 전신.
- **P53은 P52 완료 후, 필요성이 입증될 때 검토한다.**
  단일 출처 데이터셋에서는 P52로 충분. 복수 분류 체계가 실제로 요구될 때 전환.

------------------------------------------------------------------------

# 1. Design Philosophy

This model treats **taxonomic knowledge as a collection of assertions**,
not as a single fixed tree.

Core principle:

> There is no "true" parent_id stored in the database. There are only
> assertions made by authors, and classifications are derived views over
> selected assertions.

This aligns with:

-   Historical taxonomy reality (multiple coexisting viewpoints)
-   SCODA snapshot philosophy
-   Future LLM/MCP explainability requirements

------------------------------------------------------------------------

# 2. Core Entities

## 2.1 Taxon

Represents a name-bearing entity.

Fields:

-   id (PK)
-   scientific_name
-   rank
-   original_author
-   original_year
-   type_information (optional)
-   created_at

No parent_id column.

------------------------------------------------------------------------

## 2.2 Reference

Represents a bibliographic source.

Fields:

-   id (PK)
-   full_citation
-   year
-   doi (optional)
-   source_type

------------------------------------------------------------------------

## 2.3 Assertion

The fundamental unit of knowledge.

Fields:

-   id (PK)
-   subject_taxon_id (FK → taxon)
-   predicate (ENUM or controlled vocabulary)
-   object_taxon_id (nullable FK → taxon)
-   value_text (nullable)
-   reference_id (FK → reference)
-   assertion_status (asserted / incertae_sedis / indet / questionable)
-   curation_confidence (0--100 or enum)
-   note
-   created_at

------------------------------------------------------------------------

# 3. Predicate Model

Recommended controlled predicates:

-   PLACED_IN
-   SYNONYM_OF
-   RANK_AS
-   INCLUDES
-   EXCLUDES
-   COMBINATION_OF

This structure is extensible and avoids schema refactoring later.

------------------------------------------------------------------------

# 4. Classification as Derived View

A classification is defined as a filtered set of assertions.

## Example: sensu Adrain, 2011

``` sql
SELECT subject_taxon_id, object_taxon_id
FROM assertion
WHERE predicate = 'PLACED_IN'
AND reference_id = (SELECT id FROM reference WHERE full_citation LIKE '%Adrain 2011%');
```

This assertion set forms the parent-child edges of that classification.

------------------------------------------------------------------------

# 5. Classification Profiles

Optional abstraction layer.

## classification_profile

-   id
-   name
-   rule_definition (JSON)

Examples:

-   "Adrain2011" → reference_id = 12
-   "Current_Editorial" → reference_priority = \[12, 34\],
    curator_override = true

Profiles allow reproducible classification generation.

------------------------------------------------------------------------

# 6. Materialized Classification (Optional)

For performance reasons, selected profiles may generate cached edges.

## classification_edge_cache

-   profile_id
-   child_taxon_id
-   parent_taxon_id

This table is derived, not authoritative.

------------------------------------------------------------------------

# 7. Synonym Handling

Synonymy is expressed via assertions:

-   A SYNONYM_OF B (reference X)

Validity is derived rather than stored as primary truth.

------------------------------------------------------------------------

# 8. Handling Uncertain Placement

Instead of placeholder nodes:

Use:

-   assertion_status = incertae_sedis

Avoid artificial "Uncertain Order" taxa where possible.

------------------------------------------------------------------------

# 9. Example Workflow

1.  Insert taxon records.
2.  Insert assertions from literature.
3.  Define classification profile.
4.  Generate tree via recursive CTE or cached edges.

------------------------------------------------------------------------

# 10. Advantages

-   Multiple taxonomic viewpoints coexist naturally.
-   Full provenance traceability.
-   LLM-safe architecture (explicit reference tracking).
-   SCODA snapshot compatibility.
-   Long-term extensibility.

------------------------------------------------------------------------

# 11. Trade-offs

-   Higher implementation complexity.
-   More complex SQL queries.
-   Requires deliberate UI/API design.

------------------------------------------------------------------------

# 12. Migration Strategy from Parent-Based Model

Phase 1: - Introduce assertion table in parallel.

Phase 2: - Gradually stop treating parent_id as authoritative.

Phase 3: - Deprecate parent_id and derive tree entirely from assertions.

------------------------------------------------------------------------

# Final Principle

Taxonomy is not a tree. Taxonomy is a set of claims.

Trees are views. Assertions are facts.
