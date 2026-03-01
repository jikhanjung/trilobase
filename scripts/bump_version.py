#!/usr/bin/env python3
"""
Bump version for trilobase or paleocore package.

Updates the version in:
  - DB artifact_metadata table
  - create_scoda.py paleocore dependency version (when bumping paleocore)

Usage:
  python scripts/bump_version.py trilobase 0.2.0
  python scripts/bump_version.py paleocore 0.1.1
  python scripts/bump_version.py trilobase 0.2.0 --dry-run
"""

import argparse
import os
import re
import shutil
import sqlite3
import sys

from db_path import find_trilobase_db, find_paleocore_db

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(SCRIPT_DIR, '..')

DB_PATHS = {
    'trilobase': find_trilobase_db(),
    'paleocore': find_paleocore_db(),
}

# Files containing hardcoded paleocore dependency version
PALEOCORE_DEP_FILES = [
    os.path.join(SCRIPT_DIR, 'create_scoda.py'),
]

# Files containing ASSERTION_VERSION constant
ASSERTION_VERSION_FILES = [
    os.path.join(SCRIPT_DIR, 'create_assertion_db.py'),
]

VERSION_RE = re.compile(r'^\d+\.\d+\.\d+$')


def get_current_version(db_path):
    """Read current version from artifact_metadata."""
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT value FROM artifact_metadata WHERE key='version'"
    ).fetchone()
    conn.close()
    return row[0] if row else None


def update_db_version(db_path, new_version, dry_run=False):
    """Update version in artifact_metadata table."""
    current = get_current_version(db_path)
    if dry_run:
        print(f"  DB {os.path.basename(db_path)}: {current} → {new_version}")
        return current
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE artifact_metadata SET value=? WHERE key='version'",
        (new_version,)
    )
    conn.commit()
    conn.close()
    print(f"  DB {os.path.basename(db_path)}: {current} → {new_version}")
    return current


def update_assertion_version(new_version, dry_run=False):
    """Update ASSERTION_VERSION constant in create_assertion_db.py."""
    pattern = r'(ASSERTION_VERSION\s*=\s*")(\d+\.\d+\.\d+)(")'
    for fpath in ASSERTION_VERSION_FILES:
        if not os.path.exists(fpath):
            continue
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        matches = list(re.finditer(pattern, content))
        if not matches:
            print(f"  {os.path.basename(fpath)}: no ASSERTION_VERSION found (skipped)")
            continue

        old_version = matches[0].group(2)
        if dry_run:
            print(f"  {os.path.basename(fpath)}: ASSERTION_VERSION {old_version} → {new_version}")
            continue

        new_content = re.sub(pattern, rf'\g<1>{new_version}\3', content)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  {os.path.basename(fpath)}: ASSERTION_VERSION {old_version} → {new_version}")


def update_paleocore_dep_version(new_version, dry_run=False):
    """Update hardcoded paleocore dependency version in create_scoda.py."""
    for fpath in PALEOCORE_DEP_FILES:
        if not os.path.exists(fpath):
            continue
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Match "version": "X.Y.Z" inside paleocore dependency blocks
        pattern = r'("name":\s*"paleocore".*?"version":\s*")(\d+\.\d+\.\d+)(")'
        matches = list(re.finditer(pattern, content, re.DOTALL))
        if not matches:
            print(f"  {os.path.basename(fpath)}: no paleocore version found (skipped)")
            continue

        old_version = matches[0].group(2)
        if dry_run:
            print(f"  {os.path.basename(fpath)}: paleocore dep {old_version} → {new_version} ({len(matches)} occurrence(s))")
            continue

        new_content = re.sub(pattern, rf'\g<1>{new_version}\3', content, flags=re.DOTALL)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  {os.path.basename(fpath)}: paleocore dep {old_version} → {new_version} ({len(matches)} occurrence(s))")


def main():
    parser = argparse.ArgumentParser(
        description='Bump version for trilobase or paleocore package')
    parser.add_argument(
        'package', choices=['trilobase', 'paleocore', 'assertion'],
        help='Package to bump')
    parser.add_argument(
        'version',
        help='New version (e.g. 0.2.0)')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would change without modifying files')
    args = parser.parse_args()

    if not VERSION_RE.match(args.version):
        print(f"Error: Invalid version format '{args.version}' (expected X.Y.Z)", file=sys.stderr)
        sys.exit(1)

    # Assertion target: update script constant only (no canonical DB)
    if args.package == 'assertion':
        # Read current version from the script constant
        fpath = ASSERTION_VERSION_FILES[0]
        current = None
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                m = re.search(r'ASSERTION_VERSION\s*=\s*"(\d+\.\d+\.\d+)"', f.read())
                if m:
                    current = m.group(1)
        if current == args.version:
            print(f"assertion is already at version {args.version}")
            sys.exit(0)

        mode = "DRY RUN" if args.dry_run else "Bumping"
        print(f"=== {mode}: assertion {current} → {args.version} ===")
        print()
        update_assertion_version(args.version, dry_run=args.dry_run)
        print()
        if args.dry_run:
            print("No files were modified (dry run).")
        else:
            print(f"Done. assertion is now at version {args.version}.")
        return

    db_path = os.path.abspath(DB_PATHS[args.package])
    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    current = get_current_version(db_path)
    if current == args.version:
        print(f"{args.package} is already at version {args.version}")
        sys.exit(0)

    mode = "DRY RUN" if args.dry_run else "Bumping"
    print(f"=== {mode}: {args.package} {current} → {args.version} ===")
    print()

    # 1. Update DB version in artifact_metadata
    update_db_version(db_path, args.version, dry_run=args.dry_run)

    # 2. Copy to new versioned filename
    db_dir = os.path.dirname(db_path)
    new_db_path = os.path.join(db_dir, f'{args.package}-{args.version}.db')
    if args.dry_run:
        print(f"  Copy: {os.path.basename(db_path)} → {os.path.basename(new_db_path)}")
    else:
        shutil.copy2(db_path, new_db_path)
        print(f"  Copy: {os.path.basename(db_path)} → {os.path.basename(new_db_path)}")

    # 3. If paleocore, also update dependency version in create_scoda.py
    if args.package == 'paleocore':
        update_paleocore_dep_version(args.version, dry_run=args.dry_run)

    print()
    if args.dry_run:
        print("No files were modified (dry run).")
    else:
        print(f"Done. {args.package} is now at version {args.version}.")
        print("Remember to update the CHANGELOG before releasing.")


if __name__ == '__main__':
    main()
