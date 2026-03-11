#!/usr/bin/env python3
"""Parse data/treatise_1959_taxonomy.txt → update data/treatise_1959_taxonomy.json.

Reads the manually curated TXT file and replaces the corresponding
Order entries in the JSON. Orders not covered by TXT are kept from
the existing JSON unchanged.

Usage:
    python scripts/parse_treatise_txt.py [--dry-run]
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TXT_PATH = ROOT / "data" / "treatise_1959_taxonomy.txt"
JSON_PATH = ROOT / "data" / "treatise_1959_taxonomy.json"

# Rank hierarchy (lower number = higher rank)
RANK_ORDER = {
    'class': 0, 'order': 1, 'suborder': 2,
    'superfamily': 3, 'family': 4, 'subfamily': 5, 'genus': 6,
}

# Rank keywords to detect (checked case-insensitively)
RANK_KEYWORDS = [
    ('order',       r'^order\s+'),
    ('suborder',    r'^suborder\s+'),
    ('superfamily', r'^superfamily\s+'),
    ('family',      r'^family\s+'),
    ('subfamily',   r'^subfamily\s+'),
]


def normalize_name(name: str) -> str:
    """Normalize taxon name: first letter uppercase, rest lowercase.

    Only applied to single-word scientific names (no spaces).
    Multi-word placeholder names (e.g. 'Order Uncertain (Trilobita)') are
    left unchanged.
    """
    if ' ' in name or not name:
        return name
    return name[0].upper() + name[1:].lower()


def normalize_node(node: dict) -> dict:
    """Recursively normalize all 'name' fields in a taxonomy node."""
    node = dict(node)
    node['name'] = normalize_name(node['name'])
    if 'children' in node:
        node['children'] = [normalize_node(c) for c in node['children']]
    return node


def parse_author_year(text: str):
    """Extract (author, year) from 'Author, Year [type species]' text."""
    # Strip type species info
    text = re.sub(r'\[.*?\]', '', text).strip().rstrip(';.,')
    if not text:
        return None, None

    # Trailing 4-digit year after comma
    m = re.search(r',\s*(\d{4})\s*$', text)
    if m:
        author = text[:m.start()].strip() or None
        return author, int(m.group(1))

    # "nov." = no year
    if re.search(r'\bnov\.?\b', text, re.IGNORECASE):
        author = re.sub(r',?\s*nov\.?.*$', '', text, flags=re.IGNORECASE).strip() or None
        return author, None

    return text or None, None


def parse_line(raw_line: str):
    """Parse one text line → (rank, name, author, year) or None if unparseable."""
    stripped = raw_line.strip()
    if not stripped:
        return None

    # Special case: "Order and Family UNCERTAIN"
    if re.match(r'^order\s+and\s+family\s+uncertain', stripped, re.IGNORECASE):
        return 'order', 'Order and Family Uncertain (Trilobita)', None, None

    # Special case: "Order UNCERTAIN" (but not "Order and ...")
    if re.match(r'^order\s+uncertain\s*$', stripped, re.IGNORECASE):
        return 'order', 'Order Uncertain (Trilobita)', None, None

    # Skip section headers like "Unrecognizable Genera", "Unrecognizable Asaphid Genera"
    if re.match(r'^unrecognizable\b', stripped, re.IGNORECASE):
        return None

    # Check known rank keywords
    for rank, pattern in RANK_KEYWORDS:
        if re.match(pattern, stripped, re.IGNORECASE):
            rest = re.sub(pattern, '', stripped, count=1, flags=re.IGNORECASE)
            parts = rest.split(None, 1)
            if not parts:
                return None
            name = parts[0]
            author_text = parts[1] if len(parts) > 1 else ''
            author, year = parse_author_year(author_text)
            return rank, name, author, year

    # Genus: optional ? then capital letter + lowercase
    m = re.match(r'^\??([A-Z][a-zA-Z]+)\s*(.*)', stripped)
    if m:
        name = m.group(1)
        author_text = m.group(2)
        author, year = parse_author_year(author_text)
        return 'genus', name, author, year

    return None


def build_tree(txt_path: Path):
    """Parse TXT → nested tree rooted at a virtual class node.

    Returns (list_of_orders, list_of_parse_warnings).
    Uses rank-keyword hierarchy (not indentation) for robustness against
    mixed spaces/tabs.
    """
    root_node = {'rank': 'class', 'name': 'Trilobita', 'children': []}
    # Stack entries: (rank_num, node)
    stack = [(RANK_ORDER['class'], root_node)]

    warnings = []

    with open(txt_path, encoding='utf-8') as f:
        for lineno, raw_line in enumerate(f, 1):
            if not raw_line.strip():
                continue

            result = parse_line(raw_line)
            if result is None:
                warnings.append(f"  Line {lineno:3d}: SKIP  {raw_line.strip()[:70]}")
                continue

            rank, name, author, year = result
            rank_num = RANK_ORDER[rank]

            node = {'rank': rank, 'name': normalize_name(name)}
            if author:
                node['author'] = author
            if year:
                node['year'] = year
            if rank != 'genus':
                node['children'] = []

            # Pop stack until top is a valid parent (lower rank number)
            while len(stack) > 1 and stack[-1][0] >= rank_num:
                stack.pop()

            parent = stack[-1][1]
            parent.setdefault('children', []).append(node)

            if rank != 'genus':
                stack.append((rank_num, node))

    return root_node['children'], warnings


def count_genera(node: dict) -> int:
    if node.get('rank') == 'genus':
        return 1
    return sum(count_genera(c) for c in node.get('children', []))


def summarize(orders: list) -> None:
    for o in orders:
        subs = [c for c in o.get('children', []) if c['rank'] in ('suborder', 'superfamily')]
        fams_direct = [c for c in o.get('children', []) if c['rank'] == 'family']
        all_fams = []

        def collect_fams(node):
            for c in node.get('children', []):
                if c['rank'] == 'family':
                    all_fams.append(c)
                else:
                    collect_fams(c)

        collect_fams(o)
        g = count_genera(o)
        print(f"  Order {o['name']}: {len(all_fams)} families, {g} genera")

        for sub in subs:
            sub_fams = []
            collect_fams_in = lambda node, acc: [
                acc.append(c) or collect_fams_in(c, acc)
                for c in node.get('children', [])
                if c['rank'] in ('family', 'suborder', 'superfamily', 'subfamily') or
                   acc.append(None) is None
            ]

            def get_fams(node):
                result = []
                for c in node.get('children', []):
                    if c['rank'] == 'family':
                        result.append(c)
                    else:
                        result.extend(get_fams(c))
                return result

            sub_fams = get_fams(sub)
            sg = count_genera(sub)
            print(f"    Suborder {sub['name']}: {len(sub_fams)} families, {sg} genera")


def main():
    dry_run = '--dry-run' in sys.argv

    print(f"Parsing {TXT_PATH.name} ...")
    orders, warnings = build_tree(TXT_PATH)

    if warnings:
        print(f"\nParse warnings ({len(warnings)}):")
        for w in warnings:
            print(w)

    top_orders = [n for n in orders if n['rank'] == 'order']
    print(f"\nParsed {len(top_orders)} order(s):")
    summarize(top_orders)

    # Load existing JSON
    with open(JSON_PATH, encoding='utf-8') as f:
        existing = json.load(f)

    existing_orders = existing['taxonomy']['children']
    txt_map = {o['name'].upper(): o for o in top_orders}

    # Merge: replace TXT-covered orders in-place, keep others unchanged
    # Also normalize names in kept (existing) orders
    merged = []
    seen = set()
    replaced = []
    kept = []

    for orig in existing_orders:
        key = orig['name'].upper()
        if key in txt_map:
            merged.append(txt_map[key])
            replaced.append(orig['name'])
        else:
            merged.append(normalize_node(orig))
            kept.append(orig['name'])
        seen.add(key)

    # Append genuinely new orders not in existing JSON
    new_orders = []
    for o in top_orders:
        if o['name'].upper() not in seen:
            merged.append(o)
            new_orders.append(o['name'])

    total_genera = sum(count_genera(o) for o in merged)
    txt_genera = sum(count_genera(o) for o in top_orders)

    print(f"\nMerge summary:")
    print(f"  Replaced from TXT : {replaced}")
    print(f"  Kept from JSON    : {kept}")
    if new_orders:
        print(f"  New (TXT only)    : {new_orders}")
    print(f"  TXT genera parsed : {txt_genera}")
    print(f"  Total genera      : {total_genera}")

    existing['taxonomy']['children'] = merged

    if dry_run:
        print("\n[dry-run] JSON not written.")
        # Print first replaced order structure for inspection
        if replaced:
            sample = next(o for o in merged if o['name'].upper() == replaced[0].upper())
            print(f"\nSample ({replaced[0]}) — first 3 children:")
            for c in sample.get('children', [])[:3]:
                print(f"  {json.dumps(c, ensure_ascii=False)[:120]}")
        return

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"\nWritten: {JSON_PATH}")


if __name__ == '__main__':
    main()
