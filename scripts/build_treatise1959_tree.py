#!/usr/bin/env python3
"""
Build the complete 1959 Treatise taxonomy tree by integrating:
1. Higher taxonomy from the outline (treatise_1959_taxonomy.json)
2. OCR-extracted genus names (treatise_1959_genera_ocr.json)

Cleans OCR artifacts, maps genera to families by page ranges,
and produces the final tree JSON.
"""

import json
import re
from collections import defaultdict


def load_data():
    with open('data/treatise_1959_taxonomy.json') as f:
        taxonomy = json.load(f)
    with open('data/treatise_1959_genera_ocr.json') as f:
        ocr = json.load(f)
    return taxonomy, ocr


def clean_genus_name(name):
    """Fix common OCR artifacts in genus names."""
    # Remove leading/trailing junk
    name = name.strip()
    # Fix common OCR substitutions
    name = re.sub(r'[|!]', 'l', name)  # |/! -> l
    name = re.sub(r'0(?=[a-z])', 'O', name)  # leading 0 -> O
    return name


def clean_author(author):
    """Normalize OCR-garbled author names."""
    # Common OCR errors in author names
    fixes = {
        'Howerr': 'HOWELL', 'Hower.': 'HOWELL', 'Howei.': 'HOWELL',
        'Howe ect': 'HOWELL', 'Howett': 'HOWELL', 'Howeit': 'HOWELL',
        'Howerx': 'HOWELL', 'Elowen.': 'HOWELL',
        'JarKet': 'JAEKEL', 'JaEKer': 'JAEKEL', 'Jaecer': 'JAEKEL',
        'Kosayasut': 'KOBAYASHI', 'Kowavasnt': 'KOBAYASHI',
        'Kogavasti': 'KOBAYASHI', 'Kosayaset': 'KOBAYASHI',
        'Kosayasni': 'KOBAYASHI', 'Kosarasut': 'KOBAYASHI',
        'Kopayasoi': 'KOBAYASHI', 'Kosayasit': 'KOBAYASHI',
        'Kousayasai': 'KOBAYASHI', 'Robayashi': 'KOBAYASHI',
        'Wesrracaro': 'WESTERGARD', 'WitreHocse': 'WHITEHOUSE',
        'Wrorntovss': 'WHITEHOUSE', 'Warrenouse': 'WHITEHOUSE',
        'Wairenouse': 'WHITEHOUSE',
        'Lermeonrova': 'LERMONTOVA', 'Lermonrova': 'LERMONTOVA',
        'Raserti': 'RASETTI',
        'Waccotr': 'WALCOTT', 'Watcort': 'WALCOTT',
        'Berricy': 'BEYRICH', 'Bevaicu': 'BEYRICH',
        'Gdnicu': 'GURICH', 'Goricn': 'GURICH',
        'Purecer': 'PRIBYL', 'Potetragva': 'POULSEN',
        'Hawise & Corpa': 'HAWLE & CORDA',
        'Harnincron': 'HARRINGTON', 'Reep': 'REED',
        'Wargurc': 'WARBURG', 'Peacu': 'PEACH',
    }
    author = author.strip()
    for bad, good in fixes.items():
        if bad in author:
            author = author.replace(bad, good)
    return author


def is_valid_genus(name, author, year):
    """Filter out false positive genus entries."""
    # Must start with uppercase, rest lowercase
    if not re.match(r'^[A-Z][a-z]{2,}', name):
        return False

    # Skip common non-genus words that slip through
    skip = {
        'Supertamily', 'Superfamily', 'Family', 'Subfamily', 'Suborder',
        'Order', 'Class', 'Trilobita', 'Trilobitomorpha', 'Arthropoda',
        'Systematic', 'Descriptions', 'Classification', 'Stratigraphic',
        'Geographic', 'References', 'Contents', 'Discussion', 'Remarks',
        'Occurrence', 'Distribution', 'Marine', 'Diminutive', 'Cephalon',
        'Longitudinal', 'Anterior', 'Posterior', 'Pygidium', 'Thorax',
        'Glabella', 'Surface', 'Dorsal', 'Figure', 'Type', 'General',
        'Lower', 'Middle', 'Upper', 'Cambrian', 'Ordovician', 'Silurian',
        'Devonian', 'Carboniferous', 'Permian', 'Mississippian',
        'Pennsylvanian', 'Tremadocian', 'Paradoxides',
        'Trintidae', 'Saukiandiops', 'Olenelloides',
    }
    if name in skip:
        return False

    # Year must be in reasonable range
    if year < 1750 or year > 1959:
        return False

    # Name must be at least 4 chars (very few genus names shorter)
    if len(name) < 4:
        return False

    # Skip names ending in -idae, -inae, -acea (family/subfamily/superfamily suffixes)
    if re.search(r'(idae|inae|acea|idea)$', name):
        return False

    return True


def build_page_to_family_map(family_headers, taxonomy):
    """Map page ranges to family names using OCR family headers and outline structure.

    Returns dict: page_number -> (family_name, subfamily_name or None)
    """
    # Sort headers by page
    headers = sorted(family_headers, key=lambda h: (h['page'], h.get('pos', 0)))

    # Build page->family mapping
    page_map = {}
    current_family = None
    current_subfamily = None

    for h in headers:
        if h['rank'] == 'family':
            current_family = h['name']
            current_subfamily = None
        elif h['rank'] == 'subfamily':
            current_subfamily = h['name']
        page_map[h['page']] = (current_family, current_subfamily)

    return headers


def assign_genera_to_families(genera, family_headers):
    """Assign genera to their families based on page position relative to family headers."""
    # Sort family headers by page
    sorted_headers = sorted(family_headers, key=lambda h: (h['page'], h.get('pos', 0)))

    # For each genus, find the nearest preceding family header
    results = []
    for g in genera:
        pg = g['page']
        # Find the last family header before or on this page
        current_family = None
        current_subfamily = None
        for h in sorted_headers:
            if h['page'] <= pg:
                if h['rank'] == 'family':
                    current_family = h['name']
                    current_subfamily = None
                elif h['rank'] == 'subfamily':
                    current_subfamily = h['name']
            else:
                break

        g['family'] = current_family
        g['subfamily'] = current_subfamily
        results.append(g)

    return results


def integrate_genera_into_tree(taxonomy, genera):
    """Add genus children to the appropriate family/subfamily nodes in the tree.

    Strategy: build page ranges for each family/subfamily in the outline,
    then use OCR family headers to refine the mapping, and place genera
    at the lowest matching level (subfamily if possible, otherwise family).

    A genus is placed at most once (global dedup). Subfamily matches take
    priority over family-level matches to avoid OCR page-boundary errors
    (e.g. Dinesidae page range bleeding into Ptychopariidae genera).
    """

    # Build lookup: family_name (normalized) -> list of genera
    # Also build subfamily lookup
    family_genera = defaultdict(list)
    subfamily_genera = defaultdict(list)
    unplaced = []

    for g in genera:
        fam = g.get('family', '')
        subfam = g.get('subfamily', '')
        if subfam:
            subfamily_genera[subfam.upper().strip()].append(g)
        elif fam:
            family_genera[fam.upper().strip()].append(g)
        else:
            unplaced.append(g)

    placed_count = [0]
    placed_globally = set()  # track genera placed anywhere in tree

    def try_match_key(name):
        """Generate possible match keys for a taxon name."""
        name_upper = name.upper().strip()
        name_clean = re.sub(r'^[?\s]+', '', name_upper)
        keys = [name_clean]
        # Also try without common prefix variations
        if name_clean.startswith('FAMILY '):
            keys.append(name_clean[7:])
        if name_clean.startswith('SUBFAMILY '):
            keys.append(name_clean[10:])
        return keys

    def add_genera_to_node(node, genus_list):
        """Add a list of genus dicts as children of node (skip globally placed)."""
        if 'children' not in node:
            node['children'] = []
        existing_names = {c['name'] for c in node['children'] if c.get('rank') == 'genus'}
        for g in genus_list:
            if g['name'] not in existing_names and g['name'] not in placed_globally:
                node['children'].append({
                    'rank': 'genus',
                    'name': g['name'],
                    'author': g['author'],
                    'year': g['year'],
                })
                existing_names.add(g['name'])
                placed_globally.add(g['name'])
                placed_count[0] += 1

    def add_genera_recursive(node):
        name = node.get('name', '')
        rank = node.get('rank', '')

        if rank == 'subfamily':
            # Try to match subfamily with OCR subfamily genera
            for key in try_match_key(name):
                matched = subfamily_genera.get(key, [])
                if matched:
                    add_genera_to_node(node, matched)
                    break

        elif rank == 'family':
            has_subfamily_children = any(
                c.get('rank') == 'subfamily' for c in node.get('children', [])
            )

            # First: place subfamily genera (higher priority — more specific)
            if has_subfamily_children:
                for child in node.get('children', []):
                    if child.get('rank') == 'subfamily':
                        for key in try_match_key(child['name']):
                            sub_matched = subfamily_genera.get(key, [])
                            if sub_matched:
                                add_genera_to_node(child, sub_matched)
                                break

            # Then: place family-level genera (skips already-placed genera)
            matched_fam = []
            for key in try_match_key(name):
                matched_fam = family_genera.get(key, [])
                if matched_fam:
                    break
            # Also try partial match
            if not matched_fam:
                for key in family_genera:
                    for mk in try_match_key(name):
                        if mk in key or key in mk:
                            matched_fam = family_genera[key]
                            break
                    if matched_fam:
                        break

            if matched_fam:
                add_genera_to_node(node, matched_fam)

        for child in node.get('children', []):
            add_genera_recursive(child)

    add_genera_recursive(taxonomy['taxonomy'])

    # Report unplaced genera
    total_genera = len(genera)
    print(f"  Genera placed in tree: {placed_count[0]}")
    print(f"  Genera without family assignment: {len(unplaced)}")

    return taxonomy


def count_genera_in_tree(node):
    """Count genus nodes in the tree."""
    count = 0
    if node.get('rank') == 'genus':
        count = 1
    for child in node.get('children', []):
        count += count_genera_in_tree(child)
    return count


def count_all_by_rank(node, stats=None):
    if stats is None:
        stats = defaultdict(int)
    rank = node.get('rank', 'unknown')
    if rank != 'note':
        stats[rank] += 1
    for child in node.get('children', []):
        count_all_by_rank(child, stats)
    return stats


def main():
    print("Loading data...")
    taxonomy, ocr = load_data()

    genera = ocr['genera']
    family_headers = ocr['family_headers']

    print(f"Raw OCR genera: {len(genera)}")
    print(f"Family headers: {len(family_headers)}")

    # Step 1: Clean genus names and authors
    print("\nStep 1: Cleaning genus names and authors...")
    for g in genera:
        g['name'] = clean_genus_name(g['name'])
        g['author'] = clean_author(g['author'])

    # Step 2: Filter invalid entries
    print("Step 2: Filtering invalid entries...")
    valid = [g for g in genera if is_valid_genus(g['name'], g['author'], g['year'])]
    print(f"  Valid genera: {len(valid)} (removed {len(genera) - len(valid)})")

    # Step 3: Deduplicate by name (keep first occurrence)
    print("Step 3: Deduplicating...")
    seen = set()
    unique = []
    for g in valid:
        if g['name'] not in seen:
            seen.add(g['name'])
            unique.append(g)
    print(f"  Unique genera: {len(unique)}")

    # Step 4: Assign genera to families
    print("Step 4: Assigning genera to families...")
    assigned = assign_genera_to_families(unique, family_headers)
    with_family = [g for g in assigned if g.get('family')]
    print(f"  Genera with family assignment: {len(with_family)}")

    # Step 5: Integrate into taxonomy tree
    print("Step 5: Integrating into taxonomy tree...")
    # We need to not modify the original, use a copy
    import copy
    tree = copy.deepcopy(taxonomy)

    # Strip any existing genus nodes and revert placeholder renames from previous runs
    def reset_tree(node):
        if 'children' in node:
            node['children'] = [c for c in node['children'] if c.get('rank') != 'genus']
            for c in node['children']:
                reset_tree(c)
        # Revert placeholder renames like "Subfamily Uncertain (ParentName)" → "Subfamily Uncertain"
        name = node.get('name', '')
        if 'uncertain' in name.lower() and '(' in name:
            node['name'] = re.sub(r'\s*\(.*\)$', '', name)
    reset_tree(tree['taxonomy'])

    tree = integrate_genera_into_tree(tree, assigned)

    # Step 6: Make placeholder names unique by appending parent name
    print("Step 6: Making placeholder names unique...")
    placeholder_renames = [0]

    def uniquify_placeholders(node, parent_name=None):
        name = node.get('name', '')
        rank = node.get('rank', '')
        # Detect generic placeholder names like "Family Uncertain", "Subfamily Uncertain"
        if parent_name and 'uncertain' in name.lower():
            new_name = f"{name} ({parent_name})"
            if new_name != name:
                node['name'] = new_name
                placeholder_renames[0] += 1
        for child in node.get('children', []):
            uniquify_placeholders(child, name)

    uniquify_placeholders(tree['taxonomy'])
    print(f"  Renamed: {placeholder_renames[0]} placeholders")

    # Count genera actually placed in tree
    genera_in_tree = count_genera_in_tree(tree['taxonomy'])
    print(f"  Genera placed in tree: {genera_in_tree}")

    # Also keep a flat list of all genera as a separate field
    tree['genera_flat'] = [{
        'name': g['name'],
        'author': g['author'],
        'year': g['year'],
        'page': g['page'],
        'family': g.get('family'),
    } for g in unique]

    # Update metadata
    tree['source'] = "Treatise on Invertebrate Paleontology, Part O, Arthropoda 1, Trilobitomorpha (1959)"
    tree['note'] = (
        "Higher taxonomy (Order-Subfamily) manually encoded from Outline of Classification (pp. O160-O167). "
        "Genus names extracted via Tesseract OCR at 300 DPI from Systematic Descriptions (pp. O172-O525). "
        "OCR extraction may have missed some genera or introduced errors in author/year citations. "
        f"Total unique genera extracted: {len(unique)} out of ~1,401 recorded in the outline."
    )

    # Save
    output_path = 'data/treatise_1959_taxonomy.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tree, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {output_path}")

    # Print stats
    stats = count_all_by_rank(tree['taxonomy'])
    print(f"\nTaxa counts by rank:")
    for rank in ['class', 'order', 'suborder', 'superfamily', 'family', 'subfamily', 'genus']:
        print(f"  {rank}: {stats.get(rank, 0)}")

    # Show genera per order
    print(f"\nGenera per order:")
    for order in tree['taxonomy'].get('children', []):
        if order.get('rank') == 'order':
            gc = count_genera_in_tree(order)
            print(f"  {order['name']}: {gc} genera")

    # Show sample genera from different families
    print(f"\nSample genera by family (first 3 per family, first 10 families):")
    fam_count = 0
    def show_families(node, depth=0):
        nonlocal fam_count
        if fam_count >= 10:
            return
        if node.get('rank') == 'family' and node.get('children'):
            genus_children = [c for c in node['children'] if c.get('rank') == 'genus']
            if genus_children:
                fam_count += 1
                print(f"  {node['name']}:")
                for g in genus_children[:3]:
                    print(f"    {g['name']} {g['author']}, {g['year']}")
        for child in node.get('children', []):
            show_families(child, depth + 1)
    show_families(tree['taxonomy'])


if __name__ == '__main__':
    main()
