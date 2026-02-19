# P51: Taxonomic Opinions DB Design Review (A' Version Recommendation)

**작성일:** 2026-02-16
**유형:** Review

### 문서 관계

- **P50**: 이 리뷰의 대상 (방안 A/B/C 초기 분석)
- **이 문서 (P51)**: P50에 대한 리뷰 → A' 권고
- **P52 (최종)**: P50 + P51 + 논의를 종합한 확정 계획
- **P53**: 장기 아키텍처 비전 (assertion-centric 모델)

## Overview

This document reviews the proposed taxonomic opinions design (Options A,
B, C) and provides practical implementation recommendations for
Trilobase / SCODA in its current stage.

The main conclusion:

> Adopt **Option A**, but reinforce it with structural safeguards (A'
> version) to prevent data inconsistency and future refactoring pain.

------------------------------------------------------------------------

# 1. Core Recommendation: A' (Option A + Integrity Safeguards)

Option A (separate `taxonomic_opinions` table while keeping existing
tree structure) is appropriate for the current development stage.

However, it must be reinforced with:

1.  Partial unique constraints (only one accepted opinion per taxon per
    type)
2.  Triggers to synchronize `parent_id` with accepted placement opinion
3.  Clear reference model (single `reference_id` as authority source)
4.  Structured predicate system (avoid free-text opinion types)

Without these safeguards, Option A will quickly drift into
inconsistency.

------------------------------------------------------------------------

# 2. Structural Improvements

## 2.1 Enforce Single Accepted Opinion

For each `(taxon_id, opinion_type)` only one `is_accepted = 1` record
should exist.

Use partial unique index:

``` sql
CREATE UNIQUE INDEX idx_unique_accepted_opinion
ON taxonomic_opinions(taxon_id, opinion_type)
WHERE is_accepted = 1;
```

This prevents silent conflicts in classification state.

------------------------------------------------------------------------

## 2.2 Trigger-Based Synchronization (Critical)

If `opinion_type = 'placement'` and `is_accepted = 1`, then
`taxonomic_ranks.parent_id` must automatically update.

Do not rely on manual synchronization.

Conceptual trigger:

``` sql
CREATE TRIGGER trg_sync_parent
AFTER INSERT ON taxonomic_opinions
WHEN NEW.opinion_type = 'placement' AND NEW.is_accepted = 1
BEGIN
  UPDATE taxonomic_ranks
  SET parent_id = NEW.related_taxon_id
  WHERE id = NEW.taxon_id;
END;
```

This preserves compatibility while preventing tree corruption.

------------------------------------------------------------------------

# 3. Opinion Type: Avoid Free Text Drift

Instead of loose TEXT values such as:

-   placement
-   validity
-   synonymy

Use either:

-   CHECK constraint enum
-   Or structured predicate model

Example:

``` sql
CHECK(opinion_type IN ('PLACED_IN','RANK_AS','SYNONYM_OF'))
```

Better long-term model:

-   subject_taxon_id
-   predicate
-   object_taxon_id OR value_field
-   reference_id

This scales to combination changes, circumscription differences, etc.

------------------------------------------------------------------------

# 4. Reference Model Simplification

Avoid triple authority fields (`bibliography_id`, `provenance_id`,
author/year text).

Use:

-   `reference_id` (FK → reference table)

Keep provenance (dataset bundle source) separate from literature
citation.

This prevents long-term authority drift.

------------------------------------------------------------------------

# 5. Separate Conceptual vs Curation Uncertainty

Current `confidence` mixes:

1.  Author uncertainty (incertae sedis)
2.  Curator uncertainty

Separate them:

-   assertion_status (asserted / incertae_sedis / indet / questionable)
-   curation_confidence (numeric or enum)

This distinction becomes important when LLM interfaces query the system.

------------------------------------------------------------------------

# 6. Placeholder Nodes (e.g., "Uncertain Order")

If placeholder taxa are kept:

Add:

-   is_placeholder flag

Or treat uncertain placement as assertion status rather than as true
taxon node.

Otherwise phylogenetic analyses and aggregation queries will require
constant exceptions.

------------------------------------------------------------------------

# 7. Synonym Handling Strategy

Do not merge synonym logic in phase 1.

However:

-   Validity opinions must not contradict synonym records silently.
-   Ideally derive "invalid because synonym" rather than storing both
    independently.

Add integrity checks or warnings when conflicts arise.

------------------------------------------------------------------------

# 8. Migration Strategy

Phase 1: - Create `taxonomic_opinions` - Add partial unique index - Add
synchronization trigger - Insert PoC opinions (e.g., Eurekiidae case)

Phase 2: - Optional refactor toward predicate-based general assertion
model

------------------------------------------------------------------------

# Final Architectural Principle

Separate:

-   Assertions (historical claims)
-   Current accepted classification (derived view)
-   Dataset provenance (SCODA snapshot metadata)

Do not hard-code "truth" into tree structure.

Let tree structure be the materialized result of selected assertions.

------------------------------------------------------------------------

# Summary

Recommended path:

> Implement A' (Option A + structural integrity controls)

This preserves: - Existing queries - SPA compatibility - Incremental
migration safety

While enabling: - Multiple coexisting taxonomic viewpoints - Clear
provenance tracking - Future concept-level modeling expansion

