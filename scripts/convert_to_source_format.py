#!/usr/bin/env python3
"""Convert existing data files to extended source format (R04).

Generates data/sources/*.txt from existing data files:
  - treatise_1959.txt   ← data/treatise_1959_taxonomy.txt + header
  - treatise_2004_ch4.txt ← data/treatise_ch4_taxonomy.json → hierarchy text
  - treatise_2004_ch5.txt ← data/treatise_ch5_taxonomy.json → hierarchy text
  - adrain_2011.txt     ← data/adrain2011.txt + header + cleanup
  - jell_adrain_2002.txt ← data/trilobite_genus_list.txt → family-grouped hierarchy

Usage:
    python scripts/convert_to_source_format.py
"""

import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "sources"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_file(path: Path, header: str, body: str):
    """Write header + body to file."""
    content = f"---\n{header}---\n\n{body}"
    path.write_text(content, encoding="utf-8")
    lines = content.count("\n") + 1
    print(f"  → {path.name}: {lines} lines")


def normalize_name(name: str) -> str:
    """Capitalize first letter, lowercase rest (for single-word taxon names)."""
    if " " in name or not name:
        return name
    return name[0].upper() + name[1:].lower()


# ---------------------------------------------------------------------------
# 1. Treatise 1959
# ---------------------------------------------------------------------------

def convert_treatise_1959():
    print("1. Treatise 1959...")
    src = DATA / "treatise_1959_taxonomy.txt"
    body = src.read_text(encoding="utf-8")

    # Replace "nov." with 1959 (publication year)
    # e.g., "CALLAVIINAE Poulsen, nov." → "CALLAVIINAE Poulsen, 1959"
    body = re.sub(r',?\s*nov\.', ', 1959', body)

    header = """\
reference: Moore, R.C. (Ed.), 1959. Treatise on Invertebrate Paleontology, Part O, Arthropoda 1, Trilobita
scope:
  - taxon: Trilobita
    coverage: comprehensive
"""
    write_file(OUT / "treatise_1959.txt", header, body)


# ---------------------------------------------------------------------------
# 2. Treatise 2004 (ch4 + ch5)
# ---------------------------------------------------------------------------

RANK_INDENT = {
    "order": 0, "suborder": 1, "superfamily": 2,
    "family": 3, "subfamily": 4, "genus": 5,
}

RANK_PREFIX = {
    "order": "Order", "suborder": "Suborder", "superfamily": "Superfamily",
    "family": "Family", "subfamily": "Subfamily",
}


def json_to_hierarchy(node, depth=0):
    """Recursively convert a JSON taxonomy node to indented text."""
    lines = []
    rank = node.get("rank", "").lower()
    name = node.get("name", "")
    author = node.get("author", "")
    year = node.get("year", "")
    uncertain = node.get("uncertain", False)
    note = node.get("note", "")

    # Skip subgenus
    if rank == "subgenus":
        return lines

    # Skip "unrecognizable" containers but include their children
    if rank == "unrecognizable":
        for child in node.get("children", []):
            lines.extend(json_to_hierarchy(child, depth))
        return lines

    indent = "  " * depth

    # Build line
    prefix = RANK_PREFIX.get(rank, "")
    q = "?" if uncertain else ""

    if prefix:
        # Higher rank: "  Family REDLICHIIDAE Poulsen, 1927"
        disp_name = name.upper() if rank in ("order", "suborder") else normalize_name(name)
        auth_str = f" {author}, {year}" if author and year else ""
        lines.append(f"{indent}{prefix} {q}{disp_name}{auth_str}")
    else:
        # Genus: "    Redlichia Cossman, 1902"
        disp_name = normalize_name(name)
        auth_str = f" {author}, {year}" if author and year else ""
        incertae = " [incertae sedis]" if note and "incertae" in note.lower() else ""
        lines.append(f"{indent}{q}{disp_name}{auth_str}{incertae}")

    for child in node.get("children", []):
        lines.extend(json_to_hierarchy(child, depth + 1))

    return lines


def convert_treatise_2004_ch4():
    print("2a. Treatise 2004 ch4 (Agnostida)...")
    src = DATA / "treatise_ch4_taxonomy.json"
    data = json.loads(src.read_text(encoding="utf-8"))

    header = """\
reference: Shergold, J.H., Laurie, J.R. & Sun, X., 2004. Classification of the Agnostida. In: Kaesler, R.L. (Ed.), Treatise on Invertebrate Paleontology, Part O, Revised, Vol. 1, Ch. 4
scope:
  - taxon: Agnostida
    coverage: comprehensive
"""
    lines = json_to_hierarchy(data["taxonomy"])
    write_file(OUT / "treatise_2004_ch4.txt", header, "\n".join(lines) + "\n")


def convert_treatise_2004_ch5():
    print("2b. Treatise 2004 ch5 (Redlichiida)...")
    src = DATA / "treatise_ch5_taxonomy.json"
    data = json.loads(src.read_text(encoding="utf-8"))

    header = """\
reference: Palmer, A.R. & Repina, L.N., 2004. Classification of the Redlichiida. In: Kaesler, R.L. (Ed.), Treatise on Invertebrate Paleontology, Part O, Revised, Vol. 1, Ch. 5
scope:
  - taxon: Redlichiida
    coverage: comprehensive
"""
    lines = json_to_hierarchy(data["taxonomy"])
    write_file(OUT / "treatise_2004_ch5.txt", header, "\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# 3. Adrain 2011
# ---------------------------------------------------------------------------

def convert_adrain_2011():
    print("3. Adrain 2011...")
    src = DATA / "adrain2011.txt"

    header = """\
reference: Adrain, J.M., 2011. Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.), Animal biodiversity: An outline of higher-level classification and survey of taxonomic richness. Zootaxa, 3148, 104-109
scope:
  - taxon: Trilobita
    coverage: comprehensive
notes: |
  Suprafamilial classification only (Order → Family). No genera.
  Agnostida is excluded from Trilobita sensu stricto by Adrain (2011).
"""

    lines = []
    parent_stack = []  # tracks rank depth for indentation
    for raw in src.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue

        # Strip footnote digits at end (e.g., "Walch, 17711 2" → "Walch, 1771")
        # Also strip parenthetical notes like "(6 families)" "(22 genera, 87 species)"
        line = re.sub(r'\s*\(\d+\s+(?:genus|genera|famil|species|suborder|superfamil)[^)]*\)\d*\s*$', '', line)

        # Fix year with trailing footnote digits: "17711 2" → "1771", "19393" → "1939"
        # Pattern: 4-digit year followed by extra digits (footnotes)
        line = re.sub(r'(\d{4})\d+(\s|$)', r'\1\2', line)

        # Replace "nov." (with optional trailing footnote digits) with "Adrain, 2011"
        # Adrain is the author of all new taxa in this publication
        line = re.sub(r',?\s*nov\.\d*', ' Adrain, 2011', line)

        # Strip trailing footnote digits from taxon names (e.g., "Uncertain37" → "Uncertain")
        # Pattern: word ending with digits that aren't part of a year
        line = re.sub(r'([A-Za-z])\d+\s*$', r'\1', line)

        # Determine rank and indent based on parent context
        rank_match = re.match(r'^(Class|Order|Suborder|Superfamily|Family)\s+', line)
        if rank_match:
            rank = rank_match.group(1)
            if rank == "Class":
                continue
            # Track parent stack to determine indent dynamically
            rank_order = {"Order": 0, "Suborder": 1, "Superfamily": 2, "Family": 3}
            ro = rank_order.get(rank, 0)
            # Pop stack back to parent level
            while parent_stack and parent_stack[-1] >= ro:
                parent_stack.pop()
            indent = "  " * len(parent_stack)
            parent_stack.append(ro)
            lines.append(f"{indent}{line.strip()}")
        else:
            lines.append(line.strip())

    write_file(OUT / "adrain_2011.txt", header, "\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# 4. Jell & Adrain 2002
# ---------------------------------------------------------------------------

# Synonym patterns from raw entries
SYN_PATTERNS = [
    # [j.s.s. of X, fide AUTHOR, YEAR]
    (r'\[j\.s\.s\.?\s+of\s+([^,\]]+?)(?:,\s*fide\s+([^]]+))?\]', 'j.s.s.'),
    # [j.o.s. of X]
    (r'\[j\.o\.s\.?\s+of\s+([^]\]]+)\]', 'j.o.s.'),
    # [preocc., replaced by X]
    (r'\[preocc\.,?\s*replaced\s+by\s+([^]\]]+)\]', 'preocc.'),
    # [preocc., not replaced]
    (r'\[preocc\.,?\s*not\s+replaced\]', 'preocc_not_replaced'),
    # [suppressed by ICZN ... for X]
    (r'\[suppressed\s+by\s+ICZN[^]]*?for\s+([^]\]]+)\]', 'suppressed'),
    # [replacement name for X]
    (r'\[replacement\s+name\s+for\s+([^]\]]+)\]', 'replacement'),
    # [unnecessary replacement ... j.o.s. of X]  or [unnecessary replacement ... of X]
    (r'\[unnecessary\s+replacement[^]]*?(?:j\.o\.s\.?\s+)?of\s+([^]\]]+)\]', 'unnecessary_replacement'),
    # [inappropriate emendation of X]
    (r'\[inappropriate\s+emendation\s+of\s+([^]\]]+)\]', 'inappropriate_emendation'),
    # [incorrect spelling of X]
    (r'\[incorrect\s+spelling\s+of\s+([^]\]]+)\]', 'incorrect_spelling'),
]


def parse_genus_entry(line, pub_year=2002):
    """Parse a JA2002 genus entry line into structured fields."""
    line = line.strip().rstrip(".")

    # Replace "nov." with publication year
    # "JELL, nov." → "JELL, 2002", "CAMPBELL nov." → "CAMPBELL, 2002"
    line = re.sub(r',?\s*nov\.', f', {pub_year}', line)

    # Fix extra comma after year: "1965, [" → "1965 ["
    line = re.sub(r'(\d{4}[a-z]?),\s*\[', r'\1 [', line)

    # Fix period after year suffix: "1966b." → "1966b"
    line = re.sub(r'(\d{4}[a-z])\.\s', r'\1 ', line)

    # Fix lowercase-starting authority: "deKONINCK" → treat as uppercase start
    # by matching authority that starts with a lowercase prefix followed by uppercase
    line = re.sub(r'^([A-ZÀ-Ž][a-zà-ž]+(?:-[a-zà-ž]+)?)\s+(de|van|von)([A-Z])', r'\1 \2\3', line)

    # Handle "misspelling of X" — with or without authority
    m_misspell = re.match(
        r'^([A-ZÀ-Ž][a-zà-ž]+)'                       # genus name
        r'(?:\s+[A-Z][A-Z\'.&\s]+,\s*\d{4}[a-z]?)?'   # optional authority
        r'\s+misspelling\s+of\s+(.+?)(?:\s+in\s+.+)?\.?\s*$',
        line, re.IGNORECASE
    )
    if m_misspell:
        return {
            "name": m_misspell.group(1),
            "authority": "",
            "type_species": "",
            "formation_location": "",
            "family": "NOTES",
            "temporal_code": "",
            "synonyms": [],
            "questionable_family": False,
            "raw": line,
            "_note": f"misspelling of {m_misspell.group(2).rstrip('.')}",
        }

    # Extract genus name and authority
    # Strategy: find genus name, then capture everything up to the YEAR
    m = re.match(
        r'^([A-ZÀ-Ž][a-zà-ž]+(?:-[a-zà-ž]+)?)\s+'   # genus name
        r'((?:[A-Za-zÀ-Ž]'                              # start of authority (allow lowercase for de/van/von)
        r'[^\[\]]*?'                                    # anything except brackets (greedy-safe)
        r'(?:,\s*)?\d{4}[a-z]?))'                      # optional comma + YEAR[suffix]
        r'(?=\s*\[|\s+[A-Z]|\s*$)',                    # lookahead: followed by [, uppercase, or EOL
        line
    )
    if not m:
        # Fallback: "GenusName YEAR [..." (no author, e.g., "Bohemopyge 1950 [...")
        m = re.match(
            r'^([A-ZÀ-Ž][a-zà-ž]+(?:-[a-zà-ž]+)?)\s+'
            r'(\d{4}[a-z]?)',
            line
        )
    if not m:
        # Fallback: misspelling/note entries like "Blountiana [misspelling of..."
        m_note = re.match(
            r'^([A-ZÀ-Ž][a-zà-ž]+(?:-[a-zà-ž]+)?)\s*\[(.+)\]\s*\.?\s*$',
            line
        )
        if m_note:
            return {
                "name": m_note.group(1),
                "authority": "",
                "type_species": "",
                "formation_location": "",
                "family": "NOTES",
                "temporal_code": "",
                "synonyms": [],
                "questionable_family": False,
                "raw": line,
                "_note": m_note.group(2),
            }
    if not m:
        return None

    name = m.group(1)
    authority = m.group(2).strip()
    rest = line[m.end():].strip()

    # Extract type species [...]
    type_species = ""
    ts_match = re.match(r'\[([^\]]+)\]', rest)
    if ts_match:
        type_species = ts_match.group(1)
        rest = rest[ts_match.end():].strip()

    # Extract synonymy info from remaining [...] blocks
    synonyms = []
    for pattern, syn_type in SYN_PATTERNS:
        for sm in re.finditer(pattern, line, re.IGNORECASE):
            target = sm.group(1).strip() if sm.lastindex and sm.lastindex >= 1 else ""
            fide = sm.group(2).strip() if sm.lastindex and sm.lastindex >= 2 else ""
            synonyms.append({
                "type": syn_type,
                "target": target,
                "fide": fide,
            })

    # Extract family and temporal code (last two semicolon-separated fields)
    # Format: ...formation, location; FAMILY; TEMPORAL_CODE
    family = ""
    temporal_code = ""
    formation_location = ""

    # Remove all [...] blocks and stray brackets for field parsing
    clean = re.sub(r'\[[^\]]*\]', '', rest).strip()
    clean = clean.lstrip('] ').rstrip('. ')
    # Split by semicolons
    parts = [p.strip() for p in clean.split(";") if p.strip()]

    if len(parts) >= 2:
        temporal_code = parts[-1].rstrip(".")
        family = parts[-2]
        formation_location = "; ".join(parts[:-2]) if len(parts) > 2 else ""
    elif len(parts) == 1:
        # Could be just family or temporal
        family = parts[0].rstrip(".")

    # Clean family name
    family = family.strip()

    # Normalize "SUBORDER FAMILY UNCERTAIN" → "UNCERTAIN"
    # e.g., "AGNOSTINA FAMILY UNCERTAIN" → "UNCERTAIN"
    if "FAMILY UNCERTAIN" in family:
        family = "UNCERTAIN"

    # Determine if questionable family
    questionable_family = family.startswith("?")
    family = family.lstrip("?")

    return {
        "name": name,
        "authority": authority,
        "type_species": type_species,
        "formation_location": formation_location,
        "family": family,
        "temporal_code": temporal_code,
        "synonyms": synonyms,
        "questionable_family": questionable_family,
        "raw": line,
    }


def convert_jell_adrain_2002():
    print("4. Jell & Adrain 2002...")
    src = DATA / "trilobite_genus_list.txt"

    header = """\
reference: Jell, P.A. & Adrain, J.M., 2002. Available Generic Names for Trilobites. Memoirs of the Queensland Museum, 48(2), 331-553
scope:
  - taxon: Trilobita
    coverage: comprehensive
notes: |
  Complete genus-level catalogue. Genera grouped by family assignment.
  Synonym information extracted from nomenclatural brackets.
  Format: GenusName Author, Year [type species] | formation, location | TEMPORAL_CODE
"""

    # Parse all entries
    entries = []
    for line in src.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = parse_genus_entry(line)
        if parsed:
            entries.append(parsed)
        else:
            # Unparseable — keep as comment
            entries.append({"_comment": line})

    print(f"  Parsed {len([e for e in entries if 'name' in e])} genera, "
          f"{len([e for e in entries if '_comment' in e])} unparsed")

    # Group by family
    by_family = defaultdict(list)
    unparsed = []
    for e in entries:
        if "_comment" in e:
            unparsed.append(e["_comment"])
        else:
            by_family[e["family"]].append(e)

    # Sort families alphabetically; skip empty-family genera (nomenclatural notes)
    notes_genera = by_family.pop("", [])
    notes_genera.extend(by_family.pop("NOTES", []))

    lines = []
    for family in sorted(by_family.keys()):
        genera = by_family[family]
        lines.append(f"Family {family}")

        for g in sorted(genera, key=lambda x: x["name"]):
            # Note-only entries (misspellings etc.)
            if g.get("_note"):
                lines.append(f"  # {g['name']}: {g['_note']}")
                continue

            # Build genus line
            prefix = "?" if g["questionable_family"] else ""
            ts = f" [{g['type_species']}]" if g["type_species"] else ""
            fl_val = g['formation_location'].lstrip('] ') if g['formation_location'] else ""
            fl = f" | {fl_val}" if fl_val else ""
            tc = f" | {g['temporal_code']}" if g["temporal_code"] else ""
            auth = f" {g['authority']}" if g["authority"] else ""
            lines.append(f"  {prefix}{g['name']}{auth}{ts}{fl}{tc}")

            # Synonym lines
            for syn in g["synonyms"]:
                if syn["type"] == "preocc_not_replaced":
                    lines.append(f"    # preocc., not replaced")
                elif syn["type"] == "preocc.":
                    target = syn["target"]
                    lines.append(f"    # preocc., replaced by {target}")
                elif syn["type"] in ("j.s.s.", "j.o.s."):
                    target = syn["target"]
                    fide = f", fide {syn['fide']}" if syn["fide"] else ""
                    lines.append(f"    = {target} ({syn['type']}{fide})")
                elif syn["type"] == "replacement":
                    target = syn["target"]
                    lines.append(f"    # replacement name for {target}")
                elif syn["type"] == "suppressed":
                    target = syn["target"]
                    lines.append(f"    # suppressed for {target}")
                elif syn["type"] in ("unnecessary_replacement", "inappropriate_emendation", "incorrect_spelling"):
                    target = syn["target"]
                    label = syn["type"].replace("_", " ")
                    lines.append(f"    ~ {target} ({label})")

    # Nomenclatural notes (genera without family assignment — synonyms, replacements, etc.)
    if notes_genera:
        lines.append("")
        lines.append("# --- Nomenclatural notes (no family assignment) ---")
        for g in sorted(notes_genera, key=lambda x: x["name"]):
            note = g.get("_note", "")
            syns = "; ".join(
                f"{s['type']}: {s['target']}" for s in g.get("synonyms", []) if s.get("target")
            )
            detail = note or syns or "no family"
            lines.append(f"# {g['name']} {g.get('authority', '')} — {detail}")

    if unparsed:
        lines.append("")
        lines.append("# --- Unparsed entries ---")
        for u in unparsed:
            lines.append(f"# {u}")

    write_file(OUT / "jell_adrain_2002.txt", header, "\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Converting to extended source format (R04) ===\n")
    convert_treatise_1959()
    convert_treatise_2004_ch4()
    convert_treatise_2004_ch5()
    convert_adrain_2011()
    convert_jell_adrain_2002()
    print("\nDone.")


if __name__ == "__main__":
    main()
