"""Step 2: Hierarchy parsing from adrain2011.txt.

Parses the rank-prefixed hierarchy file into a flat list of nodes
that can be inserted into taxonomic_ranks.  Also adds:
  - Agnostida Order (with Agnostina Suborder + 10 families)
  - "Uncertain" Order placeholder
  - SPELLING_OF placeholder families
  - Pseudo-family entries (INDET, UNCERTAIN, NEKTASPIDA, etc.)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Agnostida families that are placed under Suborder Agnostina
# (from restructure_agnostida_opinions.py / genus list family assignments)
AGNOSTIDA_FAMILIES = [
    ('Agnostidae', 'McCOY, 1849'),
    ('Ammagnostidae', 'OPIK, 1967'),
    ('Clavagnostidae', 'HOWELL, 1937'),
    ('Condylopygidae', 'RAYMOND, 1913'),
    ('Diplagnostidae', 'WHITEHOUSE, 1936'),
    ('Doryagnostidae', 'SHERGOLD et al., 1990'),
    ('Glyptagnostidae', 'WHITEHOUSE, 1936'),
    ('Metagnostidae', 'JAEKEL, 1909'),
    ('Peronopsidae', 'WESTERGARD, 1936'),
    ('Ptychagnostidae', 'KOBAYASHI, 1939'),
]

# Families from the genus list that don't appear in adrain2011.txt
# These are placed under "Uncertain" Order
EXTRA_UNCERTAIN_FAMILIES = [
    ('Bohemillidae', 'BARRANDE, 1872'),
    ('Burlingiidae', 'WALCOTT, 1908'),
    ('Conokephalinidae', 'HUPE, 1953'),
    ('Ordosiidae', 'LU, 1954'),
    ('Pagodiidae', 'KOBAYASHI, 1935c'),
    ('Pilekiidae', 'SDZUY, 1955'),
    ('Saukiidae', 'ULRICH & RESSER, 1930'),
    ('Toernquistiidae', 'HUPE, 1953'),
]

# Pseudo-families (special entries for unplaced genera)
PSEUDO_FAMILIES = [
    ('Linguaproetidae', None, None),   # Single-genus family
    ('Scutelluidae', None, None),      # Single-genus family
    ('INDET', None, '미확정 (Indeterminate)'),
    ('UNCERTAIN', None, '불확실 (Uncertain placement)'),
    ('NEKTASPIDA', None, 'Nektaspida - 비삼엽충 절지동물'),
]

# SPELLING_OF placeholder families
SPELLING_PLACEHOLDERS = [
    ('Dokimocephalidae', None, 'Orthographic variant of Dokimokephalidae. '
     'Jell & Adrain (2002) spelling.'),
    ('Chengkouaspidae', None, 'Orthographic variant of Chengkouaspididae. '
     'Jell & Adrain (2002) spelling.'),
]


@dataclass
class HierarchyNode:
    """A node in the taxonomic hierarchy."""
    name: str
    rank: str       # Class, Order, Suborder, Superfamily, Family
    author: str | None = None
    year: int | None = None
    year_suffix: str | None = None
    notes: str | None = None
    is_placeholder: int = 0
    parent_name: str | None = None  # resolved to parent_id during load
    genera_count: int = 0
    # internal
    _parent_idx: int | None = None


def _parse_author_year(text: str) -> tuple[str | None, int | None, str | None]:
    """Extract author, year, year_suffix from a string like 'Walcott, 1890'."""
    if not text:
        return None, None, None
    m = re.match(r'^(.+?),\s*(\d{4})([a-z])?$', text.strip())
    if m:
        return m.group(1).strip(), int(m.group(2)), m.group(3)
    return text.strip(), None, None


def _parse_adrain_line(line: str) -> tuple[str, str, str | None, str | None]:
    """Parse a single line from adrain2011.txt.

    Returns (rank, name, author_str, notes).
    """
    line = line.strip()
    rank_hierarchy = ['Class', 'Order', 'Suborder', 'Superfamily', 'Family']

    rank = None
    for r in rank_hierarchy:
        if line.startswith(r):
            rank = r
            break
    if not rank:
        return '', '', None, None

    content = line[len(rank):].strip()

    # Extract notes in parentheses at end: (N genera, M species) or (N families)
    # Allow trailing footnote digits after closing paren (e.g., "(11 families)33")
    notes = None
    notes_match = re.search(r'(\(\d+\s+(?:genus|genera|famil|subfamil|suborder|superfamil).+\))\s*(?:\d{1,2}\s*)*$', content)
    if notes_match:
        notes = notes_match.group(1)
        content = content[:notes_match.start()].strip()

    # Handle "nov." in author position (allow trailing footnote digits)
    content = re.sub(r'\bnov\.(?:\s*\d{1,2})*\s*$', '', content).strip()

    # Try to extract name and author
    # Name is first word(s), author is AUTHOR, YEAR format
    # Allow trailing footnote digits (e.g., "Walch, 17711 2" → year=1771, footnotes "1 2")
    author_match = re.search(
        r'\s+([A-ZÀ-Ž][A-Za-zÀ-ž\s&,\.]+,\s*\d{4}[a-z]?)(?:\s*\d{1,2})*\s*$',
        content
    )
    if author_match:
        name = content[:author_match.start()].strip()
        author_str = author_match.group(1).strip()
    else:
        # Try: Name Author-no-year
        name = content
        author_str = None

    # Clean name of trailing whitespace and footnote superscripts
    # (only when author extraction failed; otherwise name is already clean)
    if not author_match:
        name = re.sub(r'(?:\s*\d{1,2})+\s*$', '', name).strip()

    return rank, name, author_str, notes


def parse_hierarchy(adrain_path: Path) -> list[HierarchyNode]:
    """Parse adrain2011.txt into a flat list of HierarchyNode.

    Includes additional nodes for Agnostida, Uncertain, pseudo-families,
    and SPELLING_OF placeholders.
    """
    lines = adrain_path.read_text(encoding='utf-8').splitlines()
    nodes: list[HierarchyNode] = []

    rank_hierarchy = ['Class', 'Order', 'Suborder', 'Superfamily', 'Family']
    last_seen: dict[str, int] = {}  # rank → index in nodes list

    for line in lines:
        line = line.strip()
        if not line:
            continue

        rank, name, author_str, notes = _parse_adrain_line(line)
        if not rank or not name:
            continue

        author, year, year_suffix = _parse_author_year(author_str)

        # Determine parent
        rank_idx = rank_hierarchy.index(rank)
        parent_idx = None
        for i in range(rank_idx - 1, -1, -1):
            if rank_hierarchy[i] in last_seen:
                parent_idx = last_seen[rank_hierarchy[i]]
                break

        is_placeholder = 1 if name == 'Uncertain' else 0

        node = HierarchyNode(
            name=name,
            rank=rank,
            author=author,
            year=year,
            year_suffix=year_suffix,
            notes=notes,
            is_placeholder=is_placeholder,
            _parent_idx=parent_idx,
        )
        idx = len(nodes)
        nodes.append(node)

        # Update tracking
        last_seen[rank] = idx
        # Invalidate lower ranks
        for i in range(rank_idx + 1, len(rank_hierarchy)):
            last_seen.pop(rank_hierarchy[i], None)

    # --- Fix author for Class Trilobita ---
    if nodes and nodes[0].name == 'Trilobita':
        nodes[0].author = 'Walch'
        nodes[0].year = 1771

    # --- Shirakiellidae duplicate check ---
    # adrain2011.txt has Shirakiellidae under both Leiostegiina and Uncertain.
    # The DB keeps the one under Leiostegiina (id=67) and the one under
    # Uncertain (id=196) is effectively the same family.  The Uncertain
    # copy in adrain2011 line 196 actually IS the same family repeated.
    # We skip duplicates.
    seen_families = set()
    deduped: list[HierarchyNode] = []
    for node in nodes:
        if node.rank == 'Family':
            if node.name in seen_families:
                continue
            seen_families.add(node.name)
        deduped.append(node)
    nodes = deduped

    # --- Re-index parent pointers after dedup ---
    # We need stable parent references, so use name-based lookup instead
    # Store parent_name for each node
    for node in nodes:
        if node._parent_idx is not None and node._parent_idx < len(nodes):
            # Find original parent by walking the original list
            pass  # parent_name will be set below

    # Re-derive parent names using rank hierarchy logic
    last_seen_name: dict[str, str] = {}
    for node in nodes:
        rank_idx = rank_hierarchy.index(node.rank)
        for i in range(rank_idx - 1, -1, -1):
            if rank_hierarchy[i] in last_seen_name:
                node.parent_name = last_seen_name[rank_hierarchy[i]]
                break
        last_seen_name[node.rank] = node.name
        for i in range(rank_idx + 1, len(rank_hierarchy)):
            last_seen_name.pop(rank_hierarchy[i], None)

    # --- Add Agnostida Order (separate from adrain2011 hierarchy) ---
    agnostida_node = HierarchyNode(
        name='Agnostida', rank='Order',
        author='SALTER', year=1864,
        parent_name=None,  # NOT under Trilobita per Adrain 2011
        notes='Order created based on traditional classification. '
              'Excluded from Adrain (2011) Trilobita sensu stricto.',
    )
    nodes.append(agnostida_node)

    # Agnostina Suborder under Agnostida
    agnostina_node = HierarchyNode(
        name='Agnostina', rank='Suborder',
        author='Salter', year=1864,
        parent_name='Agnostida',
    )
    nodes.append(agnostina_node)

    # Agnostida families under Agnostina
    for fam_name, fam_author_str in AGNOSTIDA_FAMILIES:
        if fam_name in seen_families:
            continue
        author, year, year_suffix = _parse_author_year(fam_author_str)
        nodes.append(HierarchyNode(
            name=fam_name, rank='Family',
            author=author, year=year, year_suffix=year_suffix,
            parent_name='Agnostina',
        ))
        seen_families.add(fam_name)

    # --- Extra Uncertain families (not in adrain2011) ---
    for fam_name, fam_author_str in EXTRA_UNCERTAIN_FAMILIES:
        if fam_name in seen_families:
            continue
        author, year, year_suffix = _parse_author_year(fam_author_str)
        nodes.append(HierarchyNode(
            name=fam_name, rank='Family',
            author=author, year=year, year_suffix=year_suffix,
            parent_name='Uncertain',
        ))
        seen_families.add(fam_name)

    # --- Pseudo-families (INDET, UNCERTAIN, NEKTASPIDA, etc.) ---
    for fam_name, fam_author_str, notes in PSEUDO_FAMILIES:
        if fam_name in seen_families:
            continue
        nodes.append(HierarchyNode(
            name=fam_name, rank='Family',
            parent_name='Uncertain',
            notes=notes,
        ))
        seen_families.add(fam_name)

    # --- SPELLING_OF placeholders ---
    for fam_name, fam_author_str, notes in SPELLING_PLACEHOLDERS:
        if fam_name in seen_families:
            continue
        nodes.append(HierarchyNode(
            name=fam_name, rank='Family',
            is_placeholder=1,
            notes=notes,
        ))
        seen_families.add(fam_name)

    return nodes
