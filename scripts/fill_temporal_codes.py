#!/usr/bin/env python3
"""
Auto-fill temporal_code for valid genera that have extractable codes in raw_entry.

85 valid genera are missing temporal_code. Of these, 84 have temporal codes
embedded in their raw_entry text that were missed during initial parsing.
Only 1 (Dignagnostus) truly has no temporal code.

Patterns handled:
  - Standard:    "; UCAM."
  - No semicolon: "INDET. LCAM." or "INDET.; LCAM."
  - Question mark: "?MDEV."
  - Trailing comma: "UCAM,"
  - Compound:     "USIL/LDEV."
  - Brackets:     "UCAM, [j.s.s. ...]"
  - With space:   "UCAM ." or "LCAM ."

Idempotent. Usage:
    python scripts/fill_temporal_codes.py [--dry-run]
"""

import argparse
import re
import sqlite3
import sys

DB_PATH = 'db/trilobase.db'

# All valid temporal codes (from existing data)
VALID_CODES = {
    'CAM', 'LCAM', 'MCAM', 'UCAM', 'MUCAM', 'LMCAM',
    'ORD', 'LORD', 'MORD', 'UORD', 'LMORD', 'MUORD',
    'SIL', 'LSIL', 'USIL', 'LUSIL',
    'DEV', 'LDEV', 'MDEV', 'UDEV', 'LMDEV', 'MUDEV',
    'MISS', 'PENN',
    'PERM', 'LPERM', 'UPERM',
}

# Regex to extract temporal code(s) from raw_entry tail
# Handles: UCAM, ?MDEV, USIL/LDEV, ORD?, UCAM/LORD
CODE_PATTERN = re.compile(
    r'[;.]\s*'               # preceded by ; or .
    r'\??'                    # optional leading ?
    r'([A-Z/]+)'             # one or more codes separated by /
    r'\??'                    # optional trailing ?
    r'\s*[.,]?\s*'           # optional trailing . or ,
    r'(?:\[.*\]\.?)?\s*$'    # optional bracketed text (with trailing .) + end
)

# Fallback: code at end without semicolon (e.g., "INDET. LCAM.")
FALLBACK_PATTERN = re.compile(
    r'\s+'
    r'\??'
    r'([A-Z/]+)'
    r'\??'
    r'\s*[.,]?\s*'
    r'(?:\[.*\]\.?)?\s*$'
)


def extract_temporal_code(raw_entry):
    """Extract temporal code from raw_entry string.

    Returns (code, method) tuple. method is 'standard' or 'fallback'.
    Returns (None, None) if no code found.
    """
    if not raw_entry:
        return None, None

    # Try standard pattern first (preceded by ; or .)
    m = CODE_PATTERN.search(raw_entry)
    if m:
        candidate = m.group(1)
        # Validate: all parts must be known codes
        parts = candidate.split('/')
        if all(p in VALID_CODES for p in parts):
            return candidate, 'standard'

    # Fallback: look for code at end preceded by space
    m = FALLBACK_PATTERN.search(raw_entry)
    if m:
        candidate = m.group(1)
        parts = candidate.split('/')
        if all(p in VALID_CODES for p in parts):
            return candidate, 'fallback'

    return None, None


def main():
    parser = argparse.ArgumentParser(
        description='Auto-fill temporal_code for valid genera from raw_entry')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without modifying DB')
    args = parser.parse_args()
    dry_run = args.dry_run

    if dry_run:
        print("=== DRY RUN MODE ===\n")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        rows = conn.execute(
            "SELECT id, name, raw_entry FROM taxonomic_ranks "
            "WHERE rank = 'Genus' AND is_valid = 1 "
            "AND (temporal_code IS NULL OR temporal_code = '') "
            "ORDER BY id"
        ).fetchall()

        print(f"Found {len(rows)} valid genera without temporal_code\n")

        updated = 0
        skipped = []

        for row_id, name, raw_entry in rows:
            code, method = extract_temporal_code(raw_entry)
            if code:
                print(f"  {name} (id={row_id}): {code}  [{method}]")
                if not dry_run:
                    conn.execute(
                        "UPDATE taxonomic_ranks SET temporal_code = ? WHERE id = ?",
                        (code, row_id)
                    )
                updated += 1
            else:
                skipped.append((row_id, name, raw_entry))

        if not dry_run:
            conn.commit()

        print(f"\nUpdated: {updated}")
        print(f"Skipped: {len(skipped)}")

        if skipped:
            print("\nSkipped entries (no extractable code):")
            for row_id, name, raw_entry in skipped:
                print(f"  {name} (id={row_id})")
                print(f"    raw: {raw_entry}")

        if not dry_run:
            # Verify
            remaining = conn.execute(
                "SELECT COUNT(*) FROM taxonomic_ranks "
                "WHERE rank = 'Genus' AND is_valid = 1 "
                "AND (temporal_code IS NULL OR temporal_code = '')"
            ).fetchone()[0]
            print(f"\nVerification: {remaining} genera still missing temporal_code")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
