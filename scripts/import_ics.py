#!/usr/bin/env python3
"""
Phase 28: Import ICS International Chronostratigraphic Chart (GTS 2020).

Creates two tables:
  1. ics_chronostrat — ICS geological time units (self-referencing hierarchy)
  2. temporal_ics_mapping — temporal_ranges ↔ ICS concept mapping

Usage:
  python scripts/import_ics.py              # full import
  python scripts/import_ics.py --dry-run    # preview without DB changes
  python scripts/import_ics.py --report     # mapping report only (DB must exist)
"""

import os
import sqlite3
import sys

try:
    from rdflib import Graph, Namespace, URIRef, Literal
    from rdflib.namespace import RDF, SKOS
except ImportError:
    print("Error: rdflib is required. Install with: pip install rdflib", file=sys.stderr)
    sys.exit(1)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'trilobase.db')
TTL_PATH = os.path.join(os.path.dirname(__file__), '..',
                        'vendor', 'ics', 'gts2020', 'chart.ttl')

# Namespaces from the TTL file
GTS = Namespace('http://resource.geosciml.org/ontology/timescale/gts#')
RANK = Namespace('http://resource.geosciml.org/ontology/timescale/rank/')
ISCHART = Namespace('http://resource.geosciml.org/classifier/ics/ischart/')
TIME = Namespace('http://www.w3.org/2006/time#')
SDO = Namespace('https://schema.org/')
SH = Namespace('http://www.w3.org/ns/shacl#')
PROV = Namespace('http://www.w3.org/ns/prov#')

# Rank URI → display name
RANK_MAP = {
    str(RANK['Super-Eon']): 'Super-Eon',
    str(RANK['Eon']): 'Eon',
    str(RANK['Era']): 'Era',
    str(RANK['Period']): 'Period',
    str(RANK['Sub-Period']): 'Sub-Period',
    str(RANK['Epoch']): 'Epoch',
    str(RANK['Age']): 'Age',
}

# ── Temporal ranges ↔ ICS mapping definition ──
# Each entry: temporal_code → list of (ics_concept_suffix, mapping_type)
# ics_concept_suffix is the local name in ischart: namespace
TEMPORAL_MAPPING = {
    'LCAM': [('Terreneuvian', 'partial'), ('CambrianSeries2', 'partial')],
    'MCAM': [('Miaolingian', 'exact')],
    'UCAM': [('Furongian', 'exact')],
    'MUCAM': [('Miaolingian', 'aggregate'), ('Furongian', 'aggregate')],
    'LMCAM': [('Terreneuvian', 'aggregate'), ('CambrianSeries2', 'aggregate'),
              ('Miaolingian', 'aggregate')],
    'CAM': [('Cambrian', 'exact')],
    'LORD': [('LowerOrdovician', 'exact')],
    'MORD': [('MiddleOrdovician', 'exact')],
    'UORD': [('UpperOrdovician', 'exact')],
    'LMORD': [('LowerOrdovician', 'aggregate'), ('MiddleOrdovician', 'aggregate')],
    'MUORD': [('MiddleOrdovician', 'aggregate'), ('UpperOrdovician', 'aggregate')],
    'ORD': [('Ordovician', 'exact')],
    'LSIL': [('Llandovery', 'exact')],
    'USIL': [('Wenlock', 'partial'), ('Ludlow', 'partial'), ('Pridoli', 'partial')],
    'LUSIL': [('Llandovery', 'aggregate'), ('Wenlock', 'aggregate'),
              ('Ludlow', 'aggregate'), ('Pridoli', 'aggregate')],
    'SIL': [('Silurian', 'exact')],
    'LDEV': [('LowerDevonian', 'exact')],
    'MDEV': [('MiddleDevonian', 'exact')],
    'UDEV': [('UpperDevonian', 'exact')],
    'EDEV': [('LowerDevonian', 'exact')],
    'LMDEV': [('LowerDevonian', 'aggregate'), ('MiddleDevonian', 'aggregate')],
    'MUDEV': [('MiddleDevonian', 'aggregate'), ('UpperDevonian', 'aggregate')],
    'MISS': [('Mississippian', 'exact')],
    'PENN': [('Pennsylvanian', 'exact')],
    'LPERM': [('Cisuralian', 'exact')],
    'PERM': [('Permian', 'exact')],
    'UPERM': [('Lopingian', 'exact')],
    'INDET': [],  # unmappable
}


def parse_ttl(ttl_path):
    """Parse chart.ttl with rdflib, return list of concept dicts."""
    print(f"Parsing: {ttl_path}")
    g = Graph()
    g.parse(ttl_path, format='turtle')
    print(f"  {len(g)} triples loaded")

    concepts = []
    ischart_prefix = str(ISCHART)

    # Find all skos:Concept instances
    for subj in g.subjects(RDF.type, SKOS.Concept):
        uri = str(subj)
        if not uri.startswith(ischart_prefix):
            continue

        # Rank
        rank_uri = g.value(subj, GTS['rank'])
        if rank_uri is None:
            continue
        rank_name = RANK_MAP.get(str(rank_uri))
        if rank_name is None:
            print(f"  Warning: unknown rank {rank_uri} for {uri}")
            continue

        # Name (English prefLabel)
        name = None
        for label in g.objects(subj, SKOS.prefLabel):
            if isinstance(label, Literal) and label.language == 'en':
                name = str(label)
                break
        if name is None:
            # Fallback: use local name from URI
            name = uri.split('/')[-1]

        # Broader (parent URI)
        broader_uri = g.value(subj, SKOS.broader)
        parent_uri = str(broader_uri) if broader_uri else None

        # Time beginning/end (blank nodes)
        start_mya = None
        start_uncertainty = None
        end_mya = None
        end_uncertainty = None

        beginning = g.value(subj, TIME.hasBeginning)
        if beginning:
            for val in g.objects(beginning, ISCHART.inMYA):
                start_mya = float(val)
            for val in g.objects(beginning, SDO.marginOfError):
                start_uncertainty = float(val)

        ending = g.value(subj, TIME.hasEnd)
        if ending:
            for val in g.objects(ending, ISCHART.inMYA):
                end_mya = float(val)
            for val in g.objects(ending, SDO.marginOfError):
                end_uncertainty = float(val)

        # Short code (ccgmShortCode notation)
        short_code = None
        for notation in g.objects(subj, SKOS.notation):
            if isinstance(notation, Literal) and \
               notation.datatype and 'ccgmShortCode' in str(notation.datatype):
                short_code = str(notation)
                break

        # Color
        color = None
        for c in g.objects(subj, SDO.color):
            color = str(c)
            break

        # Display order
        display_order = None
        for order in g.objects(subj, SH.order):
            display_order = int(order)
            break

        # Ratified GSSP
        ratified = 0
        for val in g.objects(subj, GTS.ratifiedGSSP):
            if str(val).lower() == 'true':
                ratified = 1
            break

        concepts.append({
            'ics_uri': uri,
            'name': name,
            'rank': rank_name,
            'parent_uri': parent_uri,
            'start_mya': start_mya,
            'start_uncertainty': start_uncertainty,
            'end_mya': end_mya,
            'end_uncertainty': end_uncertainty,
            'short_code': short_code,
            'color': color,
            'display_order': display_order,
            'ratified_gssp': ratified,
        })

    print(f"  {len(concepts)} concepts extracted")

    # Count by rank
    rank_counts = {}
    for c in concepts:
        rank_counts[c['rank']] = rank_counts.get(c['rank'], 0) + 1
    for r in ['Super-Eon', 'Eon', 'Era', 'Period', 'Sub-Period', 'Epoch', 'Age']:
        if r in rank_counts:
            print(f"    {r}: {rank_counts[r]}")

    return concepts


def create_ics_chronostrat(cursor, concepts):
    """Create ics_chronostrat table and insert data (2-pass for parent_id)."""
    cursor.execute("DROP TABLE IF EXISTS temporal_ics_mapping")
    cursor.execute("DROP TABLE IF EXISTS ics_chronostrat")

    cursor.execute("""
        CREATE TABLE ics_chronostrat (
            id INTEGER PRIMARY KEY,
            ics_uri TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            rank TEXT NOT NULL,
            parent_id INTEGER,
            start_mya REAL,
            start_uncertainty REAL,
            end_mya REAL,
            end_uncertainty REAL,
            short_code TEXT,
            color TEXT,
            display_order INTEGER,
            ratified_gssp INTEGER DEFAULT 0,
            FOREIGN KEY (parent_id) REFERENCES ics_chronostrat(id)
        )
    """)
    cursor.execute("CREATE INDEX idx_ics_chrono_parent ON ics_chronostrat(parent_id)")
    cursor.execute("CREATE INDEX idx_ics_chrono_rank ON ics_chronostrat(rank)")

    # Pass 1: insert without parent_id
    for i, c in enumerate(concepts, 1):
        cursor.execute("""
            INSERT INTO ics_chronostrat
                (id, ics_uri, name, rank, start_mya, start_uncertainty,
                 end_mya, end_uncertainty, short_code, color, display_order, ratified_gssp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (i, c['ics_uri'], c['name'], c['rank'],
              c['start_mya'], c['start_uncertainty'],
              c['end_mya'], c['end_uncertainty'],
              c['short_code'], c['color'], c['display_order'], c['ratified_gssp']))

    # Build URI → id index
    uri_to_id = {}
    cursor.execute("SELECT id, ics_uri FROM ics_chronostrat")
    for row_id, uri in cursor.fetchall():
        uri_to_id[uri] = row_id

    # Pass 2: update parent_id
    parent_set = 0
    parent_missing = 0
    for c in concepts:
        if c['parent_uri']:
            parent_id = uri_to_id.get(c['parent_uri'])
            if parent_id:
                cursor.execute(
                    "UPDATE ics_chronostrat SET parent_id = ? WHERE ics_uri = ?",
                    (parent_id, c['ics_uri'])
                )
                parent_set += 1
            else:
                parent_missing += 1
                print(f"  Warning: parent not found for {c['name']}: {c['parent_uri']}")

    print(f"  ics_chronostrat: {len(concepts)} records inserted")
    print(f"    parent_id set: {parent_set}, missing: {parent_missing}")

    return uri_to_id


def create_temporal_ics_mapping(cursor, uri_to_id):
    """Create temporal_ics_mapping table with manual mapping definitions."""
    cursor.execute("DROP TABLE IF EXISTS temporal_ics_mapping")
    cursor.execute("""
        CREATE TABLE temporal_ics_mapping (
            id INTEGER PRIMARY KEY,
            temporal_code TEXT NOT NULL,
            ics_id INTEGER NOT NULL,
            mapping_type TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (ics_id) REFERENCES ics_chronostrat(id)
        )
    """)
    cursor.execute("CREATE INDEX idx_tim_code ON temporal_ics_mapping(temporal_code)")
    cursor.execute("CREATE INDEX idx_tim_ics ON temporal_ics_mapping(ics_id)")

    ischart_prefix = str(ISCHART)
    row_id = 0
    mapped_codes = 0
    unmappable_codes = 0

    for code, mappings in TEMPORAL_MAPPING.items():
        if not mappings:
            # INDET — unmappable, no row inserted but counted
            unmappable_codes += 1
            continue

        for ics_suffix, mapping_type in mappings:
            ics_uri = ischart_prefix + ics_suffix
            ics_id = uri_to_id.get(ics_uri)
            if ics_id is None:
                print(f"  Warning: ICS concept not found for {code}: {ics_suffix}")
                continue

            row_id += 1
            cursor.execute("""
                INSERT INTO temporal_ics_mapping (id, temporal_code, ics_id, mapping_type)
                VALUES (?, ?, ?, ?)
            """, (row_id, code, ics_id, mapping_type))

        mapped_codes += 1

    print(f"  temporal_ics_mapping: {row_id} records inserted")
    print(f"    Mapped codes: {mapped_codes}, Unmappable: {unmappable_codes}")
    return row_id


def add_provenance(cursor):
    """Add ICS data source to provenance table."""
    cursor.execute("""
        SELECT id FROM provenance
        WHERE citation LIKE '%International Chronostratigraphic%'
    """)
    if cursor.fetchone():
        print("  provenance: ICS entry already exists, skipping")
        return

    cursor.execute("""
        INSERT INTO provenance (source_type, citation, description, year, url)
        VALUES ('reference',
                'International Commission on Stratigraphy. International Chronostratigraphic Chart (GTS 2020)',
                'ICS standard geological time scale for temporal_ranges normalization',
                2020,
                'https://stratigraphy.org/chart')
    """)
    print("  provenance: ICS entry added")


def update_schema_descriptions(cursor):
    """Add schema descriptions for new tables."""
    descriptions = [
        # ics_chronostrat table
        ('ics_chronostrat', None, 'ICS International Chronostratigraphic Chart — hierarchical geological time units (GTS 2020, 179 concepts)'),
        ('ics_chronostrat', 'id', 'Primary key'),
        ('ics_chronostrat', 'ics_uri', 'ICS standard URI (e.g. http://resource.geosciml.org/classifier/ics/ischart/Cambrian)'),
        ('ics_chronostrat', 'name', 'English name of the time unit'),
        ('ics_chronostrat', 'rank', 'Hierarchical rank: Super-Eon, Eon, Era, Period, Sub-Period, Epoch, Age'),
        ('ics_chronostrat', 'parent_id', 'FK → ics_chronostrat.id (parent in hierarchy)'),
        ('ics_chronostrat', 'start_mya', 'Start of interval in millions of years ago (Ma)'),
        ('ics_chronostrat', 'start_uncertainty', 'Uncertainty of start_mya in Ma'),
        ('ics_chronostrat', 'end_mya', 'End of interval in millions of years ago (Ma)'),
        ('ics_chronostrat', 'end_uncertainty', 'Uncertainty of end_mya in Ma'),
        ('ics_chronostrat', 'short_code', 'CCGM short code (e.g. Ep for Cambrian)'),
        ('ics_chronostrat', 'color', 'ICS standard hex color (e.g. #7FA056)'),
        ('ics_chronostrat', 'display_order', 'Sort order from ICS chart (sh:order)'),
        ('ics_chronostrat', 'ratified_gssp', 'Whether the GSSP has been ratified (0/1)'),
        # temporal_ics_mapping table
        ('temporal_ics_mapping', None, 'Mapping between Trilobase temporal_ranges codes and ICS chronostratigraphic concepts'),
        ('temporal_ics_mapping', 'id', 'Primary key'),
        ('temporal_ics_mapping', 'temporal_code', 'Trilobase temporal code (FK → temporal_ranges.code)'),
        ('temporal_ics_mapping', 'ics_id', 'FK → ics_chronostrat.id'),
        ('temporal_ics_mapping', 'mapping_type', 'exact (1:1), partial (1:many subset), aggregate (combined range), unmappable'),
        ('temporal_ics_mapping', 'notes', 'Optional notes about the mapping'),
    ]

    for table_name, column_name, description in descriptions:
        cursor.execute("""
            INSERT OR REPLACE INTO schema_descriptions (table_name, column_name, description)
            VALUES (?, ?, ?)
        """, (table_name, column_name, description))

    print(f"  schema_descriptions: {len(descriptions)} entries added/updated")


def print_report(cursor):
    """Print detailed import report."""
    print("\n" + "=" * 70)
    print("ICS CHRONOSTRAT REPORT")
    print("=" * 70)

    # Summary
    cursor.execute("SELECT COUNT(*) FROM ics_chronostrat")
    total = cursor.fetchone()[0]
    print(f"\nTotal ICS concepts: {total}")

    # By rank
    cursor.execute("""
        SELECT rank, COUNT(*) FROM ics_chronostrat
        GROUP BY rank ORDER BY
            CASE rank
                WHEN 'Super-Eon' THEN 1
                WHEN 'Eon' THEN 2
                WHEN 'Era' THEN 3
                WHEN 'Period' THEN 4
                WHEN 'Sub-Period' THEN 5
                WHEN 'Epoch' THEN 6
                WHEN 'Age' THEN 7
            END
    """)
    print("\nBy rank:")
    for rank, count in cursor.fetchall():
        print(f"  {rank:15s} {count:4d}")

    # Hierarchy check: concepts without parent
    cursor.execute("""
        SELECT name, rank FROM ics_chronostrat WHERE parent_id IS NULL
        ORDER BY rank, name
    """)
    rows = cursor.fetchall()
    print(f"\nRoot concepts (no parent): {len(rows)}")
    for name, rank in rows:
        print(f"  {rank:15s} {name}")

    # Mapping summary
    cursor.execute("SELECT COUNT(*) FROM temporal_ics_mapping")
    mapping_total = cursor.fetchone()[0]
    print(f"\nTemporal-ICS mapping rows: {mapping_total}")

    cursor.execute("""
        SELECT mapping_type, COUNT(*) FROM temporal_ics_mapping
        GROUP BY mapping_type ORDER BY COUNT(*) DESC
    """)
    print("\nBy mapping type:")
    for mtype, count in cursor.fetchall():
        print(f"  {mtype:15s} {count:4d}")

    # Detailed mapping
    cursor.execute("""
        SELECT m.temporal_code, ic.name, m.mapping_type
        FROM temporal_ics_mapping m
        JOIN ics_chronostrat ic ON m.ics_id = ic.id
        ORDER BY m.temporal_code, ic.name
    """)
    rows = cursor.fetchall()
    print(f"\nDetailed mapping ({len(rows)} rows):")
    current_code = None
    for code, ics_name, mtype in rows:
        if code != current_code:
            current_code = code
            print(f"\n  {code}:")
        print(f"    → {ics_name} ({mtype})")

    # Check unmapped temporal codes
    cursor.execute("SELECT code FROM temporal_ranges")
    all_codes = {row[0] for row in cursor.fetchall()}
    cursor.execute("SELECT DISTINCT temporal_code FROM temporal_ics_mapping")
    mapped_codes = {row[0] for row in cursor.fetchall()}
    unmapped = all_codes - mapped_codes
    if unmapped:
        print(f"\nUnmapped temporal codes: {sorted(unmapped)}")

    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Import ICS International Chronostratigraphic Chart (GTS 2020)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without modifying DB')
    parser.add_argument('--report', action='store_true',
                        help='Print report only (tables must exist)')
    args = parser.parse_args()

    db_path = os.path.abspath(DB_PATH)
    ttl_path = os.path.abspath(TTL_PATH)

    if not os.path.exists(db_path):
        print(f"Error: DB not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    if args.report:
        conn = sqlite3.connect(db_path)
        print_report(conn.cursor())
        conn.close()
        return

    if not os.path.exists(ttl_path):
        print(f"Error: TTL file not found: {ttl_path}", file=sys.stderr)
        print("Expected at: vendor/ics/gts2020/chart.ttl")
        sys.exit(1)

    # Parse TTL
    concepts = parse_ttl(ttl_path)

    if args.dry_run:
        print("\n=== DRY RUN (no DB changes) ===")
        print(f"\nWould create ics_chronostrat with {len(concepts)} records")

        # Preview mapping
        ischart_prefix = str(ISCHART)
        uri_set = {c['ics_uri'] for c in concepts}
        total_rows = 0
        missing = []
        for code, mappings in TEMPORAL_MAPPING.items():
            for ics_suffix, mtype in mappings:
                uri = ischart_prefix + ics_suffix
                if uri in uri_set:
                    total_rows += 1
                else:
                    missing.append(f"{code} → {ics_suffix}")

        print(f"Would create temporal_ics_mapping with {total_rows} rows")
        if missing:
            print(f"WARNING: {len(missing)} mapping targets not found:")
            for m in missing:
                print(f"  {m}")
        else:
            print("All mapping targets found in TTL data")
        return

    # Full import
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n[1] Creating ics_chronostrat table...")
    uri_to_id = create_ics_chronostrat(cursor, concepts)

    print("\n[2] Creating temporal_ics_mapping table...")
    create_temporal_ics_mapping(cursor, uri_to_id)

    print("\n[3] Adding provenance record...")
    add_provenance(cursor)

    print("\n[4] Updating schema descriptions...")
    update_schema_descriptions(cursor)

    conn.commit()

    # Report
    print_report(cursor)

    conn.close()
    print("Done.")


if __name__ == '__main__':
    main()
