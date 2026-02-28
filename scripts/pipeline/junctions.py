"""Step 6: Junction tables — genus_formations and genus_locations.

Creates junction tables using exact matching (no LIKE) for country_id,
and proper formation/location separation.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .parse_genera import GenusRecord, COUNTRY_NORMALIZE, LOCATION_OVERRIDES


def _resolve_country_id(country_name: str | None,
                        country_map: dict[str, int]) -> int | None:
    """Resolve country name to countries.id via exact match."""
    if not country_name:
        return None
    normalized = COUNTRY_NORMALIZE.get(country_name, country_name)
    return country_map.get(normalized)


def _resolve_region_id(region: str | None,
                       country_id: int | None,
                       conn: sqlite3.Connection) -> int | None:
    """Resolve region text + country_id to geographic_regions.id.

    Uses country_id → geographic_regions mapping via country_cow_mapping.
    """
    if not country_id:
        return None

    pc_cur = conn.cursor()

    # Find the geographic_regions entry for this country
    # First, find the cow_ccode for this country
    pc_cur.execute("""
        SELECT cm.cow_ccode FROM pc.country_cow_mapping cm
        WHERE cm.country_id = ?
    """, (country_id,))
    row = pc_cur.fetchone()
    cow_ccode = row[0] if row else None

    if not region:
        # No region → return the country-level geographic_regions.id
        if cow_ccode is not None:
            pc_cur.execute("""
                SELECT id FROM pc.geographic_regions
                WHERE cow_ccode = ? AND level = 'country'
            """, (cow_ccode,))
        else:
            # Unmappable country — look up by name
            pc_cur.execute("""
                SELECT gr.id FROM pc.geographic_regions gr
                JOIN pc.countries c ON c.name = gr.name
                WHERE c.id = ? AND gr.level = 'country'
            """, (country_id,))
        row = pc_cur.fetchone()
        return row[0] if row else None

    # Has region — find region-level entry under the country
    # First get country geo_id
    country_geo_id = None
    if cow_ccode is not None:
        pc_cur.execute("""
            SELECT id FROM pc.geographic_regions
            WHERE cow_ccode = ? AND level = 'country'
        """, (cow_ccode,))
        row = pc_cur.fetchone()
        country_geo_id = row[0] if row else None
    else:
        pc_cur.execute("""
            SELECT gr.id FROM pc.geographic_regions gr
            JOIN pc.countries c ON c.name = gr.name
            WHERE c.id = ? AND gr.level = 'country'
        """, (country_id,))
        row = pc_cur.fetchone()
        country_geo_id = row[0] if row else None

    if not country_geo_id:
        return None

    # Look for exact region match
    pc_cur.execute("""
        SELECT id FROM pc.geographic_regions
        WHERE name = ? AND parent_id = ? AND level = 'region'
    """, (region, country_geo_id))
    row = pc_cur.fetchone()
    if row:
        return row[0]

    # Also check if the country itself is a region entry
    # (e.g. "England" is both a country and a region under "United Kingdom")
    pc_cur.execute("""
        SELECT gr.id FROM pc.geographic_regions gr
        JOIN pc.countries c ON c.name = gr.name
        WHERE c.id = ? AND gr.level = 'region' AND gr.parent_id = ?
    """, (country_id, country_geo_id))
    row = pc_cur.fetchone()
    if row:
        # The country entry itself is the region
        return row[0]

    # Fallback to country level
    return country_geo_id


def load_junctions(trilobase_path: Path,
                   paleocore_path: Path,
                   genera: list[GenusRecord],
                   name_to_id: dict[str, int],
                   country_map: dict[str, int],
                   formation_map: dict[str, int]):
    """Populate genus_formations and genus_locations tables.

    Uses trilobase.db with paleocore.db attached as 'pc'.
    """
    conn = sqlite3.connect(str(trilobase_path))
    conn.execute(f"ATTACH DATABASE '{paleocore_path}' AS pc")
    cur = conn.cursor()

    gf_count = 0
    gl_count = 0

    for rec in genera:
        genus_id = name_to_id.get(rec.name)
        if not genus_id:
            continue

        # --- genus_formations ---
        if rec.formation:
            fm_id = formation_map.get(rec.formation)
            if fm_id:
                try:
                    cur.execute("""
                        INSERT OR IGNORE INTO genus_formations
                            (genus_id, formation_id)
                        VALUES (?, ?)
                    """, (genus_id, fm_id))
                    if cur.rowcount > 0:
                        gf_count += 1
                except sqlite3.IntegrityError:
                    pass

        # --- genus_locations ---
        country = rec.country
        region = rec.region

        # Handle Type 1 case: formation is actually a country
        # (no location, formation is not a real formation)
        if not rec.location and rec.formation:
            from .parse_genera import _has_formation_suffix, FORMATION_WHITELIST
            if not _has_formation_suffix(rec.formation) and rec.formation not in FORMATION_WHITELIST:
                # Check if formation is a country name
                fm_as_country = COUNTRY_NORMALIZE.get(rec.formation, rec.formation)
                if fm_as_country in country_map:
                    country = fm_as_country
                    region = None

        if country:
            country_id = _resolve_country_id(country, country_map)
            if country_id:
                region_id = _resolve_region_id(region, country_id, conn)
                try:
                    cur.execute("""
                        INSERT OR IGNORE INTO genus_locations
                            (genus_id, country_id, region, region_id)
                        VALUES (?, ?, ?, ?)
                    """, (genus_id, country_id, region, region_id))
                    if cur.rowcount > 0:
                        gl_count += 1
                except sqlite3.IntegrityError:
                    pass

    conn.commit()
    conn.close()

    print(f'    genus_formations: {gf_count}')
    print(f'    genus_locations: {gl_count}')
