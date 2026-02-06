# Trilobase as a SCODA
## Reframing Trilobase as a Self-Contained Data Artifact

---

## Purpose of This Document

This document describes **Trilobase** through the lens of **SCODA (Self-Contained Data Artifact)**.

It does **not** replace the technical README or database schema documentation.
Instead, it clarifies:

- What Trilobase *is* as a distributed knowledge object
- What responsibilities it takes (and deliberately avoids)
- How it should be used, extended, and cited

---

## What Trilobase Is (as a SCODA)

**Trilobase is a versioned, authoritative snapshot of trilobite genus-level taxonomy,
distributed as a self-contained data artifact.**

In SCODA terms:

- Trilobase is **not a service**
- Trilobase is **not a continuously synchronized database**
- Trilobase *is* a **reference artifact** representing the state of taxonomic knowledge at a given time

---

## Core Mapping: Trilobase → SCODA

| SCODA Component | Trilobase Implementation |
|----------------|--------------------------|
| Data | SQLite database containing taxonomic tables |
| Identity | Project name + semantic version |
| Semantics | Database schema, rank hierarchy, synonym relations |
| Provenance | Source literature (Jell & Adrain 2002; Adrain 2011) |
| Integrity | Immutable release artifacts; versioned updates |

---

## Immutability and Versioning

Each released version of Trilobase:

- Is treated as **read-only**
- Represents a *curated snapshot* of taxonomic interpretation
- Can be cited, archived, and reproduced

Any modification to the canonical data results in:

- A **new version**
- A **new SCODA artifact**
- An explicit update in provenance

This mirrors how taxonomic opinions evolve through publication,
not through silent mutation.

---

## Local Use and Extension

When a user opens Trilobase locally:

- The base artifact remains immutable
- Local changes are limited to:
  - Notes
  - Annotations
  - Alternative interpretations
  - Links to additional literature

These local extensions:

- Do **not** overwrite canonical taxonomy
- Are not automatically synchronized
- Exist as personal overlays

---

## Multiple Interpretations and "Sensu" Concepts

Taxonomic disagreement is an expected condition.

Trilobase supports this by allowing:

- Multiple taxonomic **concepts** to coexist
- Each concept to be explicitly labeled (e.g., *sensu Adrain, 2011*)
- Each assertion to be traceable to a source reference

The default distributed artifact may select one
**recommended concept set**, while preserving alternatives.

---

## Upgrades and Data Evolution

Updates to Trilobase occur through:

1. Curation and review
2. Generation of a new SCODA artifact
3. Explicit distribution of the new version

Users may choose when (or whether) to upgrade.

There is no implicit synchronization across installations.

---

## What Trilobase Explicitly Does Not Do

As a SCODA, Trilobase intentionally avoids:

- Real-time collaborative editing
- Automatic merge of conflicting interpretations
- Centralized live APIs as the primary interface
- Silent modification of historical data

These are features of *services*, not *artifacts*.

---

## Why This Matters

Treating Trilobase as a SCODA ensures:

- Scientific accountability
- Reproducibility of analyses
- Transparent evolution of taxonomic knowledge
- Clear separation between authoritative data and personal reasoning

In short:

> **Trilobase is not a database you connect to.  
> It is a knowledge object you open.**

---

## Status

This document defines the **conceptual role** of Trilobase within the SCODA framework.

Implementation details, runtime behavior, and contribution workflows
are defined in separate technical documents.
