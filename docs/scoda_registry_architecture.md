# SCODA Registry Architecture
## Dependency Resolution and Distribution Model

---

# 1. Purpose

This document defines how SCODA packages are distributed and how
dependencies are resolved and downloaded automatically.

---

# 2. Design Goals

- Minimal infrastructure cost
- Static hosting compatibility
- Deterministic dependency resolution
- Integrity verification
- Offline cache support

---

# 3. Registry Model

Registry consists of:

1. Package files (.scoda)
2. A static index.json
3. Checksums for verification

No dynamic server is required.

---

# 4. Recommended Hosting Strategy

Phase 1:
- Package files stored in GitHub Releases
- index.json hosted via GitHub Pages

Phase 2 (scaling):
- Object storage (R2/S3/B2)
- CDN optional

---

# 5. index.json Structure

{
  "packages": {
    "paleocore": {
      "0.3.0": {
        "url": "https://example.com/paleocore-0.3.0.scoda",
        "sha256": "...",
        "size": 12345678
      }
    },
    "trilobase": {
      "1.0.0": {
        "url": "https://example.com/trilobase-1.0.0.scoda",
        "sha256": "...",
        "size": 9876543
      }
    }
  }
}

---

# 6. Dependency Resolution Algorithm

Given:
- Package name
- Version constraint (e.g., >=0.3.0,<0.4.0)

Runtime performs:

1. Load index.json
2. List available versions
3. Filter by version constraint
4. Select highest compatible version
5. Check local cache
6. If missing → download
7. Verify sha256
8. Store in cache
9. Mount package

---

# 7. Local Cache Structure

~/.scoda/
  registry_cache/
    paleocore/
      0.3.0/
        paleocore-0.3.0.scoda
    trilobase/
      1.0.0/
        trilobase-1.0.0.scoda

Cache key = (package_name, version)

---

# 8. Locking (Optional but Recommended)

Runtime may generate a lock file:

trilobase-1.0.0.lock

Containing:

{
  "resolved_dependencies": {
    "paleocore": "0.3.2"
  }
}

This ensures reproducibility.

---

# 9. Integrity Verification

- sha256 must match index entry
- Optional future support for digital signatures

---

# 10. Failure Handling

If required dependency cannot be resolved:

- Runtime aborts package loading
- Clear error message returned
- No partial mount allowed

---

# 11. Summary

Registry is:

- Static
- Low-cost
- Deterministic
- Version-controlled
- Runtime-enforced

It supports mandatory dependencies and automatic resolution
without requiring a dedicated backend server.

