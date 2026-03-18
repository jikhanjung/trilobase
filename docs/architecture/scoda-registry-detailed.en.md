# SCODA Registry & Dependency Distribution — Detailed Design

This document provides the detailed technical specification for the SCODA registry system, including the `index.json` schema, resolver pseudocode, GitHub Releases + Pages automation, and lockfile specification.

---

## Goals

- Manage SCODA packages with **required dependencies** using semver ranges
- Runtime automatically resolves, downloads, verifies integrity, and caches packages
- Lockfile support for reproducibility

## Assumptions

- Packages are `.scoda` (ZIP) single files and immutable snapshots
- Registry is composed of **static files** — no backend server required
- Package files are distributed via **GitHub Releases** (or object storage later)
- Registry index is hosted via **GitHub Pages**

---

## Registry Components

1. `index.json` (static) — package/version/URL/integrity metadata
2. `.scoda` files — actual archives (can be large)
3. (Optional) `index.json.sig` — index signature (future)

Recommended URL structure:

- Index: `https://<org>.github.io/scoda-registry/index.json`
- Artifact: GitHub Releases asset URL (versioned `.scoda`, `checksums.sha256`)

---

## index.json Schema

### Design Principles

- A **single static JSON** provides all information the resolver needs
- "latest" is a convenience — **resolver uses semver range**
- Integrity requires at minimum `sha256`
- Core resolver fields: `name`, `version`, `url`, `sha256`, `size`, (optional) `published_at`

---

## Resolution Algorithm

Given a package name and version constraint (e.g., `>=0.3.0,<0.4.0`):

1. Load `index.json`
2. List available versions for the package
3. Filter by version constraint
4. Select highest compatible version
5. Check local cache
6. If missing → download
7. Verify sha256
8. Store in cache
9. Mount package

---

## Local Cache Structure

```
~/.scoda/
  registry_cache/
    paleocore/
      0.3.0/
        paleocore-0.3.0.scoda
    trilobase/
      1.0.0/
        trilobita-1.0.0.scoda
```

Cache key = (package_name, version)

---

## Lockfile (Optional but Recommended)

A lock file ensures reproducibility:

```json
{
  "resolved_dependencies": {
    "paleocore": "0.3.2"
  }
}
```

---

## Failure Handling

- If a required dependency cannot be resolved: runtime aborts package loading
- Clear error message returned
- No partial mount allowed

!!! note "Korean version"
    The full detailed specification with pseudocode is available in the [Korean version](scoda-registry-detailed.md) of this page.
