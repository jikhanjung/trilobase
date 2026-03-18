#!/usr/bin/env python3
"""Build paleobase meta-package (.scoda).

A meta-package contains no data.db — only manifest.json,
meta_tree.json, and package_bindings.json.

Usage:
  python scripts/build_paleobase_scoda.py
  python scripts/build_paleobase_scoda.py --dry-run
"""

import argparse
import hashlib
import json
import os
import sys
import zipfile
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), '..')
DATA_DIR = os.path.join(ROOT, 'data')
DIST_DIR = os.path.join(ROOT, 'dist')

VERSION = "0.2.0"

DEPENDENCIES = [
    {"name": "paleocore",      "alias": "pc",  "version": ">=0.1.3,<0.2.0", "required": True},
    {"name": "trilobita",      "alias": "tri", "version": ">=0.3.0,<0.4.0", "required": True},
    {"name": "brachiopoda",    "alias": "bra", "version": ">=0.2.0,<0.3.0", "required": True},
    {"name": "graptolithina",  "alias": "gra", "version": ">=0.1.0,<0.2.0", "required": True},
    {"name": "chelicerata",    "alias": "che", "version": ">=0.1.0,<0.2.0", "required": True},
    {"name": "ostracoda",      "alias": "ost", "version": ">=0.1.0,<0.2.0", "required": True},
    {"name": "bryozoa",        "alias": "bry", "version": ">=0.1.0,<0.2.0", "required": True},
    {"name": "coelenterata",   "alias": "coe", "version": ">=0.1.0,<0.2.0", "required": True},
    {"name": "hexapoda",       "alias": "hex", "version": ">=0.1.0,<0.2.0", "required": True},
    {"name": "porifera",       "alias": "por", "version": ">=0.1.0,<0.2.0", "required": True},
    {"name": "echinodermata",  "alias": "ech", "version": ">=0.1.0,<0.2.0", "required": True},
    {"name": "mollusca",       "alias": "mol", "version": ">=0.1.0,<0.2.0", "required": True},
]


def build_manifest():
    """Build the paleobase manifest dict."""
    return {
        "format": "scoda",
        "format_version": "1.0",
        "name": "paleobase",
        "version": VERSION,
        "title": "Paleobase — Treatise-derived invertebrate paleontology bundle",
        "description": (
            "Meta-package integrating trilobita, brachiopoda, graptolithina, "
            "chelicerata, ostracoda into a unified taxonomy space"
        ),
        "kind": "meta-package",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "license": "CC-BY-4.0",
        "authors": [],
        "dependencies": DEPENDENCIES,
        "entry_points": [
            {"node_id": "node:metazoa", "label": "Metazoa", "default_view": "tree"}
        ],
        "meta_tree_file": "meta_tree.json",
        "package_bindings_file": "package_bindings.json",
    }


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_hub_manifest(scoda_path):
    """Generate hub manifest alongside the .scoda file."""
    hub = {
        "hub_manifest_version": "1.0",
        "package_id": "paleobase",
        "version": VERSION,
        "title": "Paleobase — Treatise-derived invertebrate paleontology bundle",
        "kind": "meta-package",
        "license": "CC-BY-4.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dependencies": {d["name"]: d["version"] for d in DEPENDENCIES},
        "filename": os.path.basename(scoda_path),
        "sha256": _sha256(scoda_path),
        "size_bytes": os.path.getsize(scoda_path),
        "scoda_format_version": "1.0",
        "engine_compat": ">=0.2.0",
    }
    out = os.path.join(os.path.dirname(scoda_path), f"paleobase-{VERSION}.manifest.json")
    with open(out, "w") as f:
        json.dump(hub, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return out


def main():
    parser = argparse.ArgumentParser(description="Build paleobase meta-package")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview manifest without creating file")
    parser.add_argument("--output", default=None,
                        help="Output .scoda path")
    args = parser.parse_args()

    meta_tree_path = os.path.join(DATA_DIR, "paleobase_meta_tree.json")
    bindings_path = os.path.join(DATA_DIR, "paleobase_bindings.json")

    for path in (meta_tree_path, bindings_path):
        if not os.path.exists(path):
            print(f"Error: {path} not found", file=sys.stderr)
            sys.exit(1)

    manifest = build_manifest()

    if args.dry_run:
        print("=== DRY RUN ===")
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return

    os.makedirs(DIST_DIR, exist_ok=True)
    output = args.output or os.path.join(DIST_DIR, f"paleobase-{VERSION}.scoda")

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        zf.write(meta_tree_path, "meta_tree.json")
        zf.write(bindings_path, "package_bindings.json")

    size = os.path.getsize(output)
    print(f"Created: {output}")
    print(f"  Size: {size:,} bytes")
    print(f"  Kind: meta-package")
    print(f"  Version: {VERSION}")
    print(f"  Dependencies: {len(DEPENDENCIES)}")

    hub_path = build_hub_manifest(output)
    print(f"  Hub Manifest: {hub_path}")

    # Verify contents
    with zipfile.ZipFile(output, "r") as zf:
        names = zf.namelist()
        print(f"  Contents: {', '.join(names)}")


if __name__ == "__main__":
    main()
