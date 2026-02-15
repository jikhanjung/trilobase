#!/usr/bin/env python3
"""
Populate countries.code with ISO 3166-1 alpha-2 codes.

Maps 142 country names from paleocore.db countries table to ISO codes.
Uses pycountry for automatic matching + manual corrections for ambiguous names.

Usage:
  python scripts/populate_iso_codes.py              # apply to paleocore.db
  python scripts/populate_iso_codes.py --dry-run    # preview without changes
  python scripts/populate_iso_codes.py --report     # detailed mapping report
"""

import argparse
import os
import sqlite3
import sys

try:
    import pycountry
except ImportError:
    print("Error: pycountry is required. Install with: pip install pycountry",
          file=sys.stderr)
    sys.exit(1)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'paleocore.db')

# ── Manual mapping for names that pycountry can't resolve ──────────────────
# Includes: sub-national regions mapped to parent country ISO,
# alternate names, historical names, and directional prefixes.

MANUAL_MAP = {
    # === Real countries with alternate names ===
    'Burma': 'MM',
    'Czech Republic': 'CZ',
    'Korea': 'KR',
    'Luxemburg': 'LU',
    'North Korea': 'KP',
    'North Vietnam': 'VN',
    'South Korea': 'KR',
    'Tadzikhistan': 'TJ',
    'USA': 'US',

    # === Sub-national regions → parent country ISO ===
    # United States
    'Alaska': 'US',
    'E Alaska': 'US',
    'Iowa': 'US',
    'Massachusetts': 'US',
    'Missouri': 'US',
    'Pennsylvania': 'US',
    'Tennessee': 'US',
    'Texas': 'US',

    # Canada
    'New Brunswick': 'CA',
    'NW Canada': 'CA',
    'Ontario': 'CA',

    # United Kingdom
    'Devon': 'GB',
    'England': 'GB',
    'N Ireland': 'GB',
    'N Wales': 'GB',
    'NW Scotland': 'GB',
    'S Wales': 'GB',
    'Scotland': 'GB',
    'SW Wales': 'GB',
    'Wales': 'GB',

    # France
    'Montagne Noire': 'FR',
    'S France': 'FR',
    'SW France': 'FR',
    'W France': 'FR',

    # Germany
    'Bavaria': 'DE',
    'E Germany': 'DE',
    'Eifel Germany': 'DE',
    'N Germany': 'DE',
    'W Germany': 'DE',

    # Spain
    'N Spain': 'ES',
    'NE Spain': 'ES',

    # Russia
    'Arctic Russia': 'RU',
    'E Urals': 'RU',
    'E Yakutia': 'RU',
    'Gorny Altay': 'RU',
    'N Russia': 'RU',
    'NE Russia': 'RU',
    'NW Russian Platform': 'RU',
    'Novaya Zemlya': 'RU',
    'Yakutia': 'RU',
    'NE Yakutia': 'RU',

    # Kazakhstan
    'Central Kazakhstan': 'KZ',
    'E Kazakhstan': 'KZ',
    'N Kazakhstan': 'KZ',
    'NE Kazakhstan': 'KZ',
    'S Kazakhstan': 'KZ',

    # China
    'Guangxi': 'CN',
    'Henan': 'CN',
    'Sichuan': 'CN',

    # Australia
    'Australian Capital Territory': 'AU',
    'South Australia': 'AU',
    'Western Australia': 'AU',

    # Morocco
    'Central Morocco': 'MA',
    'NW Morocco': 'MA',
    'S Morocco': 'MA',
    'SE Morocco': 'MA',
    'W Morocco': 'MA',

    # Iran
    'Eastern Iran': 'IR',
    'SE Iran': 'IR',

    # Japan
    'NE Japan': 'JP',

    # Mongolia
    'NW Mongolia': 'MN',
    'W Mongolia': 'MN',

    # Belgium
    'E Belgium': 'BE',
    'W Belgium': 'BE',

    # Greenland (Danish territory)
    'E Greenland': 'GL',
    'Greenland': 'GL',
    'N Greenland': 'GL',
    'NW Greenland': 'GL',

    # Korea (sub-regions)
    'NW Korea': 'KP',

    # Algeria
    'SW Algeria': 'DZ',

    # Argentina
    'NW Argentina': 'AR',

    # Mexico
    'NW Mexico': 'MX',

    # Turkey
    'SE Turkey': 'TR',
    'Turkey': 'TR',

    # Thailand
    'S Thailand': 'TH',

    # Malaysia
    'NW Malaya': 'MY',
    'W Malaysia': 'MY',

    # Sweden
    'Gotland': 'SE',

    # Norway (Svalbard)
    'Spitsbergen': 'NO',

    # Indonesia
    'Sumatra': 'ID',
    'Timor': 'TL',

    # Afghanistan
    'Central Afghanistan': 'AF',

    # Estonia
    'N Estonia': 'EE',

    # === Unmappable (not sovereign states, kept as NULL) ===
    'Antarctica': None,
    'Central Asia': None,
    'Kashmir': None,
    'Tien-Shan': None,
    'Turkestan': None,
}


def try_pycountry(name):
    """Try to match a country name using pycountry."""
    # Exact match
    try:
        c = pycountry.countries.lookup(name)
        return c.alpha_2
    except LookupError:
        pass

    # Fuzzy search (single unambiguous result only)
    try:
        results = pycountry.countries.search_fuzzy(name)
        if len(results) == 1:
            return results[0].alpha_2
    except LookupError:
        pass

    return None


def build_mapping(countries):
    """Build ISO code mapping for all countries.

    Returns: dict of {country_id: (iso_code_or_None, method)}
    """
    mapping = {}
    for cid, name in countries:
        # Check manual mapping first
        if name in MANUAL_MAP:
            code = MANUAL_MAP[name]
            method = 'manual' if code else 'unmappable'
            mapping[cid] = (code, method)
            continue

        # Try pycountry
        code = try_pycountry(name)
        if code:
            mapping[cid] = (code, 'pycountry')
            continue

        # Not found
        mapping[cid] = (None, 'unmatched')

    return mapping


def report(db_path):
    """Print detailed mapping report."""
    conn = sqlite3.connect(db_path)
    countries = conn.execute(
        "SELECT id, name FROM countries ORDER BY name").fetchall()
    conn.close()

    mapping = build_mapping(countries)

    # Group by method
    by_method = {}
    for cid, name in countries:
        code, method = mapping[cid]
        by_method.setdefault(method, []).append((cid, name, code))

    print(f"=== ISO Code Mapping Report ===\n")
    print(f"Total countries: {len(countries)}")

    mapped = sum(1 for _, (code, _) in mapping.items() if code is not None)
    unmapped = sum(1 for _, (code, _) in mapping.items() if code is None)
    print(f"Mapped:   {mapped} ({mapped*100/len(countries):.1f}%)")
    print(f"Unmapped: {unmapped}")

    for method in ['pycountry', 'manual', 'unmappable', 'unmatched']:
        entries = by_method.get(method, [])
        if entries:
            print(f"\n--- {method} ({len(entries)}) ---")
            for cid, name, code in entries:
                print(f"  {name:40s} → {code or 'NULL'}")

    # Validate: check for duplicate ISO codes
    print(f"\n--- ISO Code Distribution ---")
    code_counts = {}
    for cid, (code, _) in mapping.items():
        if code:
            code_counts[code] = code_counts.get(code, 0) + 1
    multi = {c: n for c, n in code_counts.items() if n > 1}
    if multi:
        print(f"  Codes used by multiple countries (expected for sub-regions):")
        for code, count in sorted(multi.items()):
            names = [n for _, n in countries if mapping[_]
                     [0] == code for _ in [_]]
            # Re-do properly
            code_names = [n for cid, n in countries if mapping[cid][0] == code]
            print(f"    {code}: {count} entries — {', '.join(code_names)}")
    else:
        print("  All codes unique.")


def apply(db_path, dry_run=False):
    """Apply ISO codes to countries.code."""
    conn = sqlite3.connect(db_path)
    countries = conn.execute(
        "SELECT id, name FROM countries ORDER BY name").fetchall()

    mapping = build_mapping(countries)

    mapped = sum(1 for _, (code, _) in mapping.items() if code is not None)
    unmapped_count = sum(
        1 for _, (code, method) in mapping.items()
        if code is None and method == 'unmappable')
    unmatched = [
        (cid, name)
        for cid, name in countries
        if mapping[cid][1] == 'unmatched'
    ]

    if unmatched:
        print(f"ERROR: {len(unmatched)} unmatched countries:", file=sys.stderr)
        for cid, name in unmatched:
            print(f"  id={cid}: {name}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if dry_run:
        print(f"=== DRY RUN ===\n")
        print(f"Would update {mapped} countries with ISO codes")
        print(f"Would leave {unmapped_count} as NULL (unmappable)")
        for cid, name in countries:
            code, method = mapping[cid]
            print(f"  [{method:10s}] {name:40s} → {code or 'NULL'}")
        conn.close()
        return

    # Apply updates
    updated = 0
    for cid, (code, method) in mapping.items():
        if code is not None:
            conn.execute(
                "UPDATE countries SET code = ? WHERE id = ?",
                (code, cid))
            updated += 1

    conn.commit()

    # Verify
    result = conn.execute(
        "SELECT COUNT(*) FROM countries WHERE code IS NOT NULL"
    ).fetchone()[0]
    null_count = conn.execute(
        "SELECT COUNT(*) FROM countries WHERE code IS NULL"
    ).fetchone()[0]

    print(f"Updated {updated} countries with ISO codes")
    print(f"  code IS NOT NULL: {result}")
    print(f"  code IS NULL:     {null_count} (unmappable)")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Populate countries.code with ISO 3166-1 alpha-2 codes')
    parser.add_argument(
        '--db', default=DB_PATH,
        help='Path to paleocore.db')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Preview without applying changes')
    parser.add_argument(
        '--report', action='store_true',
        help='Print detailed mapping report')
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    if args.report:
        report(db_path)
    else:
        apply(db_path, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
