#!/usr/bin/env python3
"""Create a .scoda package from the trilobita DB.

Usage:
  python scripts/build_trilobita_scoda.py
  python scripts/build_trilobita_scoda.py --dry-run
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

from scoda_engine.scoda_package import ScodaPackage, _sha256_file
from scoda_engine_core import validate_db

from db_path import find_trilobita_db

ROOT = os.path.join(os.path.dirname(__file__), '..')
DEFAULT_DB = find_trilobita_db()
DEFAULT_OUTPUT_DIR = os.path.join(ROOT, 'dist')


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
    package_id = meta.get('artifact_id', 'trilobita')
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
        "dependencies": {
            "paleocore": ">=0.1.1,<0.2.0"
        },
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
    parser = argparse.ArgumentParser(
        description='Create a .scoda package from the assertion-centric test DB')
    parser.add_argument(
        '--db', default=DEFAULT_DB,
        help='Path to assertion DB (default: latest db/trilobita-*.db)')
    parser.add_argument(
        '--output', default=None,
        help='Output .scoda file path')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Preview manifest without creating file')
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        version = _read_version(db_path)
        output_path = os.path.abspath(
            os.path.join(DEFAULT_OUTPUT_DIR, f'trilobita-{version}.scoda'))

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        print("Run 'python scripts/build_trilobita_db.py' first.", file=sys.stderr)
        sys.exit(1)

    # Validate manifest
    errors, warnings = validate_db(db_path)
    for w in warnings:
        print(f"  WARNING: {w}")
    for e in errors:
        print(f"  ERROR: {e}", file=sys.stderr)
    if errors:
        print(f"\nManifest validation failed: {len(errors)} error(s)", file=sys.stderr)
        sys.exit(1)
    print(f"Manifest validation: OK ({len(warnings)} warning(s))")

    if args.dry_run:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT key, value FROM artifact_metadata")
        db_meta = {row['key']: row['value'] for row in cursor.fetchall()}

        scoda_meta_tables = {'artifact_metadata', 'provenance', 'schema_descriptions',
                             'ui_display_intent', 'ui_queries', 'ui_manifest'}
        all_tables = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        record_count = 0
        for (table_name,) in all_tables:
            if table_name not in scoda_meta_tables and not table_name.startswith('sqlite_'):
                cnt = cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]").fetchone()[0]
                record_count += cnt
        conn.close()

        checksum = _sha256_file(db_path)
        manifest = {
            "format": "scoda",
            "format_version": "1.0",
            "name": db_meta.get('artifact_id', 'trilobita'),
            "version": db_meta.get('version', '0.1.0'),
            "title": db_meta.get('name', '') + ' - ' + db_meta.get('description', ''),
            "description": db_meta.get('description', ''),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "license": db_meta.get('license', 'CC-BY-4.0'),
            "data_file": "data.db",
            "record_count": record_count,
            "data_checksum_sha256": checksum,
            "dependencies": [{"name": "paleocore", "alias": "pc", "version": ">=0.1.1,<0.2.0"}],
        }

        print("=== DRY RUN ===")
        print(f"Source DB:    {db_path}")
        print(f"DB size:      {os.path.getsize(db_path):,} bytes")
        print(f"Output:       {output_path}")
        print()
        print("manifest.json:")
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return

    # PaleoCore dependency for geography/stratigraphy (pc.* tables)
    metadata = {
        "dependencies": [{
            "name": "paleocore",
            "alias": "pc",
            "version": ">=0.1.1,<0.2.0",
            "file": "paleocore.scoda",
            "required": True,
            "description": "Shared paleontological infrastructure (geography, stratigraphy)"
        }]
    }

    # Include CHANGELOG if exists
    extra_assets = {}
    changelog_path = os.path.join(ROOT, 'CHANGELOG.md')
    if os.path.isfile(changelog_path):
        extra_assets['CHANGELOG.md'] = changelog_path

    result = ScodaPackage.create(db_path, output_path, metadata=metadata,
                                 extra_assets=extra_assets if extra_assets else None)
    size = os.path.getsize(result)

    print(f"Created: {result}")
    print(f"  Size: {size:,} bytes ({size / 1024 / 1024:.1f} MB)")

    # Generate Hub Manifest
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
