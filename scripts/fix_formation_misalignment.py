#!/usr/bin/env python3
"""
T-5 Phase B: Fix formation field misalignment.

Root cause: create_database.py split text between `]` and `; FAMILY;` on the
first comma only. When the source had `Region, Country` (no formation), the
region ended up in the formation field and the country in the location field.
When the source had only `Country`, the country ended up in formation with
location=NULL.

Three fix types:
  Type 1: formation = country/region, location IS NULL (8 clear cases)
    → formation → NULL, genus_formations delete, genus_locations create
  Type 2: formation = location (39 cases: country appears in both fields)
    → formation → NULL, genus_formations delete
  Type 3: formation = region, location = country (no geological suffix)
    → formation → NULL, genus_locations.region = old formation, genus_formations delete

Whitelist protects genuine formations without standard suffixes.

Usage:
    python scripts/fix_formation_misalignment.py --dry-run   # Report only
    python scripts/fix_formation_misalignment.py             # Apply fix
"""
import argparse
import os
import sqlite3
import sys

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
DB_PATH = os.path.join(BASE_DIR, 'db', 'trilobase.db')
PC_DB_PATH = os.path.join(BASE_DIR, 'db', 'paleocore.db')

# Genuine formations that lack standard suffixes (Fm/Lst/Sh/Gp/etc.)
# These should NOT be reclassified as regions.
FORMATION_WHITELIST = {
    # Known valid formation names without standard suffix
    'Andrarum',             # Swedish locality/formation
    'Surkh Bum',            # Afghanistan formation
    'Sukh Bum',             # variant spelling
    'Alum Sh',              # Shale (has suffix actually)
    'Alanis Sh',            # Shale
    'River Popovka',        # Russian stratigraphic locality
    'Krekling',             # Norwegian formation
    'Huai Luang Sh',        # Shale
    'Herrerias Marl',       # Marl
    'Donetz Basin',         # Stratigraphic basin
    'Adams Argillite',      # Argillite formation
    'Kiln Mdst',            # Mudstone
    'Kersdown Chert',       # Chert
    'White Point Cgte',     # Conglomerate
    'Lingula Flags',        # Historic formation name
    'Lower Lingula Flags',  # Historic formation name
    'Weston Flags',         # Historic formation name
    'Leenane Grits',        # Historic formation name
    'Hell\'s Mouth Grits',  # Historic formation name
    'Skiddaw Slates',       # Historic formation name
    'Ty-draw Slates',       # Historic formation name
    'Leimitz Schiefer',     # German formation (=schist/slate)
    'Geigen Schiefer',      # German formation
    'Geigen Schiefe',       # variant
    'Bokkeveld Group',      # Group (has suffix in concept)
    'Llanfawr Mdst',        # Mudstone
    'U Jon-strop Mdst',     # Mudstone
    'Wiltz Schicten',       # German formation (=Schichten)
    'Peltura-Stufe',        # German stratigraphic unit (=Stage)
    'Maekula-Schichten',    # German formation
    'Herkunfts-Schichten',  # German formation
    'Alternances Greso Calcaires',    # French formation
    'Alternances Greso-Calcaires',    # variant
    'Schistes de Saint-Chinian',      # French formation (=Shale)
    'Schistes non troues',            # French formation
    'Schistes troues',                # French formation
    'Gres de Marcory',                # French formation (=Sandstone)
    'Gres schistes et calcaires',     # French formation
    'Bancos Mixtos',                  # Spanish formation
    'Complejo de Ranaces',            # Spanish formation
    'Chorbusulina wilkesi Faunule',   # Faunal unit
    'P. forchhammeri Grit',           # Historic formation name
    '"Ostrakoden-Kalk"',              # German formation (=Limestone)
    'Bad-Grund/Ober Harz (cuII)',     # German formation
    'Rheinisches Schiefergebirge',    # German geological region (stratigraphic context)
    'Schwarzwald (Black Forrest)',    # Geological region
    'Bron-y-Buckley Wood',           # Welsh formation
    'Chirbet el-Burdsch',            # Formation
    'Chirbet el-Burj',               # variant
    'Dimeh Salt Plug',               # Geological feature
    'Geschiebe glacial erratics',    # Geological context
    'glacial boulder',               # Geological context
    'glacial erratic',               # Geological context
    'glacial erratic boulders',      # Geological context
    'glacial erratics',              # Geological context
    'erratic boulders',              # Geological context
}

# Geological suffixes that indicate a real formation
FORMATION_SUFFIXES = [
    ' Fm', ' Lst', ' Sh', ' Gp', ' Beds', ' Zone', ' Suite', ' Horizon',
    ' Series', ' Stage', ' Marl', ' Sst', ' Qtz', ' Dol', ' Limestone',
    ' Sandstone', ' Shale', ' Group', ' Congl', ' Volcanics', ' Member',
    ' Mbr', ' Flags', ' Grits', ' Slates', ' Argillite', ' Chert',
    ' Mdst', ' Schiefer', ' Schicten', ' Schichten', ' Cgte',
    ' Quartzite', ' Conglomerate', ' Calc',
]

# Country name normalization (used for matching formation values to countries)
COUNTRY_NORMALIZE = {
    'central Kazakhstan': 'Central Kazakhstan',
    'central Morocco': 'Central Morocco',
    'central Afghanistan': 'Central Afghanistan',
    'southern Kazakhstan': 'S Kazakhstan',
    'arctic Russia': 'Arctic Russia',
    'eastern Iran': 'Eastern Iran',
}

# Special Type 1 overrides: genus_name → (country_name, region)
# For location-NULL genera whose formation is a region (not a country)
TYPE1_REGION_OVERRIDES = {
    'Tetralichas': ('Russia', 'Baltic Russia'),
}


def has_formation_suffix(name):
    """Check if a name contains a geological formation suffix."""
    for suffix in FORMATION_SUFFIXES:
        if suffix in name or name.endswith(suffix.strip()):
            return True
    return False


def classify_records(cursor):
    """Classify all potential misalignment cases into types."""
    type1 = []  # formation=country, location=NULL
    type2 = []  # formation=location (same value in both)
    type3 = []  # formation=region, location=country (no suffix)
    skipped_whitelist = []
    skipped_has_suffix = []

    # Build country name set
    cursor.execute("SELECT id, name FROM pc.countries")
    country_map = {row[1]: row[0] for row in cursor.fetchall()}
    country_names = set(country_map.keys())
    # Add normalized variants
    for norm_from, norm_to in COUNTRY_NORMALIZE.items():
        if norm_to in country_names:
            country_names.add(norm_from)

    # --- Type 1: location IS NULL, formation is a country/region ---
    cursor.execute("""
        SELECT tr.id, tr.name, tr.formation
        FROM taxonomic_ranks tr
        WHERE tr.rank = 'Genus'
          AND tr.location IS NULL
          AND tr.formation IS NOT NULL
    """)
    for tr_id, name, formation in cursor.fetchall():
        # Check special overrides first (region names that aren't in countries table)
        if name in TYPE1_REGION_OVERRIDES:
            country_name, region = TYPE1_REGION_OVERRIDES[name]
            country_id = country_map.get(country_name)
            type1.append({
                'tr_id': tr_id, 'name': name, 'formation': formation,
                'country_name': country_name, 'country_id': country_id,
                'region': region,
            })
            continue

        # Check if formation is a known country
        norm_fm = COUNTRY_NORMALIZE.get(formation, formation)
        if norm_fm in country_names:
            country_id = country_map.get(norm_fm)
            type1.append({
                'tr_id': tr_id, 'name': name, 'formation': formation,
                'country_name': norm_fm, 'country_id': country_id,
                'region': None,
            })
        # else: real formation with NULL location (e.g. Mungerebar Lst) — leave as is

    # --- Type 2 & 3: formation exists, location exists, location is a single country ---
    cursor.execute("""
        SELECT tr.id, tr.name, tr.formation, tr.location
        FROM taxonomic_ranks tr
        WHERE tr.rank = 'Genus'
          AND tr.formation IS NOT NULL
          AND tr.location IS NOT NULL
          AND tr.location NOT LIKE '%,%'
    """)
    for tr_id, name, formation, location in cursor.fetchall():
        # Check if location is a known country
        norm_loc = COUNTRY_NORMALIZE.get(location, location)
        if norm_loc not in country_names:
            continue  # Not a simple country — skip

        # Type 2: formation = location (both are country name)
        if formation == location:
            country_id = country_map.get(norm_loc)
            type2.append({
                'tr_id': tr_id, 'name': name, 'formation': formation,
                'location': location, 'country_name': norm_loc,
                'country_id': country_id,
            })
            continue

        # Check if formation is whitelisted
        if formation in FORMATION_WHITELIST:
            skipped_whitelist.append({
                'tr_id': tr_id, 'name': name, 'formation': formation,
                'location': location,
            })
            continue

        # Check if formation has a geological suffix
        if has_formation_suffix(formation):
            skipped_has_suffix.append({
                'tr_id': tr_id, 'name': name, 'formation': formation,
                'location': location,
            })
            continue

        # Type 3: formation is a region, location is a country
        country_id = country_map.get(norm_loc)
        type3.append({
            'tr_id': tr_id, 'name': name, 'formation': formation,
            'location': location, 'country_name': norm_loc,
            'country_id': country_id,
        })

    return type1, type2, type3, skipped_whitelist, skipped_has_suffix


def apply_type1(cursor, records, dry_run=False):
    """Fix Type 1: formation=country/region, location=NULL.

    Actions:
      1. taxonomic_ranks.formation → NULL
      2. Delete from genus_formations (pointing to fake formation)
      3. Create genus_locations entry with correct country_id (and region if applicable)
    """
    for rec in records:
        tr_id = rec['tr_id']
        country_id = rec['country_id']
        region = rec.get('region')

        if not dry_run:
            # Clear formation
            cursor.execute(
                "UPDATE taxonomic_ranks SET formation = NULL WHERE id = ?",
                (tr_id,)
            )
            # Delete genus_formations entry
            cursor.execute(
                "DELETE FROM genus_formations WHERE genus_id = ?",
                (tr_id,)
            )
            # Create genus_locations entry (if country_id found)
            if country_id:
                cursor.execute(
                    "INSERT OR IGNORE INTO genus_locations (genus_id, country_id, region) VALUES (?, ?, ?)",
                    (tr_id, country_id, region)
                )


def apply_type2(cursor, records, dry_run=False):
    """Fix Type 2: formation=location (both are country name).

    Actions:
      1. taxonomic_ranks.formation → NULL
      2. Delete from genus_formations (pointing to fake formation)
      (genus_locations already has the correct country from Phase A)
    """
    for rec in records:
        tr_id = rec['tr_id']

        if not dry_run:
            cursor.execute(
                "UPDATE taxonomic_ranks SET formation = NULL WHERE id = ?",
                (tr_id,)
            )
            cursor.execute(
                "DELETE FROM genus_formations WHERE genus_id = ?",
                (tr_id,)
            )


def apply_type3(cursor, records, dry_run=False):
    """Fix Type 3: formation=region, location=country.

    Actions:
      1. taxonomic_ranks.formation → NULL
      2. Delete from genus_formations (pointing to fake formation)
      3. Set genus_locations.region = old formation value
    """
    for rec in records:
        tr_id = rec['tr_id']
        region_name = rec['formation']

        if not dry_run:
            cursor.execute(
                "UPDATE taxonomic_ranks SET formation = NULL WHERE id = ?",
                (tr_id,)
            )
            cursor.execute(
                "DELETE FROM genus_formations WHERE genus_id = ?",
                (tr_id,)
            )
            # Set region on the genus_locations entry
            cursor.execute(
                "UPDATE genus_locations SET region = ? WHERE genus_id = ? AND region IS NULL",
                (region_name, tr_id)
            )


def clean_orphan_formations(cursor, dry_run=False):
    """Delete formations from pc.formations that are no longer referenced."""
    cursor.execute("""
        SELECT f.id, f.name FROM pc.formations f
        WHERE NOT EXISTS (
            SELECT 1 FROM genus_formations gf WHERE gf.formation_id = f.id
        )
        AND f.formation_type IS NULL
    """)
    orphans = cursor.fetchall()

    if not dry_run and orphans:
        for f_id, f_name in orphans:
            cursor.execute("DELETE FROM pc.formations WHERE id = ?", (f_id,))

    return orphans


def main():
    parser = argparse.ArgumentParser(description='Fix formation field misalignment')
    parser.add_argument('--dry-run', action='store_true', help='Report changes without applying')
    args = parser.parse_args()

    db_path = os.path.abspath(DB_PATH)
    pc_path = os.path.abspath(PC_DB_PATH)

    if not os.path.exists(db_path):
        print(f"Error: DB not found: {db_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(pc_path):
        print(f"Error: PaleoCore DB not found: {pc_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.execute(f"ATTACH DATABASE '{pc_path}' AS pc")
    cursor = conn.cursor()

    print(f"=== Phase B: Formation Misalignment Fix {'(DRY RUN)' if args.dry_run else ''} ===\n")

    # Classify
    type1, type2, type3, skipped_wl, skipped_sf = classify_records(cursor)

    # Report
    print(f"Type 1 (formation=country, location=NULL): {len(type1)}")
    for rec in type1:
        print(f"  {rec['name']}: formation='{rec['formation']}' → country_id={rec['country_id']} ({rec['country_name']})")

    print(f"\nType 2 (formation=location, same value): {len(type2)}")
    for rec in type2[:10]:
        print(f"  {rec['name']}: formation=location='{rec['formation']}'")
    if len(type2) > 10:
        print(f"  ... and {len(type2) - 10} more")

    print(f"\nType 3 (formation=region, location=country): {len(type3)}")
    for rec in type3[:20]:
        print(f"  {rec['name']}: formation='{rec['formation']}', location='{rec['location']}'")
    if len(type3) > 20:
        print(f"  ... and {len(type3) - 20} more")

    print(f"\nSkipped (whitelist): {len(skipped_wl)}")
    print(f"Skipped (has suffix): {len(skipped_sf)}")

    total_fixes = len(type1) + len(type2) + len(type3)
    print(f"\nTotal to fix: {total_fixes}")

    # Apply
    if not args.dry_run and total_fixes > 0:
        print(f"\nApplying fixes...")
        apply_type1(cursor, type1, dry_run=False)
        print(f"  Type 1: {len(type1)} fixed")
        apply_type2(cursor, type2, dry_run=False)
        print(f"  Type 2: {len(type2)} fixed")
        apply_type3(cursor, type3, dry_run=False)
        print(f"  Type 3: {len(type3)} fixed")

        # Clean orphan formations
        orphans = clean_orphan_formations(cursor, dry_run=False)
        print(f"  Orphan formations deleted: {len(orphans)}")

        conn.commit()
        print(f"\nChanges committed.")

        # Post-fix stats
        cursor.execute("SELECT COUNT(*) FROM taxonomic_ranks WHERE rank = 'Genus' AND formation IS NOT NULL")
        fm_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM genus_formations")
        gf_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM genus_locations")
        gl_count = cursor.fetchone()[0]
        print(f"\nPost-fix counts:")
        print(f"  Genera with formation: {fm_count}")
        print(f"  genus_formations: {gf_count}")
        print(f"  genus_locations: {gl_count}")

    conn.close()


if __name__ == '__main__':
    main()
