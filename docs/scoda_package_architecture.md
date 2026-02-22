# SCODA Package Architecture
## PaleoCore & Trilobase Concept and Dependency Model

---

# 1. Overview

This document defines the conceptual separation between:

- PaleoCore (stratigraphic & geographic registry package)
- Trilobase (taxonomy-focused package)

Both are distributed as independent SCODA packages.

Dependency between them is mandatory and versioned.

---

# 2. SCODA Package Definition

A SCODA package is:

- A versioned, immutable snapshot artifact (.scoda file)
- A ZIP container including:
  - data.db — SQLite database
  - manifest.json — package metadata (includes `data_checksum_sha256` for integrity verification)
  - mcp_tools.json (optional) — MCP tool definitions
  - assets/ (optional) — reference SPA, images, etc.
  - CHANGELOG.md (optional) — version history
- Designed for distribution, caching, and reproducibility

SCODA runtime is responsible for:
- Loading packages
- Resolving dependencies
- Verifying integrity
- Managing cache

---

# 3. PaleoCore Package

## 3.1 Purpose

PaleoCore is a foundational registry package providing:

- Lithostratigraphy
- Chronostratigraphy (ICS-based)
- Geographical regions
- Absolute age data
- Provenance metadata

It is not a perfect global authority DB.
It is a structured, provenance-aware registry.

## 3.2 Responsibilities

- Maintain structural consistency (rank, hierarchy, strat_type)
- Preserve provenance for all imported data
- Allow ambiguity and multiple sources
- Remain independent from any specific fossil group

## 3.3 Conceptual Role

PaleoCore = Infrastructure layer

It is shared by:
- Trilobase
- Future taxon databases
- Occurrence-based packages

---

# 4. Trilobase Package

## 4.1 Purpose

Trilobase is a taxonomy-centered SCODA package containing:

- Taxon registry (genus/species hierarchy)
- Classification structure
- Literature provenance
- Optional occurrences/media

## 4.2 Design Principle

Trilobase does NOT duplicate stratigraphic or geographic data.
It references PaleoCore logically.

---

# 5. Dependency Model

## 5.1 Nature of Dependency

Trilobase requires PaleoCore.

This is a REQUIRED dependency.

Without PaleoCore, Trilobase cannot function correctly for:
- Stratigraphic filtering
- Geographic grouping
- Time-based analysis

## 5.2 Manifest Example

### PaleoCore

```json
{
  "name": "paleocore",
  "version": "0.1.1",
  "dependencies": []
}
```

### Trilobase

```json
{
  "name": "trilobase",
  "version": "0.2.1",
  "dependencies": [
    {
      "name": "paleocore",
      "alias": "pc",
      "version": ">=0.1.1,<0.2.0",
      "file": "paleocore.scoda",
      "required": true,
      "description": "Shared paleontological infrastructure (geography, stratigraphy)"
    }
  ]
}
```

## 5.3 Version Semantics

- Semantic versioning (MAJOR.MINOR.PATCH)
- Version range must be respected
- Runtime selects highest compatible version
- Incompatible versions block package loading

---

# 6. Runtime Behavior

When loading Trilobase:

1. Read manifest
2. Detect dependency on PaleoCore
3. Resolve version constraint
4. Verify availability locally
5. If missing → auto-download
6. Verify checksum
7. Mount both packages
8. Enable cross-package logical resolution

---

# 7. Logical Foreign Keys

Cross-package references are:

- Logical (not SQLite-enforced)
- Validated by runtime
- Namespace-aware

Example:

Trilobase.strat_unit_id → PaleoCore.strat_unit.id

---

# 8. Architectural Summary

PaleoCore = shared registry infrastructure  
Trilobase = taxonomic domain package  

Dependency is:
- Required
- Versioned
- Automatically resolved
- Runtime-enforced

