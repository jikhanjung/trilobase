#!/usr/bin/env python3
"""
Create a .scoda package from paleocore.db

Usage:
  python scripts/create_paleocore_scoda.py              # create paleocore.scoda
  python scripts/create_paleocore_scoda.py --dry-run    # preview manifest without creating file
  python scripts/create_paleocore_scoda.py --output out.scoda  # custom output path
"""

import argparse
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scoda_engine.scoda_package import ScodaPackage, _sha256_file
from validate_manifest import validate_db

DEFAULT_DB = os.path.join(os.path.dirname(__file__), '..', 'db', 'paleocore.db')
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'dist', 'paleocore.scoda')


def main():
    parser = argparse.ArgumentParser(
        description='Create a .scoda package from paleocore.db')
    parser.add_argument(
        '--db', default=DEFAULT_DB,
        help='Path to source SQLite database (default: paleocore.db)')
    parser.add_argument(
        '--output', default=DEFAULT_OUTPUT,
        help='Output .scoda file path (default: paleocore.scoda)')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Preview manifest without creating file')
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    output_path = os.path.abspath(args.output)

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    # Validate manifest before packaging
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
        import sqlite3
        from datetime import datetime, timezone

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT key, value FROM artifact_metadata")
        db_meta = {row['key']: row['value'] for row in cursor.fetchall()}

        # Count records: sum all non-SCODA-metadata tables
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
            "name": db_meta.get('artifact_id', 'paleocore'),
            "version": db_meta.get('version', '0.3.0'),
            "title": db_meta.get('name', 'PaleoCore') + ' - ' + db_meta.get('description', ''),
            "description": db_meta.get('description', ''),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "license": db_meta.get('license', 'CC-BY-4.0'),
            "authors": ["Correlates of War Project", "International Commission on Stratigraphy"],
            "data_file": "data.db",
            "record_count": record_count,
            "data_checksum_sha256": checksum,
        }

        print("=== DRY RUN (no file will be created) ===")
        print()
        print(f"Source DB:    {db_path}")
        print(f"DB size:      {os.path.getsize(db_path):,} bytes")
        print(f"Output:       {output_path}")
        print()
        print("manifest.json:")
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return

    # PaleoCore-specific metadata override
    metadata = {
        "authors": ["Correlates of War Project", "International Commission on Stratigraphy"],
    }

    result = ScodaPackage.create(db_path, output_path, metadata=metadata)
    size = os.path.getsize(result)

    print(f"Created: {result}")
    print(f"  Size: {size:,} bytes ({size / 1024:.0f} KB)")

    # Verify by opening
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
