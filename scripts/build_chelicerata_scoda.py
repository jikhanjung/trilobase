#!/usr/bin/env python3
"""Create a .scoda package from the chelicerata DB.

Usage:
  python scripts/build_chelicerata_scoda.py
  python scripts/build_chelicerata_scoda.py --dry-run
"""

import argparse
import glob
import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

from scoda_engine.scoda_package import ScodaPackage, _sha256_file
from scoda_engine_core import validate_db

ROOT = os.path.join(os.path.dirname(__file__), '..')
DB_DIR = os.path.join(ROOT, 'db')
DEFAULT_OUTPUT_DIR = os.path.join(ROOT, 'dist')

_CHELICERATA_RE = re.compile(r'^chelicerata-(\d+\.\d+\.\d+)\.db$')


def find_chelicerata_db():
    candidates = glob.glob(os.path.join(DB_DIR, 'chelicerata-*.db'))
    versioned = []
    for path in candidates:
        m = _CHELICERATA_RE.search(os.path.basename(path))
        if m:
            parts = tuple(int(x) for x in m.group(1).split('.'))
            versioned.append((parts, path))
    if not versioned:
        raise FileNotFoundError("No chelicerata-*.db found in db/")
    versioned.sort()
    return os.path.abspath(versioned[-1][1])


def _read_version(db_path):
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT value FROM artifact_metadata WHERE key='version'").fetchone()
        return row[0] if row else '0.0.0'
    finally:
        conn.close()


def _read_db_metadata(db_path):
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT key, value FROM artifact_metadata").fetchall()
        return dict(rows)
    finally:
        conn.close()


def _sha256_scoda(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_hub_manifest(scoda_path, db_path):
    meta = _read_db_metadata(db_path)
    package_id = meta.get('artifact_id', 'chelicerata')
    version = meta.get('version', '0.0.0')

    provenance = []
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT citation FROM provenance WHERE citation IS NOT NULL").fetchall()
        provenance = [r[0] for r in rows]
    finally:
        conn.close()

    manifest = {
        "hub_manifest_version": "1.0",
        "package_id": package_id,
        "version": version,
        "title": meta.get('name', '') + ' - ' + meta.get('description', ''),
        "description": meta.get('description', ''),
        "license": meta.get('license', 'CC-BY-4.0'),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance,
        "dependencies": {},
        "filename": os.path.basename(scoda_path),
        "sha256": _sha256_scoda(scoda_path),
        "size_bytes": os.path.getsize(scoda_path),
        "scoda_format_version": "1.0",
        "engine_compat": ">=0.1.0",
    }

    out_path = os.path.join(os.path.dirname(scoda_path), f"{package_id}-{version}.manifest.json")
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"  Hub Manifest: {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description='Create a .scoda package from the chelicerata DB')
    parser.add_argument('--db', default=None, help='Path to chelicerata DB')
    parser.add_argument('--output', default=None, help='Output .scoda file path')
    parser.add_argument('--dry-run', action='store_true', help='Preview without creating')
    args = parser.parse_args()

    db_path = os.path.abspath(args.db) if args.db else find_chelicerata_db()
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        version = _read_version(db_path)
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        output_path = os.path.abspath(
            os.path.join(DEFAULT_OUTPUT_DIR, f'chelicerata-{version}.scoda'))

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        print("Run 'python scripts/build_chelicerata_db.py' first.", file=sys.stderr)
        sys.exit(1)

    # Validate
    errors, warnings = validate_db(db_path)
    for w in warnings:
        print(f"  WARNING: {w}")
    for e in errors:
        print(f"  ERROR: {e}", file=sys.stderr)
    if errors:
        print(f"\nValidation failed: {len(errors)} error(s)", file=sys.stderr)
        sys.exit(1)
    print(f"Validation: OK ({len(warnings)} warning(s))")

    if args.dry_run:
        meta = _read_db_metadata(db_path)
        print("=== DRY RUN ===")
        print(f"Source DB:    {db_path}")
        print(f"DB size:      {os.path.getsize(db_path):,} bytes")
        print(f"Output:       {output_path}")
        print(f"Package:      {meta.get('artifact_id')} v{meta.get('version')}")
        return

    # No dependencies (no PaleoCore)
    metadata = {"dependencies": []}

    result = ScodaPackage.create(db_path, output_path, metadata=metadata)
    size = os.path.getsize(result)

    print(f"Created: {result}")
    print(f"  Size: {size:,} bytes ({size / 1024 / 1024:.1f} MB)")

    # Hub Manifest
    generate_hub_manifest(result, db_path)

    # Verify
    with ScodaPackage(result) as pkg:
        print(f"  Format: {pkg.manifest.get('format')} v{pkg.manifest.get('format_version')}")
        print(f"  Name: {pkg.name}")
        print(f"  Version: {pkg.version}")
        print(f"  Records: {pkg.record_count}")
        if pkg.verify_checksum():
            print(f"  Checksum: OK")
        else:
            print(f"  Checksum: MISMATCH!", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
