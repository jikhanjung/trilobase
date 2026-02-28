"""Step 8: Validation — verify rebuilt DB matches expected counts.

Runs a battery of SQL checks against the rebuilt trilobase.db and
paleocore.db to ensure correctness.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


# ---------------------------------------------------------------------------
# Expected counts (from current production DB v0.2.5)
# ---------------------------------------------------------------------------

CHECKS: list[tuple[str, str, str | int | float]] = [
    # --- taxonomic_ranks ---
    ('taxonomic_ranks total',
     'SELECT COUNT(*) FROM taxonomic_ranks',
     5341),
    ('Class count',
     "SELECT COUNT(*) FROM taxonomic_ranks WHERE rank='Class'",
     1),
    ('Order count',
     "SELECT COUNT(*) FROM taxonomic_ranks WHERE rank='Order'",
     13),
    ('Suborder count',
     "SELECT COUNT(*) FROM taxonomic_ranks WHERE rank='Suborder'",
     9),
    ('Superfamily count',
     "SELECT COUNT(*) FROM taxonomic_ranks WHERE rank='Superfamily'",
     13),
    ('Family count',
     "SELECT COUNT(*) FROM taxonomic_ranks WHERE rank='Family'",
     190),
    ('Genus count',
     "SELECT COUNT(*) FROM taxonomic_ranks WHERE rank='Genus'",
     5115),
    ('valid genera',
     "SELECT COUNT(*) FROM taxonomic_ranks WHERE rank='Genus' AND is_valid=1",
     4259),
    ('invalid genera',
     "SELECT COUNT(*) FROM taxonomic_ranks WHERE rank='Genus' AND is_valid=0",
     856),
    ('parent_id NULL (valid genera)',
     "SELECT COUNT(*) FROM taxonomic_ranks "
     "WHERE rank='Genus' AND is_valid=1 AND parent_id IS NULL",
     0),

    # --- taxonomic_opinions ---
    ('opinions total',
     'SELECT COUNT(*) FROM taxonomic_opinions',
     1139),
    ('SYNONYM_OF opinions',
     "SELECT COUNT(*) FROM taxonomic_opinions WHERE opinion_type='SYNONYM_OF'",
     1055),
    ('PLACED_IN opinions',
     "SELECT COUNT(*) FROM taxonomic_opinions WHERE opinion_type='PLACED_IN'",
     82),
    ('SPELLING_OF opinions',
     "SELECT COUNT(*) FROM taxonomic_opinions WHERE opinion_type='SPELLING_OF'",
     2),

    # --- bibliography ---
    ('bibliography',
     'SELECT COUNT(*) FROM bibliography',
     2131),

    # --- taxon_bibliography ---
    ('taxon_bibliography',
     'SELECT COUNT(*) FROM taxon_bibliography',
     '>=4100'),

    # --- junctions ---
    ('genus_formations',
     'SELECT COUNT(*) FROM genus_formations',
     '>=4500'),
    ('genus_locations',
     'SELECT COUNT(*) FROM genus_locations',
     '>=4840'),

    # --- temporal_ranges ---
    ('temporal_ranges',
     'SELECT COUNT(*) FROM temporal_ranges',
     28),

    # --- metadata ---
    ('artifact_metadata',
     'SELECT COUNT(*) FROM artifact_metadata',
     7),
    ('provenance',
     'SELECT COUNT(*) FROM provenance',
     5),
    ('ui_display_intent',
     'SELECT COUNT(*) FROM ui_display_intent',
     6),
    ('ui_queries',
     'SELECT COUNT(*) FROM ui_queries',
     37),
    ('ui_manifest',
     'SELECT COUNT(*) FROM ui_manifest',
     1),
    ('schema_descriptions',
     'SELECT COUNT(*) FROM schema_descriptions',
     '>=100'),
]

PALEOCORE_CHECKS: list[tuple[str, str, str | int | float]] = [
    ('pc.countries',
     'SELECT COUNT(*) FROM countries',
     '>=140'),
    ('pc.formations',
     'SELECT COUNT(*) FROM formations',
     '>=1780'),
    ('pc.temporal_ranges',
     'SELECT COUNT(*) FROM temporal_ranges',
     28),
    ('pc.cow_states',
     'SELECT COUNT(*) FROM cow_states',
     '>=240'),
    ('pc.country_cow_mapping',
     'SELECT COUNT(*) FROM country_cow_mapping',
     '>=130'),
    ('pc.geographic_regions',
     'SELECT COUNT(*) FROM geographic_regions',
     '>=600'),
    ('pc.ics_chronostrat',
     'SELECT COUNT(*) FROM ics_chronostrat',
     178),
    ('pc.temporal_ics_mapping',
     'SELECT COUNT(*) FROM temporal_ics_mapping',
     '>=25'),
]

# Data quality checks
QUALITY_CHECKS: list[tuple[str, str, int]] = [
    # No formation values that are actually country names
    ('no formation=country (China)',
     "SELECT COUNT(*) FROM genus_formations gf "
     "JOIN formations f ON gf.formation_id = f.id "
     "WHERE f.name = 'China'",
     0),
    # No England→China misassignment
    ('no China→England swap',
     "SELECT COUNT(*) FROM genus_locations gl "
     "JOIN countries c ON gl.country_id = c.id "
     "WHERE c.name = 'China' AND gl.region = 'England'",
     0),
]


def _check_value(actual: int | float,
                 expected: int | float | str) -> tuple[bool, str]:
    """Compare actual value against expected (exact or threshold)."""
    if isinstance(expected, str):
        if expected.startswith('>='):
            threshold = float(expected[2:])
            ok = actual >= threshold
            return ok, f'{actual} (expected >={threshold})'
        elif expected.startswith('<='):
            threshold = float(expected[2:])
            ok = actual <= threshold
            return ok, f'{actual} (expected <={threshold})'
        else:
            # exact string comparison
            ok = str(actual) == expected
            return ok, f'{actual} (expected {expected})'
    else:
        ok = actual == expected
        return ok, f'{actual} (expected {expected})'


def validate(trilobase_path: Path,
             paleocore_path: Path | None = None,
             verbose: bool = True) -> tuple[int, int]:
    """Run all validation checks.

    Returns (pass_count, fail_count).
    """
    pass_count = 0
    fail_count = 0

    conn = sqlite3.connect(str(trilobase_path))

    # Attach paleocore if available (for quality checks)
    if paleocore_path and paleocore_path.exists():
        conn.execute(f"ATTACH DATABASE '{paleocore_path}' AS pc")

    if verbose:
        print('\n  === Trilobase Validation ===')

    for label, sql, expected in CHECKS:
        try:
            val = conn.execute(sql).fetchone()[0]
            ok, detail = _check_value(val, expected)
            status = 'PASS' if ok else 'FAIL'
            if ok:
                pass_count += 1
            else:
                fail_count += 1
            if verbose:
                mark = '  ✓' if ok else '  ✗'
                print(f'{mark} {label}: {detail}')
        except Exception as e:
            fail_count += 1
            if verbose:
                print(f'  ✗ {label}: ERROR — {e}')

    # Quality checks (need paleocore attached)
    if paleocore_path and paleocore_path.exists():
        if verbose:
            print('\n  === Data Quality ===')
        for label, sql, expected in QUALITY_CHECKS:
            try:
                val = conn.execute(sql).fetchone()[0]
                ok, detail = _check_value(val, expected)
                status = 'PASS' if ok else 'FAIL'
                if ok:
                    pass_count += 1
                else:
                    fail_count += 1
                if verbose:
                    mark = '  ✓' if ok else '  ✗'
                    print(f'{mark} {label}: {detail}')
            except Exception as e:
                fail_count += 1
                if verbose:
                    print(f'  ✗ {label}: ERROR — {e}')

    conn.close()

    # PaleoCore checks
    if paleocore_path and paleocore_path.exists():
        if verbose:
            print('\n  === PaleoCore Validation ===')
        pc_conn = sqlite3.connect(str(paleocore_path))
        for label, sql, expected in PALEOCORE_CHECKS:
            try:
                val = pc_conn.execute(sql).fetchone()[0]
                ok, detail = _check_value(val, expected)
                if ok:
                    pass_count += 1
                else:
                    fail_count += 1
                if verbose:
                    mark = '  ✓' if ok else '  ✗'
                    print(f'{mark} {label}: {detail}')
            except Exception as e:
                fail_count += 1
                if verbose:
                    print(f'  ✗ {label}: ERROR — {e}')
        pc_conn.close()

    if verbose:
        total = pass_count + fail_count
        print(f'\n  Results: {pass_count}/{total} passed, {fail_count} failed')

    return pass_count, fail_count
